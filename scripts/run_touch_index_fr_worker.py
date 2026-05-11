"""FR Touch Index polling worker — run by Paperclip routine every 15 minutes.

Queries Paperclip for FDR issues updated in the last 30 minutes (overlap
window to avoid gaps on late-firing routines), then upserts to
touch_index_fr_files.

Watermark strategy: the 30-minute look-back window with idempotent upsert
means we can re-process safely without state tracking.

Usage:
    python scripts/run_touch_index_fr_worker.py [--lookback-minutes N]
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
from touch_index.paperclip_client import get_fdr_issues, transition_issue_status
from touch_index.fr_worker import run_fr_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("touch_index.fr_worker_runner")


def main() -> None:
    parser = argparse.ArgumentParser(description="FR Touch Index polling worker")
    parser.add_argument(
        "--lookback-minutes",
        type=int,
        default=30,
        help="Process FDR issues updated within this many minutes (default: 30)",
    )
    args = parser.parse_args()

    engine = get_engine()
    if not health_check(engine):
        logger.error("DB health check failed — aborting")
        sys.exit(1)

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.lookback_minutes)
    logger.info("Fetching FDR issues updated after %s", cutoff.isoformat())

    issues = get_fdr_issues(updated_after=cutoff)
    logger.info("Found %d FDR issue(s) to process", len(issues))

    if not issues:
        logger.info("Nothing to do")
        return

    results = run_fr_worker(engine, issues)

    total_files = sum(r.files_indexed for r in results)
    skipped = sum(1 for r in results if r.skipped_no_commits)

    # Mark each processed issue as done in Paperclip.
    # Skip issues already in done status to avoid 403 on redundant transition.
    for issue in issues:
        issue_id = issue.get("id", "")
        if not issue_id or issue.get("status") == "done":
            continue
        try:
            transition_issue_status(issue_id, "done")
            logger.info("Marked %s as done", issue.get("identifier", issue_id))
        except Exception:
            logger.exception(
                "Failed to mark %s as done", issue.get("identifier", issue_id)
            )

    logger.info(
        "FR worker done — %d issues processed, %d files indexed, %d skipped (no commits)",
        len(results),
        total_files,
        skipped,
    )


if __name__ == "__main__":
    main()
