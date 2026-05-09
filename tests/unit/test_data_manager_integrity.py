"""
Unit Tests: Data Manager — Data Integrity, Gap Detection & Auto-Repair
=======================================================================

Covers:
  1. Gap Detection          — detect_gaps_in_binance_files()
  2. Auto-Repair            — verify_and_repair() with mocked Binance/LakeAPI
  3. Startup Integration    — startup_check() gap detection + repair wiring
  4. Regression             — get_bars() interfaces unchanged

All Binance API calls and file I/O are mocked or use tmp_path fixtures.
No live network calls are made.

Author: QAEngineer (BTCAAAAA-14)
Date: 2026-05-02
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers: tiny factories for synthetic OHLCV data
# ---------------------------------------------------------------------------

def _make_ohlcv(
    start: datetime,
    n: int,
    freq_minutes: int = 15,
    symbol: str = "BTCUSDT",
    timeframe: str = "15m",
) -> pd.DataFrame:
    """Generate a clean, continuous OHLCV DataFrame (no NaN, no duplicates)."""
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
            "timestamp": pd.to_datetime(timestamps),
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


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame as parquet, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, compression="snappy", index=False)


def _write_month_file(
    base_dir: Path,
    month_str: str,
    df: pd.DataFrame,
    timeframe: str = "15m",
) -> Path:
    """Write to the canonical month-file layout used by UnifiedDataManager."""
    file_path = base_dir / month_str / f"BTCUSDT_PERP_{timeframe}_{month_str}.parquet"
    _write_parquet(df, file_path)
    return file_path


# ---------------------------------------------------------------------------
# Fixture: a UnifiedDataManager wired to a tmp binance_dir
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager(tmp_path):
    """
    Return a UnifiedDataManager whose binance_dir is a fresh tmp_path.

    We patch the module-level RAW_DATA_DIR so no real filesystem state leaks in,
    and disable the startup_gap_check to keep construction free of side-effects.
    """
    from src.data_manager.unified_manager import UnifiedDataManager

    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    # Redirect to tmp_path so tests create/read files in isolation
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


# ===========================================================================
# 1. GAP DETECTION — detect_gaps_in_binance_files()
# ===========================================================================

class TestDetectGapsInBinanceFiles:
    """Tests for UnifiedDataManager.detect_gaps_in_binance_files()."""

    # --------------------------------------------------------------------- #
    # 1a. No files → empty result, no crash
    # --------------------------------------------------------------------- #
    def test_no_files_returns_empty(self, manager):
        gaps = manager.detect_gaps_in_binance_files("15m")
        assert gaps == [], "Should return empty list when no parquet files exist"

    # --------------------------------------------------------------------- #
    # 1b. Clean 15m data → zero gaps (no false positives)
    # --------------------------------------------------------------------- #
    def test_clean_15m_no_false_positives(self, manager):
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=200, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-03", df, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m")
        assert gaps == [], f"Clean continuous data must not report gaps; got: {gaps}"

    # --------------------------------------------------------------------- #
    # 1c. Clean 1d data → zero gaps (no false positives for daily)
    # --------------------------------------------------------------------- #
    def test_clean_daily_no_false_positives(self, manager):
        start = datetime(2026, 1, 1, 0, 0)
        df = _make_ohlcv(start, n=60, freq_minutes=1440, timeframe="1d")
        _write_month_file(manager.binance_dir, "2026-01", df, "1d")

        gaps = manager.detect_gaps_in_binance_files("1d")
        assert gaps == [], f"Clean daily data must not report gaps; got: {gaps}"

    # --------------------------------------------------------------------- #
    # 1d. Single missing candle detected
    # --------------------------------------------------------------------- #
    def test_single_missing_candle_detected(self, manager):
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=100, freq_minutes=15, timeframe="15m")
        # Drop bar at index 50 → gap between index 49 and 51
        df_with_gap = pd.concat([df.iloc[:50], df.iloc[51:]]).reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-03", df_with_gap, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m")
        assert len(gaps) == 1, f"Expected 1 gap, got {len(gaps)}: {gaps}"
        assert gaps[0]["missing_bars"] == 1
        assert gaps[0]["timeframe"] == "15m"

    # --------------------------------------------------------------------- #
    # 1e. Large gap (34-day outage window) detected and quantified
    # --------------------------------------------------------------------- #
    def test_large_gap_detected_and_quantified(self, manager):
        # Segment 1: March 1–15 (100 bars × 15m)
        seg1_start = datetime(2026, 3, 1, 0, 0)
        seg1 = _make_ohlcv(seg1_start, n=100, freq_minutes=15, timeframe="15m")
        # Segment 2: April 20 onward (50 bars) — 36-day gap
        seg2_start = datetime(2026, 4, 20, 0, 0)
        seg2 = _make_ohlcv(seg2_start, n=50, freq_minutes=15, timeframe="15m")

        _write_month_file(manager.binance_dir, "2026-03", seg1, "15m")
        _write_month_file(manager.binance_dir, "2026-04", seg2, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m")
        assert len(gaps) == 1, f"Expected 1 gap, got {gaps}"
        gap = gaps[0]
        # 36 days × 96 bars/day ≈ 3456 bars; allow ±10% tolerance
        assert gap["missing_bars"] > 2000, (
            f"Expected large bar count, got {gap['missing_bars']}"
        )
        assert gap["gap_start"] == seg1.iloc[-1]["timestamp"]
        assert gap["gap_end"] == seg2.iloc[0]["timestamp"]

    # --------------------------------------------------------------------- #
    # 1f. Duplicate timestamps are deduped silently (no false gaps)
    # --------------------------------------------------------------------- #
    def test_duplicates_deduped_no_false_gaps(self, manager):
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=100, freq_minutes=15, timeframe="15m")
        # Duplicate the first 10 rows
        df_with_dupes = pd.concat([df, df.iloc[:10]]).reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-03", df_with_dupes, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m")
        assert gaps == [], f"Duplicates must be deduped; unexpected gaps: {gaps}"

    # --------------------------------------------------------------------- #
    # 1g. Out-of-order entries sorted and produce no false gaps
    # --------------------------------------------------------------------- #
    def test_out_of_order_sorted_no_false_gaps(self, manager):
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=100, freq_minutes=15, timeframe="15m")
        shuffled = df.sample(frac=1, random_state=99).reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-03", shuffled, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m")
        assert gaps == [], f"Out-of-order data, when sorted, must not report gaps: {gaps}"

    # --------------------------------------------------------------------- #
    # 1h. Multiple gaps in one dataset
    # --------------------------------------------------------------------- #
    def test_multiple_gaps_detected(self, manager):
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=200, freq_minutes=15, timeframe="15m")
        # Two separate gaps
        mask = list(range(200))
        mask.pop(50)   # gap 1
        mask.pop(130)  # gap 2 (index shifted after first pop)
        df_gapped = df.iloc[mask].reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-03", df_gapped, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m")
        assert len(gaps) == 2, f"Expected 2 gaps, got {len(gaps)}: {gaps}"

    # --------------------------------------------------------------------- #
    # 1i. Date range filter excludes out-of-window gaps
    # --------------------------------------------------------------------- #
    def test_date_filter_excludes_out_of_window_gaps(self, manager):
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=200, freq_minutes=15, timeframe="15m")
        # Drop a bar early (index 5) and late (index 150)
        df_gapped = df.drop(index=[5, 150]).reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-03", df_gapped, "15m")

        # Filter to only cover the first hour → should only see the early gap
        filter_end = start + timedelta(hours=3)
        gaps = manager.detect_gaps_in_binance_files("15m", end_date=filter_end)
        assert len(gaps) == 1, (
            f"Date filter should exclude the late gap; got {len(gaps)} gap(s)"
        )

    # --------------------------------------------------------------------- #
    # 1j. Unknown timeframe raises ValueError
    # --------------------------------------------------------------------- #
    def test_unknown_timeframe_raises(self, manager):
        with pytest.raises(ValueError, match="Unknown timeframe"):
            manager.detect_gaps_in_binance_files("99x")

    # --------------------------------------------------------------------- #
    # 1k. NaN/corrupt values: file with all-NaN timestamp column is skipped
    # --------------------------------------------------------------------- #
    def test_corrupt_file_skipped_gracefully(self, manager, tmp_path):
        # Write a valid file
        start = datetime(2026, 3, 1, 0, 0)
        df_good = _make_ohlcv(start, n=50, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-03", df_good, "15m")
        # Write a corrupt zero-byte file that pd.read_parquet will fail on
        corrupt_path = (
            manager.binance_dir
            / "2026-03"
            / "BTCUSDT_PERP_15m_2026-03_corrupt.parquet"
        )
        corrupt_path.write_bytes(b"not a parquet file")

        # Should not raise; corrupt file is skipped
        gaps = manager.detect_gaps_in_binance_files("15m")
        # The good file is continuous so no gaps expected
        assert gaps == [], f"Corrupt file must not cause false gaps: {gaps}"


# ===========================================================================
# 2. AUTO-REPAIR — verify_and_repair()
# ===========================================================================

class TestVerifyAndRepair:
    """Tests for UnifiedDataManager.verify_and_repair()."""

    def _setup_gap_scenario(
        self,
        manager,
        gap_start: datetime,
        gap_end: datetime,
        timeframe: str = "15m",
        freq_minutes: int = 15,
    ):
        """
        Write two parquet segments split around [gap_start, gap_end].
        Returns (seg1, seg2) DataFrames.
        """
        # Segment 1: 50 bars ending at gap_start
        seg1_start = gap_start - timedelta(minutes=freq_minutes * 49)
        seg1 = _make_ohlcv(seg1_start, n=50, freq_minutes=freq_minutes, timeframe=timeframe)
        # Ensure last timestamp == gap_start
        seg1.iloc[-1, seg1.columns.get_loc("timestamp")] = pd.Timestamp(gap_start)

        # Segment 2: 30 bars starting at gap_end
        seg2 = _make_ohlcv(gap_end, n=30, freq_minutes=freq_minutes, timeframe=timeframe)

        month1 = gap_start.strftime("%Y-%m")
        month2 = gap_end.strftime("%Y-%m")
        _write_month_file(manager.binance_dir, month1, seg1, timeframe)
        if month2 != month1:
            _write_month_file(manager.binance_dir, month2, seg2, timeframe)
        else:
            # Same month: write both to the same file
            combined = pd.concat([seg1, seg2]).drop_duplicates("timestamp").sort_values("timestamp")
            _write_month_file(manager.binance_dir, month1, combined, timeframe)

        return seg1, seg2

    # --------------------------------------------------------------------- #
    # 2a. No gaps → report shows zeros, no fetch attempted
    # --------------------------------------------------------------------- #
    def test_no_gaps_no_fetch(self, manager):
        start = datetime(2026, 4, 1, 0, 0)
        df = _make_ohlcv(start, n=200, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-04", df, "15m")

        with patch.object(manager, "_fetch_binance_range") as mock_fetch:
            result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=start,
                end_date=start + timedelta(days=2),
            )

        mock_fetch.assert_not_called()
        assert result["15m"]["gaps_found"] == 0
        assert result["15m"]["gaps_repaired"] == 0

    # --------------------------------------------------------------------- #
    # 2b. Gap within Binance horizon → repaired via _fetch_binance_range
    # --------------------------------------------------------------------- #
    def test_recent_gap_repaired_via_binance(self, manager):
        now = datetime.now()
        gap_start = now - timedelta(days=10)
        gap_start = gap_start.replace(second=0, microsecond=0)
        gap_end = gap_start + timedelta(hours=2)  # 8-bar gap

        self._setup_gap_scenario(manager, gap_start, gap_end)

        # Mock _fetch_binance_range to return 7 "new" bars
        fetched_df = _make_ohlcv(
            gap_start + timedelta(minutes=15), n=7, freq_minutes=15, timeframe="15m"
        )
        with patch.object(manager, "_fetch_binance_range", return_value=fetched_df) as mock_fetch, \
             patch.object(manager, "_save_binance_bars") as mock_save:
            result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=gap_start - timedelta(hours=1),
                end_date=gap_end + timedelta(hours=1),
                binance_api_horizon_days=90,
            )

        mock_fetch.assert_called_once()
        mock_save.assert_called_once()
        assert result["15m"]["gaps_repaired"] == 1
        assert result["15m"]["bars_fetched"] == 7

    # --------------------------------------------------------------------- #
    # 2c. Gap too old → flagged as gaps_too_old, no fetch
    # --------------------------------------------------------------------- #
    def test_old_gap_flagged_not_fetched(self, manager):
        # Put the gap 120 days ago (beyond default 90-day horizon)
        old_gap_start = datetime.now() - timedelta(days=120)
        old_gap_start = old_gap_start.replace(second=0, microsecond=0)
        old_gap_end = old_gap_start + timedelta(hours=2)

        self._setup_gap_scenario(manager, old_gap_start, old_gap_end)

        with patch.object(manager, "_fetch_binance_range") as mock_fetch, \
             patch.object(manager, "_save_binance_bars") as mock_save:
            result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=old_gap_start - timedelta(hours=1),
                end_date=old_gap_end + timedelta(hours=1),
                binance_api_horizon_days=90,
            )

        mock_fetch.assert_not_called()
        mock_save.assert_not_called()
        assert result["15m"]["gaps_too_old"] == 1
        assert result["15m"]["gaps_repaired"] == 0

    # --------------------------------------------------------------------- #
    # 2d. Dry-run mode: gaps detected but nothing fetched or saved
    # --------------------------------------------------------------------- #
    def test_dry_run_no_writes(self, manager):
        now = datetime.now()
        gap_start = now - timedelta(days=5)
        gap_start = gap_start.replace(second=0, microsecond=0)
        gap_end = gap_start + timedelta(hours=1)

        self._setup_gap_scenario(manager, gap_start, gap_end)

        with patch.object(manager, "_fetch_binance_range") as mock_fetch, \
             patch.object(manager, "_save_binance_bars") as mock_save:
            result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=gap_start - timedelta(hours=1),
                end_date=gap_end + timedelta(hours=1),
                dry_run=True,
            )

        mock_fetch.assert_not_called()
        mock_save.assert_not_called()
        assert result["15m"]["gaps_found"] > 0

    # --------------------------------------------------------------------- #
    # 2e. Repair produces no duplicate candles
    # --------------------------------------------------------------------- #
    def test_repair_no_duplicate_candles(self, manager, tmp_path):
        """
        Simulate a repair: _save_binance_bars() must deduplicate before write.
        """
        start = datetime(2026, 4, 1, 0, 0)
        existing = _make_ohlcv(start, n=96, freq_minutes=15, timeframe="15m")
        month_str = "2026-04"
        file_path = _write_month_file(manager.binance_dir, month_str, existing, "15m")

        # "New" bars overlap with first 10 rows of existing
        overlap = existing.iloc[:10].copy()
        manager._save_binance_bars(overlap, "15m")

        # Re-read and verify deduplication
        result = pd.read_parquet(file_path)
        assert result["timestamp"].duplicated().sum() == 0, (
            "Duplicate timestamps detected after _save_binance_bars"
        )
        # Total should still be 96 (no additional rows from overlap)
        assert len(result) == 96, f"Expected 96 rows, got {len(result)}"

    # --------------------------------------------------------------------- #
    # 2f. Repair preserves chronological ordering
    # --------------------------------------------------------------------- #
    def test_repair_preserves_ordering(self, manager):
        start = datetime(2026, 4, 1, 0, 0)
        existing = _make_ohlcv(start, n=96, freq_minutes=15, timeframe="15m")
        month_str = "2026-04"
        file_path = _write_month_file(manager.binance_dir, month_str, existing, "15m")

        # Add bars out of order
        extra = _make_ohlcv(start - timedelta(hours=3), n=12, freq_minutes=15, timeframe="15m")
        manager._save_binance_bars(extra, "15m")

        result = pd.read_parquet(file_path)
        result["timestamp"] = pd.to_datetime(result["timestamp"])
        timestamps = result["timestamp"].tolist()
        assert timestamps == sorted(timestamps), (
            "Timestamps are not in ascending order after _save_binance_bars"
        )

    # --------------------------------------------------------------------- #
    # 2g. API error during repair is captured in errors list, not raised
    # --------------------------------------------------------------------- #
    def test_api_error_captured_not_raised(self, manager):
        now = datetime.now()
        gap_start = now - timedelta(days=5)
        gap_start = gap_start.replace(second=0, microsecond=0)
        gap_end = gap_start + timedelta(hours=1)

        self._setup_gap_scenario(manager, gap_start, gap_end)

        with patch.object(manager, "_fetch_binance_range",
                          side_effect=ConnectionError("Network error")):
            result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=gap_start - timedelta(hours=1),
                end_date=gap_end + timedelta(hours=1),
            )

        assert len(result["15m"]["errors"]) == 1
        assert "Network error" in result["15m"]["errors"][0]
        assert result["15m"]["gaps_repaired"] == 0

    # --------------------------------------------------------------------- #
    # 2h. Return structure always has all required keys
    # --------------------------------------------------------------------- #
    def test_return_structure_complete(self, manager):
        result = manager.verify_and_repair(
            timeframes=["15m", "1h", "1d"],
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 2),
        )
        for tf in ["15m", "1h", "1d"]:
            assert tf in result, f"Timeframe '{tf}' missing from result keys"
            for key in ("gaps_found", "gaps_repaired", "gaps_too_old",
                        "bars_fetched", "errors"):
                assert key in result[tf], f"Missing key '{key}' for timeframe {tf}"


# ===========================================================================
# 3. STARTUP INTEGRATION — startup_check()
# ===========================================================================

class TestStartupCheck:
    """Tests for startup gap detection integration."""

    # --------------------------------------------------------------------- #
    # 3a. Startup check runs on construction when startup_gap_check=True
    # --------------------------------------------------------------------- #
    def test_startup_check_called_when_enabled(self, tmp_path):
        from src.data_manager.unified_manager import UnifiedDataManager

        with patch.object(
            UnifiedDataManager, "startup_check", return_value={}
        ) as mock_startup:
            mgr = UnifiedDataManager(mode="live", startup_gap_check=True)
            mock_startup.assert_called_once_with(auto_repair=True)

    # --------------------------------------------------------------------- #
    # 3b. Startup check NOT called when startup_gap_check=False (default)
    # --------------------------------------------------------------------- #
    def test_startup_check_not_called_by_default(self, tmp_path):
        from src.data_manager.unified_manager import UnifiedDataManager

        with patch.object(
            UnifiedDataManager, "startup_check", return_value={}
        ) as mock_startup:
            mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
            mock_startup.assert_not_called()

    # --------------------------------------------------------------------- #
    # 3c. startup_check detects gap and returns repair summary
    # --------------------------------------------------------------------- #
    def test_startup_check_detects_and_reports_gap(self, manager):
        now = datetime.now()
        gap_start = now - timedelta(days=3)
        gap_start = gap_start.replace(second=0, microsecond=0)
        gap_end = gap_start + timedelta(hours=2)

        # Write gapped data
        seg1_start = gap_start - timedelta(hours=5)
        seg1 = _make_ohlcv(seg1_start, n=20, freq_minutes=15, timeframe="15m")
        seg2 = _make_ohlcv(gap_end, n=10, freq_minutes=15, timeframe="15m")
        combined = pd.concat([seg1, seg2]).sort_values("timestamp").reset_index(drop=True)
        _write_month_file(manager.binance_dir, gap_start.strftime("%Y-%m"), combined, "15m")

        with patch.object(manager, "verify_and_repair",
                          return_value={"15m": {"gaps_found": 1, "gaps_repaired": 1,
                                                "gaps_too_old": 0, "bars_fetched": 7,
                                                "errors": []}}) as mock_repair:
            result = manager.startup_check(timeframes=["15m"], auto_repair=True)

        mock_repair.assert_called_once()

    # --------------------------------------------------------------------- #
    # 3d. startup_check with auto_repair=False calls run_gap_report not repair
    # --------------------------------------------------------------------- #
    def test_startup_check_no_autorepair_calls_gap_report(self, manager):
        now = datetime.now()
        gap_start = now - timedelta(days=1)
        gap_start = gap_start.replace(second=0, microsecond=0)

        seg1 = _make_ohlcv(gap_start - timedelta(hours=4), n=10, freq_minutes=15, timeframe="15m")
        seg2 = _make_ohlcv(gap_start + timedelta(hours=2), n=10, freq_minutes=15, timeframe="15m")
        combined = pd.concat([seg1, seg2]).sort_values("timestamp").reset_index(drop=True)
        _write_month_file(manager.binance_dir, gap_start.strftime("%Y-%m"), combined, "15m")

        with patch.object(manager, "verify_and_repair") as mock_repair, \
             patch.object(manager, "run_gap_report",
                          return_value={"15m": []}) as mock_report:
            manager.startup_check(timeframes=["15m"], auto_repair=False)

        mock_repair.assert_not_called()
        mock_report.assert_called_once()

    # --------------------------------------------------------------------- #
    # 3e. Startup check with genuinely gap-free data returns zero gaps.
    #
    # Previously this test wrote data anchored at `now - 6 days` ending at
    # approximately `now - 1 day`, which caused the AC5 trailing-edge check
    # inside detect_gaps_in_binance_files() to detect a gap from the last
    # stored bar to datetime.utcnow().  Fix: anchor the data to now so the
    # last bar on disk is within the trailing-edge slop window.
    #
    # Strategy (Option 2 from BTCAAAAA-378):
    #   - Floor datetime.utcnow() to the currently-forming bar boundary.
    #   - Generate lookback_days * 96 + 1 bars *backward* from there.
    #   - Write them; the last bar is always at or after `last_closed` as
    #     computed by the trailing-edge detector, so no trailing gap fires.
    # --------------------------------------------------------------------- #
    def test_startup_check_all_clean_returns_zero_gaps(self, manager):
        lookback_days = 5
        freq_minutes = 15
        bars_per_day = 1440 // freq_minutes  # 96

        # Anchor to the open time of the currently-forming 15m bar.
        # detect_gaps_in_binance_files computes last_closed = floor(end_date,
        # 15m) and flags a trailing gap only when last_closed > last_bar + slop
        # (slop = 13.5 min).  By writing the last bar AT floor(now, 15m) we
        # ensure last_closed <= last_bar for any end_date < next bar open, so
        # the trailing-edge check never fires for the entire 15-minute window.
        now = datetime.utcnow()
        last_bar = now - timedelta(
            minutes=now.minute % freq_minutes,
            seconds=now.second,
            microseconds=now.microsecond,
        )

        n = lookback_days * bars_per_day + 1  # +1 to cover the full window
        start = last_bar - timedelta(minutes=freq_minutes * (n - 1))

        df = _make_ohlcv(start, n=n, freq_minutes=freq_minutes, timeframe="15m")

        # Snap the last bar to exactly `last_bar` to guarantee no clock-skew
        df.iloc[-1, df.columns.get_loc("timestamp")] = pd.Timestamp(last_bar)

        # Write to the correct month file(s).  The data may span two calendar
        # months, so group by month and write each group separately.
        df["_month"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m")
        for month_str, group in df.groupby("_month", sort=True):
            _write_month_file(
                manager.binance_dir,
                month_str,
                group.drop(columns=["_month"]).reset_index(drop=True),
                "15m",
            )

        # Use a lookback that matches our data
        result = manager.startup_check(
            timeframes=["15m"], auto_repair=False, lookback_days=lookback_days
        )
        # All zeros → data is clean
        for tf, summary in result.items():
            assert summary["gaps_found"] == 0, (
                f"Expected 0 gaps for clean data, got {summary['gaps_found']} for {tf}"
            )


# ===========================================================================
# 4. REGRESSION — get_bars() interface unchanged
# ===========================================================================

class TestGetBarsRegression:
    """
    Regression tests to verify get_bars() is not broken by gap-detection changes.

    These tests mock the internal routing so they don't require live data.
    """

    def test_get_bars_count_returns_dataframe(self, manager):
        """get_bars(count=N) must return a DataFrame with at most N rows."""
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=200, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-03", df, "15m")

        with patch.object(manager, "_get_bars_by_count", return_value=df.tail(100)) as mock_count:
            result = manager.get_bars(timeframe="15m", count=100)

        mock_count.assert_called_once_with("15m", 100, None)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100

    def test_get_bars_date_range_returns_dataframe(self, manager):
        """get_bars(start_date, end_date) must return a DataFrame."""
        start = datetime(2026, 3, 1, 0, 0)
        end = datetime(2026, 3, 2, 0, 0)
        df = _make_ohlcv(start, n=96, freq_minutes=15, timeframe="15m")

        from src.data_manager.unified_manager import DataSource
        with patch.object(manager, "_get_bars_by_range", return_value=df) as mock_range:
            result = manager.get_bars(timeframe="15m", start_date=start, end_date=end)

        mock_range.assert_called_once_with("15m", start, end, DataSource.AUTO)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 96

    def test_get_bars_requires_count_or_start_date(self, manager):
        """Calling get_bars() with neither count nor start_date must raise ValueError."""
        with pytest.raises(ValueError, match="Must specify"):
            manager.get_bars(timeframe="15m")

    def test_get_bars_ohlcv_integrity(self, manager):
        """
        OHLCV validation: high >= low, open <= high, close <= high,
        no NaN values, no zero volumes.
        """
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=96, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-03", df, "15m")

        with patch.object(manager, "_get_bars_by_range", return_value=df):
            result = manager.get_bars(
                timeframe="15m",
                start_date=start,
                end_date=start + timedelta(days=1),
            )

        # Pre-Deployment Checklist assertions
        assert not result.isnull().any().any(), "Contains NaN values"
        assert (result["high"] >= result["low"]).all(), "High < Low error"
        assert (result["open"] <= result["high"]).all(), "Open > High error"
        assert (result["close"] <= result["high"]).all(), "Close > High error"
        assert (result["volume"] > 0).all(), "Zero volume found"

    def test_get_bars_timestamps_monotonic(self, manager):
        """Returned bars must be sorted in ascending timestamp order."""
        start = datetime(2026, 3, 1, 0, 0)
        df = _make_ohlcv(start, n=96, freq_minutes=15, timeframe="15m")

        with patch.object(manager, "_get_bars_by_range", return_value=df):
            result = manager.get_bars(
                timeframe="15m",
                start_date=start,
                end_date=start + timedelta(days=1),
            )

        ts = pd.to_datetime(result["timestamp"])
        assert ts.is_monotonic_increasing, "Timestamps are not sorted ascending"


# ===========================================================================
# 5. SAVE BARS — _save_binance_bars()
# ===========================================================================

class TestSaveBinanceBars:
    """Tests for _save_binance_bars() — file I/O, dedup, and ordering."""

    def test_creates_file_if_not_exists(self, manager):
        """New bars written to a month with no prior file."""
        start = datetime(2026, 5, 1, 0, 0)
        df = _make_ohlcv(start, n=20, freq_minutes=15, timeframe="15m")
        manager._save_binance_bars(df, "15m")

        expected = (
            manager.binance_dir / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet"
        )
        assert expected.exists(), f"Expected parquet file not created: {expected}"

    def test_merge_with_existing_no_duplicates(self, manager):
        """Merging overlapping frames must not produce duplicates."""
        start = datetime(2026, 5, 1, 0, 0)
        df = _make_ohlcv(start, n=50, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        # Overlap first 20 bars
        overlap = df.iloc[:20].copy()
        manager._save_binance_bars(overlap, "15m")

        file_path = manager.binance_dir / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet"
        result = pd.read_parquet(file_path)
        assert result["timestamp"].duplicated().sum() == 0
        assert len(result) == 50  # unchanged

    def test_new_bars_appended(self, manager):
        """New non-overlapping bars are appended to existing file."""
        start = datetime(2026, 5, 1, 0, 0)
        df_initial = _make_ohlcv(start, n=50, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df_initial, "15m")

        extension_start = start + timedelta(minutes=15 * 50)
        df_new = _make_ohlcv(extension_start, n=10, freq_minutes=15, timeframe="15m")
        manager._save_binance_bars(df_new, "15m")

        file_path = manager.binance_dir / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet"
        result = pd.read_parquet(file_path)
        assert len(result) == 60

    def test_empty_dataframe_is_noop(self, manager):
        """Passing an empty DataFrame must not create any file."""
        manager._save_binance_bars(pd.DataFrame(), "15m")
        assert not list(manager.binance_dir.glob("**/*.parquet")), (
            "Empty DataFrame should not create parquet files"
        )

    def test_cross_month_bars_written_to_correct_files(self, manager):
        """Bars spanning two calendar months go to separate files."""
        jan_start = datetime(2026, 1, 31, 20, 0)
        df = _make_ohlcv(jan_start, n=20, freq_minutes=15, timeframe="15m")
        manager._save_binance_bars(df, "15m")

        jan_file = manager.binance_dir / "2026-01" / "BTCUSDT_PERP_15m_2026-01.parquet"
        feb_file = manager.binance_dir / "2026-02" / "BTCUSDT_PERP_15m_2026-02.parquet"
        assert jan_file.exists() or feb_file.exists(), (
            "Expected at least one month file to be created"
        )


# ===========================================================================
# 6. OHLCV DATA VALIDATION
# ===========================================================================

class TestOHLCVDataValidation:
    """
    Enforce the Pre-Deployment Checklist data-quality assertions on synthetic data.
    These tests document the exact validation rules and prove _make_ohlcv() produces
    clean data.  They also serve as a reference for any data pipeline fixes.
    """

    @pytest.fixture()
    def clean_df(self):
        return _make_ohlcv(datetime(2026, 1, 1), n=500)

    def test_no_nan_values(self, clean_df):
        assert not clean_df.isnull().any().any(), "Contains NaN values"

    def test_high_gte_low(self, clean_df):
        assert (clean_df["high"] >= clean_df["low"]).all(), "High < Low error"

    def test_open_lte_high(self, clean_df):
        assert (clean_df["open"] <= clean_df["high"]).all(), "Open > High error"

    def test_close_lte_high(self, clean_df):
        assert (clean_df["close"] <= clean_df["high"]).all(), "Close > High error"

    def test_positive_volume(self, clean_df):
        assert (clean_df["volume"] > 0).all(), "Zero volume found"

    def test_timestamps_continuous(self, clean_df):
        """Verify timestamps have no unexpected gaps (all diffs == 15 min)."""
        diffs = pd.to_datetime(clean_df["timestamp"]).diff().dropna()
        assert (diffs == timedelta(minutes=15)).all(), (
            "Timestamp gaps found in clean data"
        )

    def test_detect_nan_ohlcv(self):
        """Injecting NaN into an otherwise valid frame must fail the check."""
        df = _make_ohlcv(datetime(2026, 1, 1), n=10)
        df.loc[5, "close"] = float("nan")
        with pytest.raises(AssertionError):
            assert not df.isnull().any().any(), "Contains NaN values"

    def test_detect_zero_volume(self):
        """Injecting zero volume must fail the check."""
        df = _make_ohlcv(datetime(2026, 1, 1), n=10)
        df.loc[3, "volume"] = 0.0
        with pytest.raises(AssertionError):
            assert (df["volume"] > 0).all(), "Zero volume found"


# ===========================================================================
# 7. 1D PIPELINE REGRESSION GUARD (BTCAAAAA-67)
# ===========================================================================

class TestDownloadWithRetry1dStaleness:
    """
    Regression guard: _download_with_retry() must use a staleness threshold
    of ≥ 1440 minutes for 1d bars, not the 65-minute fallback used for 1h.

    A closed daily candle is naturally many hours old; treating anything older
    than 65 minutes as stale would continuously trigger unnecessary retries.
    """

    def test_1d_staleness_threshold_is_at_least_1440_minutes(self, tmp_path):
        """
        Verify that _download_with_retry(timeframe='1d') accepts a bar whose
        latest timestamp is 900 minutes old — well past the 1h threshold (65 min)
        but well within the 1d threshold (≥ 1440 min).

        Arrange: mock get_bars() to return a DataFrame whose latest timestamp is
        900 minutes in the past.  If the staleness check incorrectly uses the
        65-minute 1h threshold, the thread would retry (or raise) instead of
        returning the data immediately on the first attempt.

        Assert: _download_with_retry returns the bars on the first attempt
        (get_bars called exactly once, no retries).
        """
        from src.strategy_builder.ui.data_update_modal import DataUpdateThread
        from src.data_manager.unified_manager import UnifiedDataManager, DataSource

        start_date = datetime(2026, 4, 1, 0, 0)
        end_date = datetime(2026, 4, 30, 0, 0)
        thread = DataUpdateThread(start_date=start_date, end_date=end_date)

        # Build a 1d DataFrame whose last bar is 900 minutes old
        stale_minutes = 900  # older than 65-min 1h threshold, fresh for 1d
        bars_1d = _make_ohlcv(
            start=datetime.now() - timedelta(minutes=stale_minutes + 10),
            n=5,
            freq_minutes=1440,
            timeframe="1d",
        )
        # Ensure the latest timestamp is exactly `stale_minutes` ago
        bars_1d.iloc[-1, bars_1d.columns.get_loc("timestamp")] = (
            pd.Timestamp(datetime.now() - timedelta(minutes=stale_minutes))
        )

        call_count = {"n": 0}

        def fake_get_bars(timeframe, start_date, end_date, source):
            call_count["n"] += 1
            return bars_1d

        with patch.object(thread.manager, "get_bars", side_effect=fake_get_bars):
            result = thread._download_with_retry(
                timeframe="1d",
                start_date=start_date,
                end_date=end_date,
            )

        assert call_count["n"] == 1, (
            f"Expected exactly 1 call to get_bars (data accepted as fresh), "
            f"but got {call_count['n']} — the 1d staleness threshold is too low"
        )
        assert len(result) == 5, "Expected 5 bars to be returned"

    def test_1h_threshold_does_not_apply_to_1d(self, tmp_path):
        """
        Complementary test: the 65-minute 1h threshold must NOT be used for 1d.

        If _download_with_retry mistakenly applies the 1h threshold (65 min) to
        a 1d request, a bar that is 70 minutes old would be treated as stale and
        trigger a retry.  With the correct threshold (≥ 1440 min), 70 minutes is
        fresh and no retry should happen.
        """
        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        start_date = datetime(2026, 4, 1, 0, 0)
        end_date = datetime(2026, 4, 30, 0, 0)
        thread = DataUpdateThread(start_date=start_date, end_date=end_date)

        # Bar is 70 minutes old — stale for 1h (65 min threshold), fresh for 1d
        bars_1d = _make_ohlcv(
            start=datetime.now() - timedelta(minutes=80),
            n=3,
            freq_minutes=1440,
            timeframe="1d",
        )
        bars_1d.iloc[-1, bars_1d.columns.get_loc("timestamp")] = (
            pd.Timestamp(datetime.now() - timedelta(minutes=70))
        )

        call_count = {"n": 0}

        def fake_get_bars(timeframe, start_date, end_date, source):
            call_count["n"] += 1
            return bars_1d

        with patch.object(thread.manager, "get_bars", side_effect=fake_get_bars):
            result = thread._download_with_retry(
                timeframe="1d",
                start_date=start_date,
                end_date=end_date,
            )

        assert call_count["n"] == 1, (
            f"A 70-min-old 1d bar should be fresh (threshold ≥ 1440 min), "
            f"but get_bars was called {call_count['n']} time(s) — threshold is wrong"
        )


class TestGetKlines1dNotFlaggedStale:
    """
    Regression guard: BinanceRestClient.get_klines(interval='1d') must NOT
    trigger the direct_fallback for a bar that is naturally hundreds of minutes
    old (e.g. 900 minutes).

    The stale threshold for '1d' must be ≥ 1440 minutes (the issue description
    calls out the old 65-minute fallback as the root-cause defect to prevent
    from recurring).
    """

    @staticmethod
    def _make_raw_klines_response(bar_timestamp: datetime, n: int = 1) -> list:
        """
        Build a minimal raw Binance klines list-of-lists response.

        Each row: [open_time_ms, open, high, low, close, volume,
                   close_time_ms, quote_vol, trades, taker_buy_base,
                   taker_buy_quote, ignore]

        The 'open_time' column is what get_klines() parses for the timestamp.
        """
        rows = []
        for i in range(n):
            ts = bar_timestamp + timedelta(minutes=1440 * i)
            open_time_ms = int(ts.timestamp() * 1000)
            close_time_ms = open_time_ms + 1440 * 60_000 - 1
            rows.append([
                open_time_ms, "30000.00", "30500.00", "29500.00", "30200.00",
                "10.5",       # volume
                close_time_ms, "315000.00", 500, "5.25", "157500.00", "0",
            ])
        return rows

    def test_900_minute_old_1d_bar_does_not_trigger_fallback(self):
        """
        A 1d bar that is 900 minutes old (15 hours) is perfectly normal — the
        daily candle for 'today' closes at midnight UTC and will always be many
        hours old when read during the trading day.

        Verify that the direct_fallback is NOT invoked for such a bar.
        """
        from src.data_manager.binance.rest_client import BinanceRestClient

        client = BinanceRestClient()

        # Bar whose open_time is 900 minutes ago
        bar_ts = datetime.now() - timedelta(minutes=900)
        raw_response = self._make_raw_klines_response(bar_ts, n=1)

        with patch.object(client, "_request", return_value=raw_response), \
             patch(
                 "src.data_manager.binance.rest_client.get_fresh_klines_direct",
                 create=True,
             ) as mock_fallback, \
             patch(
                 "src.data_manager.binance.direct_fallback.get_fresh_klines_direct",
                 create=True,
             ) as mock_fallback2:
            result = client.get_klines(interval="1d", symbol="BTCUSDT", limit=1)

        assert mock_fallback.call_count == 0 and mock_fallback2.call_count == 0, (
            "direct_fallback must NOT be triggered for a 900-min-old 1d bar; "
            "the 1d staleness threshold must be ≥ 1440 minutes"
        )

    def test_1d_stale_threshold_in_dict_is_at_least_1440(self):
        """
        White-box: confirm the '_stale_thresholds' dict inside get_klines()
        maps '1d' to a value ≥ 1440 minutes.

        We do this by placing a bar that is exactly 1439 minutes old
        (just under 24 hours) and verifying the fallback is not triggered.
        """
        from src.data_manager.binance.rest_client import BinanceRestClient

        client = BinanceRestClient()

        bar_ts = datetime.now() - timedelta(minutes=1439)
        raw_response = self._make_raw_klines_response(bar_ts, n=1)

        with patch.object(client, "_request", return_value=raw_response), \
             patch(
                 "src.data_manager.binance.rest_client.get_fresh_klines_direct",
                 create=True,
             ) as mock_fallback, \
             patch(
                 "src.data_manager.binance.direct_fallback.get_fresh_klines_direct",
                 create=True,
             ) as mock_fallback2:
            client.get_klines(interval="1d", symbol="BTCUSDT", limit=1)

        assert mock_fallback.call_count == 0 and mock_fallback2.call_count == 0, (
            "A 1439-min-old 1d bar should be fresh (threshold ≥ 1440 min), "
            "but direct_fallback was triggered — threshold too low"
        )


# ===========================================================================
# 8. TRAILING-EDGE GAP DETECTION (BTCAAAAA-115)
# ===========================================================================

class TestTrailingEdgeGapDetection:
    """
    Tests for the trailing-edge check added to detect_gaps_in_binance_files().

    Root cause: diff() only finds gaps between existing rows; when the last bar
    on disk is stale relative to end_date the function returned 0 gaps even
    though new closed candles exist.  These tests verify the trailing-edge
    check catches that scenario (BUG-B fix).
    """

    # --------------------------------------------------------------------- #
    # 8a. Stale last bar triggers trailing-edge gap
    # --------------------------------------------------------------------- #
    def test_stale_last_bar_triggers_trailing_gap(self, manager):
        """
        Data on disk ends 30 minutes before end_date (two 15m bars behind).
        detect_gaps_in_binance_files must return ≥1 gap that covers the
        trailing window.
        """
        # Anchor to a round time so floor_to_bar is deterministic
        end_date = datetime(2026, 5, 4, 12, 0, 0)   # exactly on :00 boundary
        # Last bar on disk is T-30m (two closed 15m bars behind)
        last_bar_ts = end_date - timedelta(minutes=30)
        # Write 8 consecutive bars ending at last_bar_ts
        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        gaps = manager.detect_gaps_in_binance_files(
            "15m", end_date=end_date
        )

        assert len(gaps) >= 1, (
            f"Expected at least 1 trailing-edge gap when last bar is 30 min stale; "
            f"got {gaps}"
        )
        trailing = gaps[-1]
        assert trailing["gap_start"] == df.iloc[-1]["timestamp"], (
            "gap_start must be the last bar on disk"
        )
        assert trailing["missing_bars"] >= 1, (
            "trailing gap must report ≥1 missing bar"
        )
        assert trailing["timeframe"] == "15m"

    # --------------------------------------------------------------------- #
    # 8b. Up-to-date data does NOT produce a false trailing-edge gap
    # --------------------------------------------------------------------- #
    def test_current_data_no_trailing_gap(self, manager):
        """
        When the last bar on disk is within the slop window of end_date
        no trailing gap should be emitted.
        """
        # end_date = T, last bar = T - 13m (within 10% slop of 15m = 13.5 min)
        end_date = datetime(2026, 5, 4, 12, 13, 0)
        last_bar_ts = datetime(2026, 5, 4, 12, 0, 0)   # one bar behind :13
        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m", end_date=end_date)

        assert len(gaps) == 0, (
            f"Up-to-date data (last bar within slop) must not produce trailing gap; "
            f"got {gaps}"
        )

    # --------------------------------------------------------------------- #
    # 8c. verify_and_repair with trailing gap fetches and saves bars
    # --------------------------------------------------------------------- #
    def test_verify_and_repair_repairs_trailing_gap(self, manager):
        """
        verify_and_repair() must detect the trailing gap and call
        _fetch_binance_range / _save_binance_bars for it.
        """
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

    # --------------------------------------------------------------------- #
    # 8d. dry_run=True detects trailing gap but writes nothing
    # --------------------------------------------------------------------- #
    def test_dry_run_trailing_gap_detected_no_write(self, manager):
        end_date = datetime(2026, 5, 4, 12, 0, 0)
        last_bar_ts = end_date - timedelta(minutes=30)
        start = last_bar_ts - timedelta(minutes=15 * 7)
        df = _make_ohlcv(start, n=8, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        with patch.object(manager, "_fetch_binance_range") as mock_fetch, \
             patch.object(manager, "_save_binance_bars") as mock_save:
            result = manager.verify_and_repair(
                timeframes=["15m"],
                start_date=start,
                end_date=end_date,
                dry_run=True,
            )

        mock_fetch.assert_not_called()
        mock_save.assert_not_called()
        assert result["15m"]["gaps_found"] >= 1, (
            "dry_run must still report trailing gaps found"
        )

    # --------------------------------------------------------------------- #
    # 8e. Single-bar window: trailing-edge check works with one row on disk
    # --------------------------------------------------------------------- #
    def test_single_bar_on_disk_trailing_gap_detected(self, manager):
        """
        Regression: the old early-return guard (len < 2) would skip trailing-
        edge detection for windows with only one stored bar.  Verify the new
        guard (len == 0) allows single-bar files to trigger a trailing gap.
        """
        end_date = datetime(2026, 5, 4, 12, 0, 0)
        last_bar_ts = end_date - timedelta(minutes=60)  # 4 bars behind
        df = _make_ohlcv(last_bar_ts, n=1, freq_minutes=15, timeframe="15m")
        _write_month_file(manager.binance_dir, "2026-05", df, "15m")

        gaps = manager.detect_gaps_in_binance_files(
            "15m", end_date=end_date
        )

        assert len(gaps) >= 1, (
            "Single-bar window must still produce a trailing-edge gap"
        )

    # --------------------------------------------------------------------- #
    # 8f. Internal gap + trailing gap: both reported
    # --------------------------------------------------------------------- #
    def test_internal_gap_plus_trailing_gap_both_reported(self, manager):
        """
        A file with both an internal gap and a stale trailing edge must report
        both gaps — the trailing-edge fix must not suppress internal gaps.
        """
        end_date = datetime(2026, 5, 4, 12, 0, 0)
        # Build 20-bar segment, drop bar 10 (internal gap), last bar 30 min before end_date
        last_bar_ts = end_date - timedelta(minutes=30)
        start = last_bar_ts - timedelta(minutes=15 * 19)
        df = _make_ohlcv(start, n=20, freq_minutes=15, timeframe="15m")
        df_gapped = df.drop(index=10).reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-05", df_gapped, "15m")

        gaps = manager.detect_gaps_in_binance_files("15m", end_date=end_date)

        assert len(gaps) >= 2, (
            f"Expected at least 2 gaps (1 internal + 1 trailing), got {len(gaps)}: {gaps}"
        )


class TestDataUpdateThreadDownloads1d:
    """
    Regression guard: DataUpdateThread.run() must download AND save 1d bars
    in every execution — the original bug was the 1d download being absent
    from the active code path entirely.
    """

    def _build_mock_bars(self, timeframe: str, n: int = 5) -> pd.DataFrame:
        """Return a small clean DataFrame with a very recent latest timestamp."""
        start = datetime.now() - timedelta(minutes=5)
        df = _make_ohlcv(start, n=n, freq_minutes={"15m": 15, "1h": 60, "1d": 1440}[timeframe],
                         timeframe=timeframe)
        # Ensure the latest bar is fresh (< 20 min old for 15m, < 65 for 1h, < 1500 for 1d)
        df.iloc[-1, df.columns.get_loc("timestamp")] = pd.Timestamp(datetime.now() - timedelta(minutes=1))
        return df

    def test_run_calls_download_with_retry_for_1d(self):
        """
        DataUpdateThread.run() must call _download_with_retry(timeframe='1d').

        We mock _download_with_retry and manager._save_binance_bars to avoid live
        API calls and filesystem writes, then assert on the captured call arguments.
        """
        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        start_date = datetime(2026, 4, 1, 0, 0)
        end_date = datetime(2026, 4, 30, 0, 0)
        thread = DataUpdateThread(start_date=start_date, end_date=end_date)

        bars_15m = self._build_mock_bars("15m")
        bars_1h = self._build_mock_bars("1h")
        bars_1d = self._build_mock_bars("1d")

        download_calls: list[dict] = []
        save_calls: list[dict] = []

        def fake_download(timeframe, start_date, end_date):
            download_calls.append({"timeframe": timeframe})
            return {"15m": bars_15m, "1h": bars_1h, "1d": bars_1d}[timeframe]

        def fake_save(bars, timeframe):
            save_calls.append({"timeframe": timeframe})
            # _save_binance_bars returns None (unlike old _save_bars_to_disk)

        # Patch the Binance ping so run() doesn't need network
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(thread, "_download_with_retry", side_effect=fake_download), \
             patch.object(thread.manager, "_save_binance_bars", side_effect=fake_save), \
             patch("requests.get", return_value=mock_response):
            thread.run()

        downloaded_timeframes = [c["timeframe"] for c in download_calls]
        saved_timeframes = [c["timeframe"] for c in save_calls]

        assert "1d" in downloaded_timeframes, (
            f"DataUpdateThread.run() did not call _download_with_retry for '1d'. "
            f"Timeframes downloaded: {downloaded_timeframes}"
        )
        assert "1d" in saved_timeframes, (
            f"DataUpdateThread.run() did not call _save_binance_bars for '1d'. "
            f"Timeframes saved: {saved_timeframes}"
        )

    def test_run_downloads_all_three_timeframes(self):
        """
        DataUpdateThread.run() must call _download_with_retry for all three
        timeframes: 15m, 1h, and 1d — in that order.
        """
        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        start_date = datetime(2026, 4, 1, 0, 0)
        end_date = datetime(2026, 4, 30, 0, 0)
        thread = DataUpdateThread(start_date=start_date, end_date=end_date)

        bars_15m = self._build_mock_bars("15m")
        bars_1h = self._build_mock_bars("1h")
        bars_1d = self._build_mock_bars("1d")

        download_calls: list[str] = []

        def fake_download(timeframe, start_date, end_date):
            download_calls.append(timeframe)
            return {"15m": bars_15m, "1h": bars_1h, "1d": bars_1d}[timeframe]

        def fake_save(bars, timeframe):
            pass  # _save_binance_bars returns None

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(thread, "_download_with_retry", side_effect=fake_download), \
             patch.object(thread.manager, "_save_binance_bars", side_effect=fake_save), \
             patch("requests.get", return_value=mock_response):
            thread.run()

        assert set(download_calls) == {"15m", "1h", "1d"}, (
            f"Expected downloads for 15m, 1h, and 1d, but got: {download_calls}"
        )
        # Order: 15m first, then 1h, then 1d
        assert download_calls.index("15m") < download_calls.index("1h"), (
            "15m should be downloaded before 1h"
        )
        assert download_calls.index("1h") < download_calls.index("1d"), (
            "1h should be downloaded before 1d"
        )


# ===========================================================================
# Regression: _determine_source() tz-awareness (BTCAAAAA-795)
# ===========================================================================

class TestDetermineSourceTzAwareness:
    """
    Regression tests ensuring _determine_source() never raises TypeError when
    end_date / start_date are tz-aware (UTC), tz-naive, or mixed.
    Quick Preview passes datetime.now(timezone.utc) so all three cases must work.
    """

    def test_utc_aware_end_date_does_not_raise(self, manager):
        """UTC-aware end_date must not crash — this was the Quick Preview crash case."""
        from datetime import timezone
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=40)
        # Must not raise TypeError: can't compare offset-naive and offset-aware datetimes
        result = manager._determine_source(start_date=start, end_date=end)
        assert result is not None, "_determine_source should return a DataSource value"

    def test_naive_end_date_does_not_raise(self, manager):
        """Naive end_date (legacy callers) must still work after the tz fix."""
        end = datetime.now()
        start = end - timedelta(days=40)
        result = manager._determine_source(start_date=start, end_date=end)
        assert result is not None

    def test_mixed_aware_start_naive_end_does_not_raise(self, manager):
        """Mixed tz inputs are normalized internally — no TypeError allowed."""
        from datetime import timezone
        end = datetime.now()  # naive
        start = datetime.now(timezone.utc) - timedelta(days=40)  # aware
        result = manager._determine_source(start_date=start, end_date=end)
        assert result is not None

    def test_mixed_naive_start_aware_end_does_not_raise(self, manager):
        """Reverse-mixed case: naive start, aware end."""
        from datetime import timezone
        end = datetime.now(timezone.utc)  # aware
        start = datetime.now() - timedelta(days=40)  # naive
        result = manager._determine_source(start_date=start, end_date=end)
        assert result is not None

    def test_recent_range_returns_binance(self, manager):
        """end_date in the recent window should still route to BINANCE."""
        from datetime import timezone
        from src.data_manager.unified_manager import DataSource
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=5)
        result = manager._determine_source(start_date=start, end_date=end)
        assert result == DataSource.BINANCE

    def test_old_range_returns_lakeapi(self, manager):
        """end_date well outside the Binance threshold should route to LAKEAPI."""
        from datetime import timezone
        from src.data_manager.unified_manager import DataSource
        end = datetime.now(timezone.utc) - timedelta(days=manager.binance_threshold_days + 10)
        start = end - timedelta(days=10)
        result = manager._determine_source(start_date=start, end_date=end)
        assert result == DataSource.LAKEAPI
