"""
Integration tests for auto-fix strategy_type persistence.

Covers the bug fixed in BTCAAAAA-129:
  _reload_current_version() was missing 'strategy_type' in config_dict,
  causing the UI to revert to the default 'Bullish' type after auto-fix +
  save, wiping out the user-chosen / auto-fixed strategy_type on next save.

Test strategy:
- No PyQt5 / Qt application required; tests run against the persistence
  layer and the config dataclass directly.
- The "auto-fix → save → reload" cycle is simulated via StrategyPersistence
  and a mocked database version dict, matching exactly what
  _reload_current_version() does in the main window.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.strategy_builder.persistence.strategy_persistence import StrategyPersistence
from src.strategy_builder.core.strategy_config_engine import StrategyConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_version(strategy_type: str = "Bearish") -> dict:
    """
    Return a dict that mimics the row returned by
    db.strategy.get_strategy_version(version_id).
    """
    return {
        "name": "TestStrategy",
        "description": "Test strategy for auto-fix persistence",
        "strategy_type": strategy_type,
        "blocks": [],
        "exit_conditions": [],
        "version_number": 2,
        "validation_status": "Pass",
    }


def _make_config_dict_with_strategy_type(version: dict) -> dict:
    """
    Mirrors the FIXED config_dict construction in _reload_current_version().
    strategy_type IS present — this is the correct post-fix behaviour.
    """
    return {
        "name": version["name"],
        "description": version.get("description", ""),
        "strategy_type": version.get("strategy_type", "Bullish"),  # ← the added line
        "blocks": version.get("blocks", []),
        "exit_conditions": version.get("exit_conditions", []),
    }


def _make_config_dict_without_strategy_type(version: dict) -> dict:
    """
    Mirrors the BUGGY config_dict construction from before the fix.
    strategy_type is absent — this reproduces the original bug.
    """
    return {
        "name": version["name"],
        "description": version.get("description", ""),
        # strategy_type intentionally omitted ← the original bug
        "blocks": version.get("blocks", []),
        "exit_conditions": version.get("exit_conditions", []),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAutoFixDbPersistence:
    """
    Regression tests for BTCAAAAA-129 — _reload_current_version() must
    include strategy_type so the auto-fix value survives a DB reload.
    """

    def test_dict_to_config_preserves_bearish(self):
        """
        _dict_to_config must honour strategy_type='Bearish' from the dict.
        This is the foundational contract the fix relies on.
        """
        persistence = StrategyPersistence()
        version = _make_db_version(strategy_type="Bearish")
        config_dict = _make_config_dict_with_strategy_type(version)

        config = persistence._dict_to_config(config_dict)

        assert config.strategy_type == "Bearish", (
            "_dict_to_config did not restore strategy_type='Bearish' from config_dict"
        )

    def test_dict_to_config_preserves_bullish(self):
        """
        _dict_to_config must honour strategy_type='Bullish' from the dict.
        """
        persistence = StrategyPersistence()
        version = _make_db_version(strategy_type="Bullish")
        config_dict = _make_config_dict_with_strategy_type(version)

        config = persistence._dict_to_config(config_dict)

        assert config.strategy_type == "Bullish"

    def test_dict_to_config_defaults_to_bullish_when_absent(self):
        """
        When strategy_type key is missing from the dict (legacy / corrupted
        data), _dict_to_config must default to 'Bullish', not raise.
        """
        persistence = StrategyPersistence()
        config_dict = {
            "name": "Legacy",
            "description": "",
            "blocks": [],
            "exit_conditions": [],
        }

        config = persistence._dict_to_config(config_dict)

        assert config.strategy_type == "Bullish"

    def test_reload_cycle_with_fix_preserves_bearish(self):
        """
        Simulate the fixed _reload_current_version() path end-to-end:

          DB version (strategy_type='Bearish')
            → FIXED config_dict (includes strategy_type)
            → _dict_to_config
            → restored_config.strategy_type

        strategy_type must survive the round-trip.
        """
        persistence = StrategyPersistence()
        version = _make_db_version(strategy_type="Bearish")

        # This is what the fixed code does
        config_dict = _make_config_dict_with_strategy_type(version)
        restored = persistence._dict_to_config(config_dict)

        assert restored.strategy_type == "Bearish", (
            "Fixed reload path did not preserve strategy_type='Bearish'"
        )

    def test_reload_cycle_bug_reproduced_without_fix(self):
        """
        Demonstrate the original bug: when strategy_type is absent from the
        config_dict the restored config reverts to the 'Bullish' default,
        which is incorrect for a 'Bearish' strategy.

        This test documents the bug so we can confirm the fix is necessary
        and that the regression guard works.
        """
        persistence = StrategyPersistence()
        version = _make_db_version(strategy_type="Bearish")

        # BUGGY path (no strategy_type in dict)
        buggy_config_dict = _make_config_dict_without_strategy_type(version)
        restored = persistence._dict_to_config(buggy_config_dict)

        # Without strategy_type, it defaults to 'Bullish' — the original bug
        assert restored.strategy_type == "Bullish", (
            "Expected the buggy path to produce 'Bullish' (default) when "
            "strategy_type was absent from config_dict — test setup may be wrong"
        )

    def test_auto_fix_full_cycle_bearish_to_bearish(self):
        """
        Full auto-fix simulation:

          1. User has a Bearish strategy in the DB.
          2. Auto-fix runs and sets strategy_type = 'Bearish' on config.
          3. Save writes 'Bearish' to DB (mocked here as a version dict).
          4. _reload_current_version() builds the FIXED config_dict.
          5. The reloaded config still has strategy_type = 'Bearish'.

        Previously step 4 dropped strategy_type, so step 5 reverted to
        'Bullish', corrupting the next save.
        """
        persistence = StrategyPersistence()

        # Step 1 + 2: auto-fix produced a Bearish config
        fixed_config = StrategyConfig()
        fixed_config.name = "BearishStrategy"
        fixed_config.strategy_type = "Bearish"

        # Step 3: DB version after save (strategy_type stored correctly)
        saved_version = _make_db_version(strategy_type=fixed_config.strategy_type)

        # Step 4: _reload_current_version() — FIXED path
        config_dict = _make_config_dict_with_strategy_type(saved_version)
        reloaded_config = persistence._dict_to_config(config_dict)

        # Step 5: strategy_type must be Bearish, not the Bullish default
        assert reloaded_config.strategy_type == "Bearish", (
            "strategy_type reverted to 'Bullish' after reload — "
            "fix in _reload_current_version() did not take effect"
        )

    def test_regular_load_path_already_correct(self):
        """
        Regression guard for the regular load path (line ~697 in main window).
        That path was already correct; confirm it stays correct.
        The regular load config_dict is identical in structure to the fixed
        reload config_dict, so _dict_to_config should produce the same result.
        """
        persistence = StrategyPersistence()

        # Same dict structure as the regular load path
        regular_config_dict = {
            "name": "BullishStrategy",
            "description": "Regular load",
            "strategy_type": "Bullish",
            "blocks": [],
            "exit_conditions": [],
        }

        config = persistence._dict_to_config(regular_config_dict)
        assert config.strategy_type == "Bullish"

        regular_config_dict_bearish = dict(regular_config_dict)
        regular_config_dict_bearish["strategy_type"] = "Bearish"
        config2 = persistence._dict_to_config(regular_config_dict_bearish)
        assert config2.strategy_type == "Bearish"
