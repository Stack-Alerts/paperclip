"""Backup scheduler — APScheduler AsyncIOScheduler + croniter cron parsing."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter, CroniterBadCronError

logger = logging.getLogger(__name__)


class InvalidCronExpression(ValueError):
    """Raised when a cron expression cannot be parsed."""


def parse_cron(expression: str, count: int = 3) -> list[datetime]:
    """Return the next *count* fire times for a cron expression.

    Raises ``InvalidCronExpression`` for expressions ``croniter`` cannot
    parse. Returned datetimes are tz-aware UTC.
    """
    try:
        it = croniter(expression, datetime.now(timezone.utc))
    except (CroniterBadCronError, KeyError, ValueError) as exc:
        raise InvalidCronExpression(
            f"Invalid cron expression {expression!r}: {exc}"
        ) from exc

    result: list[datetime] = []
    for _ in range(count):
        dt = it.get_next(datetime)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        result.append(dt)
    return result


def validate_cron(expression: str) -> None:
    """Raise :class:`InvalidCronExpression` if *expression* cannot be parsed.

    Convenience wrapper used by the FastAPI layer for input validation —
    no need to allocate a fire-time list just to validate a form field.
    """
    try:
        croniter(expression, datetime.now(timezone.utc))
    except (CroniterBadCronError, KeyError, ValueError) as exc:
        raise InvalidCronExpression(
            f"Invalid cron expression {expression!r}: {exc}"
        ) from exc


RunFn = Callable[[], Coroutine[Any, Any, Any]]


class BackupScheduler:
    """In-process backup scheduler that runs inside the uvicorn event loop.

    Two callbacks are injectable so tests can drive the scheduler without
    backing storage:

    * ``run_backup`` — performs one backup cycle (or a no-op when none is
      configured). Default logs and returns.
    * ``run_retention`` — prunes old backups. Default logs and returns.

    Lifecycle: ``await start()`` loads config and starts APScheduler; on
    boot a single catchup run is dispatched when ``last_run_at`` is set so
    a process restart does not silently miss the previous schedule.
    ``await shutdown(timeout=30)`` stops the scheduler and waits up to
    *timeout* seconds for an in-flight cycle.
    """

    def __init__(
        self,
        run_backup: Optional[RunFn] = None,
        run_retention: Optional[RunFn] = None,
        config_path: Optional[Path] = None,
    ) -> None:
        self._run_backup = run_backup or self._default_backup
        self._run_retention = run_retention or self._default_retention
        self._config_path = config_path
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._cron: str = "0 3 * * *"
        self._job_running = False

    # ------------------------------------------------------------------
    # Lifecycle

    async def start(self) -> None:
        """Load config and start the APScheduler.

        A bad cron expression is logged and the scheduler is **not**
        started — the API still serves requests, the backup cycle just
        does not run on a timer (manual ``run_now`` still works).
        """
        cfg = self._load_config()
        self._cron = self._cron_from_cfg(cfg)

        try:
            validate_cron(self._cron)
        except InvalidCronExpression as exc:
            logger.error(
                "Backup scheduler: bad cron %r — not starting: %s",
                self._cron,
                exc,
            )
            return

        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._execute_backup_cycle,
            trigger=CronTrigger.from_crontab(self._cron, timezone="UTC"),
            id="backup_job",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=None,
        )
        self._scheduler.start()

        last_run_at = self._get_last_run_at(cfg)
        if last_run_at:
            logger.info(
                "Backup scheduler started (last_run_at=%s); catchup run dispatched",
                last_run_at,
            )
            asyncio.get_event_loop().create_task(self._execute_backup_cycle())
        else:
            logger.info("Backup scheduler started with cron %r", self._cron)

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Stop the scheduler, waiting up to *timeout* seconds for a running job.

        Honours the in-flight wait whether or not ``start()`` was called —
        a bare ``run_now()`` without a backing scheduler must still be allowed
        to finish or be cancelled at the deadline.
        """
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)

        deadline = asyncio.get_event_loop().time() + timeout
        while self._job_running:
            if asyncio.get_event_loop().time() >= deadline:
                logger.warning(
                    "Backup scheduler: in-flight job did not finish within %ss",
                    timeout,
                )
                break
            await asyncio.sleep(0.1)

        logger.info("Backup scheduler shut down")

    async def run_now(self) -> None:
        """Trigger an immediate backup cycle, bypassing the cron schedule.

        Honours the no-double-fire invariant: when ``_execute_backup_cycle``
        is already in flight, this call becomes a no-op and logs the skip.
        """
        await self._execute_backup_cycle()

    def reload(self, cfg: Any) -> None:
        """Hot-reload the cron expression from an updated config object/dict."""
        new_cron = self._cron_from_cfg(cfg)
        if new_cron == self._cron:
            return
        try:
            validate_cron(new_cron)
        except InvalidCronExpression as exc:
            logger.warning(
                "Backup scheduler reload: ignoring bad cron %r: %s",
                new_cron,
                exc,
            )
            return

        self._cron = new_cron
        if self._scheduler is not None:
            self._scheduler.reschedule_job(
                "backup_job",
                trigger=CronTrigger.from_crontab(new_cron, timezone="UTC"),
            )
            logger.info("Backup scheduler rescheduled with cron %r", new_cron)

    # ------------------------------------------------------------------
    # Internal

    async def _execute_backup_cycle(self) -> None:
        if self._job_running:
            logger.info("Backup cycle already in progress — skipping")
            return
        self._job_running = True
        try:
            logger.info("Backup cycle starting")
            await self._run_backup()
            await self._run_retention()
            logger.info("Backup cycle complete")
        except Exception:
            logger.exception("Backup cycle failed")
        finally:
            self._job_running = False

    @staticmethod
    def _cron_from_cfg(cfg: Any) -> str:
        if isinstance(cfg, dict):
            value = cfg.get("schedule_cron")
        else:
            value = getattr(cfg, "schedule_cron", None)
        return str(value) if value else "0 3 * * *"

    def _load_config(self) -> Any:
        """Load config — uses *config_path* in tests, default disk location otherwise."""
        if self._config_path is not None:
            from .config import load_config
            return load_config(self._config_path)
        from .config import load_config
        return load_config()

    @staticmethod
    def _get_last_run_at(cfg: Any) -> Optional[str]:
        if isinstance(cfg, dict):
            return cfg.get("last_run_at")
        return getattr(cfg, "last_run_at", None)

    @staticmethod
    async def _default_backup() -> None:
        logger.info("No backup function configured — skipping backup")

    @staticmethod
    async def _default_retention() -> None:
        logger.info("No retention function configured — skipping retention")


# ---------------------------------------------------------------------------
# Module-level singleton — accessed via get_scheduler()
# ---------------------------------------------------------------------------

_scheduler_instance: Optional[BackupScheduler] = None


def get_scheduler() -> BackupScheduler:
    """Return the global ``BackupScheduler`` instance (created lazily)."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackupScheduler()
    return _scheduler_instance


def install_scheduler(scheduler: BackupScheduler) -> None:
    """Replace the cached singleton with a pre-configured instance.

    The FastAPI lifespan uses this to bind runtime callbacks
    (``run_backup``, ``run_retention``) before any endpoint can touch the
    scheduler. Subsequent ``get_scheduler()`` calls return *scheduler*.
    """
    global _scheduler_instance
    _scheduler_instance = scheduler


def reset_scheduler_instance() -> None:
    """Clear the cached singleton — only intended for tests."""
    global _scheduler_instance
    _scheduler_instance = None
