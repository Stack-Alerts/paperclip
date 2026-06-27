#!/usr/bin/env python3
"""Hourly merge-monitor routine — board directive BTCAAAAA-36465 (2026-06-24 19:13Z).

Responsibilities:
1. List OPEN PRs and their required-check status.
2. Identify stale queued runs (>2h old) — cancel duplicates, re-trigger if needed.
3. Identify PRs that are mergeable (all required checks green, no merge conflicts)
   and the merge-dispatch routine did NOT pick up — CEO-bypass squash-merge them.
4. Post a status comment to BTCAAAAA-36465 only when CEO intervention needed
   (avoid noisy routine spam — the routine is the autonomous fix surface).

Designed to run as a scheduled GitHub Actions workflow (.github/workflows/merge-monitor.yml).

Requires:
  - PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID (comment posting)
  - GH_TOKEN (admin scope for squash-merge; falls back to github.token for gh CLI)
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("merge-monitor")

REPO_OWNER = "Stack-Alerts"
REPO_NAME = "BTC-Trade-Engine-PaperClip"
GITHUB_API_BASE = "https://api.github.com"
TRACKING_ISSUE = "BTCAAAAA-36465"
STALE_QUEUED_HOURS = 2
STALE_IN_PROGRESS_HOURS = 1

# Required check names that gate `main` (must be SUCCESS for squash-merge)
REQUIRED_CHECK_SUBSTRINGS = (
    "pytest + coverage gate",
    "Lock Module Requirement Verification",
    "UI CI",
)

# BTCAAAAA-38612 — CANCELLED retrigger guard constants.
# When a required check is CANCELLED, we retrigger via `gh workflow run` (not an
# empty commit push) — but only after both guards pass:
#   1. Imminent-push guard: PR HEAD is NOT a recent automation retrigger commit.
#   2. Cooldown guard: last retrigger for this PR was >RETRIGGER_COOLDOWN_MINUTES ago.
# This prevents the infinite cancel-loop caused by the automation's own pushes
# triggering GitHub's "auto-cancel redundant runs" repo setting.
RETRIGGER_COOLDOWN_MINUTES: int = int(
    os.environ.get("MERGE_MONITOR_RETRIGGER_COOLDOWN_MINUTES", "30")
)
_RETRIGGER_STATE_FILE = Path("/tmp/merge-monitor-retrigger-state.json")
_RETRIGGER_MSG_RE = re.compile(r"ci:\s*(?:re)?trigger", re.IGNORECASE)
_RETRIGGER_AUTHORS = frozenset({"AutomationEngineer", "github-actions[bot]"})


def load_retrigger_state() -> dict[str, str]:
    """Load per-PR last-retrigger timestamps from state file. Returns {} on missing/corrupt."""
    try:
        return json.loads(_RETRIGGER_STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_retrigger_state(state: dict[str, str]) -> None:
    """Persist per-PR last-retrigger timestamps to state file."""
    try:
        _RETRIGGER_STATE_FILE.write_text(json.dumps(state))
    except OSError as exc:
        logger.warning("Failed to save retrigger state: %s", exc)


def _has_cancelled_required_check(checks: dict[str, dict[str, str]]) -> bool:
    """Return True if any REQUIRED_CHECK_SUBSTRINGS check has conclusion 'cancelled'."""
    for sub in REQUIRED_CHECK_SUBSTRINGS:
        for name, data in checks.items():
            if sub.lower() in name.lower():
                if (data.get("conclusion") or "").lower() == "cancelled":
                    return True
    return False


def _fetch_commit(session: requests.Session, sha: str) -> dict[str, Any] | None:
    """Fetch git commit object from GitHub API. Returns None on any error."""
    url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/commits/{sha}"
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        logger.warning("fetch_commit %s: HTTP %s", sha[:8], r.status_code)
    except Exception as exc:
        logger.warning("fetch_commit %s failed: %s", sha[:8], exc)
    return None


def _is_own_push_imminent(
    pr: dict[str, Any],
    session: requests.Session,
    now: datetime,
    max_age_minutes: int | None = None,
) -> bool:
    """Return True if the PR HEAD is a recent automation retrigger commit.

    BTCAAAAA-38612 imminent-push guard: when the automation pushes a retrigger
    commit, GitHub's repo-level "auto-cancel redundant runs" cancels the existing
    CI for that branch. If we immediately retrigger again, we create an infinite
    loop. This guard detects our own recent retrigger push and suppresses a second
    retrigger until RETRIGGER_COOLDOWN_MINUTES has passed.

    A commit is considered "own push" when:
      - its author matches any name in _RETRIGGER_AUTHORS, OR
      - its message matches _RETRIGGER_MSG_RE (e.g. "ci: retrigger …")
    AND the commit was authored within max_age_minutes.
    """
    if max_age_minutes is None:
        max_age_minutes = RETRIGGER_COOLDOWN_MINUTES
    sha = pr.get("head", {}).get("sha", "")
    if not sha:
        return False
    commit = _fetch_commit(session, sha)
    if not commit:
        return False
    message = commit.get("message", "")
    author_name = commit.get("author", {}).get("name", "") or ""
    author_date_str = commit.get("author", {}).get("date", "") or ""
    if not author_date_str:
        return False
    try:
        author_date = datetime.fromisoformat(author_date_str.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    age_min = (now - author_date).total_seconds() / 60
    if age_min > max_age_minutes:
        return False
    is_retrigger_msg = bool(_RETRIGGER_MSG_RE.search(message))
    is_automation_author = any(a in author_name for a in _RETRIGGER_AUTHORS)
    return is_retrigger_msg or is_automation_author


def _http_session(token: str | None = None) -> requests.Session:
    s = requests.Session()
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    s.headers.update(headers)
    adapter = HTTPAdapter(max_retries=Retry(
        total=2, backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        raise_on_status=False,
    ))
    s.mount("https://", adapter)
    return s


def _paperclip_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ.get('PAPERCLIP_API_KEY', '')}",
        "Content-Type": "application/json",
    })
    adapter = HTTPAdapter(max_retries=Retry(
        total=2, backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PATCH"],
        raise_on_status=False,
    ))
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _gh_env(token: str | None) -> dict[str, str]:
    """Build env override for gh CLI (uses GH_TOKEN env var, not -H header)."""
    if not token:
        return {}
    # gh CLI reads GH_TOKEN from env automatically; pass through so subprocess picks it up
    import os as _os
    return {**_os.environ, "GH_TOKEN": token}


def _gh_cli(token: str | None) -> list[str]:
    """Build a gh CLI invocation. Auth via GH_TOKEN env var (passed by caller)."""
    return ["gh"]


def list_open_prs(session: requests.Session) -> list[dict[str, Any]]:
    """Fetch all OPEN PRs with their statusCheckRollup."""
    prs: list[dict[str, Any]] = []
    page = 1
    while True:
        r = session.get(
            f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
            params={"state": "open", "per_page": 100, "page": page},
            timeout=30,
        )
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            break
        # Fetch each PR with detailed check status (list endpoint may omit rollup)
        for pr in chunk:
            detail = session.get(pr["url"], timeout=30).json()
            prs.append(detail)
        page += 1
        if page > 5:
            break
    return prs


def list_queued_runs(session: requests.Session) -> list[dict[str, Any]]:
    """Fetch all QUEUED workflow runs (any workflow, any PR)."""
    runs: list[dict[str, Any]] = []
    page = 1
    while True:
        r = session.get(
            f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs",
            params={"status": "queued", "per_page": 100, "page": page},
            timeout=30,
        )
        r.raise_for_status()
        chunk = r.json().get("workflow_runs", [])
        runs.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
        if page > 5:
            break
    return runs


def list_in_progress_runs(session: requests.Session) -> list[dict[str, Any]]:
    r = session.get(
        f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs",
        params={"status": "in_progress", "per_page": 100},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("workflow_runs", [])


def parse_checks(pr: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Parse a PR's statusCheckRollup into a dict of name→{status,conclusion}."""
    out: dict[str, dict[str, str]] = {}
    rollup = pr.get("statusCheckRollup") or []
    for c in rollup:
        name = c.get("name", "")
        out[name] = {
            "status": c.get("status", ""),
            "conclusion": c.get("conclusion", "") or "",
            "workflow": c.get("workflowName", ""),
            "detailsUrl": c.get("detailsUrl", ""),
        }
    return out


def is_mergeable(pr: dict[str, Any], checks: dict[str, dict[str, str]]) -> tuple[bool, str]:
    """Return (mergeable, reason).

    Note: we deliberately ignore GitHub's aggregate `mergeable_state` (often "blocked"
    while required checks are still queued on self-hosted runners). The per-check loop
    below is the source of truth: every REQUIRED_CHECK_SUBSTRINGS must be SUCCESS.
    """
    if pr.get("merged"):
        return False, "already merged"
    if pr.get("draft"):
        return False, "draft"
    if pr.get("mergeable_state") == "dirty":
        return False, "merge conflict"
    # Required checks: all REQUIRED_CHECK_SUBSTRINGS must be SUCCESS
    for sub in REQUIRED_CHECK_SUBSTRINGS:
        match = None
        for name, data in checks.items():
            if sub.lower() in name.lower():
                match = (name, data)
                break
        if not match:
            return False, f"required check missing: {sub}"
        name, data = match
        if data["status"] != "COMPLETED":
            return False, f"required check {name!r} still {data['status']}"
        if data["conclusion"] != "SUCCESS":
            return False, f"required check {name!r}={data['conclusion']}"
    return True, "all required checks SUCCESS, no merge conflict"


def cancel_run(run_id: int, gh_token: str | None = None) -> bool:
    """Cancel a workflow run via gh CLI."""
    cmd = _gh_cli(gh_token) + ["run", "cancel", str(run_id),
                                "--repo", f"{REPO_OWNER}/{REPO_NAME}"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=30, env=_gh_env(gh_token))
        if res.returncode == 0:
            logger.info("cancelled run %s", run_id)
            return True
        logger.warning("cancel run %s failed: %s", run_id, res.stderr.strip())
        return False
    except Exception as exc:
        logger.warning("cancel run %s raised: %s", run_id, exc)
        return False


def retest_pr(pr_number: int, gh_token: str | None = None) -> bool:
    """Re-run the Test and Coverage workflow on a PR (only if needed)."""
    cmd = _gh_cli(gh_token) + ["workflow", "run", "test.yml",
                                "--repo", f"{REPO_OWNER}/{REPO_NAME}",
                                "--ref", f"refs/pull/{pr_number}/head"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=30, env=_gh_env(gh_token))
        if res.returncode == 0:
            logger.info("re-triggered test.yml on PR #%s", pr_number)
            return True
        logger.warning("retest PR #%s failed: %s", pr_number, res.stderr.strip())
        return False
    except Exception as exc:
        logger.warning("retest PR #%s raised: %s", pr_number, exc)
        return False


def squash_merge(pr_number: int, gh_token: str) -> tuple[bool, str]:
    """Squash-merge a PR. Returns (success, detail)."""
    cmd = _gh_cli(gh_token) + ["pr", "merge", str(pr_number),
                                "--squash", "--delete-branch",
                                "--repo", f"{REPO_OWNER}/{REPO_NAME}"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=120, env=_gh_env(gh_token))
        if res.returncode == 0:
            return True, res.stdout.strip()[:200]
        return False, (res.stderr or res.stdout).strip()[:300]
    except Exception as exc:
        return False, f"raised: {exc}"


def post_paperclip_comment(body: str, issue_id: str | None = None) -> bool:
    """Post a comment on the tracking issue. Used only when intervention is needed."""
    if not issue_id:
        issue_id = TRACKING_ISSUE
    api_url = os.environ.get("PAPERCLIP_API_URL", "")
    company_id = os.environ.get("PAPERCLIP_COMPANY_ID", "")
    if not api_url or not company_id:
        logger.warning("PAPERCLIP_API_URL or PAPERCLIP_COMPANY_ID not set — skipping comment")
        return False
    s = _paperclip_session()
    url = f"{api_url}/api/companies/{company_id}/issues/{issue_id}/comments"
    try:
        r = s.post(url, json={"body": body}, timeout=30)
        if r.status_code < 300:
            logger.info("posted comment to %s", issue_id)
            return True
        logger.warning("post comment %s: HTTP %s: %s", issue_id, r.status_code, r.text[:200])
        return False
    except Exception as exc:
        logger.warning("post comment %s raised: %s", issue_id, exc)
        return False


def main() -> int:
    now = datetime.now(timezone.utc)
    gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    logger.info("=== merge-monitor start @ %s (dry_run=%s) ===", now.isoformat(), dry_run)

    s = _http_session(gh_token)

    # 1. Collect OPEN PRs + queued runs
    open_prs = list_open_prs(s)
    queued_runs = list_queued_runs(s)
    in_progress_runs = list_in_progress_runs(s)
    logger.info("OPEN PRs: %d, queued runs: %d, in_progress runs: %d",
                len(open_prs), len(queued_runs), len(in_progress_runs))

    # 2. Cancel wasted queued runs on MERGED/CLOSED PRs
    cancelled_waste = []
    for run in queued_runs:
        prs = run.get("pull_requests", [])
        if prs:
            try:
                r = s.get(prs[0]["url"], timeout=15)
                if r.status_code == 200 and r.json().get("state") == "open":
                    continue
            except Exception:
                pass
        if dry_run:
            logger.info("[DRY] would cancel wasted queued run %s", run["id"])
            cancelled_waste.append(run["id"])
        elif cancel_run(run["id"], gh_token):
            cancelled_waste.append(run["id"])

    # 3. Cancel duplicate queued Test and Coverage runs (>2h, keep newest per PR)
    dup_cancelled = []
    tc_by_pr: dict[str, list[dict[str, Any]]] = {}
    for run in queued_runs:
        if "Test and Coverage" not in run["name"]:
            continue
        prs = run.get("pull_requests", [])
        if not prs:
            continue
        pr_key = f"PR#{prs[0]['number']}"
        tc_by_pr.setdefault(pr_key, []).append(run)
    for pr_key, runs in tc_by_pr.items():
        runs.sort(key=lambda r: r["created_at"])
        for stale in runs[:-1]:
            created = datetime.fromisoformat(stale["created_at"].replace("Z", "+00:00"))
            age_h = (now - created).total_seconds() / 3600
            if age_h >= STALE_QUEUED_HOURS:
                if dry_run:
                    logger.info("[DRY] would cancel duplicate queued run %s", stale["id"])
                    dup_cancelled.append(stale["id"])
                elif cancel_run(stale["id"], gh_token):
                    dup_cancelled.append(stale["id"])

    # 4. Re-test PRs whose only queued run is stale (>2h)
    retested = []
    for pr in open_prs:
        pr_num = pr["number"]
        my_queued = [r for r in queued_runs
                     if any(p.get("number") == pr_num for p in r.get("pull_requests", []))
                     and "Test and Coverage" in r["name"]]
        if not my_queued:
            continue
        oldest = min(my_queued, key=lambda r: r["created_at"])
        created = datetime.fromisoformat(oldest["created_at"].replace("Z", "+00:00"))
        age_h = (now - created).total_seconds() / 3600
        if age_h >= STALE_QUEUED_HOURS and len(my_queued) == 1 and not dry_run:
            if retest_pr(pr_num, gh_token):
                retested.append(pr_num)

    # 4b. BTCAAAAA-38612 — Retrigger PRs with CANCELLED required checks.
    # Uses `gh workflow run` (NOT an empty git commit) so we don't feed the
    # auto-cancel loop. Two guards must both pass before any retrigger:
    #   - Imminent-push guard: HEAD commit is not a recent automation retrigger.
    #   - Cooldown guard: last retrigger for this PR was >RETRIGGER_COOLDOWN_MINUTES ago.
    retrigger_state = load_retrigger_state()
    cancelled_retriggered: list[int] = []
    for pr in open_prs:
        pr_num = pr["number"]
        checks = parse_checks(pr)
        if not _has_cancelled_required_check(checks):
            continue

        # Guard 1: cooldown — skip if we retrigggered this PR recently.
        last_retrigger_str = retrigger_state.get(str(pr_num))
        if last_retrigger_str:
            try:
                last_retrigger = datetime.fromisoformat(last_retrigger_str)
                if last_retrigger.tzinfo is None:
                    last_retrigger = last_retrigger.replace(tzinfo=timezone.utc)
                age_min = (now - last_retrigger).total_seconds() / 60
                if age_min < RETRIGGER_COOLDOWN_MINUTES:
                    logger.info(
                        "PR #%d CANCELLED retrigger skipped — cooldown active"
                        " (%.0f min remaining)",
                        pr_num, RETRIGGER_COOLDOWN_MINUTES - age_min,
                    )
                    continue
            except (TypeError, ValueError):
                pass  # Corrupt state — proceed with retrigger

        # Guard 2: imminent-push — HEAD is a recent automation retrigger commit.
        if _is_own_push_imminent(pr, s, now):
            logger.info(
                "PR #%d CANCELLED retrigger skipped — HEAD is recent automation"
                " retrigger commit (imminent-push guard)",
                pr_num,
            )
            continue

        if dry_run:
            logger.info("[DRY] would retrigger CANCELLED PR #%d", pr_num)
            cancelled_retriggered.append(pr_num)
        elif retest_pr(pr_num, gh_token):
            retrigger_state[str(pr_num)] = now.isoformat()
            cancelled_retriggered.append(pr_num)

    save_retrigger_state(retrigger_state)

    # 5. CEO-bypass squash-merge eligible PRs
    merged = []
    merge_blocked = []
    for pr in open_prs:
        pr_num = pr["number"]
        checks = parse_checks(pr)
        ok, reason = is_mergeable(pr, checks)
        if ok:
            if dry_run:
                logger.info("[DRY] would squash-merge PR #%s: %s", pr_num, pr["title"][:60])
                merged.append((pr_num, "DRY-RUN"))
                continue
            success, detail = squash_merge(pr_num, gh_token)
            if success:
                merged.append((pr_num, detail))
            else:
                merge_blocked.append((pr_num, detail))
                logger.warning("squash-merge PR #%s failed: %s", pr_num, detail)
        else:
            logger.info("PR #%s not yet mergeable: %s", pr_num, reason)

    # 6. Post status only if intervention needed
    intervention_needed = bool(cancelled_waste or dup_cancelled or merge_blocked)
    if intervention_needed and not dry_run:
        body_lines = [
            "## Merge-monitor routine — intervention summary",
            "",
            f"- OPEN PRs scanned: **{len(open_prs)}**",
            f"- Queued runs (start): {len(queued_runs)}, In-progress: {len(in_progress_runs)}",
            f"- Wasted queued runs cancelled: **{len(cancelled_waste)}** (PR closed/merged)",
            f"- Duplicate queued runs cancelled: **{len(dup_cancelled)}** (>2h stale)",
            f"- PRs re-tested (stuck queue): **{retested}**",
            f"- Merged this cycle: **{len(merged)}**",
        ]
        if merge_blocked:
            body_lines.append("- Merges BLOCKED:")
            for pr_num, detail in merge_blocked:
                body_lines.append(f"  - PR #{pr_num}: {detail}")
        body_lines.extend([
            "",
            "_Routine triggered by board directive 2026-06-24 19:13Z. No CEO action required unless listed above._",
        ])
        post_paperclip_comment("\n".join(body_lines))

    # 7. Always emit JSON summary for GH Actions step summary
    summary = {
        "timestamp": now.isoformat(),
        "dry_run": dry_run,
        "open_prs": len(open_prs),
        "queued_runs_start": len(queued_runs),
        "in_progress_runs_start": len(in_progress_runs),
        "waste_cancelled": cancelled_waste,
        "duplicate_cancelled": dup_cancelled,
        "retested_prs": retested,
        "cancelled_retriggered": cancelled_retriggered,
        "merged": merged,
        "merge_blocked": merge_blocked,
        "intervention_posted": intervention_needed and not dry_run,
    }
    Path("/tmp/merge-monitor-output.json").write_text(json.dumps(summary, indent=2))
    logger.info("=== merge-monitor done ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())