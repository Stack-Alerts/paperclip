"""Unit tests for scripts/lock_gate.py."""

import json
import os
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
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = REPO_ROOT / ".module_lock_registry.json"


# --- helpers ---

def make_entry(module="src/data_manager", scope="Refactor pipeline",
               expires_iso=None, approval_id="board-approval-123",
               approved_by="board"):
    entry = {
        "module": module,
        "scope_description": scope,
        "expires_iso": expires_iso,
        "approval_id": approval_id,
        "approved_by": approved_by,
    }
    if expires_iso is None:
        del entry["expires_iso"]
        entry["expires_iso"] = None
    return entry


def now_iso(offset_hours=0):
    dt = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- fixtures ---

@pytest.fixture
def registry():
    return load_json(REGISTRY_PATH)


@pytest.fixture
def locked_entries(registry):
    return registry["entries"]


HIT_DIFF_CONTENT = """\
diff --git a/src/optimizer_v3/core/trade_registry.py b/src/optimizer_v3/core/trade_registry.py
index abc123..def456 100644
--- a/src/optimizer_v3/core/trade_registry.py
+++ b/src/optimizer_v3/core/trade_registry.py
@@ -1,5 +1,6 @@
 # Trade Registry
+print("hello")
 class TradeRegistry:
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
        assert "src/optimizer_v3/core/trade_registry.py" in files

    def test_clean_diff(self, clean_diff_path):
        files = get_changed_files_from_diff(clean_diff_path)
        assert "src/strategies/completestrategy.py" in files
        assert not any("data_manager" in f for f in files)

    def test_mixed_diff(self, mixed_diff_path):
        files = get_changed_files_from_diff(mixed_diff_path)
        assert len(files) == 3
        assert "src/strategies/completestrategy.py" in files
        assert "src/optimizer_v3/core/trade_registry.py" in files
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
        entry = matches_locked_path("scripts/lock_gate.py", locked_entries)
        assert entry is not None
        assert entry["path"] == "scripts/lock_gate.py"

    def test_registry_self_hit(self, locked_entries):
        entry = matches_locked_path(".module_lock_registry.json", locked_entries)
        assert entry is not None
        assert entry["path"] == ".module_lock_registry.json"


# --- parse_iso tests ---

class TestParseIso:
    def test_valid_iso(self):
        dt = parse_iso("2026-05-25T12:00:00Z")
        assert dt is not None
        assert dt.hour == 12

    def test_valid_iso_offset(self):
        dt = parse_iso("2026-05-25T12:00:00+00:00")
        assert dt is not None

    def test_invalid_string(self):
        assert parse_iso("not-a-date") is None

    def test_empty_string(self):
        assert parse_iso("") is None

    def test_none(self):
        assert parse_iso(None) is None


# --- validate_exception_entry tests ---

class TestValidateExceptionEntry:
    def test_valid_board_entry_no_expiry(self):
        entry = make_entry(approved_by="board", expires_iso=None)
        assert validate_exception_entry(entry) == []

    def test_valid_board_entry_with_expiry(self):
        entry = make_entry(approved_by="board", expires_iso=now_iso(2))
        assert validate_exception_entry(entry) == []

    def test_valid_ceo_emergency_entry(self):
        entry = make_entry(approved_by="ceo-emergency", expires_iso=now_iso(2))
        assert validate_exception_entry(entry) == []

    def test_rejects_cto_emergency(self):
        entry = make_entry(approved_by="cto-emergency", expires_iso=now_iso(2))
        errors = validate_exception_entry(entry)
        assert any("cto-emergency" in e for e in errors)

    def test_rejects_invalid_approved_by(self):
        entry = make_entry(approved_by="ceo", expires_iso=now_iso(2))
        errors = validate_exception_entry(entry)
        assert any("approved_by" in e for e in errors)

    def test_rejects_empty_module(self):
        entry = make_entry(module="", expires_iso=None)
        errors = validate_exception_entry(entry)
        assert any("module" in e for e in errors)

    def test_rejects_empty_scope(self):
        entry = make_entry(scope="", expires_iso=None)
        errors = validate_exception_entry(entry)
        assert any("scope_description" in e for e in errors)

    def test_rejects_empty_approval_id(self):
        entry = make_entry(approval_id="", expires_iso=None)
        errors = validate_exception_entry(entry)
        assert any("approval_id" in e for e in errors)

    def test_rejects_expiry_over_4h(self):
        entry = make_entry(approved_by="ceo-emergency", expires_iso=now_iso(5))
        errors = validate_exception_entry(entry)
        assert any("4h" in e or "4" in e for e in errors)

    def test_accepts_expiry_under_4h(self):
        entry = make_entry(approved_by="ceo-emergency", expires_iso=now_iso(3))
        errors = validate_exception_entry(entry)
        assert errors == []

    def test_rejects_expiry_over_4h_board_emergency(self):
        entry = make_entry(approved_by="board-emergency", expires_iso=now_iso(5))
        errors = validate_exception_entry(entry)
        assert any("4h" in e or "4" in e for e in errors)

    def test_expiry_null_board_ok(self):
        entry = make_entry(approved_by="board", expires_iso=None)
        errors = validate_exception_entry(entry)
        assert errors == []

    def test_rejects_bad_iso_format(self):
        entry = make_entry(approved_by="board", expires_iso="2026/05/25")
        errors = validate_exception_entry(entry)
        assert any("ISO 8601" in e or "valid" in e for e in errors)

    def test_not_a_dict(self):
        errors = validate_exception_entry("not a dict")
        assert len(errors) >= 1


# --- validate_exceptions_file tests ---

class TestValidateExceptionsFile:
    def test_valid_file(self):
        data = {
            "version": 2,
            "description": "test",
            "exceptions": [
                make_entry(approved_by="board", expires_iso=None),
            ],
        }
        assert validate_exceptions_file(data) == []

    def test_empty_exceptions_array(self):
        data = {"version": 2, "description": "test", "exceptions": []}
        assert validate_exceptions_file(data) == []

    def test_wrong_version(self):
        data = {"version": 1, "description": "test", "exceptions": []}
        errors = validate_exceptions_file(data)
        assert any("version" in e for e in errors)

    def test_not_a_dict(self):
        errors = validate_exceptions_file([])
        assert len(errors) >= 1

    def test_exceptions_not_array(self):
        data = {"version": 2, "exceptions": "not an array"}
        errors = validate_exceptions_file(data)
        assert any("exceptions" in e for e in errors)


# --- get_active_exceptions tests ---

class TestGetActiveExceptions:
    def test_no_expiry_stays_active(self):
        excs = [make_entry(module="src/data_manager", expires_iso=None)]
        active = get_active_exceptions(excs)
        assert len(active) == 1

    def test_future_expiry_stays_active(self):
        excs = [make_entry(module="src/data_manager", expires_iso=now_iso(2))]
        active = get_active_exceptions(excs)
        assert len(active) == 1

    def test_past_expiry_is_ignored(self):
        excs = [make_entry(module="src/data_manager", expires_iso=now_iso(-2))]
        active = get_active_exceptions(excs)
        assert len(active) == 0

    def test_mixed_expiry(self):
        excs = [
            make_entry(module="src/a", expires_iso=None),
            make_entry(module="src/b", expires_iso=now_iso(-1)),
            make_entry(module="src/c", expires_iso=now_iso(3)),
        ]
        active = get_active_exceptions(excs)
        assert len(active) == 2
        assert {e["module"] for e in active} == {"src/a", "src/c"}

    def test_invalid_iso_treated_as_expired(self):
        excs = [make_entry(module="src/data_manager", expires_iso="not-a-date")]
        active = get_active_exceptions(excs)
        assert len(active) == 0


# --- get_excepted_modules tests ---

class TestGetExceptedModules:
    def test_uses_module_field(self):
        excs = [make_entry(module="src/data_manager", expires_iso=None)]
        modules = get_excepted_modules(excs)
        assert "src/data_manager" in modules

    def test_multiple_modules(self):
        excs = [
            make_entry(module="src/a", expires_iso=None),
            make_entry(module="src/b", expires_iso=None),
        ]
        modules = get_excepted_modules(excs)
        assert modules == {"src/a", "src/b"}


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

    def test_validate_exceptions_passes(self):
        rc = os.system(
            f"{sys.executable} scripts/lock_gate.py --validate-exceptions"
        )
        assert rc == 0, "validate exceptions should pass"
