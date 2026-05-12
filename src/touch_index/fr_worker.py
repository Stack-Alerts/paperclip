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
from .paperclip_client import FDR_LABEL_ID, get_issue_by_id

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


def process_fr_issue(
    engine: Engine,
    issue_id: str,
    *,
    dry_run: bool = False,
) -> FRIngestionResult | None:
    """Fetch a single FDR issue from Paperclip API and ingest it.

    This is the webhook/event-driven entry point.  Returns None if the
    issue is not found or is not an FDR-labelled issue.
    """
    issue = get_issue_by_id(issue_id)
    if issue is None:
        logger.info("FR issue %s not found — skipping", issue_id)
        return None
    if FDR_LABEL_ID not in (issue.get("labelIds") or []):
        logger.info("Issue %s is not FDR-labelled — skipping", issue.get("identifier"))
        return None
    return ingest_fr_issue(
        engine,
        issue_id=issue["id"],
        issue_identifier=issue["identifier"],
        owner_agent_id=issue.get("assigneeAgentId"),
        description=issue.get("description", "") or "",
        dry_run=dry_run,
    )


def ingest_fr_issue(
    engine: Engine,
    issue_id: str,
    issue_identifier: str,
    owner_agent_id: str | None,
    description: str = "",
    *,
    dry_run: bool = False,
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

    if dry_run:
        logger.info(
            "FR %s: DRY RUN — would index %d file(s) via %s",
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
            "FR %s: indexed %d file(s) via %s", issue_identifier, len(rows), source
        )
    return FRIngestionResult(
        issue_identifier=issue_identifier,
        files_indexed=len(rows),
        source=source,
        skipped_no_commits=False,
    )


def run_fr_worker(
    engine: Engine,
    issues: Sequence[dict],
    *,
    dry_run: bool = False,
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
                dry_run=dry_run,
            )
            results.append(result)
        except Exception:
            logger.exception("FR worker error for %s", issue.get("identifier"))
    return results


def main() -> None:
    """CLI entry point: parse args and dispatch to process_fr_issue or run_fr_worker."""
    import argparse
    from datetime import datetime, timedelta, timezone

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Touch Index FR ingestion worker — upsert FDR issue file references",
    )
    parser.add_argument(
        "--issue-id",
        type=str,
        metavar="UUID",
        help="Process a single FDR issue by Paperclip UUID (webhook trigger)",
    )
    parser.add_argument(
        "--lookback-minutes",
        type=int,
        default=30,
        help="Process FDR issues updated within this many minutes (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be ingested without writing to DB or transitioning issues",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run FR data quality validation after ingestion (exits non-zero on failure)",
    )
    args = parser.parse_args()

    from .db import get_engine, health_check
    from .paperclip_client import get_fdr_issues, transition_issue_status

    engine = get_engine()
    if not health_check(engine):
        logger.error("DB health check failed — aborting")
        raise SystemExit(1)

    if args.issue_id:
        result = process_fr_issue(engine, args.issue_id, dry_run=args.dry_run)
        if result is None:
            logger.info("No FR issue found for %s", args.issue_id)
        else:
            logger.info(
                "%s: %d files indexed via %s, skipped=%s",
                result.issue_identifier,
                result.files_indexed,
                result.source,
                result.skipped_no_commits,
            )
        if args.validate:
            from .quality import run_quality_checks
            report = run_quality_checks(engine)
            if not report.passed:
                logger.error("VALIDATION FAILED after single-issue ingestion")
                raise SystemExit(1)
            logger.info("VALIDATION PASSED after single-issue ingestion")
        return

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.lookback_minutes)
    logger.info("Fetching FDR issues updated after %s", cutoff.isoformat())
    issues = get_fdr_issues(updated_after=cutoff)
    logger.info("Found %d FDR issue(s) to process", len(issues))

    if not issues:
        logger.info("Nothing to do")
        if args.validate:
            from .quality import run_quality_checks
            report = run_quality_checks(engine)
            if not report.passed:
                logger.error("VALIDATION FAILED — investigate existing data")
                raise SystemExit(1)
            logger.info("VALIDATION PASSED — existing data clean")
        return

    results = run_fr_worker(engine, issues, dry_run=args.dry_run)

    total_files = sum(r.files_indexed for r in results)
    skipped = sum(1 for r in results if r.skipped_no_commits)

    # Mark each processed issue as done in Paperclip.
    # Skip issues already in done status to avoid 403 on redundant transition.
    # Skip in dry-run mode — no side effects.
    if args.dry_run:
        logger.info("DRY RUN — skipping transition-to-done for %d issue(s)", len(issues))
    else:
        for issue in issues:
            issue_id = issue.get("id", "")
            if not issue_id or issue.get("status") == "done":
                continue
            try:
                transition_issue_status(issue_id, "done")
                logger.info("Marked %s as done", issue.get("identifier", issue_id))
            except Exception:
                logger.exception(
                    "Failed to mark %s as done", issue.get("identifier", issue_id)
                )

    logger.info(
        "FR worker done — %d issues processed, %d files indexed, %d skipped (no commits)",
        len(results),
        total_files,
        skipped,
    )

    if args.validate:
        from .quality import run_quality_checks
        report = run_quality_checks(engine)
        if not report.passed:
            logger.error("VALIDATION FAILED after ingestion — investigate")
            raise SystemExit(1)
        logger.info("VALIDATION PASSED: all quality checks clean")


if __name__ == "__main__":
    main()
