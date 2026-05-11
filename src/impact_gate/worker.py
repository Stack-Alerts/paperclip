"""Impact Gate polling worker — run FR acceptance + bug regression gates on in_review issues.

Polls Paperclip for issues that have transitioned to ``in_review``, extracts
FR IDs and bug IDs from issue labels/metadata, runs the Impact Gate test suite
via ``impact_gate_runner.run()``, and posts a structured result comment.

Issues whose gate result is ``PASS`` are transitioned to ``done``.
Issues that fail remain ``in_review`` with a comment detailing failures.

State is persisted in ``IMPACT_GATE_STATE_FILE`` (defaults to
``data/impact_gate_worker_state.json``) so the worker is safe to restart.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from touch_index.paperclip_client import (
    _paginate,
    _base,
    _company,
    _session,
    transition_issue_status,
)

from impact_gate_runner import run as run_impact_gate

log = logging.getLogger(__name__)

FDR_LABEL_ID = "d523cb2d-acd9-423d-b87a-bb79cee42c40"

FIX_LABELS = {
    lbl.strip().lower()
    for lbl in os.environ.get("FIX_LABELS", "fix,bug,bugfix").split(",")
    if lbl.strip()
}

_STATE_PATH = Path(
    os.environ.get(
        "IMPACT_GATE_STATE_FILE",
        Path(__file__).resolve().parents[2] / "data" / "impact_gate_worker_state.json",
    )
)


def _load_state() -> dict:
    if _STATE_PATH.exists():
        try:
            data = json.loads(_STATE_PATH.read_text())
            if "processed_issue_ids" not in data:
                data["processed_issue_ids"] = []
            if "issue_statuses" not in data:
                data["issue_statuses"] = {}
            return data
        except Exception:
            pass
    return {"processed_issue_ids": [], "issue_statuses": {}}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2))


def _fetch_in_review_issues() -> list[dict]:
    return _paginate(
        f"/api/companies/{_company()}/issues",
        {"status": "in_review"},
        page_size=100,
    )


def _extract_fr_ids_from_labels(issue: dict) -> list[str]:
    """Extract FDR-NNN identifiers from issue labels."""
    labels = issue.get("labels") or []
    fr_ids: list[str] = []
    for lbl in labels:
        name = lbl.get("name", "")
        m = re.fullmatch(r"FDR-(\d+)", name, re.IGNORECASE)
        if m:
            fr_ids.append(f"FDR-{m.group(1)}")
    return fr_ids


def _has_fdr_label(issue: dict) -> bool:
    label_ids = issue.get("labelIds") or []
    return FDR_LABEL_ID in label_ids


def _is_fix_issue(issue: dict) -> bool:
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
    known: dict[str, str] = state.get("issue_statuses", {})
    return [i for i in issues if known.get(i.get("id", "")) != "in_review"]


def _sync_statuses(state: dict, issues: list[dict]) -> None:
    statuses = state.setdefault("issue_statuses", {})
    for issue in issues:
        issue_id = issue.get("id", "")
        status = issue.get("status", "")
        if issue_id and status:
            statuses[issue_id] = status


def _post_comment(issue_id: str, body: str) -> None:
    with _session() as sess:
        resp = sess.post(
            f"{_base()}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=30,
        )
        resp.raise_for_status()
        log.info("Posted gate result comment to %s", issue_id)


def _build_results_comment(
    identifier: str,
    result: dict,
    fr_ids: list[str],
    bug_ids: list[str],
) -> str:
    status = result.get("status", "ERROR")
    summary = result.get("summary", {})
    lines: list[str] = [
        f"## Impact Gate Result: {status}",
        "",
        f"Issue: **{identifier}**",
        f"Status: **{status}**",
        "",
        "### Summary",
        f"- Total tests: {summary.get('total', 0)}",
        f"- Passed: {summary.get('passed', 0)}",
        f"- Failed: {summary.get('failed', 0)}",
        f"- Errors: {summary.get('errors', 0)}",
        f"- Missing test files: {summary.get('missing_test_files', 0)}",
        "",
    ]

    if fr_ids:
        lines.append("### FR Acceptance Results")
        fr_results = result.get("fr_results", {})
        for fid in fr_ids:
            fr = fr_results.get(fid, {})
            lines.append(f"- **{fid}**: {fr.get('status', 'UNKNOWN')}")
        lines.append("")

    if bug_ids:
        lines.append("### Bug Regression Results")
        bug_results = result.get("bug_results", {})
        for bid in bug_ids:
            br = bug_results.get(bid, {})
            lines.append(f"- **{bid}**: {br.get('status', 'UNKNOWN')}")
        lines.append("")

    if status == "FAIL":
        lines.append("### Failures")
        for group_key in ("fr_results", "bug_results"):
            group = result.get(group_key, {})
            for tid, entry in group.items():
                if entry.get("status") == "FAIL":
                    for t in entry.get("tests", []):
                        if t.get("outcome") in ("failed", "error"):
                            lines.append(f"- `{t.get('nodeid', '')}`")
                            msg = t.get("message", "")
                            if msg:
                                lines.append(f"  ```\n  {msg}\n  ```")
        lines.append("")

    return "\n".join(lines)


def _get_issue(issue_id: str) -> dict:
    sess = _session()
    resp = sess.get(f"{_base()}/api/issues/{issue_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def process_issue(
    issue_id: str,
    dry_run: bool = False,
    old_status: str | None = None,
) -> dict | None:
    """Process a single issue through the Impact Gate."""
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
            "%s transitioned %r -> in_review (webhook)", identifier, old_status
        )
    else:
        log.info("%s is in_review (webhook, no old_status provided)", identifier)

    fr_ids = _extract_fr_ids_from_labels(issue)
    is_fix = _is_fix_issue(issue)

    bug_ids: list[str] = []
    if is_fix:
        bug_id_m = re.fullmatch(r"BTCAAAAA-(\d+)", identifier, re.IGNORECASE)
        if bug_id_m:
            bug_ids.append(identifier.upper())

    if not fr_ids and not bug_ids:
        log.info(
            "%s has no FR labels and is not a fix/bug issue -- skipping",
            identifier,
        )
        return None

    state = _load_state()
    processed: set[str] = set(state.get("processed_issue_ids", []))
    if issue_id in processed:
        log.info("%s already processed -- skipping (dedup)", identifier)
        return None

    log.info(
        "Running Impact Gate for %s (fr_ids=%s, bug_ids=%s)",
        identifier,
        fr_ids,
        bug_ids,
    )

    try:
        result = run_impact_gate(fr_ids, bug_ids)
    except Exception as exc:
        log.error("Impact Gate runner failed for %s: %s", identifier, exc)
        return {"issue": identifier, "error": f"gate runner failed: {exc}"}

    comment_body = _build_results_comment(identifier, result, fr_ids, bug_ids)

    if not dry_run:
        _post_comment(issue_id, comment_body)

        gate_passed = result.get("status") == "PASS"
        if gate_passed:
            _transition_to_done(issue_id, identifier)

        state = _load_state()
        processed_set: set[str] = set(state.get("processed_issue_ids", []))
        if issue_id not in processed_set:
            state["processed_issue_ids"] = list(processed_set | {issue_id})
        statuses = state.setdefault("issue_statuses", {})
        statuses[issue_id] = status
        _save_state(state)

    return {
        "issue": identifier,
        "gate_status": result.get("status"),
        "summary": result.get("summary"),
    }


def _transition_to_done(issue_id: str, identifier: str) -> None:
    try:
        transition_issue_status(issue_id, "done")
        log.info("Marked %s as done (gate passed)", identifier)
    except Exception:
        log.exception("Failed to mark %s as done", identifier)


def run_once(dry_run: bool = False, force_reprocess: bool = False) -> list[dict]:
    """Run the Impact Gate on all eligible in_review issues."""
    state = _load_state()
    processed: set[str] = set(state.get("processed_issue_ids", []))

    issues = _fetch_in_review_issues()
    log.info("Fetched %d in_review issues", len(issues))

    candidates = []
    for issue in issues:
        has_fr = _has_fdr_label(issue) or _extract_fr_ids_from_labels(issue)
        is_fix = _is_fix_issue(issue)
        if has_fr or is_fix:
            candidates.append(issue)

    if not force_reprocess:
        candidates = _detect_transitions(state, candidates)

    if force_reprocess:
        log.info("Force-reprocess: %d eligible gate candidates", len(candidates))
    else:
        log.info("Detected %d new gate candidate(s)", len(candidates))

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

        log.info("Running Impact Gate for %s", identifier)
        try:
            result = process_issue(issue_id, dry_run=dry_run)
            if result:
                results.append(result)
                newly_processed.append(issue_id)
        except Exception as exc:
            log.error("Failed to process %s: %s", identifier, exc)
            results.append({"issue": identifier, "error": str(exc)})

    _sync_statuses(state, issues)

    if newly_processed and not dry_run:
        state["processed_issue_ids"] = list(processed | set(newly_processed))
        _save_state(state)
        log.info("Marked %d issues as processed", len(newly_processed))

    return results


def run_loop(
    interval_seconds: int = 120, dry_run: bool = False, force_reprocess: bool = False
) -> None:
    log.info(
        "Starting Impact Gate worker loop (interval=%ds, dry_run=%s, force_reprocess=%s)",
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

    parser = argparse.ArgumentParser(
        description="Impact Gate polling worker + webhook handler"
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
        help="Log results but do not post comments or transition issues",
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
        )
        if result:
            log.info("Result: %s", json.dumps(result, indent=2))
        else:
            log.info("No gate run (issue not eligible)")
    elif args.loop:
        run_loop(
            interval_seconds=args.loop,
            dry_run=args.dry_run,
            force_reprocess=args.force_reprocess,
        )
    else:
        results = run_once(dry_run=args.dry_run, force_reprocess=args.force_reprocess)
        log.info("Results: %s", json.dumps(results, indent=2))
