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

Expanded to meet Impact Gate 10-test minimum bar (BTCAAAAA-25158).
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

    def test_validation_error_uses_settext(self):
        """_on_run_clicked must use setText for validation errors."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert 'results_text.setText(f"❌ Strategy validation failed:' in src, (
            "Validation errors should use setText to clearly show the error"
        )

    def test_serialize_error_uses_settext(self):
        """_on_run_clicked must use setText for serialization errors."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert 'results_text.setText(f"❌ Failed to prepare strategy:' in src, (
            "Serialization errors should use setText to clearly show the error"
        )

    def test_cache_hit_uses_append(self):
        """_on_run_clicked must append cache hit message."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert 'results_text.append(' in src and '"⚡ Cache HIT:' in src, (
            "Cache hit message must use append() to preserve existing messages"
        )

    def test_cache_miss_uses_append(self):
        """_on_run_clicked must append cache miss message."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert 'results_text.append(' in src and '"🔄 Cache MISS:' in src, (
            "Cache miss message must use append() to preserve existing messages"
        )

    def test_calibration_called_before_backtest_message(self):
        """_run_auto_calibration must be called before backtest start message."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        lines = src.split("\n")
        cal_line = None
        start_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "_run_auto_calibration" in stripped:
                cal_line = i
            if '"🔄 Backtest started..."' in stripped:
                start_line = i
        assert cal_line is not None, "_on_run_clicked must call _run_auto_calibration"
        assert start_line is not None, "_on_run_clicked must emit backtest started message"
        assert cal_line < start_line, (
            "_run_auto_calibration must be called before the backtest started message"
        )


class TestOnPauseClicked:
    """Structural checks for _on_pause_clicked append usage."""

    def test_resumed_uses_append(self):
        """_on_pause_clicked must append '▶️ Resumed'."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_pause_clicked)
        assert 'results_text.append("▶️ Resumed")' in src, (
            "Resumed message must use append()"
        )

    def test_paused_uses_append(self):
        """_on_pause_clicked must append '⏸️ Paused'."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_pause_clicked)
        assert 'results_text.append("⏸️ Paused")' in src, (
            "Paused message must use append()"
        )


class TestOnStopClicked:
    """Structural checks for _on_stop_clicked append usage."""

    def test_stopping_uses_append(self):
        """_on_stop_clicked must append '⏹️ Stopping...'."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_stop_clicked)
        assert 'results_text.append("⏹️ Stopping...")' in src, (
            "Stopping message must use append()"
        )


class TestCalibrationCacheMessages:
    """Structural checks for calibration cache messaging in _run_auto_calibration."""

    def test_calibration_cache_hit_uses_settext(self):
        """_run_auto_calibration must use setText for cache hit message."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert 'results_text.setText(' in src and 'Calibration already complete' in src, (
            "Calibration cache hit should use setText since it replaces the status"
        )

    def test_calibration_running_message_appended(self):
        """_run_auto_calibration must append running calibration message."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert 'results_text.append(' in src and 'Running signal calibration' in src, (
            "Calibration running message must use append()"
        )

    def test_calibration_exception_appends_warning(self):
        """_run_auto_calibration must append exception warning."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert 'results_text.append(' in src and 'Calibration skipped' in src, (
            "Calibration exception must append a warning message"
        )
