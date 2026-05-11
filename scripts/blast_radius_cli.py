#!/usr/bin/env python3
"""Blast Radius CLI — query the Touch Index for a set of files.

Usage
-----
    blast-radius query --files src/optimizer_v3/database/config.py src/strategies/base.py
    blast-radius generate --issue-id <paperclip-issue-id> [--dry-run]
    blast-radius serve [--port 8765]

`query` returns JSON to stdout:
{
  "fr_impact_set": [...],
  "regression_set": [...],
  "downstream_set": [],
  "downstream_note": "Phase 2 dep graph not yet available"
}
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure src/ is on the path when running the script directly.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))


def cmd_query(args: argparse.Namespace) -> int:
    from blast_radius.query import query_blast_radius, to_json_dict

    data = query_blast_radius(args.files)
    print(json.dumps(to_json_dict(data), indent=2))
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    from blast_radius.generator import generate_and_post

    result = generate_and_post(
        issue_id=args.issue_id,
        touched_files=args.files or None,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from blast_radius.api_server import serve

    serve(port=args.port)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="blast-radius",
        description="Blast Radius — Touch Index query and report generator",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # blast-radius query
    p_query = sub.add_parser("query", help="Query the Touch Index for a list of files")
    p_query.add_argument(
        "--files",
        nargs="+",
        required=True,
        metavar="PATH",
        help="File paths to query (relative to repo root)",
    )
    p_query.set_defaults(func=cmd_query)

    # blast-radius generate
    p_gen = sub.add_parser(
        "generate",
        help="Generate and post a Blast Radius Report for a Paperclip issue",
    )
    p_gen.add_argument("--issue-id", required=True, metavar="ID", help="Paperclip issue UUID")
    p_gen.add_argument(
        "--files",
        nargs="+",
        metavar="PATH",
        help="Override touchedFiles (parsed from issue description if omitted)",
    )
    p_gen.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the report but do not post a comment",
    )
    p_gen.set_defaults(func=cmd_generate)

    # blast-radius serve
    p_serve = sub.add_parser("serve", help="Start the HTTP API server")
    p_serve.add_argument("--port", type=int, default=8765, metavar="PORT")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
