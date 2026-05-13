"""
Regression tests for BTCAAAAA-348: simulation mode guard in _run_auto_calibration.

Issue: BTCAAAAA-348
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: when TrainingThread ran in simulation mode, it produced random/dummy
calibration results that could overwrite manually-tuned block delay parameters.

This file verifies the fix: _run_auto_calibration checks
calibration_thread.is_simulation_mode before applying delay_map to blocks,
and skips the apply step when simulation mode is active.
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-348"),
    pytest.mark.regression,
]


class TestSimulationModeGuardPresent:
    """Structural checks that the simulation mode guard exists in source."""

    def test_is_simulation_mode_guard_exists(self):
        """_run_auto_calibration must contain is_simulation_mode guard."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "is_simulation_mode" in src, (
            "_run_auto_calibration must check calibration_thread.is_simulation_mode "
            "to protect manually-tuned block delays"
        )

    def test_simulation_mode_guard_skips_apply(self):
        """The is_simulation_mode branch must skip delay_map application."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "simulation mode" in src.lower(), (
            "When is_simulation_mode is True, a 'simulation mode' message must be "
            "appended to the status area"
        )
        lines = src.split("\n")
        in_simulation_branch = False
        found_apply_in_branch = False
        for line in lines:
            stripped = line.strip()
            if "is_simulation_mode" in stripped and ":" in stripped:
                in_simulation_branch = True
                continue
            if in_simulation_branch:
                if "optimal_delay" in stripped and "=" in stripped:
                    found_apply_in_branch = True
                    break
                if stripped and not stripped.startswith((" ", "\t")):
                    break
                if stripped.startswith("else:"):
                    break
        assert not found_apply_in_branch, (
            "optimal_delay must NOT be set on blocks inside the "
            "is_simulation_mode = True branch"
        )

    def test_simulation_mode_guard_logs_message(self):
        """The simulation mode guard must log a warning message."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "using configured block delays" in src, (
            "Simulation mode guard must log a message indicating configured "
            "block delays are preserved"
        )
