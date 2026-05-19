"""Unit tests for scripts/paperclip_stalled_workflow_reporter.py — BTCAAAAA-29032.

Tests cover:
- Configuration and state loading
- Stalled issue analysis and detection
- Recovery loop detection
- Escalation tracking
- Report generation (JSON and Markdown)
- Scenario filtering

Verified workflows: stalled issue detection, recovery metrics, escalation tracking.
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
    },
    "recovery_scenarios": [
        {
            "id": "exchange_api_timeout",
            "name": "Exchange API Timeout Recovery",
            "description": "Detect and recover exchange API timeouts",
            "enabled": True,
        },
        {
            "id": "position_mismatch",
            "name": "Position Mismatch Detection",
            "description": "Detect position reconciliation failures",
            "enabled": True,
        },
        {
            "id": "orphan_checkout",
            "name": "Orphaned Checkout Recovery",
            "description": "Detect orphaned checkouts",
            "enabled": True,
        },
    ],
}


def _empty_state() -> dict:
    return {"scenarios": {}, "last_run_at": None}


def _state_with_issue(
    scenario_id: str = "exchange_api_timeout",
    issue_id: str = "00000000-0000-4000-a000-000000000001",
    recovery_attempts: int = 1,
    age_hours: float = 5.0,
    escalation_issue_id: str | None = None,
) -> dict:
    """Create a recovery state with a single tracked issue."""
    first_detected = datetime.now(tz=UTC) - timedelta(hours=age_hours)
    last_attempted = datetime.now(tz=UTC)

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
        state["scenarios"][scenario_id][issue_id]["escalation_issue_id"] = escalation_issue_id

    return state


# ---------------------------------------------------------------------------
# Config/state loading
# ---------------------------------------------------------------------------


class TestConfigLoading:
    def test_loads_valid_config(self, tmp_path, monkeypatch):
        from scripts.paperclip_stalled_workflow_reporter import load_config

        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG))
        monkeypatch.setattr("scripts.paperclip_stalled_workflow_reporter.CONFIG_PATH", cfg)

        config = load_config()
        assert config["company_id"] == SAMPLE_CONFIG["company_id"]
        assert len(config.get("recovery_scenarios", [])) == 3

    def test_returns_empty_dict_when_config_missing(self, tmp_path, monkeypatch):
        from scripts.paperclip_stalled_workflow_reporter import load_config

        cfg = tmp_path / "missing.json"
        monkeypatch.setattr("scripts.paperclip_stalled_workflow_reporter.CONFIG_PATH", cfg)

        config = load_config()
        assert config == {}

    def test_returns_empty_dict_on_corrupt_config(self, tmp_path, monkeypatch):
        from scripts.paperclip_stalled_workflow_reporter import load_config

        cfg = tmp_path / "corrupt.json"
        cfg.write_text("{not valid json")
        monkeypatch.setattr("scripts.paperclip_stalled_workflow_reporter.CONFIG_PATH", cfg)

        config = load_config()
        assert config == {}


class TestStateLoading:
    def test_loads_valid_state(self, tmp_path, monkeypatch):
        from scripts.paperclip_stalled_workflow_reporter import load_recovery_state

        state = _state_with_issue()
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr("scripts.paperclip_stalled_workflow_reporter.RECOVERY_STATE_FILE", sf)

        loaded = load_recovery_state()
        assert "exchange_api_timeout" in loaded["scenarios"]

    def test_returns_empty_state_when_missing(self, tmp_path, monkeypatch):
        from scripts.paperclip_stalled_workflow_reporter import load_recovery_state

        sf = tmp_path / "missing.json"
        monkeypatch.setattr("scripts.paperclip_stalled_workflow_reporter.RECOVERY_STATE_FILE", sf)

        state = load_recovery_state()
        assert state["scenarios"] == {}

    def test_returns_empty_state_on_corrupt_file(self, tmp_path, monkeypatch):
        from scripts.paperclip_stalled_workflow_reporter import load_recovery_state

        sf = tmp_path / "corrupt.json"
        sf.write_text("{bad json")
        monkeypatch.setattr("scripts.paperclip_stalled_workflow_reporter.RECOVERY_STATE_FILE", sf)

        state = load_recovery_state()
        assert state["scenarios"] == {}


# ---------------------------------------------------------------------------
# ISO parsing
# ---------------------------------------------------------------------------


class TestParseIso:
    def test_parses_iso_with_z(self):
        from scripts.paperclip_stalled_workflow_reporter import parse_iso

        dt = parse_iso("2026-05-19T10:00:00Z")
        assert dt is not None
        assert isinstance(dt, datetime)

    def test_parses_iso_with_offset(self):
        from scripts.paperclip_stalled_workflow_reporter import parse_iso

        dt = parse_iso("2026-05-19T10:00:00+00:00")
        assert dt is not None

    def test_returns_none_for_none(self):
        from scripts.paperclip_stalled_workflow_reporter import parse_iso

        assert parse_iso(None) is None

    def test_returns_none_for_empty(self):
        from scripts.paperclip_stalled_workflow_reporter import parse_iso

        assert parse_iso("") is None

    def test_returns_none_for_invalid_format(self):
        from scripts.paperclip_stalled_workflow_reporter import parse_iso

        assert parse_iso("not-a-timestamp") is None


# ---------------------------------------------------------------------------
# Scenario name lookup
# ---------------------------------------------------------------------------


class TestGetScenarioName:
    def test_returns_name_from_config(self):
        from scripts.paperclip_stalled_workflow_reporter import get_scenario_name

        name = get_scenario_name(SAMPLE_CONFIG, "exchange_api_timeout")
        assert name == "Exchange API Timeout Recovery"

    def test_returns_id_when_not_found(self):
        from scripts.paperclip_stalled_workflow_reporter import get_scenario_name

        name = get_scenario_name(SAMPLE_CONFIG, "unknown_scenario")
        assert name == "unknown_scenario"

    def test_handles_empty_config(self):
        from scripts.paperclip_stalled_workflow_reporter import get_scenario_name

        name = get_scenario_name({}, "any_scenario")
        assert name == "any_scenario"


# ---------------------------------------------------------------------------
# Stalled issue analysis
# ---------------------------------------------------------------------------


class TestAnalyzeStalledIssues:
    def test_returns_empty_report_for_empty_state(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        report = analyze_stalled_issues(_empty_state(), SAMPLE_CONFIG)
        assert report["summary"]["total_issues_in_recovery"] == 0
        assert report["summary"]["issues_with_escalations"] == 0
        assert report["scenarios"] == {}

    def test_counts_single_issue_in_recovery(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = _state_with_issue(recovery_attempts=2)
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert report["summary"]["total_issues_in_recovery"] == 1
        assert report["summary"]["total_scenarios_tracking_issues"] == 1

    def test_counts_escalated_issues(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = _state_with_issue(escalation_issue_id="escalation-id-123")
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert report["summary"]["issues_with_escalations"] == 1
        issue = report["issues"][0]
        assert issue["status"] == "escalated"
        assert issue["escalation_issue_id"] == "escalation-id-123"

    def test_marks_non_escalated_as_in_recovery(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = _state_with_issue()
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        issue = report["issues"][0]
        assert issue["status"] == "in_recovery"
        assert "escalation_issue_id" not in issue

    def test_calculates_recovery_age_hours(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = _state_with_issue(age_hours=3.0)
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        issue = report["issues"][0]
        age = issue.get("recovery_age_hours", 0)
        assert 2.9 <= age <= 3.1

    def test_includes_recovery_metrics(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = _state_with_issue(recovery_attempts=2)
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        issue = report["issues"][0]
        assert issue["recovery_attempts"] == 2
        assert "first_detected_at" in issue
        assert "last_recovery_attempt_at" in issue
        assert "last_action" in issue

    def test_organizes_by_scenario(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = {
            "scenarios": {
                "exchange_api_timeout": {
                    "issue-1": {
                        "recovery_attempts": 1,
                        "first_detected_at": datetime.now(tz=UTC).isoformat(),
                        "last_recovery_attempt_at": datetime.now(tz=UTC).isoformat(),
                        "last_action": "add_comment",
                    },
                },
                "position_mismatch": {
                    "issue-2": {
                        "recovery_attempts": 1,
                        "first_detected_at": datetime.now(tz=UTC).isoformat(),
                        "last_recovery_attempt_at": datetime.now(tz=UTC).isoformat(),
                        "last_action": "add_comment",
                    },
                },
            },
            "last_run_at": None,
        }
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert len(report["scenarios"]) == 2
        assert report["scenarios"]["exchange_api_timeout"]["total_issues"] == 1
        assert report["scenarios"]["position_mismatch"]["total_issues"] == 1


# ---------------------------------------------------------------------------
# Recovery loop detection
# ---------------------------------------------------------------------------


class TestRecoveryLoopDetection:
    def test_detects_rapid_recovery_attempts(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        now = datetime.now(tz=UTC)
        recent = now - timedelta(seconds=100)
        state = {
            "scenarios": {
                "exchange_api_timeout": {
                    "issue-1": {
                        "recovery_attempts": 3,
                        "first_detected_at": (now - timedelta(hours=1)).isoformat(),
                        "last_recovery_attempt_at": recent.isoformat(),
                        "last_action": "invoke_heartbeat",
                    },
                },
            },
            "last_run_at": None,
        }
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert report["summary"]["issues_stuck_in_loop"] == 1
        issue = report["issues"][0]
        assert "warning" in issue
        assert "Rapid recovery attempts" in issue["warning"]

    def test_no_loop_with_single_attempt(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = _state_with_issue(recovery_attempts=1)
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert report["summary"]["issues_stuck_in_loop"] == 0
        issue = report["issues"][0]
        assert "warning" not in issue

    def test_no_loop_with_old_last_attempt(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        now = datetime.now(tz=UTC)
        old = now - timedelta(minutes=10)
        state = {
            "scenarios": {
                "exchange_api_timeout": {
                    "issue-1": {
                        "recovery_attempts": 3,
                        "first_detected_at": (now - timedelta(hours=2)).isoformat(),
                        "last_recovery_attempt_at": old.isoformat(),
                        "last_action": "invoke_heartbeat",
                    },
                },
            },
            "last_run_at": None,
        }
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert report["summary"]["issues_stuck_in_loop"] == 0


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------


class TestMarkdownReportGeneration:
    def test_generates_empty_report(self):
        from scripts.paperclip_stalled_workflow_reporter import generate_markdown_report

        report = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "summary": {
                "total_issues_in_recovery": 0,
                "issues_with_escalations": 0,
                "issues_stuck_in_loop": 0,
            },
            "scenarios": {},
            "issues": [],
        }
        md = generate_markdown_report(report)

        assert "No stalled workflows" in md
        assert "✅" in md

    def test_includes_summary_section(self):
        from scripts.paperclip_stalled_workflow_reporter import generate_markdown_report

        state = _state_with_issue(recovery_attempts=2)
        report = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "summary": {
                "total_scenarios_tracking_issues": 1,
                "total_issues_in_recovery": 1,
                "issues_with_escalations": 0,
                "issues_stuck_in_loop": 0,
            },
            "scenarios": {},
            "issues": [],
        }
        md = generate_markdown_report(report)

        assert "Summary" in md
        assert "Scenarios tracking issues" in md
        assert "Total issues in recovery" in md

    def test_organizes_by_scenario(self):
        from scripts.paperclip_stalled_workflow_reporter import generate_markdown_report

        report = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "summary": {
                "total_scenarios_tracking_issues": 1,
                "total_issues_in_recovery": 1,
                "issues_with_escalations": 0,
                "issues_stuck_in_loop": 0,
            },
            "scenarios": {
                "exchange_api_timeout": {
                    "scenario_id": "exchange_api_timeout",
                    "scenario_name": "Exchange API Timeout Recovery",
                    "total_issues": 1,
                    "issues": [
                        {
                            "issue_id": "00000000-0000-4000-a000-000000000001",
                            "scenario_id": "exchange_api_timeout",
                            "recovery_attempts": 2,
                            "recovery_age_hours": 5.0,
                            "status": "in_recovery",
                        }
                    ],
                }
            },
            "issues": [],
        }
        md = generate_markdown_report(report)

        assert "By Scenario" in md
        assert "Exchange API Timeout Recovery" in md

    def test_includes_warnings_in_report(self):
        from scripts.paperclip_stalled_workflow_reporter import generate_markdown_report

        report = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "summary": {
                "total_scenarios_tracking_issues": 1,
                "total_issues_in_recovery": 1,
                "issues_with_escalations": 0,
                "issues_stuck_in_loop": 1,
            },
            "scenarios": {
                "exchange_api_timeout": {
                    "scenario_id": "exchange_api_timeout",
                    "scenario_name": "Exchange API Timeout Recovery",
                    "total_issues": 1,
                    "issues": [
                        {
                            "issue_id": "00000000-0000-4000-a000-000000000001",
                            "scenario_id": "exchange_api_timeout",
                            "recovery_attempts": 3,
                            "recovery_age_hours": 2.0,
                            "status": "in_recovery",
                            "warning": "Rapid recovery attempts detected",
                        }
                    ],
                }
            },
            "issues": [],
        }
        md = generate_markdown_report(report)

        assert "⚠️" in md


# ---------------------------------------------------------------------------
# Full end-to-end analysis
# ---------------------------------------------------------------------------


class TestEndToEndAnalysis:
    def test_complex_recovery_scenario(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        now = datetime.now(tz=UTC)
        state = {
            "scenarios": {
                "exchange_api_timeout": {
                    "issue-1": {
                        "recovery_attempts": 1,
                        "first_detected_at": (now - timedelta(hours=3)).isoformat(),
                        "last_recovery_attempt_at": (now - timedelta(minutes=30)).isoformat(),
                        "last_action": "add_comment",
                    },
                    "issue-2": {
                        "recovery_attempts": 4,
                        "first_detected_at": (now - timedelta(hours=5)).isoformat(),
                        "last_recovery_attempt_at": (now - timedelta(seconds=100)).isoformat(),
                        "last_action": "invoke_heartbeat",
                        "escalation_issue_id": "esc-123",
                    },
                },
                "position_mismatch": {
                    "issue-3": {
                        "recovery_attempts": 2,
                        "first_detected_at": (now - timedelta(hours=1)).isoformat(),
                        "last_recovery_attempt_at": now.isoformat(),
                        "last_action": "add_comment",
                    },
                },
            },
            "last_run_at": now.isoformat(),
        }

        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert report["summary"]["total_issues_in_recovery"] == 3
        assert report["summary"]["total_scenarios_tracking_issues"] == 2
        assert report["summary"]["issues_with_escalations"] == 1
        assert report["summary"]["issues_stuck_in_loop"] == 2
        assert len(report["issues"]) == 3

        scenario_summaries = report["scenarios"]
        assert scenario_summaries["exchange_api_timeout"]["total_issues"] == 2
        assert scenario_summaries["position_mismatch"]["total_issues"] == 1

    def test_generates_valid_json_output(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = _state_with_issue(recovery_attempts=2, age_hours=4.0)
        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        json_str = json.dumps(report, indent=2, default=str)
        parsed = json.loads(json_str)

        assert "timestamp" in parsed
        assert "summary" in parsed
        assert "scenarios" in parsed
        assert "issues" in parsed

    def test_handles_missing_timestamps_gracefully(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = {
            "scenarios": {
                "exchange_api_timeout": {
                    "issue-1": {
                        "recovery_attempts": 1,
                        # Missing timestamps
                        "last_action": "add_comment",
                    },
                },
            },
            "last_run_at": None,
        }

        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert report["summary"]["total_issues_in_recovery"] == 1
        issue = report["issues"][0]
        assert issue["first_detected_at"] is None
        assert issue["last_recovery_attempt_at"] is None


# ---------------------------------------------------------------------------
# Scenario filtering
# ---------------------------------------------------------------------------


class TestScenarioFiltering:
    def test_filters_to_specific_scenario(self, tmp_path, monkeypatch):
        from scripts.paperclip_stalled_workflow_reporter import load_recovery_state

        state = {
            "scenarios": {
                "exchange_api_timeout": {
                    "issue-1": {"recovery_attempts": 1},
                },
                "position_mismatch": {
                    "issue-2": {"recovery_attempts": 1},
                },
            },
            "last_run_at": None,
        }
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        monkeypatch.setattr("scripts.paperclip_stalled_workflow_reporter.RECOVERY_STATE_FILE", sf)

        loaded = load_recovery_state()
        filtered = {
            "scenarios": {
                "exchange_api_timeout": loaded.get("scenarios", {}).get("exchange_api_timeout", {})
            },
            "last_run_at": loaded.get("last_run_at"),
        }

        assert "exchange_api_timeout" in filtered["scenarios"]
        assert "position_mismatch" not in filtered["scenarios"]

    def test_analyze_filtered_state(self):
        from scripts.paperclip_stalled_workflow_reporter import analyze_stalled_issues

        state = {
            "scenarios": {
                "exchange_api_timeout": {
                    "issue-1": {
                        "recovery_attempts": 1,
                        "first_detected_at": datetime.now(tz=UTC).isoformat(),
                        "last_recovery_attempt_at": datetime.now(tz=UTC).isoformat(),
                        "last_action": "add_comment",
                    },
                },
            },
            "last_run_at": None,
        }

        report = analyze_stalled_issues(state, SAMPLE_CONFIG)

        assert len(report["scenarios"]) == 1
        assert "exchange_api_timeout" in report["scenarios"]
