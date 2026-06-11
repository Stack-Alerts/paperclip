#!/usr/bin/env python3
"""Stale branch alerter for BTC-Trade-Engine.

Scans remote branches that have been on origin for >7 days with no open
GitHub PR and creates Paperclip notifications. Deduplicates: will not fire
more than once per branch per week.

If the branch name contains a BTCAAAAA-NNN identifier, posts a comment on
that issue. Otherwise creates a fresh Paperclip alert issue.

Does not fire on protected branches (main, master, develop, dev).

Usage:
    python scripts/stale_branch_alert.py [--dry-run]

Exit codes:
    0 — one or more alerts sent (or dry-run simulated)
    1 — error
    2 — no stale branches found (clean state)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import requests

PROTECTED_BRANCHES = frozenset({"main", "master", "develop", "dev"})
STALE_DAYS = 7
DEDUP_DAYS = 7

ISSUE_PATTERN = re.compile(r"BTCAAAAA-(\d+)", re.IGNORECASE)

logger = logging.getLogger("stale_branch_alert")


# ---------------------------------------------------------------------------
# Paperclip API helpers
# ---------------------------------------------------------------------------

def _paperclip_session() -> requests.Session:
    api_key = os.environ.get("PAPERCLIP_API_KEY", "")
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    return s


def _base() -> str:
    return os.environ.get("PAPERCLIP_API_URL", "").rstrip("/")


def _company() -> str:
    return os.environ.get("PAPERCLIP_COMPANY_ID", "")


def _parse_iso(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Git / GitHub helpers
# ---------------------------------------------------------------------------

def get_remote_branches() -> list[str]:
    """Return all remote branch names (without the 'origin/' prefix)."""
    result = subprocess.run(
        ["git", "branch", "-r", "--format=%(refname:short)"],
        capture_output=True, text=True, check=True,
    )
    branches: list[str] = []
    for raw in result.stdout.splitlines():
        name = raw.strip()
        if name.startswith("origin/"):
            name = name[len("origin/"):]
        if not name or name == "HEAD" or "->" in name:
            continue
        branches.append(name)
    return branches


def get_branch_age_days(branch: str) -> int | None:
    """Return days since the branch's oldest diverging commit relative to main.

    Uses git merge-base so the age reflects when the branch was originally
    cut, not the date of the most recent commit.
    """
    try:
        mb = subprocess.run(
            ["git", "merge-base", "origin/main", f"origin/{branch}"],
            capture_output=True, text=True,
        )
        if mb.returncode != 0:
            return None
        base_sha = mb.stdout.strip()
        if not base_sha:
            return None

        log = subprocess.run(
            ["git", "log", "--format=%ct", "--reverse",
             f"{base_sha}..origin/{branch}"],
            capture_output=True, text=True,
        )
        timestamps = [l.strip() for l in log.stdout.splitlines() if l.strip()]
        if not timestamps:
            return None

        oldest_ts = int(timestamps[0])
        now_ts = int(datetime.now(timezone.utc).timestamp())
        return (now_ts - oldest_ts) // 86400
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def has_open_pr(branch: str) -> bool:
    """Return True if the branch has at least one open GitHub pull request."""
    result = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--state", "open",
         "--json", "number"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False
    try:
        return len(json.loads(result.stdout)) > 0
    except (json.JSONDecodeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Issue resolution
# ---------------------------------------------------------------------------

def find_source_issue_identifier(branch: str) -> str | None:
    """Return 'BTCAAAAA-NNN' if embedded in the branch name, else None."""
    m = ISSUE_PATTERN.search(branch)
    return f"BTCAAAAA-{m.group(1)}" if m else None


def get_issue_by_identifier(sess: requests.Session, identifier: str) -> dict | None:
    """Fetch a Paperclip issue by its text identifier (e.g. 'BTCAAAAA-123')."""
    resp = sess.get(
        f"{_base()}/api/companies/{_company()}/issues",
        params={"q": identifier, "limit": 5},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    for issue in resp.json():
        if issue.get("identifier") == identifier:
            return issue
    return None


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _fingerprint(branch: str) -> str:
    return f"[stale-branch-alert:{branch}]"


def recently_alerted(
    sess: requests.Session,
    branch: str,
    source_issue_id: str | None,
) -> bool:
    """Return True if a stale alert was already sent for this branch within DEDUP_DAYS."""
    fp = _fingerprint(branch)
    cutoff = datetime.now(timezone.utc) - timedelta(days=DEDUP_DAYS)

    if source_issue_id:
        resp = sess.get(
            f"{_base()}/api/issues/{source_issue_id}/comments",
            timeout=30,
        )
        if resp.status_code == 200:
            for comment in resp.json():
                if fp not in (comment.get("body") or ""):
                    continue
                created = _parse_iso(comment.get("createdAt"))
                if created and created > cutoff:
                    return True

    # Also check standalone alert issues (for branches without a source issue,
    # or as a safety net when the source was not found)
    resp = sess.get(
        f"{_base()}/api/companies/{_company()}/issues",
        params={"q": fp, "limit": 20},
        timeout=30,
    )
    if resp.status_code == 200:
        for issue in resp.json():
            if fp not in (issue.get("description") or ""):
                continue
            created = _parse_iso(issue.get("createdAt"))
            if created and created > cutoff:
                return True

    return False


# ---------------------------------------------------------------------------
# Alert delivery
# ---------------------------------------------------------------------------

def post_source_issue_comment(
    sess: requests.Session,
    issue_id: str,
    issue_identifier: str,
    branch: str,
    age_days: int,
    dry_run: bool,
) -> bool:
    """Post a stale-branch alert comment on the identified source issue."""
    fp = _fingerprint(branch)
    body = (
        f"## ⚠️ Stale Branch Alert\n\n"
        f"Branch `{branch}` has been on `origin` for **{age_days} day(s)** "
        f"with no open pull request.\n\n"
        f"**Action required — please do one of the following:**\n"
        f"- Open a PR (even a draft) against `main` to make drift visible, or\n"
        f"- Delete the branch if it is no longer needed:\n"
        f"  ```\n"
        f"  git push origin --delete {branch}\n"
        f"  ```\n\n"
        f"Per AGENTS.md §6a, a branch must have an open PR within 24 h of "
        f"first push. Without a PR, automated `chore(impact-gate)` commits "
        f"accumulate on `main` invisibly, requiring a large manual rebase.\n\n"
        f"---\n{fp}"
    )
    if dry_run:
        logger.info(
            "DRY RUN: would comment on %s for branch %s (%d days)",
            issue_identifier, branch, age_days,
        )
        return True

    resp = sess.post(
        f"{_base()}/api/issues/{issue_id}/comments",
        json={"body": body},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        logger.info(
            "Posted stale-branch alert on %s for branch %s",
            issue_identifier, branch,
        )
        return True
    logger.error(
        "Failed to post comment on %s: %s %s",
        issue_identifier, resp.status_code, resp.text[:200],
    )
    return False


def create_alert_issue(
    sess: requests.Session,
    branch: str,
    age_days: int,
    dry_run: bool,
) -> bool:
    """Create a new Paperclip alert issue for an unaffiliated stale branch."""
    fp = _fingerprint(branch)
    title = f"stale branch: `{branch}` has no open PR ({age_days}d old)"
    description = (
        f"## ⚠️ Stale Branch: `{branch}`\n\n"
        f"This branch has been on `origin` for **{age_days} day(s)** "
        f"with no open pull request.\n\n"
        f"**Action required — please do one of the following:**\n"
        f"- Open a PR (even a draft) against `main` to make drift visible, or\n"
        f"- Delete the branch:\n"
        f"  ```\n"
        f"  git push origin --delete {branch}\n"
        f"  ```\n\n"
        f"Per AGENTS.md §6a, all pushed branches must have an open PR within "
        f"24 h to prevent silent drift from automated `chore(impact-gate)` "
        f"commits accumulating on `main`.\n\n"
        f"Detected by the `branch-reaper` stale-alert workflow.\n\n"
        f"---\n{fp}"
    )
    if dry_run:
        logger.info(
            "DRY RUN: would create alert issue for branch %s (%d days)",
            branch, age_days,
        )
        return True

    resp = sess.post(
        f"{_base()}/api/companies/{_company()}/issues",
        json={"title": title, "description": description, "status": "todo"},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        created = resp.json()
        logger.info(
            "Created alert issue %s for branch %s",
            created.get("identifier", ""), branch,
        )
        return True
    logger.error(
        "Failed to create alert issue for branch %s: %s %s",
        branch, resp.status_code, resp.text[:200],
    )
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Alert on stale unmerged branches with no open PR",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Log actions without writing to Paperclip",
    )
    args = parser.parse_args()

    sess = _paperclip_session()
    branches = get_remote_branches()

    alerted = 0
    deduped = 0
    protected = 0
    young = 0
    has_pr_count = 0
    errors = 0

    for branch in sorted(branches):
        if branch in PROTECTED_BRANCHES:
            protected += 1
            continue

        age_days = get_branch_age_days(branch)
        if age_days is None:
            logger.warning("Cannot determine age for %s — skipping", branch)
            continue

        if age_days < STALE_DAYS:
            young += 1
            continue

        if has_open_pr(branch):
            has_pr_count += 1
            continue

        logger.info("Stale branch: %s (%d days, no open PR)", branch, age_days)

        source_id = find_source_issue_identifier(branch)
        source_issue_id: str | None = None
        if source_id:
            issue = get_issue_by_identifier(sess, source_id)
            if issue:
                source_issue_id = issue["id"]
                logger.info(
                    "Resolved %s (id=%s) for branch %s",
                    source_id, source_issue_id, branch,
                )
            else:
                logger.warning(
                    "Branch %s references %s but issue not found "
                    "— will create standalone alert",
                    branch, source_id,
                )

        if recently_alerted(sess, branch, source_issue_id):
            logger.info(
                "Skipping %s — alert already sent within last %d days",
                branch, DEDUP_DAYS,
            )
            deduped += 1
            continue

        if source_issue_id:
            success = post_source_issue_comment(
                sess, source_issue_id, source_id or "", branch, age_days, args.dry_run,
            )
        else:
            success = create_alert_issue(sess, branch, age_days, args.dry_run)

        if success:
            alerted += 1
        else:
            errors += 1

    print(f"\n\U0001f4ca Stale Branch Alert Summary:")
    print(f"  Alerted:             {alerted}")
    print(f"  Protected (skipped): {protected}")
    print(f"  Young (< {STALE_DAYS}d):       {young}")
    print(f"  Has open PR:         {has_pr_count}")
    print(f"  Deduped:             {deduped}")
    print(f"  Errors:              {errors}")

    if errors:
        sys.exit(1)

    if alerted == 0 and not args.dry_run:
        sys.exit(2)


if __name__ == "__main__":
    main()
