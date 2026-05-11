#!/usr/bin/env python3
"""
Extract Python import edges from the BTC-Trade-Engine-PaperClip repo
and write them to Postgres.

Usage:
    python scripts/dep_extractor.py --repo-root /path/to/repo --db-url postgresql://...
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras

MAX_DEPTH = 20
SKIP_DIRS = frozenset({"venv", ".venv", "__pycache__"})


def _collect_py_files(root: Path) -> list[Path]:
    files = []
    for p in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        files.append(p)
    return sorted(files)


def _resolve_relative_import(
    importing_file: Path,
    module: Optional[str],
    level: int,
    src_root: Path,
) -> Optional[str]:
    """Resolve a relative import to a dotted module name relative to src_root."""
    parts = importing_file.parts
    src_idx = None
    for i in range(len(parts)):
        if Path(*parts[: i + 1]) == src_root:
            src_idx = i
            break
    if src_idx is None:
        return None

    relative_parts = list(parts[src_idx + 1 : -1])  # package dirs above the file
    for _ in range(level - 1):
        if relative_parts:
            relative_parts.pop()

    full = ".".join(relative_parts + module.split(".")) if module else ".".join(relative_parts)
    return full or None


def _module_to_file(module: str, src_root: Path) -> Optional[Path]:
    """Map a dotted module name to a .py file under src_root or its parent."""
    parts = module.split(".")
    for root in (src_root, src_root.parent):
        candidate = root.joinpath(*parts).with_suffix(".py")
        if candidate.exists():
            return candidate
        pkg = root.joinpath(*parts, "__init__.py")
        if pkg.exists():
            return pkg
    return None


def _record(
    src: str,
    dep: str,
    is_internal: bool,
    edges: list[tuple[str, str, bool]],
    seen: set[tuple[str, str]],
) -> None:
    key = (src, dep)
    if key not in seen:
        seen.add(key)
        edges.append((src, dep, is_internal))


def _add_absolute_edge(
    frel: str,
    module: str,
    src_root: Path,
    file_rel: dict[Path, str],
    edges: list[tuple[str, str, bool]],
    seen: set[tuple[str, str]],
) -> None:
    # Try to resolve to an in-repo file; handles bare (optimizer_v3.foo)
    # and src-prefixed (src.optimizer_v3.foo) import styles.
    target = _module_to_file(module, src_root)
    if target and target in file_rel:
        _record(frel, file_rel[target], True, edges, seen)
    else:
        _record(frel, module, False, edges, seen)


def _add_relative_edge(
    fpath: Path,
    frel: str,
    module: Optional[str],
    level: int,
    src_root: Path,
    file_rel: dict[Path, str],
    edges: list[tuple[str, str, bool]],
    seen: set[tuple[str, str]],
) -> None:
    resolved = _resolve_relative_import(fpath, module, level, src_root)
    if resolved is None:
        return
    target = _module_to_file(resolved, src_root)
    if target and target in file_rel:
        _record(frel, file_rel[target], True, edges, seen)


def build_edges(
    repo_root: Path,
) -> tuple[list[tuple[str, str, bool]], list[tuple[str, str]]]:
    """
    Walk the repo and extract all import edges.

    Returns:
        edges: list of (source_file, dep_file, is_internal) — repo-relative POSIX paths
        parse_errors: list of (file_rel, error_message)
    """
    src_root = repo_root / "src"
    if not src_root.exists():
        src_root = repo_root

    py_files = _collect_py_files(repo_root)
    file_rel: dict[Path, str] = {
        p: p.relative_to(repo_root).as_posix() for p in py_files
    }

    edges: list[tuple[str, str, bool]] = []
    parse_errors: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for fpath, frel in file_rel.items():
        try:
            source = fpath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(fpath))
        except SyntaxError as exc:
            parse_errors.append((frel, str(exc)))
            continue
        except Exception as exc:
            parse_errors.append((frel, str(exc)))
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _add_absolute_edge(frel, alias.name, src_root, file_rel, edges, seen)
            elif isinstance(node, ast.ImportFrom):
                level = node.level or 0
                if level > 0:
                    _add_relative_edge(fpath, frel, node.module, level, src_root, file_rel, edges, seen)
                elif node.module:
                    _add_absolute_edge(frel, node.module, src_root, file_rel, edges, seen)

    return edges, parse_errors


def build_transitive_closure(
    edges: list[tuple[str, str, bool]],
) -> list[tuple[str, str, int]]:
    """
    BFS forward transitive closure over internal edges only.

    For every file A, find every file B reachable from A via internal import
    hops (up to MAX_DEPTH), recording the minimum hop count.

    Returns list of (source_file, dep_file, min_depth).
    """
    forward: dict[str, list[str]] = {}
    for src, dep, is_internal in edges:
        if is_internal:
            forward.setdefault(src, []).append(dep)

    all_files: set[str] = set(forward.keys())
    for deps in forward.values():
        all_files.update(deps)

    result: list[tuple[str, str, int]] = []
    for start in sorted(all_files):
        visited: dict[str, int] = {}
        queue: deque[tuple[str, int]] = deque()
        for neighbor in forward.get(start, []):
            if neighbor != start and neighbor not in visited:
                visited[neighbor] = 1
                queue.append((neighbor, 1))
        while queue:
            node, depth = queue.popleft()
            if depth >= MAX_DEPTH:
                continue
            for neighbor in forward.get(node, []):
                if neighbor != start and neighbor not in visited:
                    visited[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))
        for dep_file, depth in visited.items():
            result.append((start, dep_file, depth))

    return result


def _ensure_parse_errors_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dep_parse_errors (
                id         SERIAL      PRIMARY KEY,
                file_path  TEXT        NOT NULL UNIQUE,
                error_msg  TEXT        NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)


def write_to_db(
    db_url: str,
    edges: list[tuple[str, str, bool]],
    transitive: list[tuple[str, str, int]],
    parse_errors: list[tuple[str, str]],
) -> None:
    now = datetime.now(timezone.utc)
    conn = psycopg2.connect(db_url)
    try:
        _ensure_parse_errors_table(conn)
        conn.commit()

        with conn:  # single transaction: DELETE + reinsert all three tables
            with conn.cursor() as cur:
                cur.execute("DELETE FROM touch_index_file_deps")
                if edges:
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO touch_index_file_deps
                            (source_file, dep_file, is_internal, updated_at)
                        VALUES %s
                        """,
                        [(s, d, i, now) for s, d, i in edges],
                    )

                cur.execute("DELETE FROM touch_index_file_deps_transitive")
                if transitive:
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO touch_index_file_deps_transitive
                            (source_file, dep_file, min_depth, updated_at)
                        VALUES %s
                        """,
                        [(s, d, depth, now) for s, d, depth in transitive],
                    )

                cur.execute("DELETE FROM dep_parse_errors")
                if parse_errors:
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO dep_parse_errors (file_path, error_msg, updated_at)
                        VALUES %s
                        """,
                        [(f, e, now) for f, e in parse_errors],
                    )
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract Python import graph and write to Postgres."
    )
    parser.add_argument("--repo-root", required=True, help="Absolute path to repo root")
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        print(f"ERROR: --repo-root {repo_root} is not a directory", file=sys.stderr)
        return 1

    print(f"Scanning {repo_root} ...")
    edges, parse_errors = build_edges(repo_root)

    total_files = len(_collect_py_files(repo_root))
    error_count = len(parse_errors)
    error_rate = error_count / total_files if total_files else 0.0
    internal_edges = sum(1 for _, _, i in edges if i)

    print(f"  .py files scanned : {total_files}")
    print(f"  Parse errors      : {error_count} ({error_rate * 100:.1f}%)")
    print(f"  Internal edges    : {internal_edges}")
    print(f"  External edges    : {len(edges) - internal_edges}")

    print("Building transitive closure ...")
    transitive = build_transitive_closure(edges)
    print(f"  Transitive edges  : {len(transitive)}")

    print("Writing to DB ...")
    write_to_db(args.db_url, edges, transitive, parse_errors)
    print("Done.")

    if error_rate > 0.02:
        print(
            f"ERROR: parse error rate {error_rate * 100:.1f}% exceeds 2% threshold.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
