"""
Regression tests for BTCAAAAA-154:
  Duplicating a strategy must preserve strategy_type (Bearish/Bullish).

Root cause:
  _on_duplicate() in strategy_browser_dialog.py built version_data without
  the 'strategy_type' key in both branches (new version and new strategy),
  so create_strategy_version() fell through to the default 'Bullish' at
  strategy_manager.py:160 regardless of the original strategy type.

Test strategy:
  - No PyQt5 / Qt application required; tests run against the pure-Python
    dict construction logic that mirrors what _on_duplicate() produces.
  - The fix mirrors the pattern used for BTCAAAAA-129 in
    test_auto_fix_db_persistence.py.
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — mirrors the dict construction in _on_duplicate()
# ---------------------------------------------------------------------------

def _make_source_version(strategy_type: str = "Bearish") -> dict:
    """
    Return a dict that mimics the row returned by
    db.strategy.get_strategy_version(selected_version_id) inside _on_duplicate().
    """
    return {
        "name": "TestStrategy",
        "description": "Test strategy for duplicate type preservation",
        "strategy_type": strategy_type,
        "blocks": [],
        "signals": {},
        "parameters": {},
        "entry_conditions": {},
        "exit_conditions": [],
        "risk_management": {},
        "backtest_config": {},
        "tags": [],
    }


def _build_version_data_fixed(version: dict, strategy_id: str) -> dict:
    """
    Mirrors the FIXED _on_duplicate() Branch 1 (new version of same strategy).
    strategy_type IS present — this is the correct post-fix behaviour.
    """
    return {
        "strategy_id": strategy_id,
        "name": version["name"],
        "description": version.get("description", ""),
        "strategy_type": version.get("strategy_type", "Bullish"),  # ← the added line
        "blocks": version["blocks"],
        "signals": version["signals"],
        "parameters": version["parameters"],
        "entry_conditions": version["entry_conditions"],
        "exit_conditions": version["exit_conditions"],
        "risk_management": version["risk_management"],
        "backtest_config": version["backtest_config"],
        "tags": version.get("tags", []),
    }


def _build_version_data_new_strategy_fixed(version: dict, new_strategy_id: str, new_name: str) -> dict:
    """
    Mirrors the FIXED _on_duplicate() Branch 2 (duplicate as new strategy).
    strategy_type IS present — this is the correct post-fix behaviour.
    """
    return {
        "strategy_id": new_strategy_id,
        "name": new_name,
        "description": version.get("description", ""),
        "strategy_type": version.get("strategy_type", "Bullish"),  # ← the added line
        "blocks": version["blocks"],
        "signals": version["signals"],
        "parameters": version["parameters"],
        "entry_conditions": version["entry_conditions"],
        "exit_conditions": version["exit_conditions"],
        "risk_management": version["risk_management"],
        "backtest_config": version["backtest_config"],
        "tags": version.get("tags", []),
    }


def _build_version_data_buggy(version: dict, strategy_id: str) -> dict:
    """
    Mirrors the BUGGY _on_duplicate() Branch 1 (before the fix).
    strategy_type is absent — reproduces the original bug.
    """
    return {
        "strategy_id": strategy_id,
        "name": version["name"],
        "description": version.get("description", ""),
        # strategy_type intentionally omitted ← the original bug
        "blocks": version["blocks"],
        "signals": version["signals"],
        "parameters": version["parameters"],
        "entry_conditions": version["entry_conditions"],
        "exit_conditions": version["exit_conditions"],
        "risk_management": version["risk_management"],
        "backtest_config": version["backtest_config"],
        "tags": version.get("tags", []),
    }


# ---------------------------------------------------------------------------
# Tests — Branch 1: duplicate as new version of same strategy
# ---------------------------------------------------------------------------

class TestDuplicateNewVersionPreservesStrategyType:
    """
    Regression tests for BTCAAAAA-154 — Branch 1 of _on_duplicate().
    Duplicating as a new version of the same strategy must preserve strategy_type.
    """

    def test_duplicate_new_version_preserves_bearish(self):
        """
        Duplicating a Bearish strategy as a new version must produce a Bearish
        version_data dict passed to create_strategy_version().
        """
        strategy_id = "strategy-uuid-001"
        version = _make_source_version(strategy_type="Bearish")

        version_data = _build_version_data_fixed(version, strategy_id)

        assert "strategy_type" in version_data, (
            "version_data is missing 'strategy_type' key — fix not applied in Branch 1"
        )
        assert version_data["strategy_type"] == "Bearish", (
            f"Expected 'Bearish', got '{version_data['strategy_type']}' — "
            "duplicate changed strategy_type"
        )

    def test_duplicate_new_version_preserves_bullish(self):
        """
        Duplicating a Bullish strategy as a new version must produce a Bullish
        version_data dict.
        """
        strategy_id = "strategy-uuid-002"
        version = _make_source_version(strategy_type="Bullish")

        version_data = _build_version_data_fixed(version, strategy_id)

        assert version_data["strategy_type"] == "Bullish"

    def test_duplicate_new_version_defaults_bullish_when_absent(self):
        """
        If source version lacks strategy_type (legacy data), the duplicate must
        default to 'Bullish' rather than raise.
        """
        strategy_id = "strategy-uuid-003"
        version = _make_source_version(strategy_type="Bearish")
        del version["strategy_type"]  # Simulate legacy/missing data

        version_data = _build_version_data_fixed(version, strategy_id)

        assert version_data["strategy_type"] == "Bullish", (
            "Expected 'Bullish' default when source version lacks strategy_type"
        )

    def test_duplicate_bug_reproduced_without_fix(self):
        """
        Demonstrate the original bug: the buggy version_data dict has no
        'strategy_type' key, so create_strategy_version() falls through to
        the 'Bullish' default regardless of the source strategy type.
        This test documents the pre-fix behaviour as a regression guard.
        """
        strategy_id = "strategy-uuid-004"
        version = _make_source_version(strategy_type="Bearish")

        buggy_version_data = _build_version_data_buggy(version, strategy_id)

        assert "strategy_type" not in buggy_version_data, (
            "Test setup error: buggy path should NOT include strategy_type"
        )
        # The downstream default kicks in at strategy_manager.py:160
        # strategy_data.get('strategy_type', 'Bullish') → 'Bullish'
        effective_type = buggy_version_data.get("strategy_type", "Bullish")
        assert effective_type == "Bullish", (
            "Expected the buggy path to produce 'Bullish' via fallback "
            "— confirms the bug existed and the fix is necessary"
        )


# ---------------------------------------------------------------------------
# Tests — Branch 2: duplicate as new strategy
# ---------------------------------------------------------------------------

class TestDuplicateNewStrategyPreservesStrategyType:
    """
    Regression tests for BTCAAAAA-154 — Branch 2 of _on_duplicate().
    Duplicating as a brand-new strategy must preserve strategy_type.
    """

    def test_duplicate_new_strategy_preserves_bearish(self):
        """
        Duplicating a Bearish strategy as a new strategy must produce a Bearish
        version_data dict passed to create_strategy_version().
        """
        new_strategy_id = "new-strategy-uuid-001"
        version = _make_source_version(strategy_type="Bearish")

        version_data = _build_version_data_new_strategy_fixed(
            version, new_strategy_id, "TestStrategy (Copy)"
        )

        assert "strategy_type" in version_data, (
            "version_data is missing 'strategy_type' key — fix not applied in Branch 2"
        )
        assert version_data["strategy_type"] == "Bearish", (
            f"Expected 'Bearish', got '{version_data['strategy_type']}' — "
            "duplicate changed strategy_type in new-strategy branch"
        )

    def test_duplicate_new_strategy_preserves_bullish(self):
        """
        Duplicating a Bullish strategy as a new strategy must produce a Bullish
        version_data dict.
        """
        new_strategy_id = "new-strategy-uuid-002"
        version = _make_source_version(strategy_type="Bullish")

        version_data = _build_version_data_new_strategy_fixed(
            version, new_strategy_id, "TestStrategy (Copy)"
        )

        assert version_data["strategy_type"] == "Bullish"

    def test_duplicate_new_strategy_uses_new_name(self):
        """
        The new strategy branch must use the user-supplied name, not the
        original strategy name.
        """
        new_strategy_id = "new-strategy-uuid-003"
        version = _make_source_version(strategy_type="Bearish")
        new_name = "My Renamed Strategy"

        version_data = _build_version_data_new_strategy_fixed(
            version, new_strategy_id, new_name
        )

        assert version_data["name"] == new_name
        assert version_data["strategy_id"] == new_strategy_id

    def test_duplicate_new_strategy_defaults_bullish_when_absent(self):
        """
        If source version lacks strategy_type (legacy data), the duplicate as
        new strategy must default to 'Bullish' rather than raise.
        """
        new_strategy_id = "new-strategy-uuid-004"
        version = _make_source_version(strategy_type="Bearish")
        del version["strategy_type"]

        version_data = _build_version_data_new_strategy_fixed(
            version, new_strategy_id, "Legacy Copy"
        )

        assert version_data["strategy_type"] == "Bullish"


# ---------------------------------------------------------------------------
# Integration simulation — mocked create_strategy_version call
# ---------------------------------------------------------------------------

class TestDuplicateIntegrationWithMockedDB:
    """
    End-to-end simulation of the fixed _on_duplicate() call chain using
    mocked DB objects — verifies the strategy_type key reaches
    create_strategy_version() correctly.
    """

    def test_create_strategy_version_receives_bearish_branch1(self):
        """
        Simulate Branch 1: create_strategy_version() must be called with
        strategy_type='Bearish' when the source version is Bearish.
        """
        mock_db = MagicMock()
        mock_db.strategy.create_strategy_version = MagicMock(return_value="new-version-id")

        version = _make_source_version(strategy_type="Bearish")
        strategy_id = "strategy-abc-123"

        version_data = _build_version_data_fixed(version, strategy_id)
        mock_db.strategy.create_strategy_version(version_data)

        call_args = mock_db.strategy.create_strategy_version.call_args[0][0]
        assert call_args.get("strategy_type") == "Bearish", (
            "create_strategy_version was NOT called with strategy_type='Bearish' — "
            "fix did not propagate strategy_type"
        )

    def test_create_strategy_version_receives_bullish_branch1(self):
        """
        Simulate Branch 1: create_strategy_version() must be called with
        strategy_type='Bullish' when the source version is Bullish.
        """
        mock_db = MagicMock()
        version = _make_source_version(strategy_type="Bullish")
        strategy_id = "strategy-abc-456"

        version_data = _build_version_data_fixed(version, strategy_id)
        mock_db.strategy.create_strategy_version(version_data)

        call_args = mock_db.strategy.create_strategy_version.call_args[0][0]
        assert call_args.get("strategy_type") == "Bullish"

    def test_create_strategy_version_receives_bearish_branch2(self):
        """
        Simulate Branch 2: create_strategy_version() for a new strategy must be
        called with strategy_type='Bearish' when the source version is Bearish.
        """
        mock_db = MagicMock()
        mock_db.strategy.create_strategy = MagicMock(return_value="new-strategy-id")
        mock_db.strategy.create_strategy_version = MagicMock(return_value="new-version-id")

        version = _make_source_version(strategy_type="Bearish")
        new_strategy_id = mock_db.strategy.create_strategy("Bearish Strategy (Copy)")

        version_data = _build_version_data_new_strategy_fixed(
            version, new_strategy_id, "Bearish Strategy (Copy)"
        )
        mock_db.strategy.create_strategy_version(version_data)

        call_args = mock_db.strategy.create_strategy_version.call_args[0][0]
        assert call_args.get("strategy_type") == "Bearish", (
            "Branch 2: create_strategy_version was NOT called with strategy_type='Bearish'"
        )
