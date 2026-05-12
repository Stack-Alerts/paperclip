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
from datetime import datetime
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .comment_extractor import fetch_and_extract
from .git_extractor import get_files_for_issue
from .paperclip_client import FDR_LABEL_ID, get_issue_by_id

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
    *,
    dry_run: bool = False,
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
        issue_identifier=issue_identifier,
        files_indexed=len(rows),
        source=source,
        skipped_no_commits=False,
    )


def _parse_completed_at(issue: dict) -> datetime | None:
    raw = issue.get("completedAt")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Bug issue %s: malformed completedAt %r", issue.get("identifier"), raw)
        return None


def process_bug_issue(
    engine: Engine,
    issue_id: str,
    *,
    dry_run: bool = False,
) -> BugIngestionResult | None:
    """Fetch a single issue from Paperclip API and ingest as a bug.

    This is the webhook/event-driven entry point.  Returns None if the
    issue is not found, is not done, or is FDR-labelled (handled by
    the FR worker).
    """
    issue = get_issue_by_id(issue_id)
    if issue is None:
        logger.info("Bug issue %s not found — skipping", issue_id)
        return None
    if issue.get("status") != "done":
        logger.info(
            "Bug issue %s has status %r — skipping (only done issues are ingested)",
            issue.get("identifier"), issue.get("status"),
        )
        return None
    if FDR_LABEL_ID in (issue.get("labelIds") or []):
        logger.info("Bug issue %s is FDR-labelled — skipping", issue_id)
        return None
    return ingest_bug_issue(
        engine,
        issue_id=issue["id"],
        issue_identifier=issue["identifier"],
        completed_at=_parse_completed_at(issue),
        dry_run=dry_run,
    )


def run_bug_worker(
    engine: Engine,
    issues: Sequence[dict],
    *,
    dry_run: bool = False,
) -> list[BugIngestionResult]:
    """Ingest a list of closed bug issue dicts (from paperclip_client.get_closed_non_fdr_issues)."""
    results = []
    for issue in issues:
        try:
            result = ingest_bug_issue(
                engine,
                issue_id=issue["id"],
                issue_identifier=issue["identifier"],
                completed_at=_parse_completed_at(issue),
                dry_run=dry_run,
            )
            results.append(result)
        except Exception:
            logger.exception("Bug worker error for %s", issue.get("identifier"))
    return results


def main() -> None:
    """CLI entry point: parse args and dispatch to process_bug_issue or run_bug_worker."""
    import argparse
    from datetime import datetime, timedelta, timezone

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Touch Index bug-close ingestion worker \u2014 upsert bug issue file references",
    )
    parser.add_argument(
        "--issue-id",
        type=str,
        metavar="UUID",
        help="Process a single non-FDR issue by Paperclip UUID (webhook trigger)",
    )
    parser.add_argument(
        "--lookback-minutes",
        type=int,
        default=30,
        help="Process bug issues closed within this many minutes (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be ingested without writing to DB",
    )
    args = parser.parse_args()

    from .db import get_engine, health_check
    from .paperclip_client import get_closed_non_fdr_issues

    engine = get_engine()
    if not health_check(engine):
        logger.error("DB health check failed \u2014 aborting")
        raise SystemExit(1)

    if args.issue_id:
        result = process_bug_issue(engine, args.issue_id, dry_run=args.dry_run)
        if result is None:
            logger.info("No bug issue found for %s", args.issue_id)
        else:
            logger.info(
                "%s: %d files indexed via %s, skipped=%s",
                result.issue_identifier,
                result.files_indexed,
                result.source,
                result.skipped_no_commits,
            )
        return

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.lookback_minutes)
    logger.info("Fetching closed non-FDR issues completed after %s", cutoff.isoformat())
    issues = get_closed_non_fdr_issues(closed_after=cutoff)
    logger.info("Found %d closed non-FDR issue(s) to process", len(issues))

    if not issues:
        logger.info("Nothing to do")
        return

    results = run_bug_worker(engine, issues, dry_run=args.dry_run)
    total_files = sum(r.files_indexed for r in results)
    skipped = sum(1 for r in results if r.skipped_no_commits)
    logger.info(
        "Bug worker done \u2014 %d issues processed, %d files indexed, %d skipped (no commits)",
        len(results),
        total_files,
        skipped,
    )


if __name__ == "__main__":
    main()
