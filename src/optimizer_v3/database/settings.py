"""
Database Settings (pydantic-settings)
BTCAAAAA-30576

Single source of truth for POSTGRES_* connection config. Loads from process
environment first, then falls back to repo-root .env via pydantic-settings.

Use this in place of raw `os.getenv('POSTGRES_*')` so that adding a new
required DB env var in `.env` does NOT also require a `start.sh` allowlist
amendment. Adding the variable to .env + a field here is enough.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_REPO_ROOT = Path(__file__).resolve().parents[3]


def _candidate_env_files() -> Tuple[str, ...]:
    """Return .env candidates in precedence order (later wins in pydantic-settings).

    Mirrors `python-dotenv`'s historical "walk up from CWD" search and adds the
    repo-rooted .env that lives next to this package. The repo-rooted file is
    listed first so that values in a CWD-local .env (typically a developer
    override) win when both exist.
    """
    seen: set = set()
    candidates: list = []

    repo_env = _REPO_ROOT / ".env"
    if repo_env.exists():
        candidates.append(str(repo_env))
        seen.add(str(repo_env.resolve()))

    cwd_env_var = os.getenv("BTE_DOTENV_FILE")
    if cwd_env_var:
        p = Path(cwd_env_var).expanduser()
        if p.exists() and str(p.resolve()) not in seen:
            candidates.append(str(p))
            seen.add(str(p.resolve()))

    cwd = Path.cwd()
    for parent in (cwd, *cwd.parents):
        cand = parent / ".env"
        if cand.exists() and str(cand.resolve()) not in seen:
            candidates.append(str(cand))
            seen.add(str(cand.resolve()))
            break

    return tuple(candidates)


class DatabaseSettings(BaseSettings):
    """
    PostgreSQL connection settings.

    Field names match historical POSTGRES_* env vars one-for-one. Defaults
    preserve the previous raw-`os.getenv` defaults so behaviour is unchanged
    when a value is unset.
    """

    model_config = SettingsConfigDict(
        env_file=_candidate_env_files(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core connection
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "optimizer_v3"
    POSTGRES_USER: str = "optimizer_admin"
    POSTGRES_PASSWORD: str = ""

    # SSL
    POSTGRES_SSL: bool = False
    POSTGRES_SSL_CERT_PATH: Optional[str] = None
    POSTGRES_SSL_KEY_PATH: Optional[str] = None

    # Pool
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_RECYCLE: int = 3600

    # Performance
    POSTGRES_SHARED_BUFFERS: str = "1GB"
    POSTGRES_WORK_MEM: str = "32MB"
    POSTGRES_MAINTENANCE_WORK_MEM: str = "256MB"
    POSTGRES_EFFECTIVE_CACHE_SIZE: str = "3GB"
    POSTGRES_WAL_BUFFERS: str = "16MB"
    POSTGRES_CHECKPOINT_TIMEOUT: str = "10min"
    POSTGRES_RANDOM_PAGE_COST: float = 1.1
    POSTGRES_EFFECTIVE_IO_CONCURRENCY: int = 200

    # Monitoring
    POSTGRES_LOG_MIN_DURATION: int = 1000
    POSTGRES_LOG_CONNECTIONS: bool = False
    POSTGRES_LOG_DISCONNECTIONS: bool = False

    # Backup
    POSTGRES_BACKUP_PATH: str = "/tmp/optimizer_v3_backups"
    POSTGRES_BACKUP_RETENTION_DAYS: int = 30
    POSTGRES_BACKUP_COMPRESSION: bool = True

    # ai_consultant readonly pool (used by src/ai_consultant/db/query_engine.py)
    AI_READONLY_PASSWORD: str = ""
    AI_READONLY_POOL_SIZE: int = 5
    AI_READONLY_MAX_OVERFLOW: int = 10

    def database_url(self) -> str:
        """Render the full `postgresql://user:password@host:port/db` DSN."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def readonly_url(self) -> str:
        """DSN for the ai_readonly role (used by ai_consultant query engine)."""
        return (
            f"postgresql://ai_readonly:{self.AI_READONLY_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    """Cached singleton accessor — pydantic re-reads .env on every fresh call."""
    return DatabaseSettings()


def reload_database_settings() -> DatabaseSettings:
    """Drop the cached singleton (test/admin only). Returns the fresh instance."""
    get_database_settings.cache_clear()
    return get_database_settings()
