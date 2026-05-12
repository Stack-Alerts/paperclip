"""Unit tests for blast_radius.worker -- no DB or live network required.

Tests cover state management, issue detection, transition tracking, and the
orchestration entry points (run_once, process_issue, run_loop).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IN_REVIEW_ISSUES = [
    {
        "id": "uuid-fix-1",
        "identifier": "BTCAAAAA-100",
        "title": "Fix null pointer in loader",
        "status": "in_review",
        "labels": [{"name": "fix"}],
    },
    {
        "id": "uuid-bug-1",
        "identifier": "BTCAAAAA-101",
        "title": "Bug: trade list empty",
        "status": "in_review",
        "labels": [{"name": "bug"}],
    },
    {
        "id": "uuid-fr-1",
        "identifier": "BTCAAAAA-200",
        "title": "Add trailing stop feature",
        "status": "in_review",
        "labels": [{"name": "feature"}],
    },
    {
        "id": "uuid-title-match",
        "identifier": "BTCAAAAA-102",
        "title": "Fix regression in optimizer",
        "status": "in_review",
        "labels": [],
    },
]


def _patch_state(tmp_path: Path, data: dict | None = None) -> Path:
    """Write state to a temp path and return it, overriding STATE_PATH."""
    state_file = tmp_path / "blast_radius_state.json"
    if data is not None:
        state_file.write_text(json.dumps(data))
    return state_file


# ---------------------------------------------------------------------------
# _is_fix_issue
# ---------------------------------------------------------------------------


class TestIsFixIssue:
    def test_fix_label(self):
        import blast_radius.worker as worker_mod

        assert worker_mod._is_fix_issue({"labels": [{"name": "fix"}]}) is True

    def test_bug_label(self):
        import blast_radius.worker as worker_mod

        assert worker_mod._is_fix_issue({"labels": [{"name": "bug"}]}) is True

    def test_bugfix_label(self):
        import blast_radius.worker as worker_mod

        assert worker_mod._is_fix_issue({"labels": [{"name": "bugfix"}]}) is True

    def test_case_insensitive_label(self):
        import blast_radius.worker as worker_mod

        assert worker_mod._is_fix_issue({"labels": [{"name": "FIX"}]}) is True

    def test_no_labels(self):
        import blast_radius.worker as worker_mod

        assert worker_mod._is_fix_issue({"labels": [], "title": "Refactor db"}) is False

    def test_title_contains_fix(self):
        import blast_radius.worker as worker_mod

        assert (
            worker_mod._is_fix_issue({"labels": [], "title": "Fix the loader"}) is True
        )

    def test_title_contains_bug(self):
        import blast_radius.worker as worker_mod

        assert (
            worker_mod._is_fix_issue({"labels": [], "title": "Bug: crash on startup"})
            is True
        )

    def test_title_contains_regression(self):
        import blast_radius.worker as worker_mod

        assert (
            worker_mod._is_fix_issue({"labels": [], "title": "Regression in v2.1"})
            is True
        )

    def test_title_contains_hotfix(self):
        import blast_radius.worker as worker_mod

        assert (
            worker_mod._is_fix_issue({"labels": [], "title": "Hotfix for prod"}) is True
        )

    def test_whitespace_label(self):
        import blast_radius.worker as worker_mod

        assert (
            worker_mod._is_fix_issue({"labels": [{"name": "  fix  "}], "title": ""})
            is True
        )

    def test_feature_is_not_fix(self):
        import blast_radius.worker as worker_mod

        assert (
            worker_mod._is_fix_issue(
                {"labels": [{"name": "feature"}], "title": "New thing"}
            )
            is False
        )

    def test_missing_labels_key(self):
        import blast_radius.worker as worker_mod

        assert worker_mod._is_fix_issue({"title": "Some change"}) is False

    def test_non_dict_labels(self):
        import blast_radius.worker as worker_mod

        assert worker_mod._is_fix_issue({"labels": None, "title": ""}) is False

    def test_whitespace_title(self):
        import blast_radius.worker as worker_mod

        assert (
            worker_mod._is_fix_issue({"labels": [], "title": "  Refactor  "}) is False
        )

    def test_substring_fix_in_title_is_not_false_positive(self):
        """A title containing 'fix' not as first word should NOT match."""
        import blast_radius.worker as worker_mod

        assert (
            worker_mod._is_fix_issue(
                {"labels": [], "title": "Impact Gate: scan for fix issues done"}
            )
            is False
        )
        assert (
            worker_mod._is_fix_issue({"labels": [], "title": "Prefix bug in the title"})
            is False
        )


# ---------------------------------------------------------------------------
# _load_state / _save_state
# ---------------------------------------------------------------------------


class TestStatePersistence:
    def test_load_nonexistent_returns_defaults(self, tmp_path):
        import blast_radius.worker as worker_mod

        path = tmp_path / "nonexistent.json"
        with patch.object(worker_mod, "_STATE_PATH", path):
            state = worker_mod._load_state()
        assert state == {"processed_issue_ids": [], "issue_statuses": {}}

    def test_load_corrupt_json_returns_defaults(self, tmp_path):
        import blast_radius.worker as worker_mod

        path = tmp_path / "corrupt.json"
        path.write_text("{bad json")
        with patch.object(worker_mod, "_STATE_PATH", path):
            state = worker_mod._load_state()
        assert state == {"processed_issue_ids": [], "issue_statuses": {}}

    def test_load_missing_keys_filled(self, tmp_path):
        import blast_radius.worker as worker_mod

        path = tmp_path / "partial.json"
        path.write_text(json.dumps({"processed_issue_ids": ["a"]}))
        with patch.object(worker_mod, "_STATE_PATH", path):
            state = worker_mod._load_state()
        assert "issue_statuses" in state
        assert "processed_issue_ids" in state

    def test_load_missing_processed_ids_filled(self, tmp_path):
        import blast_radius.worker as worker_mod

        path = tmp_path / "partial_no_pids.json"
        path.write_text(json.dumps({"issue_statuses": {"uuid-1": "in_review"}}))
        with patch.object(worker_mod, "_STATE_PATH", path):
            state = worker_mod._load_state()
        assert state["processed_issue_ids"] == []
        assert state["issue_statuses"] == {"uuid-1": "in_review"}

    def test_save_and_load_roundtrip(self, tmp_path):
        import blast_radius.worker as worker_mod

        path = tmp_path / "roundtrip.json"
        with patch.object(worker_mod, "_STATE_PATH", path):
            worker_mod._save_state(
                {"processed_issue_ids": ["x"], "issue_statuses": {"x": "in_review"}}
            )
            state = worker_mod._load_state()
        assert state["processed_issue_ids"] == ["x"]
        assert state["issue_statuses"] == {"x": "in_review"}

    def test_save_creates_parent_dir(self, tmp_path):
        import blast_radius.worker as worker_mod

        path = tmp_path / "subdir" / "state.json"
        with patch.object(worker_mod, "_STATE_PATH", path):
            worker_mod._save_state({"processed_issue_ids": [], "issue_statuses": {}})
        assert path.exists()

    def test_load_normal_state(self, tmp_path):
        import blast_radius.worker as worker_mod

        expected = {
            "processed_issue_ids": ["uuid-1"],
            "issue_statuses": {"uuid-1": "in_review"},
        }
        path = tmp_path / "normal.json"
        path.write_text(json.dumps(expected))
        with patch.object(worker_mod, "_STATE_PATH", path):
            state = worker_mod._load_state()
        assert state == expected


# ---------------------------------------------------------------------------
# _detect_transitions
# ---------------------------------------------------------------------------


class TestDetectTransitions:
    def test_new_issue_is_transition(self):
        import blast_radius.worker as worker_mod

        issues = [{"id": "new-uuid"}]
        state = {"issue_statuses": {}}
        assert worker_mod._detect_transitions(state, issues) == issues

    def test_issue_was_not_in_review_is_transition(self):
        import blast_radius.worker as worker_mod

        issues = [{"id": "uuid-1"}]
        state = {"issue_statuses": {"uuid-1": "in_progress"}}
        assert worker_mod._detect_transitions(state, issues) == issues

    def test_issue_already_in_review_is_not_transition(self):
        import blast_radius.worker as worker_mod

        issues = [{"id": "uuid-1"}]
        state = {"issue_statuses": {"uuid-1": "in_review"}}
        assert worker_mod._detect_transitions(state, issues) == []

    def test_mixed_transitions(self):
        import blast_radius.worker as worker_mod

        issues = [{"id": "already"}, {"id": "new"}, {"id": "was-progress"}]
        state = {
            "issue_statuses": {"already": "in_review", "was-progress": "in_progress"}
        }
        result = worker_mod._detect_transitions(state, issues)
        assert [i["id"] for i in result] == ["new", "was-progress"]

    def test_empty_issue_list(self):
        import blast_radius.worker as worker_mod

        assert worker_mod._detect_transitions({}, []) == []

    def test_issue_with_missing_id_is_excluded(self):
        """An issue without an id field cannot be tracked and is excluded."""
        import blast_radius.worker as worker_mod

        issues = [{"identifier": "BTCAAAAA-100"}]
        state = {"issue_statuses": {"": "in_review"}}
        # empty string ID -> found in known with "" -> excluded
        assert worker_mod._detect_transitions(state, issues) == []

    def test_issue_with_none_id_is_excluded(self):
        """An issue with id=None cannot be tracked and is excluded."""
        import blast_radius.worker as worker_mod

        issues = [{"id": None, "identifier": "BTCAAAAA-100"}]
        state = {"issue_statuses": {}}
        assert worker_mod._detect_transitions(state, issues) == []


# ---------------------------------------------------------------------------
# _sync_statuses
# ---------------------------------------------------------------------------


class TestSyncStatuses:
    def test_updates_statuses(self):
        import blast_radius.worker as worker_mod

        state = {"issue_statuses": {}}
        issues = [{"id": "u1", "status": "in_review"}, {"id": "u2", "status": "done"}]
        worker_mod._sync_statuses(state, issues)
        assert state["issue_statuses"] == {"u1": "in_review", "u2": "done"}

    def test_preserves_existing_unrelated(self):
        import blast_radius.worker as worker_mod

        state = {"issue_statuses": {"u3": "in_progress"}}
        issues = [{"id": "u1", "status": "in_review"}]
        worker_mod._sync_statuses(state, issues)
        assert "u3" in state["issue_statuses"]

    def test_skips_empty_id(self):
        import blast_radius.worker as worker_mod

        state = {"issue_statuses": {}}
        issues = [{"id": "", "status": "in_review"}]
        worker_mod._sync_statuses(state, issues)
        assert state["issue_statuses"] == {}

    def test_removes_stale_in_review_entries(self):
        import blast_radius.worker as worker_mod

        state = {
            "issue_statuses": {
                "u1": "in_review",
                "u2": "in_review",
                "u3": "in_progress",
            }
        }
        issues = [{"id": "u1", "status": "in_review"}]
        worker_mod._sync_statuses(state, issues)
        assert "u1" in state["issue_statuses"]
        assert "u2" not in state["issue_statuses"]
        assert state["issue_statuses"]["u3"] == "in_progress"

    def test_no_cleanup_when_fetched_set_empty(self):
        import blast_radius.worker as worker_mod

        state = {"issue_statuses": {"u1": "in_review"}}
        issues: list = []
        worker_mod._sync_statuses(state, issues)
        assert state["issue_statuses"] == {"u1": "in_review"}

    def test_skips_empty_status(self):
        import blast_radius.worker as worker_mod

        state = {"issue_statuses": {}}
        issues = [{"id": "u1", "status": ""}]
        worker_mod._sync_statuses(state, issues)
        assert state["issue_statuses"] == {}


# ---------------------------------------------------------------------------
# _fetch_in_review_issues
# ---------------------------------------------------------------------------


class TestFetchInReviewIssues:
    def test_calls_paginate(self):
        import blast_radius.worker as worker_mod

        with patch("blast_radius.worker._paginate", return_value=[{"id": "x"}]) as mock:
            result = worker_mod._fetch_in_review_issues()
        assert result == [{"id": "x"}]
        args, kwargs = mock.call_args
        assert {"status": "in_review"} == args[1]


# ---------------------------------------------------------------------------
# run_once -- main polling entry point
# ---------------------------------------------------------------------------


class TestRunOnce:
    def test_fix_issue_processed(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        assert len(results) == 3  # 3 fix/bug issues (100, 101, 102)
        assert mock_gen.call_count == 3
        assert state_file.exists()

    def test_dry_run_skips_state_save(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=True)

        assert len(results) == 3
        assert mock_gen.call_count == 3
        # State should not exist (save skipped on dry-run)
        assert not state_file.exists()

    def test_skips_already_processed(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {
                "processed_issue_ids": ["uuid-fix-1"],
                "issue_statuses": {"uuid-fix-1": "in_review"},
            },
        )
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        # uuid-fix-1 is already processed and already in_review, so no transition
        assert len(results) == 2  # 101 and 102 are transitions
        mock_gen.assert_called()

    def test_force_reprocess_processes_all(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {
                "processed_issue_ids": ["uuid-fix-1", "uuid-bug-1"],
                "issue_statuses": {
                    "uuid-fix-1": "in_review",
                    "uuid-bug-1": "in_review",
                },
            },
        )
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False, force_reprocess=True)

        assert len(results) == 3
        assert mock_gen.call_count == 3

    def test_generator_error_does_not_halt(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issues = _IN_REVIEW_ISSUES

        def _side_effect(issue_id, **kw):
            if issue_id == "uuid-fix-1":
                raise RuntimeError("API timeout")
            return {"ok": True}

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch(
                "blast_radius.worker.generate_and_post", side_effect=_side_effect
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        # All 3 attempted, 1 failed, 2 successful
        assert len(results) == 3
        assert mock_gen.call_count == 3
        error_results = [r for r in results if "error" in r]
        assert len(error_results) == 1

    def test_failed_candidate_not_persisted_as_in_review(self, tmp_path):
        """A candidate that fails during generate_and_post should NOT have
        its status persisted as ``in_review``, so it can be re-detected as a
        transition on the next poll rather than silently dropped forever."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issues = _IN_REVIEW_ISSUES

        def _side_effect(issue_id, **kw):
            if issue_id == "uuid-fix-1":
                raise RuntimeError("API timeout")
            return {"ok": True}

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch("blast_radius.worker.generate_and_post", side_effect=_side_effect),
        ):
            worker_mod.run_once(dry_run=False)

        state = json.loads(state_file.read_text())
        statuses = state.get("issue_statuses", {})
        # The failed issue's status should NOT be "in_review" in state
        assert "uuid-fix-1" not in statuses or statuses["uuid-fix-1"] != "in_review", (
            "Failed candidate should not be persisted as in_review"
        )
        # Other issues should still have their statuses synced
        assert statuses.get("uuid-bug-1") == "in_review"
        assert statuses.get("uuid-title-match") == "in_review"
        # The failed issue should NOT be in processed_issue_ids
        assert "uuid-fix-1" not in state.get("processed_issue_ids", [])

    def test_skipped_issue_not_marked_processed(self, tmp_path):
        """A skipped issue (no touchedFiles) should NOT be marked as
        processed or have its status persisted as in_review, so it can be
        re-detected as a transition on the next poll."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={
                    "skipped": True,
                    "reason": "no touchedFiles",
                    "issue": "BTCAAAAA-100",
                },
            ),
        ):
            results = worker_mod.run_once(dry_run=False)

        assert len(results) == 3  # All 3 fix issues attempted
        assert all(r.get("skipped") for r in results)
        state = json.loads(state_file.read_text())
        # None of the skipped issues should be in processed_issue_ids
        assert state.get("processed_issue_ids", []) == []
        statuses = state.get("issue_statuses", {})
        # Skipped issues should NOT have persisted statuses (removed by skipped_ids cleanup)
        for issue in _IN_REVIEW_ISSUES:
            if issue.get("id") in ("uuid-fr-1",):
                continue
            assert (
                issue["id"] not in statuses or statuses[issue["id"]] != "in_review"
            ), f"Skipped issue {issue['id']} should not persist as in_review"

    def test_no_fix_issues_in_review(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        non_fix = [
            {
                "id": "fr-1",
                "identifier": "BTCAAAAA-200",
                "title": "Feature",
                "status": "in_review",
                "labels": [{"name": "feature"}],
            }
        ]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=non_fix),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        assert results == []
        mock_gen.assert_not_called()

    def test_transition_detection_respects_state(self, tmp_path):
        """Issues already in_review in state are not processed unless force."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {
                "processed_issue_ids": [],
                "issue_statuses": {
                    "uuid-fix-1": "in_review",
                    "uuid-bug-1": "in_progress",
                },
            },
        )
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        # uuid-fix-1 is already in_review in state -> NOT a transition
        # uuid-bug-1 was in_progress -> IS a transition
        # uuid-title-match was unknown -> IS a transition
        assert len(results) == 2
        processed_ids = {
            r.get("issue") or r.get("issue_identifier", "") for r in results
        }
        assert mock_gen.call_count == 2

    def test_skips_processed_issue_that_also_transitioned(self, tmp_path):
        """A processed issue that transitions to in_review is skipped by the
        continue guard (lines 179-183) rather than re-processed."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {
                "processed_issue_ids": ["uuid-bug-1"],
                "issue_statuses": {"uuid-bug-1": "in_progress"},
            },
        )
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        # uuid-bug-1 was in_progress -> IS a transition, but already processed -> continue
        # uuid-fix-1 and uuid-title-match are new -> processed
        assert len(results) == 2
        assert mock_gen.call_count == 2
        state = json.loads(state_file.read_text())
        # uuid-bug-1 preserved from initial state, uuid-fix-1 and uuid-title-match added
        assert len(state.get("processed_issue_ids", [])) == 3

    def test_empty_issues_list(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=[]),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        assert results == []
        mock_gen.assert_not_called()

    def test_state_issue_statuses_populated_after_run_once(self, tmp_path):
        """After run_once, the state file's issue_statuses should contain
        status data for ALL fetched issues (not just fix/bug ones)."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch("blast_radius.worker.generate_and_post", return_value={"ok": True}),
        ):
            worker_mod.run_once(dry_run=False)

        state = json.loads(state_file.read_text())
        statuses = state.get("issue_statuses", {})
        assert statuses["uuid-fix-1"] == "in_review"
        assert statuses["uuid-bug-1"] == "in_review"
        assert statuses["uuid-fr-1"] == "in_review"
        assert statuses["uuid-title-match"] == "in_review"

    def test_run_once_cleans_stale_statuses(self, tmp_path):
        """run_once should remove stale in_review entries that are no longer
        in the fetched set, so future re-transitions are detected correctly."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {
                "processed_issue_ids": [],
                "issue_statuses": {
                    "uuid-stale": "in_review",
                    "uuid-fix-1": "in_progress",
                },
            },
        )
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker._fetch_in_review_issues", return_value=issues),
            patch("blast_radius.worker.generate_and_post", return_value={"ok": True}),
        ):
            worker_mod.run_once(dry_run=False)

        state = json.loads(state_file.read_text())
        statuses = state.get("issue_statuses", {})
        assert "uuid-stale" not in statuses, "stale entry should have been removed"
        assert statuses["uuid-fix-1"] == "in_review"


# ---------------------------------------------------------------------------
# process_issue -- single-issue webhook entry point
# ---------------------------------------------------------------------------


class TestProcessIssue:
    def test_processes_fix_issue(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            result = worker_mod.process_issue("uuid-fix-1", dry_run=False)

        assert result == {"ok": True}
        mock_gen.assert_called_once()

    def test_process_issue_saves_status_to_state(self, tmp_path):
        """After a successful process_issue, the state file's issue_statuses
        should include the processed issue with its current status."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch("blast_radius.worker.generate_and_post", return_value={"ok": True}),
        ):
            worker_mod.process_issue("uuid-fix-1", dry_run=False)

        state = json.loads(state_file.read_text())
        statuses = state.get("issue_statuses", {})
        assert statuses["uuid-fix-1"] == "in_review"
        assert "uuid-fix-1" in state.get("processed_issue_ids", [])

    def test_dry_run_skips_state_save(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            result = worker_mod.process_issue("uuid-fix-1", dry_run=True)

        assert result == {"ok": True}
        mock_gen.assert_called_once()
        assert not state_file.exists()

    def test_skips_non_in_review(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = {
            "id": "uuid-1",
            "identifier": "BTCAAAAA-100",
            "status": "in_progress",
            "labels": [{"name": "fix"}],
        }

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            result = worker_mod.process_issue("uuid-1", dry_run=False)

        assert result is None
        mock_gen.assert_not_called()

    def test_skips_non_fix_issue(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = {
            "id": "uuid-fr",
            "identifier": "BTCAAAAA-200",
            "status": "in_review",
            "labels": [{"name": "feature"}],
            "title": "New feature",
        }

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            result = worker_mod.process_issue("uuid-fr", dry_run=False)

        assert result is None
        mock_gen.assert_not_called()

    def test_skips_already_processed(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path, {"processed_issue_ids": ["uuid-fix-1"], "issue_statuses": {}}
        )
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            result = worker_mod.process_issue("uuid-fix-1", dry_run=False)

        assert result is None
        mock_gen.assert_not_called()

    def test_force_reprocess_overrides_already_processed(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path, {"processed_issue_ids": ["uuid-fix-1"], "issue_statuses": {}}
        )
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post", return_value={"ok": True}
            ) as mock_gen,
        ):
            result = worker_mod.process_issue(
                "uuid-fix-1", dry_run=False, force_reprocess=True
            )

        assert result == {"ok": True}
        mock_gen.assert_called_once()

    def test_fetch_failure_returns_error(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch(
                "blast_radius.worker.get_issue_by_id",
                side_effect=RuntimeError("API down"),
            ),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            result = worker_mod.process_issue("bad-uuid", dry_run=False)

        assert result is not None
        assert "error" in result
        assert "API down" in result["error"]
        mock_gen.assert_not_called()

    def test_issue_not_found_returns_error(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=None),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            result = worker_mod.process_issue("missing", dry_run=False)

        assert result is not None
        assert "error" in result
        mock_gen.assert_not_called()

    def test_generator_error_caught(self, tmp_path):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post",
                side_effect=RuntimeError("gen failed"),
            ),
        ):
            result = worker_mod.process_issue("uuid-fix-1", dry_run=False)

        assert result is not None
        assert "error" in result
        assert "gen failed" in result["error"]

    def test_tracks_status_when_leaving_in_review(self, tmp_path):
        """When old_status=in_review and current status is different, state is updated."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {"processed_issue_ids": [], "issue_statuses": {"uuid-1": "in_review"}},
        )
        issue = {
            "id": "uuid-1",
            "identifier": "BTCAAAAA-100",
            "status": "in_progress",
            "labels": [{"name": "fix"}],
        }

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
        ):
            result = worker_mod.process_issue(
                "uuid-1", dry_run=False, old_status="in_review"
            )

        assert result is None
        state = json.loads(state_file.read_text())
        assert state["issue_statuses"]["uuid-1"] == "in_progress"

    def test_tracks_status_leave_in_review_dry_run(self, tmp_path):
        """On dry_run, state is NOT updated when leaving in_review."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {"processed_issue_ids": [], "issue_statuses": {"uuid-1": "in_review"}},
        )
        issue = {
            "id": "uuid-1",
            "identifier": "BTCAAAAA-100",
            "status": "in_progress",
            "labels": [{"name": "fix"}],
        }

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
        ):
            result = worker_mod.process_issue(
                "uuid-1", dry_run=True, old_status="in_review"
            )

        assert result is None
        state = json.loads(state_file.read_text())
        assert state["issue_statuses"]["uuid-1"] == "in_review"  # unchanged

    def test_with_old_status_logs_transition(self, tmp_path, caplog):
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch("blast_radius.worker.generate_and_post", return_value={"ok": True}),
            caplog.at_level(logging.INFO),
        ):
            worker_mod.process_issue(
                "uuid-fix-1", dry_run=False, old_status="in_progress"
            )

        assert any("transitioned" in r.message for r in caplog.records)

    def test_skipped_issue_not_persisted_on_process(self, tmp_path):
        """When process_issue's generate_and_post returns a skipped result,
        the issue should NOT be added to processed_issue_ids or have its
        status persisted, so a future re-trigger can detect it."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={
                    "skipped": True,
                    "reason": "no touchedFiles",
                    "issue": "BTCAAAAA-100",
                },
            ),
        ):
            result = worker_mod.process_issue("uuid-fix-1", dry_run=False)

        assert result == {
            "skipped": True,
            "reason": "no touchedFiles",
            "issue": "BTCAAAAA-100",
        }
        # State should not exist (skipped result should not trigger save)
        assert not state_file.exists()

    def test_skipped_issue_dry_run_no_persist(self, tmp_path):
        """On dry_run, a skipped result does nothing to state (no save)."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issue = _IN_REVIEW_ISSUES[0]

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={
                    "skipped": True,
                    "reason": "no touchedFiles",
                    "issue": "BTCAAAAA-100",
                },
            ),
        ):
            result = worker_mod.process_issue("uuid-fix-1", dry_run=True)

        assert result.get("skipped") is True
        assert not state_file.exists()


# ---------------------------------------------------------------------------
# run_loop
# ---------------------------------------------------------------------------


class TestRunLoop:
    def test_loop_calls_run_once(self):
        import blast_radius.worker as worker_mod

        def _run_once(**kw):
            raise SystemExit(0)

        with (
            patch("blast_radius.worker.run_once", side_effect=_run_once) as mock_run,
        ):
            with pytest.raises(SystemExit):
                worker_mod.run_loop(interval_seconds=0)

        assert mock_run.call_count == 1

    def test_loop_handles_exception(self):
        import blast_radius.worker as worker_mod

        call_count = 0

        def _run_once(**kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("boom")
            raise SystemExit(0)

        with (
            patch("blast_radius.worker.run_once", side_effect=_run_once),
        ):
            with pytest.raises(SystemExit):
                worker_mod.run_loop(interval_seconds=0)

        assert call_count == 2


# ---------------------------------------------------------------------------
# main() -- CLI entry point
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_issue_id_calls_process_issue(self, monkeypatch):
        import blast_radius.worker as worker_mod

        with (
            patch(
                "blast_radius.worker.process_issue", return_value={"ok": True}
            ) as mock_process,
        ):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--issue-id", "uuid-1"])
            worker_mod.main()

        mock_process.assert_called_once()
        args, kwargs = mock_process.call_args
        assert args[0] == "uuid-1"

    def test_main_issue_id_dry_run(self, monkeypatch):
        import blast_radius.worker as worker_mod

        with (
            patch(
                "blast_radius.worker.process_issue", return_value={"ok": True}
            ) as mock_process,
        ):
            monkeypatch.setattr(
                "sys.argv", ["blast_radius", "--issue-id", "uuid-1", "--dry-run"]
            )
            worker_mod.main()

        _, kwargs = mock_process.call_args
        assert kwargs.get("dry_run") is True

    def test_main_issue_id_old_status(self, monkeypatch):
        import blast_radius.worker as worker_mod

        with (
            patch(
                "blast_radius.worker.process_issue", return_value={"ok": True}
            ) as mock_process,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["blast_radius", "--issue-id", "uuid-1", "--old-status", "in_progress"],
            )
            worker_mod.main()

        _, kwargs = mock_process.call_args
        assert kwargs.get("old_status") == "in_progress"

    def test_main_issue_id_force_reprocess(self, monkeypatch):
        import blast_radius.worker as worker_mod

        with (
            patch(
                "blast_radius.worker.process_issue", return_value={"ok": True}
            ) as mock_process,
        ):
            monkeypatch.setattr(
                "sys.argv",
                ["blast_radius", "--issue-id", "uuid-1", "--force-reprocess"],
            )
            worker_mod.main()

        _, kwargs = mock_process.call_args
        assert kwargs.get("force_reprocess") is True

    def test_main_issue_id_none_result_prints_skipped(self, monkeypatch, capsys):
        import blast_radius.worker as worker_mod

        with (
            patch("blast_radius.worker.process_issue", return_value=None),
        ):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--issue-id", "uuid-1"])
            worker_mod.main()

        captured = capsys.readouterr()
        assert "skipped" in captured.out

    def test_main_loop_calls_run_loop(self, monkeypatch):
        import blast_radius.worker as worker_mod

        with (
            patch("blast_radius.worker.run_loop") as mock_loop,
        ):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--loop", "300"])
            worker_mod.main()

        mock_loop.assert_called_once()
        _, kwargs = mock_loop.call_args
        assert kwargs.get("interval_seconds") == 300

    def test_main_run_once_calls_run_once(self, monkeypatch):
        import blast_radius.worker as worker_mod

        with (
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run,
        ):
            monkeypatch.setattr("sys.argv", ["blast_radius"])
            worker_mod.main()

        mock_run.assert_called_once()

    def test_main_run_once_dry_run(self, monkeypatch):
        import blast_radius.worker as worker_mod

        with (
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run,
        ):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--dry-run"])
            worker_mod.main()

        _, kwargs = mock_run.call_args
        assert kwargs.get("dry_run") is True

    def test_main_run_once_force_reprocess(self, monkeypatch):
        import blast_radius.worker as worker_mod

        with (
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run,
        ):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--force-reprocess"])
            worker_mod.main()

        _, kwargs = mock_run.call_args
        assert kwargs.get("force_reprocess") is True
