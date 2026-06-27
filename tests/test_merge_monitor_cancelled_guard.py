"""Tests for BTCAAAAA-38612 — merge-monitor CANCELLED retrigger guard.

Covers:
  - _has_cancelled_required_check(): detection of cancelled required checks
  - _is_own_push_imminent(): imminent-push guard (automation commit within cooldown)
  - load_retrigger_state() / save_retrigger_state(): cooldown persistence
  - Integration: cooldown blocks re-retrigger; expired cooldown allows it
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import merge_monitor as mm  # noqa: E402


# ---------------------------------------------------------------------------
# _has_cancelled_required_check
# ---------------------------------------------------------------------------

def _check(conclusion: str) -> dict:
    return {"pytest + coverage gate / run": {"status": "COMPLETED", "conclusion": conclusion}}


def test_has_cancelled_returns_true_for_cancelled():
    assert mm._has_cancelled_required_check(_check("cancelled")) is True


def test_has_cancelled_returns_false_for_success():
    assert mm._has_cancelled_required_check(_check("SUCCESS")) is False


def test_has_cancelled_returns_false_for_failure():
    assert mm._has_cancelled_required_check(_check("FAILURE")) is False


def test_has_cancelled_returns_false_when_no_required_check():
    checks = {"some-unrelated-check": {"status": "COMPLETED", "conclusion": "cancelled"}}
    assert mm._has_cancelled_required_check(checks) is False


def test_has_cancelled_returns_false_for_empty():
    assert mm._has_cancelled_required_check({}) is False


def test_has_cancelled_case_insensitive():
    checks = {"Pytest + Coverage Gate": {"status": "COMPLETED", "conclusion": "CANCELLED"}}
    assert mm._has_cancelled_required_check(checks) is True


# ---------------------------------------------------------------------------
# _is_own_push_imminent
# ---------------------------------------------------------------------------

def _make_pr(sha: str = "abc123") -> dict:
    return {"head": {"sha": sha}, "number": 42}


def _make_commit(message: str, author_name: str, minutes_ago: float = 5) -> dict:
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    return {"message": message, "author": {"name": author_name, "date": ts}}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_returning(commit: dict | None) -> MagicMock:
    sess = MagicMock()
    if commit is None:
        sess.get.return_value.status_code = 404
    else:
        sess.get.return_value.status_code = 200
        sess.get.return_value.json.return_value = commit
    return sess


def test_retrigger_msg_recent_triggers_guard():
    commit = _make_commit("ci: retrigger CI after stuck-queue cancel", "SomeBot", minutes_ago=5)
    assert mm._is_own_push_imminent(_make_pr(), _session_returning(commit), _now()) is True


def test_automation_engineer_author_triggers_guard():
    commit = _make_commit("fix: some change", "AutomationEngineer", minutes_ago=10)
    assert mm._is_own_push_imminent(_make_pr(), _session_returning(commit), _now()) is True


def test_github_actions_author_triggers_guard():
    commit = _make_commit("ci: trigger fresh CI run", "github-actions[bot]", minutes_ago=1)
    assert mm._is_own_push_imminent(_make_pr(), _session_returning(commit), _now()) is True


def test_retrigger_msg_outside_cooldown_does_not_trigger():
    commit = _make_commit("ci: retrigger", "AutomationEngineer", minutes_ago=35)
    result = mm._is_own_push_imminent(_make_pr(), _session_returning(commit), _now(), max_age_minutes=30)
    assert result is False


def test_regular_human_commit_does_not_trigger():
    commit = _make_commit("feat: add new strategy", "Alice Dev", minutes_ago=5)
    assert mm._is_own_push_imminent(_make_pr(), _session_returning(commit), _now()) is False


def test_missing_sha_returns_false():
    pr = {"head": {}, "number": 42}
    assert mm._is_own_push_imminent(pr, MagicMock(), _now()) is False


def test_fetch_commit_failure_returns_false():
    assert mm._is_own_push_imminent(_make_pr(), _session_returning(None), _now()) is False


def test_corrupt_date_returns_false():
    commit = {"message": "ci: retrigger", "author": {"name": "AutomationEngineer", "date": "not-a-date"}}
    assert mm._is_own_push_imminent(_make_pr(), _session_returning(commit), _now()) is False


def test_just_past_max_age_is_not_imminent():
    commit = _make_commit("ci: retrigger", "AutomationEngineer", minutes_ago=31)
    result = mm._is_own_push_imminent(_make_pr(), _session_returning(commit), _now(), max_age_minutes=30)
    assert result is False


# ---------------------------------------------------------------------------
# load_retrigger_state / save_retrigger_state
# ---------------------------------------------------------------------------

def test_load_returns_empty_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(mm, "_RETRIGGER_STATE_FILE", tmp_path / "absent.json")
    assert mm.load_retrigger_state() == {}


def test_load_returns_empty_on_corrupt_json(tmp_path, monkeypatch):
    f = tmp_path / "state.json"
    f.write_text("{ not valid json")
    monkeypatch.setattr(mm, "_RETRIGGER_STATE_FILE", f)
    assert mm.load_retrigger_state() == {}


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    f = tmp_path / "state.json"
    monkeypatch.setattr(mm, "_RETRIGGER_STATE_FILE", f)
    state = {"123": "2026-06-27T10:00:00+00:00", "456": "2026-06-27T09:00:00+00:00"}
    mm.save_retrigger_state(state)
    assert mm.load_retrigger_state() == state


def test_save_tolerates_oserror(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(mm, "_RETRIGGER_STATE_FILE", tmp_path / "no-dir" / "state.json")
    import logging
    with caplog.at_level(logging.WARNING, logger="merge-monitor"):
        mm.save_retrigger_state({"1": "ts"})
    assert "Failed to save retrigger state" in caplog.text


# ---------------------------------------------------------------------------
# Cooldown integration
# ---------------------------------------------------------------------------

def test_cooldown_active_within_window(tmp_path, monkeypatch):
    f = tmp_path / "state.json"
    monkeypatch.setattr(mm, "_RETRIGGER_STATE_FILE", f)
    now = datetime.now(timezone.utc)
    mm.save_retrigger_state({"256": (now - timedelta(minutes=5)).isoformat()})
    loaded = mm.load_retrigger_state()
    last_ts = datetime.fromisoformat(loaded["256"]).replace(tzinfo=timezone.utc)
    age_min = (now - last_ts).total_seconds() / 60
    assert age_min < mm.RETRIGGER_COOLDOWN_MINUTES


def test_cooldown_expired_after_window(tmp_path, monkeypatch):
    f = tmp_path / "state.json"
    monkeypatch.setattr(mm, "_RETRIGGER_STATE_FILE", f)
    now = datetime.now(timezone.utc)
    mm.save_retrigger_state({"256": (now - timedelta(minutes=35)).isoformat()})
    loaded = mm.load_retrigger_state()
    last_ts = datetime.fromisoformat(loaded["256"]).replace(tzinfo=timezone.utc)
    age_min = (now - last_ts).total_seconds() / 60
    assert age_min >= mm.RETRIGGER_COOLDOWN_MINUTES
