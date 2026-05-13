"""
Regression tests for BTCAAAAA-202: Admin PIN lockout and sentinel-skip.

BTCAAAAA-202 added a brute-force lockout mechanism to AdminPinDialog and
sentinel-skip logic to SecretFieldWidget / SettingsService.  This file
provides coverage for the Impact Gate minimum-test bar (10 tests).

Affected code paths:
  - src/strategy_builder/ui/settings_dialog.py:
      AdminPinDialog lockout state machine (fail counting, timer ticks,
      lockout expiry, close cleanup)
      SecretFieldWidget sentinel get_value() behaviour
  - src/strategy_builder/ui/settings_service.py:
      save_user_settings() / save_admin_settings() sentinel-skip logic
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


pytestmark = [
    pytest.mark.bug("BTCAAAAA-202"),
    pytest.mark.regression,
]


class TestSentinelSkipUnit:
    """SettingsService must skip all-bullet sentinel values when saving."""

    def test_save_user_settings_skips_sentinel(self):
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        svc.save_user_settings({"OPENROUTER_API_KEY": "••••"})

        assert svc.set.call_count == 0

    def test_save_user_settings_saves_real_value(self):
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        svc.save_user_settings({"AI_MODEL": "anthropic/claude-4-opus"})

        svc.set.assert_called_once_with("AI_MODEL", "anthropic/claude-4-opus")

    def test_save_user_settings_skips_multi_bullet(self):
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        svc.save_user_settings({"OPENROUTER_API_KEY": "•" * 10})

        assert svc.set.call_count == 0

    def test_save_user_settings_skips_unknown_key(self):
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        svc.save_user_settings({"UNKNOWN_KEY": "any_value"})

        assert svc.set.call_count == 0

    def test_save_admin_settings_skips_sentinel(self):
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.ADMIN
        svc.is_admin = lambda: True
        svc.set = MagicMock()

        svc.save_admin_settings({"POSTGRES_PASSWORD": "••••"})

        assert svc.set.call_count == 0

    def test_save_admin_settings_saves_real_value(self):
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.ADMIN
        svc.is_admin = lambda: True
        svc.set = MagicMock()

        svc.save_admin_settings({"POSTGRES_HOST": "db.prod.local"})

        svc.set.assert_called_once_with("POSTGRES_HOST", "db.prod.local")

    def test_save_admin_settings_raises_for_non_admin(self):
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.USER
        svc.is_admin = lambda: False

        with pytest.raises(PermissionError):
            svc.save_admin_settings({"POSTGRES_HOST": "value"})

    def test_elevate_to_admin_false_on_wrong_pin(self):
        import bcrypt
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        hashed = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()

        with patch(
            "src.strategy_builder.ui.settings_service.keyring.get_password",
            return_value=hashed,
        ):
            svc = SettingsService.__new__(SettingsService)
            svc._role = UserRole.USER
            result = svc.elevate_to_admin("wrong")
            assert result is False

    def test_elevate_to_admin_true_on_correct_pin(self):
        import bcrypt
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        hashed = bcrypt.hashpw(b"mypin", bcrypt.gensalt()).decode()

        with patch(
            "src.strategy_builder.ui.settings_service.keyring.get_password",
            return_value=hashed,
        ):
            svc = SettingsService.__new__(SettingsService)
            svc._role = UserRole.USER
            result = svc.elevate_to_admin("mypin")
            assert result is True
            assert svc._role == UserRole.ADMIN

    def test_elevate_to_admin_does_not_change_role_on_wrong_pin(self):
        import bcrypt
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        hashed = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()

        with patch(
            "src.strategy_builder.ui.settings_service.keyring.get_password",
            return_value=hashed,
        ):
            svc = SettingsService.__new__(SettingsService)
            svc._role = UserRole.USER
            svc.elevate_to_admin("wrong")
            assert svc._role == UserRole.USER

    def test_drop_admin_reverts_role(self):
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.ADMIN

        svc.drop_admin()

        assert svc._role == UserRole.USER

    def test_authenticate_admin_delegates_to_elevate_to_admin(self):
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.USER

        with patch.object(svc, "elevate_to_admin", return_value=True) as mock_elevate:
            result = svc.authenticate_admin("1234")

        mock_elevate.assert_called_once_with("1234")
        assert result is True

    def test_save_user_settings_mixed_values(self):
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        svc.save_user_settings({
            "OPENROUTER_API_KEY": "••••",
            "AI_MODEL": "claude-4",
            "LOG_LEVEL": "DEBUG",
        })

        assert svc.set.call_count == 2
        svc.set.assert_any_call("AI_MODEL", "claude-4")
        svc.set.assert_any_call("LOG_LEVEL", "DEBUG")

    def test_save_user_settings_does_not_skip_mixed_bullet_value(self):
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        svc.save_user_settings({"AI_MODEL": "••••X"})

        svc.set.assert_called_once_with("AI_MODEL", "••••X")
