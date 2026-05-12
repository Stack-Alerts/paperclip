"""
Regression tests for BTCAAAAA-1236: add unit tests for blast_radius.worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1236
Fixed in commit: f13c605
Component: src/blast_radius/worker.py

Root cause: blast_radius.worker had zero unit test coverage.  The worker
(polling + webhook entry point for Blast Radius Report generation) was
trusted entirely on integration-level behaviour.  The fix added 83 %
coverage across _is_fix_issue, state file helpers, and run_once including
edge cases (corrupted state, dry-run, generator errors, dedup).

This file tests that:
  1. _is_fix_issue correctly identifies fix/bug issues by label and title
  2. State file helpers handle round-trip, corruption, and parent-dir creation
  3. run_once processes fix issues, skips non-fix, deduplicates, supports dry-run
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1236"),
    pytest.mark.regression,
]


class TestIsFixIssue:
    """Verify _is_fix_issue label + title heuristics from blast_radius.worker."""

    def _import_impl(self):
        from blast_radius.worker import _is_fix_issue
        return _is_fix_issue

    def test_fix_label(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "anything", "labels": [{"name": "fix"}]}) is True

    def test_bug_label(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "anything", "labels": [{"name": "Bug"}]}) is True

    def test_bugfix_label(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "anything", "labels": [{"name": "bugfix"}]}) is True

    def test_unrelated_label(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "anything", "labels": [{"name": "enhancement"}]}) is False

    def test_title_contains_fix(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "Fix null pointer", "labels": []}) is True

    def test_title_contains_bug(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "Bug: crash on empty", "labels": []}) is True

    def test_title_contains_regression(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "Regression in v3", "labels": []}) is True

    def test_title_contains_hotfix(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "Hotfix: stop-loss", "labels": []}) is True

    def test_normal_feature(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "Add chart widget", "labels": [{"name": "feature"}]}) is False

    def test_no_labels_key(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "Performance"}) is False

    def test_empty_labels(self):
        _is_fix_issue = self._import_impl()
        assert _is_fix_issue({"title": "Refactor", "labels": []}) is False


class TestStateHelpers:
    """Verify _load_state / _save_state round-trip, corruption recovery, and dir creation."""

    MARKER = "blast_radius_worker_state"

    def _import_mod(self):
        import blast_radius.worker as worker_mod
        return worker_mod

    def test_round_trip(self, tmp_path, monkeypatch):
        mod = self._import_mod()
        state_file = tmp_path / "state.json"
        monkeypatch.setattr(mod, "_STATE_PATH", state_file)

        assert mod._load_state() == {"processed_issue_ids": [], "issue_statuses": {}}

        mod._save_state({"processed_issue_ids": ["id-1", "id-2"], "issue_statuses": {}})
        loaded = mod._load_state()
        assert loaded == {"processed_issue_ids": ["id-1", "id-2"], "issue_statuses": {}}

    def test_load_corrupted_file_returns_default(self, tmp_path, monkeypatch):
        mod = self._import_mod()
        state_file = tmp_path / "state.json"
        state_file.write_text("NOT JSON{{{{")
        monkeypatch.setattr(mod, "_STATE_PATH", state_file)

        result = mod._load_state()
        assert result == {"processed_issue_ids": [], "issue_statuses": {}}

    def test_save_creates_parent_dirs(self, tmp_path, monkeypatch):
        mod = self._import_mod()
        state_file = tmp_path / "nested" / "dir" / "state.json"
        monkeypatch.setattr(mod, "_STATE_PATH", state_file)

        mod._save_state({"processed_issue_ids": ["x"], "issue_statuses": {}})
        assert state_file.exists()
        assert json.loads(state_file.read_text()) == {
            "processed_issue_ids": ["x"],
            "issue_statuses": {},
        }

    def test_load_migration_adds_missing_keys(self, tmp_path, monkeypatch):
        mod = self._import_mod()
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"processed_issue_ids": []}))
        monkeypatch.setattr(mod, "_STATE_PATH", state_file)

        result = mod._load_state()
        assert "issue_statuses" in result
        assert result["issue_statuses"] == {}


class TestRunOnce:
    """Verify run_once processes fix issues, skips non-fix, deduplicates, supports dry-run."""

    MARKER = "blast_radius_run_once"

    def _import_mod(self):
        import blast_radius.worker as worker_mod
        return worker_mod

    _FIX_ISSUE = {
        "id": "uuid-fix",
        "identifier": "BTCAAAAA-100",
        "title": "Fix the thing",
        "labels": [{"name": "fix"}],
    }

    _NON_FIX_ISSUE = {
        "id": "uuid-feat",
        "identifier": "BTCAAAAA-200",
        "title": "Add feature",
        "labels": [{"name": "feature"}],
    }

    def _patch_all(self, tmp_path, monkeypatch, issues, gen_return=None):
        mod = self._import_mod()
        state_file = tmp_path / "state.json"
        monkeypatch.setattr(mod, "_STATE_PATH", state_file)

        monkeypatch.setattr(mod, "_fetch_in_review_issues", lambda: issues)

        if gen_return is None:
            gen_return = {"issue": "BTCAAAAA-100", "dry_run": False}

        monkeypatch.setattr(
            mod,
            "generate_and_post",
            lambda issue_id, dry_run=False: gen_return,
        )
        return state_file

    def test_processes_fix_issue(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [self._FIX_ISSUE])
        mod = self._import_mod()

        results = mod.run_once()

        assert len(results) == 1
        assert results[0]["issue"] == "BTCAAAAA-100"

        state = json.loads(state_file.read_text())
        assert "uuid-fix" in state["processed_issue_ids"]

    def test_skips_non_fix_issue(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [self._NON_FIX_ISSUE])
        mod = self._import_mod()

        results = mod.run_once()

        assert results == []
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert "uuid-feat" not in state.get("processed_issue_ids", [])

    def test_skips_already_processed(self, tmp_path, monkeypatch):
        mod = self._import_mod()
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps({"processed_issue_ids": ["uuid-fix"], "issue_statuses": {}})
        )
        monkeypatch.setattr(mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(mod, "_fetch_in_review_issues", lambda: [self._FIX_ISSUE])
        monkeypatch.setattr(
            mod,
            "generate_and_post",
            lambda issue_id, dry_run=False: {"issue": "BTCAAAAA-100"},
        )

        results = mod.run_once()

        assert results == []
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == ["uuid-fix"]

    def test_dry_run_does_not_save_state(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [self._FIX_ISSUE])
        mod = self._import_mod()

        mod.run_once(dry_run=True)

        assert not state_file.exists()

    def test_generator_error_recorded(self, tmp_path, monkeypatch):
        mod = self._import_mod()
        state_file = tmp_path / "state.json"
        monkeypatch.setattr(mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(mod, "_fetch_in_review_issues", lambda: [self._FIX_ISSUE])
        monkeypatch.setattr(
            mod,
            "generate_and_post",
            lambda issue_id, dry_run=False: (_ for _ in ()).throw(
                RuntimeError("DB down")
            ),
        )

        results = mod.run_once()

        assert len(results) == 1
        assert "error" in results[0]
        assert "DB down" in results[0]["error"]

    def test_mixed_issues(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [self._FIX_ISSUE, self._NON_FIX_ISSUE])
        mod = self._import_mod()

        results = mod.run_once()

        assert len(results) == 1
        assert results[0]["issue"] == "BTCAAAAA-100"

    def test_empty_issue_list(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [])
        mod = self._import_mod()

        results = mod.run_once()

        assert results == []
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state.get("processed_issue_ids", []) == []
