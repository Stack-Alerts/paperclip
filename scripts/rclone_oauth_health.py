#!/usr/bin/env python3
"""rclone OAuth token health monitor for the Paperclip GDrive backup pipeline.

Reads the decrypted rclone config, inspects the OAuth token for the ``gdrive``
remote, and fires a Paperclip alert issue when the token is missing, expired, or
non-functional (connectivity check fails).

Runs on the self-hosted runner so it has filesystem access to the rclone config
and password.  Expected interval: every 15 min via GitHub Actions.

Usage:
    python scripts/rclone_oauth_health.py
    python scripts/rclone_oauth_health.py --dry-run
    python scripts/rclone_oauth_health.py --json-summary
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from touch_index.paperclip_client import _session, _base, _company

MONITOR_LOG = Path.home() / ".paperclip" / "rclone_oauth_health.log"
MONITOR_STATE = Path.home() / ".paperclip" / "rclone_oauth_health_state.json"
MAX_LOG_BYTES = 1 * 1024 * 1024

RCLONE_CONFIG = Path(os.environ.get("RCLONE_CONFIG", Path.home() / ".config" / "rclone" / "rclone.conf"))
RCLONE_PASS_FILE = Path(os.environ.get("RCLONE_PASS_FILE", Path.home() / ".config" / "rclone" / "rclone-pass"))
RCLONE_REMOTE = "gdrive"
RCLONE_REMOTE_DIR = "gdrive:Paperclip-Backups"

ALERT_SEARCH_QUERY = "rclone OAuth health alert"
CTO_AGENT_ID = "41b5ede6-e209-40ba-b923-dc969c722e6d"

EXPIRY_WARN_HOURS = 6
ALERT_COOLDOWN_HOURS = 2  # suppress new alerts if one was fired within this window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(MONITOR_LOG),
        logging.StreamHandler() if os.isatty(0) else logging.NullHandler(),
    ],
)
logger = logging.getLogger("rclone_oauth_health")


def _rotate_log_if_needed():
    if MONITOR_LOG.exists() and MONITOR_LOG.stat().st_size > MAX_LOG_BYTES:
        bak = MONITOR_LOG.with_suffix(".log.1")
        bak.write_text(MONITOR_LOG.read_text())
        MONITOR_LOG.write_text("")
        logger.info("Rotated log (size exceeded %d bytes)", MAX_LOG_BYTES)


def _read_rclone_pass() -> str | None:
    if not RCLONE_PASS_FILE.exists():
        return None
    try:
        pw = RCLONE_PASS_FILE.read_text().strip()
        return pw or None
    except OSError:
        return None


def _get_decrypted_token() -> tuple[str | None, dict | None]:
    """Return (raw_token_str, parsed_token_dict) by invoking rclone.

    Returns (None, None) on any failure (no config, no password, no remote, etc.).
    """
    password = _read_rclone_pass()
    env = os.environ.copy()
    if password:
        env["RCLONE_CONFIG_PASS"] = password

    try:
        result = subprocess.run(
            ["rclone", "config", "show", RCLONE_REMOTE, "--config", str(RCLONE_CONFIG)],
            capture_output=True, text=True, timeout=15, env=env,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.error("rclone invocation failed: %s", exc)
        return None, None

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.error("rclone config show failed: %s", stderr[:300])
        return None, None

    raw = result.stdout.strip()
    if not raw:
        logger.warning("rclone config show returned empty output")
        return None, None

    parsed = _parse_rclone_config_section(raw)
    if parsed is None:
        logger.warning("Could not parse remote [%s] from rclone config", RCLONE_REMOTE)
        return None, None

    token_raw = parsed.get("token", "")
    if not token_raw:
        logger.warning("No token field in rclone config for [%s]", RCLONE_REMOTE)
        return None, None

    try:
        token_dict = json.loads(token_raw)
    except json.JSONDecodeError:
        logger.warning("Token field is not valid JSON")
        return token_raw, None

    return token_raw, token_dict


def _parse_rclone_config_section(raw: str) -> dict | None:
    """Parse a single rclone config section from 'rclone config show' output."""
    lines = raw.splitlines()
    section_name = f"[{RCLONE_REMOTE}]"
    in_section = False
    result: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == section_name:
            in_section = True
            continue
        if in_section and stripped.startswith("["):
            break
        if in_section and "=" in stripped:
            key, _, val = stripped.partition("=")
            key = key.strip()
            val = val.strip()
            result[key] = val
    return result if result else None


def _check_token_health(token_dict: dict) -> dict:
    """Analyse token dict and return a health report."""
    report = {
        "has_access_token": bool(token_dict.get("access_token")),
        "has_refresh_token": bool(token_dict.get("refresh_token")),
        "expiry": token_dict.get("expiry"),
        "expiry_secs_left": None,
        "expired": False,
        "warn_soon": False,
    }

    expiry_str = token_dict.get("expiry", "")
    if expiry_str:
        try:
            exp = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            secs = (exp - now).total_seconds()
            report["expiry_secs_left"] = int(secs)
            report["expired"] = secs < 0
            report["warn_soon"] = 0 < secs < (EXPIRY_WARN_HOURS * 3600)
        except (ValueError, TypeError):
            pass

    return report


def _check_connectivity() -> bool:
    """Run a live rclone connectivity check against the GDrive remote directory.

    Retries once on network timeout to avoid false positives from transient glitches.
    Uses ``--ask-password=false`` so rclone never prompts interactively.
    """
    password = _read_rclone_pass()
    env = os.environ.copy()
    if password:
        env["RCLONE_CONFIG_PASS"] = password

    cmd = [
        "rclone", "lsd", RCLONE_REMOTE_DIR,
        "--config", str(RCLONE_CONFIG),
        "--ask-password=false",
    ]
    for attempt in range(2):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45, env=env)
            if result.returncode == 0:
                return True
            logger.warning(
                "rclone connectivity check returned non-zero (attempt %d): %s",
                attempt + 1, (result.stderr or "").strip()[:200],
            )
        except subprocess.TimeoutExpired:
            logger.warning("rclone connectivity check timed out after 45s (attempt %d)", attempt + 1)
        except FileNotFoundError as exc:
            logger.error("rclone not found: %s", exc)
            return False
    logger.error("rclone connectivity check failed after 2 attempts")
    return False


def _load_self_state() -> dict:
    if MONITOR_STATE.exists():
        try:
            return json.loads(MONITOR_STATE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_self_state(state: dict):
    MONITOR_STATE.parent.mkdir(parents=True, exist_ok=True)
    MONITOR_STATE.write_text(json.dumps(state, indent=2))


def _find_existing_alert() -> dict | None:
    try:
        sess = _session()
        base_url = _base()
        company_id = _company()
    except (KeyError, OSError) as exc:
        logger.error("Failed to init Paperclip session: %s", exc)
        return None

    try:
        resp = sess.get(
            f"{base_url}/api/companies/{company_id}/issues",
            params={"status": "todo,in_progress", "q": ALERT_SEARCH_QUERY, "limit": 10},
            timeout=30,
        )
        resp.raise_for_status()
        issues = resp.json()
    except Exception as exc:
        logger.error("Failed to search for existing alerts: %s", exc)
        return None

    for issue in issues:
        if ALERT_SEARCH_QUERY in (issue.get("title") or ""):
            return issue
    return None


def _create_alert(
    failure_reason: str,
    detail: str,
    token_health: dict | None,
    dry_run: bool,
) -> bool:
    try:
        sess = _session()
        base_url = _base()
        company_id = _company()
    except (KeyError, OSError) as exc:
        logger.error("Failed to init Paperclip session: %s", exc)
        return False

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    th = token_health or {}
    token_lines = [
        f"- **Access token present:** {th.get('has_access_token', 'N/A')}",
        f"- **Refresh token present:** {th.get('has_refresh_token', 'N/A')}",
    ]
    expiry = th.get("expiry")
    if expiry:
        token_lines.append(f"- **Token expiry:** {expiry}")
    secs = th.get("expiry_secs_left")
    if secs is not None:
        if secs < 0:
            token_lines.append(f"- **Expired:** {-secs // 60}m ago")
        else:
            token_lines.append(f"- **Expires in:** {secs // 60}m")

    description = (
        f"**rclone OAuth health alert — {failure_reason}**\n\n"
        f"- **Check time:** {now_str}\n"
        f"- **Remote:** `{RCLONE_REMOTE}`\n"
        f"- **Config file:** `{RCLONE_CONFIG}`\n"
        f"- **Detail:** {detail}\n\n"
        f"**Token health:**\n"
        + "\n".join(token_lines)
        + f"\n\n**Fix procedure:**\n"
        f"1. On a machine WITH a browser, run:\n"
        f"   `SCOPE_BLOB=$(echo -n '{{\"scope\":\"drive\"}}' | base64 -w0 | sed 's/=//g')`\n"
        f"   `rclone authorize \"drive\" \"$SCOPE_BLOB\" --auth-no-open-browser`\n"
        f"2. Copy the JSON token block output\n"
        f"3. On this server, run:\n"
        f"   `deploy/backup/rclone-headless-auth.sh --apply-token`\n"
        f"4. Paste the token block, press Ctrl+D\n\n"
        f"**Or see full instructions:** `deploy/backup/rclone-headless-auth.sh --help`\n"
    )

    title = f"{ALERT_SEARCH_QUERY} — {failure_reason}"
    payload = {
        "title": title,
        "description": description,
        "assigneeAgentId": CTO_AGENT_ID,
        "priority": "critical",
        "status": "todo",
    }

    if dry_run:
        logger.info("DRY RUN: would create alert issue '%s'", title)
        print(json.dumps(payload, indent=2))
        return True

    try:
        resp = sess.post(
            f"{base_url}/api/companies/{company_id}/issues",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        created = resp.json()
        logger.info(
            "Created alert issue %s: %s",
            created.get("identifier", created.get("id", "?")),
            title,
        )
        return True
    except Exception as exc:
        logger.error("Failed to create alert issue: %s", exc)
        return False


def run(dry_run: bool = False) -> dict:
    _rotate_log_if_needed()

    prev = _load_self_state()
    prev_runs = prev.get("total_runs", 0)
    prev_last = prev.get("last_run_utc", "never")

    alert_fired = False
    alert_skipped = False
    alert_reason = ""
    status = "healthy"

    rclone_ver = ""
    try:
        rv = subprocess.run(["rclone", "version"], capture_output=True, text=True, timeout=5)
        rclone_ver = (rv.stdout or "").splitlines()[0] if rv.returncode == 0 else ""
    except Exception:
        pass

    config_exists = RCLONE_CONFIG.exists()
    pass_exists = RCLONE_PASS_FILE.exists()
    if not config_exists:
        logger.warning("rclone config file missing: %s", RCLONE_CONFIG)
    if not pass_exists:
        logger.warning("rclone password file missing: %s", RCLONE_PASS_FILE)

    token_raw, token_dict = _get_decrypted_token()
    token_health = _check_token_health(token_dict) if token_dict else None

    connectivity = False
    connectivity_checked = False
    failure_reason = ""
    detail = ""

    if not config_exists:
        status = "alert"
        alert_reason = "no_config_file"
        failure_reason = "rclone config file missing"
        detail = f"No rclone config at {RCLONE_CONFIG}"
    elif token_raw is None and token_dict is None:
        status = "alert"
        alert_reason = "token_unreadable"
        failure_reason = "cannot read OAuth token"
        detail = "rclone config may be missing, encrypted without password, or has no gdrive remote"
    elif token_dict is None:
        status = "alert"
        alert_reason = "token_invalid_json"
        failure_reason = "token is not valid JSON"
        detail = "The token field in rclone config is unparseable"
    else:
        th = token_health
        if not th["has_access_token"]:
            status = "alert"
            alert_reason = "no_access_token"
            failure_reason = "access_token is empty or missing"
            detail = "OAuth access_token is empty — token was cleared or never set"
        elif not th["has_refresh_token"]:
            if th["expired"]:
                status = "alert"
                alert_reason = "expired_no_refresh"
                failure_reason = "token expired and no refresh_token"
                detail = "Token is expired with no refresh_token to renew it"
            elif th["warn_soon"]:
                status = "warn"
                alert_reason = "expiring_soon_no_refresh"
                failure_reason = "token expiring soon and no refresh_token"
                detail = f"Token expires in ~{th['expiry_secs_left'] // 60}m with no refresh_token"
            else:
                status = "warn"
                alert_reason = "no_refresh_token"
                failure_reason = "no refresh_token"
                detail = "Token has access_token but no refresh_token — cannot auto-renew"
        elif th["expired"]:
            status = "alert"
            alert_reason = "token_expired"
            failure_reason = "token expired"
            detail = f"Token expired {-th['expiry_secs_left'] // 60}m ago"
            if th["has_refresh_token"]:
                connectivity_checked = True
                connectivity = _check_connectivity()
                if not connectivity:
                    detail += " (and refresh_token failed to renew)"
                else:
                    logger.info("Token appears expired but connectivity check passed — refresh_token working")
                    status = "healthy"
                    alert_reason = ""
                    failure_reason = ""
        elif th["warn_soon"]:
            status = "warn"
            alert_reason = "token_expiring_soon"
            failure_reason = "token expiring soon"
            detail = f"Token expires in ~{th['expiry_secs_left'] // 60}m"
            if th["has_refresh_token"]:
                logger.info("Token expiring soon but refresh_token present — will auto-renew")
                status = "healthy"
                alert_reason = ""
                failure_reason = ""
        else:
            pass

    if status in ("healthy", "warn") and not connectivity_checked:
        connectivity_checked = True
        connectivity = _check_connectivity()
        if not connectivity:
            if status == "healthy":
                status = "alert"
                alert_reason = "connectivity_failed"
                failure_reason = "connectivity check failed despite healthy-looking token"
                detail = "Token appears valid but rclone cannot reach GDrive"
            else:
                status = "alert"
                alert_reason = f"{alert_reason}_and_connectivity_failed"
                failure_reason = f"{failure_reason} (connectivity also failed)"
                detail = f"{detail} and rclone cannot reach GDrive"

    if alert_reason and status == "alert":
        # State-based cooldown: if we fired an alert within ALERT_COOLDOWN_HOURS, skip even
        # if the previous alert was already resolved — prevents duplicate storms after transient
        # network timeouts where each resolved alert immediately triggers a new one.
        last_alert_str = prev.get("last_alert_utc")
        in_cooldown = False
        if last_alert_str:
            try:
                last_alert_dt = datetime.fromisoformat(last_alert_str)
                secs_since = (datetime.now(timezone.utc) - last_alert_dt).total_seconds()
                if secs_since < ALERT_COOLDOWN_HOURS * 3600:
                    logger.info(
                        "Alert cooldown active — last alert was %.0fm ago (cooldown: %dh), skipping",
                        secs_since / 60, ALERT_COOLDOWN_HOURS,
                    )
                    in_cooldown = True
                    alert_skipped = True
            except (ValueError, TypeError):
                pass

        if not in_cooldown:
            existing = _find_existing_alert()
            if existing:
                logger.info(
                    "Existing alert %s already open — skipping duplicate creation",
                    existing.get("identifier", existing["id"]),
                )
                alert_skipped = True
            else:
                ok = _create_alert(failure_reason, detail, token_health, dry_run)
                if ok:
                    alert_fired = True
    elif alert_reason and status == "warn":
        logger.warning("Token health warning (non-critical): %s — %s", alert_reason, detail)

    now_utc = datetime.now(timezone.utc).isoformat()
    _save_self_state({
        "total_runs": prev_runs + 1,
        "last_run_utc": now_utc,
        "last_alert_utc": now_utc if alert_fired else prev.get("last_alert_utc"),
    })

    summary = {
        "status": status,
        "rclone_version": rclone_ver,
        "config_file_exists": config_exists,
        "password_file_exists": pass_exists,
        "remote": RCLONE_REMOTE,
        "token_health": token_health,
        "connectivity_ok": connectivity if connectivity_checked else None,
        "alert_fired": alert_fired,
        "alert_skipped": alert_skipped,
        "alert_reason": alert_reason or "none",
        "failure_reason": failure_reason or "none",
        "self_last_run_utc": now_utc,
        "self_prev_run_utc": prev_last,
        "self_total_runs": prev_runs + 1,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="rclone OAuth token health monitor for Paperclip GDrive backup pipeline",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without creating alerts",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Output JSON summary to stdout (for CI step summaries)",
    )
    args = parser.parse_args()

    summary = run(dry_run=args.dry_run)

    if args.json_summary:
        print(json.dumps(summary, indent=2, default=str))

    detection_ok = summary["status"] not in ("auth_error",)
    sys.exit(0 if detection_ok else 1)


if __name__ == "__main__":
    main()
