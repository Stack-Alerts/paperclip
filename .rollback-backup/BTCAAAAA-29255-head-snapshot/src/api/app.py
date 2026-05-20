"""
BTC Trade Engine FastAPI Bridge
================================
13 REST endpoints + 7 WebSocket domains.

P1 (read-only, 10 endpoints):
  GET  /health, /state/snapshot, /strategies, /strategies/{id},
       /positions, /positions/{id}, /capital,
       /decisions/recent, /signals/recent, /alerts/active

P2 (write + lifecycle control, 3 endpoints):
  POST /strategies/{id}/enable   — activate a PAUSED/LOADING strategy
  POST /strategies/{id}/disable  — pause an ACTIVE strategy
  POST /halt                     — emergency halt: pause ALL active strategies

All endpoints and WebSocket upgrades require a valid RS256 JWT.
REST endpoints use HTTP Bearer; WebSocket endpoints use ?token= query param.

Redis key layout (reads)
------------------------
itm:state:snapshot       — ITMSystemState JSON (written by RedisStateStore)
itm:decisions:recent     — Redis list (RPUSH by EventPublisher), newest at tail
itm:signals:recent       — Redis list (RPUSH by EventPublisher), newest at tail
itm:alerts:active        — Redis hash  alert_id → alert JSON

Redis pub/sub channels (WebSocket fanout)
-----------------------------------------
itm:cycle         itm:capital      itm:positions
itm:decisions     itm:signals      itm:alerts
itm:strategies

P2 registry injection
---------------------
Call ``configure(registry)`` before starting the server so the write
endpoints can call StrategyRegistry directly.  The registry callbacks
(``on_strategy_activated``, ``on_strategy_paused``) are expected to already
be wired to an ``EventPublisher`` so WS subscribers receive state changes
automatically.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from .auth import require_jwt, ws_require_jwt
from .models import (
    AggregatedSignalModel,
    AlertModel,
    CapitalResponse,
    HaltResponse,
    HealthResponse,
    PositionModel,
    PositionEntryModel,
    PositionExitModel,
    RiskProfileModel,
    RiskSnapshotModel,
    CapitalStateModel,
    StateSnapshotResponse,
    StrategyActionResponse,
    StrategyModel,
    TradeDecisionModel,
)
from .redis_client import make_async_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_redis: Optional[aioredis.Redis] = None
_start_time: float = time.monotonic()

# P2: StrategyRegistry injected via configure() before server.start()
# Typed as Any to avoid importing ITM modules at module load time when
# the registry is not used (e.g. in test environments that only test P1).
_registry: Optional[Any] = None


def configure(registry: Any, orchestrator: Optional[Any] = None, publisher: Optional[Any] = None) -> None:
    """Inject the ITM StrategyRegistry (and optionally orchestrator) for P2.

    Call this before ``APIServer.start()``::

        from src.api.app import configure
        from src.api.event_publisher import EventPublisher

        publisher = EventPublisher(make_sync_client())
        registry = StrategyRegistry(
            on_strategy_activated=publisher.on_strategy_changed,
            on_strategy_paused=publisher.on_strategy_changed,
            on_strategy_stopped=publisher.on_strategy_changed,
        )
        orchestrator = MultiStrategyOrchestrator(
            config=...,
            on_phase_event=publisher.on_phase_started,  # see note below
        )
        configure(registry=registry, orchestrator=orchestrator, publisher=publisher)
        server.start()

    When ``orchestrator`` and ``publisher`` are both provided, the orchestrator's
    ``on_phase_event`` is wired so that ``PhaseStarted`` events call
    ``publisher.on_phase_started`` and ``PhaseCompleted`` events call
    ``publisher.on_phase_completed``, routing all phase telemetry to
    ``WS /ws/cycle``.
    """
    global _registry
    _registry = registry

    if orchestrator is not None and publisher is not None:
        def _dispatch_phase_event(event: Any) -> None:
            from src.itm.domain.events import PhaseStarted, PhaseCompleted
            if isinstance(event, PhaseStarted):
                publisher.on_phase_started(event)
            elif isinstance(event, PhaseCompleted):
                publisher.on_phase_completed(event)

        orchestrator._on_phase_event = _dispatch_phase_event

# Redis key constants (must stay in sync with RedisStateStore / EventPublisher)
_KEY_SNAPSHOT = "itm:state:snapshot"
_KEY_DECISIONS = "itm:decisions:recent"
_KEY_SIGNALS = "itm:signals:recent"
_KEY_ALERTS = "itm:alerts:active"

# Default limits for recent-N queries
_DEFAULT_RECENT_N = 50


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _start_time
    _redis = make_async_client()
    _start_time = time.monotonic()
    logger.info("BTE API: Redis client initialised")
    yield
    await _redis.aclose()
    logger.info("BTE API: Redis client closed")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BTC Trade Engine API",
    version="1.0.0",
    description="REST + WebSocket bridge between the ITM and the Next.js dashboard.",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_snapshot() -> Optional[dict]:
    """Read the latest ITMSystemState snapshot from Redis."""
    try:
        raw = await _redis.get(_KEY_SNAPSHOT)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.error("Redis snapshot read failed: %s", exc)
        return None


async def _redis_ping() -> bool:
    try:
        return bool(await _redis.ping())
    except Exception:
        return False


def _snapshot_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No ITM state snapshot available yet",
    )


def _build_capital_model(risk_dict: dict) -> Optional[CapitalStateModel]:
    cs = risk_dict.get("capital_state")
    if not cs:
        return None
    total = cs.get("total_capital", "0")
    allocated = cs.get("allocated", "0")
    locked = cs.get("locked", "0")
    from decimal import Decimal
    avail = str(Decimal(total) - Decimal(allocated) - Decimal(locked))
    return CapitalStateModel(
        total_capital=total,
        allocated=allocated,
        locked=locked,
        available=avail,
        updated_at=risk_dict.get("updated_at", ""),
    )


def _build_risk_model(risk_dict: dict) -> RiskSnapshotModel:
    daily_pnl = risk_dict.get("total_daily_pnl", "0")
    max_loss = risk_dict.get("max_daily_loss", "500")
    from decimal import Decimal
    daily_loss_reached = Decimal(daily_pnl) <= -Decimal(max_loss)
    return RiskSnapshotModel(
        total_open_positions=int(risk_dict.get("total_open_positions", 0)),
        total_pending_orders=int(risk_dict.get("total_pending_orders", 0)),
        total_realized_pnl=risk_dict.get("total_realized_pnl", "0"),
        total_daily_pnl=daily_pnl,
        max_daily_loss=max_loss,
        max_drawdown_pct=risk_dict.get("max_drawdown_pct", "0.05"),
        current_drawdown_pct=risk_dict.get("current_drawdown_pct", "0"),
        daily_loss_limit_reached=daily_loss_reached,
        capital_state=_build_capital_model(risk_dict),
        updated_at=risk_dict.get("updated_at", ""),
    )


def _build_position_model(pos_dict: dict) -> PositionModel:
    from decimal import Decimal
    entries = [
        PositionEntryModel(
            order_id=e["order_id"],
            quantity=e["quantity"],
            price=e["price"],
            timestamp=e["timestamp"],
        )
        for e in pos_dict.get("entries", [])
    ]
    exits = [
        PositionExitModel(
            order_id=x["order_id"],
            quantity=x["quantity"],
            price=x["price"],
            pnl=x.get("pnl", "0"),
            timestamp=x["timestamp"],
        )
        for x in pos_dict.get("exits", [])
    ]
    total_entered = sum(Decimal(e.quantity) for e in entries)
    total_exited = sum(Decimal(x.quantity) for x in exits)
    open_qty = total_entered - total_exited
    realized_pnl = sum(Decimal(x.pnl) for x in exits)
    avg_entry: Optional[str] = None
    if entries:
        total_cost = sum(Decimal(e.quantity) * Decimal(e.price) for e in entries)
        avg_entry = str(total_cost / total_entered) if total_entered else None
    return PositionModel(
        position_id=pos_dict["position_id"],
        instrument_symbol=pos_dict.get("instrument_symbol", ""),
        instrument_exchange=pos_dict.get("instrument_exchange", ""),
        direction=pos_dict.get("direction", ""),
        open_quantity=str(open_qty),
        total_entered=str(total_entered),
        total_exited=str(total_exited),
        average_entry_price=avg_entry,
        realized_pnl=str(realized_pnl),
        is_open=open_qty > 0,
        entries=entries,
        exits=exits,
        opened_at=pos_dict.get("opened_at", ""),
        closed_at=pos_dict.get("closed_at"),
    )


def _build_strategy_model(s: dict) -> StrategyModel:
    rp = s.get("risk_profile")
    rp_model = None
    if rp:
        rp_model = RiskProfileModel(
            strategy_id=rp["strategy_id"],
            max_drawdown_pct=rp["max_drawdown_pct"],
            max_position_qty=rp["max_position_qty"],
            heat_limit=rp["heat_limit"],
            max_daily_loss=rp["max_daily_loss"],
            max_leverage=rp.get("max_leverage", "1.0"),
        )
    instr = s.get("instrument")
    return StrategyModel(
        strategy_id=s["strategy_id"],
        run_state=s.get("run_state", "unknown"),
        instrument_symbol=instr["symbol"] if instr else None,
        active_position_id=s.get("active_position_id"),
        daily_pnl=s.get("daily_pnl", "0"),
        heat=s.get("heat", "0"),
        realized_pnl=s.get("realized_pnl", "0"),
        risk_profile=rp_model,
        error_message=s.get("error_message"),
        updated_at=s.get("updated_at", ""),
    )


# ---------------------------------------------------------------------------
# REST: GET /health
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health(_: dict = Depends(require_jwt)) -> HealthResponse:
    """Liveness probe. Returns 200 when the API is running."""
    redis_ok = await _redis_ping()
    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        redis=redis_ok,
        uptime_seconds=time.monotonic() - _start_time,
    )


# ---------------------------------------------------------------------------
# REST: GET /state/snapshot
# ---------------------------------------------------------------------------


@app.get("/state/snapshot", response_model=StateSnapshotResponse, tags=["State"])
async def state_snapshot(_: dict = Depends(require_jwt)) -> StateSnapshotResponse:
    """Return the current ITM system state snapshot from Redis."""
    snap = await _get_snapshot()
    if snap is None:
        raise _snapshot_not_found()
    risk = _build_risk_model(snap.get("risk", {}))
    return StateSnapshotResponse(
        state_id=snap.get("state_id", ""),
        checkpoint_seq=int(snap.get("checkpoint_seq", 0)),
        created_at=snap.get("created_at", ""),
        updated_at=snap.get("updated_at", ""),
        risk=risk,
        open_position_count=sum(
            1 for p in snap.get("positions", {}).values()
            if p.get("closed_at") is None
        ),
        strategy_count=len(snap.get("strategies", {})),
    )


# ---------------------------------------------------------------------------
# REST: GET /strategies
# ---------------------------------------------------------------------------


@app.get("/strategies", response_model=list[StrategyModel], tags=["Strategies"])
async def list_strategies(_: dict = Depends(require_jwt)) -> list[StrategyModel]:
    """List all configured strategies and their runtime state."""
    snap = await _get_snapshot()
    if snap is None:
        return []
    return [_build_strategy_model(s) for s in snap.get("strategies", {}).values()]


# ---------------------------------------------------------------------------
# REST: GET /strategies/{id}
# ---------------------------------------------------------------------------


@app.get("/strategies/{strategy_id}", response_model=StrategyModel, tags=["Strategies"])
async def get_strategy(
    strategy_id: str,
    _: dict = Depends(require_jwt),
) -> StrategyModel:
    """Return config and runtime state for a single strategy."""
    snap = await _get_snapshot()
    if snap is None:
        raise _snapshot_not_found()
    strategies = snap.get("strategies", {})
    if strategy_id not in strategies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )
    return _build_strategy_model(strategies[strategy_id])


# ---------------------------------------------------------------------------
# REST: GET /positions
# ---------------------------------------------------------------------------


@app.get("/positions", response_model=list[PositionModel], tags=["Positions"])
async def list_positions(_: dict = Depends(require_jwt)) -> list[PositionModel]:
    """List all currently open positions."""
    snap = await _get_snapshot()
    if snap is None:
        return []
    return [
        _build_position_model(p)
        for p in snap.get("positions", {}).values()
        if p.get("closed_at") is None
    ]


# ---------------------------------------------------------------------------
# REST: GET /positions/{id}
# ---------------------------------------------------------------------------


@app.get("/positions/{position_id}", response_model=PositionModel, tags=["Positions"])
async def get_position(
    position_id: str,
    _: dict = Depends(require_jwt),
) -> PositionModel:
    """Return a single position with verification status."""
    snap = await _get_snapshot()
    if snap is None:
        raise _snapshot_not_found()
    positions = snap.get("positions", {})
    if position_id not in positions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position '{position_id}' not found",
        )
    return _build_position_model(positions[position_id])


# ---------------------------------------------------------------------------
# REST: GET /capital
# ---------------------------------------------------------------------------


@app.get("/capital", response_model=CapitalResponse, tags=["Capital"])
async def get_capital(_: dict = Depends(require_jwt)) -> CapitalResponse:
    """Return the current capital allocation state."""
    snap = await _get_snapshot()
    if snap is None:
        raise _snapshot_not_found()
    risk = snap.get("risk", {})
    cs = risk.get("capital_state") or {}
    ah = risk.get("account_heat") or {}
    from decimal import Decimal
    total = cs.get("total_capital", "0")
    allocated = cs.get("allocated", "0")
    locked = cs.get("locked", "0")
    avail = str(Decimal(total) - Decimal(allocated) - Decimal(locked))
    return CapitalResponse(
        total_capital=total,
        allocated=allocated,
        locked=locked,
        available=avail,
        total_daily_pnl=risk.get("total_daily_pnl", "0"),
        total_realized_pnl=risk.get("total_realized_pnl", "0"),
        heat_current=ah.get("current_heat"),
        heat_max=ah.get("max_heat"),
        updated_at=risk.get("updated_at", ""),
    )


# ---------------------------------------------------------------------------
# REST: GET /decisions/recent
# ---------------------------------------------------------------------------


@app.get("/decisions/recent", response_model=list[TradeDecisionModel], tags=["Decisions"])
async def recent_decisions(
    n: int = Query(default=_DEFAULT_RECENT_N, ge=1, le=500),
    _: dict = Depends(require_jwt),
) -> list[TradeDecisionModel]:
    """Return the last N TradeDecisions (newest first)."""
    try:
        raw_items = await _redis.lrange(_KEY_DECISIONS, -n, -1)
    except Exception as exc:
        logger.error("Redis lrange %s failed: %s", _KEY_DECISIONS, exc)
        return []
    decisions = []
    for raw in reversed(raw_items):
        try:
            d = json.loads(raw)
            decisions.append(
                TradeDecisionModel(
                    decision_id=d.get("decision_id", ""),
                    action=d.get("action", ""),
                    confidence=d.get("confidence", "0"),
                    risk_gated=bool(d.get("risk_gated", False)),
                    instrument_symbol=d.get("instrument_symbol", ""),
                    reason=d.get("reason"),
                    created_at=d.get("created_at", ""),
                    metadata=d.get("metadata", {}),
                )
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Skipping malformed decision: %s", exc)
    return decisions


# ---------------------------------------------------------------------------
# REST: GET /signals/recent
# ---------------------------------------------------------------------------


@app.get("/signals/recent", response_model=list[AggregatedSignalModel], tags=["Signals"])
async def recent_signals(
    n: int = Query(default=_DEFAULT_RECENT_N, ge=1, le=500),
    _: dict = Depends(require_jwt),
) -> list[AggregatedSignalModel]:
    """Return the last N AggregatedSignals (newest first)."""
    try:
        raw_items = await _redis.lrange(_KEY_SIGNALS, -n, -1)
    except Exception as exc:
        logger.error("Redis lrange %s failed: %s", _KEY_SIGNALS, exc)
        return []
    signals = []
    for raw in reversed(raw_items):
        try:
            s = json.loads(raw)
            signals.append(
                AggregatedSignalModel(
                    signal_id=s.get("signal_id", ""),
                    direction=s.get("direction", ""),
                    strength=s.get("strength", "0"),
                    source_strategy=s.get("source_strategy", ""),
                    instrument_symbol=s.get("instrument_symbol", ""),
                    is_expired=bool(s.get("is_expired", False)),
                    created_at=s.get("created_at", ""),
                    metadata=s.get("metadata", {}),
                )
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Skipping malformed signal: %s", exc)
    return signals


# ---------------------------------------------------------------------------
# REST: GET /alerts/active
# ---------------------------------------------------------------------------


@app.get("/alerts/active", response_model=list[AlertModel], tags=["Alerts"])
async def active_alerts(_: dict = Depends(require_jwt)) -> list[AlertModel]:
    """Return all active (unresolved) alerts."""
    try:
        raw_map = await _redis.hgetall(_KEY_ALERTS)
    except Exception as exc:
        logger.error("Redis hgetall %s failed: %s", _KEY_ALERTS, exc)
        return []
    alerts = []
    for raw in raw_map.values():
        try:
            a = json.loads(raw)
            if a.get("resolved", False):
                continue
            alerts.append(
                AlertModel(
                    alert_id=a.get("alert_id", ""),
                    level=a.get("level", "info"),
                    category=a.get("category", ""),
                    message=a.get("message", ""),
                    strategy_id=a.get("strategy_id"),
                    created_at=a.get("created_at", ""),
                    resolved=False,
                )
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Skipping malformed alert: %s", exc)
    return alerts


# ---------------------------------------------------------------------------
# P2: Strategy enable/disable and emergency halt
# ---------------------------------------------------------------------------


def _registry_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Strategy registry not available; call configure() before starting the server",
    )


def _strategy_not_found(strategy_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Strategy '{strategy_id}' not found in registry",
    )


@app.post(
    "/strategies/{strategy_id}/enable",
    response_model=StrategyActionResponse,
    tags=["Strategies"],
    summary="Enable (activate) a strategy",
)
async def enable_strategy(
    strategy_id: str,
    _: dict = Depends(require_jwt),
) -> StrategyActionResponse:
    """Transition a LOADING or PAUSED strategy to ACTIVE.

    The registry's ``on_strategy_activated`` callback fires automatically,
    which (when wired to ``EventPublisher``) broadcasts the state change on
    ``WS /ws/strategies``.

    Returns 404 if the strategy is not registered.
    Returns 409 if the transition is not allowed (e.g. strategy is STOPPED).
    Returns 503 if the registry has not been injected via ``configure()``.
    """
    if _registry is None:
        raise _registry_unavailable()
    entry = _registry.get(strategy_id)
    if entry is None:
        raise _strategy_not_found(strategy_id)
    prev_state = entry.state.value
    try:
        entry = _registry.activate(strategy_id)
    except Exception as exc:
        if "StrategyRegistryError" in type(exc).__name__:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        logger.exception("Unexpected error activating strategy %r", strategy_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return StrategyActionResponse(
        strategy_id=strategy_id,
        previous_state=prev_state,
        current_state=entry.state.value,
        action="enabled",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/strategies/{strategy_id}/disable",
    response_model=StrategyActionResponse,
    tags=["Strategies"],
    summary="Disable (pause) a strategy",
)
async def disable_strategy(
    strategy_id: str,
    _: dict = Depends(require_jwt),
) -> StrategyActionResponse:
    """Transition an ACTIVE strategy to PAUSED.

    The registry's ``on_strategy_paused`` callback fires automatically,
    which (when wired to ``EventPublisher``) broadcasts the state change on
    ``WS /ws/strategies``.

    Returns 404 if the strategy is not registered.
    Returns 409 if the transition is not allowed (e.g. strategy is STOPPED).
    Returns 503 if the registry has not been injected via ``configure()``.
    """
    if _registry is None:
        raise _registry_unavailable()
    entry = _registry.get(strategy_id)
    if entry is None:
        raise _strategy_not_found(strategy_id)
    prev_state = entry.state.value
    try:
        entry = _registry.pause(strategy_id, reason="api:disabled")
    except Exception as exc:
        if "StrategyRegistryError" in type(exc).__name__:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        logger.exception("Unexpected error pausing strategy %r", strategy_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return StrategyActionResponse(
        strategy_id=strategy_id,
        previous_state=prev_state,
        current_state=entry.state.value,
        action="disabled",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/halt",
    response_model=HaltResponse,
    tags=["System"],
    summary="Emergency halt — pause all active strategies immediately",
)
async def emergency_halt(
    _: dict = Depends(require_jwt),
) -> HaltResponse:
    """Pause every ACTIVE strategy atomically.

    Each strategy is paused with reason ``"emergency_halt"``.  The registry's
    ``on_strategy_paused`` callback fires per strategy, broadcasting state
    changes on ``WS /ws/strategies``.

    Already-paused or stopped strategies are skipped silently.

    Returns 503 if the registry has not been injected via ``configure()``.
    """
    if _registry is None:
        raise _registry_unavailable()

    active = _registry.active_entries()
    halted_ids: list[str] = []
    for entry in active:
        try:
            _registry.pause(entry.strategy_id, reason="emergency_halt")
            halted_ids.append(entry.strategy_id)
        except Exception:
            logger.exception("emergency_halt: failed to pause strategy %r", entry.strategy_id)

    logger.warning(
        "EMERGENCY HALT executed: %d strategies paused (%s)",
        len(halted_ids),
        halted_ids,
    )
    return HaltResponse(
        status="halted",
        halted_count=len(halted_ids),
        halted_strategy_ids=halted_ids,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# WebSocket helper: subscribe one channel and fan out to one client
# ---------------------------------------------------------------------------


async def _ws_subscribe(websocket: WebSocket, channel: str) -> None:
    """Accept the WebSocket and relay all messages from a Redis pub/sub channel."""
    await websocket.accept()
    async with make_async_client() as r:
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.error("WS %s error: %s", channel, exc)
        finally:
            await pubsub.unsubscribe(channel)


# ---------------------------------------------------------------------------
# 7 WebSocket domains
# ---------------------------------------------------------------------------


@app.websocket("/ws/cycle")
async def ws_cycle(
    websocket: WebSocket,
    _: dict = Depends(ws_require_jwt),
) -> None:
    """Subscribe to itm:cycle pub/sub channel."""
    await _ws_subscribe(websocket, "itm:cycle")


@app.websocket("/ws/capital")
async def ws_capital(
    websocket: WebSocket,
    _: dict = Depends(ws_require_jwt),
) -> None:
    """Subscribe to itm:capital pub/sub channel."""
    await _ws_subscribe(websocket, "itm:capital")


@app.websocket("/ws/positions")
async def ws_positions(
    websocket: WebSocket,
    _: dict = Depends(ws_require_jwt),
) -> None:
    """Subscribe to itm:positions pub/sub channel."""
    await _ws_subscribe(websocket, "itm:positions")


@app.websocket("/ws/decisions")
async def ws_decisions(
    websocket: WebSocket,
    _: dict = Depends(ws_require_jwt),
) -> None:
    """Subscribe to itm:decisions pub/sub channel."""
    await _ws_subscribe(websocket, "itm:decisions")


@app.websocket("/ws/signals")
async def ws_signals(
    websocket: WebSocket,
    _: dict = Depends(ws_require_jwt),
) -> None:
    """Subscribe to itm:signals pub/sub channel."""
    await _ws_subscribe(websocket, "itm:signals")


@app.websocket("/ws/alerts")
async def ws_alerts(
    websocket: WebSocket,
    _: dict = Depends(ws_require_jwt),
) -> None:
    """Subscribe to itm:alerts pub/sub channel."""
    await _ws_subscribe(websocket, "itm:alerts")


@app.websocket("/ws/strategies")
async def ws_strategies(
    websocket: WebSocket,
    _: dict = Depends(ws_require_jwt),
) -> None:
    """Subscribe to itm:strategies pub/sub channel."""
    await _ws_subscribe(websocket, "itm:strategies")
