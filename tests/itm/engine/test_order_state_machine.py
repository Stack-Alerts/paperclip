"""
Unit tests: OrderStateMachine (Section G)
==========================================
Tests the full order lifecycle state machine: all valid transitions,
illegal transition rejection, fill aggregation, timeout detection,
and partial fill tracking.
"""

from __future__ import annotations

import time
import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from src.itm.engine.order_factory import (
    BinanceOrderType,
    OrderFactory,
    OrderSpec,
)
from src.itm.engine.order_state_machine import (
    FillRecord,
    IllegalStateTransition,
    OrderState,
    OrderStateMachine,
)
from src.itm.domain.entities import OrderSide


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def factory():
    return OrderFactory(lot_size=Decimal("0.001"), tick_size=Decimal("0.10"))


@pytest.fixture
def limit_spec(factory):
    return factory.limit(
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
        price=Decimal("45000"),
        strategy_id="test-strategy",
        signal_id="sig-001",
    )


@pytest.fixture
def sm(limit_spec):
    return OrderStateMachine(spec=limit_spec, ttl_secs=60.0)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_initial_state_is_submitted(self, sm):
        assert sm.state == OrderState.SUBMITTED

    def test_initial_filled_quantity_zero(self, sm):
        assert sm.filled_quantity == Decimal("0")

    def test_initial_remaining_quantity_equals_spec(self, sm, limit_spec):
        assert sm.remaining_quantity == limit_spec.quantity

    def test_initial_average_fill_price_none(self, sm):
        assert sm.average_fill_price is None

    def test_initial_fill_ratio_zero(self, sm):
        assert sm.fill_ratio == Decimal("0")


# ---------------------------------------------------------------------------
# SUBMITTED → ACKNOWLEDGED
# ---------------------------------------------------------------------------


class TestAcknowledge:
    def test_acknowledge_transitions_to_acknowledged(self, sm):
        sm.acknowledge("EX-123")
        assert sm.state == OrderState.ACKNOWLEDGED

    def test_acknowledge_sets_exchange_id(self, sm):
        sm.acknowledge("EX-456")
        assert sm.exchange_order_id == "EX-456"

    def test_acknowledge_twice_raises(self, sm):
        sm.acknowledge("EX-123")
        with pytest.raises(IllegalStateTransition):
            sm.acknowledge("EX-124")


# ---------------------------------------------------------------------------
# ACKNOWLEDGED → PARTIALLY_FILLED
# ---------------------------------------------------------------------------


class TestPartialFill:
    def test_partial_fill_transitions_state(self, sm):
        sm.acknowledge("EX-1")
        sm.partial_fill(Decimal("45001"), Decimal("0.05"))
        assert sm.state == OrderState.PARTIALLY_FILLED

    def test_partial_fill_accumulates(self, sm):
        sm.acknowledge("EX-1")
        sm.partial_fill(Decimal("45000"), Decimal("0.03"))
        sm.partial_fill(Decimal("45001"), Decimal("0.04"))
        assert sm.filled_quantity == Decimal("0.07")

    def test_partial_fill_updates_remaining(self, sm):
        sm.acknowledge("EX-1")
        sm.partial_fill(Decimal("45000"), Decimal("0.06"))
        assert sm.remaining_quantity == Decimal("0.04")

    def test_partial_fill_average_price(self, sm):
        sm.acknowledge("EX-1")
        sm.partial_fill(Decimal("44000"), Decimal("0.05"))
        sm.partial_fill(Decimal("46000"), Decimal("0.05"))
        avg = sm.average_fill_price
        assert avg is not None
        # (44000*0.05 + 46000*0.05) / 0.10 = 45000
        assert avg == Decimal("45000")

    def test_partial_fill_zero_qty_raises(self, sm):
        sm.acknowledge("EX-1")
        with pytest.raises(ValueError):
            sm.partial_fill(Decimal("45000"), Decimal("0"))

    def test_partial_fill_zero_price_raises(self, sm):
        sm.acknowledge("EX-1")
        with pytest.raises(ValueError):
            sm.partial_fill(Decimal("0"), Decimal("0.05"))

    def test_partial_fill_from_submitted_raises(self, sm):
        """Partial fill without ACK is not allowed."""
        with pytest.raises(IllegalStateTransition):
            sm.partial_fill(Decimal("45000"), Decimal("0.05"))


# ---------------------------------------------------------------------------
# → FILLED
# ---------------------------------------------------------------------------


class TestFill:
    def test_fill_from_acknowledged(self, sm):
        sm.acknowledge("EX-1")
        sm.fill(Decimal("45000"), Decimal("0.1"))
        assert sm.state == OrderState.FILLED

    def test_fill_from_partial(self, sm):
        sm.acknowledge("EX-1")
        sm.partial_fill(Decimal("45000"), Decimal("0.05"))
        sm.fill(Decimal("45002"), Decimal("0.05"))
        assert sm.state == OrderState.FILLED

    def test_fill_is_terminal(self, sm):
        sm.acknowledge("EX-1")
        sm.fill(Decimal("45000"), Decimal("0.1"))
        assert sm.state.is_terminal

    def test_fill_updates_filled_quantity(self, sm):
        sm.acknowledge("EX-1")
        sm.fill(Decimal("45000"), Decimal("0.1"))
        assert sm.filled_quantity == Decimal("0.1")

    def test_fill_ratio_one_when_fully_filled(self, sm):
        sm.acknowledge("EX-1")
        sm.fill(Decimal("45000"), Decimal("0.1"))
        assert sm.fill_ratio == Decimal("1")

    def test_fill_then_cancel_raises(self, sm):
        sm.acknowledge("EX-1")
        sm.fill(Decimal("45000"), Decimal("0.1"))
        with pytest.raises(IllegalStateTransition):
            sm.cancel("late cancel attempt")

    def test_fill_records_commission(self, sm):
        sm.acknowledge("EX-1")
        sm.fill(Decimal("45000"), Decimal("0.1"), commission=Decimal("0.045"))
        assert sm.total_commission == Decimal("0.045")


# ---------------------------------------------------------------------------
# → CANCELLED
# ---------------------------------------------------------------------------


class TestCancel:
    def test_cancel_from_submitted(self, sm):
        sm.cancel("pre-ack cancel")
        assert sm.state == OrderState.CANCELLED
        assert sm.cancelled_reason == "pre-ack cancel"

    def test_cancel_from_acknowledged(self, sm):
        sm.acknowledge("EX-1")
        sm.cancel("timeout")
        assert sm.state == OrderState.CANCELLED

    def test_cancel_from_partial(self, sm):
        sm.acknowledge("EX-1")
        sm.partial_fill(Decimal("45000"), Decimal("0.03"))
        sm.cancel("partial_fill_below_threshold")
        assert sm.state == OrderState.CANCELLED

    def test_cancel_is_terminal(self, sm):
        sm.cancel("test")
        assert sm.state.is_terminal

    def test_cancel_again_raises(self, sm):
        sm.cancel("first cancel")
        with pytest.raises(IllegalStateTransition):
            sm.cancel("second cancel")


# ---------------------------------------------------------------------------
# → REJECTED
# ---------------------------------------------------------------------------


class TestReject:
    def test_reject_from_submitted(self, sm):
        sm.reject("insufficient_margin")
        assert sm.state == OrderState.REJECTED
        assert sm.rejected_reason == "insufficient_margin"

    def test_reject_from_acknowledged(self, sm):
        sm.acknowledge("EX-1")
        sm.reject("exchange_rejected_post_ack")
        assert sm.state == OrderState.REJECTED

    def test_reject_is_terminal(self, sm):
        sm.reject("test")
        assert sm.state.is_terminal


# ---------------------------------------------------------------------------
# Timeout detection
# ---------------------------------------------------------------------------


class TestTimeoutDetection:
    def test_not_timed_out_within_ttl(self, limit_spec):
        sm = OrderStateMachine(spec=limit_spec, ttl_secs=3600.0)
        sm.acknowledge("EX-1")
        assert sm.is_timed_out() is False

    def test_timed_out_after_ttl(self, limit_spec):
        sm = OrderStateMachine(spec=limit_spec, ttl_secs=0.001)
        sm.acknowledge("EX-1")
        time.sleep(0.05)  # wait more than 1ms TTL
        assert sm.is_timed_out() is True

    def test_no_timeout_when_terminal(self, limit_spec):
        sm = OrderStateMachine(spec=limit_spec, ttl_secs=0.001)
        sm.acknowledge("EX-1")
        sm.fill(Decimal("45000"), Decimal("0.1"))
        time.sleep(0.05)
        assert sm.is_timed_out() is False  # terminal = not active

    def test_no_timeout_when_ttl_none(self, limit_spec):
        sm = OrderStateMachine(spec=limit_spec, ttl_secs=None)
        sm.acknowledge("EX-1")
        assert sm.is_timed_out() is False


# ---------------------------------------------------------------------------
# State change callback
# ---------------------------------------------------------------------------


class TestStateChangeCallback:
    def test_callback_called_on_transition(self, limit_spec):
        callback = MagicMock()
        sm = OrderStateMachine(
            spec=limit_spec,
            ttl_secs=60.0,
            on_state_change=callback,
        )
        sm.acknowledge("EX-1")
        assert callback.called
        call_args = callback.call_args
        assert call_args[0][1] == OrderState.SUBMITTED  # old_state
        assert call_args[0][2] == OrderState.ACKNOWLEDGED  # new_state

    def test_callback_exception_does_not_propagate(self, limit_spec):
        def bad_callback(sm, old, new):
            raise RuntimeError("callback error")

        sm = OrderStateMachine(
            spec=limit_spec,
            ttl_secs=60.0,
            on_state_change=bad_callback,
        )
        # Should not raise
        sm.acknowledge("EX-1")
        assert sm.state == OrderState.ACKNOWLEDGED


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------


class TestRepr:
    def test_repr_contains_state(self, sm):
        r = repr(sm)
        assert "submitted" in r

    def test_repr_after_fill(self, sm):
        sm.acknowledge("EX-1")
        sm.fill(Decimal("45000"), Decimal("0.1"))
        r = repr(sm)
        assert "filled" in r
