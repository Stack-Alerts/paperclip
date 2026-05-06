"""
ITM Trade State Machine
=======================
Defines the lifecycle states for a trade/order and validates all transitions.

Allowed transitions
-------------------
    pending   → open
    pending   → cancelled   (order rejected before reaching exchange)
    pending   → error

    open      → partial
    open      → closed      (fully filled immediately)
    open      → cancelled
    open      → error

    partial   → partial     (additional partial fill)
    partial   → closed      (final fill)
    partial   → cancelled   (cancelled while partially filled)
    partial   → error

    # Terminal states — no transitions out
    closed    → (none)
    cancelled → (none)
    error     → (none)

Any transition not listed above raises ``InvalidStateTransition``.
"""

from __future__ import annotations

from .entities import OrderStatus


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class InvalidStateTransition(Exception):
    """Raised when an illegal state transition is attempted.

    Attributes
    ----------
    from_state: current state
    to_state:   requested next state
    """

    def __init__(self, from_state: OrderStatus, to_state: OrderStatus) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid trade state transition: {from_state.value} → {to_state.value}"
        )


# ---------------------------------------------------------------------------
# Allowed transitions graph
# ---------------------------------------------------------------------------

_ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset(
        {OrderStatus.OPEN, OrderStatus.CANCELLED, OrderStatus.ERROR}
    ),
    OrderStatus.OPEN: frozenset(
        {
            OrderStatus.PARTIAL,
            OrderStatus.CLOSED,
            OrderStatus.CANCELLED,
            OrderStatus.ERROR,
        }
    ),
    OrderStatus.PARTIAL: frozenset(
        {
            OrderStatus.PARTIAL,  # self-loop: another partial fill
            OrderStatus.CLOSED,
            OrderStatus.CANCELLED,
            OrderStatus.ERROR,
        }
    ),
    # Terminal states — empty sets
    OrderStatus.CLOSED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.ERROR: frozenset(),
}


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class TradeState:
    """Wraps an ``OrderStatus`` value and provides a transition API.

    Keeping the mutable state wrapper separate from the ``Order`` dataclass
    ensures transition logic is centralised and testable in isolation.

    Usage
    -----
    ::

        state = TradeState()                       # starts at PENDING
        state.transition(OrderStatus.OPEN)         # OK
        state.transition(OrderStatus.PARTIAL)      # OK
        state.transition(OrderStatus.CLOSED)       # OK
        state.transition(OrderStatus.CANCELLED)    # raises InvalidStateTransition
    """

    def __init__(self, initial: OrderStatus = OrderStatus.PENDING) -> None:
        self._state = initial

    @property
    def current(self) -> OrderStatus:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return self._state in (
            OrderStatus.CLOSED,
            OrderStatus.CANCELLED,
            OrderStatus.ERROR,
        )

    def can_transition_to(self, target: OrderStatus) -> bool:
        """Return True if the transition is allowed without raising."""
        return target in _ALLOWED_TRANSITIONS.get(self._state, frozenset())

    def transition(self, target: OrderStatus) -> OrderStatus:
        """Apply a transition, returning the new state.

        Raises
        ------
        InvalidStateTransition
            If the transition is not in the allowed set for the current state.
        """
        if not self.can_transition_to(target):
            raise InvalidStateTransition(self._state, target)
        self._state = target
        return self._state

    def __repr__(self) -> str:
        return f"TradeState(current={self._state.value})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TradeState):
            return self._state == other._state
        if isinstance(other, OrderStatus):
            return self._state == other
        return NotImplemented


class TradeStateMachine:
    """Stateless helper that operates on ``TradeState`` objects.

    Provided as a thin façade so callers do not need to import both
    ``TradeState`` and ``InvalidStateTransition``.  Useful when building
    higher-level execution managers.
    """

    @staticmethod
    def transition(state: TradeState, target: OrderStatus) -> OrderStatus:
        """Apply *target* to *state*, return new status.  Propagates
        ``InvalidStateTransition`` on illegal moves."""
        return state.transition(target)

    @staticmethod
    def allowed_transitions(state: TradeState) -> frozenset[OrderStatus]:
        """Return the set of states reachable from *state*."""
        return _ALLOWED_TRANSITIONS.get(state.current, frozenset())

    @staticmethod
    def is_terminal(state: TradeState) -> bool:
        return state.is_terminal
