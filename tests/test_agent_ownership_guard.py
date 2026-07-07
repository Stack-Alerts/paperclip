"""Tests for the agent-ownership section guard (BTCAAAAA-38995).

Verifies the soft, reversible confinement guard:
  - blocks an out-of-scope write and emits the CTO escalation message,
  - allows in-scope writes (no false-positives),
  - respects the AGENT_OWNERSHIP_BYPASS escape hatch,
  - warns (does not block) when the acting agent cannot be resolved,
  - validates the shipped manifest structure and its section coverage.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD = REPO_ROOT / "scripts" / "agent_ownership_guard.py"
MANIFEST = REPO_ROOT / "agent_ownership.json"


def run_guard(args, env_extra=None):
    env = {"PATH": os.environ.get("PATH", "")}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(GUARD), *args],
        capture_output=True, text=True, env=env,
    )


def test_blocks_out_of_scope_write_and_emits_escalation():
    # DataEngineer owns src/data_manager only; editing src/api is out of scope.
    res = run_guard(
        ["--paths", "src/api/server.py"],
        env_extra={"AGENT_OWNERSHIP_ROLE": "DataEngineer"},
    )
    assert res.returncode == 1, res.stdout + res.stderr
    assert "WRITE BLOCKED" in res.stdout
    out = res.stdout.lower()
    # Phase 2: the block points at the one-command CTO escalation path.
    assert "escalation" in out and "cto" in out
    assert "escalate_cross_section.py" in out
    # names the true owner to help the actor route the escalation
    assert "PlatformEngineer" in res.stdout


def test_allows_in_scope_write():
    res = run_guard(
        ["--paths", "src/data_manager/loader.py"],
        env_extra={"AGENT_OWNERSHIP_ROLE": "DataEngineer"},
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "in scope" in res.stdout


def test_ui_engineer_owns_web_ui_panels():
    res = run_guard(
        ["--paths", "packages/web-ui/app/backtest/page.tsx"],
        env_extra={"AGENT_OWNERSHIP_ROLE": "UIEngineer"},
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_mixed_batch_blocks_on_any_out_of_scope():
    res = run_guard(
        ["--paths", "src/data_manager/loader.py", "docs/readme.md"],
        env_extra={"AGENT_OWNERSHIP_ROLE": "DataEngineer"},
    )
    assert res.returncode == 1
    assert "docs/readme.md" in res.stdout


def test_override_role_owns_everything():
    res = run_guard(
        ["--paths", "src/api/server.py", "alembic/versions/x.py"],
        env_extra={"AGENT_OWNERSHIP_ROLE": "CTO"},
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_bypass_env_skips_guard():
    res = run_guard(
        ["--paths", "src/api/server.py"],
        env_extra={"AGENT_OWNERSHIP_ROLE": "DataEngineer", "AGENT_OWNERSHIP_BYPASS": "1"},
    )
    assert res.returncode == 0
    assert "guard skipped" in res.stderr


def test_unresolved_agent_warns_but_allows():
    # No role env, no PAPERCLIP_AGENT_ID -> 'warn' policy allows.
    res = run_guard(["--paths", "src/api/server.py"])
    assert res.returncode == 0
    assert "could not resolve" in res.stderr


def test_agent_id_map_resolution():
    manifest = json.loads(MANIFEST.read_text())
    aid = next(iter(manifest["agent_id_map"]))  # CTO id -> override
    res = run_guard(
        ["--paths", "src/api/server.py"],
        env_extra={"PAPERCLIP_AGENT_ID": aid},
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_diff_file_mode(tmp_path):
    diff = tmp_path / "sample.diff"
    diff.write_text(
        "diff --git a/src/api/server.py b/src/api/server.py\n"
        "--- a/src/api/server.py\n"
        "+++ b/src/api/server.py\n"
    )
    res = run_guard(
        ["--diff-file", str(diff)],
        env_extra={"AGENT_OWNERSHIP_ROLE": "DataEngineer"},
    )
    assert res.returncode == 1
    assert "src/api/server.py" in res.stdout


def test_manifest_validates():
    res = run_guard(["--validate"])
    assert res.returncode == 0, res.stdout + res.stderr
    assert "valid" in res.stdout


def test_manifest_covers_every_table_role():
    manifest = json.loads(MANIFEST.read_text())
    required = {
        "UIEngineer", "PlatformEngineer", "DataEngineer", "StrategyResearcher",
        "BacktestAnalyst", "NautilusEngineer", "AutomationEngineer",
        "DatabaseAdministrator", "DocWriter", "RepoSteward", "LinuxSpecialist",
    }
    assert required.issubset(set(manifest["agents"]))


def test_manifest_covers_every_active_src_section():
    """Every section named in the ownership table maps to some non-override
    owner, so the guard has no blind spots on the confinement-targeted paths."""
    manifest = json.loads(MANIFEST.read_text())
    sections = [
        "src/api/x.py", "src/data_manager/x.py", "src/strategies/x.py",
        "src/optimizer_v3/x.py", "src/detectors/x.py", "src/indicators/x.py",
        "src/strategy_builder/x.py", "src/itm/x.py", "src/impact_gate/x.py",
        "src/blast_radius/x.py", "src/touch_index/x.py", "src/debugger_logger/x.py",
        "alembic/x.py", "docs/x.md", "deploy/x.yml", "scripts/x.py",
        ".github/workflows/x.yml", "packages/web-ui/app/dashboard/x.tsx",
    ]

    # reuse the guard's matcher for parity with runtime behaviour
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import agent_ownership_guard as g  # noqa: E402

    for path in sections:
        owners = [
            role for role, spec in manifest["agents"].items()
            if role not in ("CTO", "Architect")
            and g.path_matches(path, spec.get("owns", []))
        ]
        assert owners, f"no non-override owner for section path {path}"
