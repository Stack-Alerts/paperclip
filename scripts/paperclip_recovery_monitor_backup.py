#!/usr/bin/env python3
"""Recovery Monitor Backup — watches the paperclip-recovery-monitor workflow and local state.

Runs on the self-hosted machine (systemd timer or GH Actions self-hosted runner)
as a backup health check for the PaperClip Recovery Monitor. Checks the
``paperclip-recovery-monitor.yml`` workflow via ``gh run list`` and the local
recovery monitor state file as a secondary signal.

This closes the monitoring loop: the recovery-monitor (GH Actions) is watched
by this backup monitor (self-hosted).

Usage:
    python scripts/paperclip_recovery_monitor_backup.py
    python scripts/paperclip_recovery_monitor_backup.py --dry-run
    python scripts/paperclip_recovery_monitor_backup.py --threshold 90
    python scripts/paperclip_recovery_monitor_backup.py --json-summary
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from touch_index.paperclip_client import _session, _base, _company

MONITOR_LOG = Path.home() / ".paperclip" / "recovery_monitor_backup.log"
MONITOR_STATE = Path.home() / ".paperclip" / "recovery_monitor_backup_state.json"
LOCAL_RECOVERY_STATE = Path.home() / ".paperclip" / "recovery_monitor_state.json"
MAX_LOG_BYTES = 1 * 1024 * 1024

TARGET_WORKFLOW = "paperclip-recovery-monitor.yml"
ALERT_SEARCH_QUERY = "Recovery Monitor health alert"
CTO_AGENT_ID = "41b5ede6-e209-40ba-b923-dc969c722e6d"

MONITOR_INTERVAL_MINUTES = 30
MONITOR_THRESHOLD_MINUTES = 90

MONITOR_LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(MONITOR_LOG),
        logging.StreamHandler() if os.isatty(0) else logging.NullHandler(),
    ],
)
logger = logging.getLogger("recovery_monitor_backup")


def _rotate_log_if_needed():
    if MONITOR_LOG.exists() and MONITOR_LOG.stat().st_size > MAX_LOG_BYTES:
        bak = MONITOR_LOG.with_suffix(".log.1")
        bak.write_text(MONITOR_LOG.read_text())
        MONITOR_LOG.write_text("")
        logger.info("Rotated backup monitor log (size exceeded %d bytes)", MAX_LOG_BYTES)


_GH_AUTH_ERROR_PATTERNS = [
    "To get started with GitHub CLI, please run:  gh auth login",
    "no oauth token found",
    "populate the GH_TOKEN environment variable",
]


def _gh_run_list(workflow: str, limit: int = 10) -> list[dict] | None:
    gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    try:
        result = subprocess.run(
            [
                "gh", "run", "list",
                "--repo", "Stack-Alerts/BTC-Trade-Engine-PaperClip",
                "--workflow", workflow,
                "--limit", str(limit),
                "--json", "status,conclusion,createdAt,databaseId,headSha",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
        )
    except FileNotFoundError:
        logger.warning("gh CLI not found — falling back to GitHub API")
        return _gh_api_run_list(workflow, limit, gh_token)
    except subprocess.TimeoutExpired:
        logger.error("gh run list timed out — cannot query workflow runs")
        return None
    if result.returncode != 0:
        stderr_lower = result.stderr.lower() if result.stderr else ""
        for pattern in _GH_AUTH_ERROR_PATTERNS:
            if pattern.lower() in stderr_lower:
                logger.warning("gh CLI not authenticated — falling back to GitHub API")
                return _gh_api_run_list(workflow, limit, gh_token)
        logger.error("gh run list failed (rc=%d): %s", result.returncode, result.stderr.strip())
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error("gh run list returned non-JSON: %s", result.stdout[:200])
        return None


def _gh_api_run_list(workflow: str, limit: int = 10, token: str | None = None) -> list[dict] | None:
    if not token:
        logger.error("No GH_TOKEN or GITHUB_TOKEN available for API fallback")
        return None
    import requests as req
    try:
        resp = req.get(
            f"https://api.github.com/repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/actions/workflows/{workflow}/runs",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            params={"per_page": limit},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        runs = data.get("workflow_runs", [])
        return [
            {
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "createdAt": r.get("created_at"),
                "databaseId": r.get("id"),
                "headSha": r.get("head_sha"),
            }
            for r in runs
        ]
    except Exception as exc:
        logger.error("GitHub API fallback failed: %s", exc)
        return None


def _get_latest_success_age_minutes(runs: list[dict]) -> float | None:
    successes = [r for r in runs if r.get("conclusion") == "success"]
    if not successes:
        logger.warning("No successful runs found for %s", TARGET_WORKFLOW)
        return None
    latest = successes[0]
    raw = latest.get("createdAt")
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        logger.warning("Unparseable createdAt timestamp: %s", raw)
        return None
    age = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
    return age.total_seconds() / 60


def _has_any_recent_runs(runs: list[dict], minutes: int) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    for r in runs:
        raw = r.get("createdAt")
        if not raw:
            continue
        try:
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if ts.astimezone(timezone.utc) > cutoff:
            return True
    return False


def _read_local_recovery_state() -> dict | None:
    if not LOCAL_RECOVERY_STATE.exists():
        logger.warning("Local recovery monitor state file missing: %s", LOCAL_RECOVERY_STATE)
        return None
    try:
        return json.loads(LOCAL_RECOVERY_STATE.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read local recovery monitor state: %s", exc)
        return None


def _get_local_monitor_age_minutes(state: dict) -> float | None:
    raw = state.get("last_run_at")
    if raw:
        try:
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            logger.warning("Unparseable last_run_at in local recovery state: %s", raw)
        else:
            age = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
            return age.total_seconds() / 60
    # Fallback: use file mtime if last_run_at is missing
    if LOCAL_RECOVERY_STATE.exists():
        mtime = LOCAL_RECOVERY_STATE.stat().st_mtime
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(mtime, tz=timezone.utc)
        logger.info("Using file mtime for local recovery state age: %.0f min", age.total_seconds() / 60.0)
        return age.total_seconds() / 60.0
    logger.warning("Local recovery state file missing: %s", LOCAL_RECOVERY_STATE)
    return None


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
            params={
                "status": "todo,in_progress",
                "q": ALERT_SEARCH_QUERY,
                "limit": 10,
            },
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
    age_minutes: float | None,
    local_age_minutes: float | None,
    threshold_minutes: int,
    gh_available: bool,
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

    if age_minutes is None and local_age_minutes is None:
        subject = "both GH Actions and local monitor are unreachable"
    elif age_minutes is None:
        subject = "GH Actions workflow has no successful runs"
    elif local_age_minutes is None:
        subject = f"GH Actions: {age_minutes:.0f} min since last success (local state missing)"
    else:
        subject = f"GH Actions: {age_minutes:.0f} min / local: {local_age_minutes:.0f} min since last success"

    gh_age_str = f"{age_minutes:.0f} min" if age_minutes is not None else "N/A (no successes)"
    local_age_str = f"{local_age_minutes:.0f} min" if local_age_minutes is not None else "N/A (file missing)"

    description = (
        f"**Recovery Monitor health alert — "
        f"{TARGET_WORKFLOW} may be unhealthy**\n\n"
        f"- **Check time:** {now_str}\n"
        f"- **GH Actions last success:** {gh_age_str}\n"
        f"- **Local state last run:** {local_age_str}\n"
        f"- **Target workflow:** `{TARGET_WORKFLOW}`\n"
        f"- **Expected interval:** {MONITOR_INTERVAL_MINUTES} min\n"
        f"- **Alert threshold:** {threshold_minutes} min\n"
        f"- **GH CLI available:** {gh_available}\n"
        f"- **Action required:** Check the recovery monitor's health.\n"
        f"  The recovery monitor may be stalled or the GH Actions runner may be down.\n"
        f"  Verify both the workflow and the local systemd timer are running.\n"
    )

    title = f"{ALERT_SEARCH_QUERY} — {subject}"
    payload = {
        "title": title[:200],
        "description": description,
        "assigneeAgentId": CTO_AGENT_ID,
        "priority": "critical",
        "status": "todo",
    }

    if dry_run:
        logger.info("DRY RUN: would create alert issue '%s'", title)
        print(json.dumps(payload, indent=2))  # noqa: T201
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


def _comment_on_existing_alert(
    issue: dict,
    age_minutes: float | None,
    local_age_minutes: float | None,
    threshold_minutes: int,
    dry_run: bool,
) -> bool:
    try:
        sess = _session()
        base_url = _base()
    except (KeyError, OSError) as exc:
        logger.error("Failed to init Paperclip session for commenting: %s", exc)
        return False

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    issue_id = issue.get("identifier", issue.get("id", "?"))

    gh_age_str = f"{age_minutes:.0f} min" if age_minutes is not None else "N/A"
    local_age_str = f"{local_age_minutes:.0f} min" if local_age_minutes is not None else "N/A"

    body = (
        f"**Recovery Monitor health re-check — {now_str}**\n\n"
        f"- **Check time:** {now_str}\n"
        f"- **GH Actions last success:** {gh_age_str}\n"
        f"- **Local state last run:** {local_age_str}\n"
        f"- **Target workflow:** `{TARGET_WORKFLOW}`\n"
        f"- **Threshold:** {threshold_minutes} min\n"
        f"- **Status:** {TARGET_WORKFLOW} still overdue, existing alert remains open"
    )

    if dry_run:
        logger.info("DRY RUN: would comment on alert %s", issue_id)
        print(json.dumps({"issueId": issue_id, "body": body}, indent=2))  # noqa: T201
        return True

    try:
        resp = sess.post(
            f"{base_url}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Commented on existing alert %s", issue_id)
        return True
    except Exception as exc:
        logger.error("Failed to comment on alert %s: %s", issue_id, exc)
        return False


def run(
    threshold_minutes: int = MONITOR_THRESHOLD_MINUTES,
    dry_run: bool = False,
) -> dict:
    _rotate_log_if_needed()

    prev = _load_self_state()
    prev_runs = prev.get("total_runs", 0)
    prev_last = prev.get("last_run_utc", "never")

    runs = _gh_run_list(TARGET_WORKFLOW, limit=10)
    gh_available = runs is not None

    alert_fired = False
    alert_skipped = False
    alert_reason = ""
    status = "healthy"

    age_minutes = None
    if runs is not None:
        age_minutes = _get_latest_success_age_minutes(runs)

    local_age_minutes = None
    local_state = _read_local_recovery_state()
    if local_state:
        local_age_minutes = _get_local_monitor_age_minutes(local_state)

    if not gh_available and local_age_minutes is None:
        logger.error("Cannot determine recovery monitor health from any source")
        alert_reason = "cannot_determine_health"
        status = "alert"
    elif age_minutes is None and local_age_minutes is None:
        if not _has_any_recent_runs(runs, threshold_minutes) if runs else True:
            logger.warning(
                "Recovery monitor has no runs within %d min — alert will fire",
                threshold_minutes,
            )
            alert_reason = "no_runs_found"
            status = "alert"
    elif age_minutes is not None and age_minutes <= threshold_minutes:
        logger.info(
            "Recovery monitor healthy: GH Actions last success %.0f min ago "
            "(threshold %d min)",
            age_minutes,
            threshold_minutes,
        )
    elif local_age_minutes is not None and local_age_minutes <= threshold_minutes:
        logger.info(
            "Recovery monitor healthy via local state: last run %.0f min ago "
            "(threshold %d min)",
            local_age_minutes,
            threshold_minutes,
        )
    elif age_minutes is not None and local_age_minutes is not None:
        best = min(age_minutes, local_age_minutes)
        if best <= threshold_minutes:
            logger.info(
                "Recovery monitor healthy: best signal %.0f min ago "
                "(threshold %d min)",
                best,
                threshold_minutes,
            )
        else:
            logger.warning(
                "Recovery monitor stalled: best signal %.0f min ago "
                "(threshold %d min) — alert will fire",
                best,
                threshold_minutes,
            )
            alert_reason = "overdue"
            status = "alert"
    elif age_minutes is not None:
        logger.warning(
            "Recovery monitor stalled: GH Actions last success %.0f min ago "
            "(threshold %d min) — alert will fire",
            age_minutes,
            threshold_minutes,
        )
        alert_reason = "overdue"
        status = "alert"
    elif local_age_minutes is not None:
        logger.warning(
            "Recovery monitor stalled: local last run %.0f min ago "
            "(threshold %d min) — alert will fire",
            local_age_minutes,
            threshold_minutes,
        )
        alert_reason = "overdue"
        status = "alert"

    if alert_reason:
        existing = _find_existing_alert()
        if existing:
            logger.info(
                "Existing alert %s already open — commenting with re-check status",
                existing.get("identifier", existing.get("id")),
            )
            _comment_on_existing_alert(
                existing, age_minutes, local_age_minutes, threshold_minutes, dry_run,
            )
            alert_skipped = True
        else:
            ok = _create_alert(
                age_minutes, local_age_minutes, threshold_minutes, gh_available, dry_run,
            )
            if ok:
                alert_fired = True

    now_utc = datetime.now(timezone.utc).isoformat()
    _save_self_state({
        "total_runs": prev_runs + 1,
        "last_run_utc": now_utc,
        "last_alert_utc": now_utc if alert_fired else prev.get("last_alert_utc"),
    })

    summary = {
        "status": status,
        "target_workflow": TARGET_WORKFLOW,
        "monitor_interval_minutes": MONITOR_INTERVAL_MINUTES,
        "monitor_threshold_minutes": threshold_minutes,
        "gh_actions_last_success_age_minutes": age_minutes,
        "local_monitor_last_run_age_minutes": local_age_minutes,
        "total_runs_checked": len(runs) if runs is not None else 0,
        "gh_cli_available": gh_available,
        "local_state_available": local_state is not None,
        "alert_fired": alert_fired,
        "alert_skipped": alert_skipped,
        "commented": alert_skipped,
        "alert_reason": alert_reason or "none",
        "self_last_run_utc": now_utc,
        "self_prev_run_utc": prev_last,
        "self_total_runs": prev_runs + 1,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Recovery Monitor Backup — watches the paperclip-recovery-monitor workflow",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=MONITOR_THRESHOLD_MINUTES,
        help=f"Alert threshold in minutes (default: {MONITOR_THRESHOLD_MINUTES})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without creating alerts",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Output JSON summary to stdout",
    )
    args = parser.parse_args()

    summary = run(threshold_minutes=args.threshold, dry_run=args.dry_run)

    if args.json_summary:
        print(json.dumps(summary, indent=2))  # noqa: T201

    detection_ok = summary["status"] != "auth_error"
    sys.exit(0 if detection_ok else 1)


if __name__ == "__main__":
    main()
