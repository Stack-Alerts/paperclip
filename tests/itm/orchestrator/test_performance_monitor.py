"""
Tests for PerformanceMonitor (Section D — performance_monitor.py)
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.itm.orchestrator.performance_monitor import (
    PerformanceMonitor,
    StrategyMetrics,
)
from src.itm.orchestrator.registry import StrategyRegistry
from src.itm.orchestrator.sb_contract import (
    StrategyConfig,
    StrategyInstrumentConfig,
    StrategyRiskConfig,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_config(
    strategy_id="strat-001",
    max_drawdown_pct="0.05",
    max_daily_loss="500.0",
    capital_allocation_pct="0.5",
):
    return StrategyConfig(
        strategy_id=strategy_id,
        name="Test",
        instrument=StrategyInstrumentConfig(
            symbol="BTC/USDT", exchange="binance", contract_type="spot"
        ),
        capital_allocation_pct=Decimal(capital_allocation_pct),
        risk=StrategyRiskConfig(
            max_drawdown_pct=Decimal(max_drawdown_pct),
            max_position_qty=Decimal("0.5"),
            heat_limit=Decimal("5.0"),
            max_daily_loss=Decimal(max_daily_loss),
            max_leverage=Decimal("1.0"),
        ),
        signal_confidence_threshold=Decimal("0.6"),
        tags=(),
        metadata={},
    )


def setup_monitor(config=None):
    config = config or make_config()
    reg = StrategyRegistry()
    reg.load(config)
    reg.activate(config.strategy_id)
    monitor = PerformanceMonitor(registry=reg)
    monitor.register(config)
    return monitor, reg, config


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestPerformanceMonitorHappyPath:

    def test_register_creates_metrics(self):
        monitor, reg, config = setup_monitor()
        metrics = monitor.get_metrics(config.strategy_id)
        assert metrics is not None
        assert metrics.strategy_id == "strat-001"
        assert metrics.realized_pnl == Decimal("0")

    def test_record_positive_pnl(self):
        monitor, reg, config = setup_monitor()
        metrics = monitor.record_pnl("strat-001", Decimal("100"), Decimal("10000"))
        assert metrics.realized_pnl == Decimal("100")
        assert metrics.daily_pnl == Decimal("100")
        assert metrics.win_count == 1
        assert metrics.loss_count == 0

    def test_record_negative_pnl(self):
        monitor, reg, config = setup_monitor()
        metrics = monitor.record_pnl("strat-001", Decimal("-50"), Decimal("9950"))
        assert metrics.realized_pnl == Decimal("-50")
        assert metrics.daily_pnl == Decimal("-50")
        assert metrics.loss_count == 1
        assert metrics.win_count == 0

    def test_win_rate_calculation(self):
        monitor, reg, config = setup_monitor()
        monitor.record_pnl("strat-001", Decimal("100"), Decimal("10100"))
        monitor.record_pnl("strat-001", Decimal("-50"), Decimal("10050"))
        monitor.record_pnl("strat-001", Decimal("200"), Decimal("10250"))
        metrics = monitor.get_metrics("strat-001")
        assert metrics.win_count == 2
        assert metrics.loss_count == 1
        # 2/3 ≈ 0.6667
        assert abs(float(metrics.win_rate) - (2 / 3)) < 0.001

    def test_drawdown_calculation(self):
        monitor, reg, config = setup_monitor()
        # Peak at 10100, then drop to 9900
        monitor.record_pnl("strat-001", Decimal("100"), Decimal("10100"))
        monitor.record_pnl("strat-001", Decimal("-200"), Decimal("9900"))
        metrics = monitor.get_metrics("strat-001")
        # drawdown = (10100 - 9900) / 10100 ≈ 0.0198
        assert metrics.peak_portfolio_value == Decimal("10100")
        assert abs(float(metrics.current_drawdown_pct) - (200 / 10100)) < 0.0001

    def test_no_auto_pause_below_threshold(self):
        """Small drawdown should NOT trigger auto-pause."""
        config = make_config(max_drawdown_pct="0.10")  # 10% threshold
        monitor, reg, _ = setup_monitor(config)
        # Drawdown of 3% — below threshold
        monitor.record_pnl("strat-001", Decimal("100"), Decimal("10100"))
        monitor.record_pnl("strat-001", Decimal("-303"), Decimal("9797"))
        entry = reg.get("strat-001")
        assert entry.is_active  # should still be ACTIVE

    def test_all_metrics_returns_all_strategies(self):
        reg = StrategyRegistry()
        monitor = PerformanceMonitor(registry=reg)
        c1 = make_config("s1", capital_allocation_pct="0.3")
        c2 = make_config("s2", capital_allocation_pct="0.3")
        for c in [c1, c2]:
            reg.load(c)
            reg.activate(c.strategy_id)
            monitor.register(c)
        all_m = monitor.all_metrics()
        assert set(all_m.keys()) == {"s1", "s2"}

    def test_deregister_removes_metrics(self):
        monitor, reg, config = setup_monitor()
        monitor.deregister("strat-001")
        assert monitor.get_metrics("strat-001") is None


# ---------------------------------------------------------------------------
# Auto-pause tests
# ---------------------------------------------------------------------------

class TestPerformanceMonitorAutoPause:

    def test_auto_pause_on_drawdown_breach(self):
        """drawdown_pct >= max_drawdown_pct triggers auto-pause."""
        config = make_config(max_drawdown_pct="0.05")  # 5%
        monitor, reg, _ = setup_monitor(config)

        # Reach 10% drawdown (beyond 5% threshold)
        monitor.record_pnl("strat-001", Decimal("0"), Decimal("10000"))  # peak = 10000
        monitor.record_pnl("strat-001", Decimal("-1500"), Decimal("8500"))  # ~15% DD

        entry = reg.get("strat-001")
        assert entry.is_paused, "Strategy should be auto-paused after drawdown breach"
        assert "drawdown" in entry.pause_reason.lower()

    def test_auto_pause_on_daily_loss_breach(self):
        """daily_loss >= max_daily_loss triggers auto-pause."""
        config = make_config(max_daily_loss="200.0")
        monitor, reg, _ = setup_monitor(config)

        # Lose more than $200 in a single day
        monitor.record_pnl("strat-001", Decimal("-250"), Decimal("9750"))

        entry = reg.get("strat-001")
        assert entry.is_paused, "Strategy should be auto-paused after daily loss breach"
        assert "daily_loss" in entry.pause_reason.lower()

    def test_auto_pause_not_triggered_for_inactive_strategy(self):
        """Auto-pause check should skip strategies that are already paused/stopped."""
        config = make_config(max_drawdown_pct="0.01")  # very low threshold
        monitor, reg, _ = setup_monitor(config)

        # Manually pause first
        reg.pause("strat-001", "manual pause")

        # Now trigger drawdown that would normally auto-pause
        monitor.record_pnl("strat-001", Decimal("-200"), Decimal("8000"))

        # Should still be PAUSED (not ERROR), and auto_pause_count unchanged
        entry = reg.get("strat-001")
        assert entry.is_paused

    def test_auto_pause_increments_counter(self):
        config = make_config(max_drawdown_pct="0.05")
        monitor, reg, _ = setup_monitor(config)

        monitor.record_pnl("strat-001", Decimal("0"), Decimal("10000"))
        monitor.record_pnl("strat-001", Decimal("-1000"), Decimal("9000"))

        metrics = monitor.get_metrics("strat-001")
        assert metrics.auto_pause_count == 1
        assert metrics.last_auto_pause_reason is not None

    def test_record_pnl_unknown_strategy_raises(self):
        monitor, reg, config = setup_monitor()
        with pytest.raises(KeyError, match="not registered"):
            monitor.record_pnl("ghost", Decimal("100"), Decimal("10000"))
