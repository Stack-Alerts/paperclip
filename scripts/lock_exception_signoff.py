#!/usr/bin/env python3
"""Process a CTO/board sign-off on a locked-module exception request.

Triggered by RepoSteward via repository_dispatch when the CTO or board
signs off on an exception.  Adds the entry to lock_gate_exceptions.json
and pushes the change.

Usage:
    python scripts/lock_exception_signoff.py \\
        --issue-id <uuid> \\
        --module <locked-path> \\
        --scope <description> \\
        --approved-by <board|ceo-emergency> \\
        --approval-id <id> \\
        [--expires-iso <ISO8601>] \\
        [--dry-run]

Exit codes:
    0 — exception added successfully
    1 — validation error
    2 — missing arguments
"""

from __future__ import annotations

import argparse
import json
import logging

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCEPTIONS_PATH = REPO_ROOT / "lock_gate_exceptions.json"
REGISTRY_PATH = REPO_ROOT / ".module_lock_registry.json"

VALID_APPROVED_BY = {"board", "ceo-emergency"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("lock_exception_signoff")


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def validate_module(module: str) -> str | None:
    registry = load_json(REGISTRY_PATH)
    for entry in registry.get("entries", []):
        if entry["path"] == module:
            return entry.get("reason")
    return None


def validate_payload(
    module: str,
    scope: str,
    approved_by: str,
    approval_id: str,
    expires_iso: str | None,
) -> list[str]:
    errors = []

    if not module:
        errors.append("--module is required")
    else:
        reason = validate_module(module)
        if reason is None:
            errors.append(f"--module '{module}' is not in .module_lock_registry.json")

    if not scope:
        errors.append("--scope is required")

    if approved_by not in VALID_APPROVED_BY:
        errors.append(
            f"--approved-by must be one of {sorted(VALID_APPROVED_BY)}, "
            f"got '{approved_by}'",
        )

    if not approval_id:
        errors.append("--approval-id is required")

    if expires_iso:
        try:
            dt_str = expires_iso.replace("Z", "+00:00")
            dt = datetime.fromisoformat(dt_str)
            if approved_by in VALID_APPROVED_BY:
                delta = dt - datetime.now(timezone.utc)
                if delta.total_seconds() > 4 * 3600 + 60:
                    errors.append(f"expiry {expires_iso} exceeds 4-hour maximum for {approved_by}")
        except (ValueError, TypeError):
            errors.append(f"--expires-iso '{expires_iso}' is not valid ISO 8601")

    return errors


def add_exception_entry(
    module: str,
    scope: str,
    approved_by: str,
    approval_id: str,
    expires_iso: str | None,
) -> dict:
    exceptions_data = load_json(EXCEPTIONS_PATH)
    exceptions = exceptions_data.get("exceptions", [])

    entry = {
        "module": module,
        "scope_description": scope,
        "expires_iso": expires_iso,
        "approval_id": approval_id,
        "approved_by": approved_by,
    }

    exceptions.append(entry)
    exceptions_data["exceptions"] = exceptions
    write_json(EXCEPTIONS_PATH, exceptions_data)
    return entry


def commit_and_push(module: str, approval_id: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("DRY RUN: skipping git commit")
        return True

    try:
        subprocess.run(
            ["git", "add", str(EXCEPTIONS_PATH.relative_to(REPO_ROOT))],
            cwd=REPO_ROOT,
            check=True, capture_output=True,
        )

        commit_msg = (
            f"chore(lock-gate): add exception for {module} [{approval_id}]\n\n"
            f"Auto-committed by lock_exception_signoff.py."
        )
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=REPO_ROOT,
            check=True, capture_output=True,
        )

        result = subprocess.run(
            ["git", "push"],
            cwd=REPO_ROOT,
            check=True, capture_output=True, timeout=60,
        )
        logger.info("Pushed commit: %s", result.stdout.decode().strip())
        return True
    except subprocess.CalledProcessError as exc:
        logger.error("Git operation failed: %s", exc.stderr.decode())
        return False
    except subprocess.TimeoutExpired:
        logger.error("Git push timed out")
        return False


def post_paperclip_comment(issue_id: str, entry: dict, dry_run: bool) -> bool:
    if dry_run:
        logger.info("DRY RUN: would post comment to issue %s", issue_id)
        return True

    sys.path.insert(0, str(REPO_ROOT / "src"))
    try:
        from touch_index.paperclip_client import _session, _base
    except ImportError:
        logger.error("Cannot import paperclip_client — is PAPERCLIP_API_KEY set?")
        return False

    body = (
        f"**Lock Exception Approved**\n\n"
        f"An exception entry has been added to `lock_gate_exceptions.json`:\n\n"
        f"- **Module:** `{entry['module']}`\n"
        f"- **Scope:** {entry['scope_description']}\n"
        f"- **Approved by:** {entry['approved_by']}\n"
        f"- **Approval ID:** {entry['approval_id']}\n"
        f"- **Expires:** {entry['expires_iso'] or 'never (permanent)'}\n\n"
        f"The change has been committed and pushed. "
        f"PRs touching `{entry['module']}` may now merge with this exception active."
    )

    try:
        sess = _session()
        resp = sess.post(
            f"{_base()}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Posted confirmation comment on issue %s", issue_id)
        return True
    except Exception as exc:
        logger.error("Failed to post comment on issue %s: %s", issue_id, exc)
        return False


def transition_issue(issue_id: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("DRY RUN: would transition issue %s to done", issue_id)
        return True

    sys.path.insert(0, str(REPO_ROOT / "src"))
    try:
        from touch_index.paperclip_client import transition_issue_status
        transition_issue_status(issue_id, "done")
        logger.info("Transitioned issue %s to done", issue_id)
        return True
    except ImportError:
        logger.error("Cannot import paperclip_client")
        return False
    except Exception as exc:
        logger.error("Failed to transition issue %s: %s", issue_id, exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process a CTO/board sign-off on a locked-module exception",
    )
    parser.add_argument("--issue-id", required=True, help="Paperclip issue UUID")
    parser.add_argument("--module", required=True, help="Locked module path")
    parser.add_argument("--scope", required=True, help="Scope description of the change")
    parser.add_argument("--approved-by", required=True,
                        choices=sorted(VALID_APPROVED_BY),
                        help="Who approved the exception")
    parser.add_argument("--approval-id", required=True,
                        help="Approval ID or COMMENT:<url>")
    parser.add_argument("--expires-iso", default=None,
                        help="ISO 8601 expiry (null/omitted = permanent for board)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Log actions without writing or pushing")
    args = parser.parse_args()

    errors = validate_payload(
        args.module, args.scope, args.approved_by,
        args.approval_id, args.expires_iso,
    )
    if errors:
        logger.error("Validation failed:")
        for err in errors:
            logger.error("  - %s", err)
        sys.exit(1)

    entry = add_exception_entry(
        args.module, args.scope, args.approved_by,
        args.approval_id, args.expires_iso,
    )
    logger.info("Added exception entry for %s", args.module)

    if not commit_and_push(args.module, args.approval_id, args.dry_run):
        logger.error("Failed to commit and push exception entry")
        sys.exit(1)

    post_paperclip_comment(args.issue_id, entry, args.dry_run)

    transition_issue(args.issue_id, args.dry_run)

    logger.info("Exception sign-off complete for %s — issue %s", args.module, args.issue_id)


if __name__ == "__main__":
    main()
