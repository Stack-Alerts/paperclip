"""Bug-close Touch Index polling worker + webhook handler — run by Paperclip routine
every 15 minutes or triggered via repository_dispatch webhook.

Polling mode (default):
  Queries Paperclip for all done non-FDR issues closed in the last 30 minutes
  (overlap window to avoid gaps), then upserts to touch_index_bug_files for
  those that have git fix commits.  FDR-labelled issues are skipped (handled
  by the FR worker).

Webhook mode (--issue-id):
  Processes a single non-FDR issue by UUID (triggered by Paperclip
  issue_status_changed webhook events).  The issue is fetched from the
  Paperclip API and ingested immediately.

Usage:
    python scripts/run_touch_index_bug_worker.py [--lookback-minutes N] [--dry-run] [--validate]
    python scripts/run_touch_index_bug_worker.py --issue-id <uuid> [--dry-run]
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

from touch_index.db import get_engine, health_check
from touch_index.paperclip_client import get_closed_non_fdr_issues, transition_issue_status
from touch_index.bug_worker import run_bug_worker, process_bug_issue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("touch_index.bug_worker_runner")


def _run_validation(engine) -> int:
    """Run bug data quality validation. Returns number of failures (0 = clean)."""
    from validate_touch_index_bug import _run_checks

    return _run_checks(stale_days=30, engine=engine)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bug-close Touch Index polling worker")
    parser.add_argument(
        "--issue-id",
        type=str,
        default=None,
        help="Process a single non-FDR issue by Paperclip UUID (webhook trigger)",
    )
    parser.add_argument(
        "--lookback-minutes",
        type=int,
        default=30,
        help="Process bug issues closed within this many minutes (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be ingested without writing to DB",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run bug data quality validation after ingestion (exits non-zero on failure)",
    )
    args = parser.parse_args()

    engine = get_engine()
    if not health_check(engine):
        logger.error("DB health check failed — aborting")
        sys.exit(1)

    if args.issue_id:
        logger.info("Processing single issue %s (dry_run=%s)", args.issue_id, args.dry_run)
        result = process_bug_issue(engine, args.issue_id, dry_run=args.dry_run)
        if result is None:
            logger.info("No bug issue found for %s", args.issue_id)
        else:
            logger.info(
                "Bug worker (single) — %s: %d files indexed via %s, skipped=%s",
                result.issue_identifier,
                result.files_indexed,
                result.source,
                result.skipped_no_commits,
            )
            if not args.dry_run:
                try:
                    transition_issue_status(args.issue_id, "done")
                    logger.info("Marked %s as done", result.issue_identifier)
                except Exception:
                    logger.exception(
                        "Failed to mark %s as done", result.issue_identifier
                    )
        if args.validate:
            logger.info("Running bug data quality validation after single-issue ingestion…")
            failures = _run_validation(engine)
            if failures:
                logger.error("VALIDATION FAILED: %d check(s) — investigate", failures)
                sys.exit(1)
            logger.info("VALIDATION PASSED: all checks clean")
        return

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.lookback_minutes)
    logger.info("Fetching closed non-FDR issues completed after %s", cutoff.isoformat())

    issues = get_closed_non_fdr_issues(closed_after=cutoff)
    logger.info("Found %d closed non-FDR issue(s) to process", len(issues))

    if not issues:
        logger.info("Nothing to do")
        if args.validate:
            logger.info("Running validation on empty ingestion window…")
            failures = _run_validation(engine)
            if failures:
                logger.error("VALIDATION FAILED: %d check(s) — investigate", failures)
                sys.exit(1)
        return

    results = run_bug_worker(engine, issues, dry_run=args.dry_run)

    total_files = sum(r.files_indexed for r in results)
    skipped = sum(1 for r in results if r.skipped_no_commits)

    if args.dry_run:
        logger.info("DRY RUN — would have processed %d issue(s)", len(results))

    # Mark each processed issue as done in Paperclip.
    # Skip issues already in done status to avoid 403 on redundant transition.
    # Skip in dry-run mode -- no side effects.
    if args.dry_run:
        logger.info("DRY RUN -- skipping transition-to-done for %d issue(s)", len(issues))
    else:
        for issue in issues:
            issue_id = issue.get("id", "")
            if not issue_id:
                continue
            try:
                transition_issue_status(issue_id, "done")
                logger.info("Marked %s as done", issue.get("identifier", issue_id))
            except Exception:
                logger.exception(
                    "Failed to mark %s as done", issue.get("identifier", issue_id)
                )

    logger.info(
        "Bug worker done — %d issues processed, %d files indexed, %d skipped (no commits)",
        len(results),
        total_files,
        skipped,
    )

    if args.validate:
        logger.info("Running bug data quality validation after ingestion…")
        failures = _run_validation(engine)
        if failures:
            logger.error("VALIDATION FAILED: %d check(s) — investigate", failures)
            sys.exit(1)
        logger.info("VALIDATION PASSED: all checks clean")


if __name__ == "__main__":
    main()
