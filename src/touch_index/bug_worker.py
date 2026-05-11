"""Bug-close ingestion worker — upserts touch_index_bug_files rows.

Triggered on: issue_status_changed to 'done' where the issue is a bug
(title starts with 'Bug:' or 'BUG:').

For each closed bug:
  - Find git commits that reference the issue identifier.
  - Collect the source files touched by those commits.
  - Upsert one row per (file_path, bug_issue_id) into touch_index_bug_files,
    setting closed_at from completedAt.

The upsert is idempotent — safe to re-run on the same issues.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .comment_extractor import fetch_and_extract
from .git_extractor import get_files_for_issue

logger = logging.getLogger(__name__)

_UPSERT_SQL = text("""
    INSERT INTO touch_index_bug_files
        (id, file_path, bug_issue_id, bug_identifier, closed_at)
    VALUES
        (:id, :file_path, :bug_issue_id, :bug_identifier, :closed_at)
    ON CONFLICT (file_path, bug_issue_id)
    DO UPDATE SET
        closed_at = COALESCE(EXCLUDED.closed_at, touch_index_bug_files.closed_at)
""")


@dataclass
class BugIngestionResult:
    issue_identifier: str
    files_indexed: int
    source: str  # "git" | "comments" | "none"
    skipped_no_commits: bool


def ingest_bug_issue(
    engine: Engine,
    issue_id: str,
    issue_identifier: str,
    completed_at: datetime | None,
) -> BugIngestionResult:
    """Process a single closed bug issue and upsert its touched files."""
    files = get_files_for_issue(issue_identifier)
    source = "git"

    if not files:
        files = fetch_and_extract(issue_id)
        source = "comments"

    if not files:
        logger.info(
            "Bug %s: no files found in git or comments — skipping", issue_identifier
        )
        return BugIngestionResult(
            issue_identifier=issue_identifier,
            files_indexed=0,
            source="none",
            skipped_no_commits=True,
        )

    rows = [
        {
            "id": str(uuid.uuid4()),
            "file_path": f,
            "bug_issue_id": issue_id,
            "bug_identifier": issue_identifier,
            "closed_at": completed_at,
        }
        for f in files
    ]

    with engine.begin() as conn:
        conn.execute(_UPSERT_SQL, rows)

    logger.info(
        "Bug %s: indexed %d file(s) via %s", issue_identifier, len(rows), source
    )
    return BugIngestionResult(
        issue_identifier=issue_identifier,
        files_indexed=len(rows),
        source=source,
        skipped_no_commits=False,
    )


def _parse_completed_at(issue: dict) -> datetime | None:
    raw = issue.get("completedAt")
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def run_bug_worker(
    engine: Engine,
    issues: Sequence[dict],
) -> list[BugIngestionResult]:
    """Ingest a list of closed bug issue dicts (from paperclip_client.get_closed_bug_issues)."""
    results = []
    for issue in issues:
        try:
            result = ingest_bug_issue(
                engine,
                issue_id=issue["id"],
                issue_identifier=issue["identifier"],
                completed_at=_parse_completed_at(issue),
            )
            results.append(result)
        except Exception:
            logger.exception("Bug worker error for %s", issue.get("identifier"))
    return results
