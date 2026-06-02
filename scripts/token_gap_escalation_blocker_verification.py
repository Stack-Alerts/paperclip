#!/usr/bin/env python3
"""
Token-Gap Escalation Routine — Fixed version that verifies blockedBy relations.

Detects and escalates REAL token-gap blockers (GitHub auth issues) by verifying
that the blocking issue actually has auth-related causes, not just checking
block duration alone.

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("token_gap_escalation")


def _http_session():
    """Create a Paperclip API session."""
    import urllib.request
    session = urllib.request.Request
    return session


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


def load_escalations_state() -> Dict[str, str]:
    """Load escalation state file (dedup tracking)."""
    if not ESCALATIONS_FILE.exists():
        return {}

    try:
        with open(ESCALATIONS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        logger.warning("Failed to load escalations state, resetting")
        return {}


def save_escalations_state(state: Dict[str, str]) -> None:
    """Save escalation state file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ESCALATIONS_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def should_escalate_issue(issue_id: str) -> bool:
    """Check if issue should be escalated (24h dedup)."""
    state = load_escalations_state()
    key = f"{issue_id}:escalated"

    if key not in state:
        return True

    try:
        last_time = datetime.fromisoformat(state[key])
        elapsed = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
        if elapsed < 24:
            logger.info(f"  Skipping {issue_id}: escalated {elapsed:.1f}h ago (within 24h dedup window)")
            return False
    except (ValueError, TypeError):
        pass

    return True


def record_escalation(issue_id: str) -> None:
    """Record escalation for dedup tracking."""
    state = load_escalations_state()
    state[f"{issue_id}:escalated"] = datetime.now(timezone.utc).isoformat()
    save_escalations_state(state)


def has_fix_sha_none_comment(issue_id: str) -> bool:
    """Check if issue has recent 'Fix-SHA: NONE' comment from CEO."""
    try:
        comments = _api_request("GET", f"/api/issues/{issue_id}/comments")
        if not comments:
            return False

        # Look for Fix-SHA: NONE in last 24h comments
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
            logger.debug(f"    Matched auth keyword: {keyword}")
            return True

    # Check labels
    for label in labels:
        if re.search(r"(GH_TOKEN|GITHUB_TOKEN|auth|token|PAT)", label, re.IGNORECASE):
            logger.debug(f"    Matched auth label: {label}")
            return True

    return False


def check_blocker_is_auth_related(blocked_issue_id: str) -> bool:
    """
    Verify that the blocker of an issue is auth-related.

    Returns True ONLY if:
    - blockedBy is not empty
    - AND at least one blocker matches auth keywords

    Otherwise returns False (don't escalate).
    """
    try:
        issue = _api_request("GET", f"/api/issues/{blocked_issue_id}")
        if not issue:
            logger.warning(f"  Could not fetch issue {blocked_issue_id}")
            return False

        blocked_by = issue.get("blockedBy", [])
        if not blocked_by:
            logger.info(f"  Issue {blocked_issue_id} has empty blockedBy, not escalating")
            return False

        logger.info(f"  Issue {blocked_issue_id} blocked by {len(blocked_by)} issue(s):")
        for blocker in blocked_by:
            blocker_id = blocker.get("id") or blocker.get("identifier", "unknown")
            logger.info(f"    - {blocker_id}: {blocker.get('title', '')}")

        # Check if ANY blocker is auth-related
        for blocker in blocked_by:
            title = blocker.get("title", "")
            blocker_id = blocker.get("id") or blocker.get("identifier")

            if is_auth_blocker(title, "", blocker.get("labels", [])):
                logger.info(f"    ✓ {blocker_id} is AUTH-RELATED, escalation approved")
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
                f"/api/companies/{PAPERCLIP_COMPANY_ID}/issues?status=in_progress,todo,blocked&limit={page_size}&offset={offset}"
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
            # Note: blockedBy is null in list responses; individual fetch in check_blocker_is_auth_related
            # handles actual relation lookup. Here we only filter by duration.

            # Check block duration
            status_changed = issue.get("statusChangedAt")
            if not status_changed:
                started = issue.get("startedAt") or issue.get("createdAt")
            else:
                started = status_changed

            try:
                if started:
                    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    if started_dt < cutoff:
                        long_blocked.append(issue)
                        logger.info(f"Found long-blocked issue: {issue.get('identifier')} (blocked {(now - started_dt).total_seconds()/3600:.1f}h)")
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

    body = f"""🚨 **Token-Gap Escalation**

This issue is blocked by [{blocker_id}](/BTCAAAAA/issues/{blocker_id}) which involves a GitHub authentication or token issue.

**Blocker:** {blocker_title}

**Next steps:**
1. Verify GitHub token (GH_TOKEN) is valid and has required permissions
2. Check branch protection rules and required status checks
3. Review the blocker issue for specific auth error messages

[Token troubleshooting guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
"""

    if dry_run:
        logger.info(f"[DRY-RUN] Would post comment on {issue_id}:\n{body}")
        return True

    try:
        result = _api_request(
            "POST",
            f"/api/issues/{issue_id}/comments",
            {"body": body}
        )
        if result:
            logger.info(f"Posted escalation comment on {issue_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to post comment on {issue_id}: {e}")

    return False


def run_escalation_sweep(dry_run: bool = False) -> Dict[str, Any]:
    """Main routine: scan blocked issues and escalate auth-related ones."""
    logger.info("Token-Gap Escalation Routine starting...")
    logger.info(f"Block threshold: {BLOCK_THRESHOLD_HOURS}h")

    stats = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "issues_scanned": 0,
        "issues_long_blocked": 0,
        "issues_escalated": 0,
        "issues_skipped_no_auth": 0,
        "issues_skipped_dedup": 0,
        "issues_skipped_fix_sha_none": 0,
    }

    try:
        # Step 1: Find issues blocked > threshold
        long_blocked = get_issues_blocked_longer_than_threshold()
        stats["issues_long_blocked"] = len(long_blocked)

        logger.info(f"Found {len(long_blocked)} issue(s) blocked >{BLOCK_THRESHOLD_HOURS}h")

        # Step 2: For each long-blocked issue, check if blocker is auth-related
        for issue in long_blocked:
            issue_id = issue.get("id")
            identifier = issue.get("identifier", "?")
            stats["issues_scanned"] += 1

            logger.info(f"\nProcessing {identifier}...")

            # Check dedup (24h window)
            if not should_escalate_issue(issue_id):
                stats["issues_skipped_dedup"] += 1
                continue

            # Check for Fix-SHA: NONE (CEO marker to skip re-escalation)
            if has_fix_sha_none_comment(issue_id):
                stats["issues_skipped_fix_sha_none"] += 1
                continue

            # Check if blocker is auth-related
            if not check_blocker_is_auth_related(issue_id):
                stats["issues_skipped_no_auth"] += 1
                continue

            # Get the auth-related blocker for the comment
            issue_data = _api_request("GET", f"/api/issues/{issue_id}")
            if not issue_data:
                continue

            blocker_issue = issue_data.get("blockedBy", [{}])[0]

            # Post escalation comment
            if post_escalation_comment(issue_id, blocker_issue, dry_run):
                record_escalation(issue_id)
                stats["issues_escalated"] += 1

    except Exception as e:
        logger.error(f"Escalation sweep failed: {e}")
        stats["error"] = str(e)

    logger.info("\n" + "="*60)
    logger.info("Summary:")
    logger.info(f"  Issues scanned: {stats['issues_scanned']}")
    logger.info(f"  Escalated: {stats['issues_escalated']}")
    logger.info(f"  Skipped (no auth blocker): {stats['issues_skipped_no_auth']}")
    logger.info(f"  Skipped (24h dedup): {stats['issues_skipped_dedup']}")
    logger.info(f"  Skipped (Fix-SHA: NONE): {stats['issues_skipped_fix_sha_none']}")
    logger.info("="*60)

    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no comments posted)"
    )
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
