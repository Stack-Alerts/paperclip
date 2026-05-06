"""
Unit tests for ITM domain entities.
Covers: Instrument, Order, Position, Signal, Decision, RiskProfile,
        AccountHeat, CapitalState, PositionEntry, PositionExit
        + the TradeState / TradeStateMachine state machine
        + DomainEvent subclasses
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from src.itm.domain.entities import (
    AccountHeat,
    CapitalState,
    ContractType,
    Decision,
    DecisionAction,
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionDirection,
    PositionEntry,
    PositionExit,
    RiskProfile,
    Signal,
    SignalDirection,
)
from src.itm.domain.state import (
    InvalidStateTransition,
    TradeState,
    TradeStateMachine,
)
from src.itm.domain.events import (
    CapitalStateChanged,
    DecisionMade,
    DomainEvent,
    PositionUpdated,
    RiskLimitBreached,
    SignalReceived,
    TradeCancelled,
    TradeClosed,
    TradeError,
    TradeFilled,
    TradeOpened,
    TradePartialFill,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def btc_spot() -> Instrument:
    return Instrument.btc_usdt_spot("binance")


@pytest.fixture
def btc_perp() -> Instrument:
    return Instrument.btc_usdt_perp("bybit")


@pytest.fixture
def basic_order(btc_spot: Instrument) -> Order:
    return Order(
        instrument=btc_spot,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("0.1"),
        price=Decimal("45000.00"),
    )


@pytest.fixture
def basic_signal(btc_spot: Instrument) -> Signal:
    return Signal(
        direction=SignalDirection.LONG,
        strength=Decimal("0.75"),
        source_strategy="test_strat",
        instrument=btc_spot,
    )


# ---------------------------------------------------------------------------
# Instrument tests
# ---------------------------------------------------------------------------


class TestInstrument:
    def test_btc_usdt_spot_defaults(self, btc_spot: Instrument) -> None:
        assert btc_spot.symbol == "BTC/USDT"
        assert btc_spot.exchange == "binance"
        assert btc_spot.contract_type == ContractType.SPOT
        assert btc_spot.tick_size == Decimal("0.01")
        assert btc_spot.lot_size == Decimal("0.00001")
        assert btc_spot.base_currency == "BTC"
        assert btc_spot.quote_currency == "USDT"

    def test_btc_usdt_perp_defaults(self, btc_perp: Instrument) -> None:
        assert btc_perp.contract_type == ContractType.PERPETUAL
        assert btc_perp.exchange == "bybit"
        assert btc_perp.tick_size == Decimal("0.10")
        assert btc_perp.lot_size == Decimal("0.001")

    def test_frozen_immutable(self, btc_spot: Instrument) -> None:
        with pytest.raises((AttributeError, TypeError)):
            btc_spot.symbol = "ETH/USDT"  # type: ignore[misc]

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            Instrument(
                symbol="",
                exchange="binance",
                contract_type=ContractType.SPOT,
                tick_size=Decimal("0.01"),
                lot_size=Decimal("0.001"),
            )

    def test_empty_exchange_raises(self) -> None:
        with pytest.raises(ValueError, match="exchange"):
            Instrument(
                symbol="BTC/USDT",
                exchange="",
                contract_type=ContractType.SPOT,
                tick_size=Decimal("0.01"),
                lot_size=Decimal("0.001"),
            )

    def test_zero_tick_size_raises(self) -> None:
        with pytest.raises(ValueError, match="tick_size"):
            Instrument(
                symbol="BTC/USDT",
                exchange="binance",
                contract_type=ContractType.SPOT,
                tick_size=Decimal("0"),
                lot_size=Decimal("0.001"),
            )

    def test_negative_lot_size_raises(self) -> None:
        with pytest.raises(ValueError, match="lot_size"):
            Instrument(
                symbol="BTC/USDT",
                exchange="binance",
                contract_type=ContractType.SPOT,
                tick_size=Decimal("0.01"),
                lot_size=Decimal("-0.001"),
            )


# ---------------------------------------------------------------------------
# Order tests
# ---------------------------------------------------------------------------


class TestOrder:
    def test_create_limit_order(self, basic_order: Order) -> None:
        assert basic_order.side == OrderSide.BUY
        assert basic_order.order_type == OrderType.LIMIT
        assert basic_order.quantity == Decimal("0.1")
        assert basic_order.price == Decimal("45000.00")
        assert basic_order.status == OrderStatus.PENDING
        assert basic_order.filled_quantity == Decimal("0")
        assert basic_order.remaining_quantity == Decimal("0.1")

    def test_create_market_order(self, btc_spot: Instrument) -> None:
        order = Order(
            instrument=btc_spot,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.05"),
            price=None,
        )
        assert order.price is None
        assert order.remaining_quantity == Decimal("0.05")

    def test_is_terminal_states(self, btc_spot: Instrument) -> None:
        def order_with_status(s: OrderStatus) -> Order:
            o = Order(
                instrument=btc_spot,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.01"),
                price=None,
            )
            o.status = s
            return o

        assert not order_with_status(OrderStatus.PENDING).is_terminal
        assert not order_with_status(OrderStatus.OPEN).is_terminal
        assert not order_with_status(OrderStatus.PARTIAL).is_terminal
        assert order_with_status(OrderStatus.CLOSED).is_terminal
        assert order_with_status(OrderStatus.CANCELLED).is_terminal
        assert order_with_status(OrderStatus.ERROR).is_terminal

    def test_zero_quantity_raises(self, btc_spot: Instrument) -> None:
        with pytest.raises(ValueError, match="quantity"):
            Order(
                instrument=btc_spot,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0"),
                price=None,
            )

    def test_negative_price_raises(self, btc_spot: Instrument) -> None:
        with pytest.raises(ValueError, match="price"):
            Order(
                instrument=btc_spot,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("0.1"),
                price=Decimal("-1"),
            )

    def test_client_order_id_auto_generated(self, basic_order: Order) -> None:
        assert len(basic_order.client_order_id) == 36  # UUID4

    def test_touch_updates_timestamp(self, basic_order: Order) -> None:
        before = basic_order.updated_at
        import time
        time.sleep(0.01)
        basic_order.touch()
        assert basic_order.updated_at > before


# ---------------------------------------------------------------------------
# Position tests
# ---------------------------------------------------------------------------


class TestPosition:
    def _make_position(self, instrument: Instrument) -> Position:
        return Position(instrument=instrument, direction=PositionDirection.LONG)

    def test_empty_position(self, btc_spot: Instrument) -> None:
        pos = self._make_position(btc_spot)
        assert pos.open_quantity == Decimal("0")
        assert pos.total_entered == Decimal("0")
        assert pos.average_entry_price is None
        assert pos.realized_pnl == Decimal("0")
        assert not pos.is_open

    def test_add_entry(self, btc_spot: Instrument) -> None:
        pos = self._make_position(btc_spot)
        entry = PositionEntry(
            order_id="o1",
            quantity=Decimal("0.1"),
            price=Decimal("40000"),
        )
        pos.add_entry(entry)
        assert pos.open_quantity == Decimal("0.1")
        assert pos.average_entry_price == Decimal("40000")
        assert pos.is_open

    def test_multiple_entries_vwap(self, btc_spot: Instrument) -> None:
        pos = self._make_position(btc_spot)
        pos.add_entry(PositionEntry("o1", Decimal("0.1"), Decimal("40000")))
        pos.add_entry(PositionEntry("o2", Decimal("0.2"), Decimal("50000")))
        expected_vwap = (
            Decimal("0.1") * Decimal("40000") + Decimal("0.2") * Decimal("50000")
        ) / Decimal("0.3")
        assert pos.average_entry_price == expected_vwap

    def test_unrealized_pnl_long(self, btc_spot: Instrument) -> None:
        pos = self._make_position(btc_spot)
        pos.add_entry(PositionEntry("o1", Decimal("1.0"), Decimal("40000")))
        assert pos.unrealized_pnl(Decimal("45000")) == Decimal("5000")
        assert pos.unrealized_pnl(Decimal("35000")) == Decimal("-5000")

    def test_unrealized_pnl_short(self, btc_spot: Instrument) -> None:
        pos = Position(instrument=btc_spot, direction=PositionDirection.SHORT)
        pos.add_entry(PositionEntry("o1", Decimal("1.0"), Decimal("50000")))
        assert pos.unrealized_pnl(Decimal("45000")) == Decimal("5000")
        assert pos.unrealized_pnl(Decimal("55000")) == Decimal("-5000")

    def test_add_exit(self, btc_spot: Instrument) -> None:
        pos = self._make_position(btc_spot)
        pos.add_entry(PositionEntry("o1", Decimal("1.0"), Decimal("40000")))
        pos.add_exit(PositionExit("o2", Decimal("0.5"), Decimal("45000"), pnl=Decimal("2500")))
        assert pos.open_quantity == Decimal("0.5")
        assert pos.realized_pnl == Decimal("2500")

    def test_exit_exceeds_open_qty_raises(self, btc_spot: Instrument) -> None:
        pos = self._make_position(btc_spot)
        pos.add_entry(PositionEntry("o1", Decimal("0.5"), Decimal("40000")))
        with pytest.raises(ValueError, match="open quantity"):
            pos.add_exit(PositionExit("o2", Decimal("1.0"), Decimal("45000")))

    def test_close_sets_closed_at(self, btc_spot: Instrument) -> None:
        pos = self._make_position(btc_spot)
        pos.add_entry(PositionEntry("o1", Decimal("0.1"), Decimal("40000")))
        assert pos.closed_at is None
        pos.add_exit(PositionExit("o2", Decimal("0.1"), Decimal("45000"), pnl=Decimal("500")))
        assert pos.closed_at is not None

    def test_position_entry_validation(self) -> None:
        with pytest.raises(ValueError):
            PositionEntry("o1", Decimal("0"), Decimal("40000"))
        with pytest.raises(ValueError):
            PositionEntry("o1", Decimal("0.1"), Decimal("0"))

    def test_position_exit_validation(self) -> None:
        with pytest.raises(ValueError):
            PositionExit("o1", Decimal("0"), Decimal("40000"))
        with pytest.raises(ValueError):
            PositionExit("o1", Decimal("0.1"), Decimal("-1"))


# ---------------------------------------------------------------------------
# Signal tests
# ---------------------------------------------------------------------------


class TestSignal:
    def test_valid_signal(self, basic_signal: Signal) -> None:
        assert basic_signal.direction == SignalDirection.LONG
        assert basic_signal.strength == Decimal("0.75")
        assert basic_signal.source_strategy == "test_strat"
        assert not basic_signal.is_expired

    def test_strength_out_of_range_raises(self, btc_spot: Instrument) -> None:
        with pytest.raises(ValueError, match="strength"):
            Signal(
                direction=SignalDirection.LONG,
                strength=Decimal("1.5"),
                source_strategy="s1",
                instrument=btc_spot,
            )

    def test_negative_strength_raises(self, btc_spot: Instrument) -> None:
        with pytest.raises(ValueError, match="strength"):
            Signal(
                direction=SignalDirection.LONG,
                strength=Decimal("-0.1"),
                source_strategy="s1",
                instrument=btc_spot,
            )

    def test_empty_source_strategy_raises(self, btc_spot: Instrument) -> None:
        with pytest.raises(ValueError, match="source_strategy"):
            Signal(
                direction=SignalDirection.LONG,
                strength=Decimal("0.5"),
                source_strategy="",
                instrument=btc_spot,
            )

    def test_boundary_strengths_valid(self, btc_spot: Instrument) -> None:
        s0 = Signal(direction=SignalDirection.NEUTRAL, strength=Decimal("0"), source_strategy="s", instrument=btc_spot)
        s1 = Signal(direction=SignalDirection.EXIT, strength=Decimal("1"), source_strategy="s", instrument=btc_spot)
        assert s0.strength == Decimal("0")
        assert s1.strength == Decimal("1")

    def test_expired_signal(self, btc_spot: Instrument) -> None:
        from datetime import timedelta
        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        sig = Signal(
            direction=SignalDirection.LONG,
            strength=Decimal("0.5"),
            source_strategy="s1",
            instrument=btc_spot,
            expiry=past,
        )
        assert sig.is_expired

    def test_non_expired_signal(self, btc_spot: Instrument) -> None:
        from datetime import timedelta
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        sig = Signal(
            direction=SignalDirection.SHORT,
            strength=Decimal("0.5"),
            source_strategy="s1",
            instrument=btc_spot,
            expiry=future,
        )
        assert not sig.is_expired

    def test_signal_id_auto_generated(self, basic_signal: Signal) -> None:
        assert len(basic_signal.signal_id) == 36


# ---------------------------------------------------------------------------
# Decision tests
# ---------------------------------------------------------------------------


class TestDecision:
    def test_create_decision(self, basic_signal: Signal, btc_spot: Instrument) -> None:
        d = Decision(
            action=DecisionAction.ENTER_LONG,
            confidence=Decimal("0.8"),
            contributing_signals=(basic_signal,),
            risk_gated=False,
            instrument=btc_spot,
        )
        assert d.action == DecisionAction.ENTER_LONG
        assert d.confidence == Decimal("0.8")
        assert len(d.contributing_signals) == 1
        assert not d.risk_gated

    def test_reject_decision(self, btc_spot: Instrument) -> None:
        d = Decision(
            action=DecisionAction.REJECT,
            confidence=Decimal("0"),
            contributing_signals=(),
            risk_gated=True,
            instrument=btc_spot,
            reason="Daily loss limit reached",
        )
        assert d.risk_gated
        assert d.reason == "Daily loss limit reached"

    def test_confidence_out_of_range_raises(self, btc_spot: Instrument) -> None:
        with pytest.raises(ValueError, match="confidence"):
            Decision(
                action=DecisionAction.HOLD,
                confidence=Decimal("1.5"),
                contributing_signals=(),
                risk_gated=False,
                instrument=btc_spot,
            )


# ---------------------------------------------------------------------------
# RiskProfile tests
# ---------------------------------------------------------------------------


class TestRiskProfile:
    def test_valid_risk_profile(self) -> None:
        rp = RiskProfile(
            strategy_id="strat_001",
            max_drawdown_pct=Decimal("0.05"),
            max_position_qty=Decimal("1.0"),
            heat_limit=Decimal("10.0"),
            max_daily_loss=Decimal("500.00"),
        )
        assert rp.max_leverage == Decimal("1.0")

    def test_leverage_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="max_leverage"):
            RiskProfile(
                strategy_id="s1",
                max_drawdown_pct=Decimal("0.05"),
                max_position_qty=Decimal("1.0"),
                heat_limit=Decimal("10.0"),
                max_daily_loss=Decimal("500.00"),
                max_leverage=Decimal("2.0"),
            )

    def test_zero_drawdown_raises(self) -> None:
        with pytest.raises(ValueError, match="max_drawdown_pct"):
            RiskProfile(
                strategy_id="s1",
                max_drawdown_pct=Decimal("0"),
                max_position_qty=Decimal("1.0"),
                heat_limit=Decimal("10.0"),
                max_daily_loss=Decimal("500.00"),
            )

    def test_drawdown_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="max_drawdown_pct"):
            RiskProfile(
                strategy_id="s1",
                max_drawdown_pct=Decimal("1.5"),
                max_position_qty=Decimal("1.0"),
                heat_limit=Decimal("10.0"),
                max_daily_loss=Decimal("500.00"),
            )

    def test_zero_position_qty_raises(self) -> None:
        with pytest.raises(ValueError, match="max_position_qty"):
            RiskProfile(
                strategy_id="s1",
                max_drawdown_pct=Decimal("0.05"),
                max_position_qty=Decimal("0"),
                heat_limit=Decimal("10.0"),
                max_daily_loss=Decimal("500.00"),
            )


# ---------------------------------------------------------------------------
# AccountHeat tests
# ---------------------------------------------------------------------------


class TestAccountHeat:
    def test_initial_state(self) -> None:
        ah = AccountHeat(max_heat=Decimal("100"))
        assert ah.current_heat == Decimal("0")
        assert ah.available_heat == Decimal("100")
        assert not ah.is_at_limit

    def test_add_heat(self) -> None:
        ah = AccountHeat(max_heat=Decimal("100"))
        ah.add_heat("strat_a", Decimal("30"))
        assert ah.current_heat == Decimal("30")
        assert ah.available_heat == Decimal("70")
        assert not ah.is_at_limit

    def test_heat_at_limit(self) -> None:
        ah = AccountHeat(max_heat=Decimal("100"))
        ah.add_heat("strat_a", Decimal("100"))
        assert ah.is_at_limit

    def test_exceeding_heat_raises(self) -> None:
        ah = AccountHeat(max_heat=Decimal("100"))
        ah.add_heat("strat_a", Decimal("80"))
        with pytest.raises(ValueError, match="breach max_heat"):
            ah.add_heat("strat_b", Decimal("30"))

    def test_release_heat(self) -> None:
        ah = AccountHeat(max_heat=Decimal("100"))
        ah.add_heat("strat_a", Decimal("50"))
        ah.release_heat("strat_a", Decimal("20"))
        assert ah.current_heat == Decimal("30")
        assert ah.per_strategy_heat["strat_a"] == Decimal("30")

    def test_release_more_than_held(self) -> None:
        ah = AccountHeat(max_heat=Decimal("100"))
        ah.add_heat("strat_a", Decimal("30"))
        ah.release_heat("strat_a", Decimal("100"))
        assert ah.current_heat == Decimal("0")

    def test_zero_max_heat_raises(self) -> None:
        with pytest.raises(ValueError, match="max_heat"):
            AccountHeat(max_heat=Decimal("0"))


# ---------------------------------------------------------------------------
# CapitalState tests
# ---------------------------------------------------------------------------


class TestCapitalState:
    def test_initial_state(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        assert cs.available == Decimal("50000")
        assert cs.allocated == Decimal("0")
        assert cs.locked == Decimal("0")

    def test_allocate(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        cs.allocate(Decimal("10000"))
        assert cs.allocated == Decimal("10000")
        assert cs.available == Decimal("40000")

    def test_lock(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        cs.lock(Decimal("5000"))
        assert cs.locked == Decimal("5000")
        assert cs.available == Decimal("45000")

    def test_unlock(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        cs.lock(Decimal("5000"))
        cs.unlock(Decimal("5000"))
        assert cs.locked == Decimal("0")

    def test_release_with_pnl(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        cs.allocate(Decimal("10000"))
        cs.release(Decimal("10000"), pnl=Decimal("500"))
        assert cs.total_capital == Decimal("50500")
        assert cs.allocated == Decimal("0")

    def test_release_with_loss(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        cs.allocate(Decimal("10000"))
        cs.release(Decimal("10000"), pnl=Decimal("-200"))
        assert cs.total_capital == Decimal("49800")

    def test_allocate_exceeds_available_raises(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        with pytest.raises(ValueError, match="Cannot allocate"):
            cs.allocate(Decimal("60000"))

    def test_lock_exceeds_available_raises(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        with pytest.raises(ValueError, match="Cannot lock"):
            cs.lock(Decimal("60000"))

    def test_negative_total_raises(self) -> None:
        with pytest.raises(ValueError):
            CapitalState(total_capital=Decimal("-1"))

    def test_allocated_plus_locked_exceeds_total_raises(self) -> None:
        with pytest.raises(ValueError):
            CapitalState(
                total_capital=Decimal("100"),
                allocated=Decimal("70"),
                locked=Decimal("40"),
            )


# ---------------------------------------------------------------------------
# TradeState / TradeStateMachine tests
# ---------------------------------------------------------------------------


class TestTradeState:
    def test_initial_state(self) -> None:
        state = TradeState()
        assert state.current == OrderStatus.PENDING
        assert not state.is_terminal

    def test_valid_transition_pending_to_open(self) -> None:
        state = TradeState()
        result = state.transition(OrderStatus.OPEN)
        assert result == OrderStatus.OPEN
        assert state.current == OrderStatus.OPEN

    def test_valid_transition_open_to_partial(self) -> None:
        state = TradeState()
        state.transition(OrderStatus.OPEN)
        state.transition(OrderStatus.PARTIAL)
        assert state.current == OrderStatus.PARTIAL

    def test_valid_transition_partial_self_loop(self) -> None:
        state = TradeState()
        state.transition(OrderStatus.OPEN)
        state.transition(OrderStatus.PARTIAL)
        state.transition(OrderStatus.PARTIAL)
        assert state.current == OrderStatus.PARTIAL

    def test_valid_full_lifecycle(self) -> None:
        state = TradeState()
        state.transition(OrderStatus.OPEN)
        state.transition(OrderStatus.CLOSED)
        assert state.is_terminal

    def test_invalid_transition_raises(self) -> None:
        state = TradeState()  # PENDING
        with pytest.raises(InvalidStateTransition):
            state.transition(OrderStatus.CLOSED)

    def test_terminal_state_blocks_all_transitions(self) -> None:
        state = TradeState()
        state.transition(OrderStatus.OPEN)
        state.transition(OrderStatus.CLOSED)
        for target in OrderStatus:
            if target != OrderStatus.CLOSED:
                with pytest.raises(InvalidStateTransition):
                    state.transition(target)

    def test_can_transition_to(self) -> None:
        state = TradeState()
        assert state.can_transition_to(OrderStatus.OPEN)
        assert not state.can_transition_to(OrderStatus.CLOSED)

    def test_equality_with_order_status(self) -> None:
        state = TradeState()
        assert state == OrderStatus.PENDING

    def test_state_machine_facade(self) -> None:
        state = TradeState()
        sm = TradeStateMachine()
        result = sm.transition(state, OrderStatus.OPEN)
        assert result == OrderStatus.OPEN
        allowed = sm.allowed_transitions(state)
        assert OrderStatus.PARTIAL in allowed
        assert sm.is_terminal(TradeState(OrderStatus.CLOSED))

    def test_invalid_state_transition_attributes(self) -> None:
        exc = InvalidStateTransition(OrderStatus.CLOSED, OrderStatus.OPEN)
        assert exc.from_state == OrderStatus.CLOSED
        assert exc.to_state == OrderStatus.OPEN


# ---------------------------------------------------------------------------
# Domain Events tests
# ---------------------------------------------------------------------------


class TestDomainEvents:
    def test_trade_opened(self, basic_order: Order, btc_spot: Instrument) -> None:
        evt = TradeOpened(order=basic_order, instrument=btc_spot)
        assert evt.order is basic_order
        assert evt.event_type == "TradeOpened"
        assert isinstance(evt.occurred_at, datetime)

    def test_trade_opened_requires_order(self, btc_spot: Instrument) -> None:
        with pytest.raises(ValueError, match="order"):
            TradeOpened(order=None, instrument=btc_spot)  # type: ignore[arg-type]

    def test_trade_filled(self, basic_order: Order) -> None:
        evt = TradeFilled(
            order=basic_order,
            fill_price=Decimal("45000"),
            fill_quantity=Decimal("0.1"),
            commission=Decimal("4.5"),
        )
        assert evt.fill_price == Decimal("45000")
        assert evt.commission == Decimal("4.5")

    def test_trade_filled_zero_price_raises(self, basic_order: Order) -> None:
        with pytest.raises(ValueError, match="fill_price"):
            TradeFilled(
                order=basic_order,
                fill_price=Decimal("0"),
                fill_quantity=Decimal("0.1"),
            )

    def test_trade_partial_fill(self, basic_order: Order) -> None:
        evt = TradePartialFill(
            order=basic_order,
            partial_price=Decimal("45000"),
            partial_quantity=Decimal("0.05"),
            remaining_quantity=Decimal("0.05"),
        )
        assert evt.remaining_quantity == Decimal("0.05")

    def test_trade_partial_fill_negative_remaining_raises(self, basic_order: Order) -> None:
        with pytest.raises(ValueError, match="remaining_quantity"):
            TradePartialFill(
                order=basic_order,
                partial_price=Decimal("45000"),
                partial_quantity=Decimal("0.05"),
                remaining_quantity=Decimal("-1"),
            )

    def test_trade_closed(self, btc_spot: Instrument) -> None:
        pos = Position(instrument=btc_spot, direction=PositionDirection.LONG)
        evt = TradeClosed(position=pos, realized_pnl=Decimal("1000"))
        assert evt.realized_pnl == Decimal("1000")

    def test_trade_cancelled(self, basic_order: Order) -> None:
        evt = TradeCancelled(order=basic_order, reason="risk limit hit")
        assert evt.reason == "risk limit hit"

    def test_trade_error(self) -> None:
        evt = TradeError(order_id="coid-1", error_code="INSUFFICIENT_FUNDS", message="Low balance")
        assert evt.error_code == "INSUFFICIENT_FUNDS"

    def test_trade_error_empty_order_id_raises(self) -> None:
        with pytest.raises(ValueError, match="order_id"):
            TradeError(order_id="", message="error")

    def test_position_updated(self, btc_spot: Instrument) -> None:
        pos = Position(instrument=btc_spot, direction=PositionDirection.SHORT)
        evt = PositionUpdated(position=pos, change_type="entry")
        assert evt.change_type == "entry"

    def test_position_updated_invalid_change_type_raises(self, btc_spot: Instrument) -> None:
        pos = Position(instrument=btc_spot, direction=PositionDirection.SHORT)
        with pytest.raises(ValueError, match="change_type"):
            PositionUpdated(position=pos, change_type="invalid")  # type: ignore[arg-type]

    def test_signal_received(self, basic_signal: Signal) -> None:
        evt = SignalReceived(signal=basic_signal)
        assert evt.signal.direction == SignalDirection.LONG

    def test_decision_made(self, btc_spot: Instrument, basic_signal: Signal) -> None:
        d = Decision(
            action=DecisionAction.HOLD,
            confidence=Decimal("0.5"),
            contributing_signals=(basic_signal,),
            risk_gated=False,
            instrument=btc_spot,
        )
        evt = DecisionMade(decision=d)
        assert evt.decision.action == DecisionAction.HOLD

    def test_risk_limit_breached(self) -> None:
        evt = RiskLimitBreached(
            limit_type="max_position_size",
            current_value=Decimal("1.5"),
            limit_value=Decimal("1.0"),
            strategy_id="strat_001",
            message="Position size exceeded",
        )
        assert evt.limit_type == "max_position_size"

    def test_risk_limit_breached_empty_limit_type_raises(self) -> None:
        with pytest.raises(ValueError, match="limit_type"):
            RiskLimitBreached(
                limit_type="",
                current_value=Decimal("1.5"),
                limit_value=Decimal("1.0"),
            )

    def test_capital_state_changed(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        evt = CapitalStateChanged(
            capital_state=cs,
            change_type="allocate",
            amount=Decimal("10000"),
        )
        assert evt.change_type == "allocate"
        assert evt.amount == Decimal("10000")

    def test_capital_state_changed_invalid_type_raises(self) -> None:
        cs = CapitalState(total_capital=Decimal("50000"))
        with pytest.raises(ValueError, match="change_type"):
            CapitalStateChanged(
                capital_state=cs,
                change_type="bad_type",
                amount=Decimal("100"),
            )

    def test_domain_event_unique_ids(self, btc_spot: Instrument) -> None:
        pos = Position(instrument=btc_spot, direction=PositionDirection.LONG)
        e1 = TradeClosed(position=pos, realized_pnl=Decimal("0"))
        e2 = TradeClosed(position=pos, realized_pnl=Decimal("0"))
        assert e1.event_id != e2.event_id
