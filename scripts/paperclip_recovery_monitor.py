#!/usr/bin/env python3
"""PaperClip Recovery Monitor — detects and recovers stalled agent workflows.

Polls the PaperClip API for in_progress issues that match configured recovery
scenarios (exchange API timeout, position mismatch, signal timeout) and executes
source-scoped recovery actions: diagnostic comments, heartbeat invocations,
agent resumption, forced release of orphaned checkouts, and escalation.

Usage:
    python scripts/paperclip_recovery_monitor.py
    python scripts/paperclip_recovery_monitor.py --dry-run
    python scripts/paperclip_recovery_monitor.py --json-summary
    python scripts/paperclip_recovery_monitor.py --scenario exchange_api_timeout
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from touch_index.paperclip_client import _base, _company

MONITOR_LOG = Path.home() / ".paperclip" / "recovery_monitor.log"
RECOVERY_STATE_FILE = Path.home() / ".paperclip" / "recovery_monitor_state.json"
CONFIG_PATH = REPO_ROOT / "scripts" / "paperclip_recovery_actions.json"
MAX_LOG_BYTES = 1 * 1024 * 1024
API_TIMEOUT = 30

RETRY_STRATEGY = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[408, 429, 500, 502, 503, 504],
    allowed_methods=["GET", "PATCH", "POST"],
    raise_on_status=False,
)

MONITOR_LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(MONITOR_LOG),
        logging.StreamHandler() if os.isatty(0) else logging.NullHandler(),
    ],
)
logger = logging.getLogger("recovery_monitor")


def _rotate_log_if_needed() -> None:
    if MONITOR_LOG.exists() and MONITOR_LOG.stat().st_size > MAX_LOG_BYTES:
        bak = MONITOR_LOG.with_suffix(".log.1")
        bak.write_text(MONITOR_LOG.read_text())
        MONITOR_LOG.write_text("")
        logger.info("Rotated recovery monitor log (size exceeded %d bytes)", MAX_LOG_BYTES)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Recovery config not found: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text())


def load_recovery_state() -> dict[str, Any]:
    if RECOVERY_STATE_FILE.exists():
        try:
            return json.loads(RECOVERY_STATE_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            logger.warning("Corrupt recovery state file, resetting")
    return {"scenarios": {}, "last_run_at": None}


def save_recovery_state(state: dict[str, Any]) -> None:
    RECOVERY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECOVERY_STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def issue_age_hours(issue: dict[str, Any]) -> float:
    started = parse_iso(issue.get("startedAt")) or parse_iso(issue.get("createdAt"))
    if not started:
        return 0.0
    return (datetime.now(timezone.utc) - started).total_seconds() / 3600.0


def _http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}",
        "Content-Type": "application/json",
    })
    adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def fetch_in_progress_issues() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    params: dict[str, Any] = {"status": "in_progress", "limit": 100, "offset": 0}
    with _http_session() as sess:
        while True:
            resp = sess.get(
                f"{_base()}/api/companies/{_company()}/issues",
                params=params,
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            page = resp.json()

            items = page if isinstance(page, list) else page.get("items", page if isinstance(page, list) else [])
            if not items:
                break
            results.extend(items)
            if len(items) < params["limit"]:
                break
            params["offset"] += params["limit"]
    return results


def fetch_live_runs() -> list[dict[str, Any]]:
    with _http_session() as sess:
        resp = sess.get(
            f"{_base()}/api/companies/{_company()}/live-runs",
            params={"minCount": "50", "limit": "50"},
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()


def fetch_agent(agent_id: str) -> dict[str, Any] | None:
    with _http_session() as sess:
        resp = sess.get(f"{_base()}/api/agents/{agent_id}", timeout=API_TIMEOUT)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def post_comment(issue_id: str, body: str, dry_run: bool = False) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would post comment on issue %s: %s", issue_id, body[:120])
        return
    with _http_session() as sess:
        resp = sess.post(
            f"{_base()}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        logger.info("Posted recovery comment on issue %s", issue_id)


def invoke_heartbeat(agent_id: str, dry_run: bool = False) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would invoke heartbeat for agent %s", agent_id)
        return
    with _http_session() as sess:
        resp = sess.post(
            f"{_base()}/api/agents/{agent_id}/heartbeat/invoke",
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        logger.info("Invoked heartbeat for agent %s", agent_id)


def resume_agent(agent_id: str, dry_run: bool = False) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would resume agent %s", agent_id)
        return
    with _http_session() as sess:
        resp = sess.post(
            f"{_base()}/api/agents/{agent_id}/resume",
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        logger.info("Resumed agent %s", agent_id)


def force_release_issue(issue_id: str, dry_run: bool = False) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would force-release issue %s", issue_id)
        return
    board_key = os.environ.get("PAPERCLIP_BOARD_API_KEY")
    if not board_key:
        logger.warning("Cannot force-release issue %s: PAPERCLIP_BOARD_API_KEY not set", issue_id)
        return
    with requests.Session() as sess:
        sess.headers.update({
            "Authorization": f"Bearer {board_key}",
            "Content-Type": "application/json",
        })
        resp = sess.post(
            f"{_base()}/api/issues/{issue_id}/admin/force-release",
            timeout=API_TIMEOUT,
        )
        if resp.status_code == 404:
            logger.warning("Force-release: issue %s not found (404)", issue_id)
            return
        resp.raise_for_status()
        logger.info("Force-released issue %s", issue_id)


def create_escalation_issue(
    scenario: dict[str, Any],
    stalled_issue: dict[str, Any],
    company_id: str,
    escalation_agent_id: str,
    project_id: str,
    dry_run: bool = False,
) -> str | None:
    title_prefix = scenario.get("escalation_title_prefix", "[RECOVERY] ")
    title = f"{title_prefix}{stalled_issue.get('identifier', '?')} — {stalled_issue.get('title', 'Unknown')[:80]}"
    body = (
        f"## Auto-escalation: {scenario.get('name', 'Unknown scenario')}\n\n"
        f"**Stalled issue:** [{stalled_issue.get('identifier', '?')}](/{company_id[:8]}/issues/{stalled_issue.get('identifier', '?')})\n"
        f"**Assignee:** {stalled_issue.get('assigneeAgentId', 'unknown')}\n"
        f"**Started at:** {stalled_issue.get('startedAt', 'unknown')}\n"
        f"**Scenario:** {scenario.get('description', '')}\n\n"
        f"Recovery monitor detected this issue is stalled. Please investigate and take recovery action."
    )
    if dry_run:
        logger.info("[DRY-RUN] Would create escalation issue: %s", title)
        return None
    with _http_session() as sess:
        resp = sess.post(
            f"{_base()}/api/companies/{company_id}/issues",
            json={
                "title": title[:200],
                "description": body,
                "assigneeAgentId": escalation_agent_id,
                "projectId": project_id,
                "parentId": stalled_issue.get("parentId"),
                "blockedByIssueIds": [stalled_issue["id"]],
                "priority": "high",
                "status": "todo",
            },
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        created = resp.json()
        logger.info("Created escalation issue %s for stalled %s", created.get("identifier"), stalled_issue.get("identifier"))
        return created.get("id")


def get_agent_ids_for_scopes(
    config: dict[str, Any],
    scenario: dict[str, Any],
) -> set[str]:
    scope_map = config.get("agent_scope_map", {})
    agent_ids: set[str] = set()
    for scope_name in scenario.get("source_scope", {}).get("agent_scopes", []):
        agent_ids.update(scope_map.get(scope_name, []))
    return agent_ids


def issue_matches_keywords(issue: dict[str, Any], keywords: list[str]) -> bool:
    if not keywords:
        return True
    combined = f"{issue.get('title', '')} {issue.get('description', '')}".lower()
    return any(kw.lower() in combined for kw in keywords)


def issue_matches_scenario(
    issue: dict[str, Any],
    scenario: dict[str, Any],
    config: dict[str, Any],
    live_runs: list[dict[str, Any]],
) -> bool:
    if not scenario.get("enabled", True):
        return False

    detection = scenario.get("detection", {})
    source_scope = scenario.get("source_scope", {})

    if issue.get("status") != detection.get("status", "in_progress"):
        return False

    age_h = issue_age_hours(issue)
    min_age = detection.get("min_age_hours", 0)
    max_age = detection.get("max_age_hours", 999)
    if age_h < min_age or age_h > max_age:
        return False

    scoped_agents = get_agent_ids_for_scopes(config, scenario)
    if scoped_agents and issue.get("assigneeAgentId") not in scoped_agents:
        return False

    keywords = source_scope.get("issue_keywords", [])
    if keywords and not issue_matches_keywords(issue, keywords):
        return False

    if detection.get("check_live_runs", False):
        silence_levels = detection.get("run_silence_levels", [])
        if silence_levels:
            issue_runs = [
                r for r in live_runs
                if r.get("issueId") == issue["id"]
            ]
            if issue_runs:
                has_silent_run = any(
                    r.get("outputSilence", {}).get("level") in silence_levels
                    for r in issue_runs
                )
                if not has_silent_run:
                    return False

    return True


def is_in_cooldown(
    recovery_state: dict[str, Any],
    issue_id: str,
    scenario_id: str,
    cooldown_minutes: int,
) -> bool:
    scenario_state = recovery_state.get("scenarios", {}).get(scenario_id, {})
    issue_state = scenario_state.get(issue_id)
    if not issue_state:
        return False
    last_attempt = parse_iso(issue_state.get("last_recovery_attempt_at"))
    if not last_attempt:
        return False
    elapsed = (datetime.now(timezone.utc) - last_attempt).total_seconds() / 60.0
    return elapsed < cooldown_minutes


def update_recovery_state(
    recovery_state: dict[str, Any],
    issue_id: str,
    scenario_id: str,
    action: str,
    escalation_issue_id: str | None = None,
) -> None:
    recovery_state.setdefault("scenarios", {}).setdefault(scenario_id, {})
    entry = recovery_state["scenarios"][scenario_id].get(issue_id, {
        "recovery_attempts": 0,
        "first_detected_at": datetime.now(timezone.utc).isoformat(),
    })
    entry["last_recovery_attempt_at"] = datetime.now(timezone.utc).isoformat()
    entry["recovery_attempts"] = entry.get("recovery_attempts", 0) + 1
    entry["last_action"] = action
    if escalation_issue_id:
        entry["escalation_issue_id"] = escalation_issue_id
    recovery_state["scenarios"][scenario_id][issue_id] = entry
    recovery_state["last_run_at"] = datetime.now(timezone.utc).isoformat()


def execute_recovery(
    scenario: dict[str, Any],
    issue: dict[str, Any],
    config: dict[str, Any],
    recovery_state: dict[str, Any],
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    scenario_id = scenario["id"]
    issue_id = issue["id"]
    company_id = config["company_id"]
    project_id = config["defaults"]["alert_project_id"]
    cooldown = config["defaults"]["recovery_cooldown_minutes"]
    max_attempts = config["defaults"]["max_recovery_attempts"]

    if is_in_cooldown(recovery_state, issue_id, scenario_id, cooldown):
        logger.info("Issue %s scenario %s in cooldown, skipping", issue.get("identifier"), scenario_id)
        return []

    results: list[dict[str, Any]] = []
    actions = scenario.get("recovery_actions", [])

    for action_def in sorted(actions, key=lambda a: a.get("order", 99)):
        action_type = action_def["action"]
        escalation_id = None

        try:
            if action_type == "add_comment":
                agent_name = issue.get("assigneeAgentId", "assignee")[:8]
                body = (
                    f"## [Recovery Monitor] Workflow appears stalled\n\n"
                    f"Scenario: **{scenario['name']}**\n"
                    f"Issue has been `in_progress` for {issue_age_hours(issue):.1f}h.\n"
                    f"Action: {action_def.get('description', 'Diagnostic check')}\n\n"
                    f"Recovery monitor is attempting auto-recovery. "
                    f"Please resume work from the last known good state."
                )
                post_comment(issue_id, body, dry_run)

            elif action_type == "invoke_heartbeat":
                agent_id = issue.get("assigneeAgentId")
                if agent_id:
                    invoke_heartbeat(agent_id, dry_run)

            elif action_type == "resume_agent":
                agent_id = issue.get("assigneeAgentId")
                if agent_id:
                    agent = fetch_agent(agent_id)
                    if agent and agent.get("status") == "paused":
                        resume_agent(agent_id, dry_run)

            elif action_type == "force_release":
                force_release_issue(issue_id, dry_run)

            elif action_type == "create_escalation":
                esc_agent = action_def.get("escalation_agent_id") or config["defaults"]["escalation_agent_id"]
                escalation_id = create_escalation_issue(
                    action_def, issue, company_id, esc_agent, project_id, dry_run,
                )

            results.append({
                "action": action_type,
                "issue": issue.get("identifier"),
                "dry_run": dry_run,
                "escalation_issue_id": escalation_id,
            })

            update_recovery_state(recovery_state, issue_id, scenario_id, action_type, escalation_id)

        except Exception as exc:
            logger.error(
                "Recovery action %s failed for issue %s: %s",
                action_type, issue.get("identifier"), exc,
            )
            results.append({
                "action": action_type,
                "issue": issue.get("identifier"),
                "error": str(exc),
            })

    return results


def run_monitor(
    config: dict[str, Any],
    recovery_state: dict[str, Any],
    dry_run: bool = False,
    target_scenario: str | None = None,
) -> dict[str, Any]:
    _rotate_log_if_needed()

    logger.info("Recovery monitor starting%s", " (dry-run)" if dry_run else "")
    now = datetime.now(timezone.utc)

    try:
        issues = fetch_in_progress_issues()
        logger.info("Fetched %d in_progress issues", len(issues))
    except Exception as exc:
        logger.error("Failed to fetch in_progress issues: %s", exc)
        return {"error": str(exc), "timestamp": now.isoformat()}

    live_runs: list[dict[str, Any]] = []
    try:
        live_runs = fetch_live_runs()
        logger.info("Fetched %d live runs", len(live_runs))
    except Exception as exc:
        logger.warning("Failed to fetch live runs (non-fatal): %s", exc)

    scenarios = config.get("recovery_scenarios", [])
    if target_scenario:
        scenarios = [s for s in scenarios if s["id"] == target_scenario]
        if not scenarios:
            logger.error("Target scenario %s not found in config", target_scenario)
            return {"error": f"Scenario {target_scenario} not found", "timestamp": now.isoformat()}

    summary: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "dry_run": dry_run,
        "issues_scanned": len(issues),
        "scenarios_checked": len(scenarios),
        "matches": {},
        "actions_taken": [],
    }

    for scenario in scenarios:
        scenario_id = scenario["id"]
        matched_issues = [
            i for i in issues
            if issue_matches_scenario(i, scenario, config, live_runs)
        ]
        summary["matches"][scenario_id] = len(matched_issues)

        if matched_issues:
            logger.info(
                "Scenario %s: %d matched issues (%s)",
                scenario_id,
                len(matched_issues),
                ", ".join(i.get("identifier", "?") for i in matched_issues[:5]),
            )

        min_batch = scenario.get("detection", {}).get("min_issues_for_batch_alert", 1)
        if len(matched_issues) < min_batch and min_batch > 1:
            logger.info(
                "Scenario %s: %d matches below batch threshold %d, skipping",
                scenario_id, len(matched_issues), min_batch,
            )
            continue

        for issue in matched_issues:
            results = execute_recovery(scenario, issue, config, recovery_state, dry_run)
            summary["actions_taken"].extend(results)

    save_recovery_state(recovery_state)

    total_actions = len(summary["actions_taken"])
    logger.info(
        "Recovery monitor complete: %d issues scanned, %d scenarios, %d actions taken",
        len(issues), len(scenarios), total_actions,
    )

    return summary


def cmd_run(args: argparse.Namespace) -> None:
    config = load_config()
    recovery_state = load_recovery_state()
    summary = run_monitor(
        config,
        recovery_state,
        dry_run=args.dry_run,
        target_scenario=args.scenario,
    )
    if args.json_summary:
        print(json.dumps(summary, indent=2, default=str))
    if summary.get("error"):
        sys.exit(1)


def cmd_matches(args: argparse.Namespace) -> None:
    config = load_config()
    recovery_state = load_recovery_state()
    try:
        issues = fetch_in_progress_issues()
        live_runs = fetch_live_runs()
    except Exception as exc:
        logger.error("Failed to fetch data: %s", exc)
        sys.exit(1)

    scenarios = config.get("recovery_scenarios", [])
    if args.scenario:
        scenarios = [s for s in scenarios if s["id"] == args.scenario]

    output: list[dict[str, Any]] = []
    for s in scenarios:
        matched = [
            {
                "identifier": i.get("identifier"),
                "title": i.get("title"),
                "assignee": i.get("assigneeAgentId", "")[:8],
                "age_hours": round(issue_age_hours(i), 1),
            }
            for i in issues
            if issue_matches_scenario(i, s, config, live_runs)
        ]
        output.append({"scenario": s["id"], "name": s["name"], "matched": len(matched), "issues": matched})

    print(json.dumps(output, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="PaperClip Recovery Monitor")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run recovery monitor")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--json-summary", action="store_true")
    run_parser.add_argument("--scenario", type=str, default=None)

    match_parser = sub.add_parser("matches", help="Show scenario matches without taking action")
    match_parser.add_argument("--scenario", type=str, default=None)

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "matches":
        cmd_matches(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
