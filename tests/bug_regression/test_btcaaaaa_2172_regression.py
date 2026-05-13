"""
Regression tests for BTCAAAAA-2172: bars-loaded pipeline (30/30/30 -> 1,500 bars
regression) caused by missing startTime pagination in _get_bars_binance().

Issue: BTCAAAAA-2172
Fixed by: BTCAAAAA-2185 (commits b967a8d, b0d9ac9)
Components: src/data_manager/unified_manager.py

Root cause: unified_manager.py sent client.get_klines(limit=1500) with NO
startTime. Binance always returned the most-recent 1,500 candles regardless of
the requested date window, truncating data by ~48% for a 30-day 15m window.

Fix: pagination loop in _get_bars_binance() that advances startTime past the
last-received bar's open_time, fetching until the full window is covered.

This test validates the full bar-loading pipeline routing + pagination so that
a 30-day 15m window produces ~2880 bars (not 1500).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2172"),
    pytest.mark.regression,
]

from src.data_manager.unified_manager import DataSource


@pytest.fixture()
def manager(tmp_path):
    """Return a UnifiedDataManager with isolated temp directories."""
    from src.data_manager.unified_manager import UnifiedDataManager

    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


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


class TestRoutingDecision:
    """Verify _determine_source() routes date windows to the correct data source."""

    def test_recent_window_routes_to_binance(self, manager):
        """A 26-day window ending now should route to BINANCE (< 30 day threshold)."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=26)
        end = now
        source = manager._determine_source(start, end)
        from src.data_manager.unified_manager import DataSource
        assert source == DataSource.BINANCE, (
            f"Expected BINANCE for 26-day window, got {source}"
        )

    def test_historical_window_routes_to_lakeapi(self, manager):
        """A window fully outside the 30-day threshold routes to LAKEAPI."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=60)
        end = now - timedelta(days=35)
        source = manager._determine_source(start, end)
        from src.data_manager.unified_manager import DataSource
        assert source == DataSource.LAKEAPI, (
            f"Expected LAKEAPI for 60->35 day window, got {source}"
        )

    def test_spanning_window_routes_to_auto(self, manager):
        """A window spanning the 30-day threshold routes to AUTO (hybrid)."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=45)
        end = now
        source = manager._determine_source(start, end)
        from src.data_manager.unified_manager import DataSource
        assert source == DataSource.AUTO, (
            f"Expected AUTO for spanning window, got {source}"
        )

    def test_none_start_date_routes_to_binance(self, manager):
        """When start_date is None (recent data request), route to BINANCE."""
        source = manager._determine_source(None, datetime.now(timezone.utc))
        from src.data_manager.unified_manager import DataSource
        assert source == DataSource.BINANCE


class TestGetBarsBinancePagination:
    """Verify _get_bars_binance paginates correctly for large windows."""

    def test_30_day_window_returns_full_bar_count(self, manager):
        """BTCAAAAA-2172: A 30-day 15m window must not truncate at 1500 bars."""
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        page1 = _make_bars(start_date.replace(tzinfo=None), n=1500)
        last_ts = page1["timestamp"].iloc[-1]
        page2_start = last_ts + timedelta(minutes=15)
        page2 = _make_bars(page2_start.replace(tzinfo=None), n=1380)

        mock_client = MagicMock()
        mock_client.get_klines.side_effect = [page1, page2]

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            bars = manager._get_bars_binance("15m", start_date, end_date)

        assert len(bars) > 1500, (
            f"30-day window returned only {len(bars)} bars - regression of "
            f"BTCAAAAA-2172 (expected ~2880, got {len(bars)})"
        )
        assert mock_client.get_klines.call_count >= 2, (
            f"Expected >=2 calls for pagination, got {mock_client.get_klines.call_count}"
        )

    def test_small_window_no_pagination(self, manager):
        """A small window (<1500 bars) should make a single call."""
        start_date = datetime.now(timezone.utc) - timedelta(hours=6)
        end_date = datetime.now(timezone.utc)

        bars = _make_bars(start_date.replace(tzinfo=None), n=24)
        mock_client = MagicMock()
        mock_client.get_klines.return_value = bars

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert len(result) == 24
        assert mock_client.get_klines.call_count == 1

    def test_start_time_passed_to_klines(self, manager):
        """_get_bars_binance must forward a non-None start_time to get_klines."""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        bars = _make_bars(start_date.replace(tzinfo=None), n=100)
        mock_client = MagicMock()
        mock_client.get_klines.return_value = bars
        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            manager._get_bars_binance("15m", start_date, end_date)
        call_kwargs = mock_client.get_klines.call_args[1]
        assert "start_time" in call_kwargs, "start_time must be in kwargs"
        assert call_kwargs["start_time"] is not None, "start_time must not be None"
        assert isinstance(call_kwargs["start_time"], int), (
            "start_time must be int milliseconds"
        )


class TestGetBarsByRangeIntegration:
    """_get_bars_by_range with BINANCE source routes through pagination."""

    def test_get_bars_by_range_with_binance_paginates(self, manager):
        """_get_bars_by_range(..., BINANCE) should paginate for a 30-day window."""
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        page1 = _make_bars(start_date.replace(tzinfo=None), n=1500)
        pg2_start = page1["timestamp"].iloc[-1] + timedelta(minutes=15)
        page2 = _make_bars(pg2_start.replace(tzinfo=None), n=1380)

        mock_client = MagicMock()
        mock_client.get_klines.side_effect = [page1, page2]

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            bars = manager._get_bars_by_range(
                "15m", start_date, end_date, DataSource.BINANCE
            )

        assert len(bars) > 1500, (
            f"Expected >1500 bars via BINANCE route, got {len(bars)}"
        )


class TestReproScriptRouting:
    """Routing scenarios from the BTCAAAAA-2172 repro script."""

    def test_26_day_lookback_routes_to_binance(self, manager):
        """A 26-day lookback should be within the Binance threshold."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=26)
        source = manager._determine_source(start, now)
        assert source == DataSource.BINANCE, (
            f"26-day lookback should route BINANCE, got {source}"
        )

    def test_90_day_window_routes_to_auto_hybrid(self, manager):
        """90-day window should span the threshold and route to AUTO."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=90)
        source = manager._determine_source(start, now)
        assert source == DataSource.AUTO, (
            f"90-day window should route AUTO, got {source}"
        )
