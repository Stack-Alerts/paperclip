"""
Tests: Real PostgreSQL State Store
====================================
Tests the PostgreSQL-backed state store (``PostgresStateStore`` SQL dialect)
against a *real* PostgreSQL instance using the ``real_pg_store`` fixture
defined in conftest.py.

These tests validate:
- PostgreSQL-specific SQL: ``ON CONFLICT``, ``JSONB``, ``TIMESTAMPTZ``
- Table DDL is correct (the test table uses production column types)
- Write / read / prune operations produce correct results on real PostgreSQL
- Serialisation round-trips through JSONB produce identical Python objects

All tests skip automatically if PostgreSQL is not reachable (CI without
a database service).  For CI with PostgreSQL, set:
  POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD

This file REPLACES the in-memory shim approach for the ``PostgresStateStore``
path.  The ``InMemoryPgStateStore`` unit tests remain in ``test_pg_store.py``
as they test the shim's own behaviour in isolation.

Addresses: BTCAAAAA-450
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from src.itm.state.schema import ITMSystemState, StateCheckpoint
from src.itm.domain.entities import (
    Instrument,
    Position,
    PositionDirection,
    PositionEntry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_checkpoint(seq: int, source: str = "bar_close") -> StateCheckpoint:
    state = ITMSystemState()
    return StateCheckpoint(sequence=seq, state=state, source=source)


def _make_checkpoint_with_position(seq: int) -> StateCheckpoint:
    state = ITMSystemState()
    instr = Instrument.btc_usdt_perp()
    pos = Position(instrument=instr, direction=PositionDirection.LONG)
    pos.add_entry(
        PositionEntry(
            order_id="o1",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
    )
    state.positions[pos.position_id] = pos
    return StateCheckpoint(sequence=seq, state=state, source="bar_close")


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


class TestRealPgStorePing:
    """Verify the fixture is connected to a live PostgreSQL instance."""

    def test_ping_returns_true_on_connected_store(self, real_pg_store):
        """ping() must return True — confirms we are talking to real PostgreSQL."""
        assert real_pg_store.ping() is True


# ---------------------------------------------------------------------------
# Write / Read
# ---------------------------------------------------------------------------


class TestRealPgStoreWriteRead:
    """Write / read round-trips against real PostgreSQL (JSONB, ON CONFLICT)."""

    def test_write_returns_non_negative_latency(self, real_pg_store):
        latency = real_pg_store.write(_make_checkpoint(1))
        assert latency >= 0.0

    def test_read_latest_after_single_write(self, real_pg_store):
        real_pg_store.write(_make_checkpoint(1, source="bar_close"))
        loaded = real_pg_store.read_latest()
        assert loaded is not None
        assert loaded.sequence == 1

    def test_read_latest_returns_highest_sequence(self, real_pg_store):
        """ORDER BY seq DESC LIMIT 1 must return sequence 5, not 1 or 3."""
        real_pg_store.write(_make_checkpoint(1))
        real_pg_store.write(_make_checkpoint(5))
        real_pg_store.write(_make_checkpoint(3))
        loaded = real_pg_store.read_latest()
        assert loaded.sequence == 5

    def test_read_latest_empty_table(self, real_pg_store):
        assert real_pg_store.read_latest() is None

    def test_read_by_sequence_found(self, real_pg_store):
        real_pg_store.write(_make_checkpoint(100))
        loaded = real_pg_store.read_by_sequence(100)
        assert loaded is not None
        assert loaded.sequence == 100

    def test_read_by_sequence_missing(self, real_pg_store):
        assert real_pg_store.read_by_sequence(999) is None

    def test_on_conflict_upsert(self, real_pg_store):
        """Writing the same sequence twice must not raise; last write wins."""
        cp1 = _make_checkpoint(7, source="bar_close")
        cp2 = _make_checkpoint(7, source="shutdown")
        real_pg_store.write(cp1)
        real_pg_store.write(cp2)
        loaded = real_pg_store.read_by_sequence(7)
        assert loaded is not None
        assert loaded.sequence == 7
        assert loaded.source == "shutdown"  # second write wins

    # -----------------------------------------------------------------------
    # JSONB serialisation round-trip
    # -----------------------------------------------------------------------

    def test_jsonb_serialisation_round_trip_empty_state(self, real_pg_store):
        """Empty ITMSystemState survives JSONB write → JSONB read."""
        cp = _make_checkpoint(10)
        real_pg_store.write(cp)
        loaded = real_pg_store.read_latest()
        assert loaded is not None
        assert loaded.sequence == 10

    def test_jsonb_serialisation_round_trip_with_position(self, real_pg_store):
        """Position data with Decimal prices survives JSONB write → read."""
        cp = _make_checkpoint_with_position(15)
        real_pg_store.write(cp)
        loaded = real_pg_store.read_latest()
        assert loaded is not None
        assert len(loaded.state.positions) == 1

    def test_jsonb_strategy_heat_preserved(self, real_pg_store):
        """Decimal strategy heat is preserved through JSONB round-trip."""
        state = ITMSystemState()
        ss = state.ensure_strategy("s1")
        ss.heat = Decimal("5.5")
        cp = StateCheckpoint(sequence=20, state=state, source="shutdown")
        real_pg_store.write(cp)
        loaded = real_pg_store.read_by_sequence(20)
        assert loaded is not None
        assert "s1" in loaded.state.strategies
        assert loaded.state.strategies["s1"].heat == Decimal("5.5")

    def test_source_field_stored_correctly(self, real_pg_store):
        """The ``source`` column (TEXT) stores the checkpoint trigger reason."""
        for source in ("bar_close", "shutdown", "risk_gate", "manual"):
            cp = StateCheckpoint(
                sequence=_source_to_seq(source),
                state=ITMSystemState(),
                source=source,
            )
            real_pg_store.write(cp)

        for source, seq in [("bar_close", 1), ("shutdown", 2),
                             ("risk_gate", 3), ("manual", 4)]:
            loaded = real_pg_store.read_by_sequence(seq)
            assert loaded.source == source


def _source_to_seq(source: str) -> int:
    return {"bar_close": 1, "shutdown": 2, "risk_gate": 3, "manual": 4}[source]


# ---------------------------------------------------------------------------
# read_since — TIMESTAMPTZ filter
# ---------------------------------------------------------------------------


class TestRealPgStoreReadSince:
    """Verify TIMESTAMPTZ-based time filtering executes correctly in PostgreSQL."""

    def test_read_since_filters_by_time(self, real_pg_store):
        old_ts = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_ts = datetime.now(timezone.utc) - timedelta(minutes=5)

        cp_old = _make_checkpoint(1)
        cp_old.checkpointed_at = old_ts

        cp_recent = _make_checkpoint(2)
        cp_recent.checkpointed_at = recent_ts

        real_pg_store.write(cp_old)
        real_pg_store.write(cp_recent)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        results = real_pg_store.read_since(cutoff, limit=10)

        assert len(results) == 1
        assert results[0].sequence == 2

    def test_read_since_returns_all_recent(self, real_pg_store):
        """All records newer than cutoff are returned (up to limit)."""
        recent = datetime.now(timezone.utc) - timedelta(minutes=1)
        for i in range(1, 6):
            cp = _make_checkpoint(i)
            cp.checkpointed_at = recent
            real_pg_store.write(cp)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        results = real_pg_store.read_since(cutoff, limit=10)
        assert len(results) == 5

    def test_read_since_respects_limit(self, real_pg_store):
        """LIMIT clause is forwarded to PostgreSQL."""
        recent = datetime.now(timezone.utc) - timedelta(minutes=1)
        for i in range(1, 11):
            cp = _make_checkpoint(i)
            cp.checkpointed_at = recent
            real_pg_store.write(cp)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        results = real_pg_store.read_since(cutoff, limit=3)
        assert len(results) <= 3

    def test_read_since_empty_returns_empty_list(self, real_pg_store):
        """No records returns an empty list, not None or an error."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        results = real_pg_store.read_since(cutoff)
        assert results == []


# ---------------------------------------------------------------------------
# prune — DELETE with sub-SELECT
# ---------------------------------------------------------------------------


class TestRealPgStorePrune:
    """Verify the prune operation's DELETE … WHERE seq NOT IN (…) SQL."""

    def test_prune_removes_old_checkpoints(self, real_pg_store):
        for i in range(1, 11):
            real_pg_store.write(_make_checkpoint(i))
        deleted = real_pg_store.prune(keep=3)
        assert deleted == 7
        # Latest 3 sequences must remain
        assert real_pg_store.read_by_sequence(8) is not None
        assert real_pg_store.read_by_sequence(9) is not None
        assert real_pg_store.read_by_sequence(10) is not None
        assert real_pg_store.read_by_sequence(1) is None

    def test_prune_noop_when_within_keep(self, real_pg_store):
        real_pg_store.write(_make_checkpoint(1))
        real_pg_store.write(_make_checkpoint(2))
        deleted = real_pg_store.prune(keep=10)
        assert deleted == 0

    def test_prune_keeps_correct_count(self, real_pg_store):
        for i in range(1, 6):
            real_pg_store.write(_make_checkpoint(i))
        real_pg_store.prune(keep=2)
        latest = real_pg_store.read_latest()
        assert latest.sequence == 5

    def test_prune_on_empty_table(self, real_pg_store):
        deleted = real_pg_store.prune(keep=5)
        assert deleted == 0

    def test_prune_keep_exactly_one(self, real_pg_store):
        for i in range(1, 6):
            real_pg_store.write(_make_checkpoint(i))
        deleted = real_pg_store.prune(keep=1)
        assert deleted == 4
        latest = real_pg_store.read_latest()
        assert latest.sequence == 5


# ---------------------------------------------------------------------------
# Multiple-checkpoint query correctness
# ---------------------------------------------------------------------------


class TestRealPgStoreMultipleCheckpoints:
    """Correctness tests when many rows are present in the table."""

    def test_high_volume_write_and_latest(self, real_pg_store):
        """Write 50 checkpoints; read_latest returns sequence 50."""
        for i in range(1, 51):
            real_pg_store.write(_make_checkpoint(i))
        loaded = real_pg_store.read_latest()
        assert loaded.sequence == 50

    def test_write_checkpoint_api_compatibility(self, real_pg_store):
        """``write_checkpoint()`` returns (True, latency_ms >= 0)."""
        cp = _make_checkpoint(1)
        ok, latency_ms = real_pg_store.write_checkpoint(cp)
        assert ok is True
        assert latency_ms >= 0.0

    def test_read_latest_checkpoint_api_compatibility(self, real_pg_store):
        """``read_latest_checkpoint()`` returns (StateCheckpoint, True)."""
        real_pg_store.write(_make_checkpoint(1))
        cp, ok = real_pg_store.read_latest_checkpoint()
        assert ok is True
        assert cp is not None
        assert cp.sequence == 1

    def test_read_checkpoint_by_seq_api_compatibility(self, real_pg_store):
        """``read_checkpoint_by_seq()`` returns (StateCheckpoint, True)."""
        real_pg_store.write(_make_checkpoint(5))
        cp, ok = real_pg_store.read_checkpoint_by_seq(5)
        assert ok is True
        assert cp.sequence == 5
