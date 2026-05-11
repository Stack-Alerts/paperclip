"""Impact Gate polling worker runner — run by Paperclip routine every 15 minutes.

Polls Paperclip for in_review issues that carry FR labels or fix/bug markers,
runs the Impact Gate (FR acceptance + bug regression tests), and posts the
structured result as a Paperclip comment.  Issues that pass are transitioned
to ``done``; failures stay ``in_review`` with failure details.

Usage:
    python scripts/run_impact_gate_worker.py [--loop SECONDS] [--dry-run]
    python scripts/run_impact_gate_worker.py --issue-id <uuid> [--old-status <status>]
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from impact_gate.worker import process_issue, run_once, run_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("impact_gate.worker_runner")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Impact Gate worker -- run FR acceptance + bug regression gates",
    )
    parser.add_argument(
        "--issue-id",
        type=str,
        metavar="UUID",
        help="Process a single issue by Paperclip UUID (webhook trigger)",
    )
    parser.add_argument(
        "--old-status",
        type=str,
        metavar="STATUS",
        help="Previous status when called from a status-change webhook",
    )
    parser.add_argument(
        "--loop",
        type=int,
        metavar="SECONDS",
        help="Run continuously, sleeping SECONDS between polls (default: run once and exit)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log results but do not post comments or transition issues",
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Re-process already-seen issues (useful for re-running gate after fixes)",
    )
    args = parser.parse_args()

    if args.issue_id:
        logger.info(
            "Processing single issue %s (dry_run=%s, old_status=%s)",
            args.issue_id, args.dry_run, args.old_status,
        )
        result = process_issue(
            args.issue_id,
            dry_run=args.dry_run,
            old_status=args.old_status,
        )
        if result:
            logger.info("Issue %s result: %s", args.issue_id, result)
        else:
            logger.info("Issue %s not eligible -- no gate run", args.issue_id)
    elif args.loop:
        logger.info(
            "Starting Impact Gate worker loop (interval=%ds, dry_run=%s, force_reprocess=%s)",
            args.loop, args.dry_run, args.force_reprocess,
        )
        run_loop(
            interval_seconds=args.loop,
            dry_run=args.dry_run,
            force_reprocess=args.force_reprocess,
        )
    else:
        results = run_once(dry_run=args.dry_run, force_reprocess=args.force_reprocess)
        logger.info(
            "Impact Gate worker run complete -- %d issue(s) processed", len(results)
        )
        logger.info("Results: %s", results)


if __name__ == "__main__":
    main()
