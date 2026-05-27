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
    extract_fix_sha_from_comments,
    format_routine_report,
    process_issue,
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
            "errors": 0,
        }
        report = format_routine_report(10, stats)
        assert ("Requested Fix-SHA" in report and "2" in report) or "Fix-SHA Requests" in report


class TestProcessIssue:
    """Test issue processing logic."""

    @patch("closure_gate_routine.extract_fix_sha_from_comments")
    @patch("closure_gate_routine.verify_sha_on_main")
    def test_process_issue_verified(self, mock_verify, mock_extract):
        """Should mark issue as verified when SHA is on main."""
        mock_extract.return_value = "0123456789abcdef0123456789abcdef01234567"
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

    @patch("closure_gate_routine.extract_fix_sha_from_comments")
    @patch("closure_gate_routine.reopen_issue")
    @patch("closure_gate_routine.verify_sha_on_main")
    def test_process_issue_reopened(self, mock_verify, mock_reopen, mock_extract):
        """Should reopen issue when SHA is not on main."""
        mock_extract.return_value = "0123456789abcdef0123456789abcdef01234567"
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

    @patch("closure_gate_routine.extract_fix_sha_from_comments")
    @patch("closure_gate_routine.request_fix_sha_tag")
    def test_process_issue_no_sha(self, mock_request, mock_extract):
        """Should request Fix-SHA when not present."""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
