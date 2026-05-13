#!/usr/bin/env python3
"""
Lock Module Verification — requirement verification gate for locked module changes.

When a locked module is touched in a PR:
1. Detect which locked modules changed (via lock_gate.py detection)
2. Map changed locked modules to their verification tests (FR + bug regression)
3. Run the mapped tests via Impact Gate runner
4. Report results as JSON (for CI consumption) and Markdown (for PR comments)

Integration point: extends the lock-gate CI workflow with requirement verification.
Registry format defined in lock_module_verification_registry.json (populated by Architect).

Usage:
    python scripts/lock_module_verify.py                    # CI mode (git diff origin/main...HEAD)
    python scripts/lock_module_verify.py --local             # local mode (diffs HEAD~1)
    python scripts/lock_module_verify.py --diff-file <path>  # read a diff file (test fixture)
    python scripts/lock_module_verify.py --changed-files <f1,f2,...>  # explicit file list
    python scripts/lock_module_verify.py --json              # JSON output (default)
    python scripts/lock_module_verify.py --markdown          # Markdown report output
    python scripts/lock_module_verify.py --touch-index       # use Touch Index DB for discovery

Exit codes:
    0 — all verification tests passed (or nothing to verify)
    1 — one or more verification tests failed
    2 — configuration / argument error
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "lock_module_verification_registry.json"
REQUIREMENTS_REGISTRY_PATH = REPO_ROOT / "requirements_registry.json"
LOCK_REGISTRY_PATH = REPO_ROOT / ".module_lock_registry.json"
IMPACT_GATE_RUNNER = REPO_ROOT / "scripts" / "impact_gate_runner.py"


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def get_changed_files_ci() -> list[str]:
    """Get changed files in CI by diffing against the merge-base of base_ref."""
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    try:
        subprocess.run(
            ["git", "fetch", "origin", base_ref],
            capture_output=True, check=True,
        )
    except subprocess.CalledProcessError:
        pass
    result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        capture_output=True, text=True, check=True,
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def get_changed_files_local() -> list[str]:
    """Get changed files in local mode (diffs HEAD~1)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1"],
        capture_output=True, text=True, check=True,
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def get_changed_files_from_diff(diff_path: str) -> list[str]:
    """Parse changed files from a diff file (test fixture support)."""
    changed: set[str] = set()
    with open(diff_path) as f:
        for line in f:
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                path = line[6:].strip()
                if path and path != "/dev/null":
                    changed.add(path)
            elif line.startswith("diff --git a/"):
                parts = line.split()
                if len(parts) >= 4:
                    path = parts[3][2:]
                    changed.add(path)
    return sorted(changed)


def matches_locked_path(file_path: str, locked_entries: list[dict]) -> Optional[dict]:
    """Check if file_path matches any locked path (prefix match)."""
    for entry in locked_entries:
        locked_path = entry["path"]
        if locked_path.endswith("/"):
            if file_path.startswith(locked_path) or file_path == locked_path.rstrip("/"):
                return entry
        else:
            if file_path == locked_path or file_path.startswith(locked_path + "/"):
                return entry
    return None


def find_affected_locked_modules(
    changed_files: list[str],
    lock_registry: dict,
) -> list[dict]:
    """Return list of (file_path, locked_entry) for changed files that hit locked modules."""
    locked_entries = lock_registry["entries"]
    hits: list[dict] = []
    seen: set[str] = set()
    for f in changed_files:
        entry = matches_locked_path(f, locked_entries)
        if entry and entry["path"] not in seen:
            seen.add(entry["path"])
            hits.append({"file_path": f, "locked_path": entry["path"], "reason": entry["reason"]})
    return hits


def find_verification_tests_from_requirements_registry(
    locked_paths: list[str],
    requirements_registry: dict,
) -> dict[str, dict]:
    """Map locked paths to test files using the canonical requirements_registry.json.

    Matches each locked_path against source_modules in all requirements.
    Returns {locked_path: {fr_ids: [...], bug_ids: [...], test_paths: [...]}}
    """
    requirements = requirements_registry.get("requirements", [])
    result: dict[str, dict] = {}

    for lp in locked_paths:
        fr_ids: list[str] = []
        bug_ids: list[str] = []
        test_paths: list[str] = []
        matched_reqs: list[str] = []

        for req in requirements:
            source_modules = req.get("source_modules", [])
            matched = False
            for sm in source_modules:
                if lp.endswith("/"):
                    if sm.startswith(lp) or sm == lp.rstrip("/"):
                        matched = True
                        break
                else:
                    if sm == lp or sm.startswith(lp + "/"):
                        matched = True
                        break
            if matched:
                matched_reqs.append(req["id"])
                test_files = req.get("test_files", [])
                test_paths.extend(test_files)

        # Deduplicate test paths
        test_paths = list(dict.fromkeys(test_paths))

        result[lp] = {
            "fr_ids": fr_ids,
            "bug_ids": bug_ids,
            "test_paths": test_paths,
            "_matched_requirements": matched_reqs,
            "_source": "requirements_registry",
        }

    return result


def find_verification_tests(
    locked_paths: list[str],
    verification_registry: dict,
) -> dict[str, dict]:
    """Map locked paths to their verification test IDs and test file paths.

    Returns {locked_path: {fr_ids: [...], bug_ids: [...], test_paths: [...]}}
    """
    mappings = verification_registry.get("mappings", [])
    result: dict[str, dict] = {}

    for lp in locked_paths:
        found = None
        for m in mappings:
            if m["locked_path"] == lp:
                found = m
                break
        if found:
            result[lp] = {
                "fr_ids": found.get("fr_tests", []),
                "bug_ids": found.get("bug_tests", []),
                "test_paths": found.get("test_paths", []),
            }
        else:
            result[lp] = {"fr_ids": [], "bug_ids": [], "test_paths": []}

    return result


def query_touch_index_fr(locked_path: str) -> list[str]:
    """Query Touch Index for FR IDs affected by a locked module path (best-effort)."""
    try:
        from touch_index.db import get_engine as ti_get_engine
        from sqlalchemy import text
        engine = ti_get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT DISTINCT fr_identifier FROM touch_index_fr_files "
                    "WHERE file_path LIKE :pat ORDER BY fr_identifier"
                ),
                {"pat": locked_path.rstrip("/") + "%"},
            ).fetchall()
        engine.dispose()
        return [row.fr_identifier for row in rows]
    except Exception:
        return []


def query_touch_index_bugs(locked_path: str) -> list[str]:
    """Query Touch Index for bug IDs affected by a locked module path (best-effort)."""
    try:
        from touch_index.db import get_engine as ti_get_engine
        from sqlalchemy import text
        engine = ti_get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT DISTINCT bug_identifier FROM touch_index_bug_files "
                    "WHERE file_path LIKE :pat ORDER BY bug_identifier"
                ),
                {"pat": locked_path.rstrip("/") + "%"},
            ).fetchall()
        engine.dispose()
        return [row.bug_identifier for row in rows]
    except Exception:
        return []


def run_tests_for_ids(fr_ids: list[str], bug_ids: list[str]) -> dict:
    """Run Impact Gate runner for the given FR/bug IDs. Returns the runner JSON result."""
    if not fr_ids and not bug_ids:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "PASS",
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0, "missing": 0},
            "fr_results": {},
            "bug_results": {},
            "note": "No FR or bug IDs to verify.",
        }

    args = [sys.executable, str(IMPACT_GATE_RUNNER)]
    if fr_ids:
        args.extend(["--frs", ",".join(fr_ids)])
    if bug_ids:
        args.extend(["--bugs", ",".join(bug_ids)])

    try:
        proc = subprocess.run(
            args,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "PYTHONPATH": f"{REPO_ROOT / 'src'}"},
        )
        return json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "error": "Test execution timed out after 300s"}
    except json.JSONDecodeError as exc:
        return {"status": "ERROR", "error": f"Failed to parse runner output: {exc}", "raw": proc.stdout[:2000] if proc else ""}


def run_pytest_paths(test_paths: list[str]) -> dict:
    """Run pytest on specific test file/directory paths. Returns structured result."""
    if not test_paths:
        return {"status": "PASS", "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0}}

    existing = [p for p in test_paths if (REPO_ROOT / p).exists()]
    if not existing:
        return {"status": "PASS", "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
                "note": "No test paths found on disk."}

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=short", "--no-header", "-p", "no:cacheprovider", "--no-cov"] + existing,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "PYTHONPATH": f"{REPO_ROOT / 'src'}", "QT_QPA_PLATFORM": "offscreen"},
        )
        lines = proc.stdout.strip().splitlines()
        last_line = lines[-1] if lines else ""
        passed = failed = errors = 0
        import re
        m = re.search(r'(\d+)\s+passed', last_line)
        if m: passed = int(m.group(1))
        m = re.search(r'(\d+)\s+failed', last_line)
        if m: failed = int(m.group(1))
        m = re.search(r'(\d+)\s+errors?', last_line)
        if m: errors = int(m.group(1))

        status = "PASS" if (failed + errors) == 0 else "FAIL"
        return {
            "status": status,
            "summary": {"total": passed + failed + errors, "passed": passed, "failed": failed, "errors": errors},
            "test_paths": existing,
        }
    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "error": "Pytest timed out after 300s"}
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}


def render_markdown_report(results: dict) -> str:
    """Render a Markdown report of lock module verification results."""
    timestamp = results.get("timestamp", datetime.now(timezone.utc).isoformat())
    affected = results.get("affected_modules", [])
    test_map = results.get("test_mapping", {})
    fr_results = results.get("fr_bug_results", {})
    path_results = results.get("pytest_path_results", {})
    overall = results.get("overall_status", "UNKNOWN")

    lines = [
        "## Lock Module Verification Report",
        "",
        f"**Timestamp:** {timestamp}",
        f"**Overall Status:** `{overall}`",
        "",
    ]

    if affected:
        lines.append("### Changed Locked Modules")
        lines.append("")
        lines.append("| File | Locked Path | Reason |")
        lines.append("|------|-------------|--------|")
        for a in affected:
            lines.append(f"| `{a['file_path']}` | `{a['locked_path']}` | {a.get('reason', 'N/A')} |")
        lines.append("")

    if test_map:
        lines.append("### Verification Test Mapping")
        lines.append("")
        for lp, tests in test_map.items():
            frs = tests.get("fr_ids", [])
            bugs = tests.get("bug_ids", [])
            paths = tests.get("test_paths", [])
            parts = []
            if frs: parts.append(f"FRs: {', '.join(frs)}")
            if bugs: parts.append(f"Bugs: {', '.join(bugs)}")
            if paths: parts.append(f"Paths: {', '.join(paths)}")
            lines.append(f"- **`{lp}`** — {'; '.join(parts) if parts else 'No tests mapped'}")
        lines.append("")

    if fr_results:
        status = fr_results.get("status", "UNKNOWN")
        summary = fr_results.get("summary", {})
        lines.append(f"### FR/Bug Impact Gate — `{status}`")
        lines.append(f"Passed: {summary.get('passed', 0)} | Failed: {summary.get('failed', 0)} | Errors: {summary.get('errors', 0)}")
        for tid, tr in fr_results.get("fr_results", {}).items():
            lines.append(f"- **{tid}**: `{tr.get('status', '?')}` ({tr.get('test_file', '?')})")
        for tid, tr in fr_results.get("bug_results", {}).items():
            lines.append(f"- **{tid}**: `{tr.get('status', '?')}` ({tr.get('test_file', '?')})")
        lines.append("")

    if path_results:
        for lp, pr in path_results.items():
            status = pr.get("status", "UNKNOWN")
            summary = pr.get("summary", {})
            lines.append(f"### Pytest Paths for `{lp}` — `{status}`")
            lines.append(f"Passed: {summary.get('passed', 0)} | Failed: {summary.get('failed', 0)} | Errors: {summary.get('errors', 0)}")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lock Module Verification — requirement verification gate for locked module changes.",
    )
    parser.add_argument("--local", action="store_true", help="Diff HEAD~1 (local mode)")
    parser.add_argument("--diff-file", metavar="PATH", help="Read a diff file (test fixture)")
    parser.add_argument("--changed-files", metavar="F1,F2,...", help="Explicit comma-separated file list")
    parser.add_argument("--json", action="store_true", default=True, help="JSON output (default)")
    parser.add_argument("--markdown", action="store_true", help="Markdown report output")
    parser.add_argument("--touch-index", action="store_true", help="Use Touch Index DB for test discovery (fallback)")
    parser.add_argument("--json-summary", action="store_true", help="Alias for --json (compat with lock_gate.py)")
    args = parser.parse_args()

    # Resolve changed files
    if args.changed_files:
        changed = [f.strip() for f in args.changed_files.split(",") if f.strip()]
    elif args.diff_file:
        changed = get_changed_files_from_diff(args.diff_file)
    elif args.local:
        changed = get_changed_files_local()
    else:
        changed = get_changed_files_ci()

    if not changed:
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "PASS",
            "affected_modules": [],
            "test_mapping": {},
            "fr_bug_results": {},
            "pytest_path_results": {},
            "note": "No changed files detected.",
        }
        if args.markdown:
            print(render_markdown_report(result))
        else:
            json.dump(result, sys.stdout, indent=2)
            sys.stdout.write("\n")
        return 0

    # Load registries
    if not LOCK_REGISTRY_PATH.exists():
        print("ERROR: .module_lock_registry.json not found", file=sys.stderr)
        return 2

    lock_registry = load_json(LOCK_REGISTRY_PATH)
    affected = find_affected_locked_modules(changed, lock_registry)

    if not affected:
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "PASS",
            "affected_modules": [],
            "test_mapping": {},
            "fr_bug_results": {},
            "pytest_path_results": {},
            "note": "No locked modules affected by these changes.",
        }
        if args.markdown:
            print(render_markdown_report(result))
        else:
            json.dump(result, sys.stdout, indent=2)
            sys.stdout.write("\n")
        return 0

    locked_paths = [a["locked_path"] for a in affected]

    # Load verification registries — prefer canonical requirements_registry.json
    # (from Architect BTCAAAAA-25639), fall back to lock_module_verification_registry.json
    test_map: dict[str, dict] = {}
    if REQUIREMENTS_REGISTRY_PATH.exists():
        req_registry = load_json(REQUIREMENTS_REGISTRY_PATH)
        test_map = find_verification_tests_from_requirements_registry(
            locked_paths, req_registry
        )
    elif REGISTRY_PATH.exists():
        verification_registry = load_json(REGISTRY_PATH)
        test_map = find_verification_tests(locked_paths, verification_registry)
    else:
        # No registry available — map locked paths with empty test sets
        for lp in locked_paths:
            test_map[lp] = {"fr_ids": [], "bug_ids": [], "test_paths": []}

    # Collect all FR/bug IDs across all affected locked modules
    all_fr_ids: list[str] = []
    all_bug_ids: list[str] = []
    for lp in locked_paths:
        tm = test_map.get(lp, {"fr_ids": [], "bug_ids": [], "test_paths": []})
        all_fr_ids.extend(tm["fr_ids"])
        all_bug_ids.extend(tm["bug_ids"])

    # Touch Index fallback: for modules with no mapped tests, try TI discovery
    if args.touch_index:
        for lp in locked_paths:
            tm = test_map.get(lp, {"fr_ids": [], "bug_ids": [], "test_paths": []})
            if not tm["fr_ids"] and not tm["bug_ids"]:
                ti_frs = query_touch_index_fr(lp)
                ti_bugs = query_touch_index_bugs(lp)
                if ti_frs or ti_bugs:
                    tm["fr_ids"] = ti_frs
                    tm["bug_ids"] = ti_bugs
                    tm["_source"] = "touch_index"
                    test_map[lp] = tm
                    all_fr_ids.extend(ti_frs)
                    all_bug_ids.extend(ti_bugs)

    # Deduplicate
    all_fr_ids = list(dict.fromkeys(all_fr_ids))
    all_bug_ids = list(dict.fromkeys(all_bug_ids))

    # Run FR/bug tests via Impact Gate runner
    fr_bug_result = run_tests_for_ids(all_fr_ids, all_bug_ids)

    # Run pytest paths (direct test file/directory execution)
    pytest_path_results: dict[str, dict] = {}
    for lp in locked_paths:
        tm = test_map.get(lp, {"fr_ids": [], "bug_ids": [], "test_paths": []})
        if tm["test_paths"]:
            pr = run_pytest_paths(tm["test_paths"])
            pytest_path_results[lp] = pr

    # Determine overall status
    fr_status = fr_bug_result.get("status", "PASS")
    any_path_fail = any(
        pr.get("status") in ("FAIL", "ERROR")
        for pr in pytest_path_results.values()
    )

    if fr_status in ("FAIL", "ERROR") or any_path_fail:
        overall = "FAIL"
    else:
        overall = "PASS"

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "affected_modules": affected,
        "test_mapping": test_map,
        "fr_bug_results": fr_bug_result,
        "pytest_path_results": pytest_path_results,
        "changed_files": changed,
    }

    if args.markdown:
        print(render_markdown_report(result))
    else:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
