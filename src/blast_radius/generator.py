"""Blast Radius Report generator.

Triggered when a fix/bug issue transitions to `in_review`:
1. Read touchedFiles from the issue.
2. Query the Touch Index.
3. Render the report.
4. POST a comment on the issue via Paperclip API.
5. @-mention each FR owner agent in the comment.
"""

from __future__ import annotations

import logging
import os
from typing import Sequence

from touch_index.paperclip_client import _session, _base, get_issue_by_id

from .query import query_blast_radius, to_json_dict
from .report import render_report, extract_touched_files

log = logging.getLogger(__name__)

PAPERCLIP_RUN_ID = os.environ.get("PAPERCLIP_RUN_ID", "")


def _run_headers() -> dict[str, str]:
    if PAPERCLIP_RUN_ID:
        return {"X-Paperclip-Run-Id": PAPERCLIP_RUN_ID}
    return {}


def _get_issue(issue_id: str) -> dict:
    issue = get_issue_by_id(issue_id)
    if issue is None:
        raise RuntimeError(f"Issue {issue_id} not found")
    return issue


def _get_agent_name(agent_id: str) -> str | None:
    try:
        with _session() as sess:
            resp = sess.get(f"{_base()}/api/agents/{agent_id}", timeout=10)
            if resp.ok:
                data = resp.json()
                return data.get("name") or data.get("nameKey") or None
    except Exception:
        pass
    return None


def _post_comment(issue_id: str, body: str) -> None:
    with _session() as sess:
        sess.headers.update(_run_headers())
        resp = sess.post(
            f"{_base()}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=15,
        )
        resp.raise_for_status()


def generate_and_post(
    issue_id: str,
    touched_files: Sequence[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Generate a Blast Radius Report for *issue_id* and post it as a comment.

    If *touched_files* is provided it is used directly; otherwise they are
    parsed from the issue description.

    Returns the JSON-serialisable result dict (same shape as the query API).
    """
    issue = _get_issue(issue_id)
    identifier = issue["identifier"]
    title = issue["title"]
    description = issue.get("description", "") or ""

    if touched_files is None:
        touched_files = extract_touched_files(description)

    # Fallback: derive touched files from git history when not in description
    if not touched_files:
        log.info(
            "No touchedFiles in description for %s — falling back to git history",
            identifier,
        )
        try:
            from touch_index.git_extractor import get_files_for_issue

            touched_files = get_files_for_issue(identifier)
            log.info(
                "Derived %d touched file(s) from git for %s",
                len(touched_files),
                identifier,
            )
        except Exception as exc:
            log.warning("Git fallback failed for %s: %s", identifier, exc)

    if not touched_files:
        log.warning("No touchedFiles found for issue %s — skipping report", identifier)
        return {"skipped": True, "reason": "no touchedFiles", "issue": identifier}

    data = query_blast_radius(list(touched_files))

    # Resolve owner agent names for @-mentions
    agent_names: dict[str, str] = {}
    for fr in data.fr_impact_set:
        aid = fr.fr_owner_agent_id
        if aid not in agent_names:
            name = _get_agent_name(aid)
            if name:
                agent_names[aid] = name

    report_md = render_report(
        issue_identifier=identifier,
        issue_title=title,
        touched_files=list(touched_files),
        data=data,
        agent_names=agent_names,
    )

    if dry_run:
        log.info("[dry-run] Would post to issue %s:\n%s", identifier, report_md)
    else:
        _post_comment(issue_id, report_md)
        log.info("Posted Blast Radius Report to %s", identifier)

    result = to_json_dict(data)
    result["issue"] = identifier
    result["dry_run"] = dry_run
    return result
