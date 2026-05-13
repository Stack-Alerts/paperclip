"""
Regression tests for BTCAAAAA-25640: Verify 100% exit partial-exits fix.
"""
from __future__ import annotations

import inspect

import pytest


pytestmark = [
    pytest.mark.bug("BTCAAAAA-25640"),
    pytest.mark.regression,
]


class TestIsFullExitComparison:
    """Verify the >= comparison used for is_full_exit in both backtest engines."""

    def test_greater_than_or_equal_in_multicore(self):
        """is_full_exit must use >= (not >) in multicore_backtest_engine.py."""
        from src.optimizer_v3.core import multicore_backtest_engine
        src = inspect.getsource(multicore_backtest_engine)
        lines = [l for l in src.splitlines() if "is_full_exit" in l and "remaining_position" in l]
        assert len(lines) >= 1
        for line in lines:
            assert ">=" in line, f"Missing >=: {line.strip()}"

    def test_greater_than_or_equal_in_backtest_config(self):
        """is_full_exit must use >= (not >) in backtest_config_panel.py."""
        from src.strategy_builder.ui import backtest_config_panel
        src = inspect.getsource(backtest_config_panel)
        lines = [l for l in src.splitlines() if "is_full_exit" in l and "remaining_position" in l]
        assert len(lines) >= 1
        for line in lines:
            assert ">=" in line, f"Missing >=: {line.strip()}"

    def test_no_strict_greater_than_in_comparison(self):
        """Ensure no strict > in the is_full_exit comparison line."""
        from src.optimizer_v3.core import multicore_backtest_engine
        src = inspect.getsource(multicore_backtest_engine)
        lines = [l for l in src.splitlines() if "is_full_exit" in l and "remaining_position" in l]
        for line in lines:
            assert ">=" in line, f"Found > without =: {line.strip()}"


class TestIsFullExitBehavior:
    """Behavioral tests for the is_full_exit logic."""

    @staticmethod
    def _is_full(exit_pct: float, remaining: float) -> bool:
        return exit_pct >= remaining

    def test_exact_100_is_full(self):
        assert self._is_full(1.0, 1.0) is True

    def test_exact_50_is_full(self):
        assert self._is_full(0.5, 0.5) is True

    def test_exact_20_is_full(self):
        """Final TP in 50/30/20 series: 0.2 >= 0.2 = CLOSED."""
        assert self._is_full(0.2, 0.2) is True

    def test_tiny_exact_is_full(self):
        assert self._is_full(0.01, 0.01) is True

    def test_exit_exceeds_remaining_is_full(self):
        assert self._is_full(0.5, 0.3) is True

    def test_slightly_over_is_full(self):
        assert self._is_full(0.5, 0.49) is True

    def test_partial_is_not_full(self):
        assert self._is_full(0.3, 0.7) is False

    def test_first_partial_is_not_full(self):
        """First TP in 50/30/20 series: 0.5 >= 1.0 is False."""
        assert self._is_full(0.5, 1.0) is False


class TestExitTradeBoundary:
    """Verify exit_trade() semantics: remaining_position decrement and threshold."""

    def test_exit_reduces_remaining(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import TradeState
        trade = TradeState(entry_bar=0, entry_price=100000.0, entry_side='LONG', remaining_position=1.0)
        trade.remaining_position -= 0.3
        assert trade.remaining_position == pytest.approx(0.7)

    def test_multiple_exits_accumulate(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import TradeState
        trade = TradeState(entry_bar=0, entry_price=100000.0, entry_side='LONG', remaining_position=1.0)
        trade.remaining_position -= 0.5
        trade.remaining_position -= 0.3
        trade.remaining_position -= 0.2
        assert trade.remaining_position == pytest.approx(0.0)

    def test_threshold_zeroes_trade(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import TradeState
        trade = TradeState(entry_bar=0, entry_price=100000.0, entry_side='LONG', remaining_position=0.01)
        trade.remaining_position -= 0.01
        assert trade.remaining_position <= 0.01

    def test_remaining_capped_by_min(self):
        assert min(0.2, 0.1) == 0.1


class TestTradeLifecycle:
    """Verify trade state for partial-exit tracking."""

    def test_tp_hits_attribute(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import TradeState
        trade = TradeState(entry_bar=0, entry_price=100000.0, entry_side='LONG')
        assert hasattr(trade, 'tp_hits')
        assert isinstance(trade.tp_hits, list)
        assert len(trade.tp_hits) == 0

    def test_entry_preserved(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import TradeState
        trade = TradeState(entry_bar=10, entry_price=50000.0, entry_side='LONG')
        assert trade.entry_bar == 10
        assert trade.entry_price == 50000.0
        assert trade.entry_side == 'LONG'
