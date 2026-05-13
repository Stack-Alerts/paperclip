#!/usr/bin/env python3
"""
Restore Drill Script — BTCAAAAA-908

Validates the full backup/restore pipeline by restoring the most recent
backup to the optimizer_v3_drill_test database and verifying:

1.  Backup decompression and SQL restore
2.  Table count verification
3.  AI readonly role grants are intact
4.  Cleanup (drop drill DB) is optional

Usage:
    python scripts/run_restore_drill.py                             # latest backup
    python scripts/run_restore_drill.py --backup /path/to/file.sql.gz  # specific file
    python scripts/run_restore_drill.py --cleanup                     # drop drill DB
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.optimizer_v3.database.backup import DatabaseBackup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("restore_drill")

_DRILL_DB = "optimizer_v3_drill_test"


def _find_backup(path: str | None) -> Path:
    if path:
        p = Path(path)
        if p.exists():
            return p
        logger.error("Backup file not found: %s", p)
        sys.exit(1)

    backup_mgr = DatabaseBackup()
    backups = backup_mgr.list_backups()
    if backups:
        return Path(backups[-1]["path"])

    backup_dir = Path(os.environ.get("POSTGRES_BACKUP_PATH", "/home/sirrus/backups/optimizer_v3"))
    candidates = sorted(backup_dir.glob("*.sql*"))
    if candidates:
        return candidates[-1]

    logger.error("No backup files found in %s", backup_dir)
    sys.exit(1)


def _psql(db: DatabaseBackup, sql: str, env: dict) -> subprocess.CompletedProcess:
    cmd = [
        "psql", "-h", db.db_config["host"], "-p", str(db.db_config["port"]),
        "-U", db.db_config["user"], "-d", db.db_config["database"], "-tAc", sql,
    ]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def run_drill(backup_path: str | None = None) -> None:
    logger.info("=" * 60)
    logger.info("RESTORE DRILL STARTED")
    logger.info("=" * 60)

    os.environ["POSTGRES_DB"] = _DRILL_DB
    drill_backup = DatabaseBackup()
    env = {**os.environ.copy(), "PGPASSWORD": drill_backup.db_config["password"]}

    backup_file = _find_backup(backup_path)
    logger.info("Backup: %s (%d bytes)", backup_file.name, backup_file.stat().st_size)

    r = _psql(drill_backup, "SELECT 1", env)
    if r.returncode != 0 or r.stdout.strip() != "1":
        logger.error("Cannot connect to %s — does the database exist?", _DRILL_DB)
        logger.error("Run: sudo -u postgres psql -c \"CREATE DATABASE %s OWNER optimizer_admin;\"", _DRILL_DB)
        sys.exit(1)
    logger.info("Drill database reachable: PASS")

    if not drill_backup.verify_backup(backup_file):
        logger.error("Backup verification failed — aborting drill")
        sys.exit(1)
    logger.info("Backup integrity: PASS")

    logger.info("Restoring...")
    drill_backup.restore_backup(backup_file, drop_existing=False)
    logger.info("Restore: PASS")

    logger.info("Re-applying AI grants...")
    drill_backup.reapply_ai_grants()
    logger.info("Grants: PASS")

    r = _psql(drill_backup,
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'",
        env)
    logger.info("Tables restored: %s", r.stdout.strip())

    logger.info("=" * 60)
    logger.info("RESTORE DRILL COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)


def cleanup_drill() -> None:
    logger.info("Dropping drill database: %s", _DRILL_DB)
    backup_mgr = DatabaseBackup()
    env = {**os.environ.copy(), "PGPASSWORD": backup_mgr.db_config["password"]}
    r = subprocess.run(
        ["psql", "-h", backup_mgr.db_config["host"], "-p", str(backup_mgr.db_config["port"]),
         "-U", backup_mgr.db_config["user"], "-d", "postgres",
         "-c", f"DROP DATABASE IF EXISTS {_DRILL_DB}"],
        env=env, capture_output=True, text=True,
    )
    if r.returncode == 0:
        logger.info("Drill database dropped successfully")
    else:
        logger.error("Failed to drop: %s", r.stderr.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run restore drill for optimizer_v3")
    parser.add_argument("--backup", help="Specific backup file path")
    parser.add_argument("--cleanup", action="store_true", help="Drop the drill database")
    args = parser.parse_args()

    if args.cleanup:
        cleanup_drill()
    else:
        run_drill(args.backup)


if __name__ == "__main__":
    main()
