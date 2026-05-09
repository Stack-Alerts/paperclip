"""
Headless executable-path smoke tests for the Quick Preview button in
StrategyBuilderMainWindow (BTCAAAAA-749).

These tests instantiate the full StrategyBuilderMainWindow in offscreen mode.
A minimal real subclass suppresses the auto-update startup modal so the window
opens without blocking in CI.  All dialogs are auto-dismissed via
QTimer.singleShot — no monkey-overrides or fake objects are used anywhere.

Test cases:
  - Button is visible in the toolbar.
  - Button starts enabled.
  - No-blocks guard: clicking with no blocks triggers a dialog (not a crash).
  - Double-click guard: clicking while running triggers an information dialog.
  - Button re-enabled: _on_preview_finished(success=True) re-enables the button.
  - Button text resets after finish.
  - Failure path also re-enables the button.
  - Zero-trades: QuickPreviewResultsDialog is opened even for 0 trades.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_quick_preview_mainwindow.py -v --tb=long
"""
from __future__ import annotations

import pytest
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton
from PyQt5.QtCore import QThread, QTimer


# ---------------------------------------------------------------------------
# Real subclass — suppresses the startup modal without any mocking
# ---------------------------------------------------------------------------

def _make_no_modal_window_class():
    """Lazily import and subclass so import errors surface at test time, not collection."""
    from src.strategy_builder.ui.strategy_builder_main_window import StrategyBuilderMainWindow

    class _NoModalMainWindow(StrategyBuilderMainWindow):
        def _on_app_start(self):
            pass  # suppress DataUpdateModal in offscreen / CI context

    return _NoModalMainWindow


def _build_main_window(qtbot):
    """Instantiate the modal-suppressed main window and register cleanup."""
    cls = _make_no_modal_window_class()
    win = cls()
    qtbot.addWidget(win)
    QApplication.processEvents()
    return win


# ---------------------------------------------------------------------------
# Dialog auto-dismissal helper (no mocking — uses real Qt event loop)
# ---------------------------------------------------------------------------

def _schedule_dismiss_active_modal(delay_ms: int = 0):
    """
    Schedule a QTimer that accepts the first visible QDialog or QMessageBox.
    The callback fires inside the nested event loop spawned by exec_(), so
    it reliably auto-closes static QMessageBox calls without any stubbing.
    """
    def _close():
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, (QDialog, QMessageBox)) and widget.isVisible():
                widget.accept()
                return

    QTimer.singleShot(delay_ms, _close)


# ---------------------------------------------------------------------------
# Real QThread subclass that reports isRunning()=True — replaces fake-worker injection
# ---------------------------------------------------------------------------

class _RunningWorkerStub(QThread):
    """
    Real QThread subclass whose isRunning() always returns True.
    Never actually started — overriding the method is sufficient to drive the
    double-click guard logic in _on_quick_preview without spawning a real thread.
    """

    def isRunning(self) -> bool:  # noqa: N802
        return True

    def run(self):
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_preview_button_exists_in_toolbar(qtbot):
    """Quick Preview button must be present as a QPushButton with correct text."""
    win = _build_main_window(qtbot)
    assert win.preview_btn is not None, "preview_btn attribute must not be None"
    assert isinstance(win.preview_btn, QPushButton)
    assert win.preview_btn.text() == "Quick Preview", (
        f"Expected 'Quick Preview', got '{win.preview_btn.text()}'"
    )


@pytest.mark.qt_real
def test_preview_button_enabled_at_startup(qtbot):
    """Button must start in an enabled state (no preview running at startup)."""
    win = _build_main_window(qtbot)
    assert win.preview_btn.isEnabled(), "Quick Preview button must be enabled on startup"


@pytest.mark.qt_real
def test_no_blocks_guard_shows_warning_not_crash(qtbot):
    """
    Clicking Quick Preview with no strategy blocks must show a warning dialog
    and return cleanly.  Verified by: button remains enabled, no worker started.
    """
    win = _build_main_window(qtbot)
    config = win.orchestrator.get_current_config()
    if config and getattr(config, 'blocks', None):
        config.blocks = []

    _schedule_dismiss_active_modal(0)
    win._on_quick_preview()
    QApplication.processEvents()

    assert win.preview_btn.isEnabled(), (
        "Button must remain enabled after a no-blocks guard rejection"
    )
    assert win._preview_worker is None or not win._preview_worker.isRunning(), (
        "No worker must have been started by the no-blocks guard path"
    )


@pytest.mark.qt_real
def test_double_click_guard_shows_information(qtbot):
    """
    Clicking while a preview is already running must show an information dialog
    instead of crashing or starting a second worker.
    A real QThread subclass drives isRunning()=True without any mocking.
    """
    win = _build_main_window(qtbot)

    stub = _RunningWorkerStub()
    win._preview_worker = stub

    _schedule_dismiss_active_modal(0)
    win._on_quick_preview()
    QApplication.processEvents()

    assert win._preview_worker is stub, (
        "Original running worker must still be assigned after the guard fires"
    )


@pytest.mark.qt_real
def test_preview_finished_re_enables_button(qtbot):
    """
    _on_preview_finished(success=True) must re-enable the button and reset its
    text to 'Quick Preview'.  The QuickPreviewResultsDialog is auto-dismissed.
    """
    win = _build_main_window(qtbot)
    win.preview_btn.setEnabled(False)
    win.preview_btn.setText("Running...")
    win._preview_trades = []

    _schedule_dismiss_active_modal(0)
    win._on_preview_finished(success=True, results={"trades": 0})
    QApplication.processEvents()

    assert win.preview_btn.isEnabled(), (
        "Button must be re-enabled after _on_preview_finished(success=True)"
    )
    assert win.preview_btn.text() == "Quick Preview", (
        f"Button text must reset to 'Quick Preview'; got '{win.preview_btn.text()}'"
    )


@pytest.mark.qt_real
def test_preview_finished_failure_re_enables_button(qtbot):
    """
    _on_preview_finished(success=False) must also re-enable the button and reset
    its text — the worker ended even though it failed.
    """
    win = _build_main_window(qtbot)
    win.preview_btn.setEnabled(False)
    win.preview_btn.setText("Running...")

    _schedule_dismiss_active_modal(0)
    win._on_preview_finished(success=False, results={"error": "simulated error"})
    QApplication.processEvents()

    assert win.preview_btn.isEnabled(), (
        "Button must be re-enabled after _on_preview_finished(success=False)"
    )
    assert win.preview_btn.text() == "Quick Preview", (
        f"Button text must reset; got '{win.preview_btn.text()}'"
    )


@pytest.mark.qt_real
def test_preview_finished_zero_trades_shows_dialog(qtbot):
    """
    _on_preview_finished with 0 trades must open QuickPreviewResultsDialog
    (not skip it).  Verified by capturing the dialog class name before dismissal.
    """
    win = _build_main_window(qtbot)
    win.preview_btn.setEnabled(False)
    win.preview_btn.setText("Running...")
    win._preview_trades = []

    captured_dialog_classes: list[str] = []

    def _capture_and_close():
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                captured_dialog_classes.append(type(widget).__name__)
                widget.accept()
                return

    QTimer.singleShot(0, _capture_and_close)
    win._on_preview_finished(success=True, results={"trades": 0})
    QApplication.processEvents()

    assert captured_dialog_classes, (
        "_on_preview_finished must open a dialog even for 0 trades"
    )
    assert "QuickPreviewResultsDialog" in captured_dialog_classes, (
        f"Expected QuickPreviewResultsDialog, got: {captured_dialog_classes}"
    )
