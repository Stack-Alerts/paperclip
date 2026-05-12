"""Unit tests for the FR touch-index ingestion worker.

All external I/O (DB engine, Paperclip API, git subprocess) is mocked so these
tests run offline without a PostgreSQL instance or network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from touch_index.paperclip_client import FDR_LABEL_ID

from touch_index.fr_worker import (
    FRIngestionResult,
    ingest_fr_issue,
    main,
    process_fr_issue,
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

        rows = conn.execute.call_args[0][1]
        assert len(rows) == 2
        for row in rows:
            assert "id" in row
            assert row["file_path"] in files
            assert row["fr_issue_id"] == ISSUE_ID
            assert row["fr_identifier"] == ISSUE_IDENTIFIER
            assert row["fr_owner_agent_id"] == OWNER_AGENT_ID
            assert row["source"] == "comments"
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

    def test_dry_run_skips_db_upsert(self):
        """When dry_run=True, the DB upsert is not called but files are reported."""
        engine, conn = _mock_engine()
        files = ["src/touch_index/fr_worker.py", "src/touch_index/db.py"]

        with (
            patch(
                "touch_index.fr_worker.fetch_and_extract", return_value=files
            ) as mock_comments,
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            result = ingest_fr_issue(
                engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID, dry_run=True
            )

        assert result.source == "comments"
        assert result.files_indexed == 2
        assert result.skipped_no_commits is False
        conn.execute.assert_not_called()
        mock_comments.assert_called_once()

    def test_dry_run_still_extracts_files_from_all_sources(self):
        """Dry-run should still attempt all file extraction strategies."""
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
                dry_run=True,
            )

        assert result.source == "description"
        assert result.files_indexed == 1
        assert result.skipped_no_commits is False
        mock_desc.assert_called_once_with(description)
        conn.execute.assert_not_called()

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

    def test_source_field_persisted_in_upsert_rows(self):
        """source column is populated correctly for each extraction path."""
        engine, conn = _mock_engine()

        # comments path
        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=["src/comments.py"]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            ingest_fr_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID)
        rows = conn.execute.call_args[0][1]
        assert rows[0]["source"] == "comments"
        conn.reset_mock()

        # git path
        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=["src/git.py"]),
        ):
            ingest_fr_issue(engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID)
        rows = conn.execute.call_args[0][1]
        assert rows[0]["source"] == "git"
        conn.reset_mock()

        # description path
        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
            patch("touch_index.fr_worker.extract_files_from_text", return_value=["src/desc.py"]),
        ):
            ingest_fr_issue(
                engine, ISSUE_ID, ISSUE_IDENTIFIER, OWNER_AGENT_ID,
                description="Changed src/desc.py",
            )
        rows = conn.execute.call_args[0][1]
        assert rows[0]["source"] == "description"


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

    def test_empty_issue_list(self):
        engine, _ = _mock_engine()
        results = run_fr_worker(engine, [])
        assert results == []

    def test_dry_run_suppresses_db_upserts(self):
        """When dry_run=True on batch, DB upsert is skipped for all issues."""
        engine, conn = _mock_engine()

        with (
            patch(
                "touch_index.fr_worker.fetch_and_extract",
                return_value=["src/a.py", "src/b.py"],
            ),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            results = run_fr_worker(engine, self._issues(2), dry_run=True)

        assert len(results) == 2
        assert all(not r.skipped_no_commits for r in results)
        assert sum(r.files_indexed for r in results) == 4
        conn.execute.assert_not_called()

    def test_missing_description_treated_as_empty(self):
        """Issues without a 'description' key must not raise KeyError."""
        engine, _ = _mock_engine()

        with (
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch(
                "touch_index.fr_worker.get_files_for_issue",
                return_value=["src/fallback.py"],
            ),
        ):
            run_fr_worker(engine, [{"id": "id-x", "identifier": "BTCAAAAA-X"}])
        # Should complete without error; git fallback used


# ---------------------------------------------------------------------------
# process_fr_issue — single-issue webhook entry point
# ---------------------------------------------------------------------------


class TestProcessFrIssue:
    def test_fetches_and_ingests_issue(self):
        """process_fr_issue fetches issue from API and delegates to ingest_fr_issue."""
        engine, conn = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "assigneeAgentId": OWNER_AGENT_ID,
            "description": "Some FR description",
            "labelIds": [FDR_LABEL_ID],
        }
        files = ["src/touch_index/fr_worker.py"]

        with (
            patch(
                "touch_index.fr_worker.get_issue_by_id", return_value=issue
            ) as mock_get,
            patch(
                "touch_index.fr_worker.fetch_and_extract", return_value=files
            ) as mock_comments,
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
        ):
            result = process_fr_issue(engine, ISSUE_ID)

        assert result is not None
        assert result.files_indexed == 1
        assert result.issue_identifier == ISSUE_IDENTIFIER
        mock_get.assert_called_once_with(ISSUE_ID)

    def test_returns_none_when_issue_not_found(self):
        """When get_issue_by_id returns None, process_fr_issue returns None."""
        engine, _ = _mock_engine()

        with patch(
            "touch_index.fr_worker.get_issue_by_id", return_value=None
        ):
            result = process_fr_issue(engine, "nonexistent-uuid")

        assert result is None

    def test_handles_missing_assignee_agent_id(self):
        """Issue without assigneeAgentId should not crash."""
        engine, conn = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "description": "",
            "labelIds": [FDR_LABEL_ID],
        }

        with (
            patch(
                "touch_index.fr_worker.get_issue_by_id", return_value=issue
            ),
            patch(
                "touch_index.fr_worker.fetch_and_extract",
                return_value=["src/foo.py"],
            ),
        ):
            result = process_fr_issue(engine, ISSUE_ID)

        assert result is not None
        assert result.files_indexed == 1

    def test_returns_none_when_not_fdr_labelled(self):
        """Issues without the FDR label should be rejected."""
        engine, _ = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "assigneeAgentId": OWNER_AGENT_ID,
            "description": "Some description",
            "labelIds": ["other-label-uuid"],
        }

        with patch(
            "touch_index.fr_worker.get_issue_by_id", return_value=issue
        ):
            result = process_fr_issue(engine, ISSUE_ID)

        assert result is None

    def test_dry_run_passed_to_ingest(self):
        """dry_run=True on process_fr_issue is passed through to ingest_fr_issue."""
        engine, _ = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "assigneeAgentId": OWNER_AGENT_ID,
            "description": "",
            "labelIds": [FDR_LABEL_ID],
        }

        with (
            patch(
                "touch_index.fr_worker.get_issue_by_id", return_value=issue
            ),
            patch(
                "touch_index.fr_worker.fetch_and_extract",
                return_value=["src/foo.py"],
            ) as mock_comments,
        ):
            result = process_fr_issue(engine, ISSUE_ID, dry_run=True)

        assert result is not None
        assert result.files_indexed == 1
        mock_comments.assert_called_once()

    def test_passes_description_to_ingest(self):
        """Description from the fetched issue must be passed to ingest_fr_issue."""
        engine, _ = _mock_engine()
        issue = {
            "id": ISSUE_ID,
            "identifier": ISSUE_IDENTIFIER,
            "assigneeAgentId": OWNER_AGENT_ID,
            "description": "Changed `src/optimizer_v3/core.py` to fix XYZ",
            "labelIds": [FDR_LABEL_ID],
        }

        with (
            patch(
                "touch_index.fr_worker.get_issue_by_id", return_value=issue
            ),
            patch("touch_index.fr_worker.fetch_and_extract", return_value=[]),
            patch("touch_index.fr_worker.get_files_for_issue", return_value=[]),
            patch(
                "touch_index.fr_worker.extract_files_from_text",
                return_value=["src/optimizer_v3/core.py"],
            ) as mock_desc,
        ):
            result = process_fr_issue(engine, ISSUE_ID)

        assert result is not None
        assert result.source == "description"
        assert result.files_indexed == 1
        mock_desc.assert_called_once_with(issue["description"])
# ---------------------------------------------------------------------------
# main() — CLI entry point
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for fr_worker.main() CLI entry point."""

    # Note: main() imports get_engine / health_check locally via
    # "from .db import ...", so we patch at the definition site
    # (touch_index.db.get_engine, touch_index.db.health_check).

    def test_main_issue_id_calls_process_fr_issue(self, monkeypatch):
        """When --issue-id is provided, process_fr_issue is called."""
        engine = MagicMock()
        result = FRIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="comments",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.fr_worker.process_fr_issue", return_value=result
            ) as mock_process,
            patch("touch_index.paperclip_client.get_fdr_issues") as mock_fetch,
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
        mock_transition.assert_called_once_with("uuid-1", "done")

    def test_main_issue_id_not_found_logs(self, monkeypatch, caplog):
        """When process_fr_issue returns None, a message is logged."""
        import logging

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.fr_worker.process_fr_issue", return_value=None
            ),
            patch("touch_index.paperclip_client.get_fdr_issues"),
            caplog.at_level(logging.INFO),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "missing-uuid"],
            )
            main()

        assert any("No FR issue found" in r.message for r in caplog.records)

    def test_main_issue_id_dry_run(self, monkeypatch):
        """--dry-run is passed through to process_fr_issue."""
        engine = MagicMock()
        result = FRIngestionResult(
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
                "touch_index.fr_worker.process_fr_issue", return_value=result
            ) as mock_process,
            patch("touch_index.paperclip_client.get_fdr_issues"),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1", "--dry-run"],
            )
            main()

        mock_process.assert_called_once_with(engine, "uuid-1", dry_run=True)

    def test_main_polling_calls_run_fr_worker(self, monkeypatch):
        """When no --issue-id, run_fr_worker is called with FDR issues."""
        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-100", "description": ""},
        ]
        worker_results = [
            FRIngestionResult(
                issue_identifier="BTCAAAAA-100",
                issue_id="id-1",
                files_indexed=2,
                source="git",
                skipped_no_commits=False,
            ),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_fdr_issues", return_value=issues
            ),
            patch(
                "touch_index.fr_worker.run_fr_worker",
                return_value=worker_results,
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
        """--dry-run is passed through to run_fr_worker."""
        engine = MagicMock()
        issues = [{"id": "id-1", "identifier": "BTCAAAAA-100", "description": ""}]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch(
                "touch_index.fr_worker.run_fr_worker",
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
        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=False),
            patch("touch_index.paperclip_client.get_fdr_issues") as mock_fetch,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index"],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_fetch.assert_not_called()

    def test_main_no_issues_returns_early(self, monkeypatch, caplog):
        """When no FDR issues found, run_fr_worker is never called."""
        import logging

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=[]),
            patch("touch_index.fr_worker.run_fr_worker") as mock_worker,
            caplog.at_level(logging.INFO),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index"],
            )
            main()

        mock_worker.assert_not_called()
        assert any("Nothing to do" in r.message for r in caplog.records)


    # -------------------------------------------------------------------
    # --validate flag (polling mode)
    # -------------------------------------------------------------------

    def test_main_validate_polling_passed(self, monkeypatch, caplog):
        """--validate with issues: validation runs and passes."""
        import logging
        engine = MagicMock()
        issues = [{"id": "id-1", "identifier": "BTCAAAAA-100", "description": ""}]
        worker_results = [
            FRIngestionResult(
                issue_identifier="BTCAAAAA-100",
                issue_id="id-1",
                files_indexed=2,
                source="git",
                skipped_no_commits=False,
            ),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch("touch_index.fr_worker.run_fr_worker", return_value=worker_results),
            patch("touch_index.quality.run_quality_checks") as mock_quality,
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
        engine = MagicMock()
        issues = [{"id": "id-1", "identifier": "BTCAAAAA-100", "description": ""}]
        worker_results = [
            FRIngestionResult(
                issue_identifier="BTCAAAAA-100",
                issue_id="id-1",
                files_indexed=2,
                source="git",
                skipped_no_commits=False,
            ),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch("touch_index.fr_worker.run_fr_worker", return_value=worker_results),
            patch("touch_index.quality.run_quality_checks") as mock_quality,
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
        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=[]),
            patch("touch_index.fr_worker.run_fr_worker") as mock_worker,
            patch("touch_index.quality.run_quality_checks") as mock_quality,
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
        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=[]),
            patch("touch_index.fr_worker.run_fr_worker") as mock_worker,
            patch("touch_index.quality.run_quality_checks") as mock_quality,
        ):
            mock_quality.return_value.passed = False
            monkeypatch.setattr("sys.argv", ["touch_index", "--validate"])
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_worker.assert_not_called()

    # -------------------------------------------------------------------
    # --validate with --issue-id (single-issue mode)
    # -------------------------------------------------------------------

    def test_main_validate_issue_id_passed(self, monkeypatch, caplog):
        """--validate --issue-id: validation runs after single-issue processing."""
        import logging
        engine = MagicMock()
        result = FRIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="comments",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.fr_worker.process_fr_issue", return_value=result),
            patch("touch_index.paperclip_client.get_fdr_issues") as mock_fetch,
            patch("touch_index.quality.run_quality_checks") as mock_quality,
            patch(
                "touch_index.paperclip_client.transition_issue_status"
            ),
            caplog.at_level(logging.INFO),
        ):
            mock_quality.return_value.passed = True
            monkeypatch.setattr(
                "sys.argv", ["touch_index", "--issue-id", "uuid-1", "--validate"]
            )
            main()

        mock_fetch.assert_not_called()
        mock_quality.assert_called_once()
        assert any("VALIDATION PASSED" in r.message for r in caplog.records)

    def test_main_validate_issue_id_failed(self, monkeypatch):
        """--validate --issue-id: validation failure exits non-zero."""
        engine = MagicMock()
        result = FRIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="comments",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.fr_worker.process_fr_issue", return_value=result),
            patch("touch_index.paperclip_client.get_fdr_issues"),
            patch("touch_index.quality.run_quality_checks") as mock_quality,
            patch(
                "touch_index.paperclip_client.transition_issue_status"
            ),
        ):
            mock_quality.return_value.passed = False
            monkeypatch.setattr(
                "sys.argv", ["touch_index", "--issue-id", "uuid-1", "--validate"]
            )
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    # -------------------------------------------------------------------
    # --json-summary flag (single-issue + polling)
    # -------------------------------------------------------------------

    def test_main_json_summary_single_issue(self, monkeypatch, capsys):
        """--json-summary with --issue-id outputs JSON to stdout."""
        engine = MagicMock()
        result = FRIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="comments",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.fr_worker.process_fr_issue", return_value=result
            ) as mock_process,
            patch("touch_index.paperclip_client.get_fdr_issues") as mock_fetch,
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
        assert data["worker"] == "fr"
        assert data["mode"] == "single-issue"
        assert data["result"]["issue_identifier"] == "BTCAAAAA-100"
        assert data["result"]["files_indexed"] == 2

    def test_main_json_summary_polling(self, monkeypatch, capsys):
        """--json-summary in polling mode outputs JSON to stdout."""
        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "description": ""},
        ]
        results = [
            FRIngestionResult(
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
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch("touch_index.fr_worker.run_fr_worker", return_value=results),
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
        assert data["worker"] == "fr"
        assert data["mode"] == "polling"
        assert data["issues_processed"] == 1
        assert data["total_files_indexed"] == 3

    def test_main_json_summary_dry_run(self, monkeypatch, capsys):
        """--json-summary with --dry-run sets dry_run field."""
        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "description": ""},
        ]
        results = [
            FRIngestionResult(
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
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch("touch_index.fr_worker.run_fr_worker", return_value=results),
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

    def test_main_validate_issue_id_not_found_skips_validation(self, monkeypatch, caplog):
        """--validate --issue-id when issue not found: validation is skipped."""
        import logging
        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.fr_worker.process_fr_issue", return_value=None),
            patch("touch_index.paperclip_client.get_fdr_issues"),
            patch("touch_index.quality.run_quality_checks") as mock_quality,
            caplog.at_level(logging.INFO),
        ):
            mock_quality.return_value.passed = True
            monkeypatch.setattr(
                "sys.argv", ["touch_index", "--issue-id", "missing", "--validate"]
            )
            main()

        mock_quality.assert_not_called()
    def test_main_json_summary_issue_id_not_found(self, monkeypatch, capsys):
        """--json-summary --issue-id with no match outputs JSON without result field."""
        import json
        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.fr_worker.process_fr_issue", return_value=None),
            patch("touch_index.paperclip_client.get_fdr_issues"),
            patch("touch_index.paperclip_client.transition_issue_status"),
        ):
            monkeypatch.setattr(
                "sys.argv", ["touch_index", "--issue-id", "missing", "--json-summary"]
            )
            main()

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "fr"
        assert data["mode"] == "single-issue"
        assert "result" not in data
    def test_main_summary_counts_files_and_skipped(self, monkeypatch, caplog):
        """Log summary reflects total files indexed and skipped count."""
        import logging

        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "description": ""},
            {"id": "id-2", "identifier": "BTCAAAAA-102", "description": ""},
        ]
        results = [
            FRIngestionResult(
                issue_identifier="BTCAAAAA-101",
                issue_id="id-1",
                files_indexed=3,
                source="comments",
                skipped_no_commits=False,
            ),
            FRIngestionResult(
                issue_identifier="BTCAAAAA-102",
                issue_id="id-2",
                files_indexed=0,
                source="none",
                skipped_no_commits=True,
            ),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch("touch_index.fr_worker.run_fr_worker", return_value=results),
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

    def test_main_transitions_all_processed_results(self, monkeypatch, caplog):
        """All processed results are transitioned regardless of original issue status."""
        import logging
        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "status": "done", "description": ""},
            {"id": "id-2", "identifier": "BTCAAAAA-102", "status": "in_progress", "description": ""},
        ]
        results = [
            FRIngestionResult(issue_identifier="BTCAAAAA-101", issue_id="id-1", files_indexed=2, source="comments", skipped_no_commits=False),
            FRIngestionResult(issue_identifier="BTCAAAAA-102", issue_id="id-2", files_indexed=1, source="git", skipped_no_commits=False),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch("touch_index.fr_worker.run_fr_worker", return_value=results),
            patch("touch_index.paperclip_client.transition_issue_status") as mock_transition,
            caplog.at_level(logging.INFO),
        ):
            monkeypatch.setattr("sys.argv", ["touch_index"])
            main()

        # Both results are transitioned (results-based iteration, not issues)
        assert mock_transition.call_count == 2
        mock_transition.assert_has_calls([
            call("id-1", "done"),
            call("id-2", "done"),
        ])

    def test_main_transition_error_logged_does_not_crash(self, monkeypatch, caplog):
        """A failed transition is logged but does not halt the worker."""
        import logging
        engine = MagicMock()
        issues = [
            {"id": "id-1", "identifier": "BTCAAAAA-101", "description": ""},
        ]
        results = [
            FRIngestionResult(issue_identifier="BTCAAAAA-101", issue_id="id-1", files_indexed=2, source="comments", skipped_no_commits=False),
        ]

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch("touch_index.fr_worker.run_fr_worker", return_value=results),
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
        import logging
        engine = MagicMock()
        result = FRIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="comments",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.fr_worker.process_fr_issue", return_value=result),
            patch("touch_index.paperclip_client.get_fdr_issues"),
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


class TestMainProcessFrIssueError:
    """Tests for process_fr_issue exception handling in single-issue CLI path."""

    def test_process_error_raises_system_exit(self, monkeypatch):
        from touch_index.__main__ import _run_fr_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.fr_worker.process_fr_issue",
                side_effect=RuntimeError("API timeout"),
            ),
            patch("touch_index.paperclip_client.get_fdr_issues") as mock_fetch,
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
        from touch_index.__main__ import _run_fr_cli as main

        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.fr_worker.process_fr_issue",
                side_effect=RuntimeError("API timeout"),
            ),
            patch("touch_index.quality.run_quality_checks") as mock_quality,
            patch("touch_index.paperclip_client.get_fdr_issues") as mock_fetch,
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

    # -------------------------------------------------------------------
    # --json-summary with --validate (quality_report coverage)
    # -------------------------------------------------------------------

    def test_main_json_summary_with_validate_single_issue(self, monkeypatch, capsys):
        """--json-summary with --validate --issue-id includes quality in JSON."""
        import json
        engine = MagicMock()
        result = FRIngestionResult(
            issue_identifier="BTCAAAAA-100",
            issue_id="uuid-1",
            files_indexed=2,
            source="comments",
            skipped_no_commits=False,
        )

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.fr_worker.process_fr_issue", return_value=result),
            patch("touch_index.paperclip_client.get_fdr_issues") as mock_fetch,
            patch("touch_index.quality.run_quality_checks") as mock_quality,
            patch("touch_index.paperclip_client.transition_issue_status"),
        ):
            mock_quality.return_value.passed = True
            mock_quality.return_value.to_dict.return_value = {"passed": True}
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--issue-id", "uuid-1", "--validate", "--json-summary"],
            )
            main()

        mock_fetch.assert_not_called()
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "fr"
        assert data["mode"] == "single-issue"
        assert data["quality"]["passed"] is True

    def test_main_json_summary_with_validate_polling(self, monkeypatch, capsys):
        """--json-summary with --validate in polling mode includes quality in JSON."""
        import json
        engine = MagicMock()
        issues = [{"id": "id-1", "identifier": "BTCAAAAA-101", "description": ""}]
        results = [
            FRIngestionResult(
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
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=issues),
            patch("touch_index.fr_worker.run_fr_worker", return_value=results),
            patch("touch_index.quality.run_quality_checks") as mock_quality,
            patch("touch_index.paperclip_client.transition_issue_status"),
        ):
            mock_quality.return_value.passed = True
            mock_quality.return_value.to_dict.return_value = {"passed": True}
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--validate", "--json-summary"],
            )
            main()

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "fr"
        assert data["mode"] == "polling"
        assert data["quality"]["passed"] is True

    def test_main_json_summary_no_issues(self, monkeypatch, capsys):
        """--json-summary with no FDR issues outputs JSON with zero counts."""
        import json
        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=[]),
            patch("touch_index.fr_worker.run_fr_worker") as mock_worker,
            patch("touch_index.paperclip_client.transition_issue_status"),
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--json-summary"],
            )
            main()

        mock_worker.assert_not_called()
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "fr"
        assert data["mode"] == "polling"
        assert data["issues_processed"] == 0

    def test_main_json_summary_no_issues_with_validate(self, monkeypatch, capsys):
        """--json-summary --validate with no issues outputs quality in JSON."""
        import json
        engine = MagicMock()

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.paperclip_client.get_fdr_issues", return_value=[]),
            patch("touch_index.fr_worker.run_fr_worker") as mock_worker,
            patch("touch_index.quality.run_quality_checks") as mock_quality,
            patch("touch_index.paperclip_client.transition_issue_status"),
        ):
            mock_quality.return_value.passed = True
            mock_quality.return_value.to_dict.return_value = {"passed": True}
            monkeypatch.setattr(
                "sys.argv",
                ["touch_index", "--validate", "--json-summary"],
            )
            main()

        mock_worker.assert_not_called()
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["quality"]["passed"] is True
