"""Thin Paperclip API client for Touch Index ingestion workers.

Reads PAPERCLIP_API_URL and PAPERCLIP_API_KEY from environment.
All methods return plain dicts (no schema binding).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

# FDR label identifies Feature Design Requirements (FRs)
FDR_LABEL_ID = "d523cb2d-acd9-423d-b87a-bb79cee42c40"

# Bug title prefixes used by the team for formal bug issues
_BUG_TITLE_PREFIXES = ("bug:", "bug ")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}",
            "Content-Type": "application/json",
        }
    )
    return s


def _base() -> str:
    return os.environ["PAPERCLIP_API_URL"]


def _company() -> str:
    return os.environ["PAPERCLIP_COMPANY_ID"]


def _paginate(
    path: str,
    params: dict[str, Any],
    *,
    page_size: int = 100,
) -> list[dict]:
    sess = _session()
    results: list[dict] = []
    params = {**params, "limit": page_size, "offset": 0}
    while True:
        resp = sess.get(f"{_base()}{path}", params=params, timeout=30)
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break
        results.extend(page)
        if len(page) < page_size:
            break
        params["offset"] += page_size
    return results


def get_issue_by_id(issue_id: str) -> dict | None:
    """Fetch a single issue by its UUID."""
    sess = _session()
    resp = sess.get(f"{_base()}/api/issues/{issue_id}", timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def get_issue_by_identifier(identifier: str) -> dict | None:
    """Fetch a single issue by its identifier (e.g. 'BTCAAAAA-1085')."""
    issues = _paginate(
        f"/api/companies/{_company()}/issues",
        {"q": identifier, "limit": 5},
        page_size=5,
    )
    for i in issues:
        if i["identifier"] == identifier:
            return i
    return None


def get_fdr_issues(updated_after: datetime | None = None) -> list[dict]:
    """Return all FDR-labelled issues, optionally filtered by updatedAt."""
    params: dict[str, Any] = {
        "labelId": FDR_LABEL_ID,
        "status": "todo,in_progress,in_review,done",
    }
    issues = _paginate(f"/api/companies/{_company()}/issues", params)
    if updated_after:
        cutoff = updated_after.astimezone(timezone.utc)
        issues = [
            i
            for i in issues
            if datetime.fromisoformat(i["updatedAt"].replace("Z", "+00:00")) >= cutoff
        ]
    return issues


def get_closed_bug_issues(closed_after: datetime | None = None) -> list[dict]:
    """Return done issues identified as bugs (title prefix 'Bug:'/'BUG:')."""
    params: dict[str, Any] = {"status": "done"}
    issues = _paginate(f"/api/companies/{_company()}/issues", params)
    bugs = [i for i in issues if _is_bug(i["title"])]
    if closed_after:
        cutoff = closed_after.astimezone(timezone.utc)
        bugs = [
            b
            for b in bugs
            if b.get("completedAt")
            and datetime.fromisoformat(b["completedAt"].replace("Z", "+00:00"))
            >= cutoff
        ]
    return bugs


def get_closed_non_fdr_issues(closed_after: datetime | None = None) -> list[dict]:
    """Return done non-FDR issues, optionally filtered by completedAt.

    Broader than get_closed_bug_issues: captures any issue that has
    ``fix(BTCAAAAA-NNN)`` commits in git, regardless of title prefix.
    FDR-labelled issues are excluded (they are ingested by the FR worker).
    """
    params: dict[str, Any] = {"status": "done"}
    issues = _paginate(f"/api/companies/{_company()}/issues", params)
    issues = [i for i in issues if FDR_LABEL_ID not in (i.get("labelIds") or [])]
    if closed_after:
        cutoff = closed_after.astimezone(timezone.utc)
        issues = [
            i
            for i in issues
            if i.get("completedAt")
            and datetime.fromisoformat(i["completedAt"].replace("Z", "+00:00"))
            >= cutoff
        ]
    return issues


def get_all_done_issues(completed_after: datetime | None = None) -> list[dict]:
    """Return ALL done issues, optionally filtered by completedAt.

    Used by the backfill to capture fix-type issues that don't carry a 'Bug:'
    title prefix but do have ``fix(BTCAAAAA-NNN)`` commits in git history.
    """
    params: dict[str, Any] = {"status": "done"}
    issues = _paginate(f"/api/companies/{_company()}/issues", params)
    if completed_after:
        cutoff = completed_after.astimezone(timezone.utc)
        issues = [
            i
            for i in issues
            if i.get("completedAt")
            and datetime.fromisoformat(i["completedAt"].replace("Z", "+00:00"))
            >= cutoff
        ]
    return issues


def transition_issue_status(issue_id: str, status: str) -> None:
    """Transition an issue to *status* via the Paperclip API.

    Args:
        issue_id: The Paperclip issue UUID.
        status:   Target status (e.g. "done").

    Raises:
        requests.RequestException on API error.
    """
    sess = _session()
    resp = sess.patch(
        f"{_base()}/api/issues/{issue_id}",
        json={"status": status},
        timeout=30,
    )
    resp.raise_for_status()


def get_issue_assignee(issue: dict) -> str | None:
    return issue.get("assigneeAgentId")


def _is_bug(title: str) -> bool:
    lower = title.lower()
    return any(lower.startswith(p) for p in _BUG_TITLE_PREFIXES)
