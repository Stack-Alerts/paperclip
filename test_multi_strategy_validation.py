"""
BTCAAAAA-20264: Fast multi-strategy backtest validation.
Tests ALL available JSON strategies for crash-free evaluation + trade production.
Uses reduced bar count for speed.
"""
import sys, json, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos

from src.optimizer_v3.core.multicore_backtest_engine import evaluate_chunk, ChunkData
from src.optimizer_v3.core.multicore_backtest_engine import MulticoreBacktestEngine
from src.optimizer_v3.core.trade_registry import get_trade_registry

import logging
logging.basicConfig(level=logging.WARNING)
# Silence noisy debug loggers
for name in ['exit_debug', 'binding_debug', 'sl_check_debug', 'position_calc',
             'tpsl_debug', 'wiring_config', 'wiring_test', 'wiring_debug']:
    logging.getLogger(name).setLevel(logging.ERROR)

DATA_DIR = ROOT / "data" / "binance"
BACKTEST_CONFIG = {
    "timeframe": "15m", "starting_capital": 10000, "risk_per_trade_pct": 10,
    "min_risk_reward": 1.2, "max_leverage": 10, "max_bars_held": 200,
    "tpsl_mode": "Fibonacci", "sl_mode": "Static", "confluence_threshold": 40,
    "adaptive_sl": {"enabled": False, "delay_enabled": False, "delay_bars": 2,
        "emergency_sl_pct": 2, "volatility_lookback": 20,
        "volatility_multiplier": 1.2, "min_sl_pct": 0.7, "max_sl_pct": 2.0,
        "use_structure_sl": False, "structure_sources": []},
}


def load_bars(count=2000):
    path = DATA_DIR / "2026-04" / "BTCUSDT_PERP_15m_2026-04.parquet"
    df = pd.read_parquet(path).sort_values("timestamp").reset_index(drop=True)
    df = df.iloc[:count]

    instrument_id = InstrumentId(Symbol("BTC-USDT-PERP"), Venue("BINANCE"))
    bar_spec = BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST)
    bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
    bars = []
    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(pd.Timestamp(row["timestamp"]))
        bars.append(Bar(bar_type=bar_type,
            open=Price(float(row["open"]), 2), high=Price(float(row["high"]), 2),
            low=Price(float(row["low"]), 2), close=Price(float(row["close"]), 2),
            volume=Quantity(float(row["volume"]), 8), ts_event=ts, ts_init=ts))
    return bars


def main():
    print("=" * 70)
    print("BTCAAAAA-20264 Multi-Strategy Validation (fast mode)")
    print("=" * 70)

    bars = load_bars(2000)
    print(f"\nLoaded {len(bars)} bars (2026-04-01 to ~2026-04-03)")

    # Collect all strategy JSONs
    strategy_files = list((ROOT / "user_strategies").glob("*.json"))
    test_dir = ROOT / "tests/strategies"
    if test_dir.exists():
        strategy_files.extend(test_dir.glob("*.json"))

    print(f"\nTesting {len(strategy_files)} strategy configurations...")
    print(f"\n{'Strategy':45s} {'Status':10s} {'Trades':>7s} {'Signals':>8s} {'Time':>7s}")
    print("-" * 80)

    results = []
    for sf in sorted(strategy_files):
        try:
            with open(sf) as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"{str(sf.name):45s} {'LOAD_ERR':10s}")
            continue

        name = cfg.get("name", sf.stem)
        side = "SHORT" if cfg.get("strategy_type") == "Bearish" else "LONG"

        try:
            t0 = time.time()
            chunk = ChunkData(0, bars, 0, len(bars), 0)
            r = evaluate_chunk(chunk, cfg, BACKTEST_CONFIG, side)
            elapsed = time.time() - t0

            status = "OK" if r.trades else "NO_TRADES"
            print(f"{name:45s} {status:10s} {len(r.trades):>7d} {r.signals_evaluated:>8d} {elapsed:>6.1f}s")
            results.append({"name": name, "status": status, "trades": len(r.trades),
                           "signals": r.signals_evaluated, "errors": len(r.errors),
                           "elapsed": round(elapsed, 1)})
            if r.errors:
                for e in r.errors[:2]:
                    print(f"  {'':45s} {'⚠ ERR':10s} {e[:120]}")
        except Exception as e:
            import traceback
            print(f"{name:45s} {'CRASH':10s} {str(e)[:100]}")
            print(f"  {traceback.format_exc()[-300:]}")
            results.append({"name": name, "status": "CRASH", "error": str(e)[:100]})

    print("-" * 80)
    ok = sum(1 for r in results if r["status"] == "OK")
    no_trades = sum(1 for r in results if r["status"] == "NO_TRADES")
    crashes = sum(1 for r in results if r["status"] == "CRASH")
    total = len(results)
    print(f"\nResults: {total} tested | {ok} OK (trade-producing) | "
          f"{no_trades} no-trades | {crashes} crashes")

    if crashes:
        crashed = [r for r in results if r["status"] == "CRASH"]
        print(f"\n⚠ CRASHED STRATEGIES:")
        for r in crashed:
            print(f"  - {r['name']}: {r.get('error', 'unknown')}")
    else:
        print("\n✅ No crashes — all strategies evaluatable")


if __name__ == "__main__":
    main()
