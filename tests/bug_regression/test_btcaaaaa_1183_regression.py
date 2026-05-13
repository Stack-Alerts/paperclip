"""
Regression tests for BTCAAAAA-1183: bug-close touch index worker unit tests.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1183
Fixed in commits: 690269d4, 2fc7b942
Component: src/touch_index/bug_worker.py

Root cause: The bug-close touch index worker (bug_worker.py) had zero unit
test coverage.  The fix added 12+ tests covering ingest_bug_issue,
run_bug_worker, and _parse_completed_at, achieving 100% branch coverage
on bug_worker.py with no DB or network required.

This regression test verifies that the core functions are importable and
behave correctly under the key scenarios: git lookup, comments fallback,
description fallback, dry-run mode, null closed_at handling, and batch
error resilience.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from touch_index.bug_worker import (
    BugIngestionResult,
    _parse_completed_at,
    catch_up_eligible_bug_issues,
    ingest_bug_issue,
    process_bug_issue,
    run_bug_worker,
)

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1183"),
    pytest.mark.regression,
]


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

    def test_malformed_timestamp(self):
        result = _parse_completed_at({"completedAt": "not-a-date"})
        assert result is None

    def test_non_string_value(self):
        result = _parse_completed_at({"completedAt": 12345})
        assert result is None


# ---------------------------------------------------------------------------
# BugIngestionResult dataclass
# ---------------------------------------------------------------------------


class TestBugIngestionResult:
    def test_fields_set_correctly(self):
        r = BugIngestionResult(
            issue_id="id-1",
            issue_identifier="BTCAAAAA-100",
            files_indexed=3,
            source="git",
            skipped_no_commits=False,
        )
        assert r.issue_id == "id-1"
        assert r.issue_identifier == "BTCAAAAA-100"
        assert r.files_indexed == 3
        assert r.source == "git"
        assert r.skipped_no_commits is False

    def test_skipped_result(self):
        r = BugIngestionResult(
            issue_id="id-2",
            issue_identifier="BTCAAAAA-200",
            files_indexed=0,
            source="none",
            skipped_no_commits=True,
        )
        assert r.skipped_no_commits is True
        assert r.files_indexed == 0
        assert r.source == "none"


# ---------------------------------------------------------------------------
# ingest_bug_issue
# ---------------------------------------------------------------------------


class TestIngestBugIssue:
    def test_git_source_used_when_commits_available(self):
        engine, conn = _mock_engine()

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/a.py", "src/b.py"],
            ),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            result = ingest_bug_issue(
                engine, "uuid-1", "BTCAAAAA-1183",
                datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
            )

        assert result.source == "git"
        assert result.files_indexed == 2
        assert result.skipped_no_commits is False
        conn.execute.assert_called_once()

    def test_comments_fallback_when_git_empty(self):
        engine, conn = _mock_engine()

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch(
                "touch_index.bug_worker.fetch_and_extract",
                return_value=["src/comment_file.py"],
            ),
        ):
            result = ingest_bug_issue(
                engine, "uuid-2", "BTCAAAAA-1183",
                datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
            )

        assert result.source == "comments"
        assert result.files_indexed == 1
        conn.execute.assert_called_once()

    def test_description_fallback_when_both_empty(self):
        engine, conn = _mock_engine()

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
            patch(
                "touch_index.bug_worker.extract_files_from_text",
                return_value=["src/desc_file.py"],
            ),
        ):
            result = ingest_bug_issue(
                engine, "uuid-3", "BTCAAAAA-1183",
                datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
                description="Fixed in `src/desc_file.py`",
            )

        assert result.source == "description"
        assert result.files_indexed == 1
        conn.execute.assert_called_once()

    def test_skips_when_all_sources_empty(self):
        engine, conn = _mock_engine()

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            result = ingest_bug_issue(
                engine, "uuid-4", "BTCAAAAA-1183", None,
            )

        assert result.source == "none"
        assert result.files_indexed == 0
        assert result.skipped_no_commits is True
        conn.execute.assert_not_called()

    def test_null_closed_at_accepted(self):
        engine, conn = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_files_for_issue",
            return_value=["src/x.py"],
        ):
            result = ingest_bug_issue(
                engine, "uuid-5", "BTCAAAAA-1183", completed_at=None,
            )

        rows = conn.execute.call_args[0][1]
        assert rows[0]["closed_at"] is None
        assert result.files_indexed == 1

    def test_dry_run_skips_db_upsert(self):
        engine, conn = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_files_for_issue",
            return_value=["src/a.py", "src/b.py"],
        ):
            result = ingest_bug_issue(
                engine, "uuid-6", "BTCAAAAA-1183",
                datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
                dry_run=True,
            )

        assert result.source == "git"
        assert result.files_indexed == 2
        conn.execute.assert_not_called()

    def test_row_ids_are_unique_uuids(self):
        engine, conn = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_files_for_issue",
            return_value=["src/a.py", "src/b.py", "src/c.py"],
        ):
            ingest_bug_issue(engine, "id-xyz", "BTCAAAAA-700", None)

        rows = conn.execute.call_args[0][1]
        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# run_bug_worker
# ---------------------------------------------------------------------------


class TestRunBugWorker:
    def _issues(self, count=2):
        return [
            {
                "id": f"cccccccc-0000-0000-0000-{i:012d}",
                "identifier": f"BTCAAAAA-{1200 + i}",
                "completedAt": "2026-05-11T12:00:00Z",
            }
            for i in range(count)
        ]

    def test_processes_all_issues(self):
        engine, _ = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_files_for_issue",
            return_value=["src/a.py"],
        ):
            results = run_bug_worker(engine, self._issues(3))

        assert len(results) == 3
        assert all(isinstance(r, BugIngestionResult) for r in results)

    def test_continues_after_per_issue_error(self):
        engine, _ = _mock_engine()
        issues = self._issues(2)

        def _side_effect(identifier):
            if "1200" in identifier:
                raise RuntimeError("Simulated git error")
            return ["src/ok.py"]

        with patch(
            "touch_index.bug_worker.get_files_for_issue",
            side_effect=_side_effect,
        ):
            results = run_bug_worker(engine, issues)

        assert len(results) == 1
        assert results[0].issue_identifier == "BTCAAAAA-1201"

    def test_empty_issue_list(self):
        engine, _ = _mock_engine()

        with patch("touch_index.bug_worker.get_files_for_issue") as mock_git:
            results = run_bug_worker(engine, [])

        assert results == []
        mock_git.assert_not_called()

    def test_dry_run_passed_through(self):
        engine, conn = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_files_for_issue",
            return_value=["src/a.py"],
        ):
            results = run_bug_worker(engine, self._issues(2), dry_run=True)

        assert len(results) == 2
        assert all(not r.skipped_no_commits for r in results)
        conn.execute.assert_not_called()

    def test_total_files_indexed_matches_all_issues(self):
        engine, _ = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_files_for_issue",
            return_value=["src/a.py", "src/b.py"],
        ):
            results = run_bug_worker(engine, self._issues(3))

        assert sum(r.files_indexed for r in results) == 6


# ---------------------------------------------------------------------------
# process_bug_issue
# ---------------------------------------------------------------------------


class TestProcessBugIssue:
    def test_fetches_and_ingests_issue(self):
        engine, conn = _mock_engine()
        issue = {
            "id": "uuid-x",
            "identifier": "BTCAAAAA-1183",
            "status": "done",
            "completedAt": "2026-05-11T12:00:00Z",
        }

        with (
            patch(
                "touch_index.bug_worker.get_issue_by_id", return_value=issue
            ),
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/bug_worker.py"],
            ),
        ):
            result = process_bug_issue(engine, "uuid-x")

        assert result is not None
        assert result.files_indexed == 1
        assert result.issue_identifier == "BTCAAAAA-1183"
        conn.execute.assert_called_once()

    def test_returns_none_when_issue_not_found(self):
        engine, _ = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_issue_by_id", return_value=None,
        ):
            result = process_bug_issue(engine, "nonexistent-uuid")

        assert result is None


# ---------------------------------------------------------------------------
# catch_up_eligible_bug_issues
# ---------------------------------------------------------------------------


class TestCatchUpEligibleBugIssues:
    def test_returns_empty_when_no_git_ids(self):
        engine, _ = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_all_referenced_issue_ids",
            return_value=[],
        ):
            results = catch_up_eligible_bug_issues(engine)

        assert results == []
