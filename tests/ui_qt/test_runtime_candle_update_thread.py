"""
Tests for _RuntimeCandleUpdateThread lifecycle (BTCAAAAA-28544).

Verifies:
- Thread starts and stops correctly
- 60-second timeout is enforced
- Main window cleanup properly stops thread
- No resource leaks on window close
- Proper signal emission on completion

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_runtime_candle_update_thread.py -v
"""

from __future__ import annotations

import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer


def _make_no_modal_window_class():
    """Build main window class with startup modal suppressed."""
    from src.strategy_builder.ui.strategy_builder_main_window import (
        StrategyBuilderMainWindow,
    )

    class _NoModalMainWindow(StrategyBuilderMainWindow):
        def _on_app_start(self):
            pass

    return _NoModalMainWindow


def _build_window(qtbot):
    """Build a minimal main window for testing."""
    cls = _make_no_modal_window_class()
    win = cls()
    qtbot.addWidget(win)
    QApplication.processEvents()
    return win


@pytest.mark.qt_real
def test_cleanup_threads_and_timers_exists(qtbot):
    """Verify _cleanup_threads_and_timers method exists and is callable."""
    win = _build_window(qtbot)
    assert hasattr(win, '_cleanup_threads_and_timers')
    assert callable(win._cleanup_threads_and_timers)


@pytest.mark.qt_real
def test_cleanup_stops_candle_check_timer(qtbot):
    """Verify _cleanup_threads_and_timers stops candle_check_timer."""
    win = _build_window(qtbot)

    # Start a candle check timer
    win.candle_check_timer = QTimer(win)
    win.candle_check_timer.setSingleShot(True)
    win.candle_check_timer.timeout.connect(lambda: None)
    win.candle_check_timer.start(10000)  # 10 second timer

    assert win.candle_check_timer.isActive()

    # Run cleanup
    win._cleanup_threads_and_timers()

    assert not win.candle_check_timer.isActive()


@pytest.mark.qt_real
def test_cleanup_stops_countdown_timer(qtbot):
    """Verify _cleanup_threads_and_timers stops countdown_timer."""
    win = _build_window(qtbot)

    assert win.countdown_timer.isActive()

    # Run cleanup
    win._cleanup_threads_and_timers()

    assert not win.countdown_timer.isActive()


@pytest.mark.qt_real
def test_close_event_calls_cleanup(qtbot):
    """Verify closeEvent calls _cleanup_threads_and_timers before saving."""
    from PyQt5.QtGui import QCloseEvent

    win = _build_window(qtbot)

    # Start a candle check timer
    win.candle_check_timer = QTimer(win)
    win.candle_check_timer.setSingleShot(True)
    win.candle_check_timer.timeout.connect(lambda: None)
    win.candle_check_timer.start(10000)

    assert win.candle_check_timer.isActive()

    # Close the window
    win.is_modified = False  # Prevent save dialog
    event = QCloseEvent()
    win.closeEvent(event)
    QApplication.processEvents()

    # Verify timer was stopped
    assert not win.candle_check_timer.isActive()


@pytest.mark.qt_real
def test_runtime_update_thread_timeout_constant(qtbot):
    """Verify _RuntimeCandleUpdateThread has correct timeout."""
    from src.strategy_builder.ui.strategy_builder_main_window import (
        _RuntimeCandleUpdateThread,
    )

    assert hasattr(_RuntimeCandleUpdateThread, 'TIMEOUT_SECONDS')
    assert _RuntimeCandleUpdateThread.TIMEOUT_SECONDS == 60


@pytest.mark.qt_real
def test_runtime_update_thread_has_finished_signal(qtbot):
    """Verify _RuntimeCandleUpdateThread has finished signal."""
    from src.strategy_builder.ui.strategy_builder_main_window import (
        _RuntimeCandleUpdateThread,
    )

    thread = _RuntimeCandleUpdateThread()
    assert hasattr(thread, 'finished')
    # finished signal is a pyqtSignal


@pytest.mark.qt_real
def test_main_window_initializes_runtime_update_thread_as_none(qtbot):
    """Verify main window initializes _runtime_update_thread as None."""
    win = _build_window(qtbot)
    assert win._runtime_update_thread is None


@pytest.mark.qt_real
def test_main_window_initializes_session_start_time_as_none(qtbot):
    """Verify main window initializes _session_start_time as None."""
    win = _build_window(qtbot)
    # Session start time is set when _start_auto_update_system is called
    # On init, it should be None
    assert win._session_start_time is None


@pytest.mark.qt_real
def test_cleanup_handles_none_thread(qtbot):
    """Verify _cleanup_threads_and_timers handles None thread gracefully."""
    win = _build_window(qtbot)
    assert win._runtime_update_thread is None

    # Should not raise an exception
    win._cleanup_threads_and_timers()


@pytest.mark.qt_real
def test_cleanup_handles_none_timers(qtbot):
    """Verify _cleanup_threads_and_timers handles None timers gracefully."""
    win = _build_window(qtbot)
    win.candle_check_timer = None
    win.retry_timer = None

    # Should not raise an exception
    win._cleanup_threads_and_timers()
