"""Shared fixtures for strategy-builder tests.

Provides ``db_manager_for_testing`` — a real-PostgreSQL ``DatabaseManager``
with a pool large enough to exercise actual concurrent overlap
(``DatabaseManagerFactory.for_testing()`` uses ``pool_size=1`` which would
serialize the BTCAAAAA-29971 regression test on connection checkout).

The fixture skips gracefully when PostgreSQL is not reachable, matching
the ``pg_conn`` / ``db_manager_for_testing`` pattern from
``tests/database/conftest.py``.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def db_manager_for_testing():
    """Session-scoped ``DatabaseManager`` against real PostgreSQL.

    Uses ``pool_size=5, max_overflow=5`` so the
    ``test_concurrent_get_all_strategies_no_rollback_race`` test
    (BTCAAAAA-29971 regression) actually overlaps connections rather than
    serializing on a single-slot pool.
    """
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "optimizer_v3")
    user = os.environ.get("POSTGRES_USER", "optimizer_admin")
    password = os.environ.get("POSTGRES_PASSWORD", "secure_password_change_me")

    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 not installed — skipping real-PostgreSQL tests")

    try:
        conn = psycopg2.connect(
            host=host, port=int(port), dbname=db, user=user, password=password
        )
        conn.close()
    except Exception as exc:
        pytest.skip(f"Cannot connect to PostgreSQL ({host}:{port}/{db}): {exc}")

    from src.optimizer_v3.database.database_manager import DatabaseManager

    connection_string = (
        f"postgresql://{user}:{password}@{host}:{port}/{db}"
    )
    manager = DatabaseManager(
        connection_string,
        echo=False,
        pool_size=5,
        max_overflow=5,
    )
    yield manager
    manager.close()
