"""
Regression tests for BTCAAAAA-87: Width auto-sizing for Settings dialog.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-87
Component: src/strategy_builder/ui/settings_dialog.py

Root cause: SettingsDialog used resize(760, ...) and setFixedWidth() calls on
Show / Edit / Change-PIN buttons in SecretFieldWidget, which clipped the Admin
warning banner and Edit button labels at default/system font sizes.

Fix:
- Replace all setFixedWidth() calls with setMinimumWidth() so buttons can grow
  to fit their content.
- SettingsDialog: use setMinimumWidth(820) + adjustSize() instead of the old
  resize(760, ...).
- AdminPinDialog: use setMinimumWidth + adjustSize(), NOT setMinimumSize with
  the same value for both dimensions.
- Both dialog minimum widths meet the acceptance criteria (>=820 for
  SettingsDialog, >=440 for AdminPinDialog).
"""

from __future__ import annotations

import ast
import pathlib
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-87"),
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


class TestNoSetFixedWidth:
    """
    settings_dialog.py must contain zero calls to setFixedWidth().
    BTCAAAAA-87 replaced all setFixedWidth() calls with setMinimumWidth().
    """

    def test_no_setfixedwidth_in_settings_dialog_source(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)

        violations = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setFixedWidth"
            ):
                violations.append(node.lineno)

        assert not violations, (
            f"settings_dialog.py still calls setFixedWidth() at lines "
            f"{violations}. BTCAAAAA-87 requires setMinimumWidth() instead."
        )

    def test_secret_field_show_button_uses_minimum_width(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)

        violations = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setFixedWidth"
            ):
                violations.append(node.lineno)

        assert not violations, (
            f"settings_dialog.py still calls setFixedWidth() at lines "
            f"{violations}. BTCAAAAA-87 requires setMinimumWidth() instead."
        )


class TestSettingsDialogMinimumDimensions:
    """SettingsDialog must have minimum dimensions >= 820x600."""

    def test_settings_dialog_minimum_width_at_least_820(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SettingsDialog
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = _make_service_mock()
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=svc,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dialog = SettingsDialog()
            min_w = dialog.minimumWidth()
            dialog.close()

        assert min_w >= 820, (
            f"SettingsDialog minimumWidth() is {min_w}px -- "
            "must be >= 820px to prevent content clipping (BTCAAAAA-87)."
        )

    def test_settings_dialog_minimum_height_at_least_600(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SettingsDialog
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = _make_service_mock()
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=svc,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dialog = SettingsDialog()
            min_h = dialog.minimumHeight()
            dialog.close()

        assert min_h >= 600, (
            f"SettingsDialog minimumHeight() is {min_h}px -- must be >= 600px."
        )


class TestAdminPinDialogMinimumDimensions:
    """AdminPinDialog must have minimum width >= 440px."""

    def test_auth_mode_minimum_width_at_least_440(self, qapp):
        from src.strategy_builder.ui.settings_dialog import AdminPinDialog

        svc = _make_service_mock()
        svc.has_admin_pin.return_value = True
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=svc,
        ):
            dialog = AdminPinDialog(setup_mode=False)
            min_w = dialog.minimumWidth()
            dialog.close()

        assert min_w >= 440, (
            f"AdminPinDialog (auth mode) minimumWidth() is {min_w}px -- "
            "must be >= 440px to prevent content clipping (BTCAAAAA-91)."
        )

    def test_setup_mode_minimum_width_at_least_440(self, qapp):
        from src.strategy_builder.ui.settings_dialog import AdminPinDialog

        svc = _make_service_mock()
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=svc,
        ):
            dialog = AdminPinDialog(setup_mode=True)
            min_w = dialog.minimumWidth()
            dialog.close()

        assert min_w >= 440, (
            f"AdminPinDialog (setup mode) minimumWidth() is {min_w}px -- "
            "must be >= 440px to prevent content clipping (BTCAAAAA-91)."
        )


class TestAdminPinDialogTitles:
    """AdminPinDialog must show correct titles (not truncated)."""

    def test_auth_mode_title(self, qapp):
        from src.strategy_builder.ui.settings_dialog import AdminPinDialog

        svc = _make_service_mock()
        svc.has_admin_pin.return_value = True
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=svc,
        ):
            dialog = AdminPinDialog(setup_mode=False)
            title = dialog.windowTitle()
            dialog.close()

        assert title == "Admin Authentication", (
            f"AdminPinDialog (auth mode) windowTitle() is '{title}' -- "
            "expected 'Admin Authentication' (BTCAAAAA-87)."
        )

    def test_setup_mode_title(self, qapp):
        from src.strategy_builder.ui.settings_dialog import AdminPinDialog

        svc = _make_service_mock()
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=svc,
        ):
            dialog = AdminPinDialog(setup_mode=True)
            title = dialog.windowTitle()
            dialog.close()

        assert title == "Set Admin PIN", (
            f"AdminPinDialog (setup mode) windowTitle() is '{title}' -- "
            "expected 'Set Admin PIN' (BTCAAAAA-87)."
        )
