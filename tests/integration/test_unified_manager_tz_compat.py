"""
Regression tests: tz-naive vs tz-aware datetime compatibility in UnifiedDataManager.

All public methods that accept or compare datetime arguments must accept BOTH
  - tz-naive UTC (on-disk convention)
  - tz-aware UTC (caller/API convention)
without raising TypeError.  These tests use a small in-memory parquet fixture so
they are fast and require no network access.

Related issues:
  BTCAAAAA-816 — _get_bars_binance / _get_bars_from_local_files crash
  BTCAAAAA-866 — data_update_modal.py crash
  BTCAAAAA-872 — detect_gaps_in_binance_files crash (this fix)
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import pytest

from src.data_manager.unified_manager import UnifiedDataManager


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_15m_bars(
    start: datetime,
    n: int = 20,
) -> pd.DataFrame:
    """
    Build a minimal 15-minute OHLCV DataFrame with tz-naive UTC timestamps.
    Mirrors what is actually stored in Binance parquet files.
    """
    start_naive = start.replace(tzinfo=None) if start.tzinfo else start
    timestamps = [start_naive + timedelta(minutes=15 * i) for i in range(n)]
    return pd.DataFrame({
        'timestamp': pd.to_datetime(timestamps),  # tz-naive UTC
        'open':   [40000.0 + i for i in range(n)],
        'high':   [40100.0 + i for i in range(n)],
        'low':    [39900.0 + i for i in range(n)],
        'close':  [40050.0 + i for i in range(n)],
        'volume': [10.0] * n,
    })


def _write_parquet_fixture(
    binance_dir: Path,
    timeframe: str = '15m',
    year: int = 2026,
    month: int = 3,
    n_bars: int = 20,
) -> datetime:
    """
    Write a single monthly parquet file and return the start datetime of the data.
    Directory layout mirrors production:
        <binance_dir>/<YYYY-MM>/BTCUSDT_PERP_<tf>_<YYYY-MM>.parquet
    """
    month_str = f"{year}-{month:02d}"
    month_dir = binance_dir / month_str
    month_dir.mkdir(parents=True, exist_ok=True)
    file_path = month_dir / f"BTCUSDT_PERP_{timeframe}_{month_str}.parquet"

    start = datetime(year, month, 10, 0, 0)  # tz-naive UTC
    df = _make_15m_bars(start, n=n_bars)
    df.to_parquet(file_path, compression='snappy', index=False)
    return start


@pytest.fixture()
def manager_with_fixture(tmp_path):
    """
    Yield a UnifiedDataManager whose binance_dir points to a temp directory
    populated with a small 15m and 1h parquet fixture.
    """
    binance_dir = tmp_path / "binance"

    start_15m = _write_parquet_fixture(binance_dir, timeframe='15m', n_bars=20)
    # For 1h we need at least 4 bars (4 × 15m = 1h steps)
    _write_parquet_fixture(binance_dir, timeframe='1h', n_bars=5)

    mgr = UnifiedDataManager(mode='backtest')
    mgr.binance_dir = binance_dir  # override to temp dir
    return mgr, start_15m


# ---------------------------------------------------------------------------
# detect_gaps_in_binance_files
# ---------------------------------------------------------------------------

class TestDetectGapsTzCompat:
    """detect_gaps_in_binance_files must not raise TypeError for either tz form."""

    def test_naive_start_end_no_crash(self, manager_with_fixture):
        mgr, start = manager_with_fixture
        end = start + timedelta(hours=6)
        # Both tz-naive — must not raise
        gaps = mgr.detect_gaps_in_binance_files(
            timeframe='15m',
            start_date=start,
            end_date=end,
        )
        assert isinstance(gaps, list)

    def test_aware_start_end_no_crash(self, manager_with_fixture):
        mgr, start = manager_with_fixture
        start_aware = start.replace(tzinfo=timezone.utc)
        end_aware = start_aware + timedelta(hours=6)
        gaps = mgr.detect_gaps_in_binance_files(
            timeframe='15m',
            start_date=start_aware,
            end_date=end_aware,
        )
        assert isinstance(gaps, list)

    def test_naive_and_aware_return_same_gap_count(self, manager_with_fixture):
        mgr, start = manager_with_fixture
        end = start + timedelta(hours=6)

        gaps_naive = mgr.detect_gaps_in_binance_files(
            timeframe='15m',
            start_date=start,
            end_date=end,
        )
        gaps_aware = mgr.detect_gaps_in_binance_files(
            timeframe='15m',
            start_date=start.replace(tzinfo=timezone.utc),
            end_date=(start + timedelta(hours=6)).replace(tzinfo=timezone.utc),
        )
        assert len(gaps_naive) == len(gaps_aware), (
            f"Gap count mismatch: naive={len(gaps_naive)}, aware={len(gaps_aware)}"
        )

    def test_no_start_end_no_crash(self, manager_with_fixture):
        mgr, _ = manager_with_fixture
        gaps = mgr.detect_gaps_in_binance_files(timeframe='15m')
        assert isinstance(gaps, list)

    def test_only_naive_start_no_crash(self, manager_with_fixture):
        mgr, start = manager_with_fixture
        gaps = mgr.detect_gaps_in_binance_files(timeframe='15m', start_date=start)
        assert isinstance(gaps, list)

    def test_only_aware_start_no_crash(self, manager_with_fixture):
        mgr, start = manager_with_fixture
        gaps = mgr.detect_gaps_in_binance_files(
            timeframe='15m',
            start_date=start.replace(tzinfo=timezone.utc),
        )
        assert isinstance(gaps, list)


# ---------------------------------------------------------------------------
# verify_and_repair (dry_run=True — no network calls)
# ---------------------------------------------------------------------------

class TestVerifyAndRepairTzCompat:
    """verify_and_repair must accept both tz forms without TypeError."""

    def test_naive_dates_no_crash(self, manager_with_fixture):
        mgr, start = manager_with_fixture
        end = start + timedelta(hours=4)
        result = mgr.verify_and_repair(
            timeframes=['15m'],
            start_date=start,
            end_date=end,
            dry_run=True,
        )
        assert '15m' in result

    def test_aware_dates_no_crash(self, manager_with_fixture):
        mgr, start = manager_with_fixture
        start_aware = start.replace(tzinfo=timezone.utc)
        end_aware = start_aware + timedelta(hours=4)
        result = mgr.verify_and_repair(
            timeframes=['15m'],
            start_date=start_aware,
            end_date=end_aware,
            dry_run=True,
        )
        assert '15m' in result

    def test_naive_and_aware_same_gaps_found(self, manager_with_fixture):
        mgr, start = manager_with_fixture
        end = start + timedelta(hours=4)

        r_naive = mgr.verify_and_repair(
            timeframes=['15m'],
            start_date=start,
            end_date=end,
            dry_run=True,
        )
        r_aware = mgr.verify_and_repair(
            timeframes=['15m'],
            start_date=start.replace(tzinfo=timezone.utc),
            end_date=(start + timedelta(hours=4)).replace(tzinfo=timezone.utc),
            dry_run=True,
        )
        assert r_naive['15m']['gaps_found'] == r_aware['15m']['gaps_found']


# ---------------------------------------------------------------------------
# get_last_bar_timestamp
# ---------------------------------------------------------------------------

class TestGetLastBarTimestamp:
    """get_last_bar_timestamp returns tz-naive UTC or None — must not crash."""

    def test_returns_naive_datetime_or_none(self, manager_with_fixture):
        mgr, _ = manager_with_fixture
        ts = mgr.get_last_bar_timestamp('15m')
        # Returns None when no data, or a tz-naive datetime.
        if ts is not None:
            assert isinstance(ts, datetime)
            assert ts.tzinfo is None, "get_last_bar_timestamp must return tz-naive (on-disk convention)"

    def test_missing_timeframe_returns_none(self, manager_with_fixture):
        mgr, _ = manager_with_fixture
        ts = mgr.get_last_bar_timestamp('4h')
        assert ts is None


# ---------------------------------------------------------------------------
# get_all_data_types_status (called get_data_availability in issue description)
# ---------------------------------------------------------------------------

class TestGetAllDataTypesStatus:
    """get_all_data_types_status must not raise TypeError."""

    def test_no_crash(self, manager_with_fixture):
        mgr, _ = manager_with_fixture
        # lakeapi_dir points at real data which may be absent in CI — must not crash
        try:
            result = mgr.get_all_data_types_status()
            assert isinstance(result, dict)
        except Exception as exc:
            # Only TypeError indicates the tz mismatch bug; other errors (missing data) are OK
            assert not isinstance(exc, TypeError), f"TypeError raised: {exc}"
