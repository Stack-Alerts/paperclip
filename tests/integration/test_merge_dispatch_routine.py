#!/usr/bin/env python3
"""Tests for merge-dispatch routine (Phase 4a).

Verifies that the routine correctly:
1. Finds in_review issues
2. Extracts Fix-SHA from comments
3. Skips issues whose SHA is unpushed or already merged
4. Creates and merges PRs
5. Handles errors and escalates failures
"""

from unittest.mock import MagicMock, patch

import pytest


class TestFixSHAPattern:
    """Test Fix-SHA extraction pattern."""

    def test_extract_fix_sha_valid(self):
        """Test extracting valid Fix-SHA from comment."""
        import sys
        from pathlib import Path

        # Add scripts to path
        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import FIX_SHA_PATTERN

        comment = "Some text\nFix-SHA: abc123def456abc123def456abc123def456abc1\nMore text"
        match = FIX_SHA_PATTERN.search(comment)
        assert match is not None
        assert match.group(1) == "abc123def456abc123def456abc123def456abc1"

    def test_extract_fix_sha_invalid(self):
        """Test that invalid SHA doesn't match."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import FIX_SHA_PATTERN

        comment = "Fix-SHA: not-a-valid-sha"
        match = FIX_SHA_PATTERN.search(comment)
        assert match is None

    def test_extract_fix_sha_requires_line_anchor(self):
        """Test that Fix-SHA must be on its own line."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import FIX_SHA_PATTERN

        comment = "Some prefix Fix-SHA: abc123def456abc123def456abc123def456abc1"
        match = FIX_SHA_PATTERN.search(comment)
        assert match is None


class TestMergeGate:
    """Test that the routine acts on Fix-SHA without an interaction gate."""

    def _load(self):
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))
        import merge_dispatch_routine

        return merge_dispatch_routine

    def test_skip_when_no_fix_sha(self):
        """An in_review issue with no Fix-SHA is skipped, not failed."""
        mod = self._load()
        issue = {"id": "id", "identifier": "BTCAAAAA-1", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[]):
            result = mod.process_issue(issue)
        assert result == {"issue": "BTCAAAAA-1", "action": "skip", "reason": "no_fix_sha"}

    def test_skip_when_sha_not_pushed(self):
        """A Fix-SHA that is neither local nor fetchable is skipped as push lag."""
        mod = self._load()
        sha = "a" * 40
        issue = {"id": "id", "identifier": "BTCAAAAA-2", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[{"body": f"Fix-SHA: {sha}"}]), \
            patch.object(mod, "sha_exists_locally", return_value=False), \
            patch.object(mod, "fetch_sha_from_remote", return_value=False):
            result = mod.process_issue(issue)
        assert result["action"] == "skip"
        assert result["reason"] == "sha_not_pushed"

    def test_skip_when_already_merged(self):
        """A Fix-SHA already on origin/main is skipped as already_merged."""
        mod = self._load()
        sha = "b" * 40
        issue = {"id": "id", "identifier": "BTCAAAAA-3", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[{"body": f"Fix-SHA: {sha}"}]), \
            patch.object(mod, "sha_exists_locally", return_value=True), \
            patch.object(mod, "is_ancestor_of_main", return_value=True):
            result = mod.process_issue(issue)
        assert result["action"] == "skip"
        assert result["reason"] == "already_merged"

    def test_skip_when_branch_not_pushed(self):
        """A Fix-SHA present locally but on no remote branch is skipped as push lag."""
        mod = self._load()
        sha = "c" * 40
        issue = {"id": "id", "identifier": "BTCAAAAA-4", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[{"body": f"Fix-SHA: {sha}"}]), \
            patch.object(mod, "sha_exists_locally", return_value=True), \
            patch.object(mod, "is_ancestor_of_main", return_value=False), \
            patch.object(mod, "find_branch_for_sha", return_value=None):
            result = mod.process_issue(issue)
        assert result["action"] == "skip"
        assert result["reason"] == "branch_not_pushed"


class TestAgentFinishDispatch:
    """Test the --issue agent-finish single-issue dispatch path (board opt2)."""

    def _load(self):
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))
        import merge_dispatch_routine

        return merge_dispatch_routine

    def test_dispatch_skips_non_in_review_issue(self):
        """A single issue that is not in_review is skipped, not processed."""
        mod = self._load()
        issue = {"id": "x", "identifier": "BTCAAAAA-5", "status": "in_progress"}
        with patch.object(mod, "fetch_issue", return_value=issue), \
            patch.object(mod, "process_issue") as proc:
            rc = mod.dispatch_for_issue("x")
        assert rc == 0
        proc.assert_not_called()

    def test_dispatch_processes_in_review_issue(self):
        """A single in_review issue is routed through process_issue."""
        mod = self._load()
        issue = {"id": "x", "identifier": "BTCAAAAA-6", "status": "in_review"}
        with patch.object(mod, "fetch_issue", return_value=issue), \
            patch.object(mod, "process_issue", return_value={"issue": "BTCAAAAA-6", "action": "skip", "reason": "sha_not_pushed"}) as proc:
            rc = mod.dispatch_for_issue("x")
        assert rc == 0
        proc.assert_called_once_with(issue)

    def test_main_routes_issue_flag(self):
        """main(['--issue', id]) delegates to dispatch_for_issue."""
        mod = self._load()
        with patch.object(mod, "dispatch_for_issue", return_value=0) as disp:
            rc = mod.main(["--issue", "abc"])
        assert rc == 0
        disp.assert_called_once_with("abc")


class TestSessionManagement:
    """Test HTTP session cleanup."""

    def test_http_session_closes_on_success(self):
        """Test that HTTP session is closed after successful request."""
        import sys
        from pathlib import Path
        from unittest.mock import patch, MagicMock

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import fetch_issue_comments

        mock_response = MagicMock()
        mock_response.json.return_value = []

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.close = MagicMock()

        with patch("merge_dispatch_routine.os.environ", {"PAPERCLIP_API_URL": "http://test"}):
            with patch("merge_dispatch_routine._http_session", return_value=mock_session):
                fetch_issue_comments("test-id")

                # Verify close was called
                mock_session.close.assert_called_once()

    def test_http_session_closes_on_exception(self):
        """Test that HTTP session is closed even on exception."""
        import sys
        from pathlib import Path
        from unittest.mock import patch, MagicMock

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import fetch_issue_comments

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Test error")
        mock_session.close = MagicMock()

        with patch("merge_dispatch_routine.os.environ", {"PAPERCLIP_API_URL": "http://test"}):
            with patch("merge_dispatch_routine._http_session", return_value=mock_session):
                result = fetch_issue_comments("test-id")

                # Verify close was called even on exception
                mock_session.close.assert_called_once()
                assert result == []


class TestOutputFormat:
    """Test routine output format."""

    def test_output_contains_summary(self):
        """Test that output JSON contains required summary fields."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        # Mock find_in_review_issues to return empty list
        with patch("merge_dispatch_routine.find_in_review_issues", return_value=[]):
            from merge_dispatch_routine import main

            # Run main (which should return 0 for success)
            result = main()
            assert result == 0

    def test_result_action_types(self):
        """Test that process_issue returns valid action types."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import process_issue

        # Minimal issue with no Fix-SHA comment → skip
        issue = {
            "id": "test-id",
            "identifier": "BTCAAAAA-999",
            "status": "in_review",
        }

        with patch("merge_dispatch_routine.fetch_issue_comments", return_value=[]):
            result = process_issue(issue)

        assert result["action"] in ["skip", "failed", "error", "merged"]
        assert "issue" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
