"""Impact Gate worker — enforce FR acceptance + bug regression gates for fix issues.

Triggered when a fix/bug issue transitions to ``in_review`` (or called directly
via ``--issue-id``).  The worker:

1. Checks for a CEO bypass approval label — skips gate if present.
2. Reads ``touchedFiles`` from the issue description.
3. Queries the Blast Radius Touch Index for ``fr_impact_set`` and ``regression_set``.
4. Runs the Impact Gate test suite (FR acceptance + bug regression tests).
5. Posts a structured comment with results.
6. On PASS: transitions issue to ``done``.
7. On FAIL: reverts issue to ``in_progress``, creates blocking sub-issues per spec.
8. On runner error: posts escalation comment, does NOT revert.
"""

from __future__ import annotations

import json
import logging
import sys
import os
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from touch_index.paperclip_client import (
    _base,
    _company,
    _session,
    transition_issue_status,
)
from blast_radius.report import extract_touched_files
from blast_radius.query import query_blast_radius
from impact_gate_runner import run as run_impact_gate

log = logging.getLogger(__name__)

BYPASS_LABEL = "impact-gate-bypass"

COMPANY_PREFIX = "BTCAAAAA"


# ---------------------------------------------------------------------------
# Paperclip API helpers
# ---------------------------------------------------------------------------

def _get_issue(issue_id: str) -> dict:
    sess = _session()
    resp = sess.get(f"{_base()}/api/issues/{issue_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def _post_comment(issue_id: str, body: str) -> None:
    sess = _session()
    resp = sess.post(
        f"{_base()}/api/issues/{issue_id}/comments",
        json={"body": body},
        timeout=30,
    )
    resp.raise_for_status()


def _create_blocking_issue(
    fix_identifier: str,
    failing_item_id: str,
    failure_detail: str,
    issue_type: str,
) -> dict | None:
    """Create a blocking sub-issue in Paperclip for a gate failure.

    *issue_type* is one of "fr" or "bug".
    Returns the created issue dict, or None on failure.
    """
    title_map = {
        "fr": f"Impact Gate: FR acceptance tests failing for {failing_item_id}",
        "bug": f"Impact Gate: Bug regression tests failing for {failing_item_id}",
    }
    title = title_map.get(issue_type, f"Impact Gate failure for {failing_item_id}")

    body = (
        f"Blocking issue auto-created by Impact Gate worker.\n\n"
        f"**Source fix:** {fix_identifier}\n"
        f"**Failing item:** {failing_item_id}\n"
        f"**Type:** {issue_type}\n\n"
        f"**Failure detail:**\n```\n{failure_detail}\n```\n\n"
        f"This issue must be resolved before {fix_identifier} can proceed to review."
    )

    try:
        sess = _session()
        resp = sess.post(
            f"{_base()}/api/companies/{_company()}/issues",
            json={
                "title": title,
                "body": body,
                "labels": ["impact-gate-failure"],
                "status": "todo",
            },
            timeout=30,
        )
        resp.raise_for_status()
        created = resp.json()
        log.info("Created blocking issue %s for %s", created.get("identifier", ""), failing_item_id)
        return created
    except Exception as exc:
        log.error("Failed to create blocking issue for %s: %s", failing_item_id, exc)
        return None


def _set_blocked_by(issue_id: str, blocking_ids: list[str]) -> None:
    """Set ``blockedByIssueIds`` on an issue to prevent status promotion."""
    try:
        sess = _session()
        resp = sess.patch(
            f"{_base()}/api/issues/{issue_id}",
            json={"blockedByIssueIds": blocking_ids},
            timeout=30,
        )
        resp.raise_for_status()
        log.info("Set blockedByIssueIds=%s on %s", blocking_ids, issue_id)
    except Exception as exc:
        log.error("Failed to set blockedByIssueIds on %s: %s", issue_id, exc)


# ---------------------------------------------------------------------------
# Bypass check
# ---------------------------------------------------------------------------

def _has_bypass_label(issue: dict) -> bool:
    """Check if the issue carries the CEO bypass label."""
    labels = issue.get("labels") or []
    for lbl in labels:
        name = (lbl.get("name") or "").lower().strip()
        if name == BYPASS_LABEL:
            return True
    return False


# ---------------------------------------------------------------------------
# Results comment builder
# ---------------------------------------------------------------------------

def _build_pass_comment(identifier: str, result: dict) -> str:
    summary = result.get("summary", {})
    lines = [
        "## Impact Gate: PASS ✅",
        "",
        f"Issue: **{identifier}**",
        "",
        "All FR acceptance and bug regression tests passed.",
        "",
        "### Summary",
        f"- Total tests: {summary.get('total', 0)}",
        f"- Passed: {summary.get('passed', 0)}",
        f"- Failed: {summary.get('failed', 0)}",
        f"- Errors: {summary.get('errors', 0)}",
        "",
        "Gate passed — issue may proceed.",
    ]
    return "\n".join(lines)


def _build_fail_comment(
    identifier: str,
    result: dict,
    fr_ids: list[str],
    bug_ids: list[str],
    blocking_issues: list[dict],
) -> str:
    summary = result.get("summary", {})
    lines = [
        "## Impact Gate: FAIL ❌",
        "",
        f"Issue: **{identifier}**",
        "",
        "One or more tests failed. Gate has reverted this issue to **in_progress**.",
        "",
        "### Summary",
        f"- Total tests: {summary.get('total', 0)}",
        f"- Passed: {summary.get('passed', 0)}",
        f"- Failed: {summary.get('failed', 0)}",
        f"- Errors: {summary.get('errors', 0)}",
        "",
    ]

    if fr_ids:
        lines.append("### FR Acceptance Results")
        fr_results = result.get("fr_results", {})
        for fid in fr_ids:
            fr = fr_results.get(fid, {})
            lines.append(f"- **{fid}**: {fr.get('status', 'UNKNOWN')}")
            if fr.get("status") == "FAIL":
                for t in fr.get("tests", []):
                    if t.get("outcome") in ("failed", "error"):
                        lines.append(f"  - `{t['nodeid']}`")
        lines.append("")

    if bug_ids:
        lines.append("### Bug Regression Results")
        bug_results = result.get("bug_results", {})
        for bid in bug_ids:
            br = bug_results.get(bid, {})
            lines.append(f"- **{bid}**: {br.get('status', 'UNKNOWN')}")
            if br.get("status") == "FAIL":
                for t in br.get("tests", []):
                    if t.get("outcome") in ("failed", "error"):
                        lines.append(f"  - `{t['nodeid']}`")
        lines.append("")

    if blocking_issues:
        lines.append("### Blocking Issues Created")
        for bi in blocking_issues:
            bi_id = bi.get("identifier", bi.get("id", "unknown"))
            lines.append(f"- [{bi_id}](/{COMPANY_PREFIX}/issues/{bi_id})")
        lines.append("")

    return "\n".join(lines)


def _build_escalation_comment(identifier: str, error_msg: str) -> str:
    return (
        f"## Impact Gate: ERROR ⚠️\n\n"
        f"Issue: **{identifier}**\n\n"
        f"The Impact Gate runner encountered an internal error:\n\n"
        f"```\n{error_msg}\n```\n\n"
        f"**No status change was made.** Please investigate and re-run the gate."
    )


def _build_bypass_comment(identifier: str) -> str:
    return (
        f"## Impact Gate: BYPASSED 🔶\n\n"
        f"Issue: **{identifier}**\n\n"
        f"CEO bypass label detected — Impact Gate skipped."
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def process_issue(issue_id: str, dry_run: bool = False, old_status: str | None = None) -> dict:
    """Run the Impact Gate for a single fix issue.

    When called from a Paperclip ``issue_status_changed`` webhook, the caller
    may pass the previous status via *old_status* for logging and audit.

    Returns a dict with keys:
      - issue: identifier
      - gate_status: "PASS" | "FAIL" | "ERROR" | "BYPASSED" | "SKIPPED"
      - summary: test summary (if run)
      - blocking_issues: list of created blocking issue dicts (if FAIL)
    """
    try:
        issue = _get_issue(issue_id)
    except Exception as exc:
        log.error("Failed to fetch issue %s: %s", issue_id, exc)
        return {"issue": issue_id, "gate_status": "ERROR", "error": f"fetch failed: {exc}"}

    identifier = issue.get("identifier", issue_id)
    status = issue.get("status", "")
    description = issue.get("description", "") or ""
    title = issue.get("title", "")

    if old_status:
        log.info(
            "Processing issue %s (status=%s, old_status=%s, title=%s)",
            identifier, status, old_status, title,
        )
    else:
        log.info("Processing issue %s (status=%s, title=%s)", identifier, status, title)

    # --- Bypass check ---
    if _has_bypass_label(issue):
        log.info("Bypass label detected on %s — skipping gate", identifier)
        if not dry_run:
            _post_comment(issue_id, _build_bypass_comment(identifier))
        return {"issue": identifier, "gate_status": "BYPASSED"}

    # --- Only run for in_review issues ---
    if status != "in_review":
        log.info("%s has status=%r (not in_review) — skipping", identifier, status)
        return {"issue": identifier, "gate_status": "SKIPPED", "reason": f"status={status}"}

    # --- Extract touchedFiles ---
    touched_files = extract_touched_files(description)
    if not touched_files:
        log.warning("No touchedFiles found for issue %s", identifier)
        if not dry_run:
            _post_comment(
                issue_id,
                f"## Impact Gate: SKIPPED\n\nIssue **{identifier}** has no `touchedFiles` in its description.\n\nGate cannot run without file paths.",
            )
        return {"issue": identifier, "gate_status": "SKIPPED", "reason": "no touchedFiles"}

    log.info("Touched files for %s: %s", identifier, touched_files)

    # --- Query Blast Radius ---
    try:
        br_data = query_blast_radius(touched_files)
    except Exception as exc:
        log.error("Blast Radius query failed for %s: %s", identifier, exc)
        error_msg = f"Blast Radius query error: {exc}"
        if not dry_run:
            _post_comment(issue_id, _build_escalation_comment(identifier, error_msg))
        return {"issue": identifier, "gate_status": "ERROR", "error": error_msg}

    # --- Extract FR IDs and bug IDs ---
    fr_ids = [fr.fr_identifier for fr in br_data.fr_impact_set]
    regression_bug_ids = [r.bug_identifier for r in br_data.regression_set]

    # The fix issue's own identifier is always a bug ID for regression testing
    bug_ids = [identifier]
    for bid in regression_bug_ids:
        if bid not in bug_ids:
            bug_ids.append(bid)

    log.info(
        "Impact Gate for %s: fr_ids=%s, bug_ids=%s",
        identifier, fr_ids, bug_ids,
    )

    if not fr_ids and not bug_ids:
        log.info("No FR or bug IDs found for %s — nothing to gate", identifier)
        if not dry_run:
            _post_comment(
                issue_id,
                f"## Impact Gate: PASS ✅\n\nIssue **{identifier}** has no FR impact and no regression risk.\n\nGate passed — no tests to run.",
            )
            transition_issue_status(issue_id, "done")
        return {"issue": identifier, "gate_status": "PASS", "reason": "no tests needed"}

    # --- Run Impact Gate tests ---
    try:
        result = run_impact_gate(fr_ids, bug_ids)
    except Exception as exc:
        log.error("Impact Gate runner failed for %s: %s", identifier, exc)
        error_msg = f"Impact Gate runner error: {exc}"
        if not dry_run:
            _post_comment(issue_id, _build_escalation_comment(identifier, error_msg))
        return {"issue": identifier, "gate_status": "ERROR", "error": error_msg}

    gate_status = result.get("status", "ERROR")
    log.info("Impact Gate result for %s: %s", identifier, gate_status)

    if dry_run:
        log.info("[dry-run] Gate result for %s: %s", identifier, gate_status)
        return {
            "issue": identifier,
            "gate_status": gate_status,
            "summary": result.get("summary"),
            "fr_ids": fr_ids,
            "bug_ids": bug_ids,
            "dry_run": True,
        }

    # --- Act on result ---
    if gate_status == "PASS":
        _post_comment(issue_id, _build_pass_comment(identifier, result))
        transition_issue_status(issue_id, "done")
        log.info("Gate PASS for %s — transitioned to done", identifier)
        return {
            "issue": identifier,
            "gate_status": "PASS",
            "summary": result.get("summary"),
        }

    # FAIL or ERROR — revert to in_progress, create blocking sub-issues
    blocking_issues: list[dict] = []

    # Create blocking issues for each failing FR
    fr_results = result.get("fr_results", {})
    for fid in fr_ids:
        fr_entry = fr_results.get(fid, {})
        if fr_entry.get("status") in ("FAIL", "ERROR", "MISSING"):
            detail_lines = []
            for t in fr_entry.get("tests", []):
                if t.get("outcome") in ("failed", "error"):
                    detail_lines.append(f"{t['nodeid']}: {t.get('message', '')}")
            detail = "\n".join(detail_lines) if detail_lines else f"Status: {fr_entry.get('status')}"
            bi = _create_blocking_issue(identifier, fid, detail, "fr")
            if bi:
                blocking_issues.append(bi)

    # Create blocking issues for each failing bug regression
    bug_results = result.get("bug_results", {})
    for bid in bug_ids:
        bug_entry = bug_results.get(bid, {})
        if bug_entry.get("status") in ("FAIL", "ERROR", "MISSING"):
            detail_lines = []
            for t in bug_entry.get("tests", []):
                if t.get("outcome") in ("failed", "error"):
                    detail_lines.append(f"{t['nodeid']}: {t.get('message', '')}")
            detail = "\n".join(detail_lines) if detail_lines else f"Status: {bug_entry.get('status')}"
            bi = _create_blocking_issue(identifier, bid, detail, "bug")
            if bi:
                blocking_issues.append(bi)

    # Post failure comment
    fail_comment = _build_fail_comment(identifier, result, fr_ids, bug_ids, blocking_issues)
    _post_comment(issue_id, fail_comment)

    # Revert to in_progress
    transition_issue_status(issue_id, "in_progress")

    # Set blockedByIssueIds
    blocking_ids = [bi.get("id", "") for bi in blocking_issues if bi.get("id")]
    if blocking_ids:
        _set_blocked_by(issue_id, blocking_ids)

    log.info(
        "Gate FAIL for %s — reverted to in_progress, %d blocking issues created",
        identifier,
        len(blocking_issues),
    )

    return {
        "issue": identifier,
        "gate_status": gate_status,
        "summary": result.get("summary"),
        "blocking_issues": [bi.get("identifier", bi.get("id", "")) for bi in blocking_issues],
    }


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Impact Gate worker — enforce FR acceptance + bug regression gates",
    )
    parser.add_argument(
        "--issue-id",
        type=str,
        required=True,
        metavar="UUID",
        help="Paperclip issue UUID of the fix/bug issue to gate",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log results but do not post comments or transition issues",
    )
    args = parser.parse_args()

    result = process_issue(args.issue_id, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
