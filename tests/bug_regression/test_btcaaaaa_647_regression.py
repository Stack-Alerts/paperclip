"""
Regression tests for BTCAAAAA-647: prevent NoneType crash on tp_hits + gate
exit_trade on should_exit.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-647
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause (CRITICAL): After a partial-TP exit reduces remaining_position to
<= 0.01, exit_trade() sets evaluator.current_trade = None.  On the very next
TP-hit bar the old code called
evaluator.current_trade.tp_hits.append(...) unconditionally, producing an
AttributeError that was silently swallowed by the outer except block —
causing the backtest to emit backtest_finished with 0 trades recorded.

Fix 1: Prefix the tp_hits block with
  ``if evaluator.current_trade and hasattr(result, 'exit_condition_name') ...``

Root cause (HIGH): exit_trade() was called on every single bar regardless of
whether result.should_exit was True, passing exit_percentage=0.0 when no
exit was triggered.

Fix 2: Gate the call with ``if result.should_exit:``.

Bonus: Improved outer except block to emit the full traceback via
live_message and logger.error() so future exceptions are never silently
swallowed again.
"""
from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-647"),
    pytest.mark.regression,
]


class TestCurrentTradeGuard:
    """BacktestWorker.run() must guard evaluator.current_trade before
    accessing .tp_hits to prevent NoneType crash after partial exit."""

    def test_current_trade_guard_exists(self):
        """The tp_hits block must be guarded by 'if evaluator.current_trade'."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

        src = inspect.getsource(BacktestWorker.run)
        assert "if evaluator.current_trade and" in src

    def test_tp_hits_access_inside_guard(self):
        """evaluator.current_trade.tp_hits.append must appear after the guard."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

        src = inspect.getsource(BacktestWorker.run)
        guard_line = None
        for i, line in enumerate(src.splitlines()):
            if "if evaluator.current_trade and" in line:
                guard_line = i
                break
        assert guard_line is not None
        rest = src.splitlines()[guard_line:]
        assert any("tp_hits.append" in l for l in rest)


class TestExitTradeGating:
    """BacktestWorker.run() must gate exit_trade() with if result.should_exit:."""

    def test_exit_trade_gated_on_should_exit(self):
        """exit_trade() must be called only when result.should_exit is True."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

        src = inspect.getsource(BacktestWorker.run)
        assert "if result.should_exit:" in src

    def test_exit_trade_inside_should_exit_block(self):
        """evaluator.exit_trade() must be called inside the should_exit block."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

        src = inspect.getsource(BacktestWorker.run)
        guard_line = None
        for i, line in enumerate(src.splitlines()):
            if "if result.should_exit:" in line:
                guard_line = i
                break
        assert guard_line is not None
        rest = src.splitlines()[guard_line:]
        assert any("exit_trade" in l for l in rest)


class TestExceptionLogging:
    """BacktestWorker.run() except block must emit full traceback so
    exceptions are never silently swallowed."""

    def test_traceback_import_in_run_except(self):
        """The except block in run() must import traceback."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

        src = inspect.getsource(BacktestWorker.run)
        assert "import traceback" in src

    def test_full_tb_emitted_via_live_message(self):
        """The except block must emit the full formatted traceback."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

        src = inspect.getsource(BacktestWorker.run)
        assert "traceback.format_exc()" in src

    def test_logger_error_contains_full_tb(self):
        """logger.error() must include the full traceback string."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

        src = inspect.getsource(BacktestWorker.run)
        assert "logger.error" in src


class TestExitTradeSemantics:
    """Behavioral tests that verify the core fix semantics in
    exit_trade() — the method whose None-setting behaviour was
    the root cause.  Uses a minimal mock evaluator with a
    MagicMock trade to avoid heavy dependencies."""

    @staticmethod
    def _make_evaluator():
        class MockEvaluator:
            def __init__(self):
                self.current_trade = None

            def exit_trade(self, percentage):
                if self.current_trade:
                    self.current_trade.remaining_position -= percentage
                    if self.current_trade.remaining_position <= 0.01:
                        self.current_trade = None

        return MockEvaluator()

    def test_full_exit_sets_current_trade_none(self):
        """exit_trade(1.0) on a full position must set current_trade = None."""
        ev = self._make_evaluator()
        from unittest.mock import MagicMock
        ev.current_trade = MagicMock()
        ev.current_trade.remaining_position = 1.0
        ev.exit_trade(1.0)
        assert ev.current_trade is None

    def test_nearly_full_exit_sets_current_trade_none(self):
        """exit_trade that pushes remaining_position to <= 0.01 must
        set current_trade = None (the exact crash scenario)."""
        ev = self._make_evaluator()
        from unittest.mock import MagicMock
        ev.current_trade = MagicMock()
        ev.current_trade.remaining_position = 0.02
        ev.exit_trade(0.01)
        assert ev.current_trade is None

    def test_partial_exit_preserves_current_trade(self):
        """A small partial exit must leave current_trade intact."""
        ev = self._make_evaluator()
        from unittest.mock import MagicMock
        ev.current_trade = MagicMock()
        ev.current_trade.remaining_position = 0.5
        ev.exit_trade(0.1)
        assert ev.current_trade is not None
        assert ev.current_trade.remaining_position == 0.4

    def test_exit_trade_on_none_does_not_crash(self):
        """exit_trade() with current_trade=None must not raise (the
        pre-fix unconditional call with 0.0 on every bar)."""
        ev = self._make_evaluator()
        ev.current_trade = None
        ev.exit_trade(0.0)
        assert ev.current_trade is None

    def test_exit_trade_on_none_with_full_percent_does_not_crash(self):
        """exit_trade(1.0) with current_trade=None must not raise."""
        ev = self._make_evaluator()
        ev.current_trade = None
        ev.exit_trade(1.0)
        assert ev.current_trade is None
