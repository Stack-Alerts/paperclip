"""Backfill: bulk-close stale in_progress (running) routine instances.

Detects heartbeat runs stuck in ``running`` status whose output has been
silent beyond the suspicion threshold.  Cancels each stale run via the
board-level admin endpoint, bypassing the stale checkoutRunId check that
would block a normal status transition.

Usage:
    python scripts/backfill_close_stale_runs.py [--dry-run] [--stale-minutes N]
                                               [--limit N]

Requires ``PAPERCLIP_API_URL``, ``PAPERCLIP_COMPANY_ID``, and either
``PAPERCLIP_BOARD_API_KEY`` or a board-privileged ``PAPERCLIP_API_KEY``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from touch_index.paperclip_client import (
    list_live_runs,
    cancel_heartbeat_run,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("backfill.close_stale_runs")

# Paperclip server uses 60 minutes as suspicion threshold
DEFAULT_STALE_MINUTES = 60


def _is_stale(run: dict, stale_ms: int) -> bool:
    """Return True if a running run's output silence exceeds *stale_ms*."""
    if run.get("status") not in ("running",):
        return False
    silence = run.get("outputSilence") or {}
    level = silence.get("level")
    if level in ("snoozed", "not_applicable"):
        return False
    if level == "critical":
        return True
    age_ms = silence.get("silenceAgeMs")
    if age_ms is not None and age_ms >= stale_ms:
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-close stale in_progress routine instances",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report stale runs without cancelling them",
    )
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=DEFAULT_STALE_MINUTES,
        help=f"Silence threshold in minutes (default: {DEFAULT_STALE_MINUTES})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max runs to fetch (default: 200)",
    )
    args = parser.parse_args()

    stale_ms = args.stale_minutes * 60 * 1000
    logger.info(
        "Fetching live runs (stale_threshold=%d min, dry_run=%s, limit=%d)",
        args.stale_minutes,
        args.dry_run,
        args.limit,
    )

    runs = list_live_runs(min_count=0, limit=args.limit)
    logger.info("Fetched %d live run(s)", len(runs))

    stale_runs = [r for r in runs if _is_stale(r, stale_ms)]
    logger.info(
        "Found %d stale running run(s) out of %d total",
        len(stale_runs),
        len(runs),
    )

    if not stale_runs:
        logger.info("Nothing to do — no stale runs detected")
        return

    cancelled = 0
    failed = 0

    for run in stale_runs:
        run_id = run.get("id", "?")
        agent_name = run.get("agentName", "?")
        silence = run.get("outputSilence") or {}
        age_s = (silence.get("silenceAgeMs") or 0) // 1000
        logger.info(
            "Stale run: id=%s agent=%s silence_age=%ds status=%s",
            run_id,
            agent_name,
            age_s,
            run.get("status", "?"),
        )

        if args.dry_run:
            continue

        try:
            result = cancel_heartbeat_run(run_id)
            if result is None:
                logger.warning("Run %s not found (already removed?)", run_id)
            else:
                logger.info(
                    "Cancelled run %s (agent=%s, new_status=%s)",
                    run_id,
                    agent_name,
                    result.get("status", "?"),
                )
                cancelled += 1
        except Exception as exc:
            logger.error("Failed to cancel run %s: %s", run_id, exc)
            failed += 1

    summary = []
    if args.dry_run:
        summary.append(f"Dry-run: {len(stale_runs)} stale run(s) would be cancelled")
    else:
        summary.append(f"Cancelled: {cancelled}, failed: {failed}")
    summary.append(f"Total stale: {len(stale_runs)}")
    logger.info("Summary — %s", " | ".join(summary))


if __name__ == "__main__":
    main()
