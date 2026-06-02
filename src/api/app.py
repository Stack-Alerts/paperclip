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

import asyncio
import json
import logging
import os
import subprocess
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.exceptions import RedisError
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


def _resolve_running_revision() -> tuple[Optional[str], Optional[str]]:
    """Resolve the (commit_sha, branch) of the currently running code.

    Preference order (BTCAAAAA-30590):
      1. BTE_RUNNING_SHA / BTE_RUNNING_BRANCH env vars (set by start.sh).
      2. Live `git rev-parse` from the repo root (works when uvicorn is
         launched directly, outside start.sh, e.g. by a developer running
         `python -m uvicorn src.api.app:app` from the repo root).
      3. None if neither is available (deployed container without git).
    """
    sha = os.environ.get("BTE_RUNNING_SHA") or None
    branch = os.environ.get("BTE_RUNNING_BRANCH") or None

    if sha and branch:
        return sha, branch

    # Walk up from this file to the repo root (src/api/app.py -> parents[2]).
    repo_root = Path(__file__).resolve().parents[2]
    if not (repo_root / ".git").exists():
        return sha, branch

    def _git(args: list[str]) -> Optional[str]:
        try:
            out = subprocess.run(
                ["git", *args],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=2,
            )
            if out.returncode == 0:
                return out.stdout.strip() or None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        return None

    if not sha:
        sha = _git(["rev-parse", "HEAD"])
    if not branch:
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    return sha, branch


_running_sha, _running_branch = _resolve_running_revision()
if _running_sha:
    logger.info(
        "BTC Trade Engine running commit %s on branch %s",
        _running_sha,
        _running_branch or "unknown",
    )

# P2: StrategyRegistry injected via configure() before server.start()
# Typed as Any to avoid importing ITM modules at module load time when
# the registry is not used (e.g. in test environments that only test P1).
_registry: Optional[Any] = None

# Strategy-builder DB manager – lazy singleton, None until first use.
_sb_db: Optional[Any] = None


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

# Allow the Next.js dev server (port 3000) and any localhost origin to call the API.
# OPTIONS preflight requests were returning 405 because no CORS middleware was present.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Liveness probe. Returns 200 when the API is running.

    BTCAAAAA-30590: includes `commit_sha` and `branch` of the running code so
    the board can cross-reference the running build against
    `git rev-parse origin/main` without trusting the dev banner.
    """
    redis_ok = await _redis_ping()
    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        redis=redis_ok,
        uptime_seconds=time.monotonic() - _start_time,
        commit_sha=_running_sha,
        branch=_running_branch,
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
# Strategy Builder: database-backed endpoints (not ITM runtime)
# ---------------------------------------------------------------------------


def _get_sb_db() -> Optional[Any]:
    """Return the strategy-builder DB manager, initialising it on first call."""
    global _sb_db
    if _sb_db is None:
        try:
            from src.optimizer_v3.database import get_database_manager
            _sb_db = get_database_manager()
        except Exception as exc:
            logger.warning("Strategy builder DB unavailable: %s", exc)
    return _sb_db


def _sb_db_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Strategy builder database not available – check POSTGRES_* env vars",
    )


def _iso(dt: Any) -> str:
    """Serialize a datetime (or None) to ISO-8601 string."""
    if dt is None:
        return ""
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _map_validation_status(vs: Optional[str]) -> str:
    return {"Pass": "valid", "Fail": "invalid"}.get(vs or "", "draft")


def _build_sb_strategy(strategy_id: str, version: dict, tests: list) -> dict:
    """Map a DB version dict + test-result list to the web-UI Strategy shape."""
    backtest_results = None
    if tests:
        backtest_results = []
        for t in tests:
            wr_raw = float(t.get("win_rate") or 0.0)
            # DB stores win_rate as 0–100; web UI expects 0–1
            win_rate = wr_raw / 100.0 if wr_raw > 1.0 else wr_raw
            total = int(t.get("total_trades") or 0)
            wins = round(total * win_rate) if total > 0 else 0
            risk = t.get("risk_metrics") or {}
            backtest_results.append({
                "winRate": win_rate,
                "totalTrades": total,
                "winningTrades": wins,
                "losingTrades": total - wins,
                "sharpeRatio": float(t.get("sharpe_ratio") or 0.0),
                "profitFactor": float(t.get("profit_factor") or 0.0),
                "returnPercentage": float(t.get("total_return_pct") or 0.0),
                "maxDrawdown": float(t.get("max_drawdown_pct") or 0.0),
                "sortino_ratio": risk.get("sortino_ratio"),
                "calmar_ratio": risk.get("calmar_ratio"),
            })

    return {
        "id": strategy_id,
        "name": version.get("name", ""),
        "description": version.get("description") or "",
        "status": _map_validation_status(version.get("validation_status")),
        "strategyType": version.get("strategy_type"),
        "validationStatus": version.get("validation_status"),
        "versionNumber": version.get("version_number"),
        "versionId": str(version["version_id"]) if version.get("version_id") else None,
        "blocks": version.get("blocks") or [],
        "tags": version.get("tags") or [],
        "createdAt": _iso(version.get("created_at")),
        "updatedAt": _iso(version.get("timestamp") or version.get("created_at")),
        "backtestResults": backtest_results,
        "published": False,
        "testCount": len(tests),
    }


# ── Request bodies ────────────────────────────────────────────────────────────

class _CreateSBStrategyRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class _DeleteVersionsRequest(BaseModel):
    version_ids: list[str]


class _DuplicateRequest(BaseModel):
    scope: str = "version"
    name: Optional[str] = None


class _UpdateSBStrategyRequest(BaseModel):
    """Save-strategy payload from the web-UI Strategy Builder (BTCAAAAA-30023).

    Metadata-only by design. Block editing is intentionally out of scope: the
    web-UI's Block contract ({id,type,index,data}) does not match the DB's
    raw {name,logic,signals,exit_conditions} shape, and sending it back
    without a denormalizer corrupted the Strategy Browser blocks column in
    early testing. A block-edit save needs a denormalize step both sides
    agree on; that's a separate change. The previous version's blocks/etc.
    are re-used verbatim so version history stays append-only.
    """
    name: str
    description: Optional[str] = None
    strategyType: Optional[str] = None
    tags: Optional[list] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get(
    "/strategy-builder/strategies",
    tags=["Strategy Builder"],
    summary="List all strategy builder strategies (DB-backed)",
)
async def sb_list_strategies(_: dict = Depends(require_jwt)) -> list:
    """Return all strategies from the strategy builder ORM database."""
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _fetch() -> list:
        # Per-request session (BTCAAAAA-29971): concurrent mounts of the
        # Strategy Browser (inline dialog + popped-out window) raced on the
        # shared db._session and produced "rollback() already in progress"
        # warnings for every strategy in the loop, returning an empty list.
        with db.scoped_managers() as scoped:
            strategies = scoped.strategy.get_all_strategies()
            result = []
            for s in strategies:
                try:
                    version = scoped.strategy.get_latest_version(s["strategy_id"])
                    if version is None:
                        continue
                    try:
                        tests = scoped.test_results.get_version_test_results(
                            str(version["version_id"])
                        )
                    except Exception:
                        tests = []
                    result.append(_build_sb_strategy(s["strategy_id"], version, tests))
                except Exception as exc:
                    logger.warning(
                        "sb_list_strategies: skipping %s: %s",
                        s.get("strategy_id"),
                        exc,
                    )
            return result

    return await asyncio.to_thread(_fetch)


@app.get(
    "/strategy-builder/strategies/{strategy_id}/versions",
    tags=["Strategy Builder"],
    summary="List all versions of a strategy builder strategy",
)
async def sb_get_strategy_versions(
    strategy_id: str,
    _: dict = Depends(require_jwt),
) -> list:
    """Return all versions for a strategy from the strategy builder database."""
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _fetch() -> list:
        with db.scoped_managers() as scoped:
            versions = scoped.strategy.get_strategy_versions(strategy_id)
            latest_num = max((v.get("version_number", 0) for v in versions), default=0)
            return [
                {
                    "id": str(v["version_id"]),
                    "strategyId": strategy_id,
                    "versionNumber": v.get("version_number"),
                    "createdAt": _iso(v.get("created_at")),
                    "author": v.get("created_by"),
                    "description": v.get("notes") or v.get("description"),
                    "isLatest": v.get("version_number") == latest_num,
                    "changesSummary": v.get("notes"),
                }
                for v in versions
            ]

    return await asyncio.to_thread(_fetch)


@app.get(
    "/strategy-builder/strategies/{strategy_id}/versions/{version_id}",
    tags=["Strategy Builder"],
    summary="Get a specific version of a strategy builder strategy",
)
async def sb_get_strategy_version(
    strategy_id: str,
    version_id: str,
    _: dict = Depends(require_jwt),
) -> dict:
    """Return a single strategy version by version_id from the strategy builder database."""
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _fetch() -> Optional[dict]:
        with db.scoped_managers() as scoped:
            version = scoped.strategy.get_strategy_version(version_id)
            if version is None:
                return None
            try:
                tests = scoped.test_results.get_version_test_results(
                    str(version["version_id"])
                )
            except Exception:
                tests = []
            return _build_sb_strategy(strategy_id, version, tests)

    result = await asyncio.to_thread(_fetch)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{version_id}' not found for strategy '{strategy_id}'",
        )
    return result


@app.get(
    "/strategy-builder/strategies/{strategy_id}",
    tags=["Strategy Builder"],
    summary="Get a strategy builder strategy by ID",
)
async def sb_get_strategy(
    strategy_id: str,
    _: dict = Depends(require_jwt),
) -> dict:
    """Return a single strategy (latest version) from the strategy builder database."""
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _fetch() -> Optional[dict]:
        with db.scoped_managers() as scoped:
            version = scoped.strategy.get_latest_version(strategy_id)
            if version is None:
                return None
            try:
                tests = scoped.test_results.get_version_test_results(
                    str(version["version_id"])
                )
            except Exception:
                tests = []
            return _build_sb_strategy(strategy_id, version, tests)

    result = await asyncio.to_thread(_fetch)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )
    return result


_VALIDATION_SEVERITY_BUCKET = {
    "CRITICAL": "critical_issues",
    "ERROR": "errors",
    "WARNING": "warnings",
    "NOTICE": "notices",
    "INFO": "info",
}


def _serialize_validation_issue(issue: Any) -> dict:
    """Map an InstitutionalValidator ValidationIssue → web-UI shape."""
    severity_name = issue.severity.name if hasattr(issue.severity, "name") else str(issue.severity)
    return {
        "rule_id": getattr(issue, "rule_id", "") or "",
        "rule_name": getattr(issue, "rule_name", "") or "",
        "severity": severity_name,
        "category": getattr(issue, "category", "") or "",
        "message": getattr(issue, "message", "") or "",
        "location": getattr(issue, "location", "") or "",
        "suggestion": getattr(issue, "suggestion", None) or None,
        "auto_fix_available": bool(getattr(issue, "auto_fix_available", False)),
        "auto_fix_data": getattr(issue, "auto_fix_data", None) or None,
    }


def _serialize_validation_report(
    report: Any,
    strategy_name: str,
    version_number: Optional[int],
) -> dict:
    """Map InstitutionalValidator ValidationReport → web-UI ValidationReport shape.

    The web UI populates executionFlow / confluenceScoring / scenarios from the
    strategy structure on the client side, so we only return the issues,
    complexity, and timing-conflict fields here.
    """
    metrics = getattr(report, "complexity_metrics", None) or {}
    if isinstance(metrics, dict):
        complexity_score = int(metrics.get("complexity_score") or 0)
    else:
        complexity_score = 0

    timing_conflicts_raw = getattr(report, "timing_conflicts", None) or []
    timing_conflicts: list[dict] = []
    if isinstance(timing_conflicts_raw, list):
        for tc in timing_conflicts_raw:
            if not isinstance(tc, dict):
                continue
            timing_conflicts.append({
                "signal": str(tc.get("signal") or tc.get("signal_name") or ""),
                "timing_window": int(tc.get("timing_window") or tc.get("max_candles") or 0),
                "recheck_delay": int(tc.get("recheck_delay") or tc.get("bar_delay") or 0),
            })

    return {
        "is_valid": bool(getattr(report, "is_valid", False)),
        "timestamp": getattr(report, "timestamp", None)
        or datetime.now(timezone.utc).isoformat(),
        "strategy_summary": {
            "name": strategy_name or "(unnamed)",
            "version": str(version_number) if version_number is not None else None,
        },
        "critical_issues": [
            _serialize_validation_issue(i) for i in getattr(report, "critical_issues", []) or []
        ],
        "errors": [
            _serialize_validation_issue(i) for i in getattr(report, "errors", []) or []
        ],
        "warnings": [
            _serialize_validation_issue(i) for i in getattr(report, "warnings", []) or []
        ],
        "notices": [
            _serialize_validation_issue(i) for i in getattr(report, "notices", []) or []
        ],
        "info": [
            _serialize_validation_issue(i) for i in getattr(report, "info", []) or []
        ],
        "complexity_metrics": {"complexity_score": complexity_score},
        "timing_conflicts": timing_conflicts,
    }


@app.post(
    "/strategy-builder/strategies/{strategy_id}/validate",
    tags=["Strategy Builder"],
    summary="Run institutional validation against the stored strategy",
)
async def sb_validate_strategy(
    strategy_id: str,
    _: dict = Depends(require_jwt),
) -> dict:
    """Run the full InstitutionalValidator against the strategy's latest version.

    The web UI used to fall back to a TypeScript structural checker because no
    backend endpoint existed — now it can call this route to get the same
    institutional report the thick client produces (BTCAAAAA-32954).
    """
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _run() -> Optional[dict]:
        with db.scoped_managers() as scoped:
            version = scoped.strategy.get_latest_version(strategy_id)
        if version is None:
            return None

        from src.strategy_builder.persistence.strategy_persistence import (
            StrategyPersistence,
        )
        from src.optimizer_v3.validation.institutional_validator import (
            InstitutionalValidator,
        )

        version_payload = {
            "name": version.get("name", ""),
            "description": version.get("description") or "",
            "strategy_type": version.get("strategy_type") or "Bullish",
            "blocks": version.get("blocks") or [],
            "exit_conditions": version.get("exit_conditions") or [],
        }
        config = StrategyPersistence()._dict_to_config(version_payload)

        report = InstitutionalValidator().validate(config)
        return _serialize_validation_report(
            report,
            strategy_name=version.get("name", ""),
            version_number=version.get("version_number"),
        )

    try:
        result = await asyncio.to_thread(_run)
    except Exception as exc:
        logger.exception("Validation failed for strategy %s", strategy_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {exc}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )
    return result


class _AutoFixRequest(BaseModel):
    """Body for POST /strategy-builder/strategies/{id}/auto-fix.

    Matches ValidationIssue.auto_fix_data from the InstitutionalValidator
    response — pass the rule_id alongside the data dict that the validator
    attached when it flagged the issue.
    """

    rule_id: str
    auto_fix_data: Optional[dict] = None


class _RevertRequest(BaseModel):
    """Body for POST /strategy-builder/strategies/{id}/revert.

    Accepts the original blocks from a pre-fix snapshot and persists them
    as a new version to undo a previous auto-fix (BTCAAAAA-33599).
    """

    blocks: list[dict]


def _apply_auto_fix(blocks: list[dict], rule_id: str, data: dict) -> tuple[list[dict], bool]:
    """Mutate `blocks` in place per the requested auto-fix rule.

    Returns ``(blocks, changed)``. Operates on the raw API dict shape
    (name/logic/signals/exit_conditions) so the desktop AutoFix module's
    dataclass-based helpers are not needed.
    """
    changed = False
    if rule_id == "TIMING_004":
        # Reduce RECHECK delay to 75% of the timing window so the signal
        # actually has room to validate (mirrors auto_fix_recheck_delay).
        timing_window = int((data or {}).get("timing_window") or 0)
        suggested = int((data or {}).get("suggested_delay") or 0)
        if suggested <= 0 and timing_window > 0:
            suggested = max(1, int(timing_window * 0.75))
        if suggested <= 0:
            return blocks, False
        for block in blocks:
            for sig in block.get("signals") or []:
                rc = sig.get("recheck_config")
                if isinstance(rc, dict) and rc.get("enabled"):
                    rc["bar_delay"] = suggested
                    changed = True
        return blocks, changed

    if rule_id == "EXIT_009":
        # The validator flags EXIT_009 when the SAME target exit signal_name
        # (e.g. STOP_LOSS) appears anywhere in the strategy with conflicting
        # modes (one signal binds it ABSOLUTE, another FLEXIBLE). Harmonize
        # by forcing every occurrence to the highest-confidence mode
        # (ABSOLUTE > FLEXIBLE).
        target = (data or {}).get("signal_name")
        if not target:
            return blocks, False
        all_matches: list[dict] = []
        for block in blocks:
            for sig in block.get("signals") or []:
                for ec in sig.get("exit_conditions") or []:
                    if ec.get("signal_name") == target:
                        all_matches.append(ec)
        if len(all_matches) <= 1:
            return blocks, False
        modes = {e.get("exit_mode") for e in all_matches}
        if len(modes) <= 1:
            return blocks, False
        merged_mode = "ABSOLUTE" if "ABSOLUTE" in modes else next(iter(modes))
        for ec in all_matches:
            if ec.get("exit_mode") != merged_mode:
                ec["exit_mode"] = merged_mode
                changed = True
        return blocks, changed

    if rule_id == "LOGIC_003":
        # Drop the signal entirely from its block (parity with disable+remove).
        target = (data or {}).get("signal_name")
        if not target:
            return blocks, False
        for block in blocks:
            sigs = block.get("signals") or []
            new_sigs = [s for s in sigs if s.get("name") != target]
            if len(new_sigs) != len(sigs):
                block["signals"] = new_sigs
                changed = True
        return blocks, changed

    if rule_id == "DIRECTION_001":
        # Direction switches happen on the strategy, not the blocks — caller
        # handles strategy_type. Nothing to do here.
        return blocks, False

    if rule_id == "STRUCTURAL_005":
        block_name = (data or {}).get("block_name")
        signal_name = (data or {}).get("signal_name")
        fix_mode = (data or {}).get("fix_mode") or (data or {}).get("mode", "remove")
        target_index = (data or {}).get("target_index")
        new_name = (data or {}).get("new_name")
        if not block_name or not signal_name:
            return blocks, False
        for block in blocks:
            if block.get("name") != block_name:
                continue
            sigs = block.get("signals") or []
            if fix_mode == "remove" and target_index is not None:
                if 0 <= target_index < len(sigs):
                    block["signals"] = [s for i, s in enumerate(sigs) if i != target_index]
                    changed = True
            elif fix_mode == "rename" and target_index is not None and new_name:
                if 0 <= target_index < len(sigs):
                    sigs[target_index]["name"] = new_name
                    changed = True
        return blocks, changed

    return blocks, False


@app.post(
    "/strategy-builder/strategies/{strategy_id}/auto-fix",
    tags=["Strategy Builder"],
    summary="Apply an auto-fix to a stored strategy and return the new version",
)
async def sb_auto_fix_strategy(
    strategy_id: str,
    body: _AutoFixRequest,
    _: dict = Depends(require_jwt),
) -> dict:
    """Apply the named auto-fix to the latest version and persist a new one.

    Mirrors the desktop AutoFix module (see src/strategy_builder/validation/
    auto_fix.py) but works directly on the raw API dict shape so we don't have
    to round-trip through StrategyConfig dataclasses. Returns the updated
    strategy in the same shape the GET route uses, so the web UI can swap
    `currentStrategy` from the response without an extra fetch. BTCAAAAA-32954.
    """
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    rule_id = body.rule_id
    data = body.auto_fix_data or {}

    def _run() -> Optional[dict]:
        with db.scoped_managers() as scoped:
            latest = scoped.strategy.get_latest_version(strategy_id)
            if latest is None:
                return None

            existing_blocks = latest.get("blocks") or []
            # Deep copy so a no-op fix doesn't mutate the cached version row.
            import copy
            blocks = copy.deepcopy(existing_blocks)
            blocks, changed = _apply_auto_fix(blocks, rule_id, data)

            new_strategy_type = latest.get("strategy_type") or "Bullish"
            if rule_id == "DIRECTION_001":
                suggested = (data or {}).get("suggested_type")
                if isinstance(suggested, str) and suggested:
                    new_strategy_type = suggested
                    changed = True

            if not changed:
                # Nothing to apply — return the strategy unchanged so the
                # client can refresh without a stale-version write.
                tests = []
                return _build_sb_strategy(strategy_id, latest, tests)

            _strip = {
                "version_id", "version_number", "timestamp", "created_at",
                "config_hash", "validation_timestamp",
            }
            version_data: dict = {
                k: v for k, v in latest.items() if k not in _strip
            }
            version_data["strategy_id"] = strategy_id
            version_data["blocks"] = blocks
            version_data["strategy_type"] = new_strategy_type

            version_id = scoped.strategy.create_strategy_version(version_data)
            new_version = scoped.strategy.get_strategy_version(version_id)
            try:
                tests = scoped.test_results.get_version_test_results(
                    str(version_id)
                )
            except Exception:
                tests = []
            return _build_sb_strategy(strategy_id, new_version, tests)

    try:
        result = await asyncio.to_thread(_run)
    except Exception as exc:
        logger.exception("Auto-fix failed for strategy %s rule %s", strategy_id, rule_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-fix failed: {exc}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )
    return result


@app.post(
    "/strategy-builder/strategies/{strategy_id}/revert",
    tags=["Strategy Builder"],
    summary="Revert a strategy to previous blocks (undo an auto-fix)",
)
async def sb_revert_strategy(
    strategy_id: str,
    body: _RevertRequest,
    _: dict = Depends(require_jwt),
) -> dict:
    """Revert to a previous blocks snapshot by persisting them as a new version.

    Used by the Undo button on fixed validation issues — takes the original blocks
    from the pre-fix snapshot and creates a new version to undo a prior auto-fix.
    Returns the updated strategy in the same shape the GET route uses (BTCAAAAA-33599).
    """
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _run() -> Optional[dict]:
        with db.scoped_managers() as scoped:
            latest = scoped.strategy.get_latest_version(strategy_id)
            if latest is None:
                return None

            # Reuse the latest version's metadata but replace blocks with the snapshot's
            _strip = {
                "version_id", "version_number", "timestamp", "created_at",
                "config_hash", "validation_timestamp",
            }
            version_data: dict = {
                k: v for k, v in latest.items() if k not in _strip
            }
            version_data["strategy_id"] = strategy_id
            version_data["blocks"] = body.blocks

            version_id = scoped.strategy.create_strategy_version(version_data)
            new_version = scoped.strategy.get_strategy_version(version_id)
            try:
                tests = scoped.test_results.get_version_test_results(
                    str(version_id)
                )
            except Exception:
                tests = []
            return _build_sb_strategy(strategy_id, new_version, tests)

    try:
        result = await asyncio.to_thread(_run)
    except Exception as exc:
        logger.exception("Revert failed for strategy %s", strategy_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Revert failed: {exc}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )
    return result


@app.put(
    "/strategy-builder/strategies/{strategy_id}",
    tags=["Strategy Builder"],
    summary="Update a strategy builder strategy (rename + new version)",
)
async def sb_update_strategy(
    strategy_id: str,
    body: _UpdateSBStrategyRequest,
    _: dict = Depends(require_jwt),
) -> dict:
    """Persist edits from the web-UI Strategy Builder Save action (BTCAAAAA-30023).

    Updates the parent ``Strategy.name`` if it changed and appends a new
    ``StrategyVersion`` row carrying the supplied name/description/blocks on
    top of the previous version's signal/parameter/condition payload. This
    preserves the version-history invariant (versions are append-only) while
    making the Save button persist user edits to the DB so the Strategy
    Browser shows the renamed/edited strategy on the next round-trip.
    """
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _update() -> Optional[dict]:
        with db.scoped_managers() as scoped:
            latest = scoped.strategy.get_latest_version(strategy_id)
            if latest is None:
                return None

            # Re-use previous version's payload as the base; the UI only sends
            # the fields it edits (name/blocks/etc.). Strip auto-generated
            # columns so create_strategy_version mints fresh ones.
            _strip = {
                "version_id", "version_number", "timestamp", "created_at",
                "config_hash", "validation_timestamp",
            }
            version_data: dict = {k: v for k, v in latest.items() if k not in _strip}
            version_data["strategy_id"] = strategy_id
            version_data["name"] = body.name
            if body.description is not None:
                version_data["description"] = body.description
            if body.strategyType is not None:
                version_data["strategy_type"] = body.strategyType
            if body.tags is not None:
                version_data["tags"] = body.tags

            # Rename the parent strategy record so list views reflect the new
            # name even before the new version row is read back. Safe to call
            # when the name is unchanged (early-returns inside the manager).
            scoped.strategy.rename_strategy(strategy_id, body.name)

            version_id = scoped.strategy.create_strategy_version(version_data)
            version = scoped.strategy.get_strategy_version(version_id)
            try:
                tests = scoped.test_results.get_version_test_results(str(version_id))
            except Exception:
                tests = []
            return _build_sb_strategy(strategy_id, version, tests)

    result = await asyncio.to_thread(_update)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )
    return result


@app.post(
    "/strategy-builder/strategies",
    tags=["Strategy Builder"],
    summary="Create a new strategy builder strategy",
    status_code=status.HTTP_201_CREATED,
)
async def sb_create_strategy(
    body: _CreateSBStrategyRequest,
    _: dict = Depends(require_jwt),
) -> dict:
    """Create a new strategy in the strategy builder database."""
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _create() -> dict:
        with db.scoped_managers() as scoped:
            strategy_id = scoped.strategy.create_strategy(body.name)
            version_id = scoped.strategy.create_strategy_version({
                "strategy_id": strategy_id,
                "name": body.name,
                "description": body.description or "",
                "blocks": [],
                "signals": {},
                "parameters": {},
                "entry_conditions": {},
                "exit_conditions": {},
                "risk_management": {},
                "backtest_config": {},
            })
            version = scoped.strategy.get_strategy_version(version_id)
            return _build_sb_strategy(strategy_id, version, [])

    return await asyncio.to_thread(_create)


@app.delete(
    "/strategy-builder/strategies/{strategy_id}",
    tags=["Strategy Builder"],
    summary="Delete a strategy builder strategy",
)
async def sb_delete_strategy(
    strategy_id: str,
    _: dict = Depends(require_jwt),
) -> dict:
    """Delete a strategy and all its versions from the strategy builder database."""
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _delete() -> bool:
        with db.scoped_managers() as scoped:
            return scoped.strategy.delete_strategy(strategy_id)

    deleted = await asyncio.to_thread(_delete)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )
    return {"deleted": True, "strategy_id": strategy_id}


@app.post(
    "/strategy-builder/strategies/{strategy_id}/versions/delete",
    tags=["Strategy Builder"],
    summary="Delete specific versions of a strategy",
)
async def sb_delete_strategy_versions(
    strategy_id: str,
    body: _DeleteVersionsRequest,
    _: dict = Depends(require_jwt),
) -> dict:
    """Delete specific versions from the strategy builder database."""
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _delete_versions() -> dict:
        with db.scoped_managers() as scoped:
            return {
                vid: scoped.strategy.delete_strategy_version(vid)
                for vid in body.version_ids
            }

    results = await asyncio.to_thread(_delete_versions)
    return {"deleted": results}


@app.post(
    "/strategy-builder/strategies/{strategy_id}/duplicate",
    tags=["Strategy Builder"],
    summary="Duplicate a strategy builder strategy",
    status_code=status.HTTP_201_CREATED,
)
async def sb_duplicate_strategy(
    strategy_id: str,
    body: _DuplicateRequest,
    _: dict = Depends(require_jwt),
) -> dict:
    """Duplicate a strategy (new version or new strategy) in the strategy builder database."""
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _duplicate() -> Optional[dict]:
        with db.scoped_managers() as scoped:
            latest = scoped.strategy.get_latest_version(strategy_id)
            if latest is None:
                return None

            # Strip auto-generated fields before re-inserting
            _strip = {"version_id", "version_number", "timestamp", "created_at",
                      "config_hash", "validation_timestamp"}
            version_data = {k: v for k, v in latest.items() if k not in _strip}

            if body.scope == "strategy":
                new_name = body.name or f"{latest['name']} (Copy)"
                new_strategy_id = scoped.strategy.create_strategy(new_name)
                version_data["strategy_id"] = new_strategy_id
                version_data["name"] = new_name
            else:
                new_strategy_id = strategy_id
                version_data["strategy_id"] = strategy_id

            version_id = scoped.strategy.create_strategy_version(version_data)
            version = scoped.strategy.get_strategy_version(version_id)
            return _build_sb_strategy(new_strategy_id, version, [])

    result = await asyncio.to_thread(_duplicate)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )
    return result


# ---------------------------------------------------------------------------
# REST: Backtest execution (BTCAAAAA-31183 / parent BTCAAAAA-31180)
# ---------------------------------------------------------------------------
#
# Wraps MulticoreBacktestEngine + BacktestDataProvider behind a REST contract
# that the WebUI BackTesting drawer can drive:
#
#   POST /strategies/{strategy_id}/backtest               -> {runId, status}
#   GET  /strategies/{strategy_id}/backtest/{run_id}      -> live status + result
#
# Runs are stored in-process (best-effort; lost on restart). For persistent
# job history see follow-up BTCAAAAA-31247.
#
# The engine call is synchronous and CPU-heavy; we spawn a worker thread per
# run so the event loop stays responsive. Concurrency is bounded by the OS
# default ProcessPoolExecutor inside the engine itself.
#
# WebSocket /ws/backtest/{run_id} is deferred to a follow-up — polling the
# GET endpoint is sufficient for the V1 unblock per board direction.

_backtest_runs: dict[str, dict[str, Any]] = {}
_backtest_lock = threading.Lock()


def _new_backtest_run(strategy_id: str, config: dict) -> str:
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    with _backtest_lock:
        _backtest_runs[run_id] = {
            "runId": run_id,
            "strategyId": strategy_id,
            "status": "running",
            "progress": 0,
            "trades": [],
            "metrics": {},
            "logs": [],
            "error": None,
            "config": config,
            "startedAt": now,
            "completedAt": None,
        }
    return run_id


def _patch_backtest_run(run_id: str, **patch: Any) -> None:
    with _backtest_lock:
        run = _backtest_runs.get(run_id)
        if run is not None:
            run.update(patch)


def _append_backtest_log(run_id: str, message: str, level: str = "INFO") -> None:
    entry = {
        "message": str(message),
        "level": level,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _backtest_lock:
        run = _backtest_runs.get(run_id)
        if run is not None:
            logs = run.setdefault("logs", [])
            logs.append(entry)
            # Bound the log buffer so a long run doesn't balloon memory.
            if len(logs) > 500:
                del logs[: len(logs) - 500]


def _run_backtest_in_thread(run_id: str, strategy: dict, config: dict) -> None:
    """Background worker: load bars, run engine, persist result into the runs dict."""
    try:
        _append_backtest_log(
            run_id,
            f"Starting backtest for '{strategy.get('name', '?')}' "
            f"({config.get('startDate', '?')} → {config.get('endDate', '?')})",
        )

        from src.optimizer_v3.core.backtest_data_provider import get_backtest_provider
        from src.optimizer_v3.core.multicore_backtest_engine import MulticoreBacktestEngine

        timeframe = str(config.get("timeframe") or strategy.get("settings", {}).get("timeframe") or "15m")
        start = datetime.fromisoformat(str(config["startDate"]))
        end = datetime.fromisoformat(str(config["endDate"]))

        _append_backtest_log(run_id, f"Loading bars {timeframe} {config['startDate']} → {config['endDate']}")

        def _load_progress(current: int, total: int, msg: str) -> None:
            pct = int((current / total) * 25) if total else 0
            _patch_backtest_run(run_id, progress=pct)
            if msg:
                _append_backtest_log(run_id, msg)

        provider = get_backtest_provider()
        bars = provider.load_bars_for_backtest(timeframe, start, end, _load_progress)
        _append_backtest_log(run_id, f"Loaded {len(bars)} bars")
        _patch_backtest_run(run_id, progress=30)

        def _engine_progress(current: int, total: int, msg: str) -> None:
            pct = 30 + int((current / total) * 70) if total else 30
            _patch_backtest_run(run_id, progress=min(99, pct))
            if msg:
                _append_backtest_log(run_id, msg)

        engine = MulticoreBacktestEngine()
        result = engine.run_backtest(
            bars=bars,
            strategy_config=strategy,
            backtest_config=config,
            progress_callback=_engine_progress,
        )

        trades = list(result.get("trades", []))
        errors = list(result.get("errors", []))
        # Normalize trade fields the WebUI Trades tab expects so the front-end
        # doesn't have to bridge two shapes.
        normalized_trades = []
        for t in trades:
            normalized_trades.append({
                "entryTimestamp": t.get("entry_time") or t.get("entryTimestamp"),
                "exitTimestamp": t.get("exit_time") or t.get("exitTimestamp"),
                "side": t.get("side") or t.get("direction"),
                "entryPrice": t.get("entry_price") or t.get("entryPrice"),
                "exitPrice": t.get("exit_price") or t.get("exitPrice"),
                "pnl": t.get("pnl"),
                "pnlPercent": t.get("pnl_percent") or t.get("pnlPercent"),
                "exitReason": t.get("exit_reason") or t.get("exitReason"),
                "barsHeld": t.get("bars_held") or t.get("barsHeld"),
            })

        wins = [t for t in trades if (t.get("pnl") or 0) > 0]
        win_rate = (len(wins) / len(trades)) if trades else 0.0
        total_return = sum(float(t.get("pnl_percent") or t.get("pnlPercent") or 0.0) for t in trades)

        metrics = {
            "totalTrades": len(trades),
            "winningTrades": len(wins),
            "losingTrades": len(trades) - len(wins),
            "winRate": win_rate,
            "returnPercentage": total_return,
            "totalBars": int(result.get("total_bars", len(bars))),
            "totalSignals": int(result.get("total_signals", 0)),
        }

        _patch_backtest_run(
            run_id,
            status="error" if errors and not trades else "done",
            progress=100,
            trades=normalized_trades,
            metrics=metrics,
            error="; ".join(errors) if errors else None,
            completedAt=datetime.now(timezone.utc).isoformat(),
        )
        _append_backtest_log(
            run_id,
            f"Backtest completed: {len(trades)} trades, win rate {win_rate:.1%}, total return {total_return:.2f}%",
            level="SYSTEM",
        )
    except Exception as exc:  # noqa: BLE001 — surface to webui caller
        logger.exception("Backtest run %s failed", run_id)
        _patch_backtest_run(
            run_id,
            status="error",
            error=str(exc),
            completedAt=datetime.now(timezone.utc).isoformat(),
        )
        _append_backtest_log(run_id, f"ERROR: {exc}", level="ERROR")


class BacktestStartResponse(BaseModel):
    runId: str
    status: str
    streamUrl: Optional[str] = None


class BacktestRunStatus(BaseModel):
    runId: str
    strategyId: str
    status: str
    progress: int
    trades: list
    metrics: dict
    logs: list
    error: Optional[str] = None
    startedAt: str
    completedAt: Optional[str] = None


@app.post(
    "/strategies/{strategy_id}/backtest",
    response_model=BacktestStartResponse,
    tags=["Backtest"],
    summary="Start a backtest run for a strategy",
)
async def start_backtest(
    strategy_id: str,
    payload: dict,
    _: dict = Depends(require_jwt),
) -> BacktestStartResponse:
    db = _get_sb_db()
    if db is None:
        raise _sb_db_unavailable()

    def _load_strategy() -> Optional[dict]:
        with db.scoped_managers() as scoped:
            return scoped.strategy.get_latest_version(strategy_id)

    try:
        strategy = await asyncio.to_thread(_load_strategy)
    except Exception as exc:
        logger.exception("Failed to load strategy %s for backtest", strategy_id)
        raise HTTPException(status_code=500, detail=f"Failed to load strategy: {exc}") from exc

    if strategy is None:
        raise _strategy_not_found(strategy_id)

    config = dict(payload or {})
    # Webui sends camelCase; the engine accepts both — keep payload intact and
    # let the worker normalize via .get() lookups.

    run_id = _new_backtest_run(strategy_id, config)

    worker = threading.Thread(
        target=_run_backtest_in_thread,
        args=(run_id, strategy, config),
        name=f"backtest-{run_id[:8]}",
        daemon=True,
    )
    worker.start()

    return BacktestStartResponse(
        runId=run_id,
        status="running",
        streamUrl=f"/ws/backtest/{run_id}",
    )


@app.get(
    "/strategies/{strategy_id}/backtest/{run_id}",
    response_model=BacktestRunStatus,
    tags=["Backtest"],
    summary="Get current status / final result of a backtest run",
)
async def get_backtest_status(
    strategy_id: str,
    run_id: str,
    _: dict = Depends(require_jwt),
) -> BacktestRunStatus:
    with _backtest_lock:
        run = _backtest_runs.get(run_id)
        snapshot = dict(run) if run is not None else None

    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run '{run_id}' not found (may have expired or never started)",
        )

    if snapshot.get("strategyId") != strategy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Run does not belong to this strategy",
        )

    snapshot.pop("config", None)
    return BacktestRunStatus(**snapshot)


# ---------------------------------------------------------------------------
# WebSocket helper: subscribe one channel and fan out to one client
# ---------------------------------------------------------------------------


async def _ws_subscribe(websocket: WebSocket, channel: str) -> None:
    """Accept the WebSocket and relay all messages from a Redis pub/sub channel.

    If Redis is unavailable the socket is closed with code 1011 and reason
    ``upstream:redis_unavailable``. A single ``WARNING`` line is logged per
    connection instead of letting redis.ConnectionError propagate as a full
    ASGI stack trace (see BTCAAAAA-30658).
    """
    await websocket.accept()
    async with make_async_client() as r:
        try:
            await r.ping()
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)
        except RedisError as exc:
            logger.warning(
                "WS %s: Redis unavailable (%s); closing 1011", channel, exc
            )
            await websocket.close(code=1011, reason="upstream:redis_unavailable")
            return
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except WebSocketDisconnect:
            pass
        except RedisError as exc:
            logger.warning(
                "WS %s: Redis stream error (%s); closing 1011", channel, exc
            )
            try:
                await websocket.close(code=1011, reason="upstream:redis_unavailable")
            except RuntimeError:
                pass
        except Exception as exc:
            logger.error("WS %s error: %s", channel, exc)
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except RedisError:
                pass


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
