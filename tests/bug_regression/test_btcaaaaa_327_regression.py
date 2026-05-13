"""
Regression tests for BTCAAAAA-327: implement calibration gate in _on_run_clicked.

Issue: BTCAAAAA-327
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: the original calibration gate (QMessageBox + _is_calibrated()) was
replaced by a fully automatic calibration flow (BTCAAAAA-338/339) that runs
before every backtest without user interaction. The dedicated "" Calibrate
tab was removed and calibration now happens transparently via _run_auto_calibration.

This file tests that:
  1. _run_auto_calibration exists on BacktestConfigPanel (new auto path)
  2. _is_calibrated() does NOT exist (old gate method removed)
  3. "Calibration Required" dialog is NOT in _on_run_clicked source
  4. _run_auto_calibration is called within _on_run_clicked
  5. Calibration cache attributes are initialized in __init__
  6. json and calibration_cache are imported at module level
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-327"),
    pytest.mark.regression,
]


class TestCalibrationGateStructuralRequirements:
    """Structural checks that the old gate is removed and the auto path is present."""

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

    def test_no_calibration_required_dialog(self):
        """_on_run_clicked() must not contain 'Calibration Required' dialog text."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "Calibration Required" not in src, (
            "Old 'Calibration Required' dialog must not appear in _on_run_clicked"
        )

    def test_auto_calibration_called_in_on_run_clicked(self):
        """_on_run_clicked() source must call _run_auto_calibration."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "_run_auto_calibration" in src, (
            "_on_run_clicked() must call _run_auto_calibration()"
        )

    def test_cache_attributes_initialized_in_init(self):
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

    def test_run_auto_calibration_has_graceful_degradation(self):
        """_run_auto_calibration() must have exception handling."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "except" in src, (
            "_run_auto_calibration() must catch exceptions and degrade gracefully"
        )

    def test_run_auto_calibration_uses_production_mode(self):
        """_run_auto_calibration() must use 'production' mode."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "'production'" in src or '"production"' in src, (
            "_run_auto_calibration() must use mode='production'"
        )

    def test_run_auto_calibration_uses_15m_timeframe(self):
        """_run_auto_calibration() must hardcode '15m' timeframe."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "'15m'" in src or '"15m"' in src, (
            "_run_auto_calibration() must hardcode timeframe '15m'"
        )

    def test_run_auto_calibration_uses_180_day_lookback(self):
        """_run_auto_calibration() must hardcode 180-day lookback."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "180" in src, (
            "_run_auto_calibration() must hardcode 180-day lookback period"
        )
