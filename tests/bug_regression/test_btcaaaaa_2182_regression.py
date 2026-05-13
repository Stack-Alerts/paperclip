"""
Regression tests for BTCAAAAA-2182: Lock gate exception for src/data_manager.

Issue: BTCAAAAA-2182
Fixed in commit: 40652976
Component: lock_gate_exceptions.json

Root cause:
  The lock gate blocked changes to src/data_manager/ needed to fix the
  bars-truncation regression (4 incidents in 72h). A board-approved exception
  was required to bypass the module lock and deploy the pagination fix.

Fix:
  Added a board-approved exception entry for "src/data_manager" in
  lock_gate_exceptions.json (Path A, expires 2026-05-26).

This test validates the exception entry exists and meets schema requirements,
preventing accidental removal or misconfiguration.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2182"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCK_GATE_EXCEPTIONS_PATH = REPO_ROOT / "lock_gate_exceptions.json"

VALID_APPROVED_BY = {"board", "ceo-emergency"}


def _load_exceptions() -> list[dict]:
    with open(LOCK_GATE_EXCEPTIONS_PATH) as f:
        data = json.load(f)
    return data.get("exceptions", [])


def _find_data_manager_exception(exceptions: list[dict]) -> dict | None:
    for exc in exceptions:
        if exc.get("module") == "src/data_manager":
            return exc
    return None


def _count_data_manager_exceptions(exceptions: list[dict]) -> int:
    return sum(1 for exc in exceptions if exc.get("module") == "src/data_manager")


class TestLockGateExceptionDataManager:
    """Verify the src/data_manager exception entry in lock_gate_exceptions.json."""

    def test_exception_file_exists(self):
        """lock_gate_exceptions.json must exist and be valid JSON."""
        assert LOCK_GATE_EXCEPTIONS_PATH.exists()

    def test_exception_file_is_valid_json(self):
        """The file must parse as valid JSON."""
        with open(LOCK_GATE_EXCEPTIONS_PATH) as f:
            data = json.load(f)
        assert "version" in data
        assert "exceptions" in data

    def test_data_manager_exception_exists(self):
        """An exception for src/data_manager must be present."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None, (
            "Missing lock gate exception for src/data_manager "
            "(BTCAAAAA-2182)"
        )

    def test_exception_has_scope_description(self):
        """The exception must have a non-empty scope_description."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None
        desc = exc.get("scope_description", "")
        assert desc, "scope_description must not be empty"
        assert "BTCAAAAA-2182" in desc, (
            "scope_description must reference BTCAAAAA-2182"
        )

    def test_exception_has_approval_id(self):
        """The exception must have a non-empty approval_id."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None
        approval = exc.get("approval_id", "")
        assert approval, "approval_id must not be empty"

    def test_exception_approved_by_is_valid(self):
        """The exception's approved_by must be one of the valid enum values."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None
        approved_by = exc.get("approved_by", "")
        assert approved_by in VALID_APPROVED_BY, (
            f"approved_by must be one of {sorted(VALID_APPROVED_BY)}, "
            f"got '{approved_by}'"
        )

    def test_exception_approved_by_board(self):
        """The exception must be board-approved."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None
        assert exc.get("approved_by") == "board", (
            "src/data_manager exception must be approved_by 'board' "
            f"(got {exc.get('approved_by')})"
        )

    def test_exception_has_expiry(self):
        """The exception must have an expires_iso field."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None
        expires = exc.get("expires_iso")
        assert expires is not None, "expires_iso must not be null for Path A"

    def test_exception_expiry_is_future(self):
        """The exception expiry must not be in the past."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None
        expires = exc.get("expires_iso")
        assert expires is not None
        expiry_dt = datetime.fromisoformat(expires)
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        assert expiry_dt > datetime.now(timezone.utc), (
            f"Exception for src/data_manager expired on {expires}"
        )

    def test_exception_approval_id_is_valid_uuid(self):
        """The approval_id must be a valid UUID."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None
        approval = exc.get("approval_id", "")
        assert approval, "approval_id must not be empty"
        parsed = uuid.UUID(approval)
        assert str(parsed) == approval, (
            f"approval_id must be a valid UUID, got '{approval}'"
        )

    def test_exception_module_is_src_data_manager(self):
        """The exception module must be exactly src/data_manager."""
        exc = _find_data_manager_exception(_load_exceptions())
        assert exc is not None
        assert exc.get("module") == "src/data_manager", (
            f"module must be 'src/data_manager', got '{exc.get('module')}'"
        )

    def test_no_duplicate_data_manager_exception(self):
        """There must be exactly one exception entry for src/data_manager."""
        exceptions = _load_exceptions()
        count = _count_data_manager_exceptions(exceptions)
        assert count == 1, (
            f"Expected exactly 1 exception for src/data_manager, found {count}"
        )
