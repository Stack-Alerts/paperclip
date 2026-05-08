"""
Tests: StateManager (manager.py)
=================================
Tests the dual-write orchestration, circuit breaker, checkpoint sequencing,
checkpoint latency, and crash/recovery simulation.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.itm.state.schema import ITMSystemState, StrategyState
from src.itm.state.manager import (
    StateManager,
    StateManagerConfig,
    CircuitBreakerState,
    CheckpointError,
)
from src.itm.state.redis_store import InMemoryRedisStateStore
from src.itm.state.pg_store import InMemoryPgStateStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def redis():
    r = InMemoryRedisStateStore()
    r.connect()
    return r


@pytest.fixture
def pg():
    p = InMemoryPgStateStore()
    p.connect()
    return p


@pytest.fixture
def manager(redis, pg):
    mgr = StateManager(redis_store=redis, pg_store=pg)
    mgr.connect()
    return mgr


@pytest.fixture
def redis_only_manager(redis):
    mgr = StateManager(redis_store=redis, pg_store=None)
    mgr.connect()
    return mgr


@pytest.fixture
def pg_only_manager(pg):
    mgr = StateManager(redis_store=None, pg_store=pg)
    mgr.connect()
    return mgr


# ---------------------------------------------------------------------------
# Basic checkpoint
# ---------------------------------------------------------------------------


class TestBasicCheckpoint:
    def test_checkpoint_increments_seq(self, manager):
        assert manager.sequence == 0
        manager.checkpoint()
        assert manager.sequence == 1
        manager.checkpoint()
        assert manager.sequence == 2

    def test_checkpoint_returns_checkpoint_object(self, manager):
        cp = manager.checkpoint(source="bar_close")
        assert cp is not None
        assert cp.source == "bar_close"
        assert cp.sequence == 1

    def test_checkpoint_writes_to_redis(self, manager, redis):
        manager.checkpoint()
        assert redis.read_latest() is not None

    def test_checkpoint_writes_to_pg(self, manager, pg):
        manager.checkpoint()
        assert pg.read_latest() is not None

    def test_force_checkpoint_trigger_label(self, manager):
        state = ITMSystemState()
        cp = manager.force_checkpoint(state)
        assert cp.source == "on_demand"

    def test_checkpoint_latency_measured(self, manager):
        cp = manager.checkpoint()
        assert cp.redis_latency_ms is not None
        assert cp.pg_latency_ms is not None

    def test_checkpoint_latency_under_500ms(self, manager):
        """With in-memory fakes, checkpoint should be well under 500ms."""
        cp = manager.checkpoint()
        assert cp.redis_latency_ms < 500
        assert cp.pg_latency_ms < 500

    def test_checkpoint_with_state(self, manager):
        state = ITMSystemState()
        state.ensure_strategy("s1")
        cp = manager.checkpoint(state)
        assert cp.state is state

    def test_checkpoint_source_shutdown(self, manager):
        cp = manager.checkpoint(source="shutdown")
        assert cp.source == "shutdown"

    def test_redis_only_manager_checkpoint(self, redis_only_manager):
        cp = redis_only_manager.checkpoint()
        assert cp.redis_ok
        assert not cp.pg_ok

    def test_pg_only_manager_checkpoint(self, pg_only_manager):
        cp = pg_only_manager.checkpoint()
        assert cp.pg_ok
        assert not cp.redis_ok


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def test_initial_state_closed(self, manager):
        assert manager.circuit_breaker_state == CircuitBreakerState.CLOSED

    def test_circuit_opens_after_threshold_failures(self, pg):
        """After cb_failure_threshold Redis failures, CB opens."""
        class FailingRedis:
            def connect(self): pass
            def write(self, cp): raise ConnectionError("Redis down")
            def read_latest(self): return None
            def ping(self): return False
            def close(self): pass

        config = StateManagerConfig(cb_failure_threshold=3, cb_cooldown_seconds=60.0)
        mgr = StateManager(redis_store=FailingRedis(), pg_store=pg, config=config)
        mgr.connect()

        for _ in range(3):
            cp = mgr.checkpoint()
            assert cp.pg_ok

        assert mgr.circuit_breaker_state == CircuitBreakerState.OPEN

    def test_circuit_recovers_after_cooldown(self, pg):
        """CB moves OPEN → HALF_OPEN after cooldown, then CLOSED on success."""
        call_count = [0]

        class FailThenSucceedRedis:
            def connect(self): pass
            def write(self, cp):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise ConnectionError("Redis down")
                import time
                return time.monotonic() * 0  # 0ms latency

            def read_latest(self): return None
            def ping(self): return True
            def close(self): pass

        config = StateManagerConfig(
            cb_failure_threshold=1,
            cb_cooldown_seconds=0.05,
        )
        mgr = StateManager(redis_store=FailThenSucceedRedis(), pg_store=pg, config=config)
        mgr.connect()
        mgr.checkpoint()  # trips CB open
        assert mgr.circuit_breaker_state == CircuitBreakerState.OPEN

        time.sleep(0.1)
        mgr.checkpoint()  # should probe in HALF_OPEN and succeed → CLOSED
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED

    def test_both_stores_fail_raises_checkpoint_error(self):
        class FailingRedis:
            def connect(self): pass
            def write(self, cp): raise ConnectionError("Redis down")
            def read_latest(self): return None
            def ping(self): return False
            def close(self): pass

        class FailingPg:
            def connect(self): pass
            def write(self, cp): raise Exception("PG down")
            def read_latest(self): return None
            def ping(self): return False
            def close(self): pass
            def ensure_table(self): pass

        config = StateManagerConfig(cb_failure_threshold=1, cb_cooldown_seconds=60.0)
        mgr = StateManager(redis_store=FailingRedis(), pg_store=FailingPg(), config=config)
        mgr.connect()

        with pytest.raises(CheckpointError):
            mgr.checkpoint()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_health_check_structure(self, manager):
        health = manager.health_check()
        assert health["redis"]["ping"] is True
        assert health["redis"]["circuit_breaker"] == "closed"
        assert health["postgres"]["ping"] is True
        assert health["sequence"] == 0

    def test_health_check_sequence_increments(self, manager):
        manager.checkpoint()
        manager.checkpoint()
        health = manager.health_check()
        assert health["sequence"] == 2

    def test_health_check_no_stores(self):
        mgr = StateManager()
        health = mgr.health_check()
        assert health["redis"]["ping"] is False
        assert health["postgres"]["ping"] is False


# ---------------------------------------------------------------------------
# load_latest
# ---------------------------------------------------------------------------


class TestLoadLatest:
    def test_load_latest_returns_none_before_checkpoint(self, manager):
        latest = manager.load_latest()
        assert latest is None

    def test_load_latest_returns_checkpoint(self, manager):
        manager.checkpoint()
        latest = manager.load_latest()
        assert latest is not None
        assert latest.sequence == 1

    def test_load_latest_returns_highest_seq(self, manager):
        manager.checkpoint()
        manager.checkpoint()
        manager.checkpoint()
        latest = manager.load_latest()
        assert latest.sequence == 3


# ---------------------------------------------------------------------------
# Daily reset integration
# ---------------------------------------------------------------------------


class TestDailyResetInCheckpoint:
    def test_daily_reset_applied_on_checkpoint(self, manager):
        state = ITMSystemState()
        ss = state.ensure_strategy("s1")
        ss.daily_pnl = Decimal("-200")
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        ss.daily_pnl_date = yesterday.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        manager.checkpoint(state)
        assert ss.daily_pnl == Decimal("0")


# ---------------------------------------------------------------------------
# Crash and recovery simulation
# ---------------------------------------------------------------------------


class TestCrashRecovery:
    def test_crash_and_reload_state_from_redis(self):
        """Write state, destroy manager, reload from same stores."""
        redis = InMemoryRedisStateStore()
        pg = InMemoryPgStateStore()
        redis.connect()
        pg.connect()

        # Session 1 — write state before "crash"
        mgr1 = StateManager(redis_store=redis, pg_store=pg)
        mgr1.connect()
        state = ITMSystemState()
        ss = state.ensure_strategy("crash-strat")
        ss.heat = Decimal("3.5")
        mgr1.checkpoint(state)
        crashed_seq = mgr1.sequence

        # Session 2 — new manager reads from same in-memory stores
        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        latest = mgr2.load_latest()
        assert latest is not None
        assert latest.sequence == crashed_seq
        assert "crash-strat" in latest.state.strategies
        assert latest.state.strategies["crash-strat"].heat == Decimal("3.5")

    def test_crash_and_reload_from_postgres(self):
        """When Redis is empty, reload from PostgreSQL."""
        pg = InMemoryPgStateStore()
        pg.connect()

        redis1 = InMemoryRedisStateStore()
        redis1.connect()
        mgr1 = StateManager(redis_store=redis1, pg_store=pg)
        mgr1.connect()
        state = ITMSystemState()
        ss = state.ensure_strategy("pg-strat")
        ss.heat = Decimal("7.0")
        mgr1.checkpoint(state)
        crashed_seq = mgr1.sequence

        # New manager with fresh empty Redis, same PG
        redis2 = InMemoryRedisStateStore()
        redis2.connect()
        mgr2 = StateManager(redis_store=redis2, pg_store=pg)
        mgr2.connect()
        latest = mgr2.load_latest()
        assert latest is not None
        assert latest.sequence == crashed_seq
        assert "pg-strat" in latest.state.strategies
