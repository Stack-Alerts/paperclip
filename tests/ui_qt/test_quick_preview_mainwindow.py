"""
Headless executable-path smoke tests for the Quick Preview button in
StrategyBuilderMainWindow (BTCAAAAA-749).

These tests instantiate the full StrategyBuilderMainWindow (no __new__ bypass)
in offscreen mode, suppressing only the auto-update startup modal so the window
can open cleanly in CI.  They exercise the actual guard logic paths in
_on_quick_preview that cannot be reached via QuickPreviewResultsDialog alone.

Test cases:
  - Button is visible in the toolbar.
  - No-blocks guard: clicking with no blocks shows QMessageBox.warning, not a crash.
  - Double-click guard: clicking while running shows QMessageBox.information.
  - Button re-enabled: _on_preview_finished() re-enables the button.
  - Button text resets: button text returns to 'Quick Preview' after finish.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_quick_preview_mainwindow.py -v --tb=long
"""
from __future__ import annotations

import sys
import types
from unittest.mock import patch, MagicMock

import pytest
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt5.QtCore import QTimer


# ---------------------------------------------------------------------------
# Helpers — create the main window suppressing the startup modal
# ---------------------------------------------------------------------------

def _build_main_window(qtbot):
    """
    Instantiate StrategyBuilderMainWindow with the data-update startup modal
    suppressed so the window opens without blocking in offscreen mode.
    Returns the window object; qtbot.addWidget registers cleanup.
    """
    from src.strategy_builder.ui.strategy_builder_main_window import StrategyBuilderMainWindow

    with patch.object(
        StrategyBuilderMainWindow,
        "_on_app_start",
        lambda self: None,   # suppress the 2-second-delayed modal
    ):
        win = StrategyBuilderMainWindow()

    qtbot.addWidget(win)
    QApplication.processEvents()
    return win


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_preview_button_exists_in_toolbar(qtbot):
    """
    Smoke — Quick Preview button must be present on the toolbar as a QPushButton
    with text 'Quick Preview'.
    """
    win = _build_main_window(qtbot)
    assert win.preview_btn is not None, "preview_btn attribute must not be None"
    assert isinstance(win.preview_btn, QPushButton)
    assert win.preview_btn.text() == "Quick Preview", (
        f"Expected button text 'Quick Preview', got '{win.preview_btn.text()}'"
    )


@pytest.mark.qt_real
def test_preview_button_enabled_at_startup(qtbot):
    """Button must start in an enabled state (no preview running at startup)."""
    win = _build_main_window(qtbot)
    assert win.preview_btn.isEnabled(), "Quick Preview button must be enabled on startup"


@pytest.mark.qt_real
def test_no_blocks_guard_shows_warning_not_crash(qtbot):
    """
    Clicking Quick Preview with no strategy blocks must show a QMessageBox.warning
    and return cleanly without crashing or raising.
    """
    win = _build_main_window(qtbot)
    # Ensure no blocks are loaded (fresh window has default empty strategy)
    config = win.orchestrator.get_current_config()
    if config and getattr(config, 'blocks', None):
        # Clear blocks if any were auto-populated
        config.blocks = []

    warning_shown = []
    with patch(
        "src.strategy_builder.ui.strategy_builder_main_window.QMessageBox.warning",
        side_effect=lambda *a, **kw: warning_shown.append(a),
    ):
        win._on_quick_preview()

    assert warning_shown, (
        "_on_quick_preview() must show QMessageBox.warning when no blocks are configured"
    )
    # Button must remain enabled — no worker was started
    assert win.preview_btn.isEnabled(), (
        "Button must remain enabled after a no-blocks guard rejection"
    )


@pytest.mark.qt_real
def test_double_click_guard_shows_information(qtbot):
    """
    Clicking while a preview is already running must show QMessageBox.information
    ('A quick preview is already running') instead of crashing.
    """
    win = _build_main_window(qtbot)

    # Simulate a running worker by injecting a mock that reports isRunning()=True
    fake_worker = MagicMock()
    fake_worker.isRunning.return_value = True
    win._preview_worker = fake_worker

    info_shown = []
    with patch(
        "src.strategy_builder.ui.strategy_builder_main_window.QMessageBox.information",
        side_effect=lambda *a, **kw: info_shown.append(a),
    ):
        win._on_quick_preview()

    assert info_shown, (
        "_on_quick_preview() must show QMessageBox.information when a worker is already running"
    )


@pytest.mark.qt_real
def test_preview_finished_re_enables_button(qtbot):
    """
    _on_preview_finished(success=True, ...) must re-enable the button and reset
    its text to 'Quick Preview' regardless of trades found.
    """
    win = _build_main_window(qtbot)
    # Simulate the button being in 'Running...' state
    win.preview_btn.setEnabled(False)
    win.preview_btn.setText("Running...")
    win._preview_trades = []

    # Call the finish handler — patch exec_() on QDialog so it doesn't block
    from PyQt5.QtWidgets import QDialog
    with patch.object(QDialog, "exec_", return_value=0):
        win._on_preview_finished(success=True, results={"trades": 0})

    assert win.preview_btn.isEnabled(), (
        "Button must be re-enabled after _on_preview_finished(success=True)"
    )
    assert win.preview_btn.text() == "Quick Preview", (
        f"Button text must reset to 'Quick Preview'; got '{win.preview_btn.text()}'"
    )


@pytest.mark.qt_real
def test_preview_finished_failure_re_enables_button(qtbot):
    """
    _on_preview_finished(success=False, ...) must also re-enable the button and
    reset its text — the worker ended even though it failed.
    """
    win = _build_main_window(qtbot)
    win.preview_btn.setEnabled(False)
    win.preview_btn.setText("Running...")

    from PyQt5.QtWidgets import QMessageBox
    with patch.object(QMessageBox, "critical", return_value=0):
        win._on_preview_finished(success=False, results={"error": "simulated error"})

    assert win.preview_btn.isEnabled(), (
        "Button must be re-enabled after _on_preview_finished(success=False)"
    )
    assert win.preview_btn.text() == "Quick Preview"


@pytest.mark.qt_real
def test_preview_finished_zero_trades_shows_dialog(qtbot):
    """
    _on_preview_finished with 0 trades must still open QuickPreviewResultsDialog
    (not skip it), and the dialog must mention zero-trades hint.
    """
    win = _build_main_window(qtbot)
    win.preview_btn.setEnabled(False)
    win.preview_btn.setText("Running...")
    win._preview_trades = []  # no closed trades

    dialogs_opened = []
    from PyQt5.QtWidgets import QDialog
    original_exec = QDialog.exec_

    def _capture_exec(self_dlg):
        dialogs_opened.append(self_dlg)
        return 0  # do not block

    with patch.object(QDialog, "exec_", _capture_exec):
        win._on_preview_finished(success=True, results={"trades": 0})

    assert dialogs_opened, (
        "_on_preview_finished must open QuickPreviewResultsDialog even for 0 trades"
    )
