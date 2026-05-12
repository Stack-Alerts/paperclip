#!/usr/bin/env python3
"""
Lock Gate — CI gate that blocks PRs touching locked modules without an exception.

Usage:
    python scripts/lock_gate.py                     # CI mode (uses GITHUB_BASE_REF)
    python scripts/lock_gate.py --local             # local mode (diffs HEAD~1)
    python scripts/lock_gate.py --diff-file <path>  # read a diff file (test fixture)
    python scripts/lock_gate.py --validate-exceptions  # validate exceptions file only

Exit codes:
    0 — no locked paths touched (or only exceptions)
    1 — locked paths touched without exception (gate blocks)
    2 — schema validation error in exceptions file
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / ".module_lock_registry.json"
DEP_GRAPH_PATH = REPO_ROOT / "dep_graph.json"
EXCEPTIONS_PATH = REPO_ROOT / "lock_gate_exceptions.json"

VALID_APPROVED_BY = {"board", "ceo-emergency"}
EMERGENCY_MAX_HOURS = 4


def load_json(path):
    with open(path) as f:
        return json.load(f)


def parse_iso(dt_str):
    """Parse an ISO 8601 datetime string. Returns datetime or None on failure."""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def validate_exception_entry(entry, now=None):
    """Validate a single exception entry against schema rules.

    Returns list of error strings (empty = valid).
    """
    errors = []
    now = now or datetime.now(timezone.utc)

    if not isinstance(entry, dict):
        return ["entry must be a dict"]

    module = entry.get("module")
    if not module or not isinstance(module, str):
        errors.append("'module' must be a non-empty string")

    scope = entry.get("scope_description")
    if not scope or not isinstance(scope, str):
        errors.append("'scope_description' must be a non-empty string")

    approved_by = entry.get("approved_by")
    if approved_by not in VALID_APPROVED_BY:
        errors.append(
            f"'approved_by' must be one of {sorted(VALID_APPROVED_BY)}, "
            f"got '{approved_by}'"
        )

    approval_id = entry.get("approval_id")
    if not approval_id or not isinstance(approval_id, str):
        errors.append("'approval_id' must be a non-empty string")

    expires_iso = entry.get("expires_iso")
    if expires_iso is not None:
        if not isinstance(expires_iso, str):
            errors.append("'expires_iso' must be a string or null")
        else:
            parsed = parse_iso(expires_iso)
            if parsed is None:
                errors.append(f"'expires_iso' is not valid ISO 8601: '{expires_iso}'")
            elif approved_by in VALID_APPROVED_BY:
                delta = parsed - now
                if delta.total_seconds() > EMERGENCY_MAX_HOURS * 3600 + 60:
                    errors.append(
                        f"'expires_iso' ({expires_iso}) is > {EMERGENCY_MAX_HOURS}h "
                        f"from now — emergency exceptions cannot exceed {EMERGENCY_MAX_HOURS}h"
                    )

    return errors


def validate_exceptions_file(data, now=None):
    """Validate the entire exceptions file. Returns list of error strings."""
    errors = []
    now = now or datetime.now(timezone.utc)

    if not isinstance(data, dict):
        return ["exceptions file must be a JSON object"]

    version = data.get("version")
    if version != 2:
        errors.append(f"'version' must be 2, got {version}")

    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        return ["'exceptions' must be an array"]

    for i, entry in enumerate(exceptions):
        entry_errors = validate_exception_entry(entry, now)
        for err in entry_errors:
            errors.append(f"exceptions[{i}]: {err}")

    return errors


def get_active_exceptions(exceptions, now=None):
    """Filter exceptions to only active (non-expired) entries.

    Uses new schema (module field) or falls back to old schema (path field).
    """
    now = now or datetime.now(timezone.utc)
    active = []
    for entry in exceptions:
        expires_iso = entry.get("expires_iso")
        if expires_iso is not None:
            parsed = parse_iso(expires_iso)
            if parsed is None or parsed <= now:
                continue
        active.append(entry)
    return active


def get_excepted_modules(active_exceptions):
    """Build set of excepted module paths from active exceptions.

    Supports new schema (module field) and old schema (path field) for
    backward compatibility during migration.
    """
    modules = set()
    for entry in active_exceptions:
        if "module" in entry:
            modules.add(entry["module"])
        elif "path" in entry:
            modules.add(entry["path"])
    return modules


def get_changed_files_ci():
    """Get changed files in CI by diffing against the merge-base of base_ref."""
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    try:
        subprocess.run(
            ["git", "fetch", "origin", base_ref],
            capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        pass
    result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        capture_output=True, text=True, check=True
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def get_changed_files_local():
    """Get changed files in local mode (diffs HEAD~1)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1"],
        capture_output=True, text=True, check=True
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def get_changed_files_from_diff(diff_path):
    """Parse changed files from a diff file (test fixture support)."""
    changed = set()
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


def matches_locked_path(file_path, locked_entries):
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


def get_downstream_locked(file_path, dep_graph, locked_entries):
    """Check if file_path is a dependency of any locked module (reverse dep check)."""
    reverse = dep_graph.get("reverse", {})
    locked_hits = []
    if file_path in reverse:
        for dependent in reverse[file_path]:
            entry = matches_locked_path(dependent, locked_entries)
            if entry and entry not in locked_hits:
                locked_hits.append(entry)
    return locked_hits


def load_exceptions():
    """Load the exception allowlist."""
    if not EXCEPTIONS_PATH.exists():
        return []
    data = load_json(EXCEPTIONS_PATH)
    return data.get("exceptions", [])


def main():
    if "--validate-exceptions" in sys.argv:
        data = load_json(EXCEPTIONS_PATH)
        errors = validate_exceptions_file(data)
        if errors:
            print("LOCK GATE EXCEPTIONS FILE VALIDATION FAILED:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(2)
        print("lock-gate: exceptions file is valid.")
        sys.exit(0)

    if "--local" in sys.argv:
        changed = get_changed_files_local()
    elif "--diff-file" in sys.argv:
        idx = sys.argv.index("--diff-file")
        diff_path = sys.argv[idx + 1]
        changed = get_changed_files_from_diff(diff_path)
    else:
        changed = get_changed_files_ci()

    if not changed:
        print("lock-gate: no changed files detected. Gate passed.")
        sys.exit(0)

    registry = load_json(REGISTRY_PATH)
    locked_entries = registry["entries"]

    dep_graph = load_json(DEP_GRAPH_PATH) if DEP_GRAPH_PATH.exists() else {}
    exceptions = load_exceptions()

    # Validate exceptions file schema (soft warn but don't block on schema issues)
    exceptions_data = load_json(EXCEPTIONS_PATH) if EXCEPTIONS_PATH.exists() else {"exceptions": []}
    schema_errors = validate_exceptions_file(exceptions_data)
    if schema_errors:
        for err in schema_errors:
            print(f"lock-gate: WARNING: {err}", file=sys.stderr)

    active_exceptions = get_active_exceptions(exceptions)
    excepted_modules = get_excepted_modules(active_exceptions)

    hits = []

    for f in changed:
        entry = matches_locked_path(f, locked_entries)
        if entry:
            hits.append((f, entry["path"], entry["reason"]))

        if dep_graph:
            downstream = get_downstream_locked(f, dep_graph, locked_entries)
            for entry in downstream:
                hits.append((f, entry["path"], entry["reason"]))

    seen = set()
    unique_hits = []
    for file_path, locked_path, reason in hits:
        key = (file_path, locked_path)
        if key not in seen:
            seen.add(key)
            unique_hits.append((file_path, locked_path, reason))

    blocked = [(f, lp, r) for f, lp, r in unique_hits if lp not in excepted_modules]

    if not blocked:
        if "--json-summary" in sys.argv:
            import json as _json
            _summary = {
                "gate": "passed",
                "blocked": [],
                "raw_output": (
                    "lock-gate: all touched locked paths have exceptions. Gate passed."
                    if unique_hits
                    else "lock-gate: no locked paths touched. Gate passed."
                ),
            }
            _json.dump(_summary, sys.stdout)
            sys.stdout.write("\n")
        else:
            if unique_hits:
                print("lock-gate: all touched locked paths have exceptions. Gate passed.")
            else:
                print("lock-gate: no locked paths touched. Gate passed.")
        sys.exit(0)

    if "--json-summary" in sys.argv:
        import json as _json
        _summary = {
            "gate": "blocked",
            "pr_number": os.environ.get("GITHUB_PR_NUMBER", os.environ.get("GH_PR_NUMBER", "")),
            "commit_sha": os.environ.get("GITHUB_SHA", ""),
            "pr_url": os.environ.get("GITHUB_PR_URL", ""),
            "blocked": [
                {"file_path": f, "locked_path": lp, "reason": r}
                for f, lp, r in blocked
            ],
            "raw_output": "LOCK GATE BLOCKED - locked modules touched without exception",
        }
        _json.dump(_summary, sys.stdout)
        sys.stdout.write("\n")
    else:
        print("=" * 72)
        print("LOCK GATE BLOCKED - locked modules touched without exception")
        print("=" * 72)
        for file_path, locked_path, reason in blocked:
            print(f"\n  File:    {file_path}")
            print(f"  Locked:  {locked_path}")
            print(f"  Reason:  {reason}")
        print()
        print("To proceed:")
        print("  1. Determine the correct unlock path:")
        print("     Path A (planned, board-approved)  — file issue, get board approval")
        print("     Path B.1 (CEO emergency)          — CEO approval, max 4h window")
        print("     Path B.2 (board emergency)        — board approval, max 4h window")
        print("  2. Add an entry to lock_gate_exceptions.json")
        print("  3. Re-run the CI pipeline")
        print("  See docs/runbook-module-lock.md for full procedure.")
        print("=" * 72)
    sys.exit(1)


if __name__ == "__main__":
    main()
