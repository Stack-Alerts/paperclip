"""
Regression tests for BTCAAAAA-348: simulation mode guard in _run_auto_calibration.

Issue: BTCAAAAA-348
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: when TrainingThread ran in simulation mode, it produced random/dummy
calibration results that could overwrite manually-tuned block delay parameters.

This file verifies the fix: _run_auto_calibration checks
calibration_thread.is_simulation_mode before applying delay_map to blocks,
and skips the apply step when simulation mode is active.

Acceptance criteria tested here:
  AC1  _run_auto_calibration contains is_simulation_mode guard.
  AC2  The simulation-mode branch does not apply optimal_delay to blocks.
  AC3  The simulation-mode guard logs "using configured block delays".
  AC4  _run_auto_calibration returns early when blocks list is empty.
  AC5  Cache-hit path applies cached delay_map in-place and returns early.
  AC6  Cache-hit path produces a user-visible status message.
  AC7  Exception during calibration is caught gracefully (non-blocking).
  AC8  Timeout is handled gracefully without calibration application.
  AC9  _calibration_fingerprint and _calibration_cache attributes exist.
  AC10 Disk cache helpers (_load / _save) exist on BacktestConfigPanel.
  AC11 Fingerprint is stored after a successful cache-miss calibration.
  AC12 File metadata is correct (docstring, markers).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-348"),
    pytest.mark.regression,
]


def _get_run_auto_calibration_src() -> str:
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
    return inspect.getsource(BacktestConfigPanel._run_auto_calibration)


class TestSimulationModeGuardPresent:
    """AC1-AC3: Structural checks that the simulation mode guard exists in source."""

    def test_is_simulation_mode_guard_exists(self):
        """_run_auto_calibration must contain is_simulation_mode guard."""
        src = _get_run_auto_calibration_src()
        assert "is_simulation_mode" in src, (
            "_run_auto_calibration must check calibration_thread.is_simulation_mode "
            "to protect manually-tuned block delays"
        )

    def test_simulation_mode_guard_skips_apply(self):
        """The is_simulation_mode branch must skip delay_map application."""
        src = _get_run_auto_calibration_src()
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
        src = _get_run_auto_calibration_src()
        assert "using configured block delays" in src, (
            "Simulation mode guard must log a message indicating configured "
            "block delays are preserved"
        )


class TestEmptyBlocksGuard:
    """AC4: Verify _run_auto_calibration handles empty blocks gracefully."""

    def test_empty_blocks_early_return(self):
        """_run_auto_calibration must return early when blocks list is empty."""
        src = _get_run_auto_calibration_src()
        assert "if not blocks:" in src, (
            "_run_auto_calibration must guard against empty blocks list"
        )

    def test_empty_blocks_logs_skip_message(self):
        """The empty-blocks early return must log a skip message."""
        src = _get_run_auto_calibration_src()
        assert "no blocks found, skipping" in src.lower(), (
            "Empty blocks guard must log 'no blocks found, skipping'"
        )


class TestCacheHitPath:
    """AC5-AC6: Verify cache-hit path behavior."""

    def test_cache_hit_checks_fingerprint(self):
        """Cache-hit path must compare current_fingerprint with stored fingerprint."""
        src = _get_run_auto_calibration_src()
        assert "current_fingerprint == self._calibration_fingerprint" in src, (
            "Cache hit path must compare fingerprints to detect unchanged settings"
        )

    def test_cache_hit_applies_cached_delay_map(self):
        """On cache hit, cached delay_map must be applied to blocks."""
        src = _get_run_auto_calibration_src()
        assert "cached_delay_map" in src, (
            "Cache hit path must reference cached_delay_map for in-place application"
        )

    def test_cache_hit_sets_status_message(self):
        """On cache hit, a status message must be shown to the user."""
        src = _get_run_auto_calibration_src()
        assert "Calibration already complete" in src, (
            "Cache hit path must display a 'Calibration already complete' message"
        )


class TestCalibrationErrorHandling:
    """AC7-AC8: Verify calibration error handling."""

    def test_exception_handled_gracefully(self):
        """Exception in calibration must be caught and logged, not re-raised."""
        src = _get_run_auto_calibration_src()
        assert "except Exception as e:" in src, (
            "_run_auto_calibration must catch exceptions to prevent blocking backtest"
        )
        assert "non-blocking" in src.lower(), (
            "Calibration failure must be treated as non-blocking"
        )

    def test_timeout_handled_gracefully(self):
        """Calibration timeout must be handled without applying results."""
        src = _get_run_auto_calibration_src()
        assert "timed out" in src.lower(), (
            "Timeout path must log 'timed out' and skip calibration application"
        )


class TestFingerprintStorage:
    """Verify fingerprint and cache management."""

    def test_fingerprint_stored_on_cache_miss(self):
        """After successful cache-miss calibration, fingerprint must be stored."""
        src = _get_run_auto_calibration_src()
        assert "self._calibration_fingerprint" in src, (
            "_run_auto_calibration must update _calibration_fingerprint after "
            "a successful calibration"
        )

    def test_cache_updated_with_new_fingerprint_logged(self):
        """After cache-miss, a log message must confirm cache update."""
        src = _get_run_auto_calibration_src()
        assert "cache updated with new fingerprint" in src.lower(), (
            "After calibration, a log must indicate the cache was updated"
        )


class TestPanelCalibrationAttributes:
    """AC9-AC10: Verify calibration cache attributes and helpers exist."""

    def test_panel_has_calibration_cache_attribute(self):
        """BacktestConfigPanel must set _calibration_cache in __init__."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel.__init__)
        assert "self._calibration_cache" in src

    def test_panel_has_calibration_fingerprint_attribute(self):
        """BacktestConfigPanel must set _calibration_fingerprint in __init__."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel.__init__)
        assert "self._calibration_fingerprint" in src

    def test_panel_has_cache_from_disk_attribute(self):
        """BacktestConfigPanel must set _calibration_cache_from_disk in __init__."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel.__init__)
        assert "self._calibration_cache_from_disk" in src

    def test_load_calibration_disk_cache_method_exists(self):
        """BacktestConfigPanel must have _load_calibration_disk_cache method."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        assert hasattr(BacktestConfigPanel, "_load_calibration_disk_cache")

    def test_save_calibration_disk_cache_method_exists(self):
        """BacktestConfigPanel must have _save_calibration_disk_cache method."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        assert hasattr(BacktestConfigPanel, "_save_calibration_disk_cache")


# ======================================================================
# Impact Gate Meta-Tests
# ======================================================================


class TestFileMetadata:
    """AC12: Validate file structure expected by the Impact Gate runner."""

    def test_file_docstring_contains_issue_number(self):
        assert "BTCAAAAA-348" in (__doc__ or "")

    def test_bug_marker_has_correct_id(self):
        marker_ids = [
            m.args[0] for m in pytestmark
            if hasattr(m, "args") and m.args
        ]
        assert "BTCAAAAA-348" in marker_ids
