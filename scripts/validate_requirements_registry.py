#!/usr/bin/env python3
"""
Validate requirements_registry.json for structural integrity and CI readiness.

Usage:
    python scripts/validate_requirements_registry.py          # validate only
    python scripts/validate_requirements_registry.py --gaps   # also detect gaps
    python scripts/validate_requirements_registry.py --ci     # CI-friendly output

Exit codes:
    0 — all valid
    1 — structural errors (blocking)
    2 — gap warnings (non-blocking, only with --gaps)

Used by CI (requirements-gap-scan workflow) and pre-commit hooks.

Author: Architect (73eaab54) — BTCAAAAA-25644
"""

from __future__ import annotations

import json
import re
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "requirements_registry.json"

VALID_TYPES = {"FR", "NFR", "BR", "AR"}
VALID_STATUSES = {"active", "draft", "deprecated"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
ID_PATTERN = re.compile(r"^REQ-[A-Z]+-\d{3}$")

REQUIRED_FIELDS = [
    "id", "type", "title", "description", "source_issues",
    "source_modules", "test_files", "status", "priority", "owner_agent",
]

# ── helpers ──────────────────────────────────────────────────────────


def load_registry(path: Path) -> dict[str, Any]:
    """Load and parse the registry JSON. Exits on parse failure."""
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {path}: {e}")
        sys.exit(1)
    return data


def lint_ids(requirements: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for req in requirements:
        rid = req.get("id", "MISSING")
        if not ID_PATTERN.match(rid):
            errors.append(f"Invalid ID format: '{rid}' — must match REQ-DOMAIN-NNN")
        if rid in seen:
            errors.append(f"Duplicate ID: '{rid}'")
        seen.add(rid)
    return errors


def lint_fields(requirements: list[dict]) -> list[str]:
    errors: list[str] = []
    for req in requirements:
        rid = req.get("id", "MISSING")
        # required fields present
        for field in REQUIRED_FIELDS:
            if field not in req:
                errors.append(f"{rid}: missing required field '{field}'")
                continue
            val = req[field]
            if field in ("source_issues", "source_modules", "test_files") and req.get("status") == "active":
                if not isinstance(val, list):
                    errors.append(f"{rid}: '{field}' must be an array, got {type(val).__name__}")
            elif field == "type":
                if val not in VALID_TYPES:
                    errors.append(f"{rid}: invalid type '{val}' — must be one of {VALID_TYPES}")
            elif field == "status":
                if val not in VALID_STATUSES:
                    errors.append(f"{rid}: invalid status '{val}' — must be one of {VALID_STATUSES}")
            elif field == "priority":
                if val not in VALID_PRIORITIES:
                    errors.append(f"{rid}: invalid priority '{val}' — must be one of {VALID_PRIORITIES}")

        # deprecated requires superseded_by
        if req.get("status") == "deprecated" and not req.get("superseded_by"):
            errors.append(f"{rid}: deprecated requirement must have 'superseded_by'")

        # superseded_by must point to an existing requirement
        sup = req.get("superseded_by")
        if sup:
            if not any(r.get("id") == sup for r in requirements):
                errors.append(f"{rid}: 'superseded_by' references non-existent '{sup}'")
    return errors


def check_files_exist(requirements: list[dict], repo_root: Path) -> list[str]:
    """Verify source_modules and test_files paths exist on disk."""
    errors: list[str] = []
    for req in requirements:
        rid = req.get("id", "MISSING")
        for path_str in req.get("source_modules", []):
            if not (repo_root / path_str).exists():
                errors.append(f"{rid}: source_module not found: '{path_str}'")
        for path_str in req.get("test_files", []):
            # Directories are OK (tests/strategy_builder/validation/)
            p = repo_root / path_str
            if not p.exists():
                errors.append(f"{rid}: test_file not found: '{path_str}'")
    return errors


def detect_gaps(requirements: list[dict]) -> list[str]:
    """Detect requirements with no tests, stale references, orphan tests."""
    gaps: list[str] = []

    # 1. Active requirements with no test files
    for req in requirements:
        if req.get("status") == "active" and not req.get("test_files"):
            gaps.append(
                f"{req['id']} ({req.get('priority','?')}): no test_files — needs coverage"
            )

    # 2. Active requirements with no source_modules
    for req in requirements:
        if req.get("status") == "active" and not req.get("source_modules"):
            gaps.append(
                f"{req['id']} ({req.get('priority','?')}): no source_modules — needs module mapping"
            )

    # 3. Count of requirements by status
    active = sum(1 for r in requirements if r.get("status") == "active")
    draft = sum(1 for r in requirements if r.get("status") == "draft")
    deprecated = sum(1 for r in requirements if r.get("status") == "deprecated")
    gaps.append(f"Summary: {active} active, {draft} draft, {deprecated} deprecated — {len(requirements)} total")

    # 4. Requirements tagged needs-test
    needs_test = [r["id"] for r in requirements if "needs-test" in r.get("tags", [])]
    if needs_test:
        gaps.append(f"Requirements tagged needs-test: {', '.join(needs_test)}")

    return gaps


# ── main ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = ArgumentParser(description="Validate requirements_registry.json")
    parser.add_argument("--gaps", action="store_true", help="Also detect gaps in coverage")
    parser.add_argument("--ci", action="store_true", help="CI-friendly compact output")
    args = parser.parse_args()

    if not REGISTRY_PATH.exists():
        print(f"ERROR: Registry not found at {REGISTRY_PATH}")
        sys.exit(1)

    data = load_registry(REGISTRY_PATH)

    # Top-level validation
    if data.get("version") != 1:
        print(f"ERROR: Unsupported version {data.get('version')}")
        sys.exit(1)

    requirements: list[dict] = data.get("requirements", [])
    if not isinstance(requirements, list):
        print("ERROR: 'requirements' must be an array")
        sys.exit(1)

    all_errors: list[str] = []
    all_errors.extend(lint_ids(requirements))
    all_errors.extend(lint_fields(requirements))
    all_errors.extend(check_files_exist(requirements, REPO_ROOT))

    if all_errors:
        for err in all_errors:
            print(f"  FAIL: {err}")
        print(f"\nTotal structural errors: {len(all_errors)}")
        sys.exit(1)

    if args.gaps:
        gaps = detect_gaps(requirements)
        if gaps:
            for g in gaps:
                print(f"  GAP: {g}")
            # Gap detection is non-blocking (exit 2 for warnings)
            sys.exit(2)

    if not args.ci:
        print(f"OK: {len(requirements)} requirements validated successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
