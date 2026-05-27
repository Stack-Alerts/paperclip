#!/usr/bin/env python3
"""pr_scope_check_routine.py — Phase 6b PR scope-creep watchdog (BTCAAAAA-30054).

Walks every open PR on Stack-Alerts/BTC-Trade-Engine-PaperClip, runs the same
scope-creep logic as `scripts/lint-pr-scope.sh`, and on detection:

  1. Posts a PR comment naming the offending commit subject(s) — only if a
     matching comment from this routine is not already on the PR (idempotent
     via a fingerprint marker line).
  2. Applies the `scope-creep` label (creates it if missing).
  3. Posts a notification comment on the Paperclip issue whose identifier was
     leaked into the foreign branch (so the assignee of that issue gets woken
     and knows their scope was contaminated).

Designed to be runnable both as a standalone CLI and from a GitHub Actions
cron workflow (`.github/workflows/pr-scope-check.yml`).

Environment:
  GH_TOKEN              — GitHub token with `repo` scope. Required.
  PAPERCLIP_API_URL     — Paperclip control-plane URL. Optional.
  PAPERCLIP_API_KEY     — Bearer token. Optional. If absent, Paperclip
                          notification is skipped (PR comment + label still
                          posted).
  PAPERCLIP_COMPANY_ID  — Required when Paperclip notification is enabled.
  PAPERCLIP_RUN_ID      — Audit trail header; defaults to "pr-scope-check".

CLI flags:
  --dry-run             — Print findings; do not post comments or labels.
  --owner OWNER         — GitHub org/owner (default: Stack-Alerts).
  --repo REPO           — GitHub repo (default: BTC-Trade-Engine-PaperClip).
  --json                — Emit machine-readable JSON summary to stdout.

Exit codes:
  0 — routine completed (with or without findings).
  1 — fatal error (missing token, API failure that prevented any check).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

ID_REGEX = re.compile(r"BTCAAAAA-\d+")
COMMENT_MARKER = "<!-- pr-scope-check:v1 -->"
SCOPE_LABEL = "scope-creep"
DEFAULT_OWNER = "Stack-Alerts"
DEFAULT_REPO = "BTC-Trade-Engine-PaperClip"


class GitHubError(RuntimeError):
    pass


def gh_request(method: str, url: str, token: str, body: Any | None = None) -> tuple[int, Any]:
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "pr-scope-check-routine/1.0")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8") if resp.length != 0 else ""
            payload = json.loads(raw) if raw else None
            return status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise GitHubError(f"HTTP {exc.code} {method} {url}: {raw[:500]}") from exc
    except urllib.error.URLError as exc:
        raise GitHubError(f"URL error {method} {url}: {exc}") from exc


def gh_paginated(method: str, url: str, token: str) -> list[Any]:
    items: list[Any] = []
    next_url = url
    while next_url:
        req = urllib.request.Request(next_url, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "pr-scope-check-routine/1.0")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                payload = json.loads(raw) if raw else []
                if isinstance(payload, list):
                    items.extend(payload)
                else:
                    items.append(payload)
                link = resp.headers.get("Link", "")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise GitHubError(f"HTTP {exc.code} {method} {next_url}: {raw[:500]}") from exc
        next_url = ""
        for part in link.split(","):
            part = part.strip()
            if part.endswith('rel="next"'):
                next_url = part.split(";", 1)[0].strip().lstrip("<").rstrip(">")
                break
    return items


def branch_identifier(name: str) -> str | None:
    m = ID_REGEX.search(name or "")
    return m.group(0) if m else None


def offending_commits(branch_id: str, commits: list[dict]) -> list[dict]:
    offenders: list[dict] = []
    for c in commits:
        subject = (c.get("commit") or {}).get("message", "").splitlines()[0:1]
        subject = subject[0] if subject else ""
        refs = ID_REGEX.findall(subject)
        if not refs:
            continue
        foreign = [r for r in refs if r != branch_id]
        if foreign:
            offenders.append(
                {
                    "sha": c.get("sha", ""),
                    "subject": subject,
                    "foreign": sorted(set(foreign)),
                }
            )
    return offenders


def comment_already_posted(owner: str, repo: str, pr_number: int, token: str) -> bool:
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments?per_page=100"
    comments = gh_paginated("GET", url, token)
    for c in comments:
        body = c.get("body") or ""
        if COMMENT_MARKER in body:
            return True
    return False


def ensure_label(owner: str, repo: str, token: str) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/labels/{SCOPE_LABEL}"
    try:
        status, _ = gh_request("GET", url, token)
        if status == 200:
            return
    except GitHubError as exc:
        if "HTTP 404" not in str(exc):
            raise
    create_url = f"https://api.github.com/repos/{owner}/{repo}/labels"
    gh_request(
        "POST",
        create_url,
        token,
        body={
            "name": SCOPE_LABEL,
            "color": "d93f0b",
            "description": (
                "PR carries commits referencing a different BTCAAAAA-NNN "
                "than the branch (BTCAAAAA-30054)."
            ),
        },
    )


def post_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    branch: str,
    branch_id: str,
    offenders: list[dict],
    token: str,
) -> None:
    lines = [
        COMMENT_MARKER,
        f"### Scope-creep detected on `{branch}` (issue `{branch_id}`)",
        "",
        "The following commit(s) reference a different BTCAAAAA-NNN identifier than the branch:",
        "",
    ]
    for o in offenders:
        foreign = ", ".join(o["foreign"])
        lines.append(f"- `{o['sha'][:12]}` → references **{foreign}** — `{o['subject']}`")
    lines += [
        "",
        (
            "Each issue must live on its own branch (Phase 2 merge-governance, "
            "BTCAAAAA-30046). Move the offending commit(s) to a branch named "
            "for the issue they actually fix, e.g.:"
        ),
        "",
        "```bash",
        "git switch -c <type>/BTCAAAAA-NNN-<slug> origin/main",
        "git cherry-pick <commit-sha>",
        "```",
        "",
        (
            "_Generated by `pr-scope-check` (BTCAAAAA-30054). To bypass an "
            "intentional cross-reference, use a `Refs:` trailer in the commit "
            "body instead of the subject line._"
        ),
    ]
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    gh_request("POST", url, token, body={"body": "\n".join(lines)})


def apply_label(owner: str, repo: str, pr_number: int, token: str) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/labels"
    gh_request("POST", url, token, body={"labels": [SCOPE_LABEL]})


def paperclip_request(
    method: str,
    path: str,
    base_url: str,
    api_key: str,
    run_id: str,
    body: Any | None = None,
) -> tuple[int, Any]:
    url = base_url.rstrip("/") + path
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("X-Paperclip-Run-Id", run_id)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8") if resp.length != 0 else ""
            payload = json.loads(raw) if raw else None
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise GitHubError(f"Paperclip HTTP {exc.code} {method} {url}: {raw[:400]}") from exc


def notify_paperclip(
    foreign_id: str,
    pr_url: str,
    pr_branch: str,
    offenders: list[dict],
    *,
    base_url: str,
    api_key: str,
    company_id: str,
    run_id: str,
) -> None:
    query = urllib.parse.urlencode({"q": foreign_id})
    status, payload = paperclip_request(
        "GET",
        f"/api/companies/{company_id}/issues?{query}",
        base_url,
        api_key,
        run_id,
    )
    issues = payload if isinstance(payload, list) else (payload or {}).get("issues") or []
    target = None
    for issue in issues:
        if issue.get("identifier") == foreign_id:
            target = issue
            break
    if target is None:
        return

    body_lines = [
        f"### Scope-creep notice — `{foreign_id}` referenced from a foreign PR",
        "",
        (
            f"A commit referencing **{foreign_id}** landed on branch "
            f"`{pr_branch}` and is now part of [{pr_url}]({pr_url})."
        ),
        "",
        "Offending commits:",
    ]
    for o in offenders:
        body_lines.append(f"- `{o['sha'][:12]}` — `{o['subject']}`")
    body_lines += [
        "",
        (
            f"Investigate whether this work belongs on the correct branch and, "
            f"if so, cherry-pick it to a fresh `<type>/{foreign_id}-<slug>` "
            f"branch. Detected by `pr-scope-check` (BTCAAAAA-30054)."
        ),
    ]
    paperclip_request(
        "POST",
        f"/api/issues/{target['id']}/comments",
        base_url,
        api_key,
        run_id,
        body={"body": "\n".join(body_lines)},
    )


def check_pr(
    pr: dict,
    *,
    owner: str,
    repo: str,
    token: str,
    dry_run: bool,
    paperclip_cfg: dict | None,
) -> dict:
    branch = (pr.get("head") or {}).get("ref", "")
    pr_number = pr["number"]
    pr_url = pr.get("html_url") or ""
    branch_id = branch_identifier(branch)
    if not branch_id:
        return {"pr": pr_number, "branch": branch, "result": "skipped", "reason": "no-branch-identifier"}

    commits_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/commits?per_page=100"
    commits = gh_paginated("GET", commits_url, token)
    offenders = offending_commits(branch_id, commits)
    if not offenders:
        return {
            "pr": pr_number,
            "branch": branch,
            "branch_id": branch_id,
            "result": "clean",
            "commits_inspected": len(commits),
        }

    if dry_run:
        return {
            "pr": pr_number,
            "branch": branch,
            "branch_id": branch_id,
            "result": "scope-creep",
            "offenders": offenders,
            "action": "dry-run",
        }

    if not comment_already_posted(owner, repo, pr_number, token):
        ensure_label(owner, repo, token)
        post_pr_comment(owner, repo, pr_number, branch, branch_id, offenders, token)
        apply_label(owner, repo, pr_number, token)
        comment_action = "posted"
    else:
        comment_action = "already-posted"

    paperclip_action = "skipped"
    if paperclip_cfg is not None:
        foreign_ids = sorted({fid for o in offenders for fid in o["foreign"] if fid != branch_id})
        for fid in foreign_ids:
            try:
                notify_paperclip(
                    fid,
                    pr_url,
                    branch,
                    [o for o in offenders if fid in o["foreign"]],
                    **paperclip_cfg,
                )
                paperclip_action = "notified"
            except GitHubError as exc:
                paperclip_action = f"error: {exc}"

    return {
        "pr": pr_number,
        "branch": branch,
        "branch_id": branch_id,
        "result": "scope-creep",
        "offenders": offenders,
        "comment_action": comment_action,
        "paperclip_action": paperclip_action,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner", default=DEFAULT_OWNER)
    p.add_argument("--repo", default=DEFAULT_REPO)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true", help="JSON summary to stdout")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GH_TOKEN (or GITHUB_TOKEN) is required.", file=sys.stderr)
        return 1

    pc_url = os.environ.get("PAPERCLIP_API_URL")
    pc_key = os.environ.get("PAPERCLIP_API_KEY")
    pc_company = os.environ.get("PAPERCLIP_COMPANY_ID")
    pc_run_id = os.environ.get("PAPERCLIP_RUN_ID", "pr-scope-check")
    paperclip_cfg = None
    if pc_url and pc_key and pc_company:
        paperclip_cfg = {
            "base_url": pc_url,
            "api_key": pc_key,
            "company_id": pc_company,
            "run_id": pc_run_id,
        }

    list_url = (
        f"https://api.github.com/repos/{args.owner}/{args.repo}/pulls"
        "?state=open&per_page=100"
    )
    try:
        prs = gh_paginated("GET", list_url, token)
    except GitHubError as exc:
        print(f"ERROR: cannot list PRs: {exc}", file=sys.stderr)
        return 1

    results: list[dict] = []
    for pr in prs:
        if pr.get("draft"):
            continue
        try:
            res = check_pr(
                pr,
                owner=args.owner,
                repo=args.repo,
                token=token,
                dry_run=args.dry_run,
                paperclip_cfg=paperclip_cfg,
            )
        except GitHubError as exc:
            res = {
                "pr": pr.get("number"),
                "branch": (pr.get("head") or {}).get("ref"),
                "result": "error",
                "error": str(exc),
            }
        results.append(res)

    creeps = [r for r in results if r.get("result") == "scope-creep"]
    summary = {
        "owner": args.owner,
        "repo": args.repo,
        "open_prs": len(results),
        "scope_creep": len(creeps),
        "dry_run": args.dry_run,
        "paperclip_notify": paperclip_cfg is not None,
        "results": results,
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            f"pr-scope-check: scanned {len(results)} open PR(s), "
            f"flagged {len(creeps)}"
            + (" (dry-run)" if args.dry_run else "")
        )
        for r in results:
            if r.get("result") == "scope-creep":
                offs = ", ".join(
                    f"{o['sha'][:12]}→{','.join(o['foreign'])}" for o in r["offenders"]
                )
                print(f"  PR #{r['pr']} {r['branch']} (id={r['branch_id']}): {offs}")
            elif r.get("result") == "error":
                print(f"  PR #{r['pr']} {r['branch']}: ERROR {r['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
