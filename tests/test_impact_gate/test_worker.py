"""Unit tests for impact_gate.worker — no DB or live network required."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from impact_gate.worker import (
    _has_bypass_label,
    _build_pass_comment,
    _build_fail_comment,
    _build_bypass_comment,
    _build_escalation_comment,
    process_issue,
    scan_done_issues,
    MIN_TESTS_BAR,
)
import impact_gate.worker as worker_mod

_PASS_RESULT = {
    "timestamp": "2026-01-01T00:00:00",
    "status": "PASS",
    "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
    "fr_results": {},
    "bug_results": {},
}

# A pass result that meets the 10-test minimum bar
_PASS_RESULT_BAR = {
    "timestamp": "2026-01-01T00:00:00",
    "status": "PASS",
    "summary": {"total": 10, "passed": 10, "failed": 0, "errors": 0},
    "fr_results": {},
    "bug_results": {},
}

_FAIL_RESULT = {
    "timestamp": "2026-01-01T00:00:00",
    "status": "FAIL",
    "summary": {"total": 1, "passed": 0, "failed": 1, "errors": 0},
    "fr_results": {},
    "bug_results": {
        "BTCAAAAA-100": {
            "status": "FAIL",
            "test_file": "tests/bug_regression/test_btcaaaaa_100_regression.py",
            "tests": [{"nodeid": "test::f", "outcome": "failed", "message": "x"}],
            "passed": 0,
            "failed": 1,
        },
    },
}


# ---------------------------------------------------------------------------
# _has_bypass_label
# ---------------------------------------------------------------------------


class TestHasBypassLabel:
    def test_bypass_label_present(self):
        assert _has_bypass_label({"labels": [{"name": "impact-gate-bypass"}]}) is True

    def test_case_insensitive(self):
        assert _has_bypass_label({"labels": [{"name": "Impact-Gate-Bypass"}]}) is True

    def test_no_labels(self):
        assert _has_bypass_label({"labels": []}) is False

    def test_unrelated_label(self):
        assert _has_bypass_label({"labels": [{"name": "fix"}]}) is False

    def test_whitespace_trimmed(self):
        assert _has_bypass_label({"labels": [{"name": "  impact-gate-bypass  "}]}) is True


# ---------------------------------------------------------------------------
# Comment builders
# ---------------------------------------------------------------------------


class TestCommentBuilders:
    def test_pass_comment(self):
        r = _build_pass_comment("BTCAAAAA-100", {"summary": {"total": 5, "passed": 5, "failed": 0, "errors": 0}})
        assert "PASS" in r and "✅" in r and "BTCAAAAA-100" in r

    def test_fail_comment(self):
        r = _build_fail_comment("BTCAAAAA-100", {"status": "FAIL", "summary": {"total": 2, "passed": 0, "failed": 2, "errors": 0}}, ["FDR-850"], [], [])
        assert "FAIL" in r and "❌" in r

    def test_fail_comment_with_blocking(self):
        r = _build_fail_comment("BTCAAAAA-100", {"status": "FAIL", "summary": {"total": 1, "passed": 0, "failed": 1, "errors": 0}}, [], [], [{"identifier": "BTCAAAAA-200"}])
        assert "BTCAAAAA-200" in r

    def test_bypass_comment(self):
        r = _build_bypass_comment("BTCAAAAA-100")
        assert "BYPASSED" in r and "🔶" in r

    def test_escalation_comment(self):
        r = _build_escalation_comment("BTCAAAAA-100", "DB down")
        assert "ERROR" in r and "⚠️" in r and "DB down" in r


# ---------------------------------------------------------------------------
# process_issue — main entry point
# ---------------------------------------------------------------------------

_FIX_IN_REVIEW = {
    "id": "fix-uuid",
    "identifier": "BTCAAAAA-100",
    "title": "Fix null pointer",
    "status": "in_review",
    "labels": [{"name": "fix"}],
    "description": '"touchedFiles": ["src/loader.py"]',
}

_FIX_WITH_BYPASS = {**_FIX_IN_REVIEW, "id": "bypass-uuid", "identifier": "BTCAAAAA-101",
                    "labels": [{"name": "fix"}, {"name": "impact-gate-bypass"}]}

_NOT_IN_REVIEW = {**_FIX_IN_REVIEW, "id": "not-review-uuid", "identifier": "BTCAAAAA-102", "status": "in_progress"}

_NO_TF = {**_FIX_IN_REVIEW, "id": "no-tf-uuid", "identifier": "BTCAAAAA-103", "description": "No file paths"}

_FIX_DONE = {**_FIX_IN_REVIEW, "id": "done-uuid", "identifier": "BTCAAAAA-104", "status": "done"}


class TestProcessIssue:
    def _mock_fetch(self, monkeypatch, issue_dict):
        monkeypatch.setattr(worker_mod, "_get_issue", lambda iid: issue_dict)

    def _mock_br(self, monkeypatch):
        from blast_radius.query import BlastRadiusData
        monkeypatch.setattr("impact_gate.worker.query_blast_radius", lambda fps: BlastRadiusData())

    def _mock_actions(self, monkeypatch):
        posted, transitions = [], []
        monkeypatch.setattr(worker_mod, "_post_comment", lambda i, b: posted.append(i))
        monkeypatch.setattr("impact_gate.worker.transition_issue_status", lambda i, s: transitions.append((i, s)))
        monkeypatch.setattr(worker_mod, "_create_blocking_issue", lambda fi, fid, d, t: None)
        monkeypatch.setattr(worker_mod, "_set_blocked_by", lambda i, b: None)
        return posted, transitions

    def test_skips_non_in_review(self, monkeypatch):
        self._mock_fetch(monkeypatch, _NOT_IN_REVIEW)
        r = process_issue("not-review-uuid", dry_run=True)
        assert r["gate_status"] == "SKIPPED"

    def test_skips_done_without_force(self, monkeypatch):
        self._mock_fetch(monkeypatch, _FIX_DONE)
        r = process_issue("done-uuid", dry_run=True)
        assert r["gate_status"] == "SKIPPED"
        assert r.get("reason") == "status=done"

    def test_force_runs_on_done_issue(self, monkeypatch):
        self._mock_fetch(monkeypatch, _FIX_DONE)
        self._mock_br(monkeypatch)
        monkeypatch.setattr("impact_gate.worker.run_impact_gate", lambda f, b: _PASS_RESULT_BAR)
        posted, transitions = self._mock_actions(monkeypatch)
        r = process_issue("done-uuid", dry_run=False, force=True)
        assert r["gate_status"] == "PASS"
        assert len(posted) == 1
        assert transitions == [("done-uuid", "done")]

    def test_bypasses(self, monkeypatch):
        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment", lambda i, b: posted.append(i))
        self._mock_fetch(monkeypatch, _FIX_WITH_BYPASS)
        r = process_issue("bypass-uuid", dry_run=False)
        assert r["gate_status"] == "BYPASSED"
        assert len(posted) == 1

    def test_bypass_dry_run(self, monkeypatch):
        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment", lambda i, b: posted.append(i))
        self._mock_fetch(monkeypatch, _FIX_WITH_BYPASS)
        r = process_issue("bypass-uuid", dry_run=True)
        assert r["gate_status"] == "BYPASSED"
        assert len(posted) == 0

    def test_skips_no_touched_files(self, monkeypatch):
        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment", lambda i, b: posted.append(i))
        self._mock_fetch(monkeypatch, _NO_TF)
        r = process_issue("no-tf-uuid", dry_run=False)
        assert r["gate_status"] == "SKIPPED"

    def test_passes(self, monkeypatch):
        self._mock_fetch(monkeypatch, _FIX_IN_REVIEW)
        self._mock_br(monkeypatch)
        monkeypatch.setattr("impact_gate.worker.run_impact_gate", lambda f, b: _PASS_RESULT_BAR)
        posted, transitions = self._mock_actions(monkeypatch)
        r = process_issue("fix-uuid", dry_run=False)
        assert r["gate_status"] == "PASS"
        assert len(posted) == 1
        assert transitions == [("fix-uuid", "done")]

    def test_passes_dry_run(self, monkeypatch):
        self._mock_fetch(monkeypatch, _FIX_IN_REVIEW)
        self._mock_br(monkeypatch)
        monkeypatch.setattr("impact_gate.worker.run_impact_gate", lambda f, b: _PASS_RESULT_BAR)
        posted, transitions = self._mock_actions(monkeypatch)
        r = process_issue("fix-uuid", dry_run=True)
        assert r["gate_status"] == "PASS"
        assert r.get("dry_run") is True
        assert len(posted) == 0 and len(transitions) == 0

    def test_fetch_failure(self, monkeypatch):
        monkeypatch.setattr(worker_mod, "_get_issue", lambda i: (_ for _ in ()).throw(RuntimeError("API timeout")))
        r = process_issue("bad", dry_run=True)
        assert r["gate_status"] == "ERROR" and "API timeout" in r.get("error", "")

    def test_br_failure_posts_escalation(self, monkeypatch):
        self._mock_fetch(monkeypatch, _FIX_IN_REVIEW)
        monkeypatch.setattr("impact_gate.worker.query_blast_radius", lambda f: (_ for _ in ()).throw(RuntimeError("BR down")))
        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment", lambda i, b: posted.append(i))
        r = process_issue("fix-uuid", dry_run=False)
        assert r["gate_status"] == "ERROR" and len(posted) == 1

    def test_br_failure_dry_run(self, monkeypatch):
        self._mock_fetch(monkeypatch, _FIX_IN_REVIEW)
        monkeypatch.setattr("impact_gate.worker.query_blast_radius", lambda f: (_ for _ in ()).throw(RuntimeError("BR down")))
        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment", lambda i, b: posted.append(i))
        r = process_issue("fix-uuid", dry_run=True)
        assert r["gate_status"] == "ERROR" and len(posted) == 0

    def test_runner_failure_posts_escalation(self, monkeypatch):
        self._mock_fetch(monkeypatch, _FIX_IN_REVIEW)
        self._mock_br(monkeypatch)
        monkeypatch.setattr("impact_gate.worker.run_impact_gate", lambda f, b: (_ for _ in ()).throw(RuntimeError("runner crashed")))
        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment", lambda i, b: posted.append(i))
        r = process_issue("fix-uuid", dry_run=False)
        assert r["gate_status"] == "ERROR"

    def test_fail_reverts_and_creates_blocking(self, monkeypatch):
        self._mock_fetch(monkeypatch, {**_FIX_IN_REVIEW, "id": "fail-uuid", "identifier": "BTCAAAAA-300"})
        self._mock_br(monkeypatch)
        monkeypatch.setattr("impact_gate.worker.run_impact_gate", lambda f, b: _FAIL_RESULT)
        posted, transitions = self._mock_actions(monkeypatch)
        blocking_ids = []
        monkeypatch.setattr(worker_mod, "_create_blocking_issue", lambda fi, fid, d, t: (blocking_ids.append(fid) or {"id": f"b-{fid}"}))
        r = process_issue("fail-uuid", dry_run=False)
        assert r["gate_status"] == "FAIL"
        assert transitions == [("fail-uuid", "in_progress")]

    def test_fail_dry_run(self, monkeypatch):
        self._mock_fetch(monkeypatch, {**_FIX_IN_REVIEW, "id": "fail-uuid-2", "identifier": "BTCAAAAA-301"})
        self._mock_br(monkeypatch)
        monkeypatch.setattr("impact_gate.worker.run_impact_gate", lambda f, b: _FAIL_RESULT)
        posted, transitions = self._mock_actions(monkeypatch)
        r = process_issue("fail-uuid-2", dry_run=True)
        assert r["gate_status"] == "FAIL" and r.get("dry_run") is True
        assert len(posted) == 0 and len(transitions) == 0


# ---------------------------------------------------------------------------
# _create_blocking_issue
# ---------------------------------------------------------------------------


class TestCreateBlockingIssue:
    def test_creates_fr_blocking_issue(self, monkeypatch):
        mock_sess = MagicMock()
        mock_sess.post.return_value.json.return_value = {"id": "new-id", "identifier": "BTCAAAAA-500"}
        monkeypatch.setattr("impact_gate.worker._session", lambda: mock_sess)
        monkeypatch.setattr("impact_gate.worker._company", lambda: "comp-uuid")
        r = worker_mod._create_blocking_issue("BTCAAAAA-100", "FDR-850", "detail", "fr")
        assert r is not None and r["identifier"] == "BTCAAAAA-500"

    def test_returns_none_on_error(self, monkeypatch):
        mock_sess = MagicMock()
        mock_sess.post.side_effect = RuntimeError("API error")
        monkeypatch.setattr("impact_gate.worker._session", lambda: mock_sess)
        monkeypatch.setattr("impact_gate.worker._company", lambda: "comp-uuid")
        assert worker_mod._create_blocking_issue("BTCAAAAA-100", "FDR-850", "d", "fr") is None


# ---------------------------------------------------------------------------
# _set_blocked_by
# ---------------------------------------------------------------------------


class TestSetBlockedBy:
    def test_patches_correctly(self, monkeypatch):
        mock_sess = MagicMock()
        monkeypatch.setattr("impact_gate.worker._session", lambda: mock_sess)
        worker_mod._set_blocked_by("uuid", ["b1", "b2"])
        _, kw = mock_sess.patch.call_args
        assert kw["json"]["blockedByIssueIds"] == ["b1", "b2"]

    def test_logs_error(self, monkeypatch, caplog):
        mock_sess = MagicMock()
        mock_sess.patch.side_effect = RuntimeError("fail")
        monkeypatch.setattr("impact_gate.worker._session", lambda: mock_sess)
        with caplog.at_level(logging.ERROR):
            worker_mod._set_blocked_by("uuid", ["b1"])
        assert any("Failed to set blockedByIssueIds" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Minimum test bar (10-fix bar)
# ---------------------------------------------------------------------------


class TestMinimumTestBar:
    def test_below_bar_demotes_to_fail(self, monkeypatch):
        """When total tests < MIN_TESTS_BAR, a runner PASS is demoted to FAIL."""
        # Use _PASS_RESULT which has total=0, below the bar
        import impact_gate.worker as wmod
        monkeypatch.setattr(wmod, "_get_issue", lambda iid: _FIX_IN_REVIEW)
        monkeypatch.setattr("impact_gate.worker.query_blast_radius",
                            lambda fps: __import__("blast_radius.query",
                                                  fromlist=["BlastRadiusData"]).BlastRadiusData())
        monkeypatch.setattr("impact_gate.worker.run_impact_gate", lambda f, b: _PASS_RESULT)
        posted, transitions = [], []
        monkeypatch.setattr(wmod, "_post_comment", lambda i, b: posted.append(i))
        monkeypatch.setattr("impact_gate.worker.transition_issue_status",
                            lambda i, s: transitions.append((i, s)))
        monkeypatch.setattr(wmod, "_create_blocking_issue",
                            lambda fi, fid, d, t: {"id": f"b-{fid}"})
        monkeypatch.setattr(wmod, "_set_blocked_by", lambda i, b: None)
        r = process_issue("fix-uuid", dry_run=False)
        assert r["gate_status"] == "FAIL", f"Expected FAIL, got {r['gate_status']}"
        # Should have reverted to in_progress, not transitioned to done
        assert transitions == [("fix-uuid", "in_progress")]

    def test_at_bar_passes(self, monkeypatch):
        """When total tests == MIN_TESTS_BAR, the gate passes."""
        import impact_gate.worker as wmod
        monkeypatch.setattr(wmod, "_get_issue", lambda iid: _FIX_IN_REVIEW)
        monkeypatch.setattr("impact_gate.worker.query_blast_radius",
                            lambda fps: __import__("blast_radius.query",
                                                  fromlist=["BlastRadiusData"]).BlastRadiusData())
        monkeypatch.setattr("impact_gate.worker.run_impact_gate", lambda f, b: _PASS_RESULT_BAR)
        posted, transitions = [], []
        monkeypatch.setattr(wmod, "_post_comment", lambda i, b: posted.append(i))
        monkeypatch.setattr("impact_gate.worker.transition_issue_status",
                            lambda i, s: transitions.append((i, s)))
        r = process_issue("fix-uuid", dry_run=False)
        assert r["gate_status"] == "PASS", f"Expected PASS, got {r['gate_status']}"
        assert transitions == [("fix-uuid", "done")]

    def test_min_bar_constant_value(self):
        assert MIN_TESTS_BAR == 10


# ---------------------------------------------------------------------------
# _post_comment
# ---------------------------------------------------------------------------


class TestPostComment:
    def test_posts_to_correct_endpoint(self, monkeypatch):
        mock_sess = MagicMock()
        monkeypatch.setattr("impact_gate.worker._session", lambda: mock_sess)
        worker_mod._post_comment("uuid", "body")
        args, kw = mock_sess.post.call_args
        assert "uuid/comments" in args[0]
        assert kw["json"]["body"] == "body"


# ---------------------------------------------------------------------------
# _get_issue
# ---------------------------------------------------------------------------


class TestGetIssue:
    def test_fetches_issue(self, monkeypatch):
        mock_sess = MagicMock()
        monkeypatch.setattr("impact_gate.worker._session", lambda: mock_sess)
        mock_sess.get.return_value.json.return_value = {"id": "i1"}
        assert worker_mod._get_issue("i1") == {"id": "i1"}

    def test_raises_on_http_error(self, monkeypatch):
        mock_sess = MagicMock()
        monkeypatch.setattr("impact_gate.worker._session", lambda: mock_sess)
        mock_sess.get.return_value.raise_for_status.side_effect = RuntimeError("404")
        with pytest.raises(RuntimeError, match="404"):
            worker_mod._get_issue("bad")

# ---------------------------------------------------------------------------
# scan_done_issues
# ---------------------------------------------------------------------------


class TestScanDoneIssues:
    """Tests for impact_gate.worker.scan_done_issues() wrapper."""

    def test_calls_scan_and_returns_result(self, monkeypatch):
        import scan_fix_issues_done
        expected = {"total_done_fix_issues": 5}
        calls = []
        def mock_scan(**kw):
            calls.append(kw)
            return expected
        monkeypatch.setattr(scan_fix_issues_done, "scan", mock_scan)
        result = scan_done_issues()
        assert result == expected
        assert len(calls) == 1
        assert calls[0] == {"days_back": None, "dry_run": False, "retroactive": False}

    def test_passes_days_back(self, monkeypatch):
        import scan_fix_issues_done
        calls = []
        monkeypatch.setattr(scan_fix_issues_done, "scan",
                            lambda **kw: (calls.append(kw) or {}))
        scan_done_issues(days_back=7)
        assert calls[0]["days_back"] == 7

    def test_passes_dry_run(self, monkeypatch):
        import scan_fix_issues_done
        calls = []
        monkeypatch.setattr(scan_fix_issues_done, "scan",
                            lambda **kw: (calls.append(kw) or {}))
        scan_done_issues(dry_run=True)
        assert calls[0]["dry_run"] is True

    def test_passes_retroactive(self, monkeypatch):
        import scan_fix_issues_done
        calls = []
        monkeypatch.setattr(scan_fix_issues_done, "scan",
                            lambda **kw: (calls.append(kw) or {}))
        scan_done_issues(retroactive=True)
        assert calls[0]["retroactive"] is True
