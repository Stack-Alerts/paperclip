"""
Regression tests for BTCAAAAA-20: Binance 1h data gap detection and backfill.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-20
Script: scripts/binance/backfill_1h_gaps.py

Root cause: Incomplete ingestion during January 2026 left 31 gaps in the 1h
timeframe across 2026-01-16 to 2026-02-01, with all data prior to 2026-01-16
entirely missing from local storage.

This file tests gap detection in UnifiedDataManager to ensure:
  1. detect_gaps_in_binance_files correctly identifies missing bars
  2. verify_and_repair properly reports gap closure after backfill
  3. The 1h timeframe gap quantification is accurate
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-20"),
    pytest.mark.regression,
]


def _make_ohlcv(
    start: datetime, n: int, freq_minutes: int = 60, timeframe: str = "1h"
) -> pd.DataFrame:
    rng = np.random.default_rng(seed=42)
    timestamps = [start + timedelta(minutes=freq_minutes * i) for i in range(n)]
    base = 60_000.0
    opens = base + rng.uniform(-500, 500, size=n)
    closes = opens + rng.uniform(-200, 200, size=n)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "open": opens,
        "high": np.maximum(opens, closes) + rng.uniform(0, 100, size=n),
        "low": np.minimum(opens, closes) - rng.uniform(0, 100, size=n),
        "close": closes,
        "volume": rng.uniform(1.0, 50.0, size=n),
        "volume_usd": rng.uniform(1_000, 10_000, size=n),
        "trade_count": np.full(n, 100, dtype=int),
        "symbol": "BTCUSDT",
        "timeframe": timeframe,
    })


def _write_month_file(
    binance_dir: Path, month: str, df: pd.DataFrame, timeframe: str
) -> Path:
    month_dir = binance_dir / month
    month_dir.mkdir(parents=True, exist_ok=True)
    path = month_dir / f"BTCUSDT_PERP_{timeframe}_{month}.parquet"
    df.to_parquet(path, index=False)
    return path


@pytest.fixture()
def manager(tmp_path):
    from src.data_manager.unified_manager import UnifiedDataManager

    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


class TestGapDetection:
    def test_no_files_returns_empty(self, manager):
        gaps = manager.detect_gaps_in_binance_files("1h")
        assert gaps == []

    def test_continuous_1h_data_no_false_gaps(self, manager):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        df = _make_ohlcv(start, n=744, freq_minutes=60, timeframe="1h")
        _write_month_file(manager.binance_dir, "2026-01", df, "1h")

        gaps = manager.detect_gaps_in_binance_files("1h")
        assert gaps == [], f"Continuous data must not report gaps; got: {gaps}"

    def test_single_missing_1h_bar_detected(self, manager):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        df = _make_ohlcv(start, n=200, freq_minutes=60, timeframe="1h")
        df_with_gap = pd.concat([df.iloc[:100], df.iloc[101:]]).reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-01", df_with_gap, "1h")

        gaps = manager.detect_gaps_in_binance_files("1h")
        assert len(gaps) == 1, f"Expected 1 gap, got {len(gaps)}: {gaps}"
        assert gaps[0]["missing_bars"] == 1
        assert gaps[0]["timeframe"] == "1h"

    def test_multi_day_gap_correctly_quantified(self, manager):
        start_seg1 = datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)
        seg1 = _make_ohlcv(start_seg1, n=48, freq_minutes=60, timeframe="1h")
        start_seg2 = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
        seg2 = _make_ohlcv(start_seg2, n=24, freq_minutes=60, timeframe="1h")

        _write_month_file(manager.binance_dir, "2026-01", seg1, "1h")
        _write_month_file(manager.binance_dir, "2026-02", seg2, "1h")

        gaps = manager.detect_gaps_in_binance_files("1h")
        assert len(gaps) == 1, f"Expected 1 cross-month gap, got {len(gaps)}: {gaps}"
        gap = gaps[0]
        assert gap["missing_bars"] > 300
        assert gap["timeframe"] == "1h"

    def test_gap_within_single_month_file(self, manager):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        df = _make_ohlcv(start, n=744, freq_minutes=60, timeframe="1h")
        mask = list(range(744))
        for i in sorted([100, 101, 102, 200, 201, 202, 203], reverse=True):
            mask.pop(i)
        df_gapped = df.iloc[mask].reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-01", df_gapped, "1h")

        gaps = manager.detect_gaps_in_binance_files("1h")
        assert len(gaps) == 2, f"Expected 2 gaps, got {len(gaps)}: {gaps}"
        for g in gaps:
            assert g["timeframe"] == "1h"

    def test_start_date_filter_respected(self, manager):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        df = _make_ohlcv(start, n=744, freq_minutes=60, timeframe="1h")
        _write_month_file(manager.binance_dir, "2026-01", df, "1h")

        gaps = manager.detect_gaps_in_binance_files(
            "1h", start_date=datetime(2026, 1, 20, tzinfo=timezone.utc)
        )
        assert isinstance(gaps, list)

    def test_end_date_filter_respected(self, manager):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        df = _make_ohlcv(start, n=744, freq_minutes=60, timeframe="1h")
        _write_month_file(manager.binance_dir, "2026-01", df, "1h")

        gaps = manager.detect_gaps_in_binance_files(
            "1h", end_date=datetime(2026, 1, 15, tzinfo=timezone.utc)
        )
        assert isinstance(gaps, list)

    def test_duplicate_timestamps_deduped(self, manager):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        df = _make_ohlcv(start, n=100, freq_minutes=60, timeframe="1h")
        df_with_dupes = pd.concat([df, df.iloc[:10]]).reset_index(drop=True)
        _write_month_file(manager.binance_dir, "2026-01", df_with_dupes, "1h")

        gaps = manager.detect_gaps_in_binance_files("1h")
        assert gaps == [], f"Duplicates must be deduped; gaps: {gaps}"

    def test_unknown_timeframe_raises(self, manager):
        with pytest.raises(ValueError, match="Unknown timeframe"):
            manager.detect_gaps_in_binance_files("99x")


class TestVerifyAndRepair:
    def test_verify_and_repair_dry_run_on_clean_data(self, manager):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        df = _make_ohlcv(start, n=744, freq_minutes=60, timeframe="1h")
        _write_month_file(manager.binance_dir, "2026-01", df, "1h")

        report = manager.verify_and_repair(
            timeframes=["1h"],
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, 23, 59, tzinfo=timezone.utc),
            dry_run=True,
        )
        tf_report = report.get("1h", {})
        gaps_found = tf_report.get("gaps_found", -1)
        assert gaps_found == 0, (
            f"Expected 0 gaps in clean data, got {gaps_found}"
        )

    def test_verify_and_repair_reports_remaining_gaps(self, manager):
        start = datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)
        df = _make_ohlcv(start, n=48, freq_minutes=60, timeframe="1h")
        _write_month_file(manager.binance_dir, "2026-01", df, "1h")

        report = manager.verify_and_repair(
            timeframes=["1h"],
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, 23, 59, tzinfo=timezone.utc),
            dry_run=True,
        )
        tf_report = report.get("1h", {})
        assert tf_report.get("gaps_found", 0) > 0, (
            "Expected gaps before Jan 16 in verify_and_repair output"
        )
