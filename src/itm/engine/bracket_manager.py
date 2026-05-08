"""
ITM Section G — TP/SL Bracket Manager
========================================
Manages the TP + SL bracket attached to every filled entry order.

Responsibilities
----------------
* After entry fill: place TP (TAKE_PROFIT or LIMIT on opposite side)
  and SL (STOP_MARKET) via the exchange client.
* Trailing stop: attach TRAILING_STOP_MARKET if configured.
* Link TP/SL to their parent entry order; cancel the surviving leg
  when the other fills.
* Handle partial fills: track open quantity, decide to continue
  or cancel remainder per ``min_fill_ratio`` config.

Bracket lifecycle
-----------------
::

    entry FILLED
        ↓
    [place TP + SL] ← BracketManager._attach_bracket()
        ↓
    TP fills → cancel SL (OCO-style management)
    SL fills → cancel TP

Design
------
* ``BracketManager`` is *not* aware of Binance's OCO API; it manages
  cancellation explicitly to remain adapter-agnostic.
* The exchange client passed in is any object with:
    - ``place_order(spec: OrderSpec) -> str``   (returns exchange_order_id)
    - ``cancel_order(client_order_id: str) -> bool``

Partial fill policy
-------------------
If ``min_fill_ratio`` is set (e.g. ``Decimal('0.8')``), an entry that
reaches terminal state (CANCELLED/REJECTED) with ``fill_ratio >= min_fill_ratio``
still gets a bracket for the actually-filled quantity.  Below the
threshold, no bracket is placed and any partial fill is treated as a
wash.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Optional, Protocol

from ..domain.entities import OrderSide
from .order_factory import OrderFactory, OrderSpec, BinanceOrderType
from .order_state_machine import OrderStateMachine, OrderState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exchange client protocol (dependency injection)
# ---------------------------------------------------------------------------


class ExchangeClient(Protocol):
    """Minimal interface the BracketManager needs from the exchange client."""

    def place_order(self, spec: OrderSpec) -> str:
        """Submit an order; return exchange order ID."""
        ...

    def cancel_order(self, client_order_id: str) -> bool:
        """Cancel by client order ID; return True if cancelled."""
        ...


# ---------------------------------------------------------------------------
# BracketConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BracketConfig:
    """Configuration for TP/SL bracket placement.

    Parameters
    ----------
    tp_pct:          Take-profit distance as a fraction of fill price
                     (e.g. Decimal('0.03') for 3%).
    sl_pct:          Stop-loss distance (enforced minimum is 2% per risk gate;
                     this value is used if already approved by the risk gate).
    trailing_stop_callback_rate:
                     If set (e.g. Decimal('1.0')), attaches a
                     TRAILING_STOP_MARKET instead of a fixed SL.
                     Mutually exclusive with sl_pct usage for the SL leg.
    min_fill_ratio:  Minimum fill ratio below which no bracket is placed on a
                     partial fill.  Default 0.5 (50%).
    """
    tp_pct: Decimal = Decimal("0.03")          # 3% TP
    sl_pct: Decimal = Decimal("0.02")          # 2% SL (minimum per risk gate)
    trailing_stop_callback_rate: Optional[Decimal] = None  # None = fixed SL
    min_fill_ratio: Decimal = Decimal("0.5")   # 50% partial fill threshold

    def __post_init__(self) -> None:
        if self.tp_pct <= Decimal("0"):
            raise ValueError("tp_pct must be positive")
        if self.sl_pct < Decimal("0.02"):
            raise ValueError("sl_pct must be >= 0.02 (2% minimum per risk policy)")
        if self.trailing_stop_callback_rate is not None:
            if not (Decimal("0.1") <= self.trailing_stop_callback_rate <= Decimal("5.0")):
                raise ValueError("trailing_stop_callback_rate must be in [0.1, 5.0]")
        if not (Decimal("0") < self.min_fill_ratio <= Decimal("1")):
            raise ValueError("min_fill_ratio must be in (0, 1]")


# ---------------------------------------------------------------------------
# BracketRecord — tracks a live bracket for one entry
# ---------------------------------------------------------------------------


@dataclass
class BracketRecord:
    """Tracks the TP/SL bracket associated with one entry order.

    Attributes
    ----------
    entry_client_id:  clientOrderId of the entry order
    tp_client_id:     clientOrderId of the TP order (None until placed)
    sl_client_id:     clientOrderId of the SL/trailing-stop order (None until placed)
    entry_quantity:   filled quantity that this bracket covers
    tp_filled:        True when TP order fills
    sl_filled:        True when SL order fills
    """
    entry_client_id: str
    entry_quantity: Decimal
    tp_client_id: Optional[str] = None
    sl_client_id: Optional[str] = None
    tp_filled: bool = False
    sl_filled: bool = False
    cancelled: bool = False  # True when the bracket is fully resolved

    @property
    def is_resolved(self) -> bool:
        return self.tp_filled or self.sl_filled or self.cancelled


# ---------------------------------------------------------------------------
# BracketManager
# ---------------------------------------------------------------------------


class BracketManager:
    """Manages TP/SL/trailing-stop brackets for live positions.

    Parameters
    ----------
    order_factory:    ``OrderFactory`` for building bracket order specs
    exchange_client:  Adapter implementing ``ExchangeClient`` protocol
    config:           ``BracketConfig`` with TP/SL percentages and policy
    """

    def __init__(
        self,
        order_factory: OrderFactory,
        exchange_client: ExchangeClient,
        config: Optional[BracketConfig] = None,
    ) -> None:
        self._factory = order_factory
        self._client = exchange_client
        self._config = config or BracketConfig()
        # Maps entry_client_id → BracketRecord
        self._brackets: dict[str, BracketRecord] = {}

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def on_entry_filled(self, sm: OrderStateMachine) -> Optional[BracketRecord]:
        """Called when an entry order state machine reaches FILLED.

        Places TP and SL (or trailing stop) for the filled quantity.

        Parameters
        ----------
        sm:  filled entry order state machine

        Returns
        -------
        BracketRecord | None
            The bracket record, or None if bracket was not placed
            (e.g. partial fill below min_fill_ratio).
        """
        if sm.state != OrderState.FILLED:
            logger.warning(
                "on_entry_filled called but order %r is in state %s — ignoring",
                sm.spec.client_order_id, sm.state.value,
            )
            return None

        fill_qty = sm.filled_quantity
        avg_price = sm.average_fill_price

        if avg_price is None or fill_qty <= Decimal("0"):
            logger.error(
                "on_entry_filled: no fills recorded for order %r",
                sm.spec.client_order_id,
            )
            return None

        # Check fill ratio for partial-fill policy
        if sm.fill_ratio < self._config.min_fill_ratio:
            logger.warning(
                "on_entry_filled: fill ratio %.2f < min %.2f for order %r — "
                "no bracket placed",
                float(sm.fill_ratio), float(self._config.min_fill_ratio),
                sm.spec.client_order_id,
            )
            return None

        bracket = self._attach_bracket(
            entry_client_id=sm.spec.client_order_id,
            entry_side_str=sm.spec.side,        # "BUY" or "SELL"
            fill_qty=fill_qty,
            avg_price=avg_price,
            strategy_id=sm.spec.strategy_id,
            signal_id=sm.spec.signal_id,
        )
        self._brackets[sm.spec.client_order_id] = bracket
        return bracket

    def on_partial_entry_cancelled(self, sm: OrderStateMachine) -> Optional[BracketRecord]:
        """Called when an entry is CANCELLED but has a meaningful partial fill.

        Places a bracket only if fill_ratio >= min_fill_ratio.
        """
        if sm.fill_ratio >= self._config.min_fill_ratio and sm.filled_quantity > Decimal("0"):
            avg_price = sm.average_fill_price
            if avg_price is None:
                return None
            bracket = self._attach_bracket(
                entry_client_id=sm.spec.client_order_id,
                entry_side_str=sm.spec.side,
                fill_qty=sm.filled_quantity,
                avg_price=avg_price,
                strategy_id=sm.spec.strategy_id,
                signal_id=sm.spec.signal_id,
            )
            self._brackets[sm.spec.client_order_id] = bracket
            return bracket
        return None

    def on_bracket_leg_filled(self, client_order_id: str) -> None:
        """Called when a TP or SL order fills.

        Identifies which bracket this belongs to, marks the leg as filled,
        and cancels the surviving counterpart.

        Parameters
        ----------
        client_order_id:  the filled order's clientOrderId
        """
        record = self._find_bracket_by_leg(client_order_id)
        if record is None:
            logger.warning(
                "on_bracket_leg_filled: no bracket found for client_id=%r",
                client_order_id,
            )
            return

        if client_order_id == record.tp_client_id:
            record.tp_filled = True
            logger.info(
                "Bracket TP filled for entry=%r — cancelling SL %r",
                record.entry_client_id, record.sl_client_id,
            )
            if record.sl_client_id:
                self._cancel_order(record.sl_client_id, reason="tp_filled")
        elif client_order_id == record.sl_client_id:
            record.sl_filled = True
            logger.info(
                "Bracket SL filled for entry=%r — cancelling TP %r",
                record.entry_client_id, record.tp_client_id,
            )
            if record.tp_client_id:
                self._cancel_order(record.tp_client_id, reason="sl_filled")

    def cancel_bracket(self, entry_client_id: str, reason: str = "manual") -> None:
        """Cancel both legs of a bracket (e.g. on strategy stop)."""
        record = self._brackets.get(entry_client_id)
        if record is None or record.is_resolved:
            return
        if record.tp_client_id:
            self._cancel_order(record.tp_client_id, reason=reason)
        if record.sl_client_id:
            self._cancel_order(record.sl_client_id, reason=reason)
        record.cancelled = True
        logger.info(
            "Bracket cancelled for entry=%r reason=%r", entry_client_id, reason
        )

    def get_bracket(self, entry_client_id: str) -> Optional[BracketRecord]:
        return self._brackets.get(entry_client_id)

    # ------------------------------------------------------------------ #
    # Internal bracket construction                                         #
    # ------------------------------------------------------------------ #

    def _attach_bracket(
        self,
        entry_client_id: str,
        entry_side_str: str,     # "BUY" or "SELL"
        fill_qty: Decimal,
        avg_price: Decimal,
        strategy_id: str,
        signal_id: str,
    ) -> BracketRecord:
        """Place TP and SL orders; return a BracketRecord."""
        # Opposite side for exit orders
        is_long = entry_side_str.upper() == "BUY"
        exit_side = OrderSide.SELL if is_long else OrderSide.BUY

        record = BracketRecord(
            entry_client_id=entry_client_id,
            entry_quantity=fill_qty,
        )

        # ── Take-profit ──────────────────────────────────────────────── #
        if is_long:
            tp_price = avg_price * (Decimal("1") + self._config.tp_pct)
        else:
            tp_price = avg_price * (Decimal("1") - self._config.tp_pct)

        tp_spec = self._factory.take_profit(
            side=exit_side,
            quantity=fill_qty,
            price=tp_price,
            stop_price=tp_price,   # trigger == limit for TAKE_PROFIT
            strategy_id=strategy_id,
            signal_id=signal_id,
            leg_index=91,
        )
        try:
            tp_exchange_id = self._client.place_order(tp_spec)
            record.tp_client_id = tp_spec.client_order_id
            logger.info(
                "Bracket TP placed: entry=%r tp_cid=%r exchange_id=%r price=%s",
                entry_client_id, tp_spec.client_order_id, tp_exchange_id, tp_price,
            )
        except Exception:
            logger.exception(
                "Failed to place TP for entry=%r — bracket incomplete",
                entry_client_id,
            )

        # ── Stop-loss or trailing stop ────────────────────────────────── #
        if self._config.trailing_stop_callback_rate is not None:
            sl_spec = self._factory.trailing_stop(
                side=exit_side,
                quantity=fill_qty,
                callback_rate=self._config.trailing_stop_callback_rate,
                strategy_id=strategy_id,
                signal_id=signal_id,
                leg_index=92,
            )
        else:
            if is_long:
                sl_price = avg_price * (Decimal("1") - self._config.sl_pct)
            else:
                sl_price = avg_price * (Decimal("1") + self._config.sl_pct)
            sl_spec = self._factory.stop_market(
                side=exit_side,
                quantity=fill_qty,
                stop_price=sl_price,
                strategy_id=strategy_id,
                signal_id=signal_id,
                leg_index=90,
            )

        try:
            sl_exchange_id = self._client.place_order(sl_spec)
            record.sl_client_id = sl_spec.client_order_id
            sl_price_display = sl_spec.stop_price or "trailing"
            logger.info(
                "Bracket SL placed: entry=%r sl_cid=%r exchange_id=%r price=%s",
                entry_client_id, sl_spec.client_order_id, sl_exchange_id, sl_price_display,
            )
        except Exception:
            logger.exception(
                "Failed to place SL for entry=%r — CRITICAL: position unprotected",
                entry_client_id,
            )

        return record

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _cancel_order(self, client_order_id: str, reason: str) -> None:
        try:
            result = self._client.cancel_order(client_order_id)
            if result:
                logger.info(
                    "Bracket leg cancelled: client_id=%r reason=%r",
                    client_order_id, reason,
                )
            else:
                logger.warning(
                    "cancel_order returned False for client_id=%r (may already be filled)",
                    client_order_id,
                )
        except Exception:
            logger.exception(
                "Failed to cancel bracket leg client_id=%r", client_order_id
            )

    def _find_bracket_by_leg(self, client_order_id: str) -> Optional[BracketRecord]:
        """Find the bracket record that owns the given TP or SL client_order_id."""
        for record in self._brackets.values():
            if (
                client_order_id == record.tp_client_id
                or client_order_id == record.sl_client_id
            ):
                return record
        return None
