#!/usr/bin/env python3
"""
Cross-Section Escalation Helper — one-command CTO escalation (BTCAAAAA-38996).

Turns an agent-ownership guard block into an auditable ticket trail:

    requesting agent needs an out-of-scope change
      -> guard blocks + points here
      -> this script creates a CTO-assigned child issue (owner section referenced)
      -> requesting issue is marked blocked-by that child
      -> CTO delegates to the owning agent -> owner implements + tests
      -> CTO verifies -> blocker released -> requesting work auto-resumes

Complements scripts/agent_ownership_guard.py (which decides *whether* a write is
out of scope) by giving the blocked agent a single command that produces the
surgical, traceable child issue the guard's message asks for.

Usage:
    escalate_cross_section.py --issue <requesting-issue-id-or-identifier> \\
        --paths alembic/versions/0123_add_col.py \\
        [--summary "WebUI signals form needs a nullable column"] \\
        [--requesting-role UIEngineer] \\
        [--priority medium] \\
        [--assign owner|cto] \\
        [--dry-run]

Environment (for live mode):
    PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID  (required)
    PAPERCLIP_RUN_ID                                            (audit header)

Exit codes:
    0 — child issue created (or dry-run rendered) and requesting issue blocked
    1 — bad arguments / owner unresolved / API error
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_ownership_guard import (  # noqa: E402
    find_owners,
    load_manifest,
    owned_globs,
)

CTO_ROLE = "CTO"


def _role_to_agent_id(manifest, role):
    for agent_id, mapped_role in manifest.get("agent_id_map", {}).items():
        if mapped_role == role:
            return agent_id
    return None


def _api(method, path, body=None):
    base = os.environ.get("PAPERCLIP_API_URL")
    key = os.environ.get("PAPERCLIP_API_KEY")
    if not base or not key:
        raise SystemExit("escalate: PAPERCLIP_API_URL and PAPERCLIP_API_KEY must be set for live mode.")
    url = base.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    run_id = os.environ.get("PAPERCLIP_RUN_ID")
    if run_id:
        req.add_header("X-Paperclip-Run-Id", run_id)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise SystemExit(f"escalate: API {method} {path} failed ({e.code}): {detail}")


def resolve_owner(manifest, paths):
    """Return (owner_role, owner_note) for the union of path owners, or (None, '')."""
    owners = []
    for p in paths:
        for role in find_owners(manifest, p):
            if role not in owners:
                owners.append(role)
    if not owners:
        return None, ""
    primary = owners[0]
    note = manifest.get("agents", {}).get(primary, {}).get("note", "")
    return primary, note


def build_child_issue(manifest, requesting_ref, requesting_role, owner_role, paths, summary, priority):
    owner_note = manifest.get("agents", {}).get(owner_role, {}).get("note", "")
    owner_globs = owned_globs(manifest, owner_role)
    path_list = "\n".join(f"- `{p}`" for p in paths)
    title = f"Cross-section change for {owner_role}: {paths[0]}"
    if len(paths) > 1:
        title += f" (+{len(paths) - 1} more)"
    description = f"""## Cross-section escalation (agent-ownership guard)

**Requesting agent:** {requesting_role or "(unresolved)"}
**Requesting issue:** {requesting_ref}
**Owning section:** {owner_role}

The requesting agent's work needs a change inside **{owner_role}**'s owned
section, which the agent-ownership guard (`agent_ownership.json` /
`scripts/agent_ownership_guard.py`) blocks. This surgical child issue carries
that change so it stays traceable and gated.

### Files / paths needed
{path_list}

### Requested change
{summary or "(describe the specific, minimal change required)"}

### Owner scope
- Owner globs: {owner_globs or "(none)"}
- {owner_note or ""}

### CTO-mediated loop
1. **CTO delegates** this issue to {owner_role} (reassign to the owning agent).
2. **{owner_role} implements + tests** the change *only within its owned scope*.
3. **CTO verifies** the change (tests green, scope respected) and marks this done.
4. Marking this issue `done` **releases the blocker** on the requesting issue,
   which auto-resumes.

Token-spend guardrail: keep this change surgical — the minimal edit the
requesting work needs, not a broad grant of the section.
"""
    return title, description, priority


def main():
    ap = argparse.ArgumentParser(description="One-command cross-section escalation to the CTO.")
    ap.add_argument("--issue", required=True, help="Requesting issue id or identifier (e.g. BTCAAAAA-123).")
    ap.add_argument("--paths", nargs="+", required=True, help="Out-of-scope path(s) the requesting work needs.")
    ap.add_argument("--summary", default="", help="Short description of the specific change needed.")
    ap.add_argument("--requesting-role", default=os.environ.get("AGENT_OWNERSHIP_ROLE")
                    or os.environ.get("PAPERCLIP_AGENT_ROLE"), help="Role of the requesting agent.")
    ap.add_argument("--priority", default="medium", choices=["critical", "high", "medium", "low"])
    ap.add_argument("--assign", default="cto", choices=["cto", "owner"],
                    help="Assign the child to the CTO (default; CTO then delegates) or straight to the owner.")
    ap.add_argument("--dry-run", action="store_true", help="Render payloads without calling the API.")
    args = ap.parse_args()

    manifest = load_manifest()
    owner_role, _ = resolve_owner(manifest, args.paths)
    if not owner_role:
        print(f"escalate: no owning section found for {args.paths}. "
              "These paths are unassigned — assign an owner in agent_ownership.json first, "
              "or escalate to the CTO manually.", file=sys.stderr)
        return 1

    title, description, priority = build_child_issue(
        manifest, args.issue, args.requesting_role, owner_role, args.paths, args.summary, args.priority,
    )

    cto_id = _role_to_agent_id(manifest, CTO_ROLE)
    owner_id = _role_to_agent_id(manifest, owner_role)
    assignee_id = owner_id if args.assign == "owner" else cto_id
    if not assignee_id:
        print(f"escalate: could not resolve an agent id for "
              f"{'owner ' + owner_role if args.assign == 'owner' else CTO_ROLE} "
              "in agent_ownership.json:agent_id_map.", file=sys.stderr)
        return 1

    company_id = os.environ.get("PAPERCLIP_COMPANY_ID")

    if args.dry_run:
        print("=== DRY RUN — no API calls made ===")
        print(f"Owner section resolved: {owner_role} (agent {owner_id})")
        print(f"Child assignee: {'owner' if args.assign == 'owner' else 'CTO'} ({assignee_id})")
        print("\n--- POST /api/companies/{companyId}/issues ---")
        print(json.dumps({
            "title": title, "description": description, "priority": priority,
            "assigneeAgentId": assignee_id, "parentId": args.issue, "status": "todo",
        }, indent=2))
        print("\n--- PATCH /api/issues/{requesting} ---")
        print(json.dumps({"status": "blocked", "blockedByIssueIds": ["<new-child-id>"]}, indent=2))
        return 0

    # Resolve the requesting issue to its uuid + gather current blockers.
    req = _api("GET", f"/api/issues/{args.issue}")
    req_issue = req.get("issue", req)
    req_id = req_issue.get("id")
    req_ident = req_issue.get("identifier", args.issue)
    existing_blockers = [b.get("id") for b in req_issue.get("blockedBy", []) if b.get("id")]

    created = _api("POST", f"/api/companies/{company_id}/issues", {
        "title": title, "description": description, "priority": priority,
        "assigneeAgentId": assignee_id, "parentId": req_id, "status": "todo",
    })
    child = created.get("issue", created)
    child_id = child.get("id")
    child_ident = child.get("identifier", child_id)

    _api("PATCH", f"/api/issues/{req_id}", {
        "status": "blocked",
        "blockedByIssueIds": sorted(set(existing_blockers + [child_id])),
        "comment": (f"Cross-section change escalated to the CTO as {child_ident} "
                    f"(owner: {owner_role}). This issue is now blocked-by that child "
                    "and will auto-resume when the CTO verifies + releases it."),
    })

    print(f"escalate: created child {child_ident} ({child_id}) assigned to "
          f"{'owner ' + owner_role if args.assign == 'owner' else CTO_ROLE}.")
    print(f"escalate: requesting issue {req_ident} ({req_id}) set blocked, blocked-by {child_ident}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
