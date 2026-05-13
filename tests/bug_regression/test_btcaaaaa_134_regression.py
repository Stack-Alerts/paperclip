"""
Regression tests for BTCAAAAA-134 (Bug 5): Cross-month bar contamination
in Binance parquet files.

Issue: BTCAAAAA-134
Components:
  - src/data_manager/unified_manager.py (_save_binance_bars cross-month guard)
  - scripts/fix_month_boundary_parquet.py (one-time migration + helpers)

Root cause (Bug 5): Monthly parquet files could contain bars whose timestamp
belongs to a *different* month than the file's directory/name. The fix adds a
cross-month guard in _save_binance_bars() and provides a migration script.

This file contains standalone tests exercising:
  - The month-splitting behavior in _save_binance_bars
  - The month-boundary file invariant (each file contains only its month)
  - The fix script's helper functions (parse_timeframe_from_name, atomic_write)
  - The fix script's run() logic (month-boundary detection and rewrite)
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-134"),
    pytest.mark.regression,
]

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from fix_month_boundary_parquet import (  # noqa: E402
    parse_timeframe_from_name,
    atomic_write,
    run as run_fix_script,
)


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
# _save_binance_bars — month-splitting behavior
# =========================================================================== #


class TestSaveBinanceBars:
    """
    Verify that _save_binance_bars correctly splits multi-month data into
    separate monthly parquet files.
    """

    def test_same_month_bars_save_ok(self, manager):
        bars = _make_ohlcv(
            start=datetime(2026, 5, 1, 0, 0, 0),
            n=10,
            freq_minutes=15,
            timeframe="15m",
        )
        manager._save_binance_bars(bars, "15m")

        file_path = manager.binance_dir / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet"
        assert file_path.exists()
        on_disk = pd.read_parquet(file_path)
        assert len(on_disk) == 10

    def test_empty_dataframe_no_op(self, manager):
        empty = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        manager._save_binance_bars(empty, "15m")
        assert list(manager.binance_dir.iterdir()) == []

    def test_multi_month_bars_split_correctly(self, manager):
        april_bars = _make_ohlcv(
            start=datetime(2026, 4, 30, 23, 0, 0),
            n=4,
            freq_minutes=15,
            timeframe="15m",
        )
        may_bars = _make_ohlcv(
            start=datetime(2026, 5, 1, 0, 0, 0),
            n=4,
            freq_minutes=15,
            timeframe="15m",
        )
        combined = pd.concat([april_bars, may_bars], ignore_index=True)
        manager._save_binance_bars(combined, "15m")

        april_file = manager.binance_dir / "2026-04" / "BTCUSDT_PERP_15m_2026-04.parquet"
        may_file = manager.binance_dir / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet"
        assert april_file.exists()
        assert may_file.exists()
        assert len(pd.read_parquet(april_file)) == 4
        assert len(pd.read_parquet(may_file)) == 4

    def test_idempotent_save(self, manager):
        bars = _make_ohlcv(
            start=datetime(2026, 5, 1, 0, 0, 0),
            n=5,
            freq_minutes=15,
            timeframe="15m",
        )
        manager._save_binance_bars(bars, "15m")
        manager._save_binance_bars(bars, "15m")
        file_path = manager.binance_dir / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet"
        on_disk = pd.read_parquet(file_path)
        assert len(on_disk) == 5  # deduped


# =========================================================================== #
# Month-boundary file invariant
# =========================================================================== #


class TestMonthBoundaryFileInvariant:
    """
    Verify that after _save_binance_bars, each monthly file contains ONLY
    bars belonging to that month (the invariant that BTCAAAAA-134 protects).
    """

    def test_april_bars_only_in_april_file(self, manager):
        april_bars = _make_ohlcv(
            start=datetime(2026, 4, 29, 23, 0, 0),
            n=6,
            freq_minutes=15,
            timeframe="15m",
        )
        may_bars = _make_ohlcv(
            start=datetime(2026, 5, 1, 0, 0, 0),
            n=6,
            freq_minutes=15,
            timeframe="15m",
        )
        combined = pd.concat([april_bars, may_bars], ignore_index=True)
        manager._save_binance_bars(combined, "15m")

        may_file = manager.binance_dir / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet"
        may_df = pd.read_parquet(may_file)
        for ts in may_df["timestamp"]:
            m = pd.Timestamp(ts).to_period("M")
            assert m == pd.Period("2026-05", freq="M"), (
                f"Found {ts} (period {m}) in May file"
            )

    def test_boundary_crossing_midnight_bars(self, manager):
        """
        Bars at the exact UTC midnight boundary (April 30 23:45 through
        May 1 00:00) must be placed in the correct month file.
        """
        boundary_bars = _make_ohlcv(
            start=datetime(2026, 4, 30, 23, 30, 0),
            n=4,
            freq_minutes=15,
            timeframe="15m",
        )
        manager._save_binance_bars(boundary_bars, "15m")

        april_file = manager.binance_dir / "2026-04" / "BTCUSDT_PERP_15m_2026-04.parquet"
        may_file = manager.binance_dir / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet"

        april_df = pd.read_parquet(april_file) if april_file.exists() else pd.DataFrame()
        may_df = pd.read_parquet(may_file) if may_file.exists() else pd.DataFrame()

        for ts in april_df["timestamp"]:
            assert pd.Timestamp(ts).to_period("M") == pd.Period("2026-04", freq="M")
        for ts in may_df["timestamp"]:
            assert pd.Timestamp(ts).to_period("M") == pd.Period("2026-05", freq="M")

        assert len(april_df) == 2
        assert len(may_df) == 2


# =========================================================================== #
# Fix script helpers
# =========================================================================== #


class TestParseTimeframeFromName:
    def test_standard_name(self):
        assert parse_timeframe_from_name("BTCUSDT_PERP_15m_2026-05.parquet") == "15m"

    def test_one_hour(self):
        assert parse_timeframe_from_name("BTCUSDT_PERP_1h_2026-05.parquet") == "1h"

    def test_one_day(self):
        assert parse_timeframe_from_name("BTCUSDT_PERP_1d_2026-05.parquet") == "1d"

    def test_unknown_pattern_returns_unknown(self):
        assert parse_timeframe_from_name("weird_file.parquet") == "unknown"

    def test_custom_timeframe(self):
        assert parse_timeframe_from_name("BTCUSDT_PERP_5m_2026-06.parquet") == "5m"


class TestAtomicWrite:
    def test_writes_and_replaces(self, tmp_path):
        df = pd.DataFrame({"a": [1, 2, 3]})
        dest = tmp_path / "test.parquet"
        atomic_write(df, dest)
        assert dest.exists()
        assert not dest.with_suffix(".parquet.tmp").exists()
        result = pd.read_parquet(dest)
        assert len(result) == 3

    def test_overwrites_existing(self, tmp_path):
        old = pd.DataFrame({"a": [1]})
        new = pd.DataFrame({"a": [4, 5, 6]})
        dest = tmp_path / "test.parquet"
        atomic_write(old, dest)
        atomic_write(new, dest)
        result = pd.read_parquet(dest)
        assert len(result) == 3


# =========================================================================== #
# Fix script run()
# =========================================================================== #


class TestFixScriptRun:
    """
    Test run() from fix_month_boundary_parquet.py — scan, detect, rewrite.
    """

    def test_dry_run_no_changes_for_clean_data(self, tmp_path, capsys):
        _write_month_file(tmp_path, "2026-05",
                          _make_ohlcv(start=datetime(2026, 5, 1, 0, 0, 0), n=10))
        with _patched_binance_dir(tmp_path):
            run_fix_script(dry_run=True)

    def test_dry_run_detects_contamination(self, tmp_path, capsys):
        april_bars = _make_ohlcv(start=datetime(2026, 4, 30, 23, 15, 0), n=3)
        _write_month_file(tmp_path, "2026-05", april_bars)
        with _patched_binance_dir(tmp_path):
            run_fix_script(dry_run=True)
        captured = capsys.readouterr()
        assert "CONTAMINATED" in captured.out

    def test_fixes_contaminated_file(self, tmp_path):
        april_bars = _make_ohlcv(start=datetime(2026, 4, 30, 23, 0, 0), n=4)
        _write_month_file(tmp_path, "2026-05", april_bars)
        with _patched_binance_dir(tmp_path):
            run_fix_script(dry_run=False)

        april_file = tmp_path / "2026-04" / "BTCUSDT_PERP_15m_2026-04.parquet"
        assert april_file.exists()
        april_df = pd.read_parquet(april_file)
        assert len(april_df) == 4
        for ts in april_df["timestamp"]:
            assert pd.Timestamp(ts).to_period("M") == pd.Period("2026-04", freq="M")

    def test_idempotent(self, tmp_path):
        mixed = pd.concat([
            _make_ohlcv(start=datetime(2026, 4, 30, 23, 0, 0), n=2),
            _make_ohlcv(start=datetime(2026, 5, 1, 0, 0, 0), n=2),
        ], ignore_index=True)
        _write_month_file(tmp_path, "2026-05", mixed)

        with _patched_binance_dir(tmp_path):
            run_fix_script(dry_run=False)
            run_fix_script(dry_run=False)

        assert (tmp_path / "2026-04" / "BTCUSDT_PERP_15m_2026-04.parquet").exists()
        assert (tmp_path / "2026-05" / "BTCUSDT_PERP_15m_2026-05.parquet").exists()

    def test_merges_contaminated_into_existing_file(self, tmp_path):
        """Existing April file should receive the migrated April bars."""
        existing_april = _make_ohlcv(start=datetime(2026, 4, 30, 22, 0, 0), n=2)
        _write_month_file(tmp_path, "2026-04", existing_april)

        contaminated = _make_ohlcv(start=datetime(2026, 4, 30, 23, 0, 0), n=4)
        _write_month_file(tmp_path, "2026-05", contaminated)

        with _patched_binance_dir(tmp_path):
            run_fix_script(dry_run=False)

        april_file = tmp_path / "2026-04" / "BTCUSDT_PERP_15m_2026-04.parquet"
        april_df = pd.read_parquet(april_file)
        assert len(april_df) == 6  # 2 existing + 4 migrated


# --------------------------------------------------------------------------- #
# Context manager: temporarily replace fix_month_boundary_parquet.BINANCE_DIR
# --------------------------------------------------------------------------- #


@contextmanager
def _patched_binance_dir(tmp_path: Path):
    import fix_month_boundary_parquet as fmp

    original = fmp.BINANCE_DIR
    fmp.BINANCE_DIR = tmp_path
    try:
        yield
    finally:
        fmp.BINANCE_DIR = original
