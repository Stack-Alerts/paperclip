"""Unit tests for scripts/paperclip_recovery_health_check.py — BTCAAAAA-29067.

Tests cover:
- Monitor execution health (run frequency, state file validity)
- Configuration validation (schema, defaults, scenarios)
- State file health (recovery metrics, loop detection)
- Log file health (error patterns, rotation)
- Systemd timer status (if available)
- Overall health status aggregation
- CLI argument handling (--json-report, --alert-on-unhealthy)

Verified workflows: health check detection, status aggregation, alert messaging.
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

pytestmark = [pytest.mark.regression]

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

SAMPLE_CONFIG = {
    "description": "Recovery Actions Config",
    "version": "1.0.0",
    "company_id": "73419cf3-bd37-4a7c-8782-311ccb47fced",
    "defaults": {
        "recovery_cooldown_minutes": 120,
        "max_recovery_attempts": 3,
        "escalation_agent_id": "escalation-agent-id",
        "alert_project_id": "alert-project-id",
    },
    "agent_scope_map": {
        "exchange_agents": ["agent-ex-001", "agent-ex-002"],
        "risk_agents": ["agent-risk-001"],
        "signal_agents": ["agent-sig-001"],
    },
    "recovery_scenarios": [
        {
            "id": "exchange_api_timeout",
            "name": "Exchange API Timeout Recovery",
            "description": "Detect and recover exchange API timeouts",
            "enabled": True,
            "detection": {
                "min_age_hours": 2,
                "max_age_hours": 72,
            },
            "recovery_actions": [
                {"action": "add_comment", "description": "Post diagnostic comment"},
                {"action": "invoke_heartbeat", "description": "Trigger heartbeat"},
            ],
        },
        {
            "id": "position_mismatch",
            "name": "Position Mismatch Detection",
            "description": "Detect position reconciliation failures",
            "enabled": True,
            "detection": {
                "min_age_hours": 1,
                "max_age_hours": 48,
            },
            "recovery_actions": [
                {"action": "add_comment", "description": "Diagnostic check"},
            ],
        },
        {
            "id": "orphan_checkout",
            "name": "Orphaned Checkout Recovery",
            "description": "Detect orphaned checkouts",
            "enabled": False,  # Disabled scenario
            "detection": {
                "min_age_hours": 6,
                "max_age_hours": 168,
            },
            "recovery_actions": [
                {"action": "force_release", "description": "Force release"},
            ],
        },
    ],
}


def _empty_state() -> dict:
    return {
        "scenarios": {},
        "last_run_at": datetime.now(tz=UTC).isoformat(),
    }


def _state_with_issue(
    scenario_id: str = "exchange_api_timeout",
    issue_id: str = "00000000-0000-4000-a000-000000000001",
    recovery_attempts: int = 1,
    age_hours: float = 5.0,
    escalation_issue_id: str | None = None,
) -> dict:
    """Create a recovery state with a single tracked issue."""
    first_detected = datetime.now(tz=UTC) - timedelta(hours=age_hours)
    last_attempted = datetime.now(tz=UTC) - timedelta(minutes=5)

    state = {
        "scenarios": {
            scenario_id: {
                issue_id: {
                    "recovery_attempts": recovery_attempts,
                    "first_detected_at": first_detected.isoformat(),
                    "last_recovery_attempt_at": last_attempted.isoformat(),
                    "last_action": "invoke_heartbeat",
                }
            }
        },
        "last_run_at": datetime.now(tz=UTC).isoformat(),
    }

    if escalation_issue_id:
        state["scenarios"][scenario_id][issue_id][
            "escalation_issue_id"
        ] = escalation_issue_id

    return state


# ---------------------------------------------------------------------------
# Tests: Monitor execution health
# ---------------------------------------------------------------------------


class TestMonitorExecution:
    def test_pass_when_monitor_recently_ran(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_monitor_execution

        state = _empty_state()
        state["last_run_at"] = (datetime.now(tz=UTC) - timedelta(minutes=5)).isoformat()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_monitor_execution()
        assert status == "pass"
        assert msg is None
        assert details["age_minutes"] < 10

    def test_warning_when_monitor_ran_35_to_45_min_ago(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_monitor_execution

        state = _empty_state()
        state["last_run_at"] = (datetime.now(tz=UTC) - timedelta(minutes=40)).isoformat()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_monitor_execution()
        assert status == "warning"
        assert "expected ~30 min" in msg
        assert details.get("last_run_age_minutes", details.get("age_minutes", 0)) > 35

    def test_fail_when_monitor_ran_over_45_min_ago(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_monitor_execution

        state = _empty_state()
        state["last_run_at"] = (
            datetime.now(tz=UTC) - timedelta(minutes=60)
        ).isoformat()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_monitor_execution()
        assert status == "fail"
        assert "not run in" in msg
        assert details.get("last_run_age_minutes", details.get("age_minutes", 0)) > 45

    def test_fail_when_state_file_missing(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_monitor_execution

        sf = tmp_path / "missing.json"
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_monitor_execution()
        assert status == "fail"
        assert "state file not found" in msg.lower()

    def test_fail_when_state_file_corrupt(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_monitor_execution

        sf = tmp_path / "corrupt.json"
        sf.write_text("{not valid json")
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_monitor_execution()
        assert status == "fail"
        assert "corrupted" in msg.lower()

    def test_warning_when_last_run_not_recorded(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_monitor_execution

        state = {"scenarios": {}}  # No last_run_at field
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_monitor_execution()
        assert status == "warning"
        assert "not recorded" in msg.lower()


# ---------------------------------------------------------------------------
# Tests: Configuration validation
# ---------------------------------------------------------------------------


class TestConfiguration:
    def test_pass_with_valid_config(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_configuration

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )

        status, details, msg = check_configuration()
        assert status == "pass"
        assert msg is None
        assert details["scenarios_enabled"] == 2  # 2 enabled, 1 disabled
        assert details["scenarios_total"] == 3

    def test_fail_when_config_missing(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_configuration

        cfg = tmp_path / "missing.json"
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )

        status, details, msg = check_configuration()
        assert status == "fail"
        assert "not found" in msg.lower()

    def test_fail_when_config_corrupt(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_configuration

        cfg = tmp_path / "corrupt.json"
        cfg.write_text("{bad json")
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )

        status, details, msg = check_configuration()
        assert status == "fail"
        assert "corrupted" in msg.lower()

    def test_warning_when_missing_defaults(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_configuration

        bad_config = SAMPLE_CONFIG.copy()
        bad_config["defaults"] = {}  # Missing all defaults

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(bad_config))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )

        status, details, msg = check_configuration()
        assert status == "warning"
        assert "missing" in msg.lower() or "default" in msg.lower()

    def test_warning_when_no_agent_scopes(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_configuration

        bad_config = SAMPLE_CONFIG.copy()
        bad_config["agent_scope_map"] = {}  # No agent scopes

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(bad_config))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )

        status, details, msg = check_configuration()
        assert status == "warning"
        assert "agent scope" in msg.lower()

    def test_warning_when_no_scenarios(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_configuration

        bad_config = SAMPLE_CONFIG.copy()
        bad_config["recovery_scenarios"] = []  # No scenarios

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(bad_config))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )

        status, details, msg = check_configuration()
        assert status == "warning"
        assert "scenario" in msg.lower()


# ---------------------------------------------------------------------------
# Tests: State health
# ---------------------------------------------------------------------------


class TestStateHealth:
    def test_pass_with_empty_state(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_state_health

        state = _empty_state()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_state_health()
        assert status == "pass"
        assert details["total_issues_recovered"] == 0
        assert details["active_escalations"] == 0

    def test_pass_with_tracked_issues_no_loops(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_state_health

        state = _state_with_issue(recovery_attempts=2)
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_state_health()
        assert status == "pass"
        assert details["total_issues_recovered"] == 1
        # Attempt was 5 min ago, which is within the 15-minute recent window
        assert details["recent_recovery_attempts_15min"] == 1

    def test_pass_with_escalated_issues(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_state_health

        state = _state_with_issue(escalation_issue_id="esc-001")
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_state_health()
        assert status == "pass"
        assert details["active_escalations"] == 1

    def test_warning_when_high_frequency_attempts(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_state_health

        # Create state with 12 recent attempts (within 15 min)
        # Use 10 minutes ago to be safely within the 15-minute window
        state = {"scenarios": {}, "last_run_at": datetime.now(tz=UTC).isoformat()}
        recent_time = datetime.now(tz=UTC) - timedelta(minutes=10)
        state["scenarios"]["test_scenario"] = {}

        for i in range(12):
            state["scenarios"]["test_scenario"][f"issue-{i}"] = {
                "recovery_attempts": 1,
                "first_detected_at": recent_time.isoformat(),
                "last_recovery_attempt_at": recent_time.isoformat(),
                "last_action": "invoke_heartbeat",
            }

        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_state_health()
        assert status == "warning"
        assert "recovery loop" in msg.lower()
        assert details["recent_recovery_attempts_15min"] >= 10

    def test_warning_when_state_file_missing(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_state_health

        sf = tmp_path / "missing.json"
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_state_health()
        assert status == "warning"

    def test_fail_when_state_file_corrupt(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_state_health

        sf = tmp_path / "corrupt.json"
        sf.write_text("{bad json")
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )

        status, details, msg = check_state_health()
        assert status == "fail"
        assert "cannot be parsed" in msg.lower()


# ---------------------------------------------------------------------------
# Tests: Log health
# ---------------------------------------------------------------------------


class TestLogHealth:
    def test_pass_with_clean_logs(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_log_health

        log_file = tmp_path / "monitor.log"
        log_file.write_text(
            "2026-05-19 10:00:00 [INFO] Recovery monitor starting\n"
            "2026-05-19 10:00:05 [INFO] Fetched 10 in_progress issues\n"
            "2026-05-19 10:00:10 [INFO] Recovery monitor complete\n"
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        status, details, msg = check_log_health()
        assert status == "pass"
        assert details["recent_errors"] == 0

    def test_warning_with_elevated_errors(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_log_health

        log_file = tmp_path / "monitor.log"
        log_lines = ["2026-05-19 10:00:00 [INFO] Starting\n"]
        # Add 6 error lines to trigger warning threshold
        for i in range(6):
            log_lines.append(f"2026-05-19 10:00:{i:02d} [ERROR] Error {i}\n")
        log_file.write_text("".join(log_lines))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        status, details, msg = check_log_health()
        assert status == "warning"
        assert details["recent_errors"] >= 6

    def test_fail_with_fatal_errors(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_log_health

        log_file = tmp_path / "monitor.log"
        log_file.write_text(
            "2026-05-19 10:00:00 [INFO] Starting\n"
            "2026-05-19 10:00:05 [ERROR] Fatal database error\n"
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        status, details, msg = check_log_health()
        assert status == "fail"
        assert "fatal" in msg.lower()

    def test_fail_with_high_error_exception_rate(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_log_health

        log_file = tmp_path / "monitor.log"
        log_lines = []
        # Add many errors and exceptions to trigger failure threshold
        for i in range(12):
            log_lines.append(f"2026-05-19 10:00:{i:02d} [ERROR] Error {i}\n")
        for i in range(7):
            log_lines.append(f"2026-05-19 10:00:{i:02d} [ERROR] Exception raised {i}\n")
        log_file.write_text("".join(log_lines))
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        status, details, msg = check_log_health()
        assert status == "fail"

    def test_warning_when_log_missing(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_log_health

        log_file = tmp_path / "missing.log"
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        status, details, msg = check_log_health()
        assert status == "warning"
        assert "not found" in msg.lower()

    def test_detects_connection_failures(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import check_log_health

        log_file = tmp_path / "monitor.log"
        log_file.write_text(
            "2026-05-19 10:00:00 [INFO] Starting\n"
            "2026-05-19 10:00:05 [ERROR] Connection refused\n"
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        status, details, msg = check_log_health()
        assert "connection" in details["failure_patterns"]


# ---------------------------------------------------------------------------
# Tests: Systemd timer
# ---------------------------------------------------------------------------


class TestSystemdTimer:
    def test_pass_when_systemd_not_available(self):
        from scripts.paperclip_recovery_health_check import check_systemd_timer

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            status, details, msg = check_systemd_timer()
            assert status == "pass"  # Not available is OK (GitHub Actions primary)

    def test_pass_when_timer_running(self):
        from scripts.paperclip_recovery_health_check import check_systemd_timer

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            status, details, msg = check_systemd_timer()
            assert status == "pass"
            assert details["systemd_timer_running"] is True

    def test_warning_when_timer_not_running(self):
        from scripts.paperclip_recovery_health_check import check_systemd_timer

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            status, details, msg = check_systemd_timer()
            assert status == "warning"
            assert "not running" in msg.lower()


# ---------------------------------------------------------------------------
# Tests: Health check result aggregation
# ---------------------------------------------------------------------------


class TestHealthCheckResult:
    def test_aggregates_all_pass_to_healthy(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import run_health_check

        # Setup all files as healthy
        state = _empty_state()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))

        log_file = tmp_path / "monitor.log"
        log_file.write_text("2026-05-19 10:00:00 [INFO] All good\n")

        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        result = run_health_check()
        assert result.overall_status == "healthy"
        assert len(result.alert_messages) == 0

    def test_degrades_to_degraded_with_warnings(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import run_health_check

        # Setup with some warnings
        state = _empty_state()
        state["last_run_at"] = (
            datetime.now(tz=UTC) - timedelta(minutes=40)
        ).isoformat()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))

        log_file = tmp_path / "monitor.log"
        log_file.write_text("2026-05-19 10:00:00 [INFO] All good\n")

        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        result = run_health_check()
        assert result.overall_status == "degraded"
        assert len(result.warning_messages) > 0

    def test_fails_unhealthy_with_critical_failures(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import run_health_check

        # Setup with missing config
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(_empty_state()))

        cfg = tmp_path / "missing.json"  # Config missing!

        log_file = tmp_path / "monitor.log"
        log_file.write_text("2026-05-19 10:00:00 [INFO] All good\n")

        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        result = run_health_check()
        assert result.overall_status == "unhealthy"
        assert len(result.alert_messages) > 0

    def test_returns_dict_serializable_to_json(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import run_health_check

        state = _empty_state()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))

        log_file = tmp_path / "monitor.log"
        log_file.write_text("2026-05-19 10:00:00 [INFO] All good\n")

        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )

        result = run_health_check()
        report = result.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(report, default=str)
        assert "timestamp" in json_str
        assert "overall_status" in json_str


# ---------------------------------------------------------------------------
# Tests: CLI argument handling
# ---------------------------------------------------------------------------


class TestCLI:
    def test_json_report_flag(self, tmp_path, monkeypatch, capsys):
        from scripts.paperclip_recovery_health_check import main

        state = _empty_state()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))

        log_file = tmp_path / "monitor.log"
        log_file.write_text("2026-05-19 10:00:00 [INFO] All good\n")

        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )
        monkeypatch.setattr("sys.argv", ["cmd", "--json-report"])

        main()
        captured = capsys.readouterr()
        assert "overall_status" in captured.out
        assert "{" in captured.out  # JSON output

    def test_alert_on_unhealthy_exits_1_when_unhealthy(
        self, tmp_path, monkeypatch
    ):
        from scripts.paperclip_recovery_health_check import main

        sf = tmp_path / "missing.json"  # Missing file will fail health check
        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))
        log_file = tmp_path / "monitor.log"
        log_file.write_text("2026-05-19 10:00:00 [INFO] All good\n")

        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )
        monkeypatch.setattr("sys.argv", ["cmd", "--alert-on-unhealthy"])

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_alert_on_unhealthy_exits_0_when_healthy(self, tmp_path, monkeypatch):
        from scripts.paperclip_recovery_health_check import main

        state = _empty_state()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))

        log_file = tmp_path / "monitor.log"
        log_file.write_text("2026-05-19 10:00:00 [INFO] All good\n")

        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.RECOVERY_STATE_FILE", sf
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.CONFIG_PATH", cfg
        )
        monkeypatch.setattr(
            "scripts.paperclip_recovery_health_check.MONITOR_LOG", log_file
        )
        monkeypatch.setattr("sys.argv", ["cmd", "--alert-on-unhealthy"])

        main()  # Should not raise SystemExit
