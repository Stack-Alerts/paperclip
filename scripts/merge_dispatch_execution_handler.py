#!/usr/bin/env python3
"""Merge-dispatch routine execution handler.

Runs as a standalone script (via systemd timer) independent of the Paperclip
agent's availability. When the merge-dispatch routine creates an execution issue,
this handler picks it up, runs the merge dispatch logic, and marks the issue done.

Prevents the 2+ hour outages caused by agent rate-limit failures (BTCAAAAA-32757,
BTCAAAAA-32759).

Usage:
    python3 scripts/merge_dispatch_execution_handler.py
    python3 scripts/merge_dispatch_execution_handler.py --dry-run

Requires (from .env or environment):
    PAPERCLIP_API_KEY  - persistent agent API key (not the short-lived JWT)
    PAPERCLIP_API_URL  - Paperclip instance URL
    PAPERCLIP_COMPANY_ID - company UUID
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Load .env first so env vars are available before any other import
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_FILE, override=False)

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("merge_dispatch_execution_handler")

# The Paperclip merge-dispatch routine ID (Phase 4a).
MERGE_DISPATCH_ROUTINE_ID = "908726dc-c9be-4b0f-91fc-f990ffbfcf5c"

# The AutomationEngineer agent ID (the routine's assignee).
AUTOMATION_ENGINEER_AGENT_ID = "2b9152a6-07f6-4ae9-87fa-c824012c9ff6"

REPO_ROOT = Path(__file__).resolve().parent.parent


def _api_url() -> str:
    url = os.environ.get("PAPERCLIP_API_URL", "")
    if not url:
        raise RuntimeError("PAPERCLIP_API_URL not set")
    return url.rstrip("/")


def _company_id() -> str:
    cid = os.environ.get("PAPERCLIP_COMPANY_ID", "")
    if not cid:
        raise RuntimeError("PAPERCLIP_COMPANY_ID not set")
    return cid


def _api_key() -> str:
    key = os.environ.get("PAPERCLIP_API_KEY", "")
    if not key:
        raise RuntimeError("PAPERCLIP_API_KEY not set — check .env")
    return key


def _http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    })
    adapter = HTTPAdapter(max_retries=Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "PATCH", "POST"],
        raise_on_status=False,
    ))
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def get_routine_active_issue() -> dict | None:
    """Return the current in_progress or todo execution issue for the merge-dispatch routine.

    Two-pass approach:
    1. Check the routine's activeIssue field (fast path)
    2. Query issues by originId and status (fallback if activeIssue is None but issues exist)
    """
    api = _api_url()
    company = _company_id()

    with _http_session() as sess:
        # Pass 1: get routines list, find our routine's activeIssue
        resp = sess.get(f"{api}/api/companies/{company}/routines", timeout=30)
        if resp.status_code == 200:
            routines = resp.json()
            if isinstance(routines, list):
                for routine in routines:
                    if routine.get("id") == MERGE_DISPATCH_ROUTINE_ID:
                        status = routine.get("status")
                        if status in ("paused", "archived"):
                            logger.info("Merge-dispatch routine is %s — nothing to process", status)
                            return None
                        active = routine.get("activeIssue")
                        if active:
                            issue_status = active.get("status")
                            if issue_status in ("in_progress", "todo"):
                                logger.info(
                                    "Found active execution issue %s (status: %s)",
                                    active.get("identifier"),
                                    issue_status,
                                )
                                return active
                            else:
                                logger.info(
                                    "Active issue %s has status %s — skipping",
                                    active.get("identifier"),
                                    issue_status,
                                )
                                return None
                        break

        # Pass 2: query issues by originKind + status (catches recently created issues
        # that may not yet appear as activeIssue)
        resp = sess.get(
            f"{api}/api/companies/{company}/issues",
            params={
                "assigneeAgentId": AUTOMATION_ENGINEER_AGENT_ID,
                "status": "in_progress,todo",
                "limit": 50,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            logger.error("Failed to query issues: %s %s", resp.status_code, resp.text[:200])
            return None

        data = resp.json()
        issues = data.get("issues", data) if isinstance(data, dict) else data
        for issue in issues:
            if issue.get("originKind") == "routine_execution" and \
               issue.get("originId") == MERGE_DISPATCH_ROUTINE_ID:
                logger.info(
                    "Found execution issue %s via query (status: %s)",
                    issue.get("identifier"),
                    issue.get("status"),
                )
                return issue

    logger.info("No pending merge-dispatch execution issue found")
    return None


def get_full_issue(issue_id: str) -> dict | None:
    """Fetch full issue details by ID."""
    with _http_session() as sess:
        resp = sess.get(f"{_api_url()}/api/issues/{issue_id}", timeout=30)
        if resp.status_code == 200:
            return resp.json()
        logger.error("Failed to fetch issue %s: %s", issue_id, resp.status_code)
        return None


def checkout_execution_issue(issue_id: str) -> bool:
    """Check out the execution issue for processing."""
    with _http_session() as sess:
        payload = {
            "agentId": AUTOMATION_ENGINEER_AGENT_ID,
            "expectedStatuses": ["todo", "in_progress"],
        }
        resp = sess.post(
            f"{_api_url()}/api/issues/{issue_id}/checkout",
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            logger.info("Checked out execution issue %s", issue_id)
            return True
        if resp.status_code == 409:
            logger.warning("Issue %s already checked out by another runner", issue_id)
            return False
        logger.error("Checkout failed for %s: %s %s", issue_id, resp.status_code, resp.text[:200])
        return False


def update_issue(issue_id: str, status: str, comment: str) -> bool:
    """PATCH issue status with a comment."""
    with _http_session() as sess:
        resp = sess.patch(
            f"{_api_url()}/api/issues/{issue_id}",
            json={"status": status, "comment": comment},
            timeout=30,
        )
        if resp.status_code in (200, 204):
            logger.info("Updated issue %s → %s", issue_id, status)
            return True
        logger.error(
            "Failed to update issue %s to %s: %s %s",
            issue_id, status, resp.status_code, resp.text[:200],
        )
        return False


def add_comment(issue_id: str, body: str) -> bool:
    """Add a markdown comment to the issue."""
    with _http_session() as sess:
        resp = sess.post(
            f"{_api_url()}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            logger.info("Added comment to issue %s", issue_id)
            return True
        logger.error("Failed to add comment to %s: %s", issue_id, resp.status_code)
        return False


def run_merge_dispatch(dry_run: bool = False) -> dict:
    """Run merge_dispatch_routine.py and return its parsed output."""
    script = REPO_ROOT / "scripts" / "merge_dispatch_routine.py"
    if not script.exists():
        return {"error": f"Script not found: {script}"}

    if dry_run:
        logger.info("[DRY RUN] Would run: python3 %s", script)
        return {"dry_run": True, "summary": {"merged": 0, "skipped": 0, "failed": 0, "errors": 0}}

    env = {**os.environ}

    try:
        logger.info("Running merge dispatch routine...")
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=300,  # 5-minute timeout
            cwd=str(REPO_ROOT),
            env=env,
        )
        if result.returncode != 0:
            logger.error("Merge dispatch exited %d: %s", result.returncode, result.stderr[-500:])
            return {"error": f"exit_code_{result.returncode}", "stderr": result.stderr[-500:]}

        stdout = result.stdout.strip()
        if stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return {"raw_output": stdout[-1000:]}

        return {"no_output": True}

    except subprocess.TimeoutExpired:
        logger.error("Merge dispatch timed out after 300s")
        return {"error": "timeout"}
    except Exception as exc:
        logger.error("Merge dispatch failed: %s", exc)
        return {"error": str(exc)}


def process_execution_issue(issue: dict, dry_run: bool = False) -> bool:
    """Process a single merge-dispatch execution issue end-to-end.

    Returns True if the issue was handled (either successfully or with a recorded failure).
    """
    issue_id = issue.get("id", "")
    identifier = issue.get("identifier", issue_id)
    logger.info("Processing execution issue %s", identifier)

    if not dry_run:
        if not checkout_execution_issue(issue_id):
            return False

    result = run_merge_dispatch(dry_run=dry_run)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if "error" in result:
        error_msg = result["error"]
        logger.error("Merge dispatch failed for %s: %s", identifier, error_msg)
        comment = f"""## Merge Dispatch — Handler Error

**Timestamp:** {timestamp}
**Error:** `{error_msg}`

The standalone execution handler (`merge_dispatch_execution_handler.py`) encountered
an error. Manual review required.

Stderr excerpt:
```
{result.get('stderr', '')}
```
"""
        if not dry_run:
            add_comment(issue_id, comment)
            update_issue(issue_id, "blocked",
                         f"Merge dispatch handler error: {error_msg}")
        return False

    summary = result.get("summary", {})
    merged = summary.get("merged", 0)
    skipped = summary.get("skipped", 0)
    failed = summary.get("failed", 0)
    errors = summary.get("errors", 0)
    total = result.get("issues_processed", 0)

    logger.info(
        "Merge dispatch complete: %d processed, %d merged, %d skipped, %d failed, %d errors",
        total, merged, skipped, failed, errors,
    )

    comment = f"""## Merge Dispatch — Execution Complete

**Timestamp:** {timestamp}
**Issues processed:** {total}
**Merged:** {merged}
**Skipped (push lag / already merged):** {skipped}
**Failed:** {failed}
**Errors:** {errors}

Handler: `scripts/merge_dispatch_execution_handler.py` (standalone daemon, independent of Claude rate limits)
"""
    if dry_run:
        logger.info("[DRY RUN] Would post comment and mark issue done")
        logger.info("Comment:\n%s", comment)
        return True

    add_comment(issue_id, comment)

    if failed > 0 or errors > 0:
        update_issue(
            issue_id,
            "done",
            f"Dispatch complete with {failed} failed, {errors} errors — see comment for details",
        )
    else:
        update_issue(issue_id, "done", f"Merge dispatch complete: {merged} merged, {skipped} skipped")

    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Standalone merge-dispatch routine execution handler",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for pending issues and log what would happen, but don't run the dispatch",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(
        "Merge-dispatch execution handler starting (dry_run=%s)",
        args.dry_run,
    )

    try:
        issue = get_routine_active_issue()
    except RuntimeError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    if issue is None:
        logger.info("No pending execution issue — exiting")
        return 0

    full_issue = get_full_issue(issue.get("id", ""))
    if full_issue:
        issue = full_issue

    handled = process_execution_issue(issue, dry_run=args.dry_run)
    return 0 if handled else 1


if __name__ == "__main__":
    sys.exit(main())
