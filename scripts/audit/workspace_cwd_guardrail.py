#!/usr/bin/env python3
"""Workspace Confinement Phase 0 guardrail — assert git_repo workspace cwds == repo root.

Root cause this guards against (BTCAAAAA-38991 / BTCAAAAA-38994):
    Paperclip's heartbeat validator (server/src/services/heartbeat.ts ->
    hasGitMetadata(effectiveCwd)) requires a `.git` at the workspace cwd for
    sourceType `git_repo`. A workspace cwd pointed at a subfolder (e.g.
    packages/web-ui/app/strategy-builder/) has no `.git` there and fails
    `missing_git_metadata`. Confinement must NEVER be done by shrinking cwd to
    a subdirectory — that is done via the ownership manifest + guard (Phase 1).

What this script does:
    1. Enumerates every configured workspace across all projects.
    2. Flags any `git_repo` workspace whose `cwd` is a strict subdirectory of the
       repo root (the documented failure mode).
    3. Exits non-zero when any violation is found so CI / cron alarms.

A `git_repo` workspace with cwd == repo root, or cwd unset/null (which resolves to
the project's managed-checkout root that carries its own `.git`), is compliant.
`local_path` workspaces are not subject to the rule.

Usage:
    python scripts/audit/workspace_cwd_guardrail.py            # audit + alarm on violation
    python scripts/audit/workspace_cwd_guardrail.py --json     # machine-readable output
    REPO_ROOT=/some/repo python scripts/audit/workspace_cwd_guardrail.py

Env: PAPERCLIP_LISTEN_HOST/PORT or PAPERCLIP_API_URL, PAPERCLIP_API_KEY,
     PAPERCLIP_COMPANY_ID (same as the other Paperclip routines).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT_PATH = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT_PATH / "src"))

from touch_index.paperclip_client import _base, _company, _session  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("workspace_cwd_guardrail")

DEFAULT_REPO_ROOT = "/home/sirrus/projects/BTC-Trade-Engine-PaperClip"


def _norm(p: str | None) -> str | None:
    if not p:
        return None
    return p.rstrip("/")


def _is_subdirectory(cwd: str | None, root: str) -> bool:
    """True when cwd is a strict subdirectory of root (not root itself)."""
    c, r = _norm(cwd), _norm(root)
    if not c or not r:
        return False
    return c != r and c.startswith(r + "/")


def fetch_workspaces() -> list[dict]:
    """Return one row per configured workspace with project context."""
    with _session() as sess:
        resp = sess.get(f"{_base()}/api/companies/{_company()}/projects", timeout=30)
        resp.raise_for_status()
        projects = resp.json()
    rows: list[dict] = []
    for proj in projects:
        for ws in proj.get("workspaces") or []:
            rows.append(
                {
                    "project": proj.get("name"),
                    "projectArchived": bool(proj.get("archivedAt")),
                    "id": ws.get("id"),
                    "sourceType": ws.get("sourceType"),
                    "cwd": ws.get("cwd"),
                    "repoUrl": ws.get("repoUrl"),
                }
            )
    return rows


def audit(repo_root: str) -> tuple[list[dict], list[dict]]:
    rows = fetch_workspaces()
    violations = [
        r
        for r in rows
        if r["sourceType"] == "git_repo" and _is_subdirectory(r["cwd"], repo_root)
    ]
    return rows, violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=os.environ.get("REPO_ROOT", DEFAULT_REPO_ROOT))
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    rows, violations = audit(args.repo_root)

    if args.json:
        print(json.dumps({"repoRoot": args.repo_root, "workspaces": rows, "violations": violations}, indent=2))
    else:
        git_rows = [r for r in rows if r["sourceType"] == "git_repo"]
        logger.info("Repo root: %s", args.repo_root)
        logger.info(
            "Enumerated %d workspaces (%d git_repo, %d other).",
            len(rows),
            len(git_rows),
            len(rows) - len(git_rows),
        )
        for r in rows:
            flag = "  <== VIOLATION (git_repo cwd is a subdirectory)" if r in violations else ""
            logger.info("  [%s] %-32s cwd=%s%s", r["sourceType"], (r["project"] or "")[:32], r["cwd"], flag)

    if violations:
        logger.error(
            "GUARDRAIL FAILED: %d git_repo workspace(s) have a cwd pointed at a subdirectory. "
            "Confinement must use the ownership manifest + guard (Phase 1), never a shrunken cwd.",
            len(violations),
        )
        for v in violations:
            logger.error("  project=%s id=%s cwd=%s", v["project"], v["id"], v["cwd"])
        return 1

    logger.info("GUARDRAIL PASSED: no git_repo workspace cwd points at a subdirectory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
