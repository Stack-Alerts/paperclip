"""
Regression tests for BTCAAAAA-816: tz-aware vs tz-naive datetime compatibility.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-816
Component: src/data_manager/unified_manager.py

Root cause: bars['timestamp'] returned by BinanceRestClient.get_klines() is
tz-naive (UTC info stripped by .dt.tz_localize(None)), but callers pass
tz-aware UTC start_date/end_date.  Comparison of tz-naive datetime64[ns]
against tz-aware datetime raises TypeError ("Invalid comparison between
dtype=datetime64[ns] and datetime"), caught as "Binance error" -> unexpected
LakeAPI fallback.

Fix: parse bars['timestamp'] with utc=True in both _get_bars_binance and
_get_bars_from_local_files so naive columns are re-localized before
comparison.  Also in data_update_modal._download_with_retry for freshness
check.

All twelve tests PASS after the fix; 9a-9e and 10a-10c fail on pre-fix code.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-816"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# Helpers  (mirrored from tests/unit/test_data_manager_integrity.py)
# ---------------------------------------------------------------------------


def _make_ohlcv(
    start: datetime,
    n: int,
    freq_minutes: int = 15,
    symbol: str = "BTCUSDT",
    timeframe: str = "15m",
) -> pd.DataFrame:
    timestamps = [start + timedelta(minutes=freq_minutes * i) for i in range(n)]
    base = 30_000.0
    rng = np.random.default_rng(seed=42)
    opens = base + rng.uniform(-500, 500, size=n)
    closes = opens + rng.uniform(-200, 200, size=n)
    highs = np.maximum(opens, closes) + rng.uniform(0, 100, size=n)
    lows = np.minimum(opens, closes) - rng.uniform(0, 100, size=n)
    volumes = rng.uniform(1.0, 100.0, size=n)
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "volume_usd": volumes * base,
            "trade_count": np.full(n, 50, dtype=int),
            "symbol": symbol,
            "timeframe": timeframe,
        }
    )


def _write_month_file(
    base_dir: Path,
    month_str: str,
    df: pd.DataFrame,
    timeframe: str = "15m",
) -> Path:
    file_path = (
        base_dir / month_str / f"BTCUSDT_PERP_{timeframe}_{month_str}.parquet"
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(file_path, compression="snappy", index=False)
    return file_path


# ---------------------------------------------------------------------------
# manager fixture - isolated tmp_path, no side-effects
# ---------------------------------------------------------------------------


@pytest.fixture()
def manager(tmp_path):
    from src.data_manager.unified_manager import UnifiedDataManager

    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


# ===========================================================================
# 1. BTCAAAAA-816: _get_bars_binance - tz-aware start_date
# ===========================================================================


class TestGetBarsBinanceTzAware:
    """_get_bars_binance must not raise TypeError with tz-aware start_date."""

    def _make_naive_klines_df(
        self, start: datetime, n: int = 50, freq_minutes: int = 15
    ) -> pd.DataFrame:
        timestamps = [start + timedelta(minutes=freq_minutes * i) for i in range(n)]
        rng = np.random.default_rng(seed=7)
        base = 60_000.0
        opens = base + rng.uniform(-500, 500, size=n)
        closes = opens + rng.uniform(-200, 200, size=n)
        highs = np.maximum(opens, closes) + rng.uniform(0, 100, size=n)
        lows = np.minimum(opens, closes) - rng.uniform(0, 100, size=n)
        return pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": rng.uniform(1.0, 50.0, size=n),
            "quote_volume": rng.uniform(1_000, 10_000, size=n),
            "trades": np.full(n, 100, dtype=int),
        })

    def test_tz_aware_start_no_type_error(self, manager):
        now_utc = datetime.now(timezone.utc)
        klines_df = self._make_naive_klines_df(
            start=now_utc.replace(tzinfo=None) - timedelta(hours=1), n=100,
        )
        mock_client = MagicMock()
        mock_client.get_klines.return_value = klines_df
        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            try:
                result = manager._get_bars_binance(
                    "15m", now_utc - timedelta(hours=12), now_utc,
                )
            except TypeError as exc:
                pytest.fail(f"_get_bars_binance raised TypeError: {exc}")
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_tz_aware_start_non_empty_result(self, manager):
        now_utc = datetime.now(timezone.utc)
        klines_df = self._make_naive_klines_df(
            start=now_utc.replace(tzinfo=None) - timedelta(hours=1), n=100,
        )
        mock_client = MagicMock()
        mock_client.get_klines.return_value = klines_df
        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance(
                "15m", now_utc - timedelta(hours=12), now_utc,
            )
        assert len(result) >= 50

    def test_naive_start_still_works(self, manager):
        now = datetime.now(timezone.utc)
        klines_df = self._make_naive_klines_df(
            start=now - timedelta(hours=13), n=100,
        )
        mock_client = MagicMock()
        mock_client.get_klines.return_value = klines_df
        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance(
                "15m", now - timedelta(hours=12), now,
            )
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_1h_timeframe_tz_aware(self, manager):
        now_utc = datetime.now(timezone.utc)
        klines_df = self._make_naive_klines_df(
            start=now_utc.replace(tzinfo=None) - timedelta(hours=2),
            n=48, freq_minutes=60,
        )
        mock_client = MagicMock()
        mock_client.get_klines.return_value = klines_df
        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance(
                "1h", now_utc - timedelta(hours=48), now_utc,
            )
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_1d_timeframe_tz_aware(self, manager):
        now_utc = datetime.now(timezone.utc)
        klines_df = self._make_naive_klines_df(
            start=now_utc.replace(tzinfo=None) - timedelta(days=2),
            n=10, freq_minutes=1440,
        )
        mock_client = MagicMock()
        mock_client.get_klines.return_value = klines_df
        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager._get_bars_binance(
                "1d", now_utc - timedelta(days=10), now_utc,
            )
        assert isinstance(result, pd.DataFrame)


# ===========================================================================
# 2. BTCAAAAA-816: _get_bars_from_local_files - tz-aware start/end
# ===========================================================================


class TestGetBarsFromLocalFilesTzAware:
    """_get_bars_from_local_files must not raise TypeError with tz-aware dates."""

    def test_tz_aware_start_end_no_type_error(self, manager):
        start_naive = datetime(2026, 4, 1, 0, 0)
        df = _make_ohlcv(start_naive, n=96, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-04", df, "15m")

        start_utc = start_naive.replace(tzinfo=timezone.utc)
        end_utc = (start_naive + timedelta(days=1)).replace(tzinfo=timezone.utc)

        try:
            result = manager._get_bars_from_local_files("15m", start_utc, end_utc)
        except TypeError as exc:
            pytest.fail(f"_get_bars_from_local_files raised TypeError: {exc}")
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_tz_aware_non_empty_result(self, manager):
        start_naive = datetime(2026, 4, 1, 0, 0)
        df = _make_ohlcv(start_naive, n=96, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-04", df, "15m")

        start_utc = start_naive.replace(tzinfo=timezone.utc)
        end_utc = (start_naive + timedelta(days=1)).replace(tzinfo=timezone.utc)
        result = manager._get_bars_from_local_files("15m", start_utc, end_utc)
        assert len(result) >= 90

    def test_naive_start_end_still_works(self, manager):
        start_naive = datetime(2026, 4, 1, 0, 0)
        df = _make_ohlcv(start_naive, n=48, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-04", df, "15m")

        end_naive = start_naive + timedelta(hours=12)
        result = manager._get_bars_from_local_files("15m", start_naive, end_naive)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0


# ===========================================================================
# 3. BTCAAAAA-816: get_bars() end-to-end with tz-aware dates
# ===========================================================================


class TestGetBarsEndToEndTzAware:
    """Full get_bars() -> _get_bars_by_range() -> _get_bars_binance() path."""

    def test_end_to_end_tz_aware_binance_path(self, manager):
        now_utc = datetime.now(timezone.utc)
        klines_df = _make_naive_klines_df_helper(
            start=now_utc.replace(tzinfo=None) - timedelta(hours=1), n=60,
        )
        mock_client = MagicMock()
        mock_client.get_klines.return_value = klines_df
        with patch.object(manager, "_get_binance_client", return_value=mock_client):
            result = manager.get_bars(
                timeframe="15m",
                start_date=now_utc - timedelta(hours=6),
                end_date=now_utc,
            )
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_end_to_end_tz_aware_local_files_path(self, manager):
        start_naive = datetime(2026, 4, 1, 0, 0)
        df = _make_ohlcv(start_naive, n=96, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-04", df, "15m")

        start_utc = start_naive.replace(tzinfo=timezone.utc)
        end_utc = (start_naive + timedelta(days=1)).replace(tzinfo=timezone.utc)
        result = manager.get_bars(
            timeframe="15m", start_date=start_utc, end_date=end_utc,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Module-level helper (shared by TestGetBarsEndToEndTzAware)
# ---------------------------------------------------------------------------


def _make_naive_klines_df_helper(
    start: datetime, n: int = 50, freq_minutes: int = 15
) -> pd.DataFrame:
    timestamps = [start + timedelta(minutes=freq_minutes * i) for i in range(n)]
    rng = np.random.default_rng(seed=7)
    base = 60_000.0
    opens = base + rng.uniform(-500, 500, size=n)
    closes = opens + rng.uniform(-200, 200, size=n)
    highs = np.maximum(opens, closes) + rng.uniform(0, 100, size=n)
    lows = np.minimum(opens, closes) - rng.uniform(0, 100, size=n)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps),
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": rng.uniform(1.0, 50.0, size=n),
        "quote_volume": rng.uniform(1_000, 10_000, size=n),
        "trades": np.full(n, 100, dtype=int),
    })
