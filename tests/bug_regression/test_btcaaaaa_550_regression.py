"""
Regression tests for BTCAAAAA-550: fix calibration messages overwritten by
setText on backtest start.

Issue: BTCAAAAA-550
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: In _on_run_clicked(), self.results_text.setText("🔄 Backtest started...\n")
at the end of the method overwrote all calibration messages that had been appended
by _run_auto_calibration earlier in the same call chain. Users could not see the
calibration event log (signal calibration, cache hit/miss, calibration complete).

Fix: Replace setText with append() so calibration messages are preserved and
the user sees the full sequence:
    ✓ Calibration complete. Starting backtest...
    🔄 Backtest started...
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-550"),
    pytest.mark.regression,
]


class TestCalibrationMessagesPreserved:
    """Structural checks that _on_run_clicked uses append() not setText()."""

    def test_backtest_started_uses_append_not_settext(self):
        """_on_run_clicked must use append() for '🔄 Backtest started...'."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert 'results_text.append("🔄 Backtest started...")' in src, (
            "results_text must use append() not setText() for '🔄 Backtest started...' "
            "to preserve calibration messages"
        )

    def test_no_settext_for_backtest_started_message(self):
        """_on_run_clicked must NOT use setText for the backtest started message."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        lines = src.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "results_text.setText" in stripped and "Backtest started" in stripped:
                pytest.fail(
                    f"Line {i+1} still uses setText for backtest started message: {stripped}"
                )

    def test_calibration_complete_message_appended(self):
        """_run_auto_calibration should append calibration-complete message."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert 'results_text.append("✓ Calibration complete.' in src, (
            "_run_auto_calibration must append a calibration-complete message "
            "before returning on success"
        )
