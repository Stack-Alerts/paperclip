#!/usr/bin/env python3
"""PaperClip Stalled Workflow Reporter — analyzes and reports on workflows detected as stalled.

Polls PaperClip Recovery Monitor state to identify:
1. Issues currently undergoing recovery
2. Workflows stuck in recovery loops
3. Escalated issues requiring manual intervention
4. Recovery action success/failure rates

Usage:
    python scripts/paperclip_stalled_workflow_reporter.py
    python scripts/paperclip_stalled_workflow_reporter.py --json-report
    python scripts/paperclip_stalled_workflow_reporter.py --scenario exchange_api_timeout
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

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from touch_index.paperclip_client import _base, _company

REPORTER_LOG = Path.home() / ".paperclip" / "stalled_workflow_reporter.log"
RECOVERY_STATE_FILE = Path.home() / ".paperclip" / "recovery_monitor_state.json"
CONFIG_PATH = REPO_ROOT / "scripts" / "paperclip_recovery_actions.json"

REPORTER_LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(REPORTER_LOG),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("stalled_workflow_reporter")


def load_recovery_state() -> dict[str, Any]:
    """Load recovery monitor state file."""
    if not RECOVERY_STATE_FILE.exists():
        logger.warning("Recovery state file not found")
        return {"scenarios": {}, "last_run_at": None}

    try:
        return json.loads(RECOVERY_STATE_FILE.read_text())
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse recovery state file: %s", e)
        return {"scenarios": {}, "last_run_at": None}


def load_config() -> dict[str, Any]:
    """Load recovery monitor configuration."""
    if not CONFIG_PATH.exists():
        logger.warning("Recovery config not found: %s", CONFIG_PATH)
        return {}

    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse recovery config: %s", e)
        return {}


def parse_iso(raw: str | None) -> datetime | None:
    """Parse ISO 8601 timestamp."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def get_scenario_name(config: dict[str, Any], scenario_id: str) -> str:
    """Get human-readable scenario name from config."""
    scenarios = config.get("recovery_scenarios", [])
    for s in scenarios:
        if s.get("id") == scenario_id:
            return s.get("name", scenario_id)
    return scenario_id


def analyze_stalled_issues(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Analyze recovery state to identify stalled issues."""
    now = datetime.now(timezone.utc)
    report: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "summary": {
            "total_scenarios_tracking_issues": 0,
            "total_issues_in_recovery": 0,
            "issues_with_escalations": 0,
            "issues_stuck_in_loop": 0,
        },
        "scenarios": {},
        "issues": [],
    }

    scenarios = state.get("scenarios", {})
    if not scenarios:
        logger.info("No scenarios tracking issues in recovery state")
        return report

    # Analyze each scenario
    for scenario_id, issues in scenarios.items():
        if not issues:
            continue

        report["summary"]["total_scenarios_tracking_issues"] += 1
        scenario_name = get_scenario_name(config, scenario_id)
        scenario_report: dict[str, Any] = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "total_issues": len(issues),
            "issues": [],
        }

        for issue_id, issue_state in issues.items():
            report["summary"]["total_issues_in_recovery"] += 1

            # Analyze individual issue
            issue_report: dict[str, Any] = {
                "issue_id": issue_id,
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
            }

            # Recovery metrics
            recovery_attempts = issue_state.get("recovery_attempts", 0)
            first_detected_at = parse_iso(issue_state.get("first_detected_at"))
            last_recovery_attempt_at = parse_iso(
                issue_state.get("last_recovery_attempt_at")
            )

            issue_report["recovery_attempts"] = recovery_attempts
            issue_report["first_detected_at"] = (
                first_detected_at.isoformat() if first_detected_at else None
            )
            issue_report["last_recovery_attempt_at"] = (
                last_recovery_attempt_at.isoformat()
                if last_recovery_attempt_at
                else None
            )

            # Calculate issue age
            if first_detected_at:
                age_hours = (now - first_detected_at).total_seconds() / 3600.0
                issue_report["recovery_age_hours"] = round(age_hours, 1)

            # Check for escalation
            escalation_issue_id = issue_state.get("escalation_issue_id")
            if escalation_issue_id:
                report["summary"]["issues_with_escalations"] += 1
                issue_report["escalation_issue_id"] = escalation_issue_id
                issue_report["status"] = "escalated"
            else:
                issue_report["status"] = "in_recovery"

            # Check for recovery loop (repeated attempts in short time)
            if (
                last_recovery_attempt_at
                and (now - last_recovery_attempt_at).total_seconds() < 300
                and recovery_attempts >= 2
            ):
                report["summary"]["issues_stuck_in_loop"] += 1
                issue_report["warning"] = "Rapid recovery attempts detected"

            last_action = issue_state.get("last_action")
            if last_action:
                issue_report["last_action"] = last_action

            scenario_report["issues"].append(issue_report)
            report["issues"].append(issue_report)

        report["scenarios"][scenario_id] = scenario_report

    return report


def fetch_issue_details(issue_id: str) -> dict[str, Any] | None:
    """Fetch issue details from Paperclip API."""
    try:
        api_key = os.environ.get("PAPERCLIP_API_KEY")
        api_url = os.environ.get("PAPERCLIP_API_URL")
        if not api_key or not api_url:
            return None

        with requests.Session() as sess:
            sess.headers.update({"Authorization": f"Bearer {api_key}"})
            resp = sess.get(
                f"{api_url}/api/issues/{issue_id}",
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.debug("Failed to fetch issue details for %s: %s", issue_id, e)
    return None


def generate_markdown_report(report: dict[str, Any]) -> str:
    """Generate human-readable Markdown report."""
    lines = [
        "# PaperClip Stalled Workflow Report",
        "",
        f"**Generated:** {report.get('timestamp', '?')[:19]} UTC",
        "",
    ]

    summary = report.get("summary", {})
    if summary.get("total_issues_in_recovery", 0) == 0:
        lines.append("✅ **No stalled workflows currently in recovery.**")
        return "\n".join(lines)

    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"- **Scenarios tracking issues:** {summary.get('total_scenarios_tracking_issues')}"
    )
    lines.append(
        f"- **Total issues in recovery:** {summary.get('total_issues_in_recovery')}"
    )
    lines.append(
        f"- **Issues escalated:** {summary.get('issues_with_escalations')}"
    )
    lines.append(
        f"- **Issues stuck in loop:** {summary.get('issues_stuck_in_loop')}"
    )
    lines.append("")

    # Group by scenario
    scenarios = report.get("scenarios", {})
    if scenarios:
        lines.append("## By Scenario")
        lines.append("")

        for scenario_id, scenario_data in scenarios.items():
            name = scenario_data.get("scenario_name", scenario_id)
            total = scenario_data.get("total_issues", 0)
            lines.append(f"### {name} ({total} issue(s))")
            lines.append("")

            for issue in scenario_data.get("issues", [])[:10]:
                issue_id = issue.get("issue_id", "?")[:8]
                age = issue.get("recovery_age_hours", "?")
                attempts = issue.get("recovery_attempts", 0)
                status = issue.get("status", "?")
                warning = issue.get("warning", "")

                line = f"- **{issue_id}**: {status}, {attempts} attempt(s), age {age}h"
                if warning:
                    line += f" ⚠️ {warning}"
                lines.append(line)

            if len(scenario_data.get("issues", [])) > 10:
                lines.append(f"- ... and {len(scenario_data.get('issues', [])) - 10} more")

            lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="PaperClip Stalled Workflow Reporter")
    parser.add_argument(
        "--json-report",
        action="store_true",
        help="Output report as JSON",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Filter to specific scenario",
    )

    args = parser.parse_args()

    state = load_recovery_state()
    config = load_config()

    # Filter scenarios if requested
    if args.scenario:
        filtered_state = {
            "scenarios": {
                args.scenario: state.get("scenarios", {}).get(args.scenario, {})
            },
            "last_run_at": state.get("last_run_at"),
        }
        state = filtered_state

    report = analyze_stalled_issues(state, config)

    if args.json_report:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(generate_markdown_report(report))

    logger.info(
        "Stalled workflow report complete: %d issues in recovery",
        report.get("summary", {}).get("total_issues_in_recovery", 0),
    )


if __name__ == "__main__":
    main()
