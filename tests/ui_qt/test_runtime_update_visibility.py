"""
qt_real tests for runtime update visibility (BTCAAAAA-22902).

Verifies that the status bar correctly preserves runtime update messages
and that _update_countdown_status does not overwrite them.

Bug: _update_countdown_status exclusion list was missing 'Data updated',
'Update failed', and 'Auto-update', causing runtime update completion/
failure messages to be overwritten by countdown text within <=1 second.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_runtime_update_visibility.py -v
"""

from __future__ import annotations

import pytest
from PyQt5.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Helper: build a minimal main window with startup modal suppressed
# ---------------------------------------------------------------------------

def _make_no_modal_window_class():
    from src.strategy_builder.ui.strategy_builder_main_window import (
        StrategyBuilderMainWindow,
    )

    class _NoModalMainWindow(StrategyBuilderMainWindow):
        def _on_app_start(self):
            pass

    return _NoModalMainWindow


def _build_window(qtbot):
    cls = _make_no_modal_window_class()
    win = cls()
    qtbot.addWidget(win)
    QApplication.processEvents()
    return win


# ---------------------------------------------------------------------------
# Tests: runtime update status bar visibility
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_update_status_shows_data_updated_message(qtbot):
    """
    _update_status with 'Data updated at' must set the status bar text.
    The countdown timer must NOT overwrite it on subsequent ticks.
    """
    win = _build_window(qtbot)
    status_bar = win.statusBar()

    win._update_status("Data updated at 14:30:00")
    QApplication.processEvents()

    msg = status_bar.currentMessage()
    assert "Data updated at" in msg, (
        f"Status bar should show 'Data updated at', got: {msg}"
    )

    # Simulate countdown timer tick — must NOT overwrite
    win._update_countdown_status()
    QApplication.processEvents()

    msg2 = status_bar.currentMessage()
    assert "Data updated at" in msg2, (
        "Countdown timer must NOT overwrite 'Data updated at' message. "
        f"Got: {msg2}"
    )


@pytest.mark.qt_real
def test_update_status_shows_update_failed_message(qtbot):
    """
    _update_status with 'Update failed' must be preserved by the
    countdown timer.
    """
    win = _build_window(qtbot)
    status_bar = win.statusBar()

    win._update_status("Update failed: timeout after 60s")
    QApplication.processEvents()

    msg = status_bar.currentMessage()
    assert "Update failed" in msg, (
        f"Status bar should show 'Update failed', got: {msg}"
    )

    # Simulate countdown timer tick — must NOT overwrite
    win._update_countdown_status()
    QApplication.processEvents()

    msg2 = status_bar.currentMessage()
    assert "Update failed" in msg2, (
        "Countdown timer must NOT overwrite 'Update failed' message. "
        f"Got: {msg2}"
    )


@pytest.mark.qt_real
def test_on_runtime_update_finished_success_sets_status_bar(qtbot):
    """
    _on_runtime_update_finished(success=True) must set 'Data updated at'
    on the status bar.
    """
    win = _build_window(qtbot)
    status_bar = win.statusBar()
    win.next_check_time = None  # prevent countdown from showing

    win._on_runtime_update_finished(True, "15m: 2 gaps repaired")
    QApplication.processEvents()

    msg = status_bar.currentMessage()
    assert "[RuntimeUpdate] OK:" in msg, (
        f"Status bar should show .RuntimeUpdate. OK: after success, got: {msg}"
    )


@pytest.mark.qt_real
def test_on_runtime_update_finished_failure_sets_status_bar(qtbot):
    """
    _on_runtime_update_finished(success=False) must set 'Update failed'
    on the status bar.
    """
    win = _build_window(qtbot)
    status_bar = win.statusBar()
    win.next_check_time = None

    win._on_runtime_update_finished(False, "timeout after 60s")
    QApplication.processEvents()

    msg = status_bar.currentMessage()
    assert "[RuntimeUpdate] FAIL:" in msg, (
        f"Status bar should show .RuntimeUpdate. FAIL: after failure, got: {msg}"
    )


@pytest.mark.qt_real
def test_auto_update_startup_message_preserved(qtbot):
    """
    'Auto-update system started' message must not be overwritten by
    countdown.
    """
    win = _build_window(qtbot)
    status_bar = win.statusBar()

    win._update_status("Auto-update system started - Next check in 897s")
    QApplication.processEvents()

    win._update_countdown_status()
    QApplication.processEvents()

    msg = status_bar.currentMessage()
    assert "Auto-update" in msg, (
        "Countdown timer must NOT overwrite 'Auto-update' message. "
        f"Got: {msg}"
    )


@pytest.mark.qt_real
def test_countdown_shows_when_no_active_message(qtbot):
    """
    When no active message (status bar is empty or shows 'Ready'), the
    countdown should display normally.
    """
    win = _build_window(qtbot)
    status_bar = win.statusBar()

    # Set next check time
    from datetime import datetime, timedelta, timezone
    win.next_check_time = datetime.now(timezone.utc) + timedelta(minutes=4, seconds=30)

    win._update_countdown_status()
    QApplication.processEvents()

    msg = status_bar.currentMessage()
    assert "Next data check in" in msg, (
        f"Countdown should show when no active message, got: {msg}"
    )


@pytest.mark.qt_real
def test_active_operation_messages_not_overwritten(qtbot):
    """
    Known active operation messages must still be preserved by the
    countdown timer (regression check).
    """
    win = _build_window(qtbot)
    status_bar = win.statusBar()

    for test_msg in [
        "Checking for data updates...",
        "Updating candle data (15m + 1h) in background...",
        "Added block: RSI(14) (3 blocks total)",
        "Strategy updated - 5 block(s) configured",
        "Saved strategy successfully",
        "Validating strategy...",
    ]:
        win._update_status(test_msg)
        QApplication.processEvents()

        win._update_countdown_status()
        QApplication.processEvents()

        msg = status_bar.currentMessage()
        assert msg == test_msg or msg.startswith(test_msg[:10]), (
            f"Active message '{test_msg}' was overwritten by countdown. "
            f"Got: '{msg}'"
        )
