"""
Tests: ITM State Schema (schema.py)
====================================
Covers:
- ITMSystemState construction and helpers
- StrategyState (run states, daily reset, serialisation)
- RiskSnapshot (daily loss limit, heat limit)
- StateCheckpoint (envelope, latency flags, aliases)
- Serialisation round-trips: to_dict() / from_dict()
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from src.itm.state.schema import (
    ITMSystemState,
    StrategyState,
    StrategyRunState,
    RiskSnapshot,
    StateCheckpoint,
)
from src.itm.domain.entities import (
    AccountHeat,
    CapitalState,
    Instrument,
    ContractType,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    Position,
    PositionDirection,
    PositionEntry,
    RiskProfile,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def btc_instrument():
    return Instrument.btc_usdt_spot()


@pytest.fixture
def open_position(btc_instrument):
    pos = Position(instrument=btc_instrument, direction=PositionDirection.LONG)
    pos.add_entry(
        PositionEntry(order_id="ord-1", quantity=Decimal("0.1"), price=Decimal("45000"))
    )
    return pos


@pytest.fixture
def pending_order(btc_instrument):
    return Order(
        instrument=btc_instrument,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.1"),
        price=None,
    )


# ---------------------------------------------------------------------------
# StrategyState
# ---------------------------------------------------------------------------


class TestStrategyState:
    def test_construction_defaults(self):
        ss = StrategyState(strategy_id="strat-1")
        assert ss.strategy_id == "strat-1"
        assert ss.run_state == StrategyRunState.ACTIVE
        assert ss.heat == Decimal("0")
        assert ss.realized_pnl == Decimal("0")
        assert ss.daily_pnl == Decimal("0")
        assert ss.daily_pnl_date is not None

    def test_empty_strategy_id_raises(self):
        with pytest.raises(ValueError, match="strategy_id"):
            StrategyState(strategy_id="")

    def test_daily_reset_not_needed_same_day(self):
        ss = StrategyState(strategy_id="strat-1")
        ss.daily_pnl = Decimal("-100")
        reset = ss.apply_daily_reset_if_needed()
        assert not reset
        assert ss.daily_pnl == Decimal("-100")

    def test_daily_reset_needed_old_date(self):
        ss = StrategyState(strategy_id="strat-1")
        ss.daily_pnl = Decimal("-200")
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        ss.daily_pnl_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        reset = ss.apply_daily_reset_if_needed()
        assert reset
        assert ss.daily_pnl == Decimal("0")

    def test_serialisation_round_trip_basic(self):
        ss = StrategyState(strategy_id="s1")
        ss.heat = Decimal("2.5")
        ss.realized_pnl = Decimal("1234.56")
        ss.daily_pnl = Decimal("-50")
        ss.run_state = StrategyRunState.PAUSED
        d = ss.to_dict()
        restored = StrategyState.from_dict(d)
        assert restored.strategy_id == "s1"
        assert restored.heat == Decimal("2.5")
        assert restored.realized_pnl == Decimal("1234.56")
        assert restored.daily_pnl == Decimal("-50")
        assert restored.run_state == StrategyRunState.PAUSED

    def test_serialisation_with_instrument(self, btc_instrument):
        ss = StrategyState(strategy_id="s1", instrument=btc_instrument)
        d = ss.to_dict()
        restored = StrategyState.from_dict(d)
        assert restored.instrument is not None
        assert restored.instrument.symbol == "BTC/USDT"

    def test_serialisation_with_risk_profile(self):
        rp = RiskProfile(
            strategy_id="s1",
            max_drawdown_pct=Decimal("0.05"),
            max_position_qty=Decimal("1.0"),
            heat_limit=Decimal("10.0"),
            max_daily_loss=Decimal("500.00"),
        )
        ss = StrategyState(strategy_id="s1", risk_profile=rp)
        d = ss.to_dict()
        restored = StrategyState.from_dict(d)
        assert restored.risk_profile is not None
        assert restored.risk_profile.max_daily_loss == Decimal("500.00")

    def test_all_run_states_serialise(self):
        for state in StrategyRunState:
            ss = StrategyState(strategy_id="s1", run_state=state)
            d = ss.to_dict()
            restored = StrategyState.from_dict(d)
            assert restored.run_state == state

    def test_open_order_ids_round_trip(self):
        ss = StrategyState(strategy_id="s1")
        ss.open_order_ids = {"o1", "o2", "o3"}
        d = ss.to_dict()
        restored = StrategyState.from_dict(d)
        assert restored.open_order_ids == {"o1", "o2", "o3"}


# ---------------------------------------------------------------------------
# RiskSnapshot
# ---------------------------------------------------------------------------


class TestRiskSnapshot:
    def test_defaults(self):
        r = RiskSnapshot()
        assert not r.heat_at_limit
        assert not r.daily_loss_limit_reached

    def test_daily_loss_limit_reached_at_limit(self):
        r = RiskSnapshot(
            total_daily_pnl=Decimal("-500"),
            max_daily_loss=Decimal("500"),
        )
        assert r.daily_loss_limit_reached

    def test_daily_loss_limit_reached_over_limit(self):
        r = RiskSnapshot(
            total_daily_pnl=Decimal("-600"),
            max_daily_loss=Decimal("500"),
        )
        assert r.daily_loss_limit_reached

    def test_daily_loss_not_reached(self):
        r = RiskSnapshot(
            total_daily_pnl=Decimal("-499"),
            max_daily_loss=Decimal("500"),
        )
        assert not r.daily_loss_limit_reached

    def test_heat_at_limit_via_account_heat(self):
        ah = AccountHeat(max_heat=Decimal("10"))
        ah.current_heat = Decimal("10")
        r = RiskSnapshot(account_heat=ah)
        assert r.heat_at_limit

    def test_heat_not_at_limit(self):
        ah = AccountHeat(max_heat=Decimal("10"))
        ah.current_heat = Decimal("5")
        r = RiskSnapshot(account_heat=ah)
        assert not r.heat_at_limit

    def test_serialisation_round_trip(self):
        ah = AccountHeat(max_heat=Decimal("10"))
        ah.current_heat = Decimal("3")
        cs = CapitalState(
            total_capital=Decimal("10000"),
            allocated=Decimal("2000"),
            locked=Decimal("0"),
        )
        r = RiskSnapshot(
            account_heat=ah,
            capital_state=cs,
            total_open_positions=2,
            total_pending_orders=1,
            total_realized_pnl=Decimal("500"),
            total_daily_pnl=Decimal("-100"),
        )
        d = r.to_dict()
        restored = RiskSnapshot.from_dict(d)
        assert restored.total_open_positions == 2
        assert restored.total_pending_orders == 1
        assert restored.total_daily_pnl == Decimal("-100")
        assert restored.account_heat is not None
        assert restored.account_heat.max_heat == Decimal("10")
        assert restored.capital_state is not None
        assert restored.capital_state.total_capital == Decimal("10000")


# ---------------------------------------------------------------------------
# ITMSystemState
# ---------------------------------------------------------------------------


class TestITMSystemState:
    def test_construction_empty(self):
        state = ITMSystemState()
        assert state.state_id is not None
        assert len(state.positions) == 0
        assert len(state.orders) == 0
        assert len(state.strategies) == 0
        assert state.checkpoint_seq == 0

    def test_add_and_open_positions(self, open_position):
        state = ITMSystemState()
        state.add_position(open_position, "strat-1")
        assert open_position.position_id in state.positions
        assert len(state.open_positions()) == 1

    def test_add_position_associates_with_strategy(self, open_position):
        state = ITMSystemState()
        state.ensure_strategy("s1")
        state.add_position(open_position, "s1")
        assert state.strategies["s1"].active_position_id == open_position.position_id

    def test_close_position_clears_strategy(self, open_position):
        state = ITMSystemState()
        state.ensure_strategy("s1")
        state.add_position(open_position, "s1")
        state.close_position(open_position.position_id, "s1")
        assert state.strategies["s1"].active_position_id is None

    def test_add_order(self, pending_order):
        state = ITMSystemState()
        state.add_order(pending_order)
        assert pending_order.client_order_id in state.orders

    def test_remove_terminal_orders(self, btc_instrument):
        state = ITMSystemState()
        order_pending = Order(
            instrument=btc_instrument,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            price=None,
        )
        order_closed = Order(
            instrument=btc_instrument,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            price=None,
            status=OrderStatus.CLOSED,
        )
        state.add_order(order_pending)
        state.add_order(order_closed)
        removed = state.remove_terminal_orders()
        assert removed == 1
        assert order_pending.client_order_id in state.orders
        assert order_closed.client_order_id not in state.orders

    def test_ensure_strategy_idempotent(self):
        state = ITMSystemState()
        s1 = state.ensure_strategy("s1")
        s2 = state.ensure_strategy("s1")
        assert s1 is s2

    def test_apply_daily_resets(self):
        state = ITMSystemState()
        ss = state.ensure_strategy("s1")
        ss.daily_pnl = Decimal("-100")
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        ss.daily_pnl_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        reset_ids = state.apply_daily_resets()
        assert "s1" in reset_ids
        assert ss.daily_pnl == Decimal("0")

    def test_serialisation_round_trip_empty(self):
        state = ITMSystemState()
        d = state.to_dict()
        restored = ITMSystemState.from_dict(d)
        assert restored.state_id == state.state_id
        assert restored.checkpoint_seq == 0

    def test_serialisation_round_trip_with_position(self, open_position):
        state = ITMSystemState()
        state.add_position(open_position, "s1")
        d = state.to_dict()
        json_str = json.dumps(d, default=str)
        assert len(json_str) > 0
        restored = ITMSystemState.from_dict(d)
        assert len(restored.positions) == 1
        pos_restored = list(restored.positions.values())[0]
        assert pos_restored.instrument.symbol == "BTC/USDT"
        assert pos_restored.direction == PositionDirection.LONG
        assert pos_restored.entries[0].quantity == Decimal("0.1")

    def test_serialisation_round_trip_with_order(self, pending_order):
        state = ITMSystemState()
        state.add_order(pending_order)
        d = state.to_dict()
        restored = ITMSystemState.from_dict(d)
        assert len(restored.orders) == 1
        ord_restored = list(restored.orders.values())[0]
        assert ord_restored.quantity == Decimal("0.1")
        assert ord_restored.side == OrderSide.BUY
        assert ord_restored.status == OrderStatus.PENDING

    def test_serialisation_round_trip_with_strategy(self):
        state = ITMSystemState()
        ss = state.ensure_strategy("s1")
        ss.heat = Decimal("4")
        ss.run_state = StrategyRunState.COOLDOWN
        d = state.to_dict()
        restored = ITMSystemState.from_dict(d)
        assert "s1" in restored.strategies
        assert restored.strategies["s1"].heat == Decimal("4")
        assert restored.strategies["s1"].run_state == StrategyRunState.COOLDOWN

    def test_touch_updates_timestamp(self):
        state = ITMSystemState()
        old_ts = state.updated_at
        state.touch()
        assert state.updated_at >= old_ts


# ---------------------------------------------------------------------------
# StateCheckpoint
# ---------------------------------------------------------------------------


class TestStateCheckpoint:
    def test_defaults(self):
        cp = StateCheckpoint()
        assert cp.sequence == 0
        assert cp.source == "bar_close"
        assert not cp.redis_ok
        assert not cp.pg_ok
        assert not cp.any_store_ok

    def test_redis_ok(self):
        cp = StateCheckpoint(redis_latency_ms=10.5)
        assert cp.redis_ok
        assert cp.any_store_ok

    def test_pg_ok(self):
        cp = StateCheckpoint(pg_latency_ms=25.3)
        assert cp.pg_ok
        assert cp.any_store_ok

    def test_aliases_sequence_seq(self):
        cp = StateCheckpoint(sequence=42)
        assert cp.seq == 42
        cp.seq = 100
        assert cp.sequence == 100

    def test_aliases_source_trigger(self):
        cp = StateCheckpoint(source="on_demand")
        assert cp.trigger == "on_demand"
        cp.trigger = "shutdown"
        assert cp.source == "shutdown"

    def test_aliases_checkpointed_at_written_at(self):
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc)
        cp = StateCheckpoint(checkpointed_at=ts)
        assert cp.written_at == ts

    def test_serialisation_round_trip(self):
        state = ITMSystemState()
        cp = StateCheckpoint(
            sequence=42,
            state=state,
            source="on_demand",
            redis_latency_ms=15.2,
            pg_latency_ms=30.1,
        )
        d = cp.to_dict()
        restored = StateCheckpoint.from_dict(d)
        assert restored.sequence == 42
        assert restored.source == "on_demand"
        assert restored.redis_latency_ms == 15.2
        assert restored.pg_latency_ms == 30.1
        assert restored.redis_ok
        assert restored.pg_ok
