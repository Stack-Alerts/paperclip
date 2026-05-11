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
    python scripts/run_touch_index_bug_worker.py [--lookback-minutes N]
    python scripts/run_touch_index_bug_worker.py --issue-id <uuid>
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
from touch_index.paperclip_client import get_closed_non_fdr_issues
from touch_index.bug_worker import run_bug_worker, process_bug_issue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("touch_index.bug_worker_runner")


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
    args = parser.parse_args()

    engine = get_engine()
    if not health_check(engine):
        logger.error("DB health check failed — aborting")
        sys.exit(1)

    if args.issue_id:
        result = process_bug_issue(engine, args.issue_id)
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
        return

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.lookback_minutes)
    logger.info("Fetching closed non-FDR issues completed after %s", cutoff.isoformat())

    issues = get_closed_non_fdr_issues(closed_after=cutoff)
    logger.info("Found %d closed non-FDR issue(s) to process", len(issues))

    if not issues:
        logger.info("Nothing to do")
        return

    results = run_bug_worker(engine, issues)

    total_files = sum(r.files_indexed for r in results)
    skipped = sum(1 for r in results if r.skipped_no_commits)

    logger.info(
        "Bug worker done — %d issues processed, %d files indexed, %d skipped (no commits)",
        len(results),
        total_files,
        skipped,
    )


if __name__ == "__main__":
    main()
