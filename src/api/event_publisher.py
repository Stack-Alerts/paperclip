"""
EventPublisher — Additive ITM Event Bridge
==========================================
Thin Redis pub/sub layer injected at ITM callback registration sites.

Each typed method is a callback stub.  Register these alongside (not instead
of) existing ITM callbacks — no ITM source files are modified.

Redis channels:
    itm:cycle       — OHLCVBar closed-bar events (timing / phase progression)
    itm:capital     — CapitalStateChanged events
    itm:positions   — position open/update/close (ExecutionEngine post-trade)
    itm:decisions   — TradeDecision events (Decision objects)
    itm:signals     — AggregatedSignal events
    itm:alerts      — AlertRaised events (defined in BTE-API-EVENT-001)
    itm:strategies  — strategy lifecycle: activated / paused / stopped

Injection pattern (wire in bootstrap — never inside ITM modules):

    publisher = EventPublisher(make_sync_client())

    # bar-close cycle events
    bar_builder.subscribe_closed(publisher.on_bar_closed)

    # strategy lifecycle — all three states share one callback
    registry = StrategyRegistry(
        on_strategy_activated=publisher.on_strategy_changed,
        on_strategy_paused=publisher.on_strategy_changed,
        on_strategy_stopped=publisher.on_strategy_changed,
    )

    # decisions — chain with existing handler when one exists
    def _on_decision(d: Decision) -> None:
        existing_handler(d)            # existing logic unchanged
        publisher.on_decision_made(d)  # additive

    orchestrator = MultiStrategyOrchestrator(
        config=orch_config,
        on_decision=_on_decision,
    )

    # position / trade events
    engine = ExecutionEngine(
        ...,
        on_post_trade=publisher.on_position_updated,
    )

RTM: BTE-API-WS-002
Test: BTE-TC-API-002
"""

from __future__ import annotations

import dataclasses
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Channel constants
# ---------------------------------------------------------------------------

CH_CYCLE = "itm:cycle"
CH_CAPITAL = "itm:capital"
CH_POSITIONS = "itm:positions"
CH_DECISIONS = "itm:decisions"
CH_SIGNALS = "itm:signals"
CH_ALERTS = "itm:alerts"
CH_STRATEGIES = "itm:strategies"

CHANNELS: tuple[str, ...] = (
    CH_CYCLE,
    CH_CAPITAL,
    CH_POSITIONS,
    CH_DECISIONS,
    CH_SIGNALS,
    CH_ALERTS,
    CH_STRATEGIES,
)

# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _default_serializer(obj: Any) -> str:
    """JSON fallback: coerce Decimal, datetime, Enum, and unknowns to str."""
    return str(obj)


def _to_dict(event: Any) -> dict:
    """Convert an ITM event/entity to a plain serialisable dict.

    Priority:
    1. dict — returned as-is.
    2. dataclass (frozen or mutable) — converted recursively via
       dataclasses.asdict() so nested dataclasses collapse correctly.
    3. generic object — vars() fallback.
    4. scalar fallback — {"value": str(event)}.
    """
    if isinstance(event, dict):
        return event
    if dataclasses.is_dataclass(event) and not isinstance(event, type):
        try:
            return dataclasses.asdict(event)
        except Exception:
            logger.debug(
                "_to_dict: dataclasses.asdict failed for %r, falling back to vars()",
                type(event).__name__,
            )
    try:
        return vars(event)
    except TypeError:
        return {"value": str(event)}


# ---------------------------------------------------------------------------
# EventPublisher
# ---------------------------------------------------------------------------


class EventPublisher:
    """Thin Redis pub/sub bridge injected at ITM callback registration sites.

    This class adds zero business logic.  Every public method serialises its
    argument to JSON and publishes it to the corresponding Redis channel.
    Redis errors are caught and logged so they never interrupt the ITM loop.

    Parameters
    ----------
    redis_client:
        A synchronous ``redis.Redis`` instance (or compatible stub).
        Must expose ``.publish(channel: str, message: str) -> int``.
    """

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    # ------------------------------------------------------------------ #
    # Core                                                                 #
    # ------------------------------------------------------------------ #

    def publish(self, channel: str, event: dict) -> None:
        """Serialise *event* to JSON and publish on *channel*.

        Errors from Redis or JSON encoding are caught and logged so they
        never propagate to callers and never interrupt the ITM callback chain.

        Parameters
        ----------
        channel:
            Redis pub/sub channel name (one of the ``CH_*`` constants).
        event:
            Plain dict to serialise.  Decimal, datetime, Enum, and other
            non-JSON-serialisable values are coerced to str via
            ``_default_serializer``.
        """
        try:
            payload = json.dumps(event, default=_default_serializer)
            self._redis.publish(channel, payload)
        except Exception:
            logger.exception("EventPublisher.publish failed channel=%r", channel)

    # ------------------------------------------------------------------ #
    # Typed callbacks — register at ITM callback registration time        #
    # ------------------------------------------------------------------ #

    def on_bar_closed(self, bar: Any) -> None:
        """Callback for ``RealtimeBarBuilder.subscribe_closed`` → itm:cycle."""
        self.publish(CH_CYCLE, _to_dict(bar))

    def on_capital_changed(self, event: Any) -> None:
        """Publish ``CapitalStateChanged`` events → itm:capital."""
        self.publish(CH_CAPITAL, _to_dict(event))

    def on_position_updated(self, event: Any) -> None:
        """Callback for ``ExecutionEngine(on_post_trade=…)`` → itm:positions."""
        self.publish(CH_POSITIONS, _to_dict(event))

    def on_decision_made(self, decision: Any) -> None:
        """Callback for ``MultiStrategyOrchestrator(on_decision=…)`` → itm:decisions."""
        self.publish(CH_DECISIONS, _to_dict(decision))

    def on_signal_received(self, signal: Any) -> None:
        """Publish ``AggregatedSignal`` events → itm:signals."""
        self.publish(CH_SIGNALS, _to_dict(signal))

    def on_alert_raised(self, alert: Any) -> None:
        """Publish ``AlertRaised`` events → itm:alerts.

        ``AlertRaised`` is defined in BTE-API-EVENT-001.  Until that event
        ships, pass ``RiskLimitBreached`` objects to this callback as a
        drop-in substitute.
        """
        self.publish(CH_ALERTS, _to_dict(alert))

    def on_strategy_changed(self, entry: Any) -> None:
        """Callback for ``StrategyRegistry`` lifecycle events → itm:strategies.

        Register as all three lifecycle hooks::

            StrategyRegistry(
                on_strategy_activated=publisher.on_strategy_changed,
                on_strategy_paused=publisher.on_strategy_changed,
                on_strategy_stopped=publisher.on_strategy_changed,
            )
        """
        self.publish(CH_STRATEGIES, _to_dict(entry))

    def on_phase_started(self, event: Any) -> None:
        """Callback for ``PhaseStarted`` events → itm:cycle.

        Emit at the start of each of the 11 ITM phase boundaries so the B1
        cycle monitor can show per-phase timing::

            publisher.on_phase_started(PhaseStarted(
                phase_name="risk_gate",
                phase_index=4,
                cycle_id=cycle_id,
                strategy_id=strategy_id,
            ))
        """
        self.publish(CH_CYCLE, _to_dict(event))

    def on_phase_completed(self, event: Any) -> None:
        """Callback for ``PhaseCompleted`` events → itm:cycle.

        Emit at the end of each of the 11 ITM phase boundaries with the
        measured ``duration_ms`` and ``outcome``::

            publisher.on_phase_completed(PhaseCompleted(
                phase_name="risk_gate",
                phase_index=4,
                cycle_id=cycle_id,
                strategy_id=strategy_id,
                duration_ms=1.23,
                outcome="success",
            ))
        """
        self.publish(CH_CYCLE, _to_dict(event))
