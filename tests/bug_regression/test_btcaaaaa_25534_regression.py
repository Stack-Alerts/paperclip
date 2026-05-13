"""
Regression tests for BTCAAAAA-25534: Floor _get_bars_binance start_ms for
coarse timeframes (1d/4h/1h).

Issue: BTCAAAAA-25534
Components:
  - src/data_manager/unified_manager.py: _get_bars_binance()
  - src/strategy_builder/ui/data_update_modal.py: _start_update()

Fixes:
  1. Floor start_ms to the timeframe boundary before the Binance API call
     so that coarse bars (openTime >= startTime) are not excluded.
  2. Widen the query window to >=24h in data_update_modal so 1d bars get
     at least one closed candle.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25534"),
    pytest.mark.regression,
]


@pytest.fixture()
def manager(tmp_path):
    """Return a UnifiedDataManager wired to a fresh tmp_path."""
    from src.data_manager.unified_manager import UnifiedDataManager

    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


def _make_bar(ts: datetime, timeframe: str = "15m") -> pd.DataFrame:
    """Return a single-row kline DataFrame for the given timestamp."""
    return pd.DataFrame({
        "timestamp": pd.to_datetime([ts]),
        "open": [60000.0], "high": [61000.0], "low": [59000.0],
        "close": [60500.0], "volume": [10.0], "volume_usd": [600000.0],
        "trade_count": [100], "symbol": ["BTCUSDT"], "timeframe": [timeframe],
    })


class TestStartMsFlooredForCoarseTimeframes:
    """
    BTCAAAAA-25534 fix 1: _get_bars_binance must floor start_ms to the
    timeframe boundary for 1d/4h/1h before calling get_klines, so the
    coarse bar whose openTime is before a mid-bar start_ms is still returned.
    """

    def test_1d_mid_day_start_ms_floored_to_midnight(self, manager):
        """1d: start_date at 08:45 must floor start_ms to 00:00:00."""
        mid_day = datetime(2026, 5, 1, 8, 45, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 3, 0, 0, 0, tzinfo=timezone.utc)

        daily_bar = _make_bar(
            datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc), "1d"
        )
        mock_client = MagicMock()
        mock_client.get_klines.return_value = daily_bar

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("1d", mid_day, end)

        assert len(result) >= 1, (
            "1d bar must be returned even though start_date is at 08:45"
        )
        called_kwargs = mock_client.get_klines.call_args[1]
        expected_ms = int(
            datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000
        )
        assert called_kwargs["start_time"] == expected_ms

    def test_4h_mid_period_start_ms_floored(self, manager):
        """4h: start_date at 09:45 must floor to 08:00 (4h boundary)."""
        mid_period = datetime(2026, 5, 1, 9, 45, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 2, 0, 0, 0, tzinfo=timezone.utc)

        mock_client = MagicMock()
        mock_client.get_klines.return_value = _make_bar(
            datetime(2026, 5, 1, 8, 0, 0, tzinfo=timezone.utc), "4h"
        )

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("4h", mid_period, end)

        assert len(result) >= 1
        called_kwargs = mock_client.get_klines.call_args[1]
        expected_ms = int(
            datetime(2026, 5, 1, 8, 0, 0, tzinfo=timezone.utc).timestamp() * 1000
        )
        assert called_kwargs["start_time"] == expected_ms

    def test_1h_mid_hour_start_ms_floored(self, manager):
        """1h: start_date at 09:15 must floor to 09:00."""
        mid_hour = datetime(2026, 5, 1, 9, 15, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 1, 15, 0, 0, tzinfo=timezone.utc)

        mock_client = MagicMock()
        mock_client.get_klines.return_value = _make_bar(
            datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc), "1h"
        )

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("1h", mid_hour, end)

        assert len(result) >= 1
        called_kwargs = mock_client.get_klines.call_args[1]
        expected_ms = int(
            datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc).timestamp() * 1000
        )
        assert called_kwargs["start_time"] == expected_ms

    def test_15m_start_ms_not_floored(self, manager):
        """15m: start_ms must NOT be floored — fine-grained behaviour unchanged."""
        ts = datetime(2026, 5, 1, 9, 15, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 1, 10, 15, 0, tzinfo=timezone.utc)

        mock_client = MagicMock()
        mock_client.get_klines.return_value = _make_bar(ts)

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", ts, end)

        assert len(result) >= 1
        called_kwargs = mock_client.get_klines.call_args[1]
        expected_ms = int(ts.timestamp() * 1000)
        assert called_kwargs["start_time"] == expected_ms
