#!/usr/bin/env python3
"""
Query the import dependency graph stored in Postgres.

Usage:
    python scripts/depgraph.py query \\
        --file src/optimizer_v3/database.py \\
        --direction reverse \\
        --transitive \\
        --db-url postgresql://...

Direction:
    reverse   -- show files that import the given file
    forward   -- show files that the given file imports

Flags:
    --transitive  Use the transitive closure table (touch_index_file_deps_transitive).
                  Without this flag, only direct edges are queried.

Output:
    JSON: {"file": "...", "direction": "...", "transitive": bool,
           "results": [{"file": "...", "depth": N}, ...]}
"""

from __future__ import annotations

import argparse
import json
import sys

import psycopg2
import psycopg2.extras


def _query(
    db_url: str,
    file: str,
    direction: str,
    transitive: bool,
) -> list[dict]:
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if direction == "reverse" and transitive:
                # Who transitively depends on `file`?
                cur.execute(
                    """
                    SELECT source_file AS file, min_depth AS depth
                    FROM   touch_index_file_deps_transitive
                    WHERE  dep_file = %s
                    ORDER  BY min_depth, source_file
                    """,
                    (file,),
                )
            elif direction == "forward" and transitive:
                # What does `file` transitively depend on?
                cur.execute(
                    """
                    SELECT dep_file AS file, min_depth AS depth
                    FROM   touch_index_file_deps_transitive
                    WHERE  source_file = %s
                    ORDER  BY min_depth, dep_file
                    """,
                    (file,),
                )
            elif direction == "reverse":
                # Who directly imports `file`?
                cur.execute(
                    """
                    SELECT source_file AS file, 1 AS depth
                    FROM   touch_index_file_deps
                    WHERE  dep_file = %s AND is_internal = TRUE
                    ORDER  BY source_file
                    """,
                    (file,),
                )
            else:
                # Forward direct: what does `file` directly import (internal only)?
                cur.execute(
                    """
                    SELECT dep_file AS file, 1 AS depth
                    FROM   touch_index_file_deps
                    WHERE  source_file = %s AND is_internal = TRUE
                    ORDER  BY dep_file
                    """,
                    (file,),
                )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def cmd_query(args: argparse.Namespace) -> int:
    rows = _query(args.db_url, args.file, args.direction, args.transitive)
    output = {
        "file": args.file,
        "direction": args.direction,
        "transitive": args.transitive,
        "results": rows,
    }
    print(json.dumps(output))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query the Python import dependency graph stored in Postgres."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("query", help="Query dependencies for a file")
    q.add_argument("--file", required=True, help="Repo-relative POSIX file path")
    q.add_argument(
        "--direction",
        choices=["forward", "reverse"],
        default="reverse",
        help="forward = what this file imports; reverse = what imports this file",
    )
    q.add_argument(
        "--transitive",
        action="store_true",
        help="Use transitive closure (touch_index_file_deps_transitive)",
    )
    q.add_argument("--db-url", required=True, help="PostgreSQL connection URL")

    args = parser.parse_args()
    if args.command == "query":
        return cmd_query(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
