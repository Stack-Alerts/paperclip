"""Blast Radius polling worker.

Polls Paperclip for fix/bug issues that have transitioned to `in_review` since
the last run, generates a Blast Radius Report for each, and posts it as a comment.

State is persisted in a JSON file so the worker is safe to restart.

Usage
-----
    python -m blast_radius.worker                 # run once, then exit
    python -m blast_radius.worker --loop 120      # poll every 120 s forever
    python -m blast_radius.worker --dry-run             # log reports, don't post
    python -m blast_radius.worker --force-reprocess  # re-process already-seen issues

FIX_LABELS env var (comma-separated): label names that mark an issue as a fix/bug.
Defaults to "fix,bug,bugfix".
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from touch_index.paperclip_client import _paginate, _base, _company

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
    if _STATE_PATH.exists():
        try:
            return json.loads(_STATE_PATH.read_text())
        except Exception:
            pass
    return {"processed_issue_ids": []}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2))


def _fetch_in_review_issues() -> list[dict]:
    """Return all `in_review` issues from the company (paginated)."""
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


def run_once(dry_run: bool = False, force_reprocess: bool = False) -> list[dict]:
    """Process fix/bug issues in_review. Returns list of result dicts.

    When *force_reprocess* is True, already-processed issues are re-processed
    and their reports are regenerated (useful when touchedFiles have been
    updated after the initial run).
    """
    state = _load_state()
    processed: set[str] = set(state.get("processed_issue_ids", []))

    issues = _fetch_in_review_issues()
    log.info("Fetched %d in_review issues", len(issues))

    results = []
    newly_processed: list[str] = []

    for issue in issues:
        issue_id = issue.get("id", "")
        identifier = issue.get("identifier", "")

        if not force_reprocess and issue_id in processed:
            log.debug(
                "Already processed %s — skipping (use --force-reprocess to override)",
                identifier,
            )
            continue

        if not _is_fix_issue(issue):
            log.debug("%s is not a fix/bug issue — skipping", identifier)
            continue

        log.info("Generating Blast Radius Report for %s", identifier)
        try:
            result = generate_and_post(issue_id, dry_run=dry_run)
            results.append(result)
            newly_processed.append(issue_id)
        except Exception as exc:
            log.error("Failed to generate report for %s: %s", identifier, exc)
            results.append({"issue": identifier, "error": str(exc)})

    if newly_processed and not dry_run:
        state["processed_issue_ids"] = list(processed | set(newly_processed))
        _save_state(state)
        log.info("Marked %d issues as processed", len(newly_processed))

    return results


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


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    parser = argparse.ArgumentParser(description="Blast Radius polling worker")
    parser.add_argument(
        "--loop", type=int, metavar="SECONDS", help="Run in a loop with this interval"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log reports but do not post comments"
    )
    parser.add_argument(
        "--force-reprocess", action="store_true", help="Re-process already-seen issues"
    )
    args = parser.parse_args()

    if args.loop:
        run_loop(
            interval_seconds=args.loop,
            dry_run=args.dry_run,
            force_reprocess=args.force_reprocess,
        )
    else:
        results = run_once(dry_run=args.dry_run, force_reprocess=args.force_reprocess)
        log.info("Results: %s", json.dumps(results, indent=2))
