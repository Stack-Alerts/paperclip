"""
Backtest Matrix Runner — BTCAAAAA-20265

Parallel execution of Mode 1 (6-month) and Mode 2 (2-month) across 9 strategies.
Outputs validation_matrix_results.json with per-strategy signal counts, timings, and errors.
"""

import importlib, inspect, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

STRATEGY_MODULES = [
    "strategy_01_reversal_m_pattern",
    "strategy_02_reversal_w_pattern",
    "strategy_002_lod_rejection",
    "strategy_003_hod_continuation",
    "strategy_04_ema_trend_continuation",
    "strategy_06_range_breakout",
    "strategy_08_micro_trend_scalping",
    "strategy_09_order_flow_scalping",
    "strategy_15_bollinger_mean_reversion",
]

DRAFT_CONFIGS_DIR = REPO_ROOT / "src" / "strategies" / "drafts"


def discover_draft_configs() -> List[Dict]:
    configs = []
    if DRAFT_CONFIGS_DIR.exists():
        for f in sorted(DRAFT_CONFIGS_DIR.glob("*.json")):
            with open(f) as fh:
                try:
                    configs.append(json.load(fh) | {"_source": f.name})
                except json.JSONDecodeError:
                    pass
    return configs


def validate_module(mod_name: str) -> Dict:
    r = {"module": mod_name, "import_ok": False, "class": None, "error": None}
    try:
        mod = importlib.import_module(f"src.strategies.{mod_name}")
        r["import_ok"] = True
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and hasattr(obj, "_analyze_blocks"):
                r["class"] = name; break
    except Exception as e:
        r["error"] = str(e)
    return r


def _worker(args):
    """Top-level worker for multiprocessing."""
    mod_name, test_days, bar_limit = args
    sys.path.insert(0, str(REPO_ROOT))

    from src.strategies.universal_optimizer.modules.data_loader import load_btc_data, get_strategy_class
    from src.strategies.universal_optimizer.modules.data_classes import OptimizationConfig

    result = {"module": mod_name, "bars": 0, "signals": 0, "signal_bars": 0, "time_s": 0, "bars_per_sec": 0, "errors": [], "status": "ok"}

    try:
        warmup_df, test_df = load_btc_data(test_days=test_days, warmup_bars=200)
        if warmup_df is None:
            result["status"] = "error"
            result["errors"].append("No data loaded")
            return result

        strategy_class = get_strategy_class(mod_name)
        result["class"] = strategy_class.__name__

        cfg = OptimizationConfig(
            config_id=999, strategy_id=f"test_{mod_name}", strategy_name=mod_name,
            side="LONG", min_confluence=1, min_risk_reward=1.5, blocks={},
            tp_mode="PERCENTAGE", sl_mode="SWING_POINTS",
            trailing_pct=0.005, use_trailing=False, breakeven_after_tp1=False,
            tp_fallback_pcts={"tp1": 0.01, "tp2": 0.02, "tp3": 0.03},
            partial_exit_pcts={"tp1": 50, "tp2": 30, "tp3": 20},
            volatility_lookback=20, volatility_multiplier=1.5,
            absolute_min_sl_pct=0.005, absolute_max_sl_pct=0.05,
            initial_sl_multiplier=1.5, working_sl_multiplier=1.0,
            use_delayed_sl=False, delay_bars=0, emergency_sl_pct=0.03,
            use_structure_sl=True, structure_sources=["swing_points"],
            starting_capital=10000.0, max_leverage=1.0, risk_per_trade_pct=0.02,
        )

        df = test_df
        if bar_limit and len(df) > bar_limit:
            df = df.iloc[:bar_limit]

        class TestStrategy:
            def __init__(self, c):
                self.strategy_id = c.strategy_id
                self.strategy_name = c.strategy_name
                self.min_confluence = c.min_confluence
                self.max_bars_held = 1000
                self.lookback_period = 100
                self.min_risk_reward = c.min_risk_reward
                self.peak_tolerance = 0.002
                self.trough_tolerance = 0.002
                self.capital_allocation_pct = 10.0
                self.max_leverage = 2.0
                self.risk_per_trade_pct = 1.0
                self.bars_data = []
                self.blocks = c.blocks
                self.detectors = {}

        inst = TestStrategy(cfg)
        for mn in dir(strategy_class):
            if mn.startswith('_') and not mn.startswith('__'):
                m = getattr(strategy_class, mn)
                if callable(m):
                    setattr(inst, mn, m.__get__(inst))

        if hasattr(inst, '_initialize_blocks'):
            inst._initialize_blocks()
        result["building_blocks"] = len(getattr(inst, "detectors", {}))

        # Warmup phase: analyze blocks on warmup data
        for i in range(len(warmup_df)):
            inst._analyze_blocks(warmup_df.iloc[:i+1])

        # Test phase: analyze blocks on test data, count meaningful signals
        t0 = time.time()
        signal_count = 0
        signal_bars = 0
        for i in range(len(df)):
            history = df.iloc[:i+1]
            out = inst._analyze_blocks(history)
            if out and isinstance(out, dict) and any(
                v.get('signal') for v in out.values() if isinstance(v, dict)
            ):
                signal_bars += 1
            signal_count += 1

        elapsed = time.time() - t0
        result.update({
            "bars": len(df),
            "signals": signal_count,
            "signal_bars": signal_bars,
            "time_s": round(elapsed, 2),
            "bars_per_sec": round(len(df) / elapsed, 1) if elapsed else 0,
        })

    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=int, choices=[1, 2])
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    n_workers = max(1, multiprocessing.cpu_count() - 1)

    print("=" * 60)
    print(f"BTCAAAAA-20265: Backtest Matrix — Mode {'1+2' if not args.mode else args.mode}")
    print(f"  Parallel workers: {n_workers}")
    print("=" * 60)

    # Phase 1: Validate
    print("\n[1] Validating strategy modules...")
    mod_results = {m: validate_module(m) for m in STRATEGY_MODULES}
    for m, r in mod_results.items():
        ok = r["import_ok"] and r["class"]
        print(f"  {'OK' if ok else 'FAIL'} {m} -> {r['class'] or r['error']}")

    draft_configs = discover_draft_configs()
    print(f"\n  Draft configs: {len(draft_configs)}")

    modes = [args.mode] if args.mode else [1, 2]
    all_results = {}

    for mode in modes:
        test_days = 180 if mode == 1 else 60
        label = f"Mode {mode} ({test_days}d)"
        print(f"\n[{label}] Running {len(STRATEGY_MODULES)} strategies across {n_workers} workers...")

        worker_args = [(m, test_days, None) for m in STRATEGY_MODULES]

        strategy_results = {}
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            fut_map = {executor.submit(_worker, a): a[0] for a in worker_args}
            for fut in as_completed(fut_map):
                mod_name = fut_map[fut]
                sr = fut.result()
                strategy_results[mod_name] = sr
                status = "OK" if sr["status"] == "ok" else "FAIL"
                extras = (
                    f"blocks={sr.get('building_blocks','?')}, "
                    f"bars={sr['bars']}, "
                    f"signal_bars={sr['signal_bars']}, "
                    f"rate={sr['bars_per_sec']}b/s"
                )
                if sr.get("errors"):
                    extras += f", err={sr['errors'][0][:80]}"
                print(f"  [{status}] {mod_name} — {extras}")

        all_results[f"mode_{mode}"] = {
            "test_days": test_days,
            "strategies": strategy_results,
            "summary": {
                "total": len(STRATEGY_MODULES),
                "ok": sum(1 for s in strategy_results.values() if s["status"] == "ok"),
                "errors": sum(1 for s in strategy_results.values() if s.get("errors")),
                "with_signals": sum(1 for s in strategy_results.values() if s.get("signal_bars", 0) > 0),
            }
        }

    # Compile output
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modes_run": modes,
        "strategies_validated": mod_results,
        "draft_configs": len(draft_configs),
        "results": all_results,
        "overall": {
            "mode1_ok": all_results.get("mode_1", {}).get("summary", {}).get("ok", 0),
            "mode2_ok": all_results.get("mode_2", {}).get("summary", {}).get("ok", 0),
            "mode1_signals": all_results.get("mode_1", {}).get("summary", {}).get("with_signals", 0),
            "mode2_signals": all_results.get("mode_2", {}).get("summary", {}).get("with_signals", 0),
        }
    }

    output_path = (
        Path(args.output) if args.output
        else REPO_ROOT / "docs" / "backtest-analysis" / "validation_matrix_results.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"OVERALL SUMMARY")
    print(f"{'='*60}")
    o = output["overall"]
    print(f"  Mode 1 OK:     {o['mode1_ok']}/{len(STRATEGY_MODULES)}")
    print(f"  Mode 1 signals:{o['mode1_signals']}/{len(STRATEGY_MODULES)}")
    print(f"  Mode 2 OK:     {o['mode2_ok']}/{len(STRATEGY_MODULES)}")
    print(f"  Mode 2 signals:{o['mode2_signals']}/{len(STRATEGY_MODULES)}")
    print(f"  Draft configs: {len(draft_configs)}")
    print(f"\n  Results: {output_path}")
    print(f"{'='*60}")

    errors = (
        all_results.get("mode_1", {}).get("summary", {}).get("errors", 0)
        + all_results.get("mode_2", {}).get("summary", {}).get("errors", 0)
    )
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
