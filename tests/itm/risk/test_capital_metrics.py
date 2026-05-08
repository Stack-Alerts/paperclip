"""
Tests — CapitalMetrics (Section F)
=====================================
Covers:
- record_trade updates win/loss counters
- win_rate computation
- profit_factor: gross_profit / gross_loss; all-wins case
- max_drawdown: peak-to-trough tracking
- sharpe_ratio: returns None with < 2 trades; computes value otherwise
- total_pnl cumulative
- snapshot
- reset
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from src.itm.risk.capital_metrics import CapitalMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_metrics(initial_capital="25000"):
    return CapitalMetrics(initial_capital=Decimal(initial_capital))


# ---------------------------------------------------------------------------
# Win/Loss counters
# ---------------------------------------------------------------------------

class TestWinLossCounters:

    def test_initial_state(self):
        m = make_metrics()
        assert m.total_trades == 0
        assert m.win_rate is None
        assert m.profit_factor is None

    def test_win_recorded(self):
        m = make_metrics()
        m.record_trade(Decimal("100"), Decimal("25100"))
        assert m.total_trades == 1
        assert m.win_rate == Decimal("1")  # 1/1

    def test_loss_recorded(self):
        m = make_metrics()
        m.record_trade(Decimal("-50"), Decimal("24950"))
        assert m.total_trades == 1
        assert m.win_rate == Decimal("0")

    def test_mixed_win_rate(self):
        m = make_metrics()
        m.record_trade(Decimal("100"), Decimal("25100"))
        m.record_trade(Decimal("-50"), Decimal("25050"))
        m.record_trade(Decimal("80"), Decimal("25130"))
        # 2 wins, 1 loss
        assert m.win_rate == Decimal("2") / Decimal("3")

    def test_total_pnl_accumulates(self):
        m = make_metrics()
        m.record_trade(Decimal("100"), Decimal("25100"))
        m.record_trade(Decimal("-50"), Decimal("25050"))
        assert m.total_pnl == Decimal("50")


# ---------------------------------------------------------------------------
# Profit factor
# ---------------------------------------------------------------------------

class TestProfitFactor:

    def test_profit_factor_with_wins_and_losses(self):
        m = make_metrics()
        m.record_trade(Decimal("300"), Decimal("25300"))  # gross profit: 300
        m.record_trade(Decimal("-100"), Decimal("25200"))  # gross loss: 100
        # PF = 300 / 100 = 3.0
        pf = m.profit_factor
        assert pf == Decimal("3.0")

    def test_profit_factor_all_wins(self):
        m = make_metrics()
        m.record_trade(Decimal("100"), Decimal("25100"))
        m.record_trade(Decimal("200"), Decimal("25300"))
        # No losses → returns 999.99
        assert m.profit_factor == Decimal("999.99")

    def test_profit_factor_none_when_no_trades(self):
        m = make_metrics()
        assert m.profit_factor is None


# ---------------------------------------------------------------------------
# Max drawdown
# ---------------------------------------------------------------------------

class TestMaxDrawdown:

    def test_no_drawdown_initially(self):
        m = make_metrics(initial_capital="25000")
        assert m.max_drawdown == Decimal("0")

    def test_drawdown_computed(self):
        m = make_metrics(initial_capital="25000")
        m.record_trade(Decimal("0"), Decimal("25000"))   # establish peak = 25000
        m.record_trade(Decimal("-1250"), Decimal("23750"))  # drawdown = 1250/25000 = 5%
        assert m.max_drawdown == Decimal("1250") / Decimal("25000")

    def test_max_drawdown_is_worst_ever(self):
        m = make_metrics(initial_capital="25000")
        m.record_trade(Decimal("0"), Decimal("25000"))
        m.record_trade(Decimal("-2500"), Decimal("22500"))  # 10% drawdown
        m.record_trade(Decimal("1000"), Decimal("23500"))   # partial recovery
        m.record_trade(Decimal("-1000"), Decimal("22500"))  # back to same → same max
        # Max drawdown should still be 10%
        assert m.max_drawdown == Decimal("2500") / Decimal("25000")

    def test_peak_tracks_new_highs(self):
        m = make_metrics(initial_capital="25000")
        m.record_trade(Decimal("5000"), Decimal("30000"))  # new peak
        m.record_trade(Decimal("-1000"), Decimal("29000"))  # drawdown = 1000/30000
        expected = Decimal("1000") / Decimal("30000")
        assert m.max_drawdown == expected


# ---------------------------------------------------------------------------
# Sharpe ratio
# ---------------------------------------------------------------------------

class TestSharpeRatio:

    def test_sharpe_none_with_one_trade(self):
        m = make_metrics()
        m.record_trade(Decimal("100"), Decimal("25100"))
        assert m.sharpe_ratio is None  # need at least 2

    def test_sharpe_some_value_with_multiple_trades(self):
        m = make_metrics(initial_capital="25000")
        # Record several trades
        portfolio = Decimal("25000")
        for _ in range(10):
            pnl = Decimal("50")
            portfolio += pnl
            m.record_trade(pnl, portfolio)
        sr = m.sharpe_ratio
        # With all positive returns, SR should be positive (and not None)
        assert sr is not None
        assert sr > Decimal("0")

    def test_sharpe_negative_with_all_losses(self):
        m = make_metrics(initial_capital="25000")
        portfolio = Decimal("25000")
        for _ in range(5):
            pnl = Decimal("-100")
            portfolio += pnl
            m.record_trade(pnl, portfolio)
        sr = m.sharpe_ratio
        assert sr is not None
        assert sr < Decimal("0")


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:

    def test_snapshot_reflects_state(self):
        m = make_metrics(initial_capital="25000")
        m.record_trade(Decimal("100"), Decimal("25100"))
        m.record_trade(Decimal("-50"), Decimal("25050"))
        snap = m.snapshot()
        assert snap.total_trades == 2
        assert snap.win_count == 1
        assert snap.loss_count == 1
        assert snap.total_pnl == Decimal("50")
        assert snap.snapshot_at is not None


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestReset:

    def test_reset_clears_all_state(self):
        m = make_metrics()
        m.record_trade(Decimal("100"), Decimal("25100"))
        m.record_trade(Decimal("-50"), Decimal("25050"))
        m.reset()
        assert m.total_trades == 0
        assert m.total_pnl == Decimal("0")
        assert m.max_drawdown == Decimal("0")
        assert m.win_rate is None
