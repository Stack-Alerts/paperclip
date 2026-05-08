"""
ITM State Schema
================
Canonical in-memory representation of the full ITM system state that is
checkpointed to Redis (hot) and PostgreSQL (cold).

Design principles
-----------------
* Pure Python dataclasses — no I/O or persistence dependencies.
* ``Decimal`` throughout for monetary/quantity precision.
* All timestamps are UTC-aware ``datetime`` objects.
* Every schema object is JSON-serialisable via ``to_dict()`` / ``from_dict()``
  so that Redis and PostgreSQL adapters share a single serialisation path.
* ``StateCheckpoint`` is the envelope written on every checkpoint event.

State hierarchy
---------------
``ITMSystemState``
 ├── positions: dict[position_id → Position]
 ├── orders: dict[client_order_id → Order]
 ├── risk: RiskSnapshot
 └── strategies: dict[strategy_id → StrategyState]

``StrategyState``
 ├── run_state: StrategyRunState (active / paused / cooldown / error / stopped)
 └── per-strategy counters (risk_profile, heat, daily_pnl, active_position_id)
"""

from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any

from ..domain.entities import (
    AccountHeat,
    CapitalState,
    Instrument,
    Order,
    OrderStatus,
    Position,
    PositionDirection,
    PositionEntry,
    PositionExit,
    ContractType,
    OrderSide,
    OrderType,
    RiskProfile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


def _dec(v) -> Decimal:
    """Safely convert to Decimal."""
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _dt(v) -> datetime:
    """Parse ISO timestamp string or return datetime as-is."""
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v))


# ---------------------------------------------------------------------------
# StrategyRunState
# ---------------------------------------------------------------------------


class StrategyRunState(str, Enum):
    """Lifecycle state for a single running strategy."""

    ACTIVE = "active"
    PAUSED = "paused"
    COOLDOWN = "cooldown"
    ERROR = "error"
    STOPPED = "stopped"


# ---------------------------------------------------------------------------
# StrategyState
# ---------------------------------------------------------------------------


@dataclass
class StrategyState:
    """Per-strategy runtime state tracked inside ``ITMSystemState``.

    Attributes
    ----------
    strategy_id:         unique strategy identifier
    run_state:           current lifecycle state
    instrument:          the instrument this strategy trades (optional)
    risk_profile:        RiskProfile for this strategy (optional)
    active_position_id:  position_id of the current open position (None if flat)
    open_order_ids:      set of client_order_ids for orders managed by this strategy
    daily_pnl:           realized PnL since UTC midnight (resets daily)
    heat:                current heat units consumed by this strategy
    realized_pnl:        cumulative total realized PnL for this strategy
    daily_pnl_date:      the UTC date on which daily_pnl was last reset
    cooldown_until:      if run_state==COOLDOWN, the time when cooldown expires
    error_message:       last error message if run_state==ERROR
    updated_at:          last modification timestamp
    """

    strategy_id: str
    run_state: StrategyRunState = StrategyRunState.ACTIVE
    instrument: Optional[Instrument] = None
    risk_profile: Optional[RiskProfile] = None
    active_position_id: Optional[str] = None
    open_order_ids: set[str] = field(default_factory=set)
    daily_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    heat: Decimal = field(default_factory=lambda: Decimal("0"))
    realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    daily_pnl_date: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    error_message: Optional[str] = None
    updated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("StrategyState.strategy_id must not be empty")
        if self.daily_pnl_date is None:
            today = _now_utc().date()
            self.daily_pnl_date = datetime(
                today.year, today.month, today.day, tzinfo=timezone.utc
            )

    def touch(self) -> None:
        self.updated_at = _now_utc()

    def apply_daily_reset_if_needed(self) -> bool:
        """Reset daily_pnl counter if UTC date has rolled over.

        Returns True if a reset was applied.
        """
        today_midnight = datetime(
            *_now_utc().date().timetuple()[:3], tzinfo=timezone.utc
        )
        if self.daily_pnl_date is not None and self.daily_pnl_date < today_midnight:
            self.daily_pnl = Decimal("0")
            self.daily_pnl_date = today_midnight
            self.touch()
            return True
        return False

    def to_dict(self) -> dict:
        instr_dict = None
        if self.instrument is not None:
            instr_dict = {
                "symbol": self.instrument.symbol,
                "exchange": self.instrument.exchange,
                "contract_type": self.instrument.contract_type.value,
                "tick_size": str(self.instrument.tick_size),
                "lot_size": str(self.instrument.lot_size),
                "base_currency": self.instrument.base_currency,
                "quote_currency": self.instrument.quote_currency,
            }
        rp_dict = None
        if self.risk_profile is not None:
            rp_dict = {
                "strategy_id": self.risk_profile.strategy_id,
                "max_drawdown_pct": str(self.risk_profile.max_drawdown_pct),
                "max_position_qty": str(self.risk_profile.max_position_qty),
                "heat_limit": str(self.risk_profile.heat_limit),
                "max_daily_loss": str(self.risk_profile.max_daily_loss),
                "max_leverage": str(self.risk_profile.max_leverage),
            }
        return {
            "strategy_id": self.strategy_id,
            "run_state": self.run_state.value,
            "instrument": instr_dict,
            "risk_profile": rp_dict,
            "active_position_id": self.active_position_id,
            "open_order_ids": list(self.open_order_ids),
            "daily_pnl": str(self.daily_pnl),
            "heat": str(self.heat),
            "realized_pnl": str(self.realized_pnl),
            "daily_pnl_date": self.daily_pnl_date.isoformat() if self.daily_pnl_date else None,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "error_message": self.error_message,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyState":
        instr = None
        if d.get("instrument"):
            id_ = d["instrument"]
            instr = Instrument(
                symbol=id_["symbol"],
                exchange=id_["exchange"],
                contract_type=ContractType(id_["contract_type"]),
                tick_size=_dec(id_["tick_size"]),
                lot_size=_dec(id_["lot_size"]),
                base_currency=id_.get("base_currency", "BTC"),
                quote_currency=id_.get("quote_currency", "USDT"),
            )
        rp = None
        if d.get("risk_profile"):
            rpd = d["risk_profile"]
            rp = RiskProfile(
                strategy_id=rpd["strategy_id"],
                max_drawdown_pct=_dec(rpd["max_drawdown_pct"]),
                max_position_qty=_dec(rpd["max_position_qty"]),
                heat_limit=_dec(rpd["heat_limit"]),
                max_daily_loss=_dec(rpd["max_daily_loss"]),
                max_leverage=_dec(rpd.get("max_leverage", "1.0")),
            )
        obj = cls.__new__(cls)
        obj.strategy_id = d["strategy_id"]
        obj.run_state = StrategyRunState(d["run_state"])
        obj.instrument = instr
        obj.risk_profile = rp
        obj.active_position_id = d.get("active_position_id")
        obj.open_order_ids = set(d.get("open_order_ids", []))
        obj.daily_pnl = _dec(d.get("daily_pnl", "0"))
        obj.heat = _dec(d.get("heat", "0"))
        obj.realized_pnl = _dec(d.get("realized_pnl", "0"))
        raw_date = d.get("daily_pnl_date")
        obj.daily_pnl_date = _dt(raw_date) if raw_date else _now_utc()
        raw_cd = d.get("cooldown_until")
        obj.cooldown_until = _dt(raw_cd) if raw_cd else None
        obj.error_message = d.get("error_message")
        obj.updated_at = _dt(d["updated_at"]) if "updated_at" in d else _now_utc()
        return obj


# ---------------------------------------------------------------------------
# RiskSnapshot
# ---------------------------------------------------------------------------


@dataclass
class RiskSnapshot:
    """System-level risk metrics snapshot.

    Attributes
    ----------
    account_heat:            AccountHeat tracking aggregate exposure
    capital_state:           CapitalState tracking allocated/available capital
    total_open_positions:    number of open positions across all strategies
    total_pending_orders:    number of pending/open orders
    total_realized_pnl:      total realized PnL (USDT)
    total_daily_pnl:         total daily PnL (USDT)
    max_daily_loss:          configured maximum daily loss limit (USDT)
    max_drawdown_pct:        configured maximum drawdown percentage
    current_drawdown_pct:    current drawdown as a percentage (0–1)
    updated_at:              last modification timestamp
    """

    account_heat: Optional[AccountHeat] = None
    capital_state: Optional[CapitalState] = None
    total_open_positions: int = 0
    total_pending_orders: int = 0
    total_realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    total_daily_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    max_daily_loss: Decimal = field(default_factory=lambda: Decimal("500"))
    max_drawdown_pct: Decimal = field(default_factory=lambda: Decimal("0.05"))
    current_drawdown_pct: Decimal = field(default_factory=lambda: Decimal("0"))
    updated_at: datetime = field(default_factory=_now_utc)

    @property
    def daily_loss_limit_reached(self) -> bool:
        """True if cumulative daily losses have met or exceeded the limit."""
        return self.total_daily_pnl <= -self.max_daily_loss

    @property
    def heat_at_limit(self) -> bool:
        if self.account_heat is None:
            return False
        return self.account_heat.is_at_limit

    def touch(self) -> None:
        self.updated_at = _now_utc()

    def to_dict(self) -> dict:
        ah_dict = None
        if self.account_heat is not None:
            ah_dict = {
                "max_heat": str(self.account_heat.max_heat),
                "current_heat": str(self.account_heat.current_heat),
                "per_strategy_heat": {
                    k: str(v) for k, v in self.account_heat.per_strategy_heat.items()
                },
            }
        cs_dict = None
        if self.capital_state is not None:
            cs_dict = {
                "total_capital": str(self.capital_state.total_capital),
                "allocated": str(self.capital_state.allocated),
                "locked": str(self.capital_state.locked),
            }
        return {
            "account_heat": ah_dict,
            "capital_state": cs_dict,
            "total_open_positions": self.total_open_positions,
            "total_pending_orders": self.total_pending_orders,
            "total_realized_pnl": str(self.total_realized_pnl),
            "total_daily_pnl": str(self.total_daily_pnl),
            "max_daily_loss": str(self.max_daily_loss),
            "max_drawdown_pct": str(self.max_drawdown_pct),
            "current_drawdown_pct": str(self.current_drawdown_pct),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RiskSnapshot":
        ah = None
        if d.get("account_heat"):
            ahd = d["account_heat"]
            ah = AccountHeat(max_heat=_dec(ahd["max_heat"]))
            ah.current_heat = _dec(ahd.get("current_heat", "0"))
            ah.per_strategy_heat = {k: _dec(v) for k, v in ahd.get("per_strategy_heat", {}).items()}
        cs = None
        if d.get("capital_state"):
            csd = d["capital_state"]
            cs = CapitalState(
                total_capital=_dec(csd["total_capital"]),
                allocated=_dec(csd.get("allocated", "0")),
                locked=_dec(csd.get("locked", "0")),
            )
        return cls(
            account_heat=ah,
            capital_state=cs,
            total_open_positions=int(d.get("total_open_positions", 0)),
            total_pending_orders=int(d.get("total_pending_orders", 0)),
            total_realized_pnl=_dec(d.get("total_realized_pnl", "0")),
            total_daily_pnl=_dec(d.get("total_daily_pnl", "0")),
            max_daily_loss=_dec(d.get("max_daily_loss", "500")),
            max_drawdown_pct=_dec(d.get("max_drawdown_pct", "0.05")),
            current_drawdown_pct=_dec(d.get("current_drawdown_pct", "0")),
            updated_at=_dt(d["updated_at"]) if "updated_at" in d else _now_utc(),
        )


# ---------------------------------------------------------------------------
# ITMSystemState
# ---------------------------------------------------------------------------


@dataclass
class ITMSystemState:
    """Full ITM system state snapshot.

    This is the top-level object persisted to Redis and PostgreSQL on every
    checkpoint.  It is the authoritative in-memory state during a live run.

    Attributes
    ----------
    state_id:   unique ID for this state instance (regenerated on each restart)
    positions:  all tracked positions keyed by position_id
    orders:     all open/pending orders keyed by client_order_id
    risk:       system-level risk metrics snapshot
    strategies: per-strategy state keyed by strategy_id
    created_at: when this state instance was created (process start)
    updated_at: last time any field was modified
    checkpoint_seq: monotonically increasing checkpoint sequence number
    """

    state_id: str = field(default_factory=_new_id)
    positions: dict[str, Position] = field(default_factory=dict)
    orders: dict[str, Order] = field(default_factory=dict)
    risk: RiskSnapshot = field(default_factory=RiskSnapshot)
    strategies: dict[str, StrategyState] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    checkpoint_seq: int = 0

    def touch(self) -> None:
        self.updated_at = _now_utc()

    # ------------------------------------------------------------------ #
    # Position helpers                                                     #
    # ------------------------------------------------------------------ #

    def open_positions(self) -> list[Position]:
        """Return all positions with open_quantity > 0."""
        return [p for p in self.positions.values() if p.is_open]

    def position_for_strategy(self, strategy_id: str) -> Optional[Position]:
        """Return the active position for a strategy, or None."""
        strat = self.strategies.get(strategy_id)
        if strat is None or strat.active_position_id is None:
            return None
        return self.positions.get(strat.active_position_id)

    def add_position(self, position: Position, strategy_id: Optional[str] = None) -> None:
        """Register a new position, optionally associate with a strategy."""
        self.positions[position.position_id] = position
        if strategy_id is not None:
            strat = self.strategies.get(strategy_id)
            if strat is not None:
                strat.active_position_id = position.position_id
                strat.touch()
        self.touch()

    def close_position(self, position_id: str, strategy_id: Optional[str] = None) -> None:
        """Mark a position as closed for its strategy."""
        if strategy_id is not None:
            strat = self.strategies.get(strategy_id)
            if strat is not None and strat.active_position_id == position_id:
                strat.active_position_id = None
                strat.touch()
        self.touch()

    # ------------------------------------------------------------------ #
    # Order helpers                                                        #
    # ------------------------------------------------------------------ #

    def add_order(self, order: Order) -> None:
        self.orders[order.client_order_id] = order
        self.touch()

    def remove_terminal_orders(self) -> int:
        """Remove orders in terminal states, return count removed."""
        terminal = [
            cid
            for cid, o in self.orders.items()
            if o.status in (OrderStatus.CLOSED, OrderStatus.CANCELLED, OrderStatus.ERROR)
        ]
        for cid in terminal:
            del self.orders[cid]
        if terminal:
            self.touch()
        return len(terminal)

    # ------------------------------------------------------------------ #
    # Strategy helpers                                                     #
    # ------------------------------------------------------------------ #

    def ensure_strategy(self, strategy_id: str) -> StrategyState:
        """Return existing StrategyState or create a new one."""
        if strategy_id not in self.strategies:
            self.strategies[strategy_id] = StrategyState(strategy_id=strategy_id)
        return self.strategies[strategy_id]

    def apply_daily_resets(self) -> list[str]:
        """Apply daily PnL resets to all strategies that need it.

        Returns list of strategy_ids that were reset.
        """
        reset_ids = []
        for sid, strat in self.strategies.items():
            if strat.apply_daily_reset_if_needed():
                reset_ids.append(sid)
        return reset_ids

    # ------------------------------------------------------------------ #
    # Serialisation                                                        #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "state_id": self.state_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "checkpoint_seq": self.checkpoint_seq,
            "positions": {pid: _serialize_position(p) for pid, p in self.positions.items()},
            "orders": {cid: _serialize_order(o) for cid, o in self.orders.items()},
            "risk": self.risk.to_dict(),
            "strategies": {sid: s.to_dict() for sid, s in self.strategies.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ITMSystemState":
        positions = {
            pid: _deserialize_position(pd)
            for pid, pd in d.get("positions", {}).items()
        }
        orders = {
            cid: _deserialize_order(od)
            for cid, od in d.get("orders", {}).items()
        }
        risk = RiskSnapshot.from_dict(d["risk"]) if "risk" in d else RiskSnapshot()
        strategies = {
            sid: StrategyState.from_dict(sd)
            for sid, sd in d.get("strategies", {}).items()
        }
        obj = cls.__new__(cls)
        obj.state_id = d.get("state_id", _new_id())
        obj.positions = positions
        obj.orders = orders
        obj.risk = risk
        obj.strategies = strategies
        obj.created_at = _dt(d["created_at"]) if "created_at" in d else _now_utc()
        obj.updated_at = _dt(d["updated_at"]) if "updated_at" in d else _now_utc()
        obj.checkpoint_seq = int(d.get("checkpoint_seq", 0))
        return obj


# ---------------------------------------------------------------------------
# StateCheckpoint
# ---------------------------------------------------------------------------


@dataclass
class StateCheckpoint:
    """Envelope persisted on every checkpoint event.

    Attributes
    ----------
    checkpoint_id:   unique ID for this checkpoint
    sequence:        monotonically increasing sequence number
    state:           full ``ITMSystemState`` at checkpoint time
    source:          what triggered this checkpoint ('bar_close', 'on_demand',
                     'shutdown', 'manual')
    checkpointed_at: UTC timestamp when the checkpoint was created
    redis_latency_ms: time in ms to write to Redis (None if Redis write failed)
    pg_latency_ms:    time in ms to write to PostgreSQL (None if PG write failed)
    """

    checkpoint_id: str = field(default_factory=_new_id)
    sequence: int = 0
    state: ITMSystemState = field(default_factory=ITMSystemState)
    source: str = "bar_close"
    checkpointed_at: datetime = field(default_factory=_now_utc)
    redis_latency_ms: Optional[float] = None
    pg_latency_ms: Optional[float] = None

    # ------------------------------------------------------------------
    # Backward-compat aliases
    # ------------------------------------------------------------------

    @property
    def seq(self) -> int:
        return self.sequence

    @seq.setter
    def seq(self, value: int) -> None:
        self.sequence = value

    @property
    def trigger(self) -> str:
        return self.source

    @trigger.setter
    def trigger(self, value: str) -> None:
        self.source = value

    @property
    def written_at(self) -> datetime:
        return self.checkpointed_at

    @written_at.setter
    def written_at(self, value: datetime) -> None:
        self.checkpointed_at = value

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    @property
    def redis_ok(self) -> bool:
        return self.redis_latency_ms is not None

    @property
    def pg_ok(self) -> bool:
        return self.pg_latency_ms is not None

    @property
    def any_store_ok(self) -> bool:
        return self.redis_ok or self.pg_ok

    def to_dict(self) -> dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "sequence": self.sequence,
            "seq": self.sequence,
            "state": self.state.to_dict(),
            "source": self.source,
            "trigger": self.source,
            "checkpointed_at": self.checkpointed_at.isoformat(),
            "written_at": self.checkpointed_at.isoformat(),
            "redis_latency_ms": self.redis_latency_ms,
            "pg_latency_ms": self.pg_latency_ms,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StateCheckpoint":
        seq = int(d.get("sequence", d.get("seq", 0)))
        source = d.get("source", d.get("trigger", "bar_close"))
        ts_raw = d.get("checkpointed_at", d.get("written_at"))
        checkpointed_at = _dt(ts_raw) if ts_raw else _now_utc()
        return cls(
            checkpoint_id=d.get("checkpoint_id", _new_id()),
            sequence=seq,
            state=ITMSystemState.from_dict(d["state"]),
            source=source,
            checkpointed_at=checkpointed_at,
            redis_latency_ms=d.get("redis_latency_ms"),
            pg_latency_ms=d.get("pg_latency_ms"),
        )


# ---------------------------------------------------------------------------
# Private serialisation helpers
# ---------------------------------------------------------------------------


def _serialize_position(p: Position) -> dict:
    return {
        "position_id": p.position_id,
        "instrument_symbol": p.instrument.symbol,
        "instrument_exchange": p.instrument.exchange,
        "instrument_contract_type": p.instrument.contract_type.value,
        "instrument_tick_size": str(p.instrument.tick_size),
        "instrument_lot_size": str(p.instrument.lot_size),
        "instrument_base_currency": p.instrument.base_currency,
        "instrument_quote_currency": p.instrument.quote_currency,
        "direction": p.direction.value,
        "entries": [
            {
                "order_id": e.order_id,
                "quantity": str(e.quantity),
                "price": str(e.price),
                "timestamp": e.timestamp.isoformat(),
            }
            for e in p.entries
        ],
        "exits": [
            {
                "order_id": x.order_id,
                "quantity": str(x.quantity),
                "price": str(x.price),
                "pnl": str(x.pnl),
                "timestamp": x.timestamp.isoformat(),
            }
            for x in p.exits
        ],
        "opened_at": p.opened_at.isoformat(),
        "closed_at": p.closed_at.isoformat() if p.closed_at else None,
    }


def _deserialize_position(d: dict) -> Position:
    instr = Instrument(
        symbol=d["instrument_symbol"],
        exchange=d["instrument_exchange"],
        contract_type=ContractType(d["instrument_contract_type"]),
        tick_size=_dec(d["instrument_tick_size"]),
        lot_size=_dec(d["instrument_lot_size"]),
        base_currency=d.get("instrument_base_currency", "BTC"),
        quote_currency=d.get("instrument_quote_currency", "USDT"),
    )
    pos = Position.__new__(Position)
    pos.instrument = instr
    pos.direction = PositionDirection(d["direction"])
    pos.position_id = d["position_id"]
    pos.entries = [
        PositionEntry(
            order_id=e["order_id"],
            quantity=_dec(e["quantity"]),
            price=_dec(e["price"]),
            timestamp=_dt(e["timestamp"]),
        )
        for e in d.get("entries", [])
    ]
    pos.exits = [
        PositionExit(
            order_id=x["order_id"],
            quantity=_dec(x["quantity"]),
            price=_dec(x["price"]),
            pnl=_dec(x.get("pnl", "0")),
            timestamp=_dt(x["timestamp"]),
        )
        for x in d.get("exits", [])
    ]
    pos.opened_at = _dt(d["opened_at"])
    pos.closed_at = _dt(d["closed_at"]) if d.get("closed_at") else None
    return pos


def _serialize_order(o: Order) -> dict:
    return {
        "client_order_id": o.client_order_id,
        "exchange_order_id": o.exchange_order_id,
        "instrument_symbol": o.instrument.symbol,
        "instrument_exchange": o.instrument.exchange,
        "instrument_contract_type": o.instrument.contract_type.value,
        "instrument_tick_size": str(o.instrument.tick_size),
        "instrument_lot_size": str(o.instrument.lot_size),
        "instrument_base_currency": o.instrument.base_currency,
        "instrument_quote_currency": o.instrument.quote_currency,
        "side": o.side.value,
        "order_type": o.order_type.value,
        "quantity": str(o.quantity),
        "price": str(o.price) if o.price is not None else None,
        "status": o.status.value,
        "filled_quantity": str(o.filled_quantity),
        "average_fill_price": str(o.average_fill_price) if o.average_fill_price is not None else None,
        "created_at": o.created_at.isoformat(),
        "updated_at": o.updated_at.isoformat(),
        "error_message": o.error_message,
        "stop_loss_order_id": o.stop_loss_order_id,
    }


def _deserialize_order(d: dict) -> Order:
    instr = Instrument(
        symbol=d["instrument_symbol"],
        exchange=d["instrument_exchange"],
        contract_type=ContractType(d["instrument_contract_type"]),
        tick_size=_dec(d["instrument_tick_size"]),
        lot_size=_dec(d["instrument_lot_size"]),
        base_currency=d.get("instrument_base_currency", "BTC"),
        quote_currency=d.get("instrument_quote_currency", "USDT"),
    )
    price_raw = d.get("price")
    afp_raw = d.get("average_fill_price")
    order = Order.__new__(Order)
    order.instrument = instr
    order.side = OrderSide(d["side"])
    order.order_type = OrderType(d["order_type"])
    order.quantity = _dec(d["quantity"])
    order.price = _dec(price_raw) if price_raw is not None else None
    order.client_order_id = d["client_order_id"]
    order.exchange_order_id = d.get("exchange_order_id")
    order.status = OrderStatus(d["status"])
    order.filled_quantity = _dec(d.get("filled_quantity", "0"))
    order.average_fill_price = _dec(afp_raw) if afp_raw is not None else None
    order.created_at = _dt(d["created_at"])
    order.updated_at = _dt(d["updated_at"])
    order.error_message = d.get("error_message")
    order.stop_loss_order_id = d.get("stop_loss_order_id")
    return order
