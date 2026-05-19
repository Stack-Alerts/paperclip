#!/usr/bin/env python3
"""PaperClip Recovery Monitor Health Check — verifies recovery actions are functioning.

Periodically validates:
1. Monitor execution health (last run timestamp, error rate)
2. Configuration validity (scenarios enabled, agent scope map completeness)
3. State file integrity and recovery metrics
4. Log file health (recent errors, rotation status)

Usage:
    python scripts/paperclip_recovery_health_check.py
    python scripts/paperclip_recovery_health_check.py --json-report
    python scripts/paperclip_recovery_health_check.py --alert-on-unhealthy
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

HEALTH_LOG = Path.home() / ".paperclip" / "recovery_health_check.log"
MONITOR_LOG = Path.home() / ".paperclip" / "recovery_monitor.log"
RECOVERY_STATE_FILE = Path.home() / ".paperclip" / "recovery_monitor_state.json"
CONFIG_PATH = REPO_ROOT / "scripts" / "paperclip_recovery_actions.json"

HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(HEALTH_LOG),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("recovery_health_check")


class HealthCheckResult:
    """Aggregates health check status and diagnostic details."""

    def __init__(self):
        self.timestamp = datetime.now(timezone.utc)
        self.checks: dict[str, Any] = {}
        self.overall_status = "healthy"
        self.alert_messages: list[str] = []
        self.warning_messages: list[str] = []

    def add_check(
        self,
        name: str,
        status: str,  # 'pass', 'warning', 'fail'
        details: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        self.checks[name] = {
            "status": status,
            "details": details or {},
            "message": message or "",
        }
        if status == "fail":
            self.overall_status = "unhealthy"
            if message:
                self.alert_messages.append(f"{name}: {message}")
        elif status == "warning" and self.overall_status != "unhealthy":
            self.overall_status = "degraded"
            if message:
                self.warning_messages.append(f"{name}: {message}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status,
            "checks": self.checks,
            "alerts": self.alert_messages,
            "warnings": self.warning_messages,
        }


def check_monitor_execution() -> tuple[str, dict[str, Any], str | None]:
    """Check if recovery monitor is running regularly and successfully."""
    if not RECOVERY_STATE_FILE.exists():
        return (
            "fail",
            {"state_file_missing": True},
            "Recovery state file not found — monitor may have never run",
        )

    try:
        state = json.loads(RECOVERY_STATE_FILE.read_text())
    except (json.JSONDecodeError, ValueError) as e:
        return (
            "fail",
            {"state_file_corrupt": True},
            f"Recovery state file corrupted: {e}",
        )

    last_run = state.get("last_run_at")
    if not last_run:
        return (
            "warning",
            {"last_run": None},
            "Last run timestamp not recorded in state file",
        )

    try:
        last_run_time = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return (
            "warning",
            {"last_run": last_run, "parse_error": True},
            f"Could not parse last run timestamp: {last_run}",
        )

    now = datetime.now(timezone.utc)
    age_minutes = (now - last_run_time).total_seconds() / 60.0

    # Expect monitor to run at least every 45 minutes (30 min schedule + buffer)
    if age_minutes > 45:
        return (
            "fail",
            {"last_run_age_minutes": age_minutes},
            f"Monitor has not run in {age_minutes:.0f} minutes (expected < 45 min)",
        )
    elif age_minutes > 35:
        return (
            "warning",
            {"last_run_age_minutes": age_minutes},
            f"Monitor last ran {age_minutes:.0f} minutes ago (expected ~30 min)",
        )

    return (
        "pass",
        {"last_run": last_run, "age_minutes": age_minutes},
        None,
    )


def check_configuration() -> tuple[str, dict[str, Any], str | None]:
    """Validate recovery configuration file."""
    if not CONFIG_PATH.exists():
        return (
            "fail",
            {"config_missing": True},
            f"Configuration file not found: {CONFIG_PATH}",
        )

    try:
        config = json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, ValueError) as e:
        return (
            "fail",
            {"config_corrupt": True},
            f"Configuration file corrupted: {e}",
        )

    details: dict[str, Any] = {
        "config_version": config.get("version"),
        "scenarios_total": 0,
        "scenarios_enabled": 0,
        "agent_scopes_defined": 0,
    }

    # Check defaults
    defaults = config.get("defaults", {})
    if not defaults:
        return (
            "warning",
            details,
            "No default values configured",
        )

    required_defaults = [
        "recovery_cooldown_minutes",
        "max_recovery_attempts",
        "escalation_agent_id",
        "alert_project_id",
    ]
    missing_defaults = [k for k in required_defaults if k not in defaults]
    if missing_defaults:
        return (
            "warning",
            {**details, "missing_defaults": missing_defaults},
            f"Missing default config: {', '.join(missing_defaults)}",
        )

    # Check agent scope map
    agent_scope_map = config.get("agent_scope_map", {})
    details["agent_scopes_defined"] = len(agent_scope_map)
    if not agent_scope_map:
        return (
            "warning",
            details,
            "No agent scopes defined in agent_scope_map",
        )

    # Check scenarios
    scenarios = config.get("recovery_scenarios", [])
    details["scenarios_total"] = len(scenarios)
    details["scenarios_enabled"] = len([s for s in scenarios if s.get("enabled", True)])

    if not scenarios:
        return (
            "warning",
            details,
            "No recovery scenarios configured",
        )

    # Validate each scenario structure
    for scenario in scenarios:
        if "id" not in scenario or "recovery_actions" not in scenario:
            return (
                "warning",
                {**details, "invalid_scenario": scenario.get("id", "unknown")},
                f"Scenario {scenario.get('id', '?')} is missing required fields",
            )

    return ("pass", details, None)


def check_state_health() -> tuple[str, dict[str, Any], str | None]:
    """Analyze recovery state for health metrics."""
    if not RECOVERY_STATE_FILE.exists():
        return ("warning", {"state_file_missing": True}, None)

    try:
        state = json.loads(RECOVERY_STATE_FILE.read_text())
    except (json.JSONDecodeError, ValueError):
        return ("fail", {"state_file_corrupt": True}, "State file cannot be parsed")

    scenarios = state.get("scenarios", {})
    details: dict[str, Any] = {
        "scenarios_tracked": len(scenarios),
        "total_issues_recovered": 0,
        "active_escalations": 0,
    }

    for scenario_id, issues in scenarios.items():
        details["total_issues_recovered"] += len(issues)
        for issue_id, issue_state in issues.items():
            if issue_state.get("escalation_issue_id"):
                details["active_escalations"] += 1

    # Check for stale recovery attempts (stuck in recovery loop)
    last_run = state.get("last_run_at")
    stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
    stale_attempts = 0

    for scenario_id, issues in scenarios.items():
        for issue_id, issue_state in issues.items():
            last_attempt = issue_state.get("last_recovery_attempt_at")
            if last_attempt:
                try:
                    attempt_time = datetime.fromisoformat(
                        last_attempt.replace("Z", "+00:00")
                    )
                    # Flag if same issue was attempted in last 15 minutes (rapid loop)
                    if attempt_time > stale_threshold:
                        stale_attempts += 1
                except (ValueError, TypeError):
                    pass

    details["recent_recovery_attempts_15min"] = stale_attempts

    if stale_attempts > 10:
        return (
            "warning",
            details,
            f"High frequency of recovery attempts ({stale_attempts}) in last 15 min — possible recovery loop",
        )

    return ("pass", details, None)


def check_log_health() -> tuple[str, dict[str, Any], str | None]:
    """Analyze monitor log for errors and health issues."""
    if not MONITOR_LOG.exists():
        return ("warning", {"log_missing": True}, "Monitor log file not found")

    try:
        log_text = MONITOR_LOG.read_text()
    except IOError as e:
        return ("fail", {"log_read_error": True}, f"Cannot read log: {e}")

    log_size_kb = MONITOR_LOG.stat().st_size / 1024
    details: dict[str, Any] = {
        "log_size_kb": log_size_kb,
        "total_lines": len(log_text.splitlines()),
    }

    # Count error patterns in last 500 lines
    lines = log_text.splitlines()[-500:]
    recent_text = "\n".join(lines)

    error_count = recent_text.count("[ERROR]")
    fatal_count = recent_text.count("Fatal") + recent_text.count("fatal")
    exception_count = recent_text.count("Exception")

    details["recent_errors"] = error_count
    details["recent_fatal_issues"] = fatal_count
    details["recent_exceptions"] = exception_count

    # Check for specific failure patterns
    failure_patterns = [
        "Failed to fetch in_progress issues",
        "PAPERCLIP_API_KEY",
        "connection",
        "timeout",
        "Connection refused",
    ]

    failures = {
        p: recent_text.lower().count(p.lower()) for p in failure_patterns
    }
    details["failure_patterns"] = failures

    if fatal_count > 0 or (error_count > 10 and exception_count > 5):
        return (
            "fail",
            details,
            f"Recent fatal errors ({fatal_count}) or high error rate ({error_count} errors, {exception_count} exceptions)",
        )
    elif error_count > 5:
        return (
            "warning",
            details,
            f"Elevated error rate in logs ({error_count} errors in last 500 lines)",
        )

    return ("pass", details, None)


def check_systemd_timer() -> tuple[str, dict[str, Any], str | None]:
    """Check systemd timer status if available."""
    try:
        import subprocess

        result = subprocess.run(
            ["systemctl", "--user", "status", "paperclip-recovery-monitor.timer"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        is_running = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        # systemd or timer not available — this is OK, GitHub Actions primary scheduler
        return ("pass", {"systemd_available": False}, None)

    if not is_running:
        return (
            "warning",
            {"systemd_timer_running": False},
            "Systemd recovery monitor timer is not running (OK if using GitHub Actions)",
        )

    return ("pass", {"systemd_timer_running": True}, None)


def run_health_check() -> HealthCheckResult:
    """Execute all health checks and aggregate results."""
    result = HealthCheckResult()

    logger.info("Starting recovery monitor health check")

    # Run all checks
    status, details, msg = check_monitor_execution()
    result.add_check("monitor_execution", status, details, msg)

    status, details, msg = check_configuration()
    result.add_check("configuration", status, details, msg)

    status, details, msg = check_state_health()
    result.add_check("state_health", status, details, msg)

    status, details, msg = check_log_health()
    result.add_check("log_health", status, details, msg)

    status, details, msg = check_systemd_timer()
    result.add_check("systemd_timer", status, details, msg)

    # Log final status
    logger.info(
        "Health check complete: overall_status=%s, alerts=%d, warnings=%d",
        result.overall_status,
        len(result.alert_messages),
        len(result.warning_messages),
    )

    for alert in result.alert_messages:
        logger.error("ALERT: %s", alert)

    for warning in result.warning_messages:
        logger.warning("WARNING: %s", warning)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PaperClip Recovery Monitor Health Check"
    )
    parser.add_argument(
        "--json-report",
        action="store_true",
        help="Output health report as JSON",
    )
    parser.add_argument(
        "--alert-on-unhealthy",
        action="store_true",
        help="Exit with code 1 if health is not 'healthy'",
    )

    args = parser.parse_args()

    # Suppress console logging for JSON output
    if args.json_report:
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)

    result = run_health_check()
    report = result.to_dict()

    if args.json_report:
        print(json.dumps(report, indent=2, default=str))
    else:
        # Log success to console if not in JSON mode
        logger.info(
            "Health check complete: overall_status=%s",
            result.overall_status,
        )

    if args.alert_on_unhealthy and result.overall_status != "healthy":
        sys.exit(1)


if __name__ == "__main__":
    main()
