"""Blast Radius polling worker — detect fix→in_review transitions and post reports.

Polls Paperclip for fix/bug issues that have transitioned to ``in_review``
since the last run, generates a Blast Radius Report for each, and posts it
as a comment.

Transition detection is explicit: the worker tracks the last-known status of
each issue in the state file and only generates reports when the previous
status was *not* ``in_review``.  This avoids re-processing issues that were
already ``in_review`` during a prior poll cycle.

A ``process_issue()`` entry point is provided for event-driven use: call it
with an issue ID and optional ``old_status`` (from a Paperclip webhook
payload) to process a single issue on demand.

State is persisted in a JSON file so the worker is safe to restart.

Usage
-----
    python -m blast_radius.worker                         # run once, then exit
    python -m blast_radius.worker --issue-id <uuid>       # process a single issue
    python -m blast_radius.worker --issue-id <uuid> --old-status in_progress
    python -m blast_radius.worker --loop 120              # poll every 120 s forever
    python -m blast_radius.worker --dry-run               # log reports, don't post
    python -m blast_radius.worker --force-reprocess       # re-process already-seen issues

FIX_LABELS env var (comma-separated): label names that mark an issue as a fix/bug.
Defaults to ``fix,bug,bugfix``.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from touch_index.paperclip_client import (
    _paginate,
    _base,
    _company,
)

from .generator import generate_and_post

log = logging.getLogger(__name__)

FIX_LABELS = {
    lbl.strip().lower()
    for lbl in os.environ.get("FIX_LABELS", "fix,bug,bugfix").split(",")
    if lbl.strip()
}

_STATE_PATH = Path(
    os.environ.get(
        "BLAST_RADIUS_STATE_FILE",
        Path(__file__).resolve().parents[2] / "data" / "blast_radius_worker_state.json",
    )
)


def _load_state() -> dict:
    """Load persisted state or return defaults.

    State shape::

        {
            "processed_issue_ids": ["<uuid>", ...],
            "issue_statuses": {"<uuid>": "in_review", ...},
        }
    """
    if _STATE_PATH.exists():
        try:
            data = json.loads(_STATE_PATH.read_text())
            if "issue_statuses" not in data:
                data["issue_statuses"] = {}
            if "processed_issue_ids" not in data:
                data["processed_issue_ids"] = []
            return data
        except Exception:
            pass
    return {"processed_issue_ids": [], "issue_statuses": {}}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2))


def _fetch_in_review_issues() -> list[dict]:
    """Return all ``in_review`` issues from the company (paginated)."""
    return _paginate(
        f"/api/companies/{_company()}/issues",
        {"status": "in_review"},
        page_size=100,
    )


def _is_fix_issue(issue: dict) -> bool:
    """Return True if the issue looks like a fix or bug."""
    labels = issue.get("labels") or []
    for lbl in labels:
        name = (lbl.get("name") or "").lower()
        if name in FIX_LABELS:
            return True
    title_lower = (issue.get("title") or "").lower()
    return any(kw in title_lower for kw in ("fix", "bug", "regression", "hotfix"))


def _detect_transitions(
    state: dict,
    issues: list[dict],
) -> list[dict]:
    """From *issues*, return those that transitioned TO ``in_review``.

    An issue is considered a new transition when its *previous known status*
    (from the state file) was *not* ``in_review``.  Never-seen-before issues
    are included as transitions.
    """
    known: dict[str, str] = state.get("issue_statuses", {})
    return [i for i in issues if known.get(i.get("id", "")) != "in_review"]


def _sync_statuses(state: dict, issues: list[dict]) -> None:
    """Bulk-update the ``issue_statuses`` map from a list of fetched issues."""
    statuses = state.setdefault("issue_statuses", {})
    for issue in issues:
        issue_id = issue.get("id", "")
        status = issue.get("status", "")
        if issue_id and status:
            statuses[issue_id] = status

def run_once(dry_run: bool = False, force_reprocess: bool = False) -> list[dict]:
    """Detect fix/bug issues that transitioned TO ``in_review`` and post reports.

    Compared to the earlier approach (which processed every unprocessed
    ``in_review`` issue), this version uses explicit transition detection:
    the state file's ``issue_statuses`` map is compared against the current
    fetch to identify issues that genuinely moved to ``in_review`` since the
    last poll.

    When *force_reprocess* is True, status tracking is overridden and all
    ``in_review`` fix issues are processed (regardless of previous status).
    """
    state = _load_state()
    processed: set[str] = set(state.get("processed_issue_ids", []))

    issues = _fetch_in_review_issues()
    log.info("Fetched %d in_review issues", len(issues))

    fix_issues = [i for i in issues if _is_fix_issue(i)]

    if force_reprocess:
        candidates = fix_issues
    else:
        candidates = _detect_transitions(state, fix_issues)

    if force_reprocess:
        log.info(
            "Force-reprocess: %d fix/bug issues in_review",
            len(candidates),
        )
    else:
        log.info(
            "Detected %d fix->in_review transition(s) (out of %d fix issues)",
            len(candidates),
            len(fix_issues),
        )

    results = []
    newly_processed: list[str] = []

    for issue in candidates:
        issue_id = issue.get("id", "")
        identifier = issue.get("identifier", "")

        if not force_reprocess and issue_id in processed:
            log.debug(
                "Already processed %s -- skipping (use --force-reprocess to override)",
                identifier,
            )
            continue

        log.info(
            "Generating Blast Radius Report for %s (fix->in_review)",
            identifier,
        )
        try:
            result = generate_and_post(issue_id, dry_run=dry_run)
            results.append(result)
            newly_processed.append(issue_id)

        except Exception as exc:
            log.error("Failed to generate report for %s: %s", identifier, exc)
            results.append({"issue": identifier, "error": str(exc)})

    _sync_statuses(state, issues)

    if newly_processed and not dry_run:
        state["processed_issue_ids"] = list(processed | set(newly_processed))
        _save_state(state)
        log.info("Marked %d issues as processed", len(newly_processed))

    return results


def process_issue(
    issue_id: str,
    dry_run: bool = False,
    old_status: str | None = None,
    force_reprocess: bool = False,
) -> dict | None:
    """Process a single issue (webhook entry point).

    When called from a Paperclip ``issue_status_changed`` webhook, the caller
    should pass the previous status via *old_status* for logging and audit
    purposes.

    The function fetches the current issue state from the Paperclip API and
    validates that the issue is ``in_review`` and carries a fix/bug label
    before generating the report.

    When *force_reprocess* is True, the already-processed guard is bypassed
    so the issue report is regenerated even if previously processed.
    """
    try:
        issue = _get_issue(issue_id)
    except Exception as exc:
        log.error("Failed to fetch issue %s: %s", issue_id, exc)
        return {"issue": issue_id, "error": f"fetch failed: {exc}"}

    identifier = issue.get("identifier", issue_id)
    status = issue.get("status", "")

    if status != "in_review":
        log.info(
            "%s has status=%r (not in_review) -- skipping", identifier, status
        )
        return None

    if old_status:
        log.info(
            "%s transitioned %r -> in_review (webhook)",
            identifier,
            old_status,
        )
    else:
        log.info("%s is in_review (webhook, no old_status provided)", identifier)

    if not _is_fix_issue(issue):
        log.info("%s is not a fix/bug issue -- skipping", identifier)
        return None

    # Pre-check: skip if already processed (prevents duplicate webhook processing)
    state = _load_state()
    processed: set[str] = set(state.get("processed_issue_ids", []))
    if issue_id in processed:
        if force_reprocess:
            log.info("%s already processed -- force-reprocessing", identifier)
        else:
            log.info("%s already processed -- skipping (webhook dedup)", identifier)
            return None

    log.info("Generating Blast Radius Report for %s (webhook trigger)", identifier)
    try:
        result = generate_and_post(issue_id, dry_run=dry_run)

        if not dry_run:
            if issue_id not in processed:
                state["processed_issue_ids"] = list(processed | {issue_id})
            statuses = state.setdefault("issue_statuses", {})
            statuses[issue_id] = status
            _save_state(state)

        return result
    except Exception as exc:
        log.error("Failed to generate report for %s: %s", identifier, exc)
        return {"issue": identifier, "error": str(exc)}


def _get_issue(issue_id: str) -> dict:
    from touch_index.paperclip_client import _session

    with _session() as sess:
        resp = sess.get(f"{_base()}/api/issues/{issue_id}", timeout=15)
        resp.raise_for_status()
        return resp.json()


def run_loop(
    interval_seconds: int = 120, dry_run: bool = False, force_reprocess: bool = False
) -> None:
    """Poll continuously, sleeping *interval_seconds* between runs."""
    log.info(
        "Starting Blast Radius worker loop (interval=%ds, dry_run=%s, force_reprocess=%s)",
        interval_seconds,
        dry_run,
        force_reprocess,
    )
    while True:
        try:
            run_once(dry_run=dry_run, force_reprocess=force_reprocess)
        except Exception as exc:
            log.error("Worker iteration failed: %s", exc)
        time.sleep(interval_seconds)


def main() -> None:
    """CLI entry point: parse args and dispatch to process_issue / run_loop / run_once."""
    import argparse

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Blast Radius polling worker + webhook handler"
    )
    parser.add_argument(
        "--issue-id", type=str, metavar="UUID",
        help="Process a single issue by Paperclip UUID (webhook trigger)",
    )
    parser.add_argument(
        "--old-status", type=str, metavar="STATUS",
        help="Previous status when called from a status-change webhook",
    )
    parser.add_argument(
        "--loop", type=int, metavar="SECONDS",
        help="Run in a loop with this interval",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Log reports but do not post comments",
    )
    parser.add_argument(
        "--force-reprocess", action="store_true",
        help="Re-process already-seen issues (bypasses transition detection)",
    )
    args = parser.parse_args()

    if args.issue_id:
        result = process_issue(
            args.issue_id,
            dry_run=args.dry_run,
            old_status=args.old_status,
            force_reprocess=args.force_reprocess,
        )
        if result:
            log.info("Result: %s", json.dumps(result, indent=2))
        else:
            log.info("No report generated (issue not eligible)")
    elif args.loop:
        run_loop(
            interval_seconds=args.loop,
            dry_run=args.dry_run,
            force_reprocess=args.force_reprocess,
        )
    else:
        results = run_once(dry_run=args.dry_run, force_reprocess=args.force_reprocess)
        log.info("Results: %s", json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
