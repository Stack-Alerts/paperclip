"""
ITM Section F — Emergency Closeout
=====================================
Monitors drawdown and per-position loss limits; triggers market closeout of
positions when thresholds are breached.

Closeout triggers
-----------------
1. **Daily drawdown**: cumulative daily PnL loss >= ``daily_drawdown_limit``
   → close all positions for the *affected strategy*.
2. **Single position loss**: a single closed trade loss >= ``position_loss_limit``
   → close all positions for the *affected strategy*.
3. **Extreme event** (manual or programmatic): ``trigger_global_closeout()``
   → close ALL positions across ALL strategies.

Design
------
The ``EmergencyCloseout`` manager does not directly submit orders — it calls
registered closeout callbacks per strategy.  The execution engine (Section G)
provides these callbacks.  This keeps the risk module free of NT dependencies.

Callbacks
---------
* ``on_strategy_closeout(strategy_id: str, reason: str) → None``
  Called when a strategy should close all its positions.
* ``on_global_closeout(reason: str) → None``
  Called when all strategies should close all positions.

Both callbacks MUST be registered before the engine goes live.

Thread safety
-------------
Protected by an RLock.  The daily PnL reset follows the same UTC-midnight
convention as ``PerformanceMonitor``.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — institutional defaults
# ---------------------------------------------------------------------------

DEFAULT_DAILY_DRAWDOWN_LIMIT_PCT = Decimal("0.05")   # 5% daily loss triggers closeout
DEFAULT_POSITION_LOSS_LIMIT_PCT = Decimal("0.02")    # 2% single position loss


# ---------------------------------------------------------------------------
# CloseoutEvent — recorded whenever a closeout fires
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CloseoutEvent:
    """An emergency closeout that was triggered.

    Attributes
    ----------
    strategy_id:  None for global closeout, otherwise the affected strategy.
    reason:       Human-readable explanation.
    daily_pnl:    Daily PnL at time of trigger (if applicable).
    triggered_at: UTC timestamp.
    is_global:    True if this was a global (all-strategy) closeout.
    """
    reason: str
    triggered_at: datetime
    is_global: bool = False
    strategy_id: Optional[str] = None
    daily_pnl: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# EmergencyCloseoutConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmergencyCloseoutConfig:
    """Configuration for the EmergencyCloseout manager.

    Parameters
    ----------
    daily_drawdown_limit_pct:
        Fraction of base capital; when daily losses reach this fraction,
        strategy positions are closed.  Default 0.05 (5%).
    position_loss_limit_pct:
        Fraction of base capital; when a single trade loss reaches this,
        strategy positions are closed.  Default 0.02 (2%).
    base_capital:
        Total capital under management (USDT), used to convert fractions to
        absolute USDT amounts.
    """
    base_capital: Decimal
    daily_drawdown_limit_pct: Decimal = DEFAULT_DAILY_DRAWDOWN_LIMIT_PCT
    position_loss_limit_pct: Decimal = DEFAULT_POSITION_LOSS_LIMIT_PCT

    def __post_init__(self) -> None:
        if self.base_capital <= Decimal("0"):
            raise ValueError(
                f"EmergencyCloseoutConfig.base_capital must be positive, "
                f"got {self.base_capital}"
            )
        if not (Decimal("0") < self.daily_drawdown_limit_pct <= Decimal("1")):
            raise ValueError(
                f"daily_drawdown_limit_pct must be in (0, 1], "
                f"got {self.daily_drawdown_limit_pct}"
            )
        if not (Decimal("0") < self.position_loss_limit_pct <= Decimal("1")):
            raise ValueError(
                f"position_loss_limit_pct must be in (0, 1], "
                f"got {self.position_loss_limit_pct}"
            )

    @property
    def daily_drawdown_limit_usdt(self) -> Decimal:
        """Absolute USDT daily loss limit."""
        return self.base_capital * self.daily_drawdown_limit_pct

    @property
    def position_loss_limit_usdt(self) -> Decimal:
        """Absolute USDT per-position loss limit."""
        return self.base_capital * self.position_loss_limit_pct


# ---------------------------------------------------------------------------
# EmergencyCloseout
# ---------------------------------------------------------------------------

class EmergencyCloseout:
    """Monitors P&L thresholds and triggers emergency closeout of positions.

    Parameters
    ----------
    config:
        ``EmergencyCloseoutConfig`` instance.
    on_strategy_closeout:
        Callback invoked when a single strategy must close all positions.
        Signature: ``(strategy_id: str, reason: str) → None``
    on_global_closeout:
        Callback invoked when ALL strategies must close all positions.
        Signature: ``(reason: str) → None``
    """

    def __init__(
        self,
        config: EmergencyCloseoutConfig,
        on_strategy_closeout: Optional[Callable[[str, str], None]] = None,
        on_global_closeout: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._config = config
        self._lock = threading.RLock()
        self._on_strategy_closeout = on_strategy_closeout
        self._on_global_closeout = on_global_closeout

        # Per-strategy daily PnL tracking
        self._daily_pnl: dict[str, Decimal] = {}
        self._daily_pnl_date: dict[str, date] = {}

        # History of all closeout events
        self._events: list[CloseoutEvent] = []

        # Whether global closeout has been triggered (prevents duplicate fires)
        self._global_closeout_triggered: bool = False

        logger.info(
            "EmergencyCloseout initialised: base_capital=%s "
            "daily_limit=%s (%.1f%%), position_limit=%s (%.1f%%)",
            config.base_capital,
            config.daily_drawdown_limit_usdt,
            float(config.daily_drawdown_limit_pct * 100),
            config.position_loss_limit_usdt,
            float(config.position_loss_limit_pct * 100),
        )

    # ------------------------------------------------------------------ #
    # P&L notification                                                     #
    # ------------------------------------------------------------------ #

    def record_trade_pnl(
        self,
        strategy_id: str,
        pnl: Decimal,
    ) -> Optional[CloseoutEvent]:
        """Notify the manager of a closed-trade PnL.

        Automatically checks both daily drawdown and per-position loss limits.

        Parameters
        ----------
        strategy_id:
            The strategy that closed a trade.
        pnl:
            Realized PnL in USDT (negative = loss).

        Returns
        -------
        CloseoutEvent | None
            The closeout event if a limit was breached, else None.
        """
        with self._lock:
            if self._global_closeout_triggered:
                # Global closeout already in effect — nothing more to do
                return None

            self._check_daily_reset(strategy_id)
            self._daily_pnl[strategy_id] = (
                self._daily_pnl.get(strategy_id, Decimal("0")) + pnl
            )

            # 1. Single-position loss check
            if pnl < Decimal("0") and abs(pnl) >= self._config.position_loss_limit_usdt:
                reason = (
                    f"single-position loss {abs(pnl)} USDT >= limit "
                    f"{self._config.position_loss_limit_usdt} USDT "
                    f"({float(self._config.position_loss_limit_pct * 100):.1f}% of capital)"
                )
                event = CloseoutEvent(
                    reason=reason,
                    triggered_at=datetime.now(timezone.utc),
                    strategy_id=strategy_id,
                    daily_pnl=self._daily_pnl[strategy_id],
                )
                self._events.append(event)
                self._fire_strategy_closeout(strategy_id, reason)
                return event

            # 2. Daily drawdown check
            daily_loss = -self._daily_pnl[strategy_id]
            if daily_loss >= self._config.daily_drawdown_limit_usdt:
                reason = (
                    f"daily drawdown {daily_loss} USDT >= limit "
                    f"{self._config.daily_drawdown_limit_usdt} USDT "
                    f"({float(self._config.daily_drawdown_limit_pct * 100):.1f}% of capital)"
                )
                event = CloseoutEvent(
                    reason=reason,
                    triggered_at=datetime.now(timezone.utc),
                    strategy_id=strategy_id,
                    daily_pnl=self._daily_pnl[strategy_id],
                )
                self._events.append(event)
                self._fire_strategy_closeout(strategy_id, reason)
                return event

            return None

    def trigger_global_closeout(self, reason: str) -> CloseoutEvent:
        """Immediately trigger a global emergency closeout of all positions.

        Idempotent — subsequent calls after the first are no-ops (returns the
        original event).

        Parameters
        ----------
        reason:
            Human-readable explanation for the closeout.

        Returns
        -------
        CloseoutEvent
        """
        with self._lock:
            if self._global_closeout_triggered:
                # Return the first event that triggered global closeout
                for ev in self._events:
                    if ev.is_global:
                        return ev
            self._global_closeout_triggered = True
            event = CloseoutEvent(
                reason=reason,
                triggered_at=datetime.now(timezone.utc),
                is_global=True,
            )
            self._events.append(event)
            logger.critical(
                "EmergencyCloseout: GLOBAL CLOSEOUT triggered — %s", reason
            )
            if self._on_global_closeout is not None:
                try:
                    self._on_global_closeout(reason)
                except Exception:
                    logger.exception("on_global_closeout callback raised")
            return event

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    def get_daily_pnl(self, strategy_id: str) -> Decimal:
        """Return the current UTC-day PnL for *strategy_id*."""
        with self._lock:
            self._check_daily_reset(strategy_id)
            return self._daily_pnl.get(strategy_id, Decimal("0"))

    def get_events(self) -> list[CloseoutEvent]:
        """Return a copy of all closeout events recorded so far."""
        with self._lock:
            return list(self._events)

    @property
    def global_closeout_triggered(self) -> bool:
        """True after ``trigger_global_closeout`` has been called."""
        return self._global_closeout_triggered

    def reset_global_closeout(self) -> None:
        """Clear the global closeout flag (for use after positions are flat)."""
        with self._lock:
            self._global_closeout_triggered = False
            logger.info("EmergencyCloseout: global closeout flag cleared")

    def reset_daily_pnl(self, strategy_id: Optional[str] = None) -> None:
        """Force-reset daily PnL counters (e.g. on startup or manual reset).

        Parameters
        ----------
        strategy_id:
            If provided, only reset that strategy.  Otherwise reset all.
        """
        with self._lock:
            today = datetime.now(timezone.utc).date()
            if strategy_id is not None:
                self._daily_pnl[strategy_id] = Decimal("0")
                self._daily_pnl_date[strategy_id] = today
            else:
                for sid in self._daily_pnl:
                    self._daily_pnl[sid] = Decimal("0")
                    self._daily_pnl_date[sid] = today

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _check_daily_reset(self, strategy_id: str) -> None:
        """Reset daily PnL if UTC date has rolled over."""
        today = datetime.now(timezone.utc).date()
        if strategy_id not in self._daily_pnl_date:
            self._daily_pnl[strategy_id] = Decimal("0")
            self._daily_pnl_date[strategy_id] = today
        elif self._daily_pnl_date[strategy_id] != today:
            logger.info(
                "EmergencyCloseout: daily PnL reset for strategy=%r "
                "(was %s on %s, now %s)",
                strategy_id,
                self._daily_pnl.get(strategy_id, Decimal("0")),
                self._daily_pnl_date[strategy_id].isoformat(),
                today.isoformat(),
            )
            self._daily_pnl[strategy_id] = Decimal("0")
            self._daily_pnl_date[strategy_id] = today

    def _fire_strategy_closeout(self, strategy_id: str, reason: str) -> None:
        """Invoke the per-strategy closeout callback."""
        logger.warning(
            "EmergencyCloseout: strategy closeout triggered strategy=%r reason=%r",
            strategy_id, reason,
        )
        if self._on_strategy_closeout is not None:
            try:
                self._on_strategy_closeout(strategy_id, reason)
            except Exception:
                logger.exception(
                    "on_strategy_closeout callback raised for strategy=%r",
                    strategy_id,
                )
