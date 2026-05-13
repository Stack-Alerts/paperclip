"""
Regression tests for BTCAAAAA-1185.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1185
Fixed in commits: 6f9fa85, b7e2042
Component: src/touch_index/bug_worker.py

Root cause: bug_worker.ingest_bug_issue() used git-commit lookup only.
When fix commits predated the bug association on GitHub (so earlier
commits didn't reference the bug ID in their messages), the git
extractor missed the main implementation files. Per the bug report,
BTCAAAAA-691's main implementation in src/ai_consultant/audit_writer.py
was committed in a "prior heartbeat" — only .coveragerc and the test
file were found by git lookup.

Fix: add description text extraction as a third-tier fallback after
git lookup and comment extraction. Mirrors fr_worker's behavior:
git -> comments -> description.

This file tests the full fallback chain end-to-end: when both git and
comments return no files, the issue description text is parsed for
file paths.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from touch_index.bug_worker import BugIngestionResult, ingest_bug_issue

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1185"),
    pytest.mark.regression,
]


class TestBTCAAAAA1185Regression:
    """Regression tests for BTCAAAAA-1185: description fallback in bug_worker."""

    def test_description_fallback_finds_files_when_git_and_comments_empty(self) -> None:
        """Verifies the core bug fix: when git+comments yield nothing,
        the issue description is parsed as a third-tier fallback."""
        mock_engine = MagicMock()

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            result = ingest_bug_issue(
                engine=mock_engine,
                issue_id="test-id",
                issue_identifier="BTCAAAAA-1185",
                completed_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
                description="Fixed in `src/touch_index/bug_worker.py` and `src/touch_index/comment_extractor.py`",
                dry_run=False,
            )

        assert isinstance(result, BugIngestionResult)
        assert result.source == "description"
        assert result.files_indexed > 0

    def test_git_still_takes_priority_when_commits_available(self) -> None:
        """Git lookup should still be the primary source when it finds files."""
        mock_engine = MagicMock()

        with patch(
            "touch_index.bug_worker.get_files_for_issue",
            return_value=["src/touch_index/bug_worker.py"],
        ):
            result = ingest_bug_issue(
                engine=mock_engine,
                issue_id="test-id",
                issue_identifier="BTCAAAAA-1185",
                completed_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
                description="Some description text",
                dry_run=False,
            )

        assert result.source == "git"
        assert result.files_indexed > 0

    def test_no_fallback_without_description_text(self) -> None:
        """When all three sources are empty, the issue is skipped."""
        mock_engine = MagicMock()

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            result = ingest_bug_issue(
                engine=mock_engine,
                issue_id="test-id",
                issue_identifier="BTCAAAAA-1185",
                completed_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
                description="",
                dry_run=False,
            )

        assert result.source == "none"
        assert result.files_indexed == 0
        assert result.skipped_no_commits is True
