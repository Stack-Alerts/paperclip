"""Backup runtime — wires ``BackupScheduler`` to the configured providers.

``run_backup`` and ``run_retention`` are coroutine callbacks invoked by the
scheduler on every cycle. They read the current on-disk config (so live
edits are honoured without restarting uvicorn), instantiate the configured
providers, and either perform the upload or prune the retention-eligible
backups. With ``providers == []`` both callbacks short-circuit and log —
the scheduler still runs, just nothing useful happens yet.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable

from .config import load_config, write_last_run_at
from .provider import BackupProvider
from .retention import apply_retention

logger = logging.getLogger(__name__)


def _instantiate_providers(specs: Iterable[dict[str, Any]]) -> list[BackupProvider]:
    """Materialise provider instances from a list of config dicts.

    Only the ``local`` kind is recognised for now — the rclone integration
    is wired in P4. Unknown kinds log a warning and are skipped so a stale
    config entry does not crash the cycle.
    """
    providers: list[BackupProvider] = []
    for spec in specs:
        kind = spec.get("kind")
        if kind == "local":
            from .local_provider import LocalProvider

            providers.append(LocalProvider(spec["path"]))
        else:
            logger.warning("Backup runtime: unknown provider kind %r — skipping", kind)
    return providers


async def run_backup() -> None:
    """One backup cycle: upload artifacts to every configured provider.

    With ``providers == []`` (the default) this is a logged no-op so the
    scheduler still completes its cycle and retention still runs.
    """
    cfg = load_config()
    providers = _instantiate_providers(cfg.providers)
    if not providers:
        logger.info(
            "Backup run: scope=%s, no providers configured — skipping upload",
            cfg.scope,
        )
    else:
        logger.info(
            "Backup run: scope=%s, %d provider(s) configured — upload step TBD (P3)",
            cfg.scope,
            len(providers),
        )

    write_last_run_at(datetime.now(timezone.utc).isoformat())


async def run_retention() -> None:
    """Prune old backups after ``run_backup`` completes successfully."""
    cfg = load_config()
    providers = _instantiate_providers(cfg.providers)
    if not providers:
        logger.info("Retention: no providers configured — skipping prune")
        return

    for provider in providers:
        try:
            deleted = apply_retention(
                provider,
                retention_days=cfg.retention_days,
                retention_count=cfg.retention_count,
            )
            logger.info(
                "Retention: pruned %d from %s", len(deleted), type(provider).__name__
            )
        except Exception:
            logger.exception("Retention: prune failed for %s", type(provider).__name__)
