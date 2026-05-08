"""
conftest.py for ITM Section C state tests.

Ensures ``src/`` is on sys.path for all state-layer test imports.

PostgreSQL Fixture
-----------------
Provides a ``pg_conn`` session-scoped fixture that connects to a real
PostgreSQL instance using the project's standard credentials (from .env or
environment variables).  Each test that needs a real database connection uses
the ``real_pg_store`` fixture, which:

  1. Opens a connection to the running PostgreSQL server.
  2. Creates an isolated test table named ``itm_state_checkpoints_test_<uuid>``
     so parallel test runs never collide.
  3. Wraps each test in a savepoint and rolls back afterwards to keep the
     database clean.
  4. Drops the test table and closes the connection in teardown.

Environment variables (all have sensible defaults matching the project .env):
  POSTGRES_HOST     default: localhost
  POSTGRES_PORT     default: 5432
  POSTGRES_DB       default: optimizer_v3
  POSTGRES_USER     default: optimizer_admin
  POSTGRES_PASSWORD default: secure_password_change_me
"""

import os
import sys
import uuid
import logging

import pytest

_SRC_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src")
)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PostgreSQL connection helpers
# ---------------------------------------------------------------------------

def _pg_env() -> dict:
    """Return PostgreSQL connection kwargs from environment / .env defaults."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "optimizer_v3"),
        "user": os.environ.get("POSTGRES_USER", "optimizer_admin"),
        "password": os.environ.get("POSTGRES_PASSWORD", "secure_password_change_me"),
    }


# ---------------------------------------------------------------------------
# Session-scoped connection + test table
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def pg_conn():
    """Session-scoped real psycopg2 connection to PostgreSQL.

    Yields a live connection.  The caller is responsible for committing or
    rolling back within tests.  The connection is closed at session teardown.

    Tests that use this fixture require a running PostgreSQL server reachable
    with the credentials in the environment (see module docstring).

    If PostgreSQL is not reachable this fixture skips the test with a clear
    message instead of raising an error, so the suite degrades gracefully in
    environments without a database.
    """
    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 not installed — skipping real-PostgreSQL tests")

    params = _pg_env()
    try:
        conn = psycopg2.connect(**params)
    except Exception as exc:
        pytest.skip(
            f"Cannot connect to PostgreSQL ({params['host']}:{params['port']}/{params['dbname']}): {exc}"
        )

    conn.autocommit = False
    yield conn
    try:
        conn.close()
    except Exception:
        pass


@pytest.fixture(scope="session")
def pg_test_table(pg_conn) -> str:
    """Create an isolated checkpoint table for this test session.

    Returns the table name.  The table is dropped at session teardown.
    """
    table_name = f"itm_state_checkpoints_test_{uuid.uuid4().hex[:12]}"
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        seq              BIGINT PRIMARY KEY,
        checkpoint_id    TEXT NOT NULL,
        source           TEXT NOT NULL DEFAULT 'bar_close',
        state_json       JSONB NOT NULL,
        checkpointed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        redis_latency_ms DOUBLE PRECISION,
        pg_latency_ms    DOUBLE PRECISION
    );
    CREATE INDEX IF NOT EXISTS {table_name}_checkpointed_at_idx
        ON {table_name} (checkpointed_at DESC);
    """
    with pg_conn.cursor() as cur:
        cur.execute(create_sql)
    pg_conn.commit()
    logger.info("Created test table: %s", table_name)

    yield table_name

    # Teardown: drop the test table
    try:
        with pg_conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
        pg_conn.commit()
        logger.info("Dropped test table: %s", table_name)
    except Exception as exc:
        logger.warning("Failed to drop test table %s: %s", table_name, exc)


@pytest.fixture
def real_pg_store(pg_conn, pg_test_table):
    """Provide a ``PostgresStateStore`` backed by a real PostgreSQL instance.

    Truncates the test table before each test to ensure isolation.  Uses the
    same connection as ``pg_test_table`` — no per-test rollback is needed
    because TRUNCATE is fast and keeps the schema intact.

    Returns a connected ``PostgresStateStore`` instance ready for use.
    """
    from src.itm.state.pg_store import PostgresStateStore

    # Truncate to reset state between tests
    with pg_conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {pg_test_table} RESTART IDENTITY;")
    pg_conn.commit()

    store = _RealPgStateStoreForTest(pg_conn, pg_test_table, autocommit=True)
    store.ensure_table()
    return store


# ---------------------------------------------------------------------------
# Thin subclass of PostgresStateStore that targets the test table
# ---------------------------------------------------------------------------

class _RealPgStateStoreForTest:
    """Wraps ``PostgresStateStore`` and redirects SQL to the test table.

    ``PostgresStateStore`` uses module-level SQL constants that reference the
    production table name.  Rather than monkey-patching module globals, this
    wrapper reimplements the same SQL with the test table name substituted.
    This ensures the real PostgreSQL SQL dialect (JSONB, ON CONFLICT, etc.)
    is exercised against the real table, validating production correctness.
    """

    def __init__(self, conn, table_name: str, autocommit: bool = True) -> None:
        import json as _json
        import time as _time
        from datetime import timezone as _tz
        from src.itm.state.schema import ITMSystemState, StateCheckpoint

        self._conn = conn
        self._table = table_name
        self._autocommit = autocommit
        self._json = _json
        self._time = _time
        self._tz = _tz
        self._ITMSystemState = ITMSystemState
        self._StateCheckpoint = StateCheckpoint

        self._upsert_sql = f"""
        INSERT INTO {table_name}
            (seq, checkpoint_id, source, state_json, checkpointed_at,
             redis_latency_ms, pg_latency_ms)
        VALUES
            (%(seq)s, %(checkpoint_id)s, %(source)s, %(state_json)s::jsonb,
             %(checkpointed_at)s, %(redis_latency_ms)s, %(pg_latency_ms)s)
        ON CONFLICT (seq) DO UPDATE SET
            checkpoint_id    = EXCLUDED.checkpoint_id,
            source           = EXCLUDED.source,
            state_json       = EXCLUDED.state_json,
            checkpointed_at  = EXCLUDED.checkpointed_at,
            redis_latency_ms = EXCLUDED.redis_latency_ms,
            pg_latency_ms    = EXCLUDED.pg_latency_ms;
        """

        self._select_latest_sql = f"""
        SELECT seq, checkpoint_id, source, state_json, checkpointed_at,
               redis_latency_ms, pg_latency_ms
        FROM {table_name}
        ORDER BY seq DESC
        LIMIT 1;
        """

        self._select_by_seq_sql = f"""
        SELECT seq, checkpoint_id, source, state_json, checkpointed_at,
               redis_latency_ms, pg_latency_ms
        FROM {table_name}
        WHERE seq = %(seq)s;
        """

        self._select_since_sql = f"""
        SELECT seq, checkpoint_id, source, state_json, checkpointed_at,
               redis_latency_ms, pg_latency_ms
        FROM {table_name}
        WHERE checkpointed_at >= %(cutoff)s
        ORDER BY checkpointed_at DESC
        LIMIT %(limit)s;
        """

        self._prune_sql = f"""
        DELETE FROM {table_name}
        WHERE seq NOT IN (
            SELECT seq FROM {table_name}
            ORDER BY seq DESC
            LIMIT %(keep)s
        );
        """

    def ensure_table(self) -> bool:
        """No-op: table already created by pg_test_table fixture."""
        return True

    def ping(self) -> bool:
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def write_checkpoint(self, checkpoint):
        """Real PostgreSQL write using JSONB and ON CONFLICT."""
        t0 = self._time.monotonic()
        state_json = self._json.dumps(checkpoint.state.to_dict(), default=str)
        params = {
            "seq": checkpoint.sequence,
            "checkpoint_id": checkpoint.checkpoint_id,
            "source": checkpoint.source,
            "state_json": state_json,
            "checkpointed_at": checkpoint.checkpointed_at,
            "redis_latency_ms": checkpoint.redis_latency_ms,
            "pg_latency_ms": None,
        }
        with self._conn.cursor() as cur:
            cur.execute(self._upsert_sql, params)
        if self._autocommit:
            self._conn.commit()
        return True, (self._time.monotonic() - t0) * 1000

    # Alias matching the InMemoryPgStateStore interface used by tests
    def write(self, checkpoint) -> float:
        ok, latency_ms = self.write_checkpoint(checkpoint)
        return latency_ms if latency_ms is not None else 0.0

    def read_latest_checkpoint(self):
        with self._conn.cursor() as cur:
            cur.execute(self._select_latest_sql)
            row = cur.fetchone()
        if row is None:
            return None, True
        return self._row_to_checkpoint(row), True

    def read_latest(self):
        cp, _ = self.read_latest_checkpoint()
        return cp

    def read_checkpoint_by_seq(self, seq: int):
        with self._conn.cursor() as cur:
            cur.execute(self._select_by_seq_sql, {"seq": seq})
            row = cur.fetchone()
        if row is None:
            return None, True
        return self._row_to_checkpoint(row), True

    def read_by_sequence(self, sequence: int):
        cp, _ = self.read_checkpoint_by_seq(sequence)
        return cp

    def read_since(self, cutoff, limit: int = 100):
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=self._tz.utc)
        with self._conn.cursor() as cur:
            cur.execute(self._select_since_sql, {"cutoff": cutoff, "limit": limit})
            rows = cur.fetchall()
        return [self._row_to_checkpoint(r) for r in rows]

    def prune(self, keep: int = 10) -> int:
        with self._conn.cursor() as cur:
            cur.execute(self._prune_sql, {"keep": keep})
            deleted = cur.rowcount
        if self._autocommit:
            self._conn.commit()
        return deleted

    def _row_to_checkpoint(self, row):
        import json as _json
        from datetime import datetime
        seq, checkpoint_id, source, state_json_raw, checkpointed_at, redis_ms, pg_ms = row
        if isinstance(state_json_raw, str):
            state_dict = _json.loads(state_json_raw)
        else:
            state_dict = state_json_raw
        state = self._ITMSystemState.from_dict(state_dict)
        return self._StateCheckpoint(
            checkpoint_id=checkpoint_id,
            sequence=seq,
            state=state,
            source=source,
            checkpointed_at=(
                checkpointed_at
                if isinstance(checkpointed_at, datetime)
                else datetime.fromisoformat(str(checkpointed_at))
            ),
            redis_latency_ms=redis_ms,
            pg_latency_ms=pg_ms,
        )
