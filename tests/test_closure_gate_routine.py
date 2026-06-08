"""Unit tests for closure_gate_routine.py"""

import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from closure_gate_routine import (
    compute_action_hash,
    detect_unfiled_deferrals,
    extract_fix_sha_from_comments,
    followup_links_to_source,
    format_routine_report,
    process_issue,
    split_paragraphs,
    verify_sha_on_main,
)


class TestExtractFixSha:
    """Test Fix-SHA extraction from comments."""

    def test_extract_valid_fix_sha(self):
        """Should extract a valid 40-char SHA from comment."""
        comments = [
            {
                "body": "Fixed the issue.\n\nFix-SHA: 0123456789abcdef0123456789abcdef01234567\n\nDetails here.",
                "authorAgentId": "agent1",
            }
        ]
        sha = extract_fix_sha_from_comments(comments)
        assert sha == "0123456789abcdef0123456789abcdef01234567"

    def test_extract_fix_sha_line_anchored(self):
        """Should match Fix-SHA only at line start (anchored)."""
        comments = [
            {
                "body": "Some text Fix-SHA: 0123456789abcdef0123456789abcdef01234567 more text",
                "authorAgentId": "agent1",
            }
        ]
        # This should NOT match because Fix-SHA is not at line start
        sha = extract_fix_sha_from_comments(comments)
        assert sha is None

    def test_extract_fix_sha_line_start(self):
        """Should match Fix-SHA at line start."""
        comments = [
            {
                "body": "Some text\nFix-SHA: 0123456789abcdef0123456789abcdef01234567\nMore text",
                "authorAgentId": "agent1",
            }
        ]
        sha = extract_fix_sha_from_comments(comments)
        assert sha == "0123456789abcdef0123456789abcdef01234567"

    def test_no_fix_sha_present(self):
        """Should return None when no Fix-SHA is present."""
        comments = [
            {
                "body": "This issue was fixed but no SHA tag.",
                "authorAgentId": "agent1",
            }
        ]
        sha = extract_fix_sha_from_comments(comments)
        assert sha is None

    def test_empty_comments(self):
        """Should return None for empty comments list."""
        sha = extract_fix_sha_from_comments([])
        assert sha is None

    def test_multiple_comments_first_match(self):
        """Should return the first matching SHA when multiple comments exist."""
        comments = [
            {"body": "Initial comment"},
            {"body": "Fix-SHA: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            {"body": "Fix-SHA: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        ]
        sha = extract_fix_sha_from_comments(comments)
        assert sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


class TestVerifyShaOnMain:
    """Test SHA verification against origin/main."""

    @patch("subprocess.run")
    def test_sha_is_ancestor(self, mock_run):
        """Should return True when SHA is ancestor of origin/main."""
        mock_run.return_value = Mock(returncode=0)
        result = verify_sha_on_main("0123456789abcdef0123456789abcdef01234567")
        assert result is True

    @patch("subprocess.run")
    def test_sha_is_not_ancestor(self, mock_run):
        """Should return False when SHA is not ancestor of origin/main."""
        mock_run.return_value = Mock(returncode=1)
        result = verify_sha_on_main("0123456789abcdef0123456789abcdef01234567")
        assert result is False

    @patch("subprocess.run")
    def test_git_command_error(self, mock_run):
        """Should return False when git command raises exception."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)
        result = verify_sha_on_main("0123456789abcdef0123456789abcdef01234567")
        assert result is False

    @patch("subprocess.run")
    def test_fetches_origin_main(self, mock_run):
        """Should fetch origin/main before checking ancestor."""
        mock_run.return_value = Mock(returncode=0)
        verify_sha_on_main("0123456789abcdef0123456789abcdef01234567")

        # First call should be fetch
        first_call = mock_run.call_args_list[0]
        assert first_call[0][0][0] == "git"
        assert first_call[0][0][1] == "fetch"


class TestComputeActionHash:
    """Test action hash computation for deduplication."""

    def test_consistent_hash(self):
        """Should produce consistent hash for same inputs."""
        hash1 = compute_action_hash("issue1", "sha1", "reopen")
        hash2 = compute_action_hash("issue1", "sha1", "reopen")
        assert hash1 == hash2

    def test_different_issue_different_hash(self):
        """Should produce different hash for different issue IDs."""
        hash1 = compute_action_hash("issue1", "sha1", "reopen")
        hash2 = compute_action_hash("issue2", "sha1", "reopen")
        assert hash1 != hash2

    def test_different_action_different_hash(self):
        """Should produce different hash for different actions."""
        hash1 = compute_action_hash("issue1", "sha1", "reopen")
        hash2 = compute_action_hash("issue1", "sha1", "request_sha")
        assert hash1 != hash2

    def test_hash_is_short(self):
        """Should produce a short hash (8 chars)."""
        hash_val = compute_action_hash("issue1", "sha1", "reopen")
        assert len(hash_val) == 8


class TestFormatRoutineReport:
    """Test routine report formatting."""

    def test_report_with_no_actions(self):
        """Should format report with verified issues."""
        stats = {
            "verified": 5,
            "reopened": 0,
            "requested_sha": 0,
            "flagged_fabrication": 0,
            "errors": 0,
        }
        report = format_routine_report(10, stats)
        assert "Verified on main" in report and "5" in report
        assert "remain `done`" in report

    def test_report_with_reopened_issues(self):
        """Should format report with reopened issues."""
        stats = {
            "verified": 3,
            "reopened": 2,
            "requested_sha": 0,
            "flagged_fabrication": 0,
            "errors": 0,
        }
        report = format_routine_report(10, stats)
        assert "reopened: 2" in report or "Reopened" in report
        assert "Action Taken" in report

    def test_report_with_requested_sha(self):
        """Should format report with Fix-SHA requests."""
        stats = {
            "verified": 5,
            "reopened": 0,
            "requested_sha": 2,
            "flagged_fabrication": 0,
            "errors": 0,
        }
        report = format_routine_report(10, stats)
        assert ("Requested Fix-SHA" in report and "2" in report) or "Fix-SHA Requests" in report


class TestProcessIssue:
    """Test issue processing logic."""

    @patch("closure_gate_routine.detect_fabrication")
    @patch("closure_gate_routine.fetch_issue_comments")
    @patch("closure_gate_routine.extract_fix_sha_from_comments")
    @patch("closure_gate_routine.verify_sha_on_main")
    def test_process_issue_verified(self, mock_verify, mock_extract, mock_fetch_comments, mock_fab):
        """Should mark issue as verified when SHA is on main."""
        mock_fetch_comments.return_value = []
        mock_extract.return_value = "0123456789abcdef0123456789abcdef01234567"
        mock_fab.return_value = None
        mock_verify.return_value = True

        issue = {
            "id": "issue1",
            "identifier": "BTCAAAAA-123",
            "status": "done",
        }
        state = {}

        action_type, success = process_issue(issue, state)
        assert action_type == "verified"
        assert success is True

    @patch("closure_gate_routine.detect_fabrication")
    @patch("closure_gate_routine.fetch_issue_comments")
    @patch("closure_gate_routine.extract_fix_sha_from_comments")
    @patch("closure_gate_routine.reopen_issue")
    @patch("closure_gate_routine.verify_sha_on_main")
    def test_process_issue_reopened(self, mock_verify, mock_reopen, mock_extract, mock_fetch_comments, mock_fab):
        """Should reopen issue when SHA is not on main."""
        mock_fetch_comments.return_value = []
        mock_extract.return_value = "0123456789abcdef0123456789abcdef01234567"
        mock_fab.return_value = None
        mock_verify.return_value = False
        mock_reopen.return_value = True

        issue = {
            "id": "issue1",
            "identifier": "BTCAAAAA-123",
            "status": "done",
        }
        state = {}

        action_type, success = process_issue(issue, state)
        assert action_type == "reopen"
        assert success is True

    @patch("closure_gate_routine.fetch_issue_comments")
    @patch("closure_gate_routine.extract_fix_sha_from_comments")
    @patch("closure_gate_routine.request_fix_sha_tag")
    def test_process_issue_no_sha(self, mock_request, mock_extract, mock_fetch_comments):
        """Should request Fix-SHA when not present."""
        mock_fetch_comments.return_value = []
        mock_extract.return_value = None
        mock_request.return_value = True

        issue = {
            "id": "issue1",
            "identifier": "BTCAAAAA-123",
            "status": "done",
        }
        state = {}

        action_type, success = process_issue(issue, state)
        assert action_type == "request_sha"
        assert success is True

    @patch("closure_gate_routine.fetch_issue_comments")
    @patch("closure_gate_routine.request_fix_sha_tag")
    def test_process_issue_fix_sha_none_exempt(self, mock_request, mock_fetch_comments):
        """Issues carrying `Fix-SHA: NONE` are exempt and never trigger a request."""
        mock_fetch_comments.return_value = [
            {"body": "Operational fix; no code commit.\n\nFix-SHA: NONE\n"}
        ]

        issue = {
            "id": "issue-none",
            "identifier": "BTCAAAAA-26048",
            "status": "done",
            "originKind": "manual",
        }
        state: dict = {}

        action_type, success = process_issue(issue, state)
        assert action_type == "verified"
        assert success is True
        mock_request.assert_not_called()
        assert state == {}


class TestFixShaNoneExemption:
    """Cover the `Fix-SHA: NONE` exemption helper."""

    def test_marker_anywhere_in_thread(self):
        from closure_gate_routine import has_fix_sha_none_exemption

        comments = [
            {"body": "unrelated chatter"},
            {"body": "Closing as resolved.\n\nFix-SHA: NONE - operational fix.\n"},
        ]
        assert has_fix_sha_none_exemption(comments) is True

    def test_no_marker_returns_false(self):
        from closure_gate_routine import has_fix_sha_none_exemption

        assert has_fix_sha_none_exemption([{"body": "no marker here"}]) is False

    def test_inline_mention_does_not_match(self):
        from closure_gate_routine import has_fix_sha_none_exemption

        # Marker is line-anchored - prose mentioning "Fix-SHA: NONE" mid-line
        # must not match.
        comments = [
            {"body": "We could not provide Fix-SHA: NONE was acceptable here."}
        ]
        assert has_fix_sha_none_exemption(comments) is False

    def test_lowercase_none_does_not_match(self):
        from closure_gate_routine import has_fix_sha_none_exemption

        # Marker is case-sensitive: lowercase `none` should not match - keeps
        # the exemption deliberate.
        comments = [{"body": "Fix-SHA: none"}]
        assert has_fix_sha_none_exemption(comments) is False


class TestSplitParagraphs:
    """Test paragraph splitting helper."""

    def test_splits_on_blank_lines(self):
        text = "First paragraph.\nSecond line.\n\nSecond paragraph.\n\n\nThird."
        assert split_paragraphs(text) == [
            "First paragraph.\nSecond line.",
            "Second paragraph.",
            "Third.",
        ]

    def test_empty_returns_empty(self):
        assert split_paragraphs("") == []
        assert split_paragraphs(None) == []


class TestFollowupLinksToSource:
    """Test the follow-up linkage check."""

    def test_parent_id_match(self):
        assert followup_links_to_source(
            {"parentId": "src-id-1"},
            source_id="src-id-1",
            source_identifier="BTCAAAAA-100",
            source_project_id="proj-A",
        ) is True

    def test_description_cites_source(self):
        assert followup_links_to_source(
            {"description": "Follow-up to BTCAAAAA-100 cleanup."},
            source_id="src-id-1",
            source_identifier="BTCAAAAA-100",
            source_project_id="proj-A",
        ) is True

    def test_title_cites_source(self):
        assert followup_links_to_source(
            {"title": "Audit BTCAAAAA-100 leftovers"},
            source_id="src-id-1",
            source_identifier="BTCAAAAA-100",
            source_project_id="proj-A",
        ) is True

    def test_no_link_no_cite_returns_false(self):
        assert followup_links_to_source(
            {"title": "Unrelated work", "description": "Other thing."},
            source_id="src-id-1",
            source_identifier="BTCAAAAA-100",
            source_project_id="proj-A",
        ) is False

    def test_none_followup_returns_false(self):
        assert followup_links_to_source(
            None, "src", "BTCAAAAA-100", "proj-A"
        ) is False


class TestDetectUnfiledDeferrals:
    """BTCAAAAA-30577 acceptance criterion 6 — 4 scenarios."""

    def _source_issue(self):
        return {
            "id": "src-id-1",
            "identifier": "BTCAAAAA-100",
            "projectId": "proj-A",
        }

    # (a) clean closure with no deferral → 0 flags
    def test_a_clean_closure_no_deferral(self):
        comments = [
            {
                "id": "c-1",
                "body": "Fixed the bug. Tests pass on main.\n\nFix-SHA: 0123456789abcdef0123456789abcdef01234567",
            }
        ]
        flags = detect_unfiled_deferrals(self._source_issue(), comments)
        assert flags == []

    # (b) closure with deferral and filed follow-up → 0 flags
    @patch("closure_gate_routine.fetch_issue_by_identifier")
    def test_b_deferral_with_filed_followup(self, mock_fetch):
        mock_fetch.return_value = {
            "id": "f-1",
            "identifier": "BTCAAAAA-200",
            "parentId": "src-id-1",
            "projectId": "proj-A",
            "title": "Audit os.getenv usage",
            "description": "Tracking audit deferred from BTCAAAAA-100.",
        }
        comments = [
            {
                "id": "c-2",
                "body": (
                    "Shipped the fix.\n\n"
                    "Out of scope: broader os.getenv audit deferred to "
                    "BTCAAAAA-200 (filed tracking issue)."
                ),
            }
        ]
        flags = detect_unfiled_deferrals(self._source_issue(), comments)
        assert flags == []
        mock_fetch.assert_called_with("BTCAAAAA-200")

    # (c) closure with deferral + no follow-up → 1 flag
    @patch("closure_gate_routine.fetch_issue_by_identifier")
    def test_c_deferral_without_followup(self, mock_fetch):
        comments = [
            {
                "id": "c-3",
                "body": (
                    "Done.\n\n"
                    "Out of scope (deferred): cleanup of remaining call sites — "
                    "will need a follow-up audit."
                ),
            }
        ]
        flags = detect_unfiled_deferrals(self._source_issue(), comments)
        assert len(flags) == 1
        flag = flags[0]
        assert flag["source_identifier"] == "BTCAAAAA-100"
        assert flag["comment_id"] == "c-3"
        assert flag["candidate_refs"] == []
        assert flag["reason"] == "no_refs"
        assert "Out of scope" in flag["paragraph"]
        mock_fetch.assert_not_called()

    # (d) closure citing a non-existent ticket id → 1 flag
    @patch("closure_gate_routine.fetch_issue_by_identifier")
    def test_d_deferral_cites_nonexistent_ticket(self, mock_fetch):
        mock_fetch.return_value = None  # 404 → not found
        comments = [
            {
                "id": "c-4",
                "body": (
                    "Closing.\n\n"
                    "Out of scope: see tracking issue BTCAAAAA-99999 for the "
                    "broader audit."
                ),
            }
        ]
        flags = detect_unfiled_deferrals(self._source_issue(), comments)
        assert len(flags) == 1
        flag = flags[0]
        assert flag["source_identifier"] == "BTCAAAAA-100"
        assert flag["comment_id"] == "c-4"
        assert flag["candidate_refs"] == ["BTCAAAAA-99999"]
        assert flag["reason"] == "refs_invalid"
        mock_fetch.assert_called_with("BTCAAAAA-99999")

    # Self-references must not count as filed follow-ups
    @patch("closure_gate_routine.fetch_issue_by_identifier")
    def test_self_reference_does_not_count(self, mock_fetch):
        comments = [
            {
                "id": "c-5",
                "body": (
                    "Done.\n\n"
                    "Out of scope: this BTCAAAAA-100 closure does not file a "
                    "tracking issue for the broader cleanup."
                ),
            }
        ]
        flags = detect_unfiled_deferrals(self._source_issue(), comments)
        assert len(flags) == 1
        assert flags[0]["candidate_refs"] == []
        mock_fetch.assert_not_called()

    # Deferral lexicon outside any paragraph (case sensitivity / inline)
    @patch("closure_gate_routine.fetch_issue_by_identifier")
    def test_case_insensitive_lexicon(self, mock_fetch):
        comments = [
            {
                "id": "c-6",
                "body": "Closing.\n\nDEFERRED: needs follow-up audit later.",
            }
        ]
        flags = detect_unfiled_deferrals(self._source_issue(), comments)
        assert len(flags) == 1
        mock_fetch.assert_not_called()


class TestFormatRoutineReportDeferrals:
    """Verify unfiled_deferrals[] section renders into the routine report."""

    def test_report_includes_deferral_section(self):
        stats = {
            "verified": 1,
            "reopened": 0,
            "requested_sha": 0,
            "flagged_fabrication": 0,
            "errors": 0,
        }
        deferral_flags = [
            {
                "source_identifier": "BTCAAAAA-100",
                "source_id": "src-1",
                "comment_id": "c-1",
                "paragraph": "Out of scope: needs follow-up.",
                "candidate_refs": [],
                "reason": "no_refs",
            }
        ]
        report = format_routine_report(
            5, stats, deferral_flags=deferral_flags, window_hours=24
        )
        assert "unfiled_deferrals[]" in report
        assert "BTCAAAAA-100" in report
        assert "no_refs" in report
        assert "Out of scope" in report

    def test_report_window_label_days(self):
        stats = {
            "verified": 0,
            "reopened": 0,
            "requested_sha": 0,
            "flagged_fabrication": 0,
            "errors": 0,
        }
        report = format_routine_report(0, stats, window_hours=720)
        assert "30d window" in report

    def test_report_window_label_hours(self):
        stats = {
            "verified": 0,
            "reopened": 0,
            "requested_sha": 0,
            "flagged_fabrication": 0,
            "errors": 0,
        }
        report = format_routine_report(0, stats, window_hours=24)
        assert "24h window" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
