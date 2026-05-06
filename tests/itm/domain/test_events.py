"""
Unit tests for itm.domain.events
"""

import pytest
from decimal import Decimal

from src.itm.domain.entities import (
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionEntry,
    PositionExit,
    PositionDirection,
    SignalDirection,
    DecisionAction,
    Signal,
    Decision,
    CapitalState,
)
from src.itm.domain.events import (
    DomainEvent,
    TradeOpened,
    TradeFilled,
    TradePartialFill,
    TradeClosed,
    TradeCancelled,
    TradeError,
    PositionUpdated,
    SignalReceived,
    DecisionMade,
    RiskLimitBreached,
    CapitalStateChanged,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def instrument():
    return Instrument.btc_usdt_spot()


@pytest.fixture
def order(instrument):
    return Order(
        instrument=instrument,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.5"),
        price=None,
    )


@pytest.fixture
def position(instrument):
    pos = Position(instrument=instrument, direction=PositionDirection.LONG)
    pos.add_entry(PositionEntry("ord-1", Decimal("0.5"), Decimal("40000")))
    return pos


@pytest.fixture
def signal(instrument):
    return Signal(
        direction=SignalDirection.LONG,
        strength=Decimal("0.8"),
        source_strategy="MA_Cross",
        instrument=instrument,
    )


@pytest.fixture
def decision(instrument, signal):
    return Decision(
        action=DecisionAction.ENTER_LONG,
        confidence=Decimal("0.8"),
        contributing_signals=(signal,),
        risk_gated=False,
        instrument=instrument,
    )


@pytest.fixture
def capital_state():
    return CapitalState(total_capital=Decimal("100000"))


# ---------------------------------------------------------------------------
# DomainEvent base
# ---------------------------------------------------------------------------


class TestDomainEvent:
    def test_event_id_auto_generated(self):
        # Subclass to test base
        class _TestEvent(DomainEvent):
            pass

        e1 = _TestEvent()
        e2 = _TestEvent()
        assert e1.event_id != e2.event_id

    def test_occurred_at_is_utc(self):
        from datetime import timezone

        class _TestEvent(DomainEvent):
            pass

        e = _TestEvent()
        assert e.occurred_at.tzinfo == timezone.utc

    def test_event_type_property(self):
        e = TradeError(order_id="ord-1", message="error")
        assert e.event_type == "TradeError"


# ---------------------------------------------------------------------------
# TradeOpened
# ---------------------------------------------------------------------------


class TestTradeOpened:
    def test_valid(self, order, instrument):
        evt = TradeOpened(
            order=order,
            instrument=instrument,
            stop_loss_price=Decimal("39200"),
        )
        assert evt.order is order
        assert evt.instrument is instrument
        assert evt.stop_loss_price == Decimal("39200")
        assert evt.position_id  # auto-generated

    def test_missing_order_raises(self, instrument):
        with pytest.raises(ValueError, match="order"):
            TradeOpened(instrument=instrument)

    def test_missing_instrument_raises(self, order):
        with pytest.raises(ValueError, match="instrument"):
            TradeOpened(order=order)

    def test_immutable(self, order, instrument):
        evt = TradeOpened(order=order, instrument=instrument)
        with pytest.raises((AttributeError, TypeError)):
            evt.position_id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TradeFilled
# ---------------------------------------------------------------------------


class TestTradeFilled:
    def test_valid(self, order):
        evt = TradeFilled(
            order=order,
            fill_price=Decimal("41000"),
            fill_quantity=Decimal("0.5"),
            commission=Decimal("2.05"),
        )
        assert evt.fill_price == Decimal("41000")
        assert evt.fill_quantity == Decimal("0.5")

    def test_missing_order_raises(self):
        with pytest.raises(ValueError, match="order"):
            TradeFilled(fill_price=Decimal("40000"), fill_quantity=Decimal("0.1"))

    def test_zero_fill_price_raises(self, order):
        with pytest.raises(ValueError, match="fill_price"):
            TradeFilled(order=order, fill_price=Decimal("0"), fill_quantity=Decimal("0.1"))

    def test_zero_fill_quantity_raises(self, order):
        with pytest.raises(ValueError, match="fill_quantity"):
            TradeFilled(order=order, fill_price=Decimal("40000"), fill_quantity=Decimal("0"))


# ---------------------------------------------------------------------------
# TradePartialFill
# ---------------------------------------------------------------------------


class TestTradePartialFill:
    def test_valid(self, order):
        evt = TradePartialFill(
            order=order,
            partial_price=Decimal("40500"),
            partial_quantity=Decimal("0.2"),
            remaining_quantity=Decimal("0.3"),
        )
        assert evt.remaining_quantity == Decimal("0.3")

    def test_zero_partial_price_raises(self, order):
        with pytest.raises(ValueError, match="partial_price"):
            TradePartialFill(
                order=order,
                partial_price=Decimal("0"),
                partial_quantity=Decimal("0.1"),
                remaining_quantity=Decimal("0.4"),
            )

    def test_negative_remaining_raises(self, order):
        with pytest.raises(ValueError, match="remaining_quantity"):
            TradePartialFill(
                order=order,
                partial_price=Decimal("40000"),
                partial_quantity=Decimal("0.1"),
                remaining_quantity=Decimal("-0.1"),
            )


# ---------------------------------------------------------------------------
# TradeClosed
# ---------------------------------------------------------------------------


class TestTradeClosed:
    def test_valid(self, position):
        evt = TradeClosed(position=position, realized_pnl=Decimal("500"))
        assert evt.realized_pnl == Decimal("500")

    def test_missing_position_raises(self):
        with pytest.raises(ValueError, match="position"):
            TradeClosed(realized_pnl=Decimal("0"))


# ---------------------------------------------------------------------------
# TradeCancelled
# ---------------------------------------------------------------------------


class TestTradeCancelled:
    def test_valid(self, order):
        evt = TradeCancelled(order=order, reason="User cancelled")
        assert evt.reason == "User cancelled"

    def test_missing_order_raises(self):
        with pytest.raises(ValueError, match="order"):
            TradeCancelled()


# ---------------------------------------------------------------------------
# TradeError
# ---------------------------------------------------------------------------


class TestTradeError:
    def test_valid(self):
        evt = TradeError(order_id="ord-1", error_code="INSUFFICIENT_BALANCE", message="Not enough funds")
        assert evt.error_code == "INSUFFICIENT_BALANCE"

    def test_missing_order_id_raises(self):
        with pytest.raises(ValueError, match="order_id"):
            TradeError(order_id="", message="error")


# ---------------------------------------------------------------------------
# PositionUpdated
# ---------------------------------------------------------------------------


class TestPositionUpdated:
    def test_valid_entry(self, position):
        evt = PositionUpdated(position=position, change_type="entry")
        assert evt.change_type == "entry"

    def test_valid_exit(self, position):
        evt = PositionUpdated(position=position, change_type="exit")
        assert evt.change_type == "exit"

    def test_invalid_change_type_raises(self, position):
        with pytest.raises(ValueError, match="change_type"):
            PositionUpdated(position=position, change_type="amend")

    def test_missing_position_raises(self):
        with pytest.raises(ValueError, match="position"):
            PositionUpdated(change_type="entry")


# ---------------------------------------------------------------------------
# SignalReceived
# ---------------------------------------------------------------------------


class TestSignalReceived:
    def test_valid(self, signal):
        evt = SignalReceived(signal=signal)
        assert evt.signal is signal

    def test_missing_signal_raises(self):
        with pytest.raises(ValueError, match="signal"):
            SignalReceived()


# ---------------------------------------------------------------------------
# DecisionMade
# ---------------------------------------------------------------------------


class TestDecisionMade:
    def test_valid(self, decision):
        evt = DecisionMade(decision=decision)
        assert evt.decision is decision

    def test_missing_decision_raises(self):
        with pytest.raises(ValueError, match="decision"):
            DecisionMade()


# ---------------------------------------------------------------------------
# RiskLimitBreached
# ---------------------------------------------------------------------------


class TestRiskLimitBreached:
    def test_valid(self):
        evt = RiskLimitBreached(
            limit_type="max_position_size",
            current_value=Decimal("1.5"),
            limit_value=Decimal("1.0"),
            strategy_id="strat-1",
            message="Position size exceeded",
        )
        assert evt.limit_type == "max_position_size"
        assert evt.current_value == Decimal("1.5")

    def test_empty_limit_type_raises(self):
        with pytest.raises(ValueError, match="limit_type"):
            RiskLimitBreached(limit_type="", current_value=Decimal("1"), limit_value=Decimal("1"))


# ---------------------------------------------------------------------------
# CapitalStateChanged
# ---------------------------------------------------------------------------


class TestCapitalStateChanged:
    def test_valid_allocate(self, capital_state):
        evt = CapitalStateChanged(
            capital_state=capital_state,
            change_type="allocate",
            amount=Decimal("10000"),
        )
        assert evt.change_type == "allocate"

    def test_valid_release(self, capital_state):
        evt = CapitalStateChanged(
            capital_state=capital_state,
            change_type="release",
            amount=Decimal("5000"),
        )
        assert evt.change_type == "release"

    def test_invalid_change_type_raises(self, capital_state):
        with pytest.raises(ValueError, match="change_type"):
            CapitalStateChanged(
                capital_state=capital_state,
                change_type="reduce",
                amount=Decimal("1000"),
            )

    def test_missing_capital_state_raises(self):
        with pytest.raises(ValueError, match="capital_state"):
            CapitalStateChanged(change_type="allocate", amount=Decimal("1000"))
