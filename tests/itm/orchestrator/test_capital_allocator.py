"""
Tests for CapitalAllocator (Section D — capital_allocator.py)
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.itm.orchestrator.capital_allocator import (
    CapitalAllocator,
    CapitalAllocatorError,
    StrategyCapitalSlice,
)
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
            max_drawdown_pct=Decimal("0.05"),
            max_position_qty=Decimal("0.5"),
            heat_limit=Decimal("5.0"),
            max_daily_loss=Decimal("400.0"),
            max_leverage=Decimal("1.0"),
        ),
        signal_confidence_threshold=Decimal("0.6"),
        tags=(),
        metadata={},
    )


TOTAL = Decimal("10000")


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestCapitalAllocatorHappyPath:

    def test_register_single_strategy(self):
        alloc = CapitalAllocator(TOTAL)
        config = make_config(capital_allocation_pct="0.5")
        slice_ = alloc.register(config)
        assert slice_.allocated_capital == Decimal("5000")
        assert slice_.in_use == Decimal("0")
        assert slice_.available_capital == Decimal("5000")

    def test_two_strategies(self):
        alloc = CapitalAllocator(TOTAL)
        c1 = make_config("s1", "0.3")
        c2 = make_config("s2", "0.4")
        alloc.register(c1)
        alloc.register(c2)
        assert alloc.get_slice("s1").allocated_capital == Decimal("3000")
        assert alloc.get_slice("s2").allocated_capital == Decimal("4000")
        assert alloc.total_allocated == Decimal("7000")

    def test_record_and_release_capital_use(self):
        alloc = CapitalAllocator(TOTAL)
        config = make_config()
        alloc.register(config)
        alloc.record_capital_use("strat-001", Decimal("2000"))
        s = alloc.get_slice("strat-001")
        assert s.in_use == Decimal("2000")
        assert s.available_capital == Decimal("3000")

        alloc.release_capital_use("strat-001", Decimal("2000"))
        s = alloc.get_slice("strat-001")
        assert s.in_use == Decimal("0")
        assert s.available_capital == Decimal("5000")

    def test_can_allocate(self):
        alloc = CapitalAllocator(TOTAL)
        config = make_config()
        alloc.register(config)
        assert alloc.can_allocate("strat-001", Decimal("5000")) is True
        assert alloc.can_allocate("strat-001", Decimal("5001")) is False

    def test_rebalance_on_new_total(self):
        alloc = CapitalAllocator(TOTAL)
        config = make_config(capital_allocation_pct="0.5")
        alloc.register(config)
        alloc.rebalance(new_total_capital=Decimal("20000"))
        s = alloc.get_slice("strat-001")
        assert s.allocated_capital == Decimal("10000")
        assert alloc.total_capital == Decimal("20000")

    def test_deregister_strategy(self):
        alloc = CapitalAllocator(TOTAL)
        config = make_config()
        alloc.register(config)
        alloc.deregister("strat-001")
        assert alloc.get_slice("strat-001") is None
        assert alloc.total_allocated == Decimal("0")

    def test_release_caps_at_zero(self):
        """Release more than in_use should clamp to 0, not go negative."""
        alloc = CapitalAllocator(TOTAL)
        alloc.register(make_config())
        alloc.record_capital_use("strat-001", Decimal("1000"))
        alloc.release_capital_use("strat-001", Decimal("9999"))  # more than in_use
        assert alloc.get_slice("strat-001").in_use == Decimal("0")

    def test_utilization_pct(self):
        alloc = CapitalAllocator(TOTAL)
        alloc.register(make_config())
        alloc.record_capital_use("strat-001", Decimal("2500"))
        s = alloc.get_slice("strat-001")
        # 2500 / 5000 = 0.5
        assert s.utilization_pct == Decimal("0.5")

    def test_snapshot(self):
        alloc = CapitalAllocator(TOTAL)
        alloc.register(make_config("s1", "0.3"))
        alloc.register(make_config("s2", "0.4"))
        snap = alloc.snapshot()
        assert set(snap.keys()) == {"s1", "s2"}


# ---------------------------------------------------------------------------
# Error / constraint tests
# ---------------------------------------------------------------------------

class TestCapitalAllocatorErrors:

    def test_zero_total_capital_raises(self):
        with pytest.raises(CapitalAllocatorError):
            CapitalAllocator(Decimal("0"))

    def test_register_duplicate_raises(self):
        alloc = CapitalAllocator(TOTAL)
        config = make_config()
        alloc.register(config)
        with pytest.raises(CapitalAllocatorError, match="already registered"):
            alloc.register(config)

    def test_record_use_exceeds_allocation_raises(self):
        alloc = CapitalAllocator(TOTAL)
        alloc.register(make_config())  # 5000 allocated
        with pytest.raises(CapitalAllocatorError, match="cannot commit"):
            alloc.record_capital_use("strat-001", Decimal("6000"))

    def test_record_use_for_unknown_raises(self):
        alloc = CapitalAllocator(TOTAL)
        with pytest.raises(CapitalAllocatorError, match="not registered"):
            alloc.record_capital_use("ghost", Decimal("100"))

    def test_deregister_unknown_raises(self):
        alloc = CapitalAllocator(TOTAL)
        with pytest.raises(CapitalAllocatorError, match="not registered"):
            alloc.deregister("ghost")

    def test_can_allocate_for_unknown_returns_false(self):
        alloc = CapitalAllocator(TOTAL)
        assert alloc.can_allocate("ghost", Decimal("100")) is False

    def test_rebalance_with_zero_total_raises(self):
        alloc = CapitalAllocator(TOTAL)
        with pytest.raises(CapitalAllocatorError):
            alloc.rebalance(new_total_capital=Decimal("0"))
