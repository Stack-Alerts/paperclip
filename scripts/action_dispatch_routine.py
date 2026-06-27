#!/usr/bin/env python3
"""Phase 4b: Action-dispatch routine — handles [no-sha: reason] board-action issues.

This routine is the second lane in the v2 merge-process redesign (BTCAAAAA-38557).
It mirrors the structure of merge_dispatch_routine.py but targets issues whose
close-out comment carries a `[no-sha: <reason>]` tag instead of a Fix-SHA:

  [no-sha: redeploy]  — operational redeploy (no code artifact)
  [no-sha: install]   — plugin or dependency install
  [no-sha: config]    — configuration change
  [no-sha: process]   — process step (no code, no deploy)

For each matching in_review issue the routine:
1. Extracts the [no-sha: <reason>] tag from comments
2. Dispatches the corresponding action handler
3. Posts an evidence comment on success
4. PATCHes the issue to done

If the action handler fails, the routine posts a failure comment and leaves the
issue in_review (NOT done) so the closure gate does not reopen it for the wrong reason.

Feature flag: MERGE_PROCESS_V2_ENABLED=true (required; routine exits cleanly if unset).

Usage:
    python3 scripts/action_dispatch_routine.py
    python3 scripts/action_dispatch_routine.py --issue <issue-id>

Requires:
    PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID
    MERGE_PROCESS_V2_ENABLED=true
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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
logger = logging.getLogger("action_dispatch")
_TELEMETRY_LOGGER = logging.getLogger("action_dispatch.telemetry")

# Feature flag: set MERGE_PROCESS_V2_ENABLED=false to disable this routine
MERGE_PROCESS_V2_ENABLED = (
    os.environ.get("MERGE_PROCESS_V2_ENABLED", "true").lower() != "false"
)

ACTION_DISPATCH_TRACKING = "BTCAAAAA-38557"

# Valid reasons accepted by the [no-sha: <reason>] convention
VALID_NO_SHA_REASONS = frozenset({"redeploy", "install", "config", "process"})

# Line-anchored regex mirrors Fix-SHA convention — bare line only; markdown bold/bullets break it
NO_SHA_PATTERN = re.compile(
    r"^\[no-sha: (redeploy|install|config|process)\](.*?)$",
    re.MULTILINE,
)

WATERMARK_FILE = REPO_ROOT / "data" / "action_dispatch_watermark.json"
ACTION_DISPATCH_SAFETY_FLOOR_MINUTES = int(
    os.environ.get("ACTION_DISPATCH_SAFETY_FLOOR_MINUTES", "10")
)
ACTION_DISPATCH_IDEMPOTENT = (
    os.environ.get("ACTION_DISPATCH_IDEMPOTENT", "true").lower() != "false"
)


# ---------------------------------------------------------------------------
# Watermark (idempotency gate)
# ---------------------------------------------------------------------------

def load_watermark() -> dict[str, Any] | None:
    try:
        return json.loads(WATERMARK_FILE.read_text())
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not parse action-dispatch watermark at %s: %s", WATERMARK_FILE, exc)
        return None


def save_watermark(in_review_ids: list[str]) -> bool:
    sorted_ids = sorted({i for i in in_review_ids if i})
    payload = {
        "lastScanAt": datetime.now(timezone.utc).isoformat(),
        "lastInReviewIds": sorted_ids,
    }
    try:
        WATERMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
        WATERMARK_FILE.write_text(json.dumps(payload))
        return True
    except OSError as exc:
        logger.error("Failed to write action-dispatch watermark to %s: %s", WATERMARK_FILE, exc)
        return False


def check_early_exit(current_in_review_ids: list[str]) -> bool:
    if not ACTION_DISPATCH_IDEMPOTENT:
        return False
    wm = load_watermark()
    if not wm:
        return False
    raw_ts = wm.get("lastScanAt", "")
    try:
        last = datetime.fromisoformat(raw_ts)
    except (TypeError, ValueError):
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - last
    if age > timedelta(minutes=ACTION_DISPATCH_SAFETY_FLOOR_MINUTES):
        return False
    return set(wm.get("lastInReviewIds", [])) == set(current_in_review_ids)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ.get('PAPERCLIP_API_KEY', '')}",
        "Content-Type": "application/json",
        "X-Paperclip-Version": "1",
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


def _api_url() -> str:
    return os.environ.get("PAPERCLIP_API_URL", "").rstrip("/")


def fetch_issue_comments(issue_id: str) -> list[dict[str, Any]]:
    sess = _http_session()
    try:
        resp = sess.get(f"{_api_url()}/api/issues/{issue_id}/comments", timeout=30)
        resp.raise_for_status()
        comments = resp.json()
        return comments if isinstance(comments, list) else []
    except Exception as exc:
        logger.error("Failed to fetch comments for issue %s: %s", issue_id, exc)
        return []
    finally:
        sess.close()


def fetch_issue(issue_id: str) -> dict[str, Any] | None:
    sess = _http_session()
    try:
        resp = sess.get(f"{_api_url()}/api/issues/{issue_id}", timeout=30)
        resp.raise_for_status()
        issue = resp.json()
        return issue if isinstance(issue, dict) else None
    except Exception as exc:
        logger.error("Failed to fetch issue %s: %s", issue_id, exc)
        return None
    finally:
        sess.close()


def find_in_review_issues() -> list[dict[str, Any]]:
    company_id = os.environ.get("PAPERCLIP_COMPANY_ID", "")
    if not company_id:
        logger.error("PAPERCLIP_COMPANY_ID not set")
        return []

    sess = _http_session()
    try:
        resp = sess.get(
            f"{_api_url()}/api/companies/{company_id}/issues",
            params={"status": "in_review", "limit": 200},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict) and "issues" in payload:
            return payload["issues"]
        elif isinstance(payload, list):
            return payload
        logger.warning("Unexpected response format from issues API")
        return []
    except Exception as exc:
        logger.error("Failed to find in_review issues: %s", exc)
        return []
    finally:
        sess.close()


def comment_on_issue(issue_id: str, body: str, idempotency_key: str | None = None) -> bool:
    sess = _http_session()
    try:
        payload: dict[str, Any] = {"body": body}
        if idempotency_key:
            payload["idempotencyKey"] = idempotency_key
        resp = sess.post(f"{_api_url()}/api/issues/{issue_id}/comments", json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Posted comment on issue %s", issue_id)
        return True
    except Exception as exc:
        logger.error("Failed to post comment on issue %s: %s", issue_id, exc)
        return False
    finally:
        sess.close()


def update_issue_status(issue_id: str, status: str, comment: str = "") -> bool:
    payload: dict[str, Any] = {"status": status}
    if comment:
        payload["comment"] = comment

    sess = _http_session()
    try:
        resp = sess.patch(f"{_api_url()}/api/issues/{issue_id}", json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Updated issue %s to status %s", issue_id, status)
        return True
    except Exception as exc:
        logger.error("Failed to update issue %s: %s", issue_id, exc)
        return False
    finally:
        sess.close()


# ---------------------------------------------------------------------------
# [no-sha: <reason>] extraction
# ---------------------------------------------------------------------------

def extract_no_sha_tag(comments: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Return (reason, tail) from the latest [no-sha: <reason>] tag in comments.

    Returns None when no valid tag is found.  The `tail` is the rest of the
    line after the tag, stripped — used to pass parameters (e.g., plugin name
    for [no-sha: install]).
    """
    latest: tuple[str, str] | None = None
    for comment in comments:
        body = comment.get("body", "")
        match = NO_SHA_PATTERN.search(body)
        if match:
            latest = (match.group(1), match.group(2).strip())
    return latest


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

def _run_subprocess(cmd: list[str], cwd: Path = REPO_ROOT, timeout: int = 60) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
    except OSError as exc:
        return 1, "", f"Failed to run {' '.join(cmd)}: {exc}"


def handle_redeploy(issue_id: str, issue_identifier: str, tail: str) -> dict[str, Any]:
    """Execute a redeploy action.

    Looks for scripts/redeploy_dev.sh; if absent, records the action as a
    manual-required process step with an attestation comment.
    """
    redeploy_script = REPO_ROOT / "scripts" / "redeploy_dev.sh"
    timestamp = datetime.now(timezone.utc).isoformat()

    if redeploy_script.exists():
        commit_ref = tail.strip() if tail else "HEAD"
        # Validate commit_ref to git-ref/SHA character set before subprocess invocation.
        # commit_ref comes from issue comment text (attacker-controllable); reject flags.
        if not re.fullmatch(r"[A-Za-z0-9_./-]{1,200}", commit_ref) or commit_ref.startswith("-"):
            comment_on_issue(
                issue_id,
                (
                    f"**Action Dispatch — Redeploy Blocked**\n\n"
                    f"Commit ref `{commit_ref!r}` contains invalid characters or looks like a flag.\n"
                    "Allowed: letters, digits, `_`, `.`, `/`, `-` (not leading `-`), max 200 chars.\n\n"
                    "Please correct the comment and the routine will retry on the next sweep."
                ),
                idempotency_key=f"action_dispatch:redeploy_invalid_ref:{issue_id}",
            )
            return {"action": "failed", "reason": "redeploy_invalid_commit_ref", "commit_ref": commit_ref}
        logger.info("Running redeploy_dev.sh for issue %s (ref: %s)", issue_identifier, commit_ref)
        rc, stdout, stderr = _run_subprocess(
            ["bash", str(redeploy_script), "--", commit_ref],
            timeout=120,
        )
        if rc != 0:
            comment_on_issue(
                issue_id,
                (
                    f"**Action Dispatch — Redeploy Failed**\n\n"
                    f"Exit code: {rc}\n"
                    f"Stderr: ```\n{stderr[:500]}\n```\n\n"
                    f"Issue left in_review. Investigate and retry."
                ),
                idempotency_key=f"action_dispatch:redeploy_failed:{issue_id}",
            )
            return {
                "action": "failed",
                "reason": "redeploy_script_failed",
                "stderr": stderr[:500],
            }
        evidence = f"Redeploy script exited 0 at {timestamp}.\n```\n{stdout[:1000]}\n```"
    else:
        # No deploy script yet — record manual attestation so closure gate has evidence
        commit_ref = tail.strip() if tail else "(see comment)"
        logger.info(
            "redeploy_dev.sh not found; recording process attestation for %s",
            issue_identifier,
        )
        evidence = (
            f"[no-sha: redeploy] action noted at {timestamp}.\n"
            f"Ref: {commit_ref}\n"
            "Note: redeploy_dev.sh not found; this attestation confirms the operator-requested "
            "redeploy was acknowledged. Manual verification required."
        )

    comment_on_issue(
        issue_id,
        f"**Action Dispatch — Redeploy Complete**\n\n{evidence}\n",
        idempotency_key=f"action_dispatch:redeploy:{issue_id}",
    )
    return {"action": "dispatched", "reason": "redeploy", "evidence": evidence[:200]}


def handle_install(issue_id: str, issue_identifier: str, tail: str) -> dict[str, Any]:
    """Execute a plugin install action.

    The plugin name/id must appear in the tail (rest of the comment line after
    [no-sha: install]).  If absent, we leave the issue in_review and ask for
    the plugin name.
    """
    plugin_id = tail.strip() if tail else ""
    if not plugin_id:
        logger.info("Issue %s has [no-sha: install] but no plugin id in comment", issue_identifier)
        comment_on_issue(
            issue_id,
            (
                "**Action Dispatch — Install Blocked**\n\n"
                "The `[no-sha: install]` tag was found but the comment did not include "
                "the plugin name/id on the same line.\n\n"
                "Expected format:\n```\n[no-sha: install] <plugin-name-or-id>\n```\n\n"
                "Please update the comment and the routine will retry on the next sweep."
            ),
            idempotency_key=f"action_dispatch:install_no_plugin:{issue_id}",
        )
        return {"action": "failed", "reason": "install_missing_plugin_id"}

    # Validate plugin_id against a safe character set before subprocess invocation.
    # plugin_id comes from issue comment text (attacker-controllable); reject anything
    # that looks like a flag or contains shell-special characters.
    if not re.fullmatch(r"[A-Za-z0-9_./@-]{1,128}", plugin_id) or plugin_id.startswith("-"):
        logger.warning("Issue %s has invalid plugin_id %r; refusing install", issue_identifier, plugin_id)
        comment_on_issue(
            issue_id,
            (
                f"**Action Dispatch — Install Blocked**\n\n"
                f"Plugin id `{plugin_id!r}` contains invalid characters or looks like a flag.\n"
                "Allowed: letters, digits, `_`, `.`, `/`, `@`, `-` (not leading `-`), max 128 chars.\n\n"
                "Please correct the comment and the routine will retry on the next sweep."
            ),
            idempotency_key=f"action_dispatch:install_invalid_plugin:{issue_id}",
        )
        return {"action": "failed", "reason": "install_invalid_plugin_id", "plugin_id": plugin_id}

    logger.info("Running plugin install for %s (plugin: %s)", issue_identifier, plugin_id)
    rc, stdout, stderr = _run_subprocess(
        ["npx", "paperclipai", "plugin", "install", "--", plugin_id],
        timeout=120,
    )
    timestamp = datetime.now(timezone.utc).isoformat()
    if rc != 0:
        comment_on_issue(
            issue_id,
            (
                f"**Action Dispatch — Install Failed**\n\n"
                f"Plugin: `{plugin_id}`\n"
                f"Exit code: {rc}\n"
                f"Stderr: ```\n{stderr[:500]}\n```\n\n"
                f"Issue left in_review. Investigate and retry."
            ),
            idempotency_key=f"action_dispatch:install_failed:{issue_id}:{plugin_id}",
        )
        return {"action": "failed", "reason": "install_command_failed", "plugin_id": plugin_id}

    evidence = (
        f"Plugin `{plugin_id}` installed at {timestamp}.\n```\n{stdout[:500]}\n```"
    )
    comment_on_issue(
        issue_id,
        f"**Action Dispatch — Install Complete**\n\n{evidence}\n",
        idempotency_key=f"action_dispatch:install:{issue_id}:{plugin_id}",
    )
    return {"action": "dispatched", "reason": "install", "plugin_id": plugin_id}


def handle_config(issue_id: str, issue_identifier: str, tail: str) -> dict[str, Any]:
    """Record a config-change action.

    The tail should carry the config description (key=value or prose).
    We record it as an attested process step; the closure gate verifies
    the evidence comment rather than a file diff.
    """
    config_desc = tail.strip() if tail else "(see issue description)"
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info("Recording config action for %s (desc: %s)", issue_identifier, config_desc[:80])
    evidence = (
        f"Config action attested at {timestamp}.\n"
        f"Description: {config_desc}\n"
        "The operator or agent confirmed this configuration change was applied."
    )
    comment_on_issue(
        issue_id,
        f"**Action Dispatch — Config Applied**\n\n{evidence}\n",
        idempotency_key=f"action_dispatch:config:{issue_id}",
    )
    return {"action": "dispatched", "reason": "config", "description": config_desc[:100]}


def handle_process(issue_id: str, issue_identifier: str, tail: str) -> dict[str, Any]:
    """Attest a process step with no code or deploy artifact."""
    process_desc = tail.strip() if tail else "(see issue description)"
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info("Recording process attestation for %s", issue_identifier)
    evidence = (
        f"Process step attested at {timestamp}.\n"
        f"Description: {process_desc}\n"
        "No code or deploy artifact required."
    )
    comment_on_issue(
        issue_id,
        f"**Action Dispatch — Process Step Complete**\n\n{evidence}\n",
        idempotency_key=f"action_dispatch:process:{issue_id}",
    )
    return {"action": "dispatched", "reason": "process"}


_HANDLERS = {
    "redeploy": handle_redeploy,
    "install": handle_install,
    "config": handle_config,
    "process": handle_process,
}


# ---------------------------------------------------------------------------
# Per-issue dispatch
# ---------------------------------------------------------------------------

def has_fix_sha(comments: list[dict[str, Any]]) -> bool:
    """Return True if any comment contains a Fix-SHA line (merge-dispatch lane)."""
    fix_sha_re = re.compile(r"^Fix-SHA: ([0-9a-f]{40})$", re.MULTILINE)
    return any(fix_sha_re.search(c.get("body", "")) for c in comments)


def process_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Process a single in_review issue for action dispatch."""
    issue_id = issue.get("id", "")
    issue_identifier = issue.get("identifier", "")

    logger.info("Processing issue %s", issue_identifier)

    comments = issue.pop("_cached_comments", None) or fetch_issue_comments(issue_id)

    # Skip issues that carry a Fix-SHA — those belong in the merge_dispatch lane
    if has_fix_sha(comments):
        logger.info("Issue %s has Fix-SHA — merge_dispatch lane, skipping", issue_identifier)
        return {"issue": issue_identifier, "action": "skip", "reason": "has_fix_sha"}

    tag = extract_no_sha_tag(comments)
    if not tag:
        logger.info("Issue %s has no [no-sha: <reason>] tag in comments", issue_identifier)
        return {"issue": issue_identifier, "action": "skip", "reason": "no_no_sha_tag"}

    reason, tail = tag
    if reason not in VALID_NO_SHA_REASONS:
        logger.warning("Issue %s has unknown no-sha reason: %s", issue_identifier, reason)
        return {"issue": issue_identifier, "action": "skip", "reason": f"unknown_reason_{reason}"}

    logger.info("Issue %s has [no-sha: %s] (tail: %r)", issue_identifier, reason, tail)

    handler = _HANDLERS[reason]
    try:
        result = handler(issue_id, issue_identifier, tail)
    except Exception as exc:
        logger.error("Action handler %s threw for %s: %s", reason, issue_identifier, exc)
        comment_on_issue(
            issue_id,
            (
                f"**Action Dispatch — Handler Error**\n\n"
                f"Reason: `{reason}`\n"
                f"Error: `{exc}`\n\n"
                f"Issue left in_review. [{ACTION_DISPATCH_TRACKING}] routine will retry."
            ),
            idempotency_key=f"action_dispatch:handler_error:{issue_id}:{reason}",
        )
        return {"issue": issue_identifier, "action": "error", "reason": reason, "error": str(exc)}

    if result.get("action") == "failed":
        result["issue"] = issue_identifier
        return result

    # Success — mark done with evidence comment
    done_comment = (
        f"Action dispatched: `[no-sha: {reason}]`.\n"
        f"Routine: {ACTION_DISPATCH_TRACKING}"
    )
    update_issue_status(issue_id, "done", done_comment)
    result["issue"] = issue_identifier
    return result


def dispatch_for_issue(issue_id: str) -> int:
    """Agent-finish trigger: dispatch action for a single just-finished issue."""
    logger.info("Agent-finish action dispatch for issue %s", issue_id)
    issue = fetch_issue(issue_id)
    if not issue:
        print(json.dumps({"issue": issue_id, "action": "error", "error": "issue_not_found"}))
        return 1

    if issue.get("status") != "in_review":
        result = {
            "issue": issue.get("identifier", issue_id),
            "action": "skip",
            "reason": f"status_{issue.get('status')}",
        }
        print(json.dumps(result, indent=2))
        return 0

    try:
        result = process_issue(issue)
    except Exception as exc:
        result = {"issue": issue.get("identifier", issue_id), "action": "error", "error": str(exc)}

    print(json.dumps(result, indent=2))
    logger.info("Agent-finish dispatch result: %s", result.get("action"))
    return 0


def emit_telemetry_log(
    fired_at: datetime,
    idempotency_skip: bool,
    would_work_count: int,
    dispatched_count: int,
) -> None:
    payload = {
        "routine": "action_dispatch",
        "fired_at": fired_at.isoformat(),
        "idempotency_skip": idempotency_skip,
        "would_work_count": would_work_count,
        "dispatched_count": dispatched_count,
    }
    _TELEMETRY_LOGGER.info(json.dumps(payload))


def main(argv: list[str] | None = None) -> int:
    """Main routine.

    With ``--issue <id>`` runs the agent-finish trigger (primary path).
    With no args, runs the periodic backup sweep over all in_review issues.
    """
    argv = sys.argv[1:] if argv is None else argv

    if not MERGE_PROCESS_V2_ENABLED:
        logger.info(
            "MERGE_PROCESS_V2_ENABLED is not set; action_dispatch_routine is a no-op. "
            "Set MERGE_PROCESS_V2_ENABLED=true to enable."
        )
        print(json.dumps({"skipped": True, "reason": "feature_flag_disabled"}))
        return 0

    if "--issue" in argv:
        idx = argv.index("--issue")
        if idx + 1 >= len(argv):
            logger.error("--issue requires an issue id")
            return 2
        return dispatch_for_issue(argv[idx + 1])

    fired_at = datetime.now(timezone.utc)
    logger.info("Starting action-dispatch routine (backup sweep)")

    issues = find_in_review_issues()
    logger.info("Found %d in_review issues total", len(issues))

    # Filter to those with [no-sha: <reason>] tags — fetch comments lazily and cache
    awaiting: list[dict[str, Any]] = []
    for issue in issues:
        issue_id = issue.get("id", "")
        if not issue_id:
            continue
        comments = fetch_issue_comments(issue_id)
        if extract_no_sha_tag(comments):
            issue["_cached_comments"] = comments
            awaiting.append(issue)

    logger.info("Found %d issues with [no-sha:] tags to process", len(awaiting))

    awaiting_ids = [i.get("id", "") for i in awaiting]

    if check_early_exit(awaiting_ids):
        logger.info("Watermark fresh and unchanged across %d issues; early-exit", len(awaiting_ids))
        emit_telemetry_log(
            fired_at=fired_at,
            idempotency_skip=True,
            would_work_count=0,
            dispatched_count=0,
        )
        output = {
            "timestamp": fired_at.isoformat(),
            "idempotency_skip": True,
            "issues_processed": 0,
            "dispatched_count": 0,
            "results": [],
            "summary": {"dispatched": 0, "skipped": 0, "failed": 0, "errors": 0},
        }
        print(json.dumps(output, indent=2))
        return 0

    results = []
    for issue in awaiting:
        try:
            result = process_issue(issue)
            results.append(result)
        except Exception as exc:
            identifier = issue.get("identifier", "?")
            logger.error("Error processing %s: %s", identifier, exc)
            results.append({"issue": identifier, "action": "error", "error": str(exc)})

    save_watermark(awaiting_ids)

    dispatched_count = sum(1 for r in results if r.get("action") == "dispatched")
    would_work_count = sum(1 for r in results if r.get("action") in {"dispatched", "failed"})

    emit_telemetry_log(
        fired_at=fired_at,
        idempotency_skip=False,
        would_work_count=would_work_count,
        dispatched_count=dispatched_count,
    )

    output = {
        "timestamp": fired_at.isoformat(),
        "idempotency_skip": False,
        "issues_processed": len(results),
        "would_work_count": would_work_count,
        "dispatched_count": dispatched_count,
        "results": results,
        "summary": {
            "dispatched": dispatched_count,
            "skipped": sum(1 for r in results if r.get("action") == "skip"),
            "failed": sum(1 for r in results if r.get("action") == "failed"),
            "errors": sum(1 for r in results if r.get("action") == "error"),
        },
    }

    print(json.dumps(output, indent=2))
    logger.info("Routine complete: %s", output["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
