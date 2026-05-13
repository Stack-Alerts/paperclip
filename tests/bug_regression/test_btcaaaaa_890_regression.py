"""
Regression tests for BTCAAAAA-890: tz-naive/aware datetime mismatches in data pipeline.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-890
Components: src/data_manager/unified_manager.py, src/strategy_builder/ui/data_update_modal.py

Root cause: Multiple tz-naive vs tz-aware datetime comparison paths causing TypeError.

Fixes:
  1. data_update_modal.py:206 — pd.to_datetime(bars['timestamp'].iloc[-1], utc=True)
     so latest_candle is tz-aware UTC, matching datetime.now(timezone.utc).
  2. unified_manager.py:1479-1480 — strip tz from existing parquet data before
     astype cast (not only from incoming group), avoiding mixed-tz concat.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-890"),
    pytest.mark.regression,
]


def _make_fresh_bars(
    latest: datetime, n: int = 10, timeframe: str = "15m"
) -> pd.DataFrame:
    freq = 15 if timeframe == "15m" else 60
    timestamps = [latest - timedelta(minutes=freq * i) for i in range(n - 1, -1, -1)]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "open": 60000.0,
        "high": 61000.0,
        "low": 59000.0,
        "close": 60500.0,
        "volume": 100.0,
    })


# ===========================================================================
# 1. data_update_modal freshness check (BTCAAAAA-890 fix #1)
# ===========================================================================


class TestDownloadWithRetryFreshnessTzAware:
    """_download_with_retry must compare tz-aware timestamps without TypeError."""

    def test_freshness_check_with_tz_aware_bars(self):
        from unittest.mock import patch

        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        now = datetime.now(timezone.utc)
        df = _make_fresh_bars(now - timedelta(minutes=5), n=5)

        thread = DataUpdateThread(
            start_date=now - timedelta(hours=1),
            end_date=now,
        )

        def mock_get_bars(*args, **kwargs):
            return df

        with patch.object(thread.manager, "get_bars", mock_get_bars):
            result = thread._download_with_retry(
                timeframe="15m",
                start_date=now - timedelta(hours=1),
                end_date=now,
            )
        assert len(result) >= 1

    def test_freshness_check_with_tz_naive_bars(self):
        from unittest.mock import patch

        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        now = datetime.now(timezone.utc)
        timestamps = [now - timedelta(minutes=15 * i) for i in range(4, -1, -1)]
        df_naive = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps),
            "open": 60000.0,
            "high": 61000.0,
            "low": 59000.0,
            "close": 60500.0,
            "volume": 100.0,
        })

        thread = DataUpdateThread(
            start_date=now - timedelta(hours=1),
            end_date=now,
        )

        with patch.object(thread.manager, "get_bars", return_value=df_naive):
            result = thread._download_with_retry(
                timeframe="15m",
                start_date=now - timedelta(hours=1),
                end_date=now,
            )
        assert len(result) >= 1

    def test_freshness_check_does_not_raise_type_error(self):
        from unittest.mock import patch

        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        now = datetime.now(timezone.utc)
        df = _make_fresh_bars(now - timedelta(minutes=5), n=5)

        thread = DataUpdateThread(
            start_date=now - timedelta(hours=1),
            end_date=now,
        )

        with patch.object(thread.manager, "get_bars", return_value=df):
            try:
                thread._download_with_retry(
                    timeframe="15m",
                    start_date=now - timedelta(hours=1),
                    end_date=now,
                )
            except TypeError as exc:
                pytest.fail(f"_download_with_retry raised TypeError: {exc}")

    def test_source_uses_utc_true_in_pd_to_datetime(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "utc=True" in source, (
            "data_update_modal.py must use pd.to_datetime(..., utc=True)"
        )


# ===========================================================================
# 2. unified_manager _save_binance_bars mixed tz handling (BTCAAAAA-890 fix #2)
# ===========================================================================


class TestSaveBinanceBarsMixedTz:
    """_save_binance_bars must handle mixed tz-aware/tz-naive data."""

    @pytest.fixture()
    def manager(self, tmp_path):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
        mgr.binance_dir = tmp_path / "binance"
        mgr.binance_dir.mkdir(parents=True, exist_ok=True)
        return mgr

    def test_tz_aware_existing_and_tz_naive_group(self, manager):
        now = datetime.now(timezone.utc)
        timestamps = [now - timedelta(minutes=15 * i) for i in range(4, -1, -1)]

        existing = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps[:3], utc=True),
            "open": [60000.0] * 3,
            "high": [61000.0] * 3,
            "low": [59000.0] * 3,
            "close": [60500.0] * 3,
            "volume": [100.0] * 3,
        })

        month_str = now.strftime("%Y-%m")
        month_dir = manager.binance_dir / month_str
        month_dir.mkdir(parents=True, exist_ok=True)
        file_path = month_dir / f"BTCUSDT_PERP_15m_{month_str}.parquet"
        existing.to_parquet(file_path, compression="snappy", index=False)

        incoming = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "open": [60000.0] * 5,
            "high": [61000.0] * 5,
            "low": [59000.0] * 5,
            "close": [60500.0] * 5,
            "volume": [100.0] * 5,
        })
        incoming["timestamp"] = incoming["timestamp"].dt.tz_localize(None)

        try:
            manager._save_binance_bars(incoming, "15m")
        except TypeError as exc:
            pytest.fail(f"_save_binance_bars raised TypeError with mixed tz: {exc}")

        reread = pd.read_parquet(file_path)
        assert len(reread) >= 3

    def test_tz_naive_existing_and_tz_aware_group(self, manager):
        now = datetime.now(timezone.utc)
        timestamps = [now - timedelta(minutes=15 * i) for i in range(4, -1, -1)]

        existing = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps[:3]),
            "open": [60000.0] * 3,
            "high": [61000.0] * 3,
            "low": [59000.0] * 3,
            "close": [60500.0] * 3,
            "volume": [100.0] * 3,
        })

        month_str = now.strftime("%Y-%m")
        month_dir = manager.binance_dir / month_str
        month_dir.mkdir(parents=True, exist_ok=True)
        file_path = month_dir / f"BTCUSDT_PERP_15m_{month_str}.parquet"
        existing.to_parquet(file_path, compression="snappy", index=False)

        incoming = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "open": [60000.0] * 5,
            "high": [61000.0] * 5,
            "low": [59000.0] * 5,
            "close": [60500.0] * 5,
            "volume": [100.0] * 5,
        })

        try:
            manager._save_binance_bars(incoming, "15m")
        except TypeError as exc:
            pytest.fail(f"_save_binance_bars raised TypeError with mixed tz: {exc}")

        reread = pd.read_parquet(file_path)
        assert len(reread) >= 3

    def test_source_strips_tz_from_both_sides_in_save(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "data_manager"
            / "unified_manager.py"
        ).read_text()
        assert "if existing['timestamp'].dt.tz is not None:" in source, (
            "unified_manager.py must strip tz from existing data before astype"
        )
        assert "existing['timestamp'] = existing['timestamp'].dt.tz_localize(None)" in source, (
            "unified_manager.py must tz_localize(None) on existing data"
        )
