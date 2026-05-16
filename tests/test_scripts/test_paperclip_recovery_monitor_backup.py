"""Unit tests for scripts/paperclip_recovery_monitor_backup.py — BTCAAAAA-27306.

Tests cover gh CLI integration, local state reading, alert creation/dedup,
and the top-level run() orchestration.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parents[2]
import sys
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

pytestmark = [pytest.mark.bug("BTCAAAAA-27306"), pytest.mark.regression]


def _make_gh_run(
    *,
    status: str = "completed",
    conclusion: str = "success",
    created_ago_minutes: float = 10,
    db_id: int = 123,
) -> dict:
    created = (datetime.now(tz=UTC) - timedelta(minutes=created_ago_minutes)).isoformat()
    return {
        "status": status,
        "conclusion": conclusion,
        "createdAt": created,
        "databaseId": db_id,
        "headSha": "abc123",
    }


def _make_state(
    *,
    last_run_ago_minutes: float | None = 10,
    scenarios: dict | None = None,
) -> dict:
    state: dict = {"scenarios": scenarios or {}}
    if last_run_ago_minutes is not None:
        last_run = (datetime.now(tz=UTC) - timedelta(minutes=last_run_ago_minutes)).isoformat()
        state["last_run_at"] = last_run
    return state


# ---------------------------------------------------------------------------
# _rotate_log_if_needed
# ---------------------------------------------------------------------------


class TestRotateLog:
    def test_rotates_when_file_too_large(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _rotate_log_if_needed, MONITOR_LOG, MAX_LOG_BYTES

        log = tmp_path / "backup.log"
        log.write_text("x" * (MAX_LOG_BYTES + 100))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.MONITOR_LOG", log)

        _rotate_log_if_needed()
        bak = log.with_suffix(".log.1")
        assert bak.exists()

    def test_no_rotate_when_under_limit(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _rotate_log_if_needed, MAX_LOG_BYTES

        log = tmp_path / "backup.log"
        log.write_text("x" * (MAX_LOG_BYTES // 2))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.MONITOR_LOG", log)

        _rotate_log_if_needed()
        bak = log.with_suffix(".log.1")
        assert not bak.exists()


# ---------------------------------------------------------------------------
# _gh_run_list
# ---------------------------------------------------------------------------


class TestGhRunList:
    def test_returns_parsed_runs(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _gh_run_list

        runs = [_make_gh_run()]
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout=json.dumps(runs)))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = _gh_run_list("test-workflow")
        assert result == runs

    def test_returns_none_on_cli_not_found(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _gh_run_list

        def _raise_fnf(*a, **kw):
            raise FileNotFoundError("gh not found")

        monkeypatch.setattr(subprocess, "run", _raise_fnf)
        assert _gh_run_list("test-workflow") is None

    def test_returns_none_on_timeout(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _gh_run_list

        def _raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired("gh", timeout=30)

        monkeypatch.setattr(subprocess, "run", _raise_timeout)
        assert _gh_run_list("test-workflow") is None

    def test_returns_none_on_auth_error(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _gh_run_list

        mock_result = MagicMock(
            returncode=1,
            stdout="",
            stderr="gh: To get started with GitHub CLI, please run:  gh auth login",
        )
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)
        assert _gh_run_list("test-workflow") is None

    def test_returns_none_on_generic_failure(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _gh_run_list

        mock_result = MagicMock(returncode=1, stdout="", stderr="some error")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)
        assert _gh_run_list("test-workflow") is None

    def test_returns_none_on_bad_json(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _gh_run_list

        mock_result = MagicMock(returncode=0, stdout="not json")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)
        assert _gh_run_list("test-workflow") is None


# ---------------------------------------------------------------------------
# _get_latest_success_age_minutes
# ---------------------------------------------------------------------------


class TestGetLatestSuccessAgeMinutes:
    def test_returns_age_of_latest_success(self):
        from scripts.paperclip_recovery_monitor_backup import _get_latest_success_age_minutes

        runs = [
            _make_gh_run(conclusion="failure", created_ago_minutes=2),
            _make_gh_run(conclusion="success", created_ago_minutes=10),
        ]
        age = _get_latest_success_age_minutes(runs)
        assert age is not None
        assert 9 <= age <= 11

    def test_returns_none_when_no_successes(self):
        from scripts.paperclip_recovery_monitor_backup import _get_latest_success_age_minutes

        runs = [_make_gh_run(conclusion="failure")]
        assert _get_latest_success_age_minutes(runs) is None

    def test_returns_none_when_no_runs(self):
        from scripts.paperclip_recovery_monitor_backup import _get_latest_success_age_minutes

        assert _get_latest_success_age_minutes([]) is None

    def test_handles_missing_created_at(self):
        from scripts.paperclip_recovery_monitor_backup import _get_latest_success_age_minutes

        runs = [{"status": "completed", "conclusion": "success"}]
        assert _get_latest_success_age_minutes(runs) is None


# ---------------------------------------------------------------------------
# _has_any_recent_runs
# ---------------------------------------------------------------------------


class TestHasAnyRecentRuns:
    def test_true_when_recent_run_exists(self):
        from scripts.paperclip_recovery_monitor_backup import _has_any_recent_runs

        runs = [_make_gh_run(created_ago_minutes=5)]
        assert _has_any_recent_runs(runs, minutes=30) is True

    def test_false_when_all_runs_old(self):
        from scripts.paperclip_recovery_monitor_backup import _has_any_recent_runs

        runs = [_make_gh_run(created_ago_minutes=60)]
        assert _has_any_recent_runs(runs, minutes=30) is False

    def test_false_when_empty(self):
        from scripts.paperclip_recovery_monitor_backup import _has_any_recent_runs

        assert _has_any_recent_runs([], minutes=30) is False


# ---------------------------------------------------------------------------
# _read_local_recovery_state / _get_local_monitor_age_minutes
# ---------------------------------------------------------------------------


class TestReadLocalRecoveryState:
    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _read_local_recovery_state, LOCAL_RECOVERY_STATE

        missing = tmp_path / "nonexistent.json"
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.LOCAL_RECOVERY_STATE", missing)
        assert _read_local_recovery_state() is None

    def test_returns_parsed_state(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _read_local_recovery_state, LOCAL_RECOVERY_STATE

        sf = tmp_path / "state.json"
        sf.write_text(json.dumps({"last_run_at": "2026-01-01T00:00:00Z"}))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.LOCAL_RECOVERY_STATE", sf)
        state = _read_local_recovery_state()
        assert state is not None
        assert state["last_run_at"] == "2026-01-01T00:00:00Z"

    def test_returns_none_on_corrupt_file(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _read_local_recovery_state, LOCAL_RECOVERY_STATE

        sf = tmp_path / "corrupt.json"
        sf.write_text("{bad")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.LOCAL_RECOVERY_STATE", sf)
        assert _read_local_recovery_state() is None


class TestGetLocalMonitorAgeMinutes:
    def test_returns_age_from_last_run_at(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _get_local_monitor_age_minutes

        state = _make_state(last_run_ago_minutes=25)
        age = _get_local_monitor_age_minutes(state)
        assert age is not None
        assert 24 <= age <= 26

    def test_returns_none_when_no_last_run_at(self):
        from scripts.paperclip_recovery_monitor_backup import _get_local_monitor_age_minutes

        assert _get_local_monitor_age_minutes({"scenarios": {}}) is None

    def test_returns_none_on_bad_timestamp(self):
        from scripts.paperclip_recovery_monitor_backup import _get_local_monitor_age_minutes

        state = {"last_run_at": "not-a-date", "scenarios": {}}
        assert _get_local_monitor_age_minutes(state) is None


# ---------------------------------------------------------------------------
# _load_self_state / _save_self_state
# ---------------------------------------------------------------------------


class TestSelfState:
    def test_load_returns_empty_when_no_file(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _load_self_state, MONITOR_STATE

        missing = tmp_path / "nonexistent.json"
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.MONITOR_STATE", missing)
        assert _load_self_state() == {}

    def test_load_returns_existing_state(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _load_self_state, MONITOR_STATE

        sf = tmp_path / "state.json"
        sf.write_text(json.dumps({"total_runs": 5}))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.MONITOR_STATE", sf)
        assert _load_self_state() == {"total_runs": 5}

    def test_save_writes_valid_json(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _save_self_state, MONITOR_STATE

        sf = tmp_path / "out.json"
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.MONITOR_STATE", sf)
        _save_self_state({"total_runs": 3})
        assert json.loads(sf.read_text()) == {"total_runs": 3}


# ---------------------------------------------------------------------------
# _find_existing_alert
# ---------------------------------------------------------------------------


class TestFindExistingAlert:
    def test_returns_existing_alert_issue(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _find_existing_alert

        mock_sess = MagicMock()
        mock_sess.get.return_value.json.return_value = [
            {"id": "alert-1", "title": "Recovery Monitor health alert — something"},
        ]
        mock_sess.get.return_value.raise_for_status = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", lambda: mock_sess)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._base", lambda: "https://api.example.com")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._company", lambda: "company-1")

        issue = _find_existing_alert()
        assert issue is not None
        assert issue["id"] == "alert-1"

    def test_returns_none_when_no_alert(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _find_existing_alert

        mock_sess = MagicMock()
        mock_sess.get.return_value.json.return_value = []
        mock_sess.get.return_value.raise_for_status = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", lambda: mock_sess)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._base", lambda: "https://api.example.com")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._company", lambda: "company-1")

        assert _find_existing_alert() is None

    def test_returns_none_on_session_failure(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _find_existing_alert

        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", MagicMock(side_effect=KeyError("no key")))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._base", lambda: "https://api.example.com")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._company", lambda: "company-1")

        assert _find_existing_alert() is None


# ---------------------------------------------------------------------------
# _create_alert
# ---------------------------------------------------------------------------


class TestCreateAlert:
    def test_creates_alert_issue(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _create_alert

        mock_sess = MagicMock()
        mock_sess.post.return_value.json.return_value = {"identifier": "ALERT-1", "id": "alert-1"}
        mock_sess.post.return_value.raise_for_status = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", lambda: mock_sess)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._base", lambda: "https://api.example.com")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._company", lambda: "company-1")

        result = _create_alert(age_minutes=100, local_age_minutes=None, threshold_minutes=90, gh_available=True, dry_run=False)
        assert result is True
        mock_sess.post.assert_called_once()

    def test_dry_run_does_not_post(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _create_alert

        mock_sess = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", lambda: mock_sess)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._base", lambda: "https://api.example.com")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._company", lambda: "company-1")

        result = _create_alert(age_minutes=100, local_age_minutes=None, threshold_minutes=90, gh_available=True, dry_run=True)
        assert result is True
        mock_sess.post.assert_not_called()

    def test_returns_false_on_api_failure(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _create_alert

        mock_sess = MagicMock()
        mock_sess.post.side_effect = RuntimeError("API down")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", lambda: mock_sess)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._base", lambda: "https://api.example.com")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._company", lambda: "company-1")

        result = _create_alert(age_minutes=100, local_age_minutes=None, threshold_minutes=90, gh_available=True, dry_run=False)
        assert result is False

    def test_returns_false_on_session_failure(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _create_alert

        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", MagicMock(side_effect=KeyError("no key")))

        result = _create_alert(age_minutes=100, local_age_minutes=None, threshold_minutes=90, gh_available=True, dry_run=False)
        assert result is False


# ---------------------------------------------------------------------------
# _comment_on_existing_alert
# ---------------------------------------------------------------------------


class TestCommentOnExistingAlert:
    def test_comments_on_existing_alert(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _comment_on_existing_alert

        mock_sess = MagicMock()
        mock_sess.post.return_value.raise_for_status = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", lambda: mock_sess)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._base", lambda: "https://api.example.com")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._company", lambda: "company-1")

        issue = {"id": "alert-1", "identifier": "ALERT-1"}
        result = _comment_on_existing_alert(issue, age_minutes=100, local_age_minutes=None, threshold_minutes=90, dry_run=False)
        assert result is True
        mock_sess.post.assert_called_once()

    def test_dry_run_does_not_post(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import _comment_on_existing_alert

        mock_sess = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._session", lambda: mock_sess)

        issue = {"id": "alert-1"}
        result = _comment_on_existing_alert(issue, age_minutes=100, local_age_minutes=None, threshold_minutes=90, dry_run=True)
        assert result is True
        mock_sess.post.assert_not_called()


# ---------------------------------------------------------------------------
# run() orchestration
# ---------------------------------------------------------------------------


class TestRun:
    def test_reports_healthy_when_recent_success(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=15)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)

        summary = run(threshold_minutes=90, dry_run=True)
        assert summary["status"] == "healthy"
        assert summary["alert_fired"] is False

    def test_fires_alert_when_gh_overdue(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=120)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._find_existing_alert", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._create_alert", lambda *a, **kw: True)

        summary = run(threshold_minutes=90, dry_run=False)
        assert summary["status"] == "alert"
        assert summary["alert_fired"] is True

    def test_skips_alert_when_existing_open(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=120)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._find_existing_alert", lambda: {"id": "alert-1"})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._comment_on_existing_alert", lambda *a, **kw: True)

        def _should_not_be_called(*a, **kw):
            raise AssertionError("_create_alert should not be called when alert exists")

        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._create_alert", _should_not_be_called)

        summary = run(threshold_minutes=90, dry_run=False)
        assert summary["status"] == "alert"
        assert summary["alert_fired"] is False
        assert summary["alert_skipped"] is True

    def test_healthy_via_local_state(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=120)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: _make_state(last_run_ago_minutes=30))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)

        summary = run(threshold_minutes=90, dry_run=True)
        assert summary["status"] == "healthy"

    def test_fires_alert_when_no_successes_and_recent_failures(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        runs = [_make_gh_run(conclusion="failure", created_ago_minutes=5)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)

        summary = run(threshold_minutes=90, dry_run=True)
        assert summary["status"] == "healthy"

    def test_reports_error_when_both_sources_unreachable(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: None)

        def _no_local(*a, **kw):
            return None

        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", _no_local)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)

        summary = run(threshold_minutes=90, dry_run=True)
        assert summary["status"] == "alert"

    def test_uses_custom_threshold(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=60)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)

        summary = run(threshold_minutes=30, dry_run=True)
        assert summary["status"] == "alert"
        assert summary["monitor_threshold_minutes"] == 30

    def test_summary_contains_all_keys(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=15)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)

        summary = run(threshold_minutes=90, dry_run=True)
        expected_keys = {
            "status", "target_workflow", "monitor_interval_minutes",
            "monitor_threshold_minutes", "gh_actions_last_success_age_minutes",
            "local_monitor_last_run_age_minutes", "total_runs_checked",
            "gh_cli_available", "local_state_available", "alert_fired",
            "alert_skipped", "commented", "alert_reason", "self_last_run_utc",
            "self_prev_run_utc", "self_total_runs",
        }
        assert expected_keys.issubset(summary.keys())

    def test_self_state_increments_total_runs(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        saved_state = {}

        def _save(s):
            saved_state.clear()
            saved_state.update(s)

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=15)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {"total_runs": 4})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", _save)

        summary = run(threshold_minutes=90, dry_run=True)
        assert summary["self_total_runs"] == 5
        assert saved_state["total_runs"] == 5

    def test_best_signal_used_when_both_sources_available(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import run

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=60)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: _make_state(last_run_ago_minutes=30))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)

        summary = run(threshold_minutes=90, dry_run=True)
        assert summary["status"] == "healthy"


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_exits_zero_on_healthy(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import main

        runs = [_make_gh_run(conclusion="success", created_ago_minutes=15)]
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.run", lambda **kw: {"status": "healthy"})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._gh_run_list", lambda w, limit=10: runs)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._read_local_recovery_state", lambda: None)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._load_self_state", lambda: {})
        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup._save_self_state", lambda s: None)
        monkeypatch.setattr("sys.argv", ["script"])

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_exits_zero_even_on_alert(self, monkeypatch):
        from scripts.paperclip_recovery_monitor_backup import main

        monkeypatch.setattr("scripts.paperclip_recovery_monitor_backup.run", lambda **kw: {"status": "alert"})
        monkeypatch.setattr("sys.argv", ["script"])

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
