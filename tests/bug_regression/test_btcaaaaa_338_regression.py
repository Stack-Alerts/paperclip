"""
Regression tests for BTCAAAAA-338: Remove Calibrate tab, implement auto-calibration.

Issue: BTCAAAAA-338
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: The dedicated "⚙️ Calibrate" tab was removed and calibration was
made automatic — it now runs transparently via _run_auto_calibration() before
every backtest, without user interaction or a separate tab.

Fix:
1. Remove TrainingPanelUI instantiation from _init_ui
2. Remove _is_calibrated() gate method
3. Add _run_auto_calibration() with fingerprint-based skip logic
4. Wire _run_auto_calibration() into _on_run_clicked()
5. Calibration uses production mode, 15m timeframe, 180-day lookback
6. Exception handling for graceful degradation
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-338"),
    pytest.mark.regression,
]


class TestAutoCalibrationStructural:
    """Structural checks that the old gate is removed and auto-calibration is present."""

    def test_is_calibrated_method_removed(self):
        """_is_calibrated() must NOT exist in BacktestConfigPanel."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        assert not hasattr(BacktestConfigPanel, "_is_calibrated"), (
            "_is_calibrated() must be removed — calibration now runs automatically"
        )

    def test_run_auto_calibration_method_exists(self):
        """_run_auto_calibration() must exist on BacktestConfigPanel."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        assert hasattr(BacktestConfigPanel, "_run_auto_calibration"), (
            "_run_auto_calibration() must exist on BacktestConfigPanel"
        )

    def test_auto_calibration_called_in_on_run_clicked(self):
        """_on_run_clicked() source must call _run_auto_calibration."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "_run_auto_calibration" in src, (
            "_on_run_clicked() must call _run_auto_calibration()"
        )

    def test_no_calibration_required_dialog(self):
        """_on_run_clicked() must not contain 'Calibration Required' dialog text."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "Calibration Required" not in src, (
            "Old 'Calibration Required' dialog must not appear in _on_run_clicked"
        )

    def test_no_set_current_index_redirect(self):
        """_on_run_clicked() must NOT contain setCurrentIndex(1) (old Calibrate redirect)."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "setCurrentIndex(1)" not in src, (
            "_on_run_clicked() must not redirect to tab index 1; "
            "Calibrate tab has been removed"
        )

    def test_cache_attributes_initialized(self):
        """__init__ must set _calibration_fingerprint and _calibration_cache."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel.__init__)
        assert "_calibration_fingerprint" in src, (
            "_calibration_fingerprint must be initialized in __init__"
        )
        assert "_calibration_cache" in src, (
            "_calibration_cache must be initialized in __init__"
        )

    def test_json_imported_at_module_level(self):
        """json must be imported at the top of backtest_config_panel.py."""
        import src.strategy_builder.ui.backtest_config_panel as mod

        src_lines = inspect.getsource(mod).split("\n")
        assert any(line.strip() == "import json" for line in src_lines[:50]), (
            "'import json' must appear in the first 50 lines of the module"
        )

    def test_calibration_cache_imported_at_module_level(self):
        """calibration_cache must be imported at module level."""
        import src.strategy_builder.ui.backtest_config_panel as mod

        src_lines = inspect.getsource(mod).split("\n")
        assert any(
            "calibration_cache" in line for line in src_lines[:100]
        ), "'calibration_cache' import must appear in the first 100 lines of the module"


class TestAutoCalibrationParameters:
    """_run_auto_calibration() must use correct hardcoded parameters."""

    def test_uses_production_mode(self):
        """_run_auto_calibration() must use 'production' mode."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "'production'" in src or '"production"' in src, (
            "_run_auto_calibration() must use mode='production'"
        )

    def test_uses_15m_timeframe(self):
        """_run_auto_calibration() must hardcode '15m' timeframe."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "'15m'" in src or '"15m"' in src, (
            "_run_auto_calibration() must hardcode timeframe '15m'"
        )

    def test_uses_180_day_lookback(self):
        """_run_auto_calibration() must hardcode 180-day lookback."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "180" in src, (
            "_run_auto_calibration() must hardcode 180-day lookback period"
        )

    def test_has_graceful_degradation(self):
        """_run_auto_calibration() must have exception handling."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "except" in src, (
            "_run_auto_calibration() must catch exceptions and degrade gracefully"
        )

    def test_has_fingerprint_skip_logic(self):
        """_run_auto_calibration() must have fingerprint-based cache skip."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "current_fingerprint" in src, (
            "_run_auto_calibration() must compute a fingerprint for cache skip"
        )
