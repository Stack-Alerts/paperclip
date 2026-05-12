"""Unit tests for scripts/scan_fix_issues_done.py."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import importlib

_scan_path = Path(__file__).parents[2] / "scripts" / "scan_fix_issues_done.py"
_spec = importlib.util.spec_from_file_location("scan_fix_issues_done", _scan_path)
_scan = importlib.util.module_from_spec(_spec)
sys.modules["scan_fix_issues_done"] = _scan
_spec.loader.exec_module(_scan)

_is_fix = _scan._is_fix_issue
_check_gate = _scan._check_gate_status
_GATE_HEADER_RE = _scan._GATE_HEADER_RE


class TestIsFixIssue:
    def test_detects_fix_label(self):
        assert _is_fix({"labels": [{"name": "fix"}], "title": "Something"}) is True

    def test_detects_bug_label(self):
        assert _is_fix({"labels": [{"name": "bug"}], "title": "Something"}) is True

    def test_detects_hotfix_label(self):
        assert _is_fix({"labels": [{"name": "hotfix"}], "title": "Something"}) is True

    def test_detects_title_keyword(self):
        assert _is_fix({"labels": [], "title": "Bug: crash on startup"}) is True

    def test_rejects_non_fix(self):
        assert _is_fix({"labels": [{"name": "feature"}], "title": "New feature"}) is False

    def test_case_insensitive_labels(self):
        assert _is_fix({"labels": [{"name": "FIX"}], "title": ""}) is True

    def test_case_insensitive_title(self):
        assert _is_fix({"labels": [], "title": "REGRESSION in optimizer"}) is True

    def test_no_labels_or_keywords(self):
        assert _is_fix({"labels": [], "title": "Refactor logging"}) is False


class TestGateHeaderRegex:
    def test_matches_pass(self):
        m = _GATE_HEADER_RE.search("## Impact Gate: PASS")
        assert m is not None and m.group(1) == "PASS"

    def test_matches_fail(self):
        m = _GATE_HEADER_RE.search("## Impact Gate: FAIL")
        assert m is not None and m.group(1) == "FAIL"

    def test_matches_bypass(self):
        m = _GATE_HEADER_RE.search("## Impact Gate: BYPASSED")
        assert m is not None and m.group(1) == "BYPASSED"

    def test_matches_error(self):
        m = _GATE_HEADER_RE.search("## Impact Gate: ERROR")
        assert m is not None and m.group(1) == "ERROR"

    def test_no_match_for_non_gate_header(self):
        m = _GATE_HEADER_RE.search("## Some other header")
        assert m is None

    def test_no_match_for_inline_text(self):
        m = _GATE_HEADER_RE.search("not a header ## Impact Gate: PASS")
        assert m is None

    def test_matches_in_middle_of_comment(self):
        body = "Some comment text\n\n## Impact Gate: PASS\n\nMore text"
        m = _GATE_HEADER_RE.search(body)
        assert m is not None and m.group(1) == "PASS"

    def test_matches_fail_with_details(self):
        body = """## Impact Gate: FAIL

Issue: **BTCAAAAA-100**

One or more tests failed."""
        m = _GATE_HEADER_RE.search(body)
        assert m is not None and m.group(1) == "FAIL"


class TestCheckGateStatus:
    def test_detects_pass(self, monkeypatch):
        monkeypatch.setattr(
            _scan, "fetch_issue_comments", lambda iid: [
                {"body": "## Impact Gate: PASS\n\nAll tests passed."},
            ]
        )
        assert _check_gate("any-id") == "PASS"

    def test_detects_fail(self, monkeypatch):
        monkeypatch.setattr(
            _scan, "fetch_issue_comments", lambda iid: [
                {"body": "## Impact Gate: FAIL\n\nTests failed."},
            ]
        )
        assert _check_gate("any-id") == "FAIL"

    def test_detects_bypassed(self, monkeypatch):
        monkeypatch.setattr(
            _scan, "fetch_issue_comments", lambda iid: [
                {"body": "## Impact Gate: BYPASSED\n\nCEO bypass."},
            ]
        )
        assert _check_gate("any-id") == "BYPASSED"

    def test_returns_none_when_no_gate_comment(self, monkeypatch):
        monkeypatch.setattr(
            _scan, "fetch_issue_comments", lambda iid: [
                {"body": "Some other comment"},
                {"body": "Fixed the bug"},
            ]
        )
        assert _check_gate("any-id") is None

    def test_returns_none_on_empty_comments(self, monkeypatch):
        monkeypatch.setattr(_scan, "fetch_issue_comments", lambda iid: [])
        assert _check_gate("any-id") is None

    def test_handles_api_failure_gracefully(self, monkeypatch):
        monkeypatch.setattr(_scan, "fetch_issue_comments", lambda iid: (_ for _ in ()).throw(RuntimeError("API down")))
        assert _check_gate("any-id") is None


class TestScanFunction:
    def test_scan_with_no_issues(self, monkeypatch):
        monkeypatch.setattr(_scan, "_paginate", lambda path, params, page_size=100: [])
        monkeypatch.setattr(_scan, "_company", lambda: "comp-uuid")
        result = _scan.scan()
        assert result["total_done_fix_issues"] == 0
        assert result["ungated_count"] == 0
        assert result["gated"] == {"pass": 0, "fail": 0, "bypassed": 0, "errored": 0}

    def test_scan_filters_fix_issues(self, monkeypatch):
        monkeypatch.setattr(_scan, "_paginate", lambda path, params, page_size=100: [
            {"id": "u1", "identifier": "BTCAAAAA-100", "title": "Fix crash", "labels": [{"name": "fix"}], "status": "done"},
            {"id": "u2", "identifier": "BTCAAAAA-101", "title": "New feature", "labels": [{"name": "feature"}], "status": "done"},
        ])
        monkeypatch.setattr(_scan, "_company", lambda: "comp-uuid")
        monkeypatch.setattr(_scan, "fetch_issue_comments", lambda iid: [{"body": "## Impact Gate: PASS"}])
        result = _scan.scan()
        assert result["total_done_fix_issues"] == 1

    def test_scan_counts_gated_vs_ungated(self, monkeypatch):
        monkeypatch.setattr(_scan, "_paginate", lambda path, params, page_size=100: [
            {"id": "u1", "identifier": "BTCAAAAA-100", "title": "Fix A", "labels": [{"name": "fix"}], "status": "done"},
            {"id": "u2", "identifier": "BTCAAAAA-101", "title": "Fix B", "labels": [{"name": "fix"}], "status": "done"},
        ])
        monkeypatch.setattr(_scan, "_company", lambda: "comp-uuid")

        call_count = 0
        def mock_comments(iid):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [{"body": "## Impact Gate: PASS"}]
            return [{"body": "Some other comment"}]

        monkeypatch.setattr(_scan, "fetch_issue_comments", mock_comments)
        result = _scan.scan()
        assert result["total_done_fix_issues"] == 2
        assert result["gated"]["pass"] == 1
        assert result["ungated_count"] == 1

    def test_scan_respects_days_back(self, monkeypatch):
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace("+00:00", "Z")

        monkeypatch.setattr(_scan, "_paginate", lambda path, params, page_size=100: [
            {"id": "u1", "identifier": "BTCAAAAA-100", "title": "Fix recent", "labels": [{"name": "fix"}],
             "status": "done", "completedAt": recent},
            {"id": "u2", "identifier": "BTCAAAAA-101", "title": "Fix old", "labels": [{"name": "fix"}],
             "status": "done", "completedAt": old},
        ])
        monkeypatch.setattr(_scan, "_company", lambda: "comp-uuid")
        monkeypatch.setattr(_scan, "fetch_issue_comments", lambda iid: [{"body": "## Impact Gate: PASS"}])
        result = _scan.scan(days_back=7)
        assert result["total_done_fix_issues"] == 1
        assert result["gated"]["pass"] == 1

    def test_dry_run_does_not_run_retroactive(self, monkeypatch):
        monkeypatch.setattr(_scan, "_paginate", lambda path, params, page_size=100: [
            {"id": "u1", "identifier": "BTCAAAAA-100", "title": "Fix", "labels": [{"name": "fix"}], "status": "done"},
        ])
        monkeypatch.setattr(_scan, "_company", lambda: "comp-uuid")
        monkeypatch.setattr(_scan, "fetch_issue_comments", lambda iid: [{"body": "Other comment"}])
        process_called = []
        monkeypatch.setattr(_scan, "process_issue", lambda iid, dry_run=False, **kwargs: (process_called.append(iid) or {"gate_status": "PASS"}))
        _scan.scan(dry_run=True, retroactive=True)
        assert len(process_called) == 0

    def test_retroactive_runs_process_on_ungated(self, monkeypatch):
        monkeypatch.setattr(_scan, "_paginate", lambda path, params, page_size=100: [
            {"id": "u1", "identifier": "BTCAAAAA-100", "title": "Fix", "labels": [{"name": "fix"}], "status": "done"},
        ])
        monkeypatch.setattr(_scan, "_company", lambda: "comp-uuid")
        monkeypatch.setattr(_scan, "fetch_issue_comments", lambda iid: [{"body": "Other comment"}])
        calls = []
        monkeypatch.setattr(_scan, "process_issue", lambda iid, dry_run=False, **kwargs: (calls.append({"iid": iid, "kwargs": kwargs}) or {"gate_status": "PASS"}))
        result = _scan.scan(dry_run=False, retroactive=True)
        assert len(calls) == 1
        assert calls[0]["iid"] == "u1"
        assert calls[0]["kwargs"].get("force") is True
        assert "retroactive_results" in result
        assert result["retroactive_results"][0]["gate_status"] == "PASS"
