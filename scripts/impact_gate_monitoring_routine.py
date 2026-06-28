"""Impact Gate monitoring event-gated routine (Stage 2) — BTCAAAAA-38266.

Wraps the existing `src.impact_gate.scan_fix_issues_done.scan` so the
5-minute periodic sweep does no work when the ungated-issues set is
unchanged AND the safety floor (default 5h) has not elapsed. Behavior
is controlled by the IMPACT_GATE_MONITORING_IDEMPOTENT env var
(default: true) so the team can roll back without code change.

Mirrors the merge-dispatch event-gate pattern (BTCAAAAA-38258,
scripts/merge_dispatch_routine.py).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dotenv import load_dotenv  # noqa: E402

# Only load .env locally; CI / Paperclip runtime inject env directly.
if not os.environ.get("PAPERCLIP_API_URL"):
    load_dotenv(REPO_ROOT / ".env")

from impact_gate.scan_fix_issues_done import scan as _scan  # noqa: E402

log = logging.getLogger("impact_gate_monitoring")
_TELEMETRY_LOGGER = logging.getLogger("impact_gate_monitoring.telemetry")

WATERMARK_FILE = REPO_ROOT / "data" / "impact_gate_monitoring_watermark.json"
_TRACKING_ISSUE_ID = os.environ.get("IMPACT_GATE_MONITORING_TRACKING_ISSUE_ID", "")

IMPACT_GATE_MONITORING_SAFETY_FLOOR_MINUTES = int(
    os.environ.get("IMPACT_GATE_MONITORING_SAFETY_FLOOR_MINUTES", "300")  # 5h
)
IMPACT_GATE_MONITORING_IDEMPOTENT = (
    os.environ.get("IMPACT_GATE_MONITORING_IDEMPOTENT", "true").lower() != "false"
)


def load_watermark() -> dict[str, Any] | None:
    """Return the persisted watermark dict, or None if missing/corrupt."""
    try:
        return json.loads(WATERMARK_FILE.read_text())
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Failed to load watermark %s: %s", WATERMARK_FILE, exc)
        return None


def save_watermark(
    ungated_ids: list[str],
    routine_origin_id: str = "",
    issue_id: str = "",
) -> bool:
    """Persist the watermark. Returns True on success, False on error."""
    sorted_ids = sorted({i for i in ungated_ids if i})
    payload = {
        "lastScanAt": datetime.now(timezone.utc).isoformat(),
        "lastUngatedIssueIds": sorted_ids,
        "routineOriginId": routine_origin_id,
        "issueId": issue_id,
    }
    try:
        WATERMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
        WATERMARK_FILE.write_text(json.dumps(payload))
        return True
    except OSError as exc:
        log.error("Failed to save watermark %s: %s", WATERMARK_FILE, exc)
        return False


def check_early_exit(
    current_ungated_ids: list[str],
    watermark: dict[str, Any] | None = None,
) -> bool:
    """Return True iff the routine should short-circuit (no work to do).

    Conditions for early-exit:
      * idempotency kill-switch is ON
      * watermark exists and parses
      * watermark is fresh (within safety floor)
      * watermark's lastUngatedIssueIds matches current_ungated_ids (set-equal)
    """
    if not IMPACT_GATE_MONITORING_IDEMPOTENT:
        return False
    wm = watermark if watermark is not None else load_watermark()
    if not wm:
        return False
    last_scan_at_raw = wm.get("lastScanAt")
    if not last_scan_at_raw:
        return False
    try:
        last_scan_at = datetime.fromisoformat(last_scan_at_raw)
    except (TypeError, ValueError):
        return False
    if last_scan_at.tzinfo is None:
        last_scan_at = last_scan_at.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - last_scan_at).total_seconds() / 60
    if age_minutes >= IMPACT_GATE_MONITORING_SAFETY_FLOOR_MINUTES:
        return False
    return set(wm.get("lastUngatedIssueIds", [])) == set(current_ungated_ids)


def emit_telemetry_log(
    fired_at: datetime,
    idempotency_skip: bool,
    would_work_count: int,
    child_created: int,
) -> None:
    """Emit a structured JSON telemetry log line for observability."""
    payload = {
        "routine": "impact_gate_monitoring",
        "fired_at": fired_at.isoformat(),
        "idempotency_skip": idempotency_skip,
        "would_work_count": would_work_count,
        "child_created": child_created,
    }
    _TELEMETRY_LOGGER.info(json.dumps(payload))


def _scan_for_ungated(days_back: int | None = 7) -> list[str]:
    """Run the underlying scan() and return the sorted list of ungated issue IDs.

    Wrapped as a module-level function so tests can monkeypatch it for
    determinism.
    """
    try:
        report = _scan(days_back=days_back, retroactive=False)
    except Exception as exc:
        log.error("Underlying scan() failed: %s", exc)
        return []
    ungated_issues = report.get("ungated_issues") or []
    return sorted(
        {issue.get("id", "") for issue in ungated_issues if issue.get("id")}
    )


def _post_tracking_comment(
    tracking_issue_id: str,
    body: str,
    fired_at: datetime,
    ungated_ids: list[str],
    would_work_count: int,
    idempotency_skip: bool,
) -> bool:
    """Post a single per-cycle comment to the tracking issue.

    Returns True on success, False on failure. Wrapped as a module-level
    function so tests can monkeypatch it for determinism.
    """
    try:
        import urllib.request

        api_url = os.environ.get("PAPERCLIP_API_URL", "")
        api_key = os.environ.get("PAPERCLIP_API_KEY", "")
        run_id = os.environ.get("PAPERCLIP_RUN_ID", "")
        if not (api_url and api_key and tracking_issue_id):
            log.info(
                "Skipping tracking-comment post: api=%r issue=%r",
                bool(api_url), tracking_issue_id,
            )
            return False
        url = f"{api_url.rstrip('/')}/api/issues/{tracking_issue_id}/comments"
        req = urllib.request.Request(
            url,
            data=json.dumps({"body": body}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **({"X-Paperclip-Run-Id": run_id} if run_id else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except Exception as exc:
        log.error("Failed to post tracking comment: %s", exc)
        return False


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Flow:
      1. Scan for the current set of ungated issue IDs.
      2. Compare to watermark; if fresh + unchanged → early-exit.
      3. Otherwise post a single tracking-comment summary and save watermark.
      4. Always emit a structured telemetry log line.
    """
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    fired_at = datetime.now(timezone.utc)
    ungated_ids = _scan_for_ungated()
    would_work_count = len(ungated_ids)

    skip = check_early_exit(current_ungated_ids=ungated_ids)

    child_created = 0
    if skip:
        # On early-exit, no work is performed: would_work_count collapses to 0
        # and we skip posting the tracking-comment + watermark save.
        would_work_count = 0
    else:
        body = (
            f"**Impact Gate monitoring — {fired_at.isoformat()}**\n\n"
            f"- idempotency_skip: `false`\n"
            f"- would_work_count: `{would_work_count}`\n"
            f"- ungated_ids: `{','.join(ungated_ids) or '(none)'}`\n"
        )
        if _TRACKING_ISSUE_ID and _post_tracking_comment(
            _TRACKING_ISSUE_ID, body, fired_at, ungated_ids, would_work_count, False
        ):
            child_created = 1
        save_watermark(
            ungated_ids=ungated_ids,
            routine_origin_id=os.environ.get("PAPERCLIP_ROUTINE_ORIGIN_ID", ""),
            issue_id=os.environ.get("PAPERCLIP_ISSUE_ID", ""),
        )

    emit_telemetry_log(
        fired_at=fired_at,
        idempotency_skip=skip,
        would_work_count=would_work_count,
        child_created=child_created,
    )

    print(json.dumps({  # noqa: T201
        "idempotency_skip": skip,
        "would_work_count": would_work_count,
        "child_created": child_created,
        "ungated_count": would_work_count,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
