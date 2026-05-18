#!/usr/bin/env python3
"""Wrapper script for Impact Gate scan-done worker.

Polls for fix/bug issues that are done and runs retroactive impact gate.
Maintains a persistent muted state cache to avoid re-gating issues.

Usage
-----
    python scripts/scan_fix_issues_done.py --json-summary --retroactive
    python scripts/scan_fix_issues_done.py --days-back 7 --json-summary
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / ".." / "src"))

from dotenv import load_dotenv

# Only load .env if running locally (not in CI where env vars are pre-set)
if not os.environ.get("PAPERCLIP_API_URL"):
    load_dotenv(Path(__file__).parent / ".." / ".env")

from impact_gate.scan_fix_issues_done import scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("scan_fix_issues_done")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan done fix/bug issues and optionally run Impact Gate retroactively.",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=None,
        metavar="N",
        help="Only scan issues completed within the last N days (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log results but do not save muted entries or run gates",
    )
    parser.add_argument(
        "--retroactive",
        action="store_true",
        help="Run Impact Gate retroactively on ungated issues",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Purge ERROR entries from muted cache before scanning",
    )
    parser.add_argument(
        "--retry-fails",
        action="store_true",
        help="Purge FAIL entries from muted cache before scanning",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Output structured JSON summary to stdout",
    )
    args = parser.parse_args()

    report = scan(
        days_back=args.days_back,
        dry_run=args.dry_run,
        retroactive=args.retroactive,
        retry_errors=args.retry_errors,
        retry_fails=args.retry_fails,
    )

    # Output JSON summary to stdout (always, for CI compatibility)
    print(json.dumps(report, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
