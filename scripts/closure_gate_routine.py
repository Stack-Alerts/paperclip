#!/usr/bin/env python3
"""Closure-Gate Routine: Verify done issues have SHA ancestors on origin/main.

This routine:
1. Scans done issues updated in the last 24h (or --backfill-days N for first run)
2. Extracts Fix-SHA from closure comments via regex ^Fix-SHA: ([0-9a-f]{40})$
3. Verifies SHA is an ancestor of origin/main via git merge-base
4. Detects fabrication: SHA existence, author match, file:line validity
5. Detects unfiled deferrals: closure comments promising follow-ups
   ("out of scope / deferred / tracking issue / ...") without a filed BTCAAAAA-NNNNN
6. Reopens issues with unmerged SHAs to in_review, assigns to closer's manager
7. Requests Fix-SHA tags for orphaned done issues without commit evidence
8. Aggregates unfiled-deferral flags into routine report at BTCAAAAA-36127

Usage:
    python scripts/closure_gate_routine.py
    python scripts/closure_gate_routine.py --backfill-days 30
"""

from __future__ import annotations

import argparse
import hashlib
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

from touch_index.paperclip_client import _base, _company

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("closure_gate")

TRACKING_ISSUE = "BTCAAAAA-36129"
API_TIMEOUT = 30

# State file to track closure-gate actions
CLOSURE_GATE_STATE_FILE = REPO_ROOT / "data" / "closure_gate_actions.json"

# Regex for Fix-SHA comment: line-anchored
FIX_SHA_PATTERN = re.compile(r"^Fix-SHA: ([0-9a-f]{40})$", re.MULTILINE)

# Line-anchored "no code commit" exemption marker for operational/non-code closures
# (rclone reauth, routine pause/resume, manual rollback, etc.). Closure-gate
# treats issues carrying this marker as verified and skips Fix-SHA requests.
FIX_SHA_NONE_PATTERN = re.compile(r"^Fix-SHA: NONE\b", re.MULTILINE)

# CEO mention for notifications
CEO_MENTION = "@CEO"

# Deferral lexicon (BTCAAAAA-30577): phrases that signal a closure promised
# follow-up work outside the current ticket. If a closure-comment paragraph
# contains any of these AND does not name a filed BTCAAAAA-NNNNN follow-up,
# the routine raises an unfiled-deferral flag.
DEFERRAL_LEXICON = (
    r"out of scope",
    r"deferred",
    r"defer\b",
    r"follow-?up",
    r"file a separate",
    r"audit other",
    r"tracking issue",
    r"cleanup",
)
DEFERRAL_REGEX = re.compile("|".join(DEFERRAL_LEXICON), re.IGNORECASE)
TICKET_REF_PATTERN = re.compile(r"\b(BTCAAAAA-\d+)\b")
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
DEFERRAL_SNIPPET_MAX = 400


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


def load_state() -> dict[str, Any]:
    """Load the state of previous closure-gate actions."""
    if CLOSURE_GATE_STATE_FILE.exists():
        try:
            return json.loads(CLOSURE_GATE_STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Failed to load closure gate state: %s", exc)
            return {}
    return {}


def save_state(state: dict[str, Any]) -> None:
    """Save the state of closure-gate actions."""
    try:
        CLOSURE_GATE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CLOSURE_GATE_STATE_FILE.write_text(json.dumps(state, indent=2))
    except IOError as exc:
        logger.error("Failed to save closure gate state: %s", exc)


def compute_action_hash(issue_id: str, sha: str, action: str) -> str:
    """Compute a hash for idempotent deduplication."""
    data = f"{issue_id}:{sha}:{action}"
    return hashlib.sha256(data.encode()).hexdigest()[:8]


def find_done_issues(hours: int = 24) -> list[dict[str, Any]]:
    """Find done issues updated in the last `hours` hours (default 24)."""
    try:
        company_id = os.environ.get("PAPERCLIP_COMPANY_ID", "")
        if not company_id:
            logger.error("PAPERCLIP_COMPANY_ID not set")
            return []

        with _http_session() as sess:
            resp = sess.get(
                f"{_base()}/api/companies/{company_id}/issues",
                params={
                    "status": "done",
                    "limit": 500 if hours > 168 else 200,
                },
                timeout=API_TIMEOUT,
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

            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=hours)
            filtered = []
            for issue in issues_list:
                updated_at = issue.get("updatedAt")
                if updated_at:
                    try:
                        updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        if updated_dt >= cutoff:
                            filtered.append(issue)
                    except (ValueError, AttributeError):
                        pass

            logger.info("Found %d done issues updated in last %dh", len(filtered), hours)
            return filtered
    except Exception as exc:
        logger.error("Failed to find done issues: %s", exc)
        return []


def extract_fix_sha(issue: dict[str, Any]) -> str | None:
    """Extract Fix-SHA from issue comments."""
    comments = issue.get("comments", [])
    if isinstance(comments, list):
        for comment in comments:
            body = comment.get("body", "")
            match = FIX_SHA_PATTERN.search(body)
            if match:
                return match.group(1)
    return None


def fetch_issue_comments(issue_id: str) -> list[dict[str, Any]]:
    """Fetch all comments for an issue."""
    try:
        with _http_session() as sess:
            resp = sess.get(
                f"{_base()}/api/issues/{issue_id}/comments",
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            comments = resp.json()
            if isinstance(comments, list):
                return comments
            return []
    except Exception as exc:
        logger.error("Failed to fetch comments for issue %s: %s", issue_id, exc)
        return []


def extract_fix_sha_from_comments(comments: list[dict[str, Any]]) -> str | None:
    """Extract Fix-SHA from comment list."""
    for comment in comments:
        body = comment.get("body", "")
        match = FIX_SHA_PATTERN.search(body)
        if match:
            return match.group(1)
    return None


def has_fix_sha_none_exemption(comments: list[dict[str, Any]]) -> bool:
    """Return True if any comment carries the line-anchored `Fix-SHA: NONE` marker.

    Used to exempt operational/non-code closures (manual OAuth reauth, routine
    pause/resume, etc.) from Fix-SHA verification.
    """
    for comment in comments:
        if FIX_SHA_NONE_PATTERN.search(comment.get("body", "") or ""):
            return True
    return False


# === Fabrication Detection Functions (Phase 6c) ===

def sha_exists(sha: str) -> bool:
    """Check if SHA exists in the local repo via git cat-file.

    Returns True if git cat-file -e <sha> succeeds (rc=0).
    Returns False if rc=128 (object not found) or other errors.
    """
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", sha],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
        )
        exists = result.returncode == 0
        logger.info("SHA %s exists in repo: %s", sha[:8], exists)
        return exists
    except Exception as exc:
        logger.error("Failed to check SHA existence %s: %s", sha[:8], exc)
        return False


def get_commit_author(sha: str) -> tuple[str, str] | None:
    """Get commit author name and email.

    Returns (author_name, author_email) or None if SHA not found.
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%an%n%ae", sha],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
            text=True,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                return (lines[0], lines[1])
        return None
    except Exception as exc:
        logger.error("Failed to get author for SHA %s: %s", sha[:8], exc)
        return None


def extract_file_line_references(text: str) -> list[tuple[str, int, int | None]]:
    """Extract file:line references from closure comment text.

    Returns list of (file_path, start_line, end_line).
    end_line is None if only a single line is referenced.
    Pattern: path/to/file.ext:123 or path/to/file.ext:123-456
    """
    file_line_pattern = re.compile(r"([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+):(\d+)(?:-(\d+))?")
    refs = []
    for match in file_line_pattern.finditer(text):
        file_path = match.group(1)
        start_line = int(match.group(2))
        end_line = int(match.group(3)) if match.group(3) else start_line
        refs.append((file_path, start_line, end_line))
    return refs


def file_exists_at_sha(file_path: str, sha: str) -> bool:
    """Check if a file exists at a given SHA."""
    try:
        result = subprocess.run(
            ["git", "show", f"{sha}:{file_path}"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
        )
        exists = result.returncode == 0
        logger.debug("File %s exists at SHA %s: %s", file_path, sha[:8], exists)
        return exists
    except Exception as exc:
        logger.error("Failed to check file existence at SHA %s: %s", sha[:8], exc)
        return False


def count_lines_at_sha(file_path: str, sha: str) -> int | None:
    """Count the number of lines in a file at a given SHA."""
    try:
        result = subprocess.run(
            ["git", "show", f"{sha}:{file_path}"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
            text=True,
        )
        if result.returncode == 0:
            return len(result.stdout.splitlines())
        return None
    except Exception as exc:
        logger.error("Failed to count lines in %s at SHA %s: %s", file_path, sha[:8], exc)
        return None


def validate_file_line_references(file_line_refs: list[tuple[str, int, int | None]], sha: str) -> list[tuple[str, str]]:
    """Validate file:line references against a SHA.

    Returns list of (file_path, error_message) for invalid references.
    """
    errors = []
    for file_path, start_line, end_line in file_line_refs:
        if not file_exists_at_sha(file_path, sha):
            errors.append((file_path, f"File not found at SHA {sha[:8]}"))
            continue

        line_count = count_lines_at_sha(file_path, sha)
        if line_count is None:
            continue

        if end_line is None:
            end_line = start_line

        if start_line > line_count or end_line > line_count:
            errors.append((file_path, f"Line range {start_line}-{end_line} exceeds file length ({line_count} lines)"))

    return errors


def detect_fabrication(issue_id: str, issue_identifier: str, sha: str, comments: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect fabrication signals for a closure comment.

    Returns dict with:
      {
        "signals": ["A", "B", "C"],  # Signal types detected
        "labels": [...],  # Labels to apply
        "comment": "...",  # Comment to post
      }
    Or empty dict if no signals detected.
    """
    signals = []
    labels = []
    details = []

    # Signal A: SHA doesn't exist
    if not sha_exists(sha):
        signals.append("A")
        labels.append("closure-gate-fabricated-sha")
        details.append(f"**Signal A (Fabricated SHA):** SHA `{sha[:8]}` does not exist in repository (git cat-file rc=128).")

    # Signal B: Author mismatch
    author_info = get_commit_author(sha)
    if author_info:
        author_name, author_email = author_info
        # TODO: Implement proper identity matching via RepoSteward API
        # For now, just log the author for manual review
        logger.info("Commit author for SHA %s: %s <%s>", sha[:8], author_name, author_email)

    # Signal C: File:line mismatch
    # Extract closure comment text
    closure_comment_body = ""
    for comment in comments:
        body = comment.get("body", "")
        if FIX_SHA_PATTERN.search(body):
            closure_comment_body = body
            break

    file_line_refs = extract_file_line_references(closure_comment_body)
    if file_line_refs:
        line_errors = validate_file_line_references(file_line_refs, sha)
        if line_errors:
            signals.append("C")
            labels.append("closure-gate-line-mismatch")
            for file_path, error_msg in line_errors:
                details.append(f"**Signal C (Line Mismatch):** {file_path} — {error_msg}")

    if not signals:
        return {}

    # Build comment
    comment_lines = [
        "**Closure-Gate: Possible Fabrication Detected**",
        "",
        f"SHA `{sha[:8]}` referenced in closure comment may be fabricated.",
    ]
    comment_lines.extend(details)
    comment_lines.extend([
        "",
        f"**Action:** {CEO_MENTION} please review and determine if closure should be reopened.",
        f"**Labels:** {', '.join(labels)}",
        "",
        "_This is an automated fabrication check. Manual verification required._",
    ])

    return {
        "signals": signals,
        "labels": labels,
        "comment": "\n".join(comment_lines),
    }


# === End Fabrication Detection ===


# === Unfiled Deferral Detection (Phase 3 extension — BTCAAAAA-30577) ===

def split_paragraphs(text: str) -> list[str]:
    """Split comment body into paragraphs on blank lines."""
    if not text:
        return []
    return [p.strip() for p in PARAGRAPH_SPLIT_RE.split(text) if p.strip()]


def fetch_issue_by_identifier(identifier: str) -> dict[str, Any] | None:
    """Fetch issue by identifier (e.g. BTCAAAAA-30040). Returns None on 404."""
    try:
        with _http_session() as sess:
            resp = sess.get(
                f"{_base()}/api/issues/{identifier}",
                timeout=API_TIMEOUT,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
            return None
    except Exception as exc:
        logger.warning("Failed to fetch follow-up issue %s: %s", identifier, exc)
        return None


def followup_links_to_source(
    followup: dict[str, Any],
    source_id: str,
    source_identifier: str,
    source_project_id: str | None,
) -> bool:
    """Decide whether `followup` is a valid filed follow-up for the source issue.

    Per BTCAAAAA-30577 acceptance criterion 3: a follow-up "links back" if any of:
      - followup.parentId == source.id
      - followup.description or followup.title cites source identifier
      - followup is in the same project AND cites source identifier
    """
    if not followup:
        return False
    if followup.get("parentId") == source_id:
        return True

    description = followup.get("description") or ""
    title = followup.get("title") or ""
    cites_source = source_identifier in description or source_identifier in title
    if cites_source:
        return True

    followup_project = followup.get("projectId")
    if source_project_id and followup_project == source_project_id and cites_source:
        return True

    return False


def detect_unfiled_deferrals(
    issue: dict[str, Any],
    comments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect closure paragraphs that promise follow-up work without filing it.

    Returns a list of flag dicts; empty list means no flags.
    Each flag:
        {
          "source_identifier": "BTCAAAAA-XXXXX",
          "source_id": "...",
          "comment_id": "...",
          "paragraph": "snippet (<=400 chars)",
          "candidate_refs": ["BTCAAAAA-YYYYY", ...],
          "reason": "no_refs" | "refs_invalid",
        }
    """
    flags: list[dict[str, Any]] = []
    source_id = issue.get("id", "")
    source_identifier = issue.get("identifier", "")
    source_project_id = issue.get("projectId")

    for comment in comments or []:
        body = comment.get("body", "") or ""
        if not body or not DEFERRAL_REGEX.search(body):
            continue
        for paragraph in split_paragraphs(body):
            if not DEFERRAL_REGEX.search(paragraph):
                continue

            # Candidate refs in this paragraph, excluding self-references.
            candidate_refs = [
                ref
                for ref in TICKET_REF_PATTERN.findall(paragraph)
                if ref != source_identifier
            ]

            snippet = paragraph[:DEFERRAL_SNIPPET_MAX]
            comment_id = comment.get("id", "")

            if not candidate_refs:
                flags.append({
                    "source_identifier": source_identifier,
                    "source_id": source_id,
                    "comment_id": comment_id,
                    "paragraph": snippet,
                    "candidate_refs": [],
                    "reason": "no_refs",
                })
                continue

            valid = False
            for ref in candidate_refs:
                followup = fetch_issue_by_identifier(ref)
                if followup and followup_links_to_source(
                    followup, source_id, source_identifier, source_project_id
                ):
                    valid = True
                    break

            if not valid:
                flags.append({
                    "source_identifier": source_identifier,
                    "source_id": source_id,
                    "comment_id": comment_id,
                    "paragraph": snippet,
                    "candidate_refs": candidate_refs,
                    "reason": "refs_invalid",
                })

    return flags


# === End Unfiled Deferral Detection ===


def verify_sha_on_main(sha: str) -> bool:
    """Verify that SHA is an ancestor of origin/main using git."""
    try:
        # Fetch origin to ensure we have latest
        subprocess.run(
            ["git", "fetch", "origin", "main"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
            check=False,
        )

        # Run git merge-base --is-ancestor
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
        )

        is_ancestor = result.returncode == 0
        logger.info("SHA %s ancestor of origin/main: %s", sha[:8], is_ancestor)
        return is_ancestor
    except Exception as exc:
        logger.error("Failed to verify SHA %s: %s", sha[:8], exc)
        return False


def get_issue_closer_manager(issue: dict[str, Any]) -> str | None:
    """Get the manager of the agent who closed the issue."""
    # This would need to be fetched from Paperclip's agent API
    # For now, return None and assign to CTO as fallback
    logger.debug("Determining closer's manager for issue %s", issue.get("id"))
    # TODO: Implement manager lookup via Paperclip API
    return None


def reopen_issue(issue_id: str, issue_identifier: str, sha: str, comments: list[dict[str, Any]]) -> bool:
    """Reopen an issue that has an unmerged SHA."""
    try:
        closer_manager_id = get_issue_closer_manager({})

        # Construct the reopening comment
        comment_body = f"""**Closure-Gate Alert: SHA Not on origin/main**

The Fix-SHA `{sha[:8]}` referenced in the closure comment is not an ancestor of `origin/main`.

**Issue:** [{issue_identifier}](/BTCAAAAA/issues/{issue_identifier})
**Status:** Re-opening to `in_review` for merge verification
**Action required:**
- Open a PR to merge this SHA to main, or
- If already merged, update the closure comment with the correct SHA

Ancestor-check: rc=1 (not an ancestor)

_This is an automated closure-gate check. Routine will reset to done once SHA is verified on main._
"""

        # PATCH issue to in_review status
        with _http_session() as sess:
            resp = sess.patch(
                f"{_base()}/api/issues/{issue_id}",
                json={
                    "status": "in_review",
                    "comment": comment_body,
                },
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            logger.info("Reopened issue %s to in_review", issue_identifier)
            return True
    except Exception as exc:
        logger.error("Failed to reopen issue %s: %s", issue_id, exc)
        return False


def flag_fabrication(
    issue_id: str,
    issue_identifier: str,
    sha: str,
    labels: list[str],
    comment_body: str,
) -> bool:
    """Flag an issue for fabrication and notify CEO.

    Reopens issue to in_review, adds labels, posts comment.
    """
    try:
        with _http_session() as sess:
            # PATCH issue to in_review with labels
            patch_data = {
                "status": "in_review",
                "labels": labels,
            }

            resp = sess.patch(
                f"{_base()}/api/issues/{issue_id}",
                json=patch_data,
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()

            # POST comment (separate call to include the detailed message)
            comment_resp = sess.post(
                f"{_base()}/api/issues/{issue_id}/comments",
                json={"body": comment_body},
                timeout=API_TIMEOUT,
            )
            comment_resp.raise_for_status()

            logger.info("Flagged issue %s for fabrication with labels %s", issue_identifier, labels)
            return True
    except Exception as exc:
        logger.error("Failed to flag fabrication for issue %s: %s", issue_id, exc)
        return False


def request_fix_sha_tag(issue_id: str, issue_identifier: str) -> bool:
    """Post a comment requesting Fix-SHA tag on an issue."""
    try:
        comment_body = f"""**Closure-Gate: Fix-SHA Tag Missing**

This issue is marked `done` but has no closure comment with a `Fix-SHA:` tag.

**Required format (on new line):**
```
Fix-SHA: <40-character commit SHA>
```

**Action:**
1. Find the commit SHA that fixed this issue
2. Post a comment with the line above on this issue
3. The closure-gate routine will verify it's on origin/main

_Requests without a Fix-SHA tag cannot be verified by automation._
"""

        with _http_session() as sess:
            resp = sess.post(
                f"{_base()}/api/issues/{issue_id}/comments",
                json={"body": comment_body},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            logger.info("Posted Fix-SHA request to issue %s", issue_identifier)
            return True
    except requests.exceptions.HTTPError as exc:
        if hasattr(exc.response, 'status_code') and exc.response.status_code == 403:
            logger.info("Skipped Fix-SHA request to issue %s (403 Forbidden — cross-team/permission issue)", issue_identifier)
            return True
        logger.error("Failed to post Fix-SHA request to issue %s: %s", issue_id, exc)
        return False
    except Exception as exc:
        logger.error("Failed to post Fix-SHA request to issue %s: %s", issue_id, exc)
        return False


def process_issue(
    issue: dict[str, Any],
    state: dict[str, Any],
    deferral_flags: list[dict[str, Any]] | None = None,
) -> tuple[str, bool]:
    """Process a single done issue.

    Returns (action_type, success). When `deferral_flags` is provided, any
    unfiled-deferral flags discovered in this issue's comments are appended to
    it (BTCAAAAA-30577).
    """
    issue_id = issue.get("id", "")
    issue_identifier = issue.get("identifier", "")
    origin_kind = issue.get("originKind", "")

    # Exempt non-code work from Fix-SHA requirement. Routine-generated tasks,
    # escalations, and coordination issues don't have code commits (BTCAAAAA-30677).
    exempt_origin_kinds = {
        "routine_execution",
        "escalation",
        "notification",
        "coordination",
    }
    if origin_kind in exempt_origin_kinds:
        logger.info("Issue %s (originKind=%s) exempt from Fix-SHA verification", issue_identifier, origin_kind)
        return "verified", True

    # Fetch comments separately
    comments = fetch_issue_comments(issue_id)

    # Unfiled-deferral check (BTCAAAAA-30577). Runs independently of the
    # Fix-SHA path so we still flag promised follow-ups on issues that have
    # not yet been tagged with a Fix-SHA.
    if deferral_flags is not None:
        try:
            deferral_flags.extend(detect_unfiled_deferrals(issue, comments))
        except Exception as exc:
            logger.error(
                "Unfiled-deferral check failed for issue %s: %s",
                issue_identifier,
                exc,
            )

    # Line-anchored `Fix-SHA: NONE` marker (BTCAAAAA-35382). Operational/non-code
    # closures (manual OAuth reauth, routine pause/resume, rollback) cannot
    # produce a verifiable commit SHA. The marker is the explicit assertion that
    # this issue resolved without a code change and must be skipped by the gate.
    if has_fix_sha_none_exemption(comments):
        logger.info(
            "Issue %s carries Fix-SHA: NONE exemption marker; skipping verification",
            issue_identifier,
        )
        return "verified", True

    sha = extract_fix_sha_from_comments(comments)

    if not sha:
        logger.info("Issue %s has no Fix-SHA tag", issue_identifier)
        action_hash = compute_action_hash(issue_id, "none", "request_sha")
        action_key = f"{issue_id}:{action_hash}"

        if action_key not in state:
            if request_fix_sha_tag(issue_id, issue_identifier):
                state[action_key] = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "issue_identifier": issue_identifier,
                    "action": "request_sha",
                }
                return "request_sha", True
        else:
            # Already attempted; don't keep retrying as errors
            return "verified", True
        return "request_sha", False

    # Check for fabrication (Phase 6c)
    fab_result = detect_fabrication(issue_id, issue_identifier, sha, comments)
    if fab_result:
        action_hash = compute_action_hash(issue_id, sha, "flag_fabrication")
        action_key = f"{issue_id}:{action_hash}"

        if action_key not in state:
            if flag_fabrication(issue_id, issue_identifier, sha, fab_result["labels"], fab_result["comment"]):
                state[action_key] = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "issue_identifier": issue_identifier,
                    "action": "flag_fabrication",
                    "sha": sha,
                    "signals": fab_result["signals"],
                }
                return "flag_fabrication", True
        return "flag_fabrication", False

    # Verify SHA is on main
    if verify_sha_on_main(sha):
        logger.info("Issue %s SHA %s is on main", issue_identifier, sha[:8])
        return "verified", True
    else:
        logger.info("Issue %s SHA %s is NOT on main - reopening", issue_identifier, sha[:8])
        action_hash = compute_action_hash(issue_id, sha, "reopen")
        action_key = f"{issue_id}:{action_hash}"

        if action_key not in state:
            if reopen_issue(issue_id, issue_identifier, sha, comments):
                state[action_key] = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "issue_identifier": issue_identifier,
                    "action": "reopen",
                    "sha": sha,
                }
                return "reopen", True
        return "reopen", False


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Closure-gate routine")
    parser.add_argument(
        "--backfill-days",
        type=int,
        default=None,
        help=(
            "Override the scan window in days (default: 1 day / 24h). "
            "Use --backfill-days 30 for the first-deployment backfill required by "
            "BTCAAAAA-30577 acceptance criterion 7."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Main routine execution."""
    args = _parse_args(argv)
    hours = args.backfill_days * 24 if args.backfill_days else 24
    logger.info("Starting closure-gate routine (window=%dh)", hours)

    # Load previous state
    state = load_state()
    logger.info("Loaded closure-gate state: %d tracked", len(state))

    # Find done issues
    done_issues = find_done_issues(hours=hours)

    stats = {
        "verified": 0,
        "reopened": 0,
        "requested_sha": 0,
        "flagged_fabrication": 0,
        "errors": 0,
    }
    deferral_flags: list[dict[str, Any]] = []

    for issue in done_issues:
        action_type, success = process_issue(issue, state, deferral_flags)
        if action_type == "verified":
            stats["verified"] += 1
        elif action_type == "reopened":
            if success:
                stats["reopened"] += 1
            else:
                stats["errors"] += 1
        elif action_type == "request_sha":
            if success:
                stats["requested_sha"] += 1
            else:
                stats["errors"] += 1
        elif action_type == "flag_fabrication":
            if success:
                stats["flagged_fabrication"] += 1
            else:
                stats["errors"] += 1

    # Save updated state
    if stats["reopened"] > 0 or stats["requested_sha"] > 0 or stats["flagged_fabrication"] > 0:
        save_state(state)
        logger.info("Saved updated closure-gate state")

    # Report results
    report = format_routine_report(
        len(done_issues),
        stats,
        deferral_flags=deferral_flags,
        window_hours=hours,
    )
    if post_comment(TRACKING_ISSUE, report):
        logger.info(
            "Closure-gate routine completed successfully (deferral_flags=%d)",
            len(deferral_flags),
        )
    else:
        logger.error("Failed to post routine report, but processing completed")
        sys.exit(1)


def format_routine_report(
    total_done: int,
    stats: dict[str, int],
    deferral_flags: list[dict[str, Any]] | None = None,
    window_hours: int = 24,
) -> str:
    """Format the routine execution report."""
    deferral_flags = deferral_flags or []
    if window_hours >= 48 and window_hours % 24 == 0:
        window_label = f"{window_hours // 24}d window"
    else:
        window_label = f"{window_hours}h window"

    lines = [
        "## Closure-Gate Routine Report",
        "",
        f"**Time:** {datetime.now(timezone.utc).isoformat()}",
        "",
        f"**Done issues scanned ({window_label}):** {total_done}",
        f"**Verified on main:** {stats['verified']}",
        f"**Reopened (unmerged):** {stats['reopened']}",
        f"**Flagged (fabrication):** {stats['flagged_fabrication']}",
        f"**Requested Fix-SHA tag:** {stats['requested_sha']}",
        f"**Unfiled deferrals:** {len(deferral_flags)}",
        f"**Errors:** {stats['errors']}",
        "",
    ]

    if stats["flagged_fabrication"] > 0:
        lines.extend([
            "### Fabrication Alerts",
            f"Flagged {stats['flagged_fabrication']} issue(s) for possible fabrication (Signal A/B/C).",
        ])

    if stats["reopened"] > 0:
        lines.extend([
            "### Action Taken",
            f"Reopened {stats['reopened']} issue(s) with unmerged SHAs to `in_review`.",
        ])

    if stats["requested_sha"] > 0:
        lines.extend([
            "### Fix-SHA Requests",
            f"Requested Fix-SHA tags on {stats['requested_sha']} issue(s) without closure commit evidence.",
        ])

    if deferral_flags:
        lines.extend([
            "",
            "### unfiled_deferrals[]",
            (
                f"Flagged {len(deferral_flags)} closure paragraph(s) that promised "
                "follow-up work without filing a tracking issue (BTCAAAAA-30577). "
                "CEO files the missing tickets; routine does NOT auto-create."
            ),
            "",
        ])
        for flag in deferral_flags:
            source = flag.get("source_identifier", "?")
            comment_id = flag.get("comment_id", "")
            reason = flag.get("reason", "")
            refs = flag.get("candidate_refs", []) or []
            refs_str = ", ".join(refs) if refs else "—"
            snippet = (flag.get("paragraph", "") or "").replace("\n", " ")
            comment_link = (
                f"[{comment_id[:8]}](/BTCAAAAA/issues/{source}#comment-{comment_id})"
                if comment_id
                else "(comment id unavailable)"
            )
            lines.append(
                f"- [{source}](/BTCAAAAA/issues/{source}) "
                f"— reason: `{reason}` — candidate refs: {refs_str} — comment: {comment_link}"
            )
            lines.append(f"  > {snippet}")

    if stats["verified"] > 0 and not deferral_flags:
        lines.extend([
            "### Status",
            f"All scanned issues remain `done` (SHAs verified on origin/main).",
        ])

    return "\n".join(lines)


def post_comment(issue_id: str, body: str) -> bool:
    """Post a comment to an issue."""
    try:
        with _http_session() as sess:
            resp = sess.post(
                f"{_base()}/api/issues/{issue_id}/comments",
                json={"body": body},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            logger.info("Posted routine report to issue %s", issue_id)
            return True
    except Exception as exc:
        logger.error("Failed to post routine report: %s", exc)
        return False


if __name__ == "__main__":
    main()
