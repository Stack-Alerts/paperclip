#!/usr/bin/env python3
"""
Re-ingest BTCUSDT 15m+1h candles 2026-01-16 to 2026-05-02 with corrected UTC timestamps.

Issue: BTCAAAAA-993
Root cause: LakeAPI-sourced monthly files (2026-01 through 2026-04) stored OHLCV data
with incorrect UTC timestamps, causing field mismatches against Binance ground truth.

Fix: Re-fetch directly from Binance Futures API (open_time → UTC-naive datetime64[us])
and overwrite the affected monthly parquet files.

Usage:
    cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip
    python scripts/reingest/reingest_corrected_utc.py

Safety:
    - Backs up each existing file to <file>.bak before overwriting.
    - 2026-05 file is handled with surgical merge (keeps May 3+ data intact).
    - Dry-run mode available via --dry-run flag.
"""

import argparse
import os
import shutil
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "binance"

BINANCE_FUTURES_BASE = "https://fapi.binance.com"

# Re-ingest window per issue scope
REINGEST_START = datetime(2026, 1, 16, 0, 0, 0, tzinfo=timezone.utc)
REINGEST_END   = datetime(2026, 5, 3, 0, 0, 0, tzinfo=timezone.utc)  # exclusive

TIMEFRAMES = ["15m", "1h"]
SYMBOL = "BTCUSDT"


def fetch_klines_page(interval: str, start_ms: int, end_ms: int, limit: int = 1500) -> list:
    """Fetch one page of klines from Binance Futures. Returns raw list rows."""
    params = {
        "symbol": SYMBOL,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms - 1,  # Binance endTime is inclusive; subtract 1ms to avoid fence-post
        "limit": limit,
    }
    for attempt in range(5):
        try:
            resp = requests.get(
                f"{BINANCE_FUTURES_BASE}/fapi/v1/klines",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            wait = 2 ** attempt
            print(f"  ⚠️  API error (attempt {attempt+1}/5): {e} — retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Binance API failed after 5 attempts for {interval} {start_ms}-{end_ms}")


def fetch_klines_range(interval: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetch all klines for [start, end) with automatic pagination.
    Returns DataFrame with UTC-naive timestamps (datetime64[us]).
    """
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    all_rows = []
    cursor_ms = start_ms

    while cursor_ms < end_ms:
        batch = fetch_klines_page(interval, cursor_ms, end_ms)
        if not batch:
            break
        all_rows.extend(batch)
        # Advance cursor past the last returned open_time
        last_open_ms = batch[-1][0]
        cursor_ms = last_open_ms + _interval_ms(interval)
        print(f"    fetched {len(batch)} bars, cursor now {_ms_to_str(cursor_ms)}")
        if len(batch) < 1500:
            break
        time.sleep(0.1)  # gentle rate-limiting

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])

    # Convert types — open_time is the canonical UTC open timestamp
    df["timestamp"] = (
        pd.to_datetime(df["open_time"], unit="ms", utc=True)
        .dt.tz_localize(None)
        .astype("datetime64[us]")
    )
    df["open"]        = df["open"].astype(float)
    df["high"]        = df["high"].astype(float)
    df["low"]         = df["low"].astype(float)
    df["close"]       = df["close"].astype(float)
    df["volume"]      = df["volume"].astype(float)
    df["volume_usd"]  = df["quote_volume"].astype(float)
    df["trade_count"] = df["trades"].astype(int)
    df["symbol"]      = SYMBOL
    df["timeframe"]   = interval

    # Trim to [start, end) strictly
    ts_start = pd.Timestamp(start.replace(tzinfo=None))
    ts_end   = pd.Timestamp(end.replace(tzinfo=None))
    df = df[(df["timestamp"] >= ts_start) & (df["timestamp"] < ts_end)]

    return df[["timestamp", "open", "high", "low", "close", "volume",
               "volume_usd", "trade_count", "symbol", "timeframe"]].reset_index(drop=True)


def _interval_ms(interval: str) -> int:
    """Return interval duration in milliseconds."""
    mapping = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000,
               "4h": 14_400_000, "1d": 86_400_000}
    return mapping[interval]


def _ms_to_str(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def split_by_month(df: pd.DataFrame) -> dict:
    """Split DataFrame into {YYYY-MM: DataFrame} keyed by month string."""
    df = df.copy()
    df["_month"] = df["timestamp"].dt.to_period("M").astype(str)
    return {month: grp.drop(columns="_month").reset_index(drop=True)
            for month, grp in df.groupby("_month")}


def backup_file(path: Path) -> None:
    """Rename existing file to .bak (overwrites any prior .bak)."""
    bak = path.with_suffix(".parquet.bak")
    shutil.copy2(path, bak)
    print(f"  📦 Backed up → {bak.name}")


def save_monthly_file(month_str: str, tf: str, df: pd.DataFrame, dry_run: bool) -> None:
    """Write a monthly parquet file, creating parent dir if needed."""
    out_dir = DATA_DIR / month_str
    out_path = out_dir / f"BTCUSDT_PERP_{tf}_{month_str}.parquet"

    if dry_run:
        print(f"  [DRY-RUN] would write {len(df)} rows → {out_path.relative_to(PROJECT_ROOT)}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        backup_file(out_path)

    df.to_parquet(out_path, index=False)
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✅ Wrote {len(df):,} rows ({size_kb:.1f} KB) → {out_path.relative_to(PROJECT_ROOT)}")


def merge_may_file(tf: str, fresh_may: pd.DataFrame, dry_run: bool) -> None:
    """
    Merge fresh May 1-2 data into the existing 2026-05 parquet file.
    Strategy:
      - Keep rows from existing file where timestamp >= 2026-05-03 00:00
      - Prepend fresh May 1-2 data (from our re-ingestion, timestamp < 2026-05-03)
      - Sort and deduplicate on timestamp
    """
    may_path = DATA_DIR / "2026-05" / f"BTCUSDT_PERP_{tf}_2026-05.parquet"
    cutoff = pd.Timestamp("2026-05-03 00:00:00")

    if may_path.exists():
        existing = pd.read_parquet(may_path)
        existing["timestamp"] = existing["timestamp"].astype("datetime64[us]")
        keep = existing[existing["timestamp"] >= cutoff].copy()
        print(f"  Existing 2026-05 {tf}: {len(existing)} rows → keeping {len(keep)} rows (May 3+)")
    else:
        keep = pd.DataFrame(columns=fresh_may.columns)
        print(f"  No existing 2026-05 {tf} file — will create fresh.")

    # fresh_may already filtered to [REINGEST_START, REINGEST_END) so it only has up to May 2
    fresh_chunk = fresh_may[fresh_may["timestamp"] < cutoff].copy()
    print(f"  Fresh May 1-2 data: {len(fresh_chunk)} rows")

    merged = (
        pd.concat([fresh_chunk, keep], ignore_index=True)
        .sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="last")
        .reset_index(drop=True)
    )
    merged["timestamp"] = merged["timestamp"].astype("datetime64[us]")

    save_monthly_file("2026-05", tf, merged, dry_run)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be written without touching any files")
    args = parser.parse_args()

    print("=" * 70)
    print("BTCAAAAA-993: Re-ingest corrected UTC timestamps")
    print(f"  Range     : {REINGEST_START.date()} → {(REINGEST_END - timedelta(seconds=1)).date()}")
    print(f"  Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"  Symbol    : {SYMBOL} (Binance Futures perpetual)")
    print(f"  Dry-run   : {args.dry_run}")
    print("=" * 70)

    for tf in TIMEFRAMES:
        print(f"\n{'─'*60}")
        print(f"Downloading {tf} candles …")
        df_full = fetch_klines_range(tf, REINGEST_START, REINGEST_END)
        print(f"  Total fetched: {len(df_full):,} bars  "
              f"({df_full['timestamp'].iloc[0]} → {df_full['timestamp'].iloc[-1]})")

        monthly = split_by_month(df_full)

        for month_str, df_month in sorted(monthly.items()):
            print(f"\n  Month {month_str} ({len(df_month)} rows)")

            if month_str == "2026-05":
                merge_may_file(tf, df_month, args.dry_run)
            else:
                save_monthly_file(month_str, tf, df_month, args.dry_run)

    print("\n" + "=" * 70)
    print("Done. Run the candle_pipeline_audit.py to verify integrity.")
    print("=" * 70)


if __name__ == "__main__":
    main()
