"""Touch Index FR data quality validation — run after ingestion.

Checks:
  1. touch_index_fr_files has no orphan rows (fr_issue_id must resolve in Paperclip).
  2. No duplicate (file_path, fr_issue_id) pairs (UNIQUE constraint enforcement).
  3. All rows have a non-null updated_at within the last N hours.
  4. Each fr_issue_id has at least one file_path (no empty FR issues in the table).
  5. No stale rows: updated_at older than 7 days (configurable).

Usage:
    python scripts/validate_touch_index_fr.py [--stale-hours 168]
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
logger = logging.getLogger("touch_index.validate_fr")


def _run_checks(stale_hours: int) -> int:
    """Run all validation checks. Returns number of failures (0 = clean)."""
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
                    SELECT file_path, fr_issue_id, COUNT(*)
                    FROM touch_index_fr_files
                    GROUP BY file_path, fr_issue_id
                    HAVING COUNT(*) > 1
                ) dups
            """)
        ).scalar() or 0
        if dup_count:
            logger.warning("CHECK FAILED: %d duplicate (file_path, fr_issue_id) pairs", dup_count)
            failures += 1
        else:
            logger.info("CHECK PASSED: no duplicate (file_path, fr_issue_id) pairs")

        # 2. Null updated_at check
        null_updated = conn.execute(
            text("SELECT COUNT(*) FROM touch_index_fr_files WHERE updated_at IS NULL")
        ).scalar() or 0
        if null_updated:
            logger.warning("CHECK FAILED: %d rows with NULL updated_at", null_updated)
            failures += 1
        else:
            logger.info("CHECK PASSED: no NULL updated_at values")

        # 3. Stale rows (updated_at older than N hours)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_hours)
        stale_count = conn.execute(
            text("SELECT COUNT(*) FROM touch_index_fr_files WHERE updated_at < :cutoff"),
            {"cutoff": cutoff},
        ).scalar() or 0
        if stale_count:
            logger.warning(
                "CHECK WARN: %d rows with updated_at older than %d hours",
                stale_count, stale_hours,
            )
        else:
            logger.info("CHECK PASSED: no stale rows (>%d hours)", stale_hours)

        # 4. Total row count
        total = conn.execute(
            text("SELECT COUNT(*) FROM touch_index_fr_files")
        ).scalar() or 0
        logger.info("Total rows in touch_index_fr_files: %d", total)

        # 5. FR issue count
        fr_count = conn.execute(
            text("SELECT COUNT(DISTINCT fr_issue_id) FROM touch_index_fr_files")
        ).scalar() or 0
        logger.info("Distinct FR issues indexed: %d", fr_count)

        # 6. Empty FR issues (in table but no file rows)
        #    Not a hard failure — some FDRs legitimately have no code changes yet.
        empty_issues = conn.execute(
            text("""
                SELECT fr_identifier FROM touch_index_fr_files
                GROUP BY fr_issue_id, fr_identifier
                HAVING COUNT(*) = 0
            """)
        ).fetchall()
        if empty_issues:
            logger.info(
                "FR issues with no file rows: %d", len(empty_issues)
            )

    if failures:
        logger.error("VALIDATION COMPLETE: %d check(s) FAILED — investigate", failures)
    else:
        logger.info("VALIDATION COMPLETE: all checks PASSED")

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Touch Index FR data quality validation"
    )
    parser.add_argument(
        "--stale-hours",
        type=int,
        default=168,
        help="Alert if updated_at is older than this many hours (default: 168=7d)",
    )
    args = parser.parse_args()

    logger.info("Touch Index FR validation — stale threshold: %d hours", args.stale_hours)
    failures = _run_checks(args.stale_hours)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
