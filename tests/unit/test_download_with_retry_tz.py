"""
Regression tests: DataUpdateThread._download_with_retry — tz-aware timestamp fix.

Guards against BTCAAAAA-866 / BTCAAAAA-867:
  After BTCAAAAA-816, bars['timestamp'] is tz-aware UTC.
  Pre-fix code used datetime.utcnow() (tz-naive) vs tz-aware Timestamp → TypeError.
  Fix (BTCAAAAA-866): datetime.now(timezone.utc) for tz-consistent arithmetic.

These tests FAIL against pre-fix code and PASS with the fix applied.
No real Binance API calls — all network I/O is mocked.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tz_aware_bars(n: int, timeframe: str, delay_minutes: float) -> pd.DataFrame:
    """Return a DataFrame with tz-aware UTC timestamps, latest bar `delay_minutes` old."""
    now_utc = datetime.now(timezone.utc)
    latest = now_utc - timedelta(minutes=delay_minutes)

    freq_map = {"15m": timedelta(minutes=15), "1h": timedelta(hours=1), "1d": timedelta(days=1)}
    freq = freq_map.get(timeframe, timedelta(minutes=15))

    timestamps = [latest - freq * i for i in range(n - 1, -1, -1)]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "open":   [50000.0] * n,
        "high":   [51000.0] * n,
        "low":    [49000.0] * n,
        "close":  [50500.0] * n,
        "volume": [100.0] * n,
    })


@pytest.fixture()
def thread():
    """DataUpdateThread with mocked manager and signals — no live network."""
    from src.strategy_builder.ui.data_update_modal import DataUpdateThread  # noqa: PLC0415

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end   = datetime(2026, 5, 9, tzinfo=timezone.utc)
    with patch("src.strategy_builder.ui.data_update_modal.UnifiedDataManager"):
        t = DataUpdateThread(start_date=start, end_date=end)
    t.manager = MagicMock()
    return t


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDownloadWithRetryTzAware:
    """Regression guard for BTCAAAAA-866: tz-aware freshness check in _download_with_retry."""

    def test_fresh_tz_aware_no_type_error(self, thread):
        """Tz-aware timestamp must not raise TypeError in the freshness check.

        Pre-fix: datetime.utcnow() - tz-aware Timestamp → TypeError.
        Post-fix: datetime.now(timezone.utc) - tz-aware Timestamp → no error.
        """
        thread.manager.get_bars.return_value = _make_tz_aware_bars(10, "15m", 5)

        # Raises TypeError on pre-fix code; returns normally on post-fix code.
        result = thread._download_with_retry("15m", datetime(2026, 1, 1), datetime(2026, 5, 9))

        assert result is not None

    def test_fresh_response_returned_so_save_can_proceed(self, thread):
        """Fresh tz-aware response: function returns the DataFrame so _save_binance_bars can proceed."""
        fresh = _make_tz_aware_bars(10, "15m", 5)
        thread.manager.get_bars.return_value = fresh

        result = thread._download_with_retry("15m", datetime(2026, 1, 1), datetime(2026, 5, 9))

        assert len(result) == 10
        pd.testing.assert_frame_equal(result, fresh)

    def test_stale_tz_aware_triggers_retry_not_type_error(self, thread):
        """Stale tz-aware timestamp triggers retry loop, NOT a TypeError.

        Pre-fix: TypeError prevents entering the retry path at all.
        Post-fix: staleness is computed correctly → retries fire → stale bars
        returned after all attempts exhausted.
        """
        stale = _make_tz_aware_bars(10, "15m", 60)  # 60-min delay > 20-min threshold
        thread.manager.get_bars.return_value = stale

        with patch("time.sleep"):  # skip real delays
            result = thread._download_with_retry("15m", datetime(2026, 1, 1), datetime(2026, 5, 9))

        assert result is not None
        # Initial attempt + max_retries retries all consumed
        assert thread.manager.get_bars.call_count == thread.max_retries + 1

    def test_retry_resolves_to_fresh_on_second_attempt(self, thread):
        """First call returns stale; second call returns fresh — retry succeeds."""
        stale = _make_tz_aware_bars(10, "15m", 60)
        fresh = _make_tz_aware_bars(15, "15m", 5)
        thread.manager.get_bars.side_effect = [stale, fresh]

        with patch("time.sleep"):
            result = thread._download_with_retry("15m", datetime(2026, 1, 1), datetime(2026, 5, 9))

        assert len(result) == 15
        assert thread.manager.get_bars.call_count == 2

    def test_1h_timeframe_tz_aware_no_type_error(self, thread):
        """1h timeframe: same freshness-check fix path, same regression guard."""
        thread.manager.get_bars.return_value = _make_tz_aware_bars(24, "1h", 30)

        result = thread._download_with_retry("1h", datetime(2026, 1, 1), datetime(2026, 5, 9))

        assert result is not None
        assert len(result) == 24

    def test_1d_timeframe_tz_aware_no_type_error(self, thread):
        """1d timeframe: same freshness-check fix path, same regression guard."""
        thread.manager.get_bars.return_value = _make_tz_aware_bars(7, "1d", 60)

        result = thread._download_with_retry("1d", datetime(2026, 1, 1), datetime(2026, 5, 9))

        assert result is not None
        assert len(result) == 7
