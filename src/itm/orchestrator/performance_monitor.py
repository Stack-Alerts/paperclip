"""
ITM Section D — Performance Monitor
======================================
Tracks per-strategy PnL, drawdown, and win rate; auto-pauses strategies that
breach their configured drawdown or daily-loss thresholds.

Metrics tracked
---------------
Per strategy:
  * ``realized_pnl``          — cumulative realized PnL (USDT)
  * ``daily_pnl``             — realized PnL since UTC midnight (resets at midnight)
  * ``peak_portfolio_value``  — running high-water mark (for drawdown calculation)
  * ``current_drawdown_pct``  — (peak - current) / peak
  * ``win_count``             — number of profitable closed trades
  * ``loss_count``            — number of losing closed trades
  * ``win_rate``              — win_count / (win_count + loss_count)

Auto-pause triggers
-------------------
1. ``current_drawdown_pct >= config.risk.max_drawdown_pct``
2. ``daily_pnl <= -config.risk.max_daily_loss`` (daily loss limit)

When triggered, the monitor calls ``StrategyRegistry.auto_pause()`` and logs
a structured warning.

Daily reset
-----------
``daily_pnl`` resets to 0 at UTC midnight.  The monitor checks for a date
rollover on each ``record_pnl()`` call and resets automatically.

Thread safety
-------------
All mutations are protected by a per-strategy lock (coarser global lock used
for safety in the MVP).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from .registry import StrategyRegistry
from .sb_contract import StrategyConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# StrategyMetrics — per-strategy performance metrics
# ---------------------------------------------------------------------------

@dataclass
class StrategyMetrics:
    """Live performance metrics for a single strategy.

    Designed to be consumed directly by Section I (dashboard / ML) later.
    All monetary values in USDT; fractions are in [0, 1].
    """
    strategy_id: str
    strategy_name: str

    # Cumulative
    realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    win_count: int = 0
    loss_count: int = 0

    # Daily (resets at UTC midnight)
    daily_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    daily_pnl_date: date = field(default_factory=lambda: datetime.now(timezone.utc).date())

    # Drawdown
    peak_portfolio_value: Decimal = field(default_factory=lambda: Decimal("0"))
    current_drawdown_pct: Decimal = field(default_factory=lambda: Decimal("0"))

    # Auto-pause tracking
    auto_pause_count: int = 0
    last_auto_pause_at: Optional[datetime] = None
    last_auto_pause_reason: Optional[str] = None

    # Metadata
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_trades(self) -> int:
        return self.win_count + self.loss_count

    @property
    def win_rate(self) -> Optional[Decimal]:
        """Return win rate in [0, 1] or None if no trades yet."""
        if self.total_trades == 0:
            return None
        return Decimal(str(self.win_count)) / Decimal(str(self.total_trades))

    def _check_daily_reset(self) -> None:
        """Reset daily_pnl if the UTC date has rolled over."""
        today = datetime.now(timezone.utc).date()
        if today != self.daily_pnl_date:
            logger.info(
                "Daily PnL reset for strategy %r: was %s (date=%s → %s)",
                self.strategy_id, self.daily_pnl,
                self.daily_pnl_date.isoformat(), today.isoformat(),
            )
            self.daily_pnl = Decimal("0")
            self.daily_pnl_date = today

    def record_pnl(self, pnl: Decimal, capital_base: Decimal) -> None:
        """Update PnL counters with a closed-trade result.

        Parameters
        ----------
        pnl:
            Realized PnL for this trade in USDT (positive = profit, negative = loss).
        capital_base:
            Current portfolio value used for drawdown % calculation.
        """
        self._check_daily_reset()
        now = datetime.now(timezone.utc)

        self.realized_pnl += pnl
        self.daily_pnl += pnl

        if pnl > Decimal("0"):
            self.win_count += 1
        elif pnl < Decimal("0"):
            self.loss_count += 1

        # Update high-water mark and drawdown
        if capital_base > self.peak_portfolio_value:
            self.peak_portfolio_value = capital_base
        if self.peak_portfolio_value > Decimal("0"):
            self.current_drawdown_pct = (
                (self.peak_portfolio_value - capital_base) / self.peak_portfolio_value
            )
        else:
            self.current_drawdown_pct = Decimal("0")

        self.updated_at = now

    def __repr__(self) -> str:
        wr = self.win_rate
        return (
            f"StrategyMetrics(id={self.strategy_id!r}, "
            f"pnl={self.realized_pnl}, daily_pnl={self.daily_pnl}, "
            f"drawdown={self.current_drawdown_pct:.4f}, "
            f"win_rate={'N/A' if wr is None else f'{float(wr):.2%}'})"
        )


# ---------------------------------------------------------------------------
# PerformanceMonitor
# ---------------------------------------------------------------------------

class PerformanceMonitor:
    """Tracks per-strategy metrics and triggers auto-pause when limits breach.

    Parameters
    ----------
    registry:
        The ``StrategyRegistry`` used to call ``auto_pause()`` when thresholds
        are exceeded.
    """

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry
        self._lock = threading.RLock()
        self._metrics: dict[str, StrategyMetrics] = {}
        self._configs: dict[str, StrategyConfig] = {}

    # ------------------------------------------------------------------ #
    # Registration                                                         #
    # ------------------------------------------------------------------ #

    def register(self, config: StrategyConfig) -> StrategyMetrics:
        """Register a strategy so the monitor can track its metrics.

        Parameters
        ----------
        config:
            The strategy's ``StrategyConfig`` (used for risk thresholds).

        Returns
        -------
        StrategyMetrics
            Freshly initialised metrics object.
        """
        with self._lock:
            metrics = StrategyMetrics(
                strategy_id=config.strategy_id,
                strategy_name=config.name,
            )
            self._metrics[config.strategy_id] = metrics
            self._configs[config.strategy_id] = config
            logger.info(
                "PerformanceMonitor: registered strategy %r (max_drawdown_pct=%s, "
                "max_daily_loss=%s)",
                config.strategy_id, config.risk.max_drawdown_pct,
                config.risk.max_daily_loss,
            )
            return metrics

    def deregister(self, strategy_id: str) -> None:
        """Remove a strategy from tracking."""
        with self._lock:
            self._metrics.pop(strategy_id, None)
            self._configs.pop(strategy_id, None)

    # ------------------------------------------------------------------ #
    # PnL recording                                                        #
    # ------------------------------------------------------------------ #

    def record_pnl(
        self,
        strategy_id: str,
        pnl: Decimal,
        capital_base: Decimal,
    ) -> StrategyMetrics:
        """Record a closed-trade PnL update and check auto-pause thresholds.

        Parameters
        ----------
        strategy_id:
            The strategy that closed a trade.
        pnl:
            Realized PnL in USDT (positive = profit, negative = loss).
        capital_base:
            Current total portfolio value for this strategy (used to compute
            drawdown percentage against the high-water mark).

        Returns
        -------
        StrategyMetrics
            Updated metrics snapshot.

        Raises
        ------
        KeyError
            If the strategy has not been registered.
        """
        with self._lock:
            metrics = self._require(strategy_id)
            config = self._configs[strategy_id]
            metrics.record_pnl(pnl, capital_base)

        # Auto-pause checks — run outside lock to avoid holding it during registry call
        self._check_auto_pause(metrics, config)
        return metrics

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    def get_metrics(self, strategy_id: str) -> Optional[StrategyMetrics]:
        """Return current metrics for *strategy_id*, or None if unregistered."""
        with self._lock:
            return self._metrics.get(strategy_id)

    def all_metrics(self) -> dict[str, StrategyMetrics]:
        """Return a snapshot of all metrics (shallow copy)."""
        with self._lock:
            return dict(self._metrics)

    def refresh_daily_resets(self) -> None:
        """Force a check for daily PnL resets across all strategies.

        Normally called by the orchestrator at UTC midnight or on startup.
        """
        with self._lock:
            for metrics in self._metrics.values():
                metrics._check_daily_reset()

    # ------------------------------------------------------------------ #
    # Auto-pause logic                                                     #
    # ------------------------------------------------------------------ #

    def _check_auto_pause(
        self, metrics: StrategyMetrics, config: StrategyConfig
    ) -> bool:
        """Evaluate auto-pause conditions; returns True if strategy was paused."""
        entry = self._registry.get(metrics.strategy_id)
        if entry is None or not entry.is_active:
            # Nothing to pause
            return False

        # 1. Drawdown breach
        if metrics.current_drawdown_pct >= config.risk.max_drawdown_pct:
            reason = (
                f"drawdown {float(metrics.current_drawdown_pct):.2%} >= "
                f"limit {float(config.risk.max_drawdown_pct):.2%}"
            )
            self._trigger_auto_pause(metrics, reason)
            return True

        # 2. Daily loss breach
        daily_loss = -metrics.daily_pnl
        if daily_loss >= config.risk.max_daily_loss:
            reason = (
                f"daily_loss {daily_loss} >= limit {config.risk.max_daily_loss} USDT"
            )
            self._trigger_auto_pause(metrics, reason)
            return True

        return False

    def _trigger_auto_pause(self, metrics: StrategyMetrics, reason: str) -> None:
        """Record auto-pause metadata on the metrics object and call the registry."""
        now = datetime.now(timezone.utc)
        with self._lock:
            metrics.auto_pause_count += 1
            metrics.last_auto_pause_at = now
            metrics.last_auto_pause_reason = reason
            metrics.updated_at = now

        logger.warning(
            "PerformanceMonitor auto-pause: strategy=%r reason=%r",
            metrics.strategy_id, reason,
        )
        self._registry.auto_pause(metrics.strategy_id, reason)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _require(self, strategy_id: str) -> StrategyMetrics:
        metrics = self._metrics.get(strategy_id)
        if metrics is None:
            raise KeyError(
                f"Strategy {strategy_id!r} is not registered in PerformanceMonitor"
            )
        return metrics
