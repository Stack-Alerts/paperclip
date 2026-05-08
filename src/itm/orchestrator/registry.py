"""
ITM Section D — Strategy Registry
===================================
Manages the lifecycle of all active strategy instances: loading, activation,
pausing, stopping, and auto-pausing on risk threshold breach.

Strategy lifecycle
------------------
``loading`` → ``active`` → ``paused`` → ``stopped``
               ↑_________↙                ↑
                                     (terminal — no resumption)

Auto-pause path (triggered by PerformanceMonitor):
    ``active`` → ``paused``  (automatic, due to drawdown or daily-loss breach)

The registry is the authoritative source of truth for which strategies are
running and their current lifecycle state.  It does NOT own capital or signals —
those are delegated to ``CapitalAllocator`` and ``SignalAggregator`` respectively.

Thread safety
-------------
All public methods are protected by a single re-entrant lock so the registry
can be safely called from the orchestrator's main thread and any callback.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Callable, Iterator, Optional

from .sb_contract import StrategyConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifecycle state
# ---------------------------------------------------------------------------

class StrategyLifecycleState(str, Enum):
    """Lifecycle state for a registered strategy instance."""
    LOADING = "loading"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class StrategyRegistryError(Exception):
    """Raised when a registry operation violates lifecycle constraints."""


# ---------------------------------------------------------------------------
# StrategyEntry — the registry's per-strategy record
# ---------------------------------------------------------------------------

@dataclass
class StrategyEntry:
    """Internal record held by the ``StrategyRegistry`` for each strategy.

    Attributes
    ----------
    config:         immutable StrategyConfig from the SB export importer
    state:          current lifecycle state
    entry_id:       unique registration ID (different from config.strategy_id)
    registered_at:  UTC timestamp of initial registration
    activated_at:   UTC timestamp of most recent activation (None if never active)
    paused_at:      UTC timestamp of most recent pause (None if never paused)
    stopped_at:     UTC timestamp of stop (None if not stopped)
    pause_reason:   human-readable reason for the last pause
    tags:           mutable tag set for dynamic labelling
    """
    config: StrategyConfig
    state: StrategyLifecycleState = StrategyLifecycleState.LOADING
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    pause_reason: Optional[str] = None

    @property
    def strategy_id(self) -> str:
        return self.config.strategy_id

    @property
    def is_active(self) -> bool:
        return self.state == StrategyLifecycleState.ACTIVE

    @property
    def is_paused(self) -> bool:
        return self.state == StrategyLifecycleState.PAUSED

    @property
    def is_stopped(self) -> bool:
        return self.state == StrategyLifecycleState.STOPPED

    def __repr__(self) -> str:
        return (
            f"StrategyEntry(id={self.strategy_id!r}, "
            f"state={self.state.value}, "
            f"name={self.config.name!r})"
        )


# ---------------------------------------------------------------------------
# StrategyRegistry
# ---------------------------------------------------------------------------

class StrategyRegistry:
    """Thread-safe registry that manages strategy lifecycle.

    Responsibilities
    ----------------
    * Load strategy configs into the registry (LOADING state).
    * Activate / pause / stop individual strategies.
    * Provide queries: active strategies, all strategies, by-id lookup.
    * Emit structured lifecycle log events on every transition.
    * Fire optional observer callbacks for external components
      (e.g. CapitalAllocator rebalancing on start/stop).

    Parameters
    ----------
    on_strategy_activated:  optional callback ``(entry: StrategyEntry) → None``
    on_strategy_paused:     optional callback ``(entry: StrategyEntry) → None``
    on_strategy_stopped:    optional callback ``(entry: StrategyEntry) → None``
    """

    def __init__(
        self,
        on_strategy_activated: Optional[Callable[[StrategyEntry], None]] = None,
        on_strategy_paused: Optional[Callable[[StrategyEntry], None]] = None,
        on_strategy_stopped: Optional[Callable[[StrategyEntry], None]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._strategies: dict[str, StrategyEntry] = {}  # strategy_id → entry

        # Observer callbacks
        self._on_activated = on_strategy_activated
        self._on_paused = on_strategy_paused
        self._on_stopped = on_strategy_stopped

    # ------------------------------------------------------------------ #
    # Registration                                                         #
    # ------------------------------------------------------------------ #

    def load(self, config: StrategyConfig) -> StrategyEntry:
        """Register a new strategy in LOADING state.

        Parameters
        ----------
        config:
            Validated ``StrategyConfig`` from the SB importer.

        Returns
        -------
        StrategyEntry
            The newly created entry in LOADING state.

        Raises
        ------
        StrategyRegistryError
            If a strategy with the same ``strategy_id`` is already registered
            and not in STOPPED state.
        """
        with self._lock:
            existing = self._strategies.get(config.strategy_id)
            if existing is not None and not existing.is_stopped:
                raise StrategyRegistryError(
                    f"Strategy {config.strategy_id!r} is already registered "
                    f"(state={existing.state.value}). "
                    f"Stop it first before reloading."
                )

            entry = StrategyEntry(config=config)
            self._strategies[config.strategy_id] = entry
            logger.info(
                "Strategy loaded: id=%r name=%r instrument=%r alloc_pct=%.4f",
                config.strategy_id, config.name,
                config.instrument.symbol, float(config.capital_allocation_pct),
            )
            return entry

    def load_many(self, configs: list[StrategyConfig]) -> list[StrategyEntry]:
        """Batch-load multiple strategies.

        Parameters
        ----------
        configs:
            List of ``StrategyConfig`` objects (e.g. from SBExportImporter).

        Returns
        -------
        list[StrategyEntry]
            Entries in the same order as *configs*.
        """
        return [self.load(c) for c in configs]

    # ------------------------------------------------------------------ #
    # Lifecycle transitions                                                #
    # ------------------------------------------------------------------ #

    def activate(self, strategy_id: str) -> StrategyEntry:
        """Transition a strategy from LOADING or PAUSED to ACTIVE.

        Parameters
        ----------
        strategy_id:
            The strategy to activate.

        Returns
        -------
        StrategyEntry
            The updated entry.

        Raises
        ------
        StrategyRegistryError
            If the strategy is not found, is STOPPED, or is already ACTIVE.
        """
        with self._lock:
            entry = self._require(strategy_id)
            if entry.is_stopped:
                raise StrategyRegistryError(
                    f"Cannot activate stopped strategy {strategy_id!r}"
                )
            if entry.is_active:
                logger.warning(
                    "Strategy %r is already ACTIVE; ignoring activate()", strategy_id
                )
                return entry

            now = datetime.now(timezone.utc)
            entry.state = StrategyLifecycleState.ACTIVE
            entry.activated_at = now
            entry.pause_reason = None
            logger.info(
                "Strategy activated: id=%r name=%r at=%s",
                strategy_id, entry.config.name, now.isoformat(),
            )

        if self._on_activated is not None:
            try:
                self._on_activated(entry)
            except Exception:
                logger.exception(
                    "on_strategy_activated callback raised for %r", strategy_id
                )
        return entry

    def pause(self, strategy_id: str, reason: str = "manual") -> StrategyEntry:
        """Transition an ACTIVE strategy to PAUSED.

        Parameters
        ----------
        strategy_id:
            The strategy to pause.
        reason:
            Human-readable reason (used in logs and StrategyEntry.pause_reason).

        Returns
        -------
        StrategyEntry

        Raises
        ------
        StrategyRegistryError
            If the strategy is not found, STOPPED, or already PAUSED.
        """
        with self._lock:
            entry = self._require(strategy_id)
            if entry.is_stopped:
                raise StrategyRegistryError(
                    f"Cannot pause stopped strategy {strategy_id!r}"
                )
            if entry.is_paused:
                logger.warning(
                    "Strategy %r is already PAUSED (reason=%r); ignoring pause()",
                    strategy_id, entry.pause_reason,
                )
                return entry

            now = datetime.now(timezone.utc)
            entry.state = StrategyLifecycleState.PAUSED
            entry.paused_at = now
            entry.pause_reason = reason
            logger.info(
                "Strategy paused: id=%r name=%r reason=%r at=%s",
                strategy_id, entry.config.name, reason, now.isoformat(),
            )

        if self._on_paused is not None:
            try:
                self._on_paused(entry)
            except Exception:
                logger.exception(
                    "on_strategy_paused callback raised for %r", strategy_id
                )
        return entry

    def auto_pause(self, strategy_id: str, reason: str) -> StrategyEntry:
        """Risk-triggered auto-pause; same as pause() but logged differently.

        Designed to be called from ``PerformanceMonitor`` when a drawdown or
        daily-loss threshold is breached.
        """
        logger.warning(
            "AUTO-PAUSE triggered for strategy %r: %s", strategy_id, reason
        )
        return self.pause(strategy_id, reason=f"auto-pause: {reason}")

    def stop(self, strategy_id: str, reason: str = "manual") -> StrategyEntry:
        """Transition any non-STOPPED strategy to STOPPED (terminal state).

        Parameters
        ----------
        strategy_id:
            The strategy to stop.
        reason:
            Human-readable reason.

        Returns
        -------
        StrategyEntry

        Raises
        ------
        StrategyRegistryError
            If the strategy is not found or is already STOPPED.
        """
        with self._lock:
            entry = self._require(strategy_id)
            if entry.is_stopped:
                logger.warning(
                    "Strategy %r is already STOPPED; ignoring stop()", strategy_id
                )
                return entry

            now = datetime.now(timezone.utc)
            entry.state = StrategyLifecycleState.STOPPED
            entry.stopped_at = now
            entry.pause_reason = reason
            logger.info(
                "Strategy stopped: id=%r name=%r reason=%r at=%s",
                strategy_id, entry.config.name, reason, now.isoformat(),
            )

        if self._on_stopped is not None:
            try:
                self._on_stopped(entry)
            except Exception:
                logger.exception(
                    "on_strategy_stopped callback raised for %r", strategy_id
                )
        return entry

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    def get(self, strategy_id: str) -> Optional[StrategyEntry]:
        """Return the entry for *strategy_id*, or None if not registered."""
        with self._lock:
            return self._strategies.get(strategy_id)

    def active_entries(self) -> list[StrategyEntry]:
        """Return all entries currently in ACTIVE state."""
        with self._lock:
            return [e for e in self._strategies.values() if e.is_active]

    def all_entries(self) -> list[StrategyEntry]:
        """Return all registered entries regardless of state."""
        with self._lock:
            return list(self._strategies.values())

    def active_strategy_ids(self) -> list[str]:
        """Return strategy IDs for all ACTIVE strategies."""
        return [e.strategy_id for e in self.active_entries()]

    def count(self) -> int:
        """Return the total number of registered strategies."""
        with self._lock:
            return len(self._strategies)

    def active_count(self) -> int:
        """Return the number of ACTIVE strategies."""
        with self._lock:
            return sum(1 for e in self._strategies.values() if e.is_active)

    def __iter__(self) -> Iterator[StrategyEntry]:
        """Iterate over all registered entries (snapshot; safe under concurrency)."""
        with self._lock:
            entries = list(self._strategies.values())
        return iter(entries)

    def __len__(self) -> int:
        return self.count()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _require(self, strategy_id: str) -> StrategyEntry:
        """Return the entry for *strategy_id* or raise StrategyRegistryError."""
        entry = self._strategies.get(strategy_id)
        if entry is None:
            raise StrategyRegistryError(
                f"Strategy {strategy_id!r} is not registered in this registry"
            )
        return entry
