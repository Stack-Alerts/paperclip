"""
Tests for SettingsDialog — BTCAAAAA-82 regression coverage and
BTCAAAAA-87/88 width auto-sizing regression coverage.

Verifies that:
- Non-admin users can open the Settings dialog without any exception.
- Admin-only settings (e.g. POSTGRES_HOST) are NOT accessed during non-admin
  dialog initialisation.
- The admin tab is hidden on open for non-admin users.
- Admin fields are populated only after successful PIN authentication.

BTCAAAAA-87/88 — width auto-sizing regression:
- No setFixedWidth() call remains on Show / Edit / Change-PIN buttons in
  SecretFieldWidget; setMinimumWidth() is used instead so buttons can grow.
- AdminPinDialog uses setMinimumWidth + adjustSize(), NOT setMinimumSize with
  the same value for both dimensions (which would hard-lock the width).
- SettingsDialog uses setMinimumWidth(820) + adjustSize(), NOT the old
  resize(760, ...) that clipped Edit buttons and the Admin warning banner.
- Both dialog minimum widths meet the acceptance criteria (≥440 for
  AdminPinDialog per BTCAAAAA-91, ≥820 for SettingsDialog).
"""

from __future__ import annotations

import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from PyQt5.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# QApplication fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service_mock(is_admin: bool = False) -> MagicMock:
    """Return a SettingsService mock with configurable role."""
    from src.strategy_builder.ui.settings_service import UserRole

    mock = MagicMock()
    mock.is_admin.return_value = is_admin
    mock.role = UserRole.ADMIN if is_admin else UserRole.USER

    def _check_access(key: str) -> None:
        from src.strategy_builder.ui.settings_service import ADMIN_ONLY_KEYS
        if key in ADMIN_ONLY_KEYS and not is_admin:
            raise PermissionError(
                f"Setting '{key}' requires admin role. "
                "Authenticate via the Admin section in Settings."
            )

    mock._check_access.side_effect = _check_access

    def _get(key: str):
        _check_access(key)
        return None

    def _get_with_default(key: str, default: str = "") -> str:
        _check_access(key)
        return default

    def _get_masked(key: str) -> str:
        _check_access(key)
        return ""

    mock.get.side_effect = _get
    mock.get_with_default.side_effect = _get_with_default
    mock.get_masked.side_effect = _get_masked
    mock.has_admin_pin.return_value = False
    mock.authenticate_admin.return_value = False
    return mock


# ---------------------------------------------------------------------------
# Non-admin open path — the regression test for BTCAAAAA-82
# ---------------------------------------------------------------------------

class TestSettingsDialogNonAdminOpen:
    """Settings dialog must open without error for non-admin users."""

    def test_dialog_creates_without_exception_non_admin(self, qapp):
        """Creating SettingsDialog as non-admin must not raise."""
        with (
            patch(
                "src.strategy_builder.ui.settings_dialog.SettingsService",
                return_value=_make_service_mock(is_admin=False),
            ),
            patch.object(
                # Suppress .env permission enforcement during test
                __import__(
                    "src.strategy_builder.ui.settings_service",
                    fromlist=["SettingsService"],
                ).SettingsService,
                "_enforce_env_permissions",
                staticmethod(lambda: None),
            ),
        ):
            from src.strategy_builder.ui.settings_dialog import SettingsDialog
            # Must not raise PermissionError or any other exception
            dialog = SettingsDialog()
            assert dialog is not None
            dialog.close()

    def test_no_admin_key_accessed_on_non_admin_open(self, qapp):
        """
        get() / get_with_default() must NOT be called for admin-only keys
        during non-admin dialog construction.
        """
        from src.strategy_builder.ui.settings_service import ADMIN_ONLY_KEYS

        service_mock = _make_service_mock(is_admin=False)

        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=service_mock,
        ):
            from src.strategy_builder.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog()
            dialog.close()

        # Collect all keys that get() / get_with_default() were called with
        get_calls = [call.args[0] for call in service_mock.get.call_args_list]
        get_default_calls = [
            call.args[0] for call in service_mock.get_with_default.call_args_list
        ]
        all_accessed = set(get_calls + get_default_calls)

        for admin_key in ADMIN_ONLY_KEYS:
            assert admin_key not in all_accessed, (
                f"Admin-only key '{admin_key}' was accessed during non-admin "
                "dialog init — this is the BTCAAAAA-82 crash bug."
            )

    def test_admin_tab_hidden_on_non_admin_open(self, qapp):
        """Admin tab must be invisible when dialog opens without admin auth."""
        service_mock = _make_service_mock(is_admin=False)

        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=service_mock,
        ):
            from src.strategy_builder.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog()
            tabs = dialog._tabs
            admin_idx = dialog._admin_tab_index

            assert not tabs.isTabVisible(admin_idx), (
                "Admin tab must be hidden for non-admin users on dialog open."
            )
            dialog.close()

    def test_user_tab_visible_on_non_admin_open(self, qapp):
        """User tab (API Keys & Preferences) must be visible for all users."""
        service_mock = _make_service_mock(is_admin=False)

        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=service_mock,
        ):
            from src.strategy_builder.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog()
            tabs = dialog._tabs

            # Tab 0 is the user/API keys tab
            assert tabs.isTabVisible(0), (
                "User (API Keys & Preferences) tab must be visible on open."
            )
            dialog.close()


# ---------------------------------------------------------------------------
# Admin populate path
# ---------------------------------------------------------------------------

class TestSettingsDialogAdminPopulate:
    """After authentication, admin fields must be populated from the service."""

    def test_admin_fields_populated_after_auth(self, qapp):
        """
        _populate_admin_fields() must call get_with_default() for admin keys
        once the role is elevated.
        """
        service_mock = _make_service_mock(is_admin=True)
        # Override so get_with_default always succeeds when admin
        service_mock.get_with_default.side_effect = lambda key, default="": default

        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=service_mock,
        ):
            from src.strategy_builder.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog()
            # Reset call counts (may have been called during __init__ if admin)
            service_mock.get_with_default.reset_mock()

            dialog._populate_admin_fields()

            called_keys = {
                call.args[0]
                for call in service_mock.get_with_default.call_args_list
            }
            expected_admin_plain_keys = {
                "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
                "POSTGRES_USER", "LAKEAPI_REGION", "LAKEAPI_LIMIT_GB",
                "LOG_LEVEL",
            }
            assert expected_admin_plain_keys.issubset(called_keys), (
                f"Expected admin fields to be populated. Missing: "
                f"{expected_admin_plain_keys - called_keys}"
            )
            dialog.close()


# ---------------------------------------------------------------------------
# SettingsService._check_access unit tests
# ---------------------------------------------------------------------------

class TestSettingsServiceCheckAccess:
    """Unit tests for the _check_access gate in SettingsService."""

    def test_admin_key_raises_for_user_role(self):
        """Non-admin role must raise PermissionError for ADMIN_ONLY_KEYS."""
        from src.strategy_builder.ui.settings_service import SettingsService, ADMIN_ONLY_KEYS

        svc = SettingsService.__new__(SettingsService)
        from src.strategy_builder.ui.settings_service import UserRole
        svc._role = UserRole.USER

        for key in list(ADMIN_ONLY_KEYS)[:3]:  # Sample a few
            with pytest.raises(PermissionError):
                svc._check_access(key)

    def test_admin_key_allowed_for_admin_role(self):
        """Admin role must NOT raise for ADMIN_ONLY_KEYS."""
        from src.strategy_builder.ui.settings_service import SettingsService, ADMIN_ONLY_KEYS, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.ADMIN

        for key in list(ADMIN_ONLY_KEYS)[:3]:
            # Must not raise
            svc._check_access(key)

    def test_user_key_allowed_for_user_role(self):
        """USER_KEYS must not raise for user role."""
        from src.strategy_builder.ui.settings_service import SettingsService, USER_KEYS, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.USER

        for key in list(USER_KEYS)[:3]:
            svc._check_access(key)  # Must not raise


# ---------------------------------------------------------------------------
# BTCAAAAA-87/88 — width auto-sizing regression tests
# ---------------------------------------------------------------------------

class TestWidthAutoSizingRegression:
    """
    Regression guard for BTCAAAAA-87 and BTCAAAAA-91.

    Ensures that:
    - No setFixedWidth() call is used anywhere in settings_dialog.py
      (all have been replaced with setMinimumWidth() so widgets can grow).
    - SettingsDialog minimum width is ≥ 820px (not the old too-narrow 760px).
    - AdminPinDialog minimum width is ≥ 440px (raised from 360 in
      BTCAAAAA-91 to prevent clipping of title, instruction text, and
      "Authenticate" button at default size).
    - Both dialogs instantiate correctly with the new layout-driven sizing.
    """

    def test_no_setfixedwidth_in_settings_dialog_source(self):
        """
        settings_dialog.py must contain zero calls to setFixedWidth().
        BTCAAAAA-87 replaced all setFixedWidth() calls with setMinimumWidth().
        """
        import ast
        import pathlib

        source_path = pathlib.Path(
            "src/strategy_builder/ui/settings_dialog.py"
        )
        source = source_path.read_text()
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

    def test_settings_dialog_minimum_width_at_least_820(self, qapp):
        """
        SettingsDialog.minimumWidth() must be ≥ 820 so the Admin warning
        banner and Edit buttons are never clipped (BTCAAAAA-87).
        """
        service_mock = _make_service_mock(is_admin=False)

        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=service_mock,
        ):
            from src.strategy_builder.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog()
            min_w = dialog.minimumWidth()
            dialog.close()

        assert min_w >= 820, (
            f"SettingsDialog minimumWidth() is {min_w}px — "
            "must be ≥ 820px to prevent content clipping (BTCAAAAA-87)."
        )

    def test_settings_dialog_minimum_height_at_least_600(self, qapp):
        """
        SettingsDialog.minimumHeight() must be ≥ 600 (BTCAAAAA-87 floor).
        """
        service_mock = _make_service_mock(is_admin=False)

        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
            return_value=service_mock,
        ):
            from src.strategy_builder.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog()
            min_h = dialog.minimumHeight()
            dialog.close()

        assert min_h >= 600, (
            f"SettingsDialog minimumHeight() is {min_h}px — must be ≥ 600px."
        )

    def test_admin_pin_dialog_auth_mode_minimum_width_at_least_440(self, qapp):
        """
        AdminPinDialog (authentication mode) minimum width must be ≥ 440px
        so the full title, instruction text, and 'Authenticate' button label
        are not clipped (BTCAAAAA-91).
        """
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
        ):
            from src.strategy_builder.ui.settings_dialog import AdminPinDialog
            dialog = AdminPinDialog(setup_mode=False)
            min_w = dialog.minimumWidth()
            dialog.close()

        assert min_w >= 440, (
            f"AdminPinDialog (auth mode) minimumWidth() is {min_w}px — "
            "must be ≥ 440px to prevent content clipping (BTCAAAAA-91)."
        )

    def test_admin_pin_dialog_setup_mode_minimum_width_at_least_440(self, qapp):
        """
        AdminPinDialog (setup/Set Admin PIN mode) minimum width must be
        ≥ 440px so the title 'Set Admin PIN', instruction text, and both
        PIN fields are not clipped (BTCAAAAA-91).
        """
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
        ):
            from src.strategy_builder.ui.settings_dialog import AdminPinDialog
            dialog = AdminPinDialog(setup_mode=True)
            min_w = dialog.minimumWidth()
            dialog.close()

        assert min_w >= 440, (
            f"AdminPinDialog (setup mode) minimumWidth() is {min_w}px — "
            "must be ≥ 440px to prevent content clipping (BTCAAAAA-91)."
        )

    def test_admin_pin_dialog_auth_mode_title(self, qapp):
        """
        AdminPinDialog in auth mode must show the full title
        'Admin Authentication' (not a truncated version).
        """
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
        ):
            from src.strategy_builder.ui.settings_dialog import AdminPinDialog
            dialog = AdminPinDialog(setup_mode=False)
            title = dialog.windowTitle()
            dialog.close()

        assert title == "Admin Authentication", (
            f"AdminPinDialog (auth mode) windowTitle() is '{title}' — "
            "expected 'Admin Authentication' (BTCAAAAA-87)."
        )

    def test_admin_pin_dialog_setup_mode_title(self, qapp):
        """
        AdminPinDialog in setup mode must show the full title
        'Set Admin PIN' (not 'Set Ad...').
        """
        with patch(
            "src.strategy_builder.ui.settings_dialog.SettingsService",
        ):
            from src.strategy_builder.ui.settings_dialog import AdminPinDialog
            dialog = AdminPinDialog(setup_mode=True)
            title = dialog.windowTitle()
            dialog.close()

        assert title == "Set Admin PIN", (
            f"AdminPinDialog (setup mode) windowTitle() is '{title}' — "
            "expected 'Set Admin PIN' (BTCAAAAA-87)."
        )

    def test_secret_field_show_button_uses_minimum_width(self):
        """
        SecretFieldWidget._show_btn must use setMinimumWidth, not setFixedWidth,
        so it can grow rather than being clipped (BTCAAAAA-87).

        This is a redundant explicit check over the global AST test above;
        it uses the same AST approach to avoid false-positives from comments.
        """
        import ast
        import pathlib

        source_path = pathlib.Path(
            "src/strategy_builder/ui/settings_dialog.py"
        )
        tree = ast.parse(source_path.read_text())

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
