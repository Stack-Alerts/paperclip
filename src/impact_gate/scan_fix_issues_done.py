"""Scan for done fix/bug issues and track Impact Gate coverage.

Polls Paperclip for fix/bug issues that are in "done" status, checks whether
each has been processed by the Impact Gate (via muted gate results cache),
and optionally runs the gate retroactively on ungated issues.

State is persisted in a JSON file keyed by issue ID, storing the last-known
gate status (PASS, FAIL, ERROR, BYPASSED, SKIPPED). This prevents re-gating
the same issue multiple times.

Usage
-----
    python -m impact_gate.scan_fix_issues_done           # scan once, report
    python -m impact_gate.worker --poll --days-back 7    # scan last 7 days
    python -m impact_gate.worker --poll --retroactive    # run gate on ungated
    python -m impact_gate.worker --poll --retry-errors   # clear error entries
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from touch_index.paperclip_client import (
    _paginate,
    _company,
    fetch_issue_comments,
)

log = logging.getLogger(__name__)

FIX_LABELS = {
    lbl.strip().lower()
    for lbl in os.environ.get("FIX_LABELS", "fix,bug,bugfix,regression,hotfix").split(
        ","
    )
    if lbl.strip()
}

_STATE_PATH = Path(
    os.environ.get(
        "IMPACT_GATE_MUTED_RESULTS_FILE",
        Path(__file__).resolve().parents[2] / ".impact_gate_muted_state.json",
    )
)

# Exported for lazy import by worker.py (to avoid circular dependency)
_MUTED_STATE_PATH = _STATE_PATH


def _load_muted_results() -> dict[str, str]:
    """Load persisted muted gate results.

    Returns a dict mapping issue_id -> gate_status (PASS, FAIL, ERROR, etc).
    Muted results are issues that have already been gated and should not be
    re-gated unless explicitly retried.
    """
    if _MUTED_STATE_PATH.exists():
        try:
            data = json.loads(_MUTED_STATE_PATH.read_text())
            if isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
                return data
        except Exception as exc:
            log.warning("Failed to load muted results: %s", exc)
    return {}


# Alias for worker.py lazy import compatibility
_load_muted_state = _load_muted_results


def _save_muted_results(results: dict[str, str]) -> None:
    """Persist muted gate results."""
    _MUTED_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MUTED_STATE_PATH.write_text(json.dumps(results, indent=2))


def save_muted_gate_result(issue_id: str, status: str) -> None:
    """Record a gate result so the issue is not re-gated in future scans."""
    results = _load_muted_results()
    results[issue_id] = status
    _save_muted_results(results)
    log.debug("Saved muted gate result for %s: %s", issue_id, status)


def purge_muted_entries(status: str | None = None) -> int:
    """Purge muted cache entries.

    If status is provided, removes all entries with that status.
    If status is None, clears the entire cache.

    Returns the number of entries removed.
    """
    results = _load_muted_results()
    before_count = len(results)

    if status is None:
        results.clear()
    else:
        results = {k: v for k, v in results.items() if v != status}

    _save_muted_results(results)
    removed = before_count - len(results)
    log.debug("Purged %d muted entries (status=%s)", removed, status)
    return removed


def _check_gate_status(issue_id: str) -> str | None:
    """Check if issue already has an Impact Gate result (cache-first, then comments).

    Returns the gate status (PASS, FAIL, BYPASSED, ERROR, SKIPPED, SCANNED) or
    None if no result found.
    """
    # Check muted cache first
    muted = _load_muted_state()
    if issue_id in muted:
        return muted[issue_id]

    # Fall back to checking comments for gate result markers
    try:
        comments = fetch_issue_comments(issue_id)
        import re
        _GATE_HEADER_RE = re.compile(
            r"^## Impact Gate:\s+(PASS|FAIL|BYPASSED|ERROR|SKIPPED)", re.MULTILINE
        )
        for comment in reversed(comments):
            body = comment.get("body", "")
            m = _GATE_HEADER_RE.search(body)
            if m:
                return m.group(1)
            # Also detect scan-done verification comments
            if re.search(r"^## Impact Gate — Scan Done", body, re.MULTILINE):
                return "SCANNED"
    except Exception:
        pass
    return None


def process_issue(issue_id: str, dry_run: bool = False, force: bool = False) -> dict:
    """Run the Impact Gate for a single issue (wrapper for testing).

    This function is defined at module level to allow test monkeypatching.
    It delegates to worker.process_issue().
    """
    from . import worker
    return worker.process_issue(issue_id, dry_run=dry_run, force=force)


def _is_fix_issue(issue: dict) -> bool:
    """Return True if the issue looks like a fix or bug."""
    labels = issue.get("labels") or []
    for lbl in labels:
        name = (lbl.get("name") or "").strip().lower()
        if name in FIX_LABELS:
            return True
    title = issue.get("title") or ""
    return title and any(
        title.lower().startswith(prefix)
        for prefix in ("fix", "bug", "bugfix", "regression", "hotfix")
    )


def _is_recent(issue: dict, days_back: int) -> bool:
    """Check if issue was completed within the last N days."""
    if days_back is None:
        return True

    # Get the completed timestamp from the issue (falls back to updatedAt)
    timestamp = issue.get("completedAt") or issue.get("updatedAt")
    if not timestamp:
        return True  # Assume issues are in scope if no timestamp

    try:
        # Parse ISO 8601 timestamp
        if isinstance(timestamp, str):
            # Handle both "2026-05-16T12:34:56Z" and datetime objects
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1]
            timestamp_dt = datetime.fromisoformat(timestamp)
        else:
            timestamp_dt = timestamp

        cutoff = datetime.utcnow() - timedelta(days=days_back)
        return timestamp_dt >= cutoff
    except Exception as exc:
        log.warning("Failed to parse issue timestamp: %s", exc)
        return False  # Exclude issues with unparseable timestamps when days_back is set


def _fetch_done_issues(days_back: int | None = None) -> list[dict]:
    """Return all "done" fix/bug issues from the company (paginated)."""
    issues = _paginate(
        f"/api/companies/{_company()}/issues",
        {"status": "done"},
        page_size=100,
    )
    fix_issues = [i for i in issues if _is_fix_issue(i)]
    if days_back is not None:
        fix_issues = [i for i in fix_issues if _is_recent(i, days_back)]
    return fix_issues


def scan(
    days_back: int | None = None,
    dry_run: bool = False,
    retroactive: bool = False,
    retry_errors: bool = False,
    retry_fails: bool = False,
) -> dict:
    """Scan done fix/bug issues and optionally run Impact Gate retroactively.

    Parameters
    ----------
    days_back : int, optional
        Only include issues completed in the last N days.
    dry_run : bool
        Log results but do not save muted entries or run gates.
    retroactive : bool
        Run Impact Gate on ungated issues.
    retry_errors : bool
        Clear ERROR entries from muted cache before scanning.
    retry_fails : bool
        Clear FAIL entries from muted cache before scanning.

    Returns
    -------
    dict
        Report with keys:
        - timestamp: ISO 8601 timestamp of scan
        - total_done_fix_issues: count of done fix/bug issues
        - gated: count of gated issues (muted)
        - ungated_count: count of ungated issues
        - last_24h: count of issues done in last 24h
        - retroactive_results: list of gate results (if retroactive=True)
    """
    log.info(
        "Scanning done fix/bug issues (days_back=%s, retroactive=%s, retry_errors=%s, retry_fails=%s)",
        days_back,
        retroactive,
        retry_errors,
        retry_fails,
    )

    # Load and optionally clean muted results
    muted = _load_muted_results()
    if retry_errors:
        before = len(muted)
        muted = {k: v for k, v in muted.items() if v != "ERROR"}
        after = len(muted)
        log.info("Cleared %d ERROR entries from muted cache", before - after)
    if retry_fails:
        before = len(muted)
        muted = {k: v for k, v in muted.items() if v != "FAIL"}
        after = len(muted)
        log.info("Cleared %d FAIL entries from muted cache", before - after)

    if not dry_run:
        _save_muted_results(muted)

    # Fetch done issues
    done_issues = _fetch_done_issues(days_back)
    log.info("Found %d done fix/bug issues", len(done_issues))

    # Count gated vs. ungated and break down gated by status
    gated_by_status = {"pass": 0, "fail": 0, "bypassed": 0, "error": 0, "skipped": 0, "scanned": 0}
    ungated_issues = []
    for issue in done_issues:
        issue_id = issue.get("id", "")
        if not issue_id:
            continue
        gate_status = _check_gate_status(issue_id)
        if gate_status is not None:
            status = gate_status.lower()
            # Map gate status to the expected keys
            if status == "pass":
                gated_by_status["pass"] += 1
            elif status == "fail":
                gated_by_status["fail"] += 1
            elif status == "bypassed":
                gated_by_status["bypassed"] += 1
            elif status == "error":
                gated_by_status["error"] += 1
            elif status == "skipped":
                gated_by_status["skipped"] += 1
            elif status == "scanned":
                gated_by_status["scanned"] += 1
            else:
                # Unknown status, count as skipped
                gated_by_status["skipped"] += 1
            gated_by_status["scanned"] += 1
        else:
            ungated_issues.append(issue)

    gated_count = sum(v for k, v in gated_by_status.items() if k != "scanned")
    ungated_count = len(ungated_issues)
    log.info(
        "Gated: %d (%s), Ungated: %d (out of %d done issues)",
        gated_count,
        gated_by_status,
        ungated_count,
        len(done_issues),
    )

    # Count last 24h for metrics
    last_24h_count = sum(1 for i in done_issues if _is_recent(i, 1))

    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_done_fix_issues": len(done_issues),
        "gated": gated_by_status,
        "ungated_count": ungated_count,
        "ungated_issues": ungated_issues,
        "last_24h": last_24h_count,
        "days_back": days_back,
        "dry_run": dry_run,
    }

    # Optionally run retroactive gates on ungated issues (skip in dry_run mode)
    if retroactive and ungated_issues and not dry_run:
        log.info("Running retroactive Impact Gate on %d ungated issues", ungated_count)

        retroactive_results = []
        for issue in ungated_issues:
            issue_id = issue.get("id", "")
            identifier = issue.get("identifier", issue_id)
            try:
                gate_result = process_issue(issue_id, dry_run=dry_run, force=True)
                gate_status = gate_result.get("gate_status", "ERROR")
                retroactive_results.append({
                    "issue": identifier,
                    "gate_status": gate_status,
                })
                log.info(
                    "Retroactive gate for %s: %s",
                    identifier,
                    gate_status,
                )
            except Exception as exc:
                log.error("Retroactive gate failed for %s: %s", identifier, exc)
                retroactive_results.append({
                    "issue": identifier,
                    "gate_status": "ERROR",
                    "error": str(exc),
                })

        result["retroactive_results"] = retroactive_results

    return result


def main() -> None:
    """Main entry point for the scan utility."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scan done fix/bug issues for Impact Gate coverage",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=None,
        metavar="N",
        help="Only scan issues completed within the last N days (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log results but do not save muted entries",
    )
    parser.add_argument(
        "--retroactive",
        action="store_true",
        help="Run Impact Gate retroactively on ungated issues",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Purge ERROR entries from muted cache before scanning",
    )
    parser.add_argument(
        "--retry-fails",
        action="store_true",
        help="Purge FAIL entries from muted cache before scanning",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON report to stdout",
    )

    args = parser.parse_args()

    report = scan(
        days_back=args.days_back,
        dry_run=args.dry_run,
        retroactive=args.retroactive,
        retry_errors=args.retry_errors,
        retry_fails=args.retry_fails,
    )

    if args.json:
        print(json.dumps(report, default=str))  # noqa: T201
    else:
        print(json.dumps(report, indent=2, default=str))  # noqa: T201


if __name__ == "__main__":
    main()
