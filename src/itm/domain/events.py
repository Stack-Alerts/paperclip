"""
ITM Domain Events
=================
Typed immutable event dataclasses emitted by the ITM execution engine.

All events:
  * are frozen dataclasses (immutable after creation)
  * carry a ``event_id`` UUID and ``occurred_at`` UTC timestamp
  * inherit from ``DomainEvent`` for uniform handling in event buses / logs

Event catalogue
---------------
Trade lifecycle:
    TradeOpened          — new position opened, entry order accepted
    TradeFilled          — order fully filled
    TradePartialFill     — order partially filled
    TradeClosed          — position fully closed, all exits complete
    TradeCancelled       — order/position cancelled before completion
    TradeError           — unrecoverable error on an order or position

Position:
    PositionUpdated      — any change to a Position aggregate

Signal / decision:
    SignalReceived       — new Signal from Strategy Builder
    DecisionMade         — ITM decision produced from signals

Risk:
    RiskLimitBreached    — a risk parameter was violated
    CapitalStateChanged  — capital allocation/release changed CapitalState
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from .entities import (
    Instrument,
    Order,
    Position,
    Signal,
    Decision,
    CapitalState,
    OrderStatus,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all ITM domain events."""

    event_id: str = field(default_factory=_new_id)
    occurred_at: datetime = field(default_factory=_now_utc)

    @property
    def event_type(self) -> str:
        return type(self).__name__


# ---------------------------------------------------------------------------
# Trade lifecycle events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeOpened(DomainEvent):
    """Fired when a new position is opened (entry order accepted by exchange).

    Attributes
    ----------
    order:       the submitted entry Order
    instrument:  target instrument
    position_id: ID of the newly created Position aggregate
    stop_loss_price: stop-loss price enforced at submission time
    """

    order: Order = field(default=None)  # type: ignore[assignment]
    instrument: Instrument = field(default=None)  # type: ignore[assignment]
    position_id: str = field(default_factory=_new_id)
    stop_loss_price: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if self.order is None:
            raise ValueError("TradeOpened.order is required")
        if self.instrument is None:
            raise ValueError("TradeOpened.instrument is required")


@dataclass(frozen=True)
class TradeFilled(DomainEvent):
    """Fired when an order is fully filled.

    Attributes
    ----------
    order:           the filled Order
    fill_price:      average fill price
    fill_quantity:   total filled quantity
    commission:      exchange commission paid (USDT)
    """

    order: Order = field(default=None)  # type: ignore[assignment]
    fill_price: Decimal = field(default=Decimal("0"))
    fill_quantity: Decimal = field(default=Decimal("0"))
    commission: Decimal = field(default=Decimal("0"))

    def __post_init__(self) -> None:
        if self.order is None:
            raise ValueError("TradeFilled.order is required")
        if self.fill_price <= Decimal("0"):
            raise ValueError("TradeFilled.fill_price must be positive")
        if self.fill_quantity <= Decimal("0"):
            raise ValueError("TradeFilled.fill_quantity must be positive")


@dataclass(frozen=True)
class TradePartialFill(DomainEvent):
    """Fired on each partial fill.

    Attributes
    ----------
    order:              the partially filled Order
    partial_price:      price of this fill slice
    partial_quantity:   quantity of this fill slice
    remaining_quantity: quantity still outstanding
    """

    order: Order = field(default=None)  # type: ignore[assignment]
    partial_price: Decimal = field(default=Decimal("0"))
    partial_quantity: Decimal = field(default=Decimal("0"))
    remaining_quantity: Decimal = field(default=Decimal("0"))

    def __post_init__(self) -> None:
        if self.order is None:
            raise ValueError("TradePartialFill.order is required")
        if self.partial_price <= Decimal("0"):
            raise ValueError("TradePartialFill.partial_price must be positive")
        if self.partial_quantity <= Decimal("0"):
            raise ValueError("TradePartialFill.partial_quantity must be positive")
        if self.remaining_quantity < Decimal("0"):
            raise ValueError("TradePartialFill.remaining_quantity cannot be negative")


@dataclass(frozen=True)
class TradeClosed(DomainEvent):
    """Fired when a position is fully closed.

    Attributes
    ----------
    position:      the closed Position aggregate
    realized_pnl:  total realized PnL for the closed position (USDT)
    """

    position: Position = field(default=None)  # type: ignore[assignment]
    realized_pnl: Decimal = field(default=Decimal("0"))

    def __post_init__(self) -> None:
        if self.position is None:
            raise ValueError("TradeClosed.position is required")


@dataclass(frozen=True)
class TradeCancelled(DomainEvent):
    """Fired when a trade/order is cancelled.

    Attributes
    ----------
    order:   the cancelled Order
    reason:  human-readable cancellation reason
    """

    order: Order = field(default=None)  # type: ignore[assignment]
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.order is None:
            raise ValueError("TradeCancelled.order is required")


@dataclass(frozen=True)
class TradeError(DomainEvent):
    """Fired when an unrecoverable error occurs on an order or position.

    Attributes
    ----------
    order_id:    client order ID (may be the only identifier available)
    error_code:  exchange or internal error code
    message:     human-readable error description
    """

    order_id: str = field(default="")
    error_code: Optional[str] = None
    message: str = field(default="")

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("TradeError.order_id is required")


# ---------------------------------------------------------------------------
# Position events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionUpdated(DomainEvent):
    """Fired whenever a Position aggregate is mutated (entry or exit recorded).

    Attributes
    ----------
    position:    current snapshot of the Position
    change_type: 'entry' or 'exit'
    """

    position: Position = field(default=None)  # type: ignore[assignment]
    change_type: str = "entry"  # 'entry' | 'exit'

    def __post_init__(self) -> None:
        if self.position is None:
            raise ValueError("PositionUpdated.position is required")
        if self.change_type not in ("entry", "exit"):
            raise ValueError(
                f"PositionUpdated.change_type must be 'entry' or 'exit', "
                f"got {self.change_type!r}"
            )


# ---------------------------------------------------------------------------
# Signal / decision events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalReceived(DomainEvent):
    """Fired when the ITM receives a new Signal from the Strategy Builder.

    Attributes
    ----------
    signal: the received Signal
    """

    signal: Signal = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.signal is None:
            raise ValueError("SignalReceived.signal is required")


@dataclass(frozen=True)
class DecisionMade(DomainEvent):
    """Fired when the ITM produces an execution Decision.

    Attributes
    ----------
    decision: the produced Decision
    """

    decision: Decision = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.decision is None:
            raise ValueError("DecisionMade.decision is required")


# ---------------------------------------------------------------------------
# Risk events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskLimitBreached(DomainEvent):
    """Fired when a risk parameter is violated.

    Attributes
    ----------
    strategy_id:     strategy that triggered the breach (if any)
    limit_type:      human-readable limit type e.g. 'max_position_size',
                     'daily_loss_limit', 'max_leverage', 'heat_limit'
    current_value:   the value that breached the limit
    limit_value:     the configured limit threshold
    message:         human-readable description
    """

    limit_type: str = field(default="")
    current_value: Decimal = field(default=Decimal("0"))
    limit_value: Decimal = field(default=Decimal("0"))
    strategy_id: Optional[str] = None
    message: str = field(default="")

    def __post_init__(self) -> None:
        if not self.limit_type:
            raise ValueError("RiskLimitBreached.limit_type is required")


@dataclass(frozen=True)
class CapitalStateChanged(DomainEvent):
    """Fired whenever the CapitalState changes (allocate, release, lock, unlock).

    Attributes
    ----------
    capital_state:   snapshot of the current CapitalState
    change_type:     'allocate' | 'release' | 'lock' | 'unlock'
    amount:          the USDT amount that changed
    """

    capital_state: CapitalState = field(default=None)  # type: ignore[assignment]
    change_type: str = field(default="")
    amount: Decimal = field(default=Decimal("0"))

    _VALID_CHANGE_TYPES = frozenset({"allocate", "release", "lock", "unlock"})

    def __post_init__(self) -> None:
        if self.capital_state is None:
            raise ValueError("CapitalStateChanged.capital_state is required")
        if self.change_type not in self._VALID_CHANGE_TYPES:
            raise ValueError(
                f"CapitalStateChanged.change_type must be one of "
                f"{sorted(self._VALID_CHANGE_TYPES)}, got {self.change_type!r}"
            )
