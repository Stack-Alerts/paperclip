"""Impact Gate polling worker runner — run by Paperclip routine every 15 minutes.

Fetches in_review fix/bug issues (using blast_radius.worker fix detection)
and runs the Impact Gate on each.

Usage:
    python scripts/run_impact_gate_worker.py
    python scripts/run_impact_gate_worker.py --issue-id <uuid>
    python scripts/run_impact_gate_worker.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from blast_radius.worker import _fetch_in_review_issues, _is_fix_issue
from impact_gate.worker import process_issue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("run_impact_gate_worker")


def _fetch_in_review_fix_issues() -> list[dict]:
    """Return all in_review issues that look like fix/bug issues."""
    issues = _fetch_in_review_issues()
    return [i for i in issues if _is_fix_issue(i)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Impact Gate polling worker runner",
    )
    parser.add_argument(
        "--issue-id",
        type=str,
        metavar="UUID",
        help="Process a single issue by Paperclip UUID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log results but do not post comments or transition issues",
    )
    parser.add_argument(
        "--old-status",
        type=str,
        default=None,
        metavar="STATUS",
        help="Previous issue status (from webhook payload)",
    )
    args = parser.parse_args()

    if args.issue_id:
        logger.info(
            "Processing single issue %s (dry_run=%s, old_status=%s)",
            args.issue_id,
            args.dry_run,
            args.old_status,
        )
        result = process_issue(
            args.issue_id, dry_run=args.dry_run, old_status=args.old_status
        )
        logger.info("Result: %s", result)
        return

    issues = _fetch_in_review_fix_issues()
    logger.info("Found %d fix/bug issue(s) in_review", len(issues))

    if not issues:
        logger.info("Nothing to do")
        return

    for issue in issues:
        issue_id = issue.get("id", "")
        identifier = issue.get("identifier", "")
        logger.info("Processing %s (%s)", identifier, issue_id)
        try:
            result = process_issue(issue_id, dry_run=args.dry_run)
            logger.info("%s result: %s", identifier, result.get("gate_status"))
        except Exception as exc:
            logger.exception("Failed to process %s: %s", identifier, exc)


if __name__ == "__main__":
    main()
