"""
ITM Domain Entities
===================
All core domain value objects and aggregates for the Intelligent Trade Manager.

Design principles
-----------------
* Pure Python dataclasses — no NautilusTrader or I/O dependencies.
* Immutable value objects where practical (frozen=True); mutable aggregates
  (Order, Position) use post_init validation only.
* Decimal throughout for monetary precision — never float.
* All public API uses explicit keyword-only arguments where ambiguity is
  possible (via kw_only=True on Python 3.10+ or explicit ``*`` separator).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ContractType(str, Enum):
    """BTC instrument contract type."""

    SPOT = "spot"
    PERPETUAL = "perpetual"
    FUTURES = "futures"
    INVERSE_PERPETUAL = "inverse_perpetual"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ERROR = "error"


class PositionDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class SignalDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    EXIT = "exit"
    NEUTRAL = "neutral"


class DecisionAction(str, Enum):
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    HOLD = "hold"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_decimal(value: str | int | float | Decimal) -> Decimal:
    """Convert to Decimal, raising ValueError on invalid input."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Cannot convert {value!r} to Decimal: {exc}") from exc


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Instrument:
    """BTC trading pair representation.

    Parameters
    ----------
    symbol:        e.g. "BTC/USDT"
    exchange:      e.g. "binance", "bybit"
    contract_type: spot / perpetual / futures / inverse_perpetual
    tick_size:     minimum price increment as a Decimal string or Decimal
    lot_size:      minimum quantity increment as a Decimal string or Decimal
    base_currency: e.g. "BTC"
    quote_currency: e.g. "USDT"
    """

    symbol: str
    exchange: str
    contract_type: ContractType
    tick_size: Decimal
    lot_size: Decimal
    base_currency: str = "BTC"
    quote_currency: str = "USDT"

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("Instrument.symbol must not be empty")
        if not self.exchange:
            raise ValueError("Instrument.exchange must not be empty")
        if self.tick_size <= Decimal("0"):
            raise ValueError("Instrument.tick_size must be positive")
        if self.lot_size <= Decimal("0"):
            raise ValueError("Instrument.lot_size must be positive")

    @classmethod
    def btc_usdt_spot(cls, exchange: str = "binance") -> "Instrument":
        """Convenience constructor for the canonical BTC/USDT spot pair."""
        return cls(
            symbol="BTC/USDT",
            exchange=exchange,
            contract_type=ContractType.SPOT,
            tick_size=Decimal("0.01"),
            lot_size=Decimal("0.00001"),
            base_currency="BTC",
            quote_currency="USDT",
        )

    @classmethod
    def btc_usdt_perp(cls, exchange: str = "binance") -> "Instrument":
        """Convenience constructor for BTC/USDT perpetual."""
        return cls(
            symbol="BTC/USDT",
            exchange=exchange,
            contract_type=ContractType.PERPETUAL,
            tick_size=Decimal("0.10"),
            lot_size=Decimal("0.001"),
            base_currency="BTC",
            quote_currency="USDT",
        )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


@dataclass
class Order:
    """Order lifecycle model.

    Mutable aggregate — status transitions are managed by TradeStateMachine.
    """

    instrument: Instrument
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal]  # None for market orders
    client_order_id: str = field(default_factory=_new_id)
    exchange_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = field(default_factory=lambda: Decimal("0"))
    average_fill_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    error_message: Optional[str] = None
    # Optional stop-loss order linked at submission time
    stop_loss_order_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.quantity <= Decimal("0"):
            raise ValueError(f"Order.quantity must be positive, got {self.quantity}")
        if self.price is not None and self.price <= Decimal("0"):
            raise ValueError(f"Order.price must be positive, got {self.price}")
        if self.filled_quantity < Decimal("0"):
            raise ValueError("Order.filled_quantity cannot be negative")

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            OrderStatus.CLOSED,
            OrderStatus.CANCELLED,
            OrderStatus.ERROR,
        )

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        object.__setattr__(self, "updated_at", _now_utc())  # works on non-frozen

    def __repr__(self) -> str:
        return (
            f"Order(id={self.client_order_id!r}, "
            f"{self.side.value} {self.quantity} {self.instrument.symbol} "
            f"@ {self.price or 'MARKET'!r}, status={self.status.value})"
        )


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionEntry:
    """A single entry fill recorded against a position."""

    order_id: str
    quantity: Decimal
    price: Decimal
    timestamp: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        if self.quantity <= Decimal("0"):
            raise ValueError("PositionEntry.quantity must be positive")
        if self.price <= Decimal("0"):
            raise ValueError("PositionEntry.price must be positive")


@dataclass(frozen=True)
class PositionExit:
    """A single exit fill recorded against a position."""

    order_id: str
    quantity: Decimal
    price: Decimal
    timestamp: datetime = field(default_factory=_now_utc)
    pnl: Decimal = Decimal("0")  # realized PnL for this exit slice

    def __post_init__(self) -> None:
        if self.quantity <= Decimal("0"):
            raise ValueError("PositionExit.quantity must be positive")
        if self.price <= Decimal("0"):
            raise ValueError("PositionExit.price must be positive")


@dataclass
class Position:
    """Multi-entry / multi-exit position aggregate.

    Supports both LONG and SHORT positions.  PnL is always expressed in
    quote currency (USDT).
    """

    instrument: Instrument
    direction: PositionDirection
    position_id: str = field(default_factory=_new_id)
    entries: list[PositionEntry] = field(default_factory=list)
    exits: list[PositionExit] = field(default_factory=list)
    opened_at: datetime = field(default_factory=_now_utc)
    closed_at: Optional[datetime] = None

    # ------------------------------------------------------------------ #
    # Quantity helpers                                                     #
    # ------------------------------------------------------------------ #

    @property
    def total_entered(self) -> Decimal:
        """Cumulative quantity entered."""
        return sum((e.quantity for e in self.entries), Decimal("0"))

    @property
    def total_exited(self) -> Decimal:
        """Cumulative quantity exited."""
        return sum((x.quantity for x in self.exits), Decimal("0"))

    @property
    def open_quantity(self) -> Decimal:
        """Remaining open quantity."""
        return self.total_entered - self.total_exited

    @property
    def is_open(self) -> bool:
        return self.open_quantity > Decimal("0")

    # ------------------------------------------------------------------ #
    # Average prices                                                       #
    # ------------------------------------------------------------------ #

    @property
    def average_entry_price(self) -> Optional[Decimal]:
        """Volume-weighted average entry price."""
        if not self.entries:
            return None
        total_cost = sum(e.quantity * e.price for e in self.entries)
        return total_cost / self.total_entered

    @property
    def average_exit_price(self) -> Optional[Decimal]:
        """Volume-weighted average exit price."""
        if not self.exits:
            return None
        total_proceeds = sum(x.quantity * x.price for x in self.exits)
        return total_proceeds / self.total_exited

    # ------------------------------------------------------------------ #
    # PnL                                                                  #
    # ------------------------------------------------------------------ #

    @property
    def realized_pnl(self) -> Decimal:
        """Sum of per-exit realized PnL slices."""
        return sum((x.pnl for x in self.exits), Decimal("0"))

    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL at *current_price*.

        For a LONG position: (current_price - avg_entry) * open_qty
        For a SHORT position: (avg_entry - current_price) * open_qty
        """
        avg_entry = self.average_entry_price
        if avg_entry is None or self.open_quantity == Decimal("0"):
            return Decimal("0")
        if self.direction == PositionDirection.LONG:
            return (current_price - avg_entry) * self.open_quantity
        else:  # SHORT
            return (avg_entry - current_price) * self.open_quantity

    # ------------------------------------------------------------------ #
    # Mutation helpers                                                     #
    # ------------------------------------------------------------------ #

    def add_entry(self, entry: PositionEntry) -> None:
        """Record a new entry fill."""
        self.entries.append(entry)

    def add_exit(self, exit_: PositionExit) -> None:
        """Record an exit fill.  Raises ValueError if exit exceeds open qty."""
        if exit_.quantity > self.open_quantity:
            raise ValueError(
                f"Exit quantity {exit_.quantity} exceeds open quantity "
                f"{self.open_quantity} for position {self.position_id}"
            )
        self.exits.append(exit_)
        if self.open_quantity == Decimal("0"):
            self.closed_at = _now_utc()

    def __repr__(self) -> str:
        return (
            f"Position(id={self.position_id!r}, "
            f"{self.direction.value} {self.instrument.symbol}, "
            f"open={self.open_quantity}, realized_pnl={self.realized_pnl})"
        )


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    """Trading signal emitted by a Strategy Builder strategy.

    Parameters
    ----------
    direction:       LONG / SHORT / EXIT / NEUTRAL
    strength:        0.0 – 1.0 confidence score
    source_strategy: identifier of the producing strategy
    instrument:      target instrument
    expiry:          UTC timestamp after which this signal is stale
    signal_id:       auto-generated UUID if not provided
    created_at:      UTC timestamp of signal creation
    metadata:        arbitrary key/value annotations from the strategy
    """

    direction: SignalDirection
    strength: Decimal  # 0 ≤ strength ≤ 1
    source_strategy: str
    instrument: Instrument
    expiry: Optional[datetime] = None
    signal_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now_utc)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (Decimal("0") <= self.strength <= Decimal("1")):
            raise ValueError(
                f"Signal.strength must be in [0, 1], got {self.strength}"
            )
        if not self.source_strategy:
            raise ValueError("Signal.source_strategy must not be empty")

    @property
    def is_expired(self) -> bool:
        if self.expiry is None:
            return False
        return _now_utc() > self.expiry

    def __repr__(self) -> str:
        return (
            f"Signal(id={self.signal_id!r}, {self.direction.value}, "
            f"strength={self.strength}, from={self.source_strategy!r})"
        )


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    """Execution decision produced by the ITM from one or more signals.

    The decision is always risk-gated: a Decision with action=REJECT means
    the risk engine blocked the intended trade.
    """

    action: DecisionAction
    confidence: Decimal  # 0 – 1
    contributing_signals: tuple[Signal, ...]
    risk_gated: bool  # True if risk checks caused REJECT/modification
    instrument: Instrument
    decision_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now_utc)
    reason: Optional[str] = None  # human-readable rationale (especially for REJECT)

    metadata: dict = field(default_factory=dict)  # execution params: quantity, entry_price, order_type, etc.

    def __post_init__(self) -> None:
        if not (Decimal("0") <= self.confidence <= Decimal("1")):
            raise ValueError(
                f"Decision.confidence must be in [0, 1], got {self.confidence}"
            )

    def __repr__(self) -> str:
        return (
            f"Decision(id={self.decision_id!r}, action={self.action.value}, "
            f"confidence={self.confidence}, risk_gated={self.risk_gated})"
        )


# ---------------------------------------------------------------------------
# RiskProfile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskProfile:
    """Per-strategy risk parameters enforced by the ITM risk gate.

    All monetary values are in USDT.  Quantities are in BTC.
    """

    strategy_id: str
    max_drawdown_pct: Decimal  # e.g. Decimal('0.05') for 5 %
    max_position_qty: Decimal  # absolute BTC cap
    heat_limit: Decimal  # max "heat" units this strategy may consume
    max_daily_loss: Decimal  # USDT
    max_leverage: Decimal = Decimal("1.0")  # must stay at 1.0 (no margin)

    def __post_init__(self) -> None:
        if self.max_drawdown_pct <= Decimal("0") or self.max_drawdown_pct > Decimal("1"):
            raise ValueError("max_drawdown_pct must be in (0, 1]")
        if self.max_position_qty <= Decimal("0"):
            raise ValueError("max_position_qty must be positive")
        if self.heat_limit <= Decimal("0"):
            raise ValueError("heat_limit must be positive")
        if self.max_daily_loss <= Decimal("0"):
            raise ValueError("max_daily_loss must be positive")
        if self.max_leverage != Decimal("1.0"):
            raise ValueError(
                f"max_leverage must be 1.0 (no margin), got {self.max_leverage}"
            )


# ---------------------------------------------------------------------------
# AccountHeat
# ---------------------------------------------------------------------------


@dataclass
class AccountHeat:
    """Account-level heat tracking.

    Heat is a dimensionless risk unit that aggregates exposure across all
    running strategies.  When current_heat reaches max_heat, no new positions
    may be opened.
    """

    max_heat: Decimal
    current_heat: Decimal = field(default_factory=lambda: Decimal("0"))
    per_strategy_heat: dict[str, Decimal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_heat <= Decimal("0"):
            raise ValueError("AccountHeat.max_heat must be positive")

    @property
    def available_heat(self) -> Decimal:
        return self.max_heat - self.current_heat

    @property
    def is_at_limit(self) -> bool:
        return self.current_heat >= self.max_heat

    def add_heat(self, strategy_id: str, amount: Decimal) -> None:
        """Consume heat for a strategy.  Raises if it would breach max_heat."""
        if self.current_heat + amount > self.max_heat:
            raise ValueError(
                f"Adding heat {amount} for strategy {strategy_id!r} would "
                f"breach max_heat {self.max_heat} "
                f"(current={self.current_heat})"
            )
        self.per_strategy_heat[strategy_id] = (
            self.per_strategy_heat.get(strategy_id, Decimal("0")) + amount
        )
        self.current_heat += amount

    def release_heat(self, strategy_id: str, amount: Decimal) -> None:
        """Release heat previously consumed by a strategy."""
        current = self.per_strategy_heat.get(strategy_id, Decimal("0"))
        released = min(amount, current)
        self.per_strategy_heat[strategy_id] = current - released
        self.current_heat = max(Decimal("0"), self.current_heat - released)

    def __repr__(self) -> str:
        return (
            f"AccountHeat(current={self.current_heat}, max={self.max_heat}, "
            f"strategies={list(self.per_strategy_heat.keys())})"
        )


# ---------------------------------------------------------------------------
# CapitalState
# ---------------------------------------------------------------------------


@dataclass
class CapitalState:
    """Capital tracking model.

    All values are in USDT.

    total_capital  = allocated + available + locked
    allocated      = capital in open positions
    locked         = capital reserved for pending orders (not yet filled)
    available      = free capital for new positions
    """

    total_capital: Decimal
    allocated: Decimal = field(default_factory=lambda: Decimal("0"))
    locked: Decimal = field(default_factory=lambda: Decimal("0"))
    updated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.total_capital < Decimal("0"):
            raise ValueError("CapitalState.total_capital cannot be negative")
        if self.allocated < Decimal("0"):
            raise ValueError("CapitalState.allocated cannot be negative")
        if self.locked < Decimal("0"):
            raise ValueError("CapitalState.locked cannot be negative")
        if self.allocated + self.locked > self.total_capital:
            raise ValueError(
                f"allocated ({self.allocated}) + locked ({self.locked}) "
                f"exceeds total_capital ({self.total_capital})"
            )

    @property
    def available(self) -> Decimal:
        return self.total_capital - self.allocated - self.locked

    def allocate(self, amount: Decimal) -> None:
        """Move capital from available to allocated (position opened)."""
        if amount > self.available:
            raise ValueError(
                f"Cannot allocate {amount}: only {self.available} available"
            )
        self.allocated += amount
        self.updated_at = _now_utc()
        self._validate()

    def lock(self, amount: Decimal) -> None:
        """Reserve capital for a pending order."""
        if amount > self.available:
            raise ValueError(
                f"Cannot lock {amount}: only {self.available} available"
            )
        self.locked += amount
        self.updated_at = _now_utc()
        self._validate()

    def unlock(self, amount: Decimal) -> None:
        """Release previously locked capital (order cancelled/expired)."""
        self.locked = max(Decimal("0"), self.locked - amount)
        self.updated_at = _now_utc()

    def release(self, amount: Decimal, pnl: Decimal = Decimal("0")) -> None:
        """Close a position: deallocate capital and apply PnL."""
        self.allocated = max(Decimal("0"), self.allocated - amount)
        self.total_capital += pnl
        self.updated_at = _now_utc()
        self._validate()

    def __repr__(self) -> str:
        return (
            f"CapitalState(total={self.total_capital}, "
            f"allocated={self.allocated}, locked={self.locked}, "
            f"available={self.available})"
        )
