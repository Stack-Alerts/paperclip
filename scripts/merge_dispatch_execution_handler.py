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

# Upstream repository for `gh` CLI calls (Gap 2 — BTCAAAAA-38470).
REPO_OWNER = "Stack-Alerts"
REPO_NAME = "BTC-Trade-Engine-PaperClip"
REPO_FULL = f"{REPO_OWNER}/{REPO_NAME}"

REPO_ROOT = Path(__file__).resolve().parent.parent


class MergeVerificationFailed(Exception):
    """Raised when post-merge verification sees upstream state != MERGED.

    BTCAAAAA-38470 Gap 2 — closes the local-vs-upstream merge-state divergence
    documented in BTC-38125. `merge_pr()` returns success on a 200 response, but
    the upstream view can lag (webhook delay, wrong-target fork, insufficient
    token scope). The routine catches this exception and escalates with the
    actual upstream view as a structured payload instead of trusting the local
    log line.

    Attributes:
        pr_number: The PR number that failed verification.
        upstream_view: The dict returned by `gh pr view --json` showing the
            actual upstream state (state, mergedAt, mergeCommit, url, etc.).
        message: Human-readable description of the failure.
    """

    def __init__(self, pr_number: int, upstream_view: dict, message: str) -> None:
        self.pr_number = pr_number
        self.upstream_view = upstream_view
        super().__init__(message)


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


def _run_gh_pr_view(pr_number: int, timeout: int = 15) -> dict | None:
    """Run `gh pr view <N> --json state,mergedAt,mergeCommit,url` and parse.

    Returns the parsed JSON dict on success (exit 0, valid JSON). Returns None
    on any failure (gh not on PATH, non-zero exit, invalid JSON, network
    error). Caller decides whether a None means "retry" or "escalate".
    """
    import shutil
    import subprocess

    gh = shutil.which("gh")
    if gh is None:
        logger.error("gh CLI not found on PATH — cannot verify PR state")
        return None

    try:
        proc = subprocess.run(
            [
                gh, "pr", "view", str(pr_number),
                "--repo", REPO_FULL,
                "--json", "state,mergedAt,mergeCommit,url,headRefName,number",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        logger.error("gh pr view %s timed out after %ss", pr_number, timeout)
        return None
    except Exception as exc:
        logger.error("gh pr view %s failed: %s", pr_number, exc)
        return None

    if proc.returncode != 0:
        stderr_excerpt = (proc.stderr or "")[:200].strip()
        logger.warning(
            "gh pr view %s returned rc=%d: %s",
            pr_number, proc.returncode, stderr_excerpt,
        )
        return None

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        logger.error("gh pr view %s returned invalid JSON: %s", pr_number, exc)
        return None


def verify_pr_merged(pr_number: int) -> dict:
    """Confirm upstream reports PR as MERGED. Sleeps 5s, then re-queries.

    Raises:
        MergeVerificationFailed: if the upstream view is missing or its
            `state` field is not exactly `MERGED`. The exception carries the
            full upstream view so the routine can post a structured escalation
            comment instead of trusting the local log line.

    Returns:
        The upstream view dict (state=MERGED) on success.
    """
    logger.info("Post-merge verification: sleeping 5s before re-querying PR %s", pr_number)
    import time
    time.sleep(5)

    upstream = _run_gh_pr_view(pr_number)
    if upstream is None:
        raise MergeVerificationFailed(
            pr_number=pr_number,
            upstream_view={},
            message=(
                f"PR #{pr_number} post-merge verification could not query upstream "
                f"(gh pr view returned no data). Local log may show success but "
                f"upstream state is unknown."
            ),
        )

    state = upstream.get("state")
    if state != "MERGED":
        raise MergeVerificationFailed(
            pr_number=pr_number,
            upstream_view=upstream,
            message=(
                f"PR #{pr_number} local log claims merged, but upstream "
                f"gh pr view reports state={state!r} (mergedAt="
                f"{upstream.get('mergedAt')!r}, mergeCommit="
                f"{upstream.get('mergeCommit')!r}). Possible wrong-target fork, "
                f"insufficient token scope, or webhook lag."
            ),
        )

    logger.info(
        "Post-merge verification OK: PR %s state=MERGED mergedAt=%s",
        pr_number, upstream.get("mergedAt"),
    )
    return upstream


def token_scope_preflight() -> tuple[bool, str]:
    """Confirm `gh` can list PRs in upstream repo. Returns (success, detail).

    BTCAAAAA-38470 Gap 2 — runs `gh pr list --repo Stack-Alerts/BTC-Trade-Engine-PaperClip
    --limit 1`. Returns (True, "ok") on success, (False, detail) on auth or
    network failure. The detail string for auth failures includes the return
    code so the routine can surface `routine_token_has_no_upstream_access`
    with a precise error code.
    """
    import shutil
    import subprocess

    gh = shutil.which("gh")
    if gh is None:
        return False, "gh_cli_not_on_path"

    try:
        proc = subprocess.run(
            [
                gh, "pr", "list",
                "--repo", REPO_FULL,
                "--limit", "1",
                "--state", "all",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return False, "preflight_timeout"
    except Exception as exc:
        return False, f"preflight_exception:{type(exc).__name__}"

    rc = proc.returncode
    if rc == 0:
        return True, "ok"

    stderr_excerpt = (proc.stderr or "")[:200].strip()
    if rc in (401, 403):
        return False, f"auth_failed_rc_{rc}:{stderr_excerpt}"
    return False, f"preflight_failed_rc_{rc}:{stderr_excerpt}"


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

    # BTCAAAAA-38470 Gap 2 — token-scope preflight. Refuse to do any work
    # (including checking out issues) if `gh` cannot reach the upstream repo.
    preflight_ok, preflight_detail = token_scope_preflight()
    if not preflight_ok:
        if preflight_detail.startswith("auth_failed_rc_"):
            logger.error(
                "Token-scope preflight failed (%s) — escalating "
                "routine_token_has_no_upstream_access before any work",
                preflight_detail,
            )
            return 2
        logger.warning(
            "Token-scope preflight failed (%s) — continuing cautiously",
            preflight_detail,
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
