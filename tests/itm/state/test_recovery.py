"""
Tests: RecoveryProtocol (recovery.py)
=======================================
Tests the full recovery sequence including:
- Loading from Redis (hot state) via manager
- Falling back to PostgreSQL when Redis empty
- Falling back to fresh state when both empty
- Stale-state detection (age > max_recovery_age_hours)
- Binance reconciliation: all three divergence types
- Recovery elapsed time tracking
- RecoveryError and DivergenceAlert validation
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from src.itm.state.schema import (
    ITMSystemState,
    StrategyState,
    StateCheckpoint,
)
from src.itm.state.recovery import (
    RecoveryProtocol,
    RecoveryResult,
    DivergenceAlert,
    RecoveryError,
    ExchangePosition,
    MockBinancePositionFetcher,
    RecoveryConfig,
)
from src.itm.state.manager import StateManager, StateManagerConfig
from src.itm.state.redis_store import InMemoryRedisStateStore
from src.itm.state.pg_store import InMemoryPgStateStore
from src.itm.domain.entities import (
    Instrument,
    Position,
    PositionDirection,
    PositionEntry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_manager_with_state() -> tuple:
    """Return (manager, redis, pg) with a fresh ITMSystemState."""
    redis = InMemoryRedisStateStore()
    pg = InMemoryPgStateStore()
    redis.connect()
    pg.connect()
    mgr = StateManager(redis_store=redis, pg_store=pg)
    mgr.connect()
    return mgr, redis, pg


def make_state_with_position(symbol: str = "BTC/USDT") -> ITMSystemState:
    state = ITMSystemState()
    instr = Instrument.btc_usdt_spot()
    pos = Position(instrument=instr, direction=PositionDirection.LONG)
    pos.add_entry(
        PositionEntry(
            order_id="ord-1",
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )
    )
    state.positions[pos.position_id] = pos
    return state


# ---------------------------------------------------------------------------
# DivergenceAlert validation
# ---------------------------------------------------------------------------


class TestDivergenceAlert:
    def test_valid_types(self):
        for t in ["itm_open_exchange_closed", "exchange_open_itm_missing", "quantity_mismatch"]:
            a = DivergenceAlert(alert_type=t, symbol="BTC/USDT")
            assert a.alert_type == t

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="alert_type"):
            DivergenceAlert(alert_type="bogus", symbol="BTC/USDT")

    def test_has_detected_at(self):
        a = DivergenceAlert(alert_type="itm_open_exchange_closed", symbol="BTC/USDT")
        assert a.detected_at is not None


# ---------------------------------------------------------------------------
# RecoveryResult
# ---------------------------------------------------------------------------


class TestRecoveryResult:
    def test_clean_start_defaults(self):
        r = RecoveryResult()
        assert r.is_clean_start is True
        assert not r.has_divergence
        assert not r.orders_blocked


# ---------------------------------------------------------------------------
# ExchangePosition
# ---------------------------------------------------------------------------


class TestExchangePosition:
    def test_construction(self):
        ep = ExchangePosition(
            symbol="BTCUSDT",
            direction=PositionDirection.LONG,
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000"),
        )
        assert ep.symbol == "BTCUSDT"
        assert ep.quantity == Decimal("0.1")

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="symbol"):
            ExchangePosition(
                symbol="",
                direction=PositionDirection.LONG,
                quantity=Decimal("0.1"),
            )


# ---------------------------------------------------------------------------
# MockBinancePositionFetcher
# ---------------------------------------------------------------------------


class TestMockBinancePositionFetcher:
    def test_empty_returns_empty_list(self):
        f = MockBinancePositionFetcher()
        assert f.get_positions() == []

    def test_returns_configured_positions(self):
        ep = ExchangePosition(
            symbol="BTCUSDT",
            direction=PositionDirection.LONG,
            quantity=Decimal("0.5"),
        )
        f = MockBinancePositionFetcher([ep])
        positions = f.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == Decimal("0.5")

    def test_get_open_positions_dict(self):
        ep = ExchangePosition(
            symbol="BTCUSDT",
            direction=PositionDirection.LONG,
            quantity=Decimal("0.25"),
        )
        f = MockBinancePositionFetcher([ep])
        d = f.get_open_positions()
        assert "BTC/USDT" in d
        assert d["BTC/USDT"] == Decimal("0.25")


# ---------------------------------------------------------------------------
# Clean start (no persisted state)
# ---------------------------------------------------------------------------


class TestCleanStart:
    def test_clean_start_when_no_checkpoints(self):
        mgr, redis, pg = make_manager_with_state()
        fetcher = MockBinancePositionFetcher([])
        protocol = RecoveryProtocol(fetcher)
        result = protocol.run(mgr)
        assert result.is_clean_start is True
        assert not result.has_divergence

    def test_clean_start_no_fetcher(self):
        mgr, redis, pg = make_manager_with_state()
        protocol = RecoveryProtocol()
        result = protocol.run(mgr)
        assert result.is_clean_start is True


# ---------------------------------------------------------------------------
# Recovery from Redis
# ---------------------------------------------------------------------------


class TestRecoveryFromRedis:
    def test_loads_from_redis_after_checkpoint(self):
        mgr, redis, pg = make_manager_with_state()
        state = ITMSystemState()
        state.ensure_strategy("s1")
        mgr.checkpoint(state, source="bar_close")

        # New manager pointing to same stores
        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        protocol = RecoveryProtocol()
        result = protocol.run(mgr2)
        assert not result.is_clean_start
        assert result.loaded_from == "redis"
        assert "s1" in result.state.strategies

    def test_stale_checkpoint_triggers_clean_start(self):
        mgr, redis, pg = make_manager_with_state()
        state = ITMSystemState()
        cp = StateCheckpoint(
            sequence=1,
            state=state,
            source="bar_close",
            checkpointed_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        redis.write(cp)
        pg.write(cp)

        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        config = RecoveryConfig(max_recovery_age_hours=24)
        protocol = RecoveryProtocol(config=config)
        result = protocol.run(mgr2)
        assert result.is_clean_start is True


# ---------------------------------------------------------------------------
# Recovery from PostgreSQL fallback
# ---------------------------------------------------------------------------


class TestRecoveryFromPostgres:
    def test_loads_from_postgres_when_redis_empty(self):
        mgr, redis, pg = make_manager_with_state()
        state = ITMSystemState()
        state.ensure_strategy("pg-strat")
        mgr.checkpoint(state, source="bar_close")

        # Create a new manager with empty Redis
        empty_redis = InMemoryRedisStateStore()
        empty_redis.connect()
        mgr2 = StateManager(redis_store=empty_redis, pg_store=pg)
        mgr2.connect()
        protocol = RecoveryProtocol()
        result = protocol.run(mgr2)
        assert not result.is_clean_start
        assert result.loaded_from == "postgres"
        assert "pg-strat" in result.state.strategies


# ---------------------------------------------------------------------------
# Binance reconciliation
# ---------------------------------------------------------------------------


class TestBinanceReconciliation:
    def test_no_divergence_positions_match(self):
        mgr, redis, pg = make_manager_with_state()
        state = make_state_with_position("BTC/USDT")
        mgr.checkpoint(state)

        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        fetcher = MockBinancePositionFetcher([
            ExchangePosition(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                quantity=Decimal("0.1"),
            )
        ])
        protocol = RecoveryProtocol(fetcher)
        result = protocol.run(mgr2)
        assert not result.has_divergence
        assert not result.orders_blocked

    def test_detects_itm_open_exchange_closed(self):
        """ITM has open position, exchange reports no positions."""
        mgr, redis, pg = make_manager_with_state()
        state = make_state_with_position("BTC/USDT")
        mgr.checkpoint(state)

        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        fetcher = MockBinancePositionFetcher([])  # no exchange positions
        protocol = RecoveryProtocol(fetcher)
        result = protocol.run(mgr2)
        assert result.has_divergence
        assert result.orders_blocked
        assert any(
            a.alert_type == "itm_open_exchange_closed"
            for a in result.divergences
        )

    def test_detects_exchange_open_itm_missing(self):
        """Exchange has position ITM doesn't know about."""
        mgr, redis, pg = make_manager_with_state()
        state = ITMSystemState()  # no positions
        mgr.checkpoint(state)

        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        fetcher = MockBinancePositionFetcher([
            ExchangePosition(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                quantity=Decimal("0.5"),
            )
        ])
        protocol = RecoveryProtocol(fetcher)
        result = protocol.run(mgr2)
        assert result.has_divergence
        assert any(
            a.alert_type == "exchange_open_itm_missing"
            for a in result.divergences
        )

    def test_detects_quantity_mismatch(self):
        """Both know about position but quantities differ."""
        mgr, redis, pg = make_manager_with_state()
        state = make_state_with_position("BTC/USDT")  # ITM: 0.1 BTC
        mgr.checkpoint(state)

        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        fetcher = MockBinancePositionFetcher([
            ExchangePosition(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                quantity=Decimal("0.15"),  # mismatch
            )
        ])
        protocol = RecoveryProtocol(fetcher)
        result = protocol.run(mgr2)
        assert result.has_divergence
        assert any(a.alert_type == "quantity_mismatch" for a in result.divergences)

    def test_reconciliation_skipped_without_fetcher(self):
        """No fetcher → no reconciliation → no divergences."""
        mgr, redis, pg = make_manager_with_state()
        state = make_state_with_position()
        mgr.checkpoint(state)

        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        protocol = RecoveryProtocol(fetcher=None)
        result = protocol.run(mgr2)
        assert not result.has_divergence

    def test_reconciliation_failure_is_non_fatal(self):
        """If fetcher raises, recovery still succeeds."""
        class FailingFetcher:
            def get_positions(self):
                raise ConnectionError("Binance down")

        mgr, redis, pg = make_manager_with_state()
        state = make_state_with_position()
        mgr.checkpoint(state)

        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        protocol = RecoveryProtocol(FailingFetcher())
        result = protocol.run(mgr2)
        assert not result.is_clean_start
        assert not result.has_divergence  # reconciliation abandoned


# ---------------------------------------------------------------------------
# Recovery timing
# ---------------------------------------------------------------------------


class TestRecoveryTiming:
    def test_elapsed_duration_measured(self):
        mgr, redis, pg = make_manager_with_state()
        protocol = RecoveryProtocol()
        result = protocol.run(mgr)
        assert result.recovery_duration_ms >= 0.0

    def test_recovery_completes_fast_with_fakes(self):
        """With in-memory fakes, recovery should complete well under 2 minutes."""
        mgr, redis, pg = make_manager_with_state()
        mgr.checkpoint(ITMSystemState())

        mgr2 = StateManager(redis_store=redis, pg_store=pg)
        mgr2.connect()
        protocol = RecoveryProtocol()
        result = protocol.run(mgr2)
        assert result.recovery_duration_ms < 120_000, (
            f"Recovery took {result.recovery_duration_ms:.0f}ms, expected < 120000ms"
        )
