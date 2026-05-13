"""Unit tests for blast_radius.worker.

All external I/O (Paperclip API, state file) is mocked.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from blast_radius.worker import (
    _is_fix_issue,
    _load_state,
    _save_state,
    _detect_transitions,
    _sync_statuses,
    _fetch_in_review_issues,
    run_once,
    process_issue,
    run_loop,
    main,
    FIX_LABELS,
    _STATE_PATH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_issue(
    issue_id: str = "aaa-111",
    identifier: str = "BTCAAAAA-9999",
    status: str = "in_review",
    title: str = "fix: something broke",
    labels: list[dict] | None = None,
) -> dict:
    return {
        "id": issue_id,
        "identifier": identifier,
        "status": status,
        "title": title,
        "labels": [{"name": "fix"}] if labels is None else labels,
    }


# ---------------------------------------------------------------------------
# TestIsFixIssue
# ---------------------------------------------------------------------------


class TestIsFixIssue:
    def test_matching_label_name(self):
        issue = _make_issue(labels=[{"name": "bug"}])
        assert _is_fix_issue(issue) is True

    def test_matching_label_name_case_insensitive(self):
        issue = _make_issue(labels=[{"name": "Bug"}])
        assert _is_fix_issue(issue) is True

    def test_matching_title_prefix(self):
        issue = _make_issue(labels=[], title="bug: login crash")
        assert _is_fix_issue(issue) is True

    def test_matching_title_prefix_regression(self):
        issue = _make_issue(labels=[], title="regression: price feed drops")
        assert _is_fix_issue(issue) is True

    def test_non_fix_title(self):
        issue = _make_issue(labels=[], title="feature: add dark mode")
        assert _is_fix_issue(issue) is False

    def test_no_labels_key(self):
        issue = _make_issue(labels=None)
        assert _is_fix_issue(issue) is True

    def test_empty_labels(self):
        issue = _make_issue(labels=[], title="refactor: clean up db module")
        assert _is_fix_issue(issue) is False

    def test_title_case_insensitive(self):
        issue = _make_issue(labels=[], title="FIX: critical security patch")
        assert _is_fix_issue(issue) is True

    def test_hotfix_label_name(self):
        issue = _make_issue(labels=[{"name": "hotfix"}])
        assert _is_fix_issue(issue) is True

    def test_title_without_fix_suffix(self):
        issue = _make_issue(labels=[{"name": "enhancement"}], title="Add new strategy")
        assert _is_fix_issue(issue) is False

    def test_label_name_from_FIX_LABELS(self):
        for lbl_name in ["fix", "bug", "bugfix", "regression", "hotfix"]:
            issue = _make_issue(labels=[{"name": lbl_name}])
            assert _is_fix_issue(issue) is True, f"label {lbl_name} should match"


# ---------------------------------------------------------------------------
# TestStatePersistence
# ---------------------------------------------------------------------------


class TestStatePersistence:
    def test_load_returns_defaults_when_no_file(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        with patch("blast_radius.worker._STATE_PATH", Path(state_path)):
            state = _load_state()
        assert state == {"processed_issue_ids": [], "issue_statuses": {}}

    def test_load_parses_existing_file(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        expected = {
            "processed_issue_ids": ["aaa-111"],
            "issue_statuses": {"aaa-111": "in_review"},
        }
        Path(state_path).write_text(json.dumps(expected))
        with patch("blast_radius.worker._STATE_PATH", Path(state_path)):
            state = _load_state()
        assert state == expected

    def test_load_handles_missing_statuses_field(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        data = {"processed_issue_ids": ["aaa-111"]}
        Path(state_path).write_text(json.dumps(data))
        with patch("blast_radius.worker._STATE_PATH", Path(state_path)):
            state = _load_state()
        assert state["issue_statuses"] == {}

    def test_load_handles_missing_processed_ids(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        data = {"issue_statuses": {"aaa-111": "in_review"}}
        Path(state_path).write_text(json.dumps(data))
        with patch("blast_radius.worker._STATE_PATH", Path(state_path)):
            state = _load_state()
        assert state["processed_issue_ids"] == []

    def test_load_returns_defaults_on_corrupted_json(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        Path(state_path).write_text("not valid json")
        with patch("blast_radius.worker._STATE_PATH", Path(state_path)):
            state = _load_state()
        assert state == {"processed_issue_ids": [], "issue_statuses": {}}

    def test_save_writes_state_file(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        state = {
            "processed_issue_ids": ["aaa-111"],
            "issue_statuses": {"aaa-111": "in_review"},
        }
        with patch("blast_radius.worker._STATE_PATH", Path(state_path)):
            _save_state(state)
        loaded = json.loads(Path(state_path).read_text())
        assert loaded == state

    def test_save_creates_parent_dirs(self, tmp_path):
        nested = str(tmp_path / "nested" / "state.json")
        state = {"processed_issue_ids": [], "issue_statuses": {}}
        with patch("blast_radius.worker._STATE_PATH", Path(nested)):
            _save_state(state)
        assert Path(nested).exists()


# ---------------------------------------------------------------------------
# TestDetectTransitions
# ---------------------------------------------------------------------------


class TestDetectTransitions:
    def test_new_issue_is_transition(self):
        state = {"issue_statuses": {}, "processed_issue_ids": []}
        issues = [_make_issue(issue_id="aaa-111")]
        result = _detect_transitions(state, issues)
        assert len(result) == 1

    def test_known_not_in_review_is_transition(self):
        state = {
            "issue_statuses": {"aaa-111": "in_progress"},
            "processed_issue_ids": [],
        }
        issues = [_make_issue(issue_id="aaa-111")]
        result = _detect_transitions(state, issues)
        assert len(result) == 1

    def test_already_in_review_not_detected(self):
        state = {
            "issue_statuses": {"aaa-111": "in_review"},
            "processed_issue_ids": [],
        }
        issues = [_make_issue(issue_id="aaa-111")]
        result = _detect_transitions(state, issues)
        assert len(result) == 0

    def test_excludes_issues_without_id(self):
        state = {"issue_statuses": {}, "processed_issue_ids": []}
        issues = [{"identifier": "BTCAAAAA-NOID"}]
        result = _detect_transitions(state, issues)
        assert len(result) == 0

    def test_excludes_empty_id(self):
        state = {"issue_statuses": {}, "processed_issue_ids": []}
        issues = [_make_issue(issue_id="")]
        result = _detect_transitions(state, issues)
        assert len(result) == 0

    def test_excludes_none_id(self):
        state = {"issue_statuses": {}, "processed_issue_ids": []}
        issues = [_make_issue(issue_id=None)]
        result = _detect_transitions(state, issues)
        assert len(result) == 0

    def test_mixed_detection(self):
        state = {
            "issue_statuses": {
                "aaa-111": "in_review",
                "aaa-222": "in_progress",
            },
            "processed_issue_ids": [],
        }
        issues = [
            _make_issue(issue_id="aaa-111"),
            _make_issue(issue_id="aaa-222"),
        ]
        result = _detect_transitions(state, issues)
        assert len(result) == 1
        assert result[0]["id"] == "aaa-222"

    def test_empty_issues_list(self):
        state = {"issue_statuses": {}, "processed_issue_ids": []}
        result = _detect_transitions(state, [])
        assert result == []


# ---------------------------------------------------------------------------
# TestSyncStatuses
# ---------------------------------------------------------------------------


class TestSyncStatuses:
    def test_updates_statuses(self):
        state = {"issue_statuses": {}, "processed_issue_ids": []}
        issues = [_make_issue(issue_id="aaa-111", status="in_review")]
        _sync_statuses(state, issues)
        assert state["issue_statuses"]["aaa-111"] == "in_review"

    def test_removes_stale_in_review_entries(self):
        state = {
            "issue_statuses": {
                "aaa-111": "in_review",
                "aaa-222": "in_review",
            },
            "processed_issue_ids": [],
        }
        issues = [_make_issue(issue_id="aaa-111", status="in_review")]
        _sync_statuses(state, issues)
        assert "aaa-111" in state["issue_statuses"]
        assert "aaa-222" not in state["issue_statuses"]

    def test_preserves_non_in_review_stale_entries(self):
        state = {
            "issue_statuses": {
                "aaa-111": "in_review",
                "aaa-222": "done",
            },
            "processed_issue_ids": [],
        }
        issues = [_make_issue(issue_id="aaa-111", status="in_review")]
        _sync_statuses(state, issues)
        assert "aaa-222" in state["issue_statuses"]

    def test_handles_empty_fetched_set(self):
        state = {
            "issue_statuses": {"aaa-111": "in_review"},
            "processed_issue_ids": [],
        }
        _sync_statuses(state, [])
        # When fetched set is empty, in_review entries are NOT removed
        # (the stale-cleanup only runs when fetched_ids is non-empty)
        assert "aaa-111" in state["issue_statuses"]

    def test_skips_empty_status_field(self):
        state = {"issue_statuses": {}, "processed_issue_ids": []}
        issues = [_make_issue(issue_id="aaa-111", status="")]
        _sync_statuses(state, issues)
        assert "aaa-111" not in state["issue_statuses"]

    def test_adds_issue_statuses_using_setdefault(self):
        state = {"processed_issue_ids": []}
        issues = [_make_issue(issue_id="aaa-111", status="in_review")]
        _sync_statuses(state, issues)
        assert state["issue_statuses"]["aaa-111"] == "in_review"


# ---------------------------------------------------------------------------
# TestFetchInReviewIssues
# ---------------------------------------------------------------------------


class TestFetchInReviewIssues:
    def test_calls_paginate_with_correct_params(self):
        with patch("blast_radius.worker._paginate", return_value=["a", "b"]) as mock_p:
            result = _fetch_in_review_issues()
        assert result == ["a", "b"]
        args, kwargs = mock_p.call_args
        params = args[1]
        assert params.get("status") == "in_review"

    def test_returns_empty_list(self):
        with patch("blast_radius.worker._paginate", return_value=[]):
            result = _fetch_in_review_issues()
        assert result == []


# ---------------------------------------------------------------------------
# TestRunOnce
# ---------------------------------------------------------------------------


ISSUE_111 = "aaaaaaaa-1111-0000-0000-000000000001"
ISSUE_222 = "aaaaaaaa-2222-0000-0000-000000000002"


class TestRunOnce:
    def test_normal_run_generates_reports(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=[_make_issue(issue_id=ISSUE_111)],
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"issue": "BTCAAAAA-9999", "skipped": False},
            ) as mock_gen,
        ):
            results = run_once(dry_run=False)

        assert len(results) == 1
        mock_gen.assert_called_once()
        state = json.loads(Path(state_path).read_text())
        assert ISSUE_111 in state["processed_issue_ids"]

    def test_dry_run_does_not_save_state(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        Path(state_path).write_text(json.dumps({"processed_issue_ids": [], "issue_statuses": {}}))
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=[_make_issue(issue_id=ISSUE_111)],
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"issue": "BTCAAAAA-9999", "skipped": False},
            ),
        ):
            results = run_once(dry_run=True)

        assert len(results) == 1
        # State file should not have been modified (dry_run skips _save_state)
        loaded = json.loads(Path(state_path).read_text())
        assert loaded["processed_issue_ids"] == []
        assert loaded["issue_statuses"] == {}

    def test_skipped_issue_not_persisted(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=[_make_issue(issue_id=ISSUE_111)],
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"issue": "BTCAAAAA-9999", "skipped": True, "reason": "no touchedFiles"},
            ),
        ):
            results = run_once(dry_run=False)

        assert results[0]["skipped"] is True
        state = json.loads(Path(state_path).read_text())
        assert ISSUE_111 not in state["processed_issue_ids"]
        assert ISSUE_111 not in state.get("issue_statuses", {})

    def test_already_processed_skipped(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        Path(state_path).write_text(
            json.dumps({"processed_issue_ids": [ISSUE_111], "issue_statuses": {}})
        )
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=[_make_issue(issue_id=ISSUE_111)],
            ),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            results = run_once(dry_run=False)

        mock_gen.assert_not_called()

    def test_force_reprocess_overrides(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        Path(state_path).write_text(
            json.dumps({"processed_issue_ids": [ISSUE_111], "issue_statuses": {}})
        )
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=[_make_issue(issue_id=ISSUE_111)],
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"issue": "BTCAAAAA-9999", "skipped": False},
            ) as mock_gen,
        ):
            results = run_once(dry_run=False, force_reprocess=True)

        mock_gen.assert_called_once()
        assert len(results) == 1

    def test_generate_and_post_failure_handled(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=[_make_issue(issue_id=ISSUE_111)],
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                side_effect=RuntimeError("API error"),
            ),
        ):
            results = run_once(dry_run=False)

        assert len(results) == 1
        assert "error" in results[0]
        state = json.loads(Path(state_path).read_text())
        assert ISSUE_111 not in state["processed_issue_ids"]

    def test_no_fix_issues_in_review(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=[_make_issue(labels=[{"name": "enhancement"}], title="feat: new stuff")],
            ),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            results = run_once(dry_run=False)

        assert results == []
        mock_gen.assert_not_called()

    def test_multiple_issues_processed(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=[
                    _make_issue(issue_id=ISSUE_111),
                    _make_issue(issue_id=ISSUE_222, identifier="BTCAAAAA-8888"),
                ],
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"issue": "test", "skipped": False},
            ) as mock_gen,
        ):
            results = run_once(dry_run=False)

        assert len(results) == 2
        assert mock_gen.call_count == 2


# ---------------------------------------------------------------------------
# TestProcessIssue
# ---------------------------------------------------------------------------


class TestProcessIssue:
    def test_issue_not_found(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=None),
        ):
            result = process_issue("nonexistent-uuid")
        assert result is not None
        assert "error" in result
        assert "fetch failed" in result["error"]

    def test_issue_not_in_review_returns_none(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        issue = _make_issue(status="in_progress")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
        ):
            result = process_issue(ISSUE_111)
        assert result is None

    def test_issue_not_fix_returns_none(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        issue = _make_issue(
            labels=[{"name": "enhancement"}],
            title="feat: add feature",
            status="in_review",
        )
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
        ):
            result = process_issue(ISSUE_111)
        assert result is None

    def test_fix_issue_in_review_generates_report(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        issue = _make_issue(issue_id=ISSUE_111, status="in_review")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"issue": "BTCAAAAA-9999", "skipped": False},
            ) as mock_gen,
        ):
            result = process_issue(ISSUE_111, dry_run=False)

        assert result is not None
        mock_gen.assert_called_once()
        state = json.loads(Path(state_path).read_text())
        assert ISSUE_111 in state["processed_issue_ids"]

    def test_already_processed_skipped(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        Path(state_path).write_text(
            json.dumps({"processed_issue_ids": [ISSUE_111], "issue_statuses": {}})
        )
        issue = _make_issue(issue_id=ISSUE_111, status="in_review")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch("blast_radius.worker.generate_and_post") as mock_gen,
        ):
            result = process_issue(ISSUE_111)

        assert result is None
        mock_gen.assert_not_called()

    def test_already_processed_with_force_reprocess(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        Path(state_path).write_text(
            json.dumps({"processed_issue_ids": [ISSUE_111], "issue_statuses": {}})
        )
        issue = _make_issue(issue_id=ISSUE_111, status="in_review")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"issue": "BTCAAAAA-9999", "skipped": False},
            ) as mock_gen,
        ):
            result = process_issue(ISSUE_111, force_reprocess=True)

        assert result is not None
        mock_gen.assert_called_once()

    def test_dry_run_does_not_persist_state(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        Path(state_path).write_text(json.dumps({"processed_issue_ids": [], "issue_statuses": {}}))
        issue = _make_issue(issue_id=ISSUE_111, status="in_review")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"issue": "BTCAAAAA-9999", "skipped": False},
            ),
        ):
            result = process_issue(ISSUE_111, dry_run=True)

        assert result is not None
        # State file should not have been modified (dry_run skips _save_state)
        loaded = json.loads(Path(state_path).read_text())
        assert loaded["processed_issue_ids"] == []
        assert loaded["issue_statuses"] == {}

    def test_tracks_status_leaving_in_review(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        issue = _make_issue(issue_id=ISSUE_111, status="done")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
        ):
            result = process_issue(ISSUE_111, old_status="in_review")

        assert result is None
        state = json.loads(Path(state_path).read_text())
        assert state["issue_statuses"][ISSUE_111] == "done"

    def test_generate_and_post_failure(self, tmp_path):
        state_path = str(tmp_path / "state.json")
        issue = _make_issue(issue_id=ISSUE_111, status="in_review")
        with (
            patch("blast_radius.worker._STATE_PATH", Path(state_path)),
            patch("blast_radius.worker.get_issue_by_id", return_value=issue),
            patch(
                "blast_radius.worker.generate_and_post",
                side_effect=RuntimeError("API error"),
            ),
        ):
            result = process_issue(ISSUE_111)

        assert result is not None
        assert "error" in result


# ---------------------------------------------------------------------------
# TestRunLoop
# ---------------------------------------------------------------------------


class TestRunLoop:
    def test_run_loop_valid_signature(self):
            from blast_radius.worker import run_loop
            import inspect
            sig = inspect.signature(run_loop)
            params = sig.parameters
            assert "interval_seconds" in params
            assert "dry_run" in params
            assert "force_reprocess" in params

# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_is_callable(self):
        from blast_radius.worker import main as worker_main
        assert callable(worker_main)

    def test_main_delegates_to_cli(self):
        with patch("blast_radius.__main__.main", return_value=42) as mock_cli:
            from blast_radius.worker import main as worker_main
            result = worker_main()
            assert result == 42
            mock_cli.assert_called_once()

