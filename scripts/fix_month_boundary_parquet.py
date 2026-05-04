#!/usr/bin/env python3
"""
One-time migration: fix month-boundary bar contamination in Binance parquet files.

Problem (Bug 5 from BTCAAAAA-134):
  Monthly parquet files may contain bars whose timestamp belongs to a *different*
  month than the file's directory/name.  For example:
    data/binance/2026-05/BTCUSDT_PERP_15m_2026-05.parquet
  currently starts at 2026-04-29 23:15 and contains 99 April bars.

This script:
  1. Scans every parquet file under data/binance/
  2. For each file, splits rows by their correct calendar month
  3. Rewrites each affected month file atomically (temp file + os.replace)
  4. Prints a summary of what was moved

Safe to run multiple times (idempotent after first pass).

Usage:
    python scripts/fix_month_boundary_parquet.py [--dry-run]
"""

import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict

import pandas as pd

# Ensure project root is on the path so src.data_manager imports work.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_manager.config import PROJECT_ROOT as CFG_ROOT  # noqa: E402 (after sys.path fix)

BINANCE_DIR = CFG_ROOT / "data" / "binance"


def collect_all_parquet_files():
    """Return all .parquet files under BINANCE_DIR (skip .parquet.tmp)."""
    return sorted(BINANCE_DIR.rglob("*.parquet"))


def parse_timeframe_from_name(name: str) -> str:
    """Extract timeframe from filename like BTCUSDT_PERP_15m_2026-05.parquet."""
    parts = name.replace(".parquet", "").split("_")
    # Parts: BTCUSDT, PERP, <tf>, <YYYY-MM>
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


def atomic_write(df: pd.DataFrame, dest: Path, compression: str = "snappy") -> None:
    """Write *df* to *dest* atomically using a temp file + os.replace."""
    tmp = dest.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, compression=compression, index=False)
    os.replace(tmp, dest)


def run(dry_run: bool = False) -> None:
    files = collect_all_parquet_files()
    if not files:
        print(f"No parquet files found under {BINANCE_DIR}")
        return

    print(f"Scanning {len(files)} parquet file(s) under {BINANCE_DIR}")

    # Collect all data keyed by (timeframe, month_period) for rewriting.
    # Structure: {timeframe: {period_str: [DataFrame, ...]}}
    data_by_tf_month: dict = defaultdict(lambda: defaultdict(list))

    for fpath in files:
        tf = parse_timeframe_from_name(fpath.name)
        try:
            df = pd.read_parquet(fpath)
        except Exception as exc:
            print(f"  ERROR reading {fpath}: {exc} — skipping")
            continue

        if df.empty:
            continue

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["_ym"] = df["timestamp"].dt.to_period("M")

        # Detect which months are actually represented in this file.
        months_in_file = df["_ym"].unique()
        # Derive expected month from the file path (directory name).
        expected_month_str = fpath.parent.name  # e.g. '2026-05'

        contaminated = [str(m) for m in months_in_file if str(m) != expected_month_str]
        if contaminated:
            print(f"  CONTAMINATED {fpath.name}: contains bars from {contaminated}")

        for period, group in df.groupby("_ym"):
            data_by_tf_month[tf][str(period)].append(group.drop(columns=["_ym"]))

    # Now rewrite each (timeframe, month) bucket.
    print("\nRewriting files...")
    total_moved = 0

    for tf, month_map in data_by_tf_month.items():
        for month_str, frames in month_map.items():
            month_dir = BINANCE_DIR / month_str
            dest = month_dir / f"BTCUSDT_PERP_{tf}_{month_str}.parquet"

            combined = pd.concat(frames, ignore_index=True)
            combined = (
                combined.sort_values("timestamp")
                .drop_duplicates(subset=["timestamp"])
                .reset_index(drop=True)
            )

            # Check if existing file has a different bar count.
            existing_count = 0
            if dest.exists():
                try:
                    existing_df = pd.read_parquet(dest)
                    existing_count = len(existing_df)
                except Exception:
                    pass

            if existing_count == len(combined):
                # Nothing changed.
                continue

            total_moved += abs(len(combined) - existing_count)
            print(f"  {'[DRY-RUN] ' if dry_run else ''}Writing {dest.name}: {existing_count} → {len(combined)} bars")

            if not dry_run:
                month_dir.mkdir(parents=True, exist_ok=True)
                atomic_write(combined, dest)

                # Verify
                verify = pd.read_parquet(dest)
                assert len(verify) == len(combined), (
                    f"Verification FAILED for {dest}: wrote {len(combined)}, disk has {len(verify)}"
                )

    print(f"\nDone. {total_moved} bar(s) moved/rebalanced across month boundaries.")
    if dry_run:
        print("(No files were actually written — re-run without --dry-run to apply.)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix month-boundary bar contamination in Binance parquet files.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
