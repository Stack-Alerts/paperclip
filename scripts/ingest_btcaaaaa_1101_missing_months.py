#!/usr/bin/env python3
"""
Ingest missing 2025-11 and 2025-12 BTC/USDT 15m bars from Binance public API.
BTCAAAAA-1101: populate trading_data.db / parquet for QA Test 4.

Binance Futures klines API requires no authentication.
"""
import sys
import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BINANCE_FUTURES_BASE = "https://fapi.binance.com"
SYMBOL = "BTCUSDT"
INTERVAL = "15m"
LIMIT = 1500  # max per Binance Futures request

TARGET_MONTHS = [
    ("2025-11", datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 12, 1, tzinfo=timezone.utc)),
    ("2025-12", datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
]


def fetch_klines(start_ms: int, end_ms: int) -> list:
    """Fetch klines from Binance Futures with pagination."""
    all_klines = []
    current_start = start_ms
    while current_start < end_ms:
        params = {
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "startTime": current_start,
            "endTime": end_ms - 1,
            "limit": LIMIT,
        }
        resp = requests.get(f"{BINANCE_FUTURES_BASE}/fapi/v1/klines", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        all_klines.extend(data)
        last_open_time = data[-1][0]
        if last_open_time >= end_ms - 1:
            break
        current_start = last_open_time + 1
        if len(data) < LIMIT:
            break
        time.sleep(0.1)
    return all_klines


def klines_to_df(klines: list) -> pd.DataFrame:
    """Convert raw Binance kline arrays to the project's parquet schema."""
    rows = []
    for k in klines:
        rows.append({
            "timestamp": pd.Timestamp(k[0], unit="ms", tz="UTC").tz_localize(None),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "volume_usd": float(k[7]),
            "trade_count": int(k[8]),
            "symbol": SYMBOL,
            "timeframe": INTERVAL,
        })
    df = pd.DataFrame(rows)
    df["timestamp"] = df["timestamp"].astype("datetime64[us]")
    return df


def main():
    for month_str, start_dt, end_dt in TARGET_MONTHS:
        out_dir = PROJECT_ROOT / "data" / "binance" / month_str
        out_path = out_dir / f"BTCUSDT_PERP_{INTERVAL}_{month_str}.parquet"

        if out_path.exists():
            existing = pd.read_parquet(out_path)
            print(f"{month_str}: already exists ({len(existing)} rows) — skipping")
            continue

        print(f"{month_str}: fetching from Binance Futures API ...")
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        klines = fetch_klines(start_ms, end_ms)
        if not klines:
            print(f"  ERROR: no klines returned for {month_str}")
            sys.exit(1)

        df = klines_to_df(klines)
        # Deduplicate and sort
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)

        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_path, index=False)
        print(f"  Saved {len(df)} rows → {out_path}")
        print(f"  Range: {df['timestamp'].iloc[0]} UTC → {df['timestamp'].iloc[-1]} UTC")

    print("\nDone. Verifying all months now:")
    for month_str, _, _ in TARGET_MONTHS:
        path = PROJECT_ROOT / "data" / "binance" / month_str / f"BTCUSDT_PERP_{INTERVAL}_{month_str}.parquet"
        df = pd.read_parquet(path)
        print(f"  {month_str}: {len(df)} rows, {df['timestamp'].iloc[0]} → {df['timestamp'].iloc[-1]}")


if __name__ == "__main__":
    main()
