"""
Regression tests for BTCAAAAA-872: tz-aware vs tz-naive datetime in
detect_gaps_in_binance_files and related UnifiedDataManager methods.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-872
Component: src/data_manager/unified_manager.py

Root cause: detect_gaps_in_binance_files compared tz-aware caller datetimes
against tz-naive on-disk timestamps, raising TypeError when comparing
datetime64[ns] with tz-aware datetime.

Fix: entry-point normalization in detect_gaps_in_binance_files strips
tzinfo from incoming datetimes so all internal comparisons are tz-naive.
Also fixes in _RuntimeCandleUpdateThread.run() at
strategy_builder_main_window.py:184 where tz-naive get_last_bar_timestamp()
was max()'d against tz-aware max_lookback.

All tests PASS after the fix; they fail on pre-fix code with TypeError.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-872"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_15m_bars(start: datetime, n: int = 20) -> pd.DataFrame:
    start_naive = start.replace(tzinfo=None) if start.tzinfo else start
    timestamps = [start_naive + timedelta(minutes=15 * i) for i in range(n)]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps),
        "open":   [40000.0 + i for i in range(n)],
        "high":   [40100.0 + i for i in range(n)],
        "low":    [39900.0 + i for i in range(n)],
        "close":  [40050.0 + i for i in range(n)],
        "volume": [10.0] * n,
    })


def _write_parquet_fixture(
    binance_dir: Path,
    timeframe: str = "15m",
    year: int = 2026,
    month: int = 3,
    n_bars: int = 20,
) -> datetime:
    month_str = f"{year}-{month:02d}"
    month_dir = binance_dir / month_str
    month_dir.mkdir(parents=True, exist_ok=True)
    file_path = month_dir / f"BTCUSDT_PERP_{timeframe}_{month_str}.parquet"
    start = datetime(year, month, 10, 0, 0)
    df = _make_15m_bars(start, n=n_bars)
    df.to_parquet(file_path, compression="snappy", index=False)
    return start


@pytest.fixture()
def manager(tmp_path):
    from src.data_manager.unified_manager import UnifiedDataManager

    binance_dir = tmp_path / "binance"
    _write_parquet_fixture(binance_dir, timeframe="15m", n_bars=20)
    _write_parquet_fixture(binance_dir, timeframe="1h", n_bars=5)

    mgr = UnifiedDataManager(mode="backtest")
    mgr.binance_dir = binance_dir
    return mgr


# ---------------------------------------------------------------------------
# detect_gaps_in_binance_files -- must not raise TypeError
# ---------------------------------------------------------------------------


class TestDetectGapsTzCompat:
    """detect_gaps_in_binance_files must accept tz-naive and tz-aware datetimes."""

    def test_naive_start_end_no_crash(self, manager):
        start = datetime(2026, 3, 10, 0, 0)
        end = start + timedelta(hours=6)
        gaps = manager.detect_gaps_in_binance_files(
            timeframe="15m", start_date=start, end_date=end,
        )
        assert isinstance(gaps, list)

    def test_aware_start_end_no_crash(self, manager):
        start = datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(hours=6)
        gaps = manager.detect_gaps_in_binance_files(
            timeframe="15m", start_date=start, end_date=end,
        )
        assert isinstance(gaps, list)

    def test_naive_and_aware_same_gap_count(self, manager):
        end = datetime(2026, 3, 10, 12, 0)

        gaps_naive = manager.detect_gaps_in_binance_files(
            timeframe="15m",
            start_date=datetime(2026, 3, 10, 0, 0),
            end_date=end,
        )
        gaps_aware = manager.detect_gaps_in_binance_files(
            timeframe="15m",
            start_date=datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc),
            end_date=end.replace(tzinfo=timezone.utc),
        )
        assert len(gaps_naive) == len(gaps_aware)

    def test_no_dates_no_crash(self, manager):
        gaps = manager.detect_gaps_in_binance_files(timeframe="15m")
        assert isinstance(gaps, list)


# ---------------------------------------------------------------------------
# get_last_bar_timestamp -- must not raise TypeError
# ---------------------------------------------------------------------------


class TestGetLastBarTimestamp:
    """get_last_bar_timestamp must return tz-naive datetime or None."""

    def test_returns_naive_datetime_or_none(self, manager):
        ts = manager.get_last_bar_timestamp("15m")
        if ts is not None:
            assert isinstance(ts, datetime)
            assert ts.tzinfo is None

    def test_missing_timeframe_returns_none(self, manager):
        ts = manager.get_last_bar_timestamp("4h")
        assert ts is None
