"""
ITM Redis Hot-State Adapter
============================
Provides a thin, fast Redis adapter for writing and reading ``ITMSystemState``
checkpoints.

Design goals
------------
* Sub-500ms write latency per checkpoint.
* Atomic write: uses ``SET key value EX ttl`` — single round-trip.
* No connection pooling at this layer — caller is responsible for providing a
  connected Redis client (facilitates dependency injection and testing with
  fakes).
* JSON serialisation via ``json`` stdlib — no third-party deps beyond redis-py.
* Fallback-safe: every public method returns success/failure flags so callers
  (StateManager) can implement circuit-breaker logic without catching exceptions
  from this layer.

Key layout
----------
``itm:state:snapshot``         — latest full ITMSystemState JSON (overwritten each checkpoint)
``itm:state:checkpoint:{seq}`` — optional per-seq checkpoint archive (TTL-controlled)

Redis is the *hot* store — data is authoritative only for up to 24h after the
last write.  PostgreSQL is the cold/durable store.

Usage
-----
::

    import redis
    from itm.state.redis_store import RedisStateStore

    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    store = RedisStateStore(client=client, snapshot_ttl_seconds=86400)

    ok, latency_ms = store.write_snapshot(state)
    state, ok = store.read_latest_snapshot()
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional, Tuple

from .schema import ITMSystemState

logger = logging.getLogger(__name__)

# Redis key constants
_KEY_SNAPSHOT = "itm:state:snapshot"
_KEY_CHECKPOINT_PREFIX = "itm:state:checkpoint"
_KEY_META = "itm:state:meta"

# Default TTL — keep hot state for 25h (covers one full day + buffer)
_DEFAULT_TTL_SECONDS = 90_000


class RedisStateStore:
    """Hot-state Redis adapter for ITM state checkpoints.

    Parameters
    ----------
    client:
        A connected ``redis.Redis`` (or compatible) instance with
        ``decode_responses=True``.
    snapshot_ttl_seconds:
        TTL in seconds for the snapshot key.  Defaults to 90000 (~25h).
    archive_checkpoints:
        If True, also write a per-seq archive key (for debugging).
        Defaults to False to keep write overhead minimal.
    archive_ttl_seconds:
        TTL for archive checkpoint keys (only used when archive_checkpoints=True).
    """

    def __init__(
        self,
        client,  # redis.Redis — typed loosely to avoid hard redis dep at import
        snapshot_ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        archive_checkpoints: bool = False,
        archive_ttl_seconds: int = 3600,
    ) -> None:
        self._client = client
        self._snapshot_ttl = snapshot_ttl_seconds
        self._archive = archive_checkpoints
        self._archive_ttl = archive_ttl_seconds

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def write_snapshot(
        self, state: ITMSystemState
    ) -> Tuple[bool, Optional[float]]:
        """Serialise and write *state* to Redis.

        Returns
        -------
        (success: bool, latency_ms: float | None)
            success=True and latency_ms set on successful write.
            success=False and latency_ms=None on any error.
        """
        t0 = time.monotonic()
        try:
            payload = json.dumps(state.to_dict(), default=str)
            self._client.set(_KEY_SNAPSHOT, payload, ex=self._snapshot_ttl)
            # Update meta key with checkpoint sequence and timestamp
            meta = {
                "checkpoint_seq": state.checkpoint_seq,
                "updated_at": state.updated_at.isoformat(),
            }
            self._client.set(_KEY_META, json.dumps(meta), ex=self._snapshot_ttl)
            # Optionally archive per-seq
            if self._archive:
                arch_key = f"{_KEY_CHECKPOINT_PREFIX}:{state.checkpoint_seq}"
                self._client.set(arch_key, payload, ex=self._archive_ttl)
            latency_ms = (time.monotonic() - t0) * 1000
            if latency_ms > 500:
                logger.warning(
                    "Redis checkpoint latency %.1fms exceeds 500ms target "
                    "(seq=%d)",
                    latency_ms,
                    state.checkpoint_seq,
                )
            else:
                logger.debug(
                    "Redis checkpoint written in %.1fms (seq=%d)",
                    latency_ms,
                    state.checkpoint_seq,
                )
            return True, latency_ms
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis write_snapshot failed: %s", exc)
            return False, None

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def read_latest_snapshot(self) -> Tuple[Optional[ITMSystemState], bool]:
        """Read the latest snapshot from Redis.

        Returns
        -------
        (state: ITMSystemState | None, success: bool)
            state is None when the key does not exist or on error.
        """
        try:
            raw = self._client.get(_KEY_SNAPSHOT)
            if raw is None:
                logger.info("Redis: no snapshot found at %s", _KEY_SNAPSHOT)
                return None, True  # key missing is a valid "empty" state
            state = ITMSystemState.from_dict(json.loads(raw))
            logger.info(
                "Redis: loaded snapshot seq=%d updated_at=%s",
                state.checkpoint_seq,
                state.updated_at.isoformat(),
            )
            return state, True
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis read_latest_snapshot failed: %s", exc)
            return None, False

    def read_checkpoint_seq(self, seq: int) -> Tuple[Optional[ITMSystemState], bool]:
        """Read a specific archived checkpoint by sequence number.

        Only works when ``archive_checkpoints=True`` was set.
        """
        try:
            arch_key = f"{_KEY_CHECKPOINT_PREFIX}:{seq}"
            raw = self._client.get(arch_key)
            if raw is None:
                return None, True
            state = ITMSystemState.from_dict(json.loads(raw))
            return state, True
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis read_checkpoint_seq(%d) failed: %s", seq, exc)
            return None, False

    # ------------------------------------------------------------------ #
    # Meta / health                                                        #
    # ------------------------------------------------------------------ #

    def get_meta(self) -> Optional[dict]:
        """Return metadata about the latest checkpoint (seq, timestamp)."""
        try:
            raw = self._client.get(_KEY_META)
            return json.loads(raw) if raw else None
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis get_meta failed: %s", exc)
            return None

    def ping(self) -> bool:
        """Return True if the Redis connection is healthy."""
        try:
            return bool(self._client.ping())
        except Exception:  # noqa: BLE001
            return False

    def flush_all_itm_keys(self) -> int:
        """Delete all ``itm:state:*`` keys.  For testing / teardown only.

        Returns number of keys deleted.
        """
        try:
            keys = self._client.keys("itm:state:*")
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis flush_all_itm_keys failed: %s", exc)
            return 0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RedisWriteError(Exception):
    """Raised by InMemoryRedisStateStore when a write fails (e.g. not connected)."""


class RedisReadError(Exception):
    """Raised by InMemoryRedisStateStore when a read fails (e.g. not connected)."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


from dataclasses import dataclass as _dataclass


@_dataclass
class RedisStoreConfig:
    """Configuration for InMemoryRedisStateStore.

    Attributes
    ----------
    ttl_seconds: TTL for checkpoint keys.  Defaults to 90000.
    """

    ttl_seconds: int = 90_000


# ---------------------------------------------------------------------------
# InMemoryRedisStateStore
# ---------------------------------------------------------------------------


class InMemoryRedisStateStore:
    """Pure in-memory Redis state store for testing and paper-trading use.

    Implements the same interface as a real Redis-backed store but stores all
    data in a Python dict — no external dependencies.

    Usage
    -----
    ::

        store = InMemoryRedisStateStore()
        store.connect()
        latency = store.write(checkpoint)
        loaded = store.read_latest()
    """

    def __init__(self, config: "RedisStoreConfig | None" = None) -> None:
        self._config = config or RedisStoreConfig()
        self._store: dict[int, "StateCheckpoint"] = {}
        self._connected: bool = False

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def connect(self) -> None:
        """Connect (activate) the in-memory store."""
        self._connected = True
        logger.debug("InMemoryRedisStateStore: connected")

    def close(self) -> None:
        """Disconnect the in-memory store."""
        self._connected = False
        logger.debug("InMemoryRedisStateStore: closed")

    def ping(self) -> bool:
        """Return True if the store is connected."""
        return self._connected

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def write(self, checkpoint: "StateCheckpoint") -> float:
        """Write *checkpoint* to the in-memory store.

        Returns
        -------
        float
            Write latency in milliseconds (always >= 0).

        Raises
        ------
        RedisWriteError
            If the store is not connected.
        """
        if not self._connected:
            raise RedisWriteError("InMemoryRedisStateStore is not connected")
        t0 = time.monotonic()
        # Deep-copy the state to simulate serialisation isolation
        import copy
        self._store[checkpoint.sequence] = copy.deepcopy(checkpoint)
        latency_ms = (time.monotonic() - t0) * 1000
        logger.debug(
            "InMemoryRedisStateStore: wrote checkpoint seq=%d in %.3fms",
            checkpoint.sequence,
            latency_ms,
        )
        return latency_ms

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def read_latest(self) -> "StateCheckpoint | None":
        """Return the checkpoint with the highest sequence number, or None.

        Raises
        ------
        RedisReadError
            If the store is not connected.
        """
        if not self._connected:
            raise RedisReadError("InMemoryRedisStateStore is not connected")
        if not self._store:
            return None
        import copy
        return copy.deepcopy(self._store[max(self._store)])

    def read_by_sequence(self, sequence: int) -> "StateCheckpoint | None":
        """Return the checkpoint for *sequence*, or None if not found.

        Raises
        ------
        RedisReadError
            If the store is not connected.
        """
        if not self._connected:
            raise RedisReadError("InMemoryRedisStateStore is not connected")
        import copy
        cp = self._store.get(sequence)
        return copy.deepcopy(cp) if cp is not None else None

    # ------------------------------------------------------------------ #
    # Management                                                           #
    # ------------------------------------------------------------------ #

    def delete_all(self) -> None:
        """Remove all checkpoints from the in-memory store."""
        self._store.clear()
        logger.debug("InMemoryRedisStateStore: all checkpoints deleted")
