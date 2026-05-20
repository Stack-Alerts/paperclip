#!/usr/bin/env python3
"""Run PaperClip Recovery Monitor Routine and report results to BTCAAAAA-26508.

This routine:
1. Checks for stalled workflows using `matches` command
2. If any matches found, previews recovery actions with `--dry-run`
3. Posts a summary comment to BTCAAAAA-26508

Usage:
    python scripts/run_recovery_monitor_routine.py
"""

from __future__ import annotations

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("recovery_routine")

MONITOR_SCRIPT = REPO_ROOT / "scripts" / "paperclip_recovery_monitor.py"
TRACKING_ISSUE = "BTCAAAAA-26508"
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


def run_matches_check() -> dict[str, Any]:
    """Run recovery monitor matches command and return results."""
    try:
        result = subprocess.run(
            [sys.executable, str(MONITOR_SCRIPT), "matches"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            logger.error("Matches check failed: %s", result.stderr)
            return {"error": result.stderr, "returncode": result.returncode}
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse matches output: %s", exc)
        return {"error": f"JSON parse error: {exc}"}
    except subprocess.TimeoutExpired:
        logger.error("Matches check timed out")
        return {"error": "Command timeout"}
    except Exception as exc:
        logger.error("Matches check failed: %s", exc)
        return {"error": str(exc)}


def run_dry_run_check() -> dict[str, Any]:
    """Run recovery monitor with --dry-run and return results."""
    try:
        result = subprocess.run(
            [sys.executable, str(MONITOR_SCRIPT), "run", "--dry-run", "--json-summary"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            logger.error("Dry-run check failed: %s", result.stderr)
            return {"error": result.stderr, "returncode": result.returncode}
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse dry-run output: %s", exc)
        return {"error": f"JSON parse error: {exc}"}
    except subprocess.TimeoutExpired:
        logger.error("Dry-run check timed out")
        return {"error": "Command timeout"}
    except Exception as exc:
        logger.error("Dry-run check failed: %s", exc)
        return {"error": str(exc)}


def has_any_matches(matches_result: dict[str, Any]) -> bool:
    """Check if there are any matches in the results."""
    if "error" in matches_result:
        return False
    for scenario_data in matches_result:
        if scenario_data.get("matched", 0) > 0:
            return True
    return False


def format_matches_report(matches_result: dict[str, Any], dry_run_result: dict[str, Any] | None = None) -> str:
    """Format the matches and dry-run results into a readable report."""
    lines = [
        "## Recovery Monitor Routine Report",
        "",
        f"**Time:** {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    if "error" in matches_result:
        lines.extend([
            "### Error",
            f"```\n{matches_result['error']}\n```",
        ])
        return "\n".join(lines)

    # Count total matches
    total_matches = sum(s.get("matched", 0) for s in matches_result)
    lines.append(f"### Scenarios Checked")
    lines.append(f"**Total matches found:** {total_matches}")
    lines.append("")

    # List matches by scenario
    if total_matches > 0:
        lines.append("### Matched Issues by Scenario")
        for scenario_data in matches_result:
            scenario_id = scenario_data.get("scenario", "unknown")
            scenario_name = scenario_data.get("name", "Unknown Scenario")
            matched_count = scenario_data.get("matched", 0)

            if matched_count > 0:
                lines.append(f"- **{scenario_name}** (`{scenario_id}`): {matched_count} issue(s)")
                issues = scenario_data.get("issues", [])
                for issue in issues[:5]:  # Show first 5
                    identifier = issue.get("identifier", "?")
                    title = issue.get("title", "Unknown")
                    age = issue.get("age_hours", 0)
                    lines.append(f"  - `{identifier}`: {title[:60]} ({age:.1f}h)")
                if len(issues) > 5:
                    lines.append(f"  - ... and {len(issues) - 5} more")
        lines.append("")

    # Include dry-run preview if available
    if dry_run_result and "error" not in dry_run_result:
        actions = dry_run_result.get("actions_taken", [])
        if actions:
            lines.append("### Dry-Run Preview")
            lines.append(f"**Actions that would be taken:** {len(actions)}")
            for action in actions[:10]:
                action_type = action.get("action", "unknown")
                issue = action.get("issue", "?")
                lines.append(f"- {action_type} on {issue}")
            if len(actions) > 10:
                lines.append(f"- ... and {len(actions) - 10} more")
    elif dry_run_result and "error" in dry_run_result:
        lines.append("### Dry-Run Error")
        lines.append(f"```\n{dry_run_result['error']}\n```")

    return "\n".join(lines)


def post_comment(issue_id: str, body: str) -> bool:
    """Post a comment to an issue."""
    try:
        with _http_session() as sess:
            resp = sess.post(
                f"{_base()}/api/issues/{issue_id}/comments",
                json={"body": body},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            logger.info("Posted recovery routine report to issue %s", issue_id)
            return True
    except Exception as exc:
        logger.error("Failed to post comment: %s", exc)
        return False


def main() -> None:
    logger.info("Starting recovery monitor routine")

    # Step 1: Check for matches
    logger.info("Checking for stalled workflows...")
    matches_result = run_matches_check()

    if "error" in matches_result:
        logger.error("Matches check failed, will still report to tracking issue")
        report = format_matches_report(matches_result)
        post_comment(TRACKING_ISSUE, report)
        sys.exit(1)

    # Step 2: Check if any matches found
    has_matches = has_any_matches(matches_result)
    logger.info("Matches check complete: %s", "matches found" if has_matches else "no matches")

    dry_run_result = None
    if has_matches:
        # Step 3: Run dry-run to preview actions
        logger.info("Running dry-run to preview recovery actions...")
        dry_run_result = run_dry_run_check()

    # Step 4: Report results to tracking issue
    report = format_matches_report(matches_result, dry_run_result)
    logger.info("Posting report to %s", TRACKING_ISSUE)
    if post_comment(TRACKING_ISSUE, report):
        logger.info("Recovery monitor routine completed successfully")
    else:
        logger.error("Recovery monitor routine completed but failed to post report")
        sys.exit(1)


if __name__ == "__main__":
    main()
