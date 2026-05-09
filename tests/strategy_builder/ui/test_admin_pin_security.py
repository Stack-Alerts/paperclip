"""
Headless tests for admin PIN sentinel-skip behavior and brute-force lockout.

BTCAAAAA-203 — New coverage:

### 1. Sentinel-skip tests (SecretFieldWidget)
- get_value() returns the sentinel ``"••••"`` when NOT in edit mode.
- get_value() returns the sentinel when edit mode is active but the field
  is empty (unchanged).
- get_value() returns the typed text only when edit mode is active AND the
  user entered a non-empty, non-whitespace value.
- save_user_settings() / save_admin_settings() SKIP fields whose value is
  the all-bullet sentinel — the keyring entry must remain unchanged.

### 2. AdminPinDialog lockout tests (headless / no real QTimer ticks)
- After 3 wrong PIN attempts, _fail_count reaches _MAX_FAILURES.
- After 3 wrong attempts, _start_lockout() is called:
  - _lockout_remaining is set to _LOCKOUT_SECONDS (30).
  - PIN field is disabled.
  - OK button is disabled.
  - _lockout_label is visible and contains the countdown text.
- _on_lockout_tick() decrements the counter each call.
- After _LOCKOUT_SECONDS ticks, _end_lockout() is called:
  - _lockout_remaining returns to 0.
  - _fail_count is reset to 0.
  - PIN field and OK button are re-enabled.
  - Lockout label is hidden.
- A correct PIN after lockout expires succeeds (dialog accepts).
- Dialog close/reset clears the failure count and stops the timer.
- _attempt_auth() is a no-op while lockout is active.

### 3. SettingsService.elevate_to_admin() regression
- Returns False (not True) when no PIN is stored.
- Returns False for a wrong PIN.
- Returns True and elevates role on correct PIN.
- authenticate_admin() still works as a thin wrapper around elevate_to_admin().

### 4. Settings regression suite — existing tests must remain green
(Covered by importing and running test_settings_dialog.py as part of the
same pytest run; no explicit re-export needed here.)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_auth_service(correct_pin: str = "1234") -> MagicMock:
    """Return a SettingsService mock that accepts only *correct_pin*."""
    svc = MagicMock()
    svc.elevate_to_admin.side_effect = lambda pin: pin == correct_pin
    return svc


def _make_dialog(service: MagicMock | None = None) -> "AdminPinDialog":
    """Create an AdminPinDialog in auth mode with the given service mock."""
    from src.strategy_builder.ui.settings_dialog import AdminPinDialog
    return AdminPinDialog(setup_mode=False, service=service or _make_auth_service())


# ===========================================================================
# 1. Sentinel-skip tests (SecretFieldWidget)
# ===========================================================================

class TestSecretFieldWidgetSentinel:
    """
    SecretFieldWidget.get_value() must return the sentinel "••••" whenever
    the user has NOT entered a new value, so SettingsService knows to skip
    the field and leave the keyring unchanged.
    """

    def test_get_value_returns_sentinel_when_not_in_edit_mode(self, qapp):
        """
        When the widget is in display mode (not edit), get_value() must
        return the all-bullet sentinel.
        """
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = MagicMock(spec=SettingsService)
        svc.get_masked.return_value = "••••••••ac84"

        widget = SecretFieldWidget(key="OPENROUTER_API_KEY", service=svc)
        assert not widget._edit_mode, "Widget should start in display mode."
        value = widget.get_value()

        assert value == "••••", (
            f"get_value() in display mode must return the sentinel '••••', "
            f"got: {value!r}"
        )
        widget.close()

    def test_get_value_returns_sentinel_when_edit_mode_empty(self, qapp):
        """
        When the widget IS in edit mode but the edit field is empty (user
        opened Edit without typing anything), get_value() must still return
        the sentinel so the keyring entry is not overwritten with an empty
        string.
        """
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = MagicMock(spec=SettingsService)
        svc.get_masked.return_value = "••••••••ac84"

        widget = SecretFieldWidget(key="OPENROUTER_API_KEY", service=svc)
        # Simulate entering edit mode without typing
        widget._enter_edit_mode()
        # _edit_field is empty by design (cleared in _enter_edit_mode)
        assert widget._edit_mode
        assert widget._edit_field.text() == ""

        value = widget.get_value()
        assert value == "••••", (
            f"get_value() in edit mode with empty field must still return "
            f"the sentinel '••••', got: {value!r}"
        )
        widget.close()

    def test_get_value_returns_sentinel_when_edit_mode_whitespace_only(self, qapp):
        """
        Whitespace-only input is treated as empty — sentinel is returned.
        """
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = MagicMock(spec=SettingsService)
        svc.get_masked.return_value = ""

        widget = SecretFieldWidget(key="LAKEAPI_KEY", service=svc)
        widget._enter_edit_mode()
        widget._edit_field.setText("   ")  # whitespace only

        value = widget.get_value()
        assert value == "••••", (
            f"Whitespace-only edit must return sentinel, got: {value!r}"
        )
        widget.close()

    def test_get_value_returns_typed_text_when_edit_mode_non_empty(self, qapp):
        """
        When edit mode is active and the user has typed a non-empty value,
        get_value() must return that typed text (not the sentinel).
        """
        from src.strategy_builder.ui.settings_dialog import SecretFieldWidget
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = MagicMock(spec=SettingsService)
        svc.get_masked.return_value = ""

        widget = SecretFieldWidget(key="LAKEAPI_KEY", service=svc)
        widget._enter_edit_mode()
        widget._edit_field.setText("my-new-secret-key")

        value = widget.get_value()
        assert value == "my-new-secret-key", (
            f"get_value() with typed content must return the typed text, "
            f"got: {value!r}"
        )
        widget.close()


class TestSettingsServiceSentinelSkip:
    """
    SettingsService.save_user_settings() and save_admin_settings() must
    treat any value consisting entirely of bullet characters as a sentinel
    and skip it — never writing it to keyring or .env.
    """

    def test_save_user_settings_skips_sentinel_value(self):
        """
        When a USER_KEY field has value '••••' (all bullets), save_user_settings()
        must NOT call self.set() for that key, leaving the keyring untouched.
        """
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        svc.save_user_settings({
            "OPENROUTER_API_KEY": "••••",  # sentinel — must be skipped
            "AI_MODEL": "anthropic/claude-4-opus",  # real value — must be saved
        })

        called_keys = [c.args[0] for c in svc.set.call_args_list]
        assert "OPENROUTER_API_KEY" not in called_keys, (
            "save_user_settings() must NOT call set() for a sentinel value — "
            "the keyring entry must remain unchanged."
        )
        assert "AI_MODEL" in called_keys, (
            "save_user_settings() must call set() for a non-sentinel value."
        )

    def test_save_user_settings_skips_multi_bullet_sentinel(self):
        """
        Any string composed entirely of bullet characters is treated as
        a sentinel and skipped.  The service checks ``set(value) == {"•"}``,
        so a longer all-bullet string like ``"••••••••"`` also qualifies.

        Note: a masked value like ``"••••••••ac84"`` is NOT all-bullets
        (it contains alphanumeric suffix) and should therefore be saved;
        this test targets a pure-bullet string of arbitrary length.
        """
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        # Eight bullets — all same character → set(value) == {"•"} → sentinel
        svc.save_user_settings({
            "OPENROUTER_API_KEY": "••••••••",  # pure bullets — must be skipped
        })

        called_keys = [c.args[0] for c in svc.set.call_args_list]
        assert "OPENROUTER_API_KEY" not in called_keys, (
            "An all-bullet string of any length must be treated as sentinel and skipped."
        )

    def test_save_admin_settings_skips_sentinel_value(self):
        """
        save_admin_settings() must skip sentinel values identically.
        """
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.ADMIN
        svc.is_admin = lambda: True
        svc.set = MagicMock()

        svc.save_admin_settings({
            "POSTGRES_PASSWORD": "••••",      # sentinel — skip
            "POSTGRES_HOST": "db.prod.local",  # real value — save
        })

        called_keys = [c.args[0] for c in svc.set.call_args_list]
        assert "POSTGRES_PASSWORD" not in called_keys, (
            "save_admin_settings() must skip sentinel POSTGRES_PASSWORD."
        )
        assert "POSTGRES_HOST" in called_keys, (
            "save_admin_settings() must save non-sentinel POSTGRES_HOST."
        )

    def test_save_user_settings_does_not_skip_real_bullet_free_value(self):
        """
        A value that contains bullet characters mixed with other characters
        is NOT a sentinel and must be saved.
        """
        from src.strategy_builder.ui.settings_service import SettingsService

        svc = SettingsService.__new__(SettingsService)
        svc.set = MagicMock()

        # '••••X' contains non-bullet chars → set() == {"•", "X"} → not skipped
        svc.save_user_settings({
            "AI_MODEL": "••••X",
        })

        called_keys = [c.args[0] for c in svc.set.call_args_list]
        assert "AI_MODEL" in called_keys, (
            "A mixed bullet+text value must NOT be treated as a sentinel."
        )


# ===========================================================================
# 2. AdminPinDialog lockout tests (headless)
# ===========================================================================

class TestAdminPinDialogLockout:
    """
    Headless tests for the brute-force lockout mechanism added in
    BTCAAAAA-202.  QTimer ticks are simulated by calling _on_lockout_tick()
    directly rather than waiting for real time to pass.
    """

    # ------------------------------------------------------------------
    # Failure counting
    # ------------------------------------------------------------------

    def test_fail_count_increments_on_wrong_pin(self, qapp):
        """Each wrong PIN attempt must increment _fail_count by 1."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._pin_field.setText("wrong")
        dlg._attempt_auth()
        assert dlg._fail_count == 1, f"Expected _fail_count=1, got {dlg._fail_count}"

        dlg._pin_field.setText("also_wrong")
        dlg._attempt_auth()
        assert dlg._fail_count == 2, f"Expected _fail_count=2, got {dlg._fail_count}"
        dlg.close()

    def test_fail_count_does_not_increment_on_correct_pin(self, qapp):
        """A correct PIN must not increment _fail_count."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        # Patch accept() to prevent dialog from closing
        dlg.accept = MagicMock()
        dlg._pin_field.setText("1234")
        dlg._attempt_auth()

        assert dlg._fail_count == 0, (
            f"_fail_count must stay 0 on correct PIN, got {dlg._fail_count}"
        )
        dlg.close()

    # ------------------------------------------------------------------
    # Lockout activation after MAX_FAILURES
    # ------------------------------------------------------------------

    def test_lockout_activates_after_three_failures(self, qapp):
        """
        After _MAX_FAILURES (3) wrong attempts, the dialog must enter
        locked state: _lockout_remaining == _LOCKOUT_SECONDS.
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        for _ in range(dlg._MAX_FAILURES):
            dlg._pin_field.setText("bad")
            dlg._attempt_auth()

        assert dlg._lockout_remaining == dlg._LOCKOUT_SECONDS, (
            f"Expected _lockout_remaining={dlg._LOCKOUT_SECONDS} after "
            f"{dlg._MAX_FAILURES} failures, got {dlg._lockout_remaining}"
        )
        dlg.close()

    def test_pin_field_disabled_during_lockout(self, qapp):
        """PIN field must be disabled when lockout is active."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        for _ in range(dlg._MAX_FAILURES):
            dlg._pin_field.setText("bad")
            dlg._attempt_auth()

        assert not dlg._pin_field.isEnabled(), (
            "PIN input field must be disabled during lockout."
        )
        dlg.close()

    def test_ok_button_disabled_during_lockout(self, qapp):
        """OK button must be disabled when lockout is active."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        for _ in range(dlg._MAX_FAILURES):
            dlg._pin_field.setText("bad")
            dlg._attempt_auth()

        assert not dlg._ok_button.isEnabled(), (
            "OK button must be disabled during lockout."
        )
        dlg.close()

    def test_lockout_label_visible_and_contains_countdown(self, qapp):
        """
        Lockout countdown label must be shown (not hidden) and contain the
        remaining seconds after lockout activates.

        We check ``not isHidden()`` rather than ``isVisible()`` because in
        headless tests the parent dialog is never shown, so Qt always returns
        False from ``isVisible()`` for child widgets even after ``.show()``.
        ``isHidden()`` reflects only the widget's own explicit show/hide state.
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        for _ in range(dlg._MAX_FAILURES):
            dlg._pin_field.setText("bad")
            dlg._attempt_auth()

        assert not dlg._lockout_label.isHidden(), (
            "_lockout_label must not be hidden during lockout "
            "(i.e. _start_lockout() called .show() on it)."
        )
        label_text = dlg._lockout_label.text()
        assert str(dlg._LOCKOUT_SECONDS) in label_text, (
            f"Lockout label must show remaining seconds ({dlg._LOCKOUT_SECONDS}s). "
            f"Got: {label_text!r}"
        )
        dlg.close()

    # ------------------------------------------------------------------
    # attempt_auth is no-op during lockout
    # ------------------------------------------------------------------

    def test_attempt_auth_noop_during_lockout(self, qapp):
        """
        _attempt_auth() must not call elevate_to_admin() while lockout is
        active — keyboard shortcuts must not bypass the disabled OK button.
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        # Trigger lockout
        for _ in range(dlg._MAX_FAILURES):
            dlg._pin_field.setText("bad")
            dlg._attempt_auth()

        # Now reset call count and try again during lockout
        svc.elevate_to_admin.reset_mock()
        dlg._pin_field.setText("1234")  # correct PIN
        dlg._attempt_auth()  # must be ignored while locked

        svc.elevate_to_admin.assert_not_called(), (
            "elevate_to_admin() must NOT be called during lockout — "
            "_attempt_auth() must exit early."
        )
        dlg.close()

    # ------------------------------------------------------------------
    # Timer ticks / countdown decrement
    # ------------------------------------------------------------------

    def test_lockout_tick_decrements_counter(self, qapp):
        """Each call to _on_lockout_tick() must decrement _lockout_remaining."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        # Manually start lockout to avoid QTimer dependency
        dlg._start_lockout()
        initial = dlg._lockout_remaining  # should be _LOCKOUT_SECONDS

        dlg._on_lockout_tick()
        assert dlg._lockout_remaining == initial - 1, (
            f"_lockout_remaining must decrease by 1 per tick. "
            f"Expected {initial - 1}, got {dlg._lockout_remaining}"
        )

        dlg._on_lockout_tick()
        assert dlg._lockout_remaining == initial - 2
        dlg.close()

    def test_lockout_label_updates_on_each_tick(self, qapp):
        """
        The countdown label text must be updated on every tick to reflect
        the current remaining seconds.
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._start_lockout()
        dlg._on_lockout_tick()  # 29 remaining

        label_text = dlg._lockout_label.text()
        assert "29" in label_text, (
            f"Label must show 29s after one tick, got: {label_text!r}"
        )
        dlg.close()

    # ------------------------------------------------------------------
    # Lockout expiry / _end_lockout
    # ------------------------------------------------------------------

    def test_end_lockout_resets_fail_count(self, qapp):
        """_end_lockout() must reset _fail_count to 0."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._start_lockout()
        dlg._fail_count = dlg._MAX_FAILURES  # set as if 3 failures recorded
        dlg._end_lockout()

        assert dlg._fail_count == 0, (
            f"_end_lockout() must reset _fail_count to 0, got {dlg._fail_count}"
        )
        dlg.close()

    def test_end_lockout_resets_remaining_counter(self, qapp):
        """_end_lockout() must set _lockout_remaining back to 0."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._start_lockout()
        dlg._end_lockout()

        assert dlg._lockout_remaining == 0, (
            f"_lockout_remaining must be 0 after _end_lockout(), "
            f"got {dlg._lockout_remaining}"
        )
        dlg.close()

    def test_end_lockout_reenables_pin_field(self, qapp):
        """PIN field must be re-enabled after lockout expires."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._start_lockout()
        assert not dlg._pin_field.isEnabled(), "Precondition: field disabled during lockout."
        dlg._end_lockout()

        assert dlg._pin_field.isEnabled(), (
            "PIN field must be re-enabled after lockout expires."
        )
        dlg.close()

    def test_end_lockout_reenables_ok_button(self, qapp):
        """OK button must be re-enabled after lockout expires."""
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._start_lockout()
        dlg._end_lockout()

        assert dlg._ok_button.isEnabled(), (
            "OK button must be re-enabled after lockout expires."
        )
        dlg.close()

    def test_end_lockout_hides_lockout_label(self, qapp):
        """
        Lockout label must be hidden after lockout expires.

        Uses ``isHidden()`` for the same reason as the visibility test above —
        the parent dialog is not shown in headless tests, so ``isVisible()``
        always returns False even for explicitly shown child widgets.
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._start_lockout()
        assert not dlg._lockout_label.isHidden(), (
            "Precondition: label must be shown (not hidden) during lockout."
        )
        dlg._end_lockout()

        assert dlg._lockout_label.isHidden(), (
            "_lockout_label must be hidden after _end_lockout()."
        )
        dlg.close()

    def test_lockout_expires_after_lockout_seconds_ticks(self, qapp):
        """
        Simulating _LOCKOUT_SECONDS ticks must trigger _end_lockout():
        the dialog should no longer be in lockout state.
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._start_lockout()

        # Simulate all ticks except the last
        for _ in range(dlg._LOCKOUT_SECONDS - 1):
            dlg._on_lockout_tick()
        # Lockout still active
        assert dlg._lockout_remaining == 1, (
            f"After {dlg._LOCKOUT_SECONDS - 1} ticks, 1 second must remain."
        )

        # Final tick → end_lockout
        dlg._on_lockout_tick()
        assert dlg._lockout_remaining == 0, (
            "After all ticks, _lockout_remaining must be 0."
        )
        assert dlg._fail_count == 0, "After all ticks, _fail_count must be 0."
        assert dlg._pin_field.isEnabled(), "After all ticks, PIN field must be enabled."
        assert dlg._ok_button.isEnabled(), "After all ticks, OK button must be enabled."
        dlg.close()

    # ------------------------------------------------------------------
    # Correct PIN after lockout expires
    # ------------------------------------------------------------------

    def test_correct_pin_accepted_after_lockout_expires(self, qapp):
        """
        After a lockout expires, a correct PIN must succeed (dialog accepts).
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)
        dlg.accept = MagicMock()

        # Trigger and expire the lockout
        for _ in range(dlg._MAX_FAILURES):
            dlg._pin_field.setText("bad")
            dlg._attempt_auth()

        # Expire lockout by simulating all ticks
        for _ in range(dlg._LOCKOUT_SECONDS):
            dlg._on_lockout_tick()

        # Now try the correct PIN
        dlg._pin_field.setText("1234")
        dlg._attempt_auth()

        dlg.accept.assert_called_once(), (
            "accept() must be called when correct PIN entered after lockout expires."
        )
        dlg.close()

    # ------------------------------------------------------------------
    # Dialog close / reset
    # ------------------------------------------------------------------

    def test_close_event_stops_lockout_timer(self, qapp):
        """
        Closing the dialog during lockout must stop the QTimer so no
        dangling callbacks fire after the widget is destroyed.
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        dlg._start_lockout()
        timer = dlg._lockout_timer
        assert timer is not None, "Precondition: timer must be running after _start_lockout."
        assert timer.isActive(), "Precondition: timer must be active."

        # Simulate close
        from PyQt5.QtGui import QCloseEvent
        dlg.closeEvent(QCloseEvent())

        assert dlg._lockout_timer is None, (
            "closeEvent() must set _lockout_timer to None to prevent dangling callbacks."
        )
        assert not timer.isActive(), (
            "QTimer must be stopped when the dialog closes."
        )
        dlg.close()

    def test_lockout_state_is_fresh_for_new_dialog_instance(self, qapp):
        """
        Each new AdminPinDialog instance starts with clean lockout state.
        """
        svc = _make_auth_service(correct_pin="1234")
        dlg = _make_dialog(svc)

        assert dlg._fail_count == 0
        assert dlg._lockout_remaining == 0
        assert dlg._lockout_timer is None
        assert dlg._lockout_label.isHidden(), (
            "Lockout label must start hidden on a fresh dialog instance."
        )
        assert dlg._pin_field.isEnabled()
        assert dlg._ok_button.isEnabled()
        dlg.close()


# ===========================================================================
# 3. SettingsService.elevate_to_admin() regression tests
# ===========================================================================

class TestElevateToAdminRegression:
    """
    Unit tests for SettingsService.elevate_to_admin() and its
    backwards-compat wrapper authenticate_admin().
    """

    def test_elevate_returns_false_when_no_pin_stored(self):
        """elevate_to_admin() must return False when no PIN is configured."""
        from src.strategy_builder.ui.settings_service import SettingsService

        with patch("src.strategy_builder.ui.settings_service.keyring.get_password", return_value=None):
            svc = SettingsService.__new__(SettingsService)
            from src.strategy_builder.ui.settings_service import UserRole
            svc._role = UserRole.USER

            result = svc.elevate_to_admin("any_pin")

        assert result is False, (
            "elevate_to_admin() must return False when no PIN hash is stored."
        )

    def test_elevate_returns_false_for_wrong_pin(self):
        """elevate_to_admin() must return False for an incorrect PIN."""
        import bcrypt
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        correct_pin = "supersecret"
        hashed = bcrypt.hashpw(correct_pin.encode(), bcrypt.gensalt()).decode()

        with patch(
            "src.strategy_builder.ui.settings_service.keyring.get_password",
            return_value=hashed,
        ):
            svc = SettingsService.__new__(SettingsService)
            svc._role = UserRole.USER

            result = svc.elevate_to_admin("wrongpin")

        assert result is False, (
            "elevate_to_admin() must return False for a wrong PIN."
        )

    def test_elevate_returns_true_and_sets_admin_role_on_correct_pin(self):
        """
        elevate_to_admin() must return True and update _role to ADMIN
        when the supplied PIN matches the stored bcrypt hash.
        """
        import bcrypt
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        correct_pin = "supersecret"
        hashed = bcrypt.hashpw(correct_pin.encode(), bcrypt.gensalt()).decode()

        with patch(
            "src.strategy_builder.ui.settings_service.keyring.get_password",
            return_value=hashed,
        ):
            svc = SettingsService.__new__(SettingsService)
            svc._role = UserRole.USER

            result = svc.elevate_to_admin(correct_pin)

        assert result is True, (
            "elevate_to_admin() must return True for the correct PIN."
        )
        assert svc._role == UserRole.ADMIN, (
            "elevate_to_admin() must elevate _role to ADMIN on success."
        )

    def test_elevate_does_not_change_role_on_wrong_pin(self):
        """
        elevate_to_admin() must leave _role as USER when the PIN is wrong.
        """
        import bcrypt
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        correct_pin = "supersecret"
        hashed = bcrypt.hashpw(correct_pin.encode(), bcrypt.gensalt()).decode()

        with patch(
            "src.strategy_builder.ui.settings_service.keyring.get_password",
            return_value=hashed,
        ):
            svc = SettingsService.__new__(SettingsService)
            svc._role = UserRole.USER

            svc.elevate_to_admin("wrongpin")

        assert svc._role == UserRole.USER, (
            "A wrong PIN must NOT change _role from USER."
        )

    def test_authenticate_admin_delegates_to_elevate_to_admin(self):
        """
        authenticate_admin() must be a thin wrapper around elevate_to_admin()
        — both must return the same result for the same inputs.
        """
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.USER

        with patch.object(svc, "elevate_to_admin", return_value=True) as mock_elevate:
            result = svc.authenticate_admin("1234")

        mock_elevate.assert_called_once_with("1234"), (
            "authenticate_admin() must delegate to elevate_to_admin() with the same pin."
        )
        assert result is True, (
            "authenticate_admin() must return the value from elevate_to_admin()."
        )

    def test_elevate_to_admin_first_run_raises_if_pin_already_set(self):
        """
        elevate_to_admin_first_run() must raise PermissionError when a PIN
        is already stored — it is only valid during initial setup.
        """
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.USER
        svc.has_admin_pin = lambda: True  # PIN already configured

        with pytest.raises(PermissionError, match="elevate_to_admin_first_run"):
            svc.elevate_to_admin_first_run()

    def test_elevate_to_admin_first_run_grants_admin_when_no_pin(self):
        """
        elevate_to_admin_first_run() must set role to ADMIN when no PIN
        exists yet — this enables the first-run PIN setup flow.
        """
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.USER
        svc.has_admin_pin = lambda: False  # No PIN set yet

        svc.elevate_to_admin_first_run()

        assert svc._role == UserRole.ADMIN, (
            "elevate_to_admin_first_run() must set role to ADMIN when no PIN exists."
        )

    def test_drop_admin_reverts_role_to_user(self):
        """drop_admin() must return _role to USER from ADMIN."""
        from src.strategy_builder.ui.settings_service import SettingsService, UserRole

        svc = SettingsService.__new__(SettingsService)
        svc._role = UserRole.ADMIN

        svc.drop_admin()

        assert svc._role == UserRole.USER, (
            "drop_admin() must set _role back to UserRole.USER."
        )
