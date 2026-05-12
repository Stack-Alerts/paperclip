#!/usr/bin/env python3
"""
Apply branch protection rules to the default branch via GitHub API.

Usage:
    GITHUB_TOKEN=ghp_xxx python scripts/setup_branch_protection.py

Requires a token with Administration: Write scope on the repository.
"""

import json
import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("setup_branch_protection")

REPO = "Stack-Alerts/BTC-Trade-Engine-PaperClip"
BRANCH = "main"

PROTECTION_RULES = {
    "required_status_checks": {
        "strict": True,
        "checks": [
            {"context": "Ruff lint (no-print + datetime)"},
            {"context": "pytest + coverage gate"},
            {"context": "Module lock gate"},
            {"context": "Real-data regression (BTCAAAAA-745)"},
        ],
    },
    "enforce_admins": True,
    "required_pull_request_reviews": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": False,
    },
    "restrictions": None,
    "required_linear_history": False,
    "allow_force_pushes": False,
    "allow_deletions": False,
    "block_creations": False,
    "required_conversation_resolution": True,
    "lock_branch": False,
    "allow_fork_syncing": True,
}


def _check_protection(token: str) -> bool:
    result = subprocess.run(
        [
            "gh", "api",
            f"repos/{REPO}/branches/{BRANCH}/protection",
            "--jq", ".required_pull_request_reviews.required_approving_review_count",
        ],
        capture_output=True, text=True, env={**os.environ, "GH_TOKEN": token},
    )
    if result.returncode == 0:
        log.info("Branch protection already applied (reviews: %s). Skipping.", result.stdout.strip())
        return True
    return False


def _apply_protection(token: str) -> None:
    log.info("No branch protection found on %s/%s. Applying...", REPO, BRANCH)
    result = subprocess.run(
        ["gh", "api", "--method", "PUT", f"repos/{REPO}/branches/{BRANCH}/protection", "--input", "-"],
        input=json.dumps(PROTECTION_RULES),
        capture_output=True, text=True,
        env={**os.environ, "GH_TOKEN": token},
    )
    if result.returncode != 0:
        log.error("Failed to apply branch protection:\n%s", result.stderr)
        sys.exit(1)
    log.info("Branch protection applied successfully.")
    log.info(json.dumps(json.loads(result.stdout), indent=2))


def _verify(token: str) -> None:
    result = subprocess.run(
        [
            "gh", "api",
            f"repos/{REPO}/branches/{BRANCH}/protection",
            "--jq", "{enabled: true, reviews: .required_pull_request_reviews.required_approving_review_count}",
        ],
        capture_output=True, text=True,
        env={**os.environ, "GH_TOKEN": token},
    )
    if result.returncode == 0:
        log.info("Verification: %s", result.stdout.strip())


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log.error("GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    if _check_protection(token):
        return

    _apply_protection(token)
    _verify(token)


if __name__ == "__main__":
    main()
