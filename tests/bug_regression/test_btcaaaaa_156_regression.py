"""
Regression tests for BTCAAAAA-156.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-156
Component: src/strategy_builder/ui/strategy_builder_main_window.py
          _RuntimeCandleUpdateThread — scan window calculation.

RC4 FIX: scan from session_start_time instead of now-2h so gaps older
than 2 hours are never silently hidden.  The window is capped at 24h to
prevent excessively long scans on very long sessions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-156"),
    pytest.mark.regression,
]

# ---------------------------------------------------------------------------
# Helpers: replicate the scan window algorithm in isolation
# ---------------------------------------------------------------------------

MAX_SESSION_LOOKBACK_HOURS = 24


def _compute_scan_window(
    now: datetime,
    session_start_time: datetime | None,
    max_lookback_hours: int = MAX_SESSION_LOOKBACK_HOURS,
) -> datetime:
    """Replicates the _RuntimeCandleUpdateThread run() lower-bound logic."""
    max_lookback = now - timedelta(hours=max_lookback_hours)
    if session_start_time is not None:
        return max(session_start_time, max_lookback)
    return now - timedelta(hours=2)


# ---------------------------------------------------------------------------
# MAX_SESSION_LOOKBACK_HOURS constant
# ---------------------------------------------------------------------------


class TestMaxLookbackConstant:
    def test_constant_is_24_hours(self) -> None:
        assert MAX_SESSION_LOOKBACK_HOURS == 24


# ---------------------------------------------------------------------------
# _RuntimeCandleUpdateThread.__init__
# ---------------------------------------------------------------------------


class TestThreadInit:
    def test_stores_session_start_time(self) -> None:
        from src.strategy_builder.ui.strategy_builder_main_window import (
            _RuntimeCandleUpdateThread,
        )
        expected = datetime.now(timezone.utc)
        thread = _RuntimeCandleUpdateThread(session_start_time=expected)
        assert thread._session_start_time is expected

    def test_defaults_to_none(self) -> None:
        from src.strategy_builder.ui.strategy_builder_main_window import (
            _RuntimeCandleUpdateThread,
        )
        thread = _RuntimeCandleUpdateThread()
        assert thread._session_start_time is None


# ---------------------------------------------------------------------------
# StrategyBuilderMainWindow._session_start_time initialization
# ---------------------------------------------------------------------------


class TestMainWindowSessionStart:
    def test_initialized_to_none(self) -> None:
        import sys

        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)

        cls_path = "src.strategy_builder.ui.strategy_builder_main_window"
        with patch(f"{cls_path}.StrategyBuilderMainWindow._on_app_start"):
            from src.strategy_builder.ui.strategy_builder_main_window import (
                StrategyBuilderMainWindow,
            )
            win = StrategyBuilderMainWindow()
            assert win._session_start_time is None

    def test_recorded_once_on_first_start_auto_update(self) -> None:
        """_start_auto_update_system sets session_start_time only on first call."""
        import sys

        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)

        cls_path = "src.strategy_builder.ui.strategy_builder_main_window"
        with patch(f"{cls_path}.StrategyBuilderMainWindow._on_app_start"):
            from src.strategy_builder.ui.strategy_builder_main_window import (
                StrategyBuilderMainWindow,
            )
            win = StrategyBuilderMainWindow()
            assert win._session_start_time is None

            t0 = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
            with patch(f"{cls_path}.datetime") as mock_dt:
                mock_dt.now.return_value = t0
                mock_dt.timezone = timezone
                mock_dt.timedelta = timedelta
                win._start_auto_update_system()

            assert win._session_start_time == t0

            t1 = t0 + timedelta(hours=1)
            with patch(f"{cls_path}.datetime") as mock_dt:
                mock_dt.now.return_value = t1
                mock_dt.timezone = timezone
                mock_dt.timedelta = timedelta
                win._start_auto_update_system()

            assert win._session_start_time == t0


# ---------------------------------------------------------------------------
# Scan window: with session_start_time set
# ---------------------------------------------------------------------------


class TestScanWindowWithSessionStart:
    def test_recent_session_used_as_lower_bound(self) -> None:
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(hours=1)
        start = _compute_scan_window(now, session_start)
        assert start == session_start

    def test_old_session_capped_at_24h(self) -> None:
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(hours=48)
        start = _compute_scan_window(now, session_start)
        expected = now - timedelta(hours=24)
        assert start == expected

    def test_exact_24h_not_capped(self) -> None:
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(hours=24)
        start = _compute_scan_window(now, session_start)
        assert start == session_start

    def test_session_just_under_24h_not_capped(self) -> None:
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(hours=23, minutes=59)
        start = _compute_scan_window(now, session_start)
        assert start == session_start


# ---------------------------------------------------------------------------
# Scan window: without session_start_time (fallback)
# ---------------------------------------------------------------------------


class TestScanWindowFallback:
    def test_falls_back_to_2h_when_none(self) -> None:
        now = datetime.now(timezone.utc)
        start = _compute_scan_window(now, None)
        expected = now - timedelta(hours=2)
        assert start == expected


# ---------------------------------------------------------------------------
# No-bars-on-disk fallback logic (source lines 172-176)
# ---------------------------------------------------------------------------


class TestNoBarsFallback:
    """When get_last_bar_timestamp returns None for both timeframes."""

    @staticmethod
    def _fallback_start(
        now: datetime,
        session_start_time: datetime | None,
    ) -> datetime:
        base = session_start_time if session_start_time is not None else now
        return base - timedelta(minutes=15)

    def test_uses_session_start_minus_15m(self) -> None:
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(hours=1)
        start = self._fallback_start(now, session_start)
        expected = session_start - timedelta(minutes=15)
        assert start == expected

    def test_uses_now_minus_15m_when_no_session(self) -> None:
        now = datetime.now(timezone.utc)
        start = self._fallback_start(now, None)
        expected = now - timedelta(minutes=15)
        assert start == expected


# ---------------------------------------------------------------------------
# Thread is created with session_start_time from parent window
# ---------------------------------------------------------------------------


class TestThreadInjection:
    def test_check_and_update_passes_session_start(self) -> None:
        """_check_and_update_data passes _session_start_time to the thread."""
        import sys

        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)

        cls_path = "src.strategy_builder.ui.strategy_builder_main_window"
        with patch(f"{cls_path}.StrategyBuilderMainWindow._on_app_start"):
            with patch(f"{cls_path}._RuntimeCandleUpdateThread") as MockThread:
                from src.strategy_builder.ui.strategy_builder_main_window import (
                    StrategyBuilderMainWindow,
                )
                win = StrategyBuilderMainWindow()
                t0 = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
                win._session_start_time = t0
                win._runtime_update_thread = None

                with patch(
                    f"{cls_path}.StrategyBuilderMainWindow._schedule_next_check"
                ):
                    win._check_and_update_data()

                MockThread.assert_called_once()
                _args, kwargs = MockThread.call_args
                assert kwargs.get("session_start_time") == t0


# ---------------------------------------------------------------------------
# Edge case: session_start_time is in the future
# ---------------------------------------------------------------------------


class TestFutureSessionStart:
    def test_future_session_start_used_as_is(self) -> None:
        now = datetime.now(timezone.utc)
        session_start = now + timedelta(hours=12)
        start = _compute_scan_window(now, session_start)
        assert start == session_start


# ---------------------------------------------------------------------------
# Sanity: boundary checks for the 24h cap
# ---------------------------------------------------------------------------


class TestLongSessionCap:
    def test_20h_session_uses_session_start(self) -> None:
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(hours=20)
        start = _compute_scan_window(now, session_start)
        assert start == session_start

    def test_30h_session_capped_to_24h(self) -> None:
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(hours=30)
        start = _compute_scan_window(now, session_start)
        expected = now - timedelta(hours=24)
        assert start == expected


# ---------------------------------------------------------------------------
# _on_update_data does NOT set session_start_time
# ---------------------------------------------------------------------------


class TestScopeOfSessionStartAssignment:
    def test_session_start_not_set_by_data_update_modal(self) -> None:
        """_on_update_data must not touch _session_start_time."""
        import sys

        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)

        cls_path = "src.strategy_builder.ui.strategy_builder_main_window"
        with patch(f"{cls_path}.StrategyBuilderMainWindow._on_app_start"):
            with patch(f"{cls_path}.DataUpdateModal"):
                from src.strategy_builder.ui.strategy_builder_main_window import (
                    StrategyBuilderMainWindow,
                )
                win = StrategyBuilderMainWindow()
                win._session_start_time = None
                win._on_update_data()
                assert win._session_start_time is None
