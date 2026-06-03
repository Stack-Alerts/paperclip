#!/usr/bin/env python3
"""
Token-Gap Escalation Routine — v2 with blocker-chain suppression.

Detects and escalates REAL token-gap blockers (GitHub auth issues) by verifying
that the blocking issue actually has auth-related causes, not just checking
block duration alone.

Suppression rules (evaluated before posting any comment):
  1. Blocker chain terminates in a human-only action (PAT provisioning, GitHub org admin)
     AND the source issue already has a recent (< 24h) triage acknowledgement comment.
  2. Source issue already has >= MAX_TOKEN_GAP_COMMENTS_BEFORE_SUPPRESS identical
     Token-Gap escalation comments (stateless dedup via API, not local file).
  3. Classic 24h dedup via local state file (kept as tertiary fallback).

Non-goals: do NOT suppress unrelated 403s or non-PAT auth issues.

Usage:
    python3 token_gap_escalation_blocker_verification.py [--dry-run]

Environment variables:
    PAPERCLIP_API_KEY: API key for Paperclip
    PAPERCLIP_API_URL: Paperclip API base URL (defaults to http://localhost:3100)
    PAPERCLIP_COMPANY_ID: Company ID
"""

import json
import os
import sys
import re
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import urllib.request
import argparse
from urllib.error import HTTPError

# Configuration
PAPERCLIP_API_URL = os.getenv("PAPERCLIP_API_URL", "http://localhost:3100")
PAPERCLIP_API_KEY = os.getenv("PAPERCLIP_API_KEY", "")
PAPERCLIP_COMPANY_ID = os.getenv("PAPERCLIP_COMPANY_ID", "")

DATA_DIR = Path("data")
ESCALATIONS_FILE = DATA_DIR / "token_gap_escalations_v2.json"
BLOCK_THRESHOLD_HOURS = 4

# Auth-related keywords to detect in blocker issues
AUTH_KEYWORDS = [
    "GH_TOKEN", "GITHUB_TOKEN", "github.*token", "branch protection",
    "401", "403", "unauthorized", "forbidden", "auth", "token", "PAT",
    "permission denied", "credential", "authenticate"
]

# Human-only keywords: these require a GitHub org-admin action; no agent can resolve them.
# Suppression fires only when the blocker chain terminus matches one of these.
HUMAN_ONLY_BLOCKER_KEYWORDS = [
    r"provision.*PAT", r"PAT.*provision", r"GitHub.*admin.*PAT", r"admin.*PAT",
    r"fine-grained.*PAT", r"PAT.*fine-grained", r"create.*PAT",
    r"PAT.*for.*RepoSteward", r"provide.*GitHub.*admin",
    r"GitHub.*org.*admin", r"human.*action.*required", r"human-action-required",
    r"human.*org-admin", r"provide.*GitHub.*admin.*PAT",
]

# Token-gap acknowledgement keywords in comments (from CTO / SecurityAnalyst triage responses)
ACKNOWLEDGEMENT_KEYWORDS = [
    "token-gap", "token gap", "escalation acknowledged", "no new action",
    "already triaged", "duplicate triage", "triage response", "no actionable",
    "still blocked", "same escalation", "repeated automated", "duplicate of prior",
    "acknowledged the token", "human only", "human org-admin", "pat provisioning",
    "loop pattern", "third occurrence", "fourth occurrence", "redundant escalation",
    "escalation.*loop", "loop.*escalation",
]

# Suppress when this many or more identical Token-Gap escalation comments already exist.
# Using Paperclip API for stateless dedup — not ephemeral local file.
MAX_TOKEN_GAP_COMMENTS_BEFORE_SUPPRESS = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("token_gap_escalation")


def _api_request(method: str, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
    """Make a Paperclip API request."""
    url = f"{PAPERCLIP_API_URL}{path}"
    headers = {
        "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        if data:
            body = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as e:
        if e.code == 404:
            return None
        logger.error(f"HTTP {e.code} error on {method} {path}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        logger.error(f"Error on {method} {path}: {e}")
        return None


# ---------------------------------------------------------------------------
# Stateless dedup helpers (read from Paperclip API, not ephemeral local file)
# ---------------------------------------------------------------------------

def count_token_gap_escalation_comments(issue_id: str) -> int:
    """
    Count existing Token-Gap escalation comments on the issue by scanning the API.
    Stateless — works across ephemeral routine containers.
    """
    try:
        comments = _api_request("GET", f"/api/issues/{issue_id}/comments")
        if not isinstance(comments, list):
            return 0
        count = sum(
            1 for c in comments
            if "🚨 **Token-Gap Escalation**" in c.get("body", "")
            # Also match the older CEO-style escalation format
            or re.search(r"Token-Gap Escalation", c.get("body", ""), re.IGNORECASE)
            and "🚨" in c.get("body", "")
        )
        return count
    except Exception as e:
        logger.debug(f"Failed to count escalation comments for {issue_id}: {e}")
        return 0


def has_recent_triage_acknowledgement(issue_id: str, hours: int = 24) -> bool:
    """
    Return True if any non-automated comment posted within `hours` on this issue
    contains an acknowledgement that the Token-Gap escalation has already been triaged
    and no new action is available.

    This is the stateless equivalent of the 24h dedup: instead of a local file,
    we inspect actual issue comments for human/agent triage responses.
    """
    try:
        comments = _api_request("GET", f"/api/issues/{issue_id}/comments")
        if not isinstance(comments, list):
            return False

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Find the index of the most recent Token-Gap escalation comment
        sorted_comments = sorted(comments, key=lambda c: c.get("createdAt", ""))
        last_escalation_idx = -1
        for i, c in enumerate(sorted_comments):
            if re.search(r"Token-Gap Escalation", c.get("body", ""), re.IGNORECASE) and "🚨" in c.get("body", ""):
                last_escalation_idx = i

        if last_escalation_idx == -1:
            return False

        # Check for acknowledgement comment after the last escalation, within 24h
        for c in sorted_comments[last_escalation_idx + 1:]:
            created_raw = c.get("createdAt")
            if not created_raw:
                continue
            try:
                created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                if created_dt < cutoff:
                    continue
            except (ValueError, AttributeError):
                continue

            body = c.get("body", "").lower()
            if any(re.search(kw, body, re.IGNORECASE) for kw in ACKNOWLEDGEMENT_KEYWORDS):
                logger.info(
                    f"  Found recent triage ack on {issue_id} "
                    f"at {created_raw} (within {hours}h)"
                )
                return True

        return False

    except Exception as e:
        logger.debug(f"Failed to check triage acknowledgements for {issue_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# Blocker chain traversal
# ---------------------------------------------------------------------------

def is_human_only_blocker_title(title: str, description: str = "") -> bool:
    """Return True if this issue title/description describes a human-only PAT/admin action."""
    combined = f"{title} {description}"
    for pattern in HUMAN_ONLY_BLOCKER_KEYWORDS:
        if re.search(pattern, combined, re.IGNORECASE):
            return True
    return False


def blocker_chain_terminates_human_only(issue_id: str, depth: int = 0, max_depth: int = 5) -> bool:
    """
    Walk the blockedBy chain recursively.
    Return True if ANY branch of the chain terminates at a blocked issue whose
    title/description signals a human-only action (PAT provisioning, GitHub org admin).

    Depth-limited to prevent infinite recursion on circular/deep chains.
    """
    if depth >= max_depth:
        logger.debug(f"  Max depth {max_depth} reached at {issue_id}")
        return False

    try:
        issue = _api_request("GET", f"/api/issues/{issue_id}")
        if not issue:
            return False

        blocked_by = issue.get("blockedBy") or []

        if not blocked_by:
            # Terminal node: no further blockers.
            # Check whether this issue itself is a human-only blocker.
            result = is_human_only_blocker_title(
                issue.get("title", ""),
                issue.get("description", "") or ""
            )
            if result:
                logger.info(f"  Terminal blocker {issue_id} is human-only: {issue.get('title', '')}")
            return result

        for blocker in blocked_by:
            blocker_title = blocker.get("title", "")
            blocker_id = blocker.get("id") or blocker.get("identifier", "?")
            blocker_desc = blocker.get("description", "") or ""

            # Quick check on embedded title first (saves an API call)
            if is_human_only_blocker_title(blocker_title, blocker_desc):
                logger.info(
                    f"  Blocker {blocker_id} is human-only (title match): {blocker_title}"
                )
                return True

            # If the blocker is itself blocked, recurse into its chain
            if blocker.get("status") == "blocked":
                if blocker_chain_terminates_human_only(blocker_id, depth + 1, max_depth):
                    return True

        return False

    except Exception as e:
        logger.error(f"Failed to traverse blocker chain for {issue_id} at depth {depth}: {e}")
        return False


# ---------------------------------------------------------------------------
# Legacy local-file dedup (tertiary fallback; kept for compatibility)
# ---------------------------------------------------------------------------

def load_escalations_state() -> Dict[str, str]:
    if not ESCALATIONS_FILE.exists():
        return {}
    try:
        with open(ESCALATIONS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        logger.warning("Failed to load escalations state, resetting")
        return {}


def save_escalations_state(state: Dict[str, str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ESCALATIONS_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def should_escalate_issue_local_dedup(issue_id: str) -> bool:
    """Local-file 24h dedup check (ephemeral — only effective within the same container)."""
    state = load_escalations_state()
    key = f"{issue_id}:escalated"
    if key not in state:
        return True
    try:
        last_time = datetime.fromisoformat(state[key])
        elapsed = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
        if elapsed < 24:
            logger.info(f"  Local dedup: skipping {issue_id} ({elapsed:.1f}h since last escalation)")
            return False
    except (ValueError, TypeError):
        pass
    return True


def record_escalation(issue_id: str) -> None:
    state = load_escalations_state()
    state[f"{issue_id}:escalated"] = datetime.now(timezone.utc).isoformat()
    save_escalations_state(state)


# ---------------------------------------------------------------------------
# Other helpers
# ---------------------------------------------------------------------------

def has_fix_sha_none_comment(issue_id: str) -> bool:
    """Check if issue has recent 'Fix-SHA: NONE' comment from CEO."""
    try:
        comments = _api_request("GET", f"/api/issues/{issue_id}/comments")
        if not isinstance(comments, list):
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        for comment in comments:
            created = comment.get("createdAt")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if created_dt < cutoff:
                        continue
                except (ValueError, AttributeError):
                    pass
            body = comment.get("body", "").lower()
            if "fix-sha: none" in body or re.search(r"fix-sha:\s*none", body):
                logger.info(f"  Found Fix-SHA: NONE comment on {issue_id}, skipping re-escalation")
                return True
    except Exception as e:
        logger.debug(f"Failed to check comments for {issue_id}: {e}")
    return False


def is_auth_blocker(issue_title: str, issue_description: str, labels: List[str]) -> bool:
    """Check if issue describes an auth-related blocker."""
    combined_text = f"{issue_title} {issue_description}".lower()
    for keyword in AUTH_KEYWORDS:
        if re.search(keyword, combined_text, re.IGNORECASE):
            return True
    for label in labels:
        if re.search(r"(GH_TOKEN|GITHUB_TOKEN|auth|token|PAT)", label, re.IGNORECASE):
            return True
    return False


def check_blocker_is_auth_related(blocked_issue_id: str) -> bool:
    """
    Verify that the blocker of an issue is auth-related.
    Returns True ONLY if blockedBy is non-empty AND at least one blocker matches auth keywords.
    """
    try:
        issue = _api_request("GET", f"/api/issues/{blocked_issue_id}")
        if not issue:
            logger.warning(f"  Could not fetch issue {blocked_issue_id}")
            return False

        blocked_by = issue.get("blockedBy") or []
        if not blocked_by:
            logger.info(f"  Issue {blocked_issue_id} has empty blockedBy, not escalating")
            return False

        logger.info(f"  Issue {blocked_issue_id} blocked by {len(blocked_by)} issue(s):")
        for blocker in blocked_by:
            blocker_id = blocker.get("id") or blocker.get("identifier", "unknown")
            logger.info(f"    - {blocker_id}: {blocker.get('title', '')}")

        for blocker in blocked_by:
            title = blocker.get("title", "")
            blocker_id = blocker.get("id") or blocker.get("identifier")
            if is_auth_blocker(title, "", blocker.get("labels") or []):
                logger.info(f"    ✓ {blocker_id} is AUTH-RELATED, escalation candidate")
                return True

        logger.info(f"  No auth-related blockers found for {blocked_issue_id}, not escalating")
        return False

    except Exception as e:
        logger.error(f"Failed to check blockedBy for {blocked_issue_id}: {e}")
        return False


def get_issues_blocked_longer_than_threshold(hours: int = BLOCK_THRESHOLD_HOURS) -> List[Dict]:
    """Fetch issues that have been blocked for > threshold hours (paginated)."""
    try:
        all_issues = []
        offset = 0
        page_size = 100

        while True:
            page = _api_request(
                "GET",
                f"/api/companies/{PAPERCLIP_COMPANY_ID}/issues"
                f"?status=in_progress,todo,blocked&limit={page_size}&offset={offset}"
            )
            if not page:
                break
            items = page if isinstance(page, list) else page.get("items", [])
            if not items:
                break
            all_issues.extend(items)
            if len(items) < page_size:
                break
            offset += page_size

        long_blocked = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)

        for issue in all_issues:
            status_changed = issue.get("statusChangedAt")
            started = status_changed or issue.get("startedAt") or issue.get("createdAt")
            try:
                if started:
                    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    if started_dt < cutoff:
                        long_blocked.append(issue)
                        logger.info(
                            f"Found long-blocked issue: {issue.get('identifier')} "
                            f"(blocked {(now - started_dt).total_seconds() / 3600:.1f}h)"
                        )
            except (ValueError, TypeError, AttributeError):
                pass

        return long_blocked

    except Exception as e:
        logger.error(f"Failed to fetch long-blocked issues: {e}")
        return []


def post_escalation_comment(issue_id: str, blocker_issue: Dict, dry_run: bool = False) -> bool:
    """Post escalation comment on blocked issue."""
    blocker_id = blocker_issue.get("identifier", "?")
    blocker_title = blocker_issue.get("title", "Unknown")

    body = (
        f"🚨 **Token-Gap Escalation**\n\n"
        f"This issue is blocked by [{blocker_id}](/BTCAAAAA/issues/{blocker_id}) "
        f"which involves a GitHub authentication or token issue.\n\n"
        f"**Blocker:** {blocker_title}\n\n"
        f"**Next steps:**\n"
        f"1. Verify GitHub token (GH_TOKEN) is valid and has required permissions\n"
        f"2. Check branch protection rules and required status checks\n"
        f"3. Review the blocker issue for specific auth error messages\n\n"
        f"[Token troubleshooting guide]"
        f"(https://docs.github.com/en/authentication/"
        f"keeping-your-account-and-data-secure/"
        f"managing-your-personal-access-tokens)\n"
    )

    if dry_run:
        logger.info(f"[DRY-RUN] Would post comment on {issue_id}:\n{body}")
        return True

    try:
        result = _api_request("POST", f"/api/issues/{issue_id}/comments", {"body": body})
        if result:
            logger.info(f"Posted escalation comment on {issue_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to post comment on {issue_id}: {e}")

    return False


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def run_escalation_sweep(dry_run: bool = False) -> Dict[str, Any]:
    """Main routine: scan blocked issues and escalate auth-related ones."""
    logger.info("Token-Gap Escalation Routine v2 starting...")
    logger.info(f"Block threshold: {BLOCK_THRESHOLD_HOURS}h")
    logger.info(f"Max escalation comment count before suppress: {MAX_TOKEN_GAP_COMMENTS_BEFORE_SUPPRESS}")

    stats: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "issues_scanned": 0,
        "issues_long_blocked": 0,
        "issues_escalated": 0,
        "issues_skipped_no_auth": 0,
        "issues_skipped_dedup": 0,
        "issues_skipped_fix_sha_none": 0,
        "issues_skipped_human_only_chain": 0,
        "issues_skipped_comment_count": 0,
    }

    try:
        long_blocked = get_issues_blocked_longer_than_threshold()
        stats["issues_long_blocked"] = len(long_blocked)
        logger.info(f"Found {len(long_blocked)} issue(s) blocked >{BLOCK_THRESHOLD_HOURS}h")

        for issue in long_blocked:
            issue_id = issue.get("id")
            identifier = issue.get("identifier", "?")
            stats["issues_scanned"] += 1

            logger.info(f"\nProcessing {identifier}...")

            # --- Suppression rule 1: local 24h dedup (tertiary, ephemeral) ---
            if not should_escalate_issue_local_dedup(issue_id):
                stats["issues_skipped_dedup"] += 1
                continue

            # --- Suppression rule 2: Fix-SHA: NONE marker ---
            if has_fix_sha_none_comment(issue_id):
                stats["issues_skipped_fix_sha_none"] += 1
                continue

            # --- Suppression rule 3: auth check (must be auth-related to even consider) ---
            if not check_blocker_is_auth_related(issue_id):
                stats["issues_skipped_no_auth"] += 1
                continue

            # =================================================================
            # PRIMARY SUPPRESSION (req 1 from BTCAAAAA-34213):
            # Blocker chain terminates in a human-only PAT/admin blocker
            # AND there is already a recent acknowledgement on this issue.
            # =================================================================
            if blocker_chain_terminates_human_only(issue_id):
                logger.info(
                    f"  {identifier}: blocker chain terminates in human-only action"
                )
                if has_recent_triage_acknowledgement(issue_id, hours=24):
                    logger.info(
                        f"  SUPPRESSED {identifier}: human-only chain + recent triage ack — "
                        f"no new escalation comment posted"
                    )
                    stats["issues_skipped_human_only_chain"] += 1
                    continue
                else:
                    logger.info(
                        f"  {identifier}: human-only chain but NO recent ack — "
                        f"checking comment count before deciding"
                    )

            # =================================================================
            # SECONDARY SUPPRESSION (req 2 from BTCAAAAA-34213):
            # >= MAX_TOKEN_GAP_COMMENTS_BEFORE_SUPPRESS identical comments exist.
            # Stateless — reads from Paperclip API, survives container restarts.
            # =================================================================
            existing_count = count_token_gap_escalation_comments(issue_id)
            if existing_count >= MAX_TOKEN_GAP_COMMENTS_BEFORE_SUPPRESS:
                logger.info(
                    f"  SUPPRESSED {identifier}: already {existing_count} Token-Gap escalation "
                    f"comments (>= {MAX_TOKEN_GAP_COMMENTS_BEFORE_SUPPRESS}) — "
                    f"suppressing until blocker chain resolves"
                )
                stats["issues_skipped_comment_count"] += 1
                continue

            # --- All suppression checks passed: escalate ---
            issue_data = _api_request("GET", f"/api/issues/{issue_id}")
            if not issue_data:
                continue

            blocker_issue = (issue_data.get("blockedBy") or [{}])[0]

            if post_escalation_comment(issue_id, blocker_issue, dry_run):
                record_escalation(issue_id)
                stats["issues_escalated"] += 1

    except Exception as e:
        logger.error(f"Escalation sweep failed: {e}")
        stats["error"] = str(e)

    logger.info("\n" + "=" * 60)
    logger.info("Summary:")
    logger.info(f"  Issues scanned:                 {stats['issues_scanned']}")
    logger.info(f"  Escalated:                      {stats['issues_escalated']}")
    logger.info(f"  Skipped (no auth blocker):      {stats['issues_skipped_no_auth']}")
    logger.info(f"  Skipped (24h local dedup):      {stats['issues_skipped_dedup']}")
    logger.info(f"  Skipped (Fix-SHA: NONE):        {stats['issues_skipped_fix_sha_none']}")
    logger.info(f"  Skipped (human-only chain+ack): {stats['issues_skipped_human_only_chain']}")
    logger.info(f"  Skipped (comment count cap):    {stats['issues_skipped_comment_count']}")
    logger.info("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Run without posting comments")
    args = parser.parse_args()

    if not PAPERCLIP_API_KEY:
        logger.error("ERROR: PAPERCLIP_API_KEY not set")
        sys.exit(1)

    if not PAPERCLIP_COMPANY_ID:
        logger.error("ERROR: PAPERCLIP_COMPANY_ID not set")
        sys.exit(1)

    stats = run_escalation_sweep(dry_run=args.dry_run)

    if args.dry_run:
        logger.info("DRY-RUN mode: no changes made")

    sys.exit(0 if not stats.get("error") else 1)


if __name__ == "__main__":
    main()
