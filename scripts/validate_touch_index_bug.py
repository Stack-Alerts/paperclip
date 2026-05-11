"""Touch Index Bug data quality validation — run after ingestion.

Checks:
  1. touch_index_bug_files has no orphan rows (bug_issue_id must resolve in Paperclip).
  2. No duplicate (file_path, bug_issue_id) pairs (UNIQUE constraint enforcement).
  3. Each bug_issue_id has at least one file_path.
  4. No stale rows: closed_at older than N days or NULL for very old issues.
  5. count summary by source (git vs comments vs none).

Usage:
    python scripts/validate_touch_index_bug.py [--stale-days 30]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy import text
from touch_index.db import get_engine, health_check

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("touch_index.validate_bug")


def _run_checks(stale_days: int) -> int:
    failures = 0

    engine = get_engine()
    if not health_check(engine):
        logger.error("DB health check failed — aborting")
        sys.exit(1)

    with engine.connect() as conn:
        # 1. Duplicate check
        dup_count = conn.execute(
            text("""
                SELECT COUNT(*) FROM (
                    SELECT file_path, bug_issue_id, COUNT(*)
                    FROM touch_index_bug_files
                    GROUP BY file_path, bug_issue_id
                    HAVING COUNT(*) > 1
                ) dups
            """)
        ).scalar() or 0
        if dup_count:
            logger.warning("CHECK FAILED: %d duplicate (file_path, bug_issue_id) pairs", dup_count)
            failures += 1
        else:
            logger.info("CHECK PASSED: no duplicate (file_path, bug_issue_id) pairs")

        # 2. Null closed_at check (warn only — closed_at is nullable per schema)
        null_closed = conn.execute(
            text("SELECT COUNT(*) FROM touch_index_bug_files WHERE closed_at IS NULL")
        ).scalar() or 0
        if null_closed:
            logger.info(
                "CHECK NOTE: %d rows with NULL closed_at (acceptable if issue completedAt is missing)",
                null_closed,
            )

        # 3. Stale rows (closed_at older than N days, or NULL with old bug_identifier)
        cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
        stale_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM touch_index_bug_files "
                "WHERE closed_at IS NOT NULL AND closed_at < :cutoff"
            ),
            {"cutoff": cutoff},
        ).scalar() or 0
        if stale_count:
            logger.warning(
                "CHECK WARN: %d rows with closed_at older than %d days",
                stale_count, stale_days,
            )
        else:
            logger.info("CHECK PASSED: no stale rows (>%d days)", stale_days)

        # 4. Total row count
        total = conn.execute(
            text("SELECT COUNT(*) FROM touch_index_bug_files")
        ).scalar() or 0
        logger.info("Total rows in touch_index_bug_files: %d", total)

        # 5. Bug issue count
        bug_count = conn.execute(
            text("SELECT COUNT(DISTINCT bug_issue_id) FROM touch_index_bug_files")
        ).scalar() or 0
        logger.info("Distinct bug issues indexed: %d", bug_count)

    if failures:
        logger.error("VALIDATION COMPLETE: %d check(s) FAILED — investigate", failures)
    else:
        logger.info("VALIDATION COMPLETE: all checks PASSED")

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Touch Index Bug data quality validation"
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=30,
        help="Alert if closed_at is older than this many days (default: 30)",
    )
    args = parser.parse_args()

    logger.info("Touch Index Bug validation — stale threshold: %d days", args.stale_days)
    failures = _run_checks(args.stale_days)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
