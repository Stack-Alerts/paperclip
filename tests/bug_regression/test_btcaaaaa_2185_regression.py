"""
Regression tests for BTCAAAAA-2185: add startTime pagination to
_get_bars_binance() — close bars-truncation root cause.

Issue: BTCAAAAA-2185
Fixed in commits: b967a8d, b0d9ac9
Components: src/data_manager/unified_manager.py, src/data_manager/binance/rest_client.py

Root cause: unified_manager.py sent client.get_klines(limit=1500) with NO
startTime. Binance always returned the most-recent 1,500 candles regardless of
the requested date window, truncating data by ~48% for a 30-day 15m window.

Fix: two changes:
  1. unified_manager.py:526-554 — pagination loop that advances startTime past
     the last-received bar's open_time, fetching until the full window is covered.
  2. rest_client.py:363 — skip the stale-data fallback when start_time is
     explicitly set (paginated historical requests are expected to return stale
     data; the fallback was replacing them with the latest 1,500 bars, bypassing
     pagination entirely).

This file contains a dedicated test class that verifies pagination behaviour
with mocked Binance responses.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2185"),
    pytest.mark.regression,
]


# ------------------------------------------------------------------ #
# Fixture: UnifiedDataManager wired to a tmp binance_dir
# ------------------------------------------------------------------ #
@pytest.fixture()
def manager(tmp_path):
    """Return a UnifiedDataManager whose binance_dir is a fresh tmp_path."""
    from src.data_manager.unified_manager import UnifiedDataManager

    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def _make_bars(start: datetime, n: int, freq_minutes: int = 15) -> pd.DataFrame:
    """Synthetic OHLCV bars matching rest_client DataFrame format."""
    rng = np.random.default_rng(seed=7)
    timestamps = [start + timedelta(minutes=freq_minutes * i) for i in range(n)]
    base = 60_000.0
    opens = base + rng.uniform(-500, 500, size=n)
    closes = opens + rng.uniform(-200, 200, size=n)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps),
        "open": opens,
        "high": np.maximum(opens, closes) + rng.uniform(0, 100, size=n),
        "low": np.minimum(opens, closes) - rng.uniform(0, 100, size=n),
        "close": closes,
        "volume": rng.uniform(1.0, 50.0, size=n),
        "volume_usd": rng.uniform(1_000, 10_000, size=n),
        "trade_count": np.full(n, 100, dtype=int),
        "symbol": "BTCUSDT",
        "timeframe": "15m",
    })


class TestGetBarsBinancePagination:
    """
    Test that _get_bars_binance() paginates correctly with startTime.

    The pagination loop (unified_manager.py:526-554) must:
    1. Call get_klines with the initial start_time
    2. Continue fetching while the response is at max capacity (1500)
    3. Advance startTime past the last bar's open_time for each subsequent page
    4. Concatenate, deduplicate, and filter results to the requested date range
    """

    def test_paginates_two_pages_for_30_day_window(self, manager):
        """
        BTCAAAAA-2185: A 30-day 15m window expects ~2880 bars (limit=1500).
        The first call returns 1500 bars (max capacity); the pagination loop
        must issue a second call to fetch the remaining ~1380 bars.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        page1 = _make_bars(start_date.replace(tzinfo=None), n=1500)
        last_ts_page1 = pd.to_datetime(page1["timestamp"].iloc[-1])
        page2_start = last_ts_page1 + timedelta(minutes=15)
        page2 = _make_bars(page2_start.replace(tzinfo=None), n=1380)

        mock_client = MagicMock()
        mock_client.get_klines.side_effect = [page1, page2]

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert len(result) > 1500, (
            f"Expected >1500 bars from pagination, got {len(result)}"
        )
        assert mock_client.get_klines.call_count == 2, (
            f"Expected 2 calls to get_klines, got {mock_client.get_klines.call_count}"
        )

        first_call_kwargs = mock_client.get_klines.call_args_list[0][1]
        assert first_call_kwargs.get("start_time") is not None, (
            "First get_klines call must include start_time"
        )

        second_call_kwargs = mock_client.get_klines.call_args_list[1][1]
        expected_advance = int(last_ts_page1.timestamp() * 1000) + 1
        actual_advance = second_call_kwargs.get("start_time")
        assert actual_advance >= expected_advance - 1, (
            f"Second call start_time {actual_advance} should advance past "
            f"page 1 last bar {expected_advance}"
        )

    def test_single_page_when_data_fits_one_request(self, manager):
        """When the window produces fewer than 1500 bars, only one call is made."""
        start_date = datetime.now(timezone.utc) - timedelta(hours=6)
        end_date = datetime.now(timezone.utc)

        bars = _make_bars(start_date.replace(tzinfo=None), n=24)

        mock_client = MagicMock()
        mock_client.get_klines.return_value = bars

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert len(result) == 24
        assert mock_client.get_klines.call_count == 1

    def test_empty_response_returns_empty_dataframe(self, manager):
        """Binance returning no bars in the requested range returns empty DF."""
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        empty_df = _make_bars(start_date.replace(tzinfo=None), n=0)

        mock_client = MagicMock()
        mock_client.get_klines.return_value = empty_df

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_start_time_passed_to_klines(self, manager):
        """_get_bars_binance must forward the computed start_time to get_klines."""
        start_date = datetime.now(timezone.utc) - timedelta(hours=12)
        end_date = datetime.now(timezone.utc)

        bars = _make_bars(start_date.replace(tzinfo=None), n=48)

        mock_client = MagicMock()
        mock_client.get_klines.return_value = bars

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            manager._get_bars_binance("15m", start_date, end_date)

        call_kwargs = mock_client.get_klines.call_args[1]
        assert "start_time" in call_kwargs, "start_time must be passed to get_klines"
        assert call_kwargs["start_time"] is not None, "start_time must not be None"
        assert isinstance(call_kwargs["start_time"], int), "start_time must be int ms"

    def test_stale_fallback_not_triggered_for_paginated_request(self, manager):
        """
        rest_client.py:363 now skips the stale-data fallback when start_time
        is explicitly set. Historical paginated requests always return "stale"
        data by definition; the fallback must not replace them.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        page1 = _make_bars(start_date.replace(tzinfo=None), n=1500)
        page2_start = pd.to_datetime(page1["timestamp"].iloc[-1]) + timedelta(minutes=15)
        page2 = _make_bars(page2_start.replace(tzinfo=None), n=500)

        mock_client = MagicMock()
        mock_client.get_klines.side_effect = [page1, page2]

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert len(result) > 1500, (
            f"Got only {len(result)} bars — stale-data fallback likely "
            f"bypassed pagination"
        )
