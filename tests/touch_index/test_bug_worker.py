"""Unit tests for the bug touch-index ingestion worker.

All external I/O (DB engine, Paperclip API, git subprocess) is mocked so these
tests run offline without a PostgreSQL instance or network.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from touch_index.bug_worker import (
    BugIngestionResult,
    ingest_bug_issue,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_engine():
    """Return a mock SQLAlchemy engine whose context-manager .begin() works."""
    conn = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.begin = MagicMock(return_value=ctx)
    return engine, conn


ISSUE_ID = "cccccccc-0000-0000-0000-000000000001"
ISSUE_IDENTIFIER = "BTCAAAAA-1202"
COMPLETED_AT = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIngestBugIssue:
    def test_ingest_uses_git_when_available(self):
        """Git returns files → source is 'git', comment API not called."""
        engine, conn = _mock_engine()
        git_files = ["src/touch_index/bug_worker.py", "src/touch_index/db.py"]

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=git_files) as mock_git,
            patch("touch_index.bug_worker.fetch_and_extract") as mock_comments,
        ):
            result = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

        assert result.source == "git"
        assert result.files_indexed == 2
        assert result.skipped_no_commits is False
        mock_comments.assert_not_called()
        conn.execute.assert_called_once()

    def test_ingest_falls_back_to_comments(self):
        """Git returns empty → comment extractor returns files → source is 'comments', rows upserted."""
        engine, conn = _mock_engine()
        comment_files = ["src/touch_index/bug_worker.py"]

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=comment_files) as mock_comments,
        ):
            result = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

        assert result.source == "comments"
        assert result.files_indexed == 1
        assert result.skipped_no_commits is False
        mock_comments.assert_called_once_with(ISSUE_ID)
        conn.execute.assert_called_once()

    def test_ingest_skips_when_both_empty(self):
        """Git and comments both empty → skipped_no_commits=True, source 'none', nothing inserted."""
        engine, conn = _mock_engine()

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            result = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

        assert result.source == "none"
        assert result.files_indexed == 0
        assert result.skipped_no_commits is True
        conn.execute.assert_not_called()

    def test_source_field_on_result(self):
        """BugIngestionResult.source is present and correct for each code path."""
        engine, _ = _mock_engine()

        # git path
        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=["src/a.py"]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            r_git = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)
        assert hasattr(r_git, "source")
        assert r_git.source == "git"

        # comments path
        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=["src/b.py"]),
        ):
            r_comments = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)
        assert hasattr(r_comments, "source")
        assert r_comments.source == "comments"

        # none path
        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            r_none = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)
        assert hasattr(r_none, "source")
        assert r_none.source == "none"
