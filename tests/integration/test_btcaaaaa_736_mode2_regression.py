"""
Regression test for BTCAAAAA-736: Mode 2 (Live Replay) produces 0 trades.

This test exercises the full Mode 2 bar-by-bar evaluation path using:
  - Inline DictWrapper strategy config (self-contained — no external JSON file)
  - Mocked building blocks that inject known AT_ASIA_50 → BELOW_ASIA_50 + BEARISH_CLIMAX
    sequences (same mocking strategy as test_btcaaaaa_685_timing_chain.py)
  - The COMPLETE evaluator loop from BacktestWorker (not just InstitutionalSignalEvaluator)

Gap covered: test_btcaaaaa_685_timing_chain.py tests the evaluator in isolation.
This test verifies that the DictWrapper strategy config, the timing chain, and the
bar-by-bar loop all work end-to-end — a regression in the Mode 2 code path will
fail here, not just in a UI run.

Both tests fail on pre-ad3b0b1 code and pass after the fix.
"""

import json
import unittest
from datetime import datetime
from typing import Dict, Any, List, Optional

from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType

from src.strategy_builder.ui.backtest_config_panel import DictWrapper
from src.optimizer_v3.core.institutional_signal_evaluator import InstitutionalSignalEvaluator


# ---------------------------------------------------------------------------
# Inline strategy config — self-contained, no external JSON file dependency.
# The deleted user_strategies/current_strategy.json contained a phantom signal
# (liquidity_sweep::BEARISH_SWEEP) that never existed in any DB strategy_version.
# This inline dict preserves only the fields needed by the test.
# ---------------------------------------------------------------------------

_INLINE_STRATEGY_DICT: dict = {
    "name": "50% Asia Rejection (test inline)",
    "description": "Inline strategy for regression testing",
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
                        "max_candles": 10,
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
                {
                    "name": "BEARISH_CLIMAX",
                    "logic": "AND",
                    "weight": 20,
                }
            ],
        },
        {
            "name": "liquidity_sweep",
            "logic": "OR",
            "signals": [
                {
                    "name": "BEARISH_SWEEP",
                    "logic": "OR",
                    "weight": 10,
                }
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
    "version": "1.1.0",
    "validation_status": None,
    "generation_status": None,
}


# ---------------------------------------------------------------------------
# Shared helpers (mirrored from test_btcaaaaa_685_timing_chain.py)
# ---------------------------------------------------------------------------

def _load_strategy() -> DictWrapper:
    return DictWrapper(_INLINE_STRATEGY_DICT)


def _make_bar_type() -> BarType:
    return BarType(
        InstrumentId(Symbol("BTC"), Venue("BINANCE")),
        BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )


def _make_bar(bar_type: BarType, ts_ns: int, close: float = 50000.0) -> Bar:
    return Bar(
        bar_type=bar_type,
        open=Price(close - 10, 2),
        high=Price(close + 20, 2),
        low=Price(close - 20, 2),
        close=Price(close, 2),
        volume=Quantity(100.0, 8),
        ts_event=ts_ns,
        ts_init=ts_ns,
    )


# ---------------------------------------------------------------------------
# Mock building blocks — same pattern as 685 test
# ---------------------------------------------------------------------------

# Bar indices (df length = bar_index + 1 because df = lookback + [current_bar])
_AT_BAR = 61    # AT_ASIA_50 fires when df has 61 rows (bar index 60)
_BELOW_BAR = 62  # BELOW_ASIA_50 + BEARISH_CLIMAX fire at bar index 61


class _MockAsiaBlock:
    def analyze(self, df) -> Dict[str, Any]:
        n = len(df)
        if n == _AT_BAR:
            return {'signal': 'AT_ASIA_50', 'confidence': 80, 'metadata': {}}
        if n == _BELOW_BAR:
            return {'signal': 'BELOW_ASIA_50', 'confidence': 75, 'metadata': {}}
        return {'signal': 'NEUTRAL', 'confidence': 0, 'metadata': {}}


class _MockEMABlock:
    def analyze(self, df) -> Dict[str, Any]:
        n = len(df)
        if n == _BELOW_BAR:
            return {'signal': 'BEARISH_CLIMAX', 'confidence': 85, 'metadata': {}}
        return {'signal': 'NEUTRAL', 'confidence': 0, 'metadata': {}}


class _MockLiquidityBlock:
    def analyze(self, df) -> Dict[str, Any]:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'metadata': {}}


# ---------------------------------------------------------------------------
# Test: Mode 2 bar-by-bar loop produces an entry with mocked blocks
# ---------------------------------------------------------------------------

class TestMode2BarByBarLoop(unittest.TestCase):
    """
    Verifies that the complete Mode 2 bar-by-bar evaluation path — using a
    DictWrapper-wrapped strategy config (the same object BacktestWorker passes
    to InstitutionalSignalEvaluator) — fires at least one entry when the
    building blocks produce the required timing chain.

    This test would have failed silently before ad3b0b1 because:
      Bug 1 (hasattr crash) would raise TypeError in _organize_exit_conditions.
      Bug 2 (reference key) would cap confluence at 35 pts < 40 threshold.
    """

    def setUp(self):
        self.config = _load_strategy()
        self.bar_type = _make_bar_type()

        self.evaluator = InstitutionalSignalEvaluator(self.config)

        # Replace real building blocks with deterministic mocks
        self.evaluator.building_blocks = {
            'asia_session_50_percent': _MockAsiaBlock(),
            'ema_55_vector': _MockEMABlock(),
            'liquidity_sweep': _MockLiquidityBlock(),
        }

    def _run_mode2_loop(self, num_bars: int = 100) -> int:
        """
        Simulate the Mode 2 bar-by-bar loop from BacktestWorker.run().
        Returns the number of entries triggered.
        """
        base_ns = int(datetime(2026, 1, 1).timestamp() * 1e9)
        bars = [
            _make_bar(self.bar_type, base_ns + i * 15 * 60 * int(1e9))
            for i in range(num_bars)
        ]
        total_candles = len(bars)
        entries = 0

        for i in range(total_candles):
            current_bar = bars[i]
            lookback_bars = bars[0:i]

            result = self.evaluator.evaluate_bar(
                current_bar, i, lookback_bars, total_candles
            )

            if result.should_enter and not self.evaluator.current_trade:
                entries += 1
                self.evaluator.enter_trade(current_bar, i, 'SHORT')

        return entries

    def test_mode2_loop_fires_entry(self):
        """
        AT_ASIA_50 fires at bar 60, BELOW_ASIA_50 + BEARISH_CLIMAX at bar 61.
        With the ad3b0b1 timing-chain fix the confluence reaches 50 pts (>=40).
        Without it, confluence caps at 35 pts and no entry fires.
        """
        entries = self._run_mode2_loop(num_bars=100)
        self.assertGreater(
            entries, 0,
            "Mode 2 bar-by-bar loop produced 0 entries. "
            "Expected >=1 with AT_ASIA_50 → BELOW_ASIA_50 + BEARISH_CLIMAX sequence. "
            "Likely cause: timing-chain reference key fix (ad3b0b1 Bug 2) not active, "
            "or hasattr guard fix (ad3b0b1 Bug 1) causing silent init crash.",
        )

    def test_mode2_diag_sentinels_present(self):
        """
        Verify the BTCAAAAA-736 build-sentinel attributes exist on the evaluator.
        If they're missing, the evaluator was loaded from a stale build that
        pre-dates the diagnostic instrumentation added in BTCAAAAA-736.
        """
        self.assertTrue(
            hasattr(self.evaluator, '_diag_signals_fired_total'),
            "Missing _diag_signals_fired_total — evaluator may be from a stale build.",
        )
        self.assertTrue(
            hasattr(self.evaluator, '_diag_signals_filtered_total'),
            "Missing _diag_signals_filtered_total — evaluator may be from a stale build.",
        )

    def test_timing_constraint_parsed_via_dictwrapper(self):
        """
        End-to-end check: the timing constraint for BELOW_ASIA_50 must be
        parsed through DictWrapper (config uses 'reference' not 'reference_signal').
        This is the unit-level regression from BTCAAAAA-685 re-verified here
        in the Mode 2 regression suite.
        """
        result = self.evaluator._get_timing_constraint_for_signal(
            'asia_session_50_percent', 'BELOW_ASIA_50'
        )
        self.assertIsNotNone(
            result,
            "Timing constraint for BELOW_ASIA_50 must not be None. "
            "Config uses 'reference' key; fix reads both 'reference' and 'reference_signal'.",
        )
        self.assertEqual(
            result['reference_signal'],
            'asia_session_50_percent::AT_ASIA_50',
        )
        self.assertEqual(result['max_candles'], 10)


if __name__ == '__main__':
    unittest.main()
