"""FastAPI router for backup operations: ``/run-now``, ``/status``,
``/validate-cron``.

Mounted in ``src/api/app.py`` with ``prefix="/api/backup"`` — every path
here is relative to that prefix so a ``POST /run-now`` becomes
``POST /api/backup/run-now`` on the wire.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from .scheduler import (
    InvalidCronExpression,
    get_scheduler,
    parse_cron,
)

logger = logging.getLogger(__name__)

backup_router = APIRouter(tags=["Backup"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class _RunNowResponse(BaseModel):
    triggered: bool
    skipped_reason: Optional[str] = None
    note: str = "run_now dispatched; the backup cycle runs as an asyncio task"


class _StatusResponse(BaseModel):
    running: bool
    schedule_cron: str
    last_run_at: Optional[str] = None
    next_fire_times: list[str]
    scheduler_started: bool


class _CronValidateRequest(BaseModel):
    expression: str


class _CronValidateResponse(BaseModel):
    valid: bool
    fire_times: list[str] = []
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints (no JWT for P3 — internal admin tooling per board direction)
# ---------------------------------------------------------------------------


@backup_router.post("/run-now", response_model=_RunNowResponse)
async def run_now() -> _RunNowResponse:
    """Trigger an immediate backup cycle regardless of the cron schedule.

    Fire-and-forget: the actual backup runs as an ``asyncio`` task so the
    HTTP caller returns immediately. A re-entrant call while a cycle is in
    progress is a no-op (returns ``triggered=False`` with a reason).
    """
    sched = get_scheduler()
    if sched._job_running:
        return _RunNowResponse(
            triggered=False,
            skipped_reason="backup cycle already running",
        )
    asyncio.get_event_loop().create_task(sched.run_now())
    return _RunNowResponse(triggered=True)


@backup_router.get("/status", response_model=_StatusResponse)
async def status() -> _StatusResponse:
    """Return scheduler status: cron expression, last run, next 3 fire times."""
    sched = get_scheduler()
    cfg = sched._load_config()
    cron_str = sched._cron_from_cfg(cfg)
    last_run = sched._get_last_run_at(cfg)
    try:
        fire_times = parse_cron(cron_str, count=3)
    except InvalidCronExpression:
        fire_times = []
    return _StatusResponse(
        running=sched._job_running,
        schedule_cron=cron_str,
        last_run_at=last_run,
        next_fire_times=[dt.isoformat() for dt in fire_times],
        scheduler_started=sched._scheduler is not None,
    )


@backup_router.post("/validate-cron", response_model=_CronValidateResponse)
async def validate_cron_endpoint(body: _CronValidateRequest) -> _CronValidateResponse:
    """Validate a cron expression and return the next 3 fire times on success."""
    try:
        times = parse_cron(body.expression, count=3)
        return _CronValidateResponse(
            valid=True,
            fire_times=[dt.isoformat() for dt in times],
        )
    except InvalidCronExpression as exc:
        return _CronValidateResponse(valid=False, error=str(exc))
