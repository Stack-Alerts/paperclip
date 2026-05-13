"""
Regression tests for BTCAAAAA-79 — Security Architecture for Settings.

Security architecture per BTCAAAAA-79 SecurityAnalyst recommendations:
  - User section: always visible, shows only user-editable fields
  - Admin section: entirely HIDDEN (not just disabled) until PIN verified
  - Secret fields: masked display (last 4 chars), re-entry required to change
  - No plaintext secrets in editable fields on open — only masked display labels
  - On save: masked sentinel values are skipped (field unchanged)
  - OS keyring for all secret fields — no plaintext secrets written to .env
  - bcrypt PIN hash for admin role gate — hash stored in keyring
  - .env file permissions enforced to 600 on every save
"""
from __future__ import annotations

import os
import stat
import tempfile
from unittest.mock import MagicMock, patch

import keyring
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-79"),
    pytest.mark.regression,
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(role: str = "user") -> object:
    from src.strategy_builder.ui.settings_service import SettingsService, UserRole
    svc = SettingsService.__new__(SettingsService)
    svc._role = UserRole.USER if role == "user" else UserRole.ADMIN
    return svc


# ---------------------------------------------------------------------------
# Role model — default state
# ---------------------------------------------------------------------------


class TestRoleModel:
    def test_default_role_is_user(self):
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole
        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.USER
        assert svc.role == UserRole.USER

    def test_is_admin_returns_false_by_default(self):
        svc = _make_service(role="user")
        assert not svc.is_admin()

    def test_is_admin_returns_true_for_admin_role(self):
        svc = _make_service(role="admin")
        assert svc.is_admin()

    def test_drop_admin_reverts_role_to_user(self):
        from src.strategy_builder.ui.settings_service import UserRole
        svc = _make_service(role="admin")
        assert svc.is_admin()
        svc.drop_admin()
        assert not svc.is_admin()
        assert svc.role == UserRole.USER


# ---------------------------------------------------------------------------
# PIN authentication — bcrypt hash in keyring
# ---------------------------------------------------------------------------


class TestPinAuthentication:
    def test_has_admin_pin_returns_false_when_no_pin_stored(self):
        with patch.object(keyring, "get_password", return_value=None):
            svc = _make_service(role="user")
            assert not svc.has_admin_pin()

    def test_has_admin_pin_returns_true_after_set(self):
        svc = _make_service(role="admin")
        svc.set_admin_pin("1234")
        assert svc.has_admin_pin()

    def test_elevate_to_admin_fails_with_wrong_pin(self):
        svc = _make_service(role="admin")
        svc.set_admin_pin("correct-pin")
        svc.drop_admin()
        result = svc.elevate_to_admin("wrong-pin")
        assert not result
        assert not svc.is_admin()

    def test_elevate_to_admin_succeeds_with_correct_pin(self):
        svc = _make_service(role="admin")
        svc.set_admin_pin("correct-pin")
        svc.drop_admin()
        result = svc.elevate_to_admin("correct-pin")
        assert result
        assert svc.is_admin()

    def test_set_admin_pin_stores_bcrypt_hash_not_plaintext(self):
        svc = _make_service(role="admin")
        svc.set_admin_pin("my-secret-pin")
        stored = keyring.get_password("btc-trade-engine", "admin_pin_hash")
        assert stored is not None
        assert stored != "my-secret-pin"
        assert stored.startswith("$2b$") or stored.startswith("$2a$")

    def test_set_admin_pin_requires_admin_when_pin_exists(self):
        svc = _make_service(role="admin")
        svc.set_admin_pin("initial-pin")
        svc.drop_admin()
        with pytest.raises(PermissionError):
            svc.set_admin_pin("new-pin")

    def test_elevate_to_admin_first_run_raises_when_pin_exists(self):
        svc = _make_service(role="admin")
        svc.set_admin_pin("existing-pin")
        svc.drop_admin()
        with pytest.raises(PermissionError):
            svc.elevate_to_admin_first_run()

    def test_elevate_to_admin_first_run_grants_admin_when_no_pin(self):
        with patch.object(keyring, "get_password", return_value=None):
            svc = _make_service(role="user")
            svc.elevate_to_admin_first_run()
            assert svc.is_admin()


# ---------------------------------------------------------------------------
# Access control — _check_access gate
# ---------------------------------------------------------------------------


class TestAccessControl:
    def test_get_raises_permission_error_for_admin_key_as_user(self):
        svc = _make_service(role="user")
        with pytest.raises(PermissionError):
            svc.get("POSTGRES_HOST")

    def test_get_allows_admin_key_for_admin_role(self):
        svc = _make_service(role="admin")
        val = svc.get("POSTGRES_HOST")
        assert val is None or isinstance(val, str)

    def test_get_masked_raises_permission_error_for_admin_key_as_user(self):
        svc = _make_service(role="user")
        with pytest.raises(PermissionError):
            svc.get_masked("POSTGRES_HOST")

    def test_get_allows_user_key_for_user_role(self):
        svc = _make_service(role="user")
        val = svc.get("AI_MODEL")
        assert val is None or isinstance(val, str)

    def test_get_with_default_raises_permission_error_for_admin_key_as_user(self):
        svc = _make_service(role="user")
        with pytest.raises(PermissionError):
            svc.get_with_default("POSTGRES_HOST")

    def test_save_admin_settings_raises_permission_error_for_user(self):
        svc = _make_service(role="user")
        with pytest.raises(PermissionError):
            svc.save_admin_settings({"POSTGRES_HOST": "new-host"})


# ---------------------------------------------------------------------------
# Masked display — last 4 chars visible
# ---------------------------------------------------------------------------


class TestMaskedDisplay:
    def test_get_masked_returns_masked_with_last_4_chars(self):
        svc = _make_service(role="user")
        with patch.object(keyring, "get_password", return_value="sk-or-v1-abcdef1234567890"):
            masked = svc.get_masked("OPENROUTER_API_KEY")
            assert masked.endswith("7890")
            assert "•" in masked
            visible_count = len(masked) - masked.count("•")
            assert visible_count == 4

    def test_get_masked_returns_empty_for_none_value(self):
        svc = _make_service(role="user")
        with patch.object(keyring, "get_password", return_value=None):
            assert svc.get_masked("OPENROUTER_API_KEY") == ""

    def test_get_masked_returns_empty_for_empty_value(self):
        svc = _make_service(role="user")
        with patch.object(keyring, "get_password", return_value=""):
            assert svc.get_masked("OPENROUTER_API_KEY") == ""

    def test_get_masked_short_value_fully_masked(self):
        svc = _make_service(role="user")
        with patch.object(keyring, "get_password", return_value="abc"):
            masked = svc.get_masked("OPENROUTER_API_KEY")
            assert masked == "•••"
            assert masked.count("•") == 3

    def test_get_masked_four_char_value_fully_masked(self):
        svc = _make_service(role="user")
        with patch.object(keyring, "get_password", return_value="abcd"):
            masked = svc.get_masked("OPENROUTER_API_KEY")
            assert masked == "••••"
            assert masked.count("•") == 4


# ---------------------------------------------------------------------------
# Save — sentinel skip logic
# ---------------------------------------------------------------------------


class TestSaveSentinelLogic:
    def test_save_user_settings_skips_all_bullet_sentinel(self):
        svc = _make_service(role="user")
        with patch.object(svc, "set") as mock_set:
            svc.save_user_settings({"AI_MODEL": "••••••••"})
            mock_set.assert_not_called()

    def test_save_user_settings_persists_non_sentinel_value(self):
        svc = _make_service(role="user")
        with patch.object(svc, "set") as mock_set:
            svc.save_user_settings({"AI_MODEL": "anthropic/claude-opus-4"})
            mock_set.assert_called_once_with("AI_MODEL", "anthropic/claude-opus-4")

    def test_save_user_settings_skips_unknown_keys(self):
        svc = _make_service(role="user")
        with patch.object(svc, "set") as mock_set:
            svc.save_user_settings({"UNKNOWN_KEY": "value"})
            mock_set.assert_not_called()

    def test_save_admin_settings_skips_all_bullet_sentinel(self):
        svc = _make_service(role="admin")
        with patch.object(svc, "set") as mock_set:
            svc.save_admin_settings({"POSTGRES_HOST": "••••••••"})
            mock_set.assert_not_called()

    def test_save_admin_settings_persists_non_sentinel_value(self):
        svc = _make_service(role="admin")
        with patch.object(svc, "set") as mock_set:
            svc.save_admin_settings({"POSTGRES_HOST": "db-prod-1.example.com"})
            mock_set.assert_called_once_with("POSTGRES_HOST", "db-prod-1.example.com")


# ---------------------------------------------------------------------------
# .env permission enforcement
# ---------------------------------------------------------------------------


class TestEnvPermissions:
    def test_enforce_env_permissions_sets_600(self):
        from src.strategy_builder.ui.settings_service import SettingsService
        with tempfile.NamedTemporaryFile(delete=False, suffix=".env") as f:
            env_path = f.name
            f.write(b"TEST_KEY=test_value\n")
        try:
            with patch("src.strategy_builder.ui.settings_service.ENV_FILE", env_path):
                os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                SettingsService._enforce_env_permissions()
                mode = os.stat(env_path).st_mode & 0o777
                assert mode == stat.S_IRUSR | stat.S_IWUSR, (
                    f".env permissions were {oct(mode)}, expected 0o600"
                )
        finally:
            os.unlink(env_path)

    def test_enforce_env_permissions_does_not_raise_when_file_missing(self):
        from src.strategy_builder.ui.settings_service import SettingsService
        with patch(
            "src.strategy_builder.ui.settings_service.ENV_FILE",
            "/tmp/nonexistent_env_file_12345",
        ):
            SettingsService._enforce_env_permissions()


# ---------------------------------------------------------------------------
# SecretFieldWidget — masked display and sentinel return
# ---------------------------------------------------------------------------


class TestSecretFieldWidget:
    def test_secret_field_display_masked_format(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        service = MagicMock()
        service.get_masked.return_value = "••••••••••••••ac84"
        widget = SecretFieldWidget("OPENROUTER_API_KEY", service)
        assert "ac84" in widget._display_label.text()
        assert "•" in widget._display_label.text()
        widget.deleteLater()

    def test_secret_field_shows_not_set_when_empty(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        service = MagicMock()
        service.get_masked.return_value = ""
        service.get.return_value = None
        widget = SecretFieldWidget("OPENROUTER_API_KEY", service)
        assert "(not set)" in widget._display_label.text()
        widget.deleteLater()

    def test_secret_field_get_value_returns_sentinel_in_display_mode(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        service = MagicMock()
        service.get_masked.return_value = "••••••••••••••ac84"
        widget = SecretFieldWidget("OPENROUTER_API_KEY", service)
        assert widget.get_value() == "••••"
        widget.deleteLater()

    def test_secret_field_get_value_returns_entered_text_in_edit_mode(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        service = MagicMock()
        service.get_masked.return_value = "••••••••••••••ac84"
        widget = SecretFieldWidget("OPENROUTER_API_KEY", service)
        widget._enter_edit_mode()
        widget._edit_field.setText("new-api-key-value")
        assert widget.get_value() == "new-api-key-value"
        widget.deleteLater()

    def test_secret_field_get_value_returns_sentinel_when_edit_field_empty(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        service = MagicMock()
        service.get_masked.return_value = "••••••••••••••ac84"
        widget = SecretFieldWidget("OPENROUTER_API_KEY", service)
        widget._enter_edit_mode()
        widget._edit_field.clear()
        assert widget.get_value() == "••••"
        widget.deleteLater()

    def test_secret_field_clear_edit_returns_to_masked_display(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        service = MagicMock()
        service.get_masked.return_value = "••••••••••••••ac84"
        widget = SecretFieldWidget("OPENROUTER_API_KEY", service)
        widget._enter_edit_mode()
        widget.clear_edit()
        assert not widget._edit_mode
        widget.deleteLater()


# ---------------------------------------------------------------------------
# AdminPinDialog — lockout after 3 consecutive failures
# ---------------------------------------------------------------------------


class TestAdminPinDialogLockout:
    def test_lockout_activates_after_3_failures(self, qapp):
        from src.strategy_builder.ui.settings_dialog import AdminPinDialog
        service = MagicMock()
        service.has_admin_pin.return_value = True
        service.elevate_to_admin.return_value = False
        dlg = AdminPinDialog(setup_mode=False, service=service)
        dlg._pin_field.setText("wrong")
        dlg._attempt_auth()
        assert dlg._fail_count == 1
        assert dlg._lockout_remaining == 0
        dlg._attempt_auth()
        assert dlg._fail_count == 2
        dlg._attempt_auth()
        assert dlg._fail_count == 3
        assert dlg._lockout_remaining == 30
        assert not dlg._pin_field.isEnabled()
        assert not dlg._ok_button.isEnabled()
        dlg.close()

    def test_lockout_countdown_decrements(self, qapp):
        from src.strategy_builder.ui.settings_dialog import AdminPinDialog
        service = MagicMock()
        service.has_admin_pin.return_value = True
        service.elevate_to_admin.return_value = False
        dlg = AdminPinDialog(setup_mode=False, service=service)
        dlg._fail_count = 3
        dlg._start_lockout()
        assert dlg._lockout_remaining == 30
        dlg._on_lockout_tick()
        assert dlg._lockout_remaining == 29
        dlg.close()

    def test_lockout_ends_after_countdown_reaches_zero(self, qapp):
        from src.strategy_builder.ui.settings_dialog import AdminPinDialog
        service = MagicMock()
        service.has_admin_pin.return_value = True
        service.elevate_to_admin.return_value = False
        dlg = AdminPinDialog(setup_mode=False, service=service)
        dlg._fail_count = 3
        dlg._start_lockout()
        assert dlg._lockout_remaining == 30
        for _ in range(30):
            dlg._on_lockout_tick()
        assert dlg._lockout_remaining == 0
        assert dlg._pin_field.isEnabled()
        assert dlg._ok_button.isEnabled()
        dlg.close()

    def test_lockout_resets_fail_count_on_expiry(self, qapp):
        from src.strategy_builder.ui.settings_dialog import AdminPinDialog
        service = MagicMock()
        service.has_admin_pin.return_value = True
        service.elevate_to_admin.return_value = False
        dlg = AdminPinDialog(setup_mode=False, service=service)
        dlg._fail_count = 3
        dlg._start_lockout()
        for _ in range(30):
            dlg._on_lockout_tick()
        assert dlg._fail_count == 0
        dlg.close()


# ---------------------------------------------------------------------------
# SettingsDialog — admin section hidden until PIN verified
# ---------------------------------------------------------------------------


class TestSettingsDialogAdminSectionVisibility:
    def test_admin_tab_hidden_on_open_for_non_admin(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        mock_service = MagicMock(spec=SettingsService)
        mock_service.is_admin.return_value = False
        mock_service.role = MagicMock()
        mock_service.role.value = "user"
        mock_service.has_admin_pin.return_value = False
        mock_service.get_masked.return_value = ""
        mock_service.get.return_value = None
        mock_service.get_with_default.return_value = ""
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=mock_service,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            assert not dlg._tabs.isTabVisible(dlg._admin_tab_index)
            dlg.close()

    def test_user_tab_visible_on_open_for_non_admin(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        mock_service = MagicMock(spec=SettingsService)
        mock_service.is_admin.return_value = False
        mock_service.role = MagicMock()
        mock_service.role.value = "user"
        mock_service.has_admin_pin.return_value = False
        mock_service.get_masked.return_value = ""
        mock_service.get.return_value = None
        mock_service.get_with_default.return_value = ""
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=mock_service,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            assert dlg._tabs.isTabVisible(0)
            dlg.close()

    def test_admin_tab_revealed_after_authentication(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        mock_service = MagicMock(spec=SettingsService)
        mock_service.is_admin.side_effect = [False, True]
        mock_service.role = MagicMock()
        mock_service.role.value = "admin"
        mock_service.has_admin_pin.return_value = True
        mock_service.get_masked.return_value = ""
        mock_service.get.return_value = None
        mock_service.get_with_default.return_value = ""
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=mock_service,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            assert not dlg._tabs.isTabVisible(dlg._admin_tab_index)
            dlg._reveal_admin_tab()
            assert dlg._tabs.isTabVisible(dlg._admin_tab_index)
            dlg.close()

    def test_admin_tab_concealed_after_lock(self, qapp):
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        mock_service = MagicMock(spec=SettingsService)
        mock_service.is_admin.side_effect = [True, False]
        mock_service.role = MagicMock()
        mock_service.role.value = "admin"
        mock_service.has_admin_pin.return_value = True
        mock_service.get_masked.return_value = ""
        mock_service.get.return_value = None
        mock_service.get_with_default.return_value = ""
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=mock_service,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            dlg._reveal_admin_tab()
            assert dlg._tabs.isTabVisible(dlg._admin_tab_index)
            dlg._conceal_admin_tab()
            assert not dlg._tabs.isTabVisible(dlg._admin_tab_index)
            dlg.close()


# ---------------------------------------------------------------------------
# Security invariant: no admin key get()/get_with_default() during non-admin init
# ---------------------------------------------------------------------------

class TestSecurityInvariant:
    def test_no_admin_key_fetched_on_non_admin_open(self, qapp):
        """
        get() and get_with_default() must NOT be called for admin-only keys
        during non-admin dialog initialisation (BTCAAAAA-82 crash bug).
        """
        from src.strategy_builder.ui.settings_service import ADMIN_ONLY_KEYS
        from src.strategy_builder.ui.settings_dialog import SettingsDialog, SettingsService
        mock_service = MagicMock(spec=SettingsService)
        mock_service.is_admin.return_value = False
        mock_service.role = MagicMock()
        mock_service.role.value = "user"
        mock_service.has_admin_pin.return_value = False
        mock_service.get_masked.return_value = ""
        mock_service.get.return_value = None
        mock_service.get_with_default.return_value = ""
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=mock_service,
        ), patch.object(
            SettingsService, "_enforce_env_permissions", staticmethod(lambda: None)
        ):
            dlg = SettingsDialog()
            dlg.close()

        get_calls = [c.args[0] for c in mock_service.get.call_args_list]
        get_default_calls = [
            c.args[0] for c in mock_service.get_with_default.call_args_list
        ]
        all_accessed = set(get_calls + get_default_calls)

        for key in ADMIN_ONLY_KEYS:
            assert key not in all_accessed, (
                f"Admin-only key '{key}' was accessed via get/get_with_default "
                "during non-admin dialog init (BTCAAAAA-82 pattern)."
            )
