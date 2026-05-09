"""
Regression test for BTCAAAAA-693: TradeRegistry not cleared between backtest runs.

Root cause: merge_chunk_results() called get_trade_registry() without clearing it
first. On the second (or any subsequent) run with the same data+strategy the
(entry_ts, exit_ts, exit_type) unique keys match the entries already in the
registry and ALL new trades are rejected as duplicates → 0 trades shown.

Fix: registry.clear() added at the start of merge_chunk_results().
"""

import unittest
from unittest.mock import MagicMock
from datetime import datetime

from src.optimizer_v3.core.trade_registry import get_trade_registry, TradeRegistry
from src.optimizer_v3.core.multicore_backtest_engine import merge_chunk_results, ChunkResult


def _make_chunk_result(chunk_id: int, entry_ts: datetime, exit_ts: datetime) -> ChunkResult:
    """Helper: one trade inside a ChunkResult."""
    trade = {
        'entry_bar': 10,
        'exit_bar': 20,
        'entry_price': 50000.0,
        'exit_price': 49000.0,
        'entry_timestamp': entry_ts,
        'exit_timestamp': exit_ts,
        'pnl': -100.0,
        'pnl_pct': -0.2,
        'side': 'SHORT',
        'exit_reason': 'Stop Loss Hit',
        'exit_type': 'STOP_LOSS',
        'exit_condition_name': 'SL',
        'bars_held': 10,
        'partial_exit': False,
        'exit_percentage': 1.0,
        'status': 'CLOSED',
        'position_size': 0.1,
        'partial_size': 0.1,
    }
    return ChunkResult(
        chunk_id=chunk_id,
        trades=[trade],
        open_trade=None,
        total_bars_processed=100,
        signals_evaluated=100,
        errors=[],
        messages=[],
        sl_adjustments=0,
    )


class TestRegistryClearBetweenRuns(unittest.TestCase):
    """
    Verifies that merge_chunk_results clears the registry before adding trades.

    Pre-fix behaviour: identical (entry_ts, exit_ts, exit_type) keys from a
    second run were rejected as duplicates → 0 trades on the second run.
    Post-fix behaviour: registry is cleared at the start of each merge so
    the same trade appears exactly once regardless of how many times the
    backtest is executed.
    """

    def _run_merge(self) -> int:
        entry_ts = datetime(2026, 1, 16, 15, 30)
        exit_ts = datetime(2026, 1, 16, 18, 0)
        chunk = _make_chunk_result(0, entry_ts, exit_ts)
        result = merge_chunk_results([chunk])
        return len(result['trades'])

    def test_first_run_produces_trades(self):
        """Baseline: first merge yields exactly one trade."""
        count = self._run_merge()
        self.assertEqual(count, 1, "First backtest run must yield 1 trade.")

    def test_second_run_also_produces_trades(self):
        """
        Without registry.clear(), the second run returns 0 trades because
        the trade from the first run is still in the registry and the
        identical key is rejected as a duplicate.

        With the fix this test must pass: second run still shows 1 trade.
        """
        self._run_merge()            # first run (populates registry)
        count = self._run_merge()    # second run (must NOT see 0)
        self.assertEqual(
            count, 1,
            "Second backtest run must yield 1 trade. "
            "0 trades means the registry was not cleared between runs "
            "(BTCAAAAA-693 regression).",
        )

    def test_third_run_also_produces_trades(self):
        """Same data, three consecutive runs — registry must be reset each time."""
        for run_num in range(1, 4):
            count = self._run_merge()
            self.assertEqual(
                count, 1,
                f"Run #{run_num} produced {count} trades instead of 1 "
                f"(BTCAAAAA-693 regression).",
            )


if __name__ == '__main__':
    unittest.main()
