#!/usr/bin/env python3
"""Watchdog for hanging opencode processes.

Detects opencode run processes that are alive but producing zero output
for longer than SILENT_THRESHOLD_SEC, attempts a session-end autosave
of any protected-branch working tree the process owns, then terminates
them.

Detection layers:
  1. Low-CPU ghost: elapsed > SILENT_THRESHOLD_SEC AND cpu <= 0.5% AND (no output recently)
  2. Output-inactive ghost: elapsed > SILENT_THRESHOLD_SEC AND no stdout/stderr writes
     in the last OUTPUT_INACTIVE_WINDOW_SEC, regardless of CPU
  3. Absolute max-age: elapsed > MAX_ABSOLUTE_AGE_SEC, kill unconditionally (last resort)

Pre-kill autosave hook:
  Before SIGTERM, invoke scripts/session_end_autosave.py against the
  process's resolved cwd (read from /proc/<pid>/cwd) so that any
  fix/BTCAAAAA-* or feat/BTCAAAAA-* worktree is auto-snapshotted to
  origin. Snapshot failures NEVER block the kill — the watchdog's
  primary responsibility is to reap zombies.

Usage:
    python scripts/opencode_watchdog.py                # normal run (kills)
    python scripts/opencode_watchdog.py --dry-run       # report only, no kill
    python scripts/opencode_watchdog.py --verbose       # log all processes inspected
    python scripts/opencode_watchdog.py --no-autosave   # skip the pre-kill snapshot
"""

import argparse
import logging
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SILENT_THRESHOLD_SEC = 1800  # 30 minutes
OUTPUT_INACTIVE_WINDOW_SEC = 600  # 10 minutes since last stdout/stderr write
DEFAULT_MAX_ABSOLUTE_AGE_SEC = 3600  # 60 minutes
WATCHDOG_LOG = Path.home() / ".paperclip" / "opencode_watchdog.log"
KILL_LOG = Path.home() / ".paperclip" / "opencode_watchdog_killed.log"
AUTOSAVE_LOG = Path(".paperclip") / "autosave.log"

# Pre-kill autosave: snapshot script lives next to this watchdog in scripts/.
AUTOSAVE_SCRIPT = Path(__file__).resolve().parent / "session_end_autosave.py"
AUTOSAVE_TIMEOUT_SEC = (
    40  # 30s subprocess cap inside the script + 5s index-lock wait + slack
)
PROTECTED_BRANCH_PREFIXES = ("fix/BTCAAAAA-", "feat/BTCAAAAA-")
ISSUE_ID_RE = re.compile(r"BTCAAAAA-\d+")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(WATCHDOG_LOG),
        logging.StreamHandler() if os.isatty(0) else logging.NullHandler(),
    ],
)
logger = logging.getLogger("opencode_watchdog")


@dataclass
class OpenCodeProcess:
    pid: int
    ppid: int
    elapsed_seconds: float
    cpu_percent: float
    cmdline: str
    session_id: str | None = None
    model: str | None = None


def parse_elapsed(elapsed_str: str) -> float:
    parts = elapsed_str.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def get_opencode_processes() -> list[OpenCodeProcess]:
    try:
        result = subprocess.run(
            ["ps", "axo", "pid,ppid,etime,%cpu,args", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error("ps command failed: %s", e)
        return []

    processes = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or "opencode run" not in line:
            continue
        if "opencode_watchdog" in line or "grep" in line:
            continue
        try:
            parts = line.split(None, 4)
            pid = int(parts[0])
            ppid = int(parts[1])
            elapsed_str = parts[2]
            cpu = float(parts[3])
            cmdline = parts[4] if len(parts) > 4 else ""

            elapsed = parse_elapsed(elapsed_str)
            if elapsed < 60:
                continue

            session_id = None
            model = None
            args_list = cmdline.split()
            for i, arg in enumerate(args_list):
                if arg == "--session" and i + 1 < len(args_list):
                    session_id = args_list[i + 1]
                if arg == "--model" and i + 1 < len(args_list):
                    model = args_list[i + 1]

            processes.append(
                OpenCodeProcess(
                    pid=pid,
                    ppid=ppid,
                    elapsed_seconds=elapsed,
                    cpu_percent=cpu,
                    cmdline=cmdline,
                    session_id=session_id,
                    model=model,
                )
            )
        except (ValueError, IndexError):
            continue
    return processes


def _get_process_state(pid: int) -> str | None:
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("State:"):
                    return line.split(":", 1)[1].strip()
    except (OSError, FileNotFoundError, PermissionError):
        return None
    return None


def _get_output_inactive_since(pid: int) -> float | None:
    """Return seconds since last write to stdout or stderr, or None if unknown."""
    now = time.time()
    last_write = None
    for fd_name in ["1", "2"]:
        fd_path = f"/proc/{pid}/fd/{fd_name}"
        try:
            st = os.stat(fd_path)
            mtime = getattr(st, "st_mtime", None) or st.st_mtime
            if last_write is None or mtime > last_write:
                last_write = mtime
        except (OSError, FileNotFoundError, PermissionError):
            continue
    if last_write is None:
        return None
    return now - last_write


def classify_process(
    proc: OpenCodeProcess,
    silent_threshold_sec: int = DEFAULT_SILENT_THRESHOLD_SEC,
    max_absolute_age_sec: int = DEFAULT_MAX_ABSOLUTE_AGE_SEC,
) -> tuple[str, dict]:
    """Classify a process's status, returning (reason_key, metadata).

    Reason keys:
      - "absolute-max-age": unconditional kill, process too old
      - "low-cpu": low CPU usage for extended period
      - "output-inactive": no output writes recently despite CPU usage
      - "zombie": defunct process
      - "too-young": not old enough to evaluate
      - "active": appears to be doing work
    """
    state = _get_process_state(proc.pid)
    if state and "Z" in state:
        return ("zombie", {"state": state})

    if proc.elapsed_seconds >= max_absolute_age_sec:
        return (
            "absolute-max-age",
            {"cpu": proc.cpu_percent, "elapsed": proc.elapsed_seconds},
        )

    if proc.elapsed_seconds < silent_threshold_sec:
        return ("too-young", {"elapsed": proc.elapsed_seconds})

    inactive_since = _get_output_inactive_since(proc.pid)
    output_inactive = (
        inactive_since is not None and inactive_since > OUTPUT_INACTIVE_WINDOW_SEC
    )

    if proc.cpu_percent <= 0.5:
        return ("low-cpu", {"cpu": proc.cpu_percent, "inactive_since": inactive_since})

    if output_inactive:
        return (
            "output-inactive",
            {"cpu": proc.cpu_percent, "inactive_since": inactive_since},
        )

    return ("active", {"cpu": proc.cpu_percent, "inactive_since": inactive_since})


KILLABLE_REASONS = frozenset({"low-cpu", "output-inactive", "absolute-max-age"})


def _resolve_cwd(pid: int) -> Path | None:
    """Return the absolute cwd of a process, or None if unreadable.

    /proc/<pid>/cwd is a symlink owned by the process's user; the
    watchdog runs as the same user as the opencode process (typically),
    but we still defensively handle PermissionError.
    """
    try:
        target = os.readlink(f"/proc/{pid}/cwd")
        return Path(target).resolve()
    except (OSError, FileNotFoundError, PermissionError):
        return None


def _resolve_repo(start: Path) -> Path | None:
    cur = start
    for candidate in (cur, *cur.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _git(repo: Path, *args: str, timeout: int = 10) -> tuple[int, str, str]:
    """Run a git command in `repo`, returning (returncode, stdout, stderr)."""
    res = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return res.returncode, (res.stdout or "").strip(), (res.stderr or "").strip()


def _current_branch_and_sha(repo: Path) -> tuple[str | None, str | None]:
    rc, branch, _ = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if rc != 0 or not branch or branch == "HEAD":
        branch = None
    sha_rc, sha, _ = _git(repo, "rev-parse", "--verify", "HEAD")
    sha = sha if sha_rc == 0 and sha else None
    return branch, sha


def _is_protected_branch(branch: str | None) -> bool:
    if not branch:
        return False
    return any(branch.startswith(prefix) for prefix in PROTECTED_BRANCH_PREFIXES)


def _extract_issue_id(branch: str | None) -> str | None:
    if not branch:
        return None
    m = ISSUE_ID_RE.search(branch)
    return m.group(0) if m else None


def _make_run_id(proc: OpenCodeProcess) -> str:
    """Build a deterministic run-id for the autosave commit subject.

    Prefer the opencode session id (audit-traceable) when present, else
    fall back to a pid-tagged label so the snapshot is attributable.
    """
    if proc.session_id:
        return f"watchdog-{proc.session_id}"
    return f"watchdog-pid-{proc.pid}"


def _autosave_pre_kill(proc: OpenCodeProcess, no_autosave: bool) -> int:
    """Invoke scripts/session_end_autosave.py against the process's cwd.

    Best-effort: never raises. Returns the autosave script's exit code
    (0/2/3/4) on success, or -1 if the snapshot could not be attempted.
    A failure here MUST NOT block the kill — log and move on.
    """
    if no_autosave or os.environ.get("PAPERCLIP_NO_AUTOSAVE") == "1":
        logger.info("[autosave] skipped (opt-out) pid=%d", proc.pid)
        return 3

    if not AUTOSAVE_SCRIPT.exists():
        logger.warning(
            "[autosave] script not found at %s — skipping snapshot pid=%d",
            AUTOSAVE_SCRIPT,
            proc.pid,
        )
        return -1

    cwd = _resolve_cwd(proc.pid)
    if cwd is None:
        logger.warning("[autosave] could not read /proc/%d/cwd — skipping", proc.pid)
        return -1

    repo = _resolve_repo(cwd)
    if repo is None:
        logger.info(
            "[autosave] no git repo reachable from %s — skipping pid=%d", cwd, proc.pid
        )
        return 4

    branch, sha = _current_branch_and_sha(repo)
    if not _is_protected_branch(branch):
        logger.info(
            "[autosave] branch=%s is not protected — skipping snapshot pid=%d",
            branch or "<detached>",
            proc.pid,
        )
        return 0

    issue_id = _extract_issue_id(branch)
    run_id = _make_run_id(proc)

    AUTOSAVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    logger.info(
        "[autosave] snapshot attempted for pid=%d branch=%s sha=%s issue=%s run_id=%s",
        proc.pid,
        branch,
        sha or "<none>",
        issue_id or "<none>",
        run_id,
    )

    cmd = [
        sys.executable,
        str(AUTOSAVE_SCRIPT),
        "--cwd",
        str(repo),
        "--run-id",
        run_id,
    ]
    if issue_id:
        cmd.extend(["--issue-id", issue_id])

    try:
        res = subprocess.run(
            cmd,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=AUTOSAVE_TIMEOUT_SEC,
            check=False,
        )
        if res.returncode == 0:
            logger.info("[autosave] snapshot committed pid=%d rc=0", proc.pid)
        else:
            logger.warning(
                "[autosave] snapshot non-zero exit pid=%d rc=%d stderr=%s",
                proc.pid,
                res.returncode,
                (res.stderr or "").strip()[:200],
            )
        return res.returncode
    except subprocess.TimeoutExpired:
        logger.error(
            "[autosave] snapshot timed out after %ds pid=%d — proceeding with kill",
            AUTOSAVE_TIMEOUT_SEC,
            proc.pid,
        )
        return -1
    except Exception as exc:
        logger.error(
            "[autosave] snapshot crashed pid=%d err=%s — proceeding with kill",
            proc.pid,
            exc,
        )
        return -1


def kill_process_group(pid: int, no_autosave: bool = False) -> bool:
    """Send SIGTERM (then SIGKILL fallback) to the process group.

    `kill_process_group_with_snapshot` is the outer entry that invokes
    the autosave hook BEFORE calling this; snapshot failures never reach
    here — they are absorbed by the caller.
    """
    pgid = pid
    try:
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().split()
            if len(parts) > 4:
                pgid = int(parts[4])
    except (OSError, ValueError, IndexError):
        pass

    try:
        os.killpg(pgid, signal.SIGTERM)
        time.sleep(2)
        try:
            os.killpg(pgid, 0)
            logger.warning(
                "Process group %d still alive after SIGTERM, sending SIGKILL", pgid
            )
            os.killpg(pgid, signal.SIGKILL)
            time.sleep(1)
        except (OSError, ProcessLookupError):
            pass
        return True
    except (OSError, ProcessLookupError):
        return False


def kill_process_group_with_snapshot(proc: OpenCodeProcess, no_autosave: bool) -> bool:
    """Wrapper that runs the autosave hook then delegates to kill_process_group.

    The pre-kill snapshot is best-effort — it never blocks the kill.
    """
    _autosave_pre_kill(proc, no_autosave)
    return kill_process_group(proc.pid, no_autosave=no_autosave)


def log_kill(proc: OpenCodeProcess, reason: str, metadata: dict | None = None):
    meta_str = ""
    if metadata:
        meta_str = " " + " ".join(f"{k}={v}" for k, v in metadata.items())
    entry = (
        f"{datetime.now(timezone.utc).isoformat()} "
        f"KILLED reason={reason} pid={proc.pid} ppid={proc.ppid} "
        f"elapsed={proc.elapsed_seconds:.0f}s cpu={proc.cpu_percent:.1f}% "
        f"session={proc.session_id or 'N/A'} model={proc.model or 'N/A'}"
        f"{meta_str}\n"
    )
    with open(KILL_LOG, "a") as f:
        f.write(entry)
    logger.info(
        "Killed opencode process: reason=%s pid=%d elapsed=%.0fs model=%s",
        reason,
        proc.pid,
        proc.elapsed_seconds,
        proc.model or "unknown",
    )


def run(
    dry_run: bool = False,
    verbose: bool = False,
    silent_threshold_sec: int = DEFAULT_SILENT_THRESHOLD_SEC,
    max_absolute_age_sec: int = DEFAULT_MAX_ABSOLUTE_AGE_SEC,
    no_autosave: bool = False,
):
    processes = get_opencode_processes()
    if verbose:
        logger.info("Found %d opencode run processes", len(processes))
        for p in processes:
            logger.info(
                "  pid=%d elapsed=%.0fs cpu=%.1f%% model=%s",
                p.pid,
                p.elapsed_seconds,
                p.cpu_percent,
                p.model or "N/A",
            )

    would_kill = 0
    actually_killed = 0
    for proc in processes:
        reason, metadata = classify_process(
            proc,
            silent_threshold_sec=silent_threshold_sec,
            max_absolute_age_sec=max_absolute_age_sec,
        )

        if reason not in KILLABLE_REASONS:
            if verbose and reason == "active":
                logger.info(
                    "  SKIP pid=%d reason=%s cpu=%.1f%% elapsed=%.0fs",
                    proc.pid,
                    reason,
                    proc.cpu_percent,
                    proc.elapsed_seconds,
                )
            continue

        would_kill += 1
        logger.warning(
            "Hanging opencode process: reason=%s pid=%d elapsed=%.0fs cpu=%.1f%% "
            "model=%s session=%s",
            reason,
            proc.pid,
            proc.elapsed_seconds,
            proc.cpu_percent,
            proc.model or "unknown",
            proc.session_id or "none",
        )

        if not dry_run:
            if kill_process_group_with_snapshot(proc, no_autosave):
                log_kill(proc, reason, metadata)
                actually_killed += 1
            else:
                logger.error("Failed to kill pid=%d", proc.pid)

    return would_kill, actually_killed


def clear_old_logs(max_age_days: int = 7):
    for log_path in [WATCHDOG_LOG, KILL_LOG]:
        if log_path.exists():
            age = time.time() - log_path.stat().st_mtime
            if age > max_age_days * 86400:
                log_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="OpenCode hanging process watchdog")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report only, do not kill"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Log all inspected processes"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_SILENT_THRESHOLD_SEC,
        help=f"Silent threshold in seconds (default: {DEFAULT_SILENT_THRESHOLD_SEC})",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=DEFAULT_MAX_ABSOLUTE_AGE_SEC,
        help=f"Absolute max age in seconds (default: {DEFAULT_MAX_ABSOLUTE_AGE_SEC})",
    )
    parser.add_argument(
        "--no-autosave",
        action="store_true",
        help="Skip the pre-kill autosave snapshot (also honors "
        "PAPERCLIP_NO_AUTOSAVE=1)",
    )
    args = parser.parse_args()

    would_kill, actually_killed = run(
        dry_run=args.dry_run,
        verbose=args.verbose,
        silent_threshold_sec=args.threshold,
        max_absolute_age_sec=args.max_age,
        no_autosave=args.no_autosave,
    )
    clear_old_logs()

    if args.dry_run:
        logger.info("Dry-run: %d processes would be killed", would_kill)
    else:
        logger.info("Watchdog complete: %d processes killed", actually_killed)

    if actually_killed > 0 or would_kill > 0:
        logger.warning("Killed %d hanging opencode process(es)", actually_killed)

    return 1 if actually_killed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
