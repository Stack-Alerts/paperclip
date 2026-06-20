"""
Bulk Archive Backfill — Binance Public Data Archives

Downloads historical BTCUSDT perpetual OHLCV data from the Binance public
data archive at data.binance.vision (free, no API key required) and saves
it as monthly parquet files compatible with the existing data store.

The archive provides complete monthly CSVs going back to exchange launch,
bypassing the 90-day Binance Futures REST API limit.

Archive URL format:
  https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/{TF}/BTCUSDT-{TF}-{YYYY}-{MM}.zip

CSV columns (no header in file):
  open_time(ms), open, high, low, close, volume, close_time(ms),
  quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore

Output schema (matches existing parquet files):
  timestamp (datetime64[ns]), open (f64), high (f64), low (f64),
  close (f64), volume (f64)

Author: DataEngineer (BTCAAAAA-35984)
Date:   2026-06-19
"""

from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

_BASE_URL = (
    "https://data.binance.vision/data/futures/um/monthly/klines"
    "/BTCUSDT/{tf}/BTCUSDT-{tf}-{yyyy}-{mm:02d}.zip"
)

_CSV_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "count",
    "taker_buy_volume", "taker_buy_quote_volume", "ignore",
]

_TIMEFRAMES = ["15m", "1h", "1d"]

_DATA_DIR = _REPO_ROOT / "data" / "binance"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _month_url(tf: str, year: int, month: int) -> str:
    return _BASE_URL.format(tf=tf, yyyy=year, mm=month)


def _output_path(tf: str, year: int, month: int) -> Path:
    month_str = f"{year}-{month:02d}"
    month_dir = _DATA_DIR / month_str
    month_dir.mkdir(parents=True, exist_ok=True)
    return month_dir / f"BTCUSDT_PERP_{tf}_{month_str}.parquet"


def _csv_to_df(raw: bytes) -> pd.DataFrame:
    """Parse a Binance monthly CSV (no header) into the standard schema."""
    df = pd.read_csv(
        io.StringIO(raw.decode("utf-8")),
        header=None,
        names=_CSV_COLS,
        dtype={
            "open_time": "int64",
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
            "volume": "float64",
        },
    )
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_localize(None)
    return df[["timestamp", "open", "high", "low", "close", "volume"]]


def _download_month(
    session: requests.Session,
    tf: str,
    year: int,
    month: int,
    timeout: int = 120,
) -> Optional[pd.DataFrame]:
    url = _month_url(tf, year, month)
    resp = session.get(url, timeout=timeout)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = zf.namelist()[0]
        raw = zf.read(csv_name)

    return _csv_to_df(raw)


def _merge_and_save(new_df: pd.DataFrame, tf: str, year: int, month: int) -> int:
    """Merge new bars with any existing data, deduplicate, and write atomically."""
    out_path = _output_path(tf, year, month)
    if out_path.exists():
        existing = pd.read_parquet(out_path)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    combined = (
        combined
        .drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    # Atomic write via temp file
    tmp = out_path.with_suffix(".parquet.tmp")
    combined.to_parquet(tmp, compression="snappy", index=False)
    tmp.replace(out_path)
    return len(combined)


def iter_months(from_ym: tuple[int, int], to_ym: tuple[int, int]):
    y, m = from_ym
    while (y, m) <= to_ym:
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


# ---------------------------------------------------------------------------
# Core download function (also called by the FastAPI endpoint)
# ---------------------------------------------------------------------------

def bulk_backfill(
    from_year: int,
    from_month: int,
    to_year: int,
    to_month: int,
    timeframes: list[str] | None = None,
    skip_existing: bool = False,
    verbose: bool = True,
) -> dict:
    """Download and store all monthly archive files in the given range.

    Returns a results dict keyed by '{YYYY-MM}/{tf}' with status info.
    """
    if timeframes is None:
        timeframes = _TIMEFRAMES

    results: dict = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "BTC-Trade-Engine-DataEngineer/1.0"})

    for year, month in iter_months((from_year, from_month), (to_year, to_month)):
        month_str = f"{year}-{month:02d}"
        for tf in timeframes:
            key = f"{month_str}/{tf}"
            out_path = _output_path(tf, year, month)

            if skip_existing and out_path.exists():
                if verbose:
                    print(f"  skip  {key} (exists)")
                results[key] = {"status": "skipped", "bars": 0}
                continue

            if verbose:
                print(f"  ↓     {key} … ", end="", flush=True)

            try:
                df = _download_month(session, tf, year, month)
                if df is None:
                    if verbose:
                        print("404 (not available)")
                    results[key] = {"status": "not_available", "bars": 0}
                    continue

                bars = _merge_and_save(df, tf, year, month)
                if verbose:
                    print(f"ok ({bars:,} bars)")
                results[key] = {"status": "ok", "bars": bars, "downloaded": len(df)}
            except Exception as exc:
                if verbose:
                    print(f"ERROR: {exc}")
                results[key] = {"status": "error", "bars": 0, "error": str(exc)}

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_ym(s: str) -> tuple[int, int]:
    parts = s.split("-")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"Expected YYYY-MM, got '{s}'")
    return int(parts[0]), int(parts[1])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download BTCUSDT PERP OHLCV from Binance public archives"
    )
    parser.add_argument(
        "--from", dest="from_ym", type=_parse_ym, default=(2024, 2),
        metavar="YYYY-MM",
        help="First month to download (default: 2024-02)",
    )
    parser.add_argument(
        "--to", dest="to_ym", type=_parse_ym, default=(2026, 4),
        metavar="YYYY-MM",
        help="Last month to download (default: 2026-04)",
    )
    parser.add_argument(
        "--tf", dest="timeframes", nargs="+", default=_TIMEFRAMES,
        metavar="TF",
        help=f"Timeframes to download (default: {' '.join(_TIMEFRAMES)})",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Skip months where the parquet file already exists",
    )
    args = parser.parse_args()

    from_year, from_month = args.from_ym
    to_year, to_month = args.to_ym

    print("=" * 70)
    print("BINANCE BULK ARCHIVE BACKFILL")
    print("=" * 70)
    print(f"Range:      {from_year}-{from_month:02d} → {to_year}-{to_month:02d}")
    print(f"Timeframes: {', '.join(args.timeframes)}")
    print(f"Output:     {_DATA_DIR}")
    print()

    results = bulk_backfill(
        from_year, from_month, to_year, to_month,
        timeframes=args.timeframes,
        skip_existing=args.skip_existing,
        verbose=True,
    )

    ok = sum(1 for v in results.values() if v["status"] == "ok")
    skipped = sum(1 for v in results.values() if v["status"] == "skipped")
    errors = sum(1 for v in results.values() if v["status"] == "error")
    not_avail = sum(1 for v in results.values() if v["status"] == "not_available")

    print()
    print("=" * 70)
    print(f"Complete:      {ok}")
    print(f"Skipped:       {skipped}")
    print(f"Not available: {not_avail}")
    print(f"Errors:        {errors}")
    if errors:
        print()
        for k, v in results.items():
            if v["status"] == "error":
                print(f"  ✗ {k}: {v['error']}")


if __name__ == "__main__":
    main()
