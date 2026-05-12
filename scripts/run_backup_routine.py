#!/usr/bin/env python3
"""Scheduled backup routine runner — runs every 4h via systemd timer.

Creates a compressed database backup and prunes backups older than the
configured retention window.  Exits non-zero on failure so systemd can
report the failure independently of the dead-man's-switch check.

Usage:
    python scripts/run_backup_routine.py          # normal run
    python scripts/run_backup_routine.py --dry-run  # log only, no backup
"""

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.optimizer_v3.database.backup import get_backup_manager


BACKUP_LOG = Path.home() / ".paperclip" / "backup_routine.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BACKUP_LOG),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("backup_routine")


def run(dry_run: bool = False) -> bool:
    try:
        mgr = get_backup_manager()
        logger.info("backup_path=%s retention_days=%s",
                    mgr.backup_dir, mgr.backup_config.get("retention_days"))

        if dry_run:
            logger.info("DRY RUN: would create backup and cleanup old backups")
            return True

        backup_file = mgr.create_backup(compress=True)
        logger.info("Backup created: %s (%d bytes)", backup_file.name,
                    backup_file.stat().st_size)

        deleted = mgr.cleanup_old_backups()
        if deleted:
            logger.info("Cleaned %d old backup(s)", len(deleted))
        else:
            logger.info("No old backups to clean")

        logger.info("Backup routine completed successfully")
        return True

    except Exception:
        logger.exception("Backup routine failed")
        return False


def main():
    parser = argparse.ArgumentParser(description="4-hourly database backup routine")
    parser.add_argument("--dry-run", action="store_true",
                        help="Log actions without performing them")
    args = parser.parse_args()

    ok = run(dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
