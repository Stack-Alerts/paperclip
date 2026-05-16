"""Impact Gate polling worker — scan done fix/bug issues and run gate verification.

Polls Paperclip for fix/bug issues that have recently transitioned to ``done``
and runs an impact gate check: reads touchedFiles, queries the Blast Radius
Touch Index for impacted FRs and regression bugs, and posts a verification
comment on the issue.

State is deduplicated within each poll cycle using an in-memory set; no
persistent state file is required for the done-issue scan.

Usage
-----
    python -m impact_gate.polling_worker                      # run once, then exit
    python -m impact_gate.polling_worker --dry-run            # log reports, don't post
    python -m impact_gate.polling_worker --daemon             # poll every 300 s forever
    python -m impact_gate.polling_worker --daemon \\
        --poll-interval 60 --lookback-minutes 20              # custom intervals

FIX_LABELS env var (comma-separated): label names that mark an issue as a fix/bug.
Defaults to ``fix,bug,bugfix,regression,hotfix``.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Sequence

from touch_index.paperclip_client import (
    _base,
    _board_session,
    _company,
    _paginate,
    _parse_iso_ts,
    fetch_issue_comments,
    get_issue_by_id,
    is_issue_done,
)
from blast_radius.report import extract_touched_files
from blast_radius.query import query_blast_radius
from blast_radius.worker import _is_fix_issue

log = logging.getLogger(__name__)

FIX_LABELS: set[str] = {
    lbl.strip().lower()
    for lbl in os.environ.get("FIX_LABELS", "fix,bug,bugfix,regression,hotfix").split(",")
    if lbl.strip()
}

PAPERCLIP_RUN_ID = os.environ.get("PAPERCLIP_RUN_ID", "")

# Matches the header produced by _render_gate_comment — used to detect prior runs.
_SCAN_DONE_RE = re.compile(r"^## Impact Gate — Scan Done", re.MULTILINE)


def _run_headers() -> dict[str, str]:
    if PAPERCLIP_RUN_ID:
        return {"X-Paperclip-Run-Id": PAPERCLIP_RUN_ID}
    return {}


def _fetch_done_fix_issues(lookback_minutes: int = 10) -> list[dict]:
    """Return done fix/bug issues completed within the lookback window."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    issues = _paginate(
        f"/api/companies/{_company()}/issues",
        {"status": "done"},
        page_size=100,
    )
    recent = []
    for issue in issues:
        ts = _parse_iso_ts(issue.get("completedAt"))
        if ts is None or ts >= cutoff:
            recent.append(issue)
    return [i for i in recent if _is_fix_issue(i)]


def _has_scan_done_comment(issue_id: str) -> bool:
    """Return True if the issue already has an Impact Gate scan-done comment.

    Used to deduplicate: if a previous worker run already posted the report
    we skip to avoid re-opening a done issue (BTCAAAAA-27486).
    """
    try:
        comments = fetch_issue_comments(issue_id)
        return any(_SCAN_DONE_RE.search(c.get("body", "")) for c in comments)
    except Exception as exc:
        log.warning("Could not check existing comments for %s: %s — proceeding", issue_id, exc)
        return False


def _post_comment(issue_id: str, body: str, dry_run: bool = False) -> bool:
    """Post a comment on the issue.  Returns True on success."""
    if dry_run:
        log.info("[dry-run] Would post to issue %s:\n%s", issue_id, body)
        return True

    try:
        with _board_session() as sess:
            sess.headers.update(_run_headers())
            resp = sess.post(
                f"{_base()}/api/issues/{issue_id}/comments",
                json={"body": body, "idempotencyKey": f"scan-done:{issue_id}"},
                timeout=15,
            )
            resp.raise_for_status()
        return True
    except Exception as exc:
        log.error("[error] Failed to post comment on %s: %s", issue_id, exc)
        return False


def _render_gate_comment(
    identifier: str,
    touched_files: Sequence[str],
    fr_identifiers: list[str],
    bug_identifiers: list[str],
) -> str:
    """Render an Impact Gate verification comment in markdown."""
    file_list = "\n".join(f"- `{f}`" for f in sorted(touched_files)) or "_None_"
    fr_section = (
        "\n".join(f"- [{f}](/{f.split('-')[0]}/issues/{f})" for f in fr_identifiers)
        or "_None_"
    )
    bug_section = (
        "\n".join(f"- [{b}](/{b.split('-')[0]}/issues/{b})" for b in bug_identifiers)
        or "_None_"
    )

    return f"""\
## Impact Gate — Scan Done

**Fix:** [{identifier}](/{identifier.split('-')[0]}/issues/{identifier})

**Touched files:**

{file_list}

### FR Impact Set

{fr_section}

### Regression Risk

{bug_section}

> Verification complete. This issue has been gated retroactively by the Impact Gate scan-done worker.
"""


def process_issue(
    issue_id: str,
    dry_run: bool = False,
) -> dict:
    """Run the impact gate check on a single done fix/bug issue.

    Extracts touched files from the issue description, queries the Blast Radius
    Touch Index for impacted FRs and regression bugs, and posts a verification
    comment.

    Returns a result dict with ``issue``, ``status``, and ``comment_posted``.
    """
    try:
        issue = get_issue_by_id(issue_id)
    except Exception as exc:
        log.error("[error] Failed to fetch issue %s: %s", issue_id, exc)
        return {"issue": issue_id, "status": "error", "comment_posted": False}

    if issue is None:
        log.warning("[skip] Issue %s not found", issue_id)
        return {"issue": issue_id, "status": "not_found", "comment_posted": False}

    identifier = issue.get("identifier", issue_id)

    # Skip done/cancelled issues that already have a scan-done comment to avoid
    # re-opening them via a duplicate comment (BTCAAAAA-27486).
    issue_status = issue.get("status", "")
    if issue_status in ("done", "cancelled") and _has_scan_done_comment(issue_id):
        log.info("[skip] %s already has a scan-done comment — skipping", identifier)
        return {"issue": identifier, "status": "skipped_already_gated", "comment_posted": False}

    description = issue.get("description") or ""

    # Extract touched files
    touched_files = extract_touched_files(description)

    if not touched_files:
        log.info(
            "[skip] No touchedFiles in description for %s — trying git fallback",
            identifier,
        )
        try:
            from touch_index.git_extractor import get_files_for_issue

            touched_files = get_files_for_issue(identifier)
        except Exception as exc:
            log.warning("Git fallback failed for %s: %s", identifier, exc)

    if not touched_files:
        log.info("[skip] No touchedFiles found for %s — skipping gate", identifier)
        return {"issue": identifier, "status": "skipped_no_files", "comment_posted": False}

    # Query Blast Radius Touch Index
    try:
        data = query_blast_radius(list(touched_files))
    except Exception as exc:
        log.error("[error] Blast Radius query failed for %s: %s", identifier, exc)
        return {"issue": identifier, "status": "error", "comment_posted": False}

    fr_identifiers = [fr.fr_identifier for fr in data.fr_impact_set]
    bug_identifiers = [r.bug_identifier for r in data.regression_set]

    log.info(
        "[gate] %s — %d touched file(s), %d FR(s), %d regression bug(s)",
        identifier,
        len(touched_files),
        len(fr_identifiers),
        len(bug_identifiers),
    )

    comment = _render_gate_comment(identifier, touched_files, fr_identifiers, bug_identifiers)
    posted = _post_comment(issue_id, comment, dry_run=dry_run)

    if posted:
        log.info("[posted] Impact gate comment posted for %s", identifier)
    else:
        log.warning("[error] Failed to post comment for %s", identifier)

    return {
        "issue": identifier,
        "status": "gated",
        "comment_posted": posted,
        "fr_count": len(fr_identifiers),
        "bug_count": len(bug_identifiers),
        "touched_files": len(touched_files),
    }


def run_once(
    lookback_minutes: int = 10,
    dry_run: bool = False,
    processed_cache: set[str] | None = None,
) -> dict:
    """Scan for recently done fix/bug issues and run the impact gate on each.

    *processed_cache* is an in-memory set used to deduplicate across calls in
    the same daemon run.  Pass None to start with an empty set for this cycle.

    Returns a summary dict with counts.
    """
    if processed_cache is None:
        processed_cache = set()

    issues = _fetch_done_fix_issues(lookback_minutes=lookback_minutes)
    log.info(
        "Fetched %d recently done fix/bug issue(s) (lookback=%dm)",
        len(issues),
        lookback_minutes,
    )

    results: list[dict] = []
    for issue in issues:
        issue_id = issue.get("id", "")
        identifier = issue.get("identifier", issue_id)

        if not issue_id:
            continue

        if issue_id in processed_cache:
            log.debug("[skip] Already processed %s this cycle", identifier)
            continue

        log.info("Processing %s", identifier)
        result = process_issue(issue_id, dry_run=dry_run)
        results.append(result)
        processed_cache.add(issue_id)

    gated = sum(1 for r in results if r.get("status") == "gated")
    skipped = sum(1 for r in results if r.get("status", "").startswith("skipped"))
    errors = sum(1 for r in results if r.get("status") == "error")

    log.info(
        "Cycle complete — gated=%d skipped=%d errors=%d",
        gated,
        skipped,
        errors,
    )
    return {"gated": gated, "skipped": skipped, "errors": errors, "results": results}


def run_loop(
    poll_interval: int = 300,
    lookback_minutes: int = 10,
    dry_run: bool = False,
) -> None:
    """Poll continuously, sleeping *poll_interval* seconds between runs."""
    log.info(
        "Starting Impact Gate scan-done loop (interval=%ds, lookback=%dm, dry_run=%s)",
        poll_interval,
        lookback_minutes,
        dry_run,
    )
    processed_cache: set[str] = set()
    while True:
        try:
            run_once(
                lookback_minutes=lookback_minutes,
                dry_run=dry_run,
                processed_cache=processed_cache,
            )
        except Exception as exc:
            log.error("Worker iteration failed: %s", exc)
        time.sleep(poll_interval)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Impact Gate scan-done worker — poll for done fix/bug issues and run gate."
    )
    p.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously (poll loop) instead of once.",
    )
    p.add_argument(
        "--poll-interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Seconds between poll cycles in daemon mode (default: 300).",
    )
    p.add_argument(
        "--lookback-minutes",
        type=int,
        default=10,
        metavar="MINUTES",
        help="How far back to look for recently done issues (default: 10).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Log reports but do not post comments.",
    )
    p.add_argument(
        "--issue-id",
        metavar="UUID",
        help="Process a single issue by UUID (skip polling).",
    )
    return p.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = _parse_args()

    if args.issue_id:
        result = process_issue(args.issue_id, dry_run=args.dry_run)
        log.info("Result: %s", result)
        return 0 if result.get("status") not in ("error",) else 1

    if args.daemon:
        run_loop(
            poll_interval=args.poll_interval,
            lookback_minutes=args.lookback_minutes,
            dry_run=args.dry_run,
        )
        return 0

    summary = run_once(
        lookback_minutes=args.lookback_minutes,
        dry_run=args.dry_run,
    )
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
