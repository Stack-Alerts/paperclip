"""
Integration tests for the auto-fix workflow — in-memory, no DB or Qt required.

Covers:
  1. auto_fix_strategy_type() updates strategy_type and side fields correctly.
  2. The DIRECTION_001 critical issue is resolved after the direction fix is applied.
  3. AutoFixSafety.rollback_if_needed() restores the original strategy state.

Design notes:
  - All tests are pure in-memory; no PostgreSQL or Qt application is needed.
  - To trigger DIRECTION_001 (CRITICAL) a Bullish config must have >70% of its
    directional signals classified as Bearish by InstitutionalValidator.
    Bearish keywords include: 'bearish', 'short', 'sell', 'down', 'breakdown',
    'rejection', 'lower', 'falling', 'decline', 'drop', 'reversal_down',
    'hod', 'high_of_day', 'top', 'peak', 'resistance'.
    (See InstitutionalValidator._get_signal_direction for the full list.)
  - A structurally-valid config (name + block + signals) is required so that
    verify_fix_result() does not reject the fix due to unrelated structural errors.

Author: QAEngineer (BTCAAAAA-130)
"""

import pytest

from src.strategy_builder.validation.auto_fix import auto_fix_strategy_type, AutoFixSafety
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
)
from src.optimizer_v3.validation.institutional_validator import InstitutionalValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bullish_config_with_bearish_signals(bearish_count: int = 4, bullish_count: int = 1) -> StrategyConfig:
    """
    Build a structurally-valid Bullish strategy whose signal names are
    predominantly bearish-named (>70%), sufficient to trigger DIRECTION_001.

    Bearish signal names use the keyword 'bearish' so that
    InstitutionalValidator._get_signal_direction() classifies them as BEARISH.
    Bullish signal names use 'bullish' so they are classified as BULLISH.

    Both totals must be > 0 so that total_directional > 0 and the percentage
    calculation is active.  With bearish_count=4 and bullish_count=1 the
    bearish percentage is 80%, which exceeds the 70% threshold for CRITICAL.
    """
    signals = [
        SignalConfig(name=f"bearish_signal_{i}", logic="AND")
        for i in range(bearish_count)
    ]
    signals += [
        SignalConfig(name=f"bullish_signal_{j}", logic="AND")
        for j in range(bullish_count)
    ]
    block = BlockConfig(name="EntryBlock", logic="AND", signals=signals)

    config = StrategyConfig(
        name="TestBullishStrategy",
        strategy_type="Bullish",
        blocks=[block],
    )
    return config


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAutoFixIntegration:
    """
    In-memory integration tests for the direction auto-fix workflow.
    No live database or Qt application is required.
    """

    # ------------------------------------------------------------------
    # 1. Direction switch updates config fields
    # ------------------------------------------------------------------

    def test_direction_fix_updates_config_type(self):
        """
        auto_fix_strategy_type() on a Bullish config must set strategy_type
        to 'Bearish' and side to 'SHORT'.

        Uses a config whose signals are all bearish-named so that
        verify_fix_result() passes (no blocking issues after the switch).
        """
        config = _make_bullish_config_with_bearish_signals()

        result = auto_fix_strategy_type(config, "Bearish")

        assert result is True, "auto_fix_strategy_type returned False; fix was not applied"
        assert config.strategy_type == "Bearish", (
            f"Expected strategy_type='Bearish', got '{config.strategy_type}'"
        )
        assert config.side == "SHORT", (
            f"Expected side='SHORT', got '{getattr(config, 'side', '<not set>')}'"
        )

    def test_direction_fix_to_bullish_sets_long_side(self):
        """
        Switching to 'Bullish' from a Bearish config sets side to 'LONG'.
        Uses a config with all-bullish signals so verify_fix_result passes.
        """
        signals = [SignalConfig(name=f"bullish_signal_{i}", logic="AND") for i in range(5)]
        block = BlockConfig(name="EntryBlock", logic="AND", signals=signals)
        config = StrategyConfig(
            name="TestBearishStrategy",
            strategy_type="Bearish",
            blocks=[block],
        )

        result = auto_fix_strategy_type(config, "Bullish")

        assert result is True
        assert config.strategy_type == "Bullish"
        assert config.side == "LONG"

    # ------------------------------------------------------------------
    # 2. DIRECTION_001 is cleared after the direction fix
    # ------------------------------------------------------------------

    def test_direction_fix_clears_direction_001(self):
        """
        After applying auto_fix_strategy_type(config, 'Bearish') on a
        Bullish config whose signals are >70% bearish, re-running
        InstitutionalValidator.validate() must produce no DIRECTION_001
        issue.

        This is the end-to-end "fix resolves the reported issue" test.
        """
        config = _make_bullish_config_with_bearish_signals(bearish_count=4, bullish_count=1)

        # Sanity-check: before the fix there IS a DIRECTION_001 issue.
        validator = InstitutionalValidator()
        pre_fix_report = validator.validate(config)
        pre_fix_ids = [issue.rule_id for issue in pre_fix_report.critical_issues]
        assert "DIRECTION_001" in pre_fix_ids, (
            "Test setup failed: DIRECTION_001 was expected before the fix but not found. "
            f"Critical issues: {pre_fix_ids}"
        )

        # Apply the fix.
        result = auto_fix_strategy_type(config, "Bearish")
        assert result is True, "auto_fix_strategy_type returned False; fix was rolled back"

        # Re-run validation on the fixed config.
        post_fix_report = validator.validate(config)
        post_fix_ids = [issue.rule_id for issue in post_fix_report.critical_issues]

        assert "DIRECTION_001" not in post_fix_ids, (
            "DIRECTION_001 still present after auto-fix — direction mismatch was not resolved. "
            f"Remaining critical issues: {post_fix_ids}"
        )

    # ------------------------------------------------------------------
    # 3. Rollback restores the original strategy state
    # ------------------------------------------------------------------

    def test_undo_restores_original_type(self):
        """
        After backup_strategy() + auto_fix_strategy_type() + rollback_if_needed(),
        the config must be restored to its original 'Bullish' state.

        Tests the AutoFixSafety safety/rollback mechanism independently of
        the fix application so that undo logic can be verified in isolation.
        """
        config = _make_bullish_config_with_bearish_signals()
        original_type = config.strategy_type  # "Bullish"

        # Create a safety instance and take a backup manually.
        safety = AutoFixSafety()
        safety.backup_strategy(config)

        # Mutate the config to simulate a fix being applied.
        config.strategy_type = "Bearish"
        config.side = "SHORT"

        # Rollback should restore the original state.
        rollback_result = safety.rollback_if_needed(config)

        assert rollback_result is True, "rollback_if_needed returned False (no backup?)"
        assert config.strategy_type == original_type, (
            f"Expected strategy_type='{original_type}' after rollback, "
            f"got '{config.strategy_type}'"
        )

    def test_rollback_without_backup_returns_false(self):
        """
        rollback_if_needed() must return False when no backup exists.
        """
        safety = AutoFixSafety()
        config = StrategyConfig(name="NoBackup", strategy_type="Bullish")

        result = safety.rollback_if_needed(config)

        assert result is False, "Expected False when no backup state has been set"

    # ------------------------------------------------------------------
    # 4. Invalid strategy_type is rejected by auto_fix_strategy_type
    # ------------------------------------------------------------------

    def test_invalid_strategy_type_returns_false(self):
        """
        auto_fix_strategy_type() must return False for an unrecognised type.
        """
        config = StrategyConfig(name="TestStrategy", strategy_type="Bullish")

        result = auto_fix_strategy_type(config, "INVALID_TYPE")

        assert result is False, "Expected False for invalid strategy type"
        # Config must not have been modified.
        assert config.strategy_type == "Bullish"
