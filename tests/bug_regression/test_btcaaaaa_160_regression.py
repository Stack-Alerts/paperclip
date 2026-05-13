"""
Regression tests for BTCAAAAA-160: scan anchor clipping in
_RuntimeCandleUpdateThread.

Issue: BTCAAAAA-160
Components: src/strategy_builder/ui/strategy_builder_main_window.py
            src/data_manager/unified_manager.py

Root cause: RC4 used session_start_time as the lower bound for the gap scan
window in detect_gaps_in_binance_files().  When the app starts at T and the
last bar on disk is at T-15m, detect_gaps receives start_date=T (session
start).  After filtering, the T-15m bar is excluded from `combined` so the
trailing-edge check never fires and the T, T+15, T+30, ... bars are never
written during the session.

Fix (RC4b): Anchor the scan window at last_bar_on_disk - 1_bar_period rather
than session_start_time, using the minimum anchor across all managed
timeframes (15m and 1h).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-160"),
    pytest.mark.regression,
]


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


@pytest.fixture()
def manager(tmp_path):
    from src.data_manager.unified_manager import UnifiedDataManager

    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


class TestScanAnchorClipping:
    """
    Tests for the RC4b fix that changed the scan anchor from
    session_start_time to last_bar_on_disk.

    Root cause: when session_start_time is *after* the last bar on disk,
    detect_gaps filters out the last bar, making the trailing-edge check
    invisible.
    """

    def test_session_start_after_last_bar_clips_gap(self, manager):
        """
        Bug scenario: start_date (session_start_time) is after the last bar.
        The last bar is filtered out -> combined is empty -> no trailing gap
        is detected even though new closed candles exist.
        """
        last_bar_ts = datetime(2026, 5, 4, 19, 0, 0)
        session_start = datetime(2026, 5, 4, 19, 15, 0)
        end_date = datetime(2026, 5, 4, 19, 45, 0)

        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        gaps = manager.detect_gaps_in_binance_files(
            "15m", start_date=session_start, end_date=end_date
        )

        assert len(gaps) == 0, (
            f"Expected 0 gaps when start_date clips last bar, got {len(gaps)}. "
            "This reproduces the BTCAAAAA-160 bug scenario."
        )

    def test_last_bar_anchor_detects_trailing_gap(self, manager):
        """
        Fix scenario: start_date anchored at last_bar_on_disk - 1_period.
        The last bar is included -> trailing gap IS detected.
        """
        last_bar_ts = datetime(2026, 5, 4, 19, 0, 0)
        end_date = datetime(2026, 5, 4, 19, 45, 0)

        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        scan_start = last_bar_ts - timedelta(minutes=15)
        gaps = manager.detect_gaps_in_binance_files(
            "15m", start_date=scan_start, end_date=end_date
        )

        assert len(gaps) >= 1, f"Expected >=1 gap with anchored start, got {len(gaps)}"
        trailing = gaps[-1]
        assert trailing["gap_start"] == df.iloc[-1]["timestamp"]
        assert trailing["missing_bars"] >= 1
        assert trailing["timeframe"] == "15m"

    def test_get_last_bar_timestamp_returns_anchor(self, manager):
        """
        Verify get_last_bar_timestamp() returns values that
        _RuntimeCandleUpdateThread uses to compute the scan anchor per
        timeframe.
        """
        last_15m = datetime(2026, 5, 4, 19, 0, 0)
        last_1h = datetime(2026, 5, 4, 18, 0, 0)

        start = last_15m - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        h1_start = last_1h - timedelta(hours=7)
        h1_df = _make_ohlcv(h1_start, n=8, freq_minutes=60, timeframe="1h")
        _write_month_file(manager.binance_dir, "2026-05", h1_df, "1h")

        ts_15m = manager.get_last_bar_timestamp("15m")
        ts_1h = manager.get_last_bar_timestamp("1h")

        assert ts_15m is not None
        assert ts_1h is not None
        if ts_15m.tzinfo is not None:
            ts_15m = ts_15m.replace(tzinfo=None)
        if ts_1h.tzinfo is not None:
            ts_1h = ts_1h.replace(tzinfo=None)
        assert ts_15m == last_15m.replace(tzinfo=None)
        assert ts_1h == last_1h.replace(tzinfo=None)

        anchor_15m = ts_15m - timedelta(minutes=15)
        anchor_1h = ts_1h - timedelta(hours=1)
        scan_start = min(anchor_15m, anchor_1h)
        assert scan_start == anchor_1h, (
            f"Expected min anchor to be 1h anchor ({anchor_1h}), got {scan_start}"
        )

    def test_empty_disk_returns_none(self, manager):
        """When no bars exist on disk, get_last_bar_timestamp returns None."""
        assert manager.get_last_bar_timestamp("15m") is None

    def test_no_bars_for_timeframe_returns_none(self, manager):
        """When bars exist for 15m but not 1h, the 1h call returns None."""
        ts = datetime(2026, 5, 4, 19, 0, 0)
        start = ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        assert manager.get_last_bar_timestamp("15m") is not None
        assert manager.get_last_bar_timestamp("1h") is None

    def test_verify_and_repair_clipped_start_skips_repair(self, manager):
        """
        E2E: verify_and_repair with clipped start_date (session_start after
        last_bar) detects zero gaps and fetches nothing.  With the correct
        anchored start_date the trailing gap is found and repaired.
        """
        last_bar_ts = datetime(2026, 5, 4, 19, 0, 0)
        session_start = datetime(2026, 5, 4, 19, 15, 0)
        end_date = datetime(2026, 5, 4, 19, 45, 0)

        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        fetched_df = _make_ohlcv(
            last_bar_ts + timedelta(minutes=15), n=2, freq_minutes=15, timeframe="15m"
        )

        with patch.object(manager, "_fetch_binance_range", return_value=fetched_df), \
             patch.object(manager, "_save_binance_bars"):
            clipped_result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=session_start,
                end_date=end_date,
            )

        assert clipped_result["15m"]["gaps_found"] == 0
        assert clipped_result["15m"]["gaps_repaired"] == 0

        scan_start = last_bar_ts - timedelta(minutes=15)
        with patch.object(manager, "_fetch_binance_range", return_value=fetched_df), \
             patch.object(manager, "_save_binance_bars"):
            fixed_result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=scan_start,
                end_date=end_date,
            )

        assert fixed_result["15m"]["gaps_found"] >= 1
        assert fixed_result["15m"]["gaps_repaired"] >= 1
        assert fixed_result["15m"]["bars_fetched"] >= 1

    def test_get_last_bar_timestamp_skips_corrupt_month_file(self, manager):
        """
        If one monthly parquet file is corrupt,
        get_last_bar_timestamp should skip it and try older files.
        """
        healthy_ts = datetime(2026, 5, 4, 19, 0, 0)
        start = healthy_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        corrupt_dir = manager.binance_dir / "2026-04"
        corrupt_dir.mkdir(parents=True, exist_ok=True)
        corrupt_file = corrupt_dir / "BTCUSDT_PERP_15m_2026-04.parquet"
        corrupt_file.write_bytes(b"not a valid parquet file")

        ts = manager.get_last_bar_timestamp("15m")
        assert ts is not None
        assert ts == healthy_ts.replace(tzinfo=None)

    def test_get_last_bar_timestamp_only_1h_data(self, manager):
        """
        When only 1h bars exist on disk,
        get_last_bar_timestamp returns the correct 1h timestamp.
        """
        last_bar_ts = datetime(2026, 5, 4, 19, 0, 0)
        start = last_bar_ts - timedelta(hours=7)
        df = _make_ohlcv(start, n=8, freq_minutes=60, timeframe="1h")
        _write_month_file(manager.binance_dir, "2026-05", df, "1h")

        ts_15m = manager.get_last_bar_timestamp("15m")
        ts_1h = manager.get_last_bar_timestamp("1h")

        assert ts_15m is None
        assert ts_1h is not None
        if ts_1h.tzinfo is not None:
            ts_1h = ts_1h.replace(tzinfo=None)
        assert ts_1h == last_bar_ts.replace(tzinfo=None)

    def test_detect_gaps_multiple_gaps_all_reported(self, manager):
        """
        When the data has multiple discontinuities, all gaps are reported.
        The anchor-based start_date includes all bars so no gap is clipped.
        """
        bar_a_end = datetime(2026, 5, 4, 19, 0, 0)
        bar_b_start = datetime(2026, 5, 4, 20, 0, 0)
        bar_b_end = datetime(2026, 5, 4, 20, 30, 0)


        import pandas as pd
        df_a = _make_ohlcv(bar_a_end - timedelta(minutes=15 * 7), n=8, freq_minutes=15, timeframe="15m")
        df_b = _make_ohlcv(bar_b_start, n=3, freq_minutes=15, timeframe="15m")
        combined = pd.concat([df_a, df_b], ignore_index=True)
        _write_month_file(manager.binance_dir, "2026-05", combined, "15m")

        scan_start = bar_a_end - timedelta(minutes=15)
        gaps = manager.detect_gaps_in_binance_files(
            "15m", start_date=scan_start, end_date=bar_b_end
        )

        assert len(gaps) >= 1
        found_internal_gap = any(
            g["gap_start"] == df_a.iloc[-1]["timestamp"]
            for g in gaps
        )
        assert found_internal_gap, (
            f"Expected an internal gap starting at last bar of block A "
            f"({df_a.iloc[-1]['timestamp']}), gaps: {gaps}"
        )

    def test_verify_and_repair_dry_run_does_not_mutate(self, manager):
        """
        verify_and_repair(dry_run=True) detects gaps but does not
        fetch or save any data — the on-disk state remains unchanged.
        """
        last_bar_ts = datetime(2026, 5, 4, 19, 0, 0)
        end_date = datetime(2026, 5, 4, 19, 45, 0)

        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        scan_start = last_bar_ts - timedelta(minutes=15)
        result = manager.verify_and_repair(
            timeframes=["15m"],
            start_date=scan_start,
            end_date=end_date,
            dry_run=True,
        )

        assert result["15m"]["gaps_found"] >= 1
        assert result["15m"]["gaps_repaired"] == 0
        assert result["15m"]["bars_fetched"] == 0
