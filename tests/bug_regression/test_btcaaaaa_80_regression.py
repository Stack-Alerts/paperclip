"""
Regression tests for BTCAAAAA-80: Settings page under Tools menu.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-80
Components: src/strategy_builder/ui/settings_dialog.py
            src/strategy_builder/ui/settings_service.py

Tests the integration between SettingsDialog and SettingsService:
  - Dialog construction and tab layout
  - Admin auth flow (reveal/conceal admin tab)
  - Save flow integration
  - Window geometry management
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-80"),
    pytest.mark.regression,
]

_IMPORT_SRC = "src.strategy_builder.ui.settings_dialog"


def _make_mock_service(admin: bool = False, has_pin: bool = False):
    svc = MagicMock()
    svc.is_admin.return_value = admin
    svc.role = PropertyMock(return_value=MagicMock(value="admin" if admin else "user"))
    svc.has_admin_pin.return_value = has_pin
    svc.get_masked.return_value = ""
    svc.get.return_value = None
    svc.get_with_default.return_value = ""
    return svc


def _make_patched_dialog(admin: bool = False, has_pin: bool = False):
    from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
    svc = _make_mock_service(admin=admin, has_pin=has_pin)
    with patch(f"{_IMPORT_SRC}.SettingsService", return_value=svc), patch.object(
        SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
    ):
        dlg = SettingsDialog()
        dlg.show()
        return dlg


# ---------------------------------------------------------------------------
# SettingsDialog — basic construction
# ---------------------------------------------------------------------------


class TestSettingsDialogConstruction:
    def test_dialog_has_three_tabs(self, qapp_session):
        dlg = _make_patched_dialog()
        assert dlg._tabs.count() == 3
        assert dlg._tabs.tabText(0) == "API Keys"
        assert dlg._tabs.tabText(1) == "Preferences"
        assert dlg._tabs.tabText(2) == "Admin"
        dlg.close()

    def test_admin_tab_hidden_on_open(self, qapp_session):
        dlg = _make_patched_dialog()
        assert dlg._admin_tab_index == 2
        assert not dlg._tabs.isTabVisible(dlg._admin_tab_index)
        dlg.close()

    def test_dialog_has_secret_widgets(self, qapp_session):
        dlg = _make_patched_dialog()
        assert "OPENROUTER_API_KEY" in dlg._secret_widgets
        assert "LAKEAPI_KEY" in dlg._secret_widgets
        dlg.close()

    def test_dialog_has_plain_fields(self, qapp_session):
        dlg = _make_patched_dialog()
        assert "AI_MODEL" in dlg._plain_fields
        assert "MULTICORE_WORKERS" in dlg._plain_fields
        dlg.close()

    def test_dialog_window_title(self, qapp_session):
        dlg = _make_patched_dialog()
        assert dlg.windowTitle() == "Settings"
        dlg.close()

    def test_dialog_modal(self, qapp_session):
        dlg = _make_patched_dialog()
        assert dlg.isModal()
        dlg.close()


# ---------------------------------------------------------------------------
# Admin auth integration — reveal/conceal admin tab
# ---------------------------------------------------------------------------


class TestAdminAuthIntegration:
    def test_reveal_admin_tab_sets_visible(self, qapp_session):
        dlg = _make_patched_dialog()
        assert not dlg._tabs.isTabVisible(dlg._admin_tab_index)
        dlg._reveal_admin_tab()
        assert dlg._tabs.isTabVisible(dlg._admin_tab_index)
        dlg.close()

    def test_reveal_admin_tab_shows_lock_button(self, qapp_session):
        dlg = _make_patched_dialog(admin=True, has_pin=True)
        dlg._reveal_admin_tab()
        assert dlg._admin_auth_btn.isHidden()
        assert dlg._admin_lock_btn.isVisible()
        dlg.close()

    def test_conceal_admin_tab_hides_tab(self, qapp_session):
        dlg = _make_patched_dialog(admin=True, has_pin=True)
        dlg._reveal_admin_tab()
        assert dlg._tabs.isTabVisible(dlg._admin_tab_index)
        dlg._conceal_admin_tab()
        assert not dlg._tabs.isTabVisible(dlg._admin_tab_index)
        dlg.close()

    def test_conceal_admin_tab_shows_auth_button(self, qapp_session):
        dlg = _make_patched_dialog(admin=True, has_pin=True)
        dlg._reveal_admin_tab()
        dlg._conceal_admin_tab()
        assert dlg._admin_auth_btn.isVisible()
        assert dlg._admin_lock_btn.isHidden()
        dlg.close()

    def test_on_admin_lock_hides_tab(self, qapp_session):
        dlg = _make_patched_dialog(admin=True, has_pin=True)
        dlg._reveal_admin_tab()
        assert dlg._tabs.isTabVisible(dlg._admin_tab_index)
        dlg._on_admin_lock()
        assert not dlg._tabs.isTabVisible(dlg._admin_tab_index)
        dlg.close()

    def test_on_admin_lock_calls_drop_admin(self, qapp_session):
        svc = _make_mock_service(admin=True, has_pin=True)
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        with patch(f"{_IMPORT_SRC}.SettingsService", return_value=svc), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            dlg.show()
            dlg._reveal_admin_tab()
            dlg._on_admin_lock()
            svc.drop_admin.assert_called_once()
            dlg.close()


# ---------------------------------------------------------------------------
# Save flow integration
# ---------------------------------------------------------------------------


class TestSaveFlow:
    def test_on_save_calls_save_user_settings(self, qapp_session):
        svc = _make_mock_service()
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        with patch(f"{_IMPORT_SRC}.SettingsService", return_value=svc), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            dlg.show()
            dlg._on_save()
            svc.save_user_settings.assert_called_once()
            dlg.close()

    def test_on_save_skips_admin_settings_when_not_admin(self, qapp_session):
        svc = _make_mock_service()
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        with patch(f"{_IMPORT_SRC}.SettingsService", return_value=svc), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            dlg.show()
            dlg._on_save()
            svc.save_admin_settings.assert_not_called()
            dlg.close()

    def test_on_save_calls_save_admin_settings_when_admin(self, qapp_session):
        svc = _make_mock_service(admin=True, has_pin=True)
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        with patch(f"{_IMPORT_SRC}.SettingsService", return_value=svc), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            dlg.show()
            dlg._reveal_admin_tab()
            dlg._on_save()
            svc.save_admin_settings.assert_called_once()
            dlg.close()


# ---------------------------------------------------------------------------
# Window geometry integration
# ---------------------------------------------------------------------------


class TestWindowGeometry:
    def test_dialog_has_geometry_settings_key(self, qapp_session):
        dlg = _make_patched_dialog()
        assert dlg.GEOMETRY_SETTINGS_KEY == "settingsDialog"
        dlg.close()

    def test_dialog_minimum_size_set(self, qapp_session):
        dlg = _make_patched_dialog()
        assert dlg.minimumWidth() >= 860
        assert dlg.minimumHeight() >= 600
        dlg.close()

    def test_dialog_has_geometry_default_size(self, qapp_session):
        dlg = _make_patched_dialog()
        assert dlg.GEOMETRY_DEFAULT_SIZE == (800, 600)
        dlg.close()
