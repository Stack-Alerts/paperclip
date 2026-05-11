"""Unit tests for blast_radius.worker — no DB or live network required."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import blast_radius.worker as worker_mod
from blast_radius.worker import (
    _is_fix_issue,
    _load_state,
    _save_state,
    run_loop,
    run_once,
)


class _BreakLoop(BaseException):
    """Used to break out of infinite run_loop during testing."""


class TestIsFixIssue:
    def test_fix_label(self):
        issue = {"title": "Improve performance", "labels": [{"name": "fix"}]}
        assert _is_fix_issue(issue) is True

    def test_bug_label(self):
        issue = {"title": "Some thing", "labels": [{"name": "Bug"}]}
        assert _is_fix_issue(issue) is True

    def test_bugfix_label(self):
        issue = {"title": "Irrelevant", "labels": [{"name": "bugfix"}]}
        assert _is_fix_issue(issue) is True

    def test_unrelated_label(self):
        issue = {"title": "Add new feature", "labels": [{"name": "enhancement"}]}
        assert _is_fix_issue(issue) is False

    def test_title_contains_fix(self):
        issue = {"title": "Fix null pointer in strategy loader", "labels": []}
        assert _is_fix_issue(issue) is True

    def test_title_contains_bug(self):
        issue = {"title": "Bug: signals fire twice", "labels": []}
        assert _is_fix_issue(issue) is True

    def test_title_contains_regression(self):
        issue = {"title": "Regression in optimizer v3", "labels": []}
        assert _is_fix_issue(issue) is True

    def test_title_contains_hotfix(self):
        issue = {"title": "Hotfix: stop-loss ignored", "labels": []}
        assert _is_fix_issue(issue) is True

    def test_normal_feature_issue(self):
        issue = {"title": "Add live chart widget", "labels": [{"name": "feature"}]}
        assert _is_fix_issue(issue) is False

    def test_no_labels_key(self):
        issue = {"title": "Performance improvement"}
        assert _is_fix_issue(issue) is False

    def test_empty_labels(self):
        issue = {"title": "Refactor module", "labels": []}
        assert _is_fix_issue(issue) is False


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------


class TestStateHelpers:
    def test_round_trip(self, tmp_path, monkeypatch):
        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)

        assert _load_state() == {"processed_issue_ids": []}

        _save_state({"processed_issue_ids": ["id-1", "id-2"]})
        loaded = _load_state()
        assert loaded == {"processed_issue_ids": ["id-1", "id-2"]}

    def test_load_corrupted_file_returns_default(self, tmp_path, monkeypatch):
        state_file = tmp_path / "state.json"
        state_file.write_text("NOT JSON{{{{")
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)

        result = _load_state()
        assert result == {"processed_issue_ids": []}

    def test_save_creates_parent_dirs(self, tmp_path, monkeypatch):
        state_file = tmp_path / "nested" / "dir" / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)

        _save_state({"processed_issue_ids": ["x"]})
        assert state_file.exists()
        assert json.loads(state_file.read_text()) == {"processed_issue_ids": ["x"]}


# ---------------------------------------------------------------------------
# run_once
# ---------------------------------------------------------------------------

_FIX_ISSUE = {
    "id": "issue-uuid-fix",
    "identifier": "BTCAAAAA-100",
    "title": "Fix the thing",
    "labels": [{"name": "fix"}],
}

_NON_FIX_ISSUE = {
    "id": "issue-uuid-feat",
    "identifier": "BTCAAAAA-200",
    "title": "Add new feature",
    "labels": [{"name": "feature"}],
}


class TestRunOnce:
    def _patch_all(self, tmp_path, monkeypatch, issues, gen_return=None):
        """Wire up all external dependencies and return the state file path."""
        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)

        monkeypatch.setattr(
            worker_mod,
            "_fetch_in_review_issues",
            lambda: issues,
        )

        if gen_return is None:
            gen_return = {"issue": "BTCAAAAA-100", "dry_run": False}

        monkeypatch.setattr(
            worker_mod,
            "generate_and_post",
            lambda issue_id, dry_run=False: gen_return,
        )

        return state_file

    def test_processes_fix_issue(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])

        results = run_once()

        assert len(results) == 1
        assert results[0]["issue"] == "BTCAAAAA-100"

        state = json.loads(state_file.read_text())
        assert "issue-uuid-fix" in state["processed_issue_ids"]

    def test_skips_non_fix_issue(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [_NON_FIX_ISSUE])

        results = run_once()

        assert results == []
        assert not state_file.exists()

    def test_skips_already_processed(self, tmp_path, monkeypatch):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"processed_issue_ids": ["issue-uuid-fix"]}))
        self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])

        results = run_once()

        assert results == []
        # State must not grow (already processed)
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == ["issue-uuid-fix"]

    def test_dry_run_does_not_save_state(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])

        run_once(dry_run=True)

        assert not state_file.exists()

    def test_generator_error_recorded(self, tmp_path, monkeypatch):
        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(
            worker_mod,
            "_fetch_in_review_issues",
            lambda: [_FIX_ISSUE],
        )
        monkeypatch.setattr(
            worker_mod,
            "generate_and_post",
            lambda issue_id, dry_run=False: (_ for _ in ()).throw(
                RuntimeError("DB down")
            ),
        )

        results = run_once()

        assert len(results) == 1
        assert "error" in results[0]
        assert "DB down" in results[0]["error"]

    def test_mixed_issues(self, tmp_path, monkeypatch):
        issues = [_FIX_ISSUE, _NON_FIX_ISSUE]
        self._patch_all(tmp_path, monkeypatch, issues)

        results = run_once()

        assert len(results) == 1
        assert results[0]["issue"] == "BTCAAAAA-100"

    def test_force_reprocess_overrides_processed_state(self, tmp_path, monkeypatch):
        """force_reprocess=True must process already-processed issues."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"processed_issue_ids": ["issue-uuid-fix"]}))
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(
            worker_mod,
            "_fetch_in_review_issues",
            lambda: [_FIX_ISSUE],
        )
        call_count = 0

        def tracking_gen(issue_id, dry_run=False):
            nonlocal call_count
            call_count += 1
            return {"issue": "BTCAAAAA-100", "dry_run": dry_run}

        monkeypatch.setattr(worker_mod, "generate_and_post", tracking_gen)

        results = run_once(force_reprocess=True)

        assert len(results) == 1
        assert call_count == 1
        # State should still be updated
        state = json.loads(state_file.read_text())
        assert "issue-uuid-fix" in state["processed_issue_ids"]

    def test_force_reprocess_with_dry_run_does_not_save_state(
        self, tmp_path, monkeypatch
    ):
        """force_reprocess + dry_run must not persist state."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"processed_issue_ids": ["issue-uuid-fix"]}))
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(
            worker_mod,
            "_fetch_in_review_issues",
            lambda: [_FIX_ISSUE],
        )
        monkeypatch.setattr(
            worker_mod,
            "generate_and_post",
            lambda issue_id, dry_run=False: {"issue": "BTCAAAAA-100"},
        )

        run_once(dry_run=True, force_reprocess=True)

        # State file should have only the original entry (no update)
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == ["issue-uuid-fix"]

    def test_empty_issue_list(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [])

        results = run_once()

        assert results == []
        assert not state_file.exists()


# ---------------------------------------------------------------------------
# _fetch_in_review_issues (paginated wrapper)
# ---------------------------------------------------------------------------


class TestFetchInReviewIssues:
    def test_delegates_to_paginate(self, monkeypatch):
        expected = [{"id": "iss-1", "identifier": "BTCAAAAA-300"}]
        captured_args = {}

        def mock_paginate(path, params, *, page_size):
            captured_args["path"] = path
            captured_args["params"] = params
            captured_args["page_size"] = page_size
            return expected

        monkeypatch.setattr(
            "blast_radius.worker._paginate",
            mock_paginate,
        )
        monkeypatch.setattr(
            "blast_radius.worker._company",
            lambda: "comp-uuid",
        )

        from blast_radius.worker import _fetch_in_review_issues

        result = _fetch_in_review_issues()

        assert result == expected
        assert "in_review" in str(captured_args["params"])
        assert captured_args["page_size"] == 100

    def test_returns_empty_list_on_empty_result(self, monkeypatch):
        monkeypatch.setattr(
            "blast_radius.worker._paginate",
            lambda path, params, *, page_size: [],
        )
        monkeypatch.setattr(
            "blast_radius.worker._company",
            lambda: "comp-uuid",
        )

        from blast_radius.worker import _fetch_in_review_issues

        result = _fetch_in_review_issues()
        assert result == []


# ---------------------------------------------------------------------------
# run_loop
# ---------------------------------------------------------------------------


class TestRunLoop:
    """Tests for the infinite-loop poller."""

    def test_catches_run_once_exception(self, monkeypatch):
        """run_loop must catch exceptions from run_once and continue."""
        call_count = 0

        def mock_run_once(dry_run=False, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise _BreakLoop()
            raise RuntimeError("DB connection lost")

        monkeypatch.setattr("blast_radius.worker.run_once", mock_run_once)
        monkeypatch.setattr("blast_radius.worker.time.sleep", lambda s: None)

        with pytest.raises(_BreakLoop):
            run_loop(interval_seconds=1)

        assert call_count == 2, "run_once should be called again after exception"

    def test_passes_dry_run_flag(self, monkeypatch):
        """run_loop must pass dry_run to run_once."""
        captured = {"dry_run": None}

        def mock_run_once(dry_run=False, **kwargs):
            captured["dry_run"] = dry_run
            raise _BreakLoop()

        monkeypatch.setattr("blast_radius.worker.run_once", mock_run_once)
        monkeypatch.setattr("blast_radius.worker.time.sleep", lambda s: None)

        with pytest.raises(_BreakLoop):
            run_loop(interval_seconds=1, dry_run=True)

        assert captured["dry_run"] is True

    def test_logs_error_message(self, monkeypatch, caplog):
        """run_loop must log the exception message before sleeping."""
        import logging

        def mock_run_once(dry_run=False, **kwargs):
            raise RuntimeError("PostgreSQL connection refused")

        monkeypatch.setattr("blast_radius.worker.run_once", mock_run_once)
        monkeypatch.setattr(
            "blast_radius.worker.time.sleep",
            lambda s: (_ for _ in ()).throw(_BreakLoop()),
        )

        with (
            pytest.raises(_BreakLoop),
            caplog.at_level(logging.ERROR),
        ):
            run_loop(interval_seconds=1)

        assert any("PostgreSQL connection refused" in r.message for r in caplog.records)

    def test_multiple_iterations(self, monkeypatch):
        """run_loop should keep calling run_once across iterations."""
        call_count = 0

        def mock_run_once(dry_run=False, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise _BreakLoop()
            return []

        monkeypatch.setattr("blast_radius.worker.run_once", mock_run_once)
        monkeypatch.setattr("blast_radius.worker.time.sleep", lambda s: None)

        with pytest.raises(_BreakLoop):
            run_loop(interval_seconds=60)

        assert call_count == 3
