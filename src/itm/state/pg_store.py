"""
ITM PostgreSQL Cold-Snapshot Adapter
=====================================
Provides a durable cold-storage adapter for ITM state checkpoints using
PostgreSQL (or TimescaleDB).

Design goals
------------
* Durable, append-only checkpoint table.
* Latest snapshot query is fast: ``ORDER BY seq DESC LIMIT 1``.
* Schema is self-bootstrapping: call ``ensure_table()`` on startup.
 * Connection passed in at construction (facilitates DI and testing with fakes /
  real PostgreSQL test fixtures — see tests/itm/state/conftest.py).
* JSON column type for the full state payload.
* Falls back gracefully — every public method returns success flags.

Table schema
------------
::

    CREATE TABLE itm_state_checkpoints (
        seq              BIGINT PRIMARY KEY,
        checkpoint_id    TEXT NOT NULL,
        trigger          TEXT NOT NULL DEFAULT 'bar_close',
        state_json       JSONB NOT NULL,
        written_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        redis_latency_ms DOUBLE PRECISION,
        pg_latency_ms    DOUBLE PRECISION
    );

Usage
-----
::

    import psycopg2
    from itm.state.pg_store import PostgresStateStore

    conn = psycopg2.connect(dsn="postgresql://user:pass@localhost/btc")
    store = PostgresStateStore(conn=conn)
    store.ensure_table()

    ok, latency_ms = store.write_checkpoint(checkpoint)
    checkpoint, ok = store.read_latest_checkpoint()
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

from .schema import ITMSystemState, StateCheckpoint

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS itm_state_checkpoints (
    seq              BIGINT PRIMARY KEY,
    checkpoint_id    TEXT NOT NULL,
    source           TEXT NOT NULL DEFAULT 'bar_close',
    state_json       JSONB NOT NULL,
    checkpointed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    redis_latency_ms DOUBLE PRECISION,
    pg_latency_ms    DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS itm_state_checkpoints_checkpointed_at_idx
    ON itm_state_checkpoints (checkpointed_at DESC);
"""

_UPSERT_SQL = """
INSERT INTO itm_state_checkpoints
    (seq, checkpoint_id, source, state_json, checkpointed_at, redis_latency_ms, pg_latency_ms)
VALUES
    (%(seq)s, %(checkpoint_id)s, %(source)s, %(state_json)s,
     %(checkpointed_at)s, %(redis_latency_ms)s, %(pg_latency_ms)s)
ON CONFLICT (seq) DO UPDATE SET
    checkpoint_id    = EXCLUDED.checkpoint_id,
    source           = EXCLUDED.source,
    state_json       = EXCLUDED.state_json,
    checkpointed_at  = EXCLUDED.checkpointed_at,
    redis_latency_ms = EXCLUDED.redis_latency_ms,
    pg_latency_ms    = EXCLUDED.pg_latency_ms;
"""

_SELECT_LATEST_SQL = """
SELECT seq, checkpoint_id, source, state_json, checkpointed_at,
       redis_latency_ms, pg_latency_ms
FROM itm_state_checkpoints
ORDER BY seq DESC
LIMIT 1;
"""

_SELECT_BY_SEQ_SQL = """
SELECT seq, checkpoint_id, source, state_json, checkpointed_at,
       redis_latency_ms, pg_latency_ms
FROM itm_state_checkpoints
WHERE seq = %(seq)s;
"""


class PostgresStateStore:
    """Cold-storage PostgreSQL adapter for ITM state checkpoints.

    Parameters
    ----------
    conn:
        A live ``psycopg2.connection`` (or compatible) object.
        The caller is responsible for connection lifecycle.
    autocommit:
        If True, each write is immediately committed.
        Defaults to True for simplicity; set False if caller manages
        transactions explicitly.
    """

    def __init__(self, conn, autocommit: bool = True) -> None:
        self._conn = conn
        self._autocommit = autocommit

    # ------------------------------------------------------------------ #
    # Schema                                                               #
    # ------------------------------------------------------------------ #

    def ensure_table(self) -> bool:
        """Create the checkpoint table and index if they don't exist.

        Returns True on success, False on error.
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(_CREATE_TABLE_SQL)
            if self._autocommit:
                self._conn.commit()
            logger.info("PostgreSQL: itm_state_checkpoints table ensured")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("PostgresStateStore.ensure_table failed: %s", exc)
            try:
                self._conn.rollback()
            except Exception:  # noqa: BLE001
                pass
            return False

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def write_checkpoint(
        self, checkpoint: StateCheckpoint
    ) -> Tuple[bool, Optional[float]]:
        """Persist a ``StateCheckpoint`` to PostgreSQL.

        Returns
        -------
        (success: bool, latency_ms: float | None)
        """
        t0 = time.monotonic()
        try:
            state_json = json.dumps(checkpoint.state.to_dict(), default=str)
            params = {
                "seq": checkpoint.sequence,
                "checkpoint_id": checkpoint.checkpoint_id,
                "source": checkpoint.source,
                "state_json": state_json,
                "checkpointed_at": checkpoint.checkpointed_at,
                "redis_latency_ms": checkpoint.redis_latency_ms,
                "pg_latency_ms": None,  # will update after measuring
            }
            with self._conn.cursor() as cur:
                cur.execute(_UPSERT_SQL, params)
            if self._autocommit:
                self._conn.commit()
            latency_ms = (time.monotonic() - t0) * 1000
            logger.debug(
                "PostgreSQL checkpoint written in %.1fms (seq=%d)",
                latency_ms,
                checkpoint.sequence,
            )
            return True, latency_ms
        except Exception as exc:  # noqa: BLE001
            logger.error("PostgresStateStore.write_checkpoint failed: %s", exc)
            try:
                self._conn.rollback()
            except Exception:  # noqa: BLE001
                pass
            return False, None

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def read_latest_checkpoint(self) -> Tuple[Optional[StateCheckpoint], bool]:
        """Read the most recent checkpoint from PostgreSQL.

        Returns
        -------
        (checkpoint: StateCheckpoint | None, success: bool)
            checkpoint=None when table is empty or on error.
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(_SELECT_LATEST_SQL)
                row = cur.fetchone()
            if row is None:
                logger.info("PostgreSQL: no checkpoints found in table")
                return None, True
            cp = self._row_to_checkpoint(row)
            logger.info(
                "PostgreSQL: loaded checkpoint seq=%d checkpointed_at=%s",
                cp.sequence,
                cp.checkpointed_at.isoformat(),
            )
            return cp, True
        except Exception as exc:  # noqa: BLE001
            logger.error("PostgresStateStore.read_latest_checkpoint failed: %s", exc)
            return None, False

    def read_checkpoint_by_seq(self, seq: int) -> Tuple[Optional[StateCheckpoint], bool]:
        """Read a specific checkpoint by sequence number."""
        try:
            with self._conn.cursor() as cur:
                cur.execute(_SELECT_BY_SEQ_SQL, {"seq": seq})
                row = cur.fetchone()
            if row is None:
                return None, True
            return self._row_to_checkpoint(row), True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "PostgresStateStore.read_checkpoint_by_seq(%d) failed: %s", seq, exc
            )
            return None, False

    # ------------------------------------------------------------------ #
    # Health                                                               #
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Return True if the PostgreSQL connection is healthy."""
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_checkpoint(row: tuple) -> StateCheckpoint:
        """Convert a DB row tuple to a ``StateCheckpoint``."""
        seq, checkpoint_id, source, state_json_raw, checkpointed_at, redis_ms, pg_ms = row
        # state_json may be a dict (psycopg2 JSONB auto-decode) or a str
        if isinstance(state_json_raw, str):
            state_dict = json.loads(state_json_raw)
        else:
            state_dict = state_json_raw
        state = ITMSystemState.from_dict(state_dict)
        return StateCheckpoint(
            checkpoint_id=checkpoint_id,
            sequence=seq,
            state=state,
            source=source,
            checkpointed_at=checkpointed_at if isinstance(checkpointed_at, datetime) else datetime.fromisoformat(str(checkpointed_at)),
            redis_latency_ms=redis_ms,
            pg_latency_ms=pg_ms,
        )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PgWriteError(Exception):
    """Raised by InMemoryPgStateStore when a write fails (e.g. not connected)."""


class PgReadError(Exception):
    """Raised by InMemoryPgStateStore when a read fails (e.g. not connected)."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


from dataclasses import dataclass as _dataclass


@_dataclass
class PgStoreConfig:
    """Configuration for InMemoryPgStateStore.

    Attributes
    ----------
    max_checkpoints: Maximum checkpoints to keep in memory.  0 = unlimited.
    """

    max_checkpoints: int = 0


# ---------------------------------------------------------------------------
# InMemoryPgStateStore
# ---------------------------------------------------------------------------


class InMemoryPgStateStore:
    """Pure in-memory PostgreSQL state store for testing and paper-trading use.

    Implements a compatible interface to ``PostgresStateStore`` but stores all
    data in a Python dict — no external dependencies.

    Extended features vs Redis:
    - ``read_since(cutoff, limit)`` — return checkpoints newer than *cutoff*
    - ``prune(keep)`` — remove all but the latest *keep* checkpoints

    Usage
    -----
    ::

        store = InMemoryPgStateStore()
        store.connect()
        latency = store.write(checkpoint)
        loaded = store.read_latest()
        results = store.read_since(cutoff, limit=100)
        deleted = store.prune(keep=10)
    """

    def __init__(self, config: "PgStoreConfig | None" = None) -> None:
        self._config = config or PgStoreConfig()
        self._store: dict[int, StateCheckpoint] = {}
        self._connected: bool = False

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def connect(self) -> None:
        """Connect (activate) the in-memory store."""
        self._connected = True
        logger.debug("InMemoryPgStateStore: connected")

    def close(self) -> None:
        """Disconnect the in-memory store."""
        self._connected = False
        logger.debug("InMemoryPgStateStore: closed")

    def ping(self) -> bool:
        """Return True if the store is connected."""
        return self._connected

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def write(self, checkpoint: StateCheckpoint) -> float:
        """Write *checkpoint* to the in-memory store.

        Returns
        -------
        float
            Write latency in milliseconds (always >= 0).

        Raises
        ------
        PgWriteError
            If the store is not connected.
        """
        if not self._connected:
            raise PgWriteError("InMemoryPgStateStore is not connected")
        t0 = time.monotonic()
        import copy
        self._store[checkpoint.sequence] = copy.deepcopy(checkpoint)
        latency_ms = (time.monotonic() - t0) * 1000
        logger.debug(
            "InMemoryPgStateStore: wrote checkpoint seq=%d in %.3fms",
            checkpoint.sequence,
            latency_ms,
        )
        return latency_ms

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def read_latest(self) -> Optional[StateCheckpoint]:
        """Return the checkpoint with the highest sequence number, or None.

        Raises
        ------
        PgReadError
            If the store is not connected.
        """
        if not self._connected:
            raise PgReadError("InMemoryPgStateStore is not connected")
        if not self._store:
            return None
        import copy
        return copy.deepcopy(self._store[max(self._store)])

    def read_by_sequence(self, sequence: int) -> Optional[StateCheckpoint]:
        """Return the checkpoint for *sequence*, or None if not found."""
        if not self._connected:
            raise PgReadError("InMemoryPgStateStore is not connected")
        import copy
        cp = self._store.get(sequence)
        return copy.deepcopy(cp) if cp is not None else None

    def read_since(
        self, cutoff: datetime, limit: int = 100
    ) -> list[StateCheckpoint]:
        """Return checkpoints written at or after *cutoff*, newest first.

        Parameters
        ----------
        cutoff:
            UTC datetime; only checkpoints with checkpointed_at >= cutoff are returned.
        limit:
            Maximum number of checkpoints to return.
        """
        if not self._connected:
            raise PgReadError("InMemoryPgStateStore is not connected")
        import copy
        # Ensure cutoff is timezone-aware
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        results = []
        for seq in sorted(self._store.keys(), reverse=True):
            cp = self._store[seq]
            ts = cp.checkpointed_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                results.append(copy.deepcopy(cp))
                if len(results) >= limit:
                    break
        return results

    # ------------------------------------------------------------------ #
    # Management                                                           #
    # ------------------------------------------------------------------ #

    def prune(self, keep: int = 10) -> int:
        """Remove all but the latest *keep* checkpoints.

        Returns
        -------
        int
            Number of checkpoints deleted.
        """
        if len(self._store) <= keep:
            return 0
        sorted_seqs = sorted(self._store.keys(), reverse=True)
        to_delete = sorted_seqs[keep:]
        for seq in to_delete:
            del self._store[seq]
        logger.debug(
            "InMemoryPgStateStore: pruned %d checkpoints, kept %d",
            len(to_delete),
            keep,
        )
        return len(to_delete)
