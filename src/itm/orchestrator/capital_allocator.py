"""
ITM Section D — Capital Allocator
===================================
Manages per-strategy capital slices from the total ITM capital pool.

Responsibilities
----------------
* Each strategy gets an ``allocated_capital`` slice determined by
  ``StrategyConfig.capital_allocation_pct * total_capital``.
* Hard ceiling: a strategy can never use more capital than its slice.
* Rebalancing: when a strategy is added or removed, the allocator
  recomputes all strategy slices from their allocation percentages.
* Thread-safe: all mutations are protected by a reentrant lock.

Capital model
-------------
``total_capital``        — total USDT available to the ITM.
``strategy_allocation``  — each strategy's slice (= total_capital × pct).
``in_use``               — capital currently locked in open positions for
                           a strategy (updated externally).
``available``            — strategy_allocation - in_use.

The allocator does NOT track open positions itself — that is owned by the
``ITMSystemState`` / ``CapitalState`` from the domain layer.  The caller
is responsible for calling ``record_capital_use()`` and
``release_capital_use()`` when positions open/close.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from .sb_contract import StrategyConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# StrategyCapitalSlice — per-strategy capital record
# ---------------------------------------------------------------------------

@dataclass
class StrategyCapitalSlice:
    """Capital slice assigned to one strategy.

    Attributes
    ----------
    strategy_id:         strategy identifier
    allocation_pct:      fraction of total capital (e.g. Decimal('0.5'))
    allocated_capital:   absolute USDT amount assigned to this strategy
    in_use:              capital currently committed to open positions
    updated_at:          last modification timestamp
    """
    strategy_id: str
    allocation_pct: Decimal
    allocated_capital: Decimal
    in_use: Decimal = field(default_factory=lambda: Decimal("0"))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def available_capital(self) -> Decimal:
        """Capital available for new positions (allocated - in_use)."""
        return max(Decimal("0"), self.allocated_capital - self.in_use)

    @property
    def utilization_pct(self) -> Decimal:
        """Fraction of allocated capital currently in use (0-1)."""
        if self.allocated_capital == Decimal("0"):
            return Decimal("0")
        return self.in_use / self.allocated_capital

    def __repr__(self) -> str:
        return (
            f"StrategyCapitalSlice(id={self.strategy_id!r}, "
            f"alloc={self.allocated_capital}, in_use={self.in_use}, "
            f"available={self.available_capital})"
        )


# ---------------------------------------------------------------------------
# CapitalAllocator
# ---------------------------------------------------------------------------

class CapitalAllocatorError(Exception):
    """Raised when a capital allocation operation violates constraints."""


class CapitalAllocator:
    """Manages per-strategy capital slices from the total ITM capital pool.

    Parameters
    ----------
    total_capital:
        Total USDT available to the ITM for trading.
    """

    def __init__(self, total_capital: Decimal) -> None:
        if total_capital <= Decimal("0"):
            raise CapitalAllocatorError(
                f"CapitalAllocator.total_capital must be positive, got {total_capital}"
            )
        self._lock = threading.RLock()
        self._total_capital: Decimal = total_capital
        self._slices: dict[str, StrategyCapitalSlice] = {}  # strategy_id → slice

    # ------------------------------------------------------------------ #
    # Registration & rebalancing                                          #
    # ------------------------------------------------------------------ #

    def register(self, config: StrategyConfig) -> StrategyCapitalSlice:
        """Register a strategy and compute its capital slice.

        Parameters
        ----------
        config:
            The strategy's ``StrategyConfig`` (must include
            ``capital_allocation_pct``).

        Returns
        -------
        StrategyCapitalSlice
            The newly created capital slice.

        Raises
        ------
        CapitalAllocatorError
            If the strategy is already registered.
        """
        with self._lock:
            if config.strategy_id in self._slices:
                raise CapitalAllocatorError(
                    f"Strategy {config.strategy_id!r} is already registered "
                    f"in the capital allocator"
                )
            allocated = self._total_capital * config.capital_allocation_pct
            slice_ = StrategyCapitalSlice(
                strategy_id=config.strategy_id,
                allocation_pct=config.capital_allocation_pct,
                allocated_capital=allocated,
            )
            self._slices[config.strategy_id] = slice_

            logger.info(
                "Capital allocated: strategy=%r pct=%.4f amount=%s total=%s",
                config.strategy_id, float(config.capital_allocation_pct),
                allocated, self._total_capital,
            )
            self._check_total_allocation()
            return slice_

    def deregister(self, strategy_id: str) -> None:
        """Remove a strategy's capital slice and rebalance remaining.

        Capital currently in use by this strategy is returned to the pool
        (the caller must ensure the position is actually closed first).

        Parameters
        ----------
        strategy_id:
            The strategy to remove.

        Raises
        ------
        CapitalAllocatorError
            If the strategy is not registered.
        """
        with self._lock:
            slice_ = self._require(strategy_id)
            if slice_.in_use > Decimal("0"):
                logger.warning(
                    "Deregistering strategy %r with in_use=%s — "
                    "capital may not be fully released",
                    strategy_id, slice_.in_use,
                )
            del self._slices[strategy_id]
            logger.info(
                "Capital slice deregistered: strategy=%r", strategy_id
            )

    def rebalance(self, new_total_capital: Optional[Decimal] = None) -> None:
        """Recompute all slices from their allocation percentages.

        Called when a new strategy is added, one is removed, or the total
        capital changes (e.g. after a deposit / withdrawal).

        Parameters
        ----------
        new_total_capital:
            If provided, update ``total_capital`` before rebalancing.
        """
        with self._lock:
            if new_total_capital is not None:
                if new_total_capital <= Decimal("0"):
                    raise CapitalAllocatorError(
                        f"new_total_capital must be positive, got {new_total_capital}"
                    )
                self._total_capital = new_total_capital

            now = datetime.now(timezone.utc)
            for s in self._slices.values():
                new_allocated = self._total_capital * s.allocation_pct
                s.allocated_capital = new_allocated
                s.updated_at = now
                logger.debug(
                    "Rebalanced strategy=%r new_allocated=%s",
                    s.strategy_id, new_allocated,
                )

    # ------------------------------------------------------------------ #
    # Capital use tracking                                                 #
    # ------------------------------------------------------------------ #

    def record_capital_use(self, strategy_id: str, amount: Decimal) -> None:
        """Record that a strategy has committed *amount* USDT to a position.

        Parameters
        ----------
        strategy_id:
            The strategy opening the position.
        amount:
            USDT amount to commit.

        Raises
        ------
        CapitalAllocatorError
            If this would exceed the strategy's allocated slice.
        """
        with self._lock:
            slice_ = self._require(strategy_id)
            if amount > slice_.available_capital:
                raise CapitalAllocatorError(
                    f"Strategy {strategy_id!r} cannot commit {amount} USDT: "
                    f"only {slice_.available_capital} available "
                    f"(allocated={slice_.allocated_capital}, in_use={slice_.in_use})"
                )
            slice_.in_use += amount
            slice_.updated_at = datetime.now(timezone.utc)
            logger.info(
                "Capital committed: strategy=%r amount=%s in_use=%s available=%s",
                strategy_id, amount, slice_.in_use, slice_.available_capital,
            )

    def release_capital_use(self, strategy_id: str, amount: Decimal) -> None:
        """Release capital previously committed by a strategy (position closed).

        Parameters
        ----------
        strategy_id:
            The strategy releasing capital.
        amount:
            USDT amount to release.
        """
        with self._lock:
            slice_ = self._require(strategy_id)
            release = min(amount, slice_.in_use)
            slice_.in_use = max(Decimal("0"), slice_.in_use - release)
            slice_.updated_at = datetime.now(timezone.utc)
            logger.info(
                "Capital released: strategy=%r amount=%s in_use=%s available=%s",
                strategy_id, release, slice_.in_use, slice_.available_capital,
            )

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    def get_slice(self, strategy_id: str) -> Optional[StrategyCapitalSlice]:
        """Return the capital slice for *strategy_id*, or None if unregistered."""
        with self._lock:
            return self._slices.get(strategy_id)

    def can_allocate(self, strategy_id: str, amount: Decimal) -> bool:
        """Return True if the strategy can commit *amount* without exceeding its slice."""
        with self._lock:
            slice_ = self._slices.get(strategy_id)
            if slice_ is None:
                return False
            return amount <= slice_.available_capital

    @property
    def total_capital(self) -> Decimal:
        with self._lock:
            return self._total_capital

    @property
    def total_allocated(self) -> Decimal:
        """Sum of allocated_capital across all registered strategies."""
        with self._lock:
            return sum(
                (s.allocated_capital for s in self._slices.values()),
                Decimal("0"),
            )

    @property
    def total_in_use(self) -> Decimal:
        """Sum of in_use across all registered strategies."""
        with self._lock:
            return sum(
                (s.in_use for s in self._slices.values()), Decimal("0")
            )

    def snapshot(self) -> dict[str, StrategyCapitalSlice]:
        """Return a shallow copy of the current slices dict."""
        with self._lock:
            return dict(self._slices)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _require(self, strategy_id: str) -> StrategyCapitalSlice:
        slice_ = self._slices.get(strategy_id)
        if slice_ is None:
            raise CapitalAllocatorError(
                f"Strategy {strategy_id!r} is not registered in the capital allocator"
            )
        return slice_

    def _check_total_allocation(self) -> None:
        """Warn (don't raise) if total allocation exceeds total capital."""
        total_alloc = sum(
            (s.allocated_capital for s in self._slices.values()), Decimal("0")
        )
        if total_alloc > self._total_capital:
            logger.warning(
                "Total allocated capital %s exceeds total_capital %s — "
                "consider rebalancing",
                total_alloc, self._total_capital,
            )
