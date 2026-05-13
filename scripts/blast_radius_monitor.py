#!/usr/bin/env python3
"""Blast Radius worker health monitor — parse worker output and create alerts.

Reads the JSON artifact produced by the Blast Radius worker (``--json-summary``
output) and creates a Paperclip alert issue when errors or anomalies are
detected.  Intended to run as a post-processing step in CI or as a scheduled
health-check workflow.

Usage:
    python scripts/blast_radius_monitor.py --worker-output /tmp/br-output.json [--dry-run]
    python scripts/blast_radius_monitor.py --worker-output /tmp/br-output.json \\
        --run-url https://github.com/.../actions/runs/123 --dry-run

The script **always exits 0** (so it never fails the parent workflow) — errors in
alert creation are logged but do not block the pipeline.

Alert rules:
    - Error rate > 50% of processed issues  -> critical alert
    - Any errors in a poll run              -> medium alert
    - Single-issue processing error         -> medium alert
    - Dry-run runs are silently skipped (no alert needed)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("blast_radius_monitor")

REPO_ROOT = Path(__file__).resolve().parent.parent

CTO_AGENT_ID = "41b5ede6-e209-40ba-b923-dc969c722e6d"
ALERT_LABEL = "blast-radius-alert"

_ALERT_SEARCH_TERM = "Blast Radius Worker Alert"


def _setup_session():
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from touch_index.paperclip_client import _board_session, _base, _company

    return _board_session(), _base(), _company()


def _find_todays_alert(
    base_url: str,
    company_id: str,
    sess,
    date_str: str,
) -> dict | None:
    from touch_index.paperclip_client import _paginate

    try:
        candidates = _paginate(
            f"/api/companies/{company_id}/issues",
            {"q": _ALERT_SEARCH_TERM, "limit": 50},
            page_size=50,
        )
        for issue in candidates:
            title = issue.get("title", "")
            labels = [l.get("name", "") for l in (issue.get("labels") or [])]
            if date_str in title and ALERT_LABEL in labels:
                logger.info(
                    "Found existing alert issue %s: %s",
                    issue.get("identifier", ""),
                    title,
                )
                return issue
        return None
    except Exception as exc:
        logger.warning("Failed to search for existing alerts: %s", exc)
        return None


def _compute_severity(data: dict) -> tuple[str, str]:
    """Return (priority, short_reason) for the alert based on worker output."""
    mode = data.get("mode", "unknown")

    if mode == "single-issue":
        result = data.get("result", {})
        if result.get("error"):
            return ("medium", f"Single-issue processing error: {result['error'][:120]}")
        return ("low", "Single-issue processed without error — unexpected alert path")

    issues_processed = data.get("issues_processed", 0)
    issues_with_errors = data.get("issues_with_errors", 0)

    if issues_processed == 0:
        return ("low", "No issues processed in this run (idle cycle) — unexpected alert path")

    error_rate = issues_with_errors / max(issues_processed, 1)
    if error_rate > 0.5:
        return (
            "critical",
            f"{issues_with_errors}/{issues_processed} issues had errors ({error_rate:.0%} error rate)",
        )
    if issues_with_errors > 0:
        return (
            "medium",
            f"{issues_with_errors}/{issues_processed} issues had errors",
        )
    return ("low", "No errors — unexpected alert path")


def create_alert(
    base_url: str,
    company_id: str,
    sess,
    data: dict,
    run_url: str | None,
    dry_run: bool,
) -> bool:
    """Create a Blast Radius worker alert issue on Paperclip.

    Returns True when the alert was created or no alert was needed.
    Returns False on a genuine failure to create the alert.
    """
    if data.get("dry_run", False):
        logger.info("Worker ran in dry-run mode — skipping alert")
        return True

    mode = data.get("mode", "unknown")
    issues_processed = data.get("issues_processed", 0)
    issues_with_errors = data.get("issues_with_errors", 0)
    result = data.get("result", {})

    # Determine if an alert is actually needed
    needs_alert = False
    if mode == "single-issue":
        if result.get("error"):
            needs_alert = True
    elif mode == "polling":
        if issues_with_errors > 0:
            needs_alert = True

    if not needs_alert:
        logger.info(
            "Worker run healthy (mode=%s, processed=%s, errors=%s) — no alert needed",
            mode,
            issues_processed,
            issues_with_errors,
        )
        return True

    priority, reason = _compute_severity(data)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())

    existing = _find_todays_alert(base_url, company_id, sess, date_str)
    if existing is not None:
        eid = existing.get("identifier", "")
        logger.info(
            "Alert already exists for %s (%s) — appending update comment",
            date_str,
            eid,
        )
        _append_update_comment(
            base_url, sess, existing.get("id", ""), eid, reason, data, run_url
        )
        return True

    title = f"{_ALERT_SEARCH_TERM} — {date_str} ({priority})"

    body_lines = [
        f"**Blast Radius worker detected errors on {ts}**\n",
        f"- **Mode:** `{mode}`",
        f"- **Issues processed:** {issues_processed}",
        f"- **Issues with errors:** {issues_with_errors}",
        f"- **Reason:** {reason}",
    ]
    if run_url:
        body_lines.append(f"- **CI Run:** {run_url}")

    if mode == "single-issue" and result.get("error"):
        body_lines.append(f"\n### Error Detail\n```\n{result['error'][:3000]}\n```")

    body_lines.append(
        "\n---\n"
        "### Action Required\n\n"
        "1. Check the [Blast Radius Worker run]("
        + (run_url or "#")
        + ") for detailed logs.\n"
        "2. Verify Paperclip API and Touch Index DB connectivity.\n"
        "3. Review affected issues — manually re-run with `--force-reprocess` if needed.\n"
        "4. Check worker state file for corruption: `data/blast_radius_worker_state.json`.\n\n"
        "---\n"
        "_Auto-generated by blast-radius-monitor CI pipeline._"
    )

    body = "\n".join(body_lines)

    if dry_run:
        logger.info("DRY RUN: would create alert issue '%s'", title)
        print(  # noqa: T201
            json.dumps(
                {
                    "title": title,
                    "description": body,
                    "labels": [ALERT_LABEL],
                    "assigneeAgentId": CTO_AGENT_ID,
                    "priority": priority,
                },
                indent=2,
            )
        )
        return True

    payload = {
        "title": title,
        "description": body,
        "labels": [ALERT_LABEL],
        "assigneeAgentId": CTO_AGENT_ID,
        "priority": priority,
        "status": "todo",
    }

    try:
        resp = sess.post(
            f"{base_url}/api/companies/{company_id}/issues",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        created = resp.json()
        logger.info(
            "Created alert issue %s: %s",
            created.get("identifier", ""),
            title,
        )
        return True
    except Exception as exc:
        logger.error("Failed to create alert issue: %s", exc)
        return False


def _append_update_comment(
    base_url: str,
    sess,
    issue_id: str,
    identifier: str,
    reason: str,
    data: dict,
    run_url: str | None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    body = (
        f"### Recurring Alert — {ts}\n\n"
        f"**Reason:** {reason}\n"
        f"- Issues processed: {data.get('issues_processed', 'N/A')}\n"
        f"- Issues with errors: {data.get('issues_with_errors', 'N/A')}\n"
    )
    if run_url:
        body += f"- CI Run: {run_url}\n"
    body += "\n_The issue persists — see above for initial alert details._"

    try:
        resp = sess.post(
            f"{base_url}/api/issues/{issue_id}/comments",
            json={"body": body},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("Posted update comment to alert %s", identifier)
    except Exception as exc:
        logger.warning("Failed to post update comment to alert %s: %s", identifier, exc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitor Blast Radius worker health and create alerts on errors",
    )
    parser.add_argument(
        "--worker-output",
        required=True,
        help="Path to JSON file produced by the Blast Radius worker (--json-summary output)",
    )
    parser.add_argument(
        "--run-url",
        default=None,
        help="GitHub Actions run URL for linking in the alert body",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without creating issues",
    )
    args = parser.parse_args()

    out_path = Path(args.worker_output)
    if not out_path.exists():
        logger.error("Worker output file not found: %s", out_path)
        sys.exit(0)

    try:
        data = json.loads(out_path.read_text())
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse worker output JSON: %s", exc)
        sys.exit(0)

    sess, base_url, company_id = _setup_session()

    ok = create_alert(base_url, company_id, sess, data, args.run_url, args.dry_run)
    if not ok:
        logger.warning("Alert creation had issues — exiting 0 to avoid blocking CI")
        sys.exit(0)

    logger.info("Blast Radius monitor complete")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    main()
