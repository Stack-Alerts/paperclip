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
    run_once,
)


# ---------------------------------------------------------------------------
# _is_fix_issue
# ---------------------------------------------------------------------------

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
        state_file.write_text(
            json.dumps({"processed_issue_ids": ["issue-uuid-fix"]})
        )
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

    def test_empty_issue_list(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [])

        results = run_once()

        assert results == []
        assert not state_file.exists()
