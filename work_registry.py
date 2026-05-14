#!/usr/bin/env python3
"""Work Registry — agent coordination via per-component lock files.

Storage layout::

    .work-registry/
      locks/
        src-services-trading.json
        ...

Each lock file is a single JSON object:

.. code-block:: json

    {
      "component": "src/services/trading/",
      "agent": "NautilusEngineer",
      "agent_id": "a472d315-...",
      "claimed_at": "2026-05-14T08:30:00Z",
      "expires_at": "2026-05-14T10:30:00Z",
      "reason": "Fixing order validation bug"
    }

Usage
-----
    work-registry claim <component> [--reason "..."] [--ttl 2h]
    work-registry release <component>
    work-registry check <component>
    work-registry list [--agent <name>]
    work-registry cleanup
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REGISTRY_DIR = Path(".work-registry")
_LOCKS_DIR = _REGISTRY_DIR / "locks"

_UNSAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_.-]")


def _component_to_filename(component: str) -> str:
    sanitized = _UNSAFE_FILENAME_RE.sub("-", component)
    sanitized = sanitized.strip("-")
    if not sanitized:
        return "root"
    return sanitized + ".json"


def _lock_path(component: str) -> Path:
    return _LOCKS_DIR / _component_to_filename(component)


def _load_lock(component: str) -> dict | None:
    path = _lock_path(component)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return data


def _is_expired(lock_data: dict) -> bool:
    expires_str = lock_data.get("expires_at", "")
    if not expires_str:
        return False
    try:
        expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
    except ValueError:
        return False
    return datetime.now(timezone.utc) > expires


def _agent_id() -> str:
    return os.environ.get("PAPERCLIP_AGENT_ID", "unknown")


def _agent_name() -> str:
    return os.environ.get("PAPERCLIP_AGENT_NAME", os.environ.get("USER", "unknown"))


def _parse_ttl(ttl_str: str) -> timedelta:
    ttl_str = ttl_str.strip()
    if not ttl_str:
        return timedelta(hours=2)

    match = re.match(r"^(\d+)\s*(s|m|h|d)$", ttl_str, re.IGNORECASE)
    if not match:
        sys.stderr.write(f"Invalid TTL format: {ttl_str!r}. Use e.g. 30m, 2h, 1d.\n")
        sys.exit(2)

    value = int(match.group(1))
    unit = match.group(2).lower()

    if unit == "s":
        return timedelta(seconds=value)
    elif unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    return timedelta(hours=2)


def cmd_claim(args: argparse.Namespace) -> int:
    _LOCKS_DIR.mkdir(parents=True, exist_ok=True)

    agent_id = _agent_id()
    agent_name = _agent_name()
    component = args.component

    existing = _load_lock(component)

    if existing is not None and not _is_expired(existing):
        existing_agent_id = existing.get("agent_id", "")
        if existing_agent_id == agent_id:
            ttl = _parse_ttl(args.ttl)
            now = datetime.now(timezone.utc)
            existing["claimed_at"] = now.isoformat().replace("+00:00", "Z")
            existing["expires_at"] = (now + ttl).isoformat().replace("+00:00", "Z")
            if args.reason:
                existing["reason"] = args.reason
            _lock_path(component).write_text(json.dumps(existing, indent=2) + "\n")
            sys.stdout.write(f"Claim refreshed: {component} (agent: {agent_name})\n")
            return 0

        existing_agent = existing.get("agent", "unknown")
        sys.stderr.write(
            f"LOCKED: {component} is already claimed by {existing_agent} "
            f"(expires {existing.get('expires_at', 'unknown')})\n"
        )
        return 1

    ttl = _parse_ttl(args.ttl)
    now = datetime.now(timezone.utc)
    lock_data = {
        "component": component,
        "agent": agent_name,
        "agent_id": agent_id,
        "claimed_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + ttl).isoformat().replace("+00:00", "Z"),
        "reason": args.reason or "",
    }

    _lock_path(component).write_text(json.dumps(lock_data, indent=2) + "\n")
    sys.stdout.write(f"Claimed: {component} (agent: {agent_name}, TTL: {args.ttl})\n")
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    agent_id = _agent_id()
    agent_name = _agent_name()
    component = args.component

    existing = _load_lock(component)

    if existing is None:
        sys.stderr.write(f"NOT FOUND: no lock exists for {component}\n")
        return 1

    if _is_expired(existing):
        _lock_path(component).unlink(missing_ok=True)
        sys.stdout.write(f"Removed expired lock for {component}\n")
        return 0

    existing_agent_id = existing.get("agent_id", "")
    if existing_agent_id != agent_id:
        existing_agent = existing.get("agent", "unknown")
        sys.stderr.write(
            f"DENIED: {component} is held by {existing_agent}, not {agent_name}\n"
        )
        return 1

    _lock_path(component).unlink(missing_ok=True)
    sys.stdout.write(f"Released: {component} (agent: {agent_name})\n")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    component = args.component
    existing = _load_lock(component)

    if existing is None or _is_expired(existing):
        sys.stdout.write(f"FREE: {component}\n")
        return 0

    agent = existing.get("agent", "unknown")
    expires = existing.get("expires_at", "unknown")
    reason = existing.get("reason", "")
    reason_str = f" — {reason}" if reason else ""
    sys.stdout.write(f"LOCKED by {agent} (expires {expires}){reason_str}\n")
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    if not _LOCKS_DIR.exists():
        sys.stdout.write("No active locks.\n")
        return 0

    filter_agent = args.agent
    found = 0

    for lock_file in sorted(_LOCKS_DIR.iterdir()):
        if not lock_file.suffix == ".json":
            continue
        try:
            data = json.loads(lock_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        if _is_expired(data):
            continue

        component = data.get("component", lock_file.stem)
        agent = data.get("agent", "unknown")
        expires = data.get("expires_at", "unknown")

        if filter_agent and filter_agent.lower() not in agent.lower():
            continue

        reason = data.get("reason", "")
        reason_str = f" ({reason})" if reason else ""
        sys.stdout.write(f"{component:40s}  {agent:20s}  expires {expires}{reason_str}\n")
        found += 1

    if found == 0:
        if filter_agent:
            sys.stdout.write(f"No active locks for agent matching '{filter_agent}'.\n")
        else:
            sys.stdout.write("No active locks.\n")
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    if not _LOCKS_DIR.exists():
        sys.stdout.write("Nothing to clean up.\n")
        return 0

    removed = 0
    for lock_file in sorted(_LOCKS_DIR.iterdir()):
        if not lock_file.suffix == ".json":
            continue
        try:
            data = json.loads(lock_file.read_text())
        except (json.JSONDecodeError, OSError):
            lock_file.unlink(missing_ok=True)
            removed += 1
            continue

        if _is_expired(data):
            lock_file.unlink(missing_ok=True)
            removed += 1

    sys.stdout.write(f"Cleaned up {removed} expired lock(s).\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="work-registry",
        description="Agent work coordination via per-component lock files.",
    )
    sub = parser.add_subparsers(dest="command")

    p_claim = sub.add_parser("claim", help="Claim a component for work")
    p_claim.add_argument("component", help="Component path (e.g. src/services/trading/)")
    p_claim.add_argument("--reason", default="", help="Why this component is claimed")
    p_claim.add_argument("--ttl", default="2h", help="Time-to-live (e.g. 30m, 2h, 1d)")
    p_claim.set_defaults(func=cmd_claim)

    p_release = sub.add_parser("release", help="Release a claimed component")
    p_release.add_argument("component", help="Component path to release")
    p_release.set_defaults(func=cmd_release)

    p_check = sub.add_parser("check", help="Check lock status of a component")
    p_check.add_argument("component", help="Component path to check")
    p_check.set_defaults(func=cmd_check)

    p_list = sub.add_parser("list", help="List all active (non-expired) locks")
    p_list.add_argument("--agent", help="Filter locks by agent name")
    p_list.set_defaults(func=cmd_list)

    p_cleanup = sub.add_parser("cleanup", help="Remove all expired lock files")
    p_cleanup.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
