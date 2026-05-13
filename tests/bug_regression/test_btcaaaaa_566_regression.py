"""
Regression tests for BTCAAAAA-566: remove obsolete test wiring button and dead code.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-566
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: A stale "Test Wiring" button (test_wiring_btn), its 150+ line
_on_test_wiring_clicked handler, and the _generate_wiring_report wrapper
remained in the codebase long after their functionality was superseded by
Config Discovery (_on_config_discovery_clicked).

Fix:
- Remove test_wiring_btn QPushButton and its hardcoded stylesheet
- Remove _on_test_wiring_clicked handler (150+ lines of dead code)
- Remove _generate_wiring_report wrapper (superseded by Config Discovery)
- Config Discovery and shared helpers preserved and unaffected
"""
from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-566"),
    pytest.mark.regression,
]

_BacktestConfigPanel = None


def _get_panel_class():
    global _BacktestConfigPanel
    if _BacktestConfigPanel is None:
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        _BacktestConfigPanel = BacktestConfigPanel
    return _BacktestConfigPanel


class TestDeadCodeRemoved:
    """Verify the obsolete test wiring dead code has been removed."""

    def test_on_test_wiring_clicked_removed(self):
        """_on_test_wiring_clicked must NOT exist on the panel class."""
        cls = _get_panel_class()
        assert not hasattr(cls, "_on_test_wiring_clicked"), (
            "_on_test_wiring_clicked dead code was not removed"
        )

    def test_generate_wiring_report_removed(self):
        """_generate_wiring_report wrapper must NOT exist on the panel class."""
        cls = _get_panel_class()
        assert not hasattr(cls, "_generate_wiring_report"), (
            "_generate_wiring_report dead code was not removed"
        )


class TestConfigDiscoveryPreserved:
    """Verify Config Discovery infrastructure is still intact."""

    def test_on_config_discovery_clicked_exists(self):
        cls = _get_panel_class()
        assert hasattr(cls, "_on_config_discovery_clicked")

    def test_capture_ui_state_exists(self):
        cls = _get_panel_class()
        assert hasattr(cls, "_capture_ui_state")

    def test_restore_ui_state_exists(self):
        cls = _get_panel_class()
        assert hasattr(cls, "_restore_ui_state")

    def test_apply_scenario_to_ui_exists(self):
        cls = _get_panel_class()
        assert hasattr(cls, "_apply_scenario_to_ui")

    def test_run_test_and_wait_exists(self):
        cls = _get_panel_class()
        assert hasattr(cls, "_run_test_and_wait")

    def test_generate_discovery_report_exists(self):
        cls = _get_panel_class()
        assert hasattr(cls, "_generate_discovery_report")

    def test_config_discovery_btn_in_create_control_buttons(self):
        cls = _get_panel_class()
        src = inspect.getsource(cls._create_control_buttons)
        assert 'self.config_discovery_btn = QPushButton("Config Discovery")' in src, (
            "Config Discovery button must still be created in _create_control_buttons"
        )

    def test_no_test_wiring_btn_in_init_or_ui(self):
        cls = _get_panel_class()
        init_src = inspect.getsource(cls.__init__)
        ui_src = inspect.getsource(cls._init_ui)
        ctrl_src = inspect.getsource(cls._create_control_buttons)
        combined = init_src + ui_src + ctrl_src
        assert "test_wiring_btn" not in combined, (
            "test_wiring_btn must not be created in __init__, _init_ui, or _create_control_buttons"
        )
