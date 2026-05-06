"""
Unit tests for intelligent trade summarization (BTCAAAAA-343).

Covers:
- _extract_trade_results() with <=50 trades (raw pass-through path)
- _extract_trade_results() with >50 trades (statistical summarization path)
- _summarize_trades() internals: avg PnL by day-of-week, time-of-day clusters,
  consecutive loss run stats, streak stats, drawdown stats, trade sample
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.optimizer_v3.core.comprehensive_ai_request_builder import (
    ComprehensiveAIRequestBuilder,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trade(
    n: int,
    pnl: float,
    entry_dt: datetime,
    exit_dt: datetime | None = None,
    side: str = 'long',
) -> dict:
    """Return a minimal trade dict as produced by the backtest engine."""
    if exit_dt is None:
        exit_dt = entry_dt + timedelta(hours=1)
    return {
        'trade_number': n,
        'entry_time': entry_dt.isoformat(),
        'exit_time': exit_dt.isoformat(),
        'duration_bars': 4,
        'duration_time': '1h 0m',
        'side': side,
        'entry_price': 50_000.0,
        'exit_price': 50_000.0 + pnl,
        'position_size': 0.01,
        'pnl': pnl,
        'pnl_percent': pnl / 50_000.0 * 100,
        'exit_reason': 'take_profit',
        'signals_fired': [],
        'bars_data': {'entry_bar': n * 4, 'exit_bar': n * 4 + 4, 'total_bars': 4},
    }


def _make_builder() -> ComprehensiveAIRequestBuilder:
    """Create a minimal ComprehensiveAIRequestBuilder (no heavy deps needed)."""
    builder = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)
    return builder


def _make_results_with_n_trades(n: int, alternating: bool = True) -> dict:
    """
    Build a fake backtest-results dict with *n* trades.

    When ``alternating=True`` trades alternate win/loss (+100/-80).
    """
    base_dt = datetime(2025, 1, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday
    trades = []
    for i in range(n):
        entry_dt = base_dt + timedelta(days=i // 5, hours=(i % 5) * 2)
        pnl = 100.0 if (i % 2 == 0) else -80.0
        trades.append({
            'entry_time': entry_dt.isoformat(),
            'exit_time': (entry_dt + timedelta(hours=1)).isoformat(),
            'duration_bars': 4,
            'pnl': pnl,
            'pnl_percent': pnl / 50000,
            'side': 'long',
            'entry_price': 50000.0,
            'exit_price': 50000.0 + pnl,
            'position_size': 0.01,
            'exit_reason': 'tp',
            'signals_fired': [],
            'entry_bar': i * 4,
            'exit_bar': i * 4 + 4,
        })
    return {'trades': trades}


# ---------------------------------------------------------------------------
# Tests: <=50 trades → raw pass-through
# ---------------------------------------------------------------------------

class TestExtractTradeResultsSmall:

    def test_empty_trades_returns_warning(self):
        builder = _make_builder()
        result = builder._extract_trade_results({'trades': []})
        assert result['total_trades'] == 0
        assert 'warning' in result
        assert result['trades'] == []

    def test_single_trade_is_raw(self):
        builder = _make_builder()
        result = builder._extract_trade_results(_make_results_with_n_trades(1))
        assert result['total_trades'] == 1
        assert result['summarization_mode'] is False
        assert 'trades' in result
        assert len(result['trades']) == 1
        assert 'note' in result
        assert 'All trades included' in result['note']

    def test_exactly_50_trades_is_raw(self):
        builder = _make_builder()
        result = builder._extract_trade_results(_make_results_with_n_trades(50))
        assert result['total_trades'] == 50
        assert result['summarization_mode'] is False
        assert len(result['trades']) == 50
        assert 'note' in result

    def test_raw_path_contains_correct_summary_stats(self):
        builder = _make_builder()
        # 4 wins (+100), 4 losses (-80)
        result = builder._extract_trade_results(_make_results_with_n_trades(8))
        assert result['winning_trades'] == 4
        assert result['losing_trades'] == 4
        assert abs(result['total_pnl'] - (4 * 100 + 4 * -80)) < 0.01
        assert abs(result['avg_win'] - 100.0) < 0.01
        assert abs(result['avg_loss'] - (-80.0)) < 0.01
        assert result['largest_win'] == 100.0
        assert result['largest_loss'] == -80.0


# ---------------------------------------------------------------------------
# Tests: >50 trades → intelligent summarization
# ---------------------------------------------------------------------------

class TestExtractTradeResultsLarge:

    def _get_summary(self, n: int = 55) -> dict:
        builder = _make_builder()
        return builder._extract_trade_results(_make_results_with_n_trades(n))

    def test_switches_to_summarization_mode(self):
        result = self._get_summary(51)
        assert result['summarization_mode'] is True
        assert 'note' in result
        assert '51' in result['note']

    def test_no_raw_trades_key_in_summary_mode(self):
        result = self._get_summary(51)
        # The full raw trades list must NOT be present
        assert 'trades' not in result

    def test_summary_includes_required_keys(self):
        result = self._get_summary(60)
        required = [
            'avg_pnl_by_day_of_week',
            'time_of_day_clusters',
            'consecutive_loss_runs',
            'streak_stats',
            'drawdown_stats',
            'trade_sample',
        ]
        for key in required:
            assert key in result, f"Missing required summarization key: {key}"

    def test_base_stats_still_present(self):
        result = self._get_summary(60)
        for key in ['total_trades', 'winning_trades', 'losing_trades', 'win_rate',
                    'total_pnl', 'avg_win', 'avg_loss', 'largest_win', 'largest_loss']:
            assert key in result, f"Missing base stat: {key}"

    def test_trade_sample_length(self):
        result = self._get_summary(60)
        # Sample is best5 + worst5 + last5 de-duped, so at most 15
        assert 1 <= len(result['trade_sample']) <= 15

    def test_trade_sample_is_sorted(self):
        result = self._get_summary(60)
        numbers = [t['trade_number'] for t in result['trade_sample']]
        assert numbers == sorted(numbers)


# ---------------------------------------------------------------------------
# Tests: _summarize_trades internals
# ---------------------------------------------------------------------------

class TestSummarizeTrades:

    def _build_trades(self, specs: list) -> list:
        """
        specs: list of (pnl, entry_datetime) tuples
        Returns list of minimal detailed_trade dicts (as _extract_trade_results builds them).
        """
        trades = []
        for i, (pnl, dt) in enumerate(specs, 1):
            trades.append({
                'trade_number': i,
                'entry_time': dt.isoformat(),
                'exit_time': (dt + timedelta(hours=1)).isoformat(),
                'pnl': pnl,
            })
        return trades

    # ── avg_pnl_by_day_of_week ───────────────────────────────────────────────

    def test_avg_pnl_by_day_of_week_basic(self):
        builder = _make_builder()
        monday = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)   # Mon
        tuesday = datetime(2025, 1, 7, 10, 0, tzinfo=timezone.utc)  # Tue
        trades = self._build_trades([
            (100.0, monday), (200.0, monday),   # Mon avg = 150
            (-50.0, tuesday),                   # Tue avg = -50
        ])
        result = builder._summarize_trades(trades)
        dow = result['avg_pnl_by_day_of_week']
        assert 'Monday' in dow
        assert abs(dow['Monday'] - 150.0) < 0.01
        assert 'Tuesday' in dow
        assert abs(dow['Tuesday'] - (-50.0)) < 0.01

    def test_dow_skips_unparseable_times(self):
        builder = _make_builder()
        monday = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        trades = [
            {'trade_number': 1, 'entry_time': 'INVALID', 'exit_time': '', 'pnl': 999.0},
            {'trade_number': 2, 'entry_time': monday.isoformat(), 'exit_time': '', 'pnl': 100.0},
        ]
        result = builder._summarize_trades(trades)
        dow = result['avg_pnl_by_day_of_week']
        # Unparseable trade should be silently skipped
        assert 'Monday' in dow
        assert abs(dow['Monday'] - 100.0) < 0.01

    # ── time_of_day_clusters ─────────────────────────────────────────────────

    def test_time_of_day_clusters_four_sessions(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, tzinfo=timezone.utc)
        trades = self._build_trades([
            (10.0, base.replace(hour=3)),   # Asian
            (20.0, base.replace(hour=9)),   # London
            (30.0, base.replace(hour=15)),  # NY
            (40.0, base.replace(hour=21)),  # Off-hours
        ])
        result = builder._summarize_trades(trades)
        clusters = result['time_of_day_clusters']
        assert clusters['Asian_0000_0600']['avg_pnl'] == 10.0
        assert clusters['London_0700_1200']['avg_pnl'] == 20.0
        assert clusters['NY_1300_1800']['avg_pnl'] == 30.0
        assert clusters['OffHours_1900_2359']['avg_pnl'] == 40.0

    def test_time_of_day_trade_counts(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, tzinfo=timezone.utc)
        trades = self._build_trades([
            (10.0, base.replace(hour=1)),
            (20.0, base.replace(hour=2)),
            (30.0, base.replace(hour=9)),
        ])
        result = builder._summarize_trades(trades)
        clusters = result['time_of_day_clusters']
        assert clusters['Asian_0000_0600']['trade_count'] == 2
        assert clusters['London_0700_1200']['trade_count'] == 1
        assert clusters['NY_1300_1800']['trade_count'] == 0

    # ── consecutive_loss_runs ────────────────────────────────────────────────

    def test_no_losses(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        trades = self._build_trades([(50.0, base + timedelta(hours=i)) for i in range(10)])
        result = builder._summarize_trades(trades)
        clr = result['consecutive_loss_runs']
        assert clr['max_consecutive_losses'] == 0
        assert clr['total_loss_runs'] == 0

    def test_consecutive_losses_basic(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        pnls = [100, -50, -50, -50, 100, -80, -80]
        trades = self._build_trades([(p, base + timedelta(hours=i)) for i, p in enumerate(pnls)])
        result = builder._summarize_trades(trades)
        clr = result['consecutive_loss_runs']
        assert clr['max_consecutive_losses'] == 3
        assert clr['total_loss_runs'] == 2
        assert clr['runs_of_3_or_more'] == 1

    def test_streak_stats(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        # 3 wins, 2 losses, 1 win → max win streak=3
        pnls = [100, 100, 100, -50, -50, 100]
        trades = self._build_trades([(p, base + timedelta(hours=i)) for i, p in enumerate(pnls)])
        result = builder._summarize_trades(trades)
        ss = result['streak_stats']
        assert ss['max_win_streak'] == 3
        assert ss['max_loss_streak'] == 2

    # ── drawdown_stats ───────────────────────────────────────────────────────

    def test_drawdown_all_wins(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        trades = self._build_trades([(100.0, base + timedelta(hours=i)) for i in range(5)])
        result = builder._summarize_trades(trades)
        dd = result['drawdown_stats']
        assert dd['max_drawdown_abs'] == 0.0
        assert abs(dd['final_cumulative_pnl'] - 500.0) < 0.01

    def test_drawdown_loss_sequence(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        # peak at 200, then drops to 50 → drawdown = 150
        pnls = [100, 100, -80, -70]
        trades = self._build_trades([(p, base + timedelta(hours=i)) for i, p in enumerate(pnls)])
        result = builder._summarize_trades(trades)
        dd = result['drawdown_stats']
        assert abs(dd['max_drawdown_abs'] - 150.0) < 0.01

    # ── trade_sample ─────────────────────────────────────────────────────────

    def test_trade_sample_includes_best_and_worst(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        # 60 trades: first is big winner, second is big loser
        pnls = [1000.0, -900.0] + [10.0] * 58
        trades = self._build_trades([(p, base + timedelta(hours=i)) for i, p in enumerate(pnls)])
        result = builder._summarize_trades(trades)
        sample_numbers = {t['trade_number'] for t in result['trade_sample']}
        # trade 1 is the best, trade 2 is the worst — both must appear
        assert 1 in sample_numbers
        assert 2 in sample_numbers

    def test_trade_sample_includes_last_trades(self):
        builder = _make_builder()
        base = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        n = 60
        pnls = [10.0] * n
        trades = self._build_trades([(p, base + timedelta(hours=i)) for i, p in enumerate(pnls)])
        result = builder._summarize_trades(trades)
        sample_numbers = {t['trade_number'] for t in result['trade_sample']}
        # Last 5 trades (56–60) must be in the sample
        for num in range(n - 4, n + 1):
            assert num in sample_numbers
