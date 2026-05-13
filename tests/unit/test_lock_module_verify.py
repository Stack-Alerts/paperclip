"""Unit tests for scripts/lock_module_verify.py."""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.lock_module_verify import (
    get_changed_files_from_diff,
    find_affected_locked_modules,
    find_verification_tests,
    matches_locked_path,
    render_markdown_report,
    load_json,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCK_REGISTRY_PATH = REPO_ROOT / ".module_lock_registry.json"
VERIFY_REGISTRY_PATH = REPO_ROOT / "lock_module_verification_registry.json"


# --- fixtures ---

@pytest.fixture
def lock_registry():
    return load_json(LOCK_REGISTRY_PATH)


@pytest.fixture
def locked_entries(lock_registry):
    return lock_registry["entries"]


@pytest.fixture
def verification_registry():
    if VERIFY_REGISTRY_PATH.exists():
        return load_json(VERIFY_REGISTRY_PATH)
    return {"version": 1, "mappings": []}


CLEAN_DIFF = """\
diff --git a/src/strategies/completestrategy.py b/src/strategies/completestrategy.py
index abc123..def456 100644
--- a/src/strategies/completestrategy.py
+++ b/src/strategies/completestrategy.py
@@ -1,5 +1,6 @@
 # Complete Strategy
+print("hello")
"""

HIT_DIFF = """\
diff --git a/src/data_manager/unified_manager.py b/src/data_manager/unified_manager.py
index abc123..def456 100644
--- a/src/data_manager/unified_manager.py
+++ b/src/data_manager/unified_manager.py
@@ -1,5 +1,6 @@
 # Unified Data Manager
+print("hello")
"""

CANARY_DIFF = """\
diff --git a/tests/bug_regression/test_canary_trade_execution.py b/tests/bug_regression/test_canary_trade_execution.py
index abc123..def456 100644
--- a/tests/bug_regression/test_canary_trade_execution.py
+++ b/tests/bug_regression/test_canary_trade_execution.py
@@ -1,5 +1,6 @@
 # Canary Test
+print("update")
"""


@pytest.fixture
def clean_diff_path(tmp_path):
    p = tmp_path / "clean.diff"
    p.write_text(CLEAN_DIFF)
    return str(p)


@pytest.fixture
def hit_diff_path(tmp_path):
    p = tmp_path / "hit.diff"
    p.write_text(HIT_DIFF)
    return str(p)


@pytest.fixture
def canary_diff_path(tmp_path):
    p = tmp_path / "canary.diff"
    p.write_text(CANARY_DIFF)
    return str(p)


# --- get_changed_files_from_diff tests ---

class TestGetChangedFilesFromDiff:
    def test_clean_diff(self, clean_diff_path):
        files = get_changed_files_from_diff(clean_diff_path)
        assert "src/strategies/completestrategy.py" in files

    def test_hit_diff(self, hit_diff_path):
        files = get_changed_files_from_diff(hit_diff_path)
        assert "src/data_manager/unified_manager.py" in files

    def test_canary_diff(self, canary_diff_path):
        files = get_changed_files_from_diff(canary_diff_path)
        assert "tests/bug_regression/test_canary_trade_execution.py" in files


# --- matches_locked_path tests (delegated to lock_gate.py, but verify integration) ---

class TestMatchesLockedPath:
    def test_data_manager_dir_match(self, locked_entries):
        entry = matches_locked_path("src/data_manager/unified_manager.py", locked_entries)
        assert entry is not None
        assert entry["path"] == "src/data_manager"

    def test_data_manager_nested_match(self, locked_entries):
        entry = matches_locked_path("src/data_manager/binance/rest_client.py", locked_entries)
        assert entry is not None
        assert entry["path"] == "src/data_manager"

    def test_trade_registry_match(self, locked_entries):
        entry = matches_locked_path("src/optimizer_v3/core/trade_registry.py", locked_entries)
        assert entry is not None
        assert entry["path"] == "src/optimizer_v3/core/trade_registry.py"

    def test_canary_match(self, locked_entries):
        entry = matches_locked_path("tests/bug_regression/test_canary_trade_execution.py", locked_entries)
        assert entry is not None
        assert entry["path"] == "tests/bug_regression/test_canary_trade_execution.py"

    def test_no_match_unlocked(self, locked_entries):
        entry = matches_locked_path("src/strategies/completestrategy.py", locked_entries)
        assert entry is None

    def test_lock_gate_script_match(self, locked_entries):
        entry = matches_locked_path("scripts/lock_gate.py", locked_entries)
        assert entry is not None
        assert entry["path"] == "scripts/lock_gate.py"


# --- find_affected_locked_modules tests ---

class TestFindAffectedLockedModules:
    def test_clean_diff_no_hits(self, lock_registry):
        changed = ["src/strategies/completestrategy.py"]
        hits = find_affected_locked_modules(changed, lock_registry)
        assert hits == []

    def test_hit_diff_finds_data_manager(self, lock_registry):
        changed = ["src/data_manager/unified_manager.py"]
        hits = find_affected_locked_modules(changed, lock_registry)
        assert len(hits) == 1
        assert hits[0]["locked_path"] == "src/data_manager"

    def test_multiple_hits(self, lock_registry):
        changed = [
            "src/data_manager/unified_manager.py",
            "src/optimizer_v3/core/trade_registry.py",
            "src/strategies/other.py",
        ]
        hits = find_affected_locked_modules(changed, lock_registry)
        assert len(hits) == 2
        paths = {h["locked_path"] for h in hits}
        assert "src/data_manager" in paths
        assert "src/optimizer_v3/core/trade_registry.py" in paths

    def test_deduplicates_same_locked_path(self, lock_registry):
        changed = [
            "src/data_manager/unified_manager.py",
            "src/data_manager/binance/rest_client.py",
        ]
        hits = find_affected_locked_modules(changed, lock_registry)
        assert len(hits) == 1
        assert hits[0]["locked_path"] == "src/data_manager"


# --- find_verification_tests tests ---

class TestFindVerificationTests:
    def test_data_manager_has_fr_test(self, verification_registry):
        test_map = find_verification_tests(["src/data_manager"], verification_registry)
        assert "src/data_manager" in test_map
        assert "FDR-850" in test_map["src/data_manager"]["fr_ids"]

    def test_trade_registry_has_bug_test(self, verification_registry):
        test_map = find_verification_tests(
            ["src/optimizer_v3/core/trade_registry.py"], verification_registry
        )
        assert "src/optimizer_v3/core/trade_registry.py" in test_map
        assert "BTCAAAAA-1476" in test_map["src/optimizer_v3/core/trade_registry.py"]["bug_ids"]

    def test_canary_has_test_paths(self, verification_registry):
        test_map = find_verification_tests(
            ["tests/bug_regression/test_canary_trade_execution.py"], verification_registry
        )
        assert "tests/bug_regression/test_canary_trade_execution.py" in test_map
        assert "tests/bug_regression/test_canary_trade_execution.py" in test_map["tests/bug_regression/test_canary_trade_execution.py"]["test_paths"]

    def test_lock_gate_script_has_unit_test(self, verification_registry):
        test_map = find_verification_tests(["scripts/lock_gate.py"], verification_registry)
        assert "scripts/lock_gate.py" in test_map
        assert "tests/unit/test_lock_gate.py" in test_map["scripts/lock_gate.py"]["test_paths"]

    def test_unmapped_module_returns_empty(self, verification_registry):
        test_map = find_verification_tests(["nonexistent/module.py"], verification_registry)
        assert "nonexistent/module.py" in test_map
        assert test_map["nonexistent/module.py"]["fr_ids"] == []
        assert test_map["nonexistent/module.py"]["bug_ids"] == []

    def test_multiple_modules(self, verification_registry):
        test_map = find_verification_tests(
            ["src/data_manager", "src/itm/state/manager.py"], verification_registry
        )
        assert len(test_map) == 2
        assert test_map["src/data_manager"]["fr_ids"] == ["FDR-850"]
        assert test_map["src/itm/state/manager.py"]["test_paths"] == ["tests/itm/state/"]


# --- render_markdown_report tests ---

class TestRenderMarkdownReport:
    def test_render_pass_report(self):
        result = {
            "timestamp": "2026-05-13T16:00:00Z",
            "overall_status": "PASS",
            "affected_modules": [
                {
                    "file_path": "src/data_manager/unified_manager.py",
                    "locked_path": "src/data_manager",
                    "reason": "UnifiedDataManager",
                }
            ],
            "test_mapping": {
                "src/data_manager": {"fr_ids": ["FDR-850"], "bug_ids": [], "test_paths": []},
            },
            "fr_bug_results": {
                "status": "PASS",
                "summary": {"passed": 1, "failed": 0, "errors": 0},
                "fr_results": {"FDR-850": {"status": "PASS", "test_file": "tests/fr_acceptance/test_fdr_850.py"}},
                "bug_results": {},
            },
            "pytest_path_results": {},
        }
        report = render_markdown_report(result)
        assert "Lock Module Verification Report" in report
        assert "PASS" in report
        assert "src/data_manager" in report
        assert "FDR-850" in report

    def test_render_fail_report(self):
        result = {
            "timestamp": "2026-05-13T16:00:00Z",
            "overall_status": "FAIL",
            "affected_modules": [
                {
                    "file_path": "src/optimizer_v3/core/trade_registry.py",
                    "locked_path": "src/optimizer_v3/core/trade_registry.py",
                    "reason": "TradeRegistry",
                }
            ],
            "test_mapping": {
                "src/optimizer_v3/core/trade_registry.py": {"fr_ids": [], "bug_ids": ["BTCAAAAA-1476"], "test_paths": []},
            },
            "fr_bug_results": {
                "status": "FAIL",
                "summary": {"passed": 0, "failed": 1, "errors": 0},
                "fr_results": {},
                "bug_results": {"BTCAAAAA-1476": {"status": "FAIL", "test_file": "tests/bug_regression/test_canary_trade_execution.py"}},
            },
            "pytest_path_results": {},
        }
        report = render_markdown_report(result)
        assert "Lock Module Verification Report" in report
        assert "FAIL" in report
        assert "BTCAAAAA-1476" in report

    def test_render_empty_report(self):
        result = {
            "timestamp": "2026-05-13T16:00:00Z",
            "overall_status": "PASS",
            "affected_modules": [],
            "test_mapping": {},
            "fr_bug_results": {},
            "pytest_path_results": {},
        }
        report = render_markdown_report(result)
        assert "Lock Module Verification Report" in report
        assert "PASS" in report


# --- end-to-end via --diff-file ---

class TestEndToEnd:
    def test_clean_diff_passes(self, clean_diff_path):
        rc = os.system(
            f"{sys.executable} scripts/lock_module_verify.py --diff-file {clean_diff_path}"
        )
        assert rc == 0, "clean diff should pass (no locked modules touched)"

    def test_hit_diff_identifies_locked(self, hit_diff_path):
        rc = os.system(
            f"{sys.executable} scripts/lock_module_verify.py --diff-file {hit_diff_path} --json"
        )
        # os.system encodes exit code in high byte; 0=pass, 256=fail (exit 1)
        # rc == 512 would mean exit code 2 (config error)
        assert rc in (0, 256), f"hit diff should not error on config (got rc={rc})"

    def test_json_output_is_valid(self, clean_diff_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/lock_module_verify.py", "--diff-file", clean_diff_path, "--json"],
            capture_output=True, text=True,
        )
        try:
            data = json.loads(result.stdout)
            assert "overall_status" in data
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.stdout[:500]}")
