#!/usr/bin/env python3
"""Pre-merge gate: fail when a PR deletes a public Python def/class that
still has live non-test callers.

Background: BTCAAAAA-37737. PR #118 deleted ``DatabaseManager.scoped_managers()``
while 9 live callers remained in ``src/api/app.py``. CI passed because no test
imported the symbol directly, and 7 Strategy Builder endpoints went 500 in
production. This script is the MVP pre-merge gate. Renames, JS/TS, and
signature changes are out of scope.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True, **kwargs)


def changed_python_files(base_ref: str) -> list[tuple[str, str]]:
    """Return [(status, path)] for python files changed vs base_ref.

    Status is one of A/M/D/R... R (rename) is treated as out-of-scope per
    the issue.
    """
    out = run(["git", "diff", "--name-status", f"{base_ref}...HEAD", "--", "*.py"]).stdout
    files: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][0]
        if status == "R":
            continue
        path = parts[-1]
        files.append((status, path))
    return files


def collect_public_defs(source: str) -> set[str]:
    """Return public top-level and class-method def/class names.

    Public = not starting with underscore. Collected:
      - top-level def / async def / class
      - methods/classes nested directly under a public class
    Nested defs inside functions are skipped.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    names: set[str] = set()

    def add(name: str) -> None:
        if name and not name.startswith("_"):
            names.add(name)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            add(node.name)
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        add(sub.name)
    return names


def file_at_ref(ref: str, path: str) -> str | None:
    proc = run(["git", "show", f"{ref}:{path}"], check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout


def file_at_head(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def removed_defs(base_ref: str) -> dict[str, set[str]]:
    """Return {file_path: {removed_name, ...}}.

    Deleted file → every public def in the old version is removed.
    Modified file → removed = old_defs - new_defs.
    """
    out: dict[str, set[str]] = {}
    for status, path in changed_python_files(base_ref):
        if path.startswith("tests/") or "/tests/" in path:
            continue
        old_src = file_at_ref(base_ref, path)
        if old_src is None:
            continue  # newly added — no removals possible
        old_defs = collect_public_defs(old_src)
        if status == "D":
            removed = old_defs
        else:
            new_src = file_at_head(path)
            new_defs = collect_public_defs(new_src or "")
            removed = old_defs - new_defs
        if removed:
            out[path] = removed
    return out


# Generic entrypoint names are usually fresh-defined per module rather than
# imported across modules. Skipping them keeps signal:noise reasonable.
GENERIC_ENTRY_NAMES = {"main", "run", "setup", "teardown"}


def find_callers(name: str, deleted_path: str) -> list[tuple[str, int, str]]:
    """ripgrep for ``name(`` in the post-diff tree, excluding the deleted
    file itself and tests/."""
    pattern = rf"\b{re.escape(name)}\s*\("
    cmd = [
        "rg",
        "--no-heading",
        "--line-number",
        "--color=never",
        "-tpy",
        "--glob",
        "!tests/**",
        "--glob",
        "!**/tests/**",
        "--glob",
        f"!{deleted_path}",
        pattern,
        ".",
    ]
    proc = run(cmd, check=False)
    if proc.returncode not in (0, 1):
        print(f"::warning::ripgrep failed for {name}: {proc.stderr}", file=sys.stderr)
        return []
    hits: list[tuple[str, int, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path, lineno, content = parts
        if path.startswith("./"):
            path = path[2:]
        if path == deleted_path:
            continue
        if path.startswith("tests/") or "/tests/" in path:
            continue
        stripped = content.lstrip()
        if re.match(rf"^(async\s+)?def\s+{re.escape(name)}\s*\(", stripped):
            continue
        if re.match(rf"^class\s+{re.escape(name)}\s*[\(:]", stripped):
            continue
        try:
            ln = int(lineno)
        except ValueError:
            continue
        hits.append((path, ln, content.rstrip()))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-ref", default="origin/main",
                    help="Base ref to diff against (default: origin/main)")
    ap.add_argument("--json", action="store_true", help="Emit JSON to stdout instead of text")
    ap.add_argument("--allow", action="append", default=[],
                    help="Name to ignore (repeatable). For intentional removals.")
    args = ap.parse_args()

    allow = set(args.allow) | GENERIC_ENTRY_NAMES

    removed = removed_defs(args.base_ref)
    violations: list[dict] = []
    checked: list[dict] = []

    for path, names in sorted(removed.items()):
        for name in sorted(names):
            if name in allow:
                continue
            callers = find_callers(name, path)
            entry = {
                "name": name,
                "deleted_from": path,
                "callers": [
                    {"file": p, "line": ln, "text": txt} for p, ln, txt in callers
                ],
            }
            checked.append(entry)
            if callers:
                violations.append(entry)

    if args.json:
        json.dump({"violations": violations, "checked": checked}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not checked:
            print("No public defs/classes removed by this PR — nothing to check.")
        elif not violations:
            print("Removed public defs/classes — no live non-test callers:")
            for e in checked:
                print(f"  - {e['name']} (from {e['deleted_from']})")
        else:
            print("Deletion-touches-callers gate FAILED.\n")
            print("The following public defs/classes were removed but still have callers:\n")
            for v in violations:
                print(f"  ✗ {v['name']}  (deleted from {v['deleted_from']})")
                for c in v["callers"]:
                    print(f"      {c['file']}:{c['line']}: {c['text']}")
                print()
            print(
                "Either restore the symbol, update the callers, or — if the removal\n"
                "is intentional and callers are also being removed in the same PR —\n"
                "rerun with --allow <name> after confirming."
            )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
