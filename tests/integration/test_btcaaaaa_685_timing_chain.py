"""
Regression test for BTCAAAAA-685: Zero-trades root cause

Root cause: _get_timing_constraint_for_signal reads 'reference_signal' from the
timing_constraint dict, but current_strategy.json uses the key 'reference'.
This means the timing constraint for BELOW_ASIA_50 is never injected, so AT_ASIA_50
is never pulled back into the confluence window when BELOW_ASIA_50 fires.

Result: max achievable confluence = BELOW_ASIA_50 (15) + BEARISH_CLIMAX (20) = 35 < 40
Fix:    read both 'reference_signal' and 'reference' keys.

Both tests FAIL on pre-fix main and PASS after the fix.
"""

import json
import unittest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import MagicMock

from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType

from src.strategy_builder.ui.backtest_config_panel import DictWrapper
from src.optimizer_v3.core.institutional_signal_evaluator import InstitutionalSignalEvaluator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_strategy() -> DictWrapper:
    """Load current_strategy.json as a DictWrapper.

    JSON-path only — does not exercise the DB load path. NOT a proxy for UI correctness.
    The UI loads via get_strategy_version → _dict_to_config, resolving weights from
    BlockRegistry base_points. This path reads explicit weights from the JSON file.
    """
    path = "user_strategies/current_strategy.json"
    with open(path) as f:
        return DictWrapper(json.load(f))


def _make_bar(bar_type: BarType, ts_ns: int, open_: float, high: float, low: float,
              close: float, volume: float = 10.0) -> Bar:
    return Bar(
        bar_type=bar_type,
        open=Price(open_, 2),
        high=Price(high, 2),
        low=Price(low, 2),
        close=Price(close, 2),
        volume=Quantity(volume, 8),
        ts_event=ts_ns,
        ts_init=ts_ns,
    )


def _make_bar_type() -> BarType:
    return BarType(
        InstrumentId(Symbol("BTC"), Venue("BINANCE")),
        BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )


# ---------------------------------------------------------------------------
# Unit test: timing constraint key parsing
# ---------------------------------------------------------------------------

class TestTimingConstraintKeyParsing(unittest.TestCase):
    """
    BTCAAAAA-685 root cause: config uses 'reference' but code reads 'reference_signal'.

    This test calls _get_timing_constraint_for_signal directly and asserts that:
    - The result is not None (previously returned None due to key mismatch)
    - The reference_signal points at asia_session_50_percent::AT_ASIA_50
    - max_candles is 3
    """

    def setUp(self):
        self.config = _load_strategy()
        self.evaluator = InstitutionalSignalEvaluator(self.config)

    def test_below_asia_50_timing_constraint_is_parsed(self):
        result = self.evaluator._get_timing_constraint_for_signal(
            'asia_session_50_percent', 'BELOW_ASIA_50'
        )
        self.assertIsNotNone(
            result,
            "Timing constraint for BELOW_ASIA_50 must not be None — "
            "the config key is 'reference' but the code was reading 'reference_signal'."
        )
        self.assertEqual(
            result['reference_signal'],
            'asia_session_50_percent::AT_ASIA_50',
            "reference_signal must resolve to the fully-qualified AT_ASIA_50 signal id.",
        )
        self.assertEqual(result['max_candles'], 3)


# ---------------------------------------------------------------------------
# Integration test: AT_ASIA_50 → BELOW_ASIA_50 + BEARISH_CLIMAX → entry fires
# ---------------------------------------------------------------------------

_AT_BAR = 61    # df length when AT_ASIA_50 should fire (lookback 60 + current bar)
_BELOW_BAR = 62  # df length when BELOW_ASIA_50 + BEARISH_CLIMAX fire


class _MockAsiaBlock:
    """
    Deterministic mock for asia_session_50_percent.
    Fires AT_ASIA_50 when df has _AT_BAR rows (bar index 60),
    BELOW_ASIA_50 when df has _BELOW_BAR rows (bar index 61).
    The evaluator passes df = lookback + [current_bar], so len(df) == bar_index + 1.
    """

    def analyze(self, df) -> Dict[str, Any]:
        n = len(df)
        if n == _AT_BAR:
            return {
                'signal': 'AT_ASIA_50',
                'confidence': 80,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': '15m',
                'confluence_factors': [],
            }
        if n == _BELOW_BAR:
            return {
                'signal': 'BELOW_ASIA_50',
                'confidence': 80,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': '15m',
                'confluence_factors': [],
            }
        return {
            'signal': 'NO_SIGNAL',
            'confidence': 0,
            'metadata': {},
            'timestamp': datetime.now(),
            'timeframe': '15m',
            'confluence_factors': [],
        }


class _MockEma55Block:
    """
    Deterministic mock for ema_55_vector.
    Returns BEARISH_CLIMAX at bar index 61 (df length == _BELOW_BAR).
    """

    def analyze(self, df) -> Dict[str, Any]:
        if len(df) == _BELOW_BAR:
            return {
                'signal': 'BEARISH_CLIMAX',
                'confidence': 95,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': '15m',
                'confluence_factors': [],
            }
        return {
            'signal': 'NO_SIGNAL',
            'confidence': 0,
            'metadata': {},
            'timestamp': datetime.now(),
            'timeframe': '15m',
            'confluence_factors': [],
        }


class TestAsiaRejectionTimingChain(unittest.TestCase):
    """
    BTCAAAAA-685 end-to-end regression.

    Injects mocked building blocks so we fully control signal timing:
      - Bar 60: AT_ASIA_50 fires  (+15 pts recorded in fired_signals)
      - Bar 61: BELOW_ASIA_50 fires (+15 pts, timing chain activates AT_ASIA_50 ref)
               BEARISH_CLIMAX fires (+20 pts)
               Total = AT_ASIA_50(15) + BELOW_ASIA_50(15) + BEARISH_CLIMAX(20) = 50 >= 40

    Without the fix: timing constraint for BELOW_ASIA_50 is never injected,
    AT_ASIA_50 is not included in active refs, confluence = 35 < 40 → no entry.
    With the fix: confluence = 50 >= 40 → entry fires.
    """

    def setUp(self):
        self.config = _load_strategy()
        self.evaluator = InstitutionalSignalEvaluator(self.config)

        # Replace real building blocks with mocks
        self.evaluator.building_blocks = {
            'asia_session_50_percent': _MockAsiaBlock(),
            'ema_55_vector': _MockEma55Block(),
        }

        self.bar_type = _make_bar_type()

    def _make_bars(self, count: int):
        base_ns = int(datetime(2025, 6, 1, 10, 0).timestamp() * 1e9)  # London session
        step_ns = 15 * 60 * int(1e9)
        return [
            _make_bar(self.bar_type, base_ns + i * step_ns,
                      45000.0, 45100.0, 44900.0, 45050.0)
            for i in range(count)
        ]

    def test_entry_fires_after_timing_chain(self):
        bars = self._make_bars(70)
        total = len(bars)

        entries = []
        # Warmup: pass bars 0-59 so internal state is primed
        for i in range(60):
            lookback = bars[:i]
            self.evaluator.evaluate_bar(bars[i], i, lookback, total)

        # Bar 60: AT_ASIA_50 fires — record in fired_signals, but entry not yet expected
        lookback_60 = bars[:60]
        result_60 = self.evaluator.evaluate_bar(bars[60], 60, lookback_60, total)
        # AT_ASIA_50 alone = 15 pts < 40 — no entry yet
        self.assertFalse(
            result_60.should_enter,
            "Should NOT enter on AT_ASIA_50 alone (15 pts < 40 threshold)."
        )
        at_signal_id = 'asia_session_50_percent::AT_ASIA_50'
        self.assertIn(
            at_signal_id,
            self.evaluator.fired_signals,
            "AT_ASIA_50 must be recorded in fired_signals after bar 60.",
        )

        # Bar 61: BELOW_ASIA_50 + BEARISH_CLIMAX fire — timing chain must pull in AT_ASIA_50
        lookback_61 = bars[:61]
        result_61 = self.evaluator.evaluate_bar(bars[61], 61, lookback_61, total)

        self.assertGreaterEqual(
            result_61.confluence_score,
            40,
            f"Confluence must reach >=40 when timing chain works. "
            f"Got {result_61.confluence_score}. "
            f"Signals fired: {result_61.signals_fired}. "
            f"If 35, the 'reference' key fix is missing in _get_timing_constraint_for_signal."
        )
        self.assertTrue(
            result_61.should_enter,
            f"Entry must fire at bar 61 (confluence={result_61.confluence_score}). "
            f"Signals: {result_61.signals_fired}."
        )


if __name__ == '__main__':
    unittest.main()
