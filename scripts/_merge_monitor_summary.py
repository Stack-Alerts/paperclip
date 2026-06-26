#!/usr/bin/env python3
"""Render merge-monitor JSON output as a GitHub Actions step summary.

Reads /tmp/merge-monitor-output.json (written by scripts/merge_monitor.py) and
emits Markdown to $GITHUB_STEP_SUMMARY. Falls back to a single status line if
the JSON file is absent (routine did not run to completion).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUTPUT_PATH = "/tmp/merge-monitor-output.json"


def main() -> int:
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        print("GITHUB_STEP_SUMMARY not set — nothing to write", file=sys.stderr)
        return 0

    lines: list[str] = ["## Merge Monitor — Hourly Run", ""]

    if not Path(OUTPUT_PATH).exists():
        lines.append("**Status:** routine did not produce /tmp/merge-monitor-output.json")
        Path(summary_file).write_text("\n".join(lines) + "\n")
        return 0

    with open(OUTPUT_PATH) as f:
        s = json.load(f)

    lines.extend([
        f"- **Timestamp:** {s['timestamp']}",
        f"- **Dry run:** {s['dry_run']}",
        f"- **OPEN PRs scanned:** {s['open_prs']}",
        f"- **Queued runs (start):** {s['queued_runs_start']}",
        f"- **In-progress (start):** {s['in_progress_runs_start']}",
        f"- **Wasted queued runs cancelled:** {len(s['waste_cancelled'])}",
        f"- **Duplicate queued runs cancelled:** {len(s['duplicate_cancelled'])}",
        f"- **PRs re-tested:** {s['retested_prs']}",
        f"- **Merged this cycle:** {len(s['merged'])}",
        f"- **Merges BLOCKED:** {len(s['merge_blocked'])}",
        f"- **Paperclip intervention posted:** {s['intervention_posted']}",
    ])

    if s["merged"]:
        lines.extend(["", "### Merged this cycle"])
        for pr, detail in s["merged"]:
            lines.append(f"- PR #{pr}: {detail}")

    if s["merge_blocked"]:
        lines.extend(["", "### Merges BLOCKED (needs CEO attention)"])
        for pr, detail in s["merge_blocked"]:
            lines.append(f"- PR #{pr}: {detail}")

    if s["waste_cancelled"]:
        lines.extend(["", "### Wasted queued runs cancelled"])
        for rid in s["waste_cancelled"]:
            lines.append(f"- run {rid}")

    if s["duplicate_cancelled"]:
        lines.extend(["", "### Duplicate queued runs cancelled"])
        for rid in s["duplicate_cancelled"]:
            lines.append(f"- run {rid}")

    Path(summary_file).write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
