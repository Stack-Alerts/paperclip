"""Unit tests for the bug touch-index ingestion worker.

All external I/O (DB engine, Paperclip API, git subprocess) is mocked so these
tests run offline without a PostgreSQL instance or network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from touch_index.bug_worker import (
    BugIngestionResult,
    _parse_completed_at,
    ingest_bug_issue,
    process_bug_issue,
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

    def test_malformed_timestamp(self):
        """Malformed completedAt returns None instead of crashing."""
        result = _parse_completed_at({"completedAt": "not-a-date", "identifier": "BTCAAAAA-999"})
        assert result is None


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
# ingest_bug_issue
# ---------------------------------------------------------------------------


class TestIngestBugIssue:
    def test_ingest_uses_git_when_available(self):
        """Git returns files -> source is 'git', comment API not called."""
        engine, conn = _mock_engine()
        git_files = ["src/touch_index/bug_worker.py", "src/touch_index/db.py"]

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue", return_value=git_files
            ) as mock_git,
            patch("touch_index.bug_worker.fetch_and_extract") as mock_comments,
        ):
            result = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

        assert result.source == "git"
        assert result.files_indexed == 2
        assert result.skipped_no_commits is False
        mock_comments.assert_not_called()
        conn.execute.assert_called_once()

    def test_ingest_falls_back_to_comments(self):
        """Git returns empty -> comment extractor returns files -> source is 'comments', rows upserted."""
        engine, conn = _mock_engine()
        comment_files = ["src/touch_index/bug_worker.py"]

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch(
                "touch_index.bug_worker.fetch_and_extract", return_value=comment_files
            ) as mock_comments,
        ):
            result = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

        assert result.source == "comments"
        assert result.files_indexed == 1
        assert result.skipped_no_commits is False
        mock_comments.assert_called_once_with(ISSUE_ID)
        conn.execute.assert_called_once()

    def test_ingest_skips_when_both_empty(self):
        """Git and comments both empty -> skipped_no_commits=True, source 'none', nothing inserted."""
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

    def test_upsert_rows_contain_required_fields(self):
        """Each upserted row must carry id, file_path, bug_issue_id, bug_identifier, closed_at, source."""
        engine, conn = _mock_engine()
        files = ["src/touch_index/bug_worker.py", "src/touch_index/db.py"]

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=files),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)

        rows = conn.execute.call_args[0][1]
        assert len(rows) == 2
        for row in rows:
            assert "id" in row
            assert row["file_path"] in files
            assert row["bug_issue_id"] == ISSUE_ID
            assert row["bug_identifier"] == ISSUE_IDENTIFIER
            assert row["closed_at"] == COMPLETED_AT
            assert row["source"] == "git"

    def test_null_closed_at_accepted(self):
        engine, conn = _mock_engine()

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue", return_value=["src/x.py"]
            ),
        ):
            result = ingest_bug_issue(
                engine, ISSUE_ID, ISSUE_IDENTIFIER, completed_at=None
            )

        rows = conn.execute.call_args[0][1]
        assert rows[0]["closed_at"] is None
        assert result.files_indexed == 1

    def test_source_field_on_result(self):
        """BugIngestionResult.source is present and correct for each code path."""
        engine, _ = _mock_engine()

        # git path
        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue", return_value=["src/a.py"]
            ),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            r_git = ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)
        assert hasattr(r_git, "source")
        assert r_git.source == "git"

        # comments path
        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch(
                "touch_index.bug_worker.fetch_and_extract", return_value=["src/b.py"]
            ),
        ):
            r_comments = ingest_bug_issue(
                engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT
            )
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

    def test_row_ids_are_unique_uuids(self):
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

    def test_source_persisted_in_upsert_rows(self):
        """source column is set to 'git' or 'comments' in each upsert row."""
        engine, conn = _mock_engine()

        # git path
        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/a.py"],
            ),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)
        rows_git = conn.execute.call_args[0][1]
        for r in rows_git:
            assert r["source"] == "git"

        # comments path
        conn.reset_mock()
        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch(
                "touch_index.bug_worker.fetch_and_extract",
                return_value=["src/b.py"],
            ),
        ):
            ingest_bug_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT)
        rows_comments = conn.execute.call_args[0][1]
        for r in rows_comments:
            assert r["source"] == "comments"


# ---------------------------------------------------------------------------
# run_bug_worker — batch orchestration
# ---------------------------------------------------------------------------


class TestRunBugWorker:
    def _issues(self, count: int = 2) -> list[dict]:
        return [
            {
                "id": f"cccccccc-0000-0000-0000-{i:012d}",
                "identifier": f"BTCAAAAA-{1200 + i}",
                "completedAt": "2026-05-11T12:00:00Z",
            }
            for i in range(count)
        ]

    def test_returns_one_result_per_issue(self):
        engine, _ = _mock_engine()

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue", return_value=["src/a.py"]
            ),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
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

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue", side_effect=_side_effect
            ),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            results = run_bug_worker(engine, issues)

        # First issue raised, so only the second produces a result
        assert len(results) == 1

    def test_skipped_count_matches_no_files_issues(self):
        engine, _ = _mock_engine()

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            results = run_bug_worker(engine, self._issues(4))

        skipped = sum(1 for r in results if r.skipped_no_commits)
        assert skipped == 4

    def test_total_files_indexed(self):
        engine, _ = _mock_engine()

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/a.py", "src/b.py"],
            ),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            results = run_bug_worker(engine, self._issues(3))

        assert sum(r.files_indexed for r in results) == 6

    def test_null_completed_at_is_accepted(self):
        """Issues without completedAt must not crash -- closed_at is nullable."""
        engine, _ = _mock_engine()
        issues = [
            {"id": ISSUE_ID, "identifier": ISSUE_IDENTIFIER}
        ]  # no completedAt key

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue", return_value=["src/a.py"]
            ),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            results = run_bug_worker(engine, issues)

        assert len(results) == 1
        assert results[0].files_indexed == 1

    def test_empty_issue_list(self):
        engine, _ = _mock_engine()
        results = run_bug_worker(engine, [])
        assert results == []

    def test_missing_completed_at_parsed_as_none(self):
        engine, conn = _mock_engine()

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue", return_value=["src/z.py"]
            ),
        ):
            run_bug_worker(engine, [{"id": "id-x", "identifier": "BTCAAAAA-X"}])

        rows = conn.execute.call_args[0][1]
        assert rows[0]["closed_at"] is None


# ---------------------------------------------------------------------------
# process_bug_issue — single-issue webhook entry point
# ---------------------------------------------------------------------------


class TestProcessBugIssue:
    def test_fetches_and_ingests_issue(self):
        """process_bug_issue fetches issue from API and delegates to ingest_bug_issue."""
        engine, conn = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "status": "done",
            "completedAt": "2026-05-11T12:00:00Z",
        }
        files = ["src/touch_index/bug_worker.py"]

        with (
            patch(
                "touch_index.bug_worker.get_issue_by_id", return_value=issue
            ) as mock_get,
            patch(
                "touch_index.bug_worker.get_files_for_issue", return_value=files
            ) as mock_git,
            patch("touch_index.bug_worker.fetch_and_extract") as mock_comments,
        ):
            result = process_bug_issue(engine, ISSUE_ID)

        assert result is not None
        assert result.files_indexed == 1
        assert result.issue_identifier == ISSUE_IDENTIFIER
        mock_get.assert_called_once_with(ISSUE_ID)
        mock_comments.assert_not_called()
        conn.execute.assert_called_once()

    def test_returns_none_when_issue_not_found(self):
        """When get_issue_by_id returns None, process_bug_issue returns None."""
        engine, _ = _mock_engine()

        with patch(
            "touch_index.bug_worker.get_issue_by_id", return_value=None
        ):
            result = process_bug_issue(engine, "nonexistent-uuid")

        assert result is None

    def test_skips_fdr_labelled_issues(self):
        """FDR-labelled issues should be skipped (handled by FR worker)."""
        engine, _ = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "status": "done",
            "labelIds": ["d523cb2d-acd9-423d-b87a-bb79cee42c40"],
        }

        with (
            patch(
                "touch_index.bug_worker.get_issue_by_id", return_value=issue
            ),
        ):
            result = process_bug_issue(engine, ISSUE_ID)

        assert result is None

    def test_handles_missing_completed_at(self):
        """Issue without completedAt should not crash."""
        engine, conn = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "status": "done",
        }

        with (
            patch(
                "touch_index.bug_worker.get_issue_by_id", return_value=issue
            ),
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/foo.py"],
            ),
        ):
            result = process_bug_issue(engine, ISSUE_ID)

        assert result is not None
        assert result.files_indexed == 1
        rows = conn.execute.call_args[0][1]
        assert rows[0]["closed_at"] is None

    def test_filters_out_fdr_label_ids(self):
        """Non-FDR issues with other labels should pass through."""
        engine, conn = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "status": "done",
            "labelIds": ["some-other-label-uuid"],
            "completedAt": "2026-05-11T12:00:00Z",
        }

        with (
            patch(
                "touch_index.bug_worker.get_issue_by_id", return_value=issue
            ),
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/bar.py"],
            ),
        ):
            result = process_bug_issue(engine, ISSUE_ID)

        assert result is not None
        assert result.files_indexed == 1

    def test_accepts_non_done_issues(self):
        """Non-done issues are now accepted (caller handles transition)."""
        engine, conn = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "status": "in_progress",
        }

        with (
            patch(
                "touch_index.bug_worker.get_issue_by_id", return_value=issue
            ),
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/foo.py"],
            ),
            patch("touch_index.bug_worker.fetch_and_extract", return_value=[]),
        ):
            result = process_bug_issue(engine, ISSUE_ID)

        assert result is not None
        assert result.files_indexed == 1


class TestBugWorkerDryRun:
    def test_dry_run_skips_db_upsert(self):
        """When dry_run=True, the DB upsert is not called but files are reported."""
        engine, conn = _mock_engine()
        files = ["src/touch_index/bug_worker.py", "src/touch_index/db.py"]

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue", return_value=files
            ) as mock_git,
        ):
            result = ingest_bug_issue(
                engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT, dry_run=True
            )

        assert result.source == "git"
        assert result.files_indexed == 2
        assert result.skipped_no_commits is False
        conn.execute.assert_not_called()
        mock_git.assert_called_once()

    def test_dry_run_with_comments_fallback(self):
        """Dry-run with comments fallback should still extract but not upsert."""
        engine, conn = _mock_engine()
        comment_files = ["src/touch_index/bug_worker.py"]

        with (
            patch("touch_index.bug_worker.get_files_for_issue", return_value=[]),
            patch(
                "touch_index.bug_worker.fetch_and_extract", return_value=comment_files
            ),
        ):
            result = ingest_bug_issue(
                engine, ISSUE_ID, ISSUE_IDENTIFIER, COMPLETED_AT, dry_run=True
            )

        assert result.source == "comments"
        assert result.files_indexed == 1
        assert result.skipped_no_commits is False
        conn.execute.assert_not_called()

    def test_dry_run_suppresses_db_upserts_in_batch(self):
        """When dry_run=True on batch, DB upsert is skipped for all issues."""
        engine, conn = _mock_engine()

        with (
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/a.py", "src/b.py"],
            ),
        ):
            results = run_bug_worker(engine, _issues(2), dry_run=True)

        assert len(results) == 2
        assert all(not r.skipped_no_commits for r in results)
        assert sum(r.files_indexed for r in results) == 4
        conn.execute.assert_not_called()

    def test_dry_run_passed_through_process_bug_issue(self):
        """dry_run=True on process_bug_issue is passed through to ingest_bug_issue."""
        engine, conn = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "status": "done",
            "completedAt": "2026-05-11T12:00:00Z",
        }

        with (
            patch(
                "touch_index.bug_worker.get_issue_by_id", return_value=issue
            ),
            patch(
                "touch_index.bug_worker.get_files_for_issue",
                return_value=["src/foo.py"],
            ),
        ):
            result = process_bug_issue(engine, ISSUE_ID, dry_run=True)

        assert result is not None
        assert result.files_indexed == 1
        conn.execute.assert_not_called()


def _issues(count: int = 2) -> list[dict]:
    return [
        {
            "id": f"cccccccc-0000-0000-0000-{i:012d}",
            "identifier": f"BTCAAAAA-{1200 + i}",
            "completedAt": "2026-05-11T12:00:00Z",
        }
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# main() — CLI entry point
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for _run_bug_cli() CLI entry point (formerly bug_worker.main())."""

    def test_main_issue_id_calls_process_bug_issue(self, monkeypatch):
        """When --issue-id is provided, process_bug_issue is called."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        result = BugIngestionResult(
            issue_id=ISSUE_ID,
            issue_identifier="BTCAAAAA-100",
            files_indexed=2,
            source="git",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue", return_value=result
            ) as mock_process,
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
            patch(
                "touch_index.paperclip_client.transition_issue_status"
            ) as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1"],
            )
            main()

        mock_process.assert_called_once_with(engine, "uuid-1", dry_run=False)
        mock_fetch.assert_not_called()
        mock_transition.assert_called_once_with(ISSUE_ID, "done")

    def test_main_issue_id_not_found_logs(self, monkeypatch, caplog):
        """When process_bug_issue returns None, a message is logged."""
        import logging
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.bug_worker.process_bug_issue", return_value=None),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues"),
            caplog.at_level(logging.INFO),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "missing-uuid"],
            )
            main()

        assert any("No bug issue found" in r.message for r in caplog.records)

    def test_main_issue_id_dry_run(self, monkeypatch):
        """--dry-run is passed through to process_bug_issue."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        result = BugIngestionResult(
            issue_id=ISSUE_ID,
            issue_identifier="BTCAAAAA-100",
            files_indexed=2,
            source="git",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue", return_value=result
            ) as mock_process,
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues"),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1", "--dry-run"],
            )
            main()

        mock_process.assert_called_once_with(engine, "uuid-1", dry_run=True)

    def test_main_polling_calls_run_bug_worker(self, monkeypatch):
        """When no --issue-id, run_bug_worker is called with non-FDR issues."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-100", "completedAt": "2026-05-11T10:00:00Z"},
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=issues,
            ),
            patch(
                "touch_index.bug_worker.run_bug_worker",
                return_value=[BugIngestionResult(issue_id="id-1", issue_identifier="BTCAAAAA-100", files_indexed=2, source="git", skipped_no_commits=False)],
            ) as mock_worker,
            patch(
                "touch_index.paperclip_client.transition_issue_status",
            ) as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index"],
            )
            main()

        mock_worker.assert_called_once()
        args, kwargs = mock_worker.call_args
        assert args[0] is engine
        assert args[1] == issues
        assert kwargs.get("dry_run") is False
        mock_transition.assert_called_once_with("id-1", "done")

    def test_main_polling_dry_run(self, monkeypatch):
        """--dry-run is passed through to run_bug_worker."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [{"id": "id-1", "identifier": "BTCAAAAA-100", "completedAt": "2026-05-11T10:00:00Z"}]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=issues,
            ),
            patch(
                "touch_index.bug_worker.run_bug_worker",
                return_value=[],
            ) as mock_worker,
            patch(
                "touch_index.paperclip_client.transition_issue_status",
            ) as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--dry-run"],
            )
            main()

        mock_worker.assert_called_once()
        _, kwargs = mock_worker.call_args
        assert kwargs.get("dry_run") is True
        mock_transition.assert_not_called()

    def test_main_health_check_failure_exits(self, monkeypatch):
        """When health_check returns False, SystemExit is raised."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=False),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index"],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_fetch.assert_not_called()

    def test_main_health_check_failure_emits_json_summary(self, monkeypatch, capsys):
        """--json-summary with health check failure emits JSON before SystemExit."""
        import json
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=False),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--json-summary"],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_fetch.assert_not_called()
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "polling"

    def test_main_no_issues_returns_early(self, monkeypatch, caplog):
        """When no closed non-FDR issues found, run_bug_worker is never called."""
        import logging
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=[],
            ),
            patch("touch_index.bug_worker.run_bug_worker") as mock_worker,
            caplog.at_level(logging.INFO),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index"],
            )
            main()

        mock_worker.assert_not_called()
        assert any("Nothing to do" in r.message for r in caplog.records)

    def test_main_summary_counts_files_and_skipped(self, monkeypatch, caplog):
        """Log summary reflects total files indexed and skipped count."""
        import logging
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
            {"id": "id-2", "identifier": "BTCAAAAA-102", "completedAt": "2026-05-11T10:00:00Z"},
        ]
        results = [
            BugIngestionResult(
                issue_id="id-1",
                issue_identifier="BTCAAAAA-101",
                files_indexed=3,
                source="git",
                skipped_no_commits=False,
            ),
            BugIngestionResult(
                issue_id="id-2",
                issue_identifier="BTCAAAAA-102",
                files_indexed=0,
                source="none",
                skipped_no_commits=True,
            ),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=issues,
            ),
            patch("touch_index.bug_worker.run_bug_worker", return_value=results),
            patch(
                "touch_index.paperclip_client.transition_issue_status",
            ) as mock_transition,
            caplog.at_level(logging.INFO),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index"],
            )
            main()

        assert mock_transition.call_count == 2
        mock_transition.assert_has_calls([
            call("id-1", "done"),
            call("id-2", "done"),
        ])
        summary_logs = [r for r in caplog.records if "issues processed" in r.message]
        assert len(summary_logs) == 1
        msg = summary_logs[0].message
        assert "2 issues" in msg
        assert "3 files" in msg
        assert "1 skipped" in msg

    # -------------------------------------------------------------------
    # --validate flag (polling mode)
    # -------------------------------------------------------------------

    def test_main_validate_polling_passed(self, monkeypatch, caplog):
        """--validate with issues: validation runs and passes."""
        import logging
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=issues,
            ),
            patch("touch_index.bug_worker.run_bug_worker", return_value=[BugIngestionResult(issue_id="id-1", issue_identifier="BTCAAAAA-101", files_indexed=2, source="git", skipped_no_commits=False)]),
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
            patch(
                "touch_index.paperclip_client.transition_issue_status",
            ) as mock_transition,
            caplog.at_level(logging.INFO),
        ):
            mock_quality.return_value.passed = True
            monkeypatch.setattr("sys.argv", ["touch_index", "--validate"])
            main()

        mock_quality.assert_called_once()
        mock_transition.assert_called_once_with("id-1", "done")
        assert any("VALIDATION PASSED" in r.message for r in caplog.records)

    def test_main_validate_polling_failed(self, monkeypatch):
        """--validate with issues: validation failure exits non-zero."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=issues,
            ),
            patch("touch_index.bug_worker.run_bug_worker", return_value=[BugIngestionResult(issue_id="id-1", issue_identifier="BTCAAAAA-101", files_indexed=2, source="git", skipped_no_commits=False)]),
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
            patch(
                "touch_index.paperclip_client.transition_issue_status",
            ) as mock_transition,
        ):
            mock_quality.return_value.passed = False
            monkeypatch.setattr("sys.argv", ["touch_index", "--validate"])
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_transition.assert_called_once_with("id-1", "done")

    def test_main_validate_no_issues_passed(self, monkeypatch, caplog):
        """--validate with no issues: validation runs on existing data."""
        import logging
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=[],
            ),
            patch("touch_index.bug_worker.run_bug_worker") as mock_worker,
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
            caplog.at_level(logging.INFO),
        ):
            mock_quality.return_value.passed = True
            monkeypatch.setattr("sys.argv", ["touch_index", "--validate"])
            main()

        mock_worker.assert_not_called()
        mock_quality.assert_called_once()
        assert any("VALIDATION PASSED" in r.message for r in caplog.records)

    def test_main_validate_no_issues_failed(self, monkeypatch):
        """--validate with no issues: validation failure exits non-zero."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=[],
            ),
            patch("touch_index.bug_worker.run_bug_worker") as mock_worker,
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
        ):
            mock_quality.return_value.passed = False
            monkeypatch.setattr("sys.argv", ["touch_index", "--validate"])
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_worker.assert_not_called()

    def test_main_validate_no_issues_failed_with_json_summary(self, monkeypatch, capsys):
        """--json-summary --validate with no issues: emits JSON summary before exit."""
        import json
        from touch_index.__main__ import _run_bug_cli as main
        from touch_index.quality import BugQualityReport

        engine = MagicMock()
        report = BugQualityReport(
            coverage=None,
            freshness=None,
            consistency=None,
            passed=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=[],
            ),
            patch("touch_index.bug_worker.run_bug_worker") as mock_worker,
            patch("touch_index.quality.run_bug_quality_checks", return_value=report),
        ):
            monkeypatch.setattr("sys.argv", ["touch_index", "--validate", "--json-summary"])
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_worker.assert_not_called()
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "polling"
        assert data["dry_run"] is False
        assert data["quality"] == {"passed": False}

    # -------------------------------------------------------------------
    # --validate with --issue-id (single-issue mode)
    # -------------------------------------------------------------------

    def test_main_validate_issue_id_passed(self, monkeypatch, caplog):
        """--validate --issue-id: validation runs after single-issue processing."""
        import logging
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        result = BugIngestionResult(
            issue_id=ISSUE_ID,
            issue_identifier="BTCAAAAA-100",
            files_indexed=2,
            source="git",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue", return_value=result
            ),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
            patch(
                "touch_index.paperclip_client.transition_issue_status"
            ) as mock_transition,
            caplog.at_level(logging.INFO),
        ):
            mock_quality.return_value.passed = True
            monkeypatch.setattr(
                "sys.argv", ["touch_index", "--issue-id", "uuid-1", "--validate"]
            )
            main()

        mock_fetch.assert_not_called()
        mock_quality.assert_called_once()
        mock_transition.assert_called_once_with(ISSUE_ID, "done")
        assert any("VALIDATION PASSED" in r.message for r in caplog.records)

    def test_main_validate_issue_id_failed(self, monkeypatch):
        """--validate --issue-id: validation failure exits non-zero."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        result = BugIngestionResult(
            issue_id=ISSUE_ID,
            issue_identifier="BTCAAAAA-100",
            files_indexed=2,
            source="git",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue", return_value=result
            ),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues"),
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
            patch(
                "touch_index.paperclip_client.transition_issue_status"
            ) as mock_transition,
        ):
            mock_quality.return_value.passed = False
            monkeypatch.setattr(
                "sys.argv", ["touch_index", "--issue-id", "uuid-1", "--validate"]
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_transition.assert_called_once_with(ISSUE_ID, "done")

    def test_main_validate_issue_id_not_found_skips_validation(self, monkeypatch, caplog):
        """--validate --issue-id when issue not found: validation is skipped."""
        import logging
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue", return_value=None
            ),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues"),
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
            caplog.at_level(logging.INFO),
        ):
            mock_quality.return_value.passed = True
            monkeypatch.setattr(
                "sys.argv", ["touch_index", "--issue-id", "missing", "--validate"]
            )
            main()

        mock_quality.assert_not_called()

    def test_main_validate_not_called_without_flag(self, monkeypatch):
        """Without --validate, quality checks are not called."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=issues,
            ),
            patch("touch_index.bug_worker.run_bug_worker", return_value=[BugIngestionResult(issue_id="id-1", issue_identifier="BTCAAAAA-101", files_indexed=2, source="git", skipped_no_commits=False)]),
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
            patch(
                "touch_index.paperclip_client.transition_issue_status",
            ) as mock_transition,
        ):
            monkeypatch.setattr("sys.argv", ["touch_index"])
            main()

        mock_quality.assert_not_called()
        mock_transition.assert_called_once_with("id-1", "done")

    def test_main_transitions_all_processed_issues(self, monkeypatch, caplog):
        """All processed issues are transitioned to done regardless of current status."""
        from touch_index.__main__ import _run_bug_cli as main
        import logging
        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "status": "done", "completedAt": "2026-05-11T10:00:00Z"},
            {"id": "id-2", "identifier": "BTCAAAAA-102", "status": "in_progress", "completedAt": "2026-05-11T10:00:00Z"},
        ]
        results = [
            BugIngestionResult(issue_id="id-1", issue_identifier="BTCAAAAA-101", files_indexed=2, source="git", skipped_no_commits=False),
            BugIngestionResult(issue_id="id-2", issue_identifier="BTCAAAAA-102", files_indexed=1, source="git", skipped_no_commits=False),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues", return_value=issues),
            patch("touch_index.bug_worker.run_bug_worker", return_value=results),
            patch("touch_index.paperclip_client.transition_issue_status") as mock_transition,
            caplog.at_level(logging.INFO),
        ):
            monkeypatch.setattr("sys.argv", ["touch_index"])
            main()

        # Both issues should be transitioned (status check removed)
        assert mock_transition.call_count == 2
        mock_transition.assert_has_calls([
            call("id-1", "done"),
            call("id-2", "done"),
        ])

    def test_main_transition_error_logged_does_not_crash(self, monkeypatch, caplog):
        """A failed transition is logged but does not halt the worker."""
        from touch_index.__main__ import _run_bug_cli as main
        import logging
        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
        ]
        results = [
            BugIngestionResult(issue_id="id-1", issue_identifier="BTCAAAAA-101", files_indexed=2, source="git", skipped_no_commits=False),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues", return_value=issues),
            patch("touch_index.bug_worker.run_bug_worker", return_value=results),
            patch(
                "touch_index.paperclip_client.transition_issue_status",
                side_effect=RuntimeError("API timeout"),
            ) as mock_transition,
            caplog.at_level(logging.ERROR),
        ):
            monkeypatch.setattr("sys.argv", ["touch_index"])
            main()

        mock_transition.assert_called_once_with("id-1", "done")
        assert any("Failed to mark" in r.message for r in caplog.records)

    def test_main_issue_id_transition_error_logged_does_not_crash(self, monkeypatch, caplog):
        """Single-issue mode: transition failure is logged but does not crash."""
        from touch_index.__main__ import _run_bug_cli as main
        import logging
        engine = MagicMock()
        result = BugIngestionResult(
            issue_id="uuid-1",
            issue_identifier="BTCAAAAA-100",
            files_indexed=2,
            source="git",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.bug_worker.process_bug_issue", return_value=result),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues"),
            patch(
                "touch_index.paperclip_client.transition_issue_status",
                side_effect=RuntimeError("API timeout"),
            ) as mock_transition,
            caplog.at_level(logging.ERROR),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1"],
            )
            main()

        mock_transition.assert_called_once_with("uuid-1", "done")
        assert any("Failed to mark" in r.message for r in caplog.records)

class TestMainProcessBugIssueError:
    """Tests for process_bug_issue exception handling in single-issue CLI path."""

    def test_process_error_raises_system_exit(self, monkeypatch):
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue",
                side_effect=RuntimeError("API timeout"),
            ),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
            patch("touch_index.paperclip_client.transition_issue_status") as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1"],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_fetch.assert_not_called()
        mock_transition.assert_not_called()

    def test_process_error_with_validate_exits_nonzero(self, monkeypatch):
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue",
                side_effect=RuntimeError("API timeout"),
            ),
            patch("touch_index.quality.run_bug_quality_checks") as mock_quality,
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1", "--validate"],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_fetch.assert_not_called()
        mock_quality.assert_not_called()



    def test_process_error_emits_json_summary(self, monkeypatch, capsys):
        """process_bug_issue error with --json-summary emits JSON before SystemExit."""
        import json
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue",
                side_effect=RuntimeError("API timeout"),
            ),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
            patch("touch_index.paperclip_client.transition_issue_status") as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1", "--json-summary"],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_fetch.assert_not_called()
        mock_transition.assert_not_called()
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "single-issue"
        assert data["dry_run"] is False

    def test_json_summary_issue_id_not_found(self, monkeypatch, capsys):
        """--json-summary --issue-id with no match outputs JSON without result field."""
        import json
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.bug_worker.process_bug_issue", return_value=None),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
            patch("touch_index.paperclip_client.transition_issue_status") as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv", ["touch_index", "--issue-id", "missing", "--json-summary"]
            )
            main()

        mock_fetch.assert_not_called()
        mock_transition.assert_not_called()
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "single-issue"
        assert "result" not in data


class TestBugWorkerMain:
    """Tests for bug_worker.main() delegation function."""

    def test_delegates_to_run_bug_cli(self, monkeypatch):
        """bug_worker.main() calls _run_bug_cli() from __main__."""
        from touch_index.bug_worker import main

        with (
            patch("touch_index.__main__._run_bug_cli") as mock_cli,
        ):
            monkeypatch.setattr("sys.argv", ["touch_index"])
            main()

        mock_cli.assert_called_once()

# -------------------------------------------------------------------
# --json-summary flag (single-issue + polling)
# -------------------------------------------------------------------

class TestBugJsonSummary:
    """Tests for --json-summary in the bug worker CLI."""

    def test_json_summary_single_issue(self, monkeypatch, capsys):
        """--json-summary with --issue-id outputs JSON to stdout."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        result = BugIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="git",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.bug_worker.process_bug_issue", return_value=result
            ) as mock_process,
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
            patch(
                "touch_index.paperclip_client.transition_issue_status"
            ) as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1", "--json-summary"],
            )
            main()

        mock_process.assert_called_once()
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "single-issue"
        assert data["result"]["issue_identifier"] == "BTCAAAAA-100"
        assert data["result"]["files_indexed"] == 2

    def test_json_summary_polling(self, monkeypatch, capsys):
        """--json-summary in polling mode outputs JSON to stdout."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
        ]
        results = [
            BugIngestionResult(
                issue_identifier="BTCAAAAA-101",
                issue_id="id-1",
                files_indexed=3,
                source="git",
                skipped_no_commits=False,
            ),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues", return_value=issues),
            patch("touch_index.bug_worker.run_bug_worker", return_value=results),
            patch(
                "touch_index.paperclip_client.transition_issue_status",
            ) as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--json-summary"],
            )
            main()

        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "polling"
        assert data["issues_processed"] == 1
        assert data["total_files_indexed"] == 3

    def test_json_summary_dry_run(self, monkeypatch, capsys):
        """--json-summary with --dry-run sets dry_run field."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
        ]
        results = [
            BugIngestionResult(
                issue_identifier="BTCAAAAA-101",
                issue_id="id-1",
                files_indexed=3,
                source="git",
                skipped_no_commits=False,
            ),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues", return_value=issues),
            patch("touch_index.bug_worker.run_bug_worker", return_value=results),
            patch(
                "touch_index.paperclip_client.transition_issue_status",
            ),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--json-summary", "--dry-run"],
            )
            main()

        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["dry_run"] is True
        assert "quality" not in data

    def test_json_summary_no_issues(self, monkeypatch, capsys):
        """--json-summary with no issues outputs JSON with empty results."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues", return_value=[]),
            patch("touch_index.bug_worker.run_bug_worker") as mock_worker,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--json-summary"],
            )
            main()

        mock_worker.assert_not_called()
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "polling"
        assert data["issues_processed"] == 0
        assert data["total_files_indexed"] == 0

    def test_json_summary_with_validate_polling(self, monkeypatch, capsys):
        """--json-summary --validate in polling mode includes quality report."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
        ]
        results = [
            BugIngestionResult(
                issue_identifier="BTCAAAAA-101",
                issue_id="id-1",
                files_indexed=2,
                source="git",
                skipped_no_commits=False,
            ),
        ]

        qc = MagicMock()
        qc.passed = True
        qc.to_dict.return_value = {"passed": True}

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues", return_value=issues),
            patch("touch_index.bug_worker.run_bug_worker", return_value=results),
            patch("touch_index.quality.run_bug_quality_checks", return_value=qc),
            patch("touch_index.paperclip_client.transition_issue_status"),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--json-summary", "--validate"],
            )
            main()

        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "polling"
        assert data["quality"]["passed"] is True
        assert data["issues_processed"] == 1
        assert data["total_files_indexed"] == 2

    def test_json_summary_with_validate_no_issues(self, monkeypatch, capsys):
        """--json-summary --validate with no issues includes quality report."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        qc = MagicMock()
        qc.passed = True
        qc.to_dict.return_value = {"passed": True}

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues", return_value=[]),
            patch("touch_index.bug_worker.run_bug_worker") as mock_worker,
            patch("touch_index.quality.run_bug_quality_checks", return_value=qc),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--json-summary", "--validate"],
            )
            main()

        mock_worker.assert_not_called()
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "polling"
        assert data["quality"]["passed"] is True
        assert data["issues_processed"] == 0

    def test_json_summary_with_validate_polling_failed(self, monkeypatch, capsys):
        """--json-summary --validate in polling mode emits JSON even on failure."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "completedAt": "2026-05-11T10:00:00Z"},
        ]
        results = [
            BugIngestionResult(
                issue_identifier="BTCAAAAA-101",
                issue_id="id-1",
                files_indexed=2,
                source="git",
                skipped_no_commits=False,
            ),
        ]

        qc = MagicMock()
        qc.passed = False
        qc.to_dict.return_value = {"passed": False}

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues", return_value=issues),
            patch("touch_index.bug_worker.run_bug_worker", return_value=results),
            patch("touch_index.quality.run_bug_quality_checks", return_value=qc),
            patch("touch_index.paperclip_client.transition_issue_status"),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--json-summary", "--validate"],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "polling"
        assert data["quality"]["passed"] is False
        assert data["issues_processed"] == 1
        assert data["total_files_indexed"] == 2

    def test_json_summary_with_validate_issue_id_passed(self, monkeypatch, capsys):
        """--json-summary --issue-id --validate includes quality in JSON."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        result = BugIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="git",
            skipped_no_commits=False,
        )

        qc = MagicMock()
        qc.passed = True
        qc.to_dict.return_value = {"passed": True}

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.bug_worker.process_bug_issue", return_value=result) as mock_process,
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
            patch("touch_index.quality.run_bug_quality_checks", return_value=qc),
            patch("touch_index.paperclip_client.transition_issue_status") as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1", "--validate", "--json-summary"],
            )
            main()

        mock_fetch.assert_not_called()
        mock_transition.assert_called_once_with("uuid-1", "done")
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "single-issue"
        assert data["quality"]["passed"] is True
        assert data["result"]["files_indexed"] == 2


    def test_json_summary_with_validate_issue_id_failed(self, monkeypatch, capsys):
        """--json-summary --issue-id --validate emits JSON even on failure."""
        from touch_index.__main__ import _run_bug_cli as main

        engine = MagicMock()
        result = BugIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="git",
            skipped_no_commits=False,
        )

        qc = MagicMock()
        qc.passed = False
        qc.to_dict.return_value = {"passed": False}

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.bug_worker.process_bug_issue", return_value=result) as mock_process,
            patch("touch_index.paperclip_client.get_closed_non_fdr_issues") as mock_fetch,
            patch("touch_index.quality.run_bug_quality_checks", return_value=qc),
            patch("touch_index.paperclip_client.transition_issue_status") as mock_transition,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1", "--json-summary", "--validate"],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_fetch.assert_not_called()
        mock_transition.assert_called_once_with("uuid-1", "done")
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out.strip())
        assert data["worker"] == "bug"
        assert data["mode"] == "single-issue"
        assert data["quality"]["passed"] is False
        assert data["result"]["files_indexed"] == 2
