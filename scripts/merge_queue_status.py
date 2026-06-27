#!/usr/bin/env python3
"""Merge queue status — shows every in_review issue and its PR/CI state.

Usage:
    python3 scripts/merge_queue_status.py          # live table
    python3 scripts/merge_queue_status.py --json   # JSON output
    python3 scripts/merge_queue_status.py --watch  # refresh every 60 s

Env vars are auto-loaded from .env at the repo root if not already set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_dotenv() -> None:
    """Load .env from the repo root into os.environ (only for unset keys)."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

_load_dotenv()

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_OWNER = "Stack-Alerts"
REPO_NAME = "BTC-Trade-Engine-PaperClip"
GITHUB_API_BASE = "https://api.github.com"
FIX_SHA_PATTERN = re.compile(r"^Fix-SHA: ([0-9a-f]{40})$", re.MULTILINE)

REQUIRED_CHECK_SUBSTRINGS = (
    "pytest + coverage gate",
    "Lock Module Requirement Verification",
    "UI CI",
)

_COLOUR = sys.stdout.isatty()
def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text

def GREEN(t: str)  -> str: return _c("32", t)
def RED(t: str)    -> str: return _c("31", t)
def YELLOW(t: str) -> str: return _c("33", t)
def CYAN(t: str)   -> str: return _c("36", t)
def BOLD(t: str)   -> str: return _c("1",  t)
def DIM(t: str)    -> str: return _c("2",  t)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _paperclip_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ.get('PAPERCLIP_API_KEY', '')}",
        "Content-Type": "application/json",
    })
    retry = Retry(total=2, backoff_factor=0.5,
                  status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    return s


def _github_token() -> str | None:
    token = os.environ.get("GH_TOKEN", "")
    if token:
        return token
    try:
        clean = {k: v for k, v in os.environ.items() if k != "GH_TOKEN"}
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                           timeout=10, env=clean)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _github_session(token: str | None) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Accept": "application/vnd.github+json",
                       "X-GitHub-Api-Version": "2022-11-28"})
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    retry = Retry(total=2, backoff_factor=0.5,
                  status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_in_review_issues(pc: requests.Session) -> list[dict[str, Any]]:
    api_url    = os.environ.get("PAPERCLIP_API_URL", "").rstrip("/")
    company_id = os.environ.get("PAPERCLIP_COMPANY_ID", "")
    if not api_url or not company_id:
        print("ERROR: PAPERCLIP_API_URL and PAPERCLIP_COMPANY_ID must be set.", file=sys.stderr)
        return []

    # Try port 3199 proxy if 3100 is down
    for base in [api_url, api_url.replace(":3100", ":3199")]:
        try:
            r = pc.get(f"{base}/api/companies/{company_id}/issues",
                       params={"status": "in_review", "limit": 200}, timeout=20)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "issues" in data:
                    return data["issues"]
        except requests.exceptions.ConnectionError:
            continue
    print("ERROR: Paperclip API unreachable on both port 3100 and 3199.", file=sys.stderr)
    return []


def fetch_comments(pc: requests.Session, issue_id: str) -> list[dict[str, Any]]:
    api_url = os.environ.get("PAPERCLIP_API_URL", "").rstrip("/")
    for base in [api_url, api_url.replace(":3100", ":3199")]:
        try:
            r = pc.get(f"{base}/api/issues/{issue_id}/comments", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return data if isinstance(data, list) else []
        except requests.exceptions.ConnectionError:
            continue
    return []


def extract_fix_shas(comments: list[dict[str, Any]]) -> list[str]:
    """Return all unique Fix-SHAs found in comments, newest-first."""
    seen: set[str] = set()
    shas: list[str] = []
    for c in reversed(comments):  # newest first
        body = c.get("body", "") or ""
        for m in FIX_SHA_PATTERN.finditer(body):
            sha = m.group(1)
            if sha not in seen:
                seen.add(sha)
                shas.append(sha)
    return shas


def extract_fix_sha(comments: list[dict[str, Any]]) -> str | None:
    """Return the most recent Fix-SHA (kept for backwards compat)."""
    shas = extract_fix_shas(comments)
    return shas[0] if shas else None


def fetch_open_prs(gh: requests.Session) -> list[dict[str, Any]]:
    prs: list[dict[str, Any]] = []
    for page in range(1, 6):
        r = gh.get(f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
                   params={"state": "open", "per_page": 100, "page": page}, timeout=30)
        if r.status_code != 200:
            break
        chunk = r.json()
        if not chunk:
            break
        prs.extend(chunk)
    return prs


def sha_is_ancestor_of_main(sha: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, "origin/main"],
            capture_output=True, timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


def find_remote_branch_for_sha(sha: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "branch", "-r", "--contains", sha],
            capture_output=True, text=True, timeout=10,
        )
        lines = [l.strip().removeprefix("origin/") for l in r.stdout.splitlines()
                 if l.strip() and "HEAD" not in l]
        return lines[0] if lines else None
    except Exception:
        return None


def _sha_is_ancestor_of(sha: str, target: str) -> bool:
    """Return True if sha is an ancestor of (or equal to) target."""
    try:
        r = subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, target],
            capture_output=True, timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


def pr_for_sha(prs: list[dict[str, Any]], sha: str) -> dict[str, Any] | None:
    # 1. Exact branch match via git branch -r --contains <sha>
    branch = find_remote_branch_for_sha(sha)
    if branch:
        for pr in prs:
            if pr.get("head", {}).get("ref", "") == branch:
                return pr

    # 2. HEAD SHA prefix match (Fix-SHA == PR HEAD)
    for pr in prs:
        if pr.get("head", {}).get("sha", "").startswith(sha[:7]):
            return pr

    # 3. Ancestry check: Fix-SHA is an ancestor of the PR's HEAD SHA.
    #    Handles rebased/amended branches where Fix-SHA != current HEAD.
    for pr in prs:
        pr_head = pr.get("head", {}).get("sha", "")
        if pr_head and _sha_is_ancestor_of(sha, pr_head):
            return pr

    return None


def fetch_check_runs(gh: requests.Session, pr: dict[str, Any]) -> list[dict[str, Any]]:
    head_sha = pr.get("head", {}).get("sha", "")
    if not head_sha:
        return []
    r = gh.get(
        f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/commits/{head_sha}/check-runs",
        params={"per_page": 100}, timeout=20,
    )
    if r.status_code != 200:
        return []
    return r.json().get("check_runs", [])


def fetch_run_counts(gh: requests.Session) -> tuple[int, int]:
    queued = in_prog = 0
    for status in ("queued", "in_progress"):
        r = gh.get(f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs",
                   params={"status": status, "per_page": 100}, timeout=20)
        if r.status_code == 200:
            n = len(r.json().get("workflow_runs", []))
            if status == "queued":
                queued = n
            else:
                in_prog = n
    return queued, in_prog


# ---------------------------------------------------------------------------
# CI analysis
# ---------------------------------------------------------------------------

def _dedup_checks(checks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for c in checks:
        name = c.get("name", "unknown")
        if name not in by_name or c.get("id", 0) > by_name[name].get("id", 0):
            by_name[name] = c
    return by_name


def all_required_green(checks: list[dict[str, Any]]) -> bool:
    by_name = _dedup_checks(checks)
    for sub in REQUIRED_CHECK_SUBSTRINGS:
        match = next((c for n, c in by_name.items() if sub.lower() in n.lower()), None)
        if not match or match.get("conclusion") != "success":
            return False
    return True


def has_failure(checks: list[dict[str, Any]]) -> bool:
    return any(c.get("conclusion") in ("failure", "timed_out", "startup_failure")
               for c in checks)


def ci_summary(checks: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Return (status_symbol, [required-check detail lines])."""
    if not checks:
        return YELLOW("? NO CI DATA"), ["  no check-runs found for this PR"]

    by_name = _dedup_checks(checks)
    total   = len(by_name)
    success = sum(1 for c in by_name.values() if c.get("conclusion") == "success")
    failure = sum(1 for c in by_name.values()
                  if c.get("conclusion") in ("failure", "timed_out", "startup_failure"))
    pending = sum(1 for c in by_name.values()
                  if c.get("status") in ("queued", "in_progress"))

    lines: list[str] = []
    for sub in REQUIRED_CHECK_SUBSTRINGS:
        match = next((c for n, c in by_name.items() if sub.lower() in n.lower()), None)
        if not match:
            lines.append(f"  {RED('✗ MISSING')} {sub}")
        elif match.get("conclusion") == "success":
            lines.append(f"  {GREEN('✓')} {match['name']}")
        elif match.get("conclusion") in ("failure", "timed_out"):
            lines.append(f"  {RED('✗ FAIL')}    {match['name']}")
        elif match.get("status") in ("queued", "in_progress"):
            lines.append(f"  {YELLOW('⏳ PENDING')} {match['name']} [{match['status']}]")
        else:
            lines.append(f"  {DIM('?')}         {match['name']} [{match.get('conclusion','?')}]")

    if failure:
        symbol = RED(f"✗ FAILING ({failure}/{total} checks failed)")
    elif all_required_green(checks):
        symbol = GREEN(f"✓ ALL GREEN ({success}/{total} passed) — ready to merge")
    elif pending:
        symbol = YELLOW(f"⏳ WAITING ({pending}/{total} checks pending)")
    else:
        symbol = YELLOW(f"? {success}/{total} passed, {failure} failed, {pending} pending")

    return symbol, lines


def _age(ts: str | None) -> str:
    if not ts:
        return "?"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        secs = int((datetime.now(timezone.utc) - dt).total_seconds())
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60}m"
        return f"{secs // 3600}h {(secs % 3600) // 60}m"
    except Exception:
        return "?"


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def collect(verbose: bool = True) -> dict[str, Any]:
    pc = _paperclip_session()
    token = _github_token()
    gh = _github_session(token)

    if verbose:
        print(DIM("Fetching in_review issues…"), flush=True)
    issues = fetch_in_review_issues(pc)

    if verbose:
        print(DIM("Fetching open PRs from GitHub…"), flush=True)
    open_prs = fetch_open_prs(gh)

    if verbose:
        print(DIM("Fetching CI run counts…"), flush=True)
    queued_runs, in_progress_runs = fetch_run_counts(gh)

    # Fetch git remote refs so branch-contains lookups work locally
    try:
        subprocess.run(["git", "fetch", "--quiet", "origin"], timeout=20,
                       capture_output=True)
    except Exception:
        pass

    queue: list[dict[str, Any]] = []
    for issue in issues:
        issue_id    = issue.get("id") or issue.get("issueId", "")
        display_key = issue.get("displayKey") or issue_id
        title       = issue.get("title", "(no title)")
        updated_at  = issue.get("updatedAt") or issue.get("updated_at")

        if verbose:
            print(DIM(f"  Processing {display_key}…"), flush=True)

        comments = fetch_comments(pc, issue_id)
        all_shas = extract_fix_shas(comments)
        sha = all_shas[0] if all_shas else None  # most recent for display

        # Check each Fix-SHA for already-merged; any one on main = done
        already_merged = any(sha_is_ancestor_of_main(s) for s in all_shas) if all_shas else False
        # Try each Fix-SHA until we find the PR (handles rebased branches where
        # the latest Fix-SHA != PR HEAD but an earlier one is an ancestor)
        pr = None
        if all_shas and not already_merged:
            for s in all_shas:
                pr = pr_for_sha(open_prs, s)
                if pr:
                    break
        pr_num = pr["number"] if pr else None

        checks: list[dict[str, Any]] = []
        if pr:
            checks = fetch_check_runs(gh, pr)

        queue.append({
            "issue_id":      issue_id,
            "display_key":   display_key,
            "title":         title,
            "updated_at":    updated_at,
            "fix_sha":       sha,
            "already_merged": already_merged,
            "pr_number":     pr_num,
            "pr_title":      pr["title"] if pr else None,
            "pr_mergeable":  pr.get("mergeable_state") if pr else None,
            "checks":        checks,
        })

    return {
        "as_of":            datetime.now(timezone.utc).isoformat(),
        "in_review_count":  len(issues),
        "open_pr_count":    len(open_prs),
        "queued_runs":      queued_runs,
        "in_progress_runs": in_progress_runs,
        "queue":            queue,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def print_table(data: dict[str, Any]) -> None:
    W = 82
    q = data["queue"]

    print()
    print(BOLD("═" * W))
    print(BOLD("  MERGE QUEUE STATUS   ") + DIM(data["as_of"]))
    print(BOLD("═" * W))
    print(f"  {BOLD('In-review:')} {data['in_review_count']}  "
          f"{BOLD('Open PRs:')} {data['open_pr_count']}  "
          f"{BOLD('Queued CI runs:')} {data['queued_runs']}  "
          f"{BOLD('In-progress CI:')} {data['in_progress_runs']}")
    print(BOLD("─" * W))

    if not q:
        print(GREEN("  ✓ Queue is empty — nothing waiting to merge."))
        print(BOLD("═" * W))
        return

    ready = waiting = failing = no_pr = 0

    for i, item in enumerate(q, 1):
        key   = item["display_key"]
        title = item["title"]
        age   = _age(item["updated_at"])
        sha   = item["fix_sha"]
        pr_n  = item["pr_number"]
        checks = item["checks"]

        print(f"\n  {BOLD(f'#{i}')}  {CYAN(key)}  {DIM(f'(in_review for {age})')}")
        # Truncate title to fit
        print(f"      {title[:72]}")

        # Fix-SHA
        if sha:
            if item["already_merged"]:
                print(f"      Fix-SHA  {GREEN('✓ ALREADY ON MAIN')}  {DIM(sha[:12])}…  "
                      f"{DIM('(closure-gate should close this)')}")
                no_pr += 1
                print(f"      {DIM('─' * 72)}")
                continue
            print(f"      Fix-SHA  {DIM(sha[:12])}…")
        else:
            print(f"      Fix-SHA  {RED('NOT FOUND')} — merge-dispatch cannot proceed")
            no_pr += 1
            print(f"      {DIM('─' * 72)}")
            continue

        # PR
        if pr_n:
            ms = item.get("pr_mergeable", "")
            ms_display = (GREEN(ms) if ms == "clean"
                          else RED(ms) if ms in ("dirty", "blocked")
                          else YELLOW(ms))
            print(f"      PR #     {pr_n}  {ms_display}  "
                  f"{DIM((item['pr_title'] or '')[:48])}")

            sym, lines = ci_summary(checks)
            print(f"      CI       {sym}")
            for line in lines:
                print(f"      {line}")

            if all_required_green(checks):
                ready += 1
            elif has_failure(checks):
                failing += 1
            else:
                waiting += 1
        else:
            print(f"      PR #     {RED('NOT FOUND')}  "
                  f"{DIM('(Fix-SHA pushed? branch deleted? PR closed?)')}")
            no_pr += 1

        print(f"      {DIM('─' * 72)}")

    print()
    print(BOLD("═" * W))
    print(f"  {BOLD('TOTALS')}  "
          f"{GREEN(f'{ready} ready')}  "
          f"{YELLOW(f'{waiting} waiting on CI')}  "
          f"{RED(f'{failing} CI failing')}  "
          f"{DIM(f'{no_pr} no PR / SHA issue')}")
    print(BOLD("═" * W))
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Show merge queue: in_review issues → PR → CI status")
    ap.add_argument("--json",  action="store_true", help="Output raw JSON")
    ap.add_argument("--watch", action="store_true",
                    help="Auto-refresh every 60 seconds (Ctrl-C to stop)")
    ap.add_argument("--quiet", action="store_true",
                    help="Suppress progress lines while fetching")
    args = ap.parse_args()

    interval = 60

    while True:
        if args.watch and sys.stdout.isatty():
            print("\033[2J\033[H", end="")  # clear screen

        data = collect(verbose=not args.quiet and not args.json)

        if args.json:
            out = dict(data)
            for item in out["queue"]:
                item.pop("checks", None)
            print(json.dumps(out, indent=2))
        else:
            print_table(data)

        if not args.watch:
            break

        print(DIM(f"  Auto-refresh in {interval}s — Ctrl-C to quit"), flush=True)
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped.")
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
