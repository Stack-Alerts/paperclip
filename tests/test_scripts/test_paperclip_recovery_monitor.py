"""Unit tests for scripts/paperclip_recovery_monitor.py — BTCAAAAA-26556.

Tests cover config loading, recovery state persistence, issue-age calculation,
scenario matching, cooldown enforcement, recovery-action execution, and the
top-level run_monitor orchestration.

JSON config fixture data is embedded rather than loading the live file to
keep tests deterministic and free of external I/O.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

pytestmark = [pytest.mark.bug("BTCAAAAA-26556"), pytest.mark.regression]

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

SAMPLE_CONFIG = {
    "company_id": "73419cf3-bd37-4a7c-8782-311ccb47fced",
    "defaults": {
        "recovery_cooldown_minutes": 120,
        "max_recovery_attempts": 3,
        "escalation_agent_id": "41b5ede6-e209-40ba-b923-dc969c722e6d",
        "alert_project_id": "0163ad7d-d05e-4742-9fbb-f206a17fc649",
    },
    "agent_scope_map": {
        "exchange_agents": ["agent-ex-001"],
        "risk_agents": ["agent-risk-001"],
        "signal_agents": ["agent-sig-001"],
    },
    "recovery_scenarios": [
        {
            "id": "exchange_api_timeout",
            "name": "Exchange API Timeout Recovery",
            "enabled": True,
            "source_scope": {
                "agent_scopes": ["exchange_agents"],
                "issue_keywords": ["exchange", "api", "timeout"],
            },
            "detection": {
                "status": "in_progress",
                "min_age_hours": 2,
                "max_age_hours": 72,
                "check_live_runs": False,
                "run_silence_levels": [],
                "min_issues_for_batch_alert": 1,
            },
            "recovery_actions": [
                {"order": 1, "action": "add_comment", "description": "Post diagnostic comment"},
                {"order": 2, "action": "invoke_heartbeat", "description": "Trigger heartbeat"},
            ],
        },
        {
            "id": "orphan_checkout",
            "name": "Orphaned Checkout Recovery",
            "enabled": True,
            "source_scope": {
                "agent_scopes": [],
                "issue_keywords": [],
            },
            "detection": {
                "status": "in_progress",
                "min_age_hours": 6,
                "max_age_hours": 168,
                "check_live_runs": True,
                "run_silence_levels": ["critical"],
                "min_issues_for_batch_alert": 1,
            },
            "recovery_actions": [
                {"order": 1, "action": "force_release", "description": "Force release"},
            ],
        },
        {
            "id": "batch_threshold_scenario",
            "name": "Batch Threshold Scenario",
            "enabled": True,
            "source_scope": {
                "agent_scopes": [],
                "issue_keywords": ["batch"],
            },
            "detection": {
                "status": "in_progress",
                "min_age_hours": 1,
                "max_age_hours": 48,
                "check_live_runs": False,
                "run_silence_levels": [],
                "min_issues_for_batch_alert": 3,
            },
            "recovery_actions": [],
        },
    ],
}


def _make_issue(
    *,
    identifier: str = "BTCAAAAA-99999",
    agent_id: str = "agent-ex-001",
    age_hours: float = 5.0,
    status: str = "in_progress",
    title: str = "Test exchange API timeout issue",
    description: str = "",
    issue_id: str = "00000000-0000-4000-a000-000000000001",
) -> dict:
    started = (datetime.now(tz=UTC) - timedelta(hours=age_hours)).isoformat()
    return {
        "id": issue_id,
        "identifier": identifier,
        "title": title,
        "description": description,
        "status": status,
        "assigneeAgentId": agent_id,
        "startedAt": started,
        "createdAt": started,
    }


def _empty_state() -> dict:
    return {"scenarios": {}, "last_run_at": None}


# ---------------------------------------------------------------------------
# parse_iso / issue_age_hours
# ---------------------------------------------------------------------------


class TestParseIso:
    def test_parses_utc_z(self):
        from scripts.paperclip_recovery_monitor import parse_iso

        dt = parse_iso("2026-05-14T12:00:00Z")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_returns_none_for_none(self):
        from scripts.paperclip_recovery_monitor import parse_iso

        assert parse_iso(None) is None

    def test_returns_none_for_empty(self):
        from scripts.paperclip_recovery_monitor import parse_iso

        assert parse_iso("") is None

    def test_returns_none_for_garbage(self):
        from scripts.paperclip_recovery_monitor import parse_iso

        assert parse_iso("not-a-date") is None


class TestIssueAgeHours:
    def test_returns_expected_age(self):
        from scripts.paperclip_recovery_monitor import issue_age_hours

        issue = _make_issue(age_hours=3.0)
        age = issue_age_hours(issue)
        assert 2.9 <= age <= 3.1

    def test_falls_back_to_created_at(self):
        from scripts.paperclip_recovery_monitor import issue_age_hours

        now = datetime.now(tz=UTC)
        created = (now - timedelta(hours=1.5)).isoformat()
        issue = {
            "id": "x",
            "identifier": "ISS-1",
            "status": "in_progress",
            "createdAt": created,
        }
        age = issue_age_hours(issue)
        assert 1.4 <= age <= 1.6

    def test_returns_zero_when_no_timestamps(self):
        from scripts.paperclip_recovery_monitor import issue_age_hours

        assert issue_age_hours({"id": "x", "status": "open"}) == 0.0


# ---------------------------------------------------------------------------
# Load / save recovery state
# ---------------------------------------------------------------------------


class TestRecoveryState:
    def test_load_defaults_when_no_file(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor import load_recovery_state

        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.RECOVERY_STATE_FILE",
            tmp_path / "nonexistent.json",
        )
        state = load_recovery_state()
        assert state["scenarios"] == {}
        assert state["last_run_at"] is None

    def test_loads_existing_state(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor import load_recovery_state

        sf = tmp_path / "state.json"
        sf.write_text(json.dumps({"scenarios": {"s1": {"i1": {}}}, "last_run_at": "2026-01-01T00:00:00Z"}))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.RECOVERY_STATE_FILE", sf)

        state = load_recovery_state()
        assert "s1" in state["scenarios"]

    def test_resets_on_corrupt_state(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor import load_recovery_state

        sf = tmp_path / "corrupt.json"
        sf.write_text("{not json")
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.RECOVERY_STATE_FILE", sf)

        state = load_recovery_state()
        assert state["scenarios"] == {}

    def test_save_state_writes_valid_json(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor import save_recovery_state

        sf = tmp_path / "out.json"
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.RECOVERY_STATE_FILE", sf)

        save_recovery_state({"scenarios": {"s1": {"i1": {"recovery_attempts": 2}}}})
        loaded = json.loads(sf.read_text())
        assert loaded["scenarios"]["s1"]["i1"]["recovery_attempts"] == 2


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_loads_valid_config(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor import load_config

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.CONFIG_PATH", cfg)

        config = load_config()
        assert config["company_id"] == SAMPLE_CONFIG["company_id"]
        assert "recovery_scenarios" in config

    def test_raises_when_config_missing(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor import load_config

        cfg = tmp_path / "missing.json"
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.CONFIG_PATH", cfg)

        with pytest.raises(FileNotFoundError):
            load_config()


# ---------------------------------------------------------------------------
# Issue keyword matching
# ---------------------------------------------------------------------------


class TestIssueMatchesKeywords:
    def test_matches_keyword_in_title(self):
        from scripts.paperclip_recovery_monitor import issue_matches_keywords

        issue = {"title": "Exchange API timeout", "description": ""}
        assert issue_matches_keywords(issue, ["exchange"]) is True

    def test_matches_keyword_in_description(self):
        from scripts.paperclip_recovery_monitor import issue_matches_keywords

        issue = {"title": "Something", "description": "The binance API experienced a timeout"}
        assert issue_matches_keywords(issue, ["timeout"]) is True

    def test_no_match_with_different_keywords(self):
        from scripts.paperclip_recovery_monitor import issue_matches_keywords

        issue = {"title": "Check health", "description": "Everything OK"}
        assert issue_matches_keywords(issue, ["exchange", "timeout"]) is False

    def test_matches_case_insensitive(self):
        from scripts.paperclip_recovery_monitor import issue_matches_keywords

        issue = {"title": "EXCHANGE API TIMEOUT", "description": ""}
        assert issue_matches_keywords(issue, ["exchange"]) is True

    def test_empty_keywords_always_match(self):
        from scripts.paperclip_recovery_monitor import issue_matches_keywords

        issue = {"title": "Anything", "description": ""}
        assert issue_matches_keywords(issue, []) is True


# ---------------------------------------------------------------------------
# Scenario matching
# ---------------------------------------------------------------------------


class TestIssueMatchesScenario:
    def test_matches_enabled_scenario(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001", title="Exchange API timeout")
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, []) is True

    def test_disabled_scenario_does_not_match(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = dict(SAMPLE_CONFIG["recovery_scenarios"][0], enabled=False)
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001", title="Exchange API timeout")
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, []) is False

    def test_too_young_issue_does_not_match(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=0.5, agent_id="agent-ex-001")
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, []) is False

    def test_too_old_issue_does_not_match(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=80, agent_id="agent-ex-001")
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, []) is False

    def test_wrong_agent_scope_does_not_match(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="other-agent")
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, []) is False

    def test_orphan_scenario_matches_any_agent(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][1]
        issue = _make_issue(age_hours=10.0, agent_id="any-agent")
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, []) is True

    def test_keyword_mismatch_does_not_match(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001", title="General health check")
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, []) is False

    def test_wrong_status_does_not_match(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001", status="todo")
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, []) is False

    def test_live_runs_silence_level_must_match(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][1]
        issue = _make_issue(age_hours=10.0, agent_id="any-agent", issue_id="i-run")

        live_runs = [{
            "issueId": "i-run",
            "outputSilence": {"level": "critical"},
        }]
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, live_runs) is True

    def test_live_runs_silence_level_mismatch(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][1]
        issue = _make_issue(age_hours=10.0, agent_id="any-agent", issue_id="i-run")

        live_runs = [{
            "issueId": "i-run",
            "outputSilence": {"level": "normal"},
        }]
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, live_runs) is False

    def test_live_runs_no_matching_runs(self):
        from scripts.paperclip_recovery_monitor import issue_matches_scenario

        scenario = SAMPLE_CONFIG["recovery_scenarios"][1]
        issue = _make_issue(age_hours=10.0, agent_id="any-agent", issue_id="i-run")

        live_runs = [{"issueId": "other-issue", "outputSilence": {"level": "critical"}}]
        assert issue_matches_scenario(issue, scenario, SAMPLE_CONFIG, live_runs) is True


# ---------------------------------------------------------------------------
# Cooldown enforcement
# ---------------------------------------------------------------------------


class TestIsInCooldown:
    def test_not_in_cooldown_with_empty_state(self):
        from scripts.paperclip_recovery_monitor import is_in_cooldown

        assert is_in_cooldown(_empty_state(), "i1", "s1", cooldown_minutes=120) is False

    def test_in_cooldown_with_recent_attempt(self):
        from scripts.paperclip_recovery_monitor import is_in_cooldown

        now = datetime.now(tz=UTC)
        state = {
            "scenarios": {
                "s1": {
                    "i1": {
                        "last_recovery_attempt_at": now.isoformat(),
                    },
                },
            },
            "last_run_at": None,
        }
        assert is_in_cooldown(state, "i1", "s1", cooldown_minutes=120) is True

    def test_not_in_cooldown_after_expiry(self):
        from scripts.paperclip_recovery_monitor import is_in_cooldown

        past = (datetime.now(tz=UTC) - timedelta(minutes=130)).isoformat()
        state = {
            "scenarios": {
                "s1": {
                    "i1": {
                        "last_recovery_attempt_at": past,
                    },
                },
            },
            "last_run_at": None,
        }
        assert is_in_cooldown(state, "i1", "s1", cooldown_minutes=120) is False


# ---------------------------------------------------------------------------
# Update recovery state
# ---------------------------------------------------------------------------


class TestUpdateRecoveryState:
    def test_adds_entry_to_empty_state(self):
        from scripts.paperclip_recovery_monitor import update_recovery_state

        state = _empty_state()
        update_recovery_state(state, "i1", "s1", "add_comment", escalation_issue_id="esc-1")

        entry = state["scenarios"]["s1"]["i1"]
        assert entry["recovery_attempts"] == 1
        assert entry["last_action"] == "add_comment"
        assert entry["escalation_issue_id"] == "esc-1"
        assert "last_recovery_attempt_at" in entry
        assert state["last_run_at"] is not None

    def test_increments_existing_entry(self):
        from scripts.paperclip_recovery_monitor import update_recovery_state

        state = {
            "scenarios": {
                "s1": {
                    "i1": {
                        "recovery_attempts": 1,
                        "first_detected_at": "2026-01-01T00:00:00Z",
                        "last_recovery_attempt_at": "2026-01-01T00:00:00Z",
                        "last_action": "add_comment",
                    },
                },
            },
            "last_run_at": None,
        }
        update_recovery_state(state, "i1", "s1", "invoke_heartbeat")
        assert state["scenarios"]["s1"]["i1"]["recovery_attempts"] == 2


# ---------------------------------------------------------------------------
# Execute recovery actions
# ---------------------------------------------------------------------------


class TestExecuteRecovery:
    def test_add_comment_action(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import execute_recovery

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001")

        mock_post = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.post_comment", mock_post)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.invoke_heartbeat", MagicMock())

        results = execute_recovery(scenario, issue, SAMPLE_CONFIG, _empty_state(), dry_run=False)
        assert len(results) >= 1
        assert any(r["action"] == "add_comment" for r in results)

    def test_invoke_heartbeat_action(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import execute_recovery

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001")

        mock_hb = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.post_comment", MagicMock())
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.invoke_heartbeat", mock_hb)

        execute_recovery(scenario, issue, SAMPLE_CONFIG, _empty_state(), dry_run=False)
        mock_hb.assert_called()

    def test_dry_run_does_not_call_actions(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import execute_recovery

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001")

        mock_post = MagicMock()
        mock_hb = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.post_comment", mock_post)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.invoke_heartbeat", mock_hb)

        results = execute_recovery(scenario, issue, SAMPLE_CONFIG, _empty_state(), dry_run=True)
        assert all(r["dry_run"] for r in results)
        mock_post.assert_called_once()
        assert mock_post.call_args[0][2] is True

    def test_skips_when_in_cooldown(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import execute_recovery

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001")

        now = datetime.now(tz=UTC)
        state = {
            "scenarios": {
                "exchange_api_timeout": {
                    issue["id"]: {
                        "last_recovery_attempt_at": now.isoformat(),
                    },
                },
            },
            "last_run_at": None,
        }

        mock_post = MagicMock()
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.post_comment", mock_post)

        results = execute_recovery(scenario, issue, SAMPLE_CONFIG, state)
        assert results == []
        mock_post.assert_not_called()

    def test_handles_action_exceptions_gracefully(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import execute_recovery

        scenario = SAMPLE_CONFIG["recovery_scenarios"][0]
        issue = _make_issue(age_hours=5.0, agent_id="agent-ex-001")

        def _failing_comment(*a, **kw):
            raise RuntimeError("API down")

        monkeypatch.setattr("scripts.paperclip_recovery_monitor.post_comment", _failing_comment)
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.invoke_heartbeat", MagicMock())

        results = execute_recovery(scenario, issue, SAMPLE_CONFIG, _empty_state())
        errors = [r for r in results if r.get("error")]
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# run_monitor
# ---------------------------------------------------------------------------


class TestRunMonitor:
    def test_returns_summary_structure(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import run_monitor

        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_in_progress_issues",
            lambda: [],
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_live_runs",
            lambda: [],
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.load_config",
            lambda: SAMPLE_CONFIG,
        )

        summary = run_monitor(SAMPLE_CONFIG, _empty_state(), dry_run=True)
        assert "timestamp" in summary
        assert "issues_scanned" in summary
        assert "scenarios_checked" in summary
        assert "matches" in summary
        assert "actions_taken" in summary

    def test_counts_matched_issues(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import run_monitor

        issues = [
            _make_issue(identifier="ISS-1", age_hours=5.0, agent_id="agent-ex-001", title="Exchange API timeout"),
            _make_issue(identifier="ISS-2", age_hours=1.0, agent_id="agent-ex-001", title="Exchange API timeout"),
        ]
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_in_progress_issues",
            lambda: issues,
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_live_runs",
            lambda: [],
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.load_config",
            lambda: SAMPLE_CONFIG,
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.post_comment",
            MagicMock(),
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.invoke_heartbeat",
            MagicMock(),
        )

        summary = run_monitor(SAMPLE_CONFIG, _empty_state(), dry_run=True)
        matches = summary["matches"]
        assert matches.get("exchange_api_timeout", 0) == 1

    def test_handles_fetch_failure(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import run_monitor

        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_in_progress_issues",
            lambda: (_ for _ in ()).throw(RuntimeError("Connection refused")),
        )

        summary = run_monitor(SAMPLE_CONFIG, _empty_state())
        assert "error" in summary

    def test_target_scenario_filters_only_requested(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import run_monitor

        issues = [
            _make_issue(identifier="ISS-1", age_hours=10.0, agent_id="any-agent", title="orphan"),
            _make_issue(identifier="ISS-2", age_hours=5.0, agent_id="agent-ex-001", title="Exchange API timeout"),
        ]
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_in_progress_issues",
            lambda: issues,
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_live_runs",
            lambda: [],
        )

        summary = run_monitor(SAMPLE_CONFIG, _empty_state(), dry_run=True, target_scenario="exchange_api_timeout")
        assert summary["scenarios_checked"] == 1
        assert summary["matches"].get("exchange_api_timeout", 0) == 1

    def test_target_scenario_not_found(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import run_monitor

        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_in_progress_issues",
            lambda: [],
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_live_runs",
            lambda: [],
        )

        summary = run_monitor(SAMPLE_CONFIG, _empty_state(), target_scenario="nonexistent")
        assert "error" in summary

    def test_batch_threshold_skips_below_min(self, monkeypatch):
        from scripts.paperclip_recovery_monitor import run_monitor

        issues = [
            _make_issue(identifier="ISS-1", age_hours=5.0, agent_id="any-agent", title="batch job"),
        ]
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_in_progress_issues",
            lambda: issues,
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_monitor.fetch_live_runs",
            lambda: [],
        )

        summary = run_monitor(SAMPLE_CONFIG, _empty_state(), dry_run=True)
        assert summary["matches"].get("batch_threshold_scenario", 0) == 1
        assert len(summary["actions_taken"]) == 0


# ---------------------------------------------------------------------------
# _rotate_log_if_needed
# ---------------------------------------------------------------------------


class TestRotateLog:
    def test_rotates_when_file_too_large(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor import _rotate_log_if_needed, MONITOR_LOG, MAX_LOG_BYTES

        log = tmp_path / "recovery.log"
        log.write_text("x" * (MAX_LOG_BYTES + 100))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.MONITOR_LOG", log)

        _rotate_log_if_needed()
        bak = log.with_suffix(".log.1")
        assert bak.exists()

    def test_no_rotate_when_under_limit(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_monitor import _rotate_log_if_needed, MAX_LOG_BYTES

        log = tmp_path / "recovery.log"
        log.write_text("x" * (MAX_LOG_BYTES // 2))
        monkeypatch.setattr("scripts.paperclip_recovery_monitor.MONITOR_LOG", log)

        _rotate_log_if_needed()
        bak = log.with_suffix(".log.1")
        assert not bak.exists()
