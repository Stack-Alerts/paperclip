"""
Regression tests for BTCAAAAA-92: Auto-resize SettingsDialog on tab switch.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-92
Component: src/strategy_builder/ui/settings_dialog.py

Root cause: Switching between tabs (API Keys / Preferences / Admin) in
SettingsDialog could clip content when a tab's layout was taller than the
previous tab's, because the dialog never re-computed its ideal size.

Fix:
- Connect QTabWidget.currentChanged to QTimer.singleShot(0, self.adjustSize)
  so the dialog re-sizes to fit the newly selected tab's content.
- In _reveal_admin_tab(), call QTimer.singleShot(0, self.adjustSize) after
  making the Admin tab visible and switching to it, so the extra Admin
  content (badge, DB fields) does not get clipped.
"""

from __future__ import annotations

import ast
import pathlib
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-92"),
    pytest.mark.regression,
]

SOURCE_PATH = pathlib.Path("src/strategy_builder/ui/settings_dialog.py")


def _make_service_mock() -> MagicMock:
    mock = MagicMock()
    mock.is_admin.return_value = False
    mock.role = MagicMock()
    mock.role.value = "user"
    mock.has_admin_pin.return_value = False
    mock.get_masked.return_value = ""
    mock.get.return_value = None
    mock.get_with_default.return_value = ""
    mock._check_access.return_value = None
    return mock


class TestTabSwitchAdjustSizeSource:
    """
    Source-level checks that the tab-switch adjustSize wiring is present.

    BTCAAAAA-92 requires:
      1. QTabWidget.currentChanged connected to QTimer.singleShot(0, adjustSize)
      2. _reveal_admin_tab() calls QTimer.singleShot(0, self.adjustSize)
    """

    def test_current_changed_connected_to_adjust_size(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)

        found = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "singleShot":
                continue
            if len(node.args) >= 2:
                first = node.args[0]
                second = node.args[1]
                if (
                    isinstance(first, ast.Constant)
                    and first.value == 0
                    and isinstance(second, ast.Attribute)
                    and second.attr == "adjustSize"
                ):
                    found = True
                    break

        assert found, (
            "No QTimer.singleShot(0, <something>.adjustSize) call found in "
            "settings_dialog.py. BTCAAAAA-92 requires the tab widget's "
            "currentChanged signal to trigger adjustSize()."
        )

    def test_current_changed_signal_wired_to_lambda_with_timer(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)

        found_tab_connect = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "connect":
                continue
            if not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Lambda):
                body = arg.body
                if isinstance(body, ast.Call):
                    func = body.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr == "singleShot"
                    ):
                        found_tab_connect = True
                        break

        assert found_tab_connect, (
            "No lambda connected to a signal that calls QTimer.singleShot found "
            "in settings_dialog.py. BTCAAAAA-92 requires "
            "currentChanged.connect(lambda _idx: QTimer.singleShot(0, self.adjustSize))."
        )


class TestRevealAdminTabAdjustSize:
    """_reveal_admin_tab must call QTimer.singleShot(0, self.adjustSize)."""

    def test_reveal_admin_tab_calls_adjust_size(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)

        calls_in_reveal = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_reveal_admin_tab":
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute) and child.func.attr == "singleShot":
                            calls_in_reveal.append(child)

        assert len(calls_in_reveal) > 0, (
            "_reveal_admin_tab() must call QTimer.singleShot() to trigger "
            "adjustSize() after revealing the Admin tab (BTCAAAAA-92)."
        )

        has_adjustsize = any(
            len(c.args) >= 2
            and isinstance(c.args[0], ast.Constant)
            and c.args[0].value == 0
            and isinstance(c.args[1], ast.Attribute)
            and c.args[1].attr == "adjustSize"
            for c in calls_in_reveal
        )

        assert has_adjustsize, (
            "_reveal_admin_tab() calls singleShot but not with "
            "(0, self.adjustSize) pattern (BTCAAAAA-92)."
        )


class TestSettingsDialogTabSwitchBehavior:
    """Runtime test: switching tabs triggers adjustSize on SettingsDialog."""

    def test_tab_switch_triggers_adjust_size(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SettingsDialog
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = _make_service_mock()
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=svc,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            with patch.object(dlg, "adjustSize") as mock_adjust:
                dlg._tabs.setCurrentIndex(1)
                qapp.processEvents()
                assert mock_adjust.called, (
                    "adjustSize() was not called after switching tabs. "
                    "BTCAAAAA-92 requires currentChanged -> QTimer.singleShot(0, adjustSize)."
                )
            dlg.close()

    def test_reveal_admin_triggers_adjust_size(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SettingsDialog
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = _make_service_mock()
        svc.is_admin.return_value = True
        svc.role.value = "admin"
        svc.has_admin_pin.return_value = True
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=svc,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            with patch.object(dlg, "adjustSize") as mock_adjust:
                dlg._reveal_admin_tab()
                qapp.processEvents()
                assert mock_adjust.called, (
                    "adjustSize() was not called after _reveal_admin_tab(). "
                    "BTCAAAAA-92 requires QTimer.singleShot(0, self.adjustSize)."
                )
            dlg.close()
