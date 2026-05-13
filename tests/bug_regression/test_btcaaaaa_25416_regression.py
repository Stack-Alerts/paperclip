"""
Regression tests for BTCAAAAA-25416: Harden Binance pagination against
NaT timestamps and API error responses.

Issue: BTCAAAAA-25416
Components:
  - src/data_manager/unified_manager.py: _get_bars_binance(), _fetch_binance_range()
  - src/data_manager/binance/rest_client.py: get_klines()

Changes:
  1. _get_bars_binance: try/except around get_klines call in pagination loop
  2. _get_bars_binance: pd.isna() guard before advancing cursor past last_ts
  3. _fetch_binance_range: validate response is a list, detect dict error payload
  4. _fetch_binance_range: pd.isna() guard before cursor = last_ts + bar_td
  5. rest_client.get_klines: validate response is a list; return empty DF on error dict
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25416"),
    pytest.mark.regression,
]


# ------------------------------------------------------------------ #
# Fixture
# ------------------------------------------------------------------ #
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


# ------------------------------------------------------------------ #
# Tests: _get_bars_binance hardening
# ------------------------------------------------------------------ #
class TestGetBarsBinanceNatGuard:
    """
    BTCAAAAA-25416: _get_bars_binance must handle NaT timestamps and
    API errors in the pagination loop without crashing or infinite-looping.
    """

    def test_nat_timestamp_breaks_pagination_gracefully(self, manager):
        """
        If a chunk's last timestamp is NaT, the pagination loop must break
        instead of crashing on last_ts.timestamp() or infinite-looping.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        page1 = _make_bars(start_date.replace(tzinfo=None), n=1500)
        # Corrupt the last timestamp to NaT
        page1.loc[page1.index[-1], "timestamp"] = pd.NaT

        mock_client = MagicMock()
        mock_client.get_klines.return_value = page1

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        # Must return a DataFrame (possibly empty), never raise
        assert isinstance(result, pd.DataFrame)
        # The NaT bar should have been dropped by dedup — or the whole page
        # is dropped because the NaT-triggered break means we only have one page
        # with a NaT bar that likely gets filtered out
        assert not result["timestamp"].isna().any(), "NaT timestamp leaked into result"

    def test_api_error_in_pagination_loop_breaks_gracefully(self, manager):
        """
        If client.get_klines raises mid-pagination, the loop must break
        and return partial data (or empty) rather than propagating the exception.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        page1 = _make_bars(start_date.replace(tzinfo=None), n=1500)
        mock_client = MagicMock()
        mock_client.get_klines.side_effect = [
            page1,
            ConnectionError("Simulated network failure"),
        ]

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert isinstance(result, pd.DataFrame)
        # Should have at least page1 data
        assert len(result) >= 1400  # page1 minus edge filtering
        # Should have caught the error and not be empty
        assert mock_client.get_klines.call_count == 2

    def test_api_error_on_first_page_returns_empty(self, manager):
        """
        If the very first get_klines call fails (no data yet), must return
        empty DataFrame without raising.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc)

        mock_client = MagicMock()
        mock_client.get_klines.side_effect = TimeoutError("API timeout")

        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance("15m", start_date, end_date)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# ------------------------------------------------------------------ #
# Tests: _fetch_binance_range hardening
# ------------------------------------------------------------------ #
class TestFetchBinanceRangeHardening:
    """
    BTCAAAAA-25416: _fetch_binance_range must handle non-list API responses
    and NaT timestamps without crashing.
    """

    @staticmethod
    def _mock_response(json_data, status_code=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = json_data
        return mock_resp

    def test_error_dict_response_breaks_gracefully(self, manager):
        """
        When Binance returns a dict error payload (e.g. {"code": -1121, "msg": "..."})
        instead of a kline array, _fetch_binance_range must log the error and break.
        """
        start_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end_ts = start_ts + timedelta(hours=1)

        error_payload = {"code": -1121, "msg": "Invalid symbol"}

        with patch("requests.get", return_value=self._mock_response(error_payload)):
            result = manager._fetch_binance_range("15m", start_ts, end_ts)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_non_list_response_breaks_gracefully(self, manager):
        """
        If Binance returns a scalar or unexpected structure, must break
        without crashing.
        """
        start_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end_ts = start_ts + timedelta(hours=1)

        with patch("requests.get", return_value=self._mock_response({"unexpected": True})):
            result = manager._fetch_binance_range("15m", start_ts, end_ts)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_nat_timestamp_cursor_break(self, manager):
        """
        If a batch contains a NaT timestamp in the last row (e.g. from a malformed
        API response), the cursor advance must detect NaT and break the pagination
        loop instead of computing cursor = NaT + bar_td.
        """
        start_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end_ts = start_ts + timedelta(hours=2)

        # Build a valid response batch but with the last open_time = None/null
        # which produces NaT after pd.to_datetime
        raw_klines = [
            [1735689600000, "60000", "60100", "59900", "60050", "10.0",
             1735689600001, "600000", 100, "5.0", "5.0", "0"],
            [1735690500000, "60050", "60150", "59950", "60100", "15.0",
             1735690500001, "900000", 150, "7.5", "7.5", "0"],
            # Third row with NaN open_time → NaT timestamp
            [None, "60100", "60200", "60000", "60150", "20.0",
             1735691400001, "1200000", 200, "10.0", "10.0", "0"],
        ]

        with patch("requests.get", return_value=self._mock_response(raw_klines)):
            result = manager._fetch_binance_range("15m", start_ts, end_ts)

        assert isinstance(result, pd.DataFrame)
        # The valid rows should be returned; the NaT row may or may not survive
        # depending on how pd.to_datetime handles None values
        assert not result["timestamp"].isna().any(), "NaT leaked into output"


# ------------------------------------------------------------------ #
# Tests: rest_client.get_klines() hardening
# ------------------------------------------------------------------ #
class TestRestClientKlinesResponseValidation:
    """
    BTCAAAAA-25416: BinanceRestClient.get_klines() must validate that
    the API response is a list before constructing a DataFrame.
    """

    def _make_client(self):
        from src.data_manager.binance.rest_client import BinanceRestClient
        return BinanceRestClient()

    def test_error_dict_returns_empty_dataframe(self):
        """
        If Binance returns {"code": -1121, "msg": "Invalid symbol"} (a dict),
        get_klines must return an empty DataFrame instead of interpreting the
        dict keys as kline fields.
        """
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"code": -1121, "msg": "Invalid symbol"}

        with patch.object(client, "_request", return_value=mock_resp.json.return_value):
            result = client.get_klines("15m", symbol="INVALID", limit=10, futures=True)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_valid_list_returns_dataframe_normally(self):
        """
        Normal case: a list of klines still works.
        """
        client = self._make_client()
        raw_klines = [
            [1735689600000, "60000", "60100", "59900", "60050", "10.0",
             1735689600001, "600000", 100, "5.0", "5.0", "0"],
        ]

        with patch.object(client, "_request", return_value=raw_klines):
            # Use start_time so the stale-data fallback is not triggered
            result = client.get_klines(
                "15m", symbol="BTCUSDT", limit=10, futures=True,
                start_time=1735689600000,
            )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert "timestamp" in result.columns
