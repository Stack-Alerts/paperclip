#!/usr/bin/env python3
"""Requirement Sync — syncs FDR-labelled Paperclip issues into trace_requirements.

Reads PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID,
POSTGRES_HOST/PORT/DB/USER/PASSWORD from environment.

Usage:
    PYTHONPATH=src python scripts/sync_trace_requirements.py
    python scripts/sync_trace_requirements.py --issue-id <uuid>
    python scripts/sync_trace_requirements.py --dry-run
    python scripts/sync_trace_requirements.py --lookback-minutes 60
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
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

load_dotenv(REPO_ROOT / ".env")

from optimizer_v3.database.models import TraceRequirement  # noqa: E402

logger = logging.getLogger(__name__)

STATUS_MAP: dict[str, str] = {
    "todo": "draft",
    "in_progress": "accepted",
    "in_review": "accepted",
    "done": "implemented",
    "cancelled": "deprecated",
    "blocked": "deprecated",
}

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


def fetch_fdr_issues(lookback_minutes: int | None = None) -> list[dict]:
    """Fetch FDR-labelled issues from Paperclip."""
    params: dict[str, Any] = {
        "labelId": FDR_LABEL_ID,
        "status": "todo,in_progress,in_review,done",
    }
    issues = _paginate(f"/api/companies/{_company_id()}/issues", params)
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
    """Fetch a single issue by UUID from Paperclip."""
    with _paperclip_session() as sess:
        resp = sess.get(f"{_api_base()}/api/issues/{issue_id}", timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def issue_to_requirement(issue: dict) -> dict[str, Any]:
    """Map a Paperclip issue dict to a trace_requirements row dict."""
    paperclip_status = issue.get("status", "todo")
    metadata = json.dumps({
        "paperclip_status": paperclip_status,
        "paperclip_created_at": issue.get("createdAt"),
        "paperclip_updated_at": issue.get("updatedAt"),
    })
    return {
        "identifier": issue.get("identifier", ""),
        "title": issue.get("title", "")[:500],
        "description": issue.get("description"),
        "status": STATUS_MAP.get(paperclip_status, "draft"),
        "priority": issue.get("priority"),
        "labels": issue.get("labels") or issue.get("labelIds"),
        "source": "paperclip",
        "paperclip_id": issue.get("id"),
        "metadata_": metadata,
    }


def upsert_requirements(engine, requirements: list[dict], dry_run: bool = False) -> int:
    """Upsert requirement rows into trace_requirements. Returns count."""
    if not requirements:
        return 0
    if dry_run:
        for r in requirements:
            logger.info("DRY-RUN would upsert: %s status=%s", r["identifier"], r["status"])
        return len(requirements)

    with Session(engine) as session:
        upserted = 0
        for r in requirements:
            stmt = pg_insert(TraceRequirement).values(**r)
            stmt = stmt.on_conflict_do_update(
                index_elements=["identifier"],
                set_={
                    "title": stmt.excluded.title,
                    "description": stmt.excluded.description,
                    "status": stmt.excluded.status,
                    "priority": stmt.excluded.priority,
                    "labels": stmt.excluded.labels,
                    "source": stmt.excluded.source,
                    "paperclip_id": stmt.excluded.paperclip_id,
                    "metadata": stmt.excluded.metadata,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            session.execute(stmt)
            upserted += 1
        session.commit()
    return upserted


def run_coverage_gap(engine) -> list[dict]:
    """Check for active requirements with zero linked test cases."""
    with Session(engine) as session:
        rows = session.execute(text("""
            SELECT r.identifier, r.title, r.status
            FROM trace_requirements r
            WHERE r.status IN ('accepted', 'implemented')
              AND r.id NOT IN (
                SELECT DISTINCT requirement_id
                FROM trace_links
                WHERE link_type = 'verifies' AND is_active = true
              )
        """)).fetchall()
    return [{"identifier": r[0], "title": r[1], "status": r[2]} for r in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync FDR issues → trace_requirements")
    parser.add_argument("--issue-id", metavar="UUID", help="Process a single FDR issue by Paperclip UUID")
    parser.add_argument("--lookback-minutes", type=int, default=30,
                        help="Lookback window in minutes (default: 30)")
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
            logger.error("Failed to fetch issue %s: %s", args.issue_id, exc)
            errors.append(str(exc))
            summary = {"status": "error", "error": str(exc),
                       "issues_processed": 0, "upserted": 0}
            if args.json_summary:
                json.dump(summary, sys.stdout, indent=2)
                sys.stdout.write("\n")
            return 1
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
        try:
            issues = fetch_fdr_issues(lookback_minutes=args.lookback_minutes)
        except Exception as exc:
            logger.error("Failed to fetch FDR issues: %s", exc)
            errors.append(str(exc))

    logger.info("Fetched %d FDR issue(s)", len(issues))

    reqs = [issue_to_requirement(i) for i in issues]
    try:
        upserted = upsert_requirements(engine, reqs, dry_run=args.dry_run)
    except Exception as exc:
        logger.error("Database upsert failed: %s", exc)
        errors.append(str(exc))
        upserted = 0
    else:
        logger.info("Upserted %d requirement(s)", upserted)

    gaps: list[dict] = []
    if not args.dry_run and not errors:
        try:
            gaps = run_coverage_gap(engine)
            if gaps:
                logger.info("Gap: %d requirement(s) with zero tests", len(gaps))
        except Exception as exc:
            logger.error("Coverage gap check failed: %s", exc)
            errors.append(str(exc))
    elif args.dry_run:
        logger.info("DRY-RUN: skipping coverage gap check")

    summary = {
        "status": "error" if errors else "success",
        "issues_processed": len(issues),
        "upserted": upserted,
        "coverage_gaps": len(gaps),
        "gap_details": gaps[:10] if gaps else [],
        "errors": errors,
        "dry_run": args.dry_run,
    }

    if args.json_summary:
        json.dump(summary, sys.stdout, indent=2)
        sys.stdout.write("\n")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
