#!/usr/bin/env python3
"""Nightly Paperclip alert for locked module status.

Generates a summary report of the lock gate system: locked module count,
active exceptions, expired/schema issues, and creates a Paperclip alert
issue if there are actionable items.

Only creates an alert when there are items needing attention (expired
exceptions, schema validation failures, upcoming expirations). Silent
exit 2 when everything is clean.

Usage:
    python scripts/lock_gate_nightly_alert.py [--dry-run]

Exit codes:
    0 — alert created successfully
    1 — error during generation
    2 — no issues to report (clean state, alert skipped)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / ".module_lock_registry.json"
EXCEPTIONS_PATH = REPO_ROOT / "lock_gate_exceptions.json"
DEP_GRAPH_PATH = REPO_ROOT / "dep_graph.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("lock_gate_nightly_alert")


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def parse_iso(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def build_alert_body(
    registry: dict,
    exceptions: list[dict],
    dep_graph: dict,
    schema_errors: list[str],
    expired: list[dict],
    expiring_soon: list[dict],
) -> str:
    now = datetime.now(timezone.utc)
    locked_entries = registry.get("entries", [])
    active_exceptions = [e for e in exceptions if e not in expired]

    lines = [
        "## Lock Gate Nightly Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "### Summary",
        "",
        f"- **Total locked modules:** {len(locked_entries)}",
        f"- **Active exceptions:** {len(active_exceptions)}",
        f"- **Expired exceptions:** {len(expired)}",
        f"- **Expiring within 24h:** {len(expiring_soon)}",
        "",
    ]

    if schema_errors:
        lines.append("### Schema Validation Errors")
        lines.append("")
        lines.append("The exceptions file has validation errors that must be fixed:")
        lines.append("")
        for err in schema_errors:
            lines.append(f"- {err}")
        lines.append("")

    if expired:
        lines.append("### Expired Exceptions")
        lines.append("")
        lines.append(
            "The following exceptions have expired and are no longer active. "
            "They should be reviewed and either removed or renewed:"
        )
        lines.append("")
        for entry in expired:
            module = entry.get("module", entry.get("path", "unknown"))
            expires = entry.get("expires_iso", "unknown")
            approved_by = entry.get("approved_by", "unknown")
            lines.append(f"- `{module}` — expired {expires} ({approved_by})")
        lines.append("")

    if expiring_soon:
        lines.append("### Exceptions Expiring Within 24h")
        lines.append("")
        lines.append(
            "The following exceptions will expire within the next 24 hours. "
            "Plan ahead if the changes are not yet complete:"
        )
        lines.append("")
        for entry in expiring_soon:
            module = entry.get("module", entry.get("path", "unknown"))
            expires = entry.get("expires_iso", "unknown")
            approved_by = entry.get("approved_by", "unknown")
            lines.append(f"- `{module}` — expires {expires} ({approved_by})")
        lines.append("")

    if active_exceptions:
        lines.append("### Active Exceptions")
        lines.append("")
        for entry in active_exceptions:
            module = entry.get("module", entry.get("path", "unknown"))
            scope = entry.get("scope_description", "")
            approved_by = entry.get("approved_by", "")
            expires = entry.get("expires_iso") or "permanent"
            lines.append(f"- `{module}` — {scope} ({approved_by}, expires: {expires})")
        lines.append("")

    lines.append("### Locked Modules")
    lines.append("")
    for entry in locked_entries:
        locked_at = entry.get("locked_at", "")
        lines.append(f"- `{entry['path']}` — locked {locked_at}")
    lines.append("")

    if dep_graph:
        dep_entries = dep_graph.get("direct", {})
        total_deps = sum(len(v) for v in dep_entries.values())
        lines.append("### Dependency Graph")
        lines.append("")
        lines.append(f"- **Total dependencies tracked:** {total_deps}")
        lines.append(f"- **Modules with deps:** {len(dep_entries)}")
        lines.append("")

    lines.append("---")
    lines.append("_This report is auto-generated by the nightly lock gate alert._")

    return "\n".join(lines)


def create_paperclip_alert(title: str, body: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("DRY RUN: would create alert issue '%s'", title)
        return True

    sys.path.insert(0, str(REPO_ROOT / "src"))
    try:
        from touch_index.paperclip_client import _session, _base, _company
    except ImportError:
        logger.error("Cannot import paperclip_client — is PAPERCLIP_API_KEY set?")
        return False

    try:
        sess = _session()
        resp = sess.post(
            f"{_base()}/api/companies/{_company()}/issues",
            json={
                "title": title,
                "body": body,
                "labels": ["lock-gate", "nightly-alert"],
                "status": "todo",
            },
            timeout=30,
        )
        resp.raise_for_status()
        created = resp.json()
        logger.info(
            "Created alert issue %s: %s",
            created.get("identifier", ""), title,
        )
        return True
    except Exception as exc:
        logger.error("Failed to create alert issue: %s", exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nightly Paperclip alert for locked module status",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Log actions without creating an issue")
    args = parser.parse_args()

    registry = load_json(REGISTRY_PATH)
    exceptions_data = load_json(EXCEPTIONS_PATH) if EXCEPTIONS_PATH.exists() else {"exceptions": []}
    dep_graph = load_json(DEP_GRAPH_PATH) if DEP_GRAPH_PATH.exists() else {}
    exceptions = exceptions_data.get("exceptions", [])

    now = datetime.now(timezone.utc)
    soon_cutoff = now + timedelta(hours=24)

    expired = []
    expiring_soon = []
    for entry in exceptions:
        expires_iso = entry.get("expires_iso")
        if expires_iso is None:
            continue
        parsed = parse_iso(expires_iso)
        if parsed is None:
            expired.append(entry)
        elif parsed <= now:
            expired.append(entry)
        elif parsed <= soon_cutoff:
            expiring_soon.append(entry)

    schema_errors = []
    try:
        from scripts.lock_gate import validate_exceptions_file
        schema_errors = validate_exceptions_file(exceptions_data)
    except ImportError:
        pass

    date_str = now.strftime("%Y-%m-%d")

    if not expired and not expiring_soon and not schema_errors:
        logger.info(
            "Lock gate state is clean: no expired exceptions, "
            "no expiring exceptions, no schema errors. Skipping alert."
        )
        sys.exit(2)

    title = f"Lock Gate Alert — {date_str}"

    body = build_alert_body(
        registry, exceptions, dep_graph,
        schema_errors, expired, expiring_soon,
    )

    if not create_paperclip_alert(title, body, args.dry_run):
        logger.error("Failed to create alert issue")
        sys.exit(1)

    logger.info("Nightly alert created successfully")


if __name__ == "__main__":
    main()
