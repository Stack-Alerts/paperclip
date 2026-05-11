"""Unit tests for touch_index.bug_worker — no DB or network required."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from touch_index.bug_worker import (
    BugIngestionResult,
    _parse_completed_at,
    ingest_bug_issue,
    run_bug_worker,
)


# ---------------------------------------------------------------------------
# _parse_completed_at
# ---------------------------------------------------------------------------


class TestParseCompletedAt:
    def test_z_suffix(self):
        result = _parse_completed_at({"completedAt": "2026-05-11T10:30:00Z"})
        assert result == datetime(2026, 5, 11, 10, 30, 0, tzinfo=timezone.utc)

    def test_missing_key(self):
        assert _parse_completed_at({}) is None

    def test_none_value(self):
        assert _parse_completed_at({"completedAt": None}) is None

    def test_empty_string(self):
        assert _parse_completed_at({"completedAt": ""}) is None


# ---------------------------------------------------------------------------
# ingest_bug_issue
# ---------------------------------------------------------------------------


class TestIngestBugIssue:
    def _make_engine(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)
        return engine, conn

    @patch("touch_index.bug_worker.get_files_for_issue")
    def test_happy_path_upserts_rows(self, mock_git):
        mock_git.return_value = ["src/foo.py", "src/bar.py"]
        engine, conn = self._make_engine()
        closed_at = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)

        result = ingest_bug_issue(
            engine,
            issue_id="aaaa-1111",
            issue_identifier="BTCAAAAA-1183",
            completed_at=closed_at,
        )

        mock_git.assert_called_once_with("BTCAAAAA-1183")
        conn.execute.assert_called_once()
        rows = conn.execute.call_args[0][1]
        assert len(rows) == 2
        paths = {r["file_path"] for r in rows}
        assert paths == {"src/foo.py", "src/bar.py"}
        for row in rows:
            assert row["bug_issue_id"] == "aaaa-1111"
            assert row["bug_identifier"] == "BTCAAAAA-1183"
            assert row["closed_at"] == closed_at

        assert result.issue_identifier == "BTCAAAAA-1183"
        assert result.files_indexed == 2
        assert result.skipped_no_commits is False

    @patch("touch_index.bug_worker.fetch_and_extract")
    @patch("touch_index.bug_worker.get_files_for_issue")
    def test_no_commits_skips(self, mock_git, mock_comments):
        mock_git.return_value = []
        mock_comments.return_value = []
        engine, conn = self._make_engine()

        result = ingest_bug_issue(
            engine,
            issue_id="bbbb-2222",
            issue_identifier="BTCAAAAA-999",
            completed_at=None,
        )

        conn.execute.assert_not_called()
        assert result.files_indexed == 0
        assert result.skipped_no_commits is True

    @patch("touch_index.bug_worker.get_files_for_issue")
    def test_null_closed_at_accepted(self, mock_git):
        mock_git.return_value = ["src/x.py"]
        engine, conn = self._make_engine()

        result = ingest_bug_issue(
            engine, issue_id="cccc-3333", issue_identifier="BTCAAAAA-500", completed_at=None
        )

        rows = conn.execute.call_args[0][1]
        assert rows[0]["closed_at"] is None
        assert result.files_indexed == 1

    @patch("touch_index.bug_worker.get_files_for_issue")
    def test_row_ids_are_unique_uuids(self, mock_git):
        mock_git.return_value = ["src/a.py", "src/b.py", "src/c.py"]
        engine, conn = self._make_engine()

        ingest_bug_issue(engine, "id-xyz", "BTCAAAAA-700", None)

        rows = conn.execute.call_args[0][1]
        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids)), "each row must have a unique UUID"


# ---------------------------------------------------------------------------
# run_bug_worker
# ---------------------------------------------------------------------------


class TestRunBugWorker:
    def _make_engine(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)
        return engine, conn

    @patch("touch_index.bug_worker.get_files_for_issue")
    def test_processes_all_issues(self, mock_git):
        mock_git.side_effect = [["src/a.py"], ["src/b.py", "src/c.py"]]
        engine, _ = self._make_engine()

        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-10", "completedAt": "2026-05-11T10:00:00Z"},
            {"id": "id-2", "identifier": "BTCAAAAA-11", "completedAt": "2026-05-11T10:05:00Z"},
        ]
        results = run_bug_worker(engine, issues)

        assert len(results) == 2
        assert results[0].issue_identifier == "BTCAAAAA-10"
        assert results[0].files_indexed == 1
        assert results[1].issue_identifier == "BTCAAAAA-11"
        assert results[1].files_indexed == 2

    @patch("touch_index.bug_worker.get_files_for_issue")
    def test_continues_after_per_issue_error(self, mock_git):
        """An exception on one issue must not abort the whole batch."""
        mock_git.side_effect = [RuntimeError("git broke"), ["src/ok.py"]]
        engine, _ = self._make_engine()

        issues = [
            {"id": "bad-id", "identifier": "BTCAAAAA-BAD", "completedAt": None},
            {"id": "ok-id", "identifier": "BTCAAAAA-OK", "completedAt": None},
        ]
        results = run_bug_worker(engine, issues)

        # Only the successful issue produces a result
        assert len(results) == 1
        assert results[0].issue_identifier == "BTCAAAAA-OK"

    @patch("touch_index.bug_worker.get_files_for_issue")
    def test_empty_issue_list(self, mock_git):
        engine, _ = self._make_engine()
        results = run_bug_worker(engine, [])
        assert results == []
        mock_git.assert_not_called()

    @patch("touch_index.bug_worker.get_files_for_issue")
    def test_missing_completed_at_parsed_as_none(self, mock_git):
        mock_git.return_value = ["src/z.py"]
        engine, conn = self._make_engine()

        run_bug_worker(engine, [{"id": "id-x", "identifier": "BTCAAAAA-X"}])

        rows = conn.execute.call_args[0][1]
        assert rows[0]["closed_at"] is None
