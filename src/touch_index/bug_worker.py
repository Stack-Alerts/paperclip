"""Bug-close Touch Index ingestion worker — upserts touch_index_bug_files rows.

Triggered by run_touch_index_bug_worker.py every 15 minutes for all done
non-FDR issues (bug titles and fix-type commits).  Excludes FDR-labelled
issues which are ingested by the FR worker.

For each closed issue:
  - Find git commits that reference the issue identifier.
  - Collect the source files touched by those commits.
  - Fall back to Paperclip issue comments if git returns nothing.
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

from .comment_extractor import extract_files_from_text, fetch_and_extract
from .git_extractor import get_all_referenced_issue_ids, get_files_for_issue
from .paperclip_client import FDR_LABEL_ID, get_issue_by_id, get_issue_by_identifier

logger = logging.getLogger(__name__)

_UPSERT_SQL = text("""
    INSERT INTO touch_index_bug_files
        (id, file_path, bug_issue_id, bug_identifier, closed_at, source, updated_at)
    VALUES
        (:id, :file_path, :bug_issue_id, :bug_identifier, :closed_at, :source, :updated_at)
    ON CONFLICT (file_path, bug_issue_id)
    DO UPDATE SET
        bug_identifier = EXCLUDED.bug_identifier,
        closed_at      = COALESCE(EXCLUDED.closed_at, touch_index_bug_files.closed_at),
        source         = EXCLUDED.source,
        updated_at     = EXCLUDED.updated_at
""")


@dataclass
class BugIngestionResult:
    issue_identifier: str
    issue_id: str
    files_indexed: int
    source: str  # "git" | "comments" | "description" | "none"
    skipped_no_commits: bool
    issue_status: str | None = None  # Paperclip status at time of ingestion


def ingest_bug_issue(
    engine: Engine,
    issue_id: str,
    issue_identifier: str,
    completed_at: datetime | None,
    description: str = "",
    *,
    dry_run: bool = False,
    issue_status: str | None = None,
) -> BugIngestionResult:
    """Process a single closed bug issue and upsert its touched files."""
    files = get_files_for_issue(issue_identifier)
    source = "git"

    if not files:
        files = fetch_and_extract(issue_id)
        source = "comments"

    if not files and description:
        files = extract_files_from_text(description)
        source = "description"

    if not files:
        logger.info(
            "Bug %s: no files found in git or comments — skipping", issue_identifier
        )
        return BugIngestionResult(
            issue_id=issue_id,
            issue_identifier=issue_identifier,
            files_indexed=0,
            source="none",
            skipped_no_commits=True,
            issue_status=issue_status,
        )

    rows = [
        {
            "id": str(uuid.uuid4()),
            "file_path": f,
            "bug_issue_id": issue_id,
            "bug_identifier": issue_identifier,
            "closed_at": completed_at,
            "source": source,
            "updated_at": datetime.now(timezone.utc),
        }
        for f in files
    ]

    if dry_run:
        logger.info(
            "Bug %s: DRY RUN — would index %d file(s) via %s",
            issue_identifier,
            len(rows),
            source,
        )
        for r in rows:
            logger.info("  DRY RUN row: file_path=%s", r["file_path"])
    else:
        with engine.begin() as conn:
            conn.execute(_UPSERT_SQL, rows)
        logger.info(
            "Bug %s: indexed %d file(s) via %s", issue_identifier, len(rows), source
        )
    return BugIngestionResult(
        issue_id=issue_id,
        issue_identifier=issue_identifier,
        files_indexed=len(rows),
        source=source,
        skipped_no_commits=False,
        issue_status=issue_status,
    )


def _parse_completed_at(issue: dict) -> datetime | None:
    raw = issue.get("completedAt")
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        logger.warning(
            "Bug issue %s: unexpected completedAt type %s (value=%r)",
            issue.get("identifier"),
            type(raw).__name__,
            raw,
        )
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        logger.warning(
            "Bug issue %s: malformed completedAt %r", issue.get("identifier"), raw
        )
        return None


def process_bug_issue(
    engine: Engine,
    issue_id: str,
    *,
    dry_run: bool = False,
) -> BugIngestionResult | None:
    """Fetch a single issue from Paperclip API and ingest as a bug.

    This is the webhook/event-driven entry point.  Returns None if the
    issue is not found or is FDR-labelled (handled by the FR worker).
    Non-done issues are accepted — the caller is expected to transition
    the issue to ``done`` after successful ingestion.
    """
    issue = get_issue_by_id(issue_id)
    if issue is None:
        logger.info("Bug issue %s not found — skipping", issue_id)
        return None
    if FDR_LABEL_ID in (issue.get("labelIds") or []):
        logger.info("Bug issue %s is FDR-labelled — skipping", issue_id)
        return None
    return ingest_bug_issue(
        engine,
        issue_id=issue["id"],
        issue_identifier=issue["identifier"],
        completed_at=_parse_completed_at(issue),
        description=issue.get("description", "") or "",
        dry_run=dry_run,
        issue_status=issue.get("status"),
    )


def run_bug_worker(
    engine: Engine,
    issues: Sequence[dict],
    *,
    dry_run: bool = False,
) -> list[BugIngestionResult]:
    """Ingest a list of closed bug issue dicts (from paperclip_client.get_closed_non_fdr_issues).

    When the list endpoint does not return the ``description`` field, the
    description fallback in ``ingest_bug_issue`` would never fire.  This
    function detects that case and fetches the full issue by ID to obtain
    the description, then retries.
    """
    results = []
    for issue in issues:
        try:
            result = ingest_bug_issue(
                engine,
                issue_id=issue["id"],
                issue_identifier=issue["identifier"],
                completed_at=_parse_completed_at(issue),
                description=issue.get("description", "") or "",
                dry_run=dry_run,
            )
            if result.source == "none" and not issue.get("description"):
                full = get_issue_by_id(issue["id"])
                if full and full.get("description"):
                    result = ingest_bug_issue(
                        engine,
                        issue_id=full["id"],
                        issue_identifier=full["identifier"],
                        completed_at=_parse_completed_at(full),
                        description=full.get("description", "") or "",
                        dry_run=dry_run,
                        issue_status=full.get("status"),
                    )
            results.append(result)
        except Exception:
            logger.exception("Bug worker error for %s", issue.get("identifier"))
    return results


def main() -> None:
    """CLI entry point: dispatch to __main__._run_bug_cli() (unified CLI)."""
    from .__main__ import _run_bug_cli

    _run_bug_cli()


if __name__ == "__main__":
    main()


def catch_up_eligible_bug_issues(
    engine: Engine,
    *,
    dry_run: bool = False,
) -> list[BugIngestionResult]:
    """Scan all git history for eligible done non-FDR issues not yet indexed.

    New commits can reference old issues, making them eligible for indexing
    even though they were completed outside the worker's lookback window.
    This catch-up ensures those issues are indexed, keeping eligible coverage
    consistently above the quality threshold without requiring a full backfill.
    """
    all_git_ids = get_all_referenced_issue_ids()
    if not all_git_ids:
        return []

    with engine.connect() as conn:
        indexed_rows = conn.execute(
            text("SELECT DISTINCT bug_identifier FROM touch_index_bug_files")
        ).fetchall()
    indexed_in_db: set[str] = {str(r[0]) for r in indexed_rows}

    results: list[BugIngestionResult] = []
    for identifier in sorted(all_git_ids):
        if identifier in indexed_in_db:
            continue
        issue = get_issue_by_identifier(identifier)
        if issue is None:
            continue
        if issue.get("status") != "done":
            continue
        if FDR_LABEL_ID in (issue.get("labelIds") or []):
            continue
        try:
            result = ingest_bug_issue(
                engine,
                issue_id=issue["id"],
                issue_identifier=identifier,
                completed_at=_parse_completed_at(issue),
                description=issue.get("description", "") or "",
                dry_run=dry_run,
                issue_status=issue.get("status"),
            )
            results.append(result)
        except Exception:
            logger.exception("Catch-up ingestion error for %s", identifier)
    if results:
        logger.info(
            "Catch-up complete: %d eligible issues processed, %d files indexed, %d skipped",
            len(results),
            sum(r.files_indexed for r in results),
            sum(1 for r in results if r.skipped_no_commits),
        )
    return results
