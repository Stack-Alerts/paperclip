"""PostgreSQL engine factory for the Touch Index ingestion workers."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(pool_size: int = 2) -> Engine:
    # POSTGRES_* loaded via pydantic-settings (BTCAAAAA-30576) — .env is the
    # single source of truth, no start.sh allowlist needed.
    from src.optimizer_v3.database.settings import get_database_settings

    s = get_database_settings()
    return create_engine(
        s.database_url(),
        pool_size=pool_size,
        max_overflow=0,
        pool_pre_ping=True,
    )


def health_check(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
