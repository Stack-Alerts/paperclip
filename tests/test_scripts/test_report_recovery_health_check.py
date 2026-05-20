#!/usr/bin/env python3
"""Tests for recovery health check reporting script."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

# Add scripts to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
import sys
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from report_recovery_health_check import (
    format_report,
    run_health_check,
    run_stalled_workflows_check,
)


class TestFormatReport:
    """Test report formatting."""

    def test_format_healthy_report(self):
        """Test formatting a healthy report."""
        health_result = {
            "overall_status": "healthy",
            "checks": {
                "monitor_execution": {
                    "status": "pass",
                    "details": {"last_run_age_minutes": 15.0},
                    "message": "",
                },
                "configuration": {
                    "status": "pass",
                    "details": {"scenarios_total": 3, "scenarios_enabled": 3},
                    "message": "",
                },
            },
            "alerts": [],
            "warnings": [],
        }

        stalled_result = {
            "summary": {
                "total_issues_in_recovery": 0,
                "issues_with_escalations": 0,
                "issues_stuck_in_loop": 0,
            },
            "scenarios": {},
        }

        report = format_report(health_result, stalled_result)

        assert "HEALTHY" in report
        assert "✅" in report
        assert "No stalled workflows" in report
        assert "monitor_execution" in report

    def test_format_degraded_report(self):
        """Test formatting a degraded report."""
        health_result = {
            "overall_status": "degraded",
            "checks": {
                "monitor_execution": {
                    "status": "warning",
                    "details": {"last_run_age_minutes": 35.0},
                    "message": "Monitor last ran 35 minutes ago",
                },
            },
            "alerts": [],
            "warnings": ["Monitor last ran 35 minutes ago (expected ~30 min)"],
        }

        stalled_result = {
            "summary": {
                "total_issues_in_recovery": 0,
                "issues_with_escalations": 0,
                "issues_stuck_in_loop": 0,
            },
            "scenarios": {},
        }

        report = format_report(health_result, stalled_result)

        assert "DEGRADED" in report
        assert "⚠️" in report
        assert "Monitor last ran" in report

    def test_format_unhealthy_report(self):
        """Test formatting an unhealthy report."""
        health_result = {
            "overall_status": "unhealthy",
            "checks": {
                "monitor_execution": {
                    "status": "fail",
                    "details": {"last_run_age_minutes": 120.0},
                    "message": "Monitor has not run in 120 minutes",
                },
            },
            "alerts": ["monitor_execution: Monitor has not run in 120 minutes"],
            "warnings": [],
        }

        stalled_result = {
            "summary": {
                "total_issues_in_recovery": 2,
                "issues_with_escalations": 1,
                "issues_stuck_in_loop": 0,
            },
            "scenarios": {
                "exchange_api_timeout": {
                    "scenario_name": "Exchange API Timeout",
                    "total_issues": 2,
                }
            },
        }

        report = format_report(health_result, stalled_result)

        assert "UNHEALTHY" in report
        assert "🔴" in report
        assert "Issues in recovery:" in report and "2" in report
        assert "Escalations:" in report and "1" in report

    def test_format_with_stalled_workflows(self):
        """Test formatting report with stalled workflows."""
        health_result = {
            "overall_status": "healthy",
            "checks": {},
            "alerts": [],
            "warnings": [],
        }

        stalled_result = {
            "summary": {
                "total_issues_in_recovery": 1,
                "issues_with_escalations": 0,
                "issues_stuck_in_loop": 0,
            },
            "scenarios": {
                "position_mismatch": {
                    "scenario_name": "Position Mismatch",
                    "total_issues": 1,
                }
            },
        }

        report = format_report(health_result, stalled_result)

        assert "Issues in recovery:" in report and "1" in report
        assert "Position Mismatch" in report

    def test_format_health_check_error(self):
        """Test formatting report when health check fails."""
        health_result = {
            "error": "Recovery state file not found",
        }

        stalled_result = {
            "summary": {
                "total_issues_in_recovery": 0,
                "issues_with_escalations": 0,
                "issues_stuck_in_loop": 0,
            },
            "scenarios": {},
        }

        report = format_report(health_result, stalled_result)

        assert "Error" in report
        assert "Recovery state file not found" in report
