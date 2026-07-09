#!/usr/bin/env python3
"""
session_end_autosave.py — Snapshot the working tree on Paperclip run termination.

Invoked by the Paperclip adapter wrapper (or the opencode watchdog) right
before a run ends. If the current branch matches `fix/BTCAAAAA-*` or
`feat/BTCAAAAA-*`, stage everything, commit a WIP snapshot, and push to
origin with `--force-with-lease` so partial work survives restarts, OOM
kills, and harness crashes.

See BTCAAAAA-39068 for the original spec. This script is the Tier 1 hook
the paperclip merge process was missing.

Usage:
    session_end_autosave.py [--cwd <path>] [--run-id <id>] [--no-autosave]
                            [--issue-id BTCAAAAA-NNN]

Exit codes:
    0  — snapshot committed and pushed (or nothing to commit, or no-op branch)
    2  — git invocation failed (logged, exit non-zero to surface in run output)
    3  — opted out via --no-autosave or PAPERCLIP_NO_AUTOSAVE=1
    4  — not in a git repo / no reachable .git
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

LOG_PATH = Path(".paperclip/autosave.log")
PROTECTED_BRANCH_PREFIXES = ("fix/BTCAAAAA-", "feat/BTCAAAAA-")


def log(message: str) -> None:
    """Append a timestamped line to the autosave log; fall back to stderr."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[session_end_autosave] {message}\n"
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        sys.stderr.write(line)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command, capture output, return CompletedProcess."""
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_repo(start: Path) -> Path | None:
    """Walk up from `start` looking for a .git directory or file."""
    cur = start.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def current_branch(repo: Path) -> str | None:
    """Return the current short branch name, or None if detached/unborn."""
    res = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        repo,
    )
    if res.returncode != 0:
        return None
    name = res.stdout.strip()
    return name if name and name != "HEAD" else None


def is_protected_branch(branch: str) -> bool:
    return any(branch.startswith(prefix) for prefix in PROTECTED_BRANCH_PREFIXES)


def has_changes_to_commit(repo: Path) -> bool:
    """True if there is at least one staged-or-unstaged change vs HEAD."""
    res = run(["git", "status", "--porcelain"], repo)
    return res.returncode == 0 and bool(res.stdout.strip())


def push_with_lease(repo: Path, branch: str) -> tuple[int, str]:
    """Push with --force-with-lease; return (returncode, stderr-or-empty)."""
    res = run(
        ["git", "push", "origin", branch, "--force-with-lease"],
        repo,
    )
    return res.returncode, (res.stderr or "").strip()


def autosave(cwd: Path | None, run_id: str | None, issue_id: str | None,
             no_autosave: bool) -> int:
    if no_autosave or os.environ.get("PAPERCLIP_NO_AUTOSAVE") == "1":
        log("opt-out via --no-autosave or PAPERCLIP_NO_AUTOSAVE=1")
        return 3

    start = Path(cwd).resolve() if cwd else Path.cwd()
    repo = resolve_repo(start)
    if repo is None:
        log(f"no git repo reachable from {start}; exiting")
        return 4

    branch = current_branch(repo)
    if branch is None:
        log(f"{repo}: detached HEAD or unborn branch; skipping")
        return 0
    if not is_protected_branch(branch):
        log(f"{repo}: branch {branch!r} is not protected; skipping")
        return 0

    commit_msg_parts = ["WIP"]
    if issue_id:
        commit_msg_parts.append(f"({issue_id})")
    commit_msg_parts.append("auto-snapshot")
    if run_id:
        commit_msg_parts.append(run_id)
    commit_subject = ": ".join(commit_msg_parts[:2]) + " " + " ".join(commit_msg_parts[2:])

    add_res = run(["git", "add", "-A"], repo)
    if add_res.returncode != 0:
        log(f"{repo}: git add failed: {add_res.stderr.strip()}")
        return 2

    cached_res = run(["git", "diff", "--cached", "--quiet"], repo)
    if cached_res.returncode == 0:
        log(f"{repo}: nothing to commit on {branch}")
        return 0

    commit_res = run(["git", "commit", "-m", commit_subject], repo)
    if commit_res.returncode != 0:
        log(f"{repo}: git commit failed: {commit_res.stderr.strip()}")
        return 2

    log(f"{repo}: committed {commit_subject!r} on {branch}")

    rc, push_err = push_with_lease(repo, branch)
    if rc != 0:
        log(f"{repo}: push failed (rc={rc}): {push_err}")
        return 2

    log(f"{repo}: pushed {branch} to origin")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cwd",
        default=None,
        help="Working directory to start the .git walk from (default: cwd)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Paperclip run id, embedded in the WIP commit message",
    )
    parser.add_argument(
        "--issue-id",
        default=None,
        help="Paperclip issue identifier (e.g. BTCAAAAA-39068) for the WIP tag",
    )
    parser.add_argument(
        "--no-autosave",
        action="store_true",
        help="Skip the snapshot (used by intentional discards)",
    )
    args = parser.parse_args()

    return autosave(
        cwd=Path(args.cwd) if args.cwd else None,
        run_id=args.run_id,
        issue_id=args.issue_id,
        no_autosave=args.no_autosave,
    )


if __name__ == "__main__":
    raise SystemExit(main())