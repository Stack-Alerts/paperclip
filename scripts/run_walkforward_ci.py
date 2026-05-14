"""
CI Walkforward Validation Runner

Runs walkforward validation on a strategy and gates against thresholds:
  - Win rate >= 60%
  - Profit factor >= 1.5
  - Max drawdown <= 20%
  - Minimum 20 trades

Usage:
  python scripts/run_walkforward_ci.py --strategy src/strategies/strategy_01_reversal_m_pattern.py
  python scripts/run_walkforward_ci.py --strategy <path> --data data/raw/BTC_USDT_PERP_30m.pkl --timeout 600

Exit codes:
  0 - All thresholds passed
  1 - One or more thresholds failed
  2 - Runtime error (missing data, import failure, etc.)
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

DATA_DEFAULT = "data/raw/BTC_USDT_PERP_30m.pkl"
THRESHOLDS = {
    "win_rate_pct": 60.0,
    "profit_factor": 1.5,
    "max_drawdown_pct": 20.0,
    "total_trades": 20,
}
REGISTRY_FILE = "walkforward_results_registry.json"
TIMEOUT_SEC = 600

def resolve_strategy_name(filepath: str) -> str:
    path = Path(filepath)
    return path.stem

def load_30m_data(data_path: str):
    import pandas as pd

    if not os.path.exists(data_path):
        print(f"ERROR: data file not found: {data_path}", file=sys.stderr)
        sys.exit(2)

    if data_path.endswith(".pkl"):
        df = pd.read_pickle(data_path)
    elif data_path.endswith(".csv"):
        df = pd.read_csv(data_path)
    else:
        print(f"ERROR: unsupported data format: {data_path}", file=sys.stderr)
        sys.exit(2)

    if "timestamp" not in df.columns and "Timestamp" in df.columns:
        df.rename(columns={"Timestamp": "timestamp"}, inplace=True)
    if "timestamp" not in df.columns and isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

    print(f"Loaded {len(df)} bars from {data_path}")
    print(f"  Range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    return df

def run_walkforward(strategy, df, strategy_name: str) -> dict:
    """Run walkforward simulation returning metrics dict."""
    import pandas as pd
    import numpy as np

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from tests.strategies.backtest_simulator import BacktestSimulator, BacktestConfig

    config = BacktestConfig(
        starting_capital=10000.0,
        max_leverage=15.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        risk_per_trade_pct=1.0,
    )
    simulator = BacktestSimulator(config)

    min_bars = getattr(strategy, "lookback_period", 100)
    max_bars_held = getattr(strategy, "max_bars_held", 1000)
    min_confluence = getattr(strategy, "min_confluence", 70)
    min_rr = getattr(strategy, "min_risk_reward", 3.0)

    print(f"  lookback_period={min_bars}  max_bars_held={max_bars_held}")
    print(f"  min_confluence={min_confluence}  min_risk_reward={min_rr}")

    signals_checked = 0
    signals_taken = 0

    for i in range(min_bars, len(df)):
        current_bar = df.iloc[i]

        if simulator.open_trade is not None:
            simulator.update_open_position(current_bar)

        if simulator.open_trade is None:
            # Build bars incrementally (only newest bar, don't rebuild from scratch)
            current_row = df.iloc[i]
            strategy.bars_data.append({
                "timestamp": current_row["timestamp"],
                "open": current_row["open"],
                "high": current_row["high"],
                "low": current_row["low"],
                "close": current_row["close"],
                "volume": current_row.get("volume", 0) if hasattr(current_row, 'get') else current_row["volume"],
            })
            if len(strategy.bars_data) > max_bars_held:
                strategy.bars_data.pop(0)

            try:
                analysis_df = pd.DataFrame(strategy.bars_data)
                results = strategy._analyze_blocks(analysis_df)
                confluence, signal_list = strategy._calculate_confluence(results)
                signals_checked += 1

                if confluence >= min_confluence:
                    tp1, tp2, tp3, sl = strategy._calculate_tp_sl(results)
                    side = "SHORT" if "double_top" in strategy.blocks else "LONG"

                    close_price = float(current_bar["close"])
                    risk = abs(close_price - sl) if side == "SHORT" else abs(sl - close_price)
                    reward = abs(close_price - tp2) if side == "SHORT" else abs(tp2 - close_price)
                    rr = reward / risk if risk > 0 else 0

                    if rr >= min_rr:
                        success = simulator.open_position(
                            entry_time=current_bar["timestamp"],
                            entry_price=current_bar["close"],
                            side=side,
                            tp1=tp1,
                            tp2=tp2,
                            tp3=tp3,
                            sl=sl,
                            confluence=confluence,
                            signals=signal_list,
                        )
                        if success:
                            signals_taken += 1
            except Exception:
                continue

    if simulator.open_trade is not None:
        simulator.close_position(
            df.iloc[-1]["timestamp"], df.iloc[-1]["close"], "END_OF_DATA"
        )

    print(f"  Signals checked: {signals_checked}  taken: {signals_taken}")
    return simulator.get_performance_metrics()

def check_thresholds(metrics: dict) -> tuple[bool, list[str]]:
    failures = []
    win_rate = metrics.get("win_rate_pct", 0)
    profit_factor = metrics.get("profit_factor", 0)
    max_dd = metrics.get("max_drawdown_pct", 100)
    total_trades = metrics.get("total_trades", 0)

    if total_trades < THRESHOLDS["total_trades"]:
        failures.append(f"total_trades={total_trades} < {THRESHOLDS['total_trades']}")
    if win_rate < THRESHOLDS["win_rate_pct"]:
        failures.append(f"win_rate_pct={win_rate:.1f} < {THRESHOLDS['win_rate_pct']}")
    if profit_factor < THRESHOLDS["profit_factor"]:
        failures.append(f"profit_factor={profit_factor:.2f} < {THRESHOLDS['profit_factor']}")
    if max_dd > THRESHOLDS["max_drawdown_pct"]:
        failures.append(f"max_drawdown_pct={max_dd:.2f} > {THRESHOLDS['max_drawdown_pct']}")

    return len(failures) == 0, failures

def update_registry(strategy_name: str, filepath: str, metrics: dict, passed: bool):
    entry = {
        "strategy": strategy_name,
        "file": filepath,
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "metrics": {
            "total_trades": metrics.get("total_trades", 0),
            "win_rate_pct": round(metrics.get("win_rate_pct", 0), 1),
            "profit_factor": round(metrics.get("profit_factor", 0), 2),
            "max_drawdown_pct": round(metrics.get("max_drawdown_pct", 0), 2),
            "sharpe_ratio": round(metrics.get("sharpe_ratio", 0), 2),
            "total_return_pct": round(metrics.get("total_return_pct", 0), 2),
            "final_capital": round(metrics.get("final_capital", 0), 2),
        },
    }

    registry_path = Path(REGISTRY_FILE)
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)
    else:
        registry = {"last_updated": None, "entries": []}

    registry["last_updated"] = datetime.now().isoformat()
    registry["entries"].append(entry)

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)

    print(f"Registry updated: {REGISTRY_FILE} ({len(registry['entries'])} entries)")

def main():
    parser = argparse.ArgumentParser(description="CI Walkforward Validation Runner")
    parser.add_argument("--strategy", required=True, help="Path to strategy .py file")
    parser.add_argument("--data", default=DATA_DEFAULT, help="Path to data file")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SEC, help="Timeout in seconds")
    parser.add_argument("--days", type=int, default=180, help="Days of recent data to use")
    parser.add_argument("--output", default=None, help="Path to write JSON results")
    args = parser.parse_args()

    start = time.time()
    strategy_file = os.path.abspath(args.strategy)
    strategy_name = resolve_strategy_name(args.strategy)

    print(f"=== Walkforward CI: {strategy_name} ===")
    print(f"  Strategy: {strategy_file}")
    print(f"  Data: {args.data}")
    print(f"  Timeout: {args.timeout}s")

    # Load data
    try:
        df = load_30m_data(args.data)
    except Exception as e:
        print(f"FATAL: data load failed: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)

    # Trim to recent N days for CI performance
    cutoff = df['timestamp'].max() - pd.Timedelta(days=args.days)
    df = df[df['timestamp'] >= cutoff].reset_index(drop=True)
    print(f"  Trimmed to last {args.days} days: {len(df)} bars")

    # Import strategy module
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    sys.path.insert(0, os.path.dirname(strategy_file))
    import importlib.util

    spec = importlib.util.spec_from_file_location(strategy_name, strategy_file)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"FATAL: failed to import strategy: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)

    # Find strategy class
    strategy_cls = None
    for attr_name in dir(module):
        obj = getattr(module, attr_name)
        if isinstance(obj, type) and attr_name not in ("datetime", "timedelta", "Enum"):
            if hasattr(obj, "_analyze_blocks") or hasattr(obj, "_calculate_confluence"):
                strategy_cls = obj
                break

    if strategy_cls is None:
        print("WARNING: No strategy class found with walkforward methods — using MockStrategy fallback")
        strategy_cls = module.__dict__.get(
            "MPatternReversalStandard",
            module.__dict__.get("WPatternReversalStandard", None),
        )

    if strategy_cls is None:
        print("FATAL: could not locate strategy class in module", file=sys.stderr)
        sys.exit(2)

    print(f"  Strategy class: {strategy_cls.__name__}")

    # Build mock wrapper with real detector instances
    class MockStrategy:
        pass

    strategy = MockStrategy()

    # Set strategy properties from the real class or defaults
    strategy.strategy_id = strategy_name
    strategy.strategy_name = strategy_name
    strategy.min_confluence = getattr(strategy_cls, 'min_confluence', 70)
    strategy.lookback_period = getattr(strategy_cls, 'lookback_period', 100)
    strategy.max_bars_held = getattr(strategy_cls, 'max_bars_held', 1000)
    strategy.min_risk_reward = getattr(strategy_cls, 'min_risk_reward', 2.0)
    strategy.bars_data = []
    strategy.daily_pnl_usd = 0.0

    # Extract blocks configuration from strategy source
    # Strategy classes set blocks in _initialize_blocks(), so we can't read
    # them from the uninstantiated class. Parse from source or use defaults.
    import re as _re
    strategy.blocks = {}
    try:
        with open(args.strategy) as _f:
            _src = _f.read()
        # Match: self.blocks['key'] = {'name': ..., 'weight': N, ...}
        _block_pattern = _re.compile(
            r"self\.blocks\['(\w+)'\]\s*=\s*\{[^}]*'weight':\s*(\d+)", _re.DOTALL
        )
        for _match in _block_pattern.finditer(_src):
            _key = _match.group(1)
            _weight = int(_match.group(2))
            strategy.blocks[_key] = {'name': _key.replace('_', ' ').title(), 'weight': _weight, 'enabled': True}
    except Exception:
        pass

    if not strategy.blocks:
        # Fallback defaults for common strategy patterns
        strategy.blocks = {
            'double_top': {'weight': 35, 'enabled': True},
            'rsi_divergence': {'weight': 30, 'enabled': True},
            'hod': {'weight': 15, 'enabled': True},
            'asia_session_50_percent': {'weight': 12, 'enabled': True},
            'session_time': {'weight': 10, 'enabled': True},
            'vwap': {'weight': 10, 'enabled': True},
            'ema_20_50_trend': {'weight': 8, 'enabled': True},
            'kill_zones': {'weight': 8, 'enabled': True},
            'adr': {'weight': 5, 'enabled': True},
        }
    print(f"  Blocks configured: {len(strategy.blocks)} ({', '.join(strategy.blocks.keys())})")

    # Build detector map: map analysis result keys to detector class constructors
    # These are the keys used by _analyze_blocks (e.g. 'double_top', 'rsi_divergence')
    detector_specs = {
        'double_top': ('DoubleTopPattern', 'patterns.double_top'),
        'double_bottom': ('DoubleBottomPattern', 'patterns.double_bottom'),
        'rsi_divergence': ('RSIDivergence', 'oscillators.rsi_divergence'),
        'macd': ('MACDSignal', 'oscillators.macd_signal'),
        'hod': ('HOD', 'price_levels.hod'),
        'lod': ('LOD', 'price_levels.lod'),
        'asia_session_50_percent': ('AsiaSession50Percent', 'price_levels.asia_session_50_percent'),
        'session_time': ('SessionTime', 'sessions.session_time'),
        'kill_zones': ('KillZones', 'sessions.kill_zones'),
        'vwap': ('VWAP', 'institutional.vwap'),
        'adr': ('ADR', 'volatility.adr'),
        'ema_20_50_trend': ('EMA2050Trend', 'moving_averages.ema_20_50_trend'),
        'ema_200_trend': ('EMA200Trend', 'moving_averages.ema_200_trend'),
        'swing_points': ('SwingPoints', 'market_structure.swing_points'),
        'premium_discount_zones': ('PremiumDiscountZones', 'market_structure.premium_discount_zones'),
        'ema_20_50_cross': ('EMA2050Cross', 'moving_averages.ema_20_50_cross'),
    }

    strategy.detectors = {}
    failed_detectors = []
    for key, (class_name, module_path) in detector_specs.items():
        try:
            mod = importlib.import_module(
                f"src.detectors.building_blocks.{module_path}"
            )
            cls = getattr(mod, class_name)
            strategy.detectors[key] = cls(timeframe='30min')
        except Exception as e:
            failed_detectors.append(f"{key} ({module_path}): {e}")

    print(f"  Detectors initialized: {len(strategy.detectors)} blocks")
    if failed_detectors:
        print(f"  Failed detectors: {', '.join(failed_detectors[:10])}", file=sys.stderr)

    # Verify all required detectors for the strategy's _analyze_blocks
    target_method = getattr(strategy, '_analyze_blocks', None)
    if target_method:
        import inspect as _inspect, re as _re
        _src = _inspect.getsource(target_method)
        _required = set(_re.findall(r"self\.detectors\['(\w+)'\]", _src))
        _missing = _required - set(strategy.detectors.keys())
        if _missing:
            print(f"  FATAL: missing required detectors: {_missing}", file=sys.stderr)
            sys.exit(2)

    # Bind strategy methods
    for method_name in ["_analyze_blocks", "_calculate_confluence", "_calculate_tp_sl"]:
        if hasattr(strategy_cls, method_name):
            setattr(strategy, method_name, getattr(strategy_cls, method_name).__get__(strategy, MockStrategy))

    # Run walkforward with timeout
    elapsed = time.time() - start
    if elapsed > args.timeout:
        print(f"FATAL: timeout before run ({elapsed:.0f}s > {args.timeout}s)", file=sys.stderr)
        sys.exit(2)

    try:
        metrics = run_walkforward(strategy, df, strategy_name)
    except Exception as e:
        print(f"FATAL: walkforward run failed: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)

    elapsed = time.time() - start
    passed, failures = check_thresholds(metrics)

    # Output results
    result = {
        "strategy": strategy_name,
        "file": strategy_file,
        "timestamp": datetime.now().isoformat(),
        "elapsed_sec": round(elapsed, 1),
        "passed": passed,
        "thresholds": THRESHOLDS,
        "metrics": metrics,
        "failures": failures,
    }

    print(f"\n=== Results ({elapsed:.1f}s) ===")
    print(f"  Trades: {metrics['total_trades']}")
    print(f"  Win Rate: {metrics['win_rate_pct']:.1f}%  (threshold: {THRESHOLDS['win_rate_pct']}%)")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}  (threshold: {THRESHOLDS['profit_factor']})")
    print(f"  Max DD: {metrics['max_drawdown_pct']:.2f}%  (threshold: {THRESHOLDS['max_drawdown_pct']}%)")
    print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
    print(f"  Return: {metrics['total_return_pct']:.2f}%")

    if passed:
        print("\nPASS: all thresholds met")
    else:
        print(f"\nFAIL: {len(failures)} threshold(s) failed:")
        for f in failures:
            print(f"  - {f}")

    # Update registry
    update_registry(strategy_name, strategy_file, metrics, passed)

    # Write output file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Results written to {args.output}")

    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
