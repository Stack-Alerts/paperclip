"""Unit tests for impact_gate.polling_worker.

All external I/O (Paperclip API, Blast Radius) is mocked.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from impact_gate.polling_worker import (
    _fetch_done_fix_issues,
    _post_comment,
    _render_gate_comment,
    process_issue,
    run_once,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_issue(
    issue_id: str = "aaa-111",
    identifier: str = "BTCAAAAA-9999",
    status: str = "done",
    title: str = "fix: something broke",
    description: str = "",
    labels: list[dict] | None = None,
    completed_at: str = "2026-05-16T06:00:00Z",
) -> dict:
    return {
        "id": issue_id,
        "identifier": identifier,
        "status": status,
        "title": title,
        "description": description,
        "labels": [{"name": "fix"}] if labels is None else labels,
        "completedAt": completed_at,
    }


# ---------------------------------------------------------------------------
# TestRenderGateComment
# ---------------------------------------------------------------------------


class TestRenderGateComment:
    def test_render_with_files_and_impacts(self):
        comment = _render_gate_comment(
            "BTCAAAAA-123",
            ["src/main.py", "src/utils.py"],
            ["BTCAAAAA-456", "BTCAAAAA-789"],
            ["BTCAAAAA-111", "BTCAAAAA-222"],
        )
        assert "BTCAAAAA-123" in comment
        assert "`src/main.py`" in comment
        assert "`src/utils.py`" in comment
        assert "BTCAAAAA-456" in comment
        assert "BTCAAAAA-789" in comment
        assert "BTCAAAAA-111" in comment
        assert "BTCAAAAA-222" in comment
        assert "Impact Gate" in comment

    def test_render_with_no_touched_files(self):
        comment = _render_gate_comment(
            "BTCAAAAA-123",
            [],
            [],
            [],
        )
        assert "_None_" in comment
        assert "BTCAAAAA-123" in comment

    def test_render_with_only_frs(self):
        comment = _render_gate_comment(
            "BTCAAAAA-123",
            ["src/strategy.py"],
            ["BTCAAAAA-456"],
            [],
        )
        assert "BTCAAAAA-456" in comment
        assert "_None_" in comment  # For regression bugs


# ---------------------------------------------------------------------------
# TestPostComment
# ---------------------------------------------------------------------------


class TestPostComment:
    @patch("impact_gate.polling_worker._board_session")
    def test_post_comment_success(self, mock_session):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.return_value.__enter__.return_value.post.return_value = mock_response

        result = _post_comment("issue-123", "Test comment")
        assert result is True

    @patch("impact_gate.polling_worker._board_session")
    def test_post_comment_failure(self, mock_session):
        mock_session.return_value.__enter__.return_value.post.side_effect = Exception(
            "Network error"
        )

        result = _post_comment("issue-123", "Test comment")
        assert result is False

    def test_post_comment_dry_run(self):
        result = _post_comment("issue-123", "Test comment", dry_run=True)
        assert result is True


# ---------------------------------------------------------------------------
# TestProcessIssue
# ---------------------------------------------------------------------------


class TestProcessIssue:
    @patch("impact_gate.polling_worker.get_issue_by_id")
    @patch("impact_gate.polling_worker.extract_touched_files")
    @patch("impact_gate.polling_worker.query_blast_radius")
    @patch("impact_gate.polling_worker._post_comment")
    def test_process_issue_success(
        self,
        mock_post_comment,
        mock_query_blast,
        mock_extract,
        mock_get_issue,
    ):
        issue = _make_issue(
            issue_id="123",
            identifier="BTCAAAAA-999",
            description="touchedFiles: src/main.py",
        )
        mock_get_issue.return_value = issue
        mock_extract.return_value = ["src/main.py"]

        mock_data = MagicMock()
        mock_fr = MagicMock()
        mock_fr.fr_identifier = "BTCAAAAA-456"
        mock_data.fr_impact_set = [mock_fr]

        mock_reg = MagicMock()
        mock_reg.bug_identifier = "BTCAAAAA-111"
        mock_data.regression_set = [mock_reg]

        mock_query_blast.return_value = mock_data
        mock_post_comment.return_value = True

        result = process_issue("123")
        assert result["status"] == "gated"
        assert result["comment_posted"] is True
        assert result["fr_count"] == 1
        assert result["bug_count"] == 1

    @patch("impact_gate.polling_worker.get_issue_by_id")
    def test_process_issue_not_found(self, mock_get_issue):
        mock_get_issue.return_value = None

        result = process_issue("123")
        assert result["status"] == "not_found"
        assert result["comment_posted"] is False

    @patch("impact_gate.polling_worker.get_issue_by_id")
    @patch("impact_gate.polling_worker.extract_touched_files")
    def test_process_issue_no_files(self, mock_extract, mock_get_issue):
        issue = _make_issue(issue_id="123", identifier="BTCAAAAA-999")
        mock_get_issue.return_value = issue
        mock_extract.return_value = []

        with patch("touch_index.git_extractor.get_files_for_issue", side_effect=Exception("Not found")):
            result = process_issue("123")

        assert result["status"] == "skipped_no_files"
        assert result["comment_posted"] is False


# ---------------------------------------------------------------------------
# TestFetchDoneFixIssues
# ---------------------------------------------------------------------------


class TestFetchDoneFixIssues:
    @patch("impact_gate.polling_worker._paginate")
    @patch("impact_gate.polling_worker._is_fix_issue")
    def test_fetch_done_fix_issues(self, mock_is_fix, mock_paginate):
        issues = [
            _make_issue(issue_id="1", completed_at="2026-05-16T06:05:00Z"),
            _make_issue(issue_id="2", completed_at="2026-05-16T05:00:00Z"),
            _make_issue(
                issue_id="3",
                identifier="BTCAAAAA-100",
                completed_at="2026-05-16T05:50:00Z",
            ),
        ]
        mock_paginate.return_value = issues
        mock_is_fix.side_effect = [True, False, True]

        result = _fetch_done_fix_issues(lookback_minutes=10)
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "3"


# ---------------------------------------------------------------------------
# TestRunOnce
# ---------------------------------------------------------------------------


class TestRunOnce:
    @patch("impact_gate.polling_worker._fetch_done_fix_issues")
    @patch("impact_gate.polling_worker.process_issue")
    def test_run_once_success(self, mock_process, mock_fetch):
        issues = [
            _make_issue(issue_id="1", identifier="BTCAAAAA-1"),
            _make_issue(issue_id="2", identifier="BTCAAAAA-2"),
        ]
        mock_fetch.return_value = issues
        mock_process.side_effect = [
            {"issue": "BTCAAAAA-1", "status": "gated", "comment_posted": True},
            {"issue": "BTCAAAAA-2", "status": "gated", "comment_posted": True},
        ]

        result = run_once()
        assert result["gated"] == 2
        assert result["skipped"] == 0
        assert result["errors"] == 0

    @patch("impact_gate.polling_worker._fetch_done_fix_issues")
    @patch("impact_gate.polling_worker.process_issue")
    def test_run_once_with_deduplication(self, mock_process, mock_fetch):
        issues = [
            _make_issue(issue_id="1", identifier="BTCAAAAA-1"),
            _make_issue(issue_id="1", identifier="BTCAAAAA-1"),  # Duplicate
        ]
        mock_fetch.return_value = issues
        mock_process.return_value = {
            "issue": "BTCAAAAA-1",
            "status": "gated",
            "comment_posted": True,
        }

        cache = set()
        result = run_once(processed_cache=cache)
        assert result["gated"] == 1  # Only processed once
        assert mock_process.call_count == 1

    @patch("impact_gate.polling_worker._fetch_done_fix_issues")
    @patch("impact_gate.polling_worker.process_issue")
    def test_run_once_mixed_results(self, mock_process, mock_fetch):
        issues = [
            _make_issue(issue_id="1", identifier="BTCAAAAA-1"),
            _make_issue(issue_id="2", identifier="BTCAAAAA-2"),
            _make_issue(issue_id="3", identifier="BTCAAAAA-3"),
        ]
        mock_fetch.return_value = issues
        mock_process.side_effect = [
            {"issue": "BTCAAAAA-1", "status": "gated", "comment_posted": True},
            {"issue": "BTCAAAAA-2", "status": "skipped_no_files", "comment_posted": False},
            {"issue": "BTCAAAAA-3", "status": "error", "comment_posted": False},
        ]

        result = run_once()
        assert result["gated"] == 1
        assert result["skipped"] == 1
        assert result["errors"] == 1
