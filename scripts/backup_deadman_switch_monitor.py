#!/usr/bin/env python3
"""Backup dead-man's-switch monitor — watches the deadman-switch-monitor workflow.

Runs on the self-hosted machine (systemd timer) as a backup to the
GH Actions-based ``deadman-switch-monitor.yml``.  Uses the GitHub REST API
(GH_TOKEN) to check the ``deadman-switch-monitor`` workflow.  The gh CLI
dependency has been removed — ``requests`` is used directly.

This closes the monitoring loop: the backup-deadman-switch is watched
by the deadman-switch-monitor (ubuntu-latest); the deadman-switch-monitor
is watched by this backup monitor (self-hosted).

Usage:
    python scripts/backup_deadman_switch_monitor.py
    python scripts/backup_deadman_switch_monitor.py --dry-run
    python scripts/backup_deadman_switch_monitor.py --threshold 45
    python scripts/backup_deadman_switch_monitor.py --json-summary
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

# Load .env for GH_TOKEN and other non-conflicting vars.
# PAPERCLIP_* vars are injected by systemd Environment= directives and must
# NOT be overridden — override=False ensures they keep priority.
if (REPO_ROOT / ".env").exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env", override=False)
    except ImportError:
        pass

from touch_index.paperclip_client import _session, _base, _company

MONITOR_LOG = Path.home() / ".paperclip" / "backup_deadman_switch_monitor.log"
MONITOR_STATE = Path.home() / ".paperclip" / "backup_deadman_switch_monitor_state.json"
MAX_LOG_BYTES = 1 * 1024 * 1024

TARGET_WORKFLOW = "deadman-switch-monitor.yml"
GH_REPO = "Stack-Alerts/BTC-Trade-Engine-PaperClip"
ALERT_SEARCH_QUERY = "Backup dead-man's-switch monitor alert"
GH_BLIND_SEARCH_QUERY = "Backup dead-man's-switch monitor: cannot reach GitHub API"
CTO_AGENT_ID = "41b5ede6-e209-40ba-b923-dc969c722e6d"

MONITOR_INTERVAL_MINUTES = 30
# Default alert threshold (minutes since last successful run before firing).
# Override at runtime via BACKUP_DEADMAN_MONITOR_THRESHOLD_MINUTES env var.
# Tuned for observed GH Actions cron slot-dropping cadence on the *primary*
# monitor (median gap ~58 min on `deadman-switch-monitor.yml`); 180 min
# gives ~6× primary cadence so this monitor stays a real backup, not a
# chronic false-positive generator. See .github/workflows/README.md
# "Cadence vs threshold policy".
MONITOR_THRESHOLD_MINUTES = int(
    os.environ.get("BACKUP_DEADMAN_MONITOR_THRESHOLD_MINUTES", "180")
)
# If reported age exceeds this, require independent corroboration before alerting.
# A 24h+ stale signal is far more likely to be a stale local artifact than a true failure.
AGE_SANITY_CAP_MINUTES = 24 * 60

_GH_API_BASE = "https://api.github.com"
# (delay_before_attempt_s, request_timeout_s) — three attempts total
_GH_RETRY_SCHEDULE = [(0, 30), (5, 30), (15, 60)]

MONITOR_LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(MONITOR_LOG),
        logging.StreamHandler() if os.isatty(0) else logging.NullHandler(),
    ],
)
logger = logging.getLogger("backup_deadman_switch_monitor")


def _rotate_log_if_needed():
    if MONITOR_LOG.exists() and MONITOR_LOG.stat().st_size > MAX_LOG_BYTES:
        bak = MONITOR_LOG.with_suffix(".log.1")
        bak.write_text(MONITOR_LOG.read_text())
        MONITOR_LOG.write_text("")
        logger.info("Rotated backup monitor log (size exceeded %d bytes)", MAX_LOG_BYTES)


def _gh_run_list(workflow: str, limit: int = 10) -> list[dict] | None:
    """Query GitHub Actions run list via REST API with retry on transient failures.

    Returns a list of run dicts (keys: status, conclusion, createdAt, databaseId,
    headSha) on success, or None if the GitHub API is unreachable after all retries.

    Uses GH_TOKEN env var (loaded from .env via load_dotenv above).  No gh CLI needed.
    """
    import requests as req_lib

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error(
            "No GH_TOKEN/GITHUB_TOKEN available — cannot query GitHub API. "
            "Ensure GH_TOKEN is set in .env (loaded via load_dotenv) or exported."
        )
        return None

    url = f"{_GH_API_BASE}/repos/{GH_REPO}/actions/workflows/{workflow}/runs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {"per_page": limit}

    for attempt, (sleep_s, timeout_s) in enumerate(_GH_RETRY_SCHEDULE):
        if sleep_s:
            logger.info(
                "GH API retry %d/%d — waiting %ds before attempt",
                attempt + 1, len(_GH_RETRY_SCHEDULE), sleep_s,
            )
            time.sleep(sleep_s)
        try:
            resp = req_lib.get(url, headers=headers, params=params, timeout=timeout_s)
        except req_lib.exceptions.ConnectionError as exc:
            logger.warning("GH API connection error (attempt %d/%d): %s",
                           attempt + 1, len(_GH_RETRY_SCHEDULE), exc)
            continue
        except req_lib.exceptions.Timeout:
            logger.warning("GH API timeout (attempt %d/%d, timeout=%ds)",
                           attempt + 1, len(_GH_RETRY_SCHEDULE), timeout_s)
            continue
        except Exception as exc:
            logger.warning("GH API request error (attempt %d/%d): %s",
                           attempt + 1, len(_GH_RETRY_SCHEDULE), exc)
            continue

        if resp.status_code == 401:
            logger.error("GH API: unauthorized (bad GH_TOKEN) — not retrying")
            return None
        if resp.status_code == 404:
            logger.error("GH API: workflow not found: %s — not retrying", workflow)
            return None
        if resp.status_code >= 500:
            logger.warning("GH API server error %d (attempt %d/%d)",
                           resp.status_code, attempt + 1, len(_GH_RETRY_SCHEDULE))
            continue
        if resp.status_code != 200:
            logger.warning("GH API unexpected status %d (attempt %d/%d)",
                           resp.status_code, attempt + 1, len(_GH_RETRY_SCHEDULE))
            continue

        try:
            data = resp.json()
        except Exception as exc:
            logger.error("GH API response parse error: %s", exc)
            return None

        runs_raw = data.get("workflow_runs", [])
        # Normalise field names to match the old gh CLI JSON schema
        return [
            {
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "createdAt": r.get("created_at", ""),
                "databaseId": r.get("id"),
                "headSha": r.get("head_sha"),
            }
            for r in runs_raw
        ]

    logger.error("GH API unreachable after %d attempts", len(_GH_RETRY_SCHEDULE))
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


def _find_existing_alert(search_query: str) -> dict | None:
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
            params={"status": "todo,in_progress", "q": search_query, "limit": 10},
            timeout=30,
        )
        resp.raise_for_status()
        issues = resp.json()
    except Exception as exc:
        logger.error("Failed to search for existing alerts: %s", exc)
        return None
    for issue in issues:
        if search_query in (issue.get("title") or ""):
            return issue
    return None


def _create_alert(
    age_minutes: float | None,
    threshold_minutes: int,
    dry_run: bool,
    extra_detail: str = "",
    priority: str = "critical",
) -> bool:
    try:
        sess = _session()
        base_url = _base()
        company_id = _company()
    except (KeyError, OSError) as exc:
        logger.error("Failed to init Paperclip session: %s", exc)
        return False

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if age_minutes is None:
        subject = "no successful runs found for deadman-switch-monitor"
        description = (
            f"**Backup dead-man's-switch monitor alert — "
            f"{TARGET_WORKFLOW} is dead**\n\n"
            f"- **Check time:** {now_str}\n"
            f"- **Last successful run:** NONE found\n"
            f"- **Target workflow:** `{TARGET_WORKFLOW}`\n"
            f"- **Expected interval:** {MONITOR_INTERVAL_MINUTES} min\n"
            f"- **Monitor threshold:** {threshold_minutes} min\n"
            f"- **Action required:** Check GitHub Actions workflow health.\n"
            f"  The deadman-switch-monitor has no successful runs.\n"
            f"  The workflow may be disabled or misconfigured.\n"
            f"{extra_detail}"
        )
    else:
        subject = f"{age_minutes:.0f} min since deadman-switch-monitor last success"
        description = (
            f"**Backup dead-man's-switch monitor alert — "
            f"{TARGET_WORKFLOW} may be stalled**\n\n"
            f"- **Check time:** {now_str}\n"
            f"- **Last successful run:** {age_minutes:.0f} min ago\n"
            f"- **Expected interval:** {MONITOR_INTERVAL_MINUTES} min\n"
            f"- **Monitor threshold:** {threshold_minutes} min\n"
            f"- **Action required:** Check GitHub Actions workflow health.\n"
            f"  The deadman-switch-monitor has no recent successful runs.\n"
            f"  The workflow may be stalled or the ubuntu-latest runner may be down.\n"
            f"{extra_detail}"
        )

    title = f"{ALERT_SEARCH_QUERY} — {subject}"
    payload = {
        "title": title,
        "description": description,
        "assigneeAgentId": CTO_AGENT_ID,
        "priority": priority,
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


def _create_gh_blind_alert(dry_run: bool) -> bool:
    """Create a high-priority (not critical) alert when GH API is unreachable.

    This is distinct from a real workflow-stall alert so operators can triage
    "we lost GH connectivity" separately from "the workflow actually stalled".
    """
    try:
        sess = _session()
        base_url = _base()
        company_id = _company()
    except (KeyError, OSError) as exc:
        logger.error("Failed to init Paperclip session: %s", exc)
        return False

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = GH_BLIND_SEARCH_QUERY
    description = (
        f"**Backup dead-man's-switch monitor — GitHub API unreachable**\n\n"
        f"- **Check time:** {now_str}\n"
        f"- **Target workflow:** `{TARGET_WORKFLOW}`\n"
        f"- **Status:** `gh_blind` — cannot determine workflow health\n"
        f"- **Action required:** Verify GH_TOKEN is valid and GitHub API is reachable "
        f"from this host. Until connectivity is restored, the backup monitor cannot "
        f"verify that `{TARGET_WORKFLOW}` is healthy.\n"
        f"- This is a `high`-priority notice (not `critical`) — "
        f"it means the backup monitor is blind, NOT that the workflow has actually stalled."
    )
    payload = {
        "title": title,
        "description": description,
        "assigneeAgentId": CTO_AGENT_ID,
        "priority": "high",
        "status": "todo",
    }

    if dry_run:
        logger.info("DRY RUN: would create gh_blind alert")
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
            "Created gh_blind alert %s",
            created.get("identifier", created.get("id", "?")),
        )
        return True
    except Exception as exc:
        logger.error("Failed to create gh_blind alert: %s", exc)
        return False


def _comment_on_existing_alert(
    issue: dict,
    age_minutes: float | None,
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

    if age_minutes is None:
        age_line = "- **Last success:** NONE found (no successful runs)"
    else:
        age_line = f"- **Last success:** {age_minutes:.0f} min ago"

    body = (
        f"**Backup dead-man's-switch monitor re-check — {now_str}**\n\n"
        f"- **Check time:** {now_str}\n"
        f"{age_line}\n"
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

    now_utc = datetime.now(timezone.utc)
    prev = _load_self_state()
    prev_runs = prev.get("total_runs", 0)
    prev_last = prev.get("last_run_utc", "never")

    # Self-resume guard: if this machine was offline > 2× monitor interval,
    # cached state is unreliable — skip alerting on this first run.
    self_gap_minutes: float | None = None
    self_resumed = False
    if prev_last != "never":
        try:
            prev_ts = datetime.fromisoformat(prev_last.replace("Z", "+00:00"))
            self_gap_minutes = (now_utc - prev_ts.astimezone(timezone.utc)).total_seconds() / 60
            if self_gap_minutes > 2 * MONITOR_INTERVAL_MINUTES:
                self_resumed = True
                logger.warning(
                    "Self-resume detected: last self-run was %.0f min ago "
                    "(expected ≤%d min). Skipping alert on this run — "
                    "will perform a fresh GH API check next cycle.",
                    self_gap_minutes,
                    2 * MONITOR_INTERVAL_MINUTES,
                )
        except (ValueError, TypeError):
            pass

    runs = _gh_run_list(TARGET_WORKFLOW, limit=10)

    alert_fired = False
    alert_skipped = False
    alert_reason = ""
    status = "healthy"
    gh_api_available = runs is not None

    if self_resumed:
        # Don't fire on first run after machine wake-up — state is stale.
        status = "self_resumed"
        now_utc_str = now_utc.isoformat()
        _save_self_state({
            "total_runs": prev_runs + 1,
            "last_run_utc": now_utc_str,
            "last_alert_utc": prev.get("last_alert_utc"),
        })
        return {
            "status": status,
            "target_workflow": TARGET_WORKFLOW,
            "monitor_interval_minutes": MONITOR_INTERVAL_MINUTES,
            "monitor_threshold_minutes": threshold_minutes,
            "self_gap_minutes": self_gap_minutes,
            "gh_api_available": gh_api_available,
            "alert_fired": False,
            "alert_skipped": False,
            "alert_reason": "self_resumed_skipped",
            "self_last_run_utc": now_utc_str,
            "self_prev_run_utc": prev_last,
            "self_total_runs": prev_runs + 1,
        }

    if runs is None:
        # GH API truly unreachable — emit a distinct high-priority blind notice.
        # Do NOT report healthy and do NOT use local state as proxy for workflow age.
        logger.error(
            "GitHub API unreachable after all retries — emitting gh_blind alert"
        )
        status = "gh_blind"
        existing_blind = _find_existing_alert(GH_BLIND_SEARCH_QUERY)
        if existing_blind:
            logger.info(
                "gh_blind alert %s already open — skipping duplicate",
                existing_blind.get("identifier", existing_blind.get("id")),
            )
            alert_skipped = True
        else:
            ok = _create_gh_blind_alert(dry_run)
            if ok:
                alert_fired = True
    else:
        age_minutes = _get_latest_success_age_minutes(runs)

        if age_minutes is None:
            if not _has_any_recent_runs(runs, threshold_minutes):
                logger.warning(
                    "Deadman-switch-monitor has no runs within %d min — alert will fire",
                    threshold_minutes,
                )
                alert_reason = "no_runs_found"
                status = "alert"
            else:
                logger.warning(
                    "Deadman-switch-monitor has runs but no successes (failing runs exist)"
                )
                alert_reason = "all_runs_failing"
                status = "alert"
        elif age_minutes > AGE_SANITY_CAP_MINUTES:
            # Age exceeds 24h — extremely likely to be stale local artifact.
            # Do a fresh GH query to corroborate before alerting.
            logger.warning(
                "Reported age %.0f min exceeds sanity cap %d min — "
                "performing corroboration query before alerting",
                age_minutes, AGE_SANITY_CAP_MINUTES,
            )
            corroboration = _gh_run_list(TARGET_WORKFLOW, limit=5)
            if corroboration is None:
                logger.warning(
                    "Corroboration query failed — treating as gh_blind, not %.0f min stall",
                    age_minutes,
                )
                status = "gh_blind"
                existing_blind = _find_existing_alert(GH_BLIND_SEARCH_QUERY)
                if not existing_blind:
                    _create_gh_blind_alert(dry_run)
                    alert_fired = True
                else:
                    alert_skipped = True
            else:
                corr_age = _get_latest_success_age_minutes(corroboration)
                if corr_age is not None and corr_age <= threshold_minutes:
                    logger.info(
                        "Corroboration shows %.0f min ago — actually healthy (initial was stale)",
                        corr_age,
                    )
                    age_minutes = corr_age
                else:
                    logger.warning(
                        "Corroboration confirms stall: %.0f min — alert will fire",
                        corr_age if corr_age is not None else -1,
                    )
                    alert_reason = "overdue_corroborated"
                    status = "alert"
        elif age_minutes <= threshold_minutes:
            logger.info(
                "Deadman-switch-monitor healthy: last success %.0f min ago "
                "(threshold %d min)",
                age_minutes,
                threshold_minutes,
            )
        else:
            logger.warning(
                "Deadman-switch-monitor stalled: last success %.0f min ago "
                "(threshold %d min) — alert will fire",
                age_minutes,
                threshold_minutes,
            )
            alert_reason = "overdue"
            status = "alert"

        if alert_reason:
            existing = _find_existing_alert(ALERT_SEARCH_QUERY)
            if existing:
                logger.info(
                    "Existing alert %s already open — commenting with re-check status",
                    existing.get("identifier", existing.get("id")),
                )
                _comment_on_existing_alert(existing, age_minutes, threshold_minutes, dry_run)
                alert_skipped = True
            else:
                ok = _create_alert(age_minutes, threshold_minutes, dry_run)
                if ok:
                    alert_fired = True

    now_utc_str = now_utc.isoformat()
    _save_self_state({
        "total_runs": prev_runs + 1,
        "last_run_utc": now_utc_str,
        "last_alert_utc": now_utc_str if alert_fired else prev.get("last_alert_utc"),
    })

    summary = {
        "status": status,
        "target_workflow": TARGET_WORKFLOW,
        "monitor_interval_minutes": MONITOR_INTERVAL_MINUTES,
        "monitor_threshold_minutes": threshold_minutes,
        "last_success_age_minutes": (
            _get_latest_success_age_minutes(runs) if runs is not None else None
        ),
        "total_runs_checked": len(runs) if runs is not None else 0,
        "gh_api_available": gh_api_available,
        "alert_fired": alert_fired,
        "alert_skipped": alert_skipped,
        "commented": alert_skipped,
        "alert_reason": alert_reason or "none",
        "self_last_run_utc": now_utc_str,
        "self_prev_run_utc": prev_last,
        "self_gap_minutes": self_gap_minutes,
        "self_resumed": self_resumed,
        "self_total_runs": prev_runs + 1,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Backup dead-man's-switch monitor — "
                    "watches the deadman-switch-monitor workflow",
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

    sys.exit(0 if summary["status"] not in ("gh_blind",) else 1)


if __name__ == "__main__":
    main()
