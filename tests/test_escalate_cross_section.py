"""Tests for the cross-section escalation helper (BTCAAAAA-38996).

Offline coverage of the one-command CTO escalation path:
  - resolves the owning section for out-of-scope paths,
  - assigns the child to the CTO by default (owner on request),
  - renders the child-issue payload + blocked-by PATCH in --dry-run without any
    network calls,
  - keeps agent_id_map complete enough to resolve every non-override owner.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "escalate_cross_section.py"
MANIFEST = REPO_ROOT / "agent_ownership.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import escalate_cross_section as esc  # noqa: E402


def _manifest():
    return json.loads(MANIFEST.read_text())


def run_dry(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--dry-run"],
        capture_output=True, text=True,
        env={"PATH": os.environ.get("PATH", ""), "PAPERCLIP_COMPANY_ID": "test-co"},
    )


def test_resolve_owner_maps_alembic_to_dba():
    role, _ = esc.resolve_owner(_manifest(), ["alembic/versions/0001_add_col.py"])
    assert role == "DatabaseAdministrator"


def test_resolve_owner_maps_api_to_platform():
    role, _ = esc.resolve_owner(_manifest(), ["src/api/server.py"])
    assert role in ("PlatformEngineer", "AutomationEngineer")


def test_resolve_owner_none_for_unassigned_path():
    role, _ = esc.resolve_owner(_manifest(), ["some/unowned/path.py"])
    assert role is None


def test_role_to_agent_id_reverse_lookup():
    m = _manifest()
    cto_id = esc._role_to_agent_id(m, "CTO")
    assert cto_id and m["agent_id_map"][cto_id] == "CTO"
    dba_id = esc._role_to_agent_id(m, "DatabaseAdministrator")
    assert dba_id and m["agent_id_map"][dba_id] == "DatabaseAdministrator"


def test_dry_run_renders_dba_child_assigned_to_cto():
    res = run_dry(["--issue", "BTCAAAAA-999", "--paths",
                   "alembic/versions/0001_add_col.py",
                   "--summary", "WebUI needs a nullable column",
                   "--requesting-role", "UIEngineer"])
    assert res.returncode == 0, res.stdout + res.stderr
    assert "DatabaseAdministrator" in res.stdout
    # default assignment is to the CTO, who then delegates
    cto_id = esc._role_to_agent_id(_manifest(), "CTO")
    assert cto_id in res.stdout
    assert "blocked" in res.stdout
    assert "blockedByIssueIds" in res.stdout


def test_dry_run_assign_owner_targets_owner_agent():
    res = run_dry(["--issue", "BTCAAAAA-999", "--paths",
                   "alembic/versions/0001_add_col.py", "--assign", "owner"])
    assert res.returncode == 0, res.stdout + res.stderr
    dba_id = esc._role_to_agent_id(_manifest(), "DatabaseAdministrator")
    assert dba_id in res.stdout


def test_unresolved_owner_exits_nonzero():
    res = run_dry(["--issue", "BTCAAAAA-999", "--paths", "some/unowned/path.py"])
    assert res.returncode == 1
    assert "no owning section" in (res.stdout + res.stderr).lower()


def test_build_child_issue_is_surgical_and_traceable():
    m = _manifest()
    title, desc, prio = esc.build_child_issue(
        m, "BTCAAAAA-999", "UIEngineer", "DatabaseAdministrator",
        ["alembic/versions/0001_add_col.py"], "add a column", "medium",
    )
    assert "DatabaseAdministrator" in title
    assert "CTO verifies" in desc and "releases the blocker" in desc
    assert "surgical" in desc.lower()
    assert prio == "medium"


def test_agent_id_map_resolves_every_non_override_owner():
    m = _manifest()
    mapped_roles = set(m["agent_id_map"].values())
    for role, spec in m["agents"].items():
        if role in ("CTO", "Architect"):
            continue
        # every ownable role the escalation could delegate to must have an id
        assert role in mapped_roles, f"{role} missing from agent_id_map"
