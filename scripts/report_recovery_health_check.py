#!/usr/bin/env python3
"""Report Recovery Monitor Health Check results to Paperclip via routine API.

This script runs the hourly health check and reports findings to Paperclip,
including health status, configuration validity, state integrity, and stalled
workflows.

Usage:
    python scripts/report_recovery_health_check.py
    python scripts/report_recovery_health_check.py --routine-id <routine_id>
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from touch_index.paperclip_client import _base, _company

MONITOR_SCRIPT = REPO_ROOT / "scripts" / "paperclip_recovery_monitor.py"
HEALTH_CHECK_SCRIPT = REPO_ROOT / "scripts" / "paperclip_recovery_health_check.py"
STALLED_REPORTER_SCRIPT = REPO_ROOT / "scripts" / "paperclip_stalled_workflow_reporter.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("recovery_health_reporter")

API_TIMEOUT = 30


def _http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}",
        "Content-Type": "application/json",
    })
    adapter = HTTPAdapter(max_retries=Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "PATCH", "POST"],
        raise_on_status=False,
    ))
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def run_health_check() -> dict[str, Any]:
    """Run recovery monitor health check and return results."""
    try:
        result = subprocess.run(
            [sys.executable, str(HEALTH_CHECK_SCRIPT), "--json-report"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            logger.error("Health check failed: %s", result.stderr)
            return {"error": result.stderr, "returncode": result.returncode}
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse health check output: %s", exc)
        return {"error": f"JSON parse error: {exc}"}
    except subprocess.TimeoutExpired:
        logger.error("Health check timed out")
        return {"error": "Command timeout"}
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return {"error": str(exc)}


def run_stalled_workflows_check() -> dict[str, Any]:
    """Run stalled workflows reporter and return results."""
    try:
        result = subprocess.run(
            [sys.executable, str(STALLED_REPORTER_SCRIPT), "--json-report"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            logger.error("Stalled workflows check failed: %s", result.stderr)
            return {"error": result.stderr, "returncode": result.returncode}
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse stalled workflows output: %s", exc)
        return {"error": f"JSON parse error: {exc}"}
    except subprocess.TimeoutExpired:
        logger.error("Stalled workflows check timed out")
        return {"error": "Command timeout"}
    except Exception as exc:
        logger.error("Stalled workflows check failed: %s", exc)
        return {"error": str(exc)}


def format_report(health_result: dict[str, Any], stalled_result: dict[str, Any]) -> str:
    """Format health check and stalled workflows results into markdown."""
    lines = [
        "## Recovery Monitor Health Check Report",
        "",
        f"**Time:** {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    # Health check section
    if "error" in health_result:
        lines.extend([
            "### 🔴 Health Check Error",
            f"```\n{health_result['error']}\n```",
        ])
    else:
        overall = health_result.get("overall_status", "unknown").upper()
        emoji = {
            "HEALTHY": "✅",
            "DEGRADED": "⚠️",
            "UNHEALTHY": "🔴",
        }.get(overall, "❓")

        lines.append(f"### {emoji} Health Status: {overall}")
        lines.append("")

        checks = health_result.get("checks", {})
        if checks:
            lines.append("| Check | Status | Details |")
            lines.append("|-------|--------|---------|")
            for check_name, check_info in checks.items():
                status = check_info.get("status", "?").upper()
                details = check_info.get("details", {})
                detail_str = ", ".join([f"{k}={v}" for k, v in list(details.items())[:2]])[:60]
                if not detail_str:
                    detail_str = check_info.get("message", "")[:60]
                lines.append(f"| {check_name} | {status} | {detail_str} |")
            lines.append("")

        alerts = health_result.get("alerts", [])
        if alerts:
            lines.append("### 🚨 Alerts")
            for alert in alerts:
                lines.append(f"- {alert}")
            lines.append("")

        warnings = health_result.get("warnings", [])
        if warnings:
            lines.append("### ⚠️ Warnings")
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")

    # Stalled workflows section
    if "error" in stalled_result:
        lines.extend([
            "### Stalled Workflows Error",
            f"```\n{stalled_result['error']}\n```",
        ])
    else:
        summary = stalled_result.get("summary", {})
        total_issues = summary.get("total_issues_in_recovery", 0)

        lines.append("### Stalled Workflows")
        lines.append("")

        if total_issues == 0:
            lines.append("✅ No stalled workflows currently in recovery.")
        else:
            lines.append(f"**Issues in recovery:** {total_issues}")
            lines.append(f"**Escalations:** {summary.get('issues_with_escalations', 0)}")
            lines.append(f"**Recovery loops:** {summary.get('issues_stuck_in_loop', 0)}")
            lines.append("")

            scenarios = stalled_result.get("scenarios", {})
            if scenarios:
                lines.append("**By scenario:**")
                for scenario_id, scenario_data in scenarios.items():
                    name = scenario_data.get("scenario_name", scenario_id)
                    count = scenario_data.get("total_issues", 0)
                    if count > 0:
                        lines.append(f"- {name}: {count} issue(s)")

    return "\n".join(lines)


def get_routine_by_name(routine_name: str) -> dict[str, Any] | None:
    """Fetch routine ID by name."""
    try:
        with _http_session() as sess:
            resp = sess.get(
                f"{_base()}/api/routines",
                params={"name": routine_name},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            elif isinstance(data, dict) and "items" in data and len(data["items"]) > 0:
                return data["items"][0]
    except Exception as exc:
        logger.debug("Failed to fetch routine by name: %s", exc)
    return None


def report_to_routine(routine_id: str, report_body: str) -> bool:
    """Report health check results to a Paperclip routine."""
    try:
        with _http_session() as sess:
            resp = sess.patch(
                f"{_base()}/api/routines/{routine_id}",
                json={"status_message": report_body},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            logger.info("Posted health check report to routine %s", routine_id)
            return True
    except Exception as exc:
        logger.error("Failed to post health check report to routine: %s", exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report Recovery Monitor Health Check to Paperclip"
    )
    parser.add_argument(
        "--routine-id",
        type=str,
        default=None,
        help="Routine ID to report results to (default: auto-discover)",
    )

    args = parser.parse_args()

    logger.info("Starting recovery health check report")

    # Run checks
    logger.info("Running health check...")
    health_result = run_health_check()

    logger.info("Checking stalled workflows...")
    stalled_result = run_stalled_workflows_check()

    # Format report
    report = format_report(health_result, stalled_result)
    logger.info("Report formatted:\n%s", report)

    # Try to report to routine
    routine_id = args.routine_id
    if not routine_id:
        logger.info("Attempting to discover routine...")
        routine = get_routine_by_name("Recovery Monitor Health Check")
        if routine:
            routine_id = routine.get("id")
            logger.info("Discovered routine ID: %s", routine_id)

    if routine_id:
        if report_to_routine(routine_id, report):
            logger.info("Successfully reported health check to routine")
        else:
            logger.error("Failed to report to routine, but check completed successfully")
    else:
        logger.info("No routine ID found, skipping routine report")

    # Print report to stdout
    print(report)

    # Exit with failure if health check failed
    if health_result.get("overall_status") not in ("healthy", None) and "error" not in health_result:
        sys.exit(1)


if __name__ == "__main__":
    main()
