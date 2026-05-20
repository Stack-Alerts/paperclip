#!/usr/bin/env python3
"""Impact Gate polling daemon — 5-min daemon that runs full Impact Gate on done fix issues.

This daemon polls every 5 minutes for fix/bug issues that have recently transitioned
to done status and runs the full Impact Gate (FR acceptance + regression test gates)
on ungated issues, ensuring 100% regression test coverage for all fixes.

Unlike the scan-done verification comment worker, this daemon runs the FULL Impact
Gate including test execution, issue transitions, and blocking issue creation per spec.

Usage:
    python scripts/impact_gate_polling_daemon.py
    python scripts/impact_gate_polling_daemon.py --dry-run
    python scripts/impact_gate_polling_daemon.py --poll-interval 300 --lookback-minutes 10
    python scripts/impact_gate_polling_daemon.py --initial-scan

Environment variables:
    IMPACT_GATE_LOG_DIR: directory for daemon logs (default: ~/.paperclip/impact_gate)
    IMPACT_GATE_POLL_INTERVAL: seconds between polls (default: 300)
    IMPACT_GATE_LOOKBACK_MINUTES: minutes back to scan (default: 10)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

# Only load .env if running locally (not in CI where env vars are pre-set)
if not os.environ.get("PAPERCLIP_API_URL"):
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from touch_index.paperclip_client import (
    _company,
    _paginate,
    _parse_iso_ts,
    fetch_issue_comments,
    get_issue_by_id,
)
from blast_radius.worker import _is_fix_issue
from impact_gate.worker import process_issue
from impact_gate.scan_fix_issues_done import _load_muted_results
import re

# Alias for tests
_load_muted_state = _load_muted_results

# Daemon state directories and files
DAEMON_LOG_DIR = Path(
    os.environ.get(
        "IMPACT_GATE_LOG_DIR",
        Path.home() / ".paperclip" / "impact_gate",
    )
)
DAEMON_LOG_FILE = DAEMON_LOG_DIR / "daemon.log"
DAEMON_STATE_FILE = DAEMON_LOG_DIR / "daemon_state.json"
MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB

# Regex to detect Impact Gate result comments (from worker._build_*_comment)
_GATE_HEADER_RE = re.compile(
    r"^## Impact Gate:\s+(PASS|FAIL|BYPASSED|ERROR|SKIPPED)", re.MULTILINE
)

# Regex to detect scan-done verification comments (from polling_worker)
_SCAN_DONE_RE = re.compile(r"^## Impact Gate — Scan Done", re.MULTILINE)

DAEMON_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging with both file and console
log_handlers = [
    logging.FileHandler(DAEMON_LOG_FILE),
]
if os.isatty(sys.stderr.fileno()):
    log_handlers.append(logging.StreamHandler(sys.stderr))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=log_handlers,
)
logger = logging.getLogger("impact_gate_polling_daemon")


def _rotate_log_if_needed():
    """Rotate log file if it exceeds MAX_LOG_BYTES."""
    if DAEMON_LOG_FILE.exists() and DAEMON_LOG_FILE.stat().st_size > MAX_LOG_BYTES:
        bak = DAEMON_LOG_FILE.with_suffix(".log.1")
        bak.write_text(DAEMON_LOG_FILE.read_text())
        DAEMON_LOG_FILE.write_text("")
        logger.info("Rotated daemon log (size exceeded %d bytes)", MAX_LOG_BYTES)


def _load_daemon_state() -> dict:
    """Load daemon runtime state (processed issues, last run, etc)."""
    if DAEMON_STATE_FILE.exists():
        try:
            return json.loads(DAEMON_STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_poll_utc": None,
        "total_polls": 0,
        "total_gated": 0,
        "total_errors": 0,
        "processed_issues": [],  # Track by ID to avoid re-processing in same cycle
    }


def _save_daemon_state(state: dict):
    """Persist daemon state to disk."""
    DAEMON_STATE_FILE.write_text(json.dumps(state, indent=2))


def _write_data_quality_snapshot(cycle_result: dict) -> None:
    """Write data quality snapshot for Impact Gate scan-done monitoring.

    The snapshot file is used by impact_gate_scan_health.py to verify
    daemon freshness and coverage metrics.
    """
    # Get full list of done fix issues and their gate status
    repo_root = Path(__file__).resolve().parent.parent

    # Fetch all done fix issues to build comprehensive snapshot
    done_issues = _fetch_done_fix_issues(lookback_minutes=None)

    # Load muted results to check gate status
    muted = _load_muted_results()

    # Count gated by status
    gated_by_status = {"pass": 0, "fail": 0, "bypassed": 0, "error": 0, "skipped": 0}
    ungated_count = 0

    for issue in done_issues:
        issue_id = issue.get("id", "")
        if not issue_id:
            continue

        # Check current cycle results first (more up-to-date)
        found_in_cycle = False
        for result in cycle_result.get("results", []):
            if result.get("issue_id") == issue_id:
                gate_status = result.get("gate_status", result.get("reason", "")).lower()
                if result.get("action") == "skipped":
                    reason = result.get("reason", "")
                    if "already_gated" in reason:
                        # Extract status from reason like "already_gated_pass"
                        status_part = reason.split("already_gated_", 1)[-1]
                        # Map "scanned" to "skipped" for consistency
                        if status_part == "scanned":
                            gated_by_status["skipped"] += 1
                        elif status_part in gated_by_status:
                            gated_by_status[status_part] += 1
                        else:
                            gated_by_status["skipped"] += 1
                    else:
                        gated_by_status["skipped"] += 1
                elif result.get("action") == "gated":
                    if gate_status in gated_by_status:
                        gated_by_status[gate_status] += 1
                    else:
                        gated_by_status["skipped"] += 1
                elif result.get("action") == "error":
                    gated_by_status["error"] += 1
                found_in_cycle = True
                break

        # Fall back to muted cache for other issues
        if not found_in_cycle:
            if issue_id in muted:
                status = muted[issue_id].lower()
                # Map unknown statuses (e.g., "scanned") to "skipped"
                if status in gated_by_status:
                    gated_by_status[status] += 1
                else:
                    gated_by_status["skipped"] += 1
            else:
                ungated_count += 1

    total = len(done_issues)
    gated_total = sum(gated_by_status.values())
    coverage_pct = round((gated_total / total * 100), 1) if total > 0 else 0.0

    # Count issues done in last 24h
    last_24h_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    last_24h_count = 0
    for issue in done_issues:
        ts = _parse_iso_ts(issue.get("completedAt"))
        if ts is not None and ts >= last_24h_cutoff:
            last_24h_count += 1

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "impact_gate_scan": {
            "total_done_fix_issues": total,
            "gated": gated_by_status,
            "ungated_count": ungated_count,
            "coverage_pct": coverage_pct,
            "window_days": 7,
            "last_24h": last_24h_count,
        },
    }

    # Write snapshot with today's date
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    snapshot_file = repo_root / f"data_quality_impact_gate_{today}.json"
    snapshot_file.write_text(json.dumps(snapshot, indent=2))

    logger.info(
        "Wrote data quality snapshot: %s (total=%d, gated=%d, ungated=%d, coverage=%.1f%%)",
        snapshot_file.name,
        total,
        gated_total,
        ungated_count,
        coverage_pct,
    )


def _check_gate_status(issue_id: str) -> str | None:
    """Check if issue already has an Impact Gate result or scan-done comment.

    Returns the gate status (PASS, FAIL, BYPASSED, ERROR, SKIPPED) or
    None if no Impact Gate result found.
    Scan-done comments are treated as already-gated (SCANNED marker).
    """
    try:
        comments = fetch_issue_comments(issue_id)
    except Exception as exc:
        logger.warning("Failed to fetch comments for issue %s: %s", issue_id, exc)
        return None

    # Look for gate result comments (newest first, as API returns them)
    for comment in reversed(comments):
        body = comment.get("body", "")
        m = _GATE_HEADER_RE.search(body)
        if m:
            return m.group(1)
        if _SCAN_DONE_RE.search(body):
            return "SCANNED"
    return None


def _fetch_done_fix_issues(lookback_minutes: int | None = 10) -> list[dict]:
    """Fetch fix/bug issues that transitioned to done recently.

    If lookback_minutes is None, returns all done fix issues.
    Otherwise, returns only those completed within the last lookback_minutes.
    """
    issues = _paginate(
        f"/api/companies/{_company()}/issues",
        {"status": "done"},
        page_size=100,
    )

    fix_issues = [i for i in issues if _is_fix_issue(i)]

    if lookback_minutes is None:
        return fix_issues

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    recent = []
    for issue in fix_issues:
        ts = _parse_iso_ts(issue.get("completedAt"))
        if ts is None or ts >= cutoff:
            recent.append(issue)
    return recent


def poll_cycle(
    lookback_minutes: int = 10,
    dry_run: bool = False,
    state: dict | None = None,
) -> dict:
    """Run a single poll cycle: scan for done fix issues and gate ungated ones.

    Args:
        lookback_minutes: How far back to look for recently done issues.
        dry_run: Log results but do not post comments or transition issues.
        state: Daemon state dict (for deduplication within cycle).

    Returns a summary dict with poll results.
    """
    if state is None:
        state = {}

    logger.info("Starting poll cycle (lookback=%dm, dry_run=%s)", lookback_minutes, dry_run)

    issues = _fetch_done_fix_issues(lookback_minutes=lookback_minutes)
    logger.info("Fetched %d recently done fix/bug issue(s)", len(issues))

    results = []
    processed_this_cycle = set()

    for issue in issues:
        issue_id = issue.get("id", "")
        identifier = issue.get("identifier", issue_id)

        if not issue_id:
            continue

        # Skip already-processed in this cycle (dedup)
        if issue_id in processed_this_cycle:
            logger.debug("[skip] Already processed %s this cycle", identifier)
            continue

        # Check if already gated (has a gate result comment)
        gate_status = _check_gate_status(issue_id)
        if gate_status is not None:
            logger.info(
                "[skip] %s already gated with status %s",
                identifier,
                gate_status,
            )
            results.append({
                "issue": identifier,
                "issue_id": issue_id,
                "action": "skipped",
                "reason": f"already_gated_{gate_status.lower()}",
            })
            processed_this_cycle.add(issue_id)
            continue

        # Run the full Impact Gate on the ungated issue
        logger.info("[gate] Running Impact Gate on %s", identifier)
        try:
            # Force retroactive gating for done issues to bypass in_review check
            gate_result = process_issue(issue_id, dry_run=dry_run, force=True)
            gate_status = gate_result.get("gate_status", "UNKNOWN")

            result = {
                "issue": identifier,
                "issue_id": issue_id,
                "action": "gated",
                "gate_status": gate_status,
                "result": gate_result,
            }
            results.append(result)

            logger.info(
                "[gate] Impact Gate for %s completed: %s",
                identifier,
                gate_status,
            )
        except Exception as exc:
            logger.error(
                "[error] Impact Gate failed for %s: %s",
                identifier,
                exc,
                exc_info=True,
            )
            results.append({
                "issue": identifier,
                "issue_id": issue_id,
                "action": "error",
                "error": str(exc),
            })

        processed_this_cycle.add(issue_id)

    # Count outcomes
    gated = sum(1 for r in results if r.get("action") == "gated")
    skipped = sum(1 for r in results if r.get("action") == "skipped")
    errors = sum(1 for r in results if r.get("action") == "error")

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lookback_minutes": lookback_minutes,
        "dry_run": dry_run,
        "issues_found": len(issues),
        "gated": gated,
        "skipped": skipped,
        "errors": errors,
        "results": results,
    }

    logger.info(
        "Poll cycle complete — gated=%d skipped=%d errors=%d",
        gated,
        skipped,
        errors,
    )

    return summary


def daemon_loop(
    poll_interval: int = 300,
    lookback_minutes: int = 10,
    dry_run: bool = False,
) -> None:
    """Run the polling daemon indefinitely.

    Args:
        poll_interval: Seconds to sleep between poll cycles (default: 300 = 5 min).
        lookback_minutes: How far back to look for recently done issues.
        dry_run: Log results but do not post comments or transition issues.
    """
    logger.info(
        "Starting Impact Gate polling daemon (interval=%ds, lookback=%dm, dry_run=%s)",
        poll_interval,
        lookback_minutes,
        dry_run,
    )

    state = _load_daemon_state()
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state["total_polls"] = 0
    state["total_gated"] = 0
    state["total_errors"] = 0
    _save_daemon_state(state)

    while True:
        try:
            _rotate_log_if_needed()

            # Run one poll cycle
            cycle_result = poll_cycle(
                lookback_minutes=lookback_minutes,
                dry_run=dry_run,
                state=state,
            )

            # Write data quality snapshot for monitoring
            _write_data_quality_snapshot(cycle_result)

            # Update daemon state
            state["last_poll_utc"] = datetime.now(timezone.utc).isoformat()
            state["total_polls"] += 1
            state["total_gated"] += cycle_result.get("gated", 0)
            state["total_errors"] += cycle_result.get("errors", 0)
            _save_daemon_state(state)

            # Sleep until next cycle
            logger.debug("Sleeping for %d seconds", poll_interval)
            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down")
            break
        except Exception as exc:
            logger.error(
                "Unhandled error in daemon loop: %s",
                exc,
                exc_info=True,
            )
            # Wait before retrying on unhandled error
            time.sleep(min(poll_interval, 60))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Impact Gate polling daemon — 5-min daemon for full gate coverage",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=int(os.environ.get("IMPACT_GATE_POLL_INTERVAL", 300)),
        metavar="SECONDS",
        help="Seconds between poll cycles (default: 300)",
    )
    parser.add_argument(
        "--lookback-minutes",
        type=int,
        default=int(os.environ.get("IMPACT_GATE_LOOKBACK_MINUTES", 10)),
        metavar="MINUTES",
        help="Minutes back to look for recently done issues (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log results but do not post comments or transition issues",
    )
    parser.add_argument(
        "--initial-scan",
        action="store_true",
        help="Run a single poll cycle immediately, then exit (useful for testing)",
    )
    args = parser.parse_args()

    logger.info("Impact Gate polling daemon started")
    logger.info(
        "Configuration: poll_interval=%ds lookback=%dm dry_run=%s",
        args.poll_interval,
        args.lookback_minutes,
        args.dry_run,
    )

    if args.initial_scan:
        # Run once and exit
        result = poll_cycle(
            lookback_minutes=args.lookback_minutes,
            dry_run=args.dry_run,
        )
        # Write data quality snapshot for monitoring
        if not args.dry_run:
            _write_data_quality_snapshot(result)
        print(json.dumps(result, indent=2, default=str))  # noqa: T201
        return 0 if result.get("errors", 0) == 0 else 1

    # Run daemon loop forever
    try:
        daemon_loop(
            poll_interval=args.poll_interval,
            lookback_minutes=args.lookback_minutes,
            dry_run=args.dry_run,
        )
        return 0
    except Exception as exc:
        logger.error("Daemon failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
