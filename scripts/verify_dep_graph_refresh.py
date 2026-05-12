#!/usr/bin/env python3
"""Verify the nightly dep-graph-refresh run completed successfully.

Checks:
  1. dep_graph.json exists and is valid JSON
  2. There is a recent [skip ci] commit by the bot touching dep_graph.json
  3. Parse error count has not increased vs prior baseline
  4. Graph stats look healthy (edge count, file count)

Usage:
    python scripts/verify_dep_graph_refresh.py              # quick health check
    python scripts/verify_dep_graph_refresh.py --verbose    # full report

Exit code: 0 = all checks pass, 1 = one or more checks failed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GRAPH_PATH = REPO_ROOT / "dep_graph.json"

MIN_FILES = 100
MIN_EDGES = 200
MAX_PARSE_ERRORS = 10


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)


def check_graph_exists() -> tuple[bool, str]:
    if not GRAPH_PATH.exists():
        return False, "dep_graph.json not found"
    return True, "dep_graph.json exists"


def check_graph_valid_json() -> tuple[bool, str]:
    try:
        with open(GRAPH_PATH) as f:
            g = json.load(f)
        required_keys = {"forward", "reverse", "all_files", "parse_errors", "stats"}
        missing = required_keys - set(g.keys())
        if missing:
            return False, f"Missing keys: {missing}"
        return True, f"Valid JSON with {len(g['forward'])} forward, {len(g['reverse'])} reverse edges"
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Invalid/broken JSON: {e}"


def check_stats() -> tuple[bool, str]:
    with open(GRAPH_PATH) as f:
        g = json.load(f)
    s = g["stats"]
    issues = []
    if s["total_files"] < MIN_FILES:
        issues.append(f"total_files {s['total_files']} < {MIN_FILES}")
    if s["edge_count"] < MIN_EDGES:
        issues.append(f"edge_count {s['edge_count']} < {MIN_EDGES}")
    if s["error_files"] > MAX_PARSE_ERRORS:
        issues.append(f"error_files {s['error_files']} > {MAX_PARSE_ERRORS}")
    if issues:
        return False, f"Stats unhealthy: {'; '.join(issues)}"
    return True, (
        f"{s['total_files']} files, {s['edge_count']} edges, "
        f"{s['error_files']} errors ({s['parse_rate_pct']}% parse rate)"
    )


def check_bot_commit() -> tuple[bool, str]:
    result = _run([
        "git", "log", "--all", "--oneline", "--grep", "skip ci",
        "-5", "--", "dep_graph.json",
    ])
    if not result.stdout.strip():
        result = _run([
            "git", "log", "--all", "--oneline",
            "--author", "github-actions",
            "-5", "--", "dep_graph.json",
        ])
    if not result.stdout.strip():
        return False, "No [skip ci] bot commit found touching dep_graph.json"
    lines = result.stdout.strip().split("\n")
    return True, f"Bot commit(s) found ({len(lines)}):\n" + "\n".join(f"  {l}" for l in lines)


def check_no_regression(verbose: bool) -> tuple[bool, str]:
    """Compare current parse error count with the previous version."""
    result = _run(["git", "show", "HEAD:dep_graph.json"])
    if result.returncode != 0 or not result.stdout.strip():
        return True, "No prior dep_graph.json in HEAD to compare (first run)"

    try:
        prev = json.loads(result.stdout)
    except json.JSONDecodeError:
        return True, "Could not parse prior dep_graph.json (first-run baseline OK)"

    with open(GRAPH_PATH) as f:
        curr = json.load(f)

    prev_errors = prev.get("stats", {}).get("error_files", 0)
    curr_errors = curr.get("stats", {}).get("error_files", 0)
    prev_edges = prev.get("stats", {}).get("edge_count", 0)
    curr_edges = curr.get("stats", {}).get("edge_count", 0)

    diffs = []
    if curr_errors > prev_errors:
        diffs.append(f"parse errors increased: {prev_errors} -> {curr_errors}")
    if curr_edges < prev_edges:
        diffs.append(f"edge count decreased: {prev_edges} -> {curr_edges}")

    if diffs:
        return False, f"Regression detected: {'; '.join(diffs)}"

    msg = f"No regression vs HEAD (errors: {prev_errors}->{curr_errors}, edges: {prev_edges}->{curr_edges})"
    if verbose:
        msg += f"\n  prev: {json.dumps(prev.get('stats', {}))}"
        msg += f"\n  curr: {json.dumps(curr.get('stats', {}))}"
    return True, msg


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify nightly dep-graph-refresh run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Full report")
    args = parser.parse_args()

    checks = [
        ("Graph exists", check_graph_exists),
        ("Valid JSON", check_graph_valid_json),
        ("Stats healthy", check_stats),
        ("Bot commit", check_bot_commit),
        ("No regression", lambda: check_no_regression(args.verbose)),
    ]

    all_ok = True
    for name, fn in checks:
        ok, msg = fn()
        status = "PASS" if ok else "FAIL"
        all_ok = all_ok and ok
        if args.verbose or not ok:
            print(f"  [{status}] {name}: {msg}")
        elif ok:
            print(f"  [{status}] {name}")

    print()
    if all_ok:
        print("  RESULT: ALL CHECKS PASSED — dep-graph-refresh is healthy")
        return 0
    else:
        print("  RESULT: ONE OR MORE CHECKS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
