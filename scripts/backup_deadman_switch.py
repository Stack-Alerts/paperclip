#!/usr/bin/env python3
"""Dead-man's-switch monitor for the 4-hourly backup routine.

Checks whether a database backup was created within the expected window
(interval + grace period).  If no recent backup is found, creates a
Paperclip alert issue assigned to the CTO.

Expected to run every hour via systemd timer.  The grace period (default
1 hour) means an alert fires when the backup is ~5 hours overdue.

Usage:
    python scripts/backup_deadman_switch.py            # normal run
    python scripts/backup_deadman_switch.py --dry-run   # log only, no alert
    python scripts/backup_deadman_switch.py --grace 2   # 2h grace period
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

from src.optimizer_v3.database.backup import get_backup_manager

DEADMAN_LOG = Path.home() / ".paperclip" / "backup_deadman_switch.log"
CTO_AGENT_ID = "41b5ede6-e209-40ba-b923-dc969c722e6d"
ALERT_LABEL = "backup-alert"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(DEADMAN_LOG),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("backup_deadman_switch")


BACKUP_INTERVAL_HOURS = 4
DEFAULT_GRACE_HOURS = 1


def _get_latest_backup_age_hours(mgr) -> float | None:
    backups = sorted(
        mgr.backup_dir.glob("optimizer_v3_*.sql*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        return None
    latest = backups[0]
    age = (datetime.now().astimezone() - datetime.fromtimestamp(latest.stat().st_mtime).astimezone())
    return age.total_seconds() / 3600


def _create_alert(sess, base_url: str, company_id: str,
                  age_hours: float | None, grace_hours: int,
                  dry_run: bool) -> bool:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if age_hours is None:
        subject = "No database backups found at all"
        body = (
            "**Backup dead-man's-switch alert**\n\n"
            f"- **Check time:** {date_str}\n"
            "- **Status:** No backup files exist in the backup directory.\n"
            "- **Action required:** Investigate the backup routine immediately.\n"
        )
    else:
        subject = f"Backup overdue \u2014 {age_hours:.1f}h since last backup"
        body = (
            "**Backup dead-man's-switch alert**\n\n"
            f"- **Check time:** {date_str}\n"
            f"- **Hours since last backup:** {age_hours:.1f}\n"
            f"- **Expected interval:** {BACKUP_INTERVAL_HOURS}h\n"
            f"- **Grace period:** {grace_hours}h\n"
            "- **Action required:** Investigate the backup routine immediately.\n"
        )

    title = f"Backup Dead-Man Alert \u2014 {subject}"

    if dry_run:
        logger.info("DRY RUN: would create alert issue '%s'", title)
        print(json.dumps({
            "title": title,
            "body": body,
            "labels": [ALERT_LABEL],
            "assigneeAgentId": CTO_AGENT_ID,
            "priority": "critical",
        }, indent=2))
        return True

    payload = {
        "title": title,
        "body": body,
        "labels": [ALERT_LABEL],
        "assigneeAgentId": CTO_AGENT_ID,
        "priority": "critical",
        "status": "todo",
    }

    try:
        resp = sess.post(
            f"{base_url}/api/companies/{company_id}/issues",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        created = resp.json()
        logger.info("Created alert issue %s: %s",
                    created.get("identifier", ""), title)
        return True
    except Exception as exc:
        logger.error("Failed to create alert issue: %s", exc)
        return False


def run(grace_hours: int = DEFAULT_GRACE_HOURS,
        dry_run: bool = False) -> bool:
    try:
        mgr = get_backup_manager()
    except Exception:
        logger.exception("Failed to initialize backup manager")
        return False

    age_hours = _get_latest_backup_age_hours(mgr)
    threshold = BACKUP_INTERVAL_HOURS + grace_hours

    if age_hours is None:
        logger.warning("No backup files found — alert will fire")
    elif age_hours <= threshold:
        logger.info("Backup is current: %.1fh old (threshold %.1fh)",
                    age_hours, threshold)
        return True
    else:
        logger.warning(
            "Backup overdue: %.1fh old (threshold %.1fh) — alert will fire",
            age_hours, threshold,
        )

    try:
        from touch_index.paperclip_client import _session, _base, _company
        sess = _session()
        base_url = _base()
        company_id = _company()
    except Exception:
        logger.exception(
            "Failed to init Paperclip session — env vars PAPERCLIP_API_URL, "
            "PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID must be set"
        )
        return False

    ok = _create_alert(sess, base_url, company_id, age_hours, grace_hours, dry_run)
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="Dead-man's-switch monitor for 4-hourly backup routine",
    )
    parser.add_argument("--grace", type=int, default=DEFAULT_GRACE_HOURS,
                        help=f"Grace period in hours (default: {DEFAULT_GRACE_HOURS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Log actions without creating alerts")
    args = parser.parse_args()

    ok = run(grace_hours=args.grace, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
