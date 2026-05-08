"""
ITM Section F — Capital Metrics
==================================
Rolling performance metrics for the capital pool and individual strategies.

Metrics tracked
---------------
* **Sharpe ratio** (rolling 30-day, annualised) — risk-adjusted return
* **Maximum drawdown** (since inception) — worst peak-to-trough decline
* **Profit factor** — gross profit / gross loss (> 1.0 = positive expectancy)
* **Win rate** — % of trades that closed profitably

These are computed on a stream of closed-trade PnL observations.  No external
dependencies — pure Python ``Decimal`` arithmetic.

Usage
-----
::

    metrics = CapitalMetrics()

    # Record each closed trade
    metrics.record_trade(pnl=Decimal('120'), portfolio_value=Decimal('25200'))
    metrics.record_trade(pnl=Decimal('-80'), portfolio_value=Decimal('25120'))

    print(metrics.sharpe_ratio)    # rolling 30-day annualised
    print(metrics.max_drawdown)    # worst draw since inception (fraction, 0-1)
    print(metrics.profit_factor)   # e.g. Decimal('1.5')
    print(metrics.win_rate)        # e.g. Decimal('0.60')
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHARPE_ROLLING_WINDOW = 30         # calendar days
ANNUALISATION_FACTOR = Decimal("365")  # trading days per year for crypto (24/7)


# ---------------------------------------------------------------------------
# TradeRecord — a single closed-trade observation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TradeRecord:
    """A single closed-trade PnL record.

    Attributes
    ----------
    pnl:             Realized PnL in USDT (positive = win, negative = loss)
    portfolio_value: Portfolio value AFTER this trade is closed
    closed_at:       UTC timestamp of the close
    strategy_id:     Optional strategy that produced this trade
    """
    pnl: Decimal
    portfolio_value: Decimal
    closed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strategy_id: Optional[str] = None


# ---------------------------------------------------------------------------
# CapitalMetricsSnapshot — point-in-time read-out
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CapitalMetricsSnapshot:
    """Immutable snapshot of all capital metrics at a point in time."""
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: Optional[Decimal]
    profit_factor: Optional[Decimal]
    max_drawdown: Decimal           # fraction 0–1 (e.g. 0.05 = 5%)
    sharpe_ratio: Optional[Decimal] # annualised, or None if insufficient data
    peak_portfolio_value: Decimal
    current_portfolio_value: Decimal
    total_pnl: Decimal
    snapshot_at: datetime


# ---------------------------------------------------------------------------
# CapitalMetrics
# ---------------------------------------------------------------------------

class CapitalMetrics:
    """Tracks and computes rolling capital performance metrics.

    Thread safety
    -------------
    This class is intentionally NOT thread-safe — callers must synchronise
    externally if needed (e.g. via the PerformanceMonitor's lock).  This
    keeps the class simple and fast for the single-threaded NT event loop.

    Parameters
    ----------
    sharpe_window_days:
        Number of days for the rolling Sharpe ratio window (default 30).
    initial_capital:
        Starting portfolio value for drawdown baseline (default 0 — first
        record_trade call sets the baseline if not provided).
    """

    def __init__(
        self,
        sharpe_window_days: int = SHARPE_ROLLING_WINDOW,
        initial_capital: Decimal = Decimal("0"),
    ) -> None:
        self._sharpe_window_days = sharpe_window_days
        self._initial_capital = initial_capital

        # Rolling window of daily PnL returns for Sharpe computation
        self._daily_returns: deque[Decimal] = deque()
        self._daily_pnl_window: deque[tuple[datetime, Decimal]] = deque()

        # Cumulative counters
        self._total_pnl: Decimal = Decimal("0")
        self._gross_profit: Decimal = Decimal("0")
        self._gross_loss: Decimal = Decimal("0")   # stored as positive
        self._win_count: int = 0
        self._loss_count: int = 0

        # Drawdown tracking
        self._peak_portfolio_value: Decimal = initial_capital
        self._current_portfolio_value: Decimal = initial_capital
        self._max_drawdown: Decimal = Decimal("0")

        # All records (for Sharpe computation)
        self._records: list[TradeRecord] = []

    # ------------------------------------------------------------------ #
    # Trade recording                                                      #
    # ------------------------------------------------------------------ #

    def record_trade(
        self,
        pnl: Decimal,
        portfolio_value: Decimal,
        strategy_id: Optional[str] = None,
        closed_at: Optional[datetime] = None,
    ) -> None:
        """Record a closed trade and update all metrics.

        Parameters
        ----------
        pnl:
            Realized PnL in USDT (positive = profit).
        portfolio_value:
            Total portfolio value AFTER this trade closes.
        strategy_id:
            Optional strategy identifier for attribution.
        closed_at:
            Close timestamp (UTC); defaults to now.
        """
        ts = closed_at or datetime.now(timezone.utc)
        record = TradeRecord(
            pnl=pnl,
            portfolio_value=portfolio_value,
            closed_at=ts,
            strategy_id=strategy_id,
        )
        self._records.append(record)

        # Cumulative PnL
        self._total_pnl += pnl

        # Win/loss counters
        if pnl > Decimal("0"):
            self._win_count += 1
            self._gross_profit += pnl
        elif pnl < Decimal("0"):
            self._loss_count += 1
            self._gross_loss += abs(pnl)

        # Update drawdown
        self._current_portfolio_value = portfolio_value
        if portfolio_value > self._peak_portfolio_value:
            self._peak_portfolio_value = portfolio_value

        if self._peak_portfolio_value > Decimal("0"):
            drawdown = (
                (self._peak_portfolio_value - portfolio_value)
                / self._peak_portfolio_value
            )
            if drawdown > self._max_drawdown:
                self._max_drawdown = drawdown

        # Update rolling daily returns window
        self._update_daily_returns(ts, pnl, portfolio_value)

        logger.debug(
            "CapitalMetrics: recorded trade pnl=%s portfolio=%s "
            "max_dd=%s win_rate=%s",
            pnl, portfolio_value,
            f"{float(self._max_drawdown):.4f}",
            self.win_rate,
        )

    def _update_daily_returns(
        self,
        ts: datetime,
        pnl: Decimal,
        portfolio_value: Decimal,
    ) -> None:
        """Add a PnL entry to the rolling Sharpe window and prune old data."""
        self._daily_pnl_window.append((ts, pnl))

        # Prune entries older than the window
        cutoff = ts.timestamp() - (self._sharpe_window_days * 86400)
        while self._daily_pnl_window and self._daily_pnl_window[0][0].timestamp() < cutoff:
            self._daily_pnl_window.popleft()

    # ------------------------------------------------------------------ #
    # Metric properties                                                    #
    # ------------------------------------------------------------------ #

    @property
    def total_trades(self) -> int:
        return self._win_count + self._loss_count

    @property
    def win_rate(self) -> Optional[Decimal]:
        """Win rate in [0, 1], or None if no trades."""
        if self.total_trades == 0:
            return None
        return Decimal(str(self._win_count)) / Decimal(str(self.total_trades))

    @property
    def profit_factor(self) -> Optional[Decimal]:
        """Gross profit / gross loss.  None if no losing trades yet.

        > 1.0 = positive expectancy.
        """
        if self._gross_loss == Decimal("0"):
            if self._gross_profit > Decimal("0"):
                # All wins — return a large positive value
                return Decimal("999.99")
            return None
        return self._gross_profit / self._gross_loss

    @property
    def max_drawdown(self) -> Decimal:
        """Maximum drawdown fraction since inception (0–1)."""
        return self._max_drawdown

    @property
    def sharpe_ratio(self) -> Optional[Decimal]:
        """Annualised Sharpe ratio over the rolling window.

        Computed as: (mean_daily_return / std_daily_return) × sqrt(365)

        Returns None if fewer than 2 data points in the window.
        """
        window_pnls = [pnl for _, pnl in self._daily_pnl_window]
        n = len(window_pnls)
        if n < 2:
            return None
        if self._current_portfolio_value <= Decimal("0"):
            return None

        # Convert PnL to daily return fractions
        # Use a simple approximation: return_i = pnl_i / current_portfolio_value
        pv = self._current_portfolio_value
        returns = [pnl / pv for pnl in window_pnls]

        mean_r = sum(returns, Decimal("0")) / Decimal(str(n))

        # Population std dev
        variance = sum(
            (r - mean_r) ** 2 for r in returns
        ) / Decimal(str(n - 1))  # sample std dev
        if variance <= Decimal("0"):
            return None

        std_r_float = math.sqrt(float(variance))
        if std_r_float == 0.0 or not math.isfinite(std_r_float):
            return None

        mean_r_float = float(mean_r)
        if not math.isfinite(mean_r_float):
            return None

        sharpe_float = (mean_r_float / std_r_float) * math.sqrt(float(ANNUALISATION_FACTOR))
        if not math.isfinite(sharpe_float):
            return None

        return Decimal(str(round(sharpe_float, 4)))

    @property
    def total_pnl(self) -> Decimal:
        """Cumulative realized PnL since inception."""
        return self._total_pnl

    @property
    def peak_portfolio_value(self) -> Decimal:
        return self._peak_portfolio_value

    @property
    def current_portfolio_value(self) -> Decimal:
        return self._current_portfolio_value

    # ------------------------------------------------------------------ #
    # Snapshot                                                             #
    # ------------------------------------------------------------------ #

    def snapshot(self) -> CapitalMetricsSnapshot:
        """Return an immutable point-in-time snapshot."""
        return CapitalMetricsSnapshot(
            total_trades=self.total_trades,
            win_count=self._win_count,
            loss_count=self._loss_count,
            win_rate=self.win_rate,
            profit_factor=self.profit_factor,
            max_drawdown=self.max_drawdown,
            sharpe_ratio=self.sharpe_ratio,
            peak_portfolio_value=self.peak_portfolio_value,
            current_portfolio_value=self.current_portfolio_value,
            total_pnl=self.total_pnl,
            snapshot_at=datetime.now(timezone.utc),
        )

    def reset(self) -> None:
        """Reset all metrics (e.g. for a new trading session or test)."""
        self.__init__(  # type: ignore[misc]
            sharpe_window_days=self._sharpe_window_days,
            initial_capital=self._initial_capital,
        )
