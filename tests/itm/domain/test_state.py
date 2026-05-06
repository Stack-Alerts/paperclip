"""
Unit tests for itm.domain.state — TradeStateMachine
"""

import pytest

from src.itm.domain.state import (
    TradeState,
    TradeStateMachine,
    InvalidStateTransition,
)
from src.itm.domain.entities import OrderStatus


class TestTradeState:
    def test_initial_state_is_pending(self):
        state = TradeState()
        assert state.current == OrderStatus.PENDING
        assert not state.is_terminal

    def test_pending_to_open(self):
        state = TradeState()
        result = state.transition(OrderStatus.OPEN)
        assert result == OrderStatus.OPEN
        assert state.current == OrderStatus.OPEN

    def test_pending_to_cancelled(self):
        state = TradeState()
        state.transition(OrderStatus.CANCELLED)
        assert state.is_terminal

    def test_pending_to_error(self):
        state = TradeState()
        state.transition(OrderStatus.ERROR)
        assert state.is_terminal

    def test_open_to_partial(self):
        state = TradeState(OrderStatus.OPEN)
        state.transition(OrderStatus.PARTIAL)
        assert state.current == OrderStatus.PARTIAL

    def test_open_to_closed(self):
        state = TradeState(OrderStatus.OPEN)
        state.transition(OrderStatus.CLOSED)
        assert state.is_terminal

    def test_open_to_cancelled(self):
        state = TradeState(OrderStatus.OPEN)
        state.transition(OrderStatus.CANCELLED)
        assert state.is_terminal

    def test_partial_to_partial(self):
        """Multiple partial fills: self-loop allowed."""
        state = TradeState(OrderStatus.PARTIAL)
        state.transition(OrderStatus.PARTIAL)
        assert state.current == OrderStatus.PARTIAL

    def test_partial_to_closed(self):
        state = TradeState(OrderStatus.PARTIAL)
        state.transition(OrderStatus.CLOSED)
        assert state.is_terminal

    def test_partial_to_cancelled(self):
        state = TradeState(OrderStatus.PARTIAL)
        state.transition(OrderStatus.CANCELLED)
        assert state.is_terminal

    def test_partial_to_error(self):
        state = TradeState(OrderStatus.PARTIAL)
        state.transition(OrderStatus.ERROR)
        assert state.is_terminal

    # -- Illegal transitions --

    def test_pending_to_closed_raises(self):
        state = TradeState()
        with pytest.raises(InvalidStateTransition) as exc_info:
            state.transition(OrderStatus.CLOSED)
        assert exc_info.value.from_state == OrderStatus.PENDING
        assert exc_info.value.to_state == OrderStatus.CLOSED

    def test_pending_to_partial_raises(self):
        state = TradeState()
        with pytest.raises(InvalidStateTransition):
            state.transition(OrderStatus.PARTIAL)

    def test_closed_to_open_raises(self):
        state = TradeState(OrderStatus.CLOSED)
        with pytest.raises(InvalidStateTransition):
            state.transition(OrderStatus.OPEN)

    def test_closed_to_cancelled_raises(self):
        state = TradeState(OrderStatus.CLOSED)
        with pytest.raises(InvalidStateTransition):
            state.transition(OrderStatus.CANCELLED)

    def test_cancelled_to_pending_raises(self):
        state = TradeState(OrderStatus.CANCELLED)
        with pytest.raises(InvalidStateTransition):
            state.transition(OrderStatus.PENDING)

    def test_error_to_open_raises(self):
        state = TradeState(OrderStatus.ERROR)
        with pytest.raises(InvalidStateTransition):
            state.transition(OrderStatus.OPEN)

    def test_can_transition_to_true(self):
        state = TradeState(OrderStatus.PENDING)
        assert state.can_transition_to(OrderStatus.OPEN)

    def test_can_transition_to_false(self):
        state = TradeState(OrderStatus.CLOSED)
        assert not state.can_transition_to(OrderStatus.OPEN)

    def test_equality_with_status(self):
        state = TradeState(OrderStatus.OPEN)
        assert state == OrderStatus.OPEN

    def test_equality_with_trade_state(self):
        a = TradeState(OrderStatus.PARTIAL)
        b = TradeState(OrderStatus.PARTIAL)
        assert a == b


class TestTradeStateMachine:
    def test_facade_transition(self):
        state = TradeState()
        new_status = TradeStateMachine.transition(state, OrderStatus.OPEN)
        assert new_status == OrderStatus.OPEN

    def test_facade_raises_on_invalid(self):
        state = TradeState(OrderStatus.CLOSED)
        with pytest.raises(InvalidStateTransition):
            TradeStateMachine.transition(state, OrderStatus.OPEN)

    def test_allowed_transitions_from_pending(self):
        state = TradeState(OrderStatus.PENDING)
        allowed = TradeStateMachine.allowed_transitions(state)
        assert OrderStatus.OPEN in allowed
        assert OrderStatus.CANCELLED in allowed
        assert OrderStatus.ERROR in allowed
        assert OrderStatus.CLOSED not in allowed
        assert OrderStatus.PARTIAL not in allowed

    def test_allowed_transitions_from_closed_is_empty(self):
        state = TradeState(OrderStatus.CLOSED)
        allowed = TradeStateMachine.allowed_transitions(state)
        assert allowed == frozenset()

    def test_is_terminal(self):
        assert TradeStateMachine.is_terminal(TradeState(OrderStatus.CLOSED))
        assert TradeStateMachine.is_terminal(TradeState(OrderStatus.CANCELLED))
        assert TradeStateMachine.is_terminal(TradeState(OrderStatus.ERROR))
        assert not TradeStateMachine.is_terminal(TradeState(OrderStatus.OPEN))

    def test_full_happy_path(self):
        """Simulate: pending → open → partial → partial → closed"""
        state = TradeState()
        TradeStateMachine.transition(state, OrderStatus.OPEN)
        TradeStateMachine.transition(state, OrderStatus.PARTIAL)
        TradeStateMachine.transition(state, OrderStatus.PARTIAL)
        TradeStateMachine.transition(state, OrderStatus.CLOSED)
        assert state.is_terminal

    def test_cancellation_path(self):
        """Simulate: pending → open → cancelled"""
        state = TradeState()
        TradeStateMachine.transition(state, OrderStatus.OPEN)
        TradeStateMachine.transition(state, OrderStatus.CANCELLED)
        assert state.is_terminal

    def test_error_path(self):
        """Any state can go to error."""
        for initial in (OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIAL):
            state = TradeState(initial)
            TradeStateMachine.transition(state, OrderStatus.ERROR)
            assert state.is_terminal


class TestInvalidStateTransition:
    def test_exception_message(self):
        exc = InvalidStateTransition(OrderStatus.PENDING, OrderStatus.CLOSED)
        assert "pending" in str(exc)
        assert "closed" in str(exc)
        assert exc.from_state == OrderStatus.PENDING
        assert exc.to_state == OrderStatus.CLOSED
