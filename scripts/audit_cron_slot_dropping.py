#!/usr/bin/env python3
"""Audit GitHub Actions cron slot-dropping across scheduled workflows.

Queries the GitHub REST API for ``event=schedule`` runs of every workflow that
declares a ``schedule:`` trigger, computes the gap distribution between
consecutive scheduled runs, and reports:

- designed cadence (parsed from the workflow's cron expression)
- observed p50 / p95 / max gap between scheduled firings
- slot-drop rate (1 - actual_runs / expected_runs over the audit window)
- whether the current default threshold would suppress observed false positives

The motivation and policy this script implements are documented in
``.github/workflows/README.md`` ("Cadence vs threshold policy"). Run it after
editing thresholds, before tuning them down, or whenever a monitor seems to be
false-positive spiking under load.

Usage::

    # Default: audit every scheduled workflow in the current repo over 7 days
    python scripts/audit_cron_slot_dropping.py

    # Specific workflow over a longer window
    python scripts/audit_cron_slot_dropping.py \\
        --workflow deadman-switch-monitor.yml --days 14

    # Different repo (defaults to Stack-Alerts/BTC-Trade-Engine-PaperClip)
    python scripts/audit_cron_slot_dropping.py --repo owner/name

    # JSON to stdout for piping
    python scripts/audit_cron_slot_dropping.py --json

    # Persist report
    python scripts/audit_cron_slot_dropping.py --output reports/cron-audit.json

Auth: ``GITHUB_TOKEN`` or ``GH_TOKEN`` env var is required for the GH API
calls. Unauthenticated requests are rate-limited at 60 req/hr.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import requests
import yaml

DEFAULT_REPO = "Stack-Alerts/BTC-Trade-Engine-PaperClip"
DEFAULT_WINDOW_DAYS = 7

# Per-monitor default alert thresholds (minutes). Sourced from the monitor
# scripts and workflows; keep in sync with .github/workflows/README.md table.
DEFAULT_THRESHOLDS_MIN: dict[str, int] = {
    "deadman-switch-monitor.yml": 90,
    "backup-deadman-switch-monitor.yml": 180,
    "deadman-switch-local-monitor.yml": 45,
    "paperclip-recovery-monitor.yml": 90,
    "blast-radius-monitor.yml": 90,
    "closure-gate-routine.yml": 45,
    "traceability-monitor.yml": 90,
}


@dataclass
class GapStats:
    p50_min: float | None
    p95_min: float | None
    max_min: float | None
    n_gaps: int


@dataclass
class WorkflowReport:
    workflow: str
    designed_cadence_min: int | None
    cron_expression: str | None
    window_days: int
    expected_runs: int
    actual_runs: int
    missing_runs: int
    drop_rate: float
    observed_gaps: GapStats
    default_threshold_min: int | None
    threshold_sufficient: bool | None
    note: str = ""
    error: str = ""


# --- cron parsing -----------------------------------------------------------


def cron_designed_minutes(expr: str) -> int | None:
    """Parse a GitHub Actions cron expression and return the designed cadence
    in minutes between scheduled firings. Returns ``None`` for expressions
    this parser can't handle (e.g. ``@daily`` aliases — handled separately).
    """
    expr = expr.strip()
    if not expr or expr.startswith("@"):
        aliases = {
            "@hourly": 60,
            "@daily": 1440,
            "@weekly": 10080,
            "@monthly": 43200,
            "@yearly": 525600,
        }
        return aliases.get(expr.lower())

    fields = expr.split()
    if len(fields) != 5:
        return None
    minute, hour, dom, month, dow = fields

    # Restrict to "every-N-period" patterns — DOM/Month/DOW all "*".
    if not (dom == "*" and month == "*" and dow == "*"):
        return None

    minutes = _expand_field(minute, 0, 59)
    hours = _expand_field(hour, 0, 23)
    if minutes is None or hours is None:
        return None

    # Build the firing timestamps within a 24h day, then measure the uniform gap.
    # For uniform-cadence expressions like "*/15 * * * *", "15,45 * * * *", or
    # "0 */4 * * *", the gap between consecutive firings is constant. We compute
    # all firings sorted and return that constant (or None if irregular).
    firings: list[int] = []
    for h in hours:
        for m in minutes:
            firings.append(h * 60 + m)
    firings.sort()
    if len(firings) < 2:
        # Only one firing per day — daily cadence
        return 1440 if hours else None
    diffs = [firings[i + 1] - firings[i] for i in range(len(firings) - 1)]
    diffs.append(24 * 60 - firings[-1] + firings[0])  # wrap midnight
    if all(d == diffs[0] for d in diffs):
        return diffs[0]
    # Irregular spacing — fall back to total span / count
    return int(24 * 60 / len(firings))


def _expand_field(field_expr: str, lo: int, hi: int) -> list[int] | None:
    """Expand a single cron field (minute/hour/day) into the sorted list of
    matched values. Returns None if any token fails to parse.
    """
    out: list[int] = []
    for token in field_expr.split(","):
        step = 1
        if "/" in token:
            token, step_str = token.split("/", 1)
            try:
                step = int(step_str)
            except ValueError:
                return None
        if step <= 0:
            return None
        if token == "*":
            start, end = lo, hi
        elif "-" in token:
            try:
                a, b = token.split("-", 1)
                start, end = int(a), int(b)
            except ValueError:
                return None
        elif token.isdigit():
            start = end = int(token)
        else:
            return None
        if not (lo <= start <= hi) or not (lo <= end <= hi) or end < start:
            return None
        out.extend(range(start, end + 1, step))
    return sorted(set(out))


# --- workflow discovery -----------------------------------------------------


def _parse_simple_yaml(path: Path) -> dict:
    """Read a workflow YAML file and return the parsed document. Wraps
    PyYAML's safe_load so we get a consistent error surface.
    """
    with path.open() as f:
        return yaml.safe_load(f) or {}


def discover_scheduled_workflows(workflows_dir: Path) -> list[tuple[str, str]]:
    """Return ``(filename, cron_expression)`` for every workflow with a
    ``schedule:`` trigger. Files that fail to parse are skipped silently —
    the caller's output will simply lack them.
    """
    results: list[tuple[str, str]] = []
    if not workflows_dir.exists():
        return results
    for path in sorted(workflows_dir.glob("*.yml")):
        if path.name.startswith(".") or path.name in ("README.md",):
            continue
        try:
            data = _parse_simple_yaml(path)
        except Exception:
            continue
        # YAML 1.1 treats bare `on:` as the boolean True (on/off alias).
        # Accept either key so both quoted and unquoted `on:` work.
        on = data.get("on") or data.get(True) or {}
        if not isinstance(on, dict):
            continue
        schedules = on.get("schedule", [])
        if not isinstance(schedules, list):
            continue
        for entry in schedules:
            if isinstance(entry, dict):
                cron = entry.get("cron")
                if isinstance(cron, str):
                    results.append((path.name, cron))
    return results


# --- GH API -----------------------------------------------------------------


def fetch_scheduled_runs(
    repo: str,
    workflow_file: str,
    since: datetime,
    token: str | None,
    page_size: int = 100,
    max_pages: int = 10,
) -> list[dict]:
    """Fetch ``event=schedule`` runs for a workflow since ``since`` (UTC).
    Paginates up to ``max_pages`` to bound request cost.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    headers.setdefault("X-GitHub-Api-Version", "2022-11-28")
    runs: list[dict] = []
    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/runs",
                params={
                    "event": "schedule",
                    "per_page": page_size,
                    "page": page,
                    "created": f">={since.isoformat()}",
                },
                headers=headers,
                timeout=30,
            )
        except requests.RequestException as exc:
            print(f"  ! network error fetching {workflow_file} page {page}: {exc}", file=sys.stderr)
            break
        if resp.status_code == 404:
            # Workflow doesn't exist or has no schedule runs at all
            break
        if resp.status_code != 200:
            print(
                f"  ! GH API {resp.status_code} for {workflow_file}: "
                f"{resp.text[:120]}",
                file=sys.stderr,
            )
            break
        try:
            payload = resp.json()
        except json.JSONDecodeError:
            break
        runs.extend(payload.get("workflow_runs", []))
        if len(runs) >= payload.get("total_count", 0):
            break
    return runs


# --- gap analysis -----------------------------------------------------------


def _parse_run_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def gap_stats(runs: list[dict]) -> GapStats:
    timestamps = sorted(
        ts for ts in (_parse_run_ts(r.get("created_at", "")) for r in runs) if ts is not None
    )
    if len(timestamps) < 2:
        return GapStats(p50_min=None, p95_min=None, max_min=None, n_gaps=len(timestamps))
    gaps_min = [
        (timestamps[i + 1] - timestamps[i]).total_seconds() / 60
        for i in range(len(timestamps) - 1)
    ]
    gaps_min_sorted = sorted(gaps_min)
    n = len(gaps_min_sorted)

    def pct(p: float) -> float:
        if n == 0:
            return 0.0
        idx = max(0, min(n - 1, int(p / 100 * n) - 1 if int(p / 100 * n) > 0 else 0))
        return gaps_min_sorted[idx]

    return GapStats(
        p50_min=round(pct(50), 1),
        p95_min=round(pct(95), 1),
        max_min=round(max(gaps_min_sorted), 1),
        n_gaps=n,
    )


def expected_runs(designed_minutes: int | None, window_days: int) -> int:
    if designed_minutes is None or designed_minutes <= 0:
        return 0
    minutes = window_days * 24 * 60
    return int(minutes / designed_minutes)


def threshold_sufficient(
    gaps: GapStats,
    default_threshold_min: int | None,
    designed_minutes: int | None,
) -> bool | None:
    """Heuristic: the default threshold is sufficient iff observed p95 gap
    stays under it AND it's at least 3× the designed cadence (per policy).
    """
    if default_threshold_min is None or designed_minutes is None:
        return None
    if gaps.p95_min is None:
        return None
    return gaps.p95_min <= default_threshold_min


# --- reporting --------------------------------------------------------------


def render_text(reports: list[WorkflowReport]) -> str:
    lines: list[str] = []
    lines.append("# GH Actions cron slot-drop audit")
    lines.append("")
    lines.append(
        "| Workflow | Designed (min) | Expected | Actual | Drop % | "
        "Observed p50 / p95 / max (min) | Threshold (min) | Sufficient? | Note |"
    )
    lines.append("|---|---:|---:|---:|---:|---|---:|:---:|---|")
    for r in reports:
        if r.error:
            lines.append(f"| `{r.workflow}` | — | — | — | — | — | — | — | {r.error} |")
            continue
        gaps = (
            f"{r.observed_gaps.p50_min} / {r.observed_gaps.p95_min} / "
            f"{r.observed_gaps.max_min}"
            if r.observed_gaps.p50_min is not None
            else "n/a"
        )
        thr = r.default_threshold_min if r.default_threshold_min is not None else "—"
        suff = (
            "✅"
            if r.threshold_sufficient
            else ("❌" if r.threshold_sufficient is False else "—")
        )
        lines.append(
            f"| `{r.workflow}` | {r.designed_cadence_min or '—'} | {r.expected_runs} | "
            f"{r.actual_runs} | {r.drop_rate * 100:.1f}% | {gaps} | {thr} | {suff} | {r.note} |"
        )
    lines.append("")
    lines.append("**Reading the table:**")
    lines.append("- *Drop %* = 1 − actual/expected over the audit window.")
    lines.append("- *Sufficient?* = observed p95 gap ≤ current default threshold.")
    lines.append(
        "- If drop % > 25% on a `on: schedule:` workflow, consider moving the "
        "monitor to a self-hosted runner (GH Actions drops cron slots under load, "
        "not queues them — see .github/workflows/README.md)."
    )
    return "\n".join(lines)


# --- main -------------------------------------------------------------------


def audit_one(
    repo: str,
    workflow_file: str,
    cron_expr: str,
    window_days: int,
    token: str | None,
) -> WorkflowReport:
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    designed = cron_designed_minutes(cron_expr)
    runs = fetch_scheduled_runs(repo, workflow_file, since, token)
    gaps = gap_stats(runs)
    expected = expected_runs(designed, window_days)
    actual = len(runs)
    missing = max(expected - actual, 0)
    drop_rate = (missing / expected) if expected > 0 else 0.0
    default_thr = DEFAULT_THRESHOLDS_MIN.get(workflow_file)
    return WorkflowReport(
        workflow=workflow_file,
        designed_cadence_min=designed,
        cron_expression=cron_expr,
        window_days=window_days,
        expected_runs=expected,
        actual_runs=actual,
        missing_runs=missing,
        drop_rate=round(drop_rate, 3),
        observed_gaps=gaps,
        default_threshold_min=default_thr,
        threshold_sufficient=threshold_sufficient(gaps, default_thr, designed),
        note=(
            "OK"
            if drop_rate < 0.05
            else ("elevated drop; verify with longer window" if drop_rate < 0.25 else "high drop; consider self-hosted runner")
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"owner/name (default: {DEFAULT_REPO})")
    parser.add_argument("--workflow", help="audit only this workflow filename (e.g. deadman-switch-monitor.yml)")
    parser.add_argument("--days", type=int, default=DEFAULT_WINDOW_DAYS, help=f"audit window in days (default: {DEFAULT_WINDOW_DAYS})")
    parser.add_argument("--json", action="store_true", help="emit JSON report to stdout (text table otherwise)")
    parser.add_argument("--output", type=Path, help="write report to this path (text or JSON depending on --json)")
    parser.add_argument("--workflows-dir", type=Path, default=Path(".github/workflows"), help="path to workflows directory")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("warning: no GITHUB_TOKEN/GH_TOKEN set — rate-limited to 60 req/hr", file=sys.stderr)

    scheduled = discover_scheduled_workflows(args.workflows_dir)
    if args.workflow:
        scheduled = [(n, c) for n, c in scheduled if n == args.workflow]
    if not scheduled:
        print(f"no scheduled workflows found under {args.workflows_dir}", file=sys.stderr)
        return 2

    reports: list[WorkflowReport] = []
    for fname, cron in scheduled:
        print(f"auditing {fname} (cron: {cron!r}, designed: {cron_designed_minutes(cron)} min)...", file=sys.stderr)
        try:
            reports.append(audit_one(args.repo, fname, cron, args.days, token))
        except Exception as exc:  # noqa: BLE001
            reports.append(
                WorkflowReport(
                    workflow=fname,
                    designed_cadence_min=None,
                    cron_expression=cron,
                    window_days=args.days,
                    expected_runs=0,
                    actual_runs=0,
                    missing_runs=0,
                    drop_rate=0.0,
                    observed_gaps=GapStats(None, None, None, 0),
                    default_threshold_min=DEFAULT_THRESHOLDS_MIN.get(fname),
                    threshold_sufficient=None,
                    error=str(exc),
                )
            )

    if args.json:
        payload = [_report_to_dict(r) for r in reports]
        output = json.dumps(payload, indent=2)
    else:
        output = render_text(reports)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
        print(f"wrote report to {args.output}", file=sys.stderr)
    else:
        print(output)
    return 0


def _report_to_dict(r: WorkflowReport) -> dict:
    d = asdict(r)
    return d


if __name__ == "__main__":
    sys.exit(main())