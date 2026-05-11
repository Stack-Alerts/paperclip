"""FR ingestion worker — upserts touch_index_fr_files rows.

Triggered on: issue_created or issue_updated where the issue has the FDR label.

File extraction strategy (in priority order):
  1. Done-comments on the FDR issue — the implementing agent typically posts a
     completion comment that names the files they changed (e.g.
     ``src/optimizer_v3/database/strategy_manager.py``).
  2. Git commits that reference the FDR identifier directly.
  3. Issue description text (lower-signal but catches spec-level file refs).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .comment_extractor import fetch_and_extract, extract_files_from_text
from .git_extractor import get_files_for_issue

logger = logging.getLogger(__name__)

_UPSERT_SQL = text("""
    INSERT INTO touch_index_fr_files
        (id, file_path, fr_issue_id, fr_identifier, fr_owner_agent_id, updated_at)
    VALUES
        (:id, :file_path, :fr_issue_id, :fr_identifier, :fr_owner_agent_id, :updated_at)
    ON CONFLICT (file_path, fr_issue_id)
    DO UPDATE SET
        fr_owner_agent_id = EXCLUDED.fr_owner_agent_id,
        updated_at        = EXCLUDED.updated_at
""")


@dataclass
class FRIngestionResult:
    issue_identifier: str
    files_indexed: int
    source: str  # "comments" | "git" | "description" | "none"
    skipped_no_commits: bool  # True when no files found from any source


def ingest_fr_issue(
    engine: Engine,
    issue_id: str,
    issue_identifier: str,
    owner_agent_id: str | None,
    description: str = "",
) -> FRIngestionResult:
    """Process a single FDR issue — extract files and upsert."""
    # 1. Comments (highest signal — implementing agent's done-comment)
    files = fetch_and_extract(issue_id)
    source = "comments"

    # 2. Git commits that reference the issue identifier
    if not files:
        files = get_files_for_issue(issue_identifier)
        source = "git"

    # 3. Description text
    if not files and description:
        files = extract_files_from_text(description)
        source = "description"

    if not files:
        logger.info(
            "FR %s: no files found in comments, git, or description", issue_identifier
        )
        return FRIngestionResult(
            issue_identifier=issue_identifier,
            files_indexed=0,
            source="none",
            skipped_no_commits=True,
        )

    owner = owner_agent_id or "00000000-0000-0000-0000-000000000000"
    now = datetime.now(timezone.utc)

    rows = [
        {
            "id": str(uuid.uuid4()),
            "file_path": f,
            "fr_issue_id": issue_id,
            "fr_identifier": issue_identifier,
            "fr_owner_agent_id": owner,
            "updated_at": now,
        }
        for f in files
    ]

    with engine.begin() as conn:
        conn.execute(_UPSERT_SQL, rows)

    logger.info("FR %s: indexed %d file(s) via %s", issue_identifier, len(rows), source)
    return FRIngestionResult(
        issue_identifier=issue_identifier,
        files_indexed=len(rows),
        source=source,
        skipped_no_commits=False,
    )


def run_fr_worker(
    engine: Engine,
    issues: Sequence[dict],
) -> list[FRIngestionResult]:
    """Ingest a list of FDR issue dicts (from paperclip_client.get_fdr_issues)."""
    results = []
    for issue in issues:
        try:
            result = ingest_fr_issue(
                engine,
                issue_id=issue["id"],
                issue_identifier=issue["identifier"],
                owner_agent_id=issue.get("assigneeAgentId"),
                description=issue.get("description", "") or "",
            )
            results.append(result)
        except Exception:
            logger.exception("FR worker error for %s", issue.get("identifier"))
    return results
