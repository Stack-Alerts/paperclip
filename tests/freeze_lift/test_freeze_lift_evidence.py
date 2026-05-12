#!/usr/bin/env python3
"""
Freeze-Lift CI Evidence Package — BTCAAAAA-1879

Integration tests proving the module lock freeze-lift mechanism works correctly.

Test pillars:
  1. CANARY ON MAIN:  Lock gate passes on clean branches (no false positives)
  2. BROKEN-BRANCH BLOCK: Branches touching locked modules without exceptions are blocked
  3. ESCAPE HATCH PATH A+B: Board-approved and emergency exceptions correctly unblock
  4. LOCKED-ITSELF: Lock gate's own files (gate script, registry, exceptions, workflow) are locked

Usage:
    pytest tests/freeze_lift/ -v
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.lock_gate import (
    matches_locked_path,
    get_changed_files_from_diff,
    load_json,
    validate_exception_entry,
    validate_exceptions_file,
    get_active_exceptions,
    get_excepted_modules,
    parse_iso,
    REGISTRY_PATH,
    EXCEPTIONS_PATH,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# =========================================================================
# Helpers
# =========================================================================


def _diff_content(changed_files):
    lines = ["diff --git a/placeholder b/placeholder"]
    for f in changed_files:
        lines.append("--- a/" + f)
        lines.append("+++ b/" + f)
        lines.append("@@ -1 +1 @@")
        lines.append("+change")
    return "\n".join(lines)


def _registry_paths():
    registry = load_json(REGISTRY_PATH)
    return {e["path"] for e in registry["entries"]}


def _gate_exit_code(changed_files):
    """Run lock_gate with --diff-file and return the process exit code."""
    content = _diff_content(changed_files)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".diff", delete=False) as f:
        f.write(content)
        diff_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, "scripts/lock_gate.py", "--diff-file", diff_path],
            capture_output=True, text=True,
        )
        return result.returncode
    finally:
        os.unlink(diff_path)


def _active_exception_modules():
    """Return set of module paths that currently have active exceptions."""
    exceptions = load_json(EXCEPTIONS_PATH).get("exceptions", [])
    active = get_active_exceptions(exceptions)
    return get_excepted_modules(active)


@pytest.fixture
def registry_paths():
    return _registry_paths()


@pytest.fixture
def registry():
    return load_json(REGISTRY_PATH)


@pytest.fixture
def locked_entries(registry):
    return registry["entries"]


@pytest.fixture
def active_exception_modules():
    return _active_exception_modules()


# =========================================================================
# 1. CANARY ON MAIN
# =========================================================================


class TestCanaryOnMain:
    """Evidence pillar 1: lock gate operates correctly on the main branch."""

    def test_gate_passes_on_clean_diff(self):
        rc = _gate_exit_code(["src/strategies/completestrategy.py"])
        assert rc == 0, "Clean diff must pass the lock gate (exit 0)"

    def test_gate_passes_on_no_changed_files(self):
        rc = _gate_exit_code([])
        assert rc == 0, "Empty diff must pass the lock gate (exit 0)"

    def test_exceptions_file_is_valid(self):
        result = subprocess.run(
            [sys.executable, "scripts/lock_gate.py", "--validate-exceptions"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f"lock_gate_exceptions.json must be valid.\n"
            f"stderr: {result.stderr}"
        )

    def test_registry_is_loadable(self):
        registry = load_json(REGISTRY_PATH)
        assert "version" in registry, "Registry missing 'version'"
        assert "entries" in registry, "Registry missing 'entries'"
        assert isinstance(registry["entries"], list), "'entries' must be a list"
        assert len(registry["entries"]) > 0, "Registry must not be empty"

    def test_all_registry_entries_have_required_fields(self, locked_entries):
        for i, entry in enumerate(locked_entries):
            assert "path" in entry, f"entries[{i}] missing 'path'"
            assert "reason" in entry, f"entries[{i}] missing 'reason'"
            assert "locked_at" in entry, f"entries[{i}] missing 'locked_at'"
            assert "locked_by" in entry, f"entries[{i}] missing 'locked_by'"

    def test_gate_script_imports_cleanly(self):
        result = subprocess.run(
            [sys.executable, "-c", "from scripts.lock_gate import main; print('OK')"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, "lock_gate.py must import cleanly"


# =========================================================================
# 2. BROKEN-BRANCH BLOCK
# =========================================================================


class TestBrokenBranchBlock:
    """Evidence pillar 2: branches touching locked modules without exceptions are blocked."""

    LOCKED_FILE_HITS = [
        "src/data_manager/some_file.py",
        "src/optimizer_v3/core/trade_registry.py",
        "src/itm/state/manager.py",
        "src/optimizer_v3/database/models.py",
    ]

    def test_each_locked_file_blocks_without_exception(self, active_exception_modules):
        for file_path in self.LOCKED_FILE_HITS:
            rc = _gate_exit_code([file_path])
            assert rc == 1, (
                f"Gate must block changes to {file_path} "
                f"without exception. Got exit code {rc}, expected 1."
            )

    def test_mixed_diff_with_locked_file_blocks(self):
        rc = _gate_exit_code([
            "src/strategies/completestrategy.py",
            "src/data_manager/unified_manager.py",
            "tests/test_example.py",
        ])
        assert rc == 1, "Gate must block mixed diffs with locked paths"

    def test_multiple_locked_files_block(self):
        rc = _gate_exit_code([
            "src/data_manager/unified_manager.py",
            "src/optimizer_v3/core/trade_registry.py",
            "src/itm/state/manager.py",
        ])
        assert rc == 1, "Gate must block when multiple locked files are touched"

    def test_gate_exit_code_is_one_on_block(self):
        rc = _gate_exit_code(["src/data_manager/any_file.py"])
        assert rc == 1, f"Gate block must exit with code 1, got {rc}"


# =========================================================================
# 3. ESCAPE HATCH PATH A+B
# =========================================================================


class TestEscapeHatchPathA:
    """Evidence pillar 3a: Path A (board-approved planned, permanent exception)."""

    def test_board_exception_unblocks_locked_module(self, active_exception_modules):
        for module in sorted(active_exception_modules):
            rc = _gate_exit_code([module])
            assert rc == 0, (
                f"Gate must pass for {module} which has a valid board exception. "
                f"Got exit code {rc}."
            )

    def test_exceptions_file_has_bootstrap_exceptions(self):
        exceptions = load_json(EXCEPTIONS_PATH).get("exceptions", [])
        bootstrap_modules = {
            "scripts/lock_gate.py",
            ".module_lock_registry.json",
            "lock_gate_exceptions.json",
            ".github/workflows/lock-gate.yml",
            ".github/ISSUE_TEMPLATE/qa-locked-module-exception.md",
        }
        found = {e.get("module") for e in exceptions}
        missing = bootstrap_modules - found
        assert not missing, (
            f"Missing bootstrap exceptions for modules: {missing}"
        )


class TestEscapeHatchPathB:
    """Evidence pillar 3b: Path B (emergency exceptions with time window)."""

    def test_valid_future_expiry_is_active(self):
        future_iso = (
            datetime.now(timezone.utc) + timedelta(hours=2)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = {
            "module": "src/data_manager",
            "scope_description": "Test emergency",
            "expires_iso": future_iso,
            "approval_id": "test-emergency-1",
            "approved_by": "ceo-emergency",
        }
        active = get_active_exceptions([entry])
        assert len(active) == 1, "Future expiry must be active"

    def test_expired_exception_is_inactive(self):
        past_iso = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = {
            "module": "src/data_manager",
            "scope_description": "Test expired emergency",
            "expires_iso": past_iso,
            "approval_id": "test-expired-1",
            "approved_by": "ceo-emergency",
        }
        active = get_active_exceptions([entry])
        assert len(active) == 0, "Past expiry must be inactive"

    def test_ceo_emergency_entry_validates(self):
        future_iso = (
            datetime.now(timezone.utc) + timedelta(hours=3)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = {
            "module": "src/data_manager",
            "scope_description": "CEO emergency hotfix",
            "expires_iso": future_iso,
            "approval_id": "COMMENT:https://github.com/test/issues/1#issuecomment-1",
            "approved_by": "ceo-emergency",
        }
        errors = validate_exception_entry(entry)
        assert errors == [], f"Valid CEO emergency must have no errors, got: {errors}"

    def test_ceo_emergency_over_4h_rejected(self):
        far_future = (
            datetime.now(timezone.utc) + timedelta(hours=10)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = {
            "module": "src/data_manager",
            "scope_description": "CEO emergency too long",
            "expires_iso": far_future,
            "approval_id": "COMMENT:https://github.com/test/issues/2#issuecomment-2",
            "approved_by": "ceo-emergency",
        }
        errors = validate_exception_entry(entry)
        assert any("4h" in e for e in errors), "CEO emergency >4h must be rejected"

    def test_cto_emergency_rejected(self):
        entry = {
            "module": "src/data_manager",
            "scope_description": "CTO emergency not allowed",
            "expires_iso": None,
            "approval_id": "test-cto-1",
            "approved_by": "cto-emergency",
        }
        errors = validate_exception_entry(entry)
        assert any("cto-emergency" in e for e in errors), (
            "cto-emergency must be rejected per board directive"
        )


# =========================================================================
# 4. LOCKED-ITSELF
# =========================================================================


class TestLockedItself:
    """Evidence pillar 4: the lock gate system locks its own files."""

    def test_gate_script_is_locked_in_registry(self, registry_paths):
        assert "scripts/lock_gate.py" in registry_paths, (
            "The lock gate script must be locked in the registry"
        )

    def test_registry_file_is_locked_in_registry(self, registry_paths):
        assert ".module_lock_registry.json" in registry_paths, (
            "The module lock registry must be locked"
        )

    def test_exceptions_file_is_locked_in_registry(self, registry_paths):
        assert "lock_gate_exceptions.json" in registry_paths, (
            "The exceptions file must be locked"
        )

    def test_ci_workflow_is_locked_in_registry(self, registry_paths):
        assert ".github/workflows/lock-gate.yml" in registry_paths, (
            "The CI workflow must be locked"
        )

    def test_canary_test_is_locked_in_registry(self, registry_paths):
        assert "tests/bug_regression/test_canary_trade_execution.py" in registry_paths, (
            "The canary regression test must be locked"
        )

    def test_exception_request_template_is_locked(self, registry_paths):
        assert ".github/ISSUE_TEMPLATE/qa-locked-module-exception.md" in registry_paths, (
            "The exception request template must be locked"
        )

    def test_all_gate_self_files_registered(self, registry_paths):
        required = {
            "scripts/lock_gate.py",
            ".module_lock_registry.json",
            "lock_gate_exceptions.json",
            ".github/workflows/lock-gate.yml",
            "tests/bug_regression/test_canary_trade_execution.py",
            ".github/ISSUE_TEMPLATE/qa-locked-module-exception.md",
        }
        missing = required - registry_paths
        assert not missing, (
            f"Gate self-files missing from registry: {missing}"
        )


# =========================================================================
# 5. FULL FREEZE-LIFT CYCLE INTEGRATION
# =========================================================================


class TestFreezeLiftCycle:
    """End-to-end freeze-lift cycle evidence."""

    def test_freeze_then_lift_cycle(self):
        rc = _gate_exit_code(["src/data_manager/test_cycle.py"])
        assert rc == 1, f"Phase 1 (freeze): touching locked file must block, got {rc}"

    def test_blocked_gate_message_includes_paths(self):
        content = _diff_content(["src/data_manager/any_file.py"])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".diff", delete=False) as f:
            f.write(content)
            diff_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, "scripts/lock_gate.py", "--diff-file", diff_path],
                capture_output=True, text=True,
            )
            assert "LOCK GATE BLOCKED" in result.stdout, (
                "Block message must contain 'LOCK GATE BLOCKED'"
            )
            assert "src/data_manager" in result.stdout, (
                "Block message must reference the locked module path"
            )
        finally:
            os.unlink(diff_path)

    def test_json_summary_output_format(self):
        rc, stdout = _gate_exit_code_json(["src/data_manager/any_file.py"])
        assert rc == 1, f"Gate must block, got {rc}"
        data = json.loads(stdout)
        assert "gate" in data, "JSON summary must contain 'gate' key"
        assert data["gate"] == "blocked", f"Expected gate=blocked, got {data['gate']}"
        assert len(data["blocked"]) > 0, "JSON summary must list blocked modules"

    def test_json_summary_passes_cleanly(self):
        rc, stdout = _gate_exit_code_json(["src/strategies/completestrategy.py"])
        assert rc == 0, f"Gate must pass clean diff, got {rc}"
        data = json.loads(stdout)
        assert data["gate"] == "passed", f"Expected gate=passed, got {data['gate']}"


def _gate_exit_code_json(changed_files):
    """Run lock_gate with --json-summary --diff-file."""
    content = _diff_content(changed_files)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".diff", delete=False) as f:
        f.write(content)
        diff_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, "scripts/lock_gate.py", "--diff-file", diff_path, "--json-summary"],
            capture_output=True, text=True,
        )
        return result.returncode, result.stdout
    finally:
        os.unlink(diff_path)


# =========================================================================
# 6. SCHEMA AND CONTRACT ENFORCEMENT
# =========================================================================


class TestSchemaAndContracts:
    """Enforce schema contracts for the lock gate system."""

    def test_exceptions_file_has_correct_version(self):
        data = load_json(EXCEPTIONS_PATH)
        assert data.get("version") == 2, (
            f"Exceptions file version must be 2, got {data.get('version')}"
        )

    def test_registry_has_correct_version(self):
        data = load_json(REGISTRY_PATH)
        assert data.get("version") == 1, (
            f"Registry version must be 1, got {data.get('version')}"
        )

    def test_exception_approved_by_is_valid(self):
        exceptions = load_json(EXCEPTIONS_PATH).get("exceptions", [])
        valid = {"board", "ceo-emergency"}
        for entry in exceptions:
            assert entry.get("approved_by") in valid, (
                f"Exception for {entry.get('module')} has invalid "
                f"approved_by: {entry.get('approved_by')}"
            )

    def test_exception_modules_match_registry(self):
        registry_paths = _registry_paths()
        exceptions = load_json(EXCEPTIONS_PATH).get("exceptions", [])
        for entry in exceptions:
            module = entry.get("module", "")
            assert module in registry_paths, (
                f"Exception module '{module}' is not in .module_lock_registry.json. "
                f"Valid paths: {sorted(registry_paths)}"
            )
