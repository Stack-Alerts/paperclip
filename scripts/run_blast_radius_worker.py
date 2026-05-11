"""Blast Radius polling worker runner — run by Paperclip routine every 15 minutes.

Polls Paperclip for fix/bug issues that have transitioned to ``in_review``,
generates a Blast Radius Report for each, and posts it as a comment.

State is persisted in ``BLAST_RADIUS_STATE_FILE`` (defaults to
``data/blast_radius_worker_state.json``) so the worker is safe to restart.

Usage:
    python scripts/run_blast_radius_worker.py [--loop SECONDS] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from blast_radius.worker import run_once, run_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("blast_radius.worker_runner")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Blast Radius polling worker — detect fix->in_review and post report",
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
        help="Log reports but do not post comments",
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Re-process already-seen issues (useful after touchedFiles update)",
    )
    args = parser.parse_args()

    if args.loop:
        logger.info(
            "Starting Blast Radius worker loop (interval=%ds, dry_run=%s, force_reprocess=%s)",
            args.loop, args.dry_run, args.force_reprocess,
        )
        run_loop(interval_seconds=args.loop, dry_run=args.dry_run, force_reprocess=args.force_reprocess)
    else:
        results = run_once(dry_run=args.dry_run, force_reprocess=args.force_reprocess)
        logger.info("Blast Radius worker run complete — %d issue(s) processed", len(results))
        logger.info("Results: %s", results)


if __name__ == "__main__":
    main()
