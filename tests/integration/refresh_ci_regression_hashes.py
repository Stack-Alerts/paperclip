#!/usr/bin/env python3
"""
Refresh the reference backtest hash in test_ci_regression_btcaaaaa987.py.

When to run:
  - After the BTCAAAAA-991 price-attribution bug is fixed and a corrected
    backtest is verified by QAEngineer.
  - After any intentional change to the MulticoreBacktestEngine that alters
    trade execution logic.
  - Quarterly if no engine changes, to confirm baseline stability.

Usage:
    cd <project-root>
    python tests/integration/refresh_ci_regression_hashes.py

The script will:
  1. Load the reference parquet (data/audit/reference_BTCUSDT_PERP_15m_20260201_20260207.parquet).
  2. Run the "50% Asia Rejection Simple" backtest.
  3. Print the new hash and snapshot.
  4. Offer to patch _REFERENCE_BACKTEST_HASH in the test file automatically.

After patching, commit the test file with a message explaining the reason
for the hash update (e.g. "fix(ci): refresh backtest hash after BTCAAAAA-991 fix").
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity

from src.optimizer_v3.core.multicore_backtest_engine import MulticoreBacktestEngine

_REFERENCE_PARQUET = (
    _project_root / "data" / "audit"
    / "reference_BTCUSDT_PERP_15m_20260201_20260207.parquet"
)
_TEST_FILE = Path(__file__).parent / "test_ci_regression_btcaaaaa987.py"

_STRATEGY_CONFIG: dict = {
    "name": "50% Asia Rejection Simple",
    "strategy_type": "Bearish",
    "confluence_threshold": 40,
    "blocks": [
        {
            "name": "asia_session_50_percent",
            "logic": "AND",
            "signals": [
                {
                    "name": "AT_ASIA_50",
                    "logic": "AND",
                    "weight": 20,
                    "exit_conditions": [
                        {
                            "signal_name": "AT_IHOD",
                            "percentage": 1.0,
                            "exit_mode": "ABSOLUTE",
                            "tp_proximity_threshold": 2.0,
                            "reversal_trigger": 0.5,
                            "binding_level": "SIGNAL",
                        }
                    ],
                },
                {
                    "name": "BELOW_ASIA_50",
                    "logic": "AND",
                    "weight": 15,
                    "timing_constraint": {
                        "max_candles": 3,
                        "reference": "asia_session_50_percent::AT_ASIA_50",
                    },
                    "exit_conditions": [
                        {
                            "signal_name": "ABOVE_ASIA_50",
                            "percentage": 1.0,
                            "exit_mode": "FLEXIBLE",
                            "tp_proximity_threshold": 0.5,
                            "reversal_trigger": 0.4,
                            "binding_level": "SIGNAL",
                            "recheck_config": {
                                "enabled": True,
                                "bar_delay": 2,
                                "validation_mode": "SIGNAL",
                                "parent_signal": None,
                            },
                        }
                    ],
                },
            ],
        },
        {
            "name": "ema_55_vector",
            "logic": "AND",
            "signals": [
                {"name": "BEARISH_CLIMAX", "logic": "AND", "weight": 22},
            ],
        },
        {
            "name": "liquidity_sweep",
            "logic": "OR",
            "signals": [
                {"name": "BEARISH_SWEEP", "logic": "OR", "weight": 10},
            ],
        },
    ],
    "exit_conditions": [
        {
            "signal_name": "BULLISH_BREAK",
            "percentage": 0.01,
            "exit_mode": "ABSOLUTE",
            "tp_proximity_threshold": 2.0,
            "reversal_trigger": 0.5,
            "binding_level": "STRATEGY",
        }
    ],
}

_BACKTEST_CONFIG: dict = {
    "timeframe": "15m",
    "starting_capital": 10000,
    "risk_per_trade_pct": 10,
    "min_risk_reward": 1.2,
    "max_leverage": 10,
    "max_bars_held": 200,
    "tpsl_mode": "Fibonacci",
    "sl_mode": "Static",
    "confluence_threshold": 40,
    "adaptive_sl": {
        "enabled": False,
        "delay_enabled": False,
        "delay_bars": 2,
        "emergency_sl_pct": 2,
        "volatility_lookback": 20,
        "volatility_multiplier": 1.2,
        "min_sl_pct": 0.7,
        "max_sl_pct": 2.0,
        "use_structure_sl": False,
        "structure_sources": [],
    },
}


def _load_bars() -> list:
    df = (
        pd.read_parquet(_REFERENCE_PARQUET)
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    instrument_id = InstrumentId(Symbol("BTC-USDT-PERP"), Venue("BINANCE"))
    bar_type = BarType(
        instrument_id,
        BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )
    bars = []
    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(pd.Timestamp(row["timestamp"]))
        bars.append(
            Bar(
                bar_type=bar_type,
                open=Price(float(row["open"]), precision=2),
                high=Price(float(row["high"]), precision=2),
                low=Price(float(row["low"]), precision=2),
                close=Price(float(row["close"]), precision=2),
                volume=Quantity(float(row["volume"]), precision=8),
                ts_event=ts,
                ts_init=ts,
            )
        )
    return bars


def main() -> None:
    print(f"Reference parquet: {_REFERENCE_PARQUET}")
    if not _REFERENCE_PARQUET.exists():
        print("ERROR: reference parquet not found.  Run the BTCAAAAA-986 audit first.")
        sys.exit(1)

    print("Loading bars …")
    bars = _load_bars()
    print(f"  Loaded {len(bars)} bars")

    print("Running backtest (num_processes=2) …")
    engine = MulticoreBacktestEngine(num_processes=2)
    result = engine.run_backtest(
        bars=bars,
        strategy_config=_STRATEGY_CONFIG,
        backtest_config=_BACKTEST_CONFIG,
    )

    metrics = result.get("metrics", {})
    snapshot = {
        "trade_count": int(metrics.get("total_trades", 0)),
        "win_rate_pct": round(float(metrics.get("win_rate", 0.0)), 2),
        "total_pnl_usd": round(float(metrics.get("total_pnl", 0.0)), 2),
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    new_hash = hashlib.sha256(canonical.encode()).hexdigest()

    print("\n--- New snapshot ---")
    print(json.dumps(snapshot, indent=2))
    print(f"\nNew hash: {new_hash}")

    # Read current hash from test file
    test_src = _TEST_FILE.read_text()
    match = re.search(r'_REFERENCE_BACKTEST_HASH\s*=\s*\(\s*"([0-9a-f]{64})"', test_src)
    if match:
        current_hash = match.group(1)
        print(f"\nCurrent hash in test file: {current_hash}")
        if current_hash == new_hash:
            print("Hash unchanged — nothing to update.")
            return
    else:
        print("\nWARNING: could not locate _REFERENCE_BACKTEST_HASH in test file.")
        current_hash = None

    answer = input("\nPatch _REFERENCE_BACKTEST_HASH in the test file? [y/N] ").strip().lower()
    if answer != "y":
        print("Skipped.  Update the hash manually in:")
        print(f"  {_TEST_FILE}")
        return

    if current_hash:
        new_src = test_src.replace(current_hash, new_hash, 1)
        _TEST_FILE.write_text(new_src)
        print(f"Patched {_TEST_FILE}")
        print("\nNext steps:")
        print("  1. Run the full CI regression test to confirm it passes.")
        print("  2. Commit with a message that explains WHY the hash changed.")
    else:
        print("Could not auto-patch.  Update manually.")


if __name__ == "__main__":
    main()
