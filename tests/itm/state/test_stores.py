"""
Tests for ITM Section C: Redis and PostgreSQL in-memory stores.

Coverage:
- InMemoryRedisStateStore: connect, write, read_latest, read_by_sequence, ping, close
- InMemoryPgStateStore: same interface + read_since + prune
- Checkpoint latency is measurable (write returns float >= 0)
- Multiple checkpoints stored; latest returned correctly
- Serialisation round-trip through store
- Disconnected store raises correct errors
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from src.itm.domain.entities import Instrument, Position, PositionDirection, PositionEntry
from src.itm.state.schema import ITMSystemState, StateCheckpoint
from src.itm.state.redis_store import (
    InMemoryRedisStateStore,
    RedisWriteError,
    RedisReadError,
    RedisStoreConfig,
)
from src.itm.state.pg_store import (
    InMemoryPgStateStore,
    PgWriteError,
    PgReadError,
    PgStoreConfig,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_checkpoint(seq: int, source: str = "manual") -> StateCheckpoint:
    state = ITMSystemState()
    return StateCheckpoint(sequence=seq, state=state, source=source)


def make_checkpoint_with_position(seq: int) -> StateCheckpoint:
    state = ITMSystemState()
    instr = Instrument.btc_usdt_perp()
    pos = Position(instrument=instr, direction=PositionDirection.LONG)
    pos.add_entry(PositionEntry(order_id="o1", quantity=Decimal("0.1"), price=Decimal("50000")))
    state.positions[pos.position_id] = pos
    return StateCheckpoint(sequence=seq, state=state, source="bar_close")


# ---------------------------------------------------------------------------
# InMemoryRedisStateStore tests
# ---------------------------------------------------------------------------


class TestInMemoryRedisStateStore:
    def test_connect_and_ping(self):
        store = InMemoryRedisStateStore()
        assert store.ping() is False
        store.connect()
        assert store.ping() is True

    def test_close(self):
        store = InMemoryRedisStateStore()
        store.connect()
        store.close()
        assert store.ping() is False

    def test_write_returns_non_negative_latency(self):
        store = InMemoryRedisStateStore()
        store.connect()
        cp = make_checkpoint(1)
        latency = store.write(cp)
        assert latency >= 0.0

    def test_read_latest_after_write(self):
        store = InMemoryRedisStateStore()
        store.connect()
        cp = make_checkpoint(1)
        store.write(cp)
        loaded = store.read_latest()
        assert loaded is not None
        assert loaded.sequence == 1

    def test_read_latest_returns_highest_sequence(self):
        store = InMemoryRedisStateStore()
        store.connect()
        store.write(make_checkpoint(1))
        store.write(make_checkpoint(5))
        store.write(make_checkpoint(3))
        loaded = store.read_latest()
        assert loaded.sequence == 5

    def test_read_by_sequence(self):
        store = InMemoryRedisStateStore()
        store.connect()
        store.write(make_checkpoint(10))
        store.write(make_checkpoint(20))
        loaded = store.read_by_sequence(10)
        assert loaded is not None
        assert loaded.sequence == 10

    def test_read_by_sequence_missing_returns_none(self):
        store = InMemoryRedisStateStore()
        store.connect()
        assert store.read_by_sequence(999) is None

    def test_read_latest_empty_returns_none(self):
        store = InMemoryRedisStateStore()
        store.connect()
        assert store.read_latest() is None

    def test_write_not_connected_raises(self):
        store = InMemoryRedisStateStore()
        with pytest.raises(RedisWriteError):
            store.write(make_checkpoint(1))

    def test_serialisation_round_trip(self):
        store = InMemoryRedisStateStore()
        store.connect()
        cp = make_checkpoint_with_position(7)
        store.write(cp)
        loaded = store.read_latest()
        assert len(loaded.state.positions) == 1

    def test_delete_all(self):
        store = InMemoryRedisStateStore()
        store.connect()
        store.write(make_checkpoint(1))
        store.write(make_checkpoint(2))
        store.delete_all()
        assert store.read_latest() is None

    def test_upsert_same_sequence(self):
        """Writing same sequence twice should overwrite."""
        store = InMemoryRedisStateStore()
        store.connect()
        cp1 = make_checkpoint(5)
        cp2 = make_checkpoint(5)
        store.write(cp1)
        store.write(cp2)
        loaded = store.read_latest()
        assert loaded.sequence == 5


# ---------------------------------------------------------------------------
# InMemoryPgStateStore tests
# ---------------------------------------------------------------------------


class TestInMemoryPgStateStore:
    def test_connect_and_ping(self):
        store = InMemoryPgStateStore()
        assert store.ping() is False
        store.connect()
        assert store.ping() is True

    def test_close(self):
        store = InMemoryPgStateStore()
        store.connect()
        store.close()
        assert store.ping() is False

    def test_write_returns_non_negative_latency(self):
        store = InMemoryPgStateStore()
        store.connect()
        latency = store.write(make_checkpoint(1))
        assert latency >= 0.0

    def test_read_latest(self):
        store = InMemoryPgStateStore()
        store.connect()
        store.write(make_checkpoint(1))
        store.write(make_checkpoint(3))
        loaded = store.read_latest()
        assert loaded.sequence == 3

    def test_read_by_sequence(self):
        store = InMemoryPgStateStore()
        store.connect()
        store.write(make_checkpoint(100))
        loaded = store.read_by_sequence(100)
        assert loaded is not None
        assert loaded.sequence == 100

    def test_read_by_sequence_missing(self):
        store = InMemoryPgStateStore()
        store.connect()
        assert store.read_by_sequence(42) is None

    def test_read_latest_empty(self):
        store = InMemoryPgStateStore()
        store.connect()
        assert store.read_latest() is None

    def test_write_disconnected_raises(self):
        store = InMemoryPgStateStore()
        with pytest.raises(PgWriteError):
            store.write(make_checkpoint(1))

    def test_read_since(self):
        store = InMemoryPgStateStore()
        store.connect()

        old_ts = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_ts = datetime.now(timezone.utc) - timedelta(minutes=5)

        cp_old = make_checkpoint(1)
        cp_old.checkpointed_at = old_ts
        cp_recent = make_checkpoint(2)
        cp_recent.checkpointed_at = recent_ts

        store.write(cp_old)
        store.write(cp_recent)

        # Only the recent one should be returned when since = 1 hour ago
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        results = store.read_since(cutoff, limit=10)
        assert all(r.sequence == 2 for r in results)
        assert len(results) == 1

    def test_prune_removes_old_checkpoints(self):
        store = InMemoryPgStateStore()
        store.connect()
        for i in range(10):
            store.write(make_checkpoint(i + 1))
        deleted = store.prune(keep=3)
        assert deleted == 7
        # Latest 3 sequences should remain
        assert store.read_by_sequence(8) is not None
        assert store.read_by_sequence(9) is not None
        assert store.read_by_sequence(10) is not None
        assert store.read_by_sequence(1) is None

    def test_prune_noop_when_within_keep(self):
        store = InMemoryPgStateStore()
        store.connect()
        store.write(make_checkpoint(1))
        store.write(make_checkpoint(2))
        deleted = store.prune(keep=10)
        assert deleted == 0

    def test_serialisation_round_trip(self):
        store = InMemoryPgStateStore()
        store.connect()
        cp = make_checkpoint_with_position(15)
        store.write(cp)
        loaded = store.read_latest()
        assert len(loaded.state.positions) == 1
