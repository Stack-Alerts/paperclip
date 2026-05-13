#!/usr/bin/env python3
"""Issue Sync — syncs Paperclip issues into trace_issues with auto-linking.

For issues tagged with the FDR label, auto-creates trace_links entries to
trace_requirements with link_type = 'implements'.

Usage:
    PYTHONPATH=src python scripts/sync_trace_issues.py
    python scripts/sync_trace_issues.py --issue-id <uuid>
    python scripts/sync_trace_issues.py --labels FDR,fix,bug
    python scripts/sync_trace_issues.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

load_dotenv(REPO_ROOT / ".env")

from optimizer_v3.database.models import (  # noqa: E402
    TraceIssue,
    TraceRequirement,
    TraceLink,
)

logger = logging.getLogger(__name__)

FDR_LABEL_ID = "d523cb2d-acd9-423d-b87a-bb79cee42c40"


def _db_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "optimizer_v3")
    user = os.environ.get("POSTGRES_USER", "optimizer_admin")
    pwd = os.environ.get("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


def _paperclip_session():
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry

    retry = Retry(total=3, backoff_factor=0.5,
                  status_forcelist=[408, 429, 500, 502, 503, 504],
                  allowed_methods=["GET"], raise_on_status=False)
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}",
        "Content-Type": "application/json",
    })
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _api_base() -> str:
    return os.environ["PAPERCLIP_API_URL"].rstrip("/")


def _company_id() -> str:
    return os.environ["PAPERCLIP_COMPANY_ID"]


def _paginate(path: str, params: dict[str, Any], page_size: int = 100) -> list[dict]:
    with _paperclip_session() as sess:
        results: list[dict] = []
        params = {**params, "limit": page_size, "offset": 0}
        while True:
            resp = sess.get(f"{_api_base()}{path}", params=params, timeout=30)
            resp.raise_for_status()
            page = resp.json()
            if not page:
                break
            results.extend(page)
            if len(page) < page_size:
                break
            params["offset"] += page_size
        return results


def fetch_issues(lookback_minutes: int | None = None,
                 labels: list[str] | None = None,
                 statuses: list[str] | None = None) -> list[dict]:
    """Fetch issues from Paperclip with optional filters."""
    params: dict[str, Any] = {}
    if statuses:
        params["status"] = ",".join(statuses)
    if labels and FDR_LABEL_ID in labels:
        params["labelId"] = FDR_LABEL_ID

    issues = _paginate(f"/api/companies/{_company_id()}/issues", params)

    if labels:
        label_set = set(labels)
        issues = [i for i in issues
                  if any(lbl in label_set for lbl in (i.get("labelIds") or []))]

    if lookback_minutes is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        filtered: list[dict] = []
        for i in issues:
            raw = i.get("updatedAt")
            if raw:
                try:
                    ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                except ValueError:
                    pass
            filtered.append(i)
        issues = filtered

    return issues


def fetch_issue_by_id(issue_id: str) -> dict | None:
    with _paperclip_session() as sess:
        resp = sess.get(f"{_api_base()}/api/issues/{issue_id}", timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def issue_to_record(issue: dict) -> dict[str, Any]:
    """Map a Paperclip issue dict to a trace_issues row dict."""
    label_ids = issue.get("labelIds") or []
    issue_type = "task"
    if FDR_LABEL_ID in label_ids:
        issue_type = "fr"
    title = (issue.get("title") or "").lower()
    if "bug:" in title or "bug " in title:
        issue_type = "bug"
    if "fix:" in title or "fix " in title:
        issue_type = "fix"
    if "enhance" in title:
        issue_type = "enhancement"

    return {
        "identifier": issue.get("identifier", ""),
        "title": issue.get("title", "")[:500],
        "issue_type": issue_type,
        "status": issue.get("status", "todo"),
        "paperclip_id": issue.get("id"),
        "labels": label_ids,
        "parent_id": issue.get("parentId"),
    }


def upsert_issues(engine, issues: list[dict], dry_run: bool = False) -> int:
    """Upsert issue records into trace_issues (two-pass: insert then resolve parent FKs)."""
    if not issues:
        return 0
    if dry_run:
        for r in issues:
            logger.info("DRY-RUN would upsert: %s type=%s", r["identifier"], r["issue_type"])
        return len(issues)

    with Session(engine) as session:
        # Pass 1: insert all issues without parent_id (avoids FK violations)
        upserted = 0
        paperclip_parent_map: dict[str, str] = {}  # paperclip_id -> paperclip_parent_id
        for r in issues:
            fields = {
                "identifier": r["identifier"],
                "title": r["title"],
                "issue_type": r["issue_type"],
                "status": r["status"],
                "paperclip_id": r["paperclip_id"],
                "labels": r.get("labels"),
            }
            stmt = pg_insert(TraceIssue).values(**fields)
            stmt = stmt.on_conflict_do_update(
                index_elements=["identifier"],
                set_={
                    "title": stmt.excluded.title,
                    "issue_type": stmt.excluded.issue_type,
                    "status": stmt.excluded.status,
                    "paperclip_id": stmt.excluded.paperclip_id,
                    "labels": stmt.excluded.labels,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            session.execute(stmt)
            upserted += 1
            if r.get("parent_id"):
                paperclip_parent_map[r["paperclip_id"]] = r["parent_id"]
        session.commit()

        # Pass 2: resolve parent FKs (paperclip parentId -> trace_issues.id)
        if paperclip_parent_map:
            # Build lookup: paperclip_id -> internal id
            from uuid import UUID as PyUUID
            pc_ids = list({v for v in paperclip_parent_map.values()})
            parent_rows = session.execute(
                select(TraceIssue.id, TraceIssue.paperclip_id).where(
                    TraceIssue.paperclip_id.in_([PyUUID(pid) for pid in pc_ids])
                )
            ).fetchall()
            pc_to_internal: dict[str, PyUUID] = {
                str(row.paperclip_id): row.id for row in parent_rows
            }

            for child_pc_id, parent_pc_id in paperclip_parent_map.items():
                parent_internal = pc_to_internal.get(parent_pc_id)
                if parent_internal is None:
                    continue
                session.execute(
                    text(
                        "UPDATE trace_issues SET parent_id = :parent_id, "
                        "updated_at = :now WHERE paperclip_id = CAST(:child_pc_id AS uuid)"
                    ),
                    {"parent_id": parent_internal, "now": datetime.now(timezone.utc),
                     "child_pc_id": child_pc_id},
                )
            session.commit()

    return upserted


def create_implements_links(engine, issues: list[dict], dry_run: bool = False) -> int:
    """Auto-create 'implements' links for FDR-labelled issues → trace_requirements."""
    created = 0
    with Session(engine) as session:
        for i in issues:
            label_ids = i.get("labelIds") or i.get("labels") or []
            if not isinstance(label_ids, list):
                continue
            if FDR_LABEL_ID not in label_ids:
                continue

            identifier = i.get("identifier", "")
            if not identifier:
                continue

            req = session.execute(
                select(TraceRequirement).where(
                    TraceRequirement.identifier == identifier
                )
            ).scalar_one_or_none()

            issue_row = session.execute(
                select(TraceIssue).where(TraceIssue.identifier == identifier)
            ).scalar_one_or_none()

            if req is None or issue_row is None:
                continue

            if dry_run:
                logger.info("DRY-RUN would create implements link: issue=%s → req=%s",
                            identifier, req.identifier)
                created += 1
                continue

            stmt = pg_insert(TraceLink).values(
                requirement_id=req.id,
                issue_id=issue_row.id,
                link_type="implements",
                direction="forward",
                confidence=1.0,
                is_active=True,
                created_by="sync_trace_issues",
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_trace_link_edge",
                set_={
                    "direction": "forward",
                    "confidence": 1.0,
                    "is_active": True,
                },
            )
            session.execute(stmt)
            created += 1

        if not dry_run:
            session.commit()
    return created


def run_orphan_check(engine) -> list[str]:
    """Detect trace_issues rows with no matching Paperclip issue."""
    api_key = os.environ.get("PAPERCLIP_API_KEY", "")
    if not api_key:
        return []

    try:
        all_pc = _paginate(f"/api/companies/{_company_id()}/issues",
                           {"limit": 200}, page_size=200)
        pc_ids: set[str] = {i["id"] for i in all_pc}
    except Exception as exc:
        logger.error("Failed to fetch Paperclip issue IDs for orphan check: %s", exc)
        return []

    with Session(engine) as session:
        db_issues = session.execute(select(TraceIssue)).scalars().all()
        orphans: list[str] = []
        for di in db_issues:
            if di.paperclip_id and str(di.paperclip_id) not in pc_ids:
                orphans.append(di.identifier)
        return orphans


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Paperclip issues → trace_issues")
    parser.add_argument("--issue-id", metavar="UUID", help="Process a single issue by Paperclip UUID")
    parser.add_argument("--lookback-minutes", type=int, default=30,
                        help="Lookback window in minutes (default: 30)")
    parser.add_argument("--labels", help="Comma-separated label filter (e.g. FDR,fix,bug)")
    parser.add_argument("--status", help="Comma-separated status filter (e.g. done,in_review)")
    parser.add_argument("--dry-run", action="store_true", help="Log only, no DB writes")
    parser.add_argument("--json-summary", action="store_true",
                        help="Output structured JSON summary")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    api_key = os.environ.get("PAPERCLIP_API_KEY", "")
    if not api_key or not os.environ.get("PAPERCLIP_API_URL") or not os.environ.get("PAPERCLIP_COMPANY_ID"):
        logger.warning("PAPERCLIP_API_* not configured — no issues will be fetched")
        summary = {"status": "error", "error": "PAPERCLIP_API_* not configured",
                   "issues_processed": 0, "upserted": 0}
        if args.json_summary:
            json.dump(summary, sys.stdout, indent=2)
            sys.stdout.write("\n")
        return 1

    engine = create_engine(_db_url())

    issues: list[dict] = []
    errors: list[str] = []
    if args.issue_id:
        try:
            issue = fetch_issue_by_id(args.issue_id)
        except Exception as exc:
            errors.append(str(exc))
            issue = None
        if issue is None:
            logger.error("Issue %s not found", args.issue_id)
            summary = {"status": "error", "error": f"Issue {args.issue_id} not found",
                       "issues_processed": 0, "upserted": 0}
            if args.json_summary:
                json.dump(summary, sys.stdout, indent=2)
                sys.stdout.write("\n")
            return 1
        issues = [issue]
    else:
        label_list = args.labels.split(",") if args.labels else None
        status_list = args.status.split(",") if args.status else None
        try:
            issues = fetch_issues(lookback_minutes=args.lookback_minutes,
                                  labels=label_list, statuses=status_list)
        except Exception as exc:
            logger.error("Failed to fetch issues: %s", exc)
            errors.append(str(exc))

    logger.info("Fetched %d issue(s)", len(issues))

    records = [issue_to_record(i) for i in issues]
    try:
        upserted = upsert_issues(engine, records, dry_run=args.dry_run)
    except Exception as exc:
        logger.error("Database upsert failed: %s", exc)
        errors.append(str(exc))
        upserted = 0
    else:
        logger.info("Upserted %d issue(s)", upserted)

    implements_count = create_implements_links(engine, issues, dry_run=args.dry_run)
    if implements_count:
        logger.info("Auto-linked %d implements edge(s)", implements_count)

    orphans: list[str] = []
    if not args.dry_run and not errors:
        try:
            orphans = run_orphan_check(engine)
            if orphans:
                logger.info("Orphan: %d issue(s) not found in Paperclip", len(orphans))
        except Exception as exc:
            logger.error("Orphan check failed: %s", exc)
            errors.append(str(exc))

    summary = {
        "status": "error" if errors else "success",
        "issues_processed": len(issues),
        "upserted": upserted,
        "implements_links": implements_count,
        "orphans": len(orphans),
        "orphan_details": orphans[:10] if orphans else [],
        "errors": errors,
        "dry_run": args.dry_run,
    }
    if args.json_summary:
        json.dump(summary, sys.stdout, indent=2)
        sys.stdout.write("\n")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
