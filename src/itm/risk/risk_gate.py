"""
ITM Section F — Risk Gate
===========================
The synchronous pre-trade risk gate called before every order submission.

Interface
---------
``RiskGate.approve(order: OrderRequest) → RiskDecision``

Called from the order pipeline.  Always synchronous.  Returns a
``RiskDecision`` with:
  * ``approved: bool``
  * ``reason: str | None``          — human-readable rejection reason
  * ``adjusted_quantity: Decimal``  — may be reduced by heat-based sizing
  * ``stop_loss_price: Decimal``    — mandatory 2% stop-loss price

Checks executed (in order)
---------------------------
1. Leverage == 1.0 (no margin)
2. Quantity ≥ MIN_POSITION_SIZE (0.001 BTC)
3. Quantity ≤ MAX_POSITION_SIZE (1.0 BTC)
4. Strategy is not in emergency closeout
5. Account heat (RED → reject; YELLOW → reduce quantity by 50%)
6. Capital governor: position notional fits within per-trade and total limits
7. Daily loss limit not breached
8. Stop-loss price is set at 2% from the entry price (enforced)

All decisions are logged.

Usage
-----
::

    gate = RiskGate(
        capital_governor=governor,
        closeout=closeout_manager,
    )

    decision = gate.approve(OrderRequest(
        strategy_id='momentum-v1',
        side=OrderSide.BUY,
        quantity=Decimal('0.1'),
        entry_price=Decimal('45000'),
        daily_pnl=Decimal('-200'),
        max_daily_loss=Decimal('500'),
        leverage=Decimal('1.0'),
    ))

    if decision.approved:
        submit(decision.adjusted_quantity, decision.stop_loss_price)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from ..domain.entities import OrderSide
from .capital_governor import CapitalGovernor, HeatLevel
from .emergency_closeout import EmergencyCloseout

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Institutional risk constants (AGENTS.md spec)
# ---------------------------------------------------------------------------

MAX_POSITION_SIZE = Decimal("1.0")      # 1.0 BTC hard limit
MIN_POSITION_SIZE = Decimal("0.001")    # 0.001 BTC minimum
MAX_LEVERAGE = Decimal("1.0")           # no margin, ever
STOP_LOSS_PCT = Decimal("0.02")         # 2% mandatory stop-loss


# ---------------------------------------------------------------------------
# RejectionCode — machine-readable rejection category
# ---------------------------------------------------------------------------

class RejectionCode(str, Enum):
    LEVERAGE_EXCEEDED = "leverage_exceeded"
    QUANTITY_TOO_SMALL = "quantity_too_small"
    QUANTITY_TOO_LARGE = "quantity_too_large"
    EMERGENCY_CLOSEOUT_ACTIVE = "emergency_closeout_active"
    HEAT_RED = "account_heat_red"
    CAPITAL_LIMIT = "capital_limit_exceeded"
    DAILY_LOSS_LIMIT = "daily_loss_limit_reached"
    STOP_LOSS_INVALID = "stop_loss_price_invalid"


# ---------------------------------------------------------------------------
# OrderRequest — what the order pipeline sends to the gate
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderRequest:
    """Describes a proposed order for risk gate evaluation.

    Attributes
    ----------
    strategy_id:     Owning strategy.
    side:            BUY or SELL (domain OrderSide enum).
    quantity:        BTC quantity requested.
    entry_price:     Entry price in USDT (used to compute stop-loss & notional).
    daily_pnl:       Cumulative PnL for this strategy today (USDT, may be negative).
    max_daily_loss:  Per-strategy daily loss limit in USDT.
    leverage:        Requested leverage (must equal 1.0).
    stop_loss_price: Caller-suggested stop-loss price (optional; gate will
                     enforce/override to the 2% rule regardless).
    """
    strategy_id: str
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    daily_pnl: Decimal
    max_daily_loss: Decimal
    leverage: Decimal = Decimal("1.0")
    stop_loss_price: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("OrderRequest.strategy_id must not be empty")
        if self.quantity <= Decimal("0"):
            raise ValueError(f"OrderRequest.quantity must be positive, got {self.quantity}")
        if self.entry_price <= Decimal("0"):
            raise ValueError(f"OrderRequest.entry_price must be positive, got {self.entry_price}")
        if self.max_daily_loss <= Decimal("0"):
            raise ValueError(
                f"OrderRequest.max_daily_loss must be positive, got {self.max_daily_loss}"
            )


# ---------------------------------------------------------------------------
# RiskDecision — gate output
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskDecision:
    """Result of a risk gate evaluation.

    Attributes
    ----------
    approved:           True if the order may proceed.
    adjusted_quantity:  Final BTC quantity (may be reduced from request).
    stop_loss_price:    Mandatory stop-loss price in USDT (2% from entry).
    rejection_code:     Machine-readable code when approved=False.
    reason:             Human-readable description of the decision.
    evaluated_at:       UTC timestamp of the evaluation.
    """
    approved: bool
    adjusted_quantity: Decimal
    stop_loss_price: Decimal
    reason: str
    rejection_code: Optional[RejectionCode] = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_rejected(self) -> bool:
        return not self.approved


# ---------------------------------------------------------------------------
# RiskGate
# ---------------------------------------------------------------------------

class RiskGate:
    """Synchronous pre-trade risk gate.

    Parameters
    ----------
    capital_governor:
        ``CapitalGovernor`` instance for heat and capital limit checks.
    closeout:
        ``EmergencyCloseout`` instance to check if global closeout is active.
    """

    def __init__(
        self,
        capital_governor: CapitalGovernor,
        closeout: EmergencyCloseout,
    ) -> None:
        self._governor = capital_governor
        self._closeout = closeout
        logger.info("RiskGate initialised")

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def approve(self, order: OrderRequest) -> RiskDecision:
        """Evaluate *order* against all risk rules.

        Always returns a ``RiskDecision``; never raises.

        The decision is logged at INFO (approved) or ERROR (rejected) level
        with full context.
        """
        try:
            return self._evaluate(order)
        except Exception:
            # Safety net — a bug in the gate must never silently allow orders
            logger.exception(
                "RiskGate._evaluate raised unexpectedly for strategy=%r — "
                "rejecting order as a precaution",
                order.strategy_id,
            )
            return self._reject(
                order=order,
                code=RejectionCode.CAPITAL_LIMIT,
                reason="RiskGate internal error — order rejected as safety measure",
            )

    # ------------------------------------------------------------------ #
    # Internal evaluation pipeline                                         #
    # ------------------------------------------------------------------ #

    def _evaluate(self, order: OrderRequest) -> RiskDecision:
        # Compute mandatory stop-loss price (2% rule)
        stop_loss_price = self._compute_stop_loss(order)

        # -------------------------------------------------------------- #
        # Check 1: Leverage                                               #
        # -------------------------------------------------------------- #
        if order.leverage > MAX_LEVERAGE:
            return self._reject(
                order=order,
                code=RejectionCode.LEVERAGE_EXCEEDED,
                reason=(
                    f"leverage {order.leverage} exceeds maximum {MAX_LEVERAGE} "
                    f"(no margin trading)"
                ),
                stop_loss_price=stop_loss_price,
            )

        # -------------------------------------------------------------- #
        # Check 2: Minimum position size                                  #
        # -------------------------------------------------------------- #
        if order.quantity < MIN_POSITION_SIZE:
            return self._reject(
                order=order,
                code=RejectionCode.QUANTITY_TOO_SMALL,
                reason=(
                    f"quantity {order.quantity} BTC < minimum {MIN_POSITION_SIZE} BTC"
                ),
                stop_loss_price=stop_loss_price,
            )

        # -------------------------------------------------------------- #
        # Check 3: Maximum position size                                  #
        # -------------------------------------------------------------- #
        if order.quantity > MAX_POSITION_SIZE:
            return self._reject(
                order=order,
                code=RejectionCode.QUANTITY_TOO_LARGE,
                reason=(
                    f"quantity {order.quantity} BTC > maximum {MAX_POSITION_SIZE} BTC"
                ),
                stop_loss_price=stop_loss_price,
            )

        # -------------------------------------------------------------- #
        # Check 4: Emergency closeout                                     #
        # -------------------------------------------------------------- #
        if self._closeout.global_closeout_triggered:
            return self._reject(
                order=order,
                code=RejectionCode.EMERGENCY_CLOSEOUT_ACTIVE,
                reason="global emergency closeout is active — no new positions",
                stop_loss_price=stop_loss_price,
            )

        # -------------------------------------------------------------- #
        # Check 5: Account heat                                           #
        # -------------------------------------------------------------- #
        heat_level = self._governor.heat_level
        if heat_level == HeatLevel.RED:
            return self._reject(
                order=order,
                code=RejectionCode.HEAT_RED,
                reason=(
                    f"account heat is RED "
                    f"(heat={float(self._governor.heat_pct):.1f}%) — "
                    f"no new positions"
                ),
                stop_loss_price=stop_loss_price,
            )

        # Apply YELLOW heat reduction if applicable
        notional = order.quantity * order.entry_price
        if heat_level == HeatLevel.YELLOW:
            adjusted_notional = self._governor.adjusted_notional(notional)
            if adjusted_notional <= Decimal("0"):
                return self._reject(
                    order=order,
                    code=RejectionCode.HEAT_RED,
                    reason="account heat adjustment resulted in zero quantity",
                    stop_loss_price=stop_loss_price,
                )
            adjusted_qty = adjusted_notional / order.entry_price
            # Re-check quantity bounds after reduction
            adjusted_qty = max(MIN_POSITION_SIZE, min(adjusted_qty, MAX_POSITION_SIZE))
        else:
            adjusted_qty = order.quantity

        # Recompute notional with adjusted quantity
        adjusted_notional = adjusted_qty * order.entry_price

        # -------------------------------------------------------------- #
        # Check 6: Capital governor (per-trade + total exposure limits)   #
        # -------------------------------------------------------------- #
        if not self._governor.can_open_position(order.strategy_id, adjusted_notional):
            snap = self._governor.snapshot()
            return self._reject(
                order=order,
                code=RejectionCode.CAPITAL_LIMIT,
                reason=(
                    f"capital limit: notional {adjusted_notional} USDT would breach "
                    f"per-trade or total exposure cap "
                    f"(open_exposure={snap.open_exposure}, "
                    f"max={snap.max_exposure_notional})"
                ),
                stop_loss_price=stop_loss_price,
            )

        # -------------------------------------------------------------- #
        # Check 7: Daily loss limit                                       #
        # -------------------------------------------------------------- #
        daily_loss = -order.daily_pnl  # positive = loss
        if daily_loss >= order.max_daily_loss:
            return self._reject(
                order=order,
                code=RejectionCode.DAILY_LOSS_LIMIT,
                reason=(
                    f"daily loss {daily_loss} USDT >= limit {order.max_daily_loss} USDT"
                ),
                stop_loss_price=stop_loss_price,
            )

        # -------------------------------------------------------------- #
        # All checks passed — approve                                      #
        # -------------------------------------------------------------- #
        reason = (
            f"approved: strategy={order.strategy_id!r} "
            f"qty={adjusted_qty} BTC notional={adjusted_notional:.2f} USDT "
            f"stop_loss={stop_loss_price:.2f} USDT "
            f"heat={heat_level.value}"
        )
        logger.info("RiskGate: %s", reason)
        return RiskDecision(
            approved=True,
            adjusted_quantity=adjusted_qty,
            stop_loss_price=stop_loss_price,
            reason=reason,
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _compute_stop_loss(self, order: OrderRequest) -> Decimal:
        """Compute the mandatory 2% stop-loss price.

        For BUY: stop must be AT LEAST 2% below entry (stop <= entry × 0.98).
            - required_stop = entry × (1 - STOP_LOSS_PCT)   → the maximum allowed stop
            - If caller provides a looser stop (> required_stop), override to required_stop
            - If caller provides a tighter stop (<= required_stop), accept it

        For SELL: stop must be AT LEAST 2% above entry (stop >= entry × 1.02).
            - required_stop = entry × (1 + STOP_LOSS_PCT)   → the minimum allowed stop
            - If caller provides a looser stop (< required_stop), override to required_stop
            - If caller provides a tighter stop (>= required_stop), accept it
        """
        if order.side == OrderSide.BUY:
            required_stop = order.entry_price * (Decimal("1") - STOP_LOSS_PCT)
            if order.stop_loss_price is not None:
                # For BUY: stop price must be at or below required_stop (more distance)
                # min() picks the more protective (lower) price
                return min(required_stop, order.stop_loss_price)
            return required_stop
        else:  # SELL
            required_stop = order.entry_price * (Decimal("1") + STOP_LOSS_PCT)
            if order.stop_loss_price is not None:
                # For SELL: stop price must be at or above required_stop (more distance)
                # max() picks the more protective (higher) price
                return max(required_stop, order.stop_loss_price)
            return required_stop

    def _reject(
        self,
        order: OrderRequest,
        code: RejectionCode,
        reason: str,
        stop_loss_price: Optional[Decimal] = None,
    ) -> RiskDecision:
        if stop_loss_price is None:
            stop_loss_price = self._compute_stop_loss(order)
        logger.error(
            "RiskGate REJECTED: strategy=%r code=%s reason=%s",
            order.strategy_id, code.value, reason,
        )
        return RiskDecision(
            approved=False,
            adjusted_quantity=Decimal("0"),
            stop_loss_price=stop_loss_price,
            rejection_code=code,
            reason=reason,
        )
