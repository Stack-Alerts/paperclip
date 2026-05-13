"""
Regression tests for BTCAAAAA-115: Trailing-edge gap detection in
detect_gaps_in_binance_files().

Issue: BTCAAAAA-115
Components: src/data_manager/unified_manager.py

Root cause: diff() only finds gaps between existing rows; when the last bar
on disk is stale relative to end_date the function returned 0 gaps even
though new closed candles exist. The trailing-edge check added in BTCAAAAA-115
catches that scenario.

This file contains standalone tests exercising the trailing-edge gap detection
logic in a tmp_path-isolated UnifiedDataManager.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-115"),
    pytest.mark.regression,
]


# --------------------------------------------------------------------------- #
# Helpers: synthetic OHLCV factories
# --------------------------------------------------------------------------- #


def _make_ohlcv(
    start: datetime,
    n: int,
    freq_minutes: int = 15,
    timeframe: str = "15m",
) -> pd.DataFrame:
    timestamps = [start + timedelta(minutes=freq_minutes * i) for i in range(n)]
    base = 30_000.0
    rng = np.random.default_rng(seed=42)
    opens = base + rng.uniform(-500, 500, size=n)
    closes = opens + rng.uniform(-200, 200, size=n)
    highs = np.maximum(opens, closes) + rng.uniform(0, 100, size=n)
    lows = np.minimum(opens, closes) - rng.uniform(0, 100, size=n)
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": rng.uniform(1.0, 100.0, size=n),
            "volume_usd": rng.uniform(1_000, 10_000, size=n),
            "trade_count": np.full(n, 50, dtype=int),
            "symbol": "BTCUSDT",
            "timeframe": timeframe,
        }
    )


def _write_month_file(
    base_dir: Path, month_str: str, df: pd.DataFrame, timeframe: str = "15m"
) -> Path:
    file_path = base_dir / month_str / f"BTCUSDT_PERP_{timeframe}_{month_str}.parquet"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(file_path, compression="snappy", index=False)
    return file_path


# --------------------------------------------------------------------------- #
# Fixture: UnifiedDataManager wired to a tmp binance_dir
# --------------------------------------------------------------------------- #


@pytest.fixture()
def manager(tmp_path):
    from src.data_manager.unified_manager import UnifiedDataManager

    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


# =========================================================================== #
# Trailing-edge gap detection (BTCAAAAA-115)
# =========================================================================== #


class TestTrailingEdgeGapDetection:
    """
    Tests for the trailing-edge check added to detect_gaps_in_binance_files().

    Root cause: diff() only finds gaps between existing rows; when the last bar
    on disk is stale relative to end_date the function returned 0 gaps even
    though new closed candles exist.  These tests verify the trailing-edge
    check catches that scenario (BUG-B fix).
    """

    # ------------------------------------------------------------------ #
    # 8a. Stale last bar triggers trailing-edge gap
    # ------------------------------------------------------------------ #
    def test_stale_last_bar_triggers_trailing_gap(self, manager):
        """Data on disk ends 30 minutes before end_date → ≥1 gap."""
        end_date = datetime(2026, 5, 4, 12, 0, 0)
        last_bar_ts = end_date - timedelta(minutes=30)
        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m", end_date=end_date)

        assert len(gaps) >= 1, f"Expected trailing gap, got {gaps}"
        trailing = gaps[-1]
        assert trailing["gap_start"] == df.iloc[-1]["timestamp"]
        assert trailing["missing_bars"] >= 1
        assert trailing["timeframe"] == "15m"

    # ------------------------------------------------------------------ #
    # 8b. Up-to-date data does NOT produce a false trailing-edge gap
    # ------------------------------------------------------------------ #
    def test_current_data_no_trailing_gap(self, manager):
        """Last bar within slop window → no trailing gap."""
        end_date = datetime(2026, 5, 4, 12, 13, 0)
        last_bar_ts = datetime(2026, 5, 4, 12, 0, 0)
        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m", end_date=end_date)

        assert len(gaps) == 0, f"Up-to-date data must not produce trailing gap; got {gaps}"

    # ------------------------------------------------------------------ #
    # 8c. verify_and_repair with trailing gap fetches and saves bars
    # ------------------------------------------------------------------ #
    def test_verify_and_repair_repairs_trailing_gap(self, manager):
        """verify_and_repair() must detect trailing gap and fetch/save bars."""
        end_date = datetime(2026, 5, 4, 12, 0, 0)
        last_bar_ts = end_date - timedelta(minutes=30)
        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        fetched_df = _make_ohlcv(
            last_bar_ts + timedelta(minutes=15), n=2, freq_minutes=15, timeframe="15m"
        )
        with patch.object(manager, "_fetch_binance_range", return_value=fetched_df) as mock_fetch, \
             patch.object(manager, "_save_binance_bars") as mock_save:
            result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=start,
                end_date=end_date,
            )

        mock_fetch.assert_called_once()
        mock_save.assert_called_once()
        assert result["15m"]["gaps_found"] >= 1
        assert result["15m"]["gaps_repaired"] >= 1
        assert result["15m"]["bars_fetched"] == 2
