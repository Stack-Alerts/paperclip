#!/usr/bin/env python3
"""Dead-man's-switch monitor for the PaperClip backup pipeline.

Reads ``last-success.json`` from the PaperClip instance backup-state directory
and fires a Paperclip alert issue if the last successful backup exceeds the
threshold (interval + grace period).

Expected to run every 30 minutes via GitHub Actions or systemd timer.

Usage:
    python scripts/backup_deadman_switch.py              # normal run
    python scripts/backup_deadman_switch.py --dry-run     # log only, no alert
    python scripts/backup_deadman_switch.py --grace 6    # 6h grace period
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from touch_index.paperclip_client import _session, _base, _company

BACKUP_STATE_FILE = Path.home() / ".paperclip" / "instances" / "default" / "backup-state" / "last-success.json"
BACKUP_INTERVAL_HOURS = 4
DEFAULT_GRACE_HOURS = 8
DEADMAN_LOG = Path.home() / ".paperclip" / "backup_deadman_switch.log"
ALERT_SEARCH_QUERY = "Backup dead-man triggered"
CTO_AGENT_ID = "41b5ede6-e209-40ba-b923-dc969c722e6d"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(DEADMAN_LOG),
        logging.StreamHandler() if os.isatty(0) else logging.NullHandler(),
    ],
)
logger = logging.getLogger("backup_deadman_switch")


def _read_last_success() -> dict | None:
    if not BACKUP_STATE_FILE.exists():
        logger.warning("last-success.json not found at %s", BACKUP_STATE_FILE)
        return None
    try:
        return json.loads(BACKUP_STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read last-success.json: %s", exc)
        return None


def _get_backup_age_hours(state: dict) -> float | None:
    raw = state.get("lastSuccess")
    if not raw:
        logger.warning("last-success.json has no 'lastSuccess' field")
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        logger.warning("Unparseable lastSuccess timestamp: %s", raw)
        return None
    age = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
    return age.total_seconds() / 3600


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


def _create_alert(age_hours: float | None, grace_hours: int, dry_run: bool) -> bool:
    try:
        sess = _session()
        base_url = _base()
        company_id = _company()
    except (KeyError, OSError) as exc:
        logger.error("Failed to init Paperclip session: %s", exc)
        return False

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    threshold = BACKUP_INTERVAL_HOURS + grace_hours

    if age_hours is None:
        subject = "no backups ever succeeded"
        description = (
            f"**Backup dead-man triggered — no successful offsite push**\n\n"
            f"- **Check time:** {now_str}\n"
            f"- **Last success:** MISSING (no `last-success.json` found)\n"
            f"- **Action required:** Investigate backup routine immediately.\n"
            f"  Script at `/home/sirrus/.paperclip/scripts/backup-to-drive.sh`.\n"
            f"  State file path: `{BACKUP_STATE_FILE}`\n"
        )
    else:
        state = _read_last_success()
        last_dest = ""
        if state:
            last_dest = state.get("destination", "")
        subject = f"{age_hours:.1f}h since last successful offsite push"
        description = (
            "**Backup dead-man triggered — no successful offsite push "
            f"in >{threshold}h**\n\n"
            f"- **Check time:** {now_str}\n"
            f"- **Last success:** {age_hours:.1f}h ago\n"
            f"- **Expected interval:** {BACKUP_INTERVAL_HOURS}h\n"
            f"- **Grace period:** {grace_hours}h\n"
            f"- **Total threshold:** {threshold}h\n"
            f"- **Last destination:** {last_dest or 'unknown'}\n"
            f"- **Action required:** Investigate backup routine immediately.\n"
            f"  Script at `/home/sirrus/.paperclip/scripts/backup-to-drive.sh`.\n"
            f"  State file path: `{BACKUP_STATE_FILE}`\n"
        )

    title = f"Backup dead-man triggered — {subject}"
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


def run(grace_hours: int = DEFAULT_GRACE_HOURS, dry_run: bool = False) -> bool:
    state = _read_last_success()
    age_hours = _get_backup_age_hours(state) if state else None
    threshold = BACKUP_INTERVAL_HOURS + grace_hours

    if age_hours is None:
        logger.warning("No successful backup recorded — alert will fire")
    elif age_hours <= threshold:
        logger.info(
            "Backup current: %.1fh old (threshold %.1fh)",
            age_hours,
            threshold,
        )
        return True
    else:
        logger.warning(
            "Backup overdue: %.1fh old (threshold %.1fh) — alert will fire",
            age_hours,
            threshold,
        )

    existing = _find_existing_alert()
    if existing:
        logger.info(
            "Existing alert %s already open — skipping duplicate creation",
            existing.get("identifier", existing["id"]),
        )
        return True

    return _create_alert(age_hours, grace_hours, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Dead-man's-switch monitor for Paperclip backup pipeline",
    )
    parser.add_argument(
        "--grace",
        type=int,
        default=DEFAULT_GRACE_HOURS,
        help=f"Grace period in hours (default: {DEFAULT_GRACE_HOURS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without creating alerts",
    )
    args = parser.parse_args()

    ok = run(grace_hours=args.grace, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
