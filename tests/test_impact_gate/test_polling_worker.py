"""Unit tests for impact_gate.polling_worker.

All external I/O (Paperclip API, Blast Radius) is mocked.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime as datetime_cls, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from freezegun import freeze_time

from impact_gate import polling_worker as pw
from impact_gate.polling_worker import (
    _WATERMARK_FILE,
    _compute_since,
    _fetch_done_fix_issues,
    _format_iso,
    _has_scan_done_comment,
    _load_watermark,
    _parse_iso,
    _post_comment,
    _render_gate_comment,
    _save_watermark,
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
    @freeze_time("2026-05-16T06:15:00Z")
    @patch("impact_gate.polling_worker._paginate")
    @patch("impact_gate.polling_worker._is_fix_issue")
    def test_fetch_done_fix_issues(self, mock_is_fix, mock_paginate):
        # All three issues are recent (within 10m), but only 1 and 3 are fix issues
        issues = [
            _make_issue(issue_id="1", completed_at="2026-05-16T06:10:00Z"),
            _make_issue(issue_id="2", completed_at="2026-05-16T06:12:00Z"),
            _make_issue(
                issue_id="3",
                identifier="BTCAAAAA-100",
                completed_at="2026-05-16T06:08:00Z",
            ),
        ]
        mock_paginate.return_value = issues
        # side_effect: issue1=True (fix), issue2=False (not a fix), issue3=True (fix)
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


# ---------------------------------------------------------------------------
# TestHasScanDoneComment
# ---------------------------------------------------------------------------


class TestHasScanDoneComment:
    @patch("impact_gate.polling_worker.fetch_issue_comments")
    def test_returns_true_when_scan_done_comment_present(self, mock_fetch):
        mock_fetch.return_value = [
            {"id": "c1", "body": "## Impact Gate — Scan Done\n\nVerification complete."},
        ]
        assert _has_scan_done_comment("issue-123") is True

    @patch("impact_gate.polling_worker.fetch_issue_comments")
    def test_returns_false_when_no_scan_done_comment(self, mock_fetch):
        mock_fetch.return_value = [
            {"id": "c1", "body": "## Impact Gate: PASS\n\nAll tests passed."},
            {"id": "c2", "body": "Just a regular comment."},
        ]
        assert _has_scan_done_comment("issue-123") is False

    @patch("impact_gate.polling_worker.fetch_issue_comments")
    def test_returns_false_when_no_comments(self, mock_fetch):
        mock_fetch.return_value = []
        assert _has_scan_done_comment("issue-123") is False

    @patch("impact_gate.polling_worker.fetch_issue_comments")
    def test_returns_false_on_fetch_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("API error")
        assert _has_scan_done_comment("issue-123") is False


# ---------------------------------------------------------------------------
# TestProcessIssueIdempotency (BTCAAAAA-27486)
# ---------------------------------------------------------------------------


class TestProcessIssueIdempotency:
    @patch("impact_gate.polling_worker.get_issue_by_id")
    @patch("impact_gate.polling_worker._has_scan_done_comment")
    def test_skips_done_issue_with_existing_scan_done_comment(
        self, mock_has_comment, mock_get_issue
    ):
        issue = _make_issue(issue_id="abc", identifier="BTCAAAAA-27448", status="done")
        mock_get_issue.return_value = issue
        mock_has_comment.return_value = True

        result = process_issue("abc")

        assert result["status"] == "skipped_already_gated"
        assert result["comment_posted"] is False
        mock_has_comment.assert_called_once_with("abc")

    @patch("impact_gate.polling_worker.get_issue_by_id")
    @patch("impact_gate.polling_worker._has_scan_done_comment")
    def test_skips_cancelled_issue_with_existing_scan_done_comment(
        self, mock_has_comment, mock_get_issue
    ):
        issue = _make_issue(issue_id="abc", identifier="BTCAAAAA-111", status="cancelled")
        mock_get_issue.return_value = issue
        mock_has_comment.return_value = True

        result = process_issue("abc")

        assert result["status"] == "skipped_already_gated"
        assert result["comment_posted"] is False

    @patch("impact_gate.polling_worker.get_issue_by_id")
    @patch("impact_gate.polling_worker._has_scan_done_comment")
    @patch("impact_gate.polling_worker.extract_touched_files")
    @patch("impact_gate.polling_worker.query_blast_radius")
    @patch("impact_gate.polling_worker._post_comment")
    def test_processes_done_issue_without_prior_scan_done_comment(
        self, mock_post, mock_query, mock_extract, mock_has_comment, mock_get_issue
    ):
        issue = _make_issue(
            issue_id="abc",
            identifier="BTCAAAAA-999",
            status="done",
            description="touchedFiles: src/main.py",
        )
        mock_get_issue.return_value = issue
        mock_has_comment.return_value = False
        mock_extract.return_value = ["src/main.py"]

        mock_data = MagicMock()
        mock_data.fr_impact_set = []
        mock_data.regression_set = []
        mock_query.return_value = mock_data
        mock_post.return_value = True

        result = process_issue("abc")

        assert result["status"] == "gated"
        assert result["comment_posted"] is True
        mock_post.assert_called_once()

    @patch("impact_gate.polling_worker._board_session")
    def test_post_comment_includes_idempotency_key(self, mock_session):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.return_value.__enter__.return_value.post.return_value = mock_response

        _post_comment("issue-xyz", "Test body")

        call_kwargs = mock_session.return_value.__enter__.return_value.post.call_args
        payload = call_kwargs[1]["json"] if call_kwargs[1] else call_kwargs[0][1]
        assert payload.get("idempotencyKey") == "scan-done:issue-xyz"


# ---------------------------------------------------------------------------
# TestWatermarkPersistence (BTCAAAAA-38448)
# ---------------------------------------------------------------------------


class TestWatermarkPersistence:
    def test_load_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pw, "_WATERMARK_FILE", tmp_path / "no-such.json")
        assert _load_watermark() is None

    def test_save_then_load_roundtrip(self, tmp_path, monkeypatch):
        target = tmp_path / "impact_gate_watermark.json"
        monkeypatch.setattr(pw, "_WATERMARK_FILE", target)
        _save_watermark("2026-06-26T07:30:00.000Z")
        assert target.exists()
        payload = json.loads(target.read_text())
        assert payload == {"lastRunAt": "2026-06-26T07:30:00.000Z"}
        assert _load_watermark() == "2026-06-26T07:30:00.000Z"

    def test_load_returns_none_on_malformed_json(self, tmp_path, monkeypatch):
        target = tmp_path / "impact_gate_watermark.json"
        target.write_text("{not valid json")
        monkeypatch.setattr(pw, "_WATERMARK_FILE", target)
        assert _load_watermark() is None

    def test_load_returns_none_when_lastRunAt_missing(self, tmp_path, monkeypatch):
        target = tmp_path / "impact_gate_watermark.json"
        target.write_text(json.dumps({"other": "value"}))
        monkeypatch.setattr(pw, "_WATERMARK_FILE", target)
        assert _load_watermark() is None

    def test_save_creates_parent_dir(self, tmp_path, monkeypatch):
        nested = tmp_path / "deeply" / "nested" / "watermark.json"
        monkeypatch.setattr(pw, "_WATERMARK_FILE", nested)
        _save_watermark("2026-06-26T08:00:00.000Z")
        assert nested.exists()


# ---------------------------------------------------------------------------
# TestParseFormatIso
# ---------------------------------------------------------------------------


class TestParseFormatIso:
    def test_roundtrip(self):
        epoch = 1740000000.123
        ts = _format_iso(epoch)
        assert ts.endswith("Z")
        assert _parse_iso(ts) == pytest.approx(epoch, abs=1e-3)

    def test_parse_with_z_suffix(self):
        assert _parse_iso("2026-06-26T07:30:00Z") == pytest.approx(
            datetime_cls(2026, 6, 26, 7, 30, 0, tzinfo=timezone.utc).timestamp()
        )

    def test_parse_with_offset_suffix(self):
        ts = "2026-06-26T07:30:00+00:00"
        assert _parse_iso(ts) == pytest.approx(
            datetime_cls(2026, 6, 26, 7, 30, 0, tzinfo=timezone.utc).timestamp()
        )

    def test_parse_malformed_raises(self):
        with pytest.raises(ValueError):
            _parse_iso("not-a-timestamp")


# ---------------------------------------------------------------------------
# TestComputeSince
# ---------------------------------------------------------------------------


class TestComputeSince:
    @freeze_time("2026-06-26T07:30:00Z")
    def test_no_watermark_returns_24h_ago(self):
        since = _compute_since(None)
        expected = _format_iso(
            datetime_cls(2026, 6, 26, 7, 30, 0, tzinfo=timezone.utc).timestamp()
            - 24 * 3600
        )
        assert since == expected

    @freeze_time("2026-06-26T07:30:00Z")
    def test_with_watermark_pulls_back_30_minutes(self):
        wm = "2026-06-26T07:00:00Z"
        since = _compute_since(wm)
        # 07:00 - 30min safety lookback = 06:30
        expected = _format_iso(
            datetime_cls(2026, 6, 26, 6, 30, 0, tzinfo=timezone.utc).timestamp()
        )
        assert since == expected

    @freeze_time("2026-06-26T07:30:00Z")
    def test_malformed_watermark_falls_back_to_24h(self):
        since = _compute_since("definitely not iso8601")
        expected = _format_iso(
            datetime_cls(2026, 6, 26, 7, 30, 0, tzinfo=timezone.utc).timestamp()
            - 24 * 3600
        )
        assert since == expected


# ---------------------------------------------------------------------------
# TestFetchDoneFixIssuesWithWatermark
# ---------------------------------------------------------------------------


class TestFetchDoneFixIssuesWithWatermark:
    @freeze_time("2026-06-26T07:30:00Z")
    def test_no_args_uses_watermark_cursor(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pw, "_WATERMARK_FILE", tmp_path / "no-such.json")
        with patch("impact_gate.polling_worker._paginate") as mock_paginate, \
             patch("impact_gate.polling_worker._is_fix_issue", return_value=True):
            mock_paginate.return_value = []
            _fetch_done_fix_issues()

        args, kwargs = mock_paginate.call_args
        params = args[1] if len(args) > 1 else kwargs.get("params", {})
        assert "updatedAfter" in params
        # First-run: should be ~24h ago from 07:30, i.e. 2026-06-25T07:30
        assert params["updatedAfter"].startswith("2026-06-25T07:30:00")

    @freeze_time("2026-06-26T07:30:00Z")
    def test_with_watermark_uses_watermark_cursor(self, tmp_path, monkeypatch):
        target = tmp_path / "watermark.json"
        target.write_text(json.dumps({"lastRunAt": "2026-06-26T07:00:00Z"}))
        monkeypatch.setattr(pw, "_WATERMARK_FILE", target)

        with patch("impact_gate.polling_worker._paginate") as mock_paginate, \
             patch("impact_gate.polling_worker._is_fix_issue", return_value=True):
            mock_paginate.return_value = []
            _fetch_done_fix_issues()

        args, kwargs = mock_paginate.call_args
        params = args[1] if len(args) > 1 else kwargs.get("params", {})
        # Watermark 07:00 minus 30min safety lookback = 06:30
        assert params["updatedAfter"].startswith("2026-06-26T06:30:00")

    def test_explicit_updated_after_forwarded(self):
        with patch("impact_gate.polling_worker._paginate") as mock_paginate, \
             patch("impact_gate.polling_worker._is_fix_issue", return_value=True):
            mock_paginate.return_value = []
            _fetch_done_fix_issues(updated_after="2026-06-25T00:00:00Z")

        args, kwargs = mock_paginate.call_args
        params = args[1] if len(args) > 1 else kwargs.get("params", {})
        assert params["updatedAfter"] == "2026-06-25T00:00:00Z"

    def test_explicit_lookback_uses_sliding_window(self):
        with patch("impact_gate.polling_worker._paginate") as mock_paginate, \
             patch("impact_gate.polling_worker._is_fix_issue", return_value=True):
            mock_paginate.return_value = []
            _fetch_done_fix_issues(lookback_minutes=15)

        args, kwargs = mock_paginate.call_args
        params = args[1] if len(args) > 1 else kwargs.get("params", {})
        assert "updatedAfter" in params
        # Format is YYYY-MM-DDTHH:MM:SSZ (no millis); just check it's recent.
        assert params["updatedAfter"].endswith("Z")

    def test_filters_completedAt_to_cursor(self):
        # Issues completed before the cursor should be dropped client-side
        # as a defense-in-depth check even when the server returns them.
        recent_iso = "2026-06-26T07:00:00Z"
        stale_iso = "2026-06-20T00:00:00Z"
        with patch("impact_gate.polling_worker._paginate") as mock_paginate, \
             patch("impact_gate.polling_worker._is_fix_issue", return_value=True):
            mock_paginate.return_value = [
                _make_issue(issue_id="r", identifier="BTCAAAAA-RECENT", completed_at=recent_iso),
                _make_issue(issue_id="s", identifier="BTCAAAAA-STALE", completed_at=stale_iso),
            ]
            result = _fetch_done_fix_issues(
                updated_after="2026-06-26T06:00:00Z"
            )

        assert [i["id"] for i in result] == ["r"]


# ---------------------------------------------------------------------------
# TestRunOnceAdvancesWatermark
# ---------------------------------------------------------------------------


class TestRunOnceAdvancesWatermark:
    @freeze_time("2026-06-26T07:30:00Z")
    def test_run_once_persists_watermark(self, tmp_path, monkeypatch):
        target = tmp_path / "watermark.json"
        monkeypatch.setattr(pw, "_WATERMARK_FILE", target)

        with patch("impact_gate.polling_worker._fetch_done_fix_issues", return_value=[]), \
             patch("impact_gate.polling_worker.process_issue") as mock_process:
            result = run_once()

        assert result == {"gated": 0, "skipped": 0, "errors": 0, "results": []}
        assert target.exists()
        payload = json.loads(target.read_text())
        assert payload["lastRunAt"] == "2026-06-26T07:30:00.000Z"
        mock_process.assert_not_called()  # No issues to process

    @freeze_time("2026-06-26T07:30:00Z")
    def test_run_once_can_skip_watermark_advance(self, tmp_path, monkeypatch):
        target = tmp_path / "watermark.json"
        monkeypatch.setattr(pw, "_WATERMARK_FILE", target)

        with patch("impact_gate.polling_worker._fetch_done_fix_issues", return_value=[]):
            run_once(advance_watermark=False)

        assert not target.exists()

    @freeze_time("2026-06-26T07:30:00Z")
    def test_run_once_advances_after_empty_fetch(self, tmp_path, monkeypatch):
        # Even when the API returns no issues, the watermark must advance so a
        # quiet stretch doesn't trigger a backlog re-scan on the next fire.
        target = tmp_path / "watermark.json"
        monkeypatch.setattr(pw, "_WATERMARK_FILE", target)

        with patch("impact_gate.polling_worker._fetch_done_fix_issues", return_value=[]):
            run_once()

        assert target.exists()
        assert json.loads(target.read_text())["lastRunAt"] == "2026-06-26T07:30:00.000Z"
