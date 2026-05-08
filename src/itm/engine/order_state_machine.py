"""
ITM Section G — Order Lifecycle State Machine
===============================================
Tracks every order from submission through to terminal state.

State transitions
-----------------
::

    submitted
        ↓   (exchange ACK or immediate rejection)
    acknowledged ──→ rejected
        ↓
    partially_filled ←──┐
        ↓               │ (incremental fills)
    filled              │
        ↑───────────────┘
    cancelled  (timeout, manual cancel, or counterpart bracket fill)

Each transition is validated — illegal transitions raise
``IllegalStateTransition``.

Thread-safety
-------------
``OrderStateMachine`` instances are *not* thread-safe on their own.
The ``ExecutionEngine`` serialises access via its event-loop thread.

Usage
-----
::

    sm = OrderStateMachine(spec)
    sm.acknowledge("exchange-order-id-123")
    sm.partial_fill(Decimal('0.05'), Decimal('45000'))
    sm.fill(Decimal('0.05'), Decimal('45001'))   # ← now FILLED
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import Callable, List, Optional

from .order_factory import OrderSpec

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Order lifecycle states
# ---------------------------------------------------------------------------


class OrderState(str, Enum):
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

    @property
    def is_terminal(self) -> bool:
        return self in (
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
        )

    @property
    def is_active(self) -> bool:
        return not self.is_terminal


class IllegalStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""


# ---------------------------------------------------------------------------
# FillRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FillRecord:
    """Immutable snapshot of a single fill event."""

    price: Decimal
    quantity: Decimal
    commission: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# OrderStateMachine
# ---------------------------------------------------------------------------


class OrderStateMachine:
    """Manages lifecycle state for a single order.

    Parameters
    ----------
    spec:      the ``OrderSpec`` describing the order
    ttl_secs:  Time-To-Live in seconds; ``None`` means no timeout.
               The machine itself does not enforce timeouts — call
               ``is_timed_out()`` from a scheduler to check.

    Attributes
    ----------
    state:             current ``OrderState``
    exchange_order_id: set after exchange ACK
    fills:             ordered list of ``FillRecord`` objects
    cancelled_reason:  human-readable reason string when CANCELLED
    rejected_reason:   human-readable reason string when REJECTED
    """

    # Valid transitions: {from_state: set of allowed to_states}
    _TRANSITIONS: dict[OrderState, set[OrderState]] = {
        OrderState.SUBMITTED: {
            OrderState.ACKNOWLEDGED,
            OrderState.REJECTED,
            OrderState.CANCELLED,
        },
        OrderState.ACKNOWLEDGED: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
        },
        OrderState.PARTIALLY_FILLED: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELLED,
        },
        OrderState.FILLED: set(),
        OrderState.CANCELLED: set(),
        OrderState.REJECTED: set(),
    }

    def __init__(
        self,
        spec: OrderSpec,
        ttl_secs: Optional[float] = 60.0,
        on_state_change: Optional[Callable[["OrderStateMachine", OrderState, OrderState], None]] = None,
    ) -> None:
        self.spec = spec
        self.ttl_secs = ttl_secs
        self._on_state_change = on_state_change

        self.state: OrderState = OrderState.SUBMITTED
        self.exchange_order_id: Optional[str] = None
        self.fills: List[FillRecord] = []
        self.cancelled_reason: Optional[str] = None
        self.rejected_reason: Optional[str] = None
        self.submitted_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = self.submitted_at

        logger.info(
            "OrderStateMachine: SUBMITTED client_id=%r strategy=%r signal=%r",
            spec.client_order_id, spec.strategy_id, spec.signal_id,
        )

    # ------------------------------------------------------------------ #
    # State-transition methods                                             #
    # ------------------------------------------------------------------ #

    def acknowledge(self, exchange_order_id: str) -> None:
        """Exchange confirmed the order. Moves to ACKNOWLEDGED."""
        self._transition(OrderState.ACKNOWLEDGED)
        self.exchange_order_id = exchange_order_id
        logger.info(
            "OrderStateMachine ACK: client_id=%r exchange_id=%r",
            self.spec.client_order_id, exchange_order_id,
        )

    def partial_fill(self, price: Decimal, quantity: Decimal, commission: Decimal = Decimal("0")) -> None:
        """Record a partial fill. Moves to PARTIALLY_FILLED if not already."""
        if quantity <= Decimal("0"):
            raise ValueError(f"partial_fill quantity must be positive, got {quantity}")
        if price <= Decimal("0"):
            raise ValueError(f"partial_fill price must be positive, got {price}")
        new_state = (
            OrderState.PARTIALLY_FILLED
            if self.state != OrderState.PARTIALLY_FILLED
            else OrderState.PARTIALLY_FILLED  # self-loop allowed
        )
        self._transition(new_state)
        fill = FillRecord(price=price, quantity=quantity, commission=commission)
        self.fills.append(fill)
        logger.info(
            "OrderStateMachine PARTIAL_FILL: client_id=%r price=%s qty=%s "
            "total_filled=%s/%s",
            self.spec.client_order_id, price, quantity,
            self.filled_quantity, self.spec.quantity,
        )

    def fill(self, price: Decimal, quantity: Decimal, commission: Decimal = Decimal("0")) -> None:
        """Record the final fill. Moves to FILLED."""
        if quantity <= Decimal("0"):
            raise ValueError(f"fill quantity must be positive, got {quantity}")
        if price <= Decimal("0"):
            raise ValueError(f"fill price must be positive, got {price}")
        self._transition(OrderState.FILLED)
        fill = FillRecord(price=price, quantity=quantity, commission=commission)
        self.fills.append(fill)
        logger.info(
            "OrderStateMachine FILLED: client_id=%r avg_price=%s total_qty=%s",
            self.spec.client_order_id, self.average_fill_price, self.filled_quantity,
        )

    def cancel(self, reason: str = "manual") -> None:
        """Cancel the order. Moves to CANCELLED."""
        self._transition(OrderState.CANCELLED)
        self.cancelled_reason = reason
        logger.info(
            "OrderStateMachine CANCELLED: client_id=%r reason=%r",
            self.spec.client_order_id, reason,
        )

    def reject(self, reason: str) -> None:
        """Mark the order as rejected by the exchange. Moves to REJECTED."""
        self._transition(OrderState.REJECTED)
        self.rejected_reason = reason
        logger.error(
            "OrderStateMachine REJECTED: client_id=%r reason=%r",
            self.spec.client_order_id, reason,
        )

    # ------------------------------------------------------------------ #
    # Timeout detection                                                    #
    # ------------------------------------------------------------------ #

    def is_timed_out(self) -> bool:
        """Return True if the order has exceeded its TTL and is still active.

        The caller is responsible for actually cancelling the order on the
        exchange and calling ``cancel('ttl_expired')``.
        """
        if self.ttl_secs is None:
            return False
        if self.state.is_terminal:
            return False
        elapsed = (datetime.now(timezone.utc) - self.submitted_at).total_seconds()
        return elapsed > self.ttl_secs

    # ------------------------------------------------------------------ #
    # Aggregation helpers                                                  #
    # ------------------------------------------------------------------ #

    @property
    def filled_quantity(self) -> Decimal:
        """Total filled quantity across all fill records."""
        return sum((f.quantity for f in self.fills), Decimal("0"))

    @property
    def remaining_quantity(self) -> Decimal:
        """Quantity still outstanding."""
        return self.spec.quantity - self.filled_quantity

    @property
    def average_fill_price(self) -> Optional[Decimal]:
        """Volume-weighted average fill price; None if no fills."""
        if not self.fills:
            return None
        total_cost = sum(f.price * f.quantity for f in self.fills)
        total_qty = self.filled_quantity
        if total_qty == Decimal("0"):
            return None
        return total_cost / total_qty

    @property
    def total_commission(self) -> Decimal:
        """Sum of all commissions paid."""
        return sum((f.commission for f in self.fills), Decimal("0"))

    @property
    def fill_ratio(self) -> Decimal:
        """Fraction of the order that has been filled (0–1)."""
        if self.spec.quantity == Decimal("0"):
            return Decimal("0")
        return self.filled_quantity / self.spec.quantity

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _transition(self, new_state: OrderState) -> None:
        allowed = self._TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise IllegalStateTransition(
                f"Cannot transition from {self.state.value} → {new_state.value} "
                f"for order {self.spec.client_order_id!r}"
            )
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        if self._on_state_change:
            try:
                self._on_state_change(self, old_state, new_state)
            except Exception:
                logger.exception(
                    "on_state_change callback raised for order %r",
                    self.spec.client_order_id,
                )

    def __repr__(self) -> str:
        return (
            f"OrderStateMachine(id={self.spec.client_order_id!r}, "
            f"state={self.state.value}, "
            f"filled={self.filled_quantity}/{self.spec.quantity})"
        )
