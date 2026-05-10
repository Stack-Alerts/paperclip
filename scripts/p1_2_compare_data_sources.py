"""
P1.2 Data Source Comparison (BTCAAAAA-991)

Compares BacktestDataProvider.load_bars_for_backtest() output against the raw
BTC_USDT_PERP_15m.csv for the window 2025-09-02 12:00-14:00 UTC.

Run from project root:
    python scripts/p1_2_compare_data_sources.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timezone

START = datetime(2025, 9, 2, 12, 0, 0)
END   = datetime(2025, 9, 2, 14, 0, 0)
CSV_PATH = "data/raw/BTC_USDT_PERP_15m.csv"


def load_from_csv() -> pd.DataFrame:
    ohlcv = pd.read_csv(CSV_PATH)
    ohlcv["timestamp"] = pd.to_datetime(ohlcv["timestamp"])
    mask = (ohlcv["timestamp"] >= START) & (ohlcv["timestamp"] < END)
    return ohlcv[mask].reset_index(drop=True)


def load_from_provider() -> pd.DataFrame:
    from src.optimizer_v3.core.backtest_data_provider import BacktestDataProvider
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    provider = BacktestDataProvider()
    bars = provider.load_bars_for_backtest(
        timeframe="15m",
        start_date=START,
        end_date=END,
    )
    rows = []
    for bar in bars:
        ts_utc = datetime.fromtimestamp(bar.ts_event / 1e9, tz=timezone.utc).replace(tzinfo=None)
        rows.append({
            "timestamp": ts_utc,
            "open":   float(bar.open),
            "high":   float(bar.high),
            "low":    float(bar.low),
            "close":  float(bar.close),
            "volume": float(bar.volume),
        })
    return pd.DataFrame(rows)


def compare(csv_df: pd.DataFrame, provider_df: pd.DataFrame) -> None:
    print(f"\n=== P1.2 Data Source Comparison: {START} – {END} UTC ===\n")
    print(f"CSV rows:      {len(csv_df)}")
    print(f"Provider rows: {len(provider_df)}")

    if len(csv_df) != len(provider_df):
        print("WARNING: row count mismatch!\n")

    merged = csv_df.merge(provider_df, on="timestamp", suffixes=("_csv", "_prov"), how="outer")
    discrepancies = 0
    for col in ("open", "high", "low", "close"):
        col_csv  = f"{col}_csv"
        col_prov = f"{col}_prov"
        if col_csv not in merged.columns or col_prov not in merged.columns:
            print(f"  {col}: column missing after merge")
            continue
        diff = (merged[col_csv] - merged[col_prov]).abs()
        bad = diff[diff > 0.01]
        if len(bad):
            discrepancies += 1
            print(f"  {col}: {len(bad)} rows differ (max delta={diff.max():.4f})")
            print(merged[diff > 0.01][["timestamp", col_csv, col_prov]].head(5).to_string())
        else:
            print(f"  {col}: MATCH")

    if discrepancies == 0:
        print("\nVERDICT: data sources MATCH for this window.")
        print("Hypothesis B (data mismatch) is RULED OUT.")
    else:
        print(f"\nVERDICT: {discrepancies} columns show discrepancies.")
        print("Hypothesis B (data mismatch) may be CONFIRMED. Investigate further.")

    # Also report timestamp convention
    print("\n--- Timestamp convention check ---")
    if len(provider_df):
        from src.optimizer_v3.core.backtest_data_provider import BacktestDataProvider
        provider = BacktestDataProvider()
        bars = provider.load_bars_for_backtest(timeframe="15m", start_date=START, end_date=END)
        b = bars[0]
        ts_local = __import__("datetime").datetime.fromtimestamp(b.ts_init / 1e9)
        ts_utc   = __import__("datetime").datetime.fromtimestamp(b.ts_init / 1e9,
                        tz=__import__("datetime").timezone.utc).replace(tzinfo=None)
        print(f"First bar ts_event (ns): {b.ts_event}")
        print(f"ts_init (ns):            {b.ts_init}")
        print(f"ts_event == ts_init:     {b.ts_event == b.ts_init}")
        print(f"fromtimestamp (local):   {ts_local}  ← stored in entry_timestamp pre-fix")
        print(f"fromtimestamp (UTC):     {ts_utc}   ← correct UTC value")
        print(f"CSV timestamp for bar:   {csv_df.iloc[0]['timestamp']}")


if __name__ == "__main__":
    csv_df      = load_from_csv()
    provider_df = load_from_provider()
    compare(csv_df, provider_df)
