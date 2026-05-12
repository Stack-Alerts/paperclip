"""Blast Radius CLI — python -m blast_radius <subcommand> [options].

Subcommands
-----------
  worker (default)  Poll for fix/bug issues transitioning to in_review and post
                    Blast Radius Reports.  Accepts --issue-id, --old-status,
                    --loop, --dry-run, --force-reprocess, --json-summary.

  query             Query the Touch Index for a list of files.
  generate          Generate and post a Blast Radius Report for an issue.
  serve             Start the HTTP API server.

Usage
-----
    python -m blast_radius                              # run worker once
    python -m blast_radius worker --dry-run
    python -m blast_radius worker --issue-id <uuid>
    python -m blast_radius worker --loop 120
    python -m blast_radius query --files src/a.py src/b.py
    python -m blast_radius generate --issue-id <uuid>
    python -m blast_radius serve --port 8765
    python -m blast_radius --json-summary               # structured JSON output

For backward compatibility, flat args (no subcommand) are interpreted as the
worker subcommand:
    python -m blast_radius --dry-run         # same as: worker --dry-run
    python -m blast_radius --issue-id <u>    # same as: worker --issue-id <u>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

_SUBCOMMANDS = frozenset({"worker", "query", "generate", "serve"})


def cmd_query(args: argparse.Namespace) -> int:
    from blast_radius.query import query_blast_radius, to_json_dict

    data = query_blast_radius(args.files)
    print(json.dumps(to_json_dict(data), indent=2))  # noqa: T201
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    from blast_radius.generator import generate_and_post

    result = generate_and_post(
        issue_id=args.issue_id,
        touched_files=args.files or None,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))  # noqa: T201
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from blast_radius.api_server import serve

    serve(port=args.port)
    return 0


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _emit_json_summary(
    args: argparse.Namespace,
    *,
    result: dict | None = None,
    results: list[dict] | None = None,
) -> None:
    """Emit a structured JSON summary of the worker run to stdout."""
    summary: dict = {
        "worker": "blast-radius",
        "mode": "single-issue" if args.issue_id else "polling",
        "dry_run": args.dry_run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if result is not None:
        summary["result"] = result
    if results is not None:
        issues_processed = len(results)
        errors = [r for r in results if "error" in r]
        summary["issues_processed"] = issues_processed
        summary["issues_with_errors"] = len(errors)
    sys.stdout.write(json.dumps(summary, default=str) + "\n")


def _run_worker_cli(args: argparse.Namespace) -> int:
    """Worker subcommand: run once, loop, or process a single issue."""
    from blast_radius.worker import process_issue, run_once, run_loop

    if args.issue_id:
        result = process_issue(
            args.issue_id,
            dry_run=args.dry_run,
            old_status=args.old_status,
            force_reprocess=args.force_reprocess,
        )
        if args.json_summary:
            _emit_json_summary(args, result=result if result is not None else {"skipped": True, "issue": args.issue_id})
        else:
            if result:
                print(json.dumps(result, indent=2))  # noqa: T201
            else:
                print(json.dumps({"skipped": True, "issue": args.issue_id}))  # noqa: T201
        return 0

    if args.loop:
        run_loop(
            interval_seconds=args.loop,
            dry_run=args.dry_run,
            force_reprocess=args.force_reprocess,
        )
        return 0

    results = run_once(dry_run=args.dry_run, force_reprocess=args.force_reprocess)
    if args.json_summary:
        _emit_json_summary(args, results=results)
    else:
        print(json.dumps(results, indent=2))  # noqa: T201
    return 0


def _build_sub_parsers(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "worker",
        help="Poll for fix/bug issues transitioning to in_review and post Blast Radius Reports",
        description="Detect fix/bug issues that transitioned TO in_review and post a Blast Radius Report.",
    )
    p.add_argument("--issue-id", type=str, metavar="UUID", help="Process a single issue by Paperclip UUID (webhook trigger)")
    p.add_argument("--old-status", type=str, metavar="STATUS", help="Previous status when called from a status-change webhook")
    p.add_argument("--loop", type=int, metavar="SECONDS", help="Run continuously, sleeping SECONDS between polls (default: run once and exit)")
    p.add_argument("--dry-run", action="store_true", help="Log reports but do not post comments")
    p.add_argument("--force-reprocess", action="store_true", help="Re-process already-seen issues (bypasses transition detection)")
    p.add_argument("--json-summary", action="store_true", help="Output structured JSON summary to stdout")
    p.set_defaults(func=_run_worker_cli)

    p = sub.add_parser("query", help="Query the Touch Index for a list of files")
    p.add_argument("--files", nargs="+", required=True, metavar="PATH", help="File paths to query (relative to repo root)")
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("generate", help="Generate and post a Blast Radius Report for a Paperclip issue")
    p.add_argument("--issue-id", required=True, metavar="ID", help="Paperclip issue UUID")
    p.add_argument("--files", nargs="+", metavar="PATH", help="Override touchedFiles (parsed from issue description if omitted)")
    p.add_argument("--dry-run", action="store_true", help="Print the report but do not post a comment")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("serve", help="Start the HTTP API server")
    p.add_argument("--port", type=int, default=8765, metavar="PORT")
    p.set_defaults(func=cmd_serve)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="blast-radius",
        description="Blast Radius — Touch Index query, report generator, and polling worker",
        add_help=True,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command")
    _build_sub_parsers(sub)

    argv = sys.argv[1:] if len(sys.argv) > 1 else []
    has_subcommand = any(a in _SUBCOMMANDS for a in argv if not a.startswith("-"))

    if has_subcommand:
        args = parser.parse_args(argv)
        if args.verbose:
            _setup_logging(verbose=True)
        return args.func(args)

    flat_parser = argparse.ArgumentParser(
        prog="blast-radius",
        description="Blast Radius polling worker + webhook handler",
        add_help=True,
    )
    flat_parser.add_argument("-v", "--verbose", action="store_true", help=argparse.SUPPRESS)
    flat_parser.add_argument("--issue-id", type=str, metavar="UUID", help=argparse.SUPPRESS)
    flat_parser.add_argument("--old-status", type=str, metavar="STATUS", help=argparse.SUPPRESS)
    flat_parser.add_argument("--loop", type=int, metavar="SECONDS", help=argparse.SUPPRESS)
    flat_parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    flat_parser.add_argument("--force-reprocess", action="store_true", help=argparse.SUPPRESS)
    flat_parser.add_argument("--json-summary", action="store_true", help=argparse.SUPPRESS)
    flat_args = flat_parser.parse_args(argv)

    _setup_logging(verbose=flat_args.verbose)
    return _run_worker_cli(flat_args)


if __name__ == "__main__":
    sys.exit(main())
