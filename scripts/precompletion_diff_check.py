"""Pre-completion diff-check warning routine (BTCAAAAA-39070).

Cron-triggered sibling of ``scripts/closure_gate_routine.py``: every 15 minutes
the harness scans ``in_progress`` issues with an assignee, locates each
assignee's workspace cwd, and posts a ``Pre-Completion Diff Warning`` comment
when the working tree has uncommitted changes that will be lost when the
session ends. The marker is line-anchored so subsequent cycles can detect prior
warnings via comment content rather than relying solely on a state file (the
state file is wiped if the runner's ``data/`` directory is lost).

Suppression rules — short-circuit and skip the warning when ANY applies:

1. The state file records a warning within the last 60 minutes.
2. The thread already contains a comment carrying the
   ``Pre-Completion Diff Warning`` marker (state-file-wipe resilience).
3. ``executionLockedAt`` is within the last 10 minutes (the agent is
   actively checked out — let it work).
4. The workspace is missing or is not a ``git_repo`` workspace (no cwd to
   diff). Subdirectory workspaces are not diffed per the section-confinement
   guidance in the BTC board memory.

The script is read-only with respect to the repository and writes only:

* ``data/precompletion_warnings.json`` — local state, atomic write via tmp
  + ``os.replace``.
* one comment per warned issue, posted via ``POST /api/issues/{id}/comments``.

It deliberately does **not** PATCH the issue or run any destructive git
operation. The agent that owns the issue pushes its fix branch on its own.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from _merge_dispatch_branch_parser import has_precompletion_marker  # noqa: E402
from touch_index.paperclip_client import (  # noqa: E402
    _base,
    _company,
    _session,
    fetch_issue_comments,
    list_issues,
)

LOG = logging.getLogger("precompletion_diff_check")

# Suppression windows — tuned for the 15-minute cron cadence so a single
# warning lands per warn-cycle per issue.
ACTIVE_CHECKOUT_WINDOW_MINUTES = 10
WARNING_COOLDOWN_MINUTES = 60

# Per-issue subprocess timeout for ``git diff --stat HEAD``.
GIT_DIFF_TIMEOUT_SECONDS = 10

# Cron-level hard timeout — guards against a runaway loop on a wedged API or
# a `git diff` that hangs on a slow worktree fs.  20 minutes leaves headroom
# over the 15-minute cadence so the next cycle can still queue.
GLOBAL_TIMEOUT_SECONDS = 20 * 60

# State file location — mirrors the layout used by
# ``scripts/closure_gate_routine.py``.
STATE_DIR = REPO_ROOT / "data"
STATE_FILE = STATE_DIR / "precompletion_warnings.json"


# ---------------------------------------------------------------------------
# HTTP + state plumbing
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(raw: str | None):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_state() -> dict[str, str]:
    """Load ``data/precompletion_warnings.json`` (empty dict on missing)."""
    if not STATE_FILE.exists():
        return {}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            LOG.warning("state file %s not a dict — ignoring", STATE_FILE)
            return {}
        # Defensive: drop entries that aren't ``str`` ISO timestamps so a
        # corrupt value can't poison the cooldown check.
        return {k: v for k, v in data.items() if isinstance(v, str)}
    except (json.JSONDecodeError, OSError) as exc:
        LOG.warning("could not load %s: %s — starting empty", STATE_FILE, exc)
        return {}


def save_state(state: dict[str, str]) -> None:
    """Atomic write of ``data/precompletion_warnings.json``.

    Writes via a sibling tmp file then ``os.replace`` so a crashed cron
    does not leave a half-written file behind.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, STATE_FILE)


def _install_global_timeout(seconds: int) -> None:
    """SIGALRM-based hard cutoff (Unix). Mirrors ``closure_gate_routine.py``.

    On Windows or when the main thread is unavailable, this is a no-op so the
    script remains portable for unit tests run on a developer laptop.
    """
    if sys.platform == "win32":
        return
    def _on_timeout(signum, frame):  # pragma: no cover - signal handler
        raise TimeoutError(
            f"precompletion_diff_check exceeded {seconds}s global timeout"
        )
    signal.signal(signal.SIGALRM, _on_timeout)
    signal.alarm(seconds)


# ---------------------------------------------------------------------------
# Workspace + issue fetchers
# ---------------------------------------------------------------------------


def _load_workspace_map() -> dict[str, dict[str, Any]]:
    """Build ``{workspace_id: {cwd, sourceType}}`` from /api/companies/{cid}/projects.

    Each project carries a top-level ``workspaces[]`` array (per the BTC
    board memory's confirmed-by-audit shape from BTCAAAAA-38994 / PR #357).
    There is no direct ``/api/workspaces/{id}`` endpoint — every lookup
    has to go through the project's workspaces list.

    The map is cached for the lifetime of one cron run; agents do not add
    new workspaces mid-cycle.
    """
    workspace_map: dict[str, dict[str, Any]] = {}
    try:
        with _session() as sess:
            resp = sess.get(
                f"{_base()}/api/companies/{_company()}/projects",
                timeout=30,
            )
            resp.raise_for_status()
            projects = resp.json()
    except Exception as exc:
        LOG.warning("workspace map fetch failed: %s", exc)
        return workspace_map

    for project in projects or []:
        for workspace in (project or {}).get("workspaces") or []:
            ws_id = workspace.get("id")
            if not ws_id:
                continue
            workspace_map[ws_id] = {
                "cwd": workspace.get("cwd"),
                "sourceType": workspace.get("sourceType"),
                "name": workspace.get("name"),
            }
    return workspace_map


def _list_in_progress_with_assignee() -> list[dict]:
    """Paginate ``list_issues(status='in_progress')`` until exhausted.

    Skips rows missing ``assigneeAgentId`` — a checkpointed issue with no
    current assignee is not actionable for this routine (the cron cannot
    tell which agent to nudge).
    """
    results: list[dict] = []
    offset = 0
    page_size = 200
    while True:
        try:
            page = list_issues(status="in_progress", limit=page_size, offset=offset)
        except Exception as exc:
            LOG.warning(
                "list_issues offset=%d failed: %s — returning partial list",
                offset,
                exc,
            )
            return results
        if not page:
            break
        for issue in page:
            if issue.get("assigneeAgentId") and issue.get("executionWorkspaceId"):
                results.append(issue)
        if len(page) < page_size:
            break
        offset += page_size
    return results


# ---------------------------------------------------------------------------
# Per-issue gates
# ---------------------------------------------------------------------------


def _is_recent_warning(state: dict[str, str], issue_id: str) -> bool:
    """True iff the state file records a warning for ``issue_id`` within cooldown."""
    last = _parse_iso(state.get(issue_id))
    if last is None:
        return False
    elapsed = datetime.now(timezone.utc) - last
    return elapsed.total_seconds() < WARNING_COOLDOWN_MINUTES * 60


def _is_fresh_checkout(issue: dict) -> bool:
    """True iff ``executionLockedAt`` is within the active-heartbeat window."""
    last = _parse_iso(issue.get("executionLockedAt"))
    if last is None:
        # No lock record — treat as inactive checkout (cron should warn).
        return False
    elapsed = datetime.now(timezone.utc) - last
    return elapsed.total_seconds() < ACTIVE_CHECKOUT_WINDOW_MINUTES * 60


def _has_marker_in_thread(issue_id: str) -> bool:
    """True iff any comment on the issue carries the pre-completion marker.

    Provides resilience to a wiped ``data/`` directory: even when the
    state file says nothing, an already-warned issue is still detected by
    scanning the comment thread.
    """
    try:
        comments = fetch_issue_comments(issue_id)
    except Exception as exc:
        # If we cannot reach the comments endpoint, fall through and let
        # the caller post — better to double-warn than to silently miss a
        # real dirty tree.
        LOG.debug("fetch_issue_comments(%s) failed: %s", issue_id, exc)
        return False
    return any(has_precompletion_marker(c.get("body")) for c in comments or [])


def _workspace_has_uncommitted_changes(cwd: str) -> bool:
    """Run ``git diff --stat HEAD`` in ``cwd``; True iff output is non-empty.

    Wrapped in ``subprocess.run`` with an explicit timeout so a hung
    worktree fs cannot wedge the cron. Exits also false on any error
    (not a git repo, missing head ref) — we never want a false positive
    that costs the agent an unneeded nag.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=GIT_DIFF_TIMEOUT_SECONDS,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        LOG.debug("git diff failed in %s: %s", cwd, exc)
        return False
    if proc.returncode != 0:
        LOG.debug(
            "git diff in %s returned %s: %s",
            cwd,
            proc.returncode,
            (proc.stderr or "").strip()[:200],
        )
        return False
    return bool((proc.stdout or "").strip())


# ---------------------------------------------------------------------------
# Warning post + comment body
# ---------------------------------------------------------------------------


def _format_warning_body(fix_branch: str | None) -> str:
    """Build the warning comment body with the line-anchored marker.

    The first non-blank line MUST start with the marker so
    ``has_precompletion_marker`` matches on subsequent cycles.
    """
    branch_hint = (fix_branch or "").strip() or "your fix branch"
    return (
        "## Pre-Completion Diff Warning\n"
        "\n"
        f"Working tree in this issue's workspace has uncommitted changes "
        f"that will be lost when the session ends. Push to `{branch_hint}` "
        "(or whatever fix branch you are working on) before exiting the "
        "heartbeat so the work survives.\n"
        "\n"
        "_This is an automated warning from the pre-completion diff-check "
        "cron (BTCAAAAA-39070). It fires at most once per 60 minutes per "
        "issue; push your changes and the next cycle will not re-warn._\n"
    )


def post_precompletion_warning(
    issue_id: str,
    body: str,
    *,
    run_id: str | None = None,
) -> bool:
    """POST ``body`` as a new comment on ``issue_id``.

    Returns True on success, False on a non-2xx response (logged). Run-id
    header is included when available so the post is traceable to the cron
    run for the same audit-trail reasons agent actions carry the header.
    """
    headers = {"Content-Type": "application/json"}
    if run_id:
        headers["X-Paperclip-Run-Id"] = run_id
    try:
        with _session() as sess:
            resp = sess.post(
                f"{_base()}/api/issues/{issue_id}/comments",
                json={"body": body},
                headers=headers,
                timeout=30,
            )
    except Exception as exc:
        LOG.warning("post_comment(%s) failed: %s", issue_id, exc)
        return False
    if not resp.ok:
        LOG.warning(
            "post_comment(%s) returned %s: %s",
            issue_id,
            resp.status_code,
            (resp.text or "")[:200],
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Orchestrator + CLI entry
# ---------------------------------------------------------------------------


def check_precompletion_warnings(
    *,
    state: dict[str, str] | None = None,
    workspaces: dict[str, dict[str, Any]] | None = None,
    issues: list[dict] | None = None,
    sleep_fn=time.sleep,
) -> int:
    """Scan in_progress issues and post Pre-Completion Diff Warnings.

    Parameters default to "do the real work": load state from disk, fetch
    workspace map via the API, paginate `list_issues` for `in_progress`.
    Tests pass in fakes so they run hermetically without a Paperclip
    backend.
    """
    if state is None:
        state = load_state()
    if workspaces is None:
        workspaces = _load_workspace_map()
    if issues is None:
        issues = _list_in_progress_with_assignee()

    posted = 0
    now = _utcnow_iso()
    run_id = os.environ.get("PAPERCLIP_RUN_ID")

    for issue in issues:
        issue_id = issue.get("id")
        if not issue_id:
            continue
        if _is_recent_warning(state, issue_id):
            continue
        workspace_id = issue.get("executionWorkspaceId")
        ws = workspaces.get(workspace_id or "") if workspace_id else None
        if not ws or ws.get("sourceType") != "git_repo" or not ws.get("cwd"):
            continue
        if _is_fresh_checkout(issue):
            continue
        if _has_marker_in_thread(issue_id):
            # State file may have been wiped. Record what we *would* have
            # recorded so the cooldown holds even if the comment is gone
            # from the state file's perspective.
            state[issue_id] = now
            continue
        cwd = ws["cwd"]
        if not _workspace_has_uncommitted_changes(cwd):
            continue
        body = _format_warning_body(issue.get("fixBranch"))
        if post_precompletion_warning(issue_id, body, run_id=run_id):
            state[issue_id] = now
            posted += 1
        # Briefly yield so a long run does not starve other cron steps.
        sleep_fn(0)

    save_state(state)
    return posted


def main() -> int:
    """CLI entrypoint. Exits 0 on success / 1 on a runtime error.

    A non-zero exit surfaces failures in the workflow step
    ("Check routine exit code") rather than silently dropping warnings.
    """
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _install_global_timeout(GLOBAL_TIMEOUT_SECONDS)
    try:
        posted = check_precompletion_warnings()
    except TimeoutError as exc:
        LOG.error("global timeout: %s", exc)
        return 1
    except Exception as exc:  # pragma: no cover - catch-all for cron safety
        LOG.exception("check_precompletion_warnings crashed: %s", exc)
        return 1
    LOG.info(
        "precompletion_diff_check done — %d warning comment(s) posted",
        posted,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
