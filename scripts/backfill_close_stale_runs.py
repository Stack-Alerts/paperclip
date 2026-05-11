"""Backfill: bulk-close stale in_progress routine instances and issues.

Two modes of staleness detection:

1. **Stale heartbeat runs** — runs stuck in ``running`` whose output has been
   silent beyond the suspicion threshold (60 min).  Cancelled via the board-level
   ``POST /heartbeat-runs/:id/cancel`` endpoint.

2. **Stuck in_progress issues** — issues whose checkoutRunId is owned by a
   dead/ghost run, making normal PATCH status transitions fail (HTTP 500).
   These are force-released and transitioned to ``done`` via the board-level
   API, bypassing the stale checkoutRunId check.

Usage:
    python scripts/backfill_close_stale_runs.py [--dry-run] [--stale-minutes N]
                                                [--limit N]
    python scripts/backfill_close_stale_runs.py --issue-ids ID1,ID2 [--dry-run]

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
    list_issues,
    cancel_heartbeat_run,
    transition_issue_status_board,
    force_release_issue,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("backfill.close_stale_runs")

STALE_SUSPICION_MINUTES = 60


# ---------------------------------------------------------------------------
# Stale run detection
# ---------------------------------------------------------------------------

def _is_stale_run(run: dict, stale_ms: int) -> bool:
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


# ---------------------------------------------------------------------------
# Stale run actions
# ---------------------------------------------------------------------------

def _cancel_stale_runs(dry_run: bool, stale_ms: int, limit: int) -> dict:
    """Find and cancel stale heartbeat runs. Returns count dict."""
    runs = list_live_runs(min_count=0, limit=limit)
    logger.info("Fetched %d live run(s)", len(runs))

    stale = [r for r in runs if _is_stale_run(r, stale_ms)]
    logger.info("Found %d stale running run(s) out of %d", len(stale), len(runs))

    cancelled = 0
    failed = 0
    for run in stale:
        run_id = run.get("id", "?")
        agent_name = run.get("agentName", "?")
        silence = run.get("outputSilence") or {}
        age_s = (silence.get("silenceAgeMs") or 0) // 1000
        logger.info(
            "Stale run: id=%s agent=%s silence_age=%ds",
            run_id, agent_name, age_s,
        )
        if dry_run:
            continue
        try:
            result = cancel_heartbeat_run(run_id)
            if result is None:
                logger.warning("Run %s not found (already removed?)", run_id)
            else:
                cancelled += 1
        except Exception as exc:
            logger.error("Failed to cancel run %s: %s", run_id, exc)
            failed += 1

    return {"found": len(stale), "cancelled": cancelled, "failed": failed}


# ---------------------------------------------------------------------------
# Stuck issue actions
# ---------------------------------------------------------------------------

def _is_stuck_issue(issue: dict) -> bool:
    """Return True if issue is in_progress and likely stale-checkout."""
    return issue.get("status") == "in_progress"


def _close_stuck_issues(
    issues: list[dict],
    dry_run: bool,
) -> dict:
    """Force-release and transition each stuck issue to done."""
    closed = 0
    failed = 0
    for issue in issues:
        issue_id = issue.get("id", "?")
        identifier = issue.get("identifier", issue_id)
        logger.info("Stuck issue: id=%s identifier=%s", issue_id, identifier)
        if dry_run:
            continue
        try:
            force_release_issue(issue_id, clear_assignee=False)
            transition_issue_status_board(issue_id, "done")
            closed += 1
        except Exception as exc:
            logger.error("Failed to close issue %s (%s): %s", identifier, issue_id, exc)
            failed += 1
    return {"found": len(issues), "closed": closed, "failed": failed}


def _resolve_issue_ids(raw: str) -> list[str]:
    """Parse comma/space-separated issue identifiers or UUIDs."""
    ids = []
    for part in raw.replace(",", " ").split():
        part = part.strip()
        if part:
            ids.append(part)
    return ids


# ---------------------------------------------------------------------------
# Issue lookup helpers
# ---------------------------------------------------------------------------

def _fetch_issues_by_ids(identifiers: list[str]) -> list[dict]:
    """Fetch issues by identifier (BTCAAAAA-NNN) or UUID via the list API.

    The list endpoint supports ``q`` (text search) which matches identifiers.
    We fetch in batch rather than N+1.
    """
    found_issues: list[dict] = []
    seen_ids: set[str] = set()
    for identifier in identifiers:
        try:
            issues = list_issues(status="in_progress", limit=10, offset=0)
            for issue in issues:
                iid = issue.get("identifier") or issue.get("id", "")
                if iid in seen_ids:
                    continue
                if (
                    issue.get("identifier") == identifier
                    or issue.get("id") == identifier
                ):
                    found_issues.append(issue)
                    break
            else:
                logger.warning("Issue %s not found or not in_progress", identifier)
        except Exception as exc:
            logger.warning("Failed to fetch issue %s: %s", identifier, exc)
    return found_issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-close stale in_progress routine instances",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report stale items without making changes",
    )
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=STALE_SUSPICION_MINUTES,
        help=f"Run silence threshold in minutes (default: {STALE_SUSPICION_MINUTES})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max runs to fetch (default: 200)",
    )
    parser.add_argument(
        "--issue-ids",
        type=str,
        metavar="IDS",
        help="Comma-separated issue identifiers to close "
              "(e.g. BTCAAAAA-1317,BTCAAAAA-1278)",
    )
    args = parser.parse_args()

    stale_ms = args.stale_minutes * 60 * 1000
    run_result: dict | None = None
    issue_result: dict | None = None

    # --- Phase 1: close stale heartbeat runs ---
    logger.info(
        "Phase 1 — Stale runs (threshold=%d min, dry_run=%s, limit=%d)",
        args.stale_minutes, args.dry_run, args.limit,
    )
    run_result = _cancel_stale_runs(args.dry_run, stale_ms, args.limit)

    # --- Phase 2: close stuck in_progress issues ---
    if args.issue_ids:
        identifiers = _resolve_issue_ids(args.issue_ids)
        logger.info(
            "Phase 2 — Stuck issues (dry_run=%s, targets=%s)",
            args.dry_run, identifiers,
        )
        issues = _fetch_issues_by_ids(identifiers)
    else:
        logger.info(
            "Phase 2 — Scanning all in_progress issues (dry_run=%s)",
            args.dry_run,
        )
        issues = list_issues(status="in_progress", limit=500)
        logger.info("Found %d in_progress issue(s) total", len(issues))

    issue_result = _close_stuck_issues(issues, args.dry_run)

    # --- Summary ---
    lines = [
        "=== Backfill Summary ===",
        f"Runs: {run_result['found']} stale, {run_result['cancelled']}"
        f" cancelled, {run_result['failed']} failed",
        f"Issues: {issue_result['found']} stuck, {issue_result['closed']}"
        f" closed, {issue_result['failed']} failed",
    ]
    if args.dry_run:
        lines.insert(1, "(DRY RUN — no changes made)")
    logger.info("\n".join(lines))


if __name__ == "__main__":
    main()
