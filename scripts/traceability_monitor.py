#!/usr/bin/env python3
"""Traceability Monitor — health check for all three sync pipelines.

Runs after each sync cycle and on a scheduled health check (every 30 min):
- Verifies traceability tables exist and have data
- Checks for coverage gaps > 10%
- Detects orphan records
- Generates a Paperclip alert if any pipeline appears unhealthy

Usage:
    PYTHONPATH=src python scripts/traceability_monitor.py
    python scripts/traceability_monitor.py --json-summary
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

load_dotenv(REPO_ROOT / ".env")

logger = logging.getLogger(__name__)

COVERAGE_GAP_THRESHOLD = 0.10  # 10%


def _db_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "optimizer_v3")
    user = os.environ.get("POSTGRES_USER", "optimizer_admin")
    pwd = os.environ.get("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


def check_table_health(engine) -> dict[str, dict]:
    """Check row counts for each traceability table."""
    health: dict[str, dict] = {}
    with Session(engine) as session:
        for table in ["trace_requirements", "trace_test_cases", "trace_issues", "trace_links"]:
            try:
                row = session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar_one()
                health[table] = {"row_count": row, "healthy": True}
            except Exception as exc:
                health[table] = {"row_count": 0, "healthy": False,
                                 "error": str(exc)}
    return health


def check_coverage_gap(engine) -> dict[str, Any]:
    """Check coverage gap percentage for active requirements."""
    with Session(engine) as session:
        try:
            total = session.execute(text("""
                SELECT COUNT(*) FROM trace_requirements
                WHERE status IN ('accepted', 'implemented')
            """)).scalar_one()

            untested = session.execute(text("""
                SELECT COUNT(*) FROM trace_requirements r
                WHERE r.status IN ('accepted', 'implemented')
                  AND r.id NOT IN (
                    SELECT DISTINCT requirement_id FROM trace_links
                    WHERE link_type = 'verifies' AND is_active = true
                  )
            """)).scalar_one()

            gap = untested / max(total, 1)
            return {
                "total_active": total,
                "untested": untested,
                "gap_pct": round(gap * 100, 1),
                "healthy": gap <= COVERAGE_GAP_THRESHOLD,
            }
        except Exception as exc:
            return {"error": str(exc), "healthy": False}


def check_orphan_count(engine) -> dict[str, Any]:
    """Count orphan trace_issues rows (hasn't been updated in 7 days, no Paperclip match)."""
    with Session(engine) as session:
        try:
            orphan_count = session.execute(text("""
                SELECT COUNT(*) FROM trace_issues
                WHERE paperclip_id IS NULL
                   OR updated_at < NOW() - INTERVAL '7 days'
            """)).scalar_one()
            return {"orphan_count": orphan_count,
                    "healthy": orphan_count < 10}
        except Exception as exc:
            return {"error": str(exc), "healthy": False, "orphan_count": 0}


def check_link_health(engine) -> dict[str, Any]:
    """Check link integrity — counts by type."""
    with Session(engine) as session:
        try:
            rows = session.execute(text("""
                SELECT link_type, COUNT(*) as cnt
                FROM trace_links WHERE is_active = true
                GROUP BY link_type
            """)).fetchall()
            link_counts = {r[0]: r[1] for r in rows}
            total = sum(link_counts.values())
            return {"link_counts": link_counts, "total_links": total,
                    "has_verifies": link_counts.get("verifies", 0) > 0,
                    "has_implements": link_counts.get("implements", 0) > 0,
                    "has_tests": link_counts.get("tests", 0) > 0,
                    "healthy": total > 0}
        except Exception as exc:
            return {"error": str(exc), "healthy": False}


def determine_overall_status(table_health: dict, coverage: dict,
                              orphans: dict, links: dict) -> tuple[str, str]:
    """Determine overall health status and severity."""
    table_unhealthy = any(not v.get("healthy", True) for v in table_health.values())
    coverage_unhealthy = not coverage.get("healthy", True)
    orphan_unhealthy = not orphans.get("healthy", True)
    links_unhealthy = not links.get("healthy", True)

    failures = sum([table_unhealthy, coverage_unhealthy, orphan_unhealthy, links_unhealthy])
    if failures == 0:
        return "healthy", "low"
    elif failures <= 2:
        return "degraded", "medium"
    else:
        return "critical", "critical"


def post_alert(alert_level: str, message: str) -> bool:
    """Post a monitoring alert via Paperclip API (best-effort)."""
    api_key = os.environ.get("PAPERCLIP_API_KEY", "")
    api_url = os.environ.get("PAPERCLIP_API_URL", "")
    if not api_key or not api_url:
        logger.warning("Cannot post alert: PAPERCLIP_API_* not configured")
        return False

    import requests
    try:
        resp = requests.post(
            f"{api_url.rstrip('/')}/api/alerts",
            json={"level": alert_level, "message": message,
                  "source": "traceability_monitor"},
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code >= 400:
            logger.warning("Alert post returned %d: %s", resp.status_code, resp.text)
            return False
        return True
    except Exception as exc:
        logger.warning("Failed to post alert: %s", exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Traceability health monitor")
    parser.add_argument("--json-summary", action="store_true",
                        help="Output structured JSON summary")
    parser.add_argument("--no-alert", action="store_true",
                        help="Skip alert posting (for local dev)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    try:
        engine = create_engine(_db_url())
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        summary = {"status": "error", "error": str(exc),
                   "timestamp": datetime.now(timezone.utc).isoformat()}
        if args.json_summary:
            json.dump(summary, sys.stdout, indent=2)
            sys.stdout.write("\n")
        return 1

    table_health = check_table_health(engine)
    coverage = check_coverage_gap(engine)
    orphans = check_orphan_count(engine)
    links = check_link_health(engine)

    overall_status, severity = determine_overall_status(
        table_health, coverage, orphans, links
    )

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": overall_status,
        "severity": severity,
        "table_health": {
            k: v.get("row_count") if v.get("healthy") else {"error": v.get("error")}
            for k, v in table_health.items()
        },
        "coverage": coverage,
        "orphans": orphans,
        "links": links,
    }

    if overall_status == "healthy":
        logger.info("Traceability monitor: ALL HEALTHY")
    elif overall_status == "degraded":
        logger.warning("Traceability monitor: DEGRADED — %s", json.dumps({
            k: v for k, v in summary.items() if k != "timestamp"
        }, default=str))
    else:
        logger.error("Traceability monitor: CRITICAL — %s", json.dumps({
            k: v for k, v in summary.items() if k != "timestamp"
        }, default=str))

    if overall_status in ("degraded", "critical") and not args.no_alert:
        alert_msg = (
            f"Traceability monitor: {overall_status.upper()} (severity={severity}) — "
            f"Tables: {', '.join(f'{k}={v.get('row_count', '?')}rows' for k, v in table_health.items())}, "
            f"Coverage gap: {coverage.get('gap_pct', '?')} %, "
            f"Orphans: {orphans.get('orphan_count', '?')}"
        )
        post_alert(severity, alert_msg)

    if args.json_summary:
        json.dump(summary, sys.stdout, indent=2)
        sys.stdout.write("\n")

    return 0 if overall_status == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
