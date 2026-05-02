"""
1h Gap Backfill — Binance Public Data Archive

Fills identified 1-hour OHLCV gaps in the stored Binance parquet files using
data fetched from the Binance Futures API (BTCUSDT perpetual, /fapi/v1/klines).

Background
----------
The gap analysis on BTCAAAAA-20 found 31 gaps in the 1h timeframe, all within
January 2026 (2026-01-16 to 2026-02-01).  The root cause was incomplete
ingestion during that period.  Additionally, data prior to 2026-01-16 is
entirely missing from local storage.

Source selection (per BTCAAAAA-19 research)
-------------------------------------------
- Primary: Binance Futures API (/fapi/v1/klines) — same exchange already used
  for all other stored data, free, no API key required, returns 1h klines
  with explicit startTime/endTime.  All dates in scope (~Jan 2026 = ~107 days
  old) are well within Binance Futures API's deep historical window.
- Fallback: Binance Public Data Archive (data.binance.vision) for spot klines
  if Futures API ever stops serving old data.

What this script does
---------------------
1. Downloads complete 1h BTCUSDT PERP klines for Jan 2026 (plus any earlier
   months the user specifies on the CLI) using UnifiedDataManager._fetch_binance_range().
2. Merges the downloaded bars into the monthly parquet files via
   UnifiedDataManager._save_binance_bars() (deduplicated, sorted, atomic write).
3. After all downloads, calls verify_and_repair(dry_run=True) on the 1h
   timeframe to confirm no gaps remain.

Usage
-----
    # Fill Jan 2026 (default)
    python scripts/binance/backfill_1h_gaps.py

    # Fill specific year/month range
    python scripts/binance/backfill_1h_gaps.py --from 2025-12 --to 2026-01

    # Dry run — report gaps only, no writes
    python scripts/binance/backfill_1h_gaps.py --dry-run

Author: DataEngineer (BTCAAAAA-20)
Date:   2026-05-02
"""

from __future__ import annotations

import argparse
import sys
from calendar import monthrange
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root on sys.path
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.data_manager.unified_manager import UnifiedDataManager  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iter_months(from_ym: tuple[int, int], to_ym: tuple[int, int]):
    """Yield (year, month) tuples inclusive between from_ym and to_ym."""
    y, m = from_ym
    while (y, m) <= to_ym:
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Return (first_ts, last_ts) for the given calendar month."""
    first = datetime(year, month, 1, 0, 0, 0)
    last_day = monthrange(year, month)[1]
    last = datetime(year, month, last_day, 23, 0, 0)  # last full 1h open
    return first, last


def parse_ym(s: str) -> tuple[int, int]:
    """Parse 'YYYY-MM' into (year, month)."""
    parts = s.split("-")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"Expected YYYY-MM, got '{s}'")
    return int(parts[0]), int(parts[1])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill 1h BTCUSDT PERP gaps from Binance Futures API"
    )
    parser.add_argument(
        "--from", dest="from_ym", type=parse_ym, default=(2026, 1),
        metavar="YYYY-MM",
        help="First month to (re-)download (default: 2026-01)",
    )
    parser.add_argument(
        "--to", dest="to_ym", type=parse_ym, default=(2026, 1),
        metavar="YYYY-MM",
        help="Last month to (re-)download (default: 2026-01)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Detect gaps only; do not download or write data",
    )
    parser.add_argument(
        "--symbol", default="BTCUSDT",
        help="Binance symbol (default: BTCUSDT)",
    )
    args = parser.parse_args()

    mgr = UnifiedDataManager(mode="backtest")

    print()
    print("=" * 70)
    print("1H GAP BACKFILL — BINANCE FUTURES API")
    print("=" * 70)
    print(f"Range  : {args.from_ym[0]:04d}-{args.from_ym[1]:02d} → "
          f"{args.to_ym[0]:04d}-{args.to_ym[1]:02d}")
    print(f"Symbol : {args.symbol} (PERP futures)")
    print(f"Mode   : {'DRY RUN — no writes' if args.dry_run else 'LIVE — will write parquet files'}")
    print("=" * 70)

    months = list(iter_months(args.from_ym, args.to_ym))
    total_bars_fetched = 0
    total_bars_saved = 0

    for year, month in months:
        start_ts, end_ts = month_bounds(year, month)
        month_str = f"{year:04d}-{month:02d}"

        print(f"\n{'─' * 60}")
        print(f"Month: {month_str}  ({start_ts.date()} → {end_ts.date()})")
        print(f"{'─' * 60}")

        if args.dry_run:
            # Just check existing coverage for this month
            gaps = mgr.detect_gaps_in_binance_files(
                "1h", start_date=start_ts, end_date=end_ts + timedelta(hours=1)
            )
            # Also check if the month file exists at all
            month_dir = mgr.binance_dir / month_str
            file_path = month_dir / f"BTCUSDT_PERP_1h_{month_str}.parquet"
            if not file_path.exists():
                print(f"  [DRY RUN] No parquet file found for {month_str} — full month would be downloaded")
            elif gaps:
                total_missing = sum(g["missing_bars"] for g in gaps)
                print(f"  [DRY RUN] {len(gaps)} gap(s) detected, ~{total_missing} missing bars:")
                for g in gaps:
                    print(f"    {g['gap_start']} → {g['gap_end']} "
                          f"(duration={g['duration']}, missing={g['missing_bars']})")
            else:
                print(f"  [DRY RUN] No gaps found in {month_str} — data appears complete")
            continue

        # ---- Live mode: fetch full month from Binance Futures API ----
        print(f"  Fetching 1h klines from Binance Futures API ...")
        try:
            df = mgr._fetch_binance_range(
                timeframe="1h",
                start_ts=start_ts,
                end_ts=end_ts,
                symbol=args.symbol,
                futures=True,
                batch_size=1500,
            )
        except Exception as exc:
            print(f"  ERROR fetching {month_str}: {exc}")
            continue

        if df.empty:
            print(f"  WARNING: Binance returned no data for {month_str} — skipping")
            continue

        total_bars_fetched += len(df)
        print(f"  Fetched {len(df)} bars: "
              f"{df['timestamp'].min()} → {df['timestamp'].max()}")

        # Merge into monthly parquet (handles existing data, deduplication, sort)
        print(f"  Saving / merging into parquet ...")
        mgr._save_binance_bars(df, "1h")
        total_bars_saved += len(df)

    # ---- Post-backfill verification ----
    print()
    print("=" * 70)
    print("POST-BACKFILL VERIFICATION")
    print("=" * 70)

    verify_start = datetime(args.from_ym[0], args.from_ym[1], 1)
    verify_end_year, verify_end_month = args.to_ym
    verify_end = datetime(
        verify_end_year,
        verify_end_month,
        monthrange(verify_end_year, verify_end_month)[1],
        23, 59, 59,
    )

    if args.dry_run:
        print("(dry-run — skipping live verify_and_repair)")
        gaps = mgr.detect_gaps_in_binance_files(
            "1h", start_date=verify_start, end_date=verify_end
        )
        if gaps:
            print(f"  REMAINING GAPS ({len(gaps)}):")
            for g in gaps:
                print(f"    {g['gap_start']} → {g['gap_end']} "
                      f"(~{g['missing_bars']} bars)")
        else:
            print("  No gaps detected in the specified range.")
    else:
        # Run verify_and_repair in dry_run=True mode so it only reports
        # (we already wrote the data above; this is a read-only check)
        print("Running verify_and_repair(dry_run=True) to confirm gap closure ...")
        report = mgr.verify_and_repair(
            timeframes=["1h"],
            start_date=verify_start,
            end_date=verify_end,
            dry_run=True,
            binance_api_horizon_days=200,  # wide window to cover Jan 2026
        )

        print()
        print("=" * 70)
        print("BACKFILL SUMMARY")
        print("=" * 70)
        print(f"  Months processed : {len(months)}")
        print(f"  Bars fetched     : {total_bars_fetched:,}")
        print(f"  Bars saved       : {total_bars_saved:,}")
        tf_report = report.get("1h", {})
        remaining_gaps = tf_report.get("gaps_found", "?")
        print(f"  Remaining gaps   : {remaining_gaps}")
        if remaining_gaps == 0:
            print("  STATUS: CLEAN — 1h data is continuous in the backfill range ✓")
        else:
            print(f"  STATUS: {remaining_gaps} gap(s) remain — review output above")
        print("=" * 70)


if __name__ == "__main__":
    main()
