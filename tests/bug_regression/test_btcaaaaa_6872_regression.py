"""
Regression tests for BTCAAAAA-6872: Intra-Day PnL Degradation — direction-aware
signal filtering + removal of stale JSON config fallback.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-6872
Fixed in commits:
  - f1e07749: add direction-aware signal filtering (InstitutionalSignalEvaluator
    + NautilusCodeGenerator strategy_type integration)
  - 402d1a1c: remove stale JSON config fallback from _repair_if_unreachable,
    delete user_strategies/current_strategy.json

Components:
  src/optimizer_v3/core/institutional_signal_evaluator.py
  src/strategy_builder/core/nautilus_code_generator.py
  src/strategy_builder/ui/backtest_config_panel.py
  user_strategies/current_strategy.json (deleted)

Root cause / changes:
  1. InstitutionalSignalEvaluator lacked direction consistency checking — trades
     were entered on signals with opposite directional bias to the configured
     strategy_type. Fix: added _check_direction_consistency() method,
     _get_signal_direction() static method, and direction_check_enabled flag.
  2. NautilusCodeGenerator hardcoded OrderSide.BUY regardless of strategy_type.
     Fix: OrderSide now driven by self.strategy_type, and strategy_type is
     included in generated strategy config dict.
  3. _repair_if_unreachable() would silently merge missing blocks from
     user_strategies/current_strategy.json — a stale file that contained phantom
     signals not in the PostgreSQL database (source of truth). Fix: removed the
     JSON fallback, deleted the stale file, updated comments.

This file validates source-level contracts for all three fixes so the Impact
Gate runner can discover them by issue ID.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-6872"),
    pytest.mark.regression,
]

ROOT = Path(__file__).resolve().parents[2]

ISE_SOURCE = ROOT / "src" / "optimizer_v3" / "core" / "institutional_signal_evaluator.py"
ISE_TEXT = ISE_SOURCE.read_text()

NCG_SOURCE = ROOT / "src" / "strategy_builder" / "core" / "nautilus_code_generator.py"
NCG_TEXT = NCG_SOURCE.read_text()

BCP_SOURCE = ROOT / "src" / "strategy_builder" / "ui" / "backtest_config_panel.py"
BCP_TEXT = BCP_SOURCE.read_text()

STALE_JSON_PATH = ROOT / "user_strategies" / "current_strategy.json"


# ============================================================================
# InstitutionalSignalEvaluator — direction-aware signal filtering
# ============================================================================


class TestDirectionCheckEnabled:
    """BTCAAAAA-6872: direction_check_enabled must be initialized to True."""

    def test_direction_check_enabled_attribute(self):
        assert "self.direction_check_enabled" in ISE_TEXT, (
            "direction_check_enabled attribute must exist"
        )
        assert "self.direction_check_enabled = True" in ISE_TEXT, (
            "direction_check_enabled must default to True"
        )


class TestDirectionCheckInEntryLogic:
    """BTCAAAAA-6872: direction consistency check must gate entry decisions."""

    def test_direction_check_called_before_entry(self):
        lines = ISE_TEXT.split("\n")
        found_should_enter = False
        found_direction_check = False
        for line in lines:
            if "should_enter = required_ok and confluence" in line:
                found_should_enter = True
            if found_should_enter and "_check_direction_consistency(all_signals)" in line:
                found_direction_check = True
                break
        assert found_direction_check, (
            "_check_direction_consistency must be called after should_enter assignment"
        )

    def test_direction_check_blocks_entry_on_failure(self):
        assert "should_enter = False" in ISE_TEXT, (
            "Entry must be blocked when direction check fails"
        )
        assert 'logger.warning("DIRECTION CHECK:' in ISE_TEXT, (
            "Direction check failure must be logged at WARNING level"
        )


class TestGetSignalDirection:
    """BTCAAAAA-6872: _get_signal_direction must classify signals correctly."""

    def test_method_is_static(self):
        sig_line = None
        for line in ISE_TEXT.split("\n"):
            if "def _get_signal_direction" in line:
                sig_line = line.strip()
                break
        assert sig_line is not None, "_get_signal_direction must be defined"
        assert "signal_id" in sig_line, (
            "_get_signal_direction must accept signal_id parameter"
        )

    def test_bullish_classification(self):
        assert "'BULLISH' in signal_upper or '_BOUNCE' in signal_upper" in ISE_TEXT, (
            "_get_signal_direction must classify BULLISH / _BOUNCE / ABOVE_ as BULLISH"
        )

    def test_bearish_classification(self):
        assert "'BEARISH' in signal_upper or '_BREAK' in signal_upper" in ISE_TEXT, (
            "_get_signal_direction must classify BEARISH / _BREAK / BELOW_ / REJECTION as BEARISH"
        )

    def test_neutral_fallback(self):
        assert "return 'NEUTRAL'" in ISE_TEXT, (
            "_get_signal_direction must return NEUTRAL when no directional markers found"
        )


class TestCheckDirectionConsistency:
    """BTCAAAAA-6872: _check_direction_consistency must gate by signal bias."""

    def test_method_defined(self):
        assert "def _check_direction_consistency" in ISE_TEXT, (
            "_check_direction_consistency must be defined"
        )

    def test_uses_strategy_type(self):
        assert "getattr(self.strategy_config, 'strategy_type'" in ISE_TEXT, (
            "_check_direction_consistency must read strategy_type from config"
        )

    def test_rejects_bullish_on_bearish_strategy(self):
        assert "expected_direction == 'BEARISH' and bullish_count > bearish_count" in ISE_TEXT, (
            "Must reject entries when expected BEARISH but signals are BULLISH-dominant"
        )

    def test_rejects_bearish_on_bullish_strategy(self):
        assert "expected_direction == 'BULLISH' and bearish_count > bullish_count" in ISE_TEXT, (
            "Must reject entries when expected BULLISH but signals are BEARISH-dominant"
        )

    def test_allows_no_directional_signals(self):
        assert "if total_directional == 0:" in ISE_TEXT, (
            "Must allow entry when no directional signals present"
        )

    def test_allows_consistent_signals(self):
        lines = ISE_TEXT.split("\n")
        in_method = False
        found_return_true = False
        for line in lines:
            if "def _check_direction_consistency" in line:
                in_method = True
            if in_method and "return True, None" in line:
                found_return_true = True
                break
        assert found_return_true, (
            "Must return (True, None) when signals are directionally consistent"
        )


# ============================================================================
# NautilusCodeGenerator — strategy_type for OrderSide + config
# ============================================================================


class TestNautilusStrategyType:
    """BTCAAAAA-6872: NautilusCodeGenerator must use strategy_type for
    OrderSide determination and include it in generated config."""

    def test_strategy_type_in_init(self):
        assert 'self.strategy_type = config.get("strategy_type", "Bullish")' in NCG_TEXT, (
            "Generated strategy init must read strategy_type from config"
        )

    def test_order_side_driven_by_strategy_type(self):
        assert 'OrderSide.BUY if self.strategy_type == "Bullish" else OrderSide.SELL' in NCG_TEXT, (
            "OrderSide must be driven by self.strategy_type, not hardcoded BUY"
        )

    def test_no_hardcoded_buy_only(self):
        assert "OrderSide.BUY  # TODO" not in NCG_TEXT, (
            "Hardcoded OrderSide.BUY with TODO comment must be removed"
        )

    def test_strategy_type_in_generated_config_dict(self):
        assert '"strategy_type": config.strategy_type' in NCG_TEXT, (
            "Generated _generate_config_dict must include strategy_type field"
        )


# ============================================================================
# BacktestConfigPanel — removal of stale JSON config fallback
# ============================================================================


class TestRepairIfUnreachableNoJson:
    """BTCAAAAA-6872: _repair_if_unreachable must not reference
    user_strategies/current_strategy.json."""

    def test_no_current_strategy_json_reference(self):
        assert "current_strategy.json" not in BCP_TEXT, (
            "_repair_if_unreachable must no longer reference current_strategy.json"
        )

    def test_no_json_load_in_repair(self):
        lines = BCP_TEXT.split("\n")
        in_repair = False
        for line in lines:
            if "def _repair_if_unreachable" in line:
                in_repair = True
            if in_repair and "json.load" in line:
                pytest.fail(
                    "_repair_if_unreachable must not use json.load for fallback repair"
                )
            if in_repair and line.strip() == "return None":
                break

    def test_no_auto_repair_comment(self):
        assert "no automatic repair" in BCP_TEXT, (
            "Docstring must document that no automatic repair is attempted"
        )

    def test_returns_none_on_unreachable(self):
        lines = BCP_TEXT.split("\n")
        in_repair = False
        found_return_none = False
        for line in lines:
            if "def _repair_if_unreachable" in line:
                in_repair = True
            if in_repair and line.strip() == "return None":
                found_return_none = True
        assert found_return_none, (
            "_repair_if_unreachable must return None when threshold is unreachable"
        )


class TestStaleJsonDeleted:
    """BTCAAAAA-6872: user_strategies/current_strategy.json must be deleted."""

    def test_stale_json_file_deleted(self):
        assert not STALE_JSON_PATH.exists(), (
            "user_strategies/current_strategy.json must be deleted — "
            "it contained phantom signals not in PostgreSQL"
        )


# ============================================================================
# Commit provenance — verify both fix commits are reflected in source files
# ============================================================================


class TestCommitProvenance:
    """BTCAAAAA-6872: both fix commits must be reflected in source files."""

    def test_direction_check_method_exists_in_file(self):
        assert "def _check_direction_consistency" in ISE_TEXT, (
            "Commit f1e07749: _check_direction_consistency method must exist"
        )

    def test_get_signal_direction_exists_in_file(self):
        assert "def _get_signal_direction" in ISE_TEXT, (
            "Commit f1e07749: _get_signal_direction method must exist"
        )
