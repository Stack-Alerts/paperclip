"""
Tests: PostgreSQL Cold-Snapshot Store (pg_store.py)
=====================================================
Tests the InMemoryPgStateStore adapter.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.itm.state.schema import ITMSystemState, StateCheckpoint
from src.itm.state.pg_store import (
    InMemoryPgStateStore,
    PgWriteError,
    PgReadError,
    PgStoreConfig,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store():
    s = InMemoryPgStateStore()
    s.connect()
    return s


@pytest.fixture
def sample_checkpoint():
    state = ITMSystemState()
    state.ensure_strategy("strat-1")
    return StateCheckpoint(sequence=7, state=state, source="bar_close")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_connect_and_ping(self):
        s = InMemoryPgStateStore()
        assert s.ping() is False
        s.connect()
        assert s.ping() is True

    def test_close(self):
        s = InMemoryPgStateStore()
        s.connect()
        s.close()
        assert s.ping() is False

    def test_write_before_connect_raises(self):
        s = InMemoryPgStateStore()
        cp = StateCheckpoint(sequence=1, state=ITMSystemState())
        with pytest.raises(PgWriteError):
            s.write(cp)


# ---------------------------------------------------------------------------
# Write and read
# ---------------------------------------------------------------------------


class TestWriteAndRead:
    def test_write_returns_non_negative_latency(self, store, sample_checkpoint):
        latency = store.write(sample_checkpoint)
        assert latency >= 0.0

    def test_read_latest_after_write(self, store, sample_checkpoint):
        store.write(sample_checkpoint)
        loaded = store.read_latest()
        assert loaded is not None
        assert loaded.sequence == 7

    def test_read_latest_returns_highest_seq(self, store):
        store.write(StateCheckpoint(sequence=1, state=ITMSystemState()))
        store.write(StateCheckpoint(sequence=5, state=ITMSystemState()))
        store.write(StateCheckpoint(sequence=3, state=ITMSystemState()))
        loaded = store.read_latest()
        assert loaded.sequence == 5

    def test_read_by_sequence(self, store):
        store.write(StateCheckpoint(sequence=100, state=ITMSystemState()))
        loaded = store.read_by_sequence(100)
        assert loaded is not None
        assert loaded.sequence == 100

    def test_read_by_sequence_missing(self, store):
        assert store.read_by_sequence(42) is None

    def test_read_latest_empty(self, store):
        assert store.read_latest() is None

    def test_read_before_connect_raises(self):
        s = InMemoryPgStateStore()
        with pytest.raises(PgReadError):
            s.read_latest()

    def test_serialisation_round_trip(self, store):
        state = ITMSystemState()
        ss = state.ensure_strategy("s2")
        ss.heat = Decimal("5.5")
        cp = StateCheckpoint(sequence=10, state=state, source="shutdown")
        store.write(cp)
        loaded = store.read_latest()
        assert loaded is not None
        assert "s2" in loaded.state.strategies
        assert loaded.state.strategies["s2"].heat == Decimal("5.5")


# ---------------------------------------------------------------------------
# read_since
# ---------------------------------------------------------------------------


class TestReadSince:
    def test_read_since_filters_by_time(self, store):
        old_ts = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_ts = datetime.now(timezone.utc) - timedelta(minutes=5)

        cp_old = StateCheckpoint(sequence=1, state=ITMSystemState(), source="bar_close")
        cp_old.checkpointed_at = old_ts

        cp_recent = StateCheckpoint(sequence=2, state=ITMSystemState(), source="bar_close")
        cp_recent.checkpointed_at = recent_ts

        store.write(cp_old)
        store.write(cp_recent)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        results = store.read_since(cutoff, limit=10)
        assert len(results) == 1
        assert results[0].sequence == 2

    def test_read_since_respects_limit(self, store):
        for i in range(10):
            store.write(StateCheckpoint(sequence=i + 1, state=ITMSystemState()))
        # All checkpoints are recent; limit to 3
        results = store.read_since(
            datetime.now(timezone.utc) - timedelta(hours=1), limit=3
        )
        assert len(results) <= 3

    def test_read_since_before_connect_raises(self):
        s = InMemoryPgStateStore()
        with pytest.raises(PgReadError):
            s.read_since(datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# prune
# ---------------------------------------------------------------------------


class TestPrune:
    def test_prune_removes_old_checkpoints(self, store):
        for i in range(10):
            store.write(StateCheckpoint(sequence=i + 1, state=ITMSystemState()))
        deleted = store.prune(keep=3)
        assert deleted == 7
        # Latest 3 should remain
        assert store.read_by_sequence(8) is not None
        assert store.read_by_sequence(9) is not None
        assert store.read_by_sequence(10) is not None
        assert store.read_by_sequence(1) is None

    def test_prune_noop_when_within_keep(self, store):
        store.write(StateCheckpoint(sequence=1, state=ITMSystemState()))
        store.write(StateCheckpoint(sequence=2, state=ITMSystemState()))
        deleted = store.prune(keep=10)
        assert deleted == 0

    def test_prune_keeps_correct_count(self, store):
        for i in range(5):
            store.write(StateCheckpoint(sequence=i + 1, state=ITMSystemState()))
        store.prune(keep=2)
        latest = store.read_latest()
        assert latest.sequence == 5
