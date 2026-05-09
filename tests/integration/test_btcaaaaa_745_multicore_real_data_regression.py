"""
Regression test for BTCAAAAA-745: real-data multicore backtest (8,632 bars)
must produce trades > 0 on 3 consecutive runs.

Root cause: merge_chunk_results() called get_trade_registry() without clearing
it first. On the second (or any subsequent) run, identical (entry_ts, exit_ts,
exit_type) keys were rejected as duplicates → 0 trades on every run after the
first.

Fix: registry.clear() at the start of merge_chunk_results() (commit c2d19ff).

This test FAILS on pre-c2d19ff code and PASSES after.

Strategy under test: "50% Asia Rejection Simple"
  AT_ASIA_50 (15) + BELOW_ASIA_50 (15) + BEARISH_CLIMAX (20) → ≥40 confluence
Dataset: 15-minute BTCUSDT_PERP bars, Feb–May 2026 (≥8,000 bars)
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

# Ensure the project root is on sys.path for src/ imports.
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity

from src.optimizer_v3.core.multicore_backtest_engine import MulticoreBacktestEngine

# ---------------------------------------------------------------------------
# Strategy config — "50% Asia Rejection Simple" (current_strategy.json)
# ---------------------------------------------------------------------------

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
                    "weight": 15,
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
                {"name": "BEARISH_CLIMAX", "logic": "AND", "weight": 20},
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

# ---------------------------------------------------------------------------
# Bar-loading helper
# ---------------------------------------------------------------------------

_DATA_DIR = _project_root / "data" / "binance"
_MONTHS = ["2026-02", "2026-03", "2026-04", "2026-05"]


def _load_real_bars() -> list:
    """
    Load NautilusTrader Bar objects from the committed parquet files for
    Feb–May 2026 (BTCUSDT_PERP 15-minute data).

    Returns at least 8,000 bars; the CTO investigation confirmed 8,632.
    """
    dfs = []
    for month in _MONTHS:
        path = _DATA_DIR / month / f"BTCUSDT_PERP_15m_{month}.parquet"
        if path.exists():
            dfs.append(pd.read_parquet(path))

    if not dfs:
        raise RuntimeError(
            f"No 15m parquet files found under {_DATA_DIR} for months "
            f"{_MONTHS}. Check that data/binance/ is committed."
        )

    df = pd.concat(dfs).sort_values("timestamp").reset_index(drop=True)

    instrument_id = InstrumentId(Symbol("BTC-USDT-PERP"), Venue("BINANCE"))
    bar_spec = BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST)
    bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)

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


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestMulticoreRealDataRegression(unittest.TestCase):
    """
    Integration test: real 15m BTCUSDT_PERP dataset (Feb–May 2026, ≥8,000
    bars) must produce trades > 0 on 3 consecutive multicore backtest runs.

    Run 1 passing is trivial. The regression being guarded is runs 2 and 3
    returning 0 because the TradeRegistry was not cleared between runs
    (pre-c2d19ff behaviour).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.bars = _load_real_bars()
        # Limit processes so the test completes in a reasonable time on CI.
        cls.engine = MulticoreBacktestEngine(num_processes=4)

    def _run(self) -> int:
        result = self.engine.run_backtest(
            bars=self.bars,
            strategy_config=_STRATEGY_CONFIG,
            backtest_config=_BACKTEST_CONFIG,
        )
        return len(result["trades"])

    def test_bar_count_sanity(self) -> None:
        """At least 8,000 real bars must be loaded from the parquet files."""
        self.assertGreaterEqual(
            len(self.bars),
            8000,
            f"Expected ≥8,000 real bars; got {len(self.bars)}. "
            "Verify data/binance/2026-02 through 2026-05 parquet files.",
        )

    def test_three_consecutive_runs_all_produce_trades(self) -> None:
        """
        Each of 3 consecutive multicore runs on real BTC data must yield
        trades > 0, and all three counts must agree.

        Pre-c2d19ff failure mode:
          Run 1: N trades (e.g. 172)
          Run 2: 0 trades — registry not cleared, all keys deduplicated
          Run 3: 0 trades — same dedup

        Post-c2d19ff (current main): all three runs return N trades.
        """
        counts = []
        for run_num in range(1, 4):
            count = self._run()
            counts.append(count)
            self.assertGreater(
                count,
                0,
                f"Run #{run_num} produced 0 trades on the real 8,632-bar "
                "dataset. This is the BTCAAAAA-745 regression: the "
                "TradeRegistry was not cleared before merge_chunk_results() "
                "(pre-c2d19ff).",
            )

        self.assertEqual(
            counts[0],
            counts[1],
            f"Run 1 → {counts[0]} trades, Run 2 → {counts[1]} trades. "
            "Counts must match; mismatch indicates registry.clear() is missing.",
        )
        self.assertEqual(
            counts[1],
            counts[2],
            f"Run 2 → {counts[1]} trades, Run 3 → {counts[2]} trades. "
            "Counts must match; mismatch indicates registry.clear() is missing.",
        )


if __name__ == "__main__":
    unittest.main()
