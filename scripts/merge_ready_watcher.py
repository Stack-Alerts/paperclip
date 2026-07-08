#!/usr/bin/env python3
"""Merge-ready watcher: merges any open PR where all required checks pass.

This script is the fix for the chronic merge backlog (BTCAAAAA-38557).
It bypasses the Fix-SHA lookup in merge_dispatch_routine.py entirely and
directly watches GitHub for PRs that are ready to merge.

Root cause it addresses:
  merge_dispatch_routine.py uses `git branch -r --contains <fix-sha>` to find
  the branch to merge. When an agent records Fix-SHA for an intermediate commit
  and later rebases, the SHA is no longer reachable from any remote branch tip.
  merge_dispatch silently skips the issue with "push lag" and the PR never merges.

This watcher instead asks GitHub: "which PRs have mergeable_state=clean right now?"
and merges them directly, then closes the corresponding Paperclip issue.

Merge criteria (ALL must be true):
  - PR is open and targets main
  - PR mergeable_state == "clean" (all checks pass, no conflicts, up to date)

Update-branch behavior:
  - If mergeable_state == "behind" and all checks pass: update the branch.
    On the next run (after CI re-runs), it should reach "clean" and merge.

Usage:
    python3 scripts/merge_ready_watcher.py
    python3 scripts/merge_ready_watcher.py --dry-run   # preview without merging

Cron (every 5 minutes):
    */5 * * * * cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip && python3 scripts/merge_ready_watcher.py >> /tmp/merge_ready_watcher.log 2>&1
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _load_env_file(path: Path) -> None:
    """Populate os.environ from a KEY=VALUE file. Skips blanks and comments.

    Used as a fallback when the script is invoked from a context that does not
    pre-export GH_TOKEN / PAPERCLIP_API_KEY (e.g. the */5 * * * * cron line in
    the operator's crontab, which otherwise logs 'No valid GitHub token
    available' every 5 minutes because GH_TOKEN is unset AND `gh` is not on
    the systemd user PATH). See BTCAAAAA-39034.
    """
    if not path.is_file():
        return
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if not key:
                continue
            os.environ.setdefault(key, value.strip())
    except OSError as exc:
        logging.getLogger("merge_ready_watcher").warning(
            "Could not read env file %s: %s", path, exc
        )


# Pull GH_TOKEN / PAPERCLIP_* from <repo>/.env if not already in the environment.
# The cron entry does not export these, so the watcher would otherwise exit
# with "No valid GitHub token available" before doing any work.
_load_env_file(REPO_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("merge_ready_watcher")

REPO_OWNER = "Stack-Alerts"
REPO_NAME = "BTC-Trade-Engine-PaperClip"
GITHUB_API_BASE = "https://api.github.com"
ISSUE_ID_PATTERN = re.compile(r"(BTCAAAAA-\d+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# GitHub session helpers
# ---------------------------------------------------------------------------

def _github_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    adapter = HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    ))
    s.mount("https://", adapter)
    return s


def _token_is_valid(token: str) -> bool:
    if not token:
        return False
    try:
        resp = _github_session(token).get(f"{GITHUB_API_BASE}/user", timeout=15)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def resolve_gh_token() -> str | None:
    env_token = os.environ.get("GH_TOKEN", "")
    if _token_is_valid(env_token):
        return env_token
    if env_token:
        logger.warning("GH_TOKEN env invalid, falling back to gh keyring")
    try:
        clean_env = {k: v for k, v in os.environ.items() if k != "GH_TOKEN"}
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=15, env=clean_env,
        )
        token = result.stdout.strip()
        if result.returncode == 0 and _token_is_valid(token):
            return token
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("gh auth token fallback failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Paperclip helpers
# ---------------------------------------------------------------------------

def _paperclip_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ.get('PAPERCLIP_API_KEY', '')}",
        "Content-Type": "application/json",
    })
    adapter = HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5))
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def _paperclip_base_url() -> str:
    return os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100").rstrip("/")


def find_paperclip_issue(identifier: str) -> dict | None:
    """Look up a Paperclip issue by its BTCAAAAA-XXXXX identifier."""
    session = _paperclip_session()
    base = _paperclip_base_url()
    try:
        resp = session.get(
            f"{base}/api/issues",
            params={"identifier": identifier, "limit": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        issues = data.get("issues", data) if isinstance(data, dict) else data
        if isinstance(issues, list) and issues:
            return issues[0]
    except Exception as exc:
        logger.warning("Failed to look up issue %s: %s", identifier, exc)
    return None


def close_paperclip_issue(issue_id: str, identifier: str, pr_number: int, squash_sha: str) -> bool:
    """Mark a Paperclip issue done after its PR merged."""
    session = _paperclip_session()
    base = _paperclip_base_url()

    comment_body = (
        f"PR #{pr_number} squash-merged to main via merge_ready_watcher.\n\n"
        f"Fix-SHA: {squash_sha}"
    )

    # Post closure comment
    try:
        resp = session.post(
            f"{base}/api/issues/{issue_id}/comments",
            json={"body": comment_body, "payload": {"version": 1}},
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            logger.warning("Comment POST returned %d for %s", resp.status_code, identifier)
    except Exception as exc:
        logger.warning("Failed to post comment on %s: %s", identifier, exc)

    # Mark done via CLI (more reliable than HTTP PATCH per BTC-38461 bug class)
    try:
        result = subprocess.run(
            ["npx", "paperclipai", "issue", "update",
             "--id", identifier, "--status", "done"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            logger.info("Marked %s done via CLI", identifier)
            return True
        logger.warning("CLI update failed for %s: %s", identifier, result.stderr[:200])
    except Exception as exc:
        logger.warning("CLI update failed for %s: %s", identifier, exc)

    # Fallback: HTTP PATCH
    try:
        resp = session.patch(
            f"{base}/api/issues/{issue_id}",
            json={"status": "done"},
            timeout=10,
        )
        if resp.status_code in (200, 204):
            logger.info("Marked %s done via HTTP PATCH", identifier)
            return True
        logger.warning("HTTP PATCH returned %d for %s", resp.status_code, identifier)
    except Exception as exc:
        logger.warning("HTTP PATCH failed for %s: %s", identifier, exc)

    return False


# ---------------------------------------------------------------------------
# GitHub PR helpers
# ---------------------------------------------------------------------------

def list_open_prs(session: requests.Session) -> list[dict]:
    """List all open PRs targeting main (stub info only)."""
    prs: list[dict] = []
    page = 1
    while True:
        resp = session.get(
            f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
            params={"state": "open", "base": "main", "per_page": 100, "page": page},
            timeout=20,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        prs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return prs


def get_pr_detail(session: requests.Session, pr_number: int) -> dict | None:
    """Fetch full PR detail including mergeable_state (requires individual GET)."""
    try:
        resp = session.get(
            f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Failed to get PR #%d detail: %s", pr_number, exc)
        return None


def update_branch(session: requests.Session, pr_number: int) -> bool:
    """Update PR branch to be current with base branch."""
    try:
        resp = session.put(
            f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/update-branch",
            timeout=15,
        )
        if resp.status_code in (200, 202):
            logger.info("PR #%d branch updated successfully", pr_number)
            return True
        logger.warning("Update-branch for PR #%d returned %d: %s",
                       pr_number, resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        logger.warning("Failed to update branch for PR #%d: %s", pr_number, exc)
        return False


def check_runs_all_pass(session: requests.Session, head_sha: str) -> bool:
    """Return True if all check runs for the given SHA have passed."""
    try:
        resp = session.get(
            f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/commits/{head_sha}/check-runs",
            params={"per_page": 100},
            timeout=15,
        )
        if resp.status_code != 200:
            return False
        runs = resp.json().get("check_runs", [])
        if not runs:
            return False

        # Keep latest run per name
        by_name: dict[str, dict] = {}
        for run in runs:
            name = run.get("name", "")
            existing = by_name.get(name)
            if not existing or run.get("id", 0) > existing.get("id", 0):
                by_name[name] = run

        for run in by_name.values():
            if run.get("status") != "completed":
                return False
            if run.get("conclusion") not in ("success", "neutral", "skipped"):
                return False
        return True
    except Exception as exc:
        logger.warning("Failed to check runs for %s: %s", head_sha[:8], exc)
        return False


def squash_merge_pr(session: requests.Session, pr: dict, dry_run: bool = False) -> str | None:
    """Squash-merge PR. Returns the squash SHA on success, None on failure."""
    pr_number = pr.get("number")
    title = pr.get("title", f"Merge PR #{pr_number}")
    head_sha = pr.get("head", {}).get("sha", "")

    if dry_run:
        logger.info("[DRY-RUN] Would squash-merge PR #%d: %s", pr_number, title)
        return "dry-run-sha"

    url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge"
    payload = {
        "merge_method": "squash",
        "commit_title": f"[Automated] {title} (#{pr_number})",
        "sha": head_sha,
    }
    try:
        resp = session.put(url, json=payload, timeout=30)
        if resp.status_code == 200:
            squash_sha = resp.json().get("sha", "")
            logger.info("PR #%d squash-merged → %s", pr_number, squash_sha[:12])
            return squash_sha
        logger.warning("PR #%d merge returned %d: %s", pr_number, resp.status_code, resp.text[:300])
        return None
    except Exception as exc:
        logger.error("Failed to merge PR #%d: %s", pr_number, exc)
        return None


# ---------------------------------------------------------------------------
# Issue identifier extraction
# ---------------------------------------------------------------------------

def extract_issue_identifier(pr: dict) -> str | None:
    """Extract BTCAAAAA-XXXXX from PR title, branch name, or body."""
    title = pr.get("title", "")
    branch = pr.get("head", {}).get("ref", "")
    body = (pr.get("body", "") or "")[:500]

    for text in [title, branch, body]:
        m = ISSUE_ID_PATTERN.search(text)
        if m:
            identifier = m.group(1).upper()
            return identifier
    return None


# ---------------------------------------------------------------------------
# Main watcher logic
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> dict[str, Any]:
    token = resolve_gh_token()
    if not token:
        logger.error("No valid GitHub token available")
        return {"error": "no_token"}

    session = _github_session(token)

    logger.info("Fetching open PRs...")
    try:
        pr_stubs = list_open_prs(session)
    except Exception as exc:
        logger.error("Failed to list open PRs: %s", exc)
        return {"error": str(exc)}

    logger.info("Found %d open PRs targeting main", len(pr_stubs))

    results: dict[str, list] = {
        "merged": [],
        "updated": [],
        "skipped": [],
        "errors": [],
    }

    for stub in pr_stubs:
        pr_number = stub.get("number")

        # Individual GET required to get mergeable_state (not in list response)
        pr = get_pr_detail(session, pr_number)
        if not pr:
            results["errors"].append({"pr": pr_number, "reason": "detail_fetch_failed"})
            continue

        state = pr.get("mergeable_state", "unknown")
        title = pr.get("title", "")[:60]
        head_sha = pr.get("head", {}).get("sha", "")

        logger.info("PR #%d [%s] %s", pr_number, state, title)

        if state == "dirty":
            logger.info("  → conflicts, skipping")
            results["skipped"].append({"pr": pr_number, "reason": "dirty"})
            continue

        if state == "unknown":
            logger.info("  → mergeable_state still computing, skipping")
            results["skipped"].append({"pr": pr_number, "reason": "unknown"})
            continue

        if state == "behind":
            # Update only if current checks all pass (no point updating a failing branch)
            if check_runs_all_pass(session, head_sha):
                logger.info("  → BEHIND, all checks pass; updating branch")
                if not dry_run:
                    update_branch(session, pr_number)
                results["updated"].append(pr_number)
            else:
                logger.info("  → BEHIND, checks not all passing; skipping")
                results["skipped"].append({"pr": pr_number, "reason": "behind_checks_pending"})
            continue

        if state == "blocked":
            logger.info("  → BLOCKED (CI pending/failing), skipping")
            results["skipped"].append({"pr": pr_number, "reason": "blocked"})
            continue

        if state != "clean":
            logger.info("  → unexpected state %r, skipping", state)
            results["skipped"].append({"pr": pr_number, "reason": state})
            continue

        # state == "clean": ready to merge now
        logger.info("  → CLEAN — merging PR #%d", pr_number)

        squash_sha = squash_merge_pr(session, pr, dry_run=dry_run)
        if not squash_sha:
            results["errors"].append({"pr": pr_number, "reason": "merge_failed"})
            continue

        results["merged"].append(pr_number)

        # Close the corresponding Paperclip issue
        identifier = extract_issue_identifier(pr)
        if identifier:
            logger.info("  Looking up Paperclip issue %s", identifier)
            issue = find_paperclip_issue(identifier)
            if issue:
                issue_id = issue.get("id", "")
                if issue.get("status") == "done":
                    logger.info("  Issue %s already done", identifier)
                elif not dry_run:
                    ok = close_paperclip_issue(issue_id, identifier, pr_number, squash_sha)
                    logger.info("  Issue %s close result: %s", identifier, "ok" if ok else "failed")
                else:
                    logger.info("  [DRY-RUN] Would mark %s done", identifier)
            else:
                logger.warning("  Could not find Paperclip issue %s", identifier)
        else:
            logger.warning("  PR #%d: no BTCAAAAA-XXXXX found in title/branch/body", pr_number)

    logger.info(
        "Done: %d merged, %d updated (branch), %d skipped, %d errors",
        len(results["merged"]), len(results["updated"]),
        len(results["skipped"]), len(results["errors"]),
    )
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        logger.info("DRY-RUN mode — no merges or issue updates will happen")
    run(dry_run=dry_run)
