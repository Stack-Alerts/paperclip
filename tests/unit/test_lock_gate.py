"""Unit tests for scripts/lock_gate.py."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.lock_gate import (
    matches_locked_path,
    get_changed_files_from_diff,
    load_json,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = REPO_ROOT / ".module_lock_registry.json"


@pytest.fixture
def registry():
    return load_json(REGISTRY_PATH)


@pytest.fixture
def locked_entries(registry):
    return registry["entries"]


# Test diff fixtures (as file paths via tmp_path)
HIT_DIFF_CONTENT = """\
diff --git a/src/data_manager/unified_manager.py b/src/data_manager/unified_manager.py
index abc123..def456 100644
--- a/src/data_manager/unified_manager.py
+++ b/src/data_manager/unified_manager.py
@@ -1,5 +1,6 @@
 # Unified Data Manager
+print("hello")
 class UnifiedDataManager:
     def __init__(self):
         pass
"""

CLEAN_DIFF_CONTENT = """\
diff --git a/src/strategies/completestrategy.py b/src/strategies/completestrategy.py
index abc123..def456 100644
--- a/src/strategies/completestrategy.py
+++ b/src/strategies/completestrategy.py
@@ -1,5 +1,6 @@
 # Complete Strategy
+print("hello")
 class CompleteStrategy:
     def __init__(self):
         pass
"""

MIXED_DIFF_CONTENT = """\
diff --git a/src/strategies/completestrategy.py b/src/strategies/completestrategy.py
index abc123..def456 100644
--- a/src/strategies/completestrategy.py
+++ b/src/strategies/completestrategy.py
@@ -1,5 +1,6 @@
 # Complete Strategy
 class CompleteStrategy:
     def __init__(self):
         pass
diff --git a/src/data_manager/unified_manager.py b/src/data_manager/unified_manager.py
index abc123..def456 100644
--- a/src/data_manager/unified_manager.py
+++ b/src/data_manager/unified_manager.py
@@ -1,5 +1,6 @@
 # Unified Data Manager
 class UnifiedDataManager:
     def __init__(self):
         pass
diff --git a/src/optimizer_v3/core/trade_registry.py b/src/optimizer_v3/core/trade_registry.py
index abc123..def456 100644
--- a/src/optimizer_v3/core/trade_registry.py
+++ b/src/optimizer_v3/core/trade_registry.py
@@ -1,5 +1,6 @@
 # Trade Registry
 class TradeRegistry:
     def __init__(self):
         pass
"""

EXCEPTION_DIFF_CONTENT = """\
diff --git a/scripts/lock_gate.py b/scripts/lock_gate.py
index abc123..def456 100644
--- a/scripts/lock_gate.py
+++ b/scripts/lock_gate.py
@@ -1,5 +1,6 @@
 # Lock Gate Script
+print("update")
 class LockGate:
     def __init__(self):
         pass
"""


@pytest.fixture
def hit_diff_path(tmp_path):
    p = tmp_path / "hit.diff"
    p.write_text(HIT_DIFF_CONTENT)
    return str(p)


@pytest.fixture
def clean_diff_path(tmp_path):
    p = tmp_path / "clean.diff"
    p.write_text(CLEAN_DIFF_CONTENT)
    return str(p)


@pytest.fixture
def mixed_diff_path(tmp_path):
    p = tmp_path / "mixed.diff"
    p.write_text(MIXED_DIFF_CONTENT)
    return str(p)


@pytest.fixture
def exception_diff_path(tmp_path):
    p = tmp_path / "exception.diff"
    p.write_text(EXCEPTION_DIFF_CONTENT)
    return str(p)


# --- get_changed_files_from_diff tests ---

class TestGetChangedFilesFromDiff:
    def test_hit_diff(self, hit_diff_path):
        files = get_changed_files_from_diff(hit_diff_path)
        assert "src/data_manager/unified_manager.py" in files

    def test_clean_diff(self, clean_diff_path):
        files = get_changed_files_from_diff(clean_diff_path)
        assert "src/strategies/completestrategy.py" in files
        assert not any("data_manager" in f for f in files)

    def test_mixed_diff(self, mixed_diff_path):
        files = get_changed_files_from_diff(mixed_diff_path)
        assert len(files) == 3
        assert "src/strategies/completestrategy.py" in files
        assert "src/data_manager/unified_manager.py" in files
        assert "src/optimizer_v3/core/trade_registry.py" in files

    def test_exception_diff(self, exception_diff_path):
        files = get_changed_files_from_diff(exception_diff_path)
        assert "scripts/lock_gate.py" in files


# --- matches_locked_path tests ---

class TestMatchesLockedPath:
    def test_direct_file_hit(self, locked_entries):
        entry = matches_locked_path(
            "src/optimizer_v3/core/trade_registry.py", locked_entries
        )
        assert entry is not None
        assert entry["path"] == "src/optimizer_v3/core/trade_registry.py"

    def test_directory_prefix_hit(self, locked_entries):
        entry = matches_locked_path(
            "src/data_manager/unified_manager.py", locked_entries
        )
        assert entry is not None
        assert entry["path"] == "src/data_manager"

    def test_directory_prefix_hit_nested(self, locked_entries):
        entry = matches_locked_path(
            "src/data_manager/binance/rest_client.py", locked_entries
        )
        assert entry is not None
        assert entry["path"] == "src/data_manager"

    def test_clean_path_no_hit(self, locked_entries):
        entry = matches_locked_path(
            "src/strategies/completestrategy.py", locked_entries
        )
        assert entry is None

    def test_locked_dir_slash_suffix(self, locked_entries):
        entry = matches_locked_path(
            "src/optimizer_v3/database/models.py", locked_entries
        )
        assert entry is not None
        assert entry["path"] == "src/optimizer_v3/database/"

    def test_system_file_hit(self, locked_entries):
        entry = matches_locked_path(
            "scripts/lock_gate.py", locked_entries
        )
        assert entry is not None
        assert entry["path"] == "scripts/lock_gate.py"

    def test_registry_self_hit(self, locked_entries):
        entry = matches_locked_path(
            ".module_lock_registry.json", locked_entries
        )
        assert entry is not None
        assert entry["path"] == ".module_lock_registry.json"


# --- end-to-end via --diff-file ---

class TestEndToEnd:
    def test_clean_diff_passes(self, clean_diff_path):
        rc = os.system(
            f"{sys.executable} scripts/lock_gate.py --diff-file {clean_diff_path}"
        )
        assert rc == 0, "clean diff should pass"

    def test_hit_diff_blocks(self, hit_diff_path):
        rc = os.system(
            f"{sys.executable} scripts/lock_gate.py --diff-file {hit_diff_path}"
        )
        assert rc != 0, "hit diff should block"

    def test_mixed_diff_blocks(self, mixed_diff_path):
        rc = os.system(
            f"{sys.executable} scripts/lock_gate.py --diff-file {mixed_diff_path}"
        )
        assert rc != 0, "mixed diff should block"

    def test_exception_diff_passes(self, exception_diff_path):
        rc = os.system(
            f"{sys.executable} scripts/lock_gate.py --diff-file {exception_diff_path}"
        )
        assert rc == 0, "exception diff should pass"
