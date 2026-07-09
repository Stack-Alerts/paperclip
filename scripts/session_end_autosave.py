#!/usr/bin/env python3
"""
session_end_autosave.py - Snapshot the working tree on Paperclip run termination.

Invoked by the Paperclip adapter wrapper (or the opencode watchdog) right
before a run ends. If the current branch matches `fix/BTCAAAAA-*` or
`feat/BTCAAAAA-*`, stage everything, commit a WIP snapshot, and push to
origin with `--force-with-lease` so partial work survives restarts, OOM
kills, and harness crashes.

See BTCAAAAA-39068 for the original spec. This script is the Tier 1 hook
the paperclip merge process was missing.

Usage:
    session_end_autosave.py [--cwd <path>] [--run-id <id>] [--issue-id BTCAAAAA-NNN]
                            [--dry-run] [--no-autosave]

Opt-out (returns exit 3, leaves working tree dirty):
    --no-autosave                          command-line flag
    PAPERCLIP_NO_AUTOSAVE=1                environment variable
    AUTOSAVE=0                             environment variable

Exit codes:
    0  - snapshot committed and pushed (or nothing to commit, or no-op branch)
    2  - git invocation failed (logged, exit non-zero to surface in run output)
    3  - opted out via flag or environment variable
    4  - not in a git repo / no reachable .git

Log: append-only structured lines to .paperclip/autosave.log, one per step:

    2026-07-09T10:45:00Z run=47a36e1f branch=fix/BTCAAAAA-1234 sha=abc1234 step=commit status=ok note="WIP(BTCAAAAA-1234): auto-snapshot 47a36e1f"
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(".paperclip/autosave.log")
PROTECTED_BRANCH_PREFIXES = ("fix/BTCAAAAA-", "feat/BTCAAAAA-")
ISSUE_ID_RE = re.compile(r"BTCAAAAA-\d+")
SUBPROCESS_TIMEOUT_SEC = 30
INDEX_LOCK_TIMEOUT_SEC = 5.0
INDEX_LOCK_POLL_INTERVAL_SEC = 0.25


def _utc_stamp() -> str:
    """Current UTC timestamp formatted as YYYY-MM-DDTHH:MM:SSZ."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_structured(
    step: str,
    branch: str,
    run_id: str | None,
    sha: str | None,
    status: str,
    note: str = "",
) -> None:
    """Append one structured line to the autosave log; fall back to stderr."""
    parts = [_utc_stamp(), f"run={run_id or '-'}", f"branch={branch}"]
    if sha:
        parts.append(f"sha={sha}")
    parts.append(f"step={step}")
    parts.append(f"status={status}")
    if note:
        parts.append(f"note={note}")
    line = " ".join(parts) + "\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError as exc:
        sys.stderr.write(line.rstrip("\n") + f"  # log write failed: {exc}\n")


def _log_freeform(message: str) -> None:
    """Append a freeform line (used by opt-out / no-repo paths only)."""
    line = f"[session_end_autosave] {message}\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        sys.stderr.write(line)


def run(
    cmd: list[str], cwd: Path, timeout: int = SUBPROCESS_TIMEOUT_SEC
) -> subprocess.CompletedProcess[str]:
    """Run a git command, capture output, return CompletedProcess."""
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def wait_index_lock(repo: Path, timeout_sec: float = INDEX_LOCK_TIMEOUT_SEC) -> bool:
    """Block until any pre-existing .git/index.lock clears, or the budget runs out.

    Returns True if the lock was cleared (or never existed), False on timeout.
    Git writes .git/index.lock during `add`/`commit`/`stash`; concurrent
    autosaves must serialize rather than race the index.
    """
    lock = repo / ".git" / "index.lock"
    deadline = time.monotonic() + timeout_sec
    while lock.exists():
        if time.monotonic() >= deadline:
            return False
        time.sleep(INDEX_LOCK_POLL_INTERVAL_SEC)
    return True


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


def extract_issue_id(branch: str) -> str | None:
    """Pull the BTCAAAAA-NNN identifier out of a branch name, if present."""
    m = ISSUE_ID_RE.search(branch)
    return m.group(0) if m else None


def head_sha(repo: Path) -> str | None:
    """Return the current HEAD sha, or None if the repo is empty / failing."""
    res = run(["git", "rev-parse", "--verify", "HEAD"], repo)
    if res.returncode != 0:
        return None
    sha = res.stdout.strip()
    return sha or None


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


def build_commit_subject(issue_id: str | None, run_id: str | None) -> str:
    """Render the WIP commit subject.

    Spec: `WIP(BTCAAAAA-NNN): auto-snapshot <run-id>`. If issue-id is missing
    (the branch is protected but carries no identifier - unusual), fall back
    to `WIP: auto-snapshot <run-id>`.
    """
    prefix = f"WIP({issue_id}): " if issue_id else "WIP: "
    suffix = f"auto-snapshot {run_id}" if run_id else "auto-snapshot"
    return prefix + suffix


def autosave(
    cwd: Path | None,
    run_id: str | None,
    issue_id: str | None,
    dry_run: bool,
    no_autosave: bool,
) -> int:
    """Run the snapshot. Returns one of the exit codes documented above."""

    if (
        no_autosave
        or os.environ.get("PAPERCLIP_NO_AUTOSAVE") == "1"
        or os.environ.get("AUTOSAVE") == "0"
    ):
        _log_freeform(
            "opt-out via --no-autosave, PAPERCLIP_NO_AUTOSAVE=1, or AUTOSAVE=0"
        )
        return 3

    start = Path(cwd).resolve() if cwd else Path.cwd()
    repo = resolve_repo(start)
    if repo is None:
        _log_freeform(f"no git repo reachable from {start}; exiting")
        return 4

    branch = current_branch(repo)
    if branch is None:
        _log_structured(
            "resolve",
            "-",
            run_id,
            head_sha(repo),
            "skip",
            "detached HEAD or unborn branch",
        )
        return 0
    if not is_protected_branch(branch):
        _log_structured(
            "resolve", branch, run_id, head_sha(repo), "skip", "non-protected branch"
        )
        return 0

    effective_issue_id = issue_id or extract_issue_id(branch)
    commit_subject = build_commit_subject(effective_issue_id, run_id)

    if dry_run:
        _log_structured(
            "dry-run",
            branch,
            run_id,
            head_sha(repo),
            "ok",
            f"would commit: {commit_subject!r}",
        )
        return 0

    if not wait_index_lock(repo):
        _log_structured(
            "add", branch, run_id, head_sha(repo), "error", "index.lock held > 5s"
        )
        return 2

    add_res = run(["git", "add", "-A"], repo)
    if add_res.returncode != 0:
        _log_structured(
            "add",
            branch,
            run_id,
            head_sha(repo),
            "error",
            (add_res.stderr or "").strip()[:200],
        )
        return 2

    cached_res = run(["git", "diff", "--cached", "--quiet"], repo)
    if cached_res.returncode == 0:
        _log_structured(
            "commit", branch, run_id, head_sha(repo), "noop", "nothing to commit"
        )
        return 0

    commit_res = run(["git", "commit", "-m", commit_subject], repo)
    if commit_res.returncode != 0:
        _log_structured(
            "commit",
            branch,
            run_id,
            head_sha(repo),
            "error",
            (commit_res.stderr or "").strip()[:200],
        )
        return 2

    new_sha = head_sha(repo)
    _log_structured("commit", branch, run_id, new_sha, "ok", commit_subject)

    if not wait_index_lock(repo):
        _log_structured(
            "push", branch, run_id, new_sha, "error", "index.lock held > 5s pre-push"
        )
        return 2

    rc, push_err = push_with_lease(repo, branch)
    if rc != 0:
        _log_structured("push", branch, run_id, new_sha, "error", push_err[:200])
        return 2

    _log_structured("push", branch, run_id, new_sha, "ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
        help="Paperclip issue identifier (e.g. BTCAAAAA-39068) for the WIP tag; "
        "auto-extracted from the branch name when omitted",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log the planned commit subject and exit 0 without touching git",
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
        dry_run=args.dry_run,
        no_autosave=args.no_autosave,
    )


if __name__ == "__main__":
    raise SystemExit(main())
