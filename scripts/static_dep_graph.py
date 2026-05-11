"""
Static file-level dependency graph extractor for the BTC Trade Engine codebase.

Parses Python imports using AST to build a directed graph: file A -> file B
means file A imports from file B. Exposes forward and reverse queries.

Output: JSON file consumable by the Touch Index (Phase 1).
"""

from __future__ import annotations

import ast
import json
import os
import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import Optional


ROOT = Path(__file__).parent.parent
SRC_ROOT = ROOT / "src"
OUTPUT_PATH = ROOT / "dep_graph.json"


def _resolve_relative_import(
    importing_file: Path, module: Optional[str], level: int, src_root: Path
) -> Optional[str]:
    """Convert a relative import to an absolute module path."""
    parts = importing_file.parts
    src_idx = None
    for i, part in enumerate(parts):
        if (Path(*parts[: i + 1])) == src_root:
            src_idx = i
            break
    if src_idx is None:
        return None

    relative_parts = list(parts[src_idx + 1 : -1])  # package dirs above file
    # go up `level-1` directories
    for _ in range(level - 1):
        if relative_parts:
            relative_parts.pop()

    if module:
        full = ".".join(relative_parts + module.split("."))
    else:
        full = ".".join(relative_parts)
    return full or None


def _module_to_file(module: str, src_root: Path) -> Optional[Path]:
    """Best-effort: map a dotted module name to a .py file.

    Tries two roots:
    1. src_root — for packages like 'optimizer_v3.core.logger'
    2. src_root.parent (project root) — for 'src.optimizer_v3.core.logger'
    """
    parts = module.split(".")
    for root in (src_root, src_root.parent):
        candidate = root.joinpath(*parts).with_suffix(".py")
        if candidate.exists():
            return candidate
        pkg = root.joinpath(*parts, "__init__.py")
        if pkg.exists():
            return pkg
    return None


def _collect_py_files(root: Path) -> list[Path]:
    """Collect all .py files under root, excluding venv."""
    files = []
    for p in root.rglob("*.py"):
        parts = p.parts
        if any(skip in parts for skip in ("venv", ".venv", "__pycache__", "archived")):
            continue
        files.append(p)
    return sorted(files)


def build_graph(project_root: Path) -> dict:
    """
    Build the forward and reverse file-level import dependency graph.

    Returns a dict with:
      - forward: {file_rel -> [imported_file_rel, ...]}
      - reverse: {file_rel -> [importing_file_rel, ...]}
      - parse_errors: [file_rel, ...]
      - stats: {total_files, parsed_files, error_files, edge_count}
    """
    src_root = project_root / "src"
    if not src_root.exists():
        src_root = project_root

    py_files = _collect_py_files(project_root)
    all_files = {p: str(p.relative_to(project_root)) for p in py_files}

    forward: dict[str, list[str]] = defaultdict(list)
    reverse: dict[str, list[str]] = defaultdict(list)
    parse_errors: list[str] = []

    for fpath, frel in all_files.items():
        try:
            source = fpath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(fpath))
        except SyntaxError:
            parse_errors.append(frel)
            continue
        except Exception:
            parse_errors.append(frel)
            continue

        for node in ast.walk(tree):
            target_mod: Optional[str] = None

            if isinstance(node, ast.Import):
                for alias in node.names:
                    target_mod = alias.name
                    target_file = _module_to_file(target_mod, src_root)
                    if target_file and target_file in all_files:
                        trel = all_files[target_file]
                        if trel not in forward[frel]:
                            forward[frel].append(trel)
                        if frel not in reverse[trel]:
                            reverse[trel].append(frel)

            elif isinstance(node, ast.ImportFrom):
                level = node.level or 0
                if level > 0:
                    target_mod = _resolve_relative_import(
                        fpath, node.module, level, src_root
                    )
                else:
                    target_mod = node.module

                if target_mod:
                    target_file = _module_to_file(target_mod, src_root)
                    if target_file and target_file in all_files:
                        trel = all_files[target_file]
                        if trel not in forward[frel]:
                            forward[frel].append(trel)
                        if frel not in reverse[trel]:
                            reverse[trel].append(frel)

    total = len(all_files)
    parsed = total - len(parse_errors)
    edge_count = sum(len(v) for v in forward.values())

    return {
        "forward": dict(forward),
        "reverse": dict(reverse),
        "all_files": list(all_files.values()),
        "parse_errors": parse_errors,
        "stats": {
            "total_files": total,
            "parsed_files": parsed,
            "error_files": len(parse_errors),
            "parse_rate_pct": round(parsed / total * 100, 2) if total else 0,
            "edge_count": edge_count,
        },
    }


def reverse_query(graph: dict, file_rel: str, transitive: bool = False) -> list[str]:
    """
    Return the list of files that import `file_rel`.

    Args:
        graph: The graph dict returned by build_graph().
        file_rel: Relative path of the target file.
        transitive: If True, return all transitive importers (BFS).
    """
    rev = graph["reverse"]
    if not transitive:
        return rev.get(file_rel, [])

    visited: set[str] = set()
    queue = list(rev.get(file_rel, []))
    result: list[str] = []
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        result.append(node)
        queue.extend(rev.get(node, []))
    return result


def top_high_fan_in(graph: dict, n: int = 10) -> list[tuple[str, int]]:
    """Return the top-n files by number of reverse-importers (fan-in)."""
    rev = graph["reverse"]
    ranked = sorted(rev.items(), key=lambda kv: len(kv[1]), reverse=True)
    return [(f, len(importers)) for f, importers in ranked[:n]]


if __name__ == "__main__":
    print(f"Building dependency graph for {ROOT} ...")
    t0 = time.perf_counter()
    graph = build_graph(ROOT)
    elapsed = time.perf_counter() - t0

    stats = graph["stats"]
    print(f"\n=== Build Stats ===")
    print(f"  Total .py files : {stats['total_files']}")
    print(f"  Parsed          : {stats['parsed_files']}")
    print(f"  Parse errors    : {stats['error_files']}")
    print(f"  Parse rate      : {stats['parse_rate_pct']}%")
    print(f"  Edges (imports) : {stats['edge_count']}")
    print(f"  Build time      : {elapsed:.3f}s")

    if graph["parse_errors"]:
        print(f"\nUnparseable files:")
        for f in graph["parse_errors"]:
            print(f"  {f}")

    print(f"\n=== Top-10 High-Fan-In Files ===")
    for f, count in top_high_fan_in(graph):
        print(f"  {count:4d}  {f}")

    OUTPUT_PATH.write_text(json.dumps(graph, indent=2))
    print(f"\nGraph written to {OUTPUT_PATH}")
