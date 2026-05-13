"""
Regression tests for BTCAAAAA-66: Add 1d Binance kline download to active data pipeline.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-66
Fixed in commit: e23ae52b

Root cause: The 1d (daily) timeframe was never fetched by any active code path.
Zero 1d parquet files existed. Every active download path hardcoded 15m and 1h only.

Changes:
  1. DataUpdateThread.run() — add 1d download/save block after the 1h block
  2. _download_with_retry() — per-timeframe acceptable_delay (1d = 1500 min)
  3. BinanceRestClient.get_klines() — _stale_thresholds dict replacing flat 20-min
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-66"),
    pytest.mark.regression,
]


def _make_1d_bars(latest: datetime, n: int = 10) -> pd.DataFrame:
    timestamps = [latest - timedelta(days=i) for i in range(n - 1, -1, -1)]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "open": 60000.0,
        "high": 61000.0,
        "low": 59000.0,
        "close": 60500.0,
        "volume": 100.0,
    })


class TestDownloadWithRetry1dThreshold:
    """_download_with_retry must use a 1d-friendly staleness threshold."""

    def test_1d_threshold_exists_in_source(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "acceptable_delay = 1500" in source, (
            "1d staleness threshold must be 1500 min"
        )

    def test_1d_threshold_greater_than_1h(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        import re
        thresholds = re.findall(r"acceptable_delay\s*=\s*(\d+)", source)
        thresholds_int = [int(t) for t in thresholds]
        assert len(thresholds_int) >= 3
        daily = max(thresholds_int)
        hourly = min(t for t in thresholds_int if t > 30)
        assert daily > hourly, "1d threshold must exceed 1h threshold"

    def test_1d_branch_uses_else(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "else:  # 1d and others" in source, (
            "1d timeframe must fall through to else branch"
        )


class TestStaleThresholdsDict:
    """BinanceRestClient.get_klines must use per-interval stale thresholds."""

    def test_stale_thresholds_dict_exists_in_source(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "data_manager"
            / "binance"
            / "rest_client.py"
        ).read_text()
        assert "_stale_thresholds" in source, (
            "_stale_thresholds dict must exist in BinanceRestClient"
        )

    def test_stale_thresholds_contains_1d(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "data_manager"
            / "binance"
            / "rest_client.py"
        ).read_text()
        assert '"1d": 1500' in source or "'1d': 1500" in source, (
            "_stale_thresholds must include 1d with threshold 1500"
        )

    def test_stale_thresholds_contains_all_intervals(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "data_manager"
            / "binance"
            / "rest_client.py"
        ).read_text()
        for interval in ("1m", "5m", "15m", "1h", "4h", "1d"):
            assert interval in source, (
                f"_stale_thresholds must contain interval {interval}"
            )


class TestDataUpdateThreadRunHas1d:
    """DataUpdateThread.run() must download and save 1d bars."""

    def test_1d_download_block_exists(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "Downloading 1d bars from Binance" in source, (
            "1d download block must exist in DataUpdateThread.run()"
        )

    def test_1d_save_block_exists(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "Saving 1d bars to disk" in source, (
            "1d save block must exist after 1d download"
        )

    def test_success_message_includes_1d(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "1d bars:" in source, (
            "Success message must include 1d bar count"
        )


class Test1dAcceptance:
    """End-to-end behavioral: 1d bars pass freshness checks."""

    def test_fresh_1d_bar_900_min_old_does_not_raise(self):
        from unittest.mock import patch

        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        now = datetime.now(timezone.utc)
        dt = now - timedelta(minutes=900)
        df = _make_1d_bars(dt)

        thread = DataUpdateThread(
            start_date=now - timedelta(days=7),
            end_date=now,
        )

        def mock_get_bars(*args, **kwargs):
            return df

        with patch.object(thread.manager, "get_bars", mock_get_bars):
            result = thread._download_with_retry(
                timeframe="1d",
                start_date=now - timedelta(days=7),
                end_date=now,
            )
        assert len(result) >= 1, (
            "A 900-min-old 1d bar must be returned (not stale)"
        )

    def test_1d_stale_threshold_gte_1440_in_source(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "data_manager"
            / "binance"
            / "rest_client.py"
        ).read_text()
        assert '"1d": 1500' in source or "'1d': 1500" in source, (
            "rest_client.py _stale_thresholds must define 1d >= 1400"
        )

    def test_stale_threshold_logic_guards_1d(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "data_manager"
            / "binance"
            / "rest_client.py"
        ).read_text()
        assert "stale_threshold = _stale_thresholds.get(interval, 20)" in source, (
            "get_klines must use _stale_thresholds.get() with 20 fallback"
        )
