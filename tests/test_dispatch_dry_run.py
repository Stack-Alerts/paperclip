"""Tests for the --dry-run CLI flag on the merge-dispatch routine (BTCAAAAA-38473).

Gap 6 of the BTC-38306 merge-process checkup. The flag makes the dispatch
routine safe to run against a live paperclip board without write access:
- ``gh pr create`` is NOT called.
- ``gh pr merge`` is NOT called.
- ``comment_on_issue`` is NOT called (no board mutation).
- ``update_issue_status`` is NOT called (no status flip).

Acceptance criteria:
- ``main(["--issue", "<id>", "--dry-run"])`` parses the flag and forwards
  ``dry_run=True`` into ``dispatch_for_issue``.
- ``main(["--issue", "<id>"])`` (no flag) forwards ``dry_run=False``.
- ``process_issue(issue, dry_run=True)`` does not call any of the mutating
  helpers.
- ``process_issue(issue, dry_run=True)`` returns a result carrying
  ``dry_run=True``.
"""

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import merge_dispatch_routine as mdr  # noqa: E402


VALID_SHA = "a" * 40


def _comments_with_sha(sha: str) -> list[dict]:
    return [{"id": "c-1", "body": f"Fix-SHA: {sha}\n\nPR opened."}]


# ---------------------------------------------------------------------------
# CLI parsing — main() → dispatch_for_issue()
# ---------------------------------------------------------------------------


def test_main_passes_dry_run_true_when_flag_set():
    captured = {}

    def fake_dispatch(issue_id, dry_run=False):
        captured["issue_id"] = issue_id
        captured["dry_run"] = dry_run
        return 0

    with patch.object(mdr, "dispatch_for_issue", side_effect=fake_dispatch):
        rc = mdr.main(["--issue", "BTCAAAAA-12345", "--dry-run"])

    assert rc == 0
    assert captured["issue_id"] == "BTCAAAAA-12345"
    assert captured["dry_run"] is True


def test_main_passes_dry_run_false_when_flag_absent():
    captured = {}

    def fake_dispatch(issue_id, dry_run=False):
        captured["issue_id"] = issue_id
        captured["dry_run"] = dry_run
        return 0

    with patch.object(mdr, "dispatch_for_issue", side_effect=fake_dispatch):
        rc = mdr.main(["--issue", "BTCAAAAA-12345"])

    assert rc == 0
    assert captured["dry_run"] is False


# ---------------------------------------------------------------------------
# Sweep path — main() with no --issue (periodic sweep)
# ---------------------------------------------------------------------------


def test_main_sweep_propagates_dry_run_into_process_issue():
    """No-arg sweep path must propagate --dry-run into each process_issue call.

    Without the CLI wiring the sweep path raises NameError on `dry_run` at line 1335
    of merge_dispatch_routine.py (BTCAAAAA-38473 Gap 6 regression).
    """
    issues = [
        {"id": "i-1", "identifier": "BTCAAAAA-11111"},
        {"id": "i-2", "identifier": "BTCAAAAA-22222"},
    ]
    captured_dry_runs = []

    def fake_process(issue, dry_run=False):
        captured_dry_runs.append(dry_run)
        return {"issue": issue.get("identifier"), "action": "skip", "reason": "fake"}

    with patch.object(mdr, "token_scope_preflight", None), \
         patch.object(mdr, "find_in_review_issues", return_value=issues), \
         patch.object(mdr, "check_early_exit", return_value=False), \
         patch.object(mdr, "process_issue", side_effect=fake_process), \
         patch.object(mdr, "save_watermark"), \
         patch.object(mdr, "emit_telemetry_log"):
        rc = mdr.main(["--dry-run"])

    assert rc == 0
    assert captured_dry_runs == [True, True]


# ---------------------------------------------------------------------------
# process_issue() — dry-run does not mutate
# ---------------------------------------------------------------------------


def _stub_paperclip_dry_run_patches():
    """Return a list of patch-object context managers.

    Each patch short-circuits one of the early-return branches in
    ``process_issue`` so the test reaches the dry-run PR-create branch
    without hitting the real paperclip / git / gh APIs.
    """
    return [
        patch.object(mdr, "fetch_issue_comments", return_value=_comments_with_sha(VALID_SHA)),
        patch.object(mdr, "extract_fix_sha_from_comments", return_value=VALID_SHA),
        patch.object(mdr, "sha_exists_locally", return_value=True),
        patch.object(mdr, "fetch_sha_from_remote", return_value=True),
        patch.object(mdr, "is_ancestor_of_main", return_value=False),
        patch.object(
            mdr, "pre_dispatch_already_merged_check", return_value=(False, "")
        ),
        patch.object(
            mdr, "find_branch_for_sha", return_value="fix/BTCAAAAA-12345-foo"
        ),
        patch.object(mdr, "resolve_gh_token", return_value="fake-token"),
        patch.object(mdr, "find_existing_pr", return_value=None),
        patch.object(mdr, "verify_pr_merged", None),
    ]


def test_process_issue_dry_run_does_not_call_create_pr():
    mocks = list(_stub_paperclip_dry_run_patches())
    with patch.object(mdr, "create_pr") as mock_create_pr, \
         patch.object(mdr, "merge_pr") as mock_merge_pr, \
         patch.object(mdr, "comment_on_issue") as mock_comment, \
         patch.object(mdr, "update_issue_status") as mock_update_status:
        for m in mocks:
            m.__enter__()
        try:
            result = mdr.process_issue(
                {"id": "i-1", "identifier": "BTCAAAAA-12345"},
                dry_run=True,
            )
        finally:
            for m in mocks:
                m.__exit__(None, None, None)

    assert mock_create_pr.call_count == 0
    assert mock_merge_pr.call_count == 0
    assert mock_comment.call_count == 0
    assert mock_update_status.call_count == 0


def test_process_issue_dry_run_result_has_dry_run_marker():
    mocks = list(_stub_paperclip_dry_run_patches())
    with patch.object(mdr, "create_pr"), \
         patch.object(mdr, "merge_pr"), \
         patch.object(mdr, "comment_on_issue"), \
         patch.object(mdr, "update_issue_status"):
        for m in mocks:
            m.__enter__()
        try:
            result = mdr.process_issue(
                {"id": "i-1", "identifier": "BTCAAAAA-12345"},
                dry_run=True,
            )
        finally:
            for m in mocks:
                m.__exit__(None, None, None)

    assert result.get("action") == "merged"
    assert result.get("dry_run") is True
    assert result.get("pr_number") == 0


def test_process_issue_normal_run_calls_create_pr():
    """Control test: without --dry-run the real ``create_pr`` is invoked."""
    mocks = list(_stub_paperclip_dry_run_patches())
    fake_pr = {"number": 42, "html_url": "https://github.com/x/y/pull/42"}
    fake_merge = {"sha": VALID_SHA}

    with patch.object(mdr, "create_pr", return_value=fake_pr) as mock_create_pr, \
         patch.object(mdr, "merge_pr", return_value=fake_merge), \
         patch.object(mdr, "comment_on_issue", return_value=True), \
         patch.object(mdr, "update_issue_status", return_value=True):
        for m in mocks:
            m.__enter__()
        try:
            result = mdr.process_issue(
                {"id": "i-1", "identifier": "BTCAAAAA-12345"},
                dry_run=False,
            )
        finally:
            for m in mocks:
                m.__exit__(None, None, None)

    assert mock_create_pr.call_count == 1
    assert result.get("pr_number") == 42
    assert "dry_run" not in result