#!/usr/bin/env python3
"""
Agent Ownership Guard — soft, reversible section confinement (BTCAAAAA-38995).

Blocks writes that fall outside the acting agent's owned path globs, as declared
in agent_ownership.json at the repo root. Complements .module_lock_registry.json:
the lock registry is a board-approval deny-list for a few critical files; this
guard is a per-agent allow-list for whole sections.

Acting-agent resolution order:
    1. AGENT_OWNERSHIP_ROLE env var (explicit role name)
    2. PAPERCLIP_AGENT_ROLE env var
    3. agent_id_map[PAPERCLIP_AGENT_ID] in the manifest

Bypass (single intentional out-of-scope operation):
    AGENT_OWNERSHIP_BYPASS=1

Usage:
    agent_ownership_guard.py --paths a/b.py c/d.py   # check explicit paths
    agent_ownership_guard.py --staged                # check git-staged files
    agent_ownership_guard.py --diff-file <path>      # check files in a diff (test)
    agent_ownership_guard.py --validate              # validate manifest structure only

Exit codes:
    0 — all paths in scope (or agent unresolved under 'warn' policy, or bypass)
    1 — at least one path out of the acting agent's scope (guard blocks)
    2 — manifest structural validation error / missing manifest
"""

import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "agent_ownership.json"


def load_manifest():
    if not MANIFEST_PATH.exists():
        print(f"agent-ownership: manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(2)
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def validate_manifest(manifest):
    """Return a list of structural error strings (empty = valid)."""
    errors = []
    if manifest.get("version") != 1:
        errors.append("'version' must be 1")
    agents = manifest.get("agents")
    if not isinstance(agents, dict) or not agents:
        errors.append("'agents' must be a non-empty object")
        return errors
    for role, spec in agents.items():
        if not isinstance(spec, dict):
            errors.append(f"agent '{role}' must be an object")
            continue
        owns = spec.get("owns")
        if not isinstance(owns, list):
            errors.append(f"agent '{role}' must have an 'owns' list")
            continue
        for glob in owns:
            if not isinstance(glob, str) or not glob:
                errors.append(f"agent '{role}' has an invalid glob: {glob!r}")
    policy = manifest.get("unlisted_agent_policy", "warn")
    if policy not in ("warn", "block"):
        errors.append("'unlisted_agent_policy' must be 'warn' or 'block'")
    id_map = manifest.get("agent_id_map", {})
    if not isinstance(id_map, dict):
        errors.append("'agent_id_map' must be an object")
    else:
        for aid, role in id_map.items():
            if role not in agents:
                errors.append(f"agent_id_map['{aid}'] -> unknown role '{role}'")
    return errors


def resolve_role(manifest):
    """Resolve the acting agent's role, or None if unresolved."""
    role = os.environ.get("AGENT_OWNERSHIP_ROLE") or os.environ.get("PAPERCLIP_AGENT_ROLE")
    if role:
        return role.strip()
    agent_id = os.environ.get("PAPERCLIP_AGENT_ID")
    if agent_id:
        return manifest.get("agent_id_map", {}).get(agent_id.strip())
    return None


def path_matches(path, globs):
    """True if repo-relative path matches any glob. '**' spans directories."""
    norm = path.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    for glob in globs:
        g = glob.replace("\\", "/")
        if fnmatch.fnmatch(norm, g):
            return True
        # A trailing '/**' should also match the directory itself and any file
        # directly beneath it; a trailing '/*' should match only direct children.
        if g.endswith("/**"):
            base = g[:-3]
            if norm == base or norm.startswith(base + "/"):
                return True
        if g.endswith("/*"):
            base = g[:-2]
            if norm.startswith(base + "/") and "/" not in norm[len(base) + 1:]:
                return True
    return False


def owned_globs(manifest, role):
    spec = manifest.get("agents", {}).get(role, {})
    return spec.get("owns", [])


def find_owners(manifest, path):
    """List of roles that own the given path (for escalation messaging)."""
    owners = []
    for role, spec in manifest.get("agents", {}).items():
        globs = [g for g in spec.get("owns", []) if g != "**"]
        if globs and path_matches(path, globs):
            owners.append(role)
    return owners


def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT,
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def get_files_from_diff(diff_path):
    changed = set()
    with open(diff_path) as f:
        for line in f:
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                p = line[6:].strip()
                if p and p != "/dev/null":
                    changed.add(p)
            elif line.startswith("diff --git a/"):
                parts = line.split()
                if len(parts) >= 4:
                    changed.add(parts[3][2:])
    return sorted(changed)


def print_block(manifest, role, violations):
    print("=" * 72)
    print("AGENT OWNERSHIP GUARD — WRITE BLOCKED (out-of-scope section edit)")
    print("=" * 72)
    print(f"\n  Acting agent: {role}")
    print(f"  Owned globs : {owned_globs(manifest, role) or '(none)'}")
    for path in violations:
        owners = find_owners(manifest, path) or ["(unassigned)"]
        print(f"\n  File : {path}")
        print(f"  Owner: {', '.join(owners)}")
    print()
    print(manifest.get("escalation_message", "Escalate to the CTO."))
    print("=" * 72)


def check_paths(manifest, paths):
    """Return an exit code. Prints block message + escalation on violation."""
    if os.environ.get("AGENT_OWNERSHIP_BYPASS") == "1":
        print("agent-ownership: AGENT_OWNERSHIP_BYPASS=1 — guard skipped.", file=sys.stderr)
        return 0

    role = resolve_role(manifest)
    if not role:
        policy = manifest.get("unlisted_agent_policy", "warn")
        msg = ("agent-ownership: could not resolve acting agent role "
               "(set AGENT_OWNERSHIP_ROLE or PAPERCLIP_AGENT_ID).")
        if policy == "block":
            print(msg + " Policy=block — refusing.", file=sys.stderr)
            return 1
        print(msg + " Policy=warn — allowing.", file=sys.stderr)
        return 0

    if role not in manifest.get("agents", {}):
        policy = manifest.get("unlisted_agent_policy", "warn")
        msg = f"agent-ownership: role '{role}' not in manifest."
        if policy == "block":
            print(msg + " Policy=block — refusing.", file=sys.stderr)
            return 1
        print(msg + " Policy=warn — allowing.", file=sys.stderr)
        return 0

    globs = owned_globs(manifest, role)
    violations = [p for p in paths if not path_matches(p, globs)]
    if violations:
        print_block(manifest, role, violations)
        return 1
    print(f"agent-ownership: {role}: all {len(paths)} path(s) in scope. OK.")
    return 0


def main():
    argv = sys.argv[1:]
    manifest = load_manifest()

    if "--validate" in argv:
        errors = validate_manifest(manifest)
        if errors:
            print("agent-ownership: manifest validation FAILED:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(2)
        print("agent-ownership: manifest is valid.")
        sys.exit(0)

    if "--paths" in argv:
        idx = argv.index("--paths")
        paths = [a for a in argv[idx + 1:] if not a.startswith("--")]
    elif "--staged" in argv:
        paths = get_staged_files()
    elif "--diff-file" in argv:
        idx = argv.index("--diff-file")
        paths = get_files_from_diff(argv[idx + 1])
    else:
        print(__doc__)
        sys.exit(2)

    if not paths:
        print("agent-ownership: no paths to check. OK.")
        sys.exit(0)

    sys.exit(check_paths(manifest, paths))


if __name__ == "__main__":
    main()
