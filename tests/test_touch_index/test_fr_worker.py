"""Unit tests for touch_index.fr_worker — no DB or network required."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from touch_index.fr_worker import (
    FRIngestionResult,
    ingest_fr_issue,
    run_fr_worker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine():
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine, conn


# ---------------------------------------------------------------------------
# ingest_fr_issue — source priority
# ---------------------------------------------------------------------------


class TestIngestFrIssue:
    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_comments_are_primary_source(self, mock_comments, mock_git):
        """Files from done-comments take precedence; git is never called."""
        mock_comments.return_value = ["src/foo.py", "src/bar.py"]
        engine, conn = _make_engine()

        result = ingest_fr_issue(
            engine,
            issue_id="issue-uuid-1",
            issue_identifier="BTCAAAAA-1182",
            owner_agent_id="agent-uuid-1",
        )

        mock_comments.assert_called_once_with("issue-uuid-1")
        mock_git.assert_not_called()
        assert result.source == "comments"
        assert result.files_indexed == 2
        assert result.skipped_no_commits is False

    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_falls_back_to_git_when_no_comments(self, mock_comments, mock_git):
        mock_comments.return_value = []
        mock_git.return_value = ["src/optimizer_v3/strategy.py"]
        engine, conn = _make_engine()

        result = ingest_fr_issue(
            engine,
            issue_id="issue-uuid-2",
            issue_identifier="BTCAAAAA-1100",
            owner_agent_id=None,
        )

        mock_git.assert_called_once_with("BTCAAAAA-1100")
        assert result.source == "git"
        assert result.files_indexed == 1

    @patch("touch_index.fr_worker.extract_files_from_text")
    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_falls_back_to_description_when_no_git(
        self, mock_comments, mock_git, mock_desc
    ):
        mock_comments.return_value = []
        mock_git.return_value = []
        mock_desc.return_value = ["src/strategies/base.py"]
        engine, conn = _make_engine()

        result = ingest_fr_issue(
            engine,
            issue_id="issue-uuid-3",
            issue_identifier="BTCAAAAA-900",
            owner_agent_id=None,
            description="Touches `src/strategies/base.py` for the new signal.",
        )

        mock_desc.assert_called_once()
        assert result.source == "description"
        assert result.files_indexed == 1

    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_skipped_when_no_files_found(self, mock_comments, mock_git):
        mock_comments.return_value = []
        mock_git.return_value = []
        engine, conn = _make_engine()

        result = ingest_fr_issue(
            engine,
            issue_id="issue-uuid-4",
            issue_identifier="BTCAAAAA-800",
            owner_agent_id=None,
        )

        conn.execute.assert_not_called()
        assert result.files_indexed == 0
        assert result.skipped_no_commits is True
        assert result.source == "none"

    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_upsert_rows_contain_correct_fields(self, mock_comments, mock_git):
        mock_comments.return_value = ["src/a.py", "src/b.py"]
        engine, conn = _make_engine()

        ingest_fr_issue(
            engine,
            issue_id="issue-uuid-5",
            issue_identifier="BTCAAAAA-1307",
            owner_agent_id="agent-abc",
        )

        conn.execute.assert_called_once()
        rows = conn.execute.call_args[0][1]
        assert len(rows) == 2
        for row in rows:
            assert row["fr_issue_id"] == "issue-uuid-5"
            assert row["fr_identifier"] == "BTCAAAAA-1307"
            assert row["fr_owner_agent_id"] == "agent-abc"
            assert row["file_path"] in {"src/a.py", "src/b.py"}
            assert row["updated_at"] is not None

    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_row_ids_are_unique_uuids(self, mock_comments, mock_git):
        mock_comments.return_value = ["src/x.py", "src/y.py", "src/z.py"]
        engine, conn = _make_engine()

        ingest_fr_issue(engine, "id-999", "BTCAAAAA-999", None)

        rows = conn.execute.call_args[0][1]
        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids)), "each row must have a unique UUID"

    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_none_owner_agent_substituted_with_zero_uuid(self, mock_comments, mock_git):
        mock_comments.return_value = ["src/z.py"]
        engine, conn = _make_engine()

        ingest_fr_issue(engine, "id-000", "BTCAAAAA-000", owner_agent_id=None)

        rows = conn.execute.call_args[0][1]
        assert rows[0]["fr_owner_agent_id"] == "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# run_fr_worker
# ---------------------------------------------------------------------------


class TestRunFrWorker:
    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_processes_all_issues(self, mock_comments, mock_git):
        mock_comments.side_effect = [["src/a.py"], ["src/b.py", "src/c.py"]]
        engine, _ = _make_engine()

        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-10", "assigneeAgentId": "ag-1", "description": ""},
            {"id": "id-2", "identifier": "BTCAAAAA-11", "assigneeAgentId": None, "description": ""},
        ]
        results = run_fr_worker(engine, issues)

        assert len(results) == 2
        assert results[0].issue_identifier == "BTCAAAAA-10"
        assert results[0].files_indexed == 1
        assert results[1].issue_identifier == "BTCAAAAA-11"
        assert results[1].files_indexed == 2

    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_continues_after_per_issue_error(self, mock_comments, mock_git):
        """An exception on one issue must not abort the whole batch."""
        mock_comments.side_effect = [RuntimeError("API error"), ["src/ok.py"]]
        engine, _ = _make_engine()

        issues = [
            {"id": "bad-id", "identifier": "BTCAAAAA-BAD", "assigneeAgentId": None},
            {"id": "ok-id", "identifier": "BTCAAAAA-OK", "assigneeAgentId": None},
        ]
        results = run_fr_worker(engine, issues)

        # Only the successful issue produces a result
        assert len(results) == 1
        assert results[0].issue_identifier == "BTCAAAAA-OK"

    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_empty_issue_list(self, mock_comments):
        engine, _ = _make_engine()
        results = run_fr_worker(engine, [])
        assert results == []
        mock_comments.assert_not_called()

    @patch("touch_index.fr_worker.get_files_for_issue")
    @patch("touch_index.fr_worker.fetch_and_extract")
    def test_missing_description_treated_as_empty(self, mock_comments, mock_git):
        """Issues without a 'description' key must not raise KeyError."""
        mock_comments.return_value = []
        mock_git.return_value = ["src/fallback.py"]
        engine, _ = _make_engine()

        run_fr_worker(engine, [{"id": "id-x", "identifier": "BTCAAAAA-X"}])
        # Should complete without error; git fallback used
