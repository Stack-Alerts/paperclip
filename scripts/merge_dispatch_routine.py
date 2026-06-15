#!/usr/bin/env python3
"""Phase 4a: Merge-dispatch routine — backup sweep that opens PRs and merges in_review issues.

This routine is the *backup* mechanism (the primary path is an agent-finish trigger that
dispatches a merge immediately when an issue is set to in_review). It periodically sweeps
every in_review issue and acts on any that carries a parseable Fix-SHA whose commit has been
pushed to a remote branch but is not yet on origin/main:

1. Extracts the Fix-SHA from the close-out comment (no interaction gate)
2. Confirms the SHA exists locally (fetch if needed); skips if not yet pushed (push lag)
3. Skips if the SHA is already an ancestor of origin/main (merge already landed)
4. Finds the pushed remote branch containing the SHA; skips if none (push lag)
5. Opens a PR via GitHub API (CEO's GH_TOKEN)
6. Merges the PR with squash
7. Comments on source issue and sets status to done
8. On failure, escalates via BTCAAAAA-30033 routine

Historical note: this routine previously gated on a `merge_request` interaction created
within the last hour. No agent or API could create that interaction (the interactions API
only accepts suggest_tasks | ask_user_questions | request_confirmation |
request_checkbox_confirmation), so the routine skipped every issue and merges never
dispatched — the chronic PUSH_LAG. The gate was removed in BTCAAAAA-36522.

Usage:
    python3 scripts/merge_dispatch_routine.py

Requires:
    PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID
    GH_TOKEN (CEO's GitHub token — has admin access to BTC-Trade-Engine-PaperClip)
"""

from __future__ import annotations

import json
import logging
import os
import re
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("merge_dispatch")

# Configuration
REPO_OWNER = "Stack-Alerts"
REPO_NAME = "BTC-Trade-Engine-PaperClip"
GITHUB_API_BASE = "https://api.github.com"
TRACKING_ISSUE = "BTCAAAAA-30033"  # Escalation issue
MERGE_DISPATCH_TRACKING = "BTCAAAAA-30048"  # This routine's tracking issue

# Regex for Fix-SHA comment: line-anchored
FIX_SHA_PATTERN = re.compile(r"^Fix-SHA: ([0-9a-f]{40})$", re.MULTILINE)


def _http_session() -> requests.Session:
    """Create HTTP session with retries and proper headers."""
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ.get('PAPERCLIP_API_KEY', '')}",
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


def _github_session(token: str) -> requests.Session:
    """Create authenticated GitHub API session."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return session


def _token_is_valid(token: str) -> bool:
    """Return True if the token authenticates against the GitHub API."""
    if not token:
        return False
    try:
        resp = _github_session(token).get(f"{GITHUB_API_BASE}/user", timeout=15)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def resolve_gh_token() -> str | None:
    """Return a working GitHub token.

    The runner's GH_TOKEN env var has historically held an invalid placeholder
    (BTCAAAAA-36525), which 401s every API call and stalls the merge backlog.
    Prefer the env token only if it actually authenticates; otherwise fall back
    to the gh CLI keyring token (GH_TOKEN stripped so gh reads the keyring).
    """
    env_token = os.environ.get("GH_TOKEN", "")
    if _token_is_valid(env_token):
        return env_token

    if env_token:
        logger.warning("GH_TOKEN env var is set but failed auth; falling back to gh keyring")

    try:
        clean_env = {k: v for k, v in os.environ.items() if k != "GH_TOKEN"}
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=15,
            env=clean_env,
        )
        keyring_token = result.stdout.strip()
        if result.returncode == 0 and _token_is_valid(keyring_token):
            return keyring_token
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("gh auth token fallback failed: %s", exc)

    return None


def fetch_issue_comments(issue_id: str) -> list[dict[str, Any]]:
    """Fetch all comments for an issue."""
    sess = _http_session()
    try:
        resp = sess.get(
            f"{os.environ.get('PAPERCLIP_API_URL')}/api/issues/{issue_id}/comments",
            timeout=30,
        )
        resp.raise_for_status()
        comments = resp.json()
        if isinstance(comments, list):
            return comments
        return []
    except Exception as exc:
        logger.error("Failed to fetch comments for issue %s: %s", issue_id, exc)
        return []
    finally:
        sess.close()


def fetch_issue(issue_id: str) -> dict[str, Any] | None:
    """Fetch a single issue by id (used by the agent-finish trigger path)."""
    sess = _http_session()
    try:
        resp = sess.get(
            f"{os.environ.get('PAPERCLIP_API_URL')}/api/issues/{issue_id}",
            timeout=30,
        )
        resp.raise_for_status()
        issue = resp.json()
        if isinstance(issue, dict):
            return issue
        return None
    except Exception as exc:
        logger.error("Failed to fetch issue %s: %s", issue_id, exc)
        return None
    finally:
        sess.close()


def find_in_review_issues() -> list[dict[str, Any]]:
    """Find all in_review issues."""
    company_id = os.environ.get("PAPERCLIP_COMPANY_ID", "")
    if not company_id:
        logger.error("PAPERCLIP_COMPANY_ID not set")
        return []

    sess = _http_session()
    try:
        resp = sess.get(
            f"{os.environ.get('PAPERCLIP_API_URL')}/api/companies/{company_id}/issues",
            params={
                "status": "in_review",
                "limit": 200,
            },
            timeout=30,
        )
        resp.raise_for_status()
        issues = resp.json()
        if isinstance(issues, dict) and "issues" in issues:
            issues_list = issues["issues"]
        elif isinstance(issues, list):
            issues_list = issues
        else:
            logger.warning("Unexpected response format from issues API")
            return []

        logger.info("Found %d in_review issues", len(issues_list))
        return issues_list
    except Exception as exc:
        logger.error("Failed to find in_review issues: %s", exc)
        return []
    finally:
        sess.close()


def extract_fix_sha_from_comments(comments: list[dict[str, Any]]) -> str | None:
    """Extract Fix-SHA from comment list."""
    for comment in comments:
        body = comment.get("body", "")
        match = FIX_SHA_PATTERN.search(body)
        if match:
            return match.group(1)
    return None


def sha_exists_locally(sha: str) -> bool:
    """Check if SHA exists in local clone."""
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", sha],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception as exc:
        logger.error("Failed to check SHA locally: %s", exc)
        return False


def fetch_sha_from_remote(sha: str) -> bool:
    """Fetch SHA from remote if it doesn't exist locally."""
    try:
        result = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("Failed to fetch from origin: %s", result.stderr.decode())
            return False

        # Verify it exists now
        return sha_exists_locally(sha)
    except Exception as exc:
        logger.error("Failed to fetch from remote: %s", exc)
        return False


def find_branch_for_sha(sha: str) -> str | None:
    """Find the remote branch containing the given SHA."""
    try:
        result = subprocess.run(
            ["git", "branch", "-r", "--contains", sha],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.error("Failed to find branch for SHA: %s", result.stderr.decode())
            return None

        branches = result.stdout.decode().strip().split("\n")
        if not branches:
            return None

        # Find the first origin/fix/* branch
        for branch in branches:
            branch = branch.strip()
            if branch.startswith("origin/fix/BTCAAAAA-"):
                return branch.replace("origin/", "")

        # Fallback: use first branch
        return branches[0].strip().replace("origin/", "")
    except Exception as exc:
        logger.error("Failed to find branch for SHA: %s", exc)
        return None


def is_ancestor_of_main(sha: str) -> bool:
    """Return True if SHA is already an ancestor of origin/main (merge already landed)."""
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception as exc:
        logger.error("Failed ancestry check for %s: %s", sha, exc)
        return False


def find_existing_pr(session: requests.Session, branch_name: str) -> dict | None:
    """Check if PR already exists for branch."""
    try:
        url = (
            f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
            f"?state=open&head={REPO_OWNER}:{branch_name}"
        )
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        prs = resp.json()
        if isinstance(prs, list) and len(prs) > 0:
            return prs[0]
    except Exception as e:
        logger.warning("Failed to check for existing PR on branch %s: %e", branch_name, e)
    return None


def create_pr(
    session: requests.Session,
    branch_name: str,
    title: str,
    body: str,
) -> dict | None:
    """Create PR from branch to main."""
    url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
    payload = {
        "title": title,
        "head": branch_name,
        "base": "main",
        "body": body,
    }
    try:
        resp = session.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        pr = resp.json()
        logger.info("Created PR #%d for branch %s", pr.get("number"), branch_name)
        return pr
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning("Token forbidden (403): %s", e.response.text)
            return None
        logger.error("Failed to create PR: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to create PR: %s", e)
        return None


def merge_pr(session: requests.Session, pr_number: int) -> dict | None:
    """Merge PR with squash."""
    url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge"
    payload = {
        "merge_method": "squash",
        "commit_title": f"Merge branch for PR #{pr_number}",
    }
    try:
        resp = session.put(url, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        logger.info("Merged PR #%d", pr_number)
        return result
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning("Token forbidden (403) on merge: %s", e.response.text)
            return None
        logger.error("Failed to merge PR #%d: %s", pr_number, e)
        return None
    except Exception as e:
        logger.error("Failed to merge PR #%d: %s", pr_number, e)
        return None


def comment_on_issue(issue_id: str, body: str) -> bool:
    """Post a comment to an issue."""
    sess = _http_session()
    try:
        resp = sess.post(
            f"{os.environ.get('PAPERCLIP_API_URL')}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Posted comment on issue %s", issue_id)
        return True
    except Exception as exc:
        logger.error("Failed to post comment on issue %s: %s", issue_id, exc)
        return False
    finally:
        sess.close()


def update_issue_status(issue_id: str, status: str, comment: str = "") -> bool:
    """Update issue status."""
    payload = {"status": status}
    if comment:
        payload["comment"] = comment

    sess = _http_session()
    try:
        resp = sess.patch(
            f"{os.environ.get('PAPERCLIP_API_URL')}/api/issues/{issue_id}",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Updated issue %s to status %s", issue_id, status)
        return True
    except Exception as exc:
        logger.error("Failed to update issue %s: %s", issue_id, exc)
        return False
    finally:
        sess.close()


def escalate_failure(issue_id: str, issue_identifier: str, sha: str, reason: str) -> None:
    """Escalate a merge-dispatch failure to the escalation routine."""
    try:
        body = f"""**Merge-Dispatch Failure Escalation**

Source issue: [{issue_identifier}](/BTCAAAAA/issues/{issue_identifier})
Fix-SHA: {sha[:8]}
Reason: {reason}

This issue requires manual intervention from the merge-dispatch routine ([BTCAAAAA-30048](/BTCAAAAA/issues/BTCAAAAA-30048)).
"""
        comment_on_issue(TRACKING_ISSUE, body)
    except Exception as exc:
        logger.error("Failed to escalate failure: %s", exc)


def process_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Process a single in_review issue for merge dispatch."""
    issue_id = issue.get("id", "")
    issue_identifier = issue.get("identifier", "")

    logger.info("Processing issue %s", issue_identifier)

    # Step 1: Extract Fix-SHA from comments (primary trigger — no interaction gate)
    comments = fetch_issue_comments(issue_id)
    sha = extract_fix_sha_from_comments(comments)
    if not sha:
        logger.info("Issue %s has no Fix-SHA in comments", issue_identifier)
        return {
            "issue": issue_identifier,
            "action": "skip",
            "reason": "no_fix_sha",
        }

    logger.info("Issue %s has Fix-SHA %s", issue_identifier, sha[:8])

    # Step 2: Confirm SHA exists locally, fetch if needed.
    # If still absent after a fetch, the commit has not been pushed yet (push lag) —
    # skip quietly so a later sweep retries once the agent pushes.
    if not sha_exists_locally(sha):
        logger.info("SHA %s not found locally, fetching from remote", sha[:8])
        if not fetch_sha_from_remote(sha):
            logger.info("SHA %s not on remote yet (push lag) for %s", sha[:8], issue_identifier)
            return {
                "issue": issue_identifier,
                "action": "skip",
                "reason": "sha_not_pushed",
            }

    # Step 3: If the SHA already landed on origin/main, the merge is done —
    # leave the closure gate to flip status; nothing to dispatch.
    if is_ancestor_of_main(sha):
        logger.info("SHA %s already on origin/main for %s", sha[:8], issue_identifier)
        return {
            "issue": issue_identifier,
            "action": "skip",
            "reason": "already_merged",
        }

    # Step 4: Find the pushed remote branch containing the SHA.
    # No remote branch means the commit is local-only (push lag) — skip, do not escalate.
    branch = find_branch_for_sha(sha)
    if not branch:
        logger.info("No remote branch contains SHA %s for %s (push lag)", sha[:8], issue_identifier)
        return {
            "issue": issue_identifier,
            "action": "skip",
            "reason": "branch_not_pushed",
        }

    logger.info("Found branch %s for SHA %s", branch, sha[:8])

    # Step 5: Use CEO token for GitHub operations.
    # Note: RepoSteward token doesn't work on BTC repo, so we use CEO's token only.
    # GH_TOKEN env may hold an invalid placeholder (BTCAAAAA-36525); resolve_gh_token
    # validates it and falls back to the gh keyring so the backlog still drains.
    gh_token = resolve_gh_token()
    if not gh_token:
        escalate_failure(issue_id, issue_identifier, sha, "No valid GitHub token (GH_TOKEN invalid and gh keyring unavailable)")
        return {
            "issue": issue_identifier,
            "action": "failed",
            "reason": "no_token",
        }

    session = _github_session(gh_token)

    # Check for existing PR
    existing_pr = find_existing_pr(session, branch)
    if existing_pr:
        logger.info("PR already exists for branch %s: PR #%d", branch, existing_pr.get("number"))
        pr = existing_pr
    else:
        # Try to create PR
        title = f"[Automated] Merge {branch} ({sha[:8]})"
        body = f"Automated merge dispatch for [{issue_identifier}](/BTCAAAAA/issues/{issue_identifier}).\n\nBranch: {branch}\nFix-SHA: {sha}"
        pr = create_pr(session, branch, title, body)

    if not pr:
        escalate_failure(issue_id, issue_identifier, sha, "Failed to create PR")
        return {
            "issue": issue_identifier,
            "action": "failed",
            "reason": "pr_creation_failed",
        }

    pr_number = pr.get("number")
    pr_url = pr.get("html_url")
    logger.info("PR #%d opened for issue %s", pr_number, issue_identifier)

    # Step 7: Merge the PR
    merge_result = merge_pr(session, pr_number)
    if not merge_result:
        escalate_failure(issue_id, issue_identifier, sha, f"Failed to merge PR #{pr_number}")
        return {
            "issue": issue_identifier,
            "action": "failed",
            "reason": "merge_failed",
            "pr_number": pr_number,
        }

    merge_sha = merge_result.get("sha", sha)
    logger.info("PR #%d merged with commit %s", pr_number, merge_sha[:8])

    # Step 8: Comment on issue and set status to done
    comment_body = f"""**Merge Complete**

PR #{pr_number} has been merged via squash.
- PR URL: {pr_url}
- Merge commit: {merge_sha[:8]}
- Branch landed on origin/main

This issue is now marked as done.
"""

    if not comment_on_issue(issue_id, comment_body):
        logger.warning("Failed to post comment, but PR was merged")

    if not update_issue_status(issue_id, "done", "Merged via automated dispatch"):
        logger.warning("Failed to update status, but PR was merged")

    return {
        "issue": issue_identifier,
        "action": "merged",
        "pr_number": pr_number,
        "pr_url": pr_url,
        "merge_sha": merge_sha,
    }


def dispatch_for_issue(issue_id: str) -> int:
    """Agent-finish trigger: dispatch a merge for a single just-finished issue.

    Invoked at close-out (see CLAUDE.md) right after an agent sets an issue to in_review
    with a Fix-SHA, so the merge is prompt instead of waiting for the periodic sweep.
    """
    logger.info("Agent-finish merge dispatch for issue %s", issue_id)
    issue = fetch_issue(issue_id)
    if not issue:
        print(json.dumps({"issue": issue_id, "action": "error", "error": "issue_not_found"}))
        return 1

    if issue.get("status") != "in_review":
        result = {"issue": issue.get("identifier", issue_id), "action": "skip",
                  "reason": f"status_{issue.get('status')}"}
        print(json.dumps(result, indent=2))
        return 0

    try:
        result = process_issue(issue)
    except Exception as e:
        result = {"issue": issue.get("identifier", issue_id), "action": "error", "error": str(e)}

    print(json.dumps(result, indent=2))
    logger.info("Agent-finish dispatch result: %s", result.get("action"))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main routine execution.

    With ``--issue <id>`` runs the agent-finish trigger for a single issue (primary path).
    With no args, runs the periodic backup sweep over all in_review issues.
    """
    argv = sys.argv[1:] if argv is None else argv
    if "--issue" in argv:
        idx = argv.index("--issue")
        if idx + 1 >= len(argv):
            logger.error("--issue requires an issue id")
            return 2
        return dispatch_for_issue(argv[idx + 1])

    logger.info("Starting merge-dispatch routine (backup sweep)")

    # Find all in_review issues
    issues = find_in_review_issues()
    logger.info("Found %d in_review issues to process", len(issues))

    results = []
    for issue in issues:
        try:
            result = process_issue(issue)
            results.append(result)
        except Exception as e:
            issue_id = issue.get("identifier", "?")
            logger.error("Error processing %s: %s", issue_id, e)
            results.append({
                "issue": issue_id,
                "action": "error",
                "error": str(e),
            })

    # Report results
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issues_processed": len(results),
        "results": results,
        "summary": {
            "merged": len([r for r in results if r.get("action") == "merged"]),
            "skipped": len([r for r in results if r.get("action") == "skip"]),
            "failed": len([r for r in results if r.get("action") == "failed"]),
            "errors": len([r for r in results if r.get("action") == "error"]),
        },
    }

    print(json.dumps(output, indent=2))
    logger.info(f"Routine complete: {output['summary']}")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
