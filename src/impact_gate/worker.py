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
import time
import sys
import os
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from touch_index.paperclip_client import (
    _base,
    _company,
    _paginate,
    _session,
    _board_session,
    transition_issue_status_board,
)
from blast_radius.report import extract_touched_files
from blast_radius.query import query_blast_radius
from impact_gate_runner import run as run_impact_gate

log = logging.getLogger(__name__)

BYPASS_LABEL = "impact-gate-bypass"

COMPANY_PREFIX = "BTCAAAAA"

# Minimum test bar - the Impact Gate must collect at least this many
# individual test cases (FR acceptance + bug regression combined) before
# it can declare a PASS.  This is the "10-fix bar" required for production
# acceptance: sufficient coverage to justify promoting a fix to done.

MIN_TESTS_BAR = 10
# Impact Gate runner retry — transient CI failures can produce false-negative
# FAIL results.  Retry up to GATE_RETRY_MAX_ATTEMPTS times with exponential
# backoff before accepting a FAIL verdict and creating blocking issues.
GATE_RETRY_MAX_ATTEMPTS = 3
GATE_RETRY_BASE_DELAY = 2.0  # seconds

# Rate limiting between blocking issue API calls to avoid flooding the Paperclip API
BLOCKING_ISSUE_CREATE_INTERVAL = 1.0  # seconds


def _build_dedup_key(fix_identifier: str, failing_item_id: str, issue_type: str) -> str:
    """Build a deterministic dedup marker embedded in blocking issue bodies.
    
    Used to detect and skip duplicate blocking issue creation when
    the same fix issue fails the same gate multiple times.
    """
    return f"<!-- dedup:impact-gate:{fix_identifier}:{failing_item_id}:{issue_type} -->"



def _find_existing_blocking_issue(
    fix_identifier: str,
    failing_item_id: str,
    issue_type: str,
) -> dict | None:
    """Search for an existing blocking issue matching (fix, item, type)."""
    dedup_key = _build_dedup_key(fix_identifier, failing_item_id, issue_type)
    try:
        issues = _paginate(
            f"/api/companies/{_company()}/issues",
            {"q": fix_identifier, "limit": 50},
            page_size=50,
        )
        for issue in issues:
            body = issue.get("description") or ""
            if dedup_key in body:
                log.info(
                    "Found existing blocking issue %s for %s/%s — skipping",
                    issue.get("identifier", ""),
                    fix_identifier,
                    failing_item_id,
                )
                return issue
    except Exception as exc:
        log.warning("Failed to search for existing blocking issues: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Paperclip API helpers
# ---------------------------------------------------------------------------


def _get_issue(issue_id: str) -> dict:
    sess = _board_session()
    resp = sess.get(f"{_base()}/api/issues/{issue_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def _post_comment(issue_id: str, body: str) -> bool:
    """Post a comment on an issue.  Silently skips if the issue is done
    (done-guard, BTCAAAAA-25832)."""
    try:
        from touch_index.paperclip_client import is_issue_done
        if is_issue_done(issue_id):
            log.info(
                "_post_comment: issue %s is done — skipping comment (done-guard)",
                issue_id,
            )
            return False
    except Exception:
        pass

    try:
        sess = _board_session()
        resp = sess.post(
            f"{_base()}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=30,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        log.warning("Failed to post comment on %s: %s", issue_id, exc)
        return False


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

    dedup_key = _build_dedup_key(fix_identifier, failing_item_id, issue_type)
    body = (
        f"Blocking issue auto-created by Impact Gate worker.\n\n"
        f"**Source fix:** {fix_identifier}\n"
        f"**Failing item:** {failing_item_id}\n"
        f"**Type:** {issue_type}\n\n"
        f"**Failure detail:**\n```\n{failure_detail}\n```\n\n"
        f"This issue must be resolved before {fix_identifier} can proceed to review.\n\n"
        f"{dedup_key}"
    )

    try:
        sess = _session()
        resp = sess.post(
            f"{_base()}/api/companies/{_company()}/issues",
            json={
                "title": title,
                "description": body,
                "labels": ["impact-gate-failure"],
                "status": "todo",
            },
            timeout=30,
        )
        resp.raise_for_status()
        created = resp.json()
        log.info(
            "Created blocking issue %s for %s",
            created.get("identifier", ""),
            failing_item_id,
        )
        return created
    except Exception as exc:
        log.error("Failed to create blocking issue for %s: %s", failing_item_id, exc)
        return None


def _set_blocked_by(issue_id: str, blocking_ids: list[str]) -> None:
    """Set ``blockedByIssueIds`` on an issue to prevent status promotion."""
    try:
        sess = _board_session()
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
    bar_reason = result.get("_bar_fail_reason")
    lines = [
        "## Impact Gate: FAIL ❌",
        "",
        f"Issue: **{identifier}**",
        "",
        "One or more tests failed. Gate has reverted this issue to **in_progress**.",
        "",
    ]

    if bar_reason:
        lines.append("> **Minimum test bar not met**")
        lines.append(">")
        lines.append(f"> {bar_reason}")
        lines.append("")

    lines += [
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


def process_issue(
    issue_id: str,
    dry_run: bool = False,
    old_status: str | None = None,
    force: bool = False,
) -> dict:
    """Run the Impact Gate for a single fix issue.

    When called from a Paperclip ``issue_status_changed`` webhook, the caller
    may pass the previous status via *old_status* for logging and audit.

    *force* bypasses the in_review status check so that already-done issues
    can be retroactively gated (used by scan_fix_issues_done.py --retroactive).

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
        return {
            "issue": issue_id,
            "gate_status": "ERROR",
            "error": f"fetch failed: {exc}",
        }

    identifier = issue.get("identifier", issue_id)
    status = issue.get("status", "")
    description = issue.get("description", "") or ""
    title = issue.get("title", "")

    if old_status:
        log.info(
            "Processing issue %s (status=%s, old_status=%s, title=%s)",
            identifier,
            status,
            old_status,
            title,
        )
    else:
        log.info("Processing issue %s (status=%s, title=%s)", identifier, status, title)

    # Suppress all mutations (comments, transitions, blocking issues)
    # when force-gating already-done issues to avoid triggering the
    # platform's comment-on-done → reopen behaviour (BTCAAAAA-25693).
    # Also mute when the issue is already done regardless of force flag
    # (BTCAAAAA-25832 done-guard).
    mute = (force and not dry_run) or (status == "done" and not dry_run)

    def _save_if_muted(status: str) -> None:
        """Persist muted gate result so future scans skip this issue."""
        if mute:
            try:
                from scan_fix_issues_done import save_muted_gate_result
                save_muted_gate_result(issue_id, status)
            except Exception:
                pass

    # --- Bypass check ---
    if _has_bypass_label(issue):
        log.info("Bypass label detected on %s — skipping gate", identifier)
        if not dry_run and not mute:
            _post_comment(issue_id, _build_bypass_comment(identifier))
        _save_if_muted("BYPASSED")
        return {"issue": identifier, "gate_status": "BYPASSED"}

    # --- Only run for in_review issues (or force retroactive) ---
    if status != "in_review" and not force:
        log.info("%s has status=%r (not in_review) — skipping", identifier, status)
        return {
            "issue": identifier,
            "gate_status": "SKIPPED",
            "reason": f"status={status}",
        }
    if status != "in_review" and force:
        log.info("%s has status=%r — force retroactive gate", identifier, status)

    # --- Extract touchedFiles ---
    touched_files = extract_touched_files(description)

    # Fallback: derive touched files from git history when not in description
    if not touched_files:
        log.info(
            "No touchedFiles in description for %s — falling back to git history",
            identifier,
        )
        try:
            from touch_index.git_extractor import get_files_for_issue

            touched_files = get_files_for_issue(identifier)
            log.info(
                "Derived %d touched file(s) from git for %s",
                len(touched_files),
                identifier,
            )
        except Exception as exc:
            log.warning("Git fallback failed for %s: %s", identifier, exc)

    if not touched_files:
        log.warning("No touchedFiles found for issue %s", identifier)
        if not dry_run and not mute:
            _post_comment(
                issue_id,
                f"## Impact Gate: SKIPPED\n\nIssue **{identifier}** has no `touchedFiles` in its description and no git commits referencing it.\n\nGate cannot run without file paths.",
            )
        _save_if_muted("SKIPPED")
        return {
            "issue": identifier,
            "gate_status": "SKIPPED",
            "reason": "no touchedFiles",
        }

    log.info("Touched files for %s: %s", identifier, touched_files)

    # --- Query Blast Radius ---
    try:
        br_data = query_blast_radius(touched_files)
    except Exception as exc:
        log.error("Blast Radius query failed for %s: %s", identifier, exc)
        error_msg = f"Blast Radius query error: {exc}"
        if not dry_run and not mute:
            _post_comment(issue_id, _build_escalation_comment(identifier, error_msg))
        _save_if_muted("ERROR")
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
        identifier,
        fr_ids,
        bug_ids,
    )

    if not fr_ids and not bug_ids:
        log.info("No FR or bug IDs found for %s — nothing to gate", identifier)
        if not dry_run and not mute:
            _post_comment(
                issue_id,
                f"## Impact Gate: PASS ✅\n\nIssue **{identifier}** has no FR impact and no regression risk.\n\nGate passed — no tests to run.",
            )
            try:
                transition_issue_status_board(issue_id, "done")
            except Exception as exc:
                log.warning("Failed to transition %s to done: %s", identifier, exc)
        _save_if_muted("PASS")
        return {"issue": identifier, "gate_status": "PASS", "reason": "no tests needed"}

    # --- Run Impact Gate tests (with retry for transient CI failures) ---
    result = None
    last_error = None
    for gate_attempt in range(1, GATE_RETRY_MAX_ATTEMPTS + 1):
        try:
            result = run_impact_gate(fr_ids, bug_ids)
        except Exception as exc:
            log.error("Impact Gate runner failed for %s (attempt %d/%d): %s",
                       identifier, gate_attempt, GATE_RETRY_MAX_ATTEMPTS, exc)
            last_error = f"Impact Gate runner error: {exc}"
            if gate_attempt < GATE_RETRY_MAX_ATTEMPTS:
                delay = GATE_RETRY_BASE_DELAY * (2 ** (gate_attempt - 1))
                log.info("Retrying Impact Gate for %s in %.1fs ...", identifier, delay)
                time.sleep(delay)
            continue

        gate_status = result.get("status", "ERROR")
        if gate_status == "PASS":
            break  # success — stop retrying

        if gate_attempt < GATE_RETRY_MAX_ATTEMPTS:
            delay = GATE_RETRY_BASE_DELAY * (2 ** (gate_attempt - 1))
            log.warning(
                "Impact Gate for %s returned %s on attempt %d/%d — retrying in %.1fs ...",
                identifier, gate_status, gate_attempt, GATE_RETRY_MAX_ATTEMPTS, delay,
            )
            time.sleep(delay)

    if result is None:
        log.error("Impact Gate runner exhausted all %d attempts for %s",
                   GATE_RETRY_MAX_ATTEMPTS, identifier)
        error_msg = last_error or "Impact Gate runner: all attempts failed"
        if not dry_run and not mute:
            _post_comment(issue_id, _build_escalation_comment(identifier, error_msg))
        _save_if_muted("ERROR")
        return {"issue": identifier, "gate_status": "ERROR", "error": error_msg}

    # Enforce the minimum test bar (10-fix bar)
    total_tests = result.get("summary", {}).get("total", 0)
    if total_tests < MIN_TESTS_BAR and result.get("status") == "PASS":
        log.warning(
            "Impact Gate for %s: %d tests collected but bar requires %d — demoting PASS to FAIL",
            identifier,
            total_tests,
            MIN_TESTS_BAR,
        )
        result["status"] = "FAIL"
        bar_parts = [
            f"Insufficient test coverage: only {total_tests} test(s) collected ",
            f"(minimum bar is {MIN_TESTS_BAR}).  ",
            f"FR IDs: {fr_ids}, bug IDs: {bug_ids}.  ",
            f"Add more FR acceptance or bug regression test files covering ",
            f"the touched code paths.",
        ]
        result["_bar_fail_reason"] = "".join(bar_parts)

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
        if not mute:
            _post_comment(issue_id, _build_pass_comment(identifier, result))
            try:
                transition_issue_status_board(issue_id, "done")
            except Exception as exc:
                log.warning("Failed to transition %s to done: %s", identifier, exc)
        _save_if_muted("PASS")
        log.info("Gate PASS for %s — transitioned to done" if not mute else "Gate PASS for %s — mute (retroactive, no mutation)", identifier)
        return {
            "issue": identifier,
            "gate_status": "PASS",
            "summary": result.get("summary"),
        }

    # FAIL or ERROR — revert to in_progress, create blocking sub-issues
    blocking_issues: list[dict] = []
    if not mute:
        _last_create_time: float = 0.0

        def _maybe_throttle() -> None:
            """Ensure at least BLOCKING_ISSUE_CREATE_INTERVAL between API mutation calls."""
            nonlocal _last_create_time
            if _last_create_time > 0:
                elapsed = time.monotonic() - _last_create_time
                needed = BLOCKING_ISSUE_CREATE_INTERVAL - elapsed
                if needed > 0:
                    time.sleep(needed)
            _last_create_time = time.monotonic()

        # Create blocking issues for each failing FR (with dedup and rate limiting)
        fr_results = result.get("fr_results", {})
        for fid in fr_ids:
            fr_entry = fr_results.get(fid, {})
            if fr_entry.get("status") in ("FAIL", "ERROR", "MISSING"):
                detail_lines = []
                for t in fr_entry.get("tests", []):
                    if t.get("outcome") in ("failed", "error"):
                        detail_lines.append(f"{t['nodeid']}: {t.get('message', '')}")
                detail = (
                    "\n".join(detail_lines)
                    if detail_lines
                    else f"Status: {fr_entry.get('status')}"
                )
                _maybe_throttle()
                existing = _find_existing_blocking_issue(identifier, fid, "fr")
                if existing:
                    blocking_issues.append(existing)
                else:
                    _maybe_throttle()
                    bi = _create_blocking_issue(identifier, fid, detail, "fr")
                    if bi:
                        _last_create_time = time.monotonic()
                        blocking_issues.append(bi)

        # Create blocking issues for each failing bug regression (with dedup and rate limiting)
        bug_results = result.get("bug_results", {})
        for bid in bug_ids:
            bug_entry = bug_results.get(bid, {})
            if bug_entry.get("status") in ("FAIL", "ERROR", "MISSING"):
                detail_lines = []
                for t in bug_entry.get("tests", []):
                    if t.get("outcome") in ("failed", "error"):
                        detail_lines.append(f"{t['nodeid']}: {t.get('message', '')}")
                detail = (
                    "\n".join(detail_lines)
                    if detail_lines
                    else f"Status: {bug_entry.get('status')}"
                )
                _maybe_throttle()
                existing = _find_existing_blocking_issue(identifier, bid, "bug")
                if existing:
                    blocking_issues.append(existing)
                else:
                    _maybe_throttle()
                    bi = _create_blocking_issue(identifier, bid, detail, "bug")
                    if bi:
                        _last_create_time = time.monotonic()
                        blocking_issues.append(bi)

        # Post failure comment
        fail_comment = _build_fail_comment(
            identifier, result, fr_ids, bug_ids, blocking_issues
        )
        _post_comment(issue_id, fail_comment)

        # Revert to in_progress (skip for retroactive — don't undo "done" status)
        if not force:
            try:
                transition_issue_status_board(issue_id, "in_progress")
            except Exception as exc:
                log.warning("Failed to revert %s to in_progress: %s", identifier, exc)

        # Set blockedByIssueIds
        blocking_ids = [bi.get("id", "") for bi in blocking_issues if bi.get("id")]
        if blocking_ids:
            _set_blocked_by(issue_id, blocking_ids)

    action = "mute (retroactive, no mutation)" if mute else ("posted retroactive fail comment (status unchanged)" if force else "reverted to in_progress")
    _save_if_muted(gate_status)
    log.info(
        "Gate FAIL for %s — %s, %d blocking issues created",
        identifier,
        action,
        len(blocking_issues),
    )

    return {
        "issue": identifier,
        "gate_status": gate_status,
        "summary": result.get("summary"),
        "blocking_issues": [
            bi.get("identifier", bi.get("id", "")) for bi in blocking_issues
        ],
    }


# ---------------------------------------------------------------------------
# Scan-done: audit done fix/bug issues for Impact Gate coverage
# ---------------------------------------------------------------------------


def scan_done_issues(
    days_back: int | None = None,
    dry_run: bool = False,
    retroactive: bool = False,
    retry_errors: bool = False,
    retry_fails: bool = False,
) -> dict:
    from scan_fix_issues_done import scan as _scan_impl

    return _scan_impl(
        days_back=days_back,
        dry_run=dry_run,
        retroactive=retroactive,
        retry_errors=retry_errors,
        retry_fails=retry_fails,
    )


if __name__ == "__main__":
    import argparse
    import signal

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
        default=None,
        metavar="UUID",
        help="Paperclip issue UUID of the fix/bug issue to gate (single-issue mode)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log results but do not post comments or transition issues",
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Continuous polling mode — scan done fix/bug issues every --poll-interval seconds",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Poll interval in seconds for --poll mode (default: 300 = 5 min)",
    )
    parser.add_argument(
        "--retroactive",
        action="store_true",
        help="Run retroactive Impact Gate on ungated issues (used with --poll)",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=None,
        metavar="N",
        help="Only scan issues completed within the last N days (default: all, used with --poll)",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Purge muted ERROR entries for fresh retroactive gate (used with --poll)",
    )
    parser.add_argument(
        "--retry-fails",
        action="store_true",
        help="Purge muted FAIL entries for fresh retroactive gate (used with --poll)",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Output structured JSON summary to stdout (used with --poll, one-shot mode)",
    )
    args = parser.parse_args()

    if args.poll:
        if args.issue_id:
            log.error("--issue-id is not compatible with --poll mode")
            sys.exit(2)

        log.info(
            "Starting Impact Gate scan-done poll (interval=%ds, retroactive=%s, dry_run=%s, days_back=%s, retry_errors=%s, retry_fails=%s)",
            args.poll_interval,
            args.retroactive,
            args.dry_run,
            args.days_back,
            args.retry_errors,
            args.retry_fails,
        )

        _shutdown = [False]

        def _handle_signal(signum: int, _frame: object) -> None:
            log.info(
                "Received signal %d (%s) — shutting down after current poll cycle",
                signum,
                signal.Signals(signum).name,
            )
            _shutdown[0] = True

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        _first = True
        while not _shutdown[0]:
            try:
                result = scan_done_issues(
                    days_back=args.days_back,
                    dry_run=args.dry_run,
                    retroactive=args.retroactive,
                    retry_errors=args.retry_errors,
                    retry_fails=args.retry_fails,
                )
                if args.json_summary:
                    summary = {
                        "worker": "impact-gate-scan-done",
                        "dry_run": args.dry_run,
                        "retroactive": args.retroactive,
                        "retry_errors": args.retry_errors,
                        "retry_fails": args.retry_fails,
                        "days_back": args.days_back,
                        "timestamp": result.get("timestamp"),
                        "total_done_fix_issues": result.get("total_done_fix_issues"),
                        "gated": result.get("gated"),
                        "ungated_count": result.get("ungated_count"),
                        "last_24h": result.get("last_24h"),
                    }
                    if "retroactive_results" in result:
                        summary["retroactive_results"] = result["retroactive_results"]
                    print(json.dumps(summary, default=str))  # noqa: T201
            except Exception as exc:
                log.exception("Poll cycle failed: %s", exc)

            if _first and args.poll_interval == 0:
                log.info("--once mode (poll-interval=0) — exiting after single cycle")
                break
            _first = False

            if not _shutdown[0]:
                log.info(
                    "Sleeping %ds until next poll cycle ...", args.poll_interval
                )
                time.sleep(args.poll_interval)

        log.info("Shutdown complete")
        sys.exit(0)

    if args.issue_id:
        result = process_issue(args.issue_id, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))  # noqa: T201
        sys.exit(0)

    parser.error("Either --issue-id or --poll is required")
