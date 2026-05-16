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
        Path(__file__).resolve().parents[2] / "data" / "impact_gate_muted_results.json",
    )
)


def _load_muted_results() -> dict[str, str]:
    """Load persisted muted gate results.

    Returns a dict mapping issue_id -> gate_status (PASS, FAIL, ERROR, etc).
    Muted results are issues that have already been gated and should not be
    re-gated unless explicitly retried.
    """
    if _STATE_PATH.exists():
        try:
            data = json.loads(_STATE_PATH.read_text())
            if isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
                return data
        except Exception as exc:
            log.warning("Failed to load muted results: %s", exc)
    return {}


def _save_muted_results(results: dict[str, str]) -> None:
    """Persist muted gate results."""
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(results, indent=2))


def save_muted_gate_result(issue_id: str, status: str) -> None:
    """Record a gate result so the issue is not re-gated in future scans."""
    results = _load_muted_results()
    results[issue_id] = status
    _save_muted_results(results)
    log.debug("Saved muted gate result for %s: %s", issue_id, status)


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

    # Get the completed timestamp from the issue
    updated_at = issue.get("updatedAt")
    if not updated_at:
        return True  # Assume old issues are in scope if no timestamp

    try:
        # Parse ISO 8601 timestamp
        if isinstance(updated_at, str):
            # Handle both "2026-05-16T12:34:56Z" and datetime objects
            if updated_at.endswith("Z"):
                updated_at = updated_at[:-1]
            updated_dt = datetime.fromisoformat(updated_at)
        else:
            updated_dt = updated_at

        cutoff = datetime.utcnow() - timedelta(days=days_back)
        return updated_dt >= cutoff
    except Exception as exc:
        log.warning("Failed to parse issue timestamp: %s", exc)
        return True


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

    # Count gated vs. ungated
    gated_count = 0
    ungated_issues = []
    for issue in done_issues:
        issue_id = issue.get("id", "")
        if not issue_id:
            continue
        if issue_id in muted:
            gated_count += 1
        else:
            ungated_issues.append(issue)

    ungated_count = len(ungated_issues)
    log.info(
        "Gated: %d, Ungated: %d (out of %d done issues)",
        gated_count,
        ungated_count,
        len(done_issues),
    )

    # Count last 24h for metrics
    last_24h_count = sum(1 for i in done_issues if _is_recent(i, 1))

    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_done_fix_issues": len(done_issues),
        "gated": gated_count,
        "ungated_count": ungated_count,
        "last_24h": last_24h_count,
    }

    # Optionally run retroactive gates on ungated issues
    if retroactive and ungated_issues:
        log.info("Running retroactive Impact Gate on %d ungated issues", ungated_count)
        from . import worker

        retroactive_results = []
        for issue in ungated_issues:
            issue_id = issue.get("id", "")
            identifier = issue.get("identifier", issue_id)
            try:
                gate_result = worker.process_issue(issue_id, dry_run=dry_run, force=True)
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


if __name__ == "__main__":
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
