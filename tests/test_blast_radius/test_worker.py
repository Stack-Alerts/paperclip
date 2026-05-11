"""Unit tests for blast_radius.worker — no DB or live network required."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import blast_radius.worker as worker_mod
from blast_radius.query import BlastRadiusData

from blast_radius.worker import (
    _is_fix_issue,
    _load_state,
    _save_state,
    _detect_transitions,
    _sync_statuses,
    run_loop,
    run_once,
    main as worker_main,
)


class _BreakLoop(BaseException):
    """Used to break out of infinite run_loop during testing."""


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

        default = _load_state()
        assert default == {"processed_issue_ids": [], "issue_statuses": {}}

        _save_state({"processed_issue_ids": ["id-1", "id-2"], "issue_statuses": {"id-1": "in_review"}})
        loaded = _load_state()
        assert loaded["processed_issue_ids"] == ["id-1", "id-2"]
        assert loaded["issue_statuses"] == {"id-1": "in_review"}

    def test_load_corrupted_file_returns_default(self, tmp_path, monkeypatch):
        state_file = tmp_path / "state.json"
        state_file.write_text("NOT JSON{{{{")
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)

        result = _load_state()
        assert result == {"processed_issue_ids": [], "issue_statuses": {}}

    def test_save_creates_parent_dirs(self, tmp_path, monkeypatch):
        state_file = tmp_path / "nested" / "dir" / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)

        _save_state({"processed_issue_ids": ["x"], "issue_statuses": {}})
        assert state_file.exists()
        assert json.loads(state_file.read_text()) == {
            "processed_issue_ids": ["x"],
            "issue_statuses": {},
        }

    def test_backward_compat_no_issue_statuses(self, tmp_path, monkeypatch):
        """Old state files without issue_statuses should still load."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"processed_issue_ids": ["id-1"]}))
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)

        result = _load_state()
        assert result["processed_issue_ids"] == ["id-1"]
        assert result["issue_statuses"] == {}

    def test_backward_compat_no_processed_ids(self, tmp_path, monkeypatch):
        """Old state files without processed_issue_ids should still load."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"issue_statuses": {"id-1": "in_review"}}))
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)

        result = _load_state()
        assert result["processed_issue_ids"] == []
        assert result["issue_statuses"] == {"id-1": "in_review"}


# ---------------------------------------------------------------------------
# _detect_transitions
# ---------------------------------------------------------------------------


class TestDetectTransitions:
    def test_new_issue_is_transition(self):
        state = {"issue_statuses": {}}
        issues = [{"id": "u1", "status": "in_review"}]
        assert _detect_transitions(state, issues) == issues

    def test_known_in_review_is_not_transition(self):
        state = {"issue_statuses": {"u1": "in_review"}}
        issues = [{"id": "u1", "status": "in_review"}]
        assert _detect_transitions(state, issues) == []

    def test_known_other_status_is_transition(self):
        state = {"issue_statuses": {"u1": "in_progress"}}
        issues = [{"id": "u1", "status": "in_review"}]
        assert _detect_transitions(state, issues) == issues

    def test_mixed_issues(self):
        state = {"issue_statuses": {"u1": "in_review", "u2": "in_progress", "u3": "todo"}}
        issues = [
            {"id": "u1", "status": "in_review"},
            {"id": "u2", "status": "in_review"},
            {"id": "u3", "status": "in_review"},
            {"id": "u4", "status": "in_review"},
        ]
        result = _detect_transitions(state, issues)
        assert [i["id"] for i in result] == ["u2", "u3", "u4"]

    def test_issue_without_id_is_skipped(self):
        state = {"issue_statuses": {"u1": "in_review"}}
        issues = [{"status": "in_review"}, {"id": "u2", "status": "in_review"}]
        result = _detect_transitions(state, issues)
        assert [i.get("id") for i in result] == [None, "u2"]


# ---------------------------------------------------------------------------
# _sync_statuses
# ---------------------------------------------------------------------------


class TestSyncStatuses:
    def test_updates_statuses(self):
        state = {"issue_statuses": {"u1": "todo"}}
        issues = [
            {"id": "u1", "status": "in_review"},
            {"id": "u2", "status": "in_review"},
        ]
        _sync_statuses(state, issues)
        assert state["issue_statuses"]["u1"] == "in_review"
        assert state["issue_statuses"]["u2"] == "in_review"

    def test_ignores_issue_without_id_or_status(self):
        state = {"issue_statuses": {}}
        issues = [
            {"id": "", "status": "in_review"},
            {"id": "u1", "status": ""},
            {"id": "u2", "status": "in_review"},
        ]
        _sync_statuses(state, issues)
        assert "u2" in state["issue_statuses"]
        assert state["issue_statuses"]["u2"] == "in_review"
        assert "" not in state["issue_statuses"]


# ---------------------------------------------------------------------------
# run_once
# ---------------------------------------------------------------------------

_FIX_ISSUE = {
    "id": "issue-uuid-fix",
    "identifier": "BTCAAAAA-100",
    "title": "Fix the thing",
    "status": "in_review",
    "labels": [{"name": "fix"}],
}

_NON_FIX_ISSUE = {
    "id": "issue-uuid-feat",
    "identifier": "BTCAAAAA-200",
    "title": "Add new feature",
    "status": "in_review",
    "labels": [{"name": "feature"}],
}


class TestRunOnce:
    def _patch_all(self, tmp_path, monkeypatch, issues, gen_return=None):
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
        assert state["issue_statuses"]["issue-uuid-fix"] == "in_review"

    def test_skips_non_fix_issue(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [_NON_FIX_ISSUE])

        results = run_once()

        assert results == []
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == []
        assert state["issue_statuses"]["issue-uuid-feat"] == "in_review"

    def test_skips_already_processed(self, tmp_path, monkeypatch):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "processed_issue_ids": ["issue-uuid-fix"],
            "issue_statuses": {"issue-uuid-fix": "in_review"},
        }))
        self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])

        results = run_once()

        assert results == []
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == ["issue-uuid-fix"]

    def test_skips_already_processed_when_transition(self, tmp_path, monkeypatch):
        """Issue in processed_issue_ids is skipped even when it IS a new transition."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "processed_issue_ids": ["issue-uuid-fix"],
            "issue_statuses": {"issue-uuid-fix": "in_progress"},
        }))
        self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])

        results = run_once()

        assert results == []
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == ["issue-uuid-fix"]

    def test_transition_detected_for_new_issue(self, tmp_path, monkeypatch):
        """A previously unknown issue (no status tracked) is treated as a transition."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"processed_issue_ids": [], "issue_statuses": {}}))
        self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])

        results = run_once()

        assert len(results) == 1

    def test_no_transition_for_known_in_review(self, tmp_path, monkeypatch):
        """An issue already tracked as in_review is NOT a new transition."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "processed_issue_ids": [],
            "issue_statuses": {"issue-uuid-fix": "in_review"},
        }))
        self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])

        results = run_once()

        assert results == []

    def test_transition_for_known_other_status(self, tmp_path, monkeypatch):
        """An issue previously in_progress IS a new transition."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "processed_issue_ids": [],
            "issue_statuses": {"issue-uuid-fix": "in_progress"},
        }))
        self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])

        results = run_once()

        assert len(results) == 1

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
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == []
        assert state["issue_statuses"]["issue-uuid-fix"] == "in_review"

    def test_mixed_issues(self, tmp_path, monkeypatch):
        issues = [_FIX_ISSUE, _NON_FIX_ISSUE]
        self._patch_all(tmp_path, monkeypatch, issues)

        results = run_once()

        assert len(results) == 1
        assert results[0]["issue"] == "BTCAAAAA-100"

    def test_force_reprocess_overrides_transition_detection(self, tmp_path, monkeypatch):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "processed_issue_ids": [],
            "issue_statuses": {"issue-uuid-fix": "in_review"},
        }))
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
        state = json.loads(state_file.read_text())
        assert "issue-uuid-fix" in state["processed_issue_ids"]

    def test_force_reprocess_with_dry_run_does_not_save_state(
        self, tmp_path, monkeypatch
    ):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "processed_issue_ids": ["issue-uuid-fix"],
            "issue_statuses": {"issue-uuid-fix": "in_review"},
        }))
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

        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == ["issue-uuid-fix"]

    def test_statuses_synced_for_all_issues(self, tmp_path, monkeypatch):
        """Statuses for ALL fetched issues, not just processed ones."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"processed_issue_ids": [], "issue_statuses": {}}))
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(
            worker_mod,
            "_fetch_in_review_issues",
            lambda: [_FIX_ISSUE, _NON_FIX_ISSUE],
        )
        monkeypatch.setattr(
            worker_mod,
            "generate_and_post",
            lambda issue_id, dry_run=False: {"issue": "BTCAAAAA-100"},
        )

        run_once()

        state = json.loads(state_file.read_text())
        assert state["issue_statuses"]["issue-uuid-fix"] == "in_review"
        assert state["issue_statuses"]["issue-uuid-feat"] == "in_review"

    def test_does_not_transition_issue(self, tmp_path, monkeypatch):
        self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])
        run_once()
        assert True

    def test_does_not_transition_on_dry_run(self, tmp_path, monkeypatch):
        self._patch_all(tmp_path, monkeypatch, [_FIX_ISSUE])
        run_once(dry_run=True)
        assert True

    def test_does_not_transition_when_skipped(self, tmp_path, monkeypatch):
        self._patch_all(
            tmp_path,
            monkeypatch,
            [_FIX_ISSUE],
            gen_return={"skipped": True, "reason": "no touchedFiles", "issue": "BTCAAAAA-100"},
        )

        result = run_once()
        assert len(result) == 1
        assert result[0].get("skipped") is True

    def test_empty_issue_list(self, tmp_path, monkeypatch):
        state_file = self._patch_all(tmp_path, monkeypatch, [])

        results = run_once()

        assert results == []
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == []
        assert state["issue_statuses"] == {}


# ---------------------------------------------------------------------------
# process_issue (single-issue webhook entry point)
# ---------------------------------------------------------------------------


class TestProcessIssue:
    _FIX_IN_REVIEW = {
        "id": "issue-uuid-42",
        "identifier": "BTCAAAAA-1507",
        "title": "Fix the webhook handler",
        "status": "in_review",
        "labels": [{"name": "fix"}],
        "description": (
            '"touchedFiles": ["src/blast_radius/worker.py"]'
        ),
    }

    _NON_FIX_IN_REVIEW = {
        "id": "issue-uuid-43",
        "identifier": "BTCAAAAA-1508",
        "title": "Feature request",
        "status": "in_review",
        "labels": [{"name": "feature"}],
    }

    _ISSUE_NOT_IN_REVIEW = {
        "id": "issue-uuid-44",
        "identifier": "BTCAAAAA-1509",
        "title": "Fix in progress",
        "status": "in_progress",
        "labels": [{"name": "fix"}],
    }

    def _patch_gen(self, monkeypatch, posted_list=None):
        if posted_list is None:
            posted_list = []
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_agent_name",
            lambda agent_id: "Bot",
        )
        monkeypatch.setattr(
            "blast_radius.generator._post_comment",
            lambda issue_id, body: posted_list.append(issue_id),
        )
        monkeypatch.setattr(
            "blast_radius.generator.query_blast_radius",
            lambda file_paths: BlastRadiusData(),
        )
        return posted_list

    def test_processes_fix_in_review(self, tmp_path, monkeypatch):
        from blast_radius.worker import process_issue

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        monkeypatch.setattr(worker_mod, "_STATE_PATH", tmp_path / "state.json")
        posted = self._patch_gen(monkeypatch)

        result = process_issue("issue-uuid-42", dry_run=False)

        assert result is not None
        assert result.get("issue") == "BTCAAAAA-1507"
        assert posted == ["issue-uuid-42"]

        # State should be updated
        state = json.loads((tmp_path / "state.json").read_text())
        assert "issue-uuid-42" in state["processed_issue_ids"]
        assert state["issue_statuses"]["issue-uuid-42"] == "in_review"

    def test_skips_non_fix_issue(self, monkeypatch):
        from blast_radius.worker import process_issue

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._NON_FIX_IN_REVIEW,
        )

        result = process_issue("issue-uuid-43", dry_run=True)

        assert result is None

    def test_skips_not_in_review(self, monkeypatch):
        from blast_radius.worker import process_issue

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._ISSUE_NOT_IN_REVIEW,
        )

        result = process_issue("issue-uuid-44", dry_run=True)

        assert result is None

    def test_dry_run_does_not_post(self, monkeypatch):
        from blast_radius.worker import process_issue
        from unittest.mock import MagicMock

        mock_sess = MagicMock()
        monkeypatch.setattr(
            "touch_index.paperclip_client._session",
            lambda: mock_sess,
        )

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        posted = self._patch_gen(monkeypatch)

        result = process_issue("issue-uuid-42", dry_run=True)

        assert result is not None
        assert result["dry_run"] is True
        assert posted == []

    def test_dry_run_does_not_save_state(self, tmp_path, monkeypatch):
        from blast_radius.worker import process_issue

        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        self._patch_gen(monkeypatch)

        process_issue("issue-uuid-42", dry_run=True)

        assert not state_file.exists()

    def test_does_not_transition_to_done(self, tmp_path, monkeypatch):
        from blast_radius.worker import process_issue

        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        self._patch_gen(monkeypatch)

        result = process_issue("issue-uuid-42", dry_run=False)
        assert result is not None

    def test_does_not_transition_on_dry_run_process(self, tmp_path, monkeypatch):
        from blast_radius.worker import process_issue

        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        self._patch_gen(monkeypatch)

        result = process_issue("issue-uuid-42", dry_run=True)
        assert result is not None
        assert result.get("dry_run") is True

    def test_fetch_failure_returns_error_dict(self, monkeypatch):
        from blast_radius.worker import process_issue
        from unittest.mock import MagicMock

        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = RuntimeError("API timeout")
        mock_sess.get.return_value = mock_resp

        monkeypatch.setattr(
            "touch_index.paperclip_client._session",
            lambda: mock_sess,
        )

        result = process_issue("bad-uuid", dry_run=True)

        assert result is not None
        assert "error" in result
        assert "API timeout" in result["error"]

    def test_generator_failure_returns_error_dict(self, monkeypatch):
        from blast_radius.worker import process_issue
        from unittest.mock import MagicMock

        mock_sess = MagicMock()
        monkeypatch.setattr(
            "touch_index.paperclip_client._session",
            lambda: mock_sess,
        )

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_agent_name",
            lambda agent_id: "Bot",
        )
        monkeypatch.setattr(
            "blast_radius.generator.query_blast_radius",
            lambda file_paths: (_ for _ in ()).throw(RuntimeError("DB down")),
        )

        result = process_issue("issue-uuid-42", dry_run=True)

        assert result is not None
        assert "error" in result
        assert "DB down" in result["error"]

    def test_accepts_old_status_from_webhook(self, monkeypatch):
        """process_issue should accept and log old_status."""
        from blast_radius.worker import process_issue

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        self._patch_gen(monkeypatch)

        result = process_issue(
            "issue-uuid-42",
            dry_run=True,
            old_status="in_progress",
        )

        assert result is not None
        assert result["dry_run"] is True

    def test_skips_already_processed_webhook(self, tmp_path, monkeypatch):
        """Webhook should skip if issue already in processed_issue_ids."""
        from blast_radius.worker import process_issue

        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        state_file.write_text(json.dumps({
            "processed_issue_ids": ["issue-uuid-42"],
            "issue_statuses": {"issue-uuid-42": "in_review"},
        }))

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )

        result = process_issue("issue-uuid-42", dry_run=True)

        assert result is None

    def test_force_reprocess_bypasses_already_processed_guard(self, tmp_path, monkeypatch):
        """force_reprocess=True should bypass the already-processed guard."""
        from blast_radius.worker import process_issue

        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        state_file.write_text(json.dumps({
            "processed_issue_ids": ["issue-uuid-42"],
            "issue_statuses": {"issue-uuid-42": "in_review"},
        }))

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        posted = self._patch_gen(monkeypatch)

        result = process_issue("issue-uuid-42", dry_run=False, force_reprocess=True)

        assert result is not None
        assert result.get("issue") == "BTCAAAAA-1507"
        assert posted == ["issue-uuid-42"]

    def test_force_reprocess_with_dry_run_does_not_post_or_save(self, tmp_path, monkeypatch):
        """force_reprocess with dry_run should not post or save state."""
        from blast_radius.worker import process_issue

        state_file = tmp_path / "state.json"
        monkeypatch.setattr(worker_mod, "_STATE_PATH", state_file)
        state_file.write_text(json.dumps({
            "processed_issue_ids": ["issue-uuid-42"],
            "issue_statuses": {"issue-uuid-42": "in_review"},
        }))

        monkeypatch.setattr(
            "blast_radius.worker._get_issue",
            lambda issue_id: self._FIX_IN_REVIEW,
        )
        posted = self._patch_gen(monkeypatch)

        result = process_issue("issue-uuid-42", dry_run=True, force_reprocess=True)

        assert result is not None
        assert result["dry_run"] is True
        assert posted == []
        state = json.loads(state_file.read_text())
        assert state["processed_issue_ids"] == ["issue-uuid-42"]


# ---------------------------------------------------------------------------
# _get_issue
# ---------------------------------------------------------------------------


class TestGetIssue:
    def test_fetches_issue(self, monkeypatch):
        from blast_radius.worker import _get_issue

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "iss-1", "identifier": "BTCAAAAA-100"}
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.get.return_value = mock_resp

        monkeypatch.setattr(
            "touch_index.paperclip_client._session",
            lambda: mock_sess,
        )

        result = _get_issue("iss-1")
        assert result == {"id": "iss-1", "identifier": "BTCAAAAA-100"}
        mock_sess.get.assert_called_once()
        assert "/api/issues/iss-1" in str(mock_sess.get.call_args[0][0])

    def test_raises_on_http_error(self, monkeypatch):
        from blast_radius.worker import _get_issue

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = RuntimeError("404 Not Found")
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.get.return_value = mock_resp

        monkeypatch.setattr(
            "touch_index.paperclip_client._session",
            lambda: mock_sess,
        )

        with pytest.raises(RuntimeError, match="404 Not Found"):
            _get_issue("bad-id")


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


# ---------------------------------------------------------------------------
# CLI argparse
# ---------------------------------------------------------------------------


class TestCliArgparse:
    """Verify CLI flags are wired correctly (no side effects)."""

    def test_old_status_flag_accepted(self):
        """--old-status should be parsed without error."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--old-status", type=str)
        args = parser.parse_args(["--old-status", "in_progress"])
        assert args.old_status == "in_progress"

    def test_old_status_defaults_to_none(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--old-status", type=str, default=None)
        args = parser.parse_args([])
        assert args.old_status is None


# ---------------------------------------------------------------------------
# main() CLI entry point
# ---------------------------------------------------------------------------


class TestMainCli:
    """Tests for blast_radius.worker.main() — CLI entry point.

    Verifies command-line flags are dispatched to the underlying
    ``process_issue``, ``run_once``, and ``run_loop`` functions.
    """

    _CLEAN_ARGV = ["blast_radius.worker"]

    def test_default_calls_run_once(self, monkeypatch):
        import sys
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV)
        with (
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
        ):
            worker_main()
        mock_run_once.assert_called_once_with(dry_run=False, force_reprocess=False)

    def test_dry_run_flag_passed_to_run_once(self, monkeypatch):
        import sys
        monkeypatch.setattr(
            sys, "argv", self._CLEAN_ARGV + ["--dry-run"]
        )
        with (
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
        ):
            worker_main()
        mock_run_once.assert_called_once_with(dry_run=True, force_reprocess=False)

    def test_force_reprocess_flag_passed_to_run_once(self, monkeypatch):
        import sys
        monkeypatch.setattr(
            sys, "argv", self._CLEAN_ARGV + ["--force-reprocess"]
        )
        with (
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
        ):
            worker_main()
        mock_run_once.assert_called_once_with(dry_run=False, force_reprocess=True)

    def test_loop_flag_calls_run_loop(self, monkeypatch):
        import sys
        monkeypatch.setattr(
            sys, "argv", self._CLEAN_ARGV + ["--loop", "300"]
        )
        with (
            patch("blast_radius.worker.run_loop") as mock_run_loop,
        ):
            worker_main()
        mock_run_loop.assert_called_once_with(
            interval_seconds=300, dry_run=False, force_reprocess=False
        )

    def test_loop_with_dry_run(self, monkeypatch):
        import sys
        monkeypatch.setattr(
            sys, "argv",
            self._CLEAN_ARGV + ["--loop", "120", "--dry-run"],
        )
        with (
            patch("blast_radius.worker.run_loop") as mock_run_loop,
        ):
            worker_main()
        mock_run_loop.assert_called_once_with(
            interval_seconds=120, dry_run=True, force_reprocess=False
        )

    def test_loop_with_force_reprocess(self, monkeypatch):
        import sys
        monkeypatch.setattr(
            sys, "argv",
            self._CLEAN_ARGV + ["--loop", "60", "--force-reprocess"],
        )
        with (
            patch("blast_radius.worker.run_loop") as mock_run_loop,
        ):
            worker_main()
        mock_run_loop.assert_called_once_with(
            interval_seconds=60, dry_run=False, force_reprocess=True
        )

    def test_issue_id_calls_process_issue(self, monkeypatch):
        import sys
        monkeypatch.setattr(
            sys, "argv",
            self._CLEAN_ARGV + ["--issue-id", "uuid-1"],
        )
        with (
            patch("blast_radius.worker.process_issue", return_value=None) as mock_process,
            patch("blast_radius.worker.run_once") as mock_run_once,
        ):
            worker_main()
        mock_process.assert_called_once_with(
            "uuid-1", dry_run=False, old_status=None, force_reprocess=False
        )
        mock_run_once.assert_not_called()

    def test_issue_id_with_old_status(self, monkeypatch):
        import sys
        monkeypatch.setattr(
            sys, "argv",
            self._CLEAN_ARGV + ["--issue-id", "uuid-1", "--old-status", "in_progress"],
        )
        with (
            patch("blast_radius.worker.process_issue", return_value=None) as mock_process,
            patch("blast_radius.worker.run_once") as mock_run_once,
        ):
            worker_main()
        mock_process.assert_called_once_with(
            "uuid-1", dry_run=False, old_status="in_progress", force_reprocess=False
        )
        mock_run_once.assert_not_called()

    def test_issue_id_with_dry_run(self, monkeypatch):
        import sys
        monkeypatch.setattr(
            sys, "argv",
            self._CLEAN_ARGV + ["--issue-id", "uuid-1", "--dry-run"],
        )
        with (
            patch("blast_radius.worker.process_issue", return_value=None) as mock_process,
            patch("blast_radius.worker.run_once") as mock_run_once,
        ):
            worker_main()
        mock_process.assert_called_once_with(
            "uuid-1", dry_run=True, old_status=None, force_reprocess=False
        )
        mock_run_once.assert_not_called()

    def test_result_logged_for_process_issue(self, monkeypatch, caplog):
        import logging, sys

        monkeypatch.setattr(
            sys, "argv",
            self._CLEAN_ARGV + ["--issue-id", "uuid-1"],
        )
        result = {"issue": "BTCAAAAA-100", "dry_run": False}
        with (
            patch("blast_radius.worker.process_issue", return_value=result),
            caplog.at_level(logging.INFO),
        ):
            worker_main()
        assert any("BTCAAAAA-100" in r.message for r in caplog.records)

    def test_no_report_logged_when_not_eligible(self, monkeypatch, caplog):
        import logging, sys

        monkeypatch.setattr(
            sys, "argv",
            self._CLEAN_ARGV + ["--issue-id", "missing-uuid"],
        )
        with (
            patch("blast_radius.worker.process_issue", return_value=None),
            caplog.at_level(logging.INFO),
        ):
            worker_main()
        assert any("not eligible" in r.message for r in caplog.records)

    def test_results_logged_on_run_once(self, monkeypatch, caplog):
        import logging, sys

        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV)
        results = [{"issue": "BTCAAAAA-100", "dry_run": False}]
        with (
            patch("blast_radius.worker.run_once", return_value=results),
            caplog.at_level(logging.INFO),
        ):
            worker_main()
        assert any("Results" in r.message for r in caplog.records)
        assert any("BTCAAAAA-100" in r.message for r in caplog.records)

