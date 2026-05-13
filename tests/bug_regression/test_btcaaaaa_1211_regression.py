"""
Regression tests for BTCAAAAA-1211: fix test_no_commits_skips — mock fetch_and_extract
after comment fallback was wired into ingest_bug_issue.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1211
Fixed in commit: 79554b98

The comment fallback added to ingest_bug_issue() in bug_worker.py meant the
test_no_commits_skips test needed to also mock fetch_and_extract to stay offline;
without it, the test made a real HTTP call to the Paperclip API and raised a 404.

Components:
  - src/touch_index/bug_worker.py — ingest_bug_issue git→comments→description fallback
  - src/touch_index/comment_extractor.py — fetch_and_extract, extract_files_from_text
  - tests/test_touch_index/test_bug_worker.py — test_no_commits_skips mock coverage
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1211"),
    pytest.mark.regression,
]


class TestCommentExtractorPublicApi:
    """Verify fetch_and_extract is available and properly wired."""

    def test_fetch_and_extract_is_callable(self):
        from touch_index.comment_extractor import fetch_and_extract
        assert callable(fetch_and_extract)

    def test_extract_files_from_text_is_callable(self):
        from touch_index.comment_extractor import extract_files_from_text
        assert callable(extract_files_from_text)


class TestCommentExtractorIntegration:
    """Verify extract_files_from_text correctly identifies source files."""

    def test_extracts_backtick_path(self):
        from touch_index.comment_extractor import extract_files_from_text
        text = "Fixed in `src/touch_index/bug_worker.py` and `tests/test_touch_index/test_bug_worker.py`"
        paths = extract_files_from_text(text)
        assert "src/touch_index/bug_worker.py" in paths
        assert "tests/test_touch_index/test_bug_worker.py" in paths

    def test_filters_non_source_files(self):
        from touch_index.comment_extractor import extract_files_from_text
        text = "See `README.md` and `docs/runbook.md`"
        paths = extract_files_from_text(text)
        assert len(paths) == 0


class TestBugWorkerFallbackChainIntact:
    """Verify the git → comments → description fallback chain in ingest_bug_issue."""

    def test_ingest_bug_issue_imports_fetch_and_extract(self):
        """Ensure bug_worker imports fetch_and_extract from comment_extractor."""
        from touch_index.bug_worker import fetch_and_extract
        assert callable(fetch_and_extract)

    def test_ingest_bug_issue_is_callable(self):
        from touch_index.bug_worker import ingest_bug_issue
        assert callable(ingest_bug_issue)

    def test_bug_ingestion_result_has_source_field(self):
        from touch_index.bug_worker import BugIngestionResult
        fields = BugIngestionResult.__dataclass_fields__
        assert "source" in fields
        assert "skipped_no_commits" in fields


class TestBugWorkerCommentFallbackMockCoverage:
    """Verify that ingest_bug_issue calls fetch_and_extract when git returns no files.
    
    These tests mirror the pattern from test_no_commits_skips:
    when get_files_for_issue returns [], ingest_bug_issue falls back to
    fetch_and_extract (comments) before trying the description fallback.
    """

    def test_fallback_to_comments_when_git_returns_empty(self):
        from unittest.mock import patch
        from sqlalchemy import create_engine
        from touch_index.bug_worker import ingest_bug_issue

        engine = create_engine("sqlite://")
        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]) as mock_comments,
        ):
            result = ingest_bug_issue(
                engine=engine,
                issue_id="test-issue-id",
                issue_identifier="BTCAAAAA-1211",
                completed_at=None,
                description="",
                dry_run=True,
            )
            mock_comments.assert_called_once_with("test-issue-id")
            assert result.skipped_no_commits is True
            assert result.source == "none"

    def test_fallback_to_description_when_both_git_and_comments_empty(self):
        from unittest.mock import patch
        from sqlalchemy import create_engine
        from touch_index.bug_worker import ingest_bug_issue

        engine = create_engine("sqlite://")
        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            result = ingest_bug_issue(
                engine=engine,
                issue_id="test-issue-id-2",
                issue_identifier="BTCAAAAA-1211",
                completed_at=None,
                description="Fixed `src/touch_index/bug_worker.py`",
                dry_run=True,
            )
            assert result.source == "description"
            assert result.skipped_no_commits is False
            assert result.files_indexed == 1
