#!/usr/bin/env python3
"""
Token-Gap Escalation Routine - Escalates PR-merge issues blocked by GitHub API token gaps.

Runs every 30 minutes to:
1. Find blocked issues related to PR merging that are blocked by GitHub API token gaps
2. Escalate those blocked for > 4 hours to the CEO
3. Post idempotent escalation comments (no duplicates)
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import requests


class TokenGapEscalationMonitor:
    """Monitor and escalate PR-merge issues blocked by GitHub API token gaps."""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None, company_id: Optional[str] = None):
        """Initialize monitor with API credentials."""
        self.api_url = api_url or os.environ.get("PAPERCLIP_API_URL", "http://localhost:3100")
        self.api_key = api_key or os.environ.get("PAPERCLIP_API_KEY", "")
        self.company_id = company_id or os.environ.get("PAPERCLIP_COMPANY_ID", "")
        self.run_id = os.environ.get("PAPERCLIP_RUN_ID", "")

    def _api_request(self, method: str, endpoint: str, data: Optional[dict] = None) -> Optional[dict]:
        """Make a request to the Paperclip API."""
        url = f"{self.api_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.run_id:
            headers["X-Paperclip-Run-Id"] = self.run_id

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            else:
                return None

            if response.status_code in (200, 201, 204):
                return response.json() if response.text else {}
            else:
                print(f"Warning: API request failed ({response.status_code}): {response.text[:200]}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"Warning: API request exception: {str(e)}", file=sys.stderr)
            return None

    def _has_github_token_error(self, issue_id: str) -> bool:
        """Check if issue has comments indicating GitHub API token gap error."""
        comments = self._api_request("GET", f"/api/issues/{issue_id}/comments")
        if not comments:
            return False

        # Handle both array and object responses
        items = comments if isinstance(comments, list) else comments.get("items", [])
        if not items:
            return False

        token_error_patterns = [
            r"github.*token",
            r"authentication.*failed",
            r"bad credentials",
            r"invalid token",
            r"token.*expired",
            r"token.*invalid",
            r"401.*github",
            r"github.*401",
            r"permission denied.*github"
        ]

        for comment in items:
            body = comment.get("body", "").lower()
            for pattern in token_error_patterns:
                if re.search(pattern, body):
                    return True
        return False

    def _has_existing_escalation(self, issue_id: str) -> bool:
        """Check if issue already has an active escalation task (idempotency check)."""
        # Check both for existing comments and for pending escalation subtasks
        issue = self._api_request("GET", f"/api/issues/{issue_id}")
        if not issue:
            return False

        # Check for comments with escalation marker
        comments = self._api_request("GET", f"/api/issues/{issue_id}/comments")
        if comments:
            items = comments if isinstance(comments, list) else comments.get("items", [])
            escalation_marker = "🚨 Token-Gap Escalation"
            for comment in items:
                if escalation_marker in comment.get("body", ""):
                    return True

        # Check if there are pending CEO escalation subtasks
        if "blocks" in issue:
            for blocking_issue in issue.get("blocks", []):
                if "escalat" in blocking_issue.get("title", "").lower() and blocking_issue.get("status") in ["todo", "in_progress"]:
                    return True

        return False

    def _get_issue_blocker_duration(self, issue: dict) -> Optional[int]:
        """Get how long (in minutes) an issue has been blocked."""
        if issue.get("status") != "blocked":
            return None

        blocked_at = issue.get("updatedAt")
        if not blocked_at:
            return None

        try:
            blocked_time = datetime.fromisoformat(blocked_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            duration = (now - blocked_time).total_seconds() / 60
            return int(duration)
        except Exception:
            return None

    def escalate_issue(self, issue_id: str, issue_identifier: str, blocked_minutes: int, escalation_issue_id: Optional[str] = None) -> bool:
        """Create escalation task for CEO to handle."""
        hours = blocked_minutes // 60
        minutes = blocked_minutes % 60

        # Create an escalation issue that the CEO will handle
        escalation_title = f"Escalate token-gap blocker: {issue_identifier}"
        escalation_description = f"""Token-gap escalation required

**Blocked Issue:** [{issue_identifier}](/{self.company_id.split('-')[0]}/issues/{issue_identifier})

**Duration:** {hours}h {minutes}m (threshold: 4h)

**Required Action:** Post CEO escalation comment on the blocked issue to notify relevant parties about GitHub token gap issue.

**Comment to Post:**
```
## 🚨 Token-Gap Escalation

This PR-merge issue has been blocked by a GitHub API token gap for **{hours}h {minutes}m**.

**Action Required:** Review GitHub token configuration and resolve authentication issue to unblock this merge.

_Auto-escalated by Token-Gap Escalation Routine_
```

This escalation task is idempotent - only one such task per blocked issue will be created per routine run.
"""

        # Create escalation subtask for the CEO
        escalation_data = {
            "title": escalation_title,
            "description": escalation_description,
            "status": "todo",
            "priority": "critical",
            "assigneeAgentId": "73e7ef43-1337-47f8-9cf2-8db91ebcf555",  # CEO agent ID
            "parentId": escalation_issue_id or issue_id,
            "projectId": self.project_id if hasattr(self, 'project_id') else None
        }

        response = self._api_request(
            "POST",
            f"/api/companies/{self.company_id}/issues",
            escalation_data
        )

        if response:
            escalation_id = response.get("id")
            print(f"✓ Created escalation task {escalation_id} for {issue_identifier} (blocked {hours}h {minutes}m)")
            return True
        else:
            print(f"✗ Failed to create escalation for {issue_identifier}", file=sys.stderr)
            return False

    def find_and_escalate_token_gaps(self) -> dict:
        """Find and escalate PR-merge issues blocked by token gaps > 4h."""
        result = {"scanned": 0, "escalated": 0, "issues": []}

        # Query for blocked issues
        issues_response = self._api_request(
            "GET",
            f"/api/companies/{self.company_id}/issues?status=blocked&limit=100"
        )

        if not issues_response:
            return result

        # Handle both array and object responses
        items = issues_response if isinstance(issues_response, list) else issues_response.get("items", [])
        if not items:
            return result

        now = datetime.now(timezone.utc)
        threshold_hours = 4

        for issue in items:
            result["scanned"] += 1
            issue_id = issue.get("id")
            issue_identifier = issue.get("identifier")
            title = issue.get("title", "")

            # Check if this is a PR-merge related issue
            is_pr_merge_issue = any(keyword in title.lower() for keyword in ["merge", "pr", "pull request"])
            if not is_pr_merge_issue:
                continue

            # Check for token gap error in comments
            if not self._has_github_token_error(issue_id):
                continue

            # Check how long it's been blocked
            blocked_minutes = self._get_issue_blocker_duration(issue)
            if not blocked_minutes or blocked_minutes < (threshold_hours * 60):
                continue

            # Check if already escalated (idempotency)
            if self._has_existing_escalation(issue_id):
                print(f"⊘ Already escalated {issue_identifier}")
                continue

            # Escalate to CEO by creating escalation task
            if self.escalate_issue(issue_id, issue_identifier, blocked_minutes):
                result["escalated"] += 1
                result["issues"].append({
                    "identifier": issue_identifier,
                    "blocked_minutes": blocked_minutes,
                    "title": title
                })

        return result

    def run(self):
        """Execute the escalation routine."""
        print(f"Starting Token-Gap Escalation scan at {datetime.now(timezone.utc).isoformat()}")

        result = self.find_and_escalate_token_gaps()

        print(f"\nResults:")
        print(f"  Scanned: {result['scanned']} blocked issues")
        print(f"  Escalated: {result['escalated']} token-gap issues")

        if result['issues']:
            print(f"\nEscalated issues:")
            for issue in result['issues']:
                hours = issue['blocked_minutes'] // 60
                minutes = issue['blocked_minutes'] % 60
                print(f"  - {issue['identifier']}: {hours}h {minutes}m ({issue['title']})")

        return 0 if result['escalated'] >= 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="Token-Gap Escalation Routine - Escalate PR-merge issues blocked by GitHub API token gaps"
    )
    parser.add_argument("--api-url", help="Paperclip API URL")
    parser.add_argument("--api-key", help="Paperclip API key")
    parser.add_argument("--company-id", help="Company ID")

    args = parser.parse_args()

    monitor = TokenGapEscalationMonitor(
        api_url=args.api_url,
        api_key=args.api_key,
        company_id=args.company_id
    )

    sys.exit(monitor.run())


if __name__ == "__main__":
    main()
