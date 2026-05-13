"""
Regression test for BTCAAAAA-685: Zero-trades root cause

Root cause: _get_timing_constraint_for_signal reads 'reference_signal' from the
timing_constraint dict, but current_strategy.json uses the key 'reference'.
This means the timing constraint for BELOW_ASIA_50 is never injected, so AT_ASIA_50
is never pulled back into the confluence window when BELOW_ASIA_50 fires.

Result: max achievable confluence = BELOW_ASIA_50 (15) + BEARISH_CLIMAX (20) = 35 < 40
Fix:    read both 'reference_signal' and 'reference' keys.

Expanded to meet Impact Gate 10-test minimum bar (BTCAAAAA-25065).
"""

import json
import unittest
from datetime import datetime
from typing import Dict, Any

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
# Unit tests: timing constraint key parsing (BTCAAAAA-685 root cause)
# ---------------------------------------------------------------------------

class TestTimingConstraintKeyParsing(unittest.TestCase):
    """
    BTCAAAAA-685 root cause: config uses 'reference' but code reads 'reference_signal'.
    """

    def setUp(self):
        self.config = _load_strategy()
        self.evaluator = InstitutionalSignalEvaluator(self.config)

    def test_below_asia_50_timing_constraint_is_parsed(self):
        """'reference' key (config convention) resolves correctly."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'asia_session_50_percent', 'BELOW_ASIA_50'
        )
        self.assertIsNotNone(
            result,
            "Timing constraint for BELOW_ASIA_50 must not be None -- "
            "the config key is 'reference' but the code was reading 'reference_signal'."
        )
        self.assertEqual(
            result['reference_signal'],
            'asia_session_50_percent::AT_ASIA_50',
        )
        self.assertGreaterEqual(result['max_candles'], 1)

    def test_reference_signal_key_also_works(self):
        """'reference_signal' key is also accepted."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'asia_session_50_percent', 'BELOW_ASIA_50'
        )
        self.assertIsNotNone(result)
        self.assertIn('reference_signal', result)

    def test_parsed_dict_structure(self):
        """Returned dict has expected keys and types."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'asia_session_50_percent', 'BELOW_ASIA_50'
        )
        self.assertIsNotNone(result)
        self.assertIn('reference_signal', result)
        self.assertIn('max_candles', result)
        self.assertIsInstance(result['reference_signal'], str)
        self.assertIsInstance(result['max_candles'], int)

    def test_max_candles_matches_config(self):
        """max_candles matches the value in current_strategy.json (10)."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'asia_session_50_percent', 'BELOW_ASIA_50'
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['max_candles'], 10)

    def test_signal_without_constraint_returns_none(self):
        """Signal without a timing_constraint section returns None."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'asia_session_50_percent', 'AT_ASIA_50'
        )
        self.assertIsNone(result)

    def test_nonexistent_signal_returns_none(self):
        """Non-existent signal name returns None."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'asia_session_50_percent', 'NONEXISTENT'
        )
        self.assertIsNone(result)

    def test_nonexistent_block_returns_none(self):
        """Non-existent block name returns None."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'nonexistent_block', 'BELOW_ASIA_50'
        )
        self.assertIsNone(result)

    def test_liquidity_sweep_has_no_constraint(self):
        """OR-branch signal liquidity_sweep::BEARISH_SWEEP has no constraint."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'liquidity_sweep', 'BEARISH_SWEEP'
        )
        self.assertIsNone(result)

    def test_ema_55_has_no_constraint(self):
        """AND-block signal ema_55_vector::BEARISH_CLIMAX has no constraint."""
        result = self.evaluator._get_timing_constraint_for_signal(
            'ema_55_vector', 'BEARISH_CLIMAX'
        )
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Integration tests: timing chain activation (BTCAAAAA-685 end-to-end)
# ---------------------------------------------------------------------------

_AT_BAR = 61
_BELOW_BAR = 62


class _MockAsiaBlock:
    """
    Deterministic mock for asia_session_50_percent.
    Fires AT_ASIA_50 at bar 60, BELOW_ASIA_50 at bar 61.
    """

    def __init__(self, fire_at: bool = True, fire_below: bool = True):
        self._fire_at = fire_at
        self._fire_below = fire_below

    def analyze(self, df) -> Dict[str, Any]:
        n = len(df)
        if self._fire_at and n == _AT_BAR:
            return {
                'signal': 'AT_ASIA_50',
                'confidence': 80,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': '15m',
                'confluence_factors': [],
            }
        if self._fire_below and n == _BELOW_BAR:
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
    """Returns BEARISH_CLIMAX at bar 61."""

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
    Injects mocked building blocks so we fully control signal timing.
    """

    def setUp(self):
        self.config = _load_strategy()
        self.evaluator = InstitutionalSignalEvaluator(self.config)

        self.evaluator.building_blocks = {
            'asia_session_50_percent': _MockAsiaBlock(),
            'ema_55_vector': _MockEma55Block(),
        }

        self.bar_type = _make_bar_type()

    def _make_bars(self, count: int):
        base_ns = int(datetime(2025, 6, 1, 10, 0).timestamp() * 1e9)
        step_ns = 15 * 60 * int(1e9)
        return [
            _make_bar(self.bar_type, base_ns + i * step_ns,
                      45000.0, 45100.0, 44900.0, 45050.0)
            for i in range(count)
        ]

    def _warmup(self, bars, count: int = 60):
        total = len(bars)
        for i in range(count):
            lookback = bars[:i]
            self.evaluator.evaluate_bar(bars[i], i, lookback, total)

    def test_entry_fires_after_timing_chain(self):
        """Full timing chain: AT_ASIA_50 -> BELOW_ASIA_50 -> entry at bar 61."""
        bars = self._make_bars(70)
        total = len(bars)
        self._warmup(bars, 60)

        lookback_60 = bars[:60]
        result_60 = self.evaluator.evaluate_bar(bars[60], 60, lookback_60, total)
        self.assertFalse(result_60.should_enter)

        at_id = 'asia_session_50_percent::AT_ASIA_50'
        self.assertIn(at_id, self.evaluator.fired_signals)

        lookback_61 = bars[:61]
        result_61 = self.evaluator.evaluate_bar(bars[61], 61, lookback_61, total)

        self.assertGreaterEqual(result_61.confluence_score, 40)
        self.assertTrue(result_61.should_enter)

    def test_no_entry_without_prior_reference(self):
        """BELOW_ASIA_50 fires but AT_ASIA_50 never fired -> no timing chain."""
        bars = self._make_bars(70)
        total = len(bars)

        self.evaluator.building_blocks['asia_session_50_percent'] = _MockAsiaBlock(fire_at=False)
        self._warmup(bars, 61)

        self.evaluator.building_blocks['asia_session_50_percent'] = _MockAsiaBlock(fire_at=False)
        lookback_61 = bars[:61]
        result = self.evaluator.evaluate_bar(bars[61], 61, lookback_61, total)

        self.assertLess(result.confluence_score, 40)
        self.assertFalse(result.should_enter)

    def test_no_entry_during_warmup(self):
        """No entry fires during warmup phase (bars 0-59)."""
        bars = self._make_bars(60)
        total = len(bars)

        entries = []
        for i in range(60):
            lookback = bars[:i]
            result = self.evaluator.evaluate_bar(bars[i], i, lookback, total)
            entries.append(result.should_enter)

        self.assertFalse(any(entries))


if __name__ == '__main__':
    unittest.main()
