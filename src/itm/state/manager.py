"""
ITM StateManager
================
Orchestrates dual-write (Redis hot + PostgreSQL cold) checkpointing with a
circuit-breaker pattern for write failures.

API design (from integration spec)
-----------------------------------
::

    manager = StateManager(redis_store=redis, pg_store=pg, config=StateManagerConfig(...))
    manager.connect()
    cp = manager.checkpoint(state, source="bar_close")
    latest = manager.load_latest()
    health = manager.health_check()

Circuit breaker states
----------------------
* ``CLOSED``    — healthy, both stores being written.
* ``OPEN``      — Redis has failed; writes go to PostgreSQL only.
* ``HALF_OPEN`` — probing Redis after cooldown.

Raises
------
CheckpointError — when both Redis and PostgreSQL writes fail.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .schema import ITMSystemState, StateCheckpoint

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CheckpointError(Exception):
    """Raised when both Redis and PostgreSQL writes fail on checkpoint."""


# ---------------------------------------------------------------------------
# Circuit breaker state
# ---------------------------------------------------------------------------


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class StateManagerConfig:
    """Configuration for the StateManager.

    Parameters
    ----------
    instance_id:
        Human-readable identifier for this manager instance (for logging).
    cb_failure_threshold:
        Number of consecutive Redis failures before opening the circuit.
    cb_cooldown_seconds:
        Seconds to wait before probing Redis again (HALF_OPEN transition).
    """

    instance_id: str = "default"
    cb_failure_threshold: int = 3
    cb_cooldown_seconds: float = 30.0


# ---------------------------------------------------------------------------
# StateManager
# ---------------------------------------------------------------------------


class StateManager:
    """Manages ITM system state persistence with dual-write + circuit breaker.

    Parameters
    ----------
    redis_store:
        Optional Redis store (``InMemoryRedisStateStore`` or real adapter).
        Must have ``connect/close/ping/write/read_latest`` methods.
    pg_store:
        Optional PostgreSQL store (``InMemoryPgStateStore`` or real adapter).
        Must have ``connect/close/ping/write/read_latest`` methods.
    config:
        ``StateManagerConfig`` with circuit-breaker settings.
    """

    def __init__(
        self,
        redis_store=None,
        pg_store=None,
        config: Optional[StateManagerConfig] = None,
    ) -> None:
        self._redis = redis_store
        self._pg = pg_store
        self._config = config or StateManagerConfig()

        # Circuit breaker
        self._cb_state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self._cb_failure_count: int = 0
        self._cb_last_failure_at: Optional[float] = None

        # Sequence counter
        self._seq: int = 0
        self._connected: bool = False

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def connect(self) -> None:
        """Connect to backing stores."""
        if self._redis is not None:
            self._redis.connect()
        if self._pg is not None:
            self._pg.connect()
        self._connected = True
        logger.info(
            "StateManager[%s] connected (redis=%s, pg=%s)",
            self._config.instance_id,
            self._redis is not None,
            self._pg is not None,
        )

    def close(self) -> None:
        """Disconnect from backing stores."""
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception as exc:  # noqa: BLE001
                logger.error("StateManager: redis close failed: %s", exc)
        if self._pg is not None:
            try:
                self._pg.close()
            except Exception as exc:  # noqa: BLE001
                logger.error("StateManager: pg close failed: %s", exc)
        self._connected = False

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def circuit_breaker_state(self) -> CircuitBreakerState:
        return self._cb_state

    @property
    def sequence(self) -> int:
        return self._seq

    # ------------------------------------------------------------------ #
    # Checkpoint                                                           #
    # ------------------------------------------------------------------ #

    def checkpoint(
        self,
        state: Optional[ITMSystemState] = None,
        source: str = "bar_close",
    ) -> StateCheckpoint:
        """Write a checkpoint to Redis (hot) and PostgreSQL (cold).

        Parameters
        ----------
        state:
            The ``ITMSystemState`` to persist.  If None, an empty state is used.
        source:
            Human-readable trigger label: 'bar_close', 'on_demand', 'shutdown'.

        Returns
        -------
        StateCheckpoint

        Raises
        ------
        CheckpointError
            If both Redis and PostgreSQL writes fail.
        """
        if state is None:
            state = ITMSystemState()

        # Apply daily resets
        reset_ids = state.apply_daily_resets()
        if reset_ids:
            logger.info("Daily PnL reset applied for strategies: %s", reset_ids)

        self._seq += 1
        state.checkpoint_seq = self._seq
        state.touch()

        cp = StateCheckpoint(
            sequence=self._seq,
            state=state,
            source=source,
            checkpointed_at=datetime.now(timezone.utc),
        )

        redis_ok = False
        redis_ms = None
        pg_ok = False
        pg_ms = None

        # Redis write (hot state)
        if self._redis is not None and self._should_try_redis():
            try:
                t0 = time.monotonic()
                redis_ms = self._redis.write(cp)
                if redis_ms is None:
                    redis_ms = (time.monotonic() - t0) * 1000
                redis_ok = True
                self._on_redis_success()
            except Exception as exc:  # noqa: BLE001
                logger.error("StateManager: Redis write failed: %s", exc)
                self._on_redis_failure()

        # PostgreSQL write (cold/durable)
        if self._pg is not None:
            try:
                t0 = time.monotonic()
                pg_ms = self._pg.write(cp)
                if pg_ms is None:
                    pg_ms = (time.monotonic() - t0) * 1000
                pg_ok = True
            except Exception as exc:  # noqa: BLE001
                logger.error("StateManager: PG write failed: %s", exc)

        cp.redis_latency_ms = redis_ms
        cp.pg_latency_ms = pg_ms

        if not redis_ok and not pg_ok:
            raise CheckpointError(
                f"Checkpoint seq={self._seq} failed: both Redis and PostgreSQL writes failed"
            )

        if redis_ms is not None and redis_ms > 500:
            logger.warning(
                "Checkpoint seq=%d Redis latency %.1fms exceeds 500ms SLA",
                self._seq,
                redis_ms,
            )

        logger.info(
            "Checkpoint seq=%d written (source=%s, redis_ok=%s %.1fms, pg_ok=%s %.1fms)",
            self._seq,
            source,
            redis_ok,
            redis_ms or 0.0,
            pg_ok,
            pg_ms or 0.0,
        )

        return cp

    def force_checkpoint(self, state: Optional[ITMSystemState] = None) -> StateCheckpoint:
        """Trigger an immediate checkpoint outside of bar-close cadence."""
        return self.checkpoint(state=state, source="on_demand")

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def load_latest(self) -> Optional[StateCheckpoint]:
        """Load the most recent checkpoint from Redis, falling back to PostgreSQL.

        Returns None if no checkpoint exists.
        """
        # Try Redis first (hot state)
        if self._redis is not None:
            try:
                cp = self._redis.read_latest()
                if cp is not None:
                    logger.info(
                        "StateManager: loaded from Redis seq=%d", cp.sequence
                    )
                    cp._load_source = "redis"
                    self._last_load_source = "redis"
                    return cp
            except Exception as exc:  # noqa: BLE001
                logger.warning("StateManager: Redis read_latest failed: %s", exc)

        # Fall back to PostgreSQL
        if self._pg is not None:
            try:
                cp = self._pg.read_latest()
                if cp is not None:
                    logger.info(
                        "StateManager: loaded from PostgreSQL seq=%d", cp.sequence
                    )
                    cp._load_source = "postgres"
                    self._last_load_source = "postgres"
                    return cp
            except Exception as exc:  # noqa: BLE001
                logger.warning("StateManager: PG read_latest failed: %s", exc)

        return None

    # ------------------------------------------------------------------ #
    # Health check                                                         #
    # ------------------------------------------------------------------ #

    def health_check(self) -> dict:
        """Return a health status dict for monitoring.

        Returns
        -------
        dict with keys:
            redis.ping: bool
            redis.circuit_breaker: str
            postgres.ping: bool
            sequence: int
        """
        redis_ping = False
        if self._redis is not None:
            try:
                redis_ping = bool(self._redis.ping())
            except Exception:  # noqa: BLE001
                pass

        pg_ping = False
        if self._pg is not None:
            try:
                pg_ping = bool(self._pg.ping())
            except Exception:  # noqa: BLE001
                pass

        return {
            "redis": {
                "ping": redis_ping,
                "circuit_breaker": self._cb_state.value,
            },
            "postgres": {
                "ping": pg_ping,
            },
            "sequence": self._seq,
        }

    # ------------------------------------------------------------------ #
    # Circuit breaker internals                                            #
    # ------------------------------------------------------------------ #

    def _should_try_redis(self) -> bool:
        if self._cb_state == CircuitBreakerState.CLOSED:
            return True
        if self._cb_state == CircuitBreakerState.OPEN:
            elapsed = time.monotonic() - (self._cb_last_failure_at or 0.0)
            if elapsed >= self._config.cb_cooldown_seconds:
                logger.info(
                    "Redis circuit breaker: OPEN → HALF_OPEN after %.1fs cooldown", elapsed
                )
                self._cb_state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN — try once

    def _on_redis_success(self) -> None:
        if self._cb_state != CircuitBreakerState.CLOSED:
            logger.info("Redis circuit breaker: recovered → CLOSED")
        self._cb_state = CircuitBreakerState.CLOSED
        self._cb_failure_count = 0
        self._cb_last_failure_at = None

    def _on_redis_failure(self) -> None:
        self._cb_failure_count += 1
        self._cb_last_failure_at = time.monotonic()
        if self._cb_failure_count >= self._config.cb_failure_threshold:
            if self._cb_state != CircuitBreakerState.OPEN:
                logger.error(
                    "Redis circuit breaker: OPEN after %d consecutive failures",
                    self._cb_failure_count,
                )
            self._cb_state = CircuitBreakerState.OPEN
        else:
            logger.warning(
                "Redis write failed (%d/%d before CB opens)",
                self._cb_failure_count,
                self._config.cb_failure_threshold,
            )
