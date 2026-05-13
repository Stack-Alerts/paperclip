"""
Regression tests for BTCAAAAA-699: add objectName to key dialogs for pytest-qt targeting.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-699
Fixed in commit: c6fbb79e

Changed files:
  - src/strategy_builder/ui/main_window.py
  - src/strategy_builder/ui/strategy_builder_main_window.py
  - src/strategy_builder/ui/new_strategy_dialog.py
  - src/strategy_builder/ui/settings_dialog.py
  - src/strategy_builder/ui/backtest_config_dialog.py

Fix: Added setObjectName() calls on 5 dialogs and their critical widgets
so that pytest-qt tests can target them by object name.

This file verifies that every setObjectName call from the fix remains present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-699"),
    pytest.mark.regression,
]

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]


# ---------------------------------------------------------------------------
# src/strategy_builder/ui/main_window.py
# ---------------------------------------------------------------------------

_MAIN_WINDOW_PATH = _REPO_ROOT / "src/strategy_builder/ui/main_window.py"


def _main_window_source() -> str:
    return _MAIN_WINDOW_PATH.read_text(encoding="utf-8")


class TestMainWindowObjectName:
    def test_main_window_has_object_name(self):
        source = _main_window_source()
        assert 'self.setObjectName("main_window")' in source


# ---------------------------------------------------------------------------
# src/strategy_builder/ui/strategy_builder_main_window.py
# ---------------------------------------------------------------------------

_SB_MAIN_WINDOW_PATH = (
    _REPO_ROOT / "src/strategy_builder/ui/strategy_builder_main_window.py"
)


def _sb_main_window_source() -> str:
    return _SB_MAIN_WINDOW_PATH.read_text(encoding="utf-8")


class TestStrategyBuilderMainWindowObjectName:
    def test_strategy_builder_main_window_has_object_name(self):
        source = _sb_main_window_source()
        assert 'self.setObjectName("strategy_builder_main_window")' in source


# ---------------------------------------------------------------------------
# src/strategy_builder/ui/new_strategy_dialog.py
# ---------------------------------------------------------------------------

_NEW_STRATEGY_DIALOG_PATH = (
    _REPO_ROOT / "src/strategy_builder/ui/new_strategy_dialog.py"
)


def _new_strategy_dialog_source() -> str:
    return _NEW_STRATEGY_DIALOG_PATH.read_text(encoding="utf-8")


class TestNewStrategyDialogObjectName:
    def test_new_strategy_dialog_has_object_name(self):
        source = _new_strategy_dialog_source()
        assert 'self.setObjectName("new_strategy_dialog")' in source

    def test_strategy_name_input_has_object_name(self):
        source = _new_strategy_dialog_source()
        assert 'self.name_input.setObjectName("strategy_name_input")' in source

    def test_strategy_desc_input_has_object_name(self):
        source = _new_strategy_dialog_source()
        assert 'self.desc_input.setObjectName("strategy_desc_input")' in source

    def test_cancel_btn_has_object_name(self):
        source = _new_strategy_dialog_source()
        assert 'self.cancel_btn.setObjectName("cancel_btn")' in source

    def test_create_btn_has_object_name(self):
        source = _new_strategy_dialog_source()
        assert 'self.create_btn.setObjectName("create_strategy_btn")' in source


# ---------------------------------------------------------------------------
# src/strategy_builder/ui/settings_dialog.py — SettingsDialog
# ---------------------------------------------------------------------------

_SETTINGS_DIALOG_PATH = _REPO_ROOT / "src/strategy_builder/ui/settings_dialog.py"


def _settings_dialog_source() -> str:
    return _SETTINGS_DIALOG_PATH.read_text(encoding="utf-8")


class TestSettingsDialogObjectName:
    def test_settings_dialog_has_object_name(self):
        source = _settings_dialog_source()
        assert 'self.setObjectName("settings_dialog")' in source

    def test_settings_tabs_has_object_name(self):
        source = _settings_dialog_source()
        assert 'self._tabs.setObjectName("settings_tabs")' in source

    def test_settings_cancel_btn_has_object_name(self):
        source = _settings_dialog_source()
        assert 'cancel_btn.setObjectName("cancel_btn")' in source

    def test_settings_save_btn_has_object_name(self):
        source = _settings_dialog_source()
        assert 'save_btn.setObjectName("save_btn")' in source

    def test_admin_auth_btn_has_object_name(self):
        source = _settings_dialog_source()
        assert 'self._admin_auth_btn.setObjectName("admin_auth_btn")' in source

    def test_admin_lock_btn_has_object_name(self):
        source = _settings_dialog_source()
        assert 'self._admin_lock_btn.setObjectName("admin_lock_btn")' in source


# ---------------------------------------------------------------------------
# src/strategy_builder/ui/settings_dialog.py — AdminPinDialog
# ---------------------------------------------------------------------------


class TestAdminPinDialogObjectName:
    def test_admin_pin_dialog_has_object_name(self):
        source = _settings_dialog_source()
        assert 'self.setObjectName("admin_pin_dialog")' in source

    def test_pin_input_has_object_name(self):
        source = _settings_dialog_source()
        assert 'self._pin_field.setObjectName("pin_input")' in source


# ---------------------------------------------------------------------------
# src/strategy_builder/ui/backtest_config_dialog.py
# ---------------------------------------------------------------------------

_BACKTEST_CONFIG_DIALOG_PATH = (
    _REPO_ROOT / "src/strategy_builder/ui/backtest_config_dialog.py"
)


def _backtest_config_dialog_source() -> str:
    return _BACKTEST_CONFIG_DIALOG_PATH.read_text(encoding="utf-8")


class TestBacktestConfigDialogObjectName:
    def test_backtest_config_dialog_has_object_name(self):
        source = _backtest_config_dialog_source()
        assert 'self.setObjectName("backtest_config_dialog")' in source
