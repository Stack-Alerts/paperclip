#!/usr/bin/env python3
"""Test Case Collection — collects pytest metadata into trace_test_cases + auto-links.

Parses pytest --collect-only output for test functions, extracts markers
(@pytest.mark.fr, @pytest.mark.bug), and upserts into trace_test_cases.
Auto-creates trace_links for marker-based FR/bug references.

Usage:
    PYTHONPATH=src python scripts/sync_trace_test_cases.py
    python scripts/sync_trace_test_cases.py --dry-run
    python scripts/sync_trace_test_cases.py --test-dir tests/fr_acceptance
    python scripts/sync_trace_test_cases.py --regenerate-links
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
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
    TraceTestCase,
    TraceRequirement,
    TraceIssue,
    TraceLink,
)

logger = logging.getLogger(__name__)

MARKER_FR_RE = re.compile(r"fr\s*\(\s*['\"]([^'\"]+)['\"]")
MARKER_BUG_RE = re.compile(r"bug\s*\(\s*['\"]([^'\"]+)['\"]")
FILE_FDR_RE = re.compile(r"test_fdr[_\-](\d+)\.py", re.IGNORECASE)
TEST_ID_RE = re.compile(r"^(.+?)::(.+)$")
MARKER_DECORATOR_RE = re.compile('@pytest\\.mark\\.(fr|bug)\\s*\\(\\s*["\\x27]([^"\\x27]+)["\\x27]\\)')


def _db_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "optimizer_v3")
    user = os.environ.get("POSTGRES_USER", "optimizer_admin")
    pwd = os.environ.get("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


def run_collect_tests(test_dir: str) -> list[dict]:
    """Run pytest --collect-only -q and parse ::-separated test IDs."""
    test_path = REPO_ROOT / test_dir
    if not test_path.exists():
        logger.warning("Test directory %s does not exist", test_dir)
        return []

    env = {**os.environ, "PYTHONPATH": f"{REPO_ROOT / 'src'}"}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             "--override-ini=addopts=", str(test_path)],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=120,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.error("pytest --collect-only timed out")
        return []
    except FileNotFoundError:
        logger.error("pytest not found")
        return []

    output = proc.stdout
    tests: list[dict] = []

    for line in output.splitlines():
        line = line.strip()
        m = TEST_ID_RE.match(line)
        if not m:
            continue
        file_part = m.group(1).strip()
        func_part_raw = m.group(2).strip()
        if not file_part.endswith(".py"):
            continue

        rel_file = file_part

        # Split class::function
        func_parts = func_part_raw.split("::")
        test_class = None
        func_part = func_parts[-1]
        if len(func_parts) > 1:
            test_class = func_parts[0]

        # Extract markers by scanning source file
        markers, fr_refs, bug_refs = _extract_markers_from_file(file_part, func_part)

        tests.append({
            "identifier": f"{file_part}::{func_part_raw}",
            "test_file": rel_file,
            "test_function": func_part,
            "test_class": test_class,
            "markers": json.dumps(markers) if markers else None,
            "fr_refs": fr_refs,
            "bug_refs": bug_refs,
            "source": "pytest_collection",
            "language": "python",
        })

    logger.info("Collected %d test case(s)", len(tests))
    return tests


def _extract_markers_from_file(file_part: str, func_name: str) -> tuple[list[str], list[str], list[str]]:
    """Scan a test source file for @pytest.mark.fr / @pytest.mark.bug decorators."""
    src_path = REPO_ROOT / file_part
    if not src_path.exists():
        return [], [], []

    try:
        with open(src_path) as f:
            source = f.read()
    except Exception:
        return [], [], []

    markers: list[str] = []
    fr_refs: list[str] = []
    bug_refs: list[str] = []

    for m in MARKER_DECORATOR_RE.finditer(source):
        mtype, value = m.group(1), m.group(2)
        markers.append(f"{mtype}({value})")
        if mtype == "fr":
            fr_refs.append(value)
        elif mtype == "bug":
            bug_refs.append(value)

    return markers, fr_refs, bug_refs



def upsert_test_cases(engine, tests: list[dict], dry_run: bool = False) -> int:
    """Upsert test case metadata into trace_test_cases. Returns count."""
    if not tests:
        return 0
    if dry_run:
        for t in tests:
            logger.info("DRY-RUN would upsert: %s", t["identifier"])
        return len(tests)

    with Session(engine) as session:
        upserted = 0
        for t in tests:
            fields = {
                "identifier": t["identifier"],
                "test_file": t["test_file"],
                "test_function": t["test_function"],
                "test_class": t.get("test_class"),
                "markers": t.get("markers"),
                "source": t.get("source", "pytest_collection"),
                "language": t.get("language", "python"),
                "component": t.get("component"),
            }
            stmt = pg_insert(TraceTestCase).values(**fields)
            stmt = stmt.on_conflict_do_update(
                index_elements=["identifier"],
                set_={
                    "test_file": stmt.excluded.test_file,
                    "test_function": stmt.excluded.test_function,
                    "test_class": stmt.excluded.test_class,
                    "markers": stmt.excluded.markers,
                    "source": stmt.excluded.source,
                    "language": stmt.excluded.language,
                    "component": stmt.excluded.component,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            session.execute(stmt)
            upserted += 1
        session.commit()
    return upserted


def create_marker_links(engine, tests: list[dict], dry_run: bool = False) -> dict[str, int]:
    """Auto-create trace_links from pytest markers (fr/bug)."""
    if dry_run:
        verifies = sum(len(t.get("fr_refs", [])) for t in tests)
        bugs = sum(len(t.get("bug_refs", [])) for t in tests)
        logger.info("DRY-RUN: would create %d verifies + %d tests links", verifies, bugs)
        return {"verifies": verifies, "tests": bugs}

    created_verifies = 0
    created_tests = 0

    with Session(engine) as session:
        # Look up requirement and issue IDs
        for t in tests:
            if not t.get("fr_refs") and not t.get("bug_refs"):
                continue

            test_case = session.execute(
                select(TraceTestCase).where(TraceTestCase.identifier == t["identifier"])
            ).scalar_one_or_none()
            if test_case is None:
                continue

            for fr_ref in t.get("fr_refs", []):
                req = session.execute(
                    select(TraceRequirement).where(
                        TraceRequirement.identifier == fr_ref
                    )
                ).scalar_one_or_none()
                if req is None:
                    fdr_id = f"FDR-{fr_ref}"
                    req = session.execute(
                        select(TraceRequirement).where(
                            TraceRequirement.identifier == fdr_id
                        )
                    ).scalar_one_or_none()
                if req is None:
                    logger.debug("Requirement %s not found for test %s", fr_ref, t["identifier"])
                    continue
                if dry_run:
                    logger.info("DRY-RUN would create verifies link: test=%s → req=%s", t["identifier"], req.identifier)
                    created_verifies += 1
                    continue
                _upsert_link(session, TraceLink(
                    requirement_id=req.id,
                    test_case_id=test_case.id,
                    link_type="verifies",
                    direction="forward",
                    confidence=1.0,
                    is_active=True,
                    created_by="sync_trace_test_cases",
                ))
                created_verifies += 1

            for bug_ref in t.get("bug_refs", []):
                issue = session.execute(
                    select(TraceIssue).where(TraceIssue.identifier == bug_ref)
                ).scalar_one_or_none()
                if issue is None:
                    logger.debug("Issue %s not found for test %s", bug_ref, t["identifier"])
                    continue
                if dry_run:
                    logger.info("DRY-RUN would create tests link: test=%s → issue=%s", t["identifier"], bug_ref)
                    created_tests += 1
                    continue
                _upsert_link(session, TraceLink(
                    test_case_id=test_case.id,
                    issue_id=issue.id,
                    link_type="tests",
                    direction="forward",
                    confidence=1.0,
                    is_active=True,
                    created_by="sync_trace_test_cases",
                ))
                created_tests += 1

        if not dry_run:
            session.commit()

    return {"verifies": created_verifies, "tests": created_tests}


def _upsert_link(session, link: TraceLink) -> None:
    """Upsert a single trace_link row."""
    stmt = pg_insert(TraceLink).values(
        requirement_id=link.requirement_id,
        test_case_id=link.test_case_id,
        issue_id=link.issue_id,
        link_type=link.link_type,
        direction=link.direction,
        confidence=link.confidence,
        is_active=link.is_active,
        created_by=link.created_by,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_trace_link_edge",
        set_={
            "direction": stmt.excluded.direction,
            "confidence": stmt.excluded.confidence,
            "is_active": True,
            "created_by": stmt.excluded.created_by,
        },
    )
    session.execute(stmt)


def create_file_heuristic_links(engine, tests: list[dict], dry_run: bool = False) -> int:
    """Create verifies links based on file-name heuristics (test_fdr_NNN.py → FDR-NNN)."""
    if dry_run:
        count = sum(1 for t in tests if FILE_FDR_RE.search(t.get("test_file", "")))
        logger.info("DRY-RUN: would create %d file-heuristic links", count)
        return count

    created = 0
    with Session(engine) as session:
        for t in tests:
            m = FILE_FDR_RE.search(t["test_file"])
            if not m:
                continue
            fdr_num = m.group(1)
            req_identifier = f"FDR-{fdr_num}"

            req = session.execute(
                select(TraceRequirement).where(
                    TraceRequirement.identifier == req_identifier
                )
            ).scalar_one_or_none()
            if req is None:
                continue

            test_case = session.execute(
                select(TraceTestCase).where(TraceTestCase.identifier == t["identifier"])
            ).scalar_one_or_none()
            if test_case is None:
                continue

            if dry_run:
                logger.info("DRY-RUN would create heuristic verifies link: %s → %s (confidence=0.7)",
                            t["identifier"], req_identifier)
                created += 1
                continue

            _upsert_link(session, TraceLink(
                requirement_id=req.id,
                test_case_id=test_case.id,
                link_type="verifies",
                direction="forward",
                confidence=0.7,
                is_active=True,
                created_by="sync_trace_test_cases",
                metadata_=json.dumps({"source": "file_name_heuristic"}),
            ))
            created += 1

        if not dry_run:
            session.commit()

    return created


def run_gap_analysis(engine) -> list[dict]:
    """Compare collected tests against requirements_registry.json for untested requirements."""
    registry_path = REPO_ROOT / "requirements_registry.json"
    if not registry_path.exists():
        return []

    with open(registry_path) as f:
        registry = json.load(f)

    active_reqs = [r for r in registry.get("requirements", [])
                   if r.get("status") == "active"]

    untested: list[dict] = []
    for req in active_reqs:
        test_files = req.get("test_files", [])
        test_markers = req.get("test_markers", [])
        if not test_files and not test_markers:
            untested.append({"id": req["id"], "title": req.get("title", ""),
                             "priority": req.get("priority", "unknown")})

    return untested


def regenerate_links(engine, tests: list[dict], dry_run: bool = False) -> dict:
    """Drop and recreate all test→requirement/issue links for collected tests."""
    if dry_run:
        counts = create_marker_links(engine, tests, dry_run=True)
        heuristic = create_file_heuristic_links(engine, tests, dry_run=True)
        logger.info("DRY-RUN: would drop and recreate all test links")
        return {"dropped": 0, "verifies": counts.get("verifies", 0),
                "tests": counts.get("tests", 0), "heuristic": heuristic}

    with Session(engine) as session:
        test_ids = [t["identifier"] for t in tests]
        existing = session.execute(
            select(TraceTestCase.id).where(TraceTestCase.identifier.in_(test_ids))
        ).fetchall()
        tc_ids = [r[0] for r in existing]
        if tc_ids:
            deleted = session.execute(
                text("DELETE FROM trace_links WHERE test_case_id IN :ids"),
                {"ids": tuple(tc_ids)},
            )
            logger.info("Deleted %d link(s) for regeneration", deleted.rowcount)
        session.commit()

    link_counts = create_marker_links(engine, tests, dry_run=False)
    heuristic_count = create_file_heuristic_links(engine, tests, dry_run=False)
    return {"dropped": len(existing), "verifies": link_counts["verifies"],
            "tests": link_counts["tests"], "heuristic": heuristic_count}


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect test cases → trace_test_cases")
    parser.add_argument("--test-dir", default="tests/", help="Test directory to scan (default: tests/)")
    parser.add_argument("--dry-run", action="store_true", help="Log only, no DB writes")
    parser.add_argument("--regenerate-links", action="store_true",
                        help="Drop and recreate all test→requirement/issue links")
    parser.add_argument("--json-summary", action="store_true",
                        help="Output structured JSON summary")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    engine = create_engine(_db_url())

    tests = run_collect_tests(args.test_dir)
    if not tests:
        logger.warning("No test cases collected from %s", args.test_dir)
        summary = {"status": "warning", "collected": 0, "upserted": 0,
                   "links_created": {}, "file_heuristic_links": 0,
                   "untested_requirements": [], "dry_run": args.dry_run}
        if args.json_summary:
            json.dump(summary, sys.stdout, indent=2)
            sys.stdout.write("\n")
        return 0

    upserted = upsert_test_cases(engine, tests, dry_run=args.dry_run)

    if args.regenerate_links:
        link_counts = regenerate_links(engine, tests, dry_run=args.dry_run)
        heuristic_count = link_counts.get("heuristic", 0)
    else:
        link_counts = create_marker_links(engine, tests, dry_run=args.dry_run)
        heuristic_count = create_file_heuristic_links(engine, tests, dry_run=args.dry_run)

    logger.info("Created %d link(s) from markers (verifies=%d, tests=%d)",
                link_counts.get("verifies", 0) + link_counts.get("tests", 0),
                link_counts.get("verifies", 0), link_counts.get("tests", 0))
    logger.info("Created %d link(s) from file-name heuristics", heuristic_count)

    untested: list[dict] = []
    if not args.dry_run:
        untested = run_gap_analysis(engine)
        if untested:
            logger.info("Gap: %d requirement(s) with zero tests", len(untested))

    summary = {
        "status": "success",
        "collected": len(tests),
        "upserted": upserted,
        "links_created": {
            "verifies": link_counts.get("verifies", 0),
            "tests": link_counts.get("tests", 0),
            "file_heuristic": heuristic_count,
        },
        "untested_requirements": [u["id"] for u in untested[:20]],
        "dry_run": args.dry_run,
    }
    if args.json_summary:
        json.dump(summary, sys.stdout, indent=2)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
