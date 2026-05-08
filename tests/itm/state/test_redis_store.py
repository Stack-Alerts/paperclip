"""
Tests: Redis Hot-State Store (redis_store.py)
=============================================
Tests the InMemoryRedisStateStore and the real RedisStateStore adapter.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.itm.state.schema import ITMSystemState, StrategyState, StateCheckpoint
from src.itm.state.redis_store import (
    InMemoryRedisStateStore,
    RedisWriteError,
    RedisReadError,
    RedisStoreConfig,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store():
    s = InMemoryRedisStateStore()
    s.connect()
    return s


@pytest.fixture
def sample_checkpoint():
    state = ITMSystemState()
    state.ensure_strategy("strat-1")
    return StateCheckpoint(sequence=5, state=state, source="bar_close")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_connect_enables_ping(self):
        s = InMemoryRedisStateStore()
        assert s.ping() is False
        s.connect()
        assert s.ping() is True

    def test_close_disables_ping(self):
        s = InMemoryRedisStateStore()
        s.connect()
        s.close()
        assert s.ping() is False

    def test_write_before_connect_raises(self):
        s = InMemoryRedisStateStore()
        cp = StateCheckpoint(sequence=1, state=ITMSystemState())
        with pytest.raises(RedisWriteError):
            s.write(cp)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


class TestWrite:
    def test_write_returns_non_negative_latency(self, store, sample_checkpoint):
        latency = store.write(sample_checkpoint)
        assert latency >= 0.0

    def test_write_stores_checkpoint(self, store, sample_checkpoint):
        store.write(sample_checkpoint)
        loaded = store.read_latest()
        assert loaded is not None
        assert loaded.sequence == 5

    def test_write_upserts_same_sequence(self, store):
        cp1 = StateCheckpoint(sequence=5, state=ITMSystemState(), source="bar_close")
        cp2 = StateCheckpoint(sequence=5, state=ITMSystemState(), source="on_demand")
        store.write(cp1)
        store.write(cp2)
        loaded = store.read_latest()
        assert loaded.sequence == 5
        assert loaded.source == "on_demand"


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class TestRead:
    def test_read_latest_empty_returns_none(self, store):
        assert store.read_latest() is None

    def test_read_latest_returns_highest_seq(self, store):
        store.write(StateCheckpoint(sequence=1, state=ITMSystemState()))
        store.write(StateCheckpoint(sequence=5, state=ITMSystemState()))
        store.write(StateCheckpoint(sequence=3, state=ITMSystemState()))
        loaded = store.read_latest()
        assert loaded.sequence == 5

    def test_read_by_sequence(self, store):
        store.write(StateCheckpoint(sequence=10, state=ITMSystemState()))
        store.write(StateCheckpoint(sequence=20, state=ITMSystemState()))
        loaded = store.read_by_sequence(10)
        assert loaded is not None
        assert loaded.sequence == 10

    def test_read_by_sequence_missing_returns_none(self, store):
        assert store.read_by_sequence(999) is None

    def test_read_before_connect_raises(self):
        s = InMemoryRedisStateStore()
        with pytest.raises(RedisReadError):
            s.read_latest()

    def test_serialisation_round_trip_with_strategy(self, store):
        state = ITMSystemState()
        ss = state.ensure_strategy("strat-x")
        ss.heat = Decimal("3.5")
        cp = StateCheckpoint(sequence=1, state=state)
        store.write(cp)
        loaded = store.read_latest()
        assert loaded is not None
        assert "strat-x" in loaded.state.strategies
        assert loaded.state.strategies["strat-x"].heat == Decimal("3.5")


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_all(self, store):
        store.write(StateCheckpoint(sequence=1, state=ITMSystemState()))
        store.write(StateCheckpoint(sequence=2, state=ITMSystemState()))
        store.delete_all()
        assert store.read_latest() is None
