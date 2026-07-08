"""Backup subsystem configuration.

Loaded from ``~/.btc-backup/config.json`` (auto-created with defaults on
first read). The scheduler and the API both go through ``load_config()``
so the on-disk schema is the single source of truth.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(os.path.expanduser("~/.btc-backup"))
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "providers": [],
    "schedule_cron": "0 3 * * *",
    "scope": "db",
    "retention_days": 30,
    "retention_count": 100,
}


@dataclass
class BackupConfig:
    """Typed view over the on-disk JSON config used by the scheduler + API."""

    providers: list[dict[str, Any]] = field(default_factory=list)
    schedule_cron: str = "0 3 * * *"
    scope: str = "db"
    retention_days: int = 30
    retention_count: int = 100
    last_run_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def _read_disk_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        logger.warning("Backup config: %s unreadable (%s) — using defaults", path, exc)
        return {}


def _merge_defaults(disk: dict[str, Any]) -> dict[str, Any]:
    """Apply DEFAULT_CONFIG for missing keys without clobbering on-disk values."""
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: v for k, v in disk.items() if v is not None})
    return merged


def load_config(config_path: Path | None = None) -> BackupConfig:
    """Load the backup configuration, returning a typed dataclass.

    Reads from ``config_path`` if given, otherwise the default location
    (``~/.btc-backup/config.json``). A missing file is treated as the
    default config — callers do not need to seed the disk.
    """
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    disk = _read_disk_config(path)
    merged = _merge_defaults(disk)
    return BackupConfig(
        providers=list(merged.get("providers") or []),
        schedule_cron=str(merged.get("schedule_cron") or "0 3 * * *"),
        scope=str(merged.get("scope") or "db"),
        retention_days=int(merged.get("retention_days") or 30),
        retention_count=int(merged.get("retention_count") or 100),
        last_run_at=merged.get("last_run_at"),
    )


def save_config(cfg: BackupConfig, config_path: Path | None = None) -> Path:
    """Persist *cfg* to disk, creating the parent directory if needed."""
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = cfg.to_dict()
    path.write_text(json.dumps(payload, indent=2))
    return path


def write_last_run_at(ts_iso: str, config_path: Path | None = None) -> None:
    """Update only the ``last_run_at`` field, preserving every other setting."""
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    cfg = load_config(path)
    cfg.last_run_at = ts_iso
    save_config(cfg, path)
