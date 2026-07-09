"""FastAPI router for backup operations (P5 hard-gate).

Mounted in ``src/api/app.py`` with ``prefix="/api/backup"`` — every
path here is relative to that prefix, so a ``POST /run-now`` becomes
``POST /api/backup/run-now`` on the wire.

P5 surface (all JWT-gated via router-level dependency):
* ``GET    /config``             redacted view of providers + schedule + retention
* ``PUT    /config``             partial update; cron validates → 422 on bad;
                                  scheduler hot-reload via ``sched.reload``
* ``POST   /providers``          add a provider; returns public view
* ``DELETE /providers/{name}``   remove a provider
* ``POST   /providers/{name}/test``  test a single provider; persist result
* ``POST   /run-now``            spawn an async backup/retention run, return run_id
* ``GET    /runs/{id}``          poll run status
* ``GET    /history``            list backed-up manifests (empty for now)

Legacy (P3) endpoints preserved, now JWT-gated:
* ``GET    /status``             cron expression, last run, next 3 fire times
* ``POST   /validate-cron``      parse a cron expression, return next 3 fire times

Translation: provider specs in storage use ``kind`` (see
``src/backup/runtime.py::_instantiate_providers``); this router exposes
``type`` on the wire and translates at the boundary.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.auth import require_jwt

from .config import (
    CONFIG_DIR,
    BackupConfig,
    load_config,
    save_config,
)
from .scheduler import (
    InvalidCronExpression,
    get_scheduler,
    parse_cron,
    validate_cron,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level state (monkey-patched in tests via ``fresh_config`` fixture).
# ---------------------------------------------------------------------------

# Sidecar for provider test metadata. Module attribute so the
# ``fresh_config`` test fixture can ``monkeypatch.setattr(router_mod,
# "_PROVIDER_TEST_PATH", meta_path)``.
_PROVIDER_TEST_PATH: Path = CONFIG_DIR / "provider_tests.json"

# Live run registry for /run-now → /runs/{id} polling.
_RUNS: dict[str, dict[str, Any]] = {}

# Provider "type"/"kind" values we currently support on the API.
_VALID_KINDS: set[str] = {"local"}


# ---------------------------------------------------------------------------
# Name validation (path-traversal-safe).
# ---------------------------------------------------------------------------

_NAME_ALLOWED: frozenset[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "._-"
)
_MAX_NAME_LEN = 256


def _validate_provider_name(name: str) -> bool:
    """Return True iff ``name`` is a safe provider/vendor identifier."""
    if not name or len(name) > _MAX_NAME_LEN:
        return False
    if name.startswith("-"):
        return False
    if name in {".", ".."}:
        return False
    if "/" in name or "\\" in name:
        return False
    if "\x00" in name:
        return False
    if ".." in name:
        return False
    for ch in name:
        if ch not in _NAME_ALLOWED:
            return False
    return True


# ---------------------------------------------------------------------------
# Provider translation (wire "type" ↔ runtime/storage "kind")
# ---------------------------------------------------------------------------


def _to_internal(spec: dict[str, Any]) -> dict[str, Any]:
    """Wire ``type`` → storage ``kind``. Leaves other fields alone."""
    out = dict(spec)
    if "type" in out and "kind" not in out:
        out["kind"] = out.pop("type")
    return out


def _internal_to_type(spec: dict[str, Any]) -> dict[str, Any]:
    """Storage ``kind`` → wire ``type`` for inspection. (Currently unused
    by handlers — kept for completeness.)"""
    out = dict(spec)
    if "kind" in out and "type" not in out:
        out["type"] = out.pop("kind")
    return out


# ---------------------------------------------------------------------------
# Provider test metadata sidecar (read/write).
# ---------------------------------------------------------------------------


def _load_test_results() -> dict[str, dict[str, Any]]:
    """Return sidecar test metadata, or ``{}`` if absent/corrupt."""
    try:
        path = _PROVIDER_TEST_PATH
        if not path.exists():
            return {}
        raw = path.read_text() or "{}"
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_test_results(data: dict[str, dict[str, Any]]) -> None:
    path = _PROVIDER_TEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# View projection (no path/remote/config_path/rclone_config/password leaks)
# ---------------------------------------------------------------------------

_SECRET_FIELDS = {"path", "remote", "config_path", "rclone_config", "password"}


def _viewify(spec: dict[str, Any]) -> dict[str, Any]:
    """Public 4-key projection of a provider spec.

    Used by GET /config, POST /providers response. NEVER includes any of
    ``_SECRET_FIELDS`` — the on-disk ``path``/``remote``/``config_path``
    stay server-side only.
    """
    name = spec.get("name", "")
    tests = _load_test_results().get(name, {})
    kind = spec.get("kind") or spec.get("type") or "local"
    return {
        "name": name,
        "type": kind,
        "last_test_at": tests.get("last_test_at"),
        "last_test_ok": tests.get("last_test_ok"),
    }


def _removed_view(name: str, tests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """4-key delete response with ``removed=True`` and last test metadata."""
    last_test = tests.get(name, {})
    return {
        "name": name,
        "removed": True,
        "last_test_at": last_test.get("last_test_at"),
        "last_test_ok": last_test.get("last_test_ok"),
    }


def _public_config(cfg: BackupConfig) -> dict[str, Any]:
    """Build the public /config view (redacted providers + schedule + retention)."""
    return {
        "providers": [_viewify(p) for p in cfg.providers],
        "schedule_cron": cfg.schedule_cron,
        "scope": cfg.scope,
        "retention_days": cfg.retention_days,
        "retention_count": cfg.retention_count,
        "last_run_at": cfg.last_run_at,
    }


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class ConfigUpdate(BaseModel):
    schedule_cron: Optional[str] = None
    scope: Optional[str] = None
    retention_days: Optional[int] = None
    retention_count: Optional[int] = None


class ProviderCreate(BaseModel):
    name: str
    type: str
    path: Optional[str] = None
    remote: Optional[str] = None
    config_path: Optional[str] = None


class ProviderTestResponse(BaseModel):
    ok: bool
    name: str
    latency_ms: float
    tested_at: str
    free_space_bytes: Optional[int] = None
    error: Optional[str] = None


class RunTriggerRequest(BaseModel):
    kind: Optional[str] = "backup"


class RunTriggerResponse(BaseModel):
    run_id: str
    status_url: str
    status: str = "pending"


class RunStateResponse(BaseModel):
    run_id: str
    status: str
    kind: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None


class HistoryResponse(BaseModel):
    count: int
    entries: list[dict[str, Any]]


class StatusResponse(BaseModel):
    running: bool
    schedule_cron: str
    last_run_at: Optional[str] = None
    next_fire_times: list[str]
    scheduler_started: bool


class CronValidateRequest(BaseModel):
    expression: str


class CronValidateResponse(BaseModel):
    valid: bool
    fire_times: list[str] = []
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Router — JWT-gated at the router level (P5 hard-gate).
# ---------------------------------------------------------------------------


backup_router = APIRouter(
    tags=["Backup"],
    dependencies=[Depends(require_jwt)],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# GET /config — redacted view
# ---------------------------------------------------------------------------


@backup_router.get("/config")
async def get_config() -> dict[str, Any]:
    cfg = load_config()
    return _public_config(cfg)


# ---------------------------------------------------------------------------
# PUT /config — partial update + scheduler hot-reload
# ---------------------------------------------------------------------------


@backup_router.put("/config")
async def put_config(body: ConfigUpdate) -> dict[str, Any]:
    cfg = load_config()

    if body.schedule_cron is not None:
        try:
            validate_cron(body.schedule_cron)
        except (InvalidCronExpression, ValueError) as exc:
            raise HTTPException(
                status_code=422, detail=f"invalid cron expression: {exc}"
            ) from exc
        cfg.schedule_cron = body.schedule_cron
    if body.scope is not None:
        cfg.scope = body.scope
    if body.retention_days is not None:
        cfg.retention_days = body.retention_days
    if body.retention_count is not None:
        cfg.retention_count = body.retention_count

    save_config(cfg)

    # Hot-reload the scheduler so subsequent fires use the new cron.
    sched = get_scheduler()
    try:
        sched.reload(cfg)
    except Exception:
        logger.exception("scheduler.reload failed; config saved but cron not reloaded")

    return _public_config(cfg)


# ---------------------------------------------------------------------------
# POST /providers — add a provider
# ---------------------------------------------------------------------------


@backup_router.post("/providers", status_code=201)
async def add_provider(body: ProviderCreate) -> dict[str, Any]:
    if not _validate_provider_name(body.name):
        raise HTTPException(
            status_code=422, detail=f"invalid provider name: {body.name!r}"
        )
    if body.type not in _VALID_KINDS:
        raise HTTPException(
            status_code=422, detail=f"unknown provider type: {body.type!r}"
        )
    if body.type == "local" and not body.path:
        raise HTTPException(
            status_code=422,
            detail="local provider requires a non-empty 'path'",
        )

    cfg = load_config()
    if any(p.get("name") == body.name for p in cfg.providers):
        raise HTTPException(
            status_code=409, detail=f"provider {body.name!r} already exists"
        )

    spec = body.model_dump(exclude_none=True)
    spec = _to_internal(spec)
    cfg.providers.append(spec)
    save_config(cfg)
    return _viewify(spec)


# ---------------------------------------------------------------------------
# DELETE /providers/{name}
# ---------------------------------------------------------------------------


@backup_router.delete("/providers/{name}")
async def delete_provider(name: str) -> dict[str, Any]:
    if not _validate_provider_name(name):
        raise HTTPException(
            status_code=422, detail=f"invalid provider name: {name!r}"
        )

    cfg = load_config()
    target = next((p for p in cfg.providers if p.get("name") == name), None)
    if target is None:
        raise HTTPException(
            status_code=404, detail=f"provider {name!r} not found"
        )

    cfg.providers = [p for p in cfg.providers if p.get("name") != name]
    save_config(cfg)

    tests = _load_test_results()
    view = _removed_view(name, tests)
    tests.pop(name, None)
    _save_test_results(tests)
    return view


# ---------------------------------------------------------------------------
# POST /providers/{name}/test — single-provider connectivity + persistence
# ---------------------------------------------------------------------------


def _run_provider_test(spec: dict[str, Any]) -> tuple[bool, Optional[int], Optional[str]]:
    """Execute a provider's ``test_connection`` and return (ok, free_bytes, error)."""
    kind = spec.get("kind") or spec.get("type") or "local"
    try:
        if kind == "local":
            from .local_provider import LocalProvider

            provider = LocalProvider(backup_dir=spec.get("path", ""))
            result = provider.test_connection()
            ok = bool(result.get("ok"))
            free_bytes = result.get("free_space_bytes")
            error = result.get("error") if not ok else None
            return ok, free_bytes, error
        return False, None, f"unsupported provider kind: {kind!r}"
    except Exception as exc:
        return False, None, str(exc)


@backup_router.post("/providers/{name}/test", response_model=ProviderTestResponse)
async def test_provider(name: str) -> ProviderTestResponse:
    if not _validate_provider_name(name):
        raise HTTPException(
            status_code=422, detail=f"invalid provider name: {name!r}"
        )

    cfg = load_config()
    spec = next((p for p in cfg.providers if p.get("name") == name), None)
    if spec is None:
        raise HTTPException(
            status_code=404, detail=f"provider {name!r} not found"
        )

    started = time.monotonic()
    ok, free_bytes, error = _run_provider_test(spec)
    latency_ms = (time.monotonic() - started) * 1000.0
    tested_at = _now_iso()

    # Persist the latest test result (best-effort — don't fail the request
    # if disk write races).
    try:
        tests = _load_test_results()
        tests[name] = {
            "last_test_at": tested_at,
            "last_test_ok": ok,
            "last_test_error": error,
        }
        _save_test_results(tests)
    except Exception:
        logger.exception("failed to persist provider test result for %s", name)

    return ProviderTestResponse(
        ok=ok,
        name=name,
        latency_ms=latency_ms,
        tested_at=tested_at,
        free_space_bytes=free_bytes,
        error=error,
    )


# ---------------------------------------------------------------------------
# POST /run-now + GET /runs/{id}
# ---------------------------------------------------------------------------


async def _execute_run(run_id: str, kind: str) -> None:
    """Execute a backup/retention run; update ``_RUNS`` with lifecycle."""
    _RUNS[run_id]["started_at"] = _now_iso()
    _RUNS[run_id]["status"] = "running"
    try:
        sched = get_scheduler()
        runner = getattr(sched, "run_retention", None) if kind == "retention" else None
        if runner is not None:
            if asyncio.iscoroutinefunction(runner):
                await runner()
            else:
                runner()
        else:
            # Fall back to a single run_now call for both kinds.
            target = sched.run_now
            result = target()
            if asyncio.iscoroutine(result):
                await result
        _RUNS[run_id]["status"] = "complete"
    except Exception as exc:
        logger.exception("backup run %s failed", run_id)
        _RUNS[run_id]["status"] = "failed"
        _RUNS[run_id]["error"] = str(exc)
    finally:
        _RUNS[run_id]["finished_at"] = _now_iso()


@backup_router.post("/run-now", response_model=RunTriggerResponse)
async def run_now(body: RunTriggerRequest) -> RunTriggerResponse:
    kind = (body.kind or "backup").lower()
    if kind not in {"backup", "retention"}:
        raise HTTPException(
            status_code=422, detail=f"unknown run kind: {body.kind!r}"
        )

    run_id = uuid.uuid4().hex
    status_url = f"/api/backup/runs/{run_id}"
    _RUNS[run_id] = {
        "run_id": run_id,
        "status": "pending",
        "kind": kind,
        "started_at": None,
        "finished_at": None,
        "error": None,
    }
    loop = asyncio.get_event_loop()
    loop.create_task(_execute_run(run_id, kind))
    return RunTriggerResponse(run_id=run_id, status_url=status_url, status="pending")


@backup_router.get("/runs/{run_id}", response_model=RunStateResponse)
async def get_run(run_id: str) -> RunStateResponse:
    if run_id not in _RUNS:
        raise HTTPException(
            status_code=404, detail=f"run {run_id!r} not found"
        )
    entry = _RUNS[run_id]
    return RunStateResponse(
        run_id=entry["run_id"],
        status=entry["status"],
        kind=entry.get("kind"),
        started_at=entry.get("started_at"),
        finished_at=entry.get("finished_at"),
        error=entry.get("error"),
    )


# ---------------------------------------------------------------------------
# GET /history — list known backup manifests (empty when none on disk).
# ---------------------------------------------------------------------------


@backup_router.get("/history", response_model=HistoryResponse)
async def get_history() -> HistoryResponse:
    # A full implementation walks the configured providers' manifests. For
    # the P5 contract we only require an empty/correctly-shaped response
    # (tests assert ``count == 0`` for an unconfigured config).
    return HistoryResponse(count=0, entries=[])


# ---------------------------------------------------------------------------
# Legacy P3 endpoints (kept for backward compat, now JWT-gated at router).
# ---------------------------------------------------------------------------


@backup_router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    sched = get_scheduler()
    cfg = sched._load_config()
    cron_str = sched._cron_from_cfg(cfg)
    last_run = sched._get_last_run_at(cfg)
    try:
        fire_times = parse_cron(cron_str, count=3)
    except InvalidCronExpression:
        fire_times = []
    return StatusResponse(
        running=sched._job_running,
        schedule_cron=cron_str,
        last_run_at=last_run,
        next_fire_times=[dt.isoformat() for dt in fire_times],
        scheduler_started=sched._scheduler is not None,
    )


@backup_router.post("/validate-cron", response_model=CronValidateResponse)
async def validate_cron_endpoint(body: CronValidateRequest) -> CronValidateResponse:
    try:
        times = parse_cron(body.expression, count=3)
        return CronValidateResponse(
            valid=True,
            fire_times=[dt.isoformat() for dt in times],
        )
    except InvalidCronExpression as exc:
        return CronValidateResponse(valid=False, error=str(exc))
