#!/usr/bin/env python3
"""
Lock Gate — CI gate that blocks PRs touching locked modules without an exception.

Usage:
    python scripts/lock_gate.py                     # CI mode (uses GITHUB_BASE_REF)
    python scripts/lock_gate.py --local             # local mode (diffs HEAD~1)
    python scripts/lock_gate.py --diff-file <path>  # read a diff file (test fixture)

Exit codes:
    0 — no locked paths touched (or only exceptions)
    1 — locked paths touched without exception (gate blocks)
"""

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / ".module_lock_registry.json"
DEP_GRAPH_PATH = REPO_ROOT / "dep_graph.json"
EXCEPTIONS_PATH = REPO_ROOT / "lock_gate_exceptions.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


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

    excepted_paths = {e["path"] for e in exceptions}
    blocked = [(f, lp, r) for f, lp, r in unique_hits if lp not in excepted_paths]

    if not blocked:
        if unique_hits:
            print("lock-gate: all touched locked paths have exceptions. Gate passed.")
        else:
            print("lock-gate: no locked paths touched. Gate passed.")
        sys.exit(0)

    print("=" * 72)
    print("LOCK GATE BLOCKED - locked modules touched without exception")
    print("=" * 72)
    for file_path, locked_path, reason in blocked:
        print(f"\n  File:    {file_path}")
        print(f"  Locked:  {locked_path}")
        print(f"  Reason:  {reason}")
    print()
    print("To proceed:")
    print("  1. File an exception request using the issue template:")
    print("     .github/ISSUE_TEMPLATE/qa-locked-module-exception.md")
    print("  2. Get CTO approval and document the approval_id in")
    print("     lock_gate_exceptions.json")
    print("  3. Re-run the CI pipeline")
    print("=" * 72)
    sys.exit(1)


if __name__ == "__main__":
    main()
