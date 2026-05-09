"""
E2E tests for WindowGeometryMixin — maximize, restore, and multi-monitor
position guard.

Regression coverage for:
  BTCAAAAA-386 — maximize button absent on Linux after parent-window flag
                 inheritance.
  BTCAAAAA-682 — window crashes or loses state on restore after maximize.

Happy-path: window reaches maximized state; restore brings it back to normal.
Error-path (multi-monitor): window position must fall on at least one screen
          even after geometry persistence / restore.

Tested windows (both use WindowGeometryMixin):
  - SettingsDialog   (QDialog subclass)
  - ValidationReportWindow (QMainWindow subclass)

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_window_geometry.py -v
"""

import pytest
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.strategy_builder.ui.settings_dialog import SettingsDialog
from src.strategy_builder.ui.validation_report_window import ValidationReportWindow
from src.optimizer_v3.validation.institutional_validator import ValidationReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_report():
    return ValidationReport(
        timestamp=datetime.now().isoformat(),
        is_valid=True,
        validation_level="FULL",
    )


# ---------------------------------------------------------------------------
# SettingsDialog — maximize / restore
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_settings_dialog_window_flags_allow_maximize(qtbot):
    """
    Regression BTCAAAAA-240 / BTCAAAAA-386: SettingsDialog must carry
    WindowMaximizeButtonHint so the OS title bar shows a maximize button.
    """
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    flags = dlg.windowFlags()
    assert flags & Qt.WindowMaximizeButtonHint, (
        "SettingsDialog must set Qt.WindowMaximizeButtonHint"
    )
    # Flush the 100ms QTimer scheduled in _build_ui() so it fires while the
    # widget is still alive — prevents cross-test timer contamination.
    qtbot.wait(200)


@pytest.mark.qt_real
def test_settings_dialog_can_maximize(qtbot):
    """Happy path: SettingsDialog enters maximized state via showMaximized()."""
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    dlg.showMaximized()
    # Wait > 200 ms so QTimer.singleShot(200, ...) in showEvent fires while
    # the widget is still alive, preventing a "wrapped C/C++ object deleted" error.
    qtbot.wait(350)

    assert dlg.isMaximized(), "SettingsDialog failed to enter maximized state"


@pytest.mark.qt_real
def test_settings_dialog_restore_from_maximized(qtbot):
    """
    Regression BTCAAAAA-682: SettingsDialog must exit maximized state after
    showNormal() — no crash, no stuck-maximized state.
    """
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    dlg.showMaximized()
    qtbot.wait(350)
    dlg.showNormal()
    qtbot.wait(350)

    assert not dlg.isMaximized(), (
        "SettingsDialog must not remain maximized after showNormal()"
    )


# ---------------------------------------------------------------------------
# ValidationReportWindow — maximize / restore
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_validation_report_window_flags_allow_maximize(qtbot):
    """
    Regression BTCAAAAA-386: ValidationReportWindow must carry
    WindowMaximizeButtonHint despite having a parent window.
    """
    window = ValidationReportWindow(report=_empty_report(), config=None)
    qtbot.addWidget(window)

    flags = window.windowFlags()
    assert flags & Qt.WindowMaximizeButtonHint, (
        "ValidationReportWindow must set Qt.WindowMaximizeButtonHint"
    )
    qtbot.wait(200)


@pytest.mark.qt_real
def test_validation_report_window_can_maximize(qtbot):
    """Happy path: ValidationReportWindow enters maximized state."""
    window = ValidationReportWindow(report=_empty_report(), config=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    window.showMaximized()
    qtbot.wait(350)

    assert window.isMaximized(), "ValidationReportWindow failed to enter maximized state"


@pytest.mark.qt_real
def test_validation_report_window_restore_from_maximized(qtbot):
    """
    Regression BTCAAAAA-682: ValidationReportWindow must survive maximize →
    restore without crashing or retaining maximized state.
    """
    window = ValidationReportWindow(report=_empty_report(), config=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    window.showMaximized()
    qtbot.wait(350)
    window.showNormal()
    qtbot.wait(350)

    assert not window.isMaximized(), (
        "ValidationReportWindow must not remain maximized after showNormal()"
    )


# ---------------------------------------------------------------------------
# Multi-monitor position guard
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_window_position_is_on_a_valid_screen(qtbot):
    """
    Multi-monitor guard: after show(), the window's top-left must fall on or
    intersect with at least one available screen geometry.

    This tests the WindowGeometryMixin screen-validation logic introduced to
    prevent windows from appearing off-screen after a monitor is disconnected.

    Regression: BTCAAAAA-386 / BTCAAAAA-682.
    """
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    app = QApplication.instance()
    screens = app.screens()
    assert screens, "No screens available — test environment issue"

    window_geometry = dlg.geometry()
    on_a_screen = any(
        screen.availableGeometry().intersects(window_geometry)
        for screen in screens
    )

    assert on_a_screen, (
        f"Window geometry {window_geometry} does not intersect any screen "
        f"(screens: {[s.availableGeometry() for s in screens]})"
    )


@pytest.mark.qt_real
def test_settings_dialog_no_fixed_maximum_size(qtbot):
    """
    Regression BTCAAAAA-240: SettingsDialog must NOT set a fixed maximum size
    — doing so prevents the window from maximising on larger screens.
    """
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    max_w = dlg.maximumWidth()
    max_h = dlg.maximumHeight()

    # Qt uses 16_777_215 as the "no maximum" sentinel value (QWIDGETSIZE_MAX)
    assert max_w >= 16_777_215, (
        f"SettingsDialog.maximumWidth()={max_w} — fixed max width blocks maximize"
    )
    assert max_h >= 16_777_215, (
        f"SettingsDialog.maximumHeight()={max_h} — fixed max height blocks maximize"
    )
    qtbot.wait(200)
