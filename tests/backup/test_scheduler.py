"""Tests for ``src/backup/scheduler.py`` + ``src/backup/config.py``.

Covers hard gates 1–5 of the BTCAAAAA-38754 scope:

* Cron parsing — ``parse_cron("*/15 * * * *")`` returns the next 3 fire
  times, spaced exactly 15 min apart and within 1 s of expected.
* Cron validation — invalid expressions raise ``InvalidCronExpression``;
  valid expressions succeed without raising.
* No double-fire — ``_execute_backup_cycle`` is a no-op while another
  cycle is in flight; ``run_now`` honours the same gate.
* Survives restart — a fresh ``BackupScheduler`` whose config has
  ``last_run_at`` set dispatches a catchup task in ``start()``.
* Graceful shutdown — ``shutdown()`` waits up to the timeout for an
  in-flight cycle to finish, then returns cleanly.

Additional behaviour covered: hot ``reload()``, singleton + reset hooks,
and the ``config.py`` round-trip (load → save → load preserves fields).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.backup.config import (
    DEFAULT_CONFIG,
    BackupConfig,
    load_config,
    save_config,
    write_last_run_at,
)
from src.backup.scheduler import (
    BackupScheduler,
    InvalidCronExpression,
    get_scheduler,
    parse_cron,
    reset_scheduler_instance,
    validate_cron,
)


# ---------------------------------------------------------------------------
# Hard gate 1 — cron parsing
# ---------------------------------------------------------------------------


def test_parse_cron_three_fire_times_15min_apart():
    """``parse_cron("*/15 * * * *")`` returns 3 fire times 15 min apart."""
    times = parse_cron("*/15 * * * *", count=3)
    assert len(times) == 3
    for t in times:
        assert t.tzinfo is not None, "fire times must be tz-aware"
        assert t.utcoffset() == timedelta(0), "fire times must be UTC"

    deltas = [(times[i] - times[i - 1]).total_seconds() for i in range(1, 3)]
    assert all(abs(d - 900.0) <= 1.0 for d in deltas), (
        f"fire times not 15 min apart within 1 s: {deltas}"
    )


def test_parse_cron_returns_chrono_ordered():
    """Returned fire times are strictly increasing."""
    times = parse_cron("0 * * * *", count=4)
    assert len(times) == 4
    for a, b in zip(times, times[1:]):
        assert b > a


# ---------------------------------------------------------------------------
# Hard gate 2 — cron validation
# ---------------------------------------------------------------------------


def test_validate_cron_accepts_valid_expression():
    """Valid expressions do not raise."""
    validate_cron("0 3 * * *")
    validate_cron("*/15 * * * *")
    validate_cron("0 0 1 * *")


@pytest.mark.parametrize("bad", ["not a cron", "60 * * * *", ""])
def test_validate_cron_rejects_bad_expression(bad: str):
    """Invalid expressions raise ``InvalidCronExpression``."""
    with pytest.raises(InvalidCronExpression):
        validate_cron(bad)


def test_parse_cron_invalid_raises_invalid_cron_expression():
    """``parse_cron`` propagates ``InvalidCronExpression`` for bad input."""
    with pytest.raises(InvalidCronExpression):
        parse_cron("not a cron")


# ---------------------------------------------------------------------------
# Hard gate 3 — no double-fire
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_backup_cycle_no_double_fire(monkeypatch: pytest.MonkeyPatch):
    """A second cycle while one is in flight is a no-op (logs + skips)."""

    backup_calls = 0
    retention_calls = 0
    release = asyncio.Event()
    started = asyncio.Event()

    async def slow_backup() -> None:
        nonlocal backup_calls
        backup_calls += 1
        started.set()
        await release.wait()

    async def quick_retention() -> None:
        nonlocal retention_calls
        retention_calls += 1

    sched = BackupScheduler(
        run_backup=slow_backup,
        run_retention=quick_retention,
    )

    first = asyncio.create_task(sched._execute_backup_cycle())
    await started.wait()
    assert sched._job_running is True
    assert backup_calls == 1

    second = asyncio.create_task(sched._execute_backup_cycle())
    await asyncio.sleep(0.05)
    assert backup_calls == 1, "second cycle should not enter while first is in flight"

    release.set()
    await asyncio.gather(first, second)
    assert backup_calls == 1
    assert retention_calls == 1
    assert sched._job_running is False


@pytest.mark.asyncio
async def test_run_now_skips_when_job_in_progress():
    """``run_now`` honours the same single-flight gate as the cron path."""
    release = asyncio.Event()
    started = asyncio.Event()

    async def slow_backup() -> None:
        started.set()
        await release.wait()

    sched = BackupScheduler(
        run_backup=slow_backup,
        run_retention=MagicMock(),
    )

    in_flight = asyncio.create_task(sched.run_now())
    await started.wait()

    await sched.run_now()
    assert sched._job_running is True
    release.set()
    await in_flight


# ---------------------------------------------------------------------------
# Hard gate 4 — survives restart via last_run_at catchup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_dispatches_catchup_when_last_run_at_set(tmp_path: Path):
    """A config with ``last_run_at`` triggers one catchup cycle on start."""
    cfg = BackupConfig(
        providers=[],
        schedule_cron="0 3 * * *",
        scope="db",
        retention_days=30,
        retention_count=100,
        last_run_at="2026-07-05T00:00:00+00:00",
    )
    save_config(cfg, tmp_path / "config.json")

    backup_calls = 0
    retention_calls = 0

    async def backup() -> None:
        nonlocal backup_calls
        backup_calls += 1

    async def retention() -> None:
        nonlocal retention_calls
        retention_calls += 1

    sched = BackupScheduler(run_backup=backup, run_retention=retention, config_path=tmp_path / "config.json")
    try:
        await sched.start()
        # Catchup task is dispatched via create_task — give it a chance to run.
        for _ in range(20):
            if backup_calls >= 1 and retention_calls >= 1:
                break
            await asyncio.sleep(0.05)
        assert backup_calls == 1, f"catchup did not call backup: {backup_calls}"
        assert retention_calls == 1, f"catchup did not call retention: {retention_calls}"
    finally:
        await sched.shutdown(timeout=2.0)


@pytest.mark.asyncio
async def test_start_no_catchup_without_last_run_at(tmp_path: Path):
    """Without ``last_run_at``, ``start()`` does NOT trigger an immediate run."""
    cfg_path = tmp_path / "config.json"
    save_config(BackupConfig(), cfg_path)

    backup_calls = 0

    async def backup() -> None:
        nonlocal backup_calls
        backup_calls += 1

    sched = BackupScheduler(run_backup=backup, run_retention=MagicMock(), config_path=cfg_path)
    try:
        await sched.start()
        await asyncio.sleep(0.2)
        assert backup_calls == 0, f"unexpected initial cycle: {backup_calls}"
    finally:
        await sched.shutdown(timeout=2.0)


@pytest.mark.asyncio
async def test_start_with_bad_cron_skips_scheduler(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """A malformed cron expression is logged and the scheduler is not started."""
    cfg_path = tmp_path / "config.json"
    save_config(
        BackupConfig(schedule_cron="not a cron"),
        cfg_path,
    )

    sched = BackupScheduler(
        run_backup=MagicMock(),
        run_retention=MagicMock(),
        config_path=cfg_path,
    )
    with caplog.at_level("ERROR"):
        await sched.start()
    assert sched._scheduler is None
    assert any("bad cron" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# Hard gate 5 — graceful shutdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_waits_for_in_flight_job():
    """``shutdown`` waits for in-flight job, then returns."""
    release = asyncio.Event()
    started = asyncio.Event()

    async def long_backup() -> None:
        started.set()
        await release.wait()

    sched = BackupScheduler(
        run_backup=long_backup,
        run_retention=MagicMock(),
    )

    in_flight = asyncio.create_task(sched._execute_backup_cycle())
    await started.wait()

    shutdown_task = asyncio.create_task(sched.shutdown(timeout=2.0))
    await asyncio.sleep(0.1)
    assert not shutdown_task.done(), "shutdown returned while job in flight"

    release.set()
    await in_flight
    await shutdown_task
    assert sched._job_running is False


@pytest.mark.asyncio
async def test_shutdown_no_in_flight_returns_quickly(tmp_path: Path):
    """With nothing in flight, ``shutdown`` returns essentially immediately."""
    cfg_path = tmp_path / "config.json"
    save_config(BackupConfig(), cfg_path)

    sched = BackupScheduler(run_backup=MagicMock(), run_retention=MagicMock(), config_path=cfg_path)
    await sched.start()
    start = asyncio.get_event_loop().time()
    await sched.shutdown(timeout=2.0)
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 1.0, f"shutdown took too long: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_shutdown_exceeds_timeout_warns(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """If the in-flight job exceeds the timeout, shutdown logs + returns."""
    release = asyncio.Event()
    started = asyncio.Event()

    async def stuck_backup() -> None:
        started.set()
        await release.wait()

    sched = BackupScheduler(run_backup=stuck_backup, run_retention=MagicMock())

    in_flight = asyncio.create_task(sched._execute_backup_cycle())
    await started.wait()

    with caplog.at_level("WARNING"):
        await sched.shutdown(timeout=0.2)
    assert any("in-flight job did not finish" in rec.message for rec in caplog.records)

    release.set()
    await in_flight


# ---------------------------------------------------------------------------
# Hot reload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reload_same_cron_no_op(tmp_path: Path):
    cfg_path = tmp_path / "config.json"
    save_config(BackupConfig(schedule_cron="0 3 * * *"), cfg_path)

    sched = BackupScheduler(run_backup=MagicMock(), run_retention=MagicMock(), config_path=cfg_path)
    await sched.start()
    try:
        sched.reload({"schedule_cron": "0 3 * * *"})
        assert sched._cron == "0 3 * * *"
    finally:
        await sched.shutdown(timeout=2.0)


@pytest.mark.asyncio
async def test_reload_valid_cron_reschedules(tmp_path: Path):
    cfg_path = tmp_path / "config.json"
    save_config(BackupConfig(schedule_cron="0 3 * * *"), cfg_path)

    sched = BackupScheduler(run_backup=MagicMock(), run_retention=MagicMock(), config_path=cfg_path)
    await sched.start()
    try:
        sched.reload({"schedule_cron": "0 4 * * *"})
        assert sched._cron == "0 4 * * *"
    finally:
        await sched.shutdown(timeout=2.0)


def test_reload_invalid_cron_logs_no_change(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    cfg_path = tmp_path / "config.json"
    save_config(BackupConfig(schedule_cron="0 3 * * *"), cfg_path)

    sched = BackupScheduler(run_backup=MagicMock(), run_retention=MagicMock(), config_path=cfg_path)
    sched._cron = "0 3 * * *"
    with caplog.at_level("WARNING"):
        sched.reload({"schedule_cron": "not a cron"})
    assert sched._cron == "0 3 * * *"
    assert any("ignoring bad cron" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# Singleton + reset
# ---------------------------------------------------------------------------


def test_get_scheduler_singleton(monkeypatch: pytest.MonkeyPatch):
    """Multiple calls return the same instance; reset clears the cache."""
    reset_scheduler_instance()
    a = get_scheduler()
    b = get_scheduler()
    assert a is b

    reset_scheduler_instance()
    c = get_scheduler()
    assert c is not a


def test_parse_cron_respects_count():
    """Larger ``count`` returns that many fire times."""
    times = parse_cron("* * * * *", count=5)
    assert len(times) == 5


# ---------------------------------------------------------------------------
# config.py round-trip — written alongside scheduler.py so the heartbeat
# could not be green without both modules wired together.
# ---------------------------------------------------------------------------


def test_load_config_default_when_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A missing config file returns ``DEFAULT_CONFIG`` materialised into a BackupConfig."""
    cfg_path = tmp_path / "missing.json"
    cfg = load_config(cfg_path)
    assert isinstance(cfg, BackupConfig)
    assert cfg.providers == []
    assert cfg.schedule_cron == DEFAULT_CONFIG["schedule_cron"]
    assert cfg.retention_days == DEFAULT_CONFIG["retention_days"]
    assert cfg.retention_count == DEFAULT_CONFIG["retention_count"]


def test_load_config_with_existing_file(tmp_path: Path):
    """Values on disk are honoured."""
    cfg_path = tmp_path / "config.json"
    payload = {
        "providers": [{"kind": "local", "path": "/tmp/x"}],
        "schedule_cron": "0 4 * * *",
        "scope": "config",
        "retention_days": 7,
        "retention_count": 10,
        "last_run_at": "2026-07-05T00:00:00+00:00",
    }
    cfg_path.write_text(json.dumps(payload))

    cfg = load_config(cfg_path)
    assert cfg.providers == [{"kind": "local", "path": "/tmp/x"}]
    assert cfg.schedule_cron == "0 4 * * *"
    assert cfg.scope == "config"
    assert cfg.retention_days == 7
    assert cfg.retention_count == 10
    assert cfg.last_run_at == "2026-07-05T00:00:00+00:00"


def test_save_config_round_trip(tmp_path: Path):
    """``save_config`` writes JSON; ``load_config`` reads it back unchanged."""
    cfg_path = tmp_path / "rt.json"
    src = BackupConfig(
        providers=[{"kind": "rclone"}],
        schedule_cron="0 5 * * *",
        scope="config",
        retention_days=14,
        retention_count=50,
        last_run_at="2026-07-04T12:00:00+00:00",
    )
    save_config(src, cfg_path)

    raw = json.loads(cfg_path.read_text())
    assert raw["schedule_cron"] == "0 5 * * *"
    assert raw["retention_days"] == 14

    dst = load_config(cfg_path)
    assert dst.schedule_cron == src.schedule_cron
    assert dst.retention_days == src.retention_days
    assert dst.retention_count == src.retention_count
    assert dst.last_run_at == src.last_run_at
    assert dst.providers == src.providers


def test_write_last_run_at_preserves_other_fields(tmp_path: Path):
    """Updating only ``last_run_at`` retains providers, cron, retention."""
    cfg_path = tmp_path / "lt.json"
    save_config(
        BackupConfig(
            providers=[{"kind": "local", "path": "/var/backups"}],
            schedule_cron="0 3 * * *",
            scope="db",
            retention_days=30,
            retention_count=100,
        ),
        cfg_path,
    )

    write_last_run_at("2026-07-05T00:00:00+00:00", cfg_path)
    cfg = load_config(cfg_path)

    assert cfg.last_run_at == "2026-07-05T00:00:00+00:00"
    assert cfg.providers == [{"kind": "local", "path": "/var/backups"}]
    assert cfg.schedule_cron == "0 3 * * *"
    assert cfg.retention_days == 30
    assert cfg.retention_count == 100


def test_load_config_malformed_uses_defaults(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """Garbage JSON is logged and ``DEFAULT_CONFIG`` is materialised."""
    cfg_path = tmp_path / "bad.json"
    cfg_path.write_text("not json {")

    with caplog.at_level("WARNING"):
        cfg = load_config(cfg_path)

    assert cfg.schedule_cron == DEFAULT_CONFIG["schedule_cron"]
    assert any("unreadable" in rec.message for rec in caplog.records)
