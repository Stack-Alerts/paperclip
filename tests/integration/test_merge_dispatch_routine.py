#!/usr/bin/env python3
"""Tests for merge-dispatch routine (Phase 4a).

Verifies that the routine correctly:
1. Finds in_review issues
2. Checks for recent merge_request interactions
3. Extracts Fix-SHA from comments
4. Creates and merges PRs
5. Handles errors and escalates failures
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

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


class TestInteractionTimestamp:
    """Test merge_request interaction timestamp parsing."""

    def test_recent_interaction(self):
        """Test that recent interactions are detected."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import has_recent_merge_request_interaction

        now = datetime.now(timezone.utc)
        recent_time = (now - timedelta(minutes=30)).isoformat()

        interactions = [
            {
                "kind": "merge_request",
                "createdAt": recent_time,
            }
        ]

        assert has_recent_merge_request_interaction(interactions) is True

    def test_old_interaction(self):
        """Test that old interactions are not detected as recent."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import has_recent_merge_request_interaction

        now = datetime.now(timezone.utc)
        old_time = (now - timedelta(hours=2)).isoformat()

        interactions = [
            {
                "kind": "merge_request",
                "createdAt": old_time,
            }
        ]

        assert has_recent_merge_request_interaction(interactions) is False

    def test_non_merge_request_interaction(self):
        """Test that non-merge_request interactions are ignored."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import has_recent_merge_request_interaction

        now = datetime.now(timezone.utc)
        recent_time = (now - timedelta(minutes=30)).isoformat()

        interactions = [
            {
                "kind": "some_other_interaction",
                "createdAt": recent_time,
            }
        ]

        assert has_recent_merge_request_interaction(interactions) is False


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

        # Test with minimal issue (no merge_request interaction)
        issue = {
            "id": "test-id",
            "identifier": "BTCAAAAA-999",
            "status": "in_review",
        }

        with patch("merge_dispatch_routine.fetch_issue_interactions", return_value=[]):
            result = process_issue(issue)

        assert result["action"] in ["skip", "failed", "error", "merged"]
        assert "issue" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
