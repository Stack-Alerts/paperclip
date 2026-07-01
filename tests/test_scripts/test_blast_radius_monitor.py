"""Unit tests for scripts/blast_radius_monitor.py.

Tests cover:
- _compute_severity: priority/reason derivation
- create_alert: alert body rendering including the new 'errors' array section
- _append_update_comment: recurring alert body includes 'Failed issues' section
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure scripts/ is importable
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import blast_radius_monitor as monitor


# ---------------------------------------------------------------------------
# _compute_severity
# ---------------------------------------------------------------------------

class TestComputeSeverity:
    def test_single_issue_error(self):
        data = {"mode": "single-issue", "result": {"error": "boom"}}
        priority, reason = monitor._compute_severity(data)
        assert priority == "medium"
        assert "Single-issue" in reason

    def test_polling_high_error_rate(self):
        data = {"mode": "polling", "issues_processed": 4, "issues_with_errors": 3}
        priority, reason = monitor._compute_severity(data)
        assert priority == "critical"

    def test_polling_low_error_rate(self):
        data = {"mode": "polling", "issues_processed": 4, "issues_with_errors": 1}
        priority, reason = monitor._compute_severity(data)
        assert priority == "medium"
        assert "1/4" in reason

    def test_polling_zero_processed(self):
        data = {"mode": "polling", "issues_processed": 0, "issues_with_errors": 0}
        priority, reason = monitor._compute_severity(data)
        assert priority == "low"


# ---------------------------------------------------------------------------
# create_alert — alert body contains Failed issues section
# ---------------------------------------------------------------------------

class TestCreateAlertFailedIssuesSection:
    def _make_sess(self):
        sess = MagicMock()
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"identifier": "BTCAAAAA-99999", "id": "fake-id"}
        sess.post.return_value = resp
        return sess

    def test_alert_body_includes_failed_issues(self):
        data = {
            "mode": "polling",
            "dry_run": False,
            "timestamp": "2026-06-30T12:00:00+00:00",
            "issues_processed": 2,
            "issues_with_errors": 1,
            "errors": [
                {"issue": "BTCAAAAA-33167", "error_truncated": "HTTPError: 503 Service Unavailable"},
            ],
        }
        with patch.object(monitor, "_find_todays_alert", return_value=None):
            sess = self._make_sess()
            ok = monitor.create_alert("http://fake", "company-id", sess, data, None, dry_run=False)
        assert ok is True
        body = sess.post.call_args[1]["json"]["description"]
        assert "### Failed issues" in body
        assert "BTCAAAAA-33167" in body
        assert "HTTPError: 503 Service Unavailable" in body

    def test_alert_body_no_failed_issues_section_when_empty(self):
        data = {
            "mode": "polling",
            "dry_run": False,
            "timestamp": "2026-06-30T12:00:00+00:00",
            "issues_processed": 2,
            "issues_with_errors": 1,
            "errors": [],
        }
        with patch.object(monitor, "_find_todays_alert", return_value=None):
            sess = self._make_sess()
            ok = monitor.create_alert("http://fake", "company-id", sess, data, None, dry_run=False)
        assert ok is True
        body = sess.post.call_args[1]["json"]["description"]
        assert "### Failed issues" not in body

    def test_dry_run_output_includes_failed_issues(self, capsys):
        data = {
            "mode": "polling",
            "dry_run": False,
            "timestamp": "2026-06-30T12:00:00+00:00",
            "issues_processed": 2,
            "issues_with_errors": 2,
            "errors": [
                {"issue": "BTCAAAAA-111", "error_truncated": "timeout"},
                {"issue": "BTCAAAAA-222", "error_truncated": "not found"},
            ],
        }
        with patch.object(monitor, "_find_todays_alert", return_value=None):
            ok = monitor.create_alert("http://fake", "company-id", MagicMock(), data, None, dry_run=True)
        assert ok is True
        out = json.loads(capsys.readouterr().out)
        assert "### Failed issues" in out["description"]
        assert "BTCAAAAA-111" in out["description"]
        assert "BTCAAAAA-222" in out["description"]

    def test_alert_skipped_when_dry_run_worker(self):
        data = {"mode": "polling", "dry_run": True}
        ok = monitor.create_alert("http://fake", "company-id", MagicMock(), data, None, dry_run=False)
        assert ok is True

    def test_aggregate_counters_preserved(self):
        data = {
            "mode": "polling",
            "dry_run": False,
            "timestamp": "2026-06-30T12:00:00+00:00",
            "issues_processed": 5,
            "issues_with_errors": 2,
            "errors": [
                {"issue": "BTCAAAAA-A", "error_truncated": "err1"},
                {"issue": "BTCAAAAA-B", "error_truncated": "err2"},
            ],
        }
        with patch.object(monitor, "_find_todays_alert", return_value=None):
            sess = self._make_sess()
            monitor.create_alert("http://fake", "company-id", sess, data, None, dry_run=False)
        body = sess.post.call_args[1]["json"]["description"]
        assert "Issues processed:** 5" in body
        assert "Issues with errors:** 2" in body


# ---------------------------------------------------------------------------
# _append_update_comment — recurring alert includes Failed issues section
# ---------------------------------------------------------------------------

class TestAppendUpdateCommentFailedIssues:
    def _make_sess(self):
        sess = MagicMock()
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        sess.post.return_value = resp
        return sess

    def test_update_comment_includes_failed_issues(self):
        data = {
            "issues_processed": 3,
            "issues_with_errors": 2,
            "errors": [
                {"issue": "BTCAAAAA-33167", "error_truncated": "connect timeout"},
                {"issue": "BTCAAAAA-30269", "error_truncated": "key error"},
            ],
        }
        sess = self._make_sess()
        monitor._append_update_comment(
            "http://fake", sess, "issue-id-abc", "BTCAAAAA-99", "1/3 errors", data, None
        )
        body = sess.post.call_args[1]["json"]["body"]
        assert "### Failed issues" in body
        assert "BTCAAAAA-33167" in body
        assert "connect timeout" in body
        assert "BTCAAAAA-30269" in body

    def test_update_comment_no_failed_section_when_empty(self):
        data = {"issues_processed": 2, "issues_with_errors": 0, "errors": []}
        sess = self._make_sess()
        monitor._append_update_comment(
            "http://fake", sess, "issue-id-abc", "BTCAAAAA-99", "0 errors", data, None
        )
        body = sess.post.call_args[1]["json"]["body"]
        assert "### Failed issues" not in body

    def test_update_comment_no_failed_section_when_errors_key_missing(self):
        data = {"issues_processed": 1, "issues_with_errors": 1}
        sess = self._make_sess()
        monitor._append_update_comment(
            "http://fake", sess, "issue-id-abc", "BTCAAAAA-99", "1 error", data, None
        )
        body = sess.post.call_args[1]["json"]["body"]
        assert "### Failed issues" not in body
