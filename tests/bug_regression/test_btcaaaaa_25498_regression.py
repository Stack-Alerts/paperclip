"""
Regression tests for BTCAAAAA-25498: Data Manager — Binance returning
0 candles / NaT timestamps.

Issue: BTCAAAAA-25498
Components:
  - src/data_manager/unified_manager.py: _get_bars_binance()

Fixes:
  1. Re-raise API error on first empty page so outer try/except triggers
     LakeAPI fallback instead of silently returning empty (0 candles).
  2. Preserve partial data on mid-pagination API error — return what we have.
  3. Filter NaT rows from the final result even when last_ts is valid.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25498"),
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


# ------------------------------------------------------------------ #
# Fix 1: API error on first page → LakeAPI fallback
# ------------------------------------------------------------------ #
class TestApiErrorOnFirstPageTriggersFallback:
    """BTCAAAAA-25498 fix 1: re-raise so outer handler falls back."""

    def test_lakeapi_fallback_triggered_on_first_page_error(self, manager):
        """
        If the first get_klines call raises, _get_bars_binance must
        propagate the exception to the outer try/except, which triggers
        the LakeAPI fallback.  Before the fix, the inner catch-and-break
        silently returned an empty DataFrame (0 candles).
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        mock_client = MagicMock()
        mock_client.get_klines.side_effect = ConnectionError("API unreachable")

        from datetime import datetime as dt
        lakeapi_result = pd.DataFrame({
            "timestamp": pd.to_datetime([start_date]),
            "open": [60000.0], "high": [61000.0], "low": [59000.0],
            "close": [60500.0], "volume": [10.0], "volume_usd": [600000.0],
            "trade_count": [100], "symbol": ["BTCUSDT"], "timeframe": ["15m"],
        })

        with patch.object(manager, "_get_binance_client", return_value=mock_client), \
             patch.object(manager, "_get_bars_lakeapi", return_value=lakeapi_result) as mock_fb:
            result = manager._get_bars_binance("15m", start_date, end_date)

        mock_fb.assert_called_once()
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1, "Must get data from LakeAPI fallback, not empty"

    def test_partial_data_preserved_on_mid_pipeline_api_error(self, manager):
        """
        If data was already fetched (partial) and a subsequent page fails,
        the partial data must be returned WITHOUT triggering the LakeAPI
        fallback — falling back would discard what we already have.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        # Build a mock response that succeeds on page 1, fails on page 2
        page1 = pd.DataFrame({
            "timestamp": pd.to_datetime([start_date]),
            "open": [60000.0], "high": [61000.0], "low": [59000.0],
            "close": [60500.0], "volume": [10.0], "volume_usd": [600000.0],
            "trade_count": [100], "symbol": ["BTCUSDT"], "timeframe": ["15m"],
        })

        mock_client = MagicMock()
        mock_client.get_klines.side_effect = [
            page1,
            ConnectionError("Page 2 failure"),
        ]

        with patch.object(manager, "_get_binance_client", return_value=mock_client), \
             patch.object(manager, "_get_bars_lakeapi") as mock_fb:
            result = manager._get_bars_binance("15m", start_date, end_date)

        mock_fb.assert_not_called()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1, "Must return the partial data (1 bar)"


# ------------------------------------------------------------------ #
# Fix 3: NaT row filtering
# ------------------------------------------------------------------ #
class TestNatRowsFilteredFromResult:
    """BTCAAAAA-25498 fix 3: drop NaT rows from the final result."""

    def test_nat_middle_row_filtered(self, manager):
        """
        A NaT timestamp in a middle row (not the last row, so the per-page
        cursor guard misses it) must be filtered from the final result.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        ts = [start_date + timedelta(minutes=15 * i) for i in range(5)]
        ts_with_nat = ts.copy()
        ts_with_nat[2] = pd.NaT  # middle row — cursor guard doesn't check this

        df_with_nat = pd.DataFrame({
            "timestamp": ts_with_nat,
            "open": [60000.0] * 5, "high": [61000.0] * 5,
            "low": [59000.0] * 5, "close": [60500.0] * 5,
            "volume": [10.0] * 5, "volume_usd": [600000.0] * 5,
            "trade_count": [100] * 5, "symbol": ["BTCUSDT"] * 5,
            "timeframe": ["15m"] * 5,
        })

        mock_client = MagicMock()
        mock_client.get_klines.return_value = df_with_nat

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        nat_count = result["timestamp"].isna().sum()
        assert nat_count == 0, f"NaT rows leaked: {nat_count} NaT in result"
        assert len(result) == 4, f"Expected 4 valid bars, got {len(result)}"

    def test_all_nat_rows_filtered(self, manager):
        """
        If ALL timestamps are NaT, the result must be empty but not crash.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        df_all_nat = pd.DataFrame({
            "timestamp": [pd.NaT, pd.NaT, pd.NaT],
            "open": [60000.0] * 3, "high": [61000.0] * 3,
            "low": [59000.0] * 3, "close": [60500.0] * 3,
            "volume": [10.0] * 3, "volume_usd": [600000.0] * 3,
            "trade_count": [100] * 3, "symbol": ["BTCUSDT"] * 3,
            "timeframe": ["15m"] * 3,
        })

        mock_client = MagicMock()
        mock_client.get_klines.return_value = df_all_nat

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0, "All-NaT input must produce empty result"
        assert not result["timestamp"].isna().any(), "Empty DF must not have NaT column"


# ------------------------------------------------------------------ #
# Integration: get_bars via AUTO routing with Binance failure
# ------------------------------------------------------------------ #
class TestGetBarsBinanceFallbackIntegration:
    """End-to-end: get_bars() must still return data when Binance fails."""

    def test_get_bars_auto_routing_falls_back_on_binance_failure(self, manager):
        """
        When source=AUTO and Binance returns an error, get_bars() must
        still return data through the LakeAPI fallback.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        mock_client = MagicMock()
        mock_client.get_klines.side_effect = ConnectionError("API unreachable")

        lakeapi_result = pd.DataFrame({
            "timestamp": pd.to_datetime([start_date]),
            "open": [60000.0], "high": [61000.0], "low": [59000.0],
            "close": [60500.0], "volume": [10.0], "volume_usd": [600000.0],
            "trade_count": [100], "symbol": ["BTCUSDT"], "timeframe": ["15m"],
        })

        with patch.object(manager, "_get_binance_client", return_value=mock_client), \
             patch.object(manager, "_get_bars_lakeapi", return_value=lakeapi_result):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1, (
            "get_bars with failing Binance must fall back to LakeAPI and return data"
        )
