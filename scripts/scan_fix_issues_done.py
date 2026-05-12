#!/usr/bin/env python3
"""Scan fix/bug issues that are already ``done`` and report Impact Gate coverage.

Usage:
    python scripts/scan_fix_issues_done.py
    python scripts/scan_fix_issues_done.py --dry-run
    python scripts/scan_fix_issues_done.py --retroactive
    python scripts/scan_fix_issues_done.py --days-back 7
    python scripts/scan_fix_issues_done.py --json-summary

Output schema (JSON)::

    {
        "timestamp": "<ISO-8601>",
        "total_done_fix_issues": <int>,
        "gated": {"pass": <int>, "fail": <int>, "bypassed": <int>, "error": <int>, "skipped": <int>},
        "ungated_count": <int>,
        "ungated_issues": [{"id": "<uuid>", "identifier": "BTCAAAAA-NNN", "title": "..."}, ...],
        "gated_issues": [{"identifier": "BTCAAAAA-NNN", "gate_status": "PASS|FAIL|BYPASSED|ERROR|SKIPPED"}, ...],
    }

The ``--retroactive`` flag causes the scan to run the full Impact Gate on any
ungated issue, posting results and transitioning the issue to its current
state (the gate runner handles PASS -> done, FAIL -> in_progress).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from touch_index.paperclip_client import (
    _paginate,
    _company,
    fetch_issue_comments,
)
from impact_gate.worker import process_issue
from blast_radius.worker import _is_fix_issue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("scan_fix_issues_done")

# Regex to detect an Impact Gate comment in an issue's comment thread.
# Matches the markdown headers produced by worker._build_*_comment().
_GATE_HEADER_RE = re.compile(
    r"^## Impact Gate:\s+(PASS|FAIL|BYPASSED|ERROR|SKIPPED)", re.MULTILINE
)


def _check_gate_status(issue_id: str) -> str | None:
    """Check comments for an Impact Gate result.

    Returns the gate status string (PASS, FAIL, BYPASSED, ERROR) or None
    if no Impact Gate comment was found.
    """
    try:
        comments = fetch_issue_comments(issue_id)
    except Exception as exc:
        logger.warning("Failed to fetch comments for issue %s: %s", issue_id, exc)
        return None

    for comment in comments:
        body = comment.get("body", "")
        m = _GATE_HEADER_RE.search(body)
        if m:
            return m.group(1)
    return None


def scan(
    days_back: int | None = None,
    dry_run: bool = False,
    retroactive: bool = False,
) -> dict:
    """Scan done fix/bug issues and report Impact Gate coverage.

    Args:
        days_back: Only scan issues completed within this many days (None = all).
        dry_run: Log results but do NOT run retroactive gates.
        retroactive: Run the Impact Gate on ungated issues.

    Returns a summary dict (see module docstring for schema).
    """
    params: dict = {"status": "done"}
    issues = _paginate(
        f"/api/companies/{_company()}/issues",
        params,
        page_size=100,
    )
    logger.info("Fetched %d done issues total", len(issues))

    if days_back is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        filtered = []
        for issue in issues:
            raw = issue.get("completedAt") or issue.get("updatedAt")
            if raw:
                try:
                    ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    if ts >= cutoff:
                        filtered.append(issue)
                except ValueError:
                    pass
        issues = filtered
        logger.info(
            "Filtered to %d done issues within last %d days", len(issues), days_back
        )

    fix_issues = [i for i in issues if _is_fix_issue(i)]
    logger.info("Found %d fix/bug issues in done status", len(fix_issues))

    gated: dict[str, int] = {
        "pass": 0,
        "fail": 0,
        "bypassed": 0,
        "error": 0,
        "skipped": 0,
    }
    ungated: list[dict] = []
    gated_issues: list[dict] = []

    for issue in fix_issues:
        issue_id = issue.get("id", "")
        identifier = issue.get("identifier", "")
        title = issue.get("title", "")

        gate_status = _check_gate_status(issue_id)

        if gate_status is None:
            ungated.append(
                {
                    "id": issue_id,
                    "identifier": identifier,
                    "title": title,
                }
            )
        else:
            status_key = gate_status.lower()
            gated[status_key] = gated.get(status_key, 0) + 1
            gated_issues.append(
                {
                    "identifier": identifier,
                    "gate_status": gate_status,
                }
            )

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_done_fix_issues": len(fix_issues),
        "gated": gated,
        "ungated_count": len(ungated),
        "ungated_issues": ungated,
        "gated_issues": gated_issues,
    }

    logger.info(
        "Scan complete: %d total, %d gated (PASS=%d FAIL=%d BYPASS=%d ERROR=%d SKIPPED=%d), %d ungated",
        len(fix_issues),
        sum(gated.values()),
        gated.get("pass", 0),
        gated.get("fail", 0),
        gated.get("bypassed", 0),
        gated.get("error", 0),
        gated.get("skipped", 0),
        len(ungated),
    )

    # --- Retroactive gating ---
    if retroactive and ungated and not dry_run:
        logger.info(
            "Running retroactive Impact Gate on %d ungated issues", len(ungated)
        )
        retro_results: list[dict] = []
        for entry in ungated:
            issue_id = entry["id"]
            try:
                r = process_issue(issue_id, dry_run=False, force=True)
                retro_results.append(r)
                logger.info(
                    "Retroactive gate for %s: %s",
                    entry["identifier"],
                    r.get("gate_status"),
                )
            except Exception as exc:
                logger.error(
                    "Retroactive gate failed for %s: %s", entry["identifier"], exc
                )
                retro_results.append({"issue": entry["identifier"], "error": str(exc)})
        result["retroactive_results"] = retro_results

        # Re-scan previously ungated issues to update counts after retroactive gating
        remaining_ungated: list[dict] = []
        for entry in ungated:
            gate_status = _check_gate_status(entry["id"])
            if gate_status is None:
                remaining_ungated.append(entry)
            else:
                status_key = gate_status.lower()
                gated[status_key] = gated.get(status_key, 0) + 1
                gated_issues.append(
                    {"identifier": entry["identifier"], "gate_status": gate_status}
                )
        result["ungated_count"] = len(remaining_ungated)
        result["ungated_issues"] = remaining_ungated
        result["gated"] = gated
        result["gated_issues"] = gated_issues
        logger.info(
            "After retroactive gating: %d remaining ungated, %d total gated",
            len(remaining_ungated),
            sum(gated.values()),
        )

    if dry_run and retroactive:
        logger.info(
            "[dry-run] Would retroactively gate %d ungated issues",
            len(ungated),
        )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan done fix/bug issues for Impact Gate coverage",
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
        help="Log results but do not post comments or run retroactive gates",
    )
    parser.add_argument(
        "--retroactive",
        action="store_true",
        help="Run the Impact Gate on ungated issues",
    )
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="pretty",
        help="Output format (default: pretty)",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Output structured JSON summary to stdout (overrides --output)",
    )
    args = parser.parse_args()

    result = scan(
        days_back=args.days_back,
        dry_run=args.dry_run,
        retroactive=args.retroactive,
    )

    if args.json_summary:
        summary = {
            "worker": "impact-gate-scan-done",
            "dry_run": args.dry_run,
            "retroactive": args.retroactive,
            "timestamp": result["timestamp"],
            "total_done_fix_issues": result["total_done_fix_issues"],
            "gated": result["gated"],
            "ungated_count": result["ungated_count"],
            "ungated_issues": result["ungated_issues"],
            "gated_issues": result["gated_issues"],
        }
        if "retroactive_results" in result:
            summary["retroactive_results"] = result["retroactive_results"]
        print(json.dumps(summary, default=str))  # noqa: T201
    elif args.output == "pretty":
        print(json.dumps(result, indent=2))  # noqa: T201
    else:
        print(json.dumps(result))  # noqa: T201

    return 0 if result["ungated_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
