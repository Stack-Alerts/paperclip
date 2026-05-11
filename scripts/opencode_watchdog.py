#!/usr/bin/env python3
"""Watchdog for hanging opencode processes.

Detects opencode run processes that are alive but producing zero output
for longer than SILENT_THRESHOLD_SEC, and terminates them.

Detection layers:
  1. Low-CPU ghost: elapsed > SILENT_THRESHOLD_SEC AND cpu <= 0.5% AND (no output recently)
  2. Output-inactive ghost: elapsed > SILENT_THRESHOLD_SEC AND no stdout/stderr writes
     in the last OUTPUT_INACTIVE_WINDOW_SEC, regardless of CPU
  3. Absolute max-age: elapsed > MAX_ABSOLUTE_AGE_SEC, kill unconditionally (last resort)

Usage:
    python scripts/opencode_watchdog.py           # normal run (kills)
    python scripts/opencode_watchdog.py --dry-run  # report only, no kill
    python scripts/opencode_watchdog.py --verbose  # log all processes inspected
"""

import argparse
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SILENT_THRESHOLD_SEC = 1800  # 30 minutes
OUTPUT_INACTIVE_WINDOW_SEC = 600  # 10 minutes since last stdout/stderr write
DEFAULT_MAX_ABSOLUTE_AGE_SEC = 3600  # 60 minutes
WATCHDOG_LOG = Path.home() / ".paperclip" / "opencode_watchdog.log"
KILL_LOG = Path.home() / ".paperclip" / "opencode_watchdog_killed.log"

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
            capture_output=True, text=True, timeout=10,
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

            processes.append(OpenCodeProcess(
                pid=pid, ppid=ppid, elapsed_seconds=elapsed,
                cpu_percent=cpu, cmdline=cmdline,
                session_id=session_id, model=model,
            ))
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
        return ("absolute-max-age", {"cpu": proc.cpu_percent, "elapsed": proc.elapsed_seconds})

    if proc.elapsed_seconds < silent_threshold_sec:
        return ("too-young", {"elapsed": proc.elapsed_seconds})

    inactive_since = _get_output_inactive_since(proc.pid)
    output_inactive = (
        inactive_since is not None and inactive_since > OUTPUT_INACTIVE_WINDOW_SEC
    )

    if proc.cpu_percent <= 0.5:
        return ("low-cpu", {"cpu": proc.cpu_percent, "inactive_since": inactive_since})

    if output_inactive:
        return ("output-inactive",
                {"cpu": proc.cpu_percent, "inactive_since": inactive_since})

    return ("active", {"cpu": proc.cpu_percent, "inactive_since": inactive_since})


KILLABLE_REASONS = frozenset({"low-cpu", "output-inactive", "absolute-max-age"})


def kill_process_group(pid: int) -> bool:
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
            logger.warning("Process group %d still alive after SIGTERM, sending SIGKILL", pgid)
            os.killpg(pgid, signal.SIGKILL)
            time.sleep(1)
        except (OSError, ProcessLookupError):
            pass
        return True
    except (OSError, ProcessLookupError):
        return False


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
    logger.info("Killed opencode process: reason=%s pid=%d elapsed=%.0fs model=%s",
                reason, proc.pid, proc.elapsed_seconds, proc.model or "unknown")


def run(
    dry_run: bool = False,
    verbose: bool = False,
    silent_threshold_sec: int = DEFAULT_SILENT_THRESHOLD_SEC,
    max_absolute_age_sec: int = DEFAULT_MAX_ABSOLUTE_AGE_SEC,
):
    processes = get_opencode_processes()
    if verbose:
        logger.info("Found %d opencode run processes", len(processes))
        for p in processes:
            logger.info("  pid=%d elapsed=%.0fs cpu=%.1f%% model=%s",
                        p.pid, p.elapsed_seconds, p.cpu_percent,
                        p.model or "N/A")

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
                logger.info("  SKIP pid=%d reason=%s cpu=%.1f%% elapsed=%.0fs",
                            proc.pid, reason, proc.cpu_percent, proc.elapsed_seconds)
            continue

        would_kill += 1
        logger.warning(
            "Hanging opencode process: reason=%s pid=%d elapsed=%.0fs cpu=%.1f%% "
            "model=%s session=%s",
            reason, proc.pid, proc.elapsed_seconds, proc.cpu_percent,
            proc.model or "unknown", proc.session_id or "none",
        )

        if not dry_run:
            if kill_process_group(proc.pid):
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
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not kill")
    parser.add_argument("--verbose", action="store_true", help="Log all inspected processes")
    parser.add_argument("--threshold", type=int, default=DEFAULT_SILENT_THRESHOLD_SEC,
                        help=f"Silent threshold in seconds (default: {DEFAULT_SILENT_THRESHOLD_SEC})")
    parser.add_argument("--max-age", type=int, default=DEFAULT_MAX_ABSOLUTE_AGE_SEC,
                        help=f"Absolute max age in seconds (default: {DEFAULT_MAX_ABSOLUTE_AGE_SEC})")
    args = parser.parse_args()

    would_kill, actually_killed = run(
        dry_run=args.dry_run,
        verbose=args.verbose,
        silent_threshold_sec=args.threshold,
        max_absolute_age_sec=args.max_age,
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
