"""
ITM Section D — Signal Aggregator
===================================
Receives ``Signal`` objects from active strategies, applies confidence weighting,
and produces ``Decision`` objects for the execution engine.

Aggregation modes
-----------------
MVP mode (``AggregationMode.PASSTHROUGH``)
    Direct signal → decision passthrough.  No cross-strategy weighting.
    Each signal from an active strategy produces exactly one Decision.
    The Decision action mirrors the Signal direction; confidence is taken
    directly from Signal.strength.

Weighted mode (``AggregationMode.CONFIDENCE_WEIGHTED``) — future extension
    Signals from multiple strategies are pooled per instrument and combined
    using their confidence scores.  This mode is **not** activated in the MVP
    but the interface is reserved so Section I (ML ensemble) can plug in.

Design
------
* Thread-safe: uses a reentrant lock for the internal pending-signal buffer.
* Signals that do not pass the per-strategy ``signal_confidence_threshold``
  (stored in ``StrategyConfig``) are **dropped** before Decision creation.
* Signals from PAUSED or STOPPED strategies are ignored.
* Every accepted signal produces a logged Decision.
* The ``on_decision`` callback is called synchronously in the caller's thread
  (the orchestrator routes it to the execution engine).

Signal → Decision direction mapping
-------------------------------------
+---------------------+------------------+
| SignalDirection     | DecisionAction   |
+=====================+==================+
| LONG                | ENTER_LONG       |
| SHORT               | ENTER_SHORT      |
| EXIT (from LONG)    | EXIT_LONG        |
| EXIT (from SHORT)   | EXIT_SHORT       |
| NEUTRAL             | HOLD             |
+---------------------+------------------+

EXIT direction ambiguity: without position context available in the aggregator,
EXIT signals default to ``EXIT_LONG``.  The execution engine is responsible for
resolving the actual direction from position state and may override the action.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Callable, Optional

from ..domain.entities import (
    Decision,
    DecisionAction,
    Signal,
    SignalDirection,
)
from .registry import StrategyEntry, StrategyRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Aggregation mode
# ---------------------------------------------------------------------------

class AggregationMode(str, Enum):
    """Controls how multiple signals are combined into a Decision."""
    PASSTHROUGH = "passthrough"               # MVP: 1 signal → 1 Decision
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Future: multi-strategy pooling


# ---------------------------------------------------------------------------
# Signal → Decision direction mapping
# ---------------------------------------------------------------------------

_DIRECTION_TO_ACTION: dict[SignalDirection, DecisionAction] = {
    SignalDirection.LONG: DecisionAction.ENTER_LONG,
    SignalDirection.SHORT: DecisionAction.ENTER_SHORT,
    SignalDirection.EXIT: DecisionAction.EXIT_LONG,   # resolved by exec engine
    SignalDirection.NEUTRAL: DecisionAction.HOLD,
}


# ---------------------------------------------------------------------------
# AggregationStats — metrics for monitoring
# ---------------------------------------------------------------------------

@dataclass
class AggregationStats:
    """Runtime statistics for the SignalAggregator."""
    signals_received: int = 0
    signals_dropped_stale: int = 0
    signals_dropped_low_confidence: int = 0
    signals_dropped_inactive_strategy: int = 0
    decisions_produced: int = 0
    decisions_rejected: int = 0   # HOLD / no-op decisions

    def __repr__(self) -> str:
        return (
            f"AggregationStats("
            f"received={self.signals_received}, "
            f"dropped_stale={self.signals_dropped_stale}, "
            f"dropped_low_conf={self.signals_dropped_low_confidence}, "
            f"dropped_inactive={self.signals_dropped_inactive_strategy}, "
            f"decisions={self.decisions_produced})"
        )


# ---------------------------------------------------------------------------
# SignalAggregator
# ---------------------------------------------------------------------------

class SignalAggregator:
    """Aggregates signals from active strategies into Decisions.

    Parameters
    ----------
    registry:
        The ``StrategyRegistry`` used to verify that the signal's source
        strategy is ACTIVE before accepting the signal.
    on_decision:
        Callback ``(decision: Decision) → None`` invoked for every Decision
        produced.  Runs synchronously in the submitter's thread — keep it fast
        or delegate to a queue.
    mode:
        ``AggregationMode.PASSTHROUGH`` (default, MVP) — one signal → one
        Decision.  ``CONFIDENCE_WEIGHTED`` is reserved for future use.
    """

    def __init__(
        self,
        registry: StrategyRegistry,
        on_decision: Optional[Callable[[Decision], None]] = None,
        mode: AggregationMode = AggregationMode.PASSTHROUGH,
    ) -> None:
        self._registry = registry
        self._on_decision = on_decision
        self._mode = mode
        self._lock = threading.RLock()
        self._stats = AggregationStats()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def submit_signal(self, signal: Signal) -> Optional[Decision]:
        """Accept a Signal and produce a Decision if it passes all filters.

        Parameters
        ----------
        signal:
            Typed ``Signal`` domain object from a strategy.

        Returns
        -------
        Decision | None
            The produced Decision, or None if the signal was dropped.
        """
        with self._lock:
            self._stats.signals_received += 1

        # 1. Stale signal check
        if signal.is_expired:
            logger.warning(
                "Signal %r from strategy %r is stale (expired=%s); dropping",
                signal.signal_id, signal.source_strategy,
                signal.expiry.isoformat() if signal.expiry else "N/A",
            )
            with self._lock:
                self._stats.signals_dropped_stale += 1
            return None

        # 2. Active strategy check
        entry = self._registry.get(signal.source_strategy)
        if entry is None or not entry.is_active:
            state_str = entry.state.value if entry else "not_registered"
            logger.debug(
                "Signal %r from strategy %r ignored: strategy is %s",
                signal.signal_id, signal.source_strategy, state_str,
            )
            with self._lock:
                self._stats.signals_dropped_inactive_strategy += 1
            return None

        # 3. Confidence threshold check (per-strategy)
        threshold = entry.config.signal_confidence_threshold
        if signal.strength < threshold:
            logger.debug(
                "Signal %r from %r dropped: strength %.4f < threshold %.4f",
                signal.signal_id, signal.source_strategy,
                float(signal.strength), float(threshold),
            )
            with self._lock:
                self._stats.signals_dropped_low_confidence += 1
            return None

        # 4. Produce Decision
        if self._mode == AggregationMode.PASSTHROUGH:
            decision = self._passthrough_decision(signal, entry)
        else:
            # CONFIDENCE_WEIGHTED reserved for Section I (ML ensemble)
            decision = self._passthrough_decision(signal, entry)

        with self._lock:
            self._stats.decisions_produced += 1
            if decision.action in (DecisionAction.HOLD, DecisionAction.REJECT):
                self._stats.decisions_rejected += 1

        logger.info(
            "Decision produced: id=%r action=%s confidence=%.4f "
            "from_signal=%r strategy=%r",
            decision.decision_id, decision.action.value,
            float(decision.confidence), signal.signal_id,
            signal.source_strategy,
        )

        if self._on_decision is not None:
            try:
                self._on_decision(decision)
            except Exception:
                logger.exception(
                    "on_decision callback raised for decision %r", decision.decision_id
                )

        return decision

    @property
    def stats(self) -> AggregationStats:
        """Return a snapshot of aggregation statistics."""
        with self._lock:
            return AggregationStats(
                signals_received=self._stats.signals_received,
                signals_dropped_stale=self._stats.signals_dropped_stale,
                signals_dropped_low_confidence=self._stats.signals_dropped_low_confidence,
                signals_dropped_inactive_strategy=self._stats.signals_dropped_inactive_strategy,
                decisions_produced=self._stats.decisions_produced,
                decisions_rejected=self._stats.decisions_rejected,
            )

    @property
    def mode(self) -> AggregationMode:
        return self._mode

    def reset_stats(self) -> None:
        """Reset all counters to zero (useful in tests)."""
        with self._lock:
            self._stats = AggregationStats()

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _passthrough_decision(
        self, signal: Signal, entry: StrategyEntry
    ) -> Decision:
        """One signal → one Decision with direct direction mapping."""
        action = _DIRECTION_TO_ACTION.get(signal.direction, DecisionAction.HOLD)

        return Decision(
            action=action,
            confidence=signal.strength,
            contributing_signals=(signal,),
            risk_gated=False,  # risk gate is applied later by the execution engine
            instrument=signal.instrument,
            reason=(
                f"Passthrough from strategy {signal.source_strategy!r} "
                f"(strength={signal.strength})"
            ),
        )
