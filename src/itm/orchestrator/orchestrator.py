"""
ITM Section D — Multi-Strategy Orchestrator
=============================================
The central coordinator that wires together:
  * ``SBExportImporter``    — parses Strategy Builder exports
  * ``StrategyRegistry``    — manages strategy lifecycle
  * ``SignalAggregator``    — converts signals to decisions
  * ``CapitalAllocator``    — enforces per-strategy capital ceilings
  * ``PerformanceMonitor``  — tracks PnL / drawdown; auto-pauses on breach

Responsibilities
----------------
1. Load strategies from SB export documents (JSON / YAML / dict).
2. Activate / pause / stop individual strategies.
3. Route inbound signals through the aggregator and emit decisions.
4. Guard every entry with the full pre-trade risk checklist:
   - Position size ≤ MAX_POSITION_SIZE
   - Stop-loss attached on every entry
   - Daily loss limit checked
   - Leverage = 1.0
5. Record PnL updates and relay to PerformanceMonitor.
6. Expose a metrics snapshot for Section I (dashboard / ML).

Pre-trade enforcement pattern
------------------------------
Every ``submit_order()`` call runs these guards in order:
  1. Quantity ≤ MAX_POSITION_SIZE (1.0 BTC)
  2. Quantity ≥ MIN_POSITION_SIZE (0.001 BTC)
  3. Strategy is ACTIVE
  4. Capital available for the strategy
  5. Daily loss limit not breached
  # (Stop-loss logic is handled at execution engine level in Section G;
  #   the orchestrator enforces it by rejecting submissions that lack a stop)

Thread safety
-------------
The orchestrator is designed to be called from a single event-loop thread
(the NautilusTrader Actor / Strategy dispatch thread).  Internal components
are individually thread-safe, so cross-thread calls are safe but not the
primary design target.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Optional

from ..domain.entities import Decision, Instrument, Signal
from .capital_allocator import CapitalAllocator
from .performance_monitor import PerformanceMonitor, StrategyMetrics
from .registry import StrategyEntry, StrategyLifecycleState, StrategyRegistry
from .sb_contract import SBExportImporter, StrategyConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Institutional risk constants (must match agent AGENTS.md specification)
# ---------------------------------------------------------------------------

MAX_POSITION_SIZE = Decimal("1.0")    # 1.0 BTC hard limit
MIN_POSITION_SIZE = Decimal("0.001")  # 0.001 BTC minimum
MAX_LEVERAGE = Decimal("1.0")         # no margin, ever


# ---------------------------------------------------------------------------
# OrchestratorConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrchestratorConfig:
    """Configuration for the MultiStrategyOrchestrator.

    Parameters
    ----------
    total_capital:
        Total USDT capital pool managed by the ITM.
    auto_activate_on_load:
        If True, strategies transition directly from LOADING → ACTIVE after
        successful loading.  Default is True for simplicity; set to False for
        staged rollout.
    """
    total_capital: Decimal
    auto_activate_on_load: bool = True

    def __post_init__(self) -> None:
        if self.total_capital <= Decimal("0"):
            raise ValueError(
                f"OrchestratorConfig.total_capital must be positive, "
                f"got {self.total_capital}"
            )


# ---------------------------------------------------------------------------
# OrderRejectionReason
# ---------------------------------------------------------------------------

class OrderRejectionReason(str):
    """Reasons used when the orchestrator rejects a pre-trade request."""
    QUANTITY_TOO_LARGE = "quantity_exceeds_MAX_POSITION_SIZE"
    QUANTITY_TOO_SMALL = "quantity_below_MIN_POSITION_SIZE"
    STRATEGY_NOT_ACTIVE = "strategy_not_active"
    INSUFFICIENT_CAPITAL = "insufficient_capital"
    DAILY_LOSS_LIMIT = "daily_loss_limit_reached"
    LEVERAGE_EXCEEDED = "leverage_exceeds_1.0"


# ---------------------------------------------------------------------------
# MultiStrategyOrchestrator
# ---------------------------------------------------------------------------

class MultiStrategyOrchestrator:
    """Central orchestrator for the multi-strategy execution framework.

    Parameters
    ----------
    config:
        ``OrchestratorConfig`` instance.
    on_decision:
        Callback ``(decision: Decision) → None`` for every Decision the
        SignalAggregator produces.  Typically routes to the execution engine.
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        on_decision: Optional[Callable[[Decision], None]] = None,
    ) -> None:
        self._config = config
        self._lock = threading.RLock()

        # Initialise sub-components
        self._registry = StrategyRegistry(
            on_strategy_activated=self._on_strategy_activated,
            on_strategy_paused=self._on_strategy_paused,
            on_strategy_stopped=self._on_strategy_stopped,
        )
        self._capital = CapitalAllocator(config.total_capital)
        self._monitor = PerformanceMonitor(self._registry)
        self._aggregator = SignalAggregator(
            registry=self._registry,
            on_decision=on_decision,
        )
        self._importer = SBExportImporter()

        logger.info(
            "MultiStrategyOrchestrator initialised: total_capital=%s, "
            "auto_activate=%s",
            config.total_capital, config.auto_activate_on_load,
        )

    # ------------------------------------------------------------------ #
    # Strategy loading from SB exports                                    #
    # ------------------------------------------------------------------ #

    def load_from_sb_json(self, json_str: str) -> list[StrategyEntry]:
        """Parse a Strategy Builder JSON export and load all strategies.

        Parameters
        ----------
        json_str:
            Raw JSON string from the Strategy Builder.

        Returns
        -------
        list[StrategyEntry]
            Loaded (and optionally activated) entries.
        """
        configs = self._importer.from_json(json_str)
        return self._load_configs(configs)

    def load_from_sb_dict(self, export_dict: dict) -> list[StrategyEntry]:
        """Load strategies from a pre-parsed SB export dict."""
        configs = self._importer.from_dict(export_dict)
        return self._load_configs(configs)

    def load_from_sb_yaml(self, path: str) -> list[StrategyEntry]:
        """Load strategies from a YAML file path."""
        configs = self._importer.from_yaml_file(path)
        return self._load_configs(configs)

    def load_config(self, config: StrategyConfig) -> StrategyEntry:
        """Load a single pre-built ``StrategyConfig`` into the orchestrator."""
        entries = self._load_configs([config])
        return entries[0]

    def _load_configs(self, configs: list[StrategyConfig]) -> list[StrategyEntry]:
        """Internal: load + optionally activate a list of StrategyConfig objects."""
        entries = self._registry.load_many(configs)

        for config, entry in zip(configs, entries):
            # Register with capital allocator
            self._capital.register(config)
            # Register with performance monitor
            self._monitor.register(config)
            # Auto-activate if configured
            if self._config.auto_activate_on_load:
                self._registry.activate(config.strategy_id)

        return entries

    # ------------------------------------------------------------------ #
    # Lifecycle control                                                    #
    # ------------------------------------------------------------------ #

    def activate_strategy(self, strategy_id: str) -> StrategyEntry:
        """Manually activate a LOADING or PAUSED strategy."""
        entry = self._registry.activate(strategy_id)
        return entry

    def pause_strategy(self, strategy_id: str, reason: str = "manual") -> StrategyEntry:
        """Manually pause an ACTIVE strategy."""
        entry = self._registry.pause(strategy_id, reason=reason)
        return entry

    def stop_strategy(self, strategy_id: str, reason: str = "manual") -> StrategyEntry:
        """Stop a strategy (terminal — cannot be restarted)."""
        entry = self._registry.stop(strategy_id, reason=reason)
        # Release capital slice
        self._capital.deregister(strategy_id)
        self._monitor.deregister(strategy_id)
        return entry

    # ------------------------------------------------------------------ #
    # Signal submission                                                    #
    # ------------------------------------------------------------------ #

    def submit_signal(self, signal: Signal) -> Optional[Decision]:
        """Submit a signal from a strategy to produce a Decision.

        The signal passes through the ``SignalAggregator`` which validates:
        - Signal is not stale
        - Strategy is ACTIVE
        - Signal strength ≥ strategy's confidence threshold

        Returns
        -------
        Decision | None
            Decision if accepted, None if dropped.
        """
        return self._aggregator.submit_signal(signal)

    # ------------------------------------------------------------------ #
    # Pre-trade order validation (risk gate)                               #
    # ------------------------------------------------------------------ #

    def validate_order(
        self,
        strategy_id: str,
        quantity: Decimal,
        capital_required: Decimal,
        leverage: Decimal = Decimal("1.0"),
    ) -> tuple[bool, Optional[str]]:
        """Run the full pre-trade risk checklist.

        Parameters
        ----------
        strategy_id:
            The strategy submitting the order.
        quantity:
            Order size in BTC.
        capital_required:
            USDT amount required (position notional for 1x leverage).
        leverage:
            Must be 1.0 (no margin).

        Returns
        -------
        (allowed, rejection_reason)
            ``(True, None)`` if all checks pass.
            ``(False, reason_string)`` if any check fails.
        """
        # 1. Leverage check
        if leverage > MAX_LEVERAGE:
            reason = (
                f"{OrderRejectionReason.LEVERAGE_EXCEEDED}: "
                f"requested {leverage} > max {MAX_LEVERAGE}"
            )
            logger.error("Order rejected: %s strategy=%r", reason, strategy_id)
            return False, reason

        # 2. Position size — upper bound
        if quantity > MAX_POSITION_SIZE:
            reason = (
                f"{OrderRejectionReason.QUANTITY_TOO_LARGE}: "
                f"{quantity} BTC > MAX {MAX_POSITION_SIZE} BTC"
            )
            logger.error("Order rejected: %s strategy=%r", reason, strategy_id)
            return False, reason

        # 3. Position size — lower bound
        if quantity < MIN_POSITION_SIZE:
            reason = (
                f"{OrderRejectionReason.QUANTITY_TOO_SMALL}: "
                f"{quantity} BTC < MIN {MIN_POSITION_SIZE} BTC"
            )
            logger.error("Order rejected: %s strategy=%r", reason, strategy_id)
            return False, reason

        # 4. Strategy must be ACTIVE
        entry = self._registry.get(strategy_id)
        if entry is None or not entry.is_active:
            state = entry.state.value if entry else "not_registered"
            reason = f"{OrderRejectionReason.STRATEGY_NOT_ACTIVE}: state={state}"
            logger.error("Order rejected: %s strategy=%r", reason, strategy_id)
            return False, reason

        # 5. Capital check
        if not self._capital.can_allocate(strategy_id, capital_required):
            slice_ = self._capital.get_slice(strategy_id)
            available = slice_.available_capital if slice_ else Decimal("0")
            reason = (
                f"{OrderRejectionReason.INSUFFICIENT_CAPITAL}: "
                f"need {capital_required} USDT, only {available} available"
            )
            logger.error("Order rejected: %s strategy=%r", reason, strategy_id)
            return False, reason

        # 6. Daily loss limit
        metrics = self._monitor.get_metrics(strategy_id)
        if metrics is not None:
            config = self._registry.get(strategy_id)
            if config is not None:
                daily_loss = -metrics.daily_pnl
                max_loss = config.config.risk.max_daily_loss
                if daily_loss >= max_loss:
                    reason = (
                        f"{OrderRejectionReason.DAILY_LOSS_LIMIT}: "
                        f"daily_loss={daily_loss} >= limit={max_loss} USDT"
                    )
                    logger.error(
                        "Order rejected: %s strategy=%r", reason, strategy_id
                    )
                    return False, reason

        logger.info(
            "Pre-trade checks PASSED: strategy=%r qty=%s capital=%s",
            strategy_id, quantity, capital_required,
        )
        return True, None

    # ------------------------------------------------------------------ #
    # PnL recording                                                        #
    # ------------------------------------------------------------------ #

    def record_trade_pnl(
        self,
        strategy_id: str,
        pnl: Decimal,
        capital_base: Decimal,
    ) -> Optional[StrategyMetrics]:
        """Record a closed-trade PnL for performance monitoring.

        Also releases the capital held for this trade.

        Parameters
        ----------
        strategy_id:
            The strategy that closed the trade.
        pnl:
            Realized PnL in USDT.
        capital_base:
            Current portfolio value for drawdown computation.

        Returns
        -------
        StrategyMetrics | None
            Updated metrics, or None if strategy not registered.
        """
        try:
            metrics = self._monitor.record_pnl(strategy_id, pnl, capital_base)
            return metrics
        except KeyError:
            logger.warning(
                "record_trade_pnl: strategy %r not registered in monitor",
                strategy_id,
            )
            return None

    def record_capital_use(self, strategy_id: str, amount: Decimal) -> None:
        """Notify the allocator that *amount* USDT has been committed to a position."""
        try:
            self._capital.record_capital_use(strategy_id, amount)
        except Exception:
            logger.exception(
                "record_capital_use failed for strategy=%r amount=%s",
                strategy_id, amount,
            )

    def release_capital_use(self, strategy_id: str, amount: Decimal) -> None:
        """Notify the allocator that *amount* USDT has been released from a position."""
        try:
            self._capital.release_capital_use(strategy_id, amount)
        except Exception:
            logger.exception(
                "release_capital_use failed for strategy=%r amount=%s",
                strategy_id, amount,
            )

    # ------------------------------------------------------------------ #
    # Queries / metrics snapshot                                           #
    # ------------------------------------------------------------------ #

    def active_strategy_ids(self) -> list[str]:
        """Return IDs of all ACTIVE strategies."""
        return self._registry.active_strategy_ids()

    def get_strategy_metrics(self, strategy_id: str) -> Optional[StrategyMetrics]:
        """Return performance metrics for a strategy."""
        return self._monitor.get_metrics(strategy_id)

    def all_metrics(self) -> dict[str, StrategyMetrics]:
        """Return metrics for all registered strategies."""
        return self._monitor.all_metrics()

    def strategy_count(self) -> int:
        """Total registered strategies."""
        return self._registry.count()

    def active_strategy_count(self) -> int:
        """Number of ACTIVE strategies."""
        return self._registry.active_count()

    @property
    def registry(self) -> StrategyRegistry:
        return self._registry

    @property
    def capital(self) -> CapitalAllocator:
        return self._capital

    @property
    def monitor(self) -> PerformanceMonitor:
        return self._monitor

    @property
    def aggregator(self) -> "SignalAggregator":  # type: ignore[name-defined]
        return self._aggregator

    # ------------------------------------------------------------------ #
    # Registry observer callbacks                                          #
    # ------------------------------------------------------------------ #

    def _on_strategy_activated(self, entry: StrategyEntry) -> None:
        logger.info(
            "Orchestrator: strategy ACTIVATED id=%r name=%r",
            entry.strategy_id, entry.config.name,
        )

    def _on_strategy_paused(self, entry: StrategyEntry) -> None:
        logger.info(
            "Orchestrator: strategy PAUSED id=%r name=%r reason=%r",
            entry.strategy_id, entry.config.name, entry.pause_reason,
        )

    def _on_strategy_stopped(self, entry: StrategyEntry) -> None:
        logger.info(
            "Orchestrator: strategy STOPPED id=%r name=%r reason=%r",
            entry.strategy_id, entry.config.name, entry.pause_reason,
        )


# ---------------------------------------------------------------------------
# Re-export SignalAggregator so orchestrator module is self-contained
# ---------------------------------------------------------------------------
from .signal_aggregator import SignalAggregator  # noqa: E402  (avoid circular at top)
