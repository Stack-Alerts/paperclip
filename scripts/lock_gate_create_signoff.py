#!/usr/bin/env python3
"""Create a CTO sign-off request Paperclip issue when the lock gate blocks.

Reads lock gate failure details from a JSON file (produced by lock_gate.py
--json-summary) and creates or updates a Paperclip issue.

Usage:
    python scripts/lock_gate_create_signoff.py --gate-output <file> [--dry-run]

Exit codes:
    0 — sign-off issue created or updated
    1 — error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("lock_gate_create_signoff")

REPO_ROOT = Path(__file__).resolve().parent.parent

# CTO agent ID per plan BTCAAAAA-1479 §2
CTO_AGENT_ID = "41b5ede6-e209-40ba-b923-dc969c722e6d"

# Paperclip label for tracking sign-off issues
SIGNOFF_LABEL = "cto-signoff-required"


def _session():
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from touch_index.paperclip_client import _session, _base, _company
    return _session(), _base(), _company()


def dedup_key(pr_number: str, commit_sha: str) -> str:
    """Stable deduplication key for a PR + commit combination."""
    raw = f"{pr_number}:{commit_sha}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def find_existing_signoff(base_url: str, company_id: str, sess, dedup: str) -> dict | None:
    """Check if a sign-off issue already exists for this dedup key.

    Scans the issue description for the dedup marker.
    Returns the issue dict or None.
    """
    try:
        from touch_index.paperclip_client import _paginate
    except ImportError:
        return None
    issues = _paginate(
        f"/api/companies/{company_id}/issues",
        {"status": "todo,in_progress,in_review"},
        page_size=100,
    )
    for issue in issues:
        labels = issue.get("labels") or []
        label_names = [lb.get("name", "") for lb in labels]
        if SIGNOFF_LABEL in label_names or SIGNOFF_LABEL in (issue.get("labelIds") or []):
            body = issue.get("body", "")
            if f"<!-- dedup:{dedup} -->" in body:
                return issue
    return None


def create_signoff_issue(
    base_url: str,
    company_id: str,
    sess,
    pr_number: str,
    commit_sha: str,
    pr_url: str,
    blocked_modules: list[dict],
    gate_output: str,
    dedup: str,
) -> dict | None:
    title = f"CTO Sign-off Required: PR #{pr_number} touches locked module"

    module_list = "\n".join(
        f"- `{m['locked_path']}` — file `{m['file_path']}` — {m['reason']}"
        for m in blocked_modules
    )

    body = (
        f"**Lock Gate blocked PR #{pr_number}**\n\n"
        f"**PR:** {pr_url}\n"
        f"**Commit:** {commit_sha}\n\n"
        f"### Blocked Modules\n\n"
        f"{module_list}\n\n"
        f"### Gate Output\n\n"
        f"```\n{gate_output}\n```\n\n"
        f"### Action Required\n\n"
        f"To unblock, approve via one of the paths in `docs/runbook-module-lock.md`:\n"
        f"- **Path A** — Board-approved planned exception (permanent)\n"
        f"- **Path B.1** — CEO emergency (4-hour window)\n"
        f"- **Path B.2** — Board emergency (4-hour window)\n\n"
        f"After approval, use the Lock Exception Sign-Off workflow "
        f"(`.github/workflows/lock-exception-signoff.yml`) to add the exception "
        f"entry and unblock the PR.\n"
        f"<!-- dedup:{dedup} -->"
    )

    payload = {
        "title": title,
        "description": body,
        "labels": [SIGNOFF_LABEL],
        "assigneeAgentId": CTO_AGENT_ID,
        "priority": "high",
        "status": "todo",
    }

    try:
        resp = sess.post(
            f"{base_url}/api/companies/{company_id}/issues",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        created = resp.json()
        logger.info(
            "Created sign-off issue %s for PR #%s",
            created.get("identifier", ""), pr_number,
        )
        return created
    except Exception as exc:
        logger.error("Failed to create sign-off issue: %s", exc)
        return None


def comment_on_existing(base_url: str, sess, issue: dict, commit_sha: str) -> bool:
    """Add a comment to an existing sign-off issue noting a new attempt."""
    issue_id = issue["id"]
    body = (
        f"**Re-triggered by commit {commit_sha}**\n\n"
        f"The lock gate blocked again on a new push. "
        f"The existing sign-off request covers this PR; please re-evaluate "
        f"and approve or deny the exception."
    )
    try:
        resp = sess.post(
            f"{base_url}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Commented on existing sign-off issue %s", issue_id)
        return True
    except Exception as exc:
        logger.error("Failed to comment on issue %s: %s", issue_id, exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create CTO sign-off Paperclip issue on lock gate failure",
    )
    parser.add_argument(
        "--gate-output", required=True,
        help="Path to JSON file with lock gate failure output",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Log actions without creating issues")
    args = parser.parse_args()

    gate_path = Path(args.gate_output)
    if not gate_path.exists():
        logger.error("Gate output file not found: %s", gate_path)
        sys.exit(1)

    with open(gate_path) as f:
        gate_data = json.load(f)

    pr_number = gate_data.get("pr_number", "unknown")
    commit_sha = gate_data.get("commit_sha", os.environ.get("GITHUB_SHA", "unknown"))
    pr_url = gate_data.get("pr_url", "")
    blocked = gate_data.get("blocked", [])

    if not blocked:
        logger.info("No blocked modules in gate output — nothing to do")
        sys.exit(0)

    dedup = dedup_key(str(pr_number), commit_sha)

    if args.dry_run:
        logger.info(
            "DRY RUN: would create sign-off issue for PR #%s (dedup=%s)",
            pr_number, dedup,
        )
        print(json.dumps({
            "pr_number": pr_number,
            "commit_sha": commit_sha,
            "dedup": dedup,
            "blocked_modules": blocked,
            "action": "create_or_comment",
        }, indent=2))
        sys.exit(0)

    sess, base_url, company_id = _session()

    existing = find_existing_signoff(base_url, company_id, sess, dedup)
    if existing:
        logger.info(
            "Sign-off issue %s already exists for PR #%s — commenting",
            existing.get("identifier", "?"), pr_number,
        )
        comment_on_existing(base_url, sess, existing, commit_sha)
        sys.exit(0)

    created = create_signoff_issue(
        base_url, company_id, sess,
        pr_number, commit_sha, pr_url,
        blocked, gate_data.get("raw_output", ""),
        dedup,
    )
    if created is None:
        sys.exit(1)

    logger.info(
        "Sign-off issue %s created for PR #%s",
        created.get("identifier", ""), pr_number,
    )


if __name__ == "__main__":
    main()
