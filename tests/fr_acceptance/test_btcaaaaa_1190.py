"""
Acceptance tests for BTCAAAAA-1190.

FDR: Touch Index bug-close ingestion worker MUST extract source files
     from git commits, issue comments, and description text, then upsert
     them into the touch_index_bug_files table.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1190
Components: src/touch_index/bug_worker.py, src/touch_index/git_extractor.py,
             src/touch_index/comment_extractor.py

Each test maps to exactly one acceptance criterion stated in the FDR.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from touch_index.bug_worker import BugIngestionResult, ingest_bug_issue

pytestmark = [
    pytest.mark.fr("BTCAAAAA-1190"),
    pytest.mark.acceptance,
]

ISSUE_ID = "cccccccc-0000-0000-0000-000000000001"
ISSUE_IDENTIFIER = "BTCAAAAA-1190"
COMPLETED_AT = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)


def _mock_engine():
    conn = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.begin = MagicMock(return_value=ctx)
    engine.connect = MagicMock(return_value=ctx)
    return engine, conn


# ---------------------------------------------------------------------------
# AC-1: Git extraction is the primary source
# ---------------------------------------------------------------------------


def test_ac1_ingest_uses_git_files_when_available():
    """
    AC-1: When git commits reference the bug issue, those files MUST be
    extracted and upserted.  Comment and description extractors MUST NOT
    be consulted.
    """
    engine, conn = _mock_engine()
    git_files = ["src/touch_index/bug_worker.py", "src/touch_index/db.py"]

    with (
        patch("touch_index.bug_worker.get_files_for_issue", return_value=git_files) as mock_git,
        patch("touch_index.bug_worker.fetch_and_extract") as mock_comments,
        patch("touch_index.bug_worker.extract_files_from_text") as mock_text,
    ):
        result = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

    assert result.source == "git"
    assert result.files_indexed == 2
    assert not result.skipped_no_commits
    mock_comments.assert_not_called()
    mock_text.assert_not_called()
    conn.execute.assert_called_once()


# ---------------------------------------------------------------------------
# AC-2: Comment fallback when git returns nothing
# ---------------------------------------------------------------------------


def test_ac2_comment_fallback_when_git_empty():
    """
    AC-2: When git returns no files, the system MUST fall back to
    Paperclip comment extraction.  Description extractor MUST NOT be
    consulted when comments return files.
    """
    engine, conn = _mock_engine()
    comment_files = ["src/touch_index/comment_extractor.py"]

    with (
        patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
        patch(
            "touch_index.bug_worker.fetch_and_extract", return_value=comment_files
        ) as mock_comments,
        patch("touch_index.bug_worker.extract_files_from_text") as mock_text,
    ):
        result = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

    assert result.source == "comments"
    assert result.files_indexed == 1
    assert not result.skipped_no_commits
    mock_comments.assert_called_once_with(ISSUE_ID)
    mock_text.assert_not_called()
    conn.execute.assert_called_once()


# ---------------------------------------------------------------------------
# AC-3: Description fallback when git and comments both empty
# ---------------------------------------------------------------------------


def test_ac3_description_fallback_when_git_and_comments_empty():
    """
    AC-3: When both git and comments return no files, the system MUST
    fall back to extracting file paths from the issue description text.
    """
    engine, conn = _mock_engine()
    desc = "Fixed bug in `src/touch_index/bug_worker.py` and `src/touch_index/db.py`"

    with (
        patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
        patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        patch(
            "touch_index.bug_worker.extract_files_from_text",
            return_value=["src/touch_index/bug_worker.py", "src/touch_index/db.py"],
        ) as mock_extract,
    ):
        result = ingest_bug_issue(
            engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT, description=desc
        )

    assert result.source == "description"
    assert result.files_indexed == 2
    assert not result.skipped_no_commits
    mock_extract.assert_called_once_with(desc)
    conn.execute.assert_called_once()


# ---------------------------------------------------------------------------
# AC-4: Graceful skip when no files from any source
# ---------------------------------------------------------------------------


def test_ac4_skip_when_all_sources_empty():
    """
    AC-4: When git, comments, and description all yield no files, the
    system MUST return a skipped result without attempting a DB upsert.
    """
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


# ---------------------------------------------------------------------------
# AC-5: Upsert rows carry all required fields
# ---------------------------------------------------------------------------


def test_ac5_upsert_rows_contain_all_required_fields():
    """
    AC-5: Each upserted row MUST carry id, file_path, bug_issue_id,
    bug_identifier, closed_at, source, and updated_at with correct values.
    """
    engine, conn = _mock_engine()
    files = ["src/touch_index/bug_worker.py", "src/touch_index/git_extractor.py"]

    with (
        patch("touch_index.bug_worker.get_files_for_issue", return_value=files),
        patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
    ):
        ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

    rows = conn.execute.call_args[0][1]
    assert len(rows) == 2
    for row in rows:
        assert isinstance(row["id"], str) and len(row["id"]) > 0
        assert row["file_path"] in files
        assert row["bug_issue_id"] == ISSUE_ID
        assert row["bug_identifier"] == ISSUE_IDENTIFIER
        assert row["closed_at"] == COMPLETED_AT
        assert row["source"] == "git"
        assert "updated_at" in row


# ---------------------------------------------------------------------------
# AC-6: Null completed_at is accepted
# ---------------------------------------------------------------------------


def test_ac6_null_completed_at_accepted():
    """
    AC-6: An issue without a completedAt timestamp MUST be ingested
    without error, recording closed_at as None.
    """
    engine, conn = _mock_engine()

    with (
        patch(
            "touch_index.bug_worker.get_files_for_issue", return_value=["src/a.py"]
        ),
    ):
        result = ingest_bug_issue(
            engine, ISSUE_ID, ISSUE_IDENTIFIER, completed_at=None
        )

    rows = conn.execute.call_args[0][1]
    assert rows[0]["closed_at"] is None
    assert result.files_indexed == 1


# ---------------------------------------------------------------------------
# AC-7: Row IDs are unique UUIDs per file
# ---------------------------------------------------------------------------


def test_ac7_each_row_has_unique_id():
    """
    AC-7: Every upsert row MUST receive a unique UUID so that no two
    rows share the same primary key.
    """
    engine, conn = _mock_engine()

    with (
        patch(
            "touch_index.bug_worker.get_files_for_issue",
            return_value=["src/a.py", "src/b.py", "src/c.py"],
        ),
    ):
        ingest_bug_issue(engine, "id-xyz", "BTCAAAAA-700", None)

    rows = conn.execute.call_args[0][1]
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "each row must have a unique UUID"


# ---------------------------------------------------------------------------
# AC-8: BugIngestionResult carries correct metadata
# ---------------------------------------------------------------------------


def test_ac8_result_dataclass_contains_required_fields():
    """
    AC-8: The returned BugIngestionResult MUST include issue_id,
    issue_identifier, files_indexed, source, and skipped_no_commits.
    """
    engine, _ = _mock_engine()

    with (
        patch(
            "touch_index.bug_worker.get_files_for_issue", return_value=["src/a.py"]
        ),
    ):
        result = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

    assert isinstance(result, BugIngestionResult)
    assert result.issue_id == ISSUE_ID
    assert result.issue_identifier == ISSUE_IDENTIFIER
    assert result.files_indexed == 1
    assert result.source == "git"
    assert result.skipped_no_commits is False


# ---------------------------------------------------------------------------
# AC-9: Dry-run mode skips DB write
# ---------------------------------------------------------------------------


def test_ac9_dry_run_skips_db_upsert():
    """
    AC-9: When dry_run=True, the system MUST extract files but MUST NOT
    execute any database write.
    """
    engine, conn = _mock_engine()
    files = ["src/touch_index/bug_worker.py"]

    with (
        patch(
            "touch_index.bug_worker.get_files_for_issue", return_value=files
        ) as mock_git,
    ):
        result = ingest_bug_issue(
            engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT, dry_run=True
        )

    assert result.source == "git"
    assert result.files_indexed == 1
    mock_git.assert_called_once()
    conn.execute.assert_not_called()
