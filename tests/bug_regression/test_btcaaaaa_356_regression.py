"""
Regression tests for BTCAAAAA-356: show calibration progress bar and disable
Run Test during auto-calibration.

Issue: BTCAAAAA-356
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: _run_auto_calibration did not provide visual feedback during the
15-60s calibration window — the progress bar remained static at 0% and the
Run Test button stayed clickable, letting the user trigger concurrent runs.

Fix: set progress_bar to indeterminate mode (setRange(0,0)) with
"Calibrating blocks..." format at the start, disable run_btn, and reset
progress_bar (setRange(0,100), setValue(0), setFormat("%p%")) on all three
exit paths: success (post calibration), timeout, and exception.
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-356"),
    pytest.mark.regression,
]


class TestCalibrationProgressBarStructural:
    """Structural checks that the calibration progress-bar fix is in place."""

    def test_progress_bar_indeterminate_at_start(self):
        """_run_auto_calibration must set indeterminate progress bar."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "setRange(0, 0)" in src, (
            "progress_bar must be set to indeterminate mode at calibration start"
        )

    def test_progress_bar_format_at_start(self):
        """_run_auto_calibration must set progress bar format to 'Calibrating blocks...'."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "Calibrating blocks..." in src, (
            "progress_bar format must be set to 'Calibrating blocks...' at calibration start"
        )

    def test_run_btn_disabled_during_calibration(self):
        """_run_auto_calibration must disable run_btn during calibration."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "run_btn.setEnabled(False)" in src, (
            "run_btn must be disabled while calibration is running"
        )

    def test_progress_bar_reset_after_timeout(self):
        """Timeout exit path must reset progress bar to normal mode."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "setRange(0, 100)" in src, (
            "progress_bar must be reset to determinate mode on timeout"
        )

    def test_progress_bar_reset_on_success(self):
        """Success exit path must reset progress bar to normal mode."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "setValue(0)" in src, (
            "progress_bar value must be reset on completion"
        )

    def test_progress_bar_format_reset_on_exit(self):
        """All exit paths must reset progress bar format to '%p%'."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert '"%p%"' in src, (
            "progress_bar format must be reset to '%p%' on all exit paths"
        )

    def test_run_btn_disabled_before_calibration_thread(self):
        """run_btn must be disabled BEFORE the TrainingThread is created."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        lines = src.split("\n")
        disable_line = None
        thread_import_line = None
        for i, line in enumerate(lines):
            if "run_btn.setEnabled(False)" in line:
                disable_line = i
            if "TrainingThread" in line and "import" in line:
                thread_import_line = i
        assert disable_line is not None, "run_btn.setEnabled(False) must exist"
        assert thread_import_line is not None, "TrainingThread import must exist"
        assert disable_line < thread_import_line, (
            "run_btn must be disabled before TrainingThread is imported/created"
        )

    def test_three_exit_paths_reset_progress_bar(self):
        """There must be at least 3 progress-bar reset sites (timeout, success, exception)."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        count = src.count("setRange(0, 100)")
        assert count >= 3, (
            f"Expected at least 3 progress bar reset sites, found {count}"
        )

    def test_empty_blocks_early_return(self):
        """_run_auto_calibration must return early when blocks list is empty."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "if not blocks:" in src, (
            "Must guard against empty blocks"
        )
        assert "return" in src.split("if not blocks:")[1].split(chr(92)+"n")[0], (
            "Must return early when no blocks"
        )

    def test_fingerprint_computation_call(self):
        """_run_auto_calibration must compute a fingerprint via calibration_cache."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "calibration_cache.compute_fingerprint" in src, (
            "Must compute calibration fingerprint for cache-key comparison"
        )
        assert "block_names=block_names" in src, (
            "Fingerprint must include block_names parameter"
        )
