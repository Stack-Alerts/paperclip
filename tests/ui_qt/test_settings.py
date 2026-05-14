"""
E2E tests for the Settings dialog — open, change a value, save, verify.

Happy-path: dialog opens, fields are editable, save round-trips through service.
Error-path: save via stub captures values correctly even when admin tab is hidden.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_settings.py -v
"""

import pytest
from PyQt5.QtWidgets import QComboBox, QTabWidget, QPushButton, QLineEdit

from src.strategy_builder.ui.settings_dialog import SettingsDialog
from src.strategy_builder.ui.settings_service import USER_DEFAULTS


# ---------------------------------------------------------------------------
# Stub service — no keyring or .env I/O; in-memory only.
# ---------------------------------------------------------------------------

class _StubSettingsService:
    """Minimal SettingsService replacement for tests.

    Implements only the methods called by SettingsDialog so tests never
    touch the real keyring or .env file.
    """

    def __init__(self, initial=None):
        self._store = dict(USER_DEFAULTS)
        if initial:
            self._store.update(initial)

    def is_admin(self):
        return False

    def get(self, key):
        return self._store.get(key)

    def get_with_default(self, key, default=""):
        return self._store.get(key, default)

    def get_masked(self, key):
        val = self._store.get(key, "")
        if not val:
            return "(not set)"
        if len(val) > 4:
            return "•" * (len(val) - 4) + val[-4:]
        return "•" * len(val)

    def save_user_settings(self, values):
        for k, v in values.items():
            if v and set(v) != {"•"}:
                self._store[k] = v

    def save_admin_settings(self, values):
        pass

    @staticmethod
    def _enforce_env_permissions():
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_settings_dialog_has_title(qtbot):
    """Dialog window title must be 'Settings'."""
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    assert dlg.windowTitle() == "Settings"
    qtbot.wait(200)


@pytest.mark.qt_real
def test_settings_dialog_has_tab_widget(qtbot):
    """Dialog contains a QTabWidget with at least 2 tabs."""
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    tabs = dlg.findChild(QTabWidget)
    assert tabs is not None, "No QTabWidget found in SettingsDialog"
    assert tabs.count() >= 2, f"Expected ≥2 tabs, got {tabs.count()}"
    qtbot.wait(200)


@pytest.mark.qt_real
def test_settings_dialog_has_save_button(qtbot):
    """Save button must exist and be enabled by default."""
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    buttons = dlg.findChildren(QPushButton)
    save_btn = next(
        (b for b in buttons if "save" in b.text().lower()),
        None,
    )
    assert save_btn is not None, (
        f"No Save button found; available buttons: {[b.text() for b in buttons]}"
    )
    assert save_btn.isEnabled(), "Save button should be enabled by default"
    qtbot.wait(200)


@pytest.mark.qt_real
def test_settings_minimum_size(qtbot):
    """Dialog minimum size satisfies BTCAAAAA-87 / BTCAAAAA-90 requirements."""
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    assert dlg.minimumWidth() >= 860
    assert dlg.minimumHeight() >= 600
    qtbot.wait(200)


@pytest.mark.qt_real
def test_settings_ai_model_field_is_editable(qtbot):
    """Happy path: AI_MODEL editable QComboBox accepts typed input."""
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    ai_combo = dlg._combo_fields.get("AI_MODEL")
    assert ai_combo is not None, "_combo_fields['AI_MODEL'] not found"
    assert ai_combo.isEditable(), "AI_MODEL combo must be editable"

    ai_combo.setEditText("anthropic/claude-opus-4")
    assert ai_combo.currentText() == "anthropic/claude-opus-4"
    qtbot.wait(200)


@pytest.mark.qt_real
def test_settings_save_persists_changed_value_via_stub(qtbot):
    """
    Happy path: Changing AI_MODEL in the editable combo then saving stores
    the new value in the service.

    The real SettingsService is replaced with a stub *before* _on_save() so
    no keyring or .env I/O occurs.  The test verifies the round-trip through
    the dialog's own field→service plumbing.
    """
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    stub = _StubSettingsService()
    dlg._service = stub

    ai_combo = dlg._combo_fields["AI_MODEL"]
    ai_combo.setEditText("anthropic/claude-test-model")

    dlg._on_save()

    assert stub._store.get("AI_MODEL") == "anthropic/claude-test-model"
    qtbot.wait(200)


@pytest.mark.qt_real
def test_settings_save_ignores_bullet_sentinel(qtbot):
    """
    Error path: A plain-text field left as all-bullet mask (unchanged sentinel)
    must NOT overwrite the stored value.
    """
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    stub = _StubSettingsService(initial={"ALERT_EMAIL": "admin@example.com"})
    dlg._service = stub

    alert_field = dlg._plain_fields["ALERT_EMAIL"]
    alert_field.setText("••••••••")  # simulate "unchanged" sentinel

    dlg._on_save()

    # Bullet-only string must not overwrite the original
    assert stub._store.get("ALERT_EMAIL") == "admin@example.com"
    qtbot.wait(200)
