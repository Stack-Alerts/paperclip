"""Unit tests for the FR touch-index ingestion worker.

All external I/O (DB engine, Paperclip API, git subprocess) is mocked so these
tests run offline without a PostgreSQL instance or network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from touch_index.fr_worker import (
    FRIngestionResult,
    ingest_fr_issue,
    run_fr_worker,
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


ISSUE_ID = "aaaaaaaa-0000-0000-0000-000000000001"
ISSUE_IDENTIFIER = "BTCAAAAA-1182"
OWNER_AGENT_ID = "bbbbbbbb-0000-0000-0000-000000000002"


# ---------------------------------------------------------------------------
# ingest_fr_issue — file source priority
# ---------------------------------------------------------------------------


class TestIngestFrIssue:
    def test_files_from_comments(self):
        engine, conn = _mock_engine()
        files = ["src/touch_index/fr_worker.py", "src/touch_index/db.py"]

        with (
            patch(
                "touch_index.fr_worker.fetch_and_extract", return_value=files
            ) as mock_comments,
            patch(
                "touch_index.fr_worker.get_files_for_issue", return_value=[]
            ) as mock_git,
        ):
            result = ingest_fr_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID)

        assert result.source == "comments"
        assert result.files_indexed == 2
        assert result.skipped_no_commits is False
        mock_git.assert_not_called()
        conn.execute.assert_called_once()

    def test_falls_back_to_git_when_no_comments(self):
        engine, conn = _mock_engine()
        git_files = ["src/touch_index/fr_worker.py"]

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=git_files),
        ):
            result = ingest_fr_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID)

        assert result.source == "git"
        assert result.files_indexed == 1
        assert result.skipped_no_commits is False

    def test_falls_back_to_description_when_no_comments_no_git(self):
        engine, conn = _mock_engine()
        desc_files = ["src/optimizer_v3/database/strategy_manager.py"]
        description = (
            "Changed `src/optimizer_v3/database/strategy_manager.py` to fix XYZ."
        )

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
            patch(
                "touch_index.fr_worker.extract_files_from_text", return_value=desc_files
            ) as mock_desc,
        ):
            result = ingest_fr_issue(
                engine,
                ISSUE_ID,
                ISSUE_IDENTIFIER,
                OWNER_AGENT_ID,
                description=description,
            )

        assert result.source == "description"
        assert result.files_indexed == 1
        assert result.skipped_no_commits is False
        mock_desc.assert_called_once_with(description)

    def test_skips_when_all_sources_empty(self):
        engine, conn = _mock_engine()

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            result = ingest_fr_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID)

        assert result.source == "none"
        assert result.files_indexed == 0
        assert result.skipped_no_commits is True
        conn.execute.assert_not_called()

    def test_empty_description_not_passed_to_extractor(self):
        """extract_files_from_text must not be called when description is empty."""
        engine, _ = _mock_engine()

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.fr_worker.extract_files_from_text") as mock_desc,
        ):
            result = ingest_fr_issue(
                engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID, description=""
            )

        mock_desc.assert_not_called()
        assert result.skipped_no_commits is True

    def test_upsert_rows_contain_required_fields(self):
        engine, conn = _mock_engine()
        files = ["src/foo.py", "src/bar.py"]

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=files),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            ingest_fr_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID)

        _, rows_arg = conn.execute.call_args
        # conn.execute(sql, rows) — rows is the second positional arg
        rows = conn.execute.call_args[0][1]
        assert len(rows) == 2
        for row in rows:
            assert "id" in row
            assert row["file_path"] in files
            assert row["fr_issue_id"] == ISSUE_ID
            assert row["fr_identifier"] == ISSUE_IDENTIFIER
            assert row["fr_owner_agent_id"] == OWNER_AGENT_ID
            assert isinstance(row["updated_at"], datetime)

    def test_null_owner_replaced_with_sentinel(self):
        engine, conn = _mock_engine()
        files = ["src/foo.py"]

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=files),
        ):
            ingest_fr_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, owner_agent_id=None)

        rows = conn.execute.call_args[0][1]
        assert rows[0]["fr_owner_agent_id"] == "00000000-0000-0000-0000-000000000000"

    def test_description_not_called_when_comments_present(self):
        """Description path must be skipped if comments already found files."""
        engine, _ = _mock_engine()
        files = ["src/touch_index/fr_worker.py"]

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=files),
            patch("touch_index.fr_worker.extract_files_from_text") as mock_desc,
        ):
            result = ingest_fr_issue(
                engine,
                ISSUE_ID,
                ISSUE_IDENTIFIER,
                OWNER_AGENT_ID,
                description="Some description with src/foo.py",
            )

        mock_desc.assert_not_called()
        assert result.source == "comments"


# ---------------------------------------------------------------------------
# run_fr_worker — batch orchestration
# ---------------------------------------------------------------------------


class TestRunFrWorker:
    def _issues(self, count: int = 2) -> list[dict]:
        return [
            {
                "id": f"aaaaaaaa-0000-0000-0000-{i:012d}",
                "identifier": f"BTCAAAAA-{1000 + i}",
                "assigneeAgentId": OWNER_AGENT_ID,
                "description": "",
            }
            for i in range(count)
        ]

    def test_returns_one_result_per_issue(self):
        engine, _ = _mock_engine()

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=["src/a.py"]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            results = run_fr_worker(engine, self._issues(3))

        assert len(results) == 3
        assert all(isinstance(r, FRIngestionResult) for r in results)

    def test_continues_after_per_issue_error(self):
        engine, _ = _mock_engine()
        issues = self._issues(2)

        def _side_effect(issue_id):
            if "000000000000" in issue_id:
                raise RuntimeError("Simulated API error")
            return ["src/ok.py"]

        with (
            patch("touch_index.fr_worker.fetch_and_extract", side_effect=_side_effect),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            results = run_fr_worker(engine, issues)

        # First issue raised, so only the second produces a result
        assert len(results) == 1

    def test_skipped_count_matches_no_files_issues(self):
        engine, _ = _mock_engine()

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            results = run_fr_worker(engine, self._issues(4))

        skipped = sum(1 for r in results if r.skipped_no_commits)
        assert skipped == 4

    def test_total_files_indexed(self):
        engine, _ = _mock_engine()

        with (
            patch(
                "touch_index.fr_worker.fetch_and_extract",
                return_value=["src/a.py", "src/b.py"],
            ),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            results = run_fr_worker(engine, self._issues(3))

        assert sum(r.files_indexed for r in results) == 6
