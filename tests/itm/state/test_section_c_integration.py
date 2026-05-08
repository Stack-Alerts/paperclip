"""
ITM Section C — Integration Test: Full State Management & Recovery Flow.

Tests the complete Section C system working end-to-end:

1. Build initial state with positions, orders, strategies
2. Checkpoint to both stores (dual-write)
3. Simulate process restart: state lost in memory
4. Recover from persistence: state loaded
5. Reconcile with mock Binance API
6. Verify no divergences → orders unblocked
7. Verify checkpoint latency < 500ms
8. Simulate Redis failure → circuit breaker opens → Postgres-only
9. Simulate graceful shutdown: SIGTERM → checkpoint → stores closed

This test uses only in-memory mocks — no real Redis or Postgres required.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from src.itm.domain.entities import (
    AccountHeat,
    CapitalState,
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionDirection,
    PositionEntry,
    RiskProfile,
)
from src.itm.state.schema import (
    ITMSystemState,
    RiskSnapshot,
    StateCheckpoint,
    StrategyRunState,
    StrategyState,
)
from src.itm.state.manager import CircuitBreakerState, StateManager, StateManagerConfig
from src.itm.state.redis_store import InMemoryRedisStateStore
from src.itm.state.pg_store import InMemoryPgStateStore
from src.itm.state.recovery import (
    ExchangePosition,
    MockBinancePositionFetcher,
    RecoveryConfig,
    RecoveryProtocol,
)
from src.itm.state.shutdown import GracefulShutdownHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_full_state() -> ITMSystemState:
    """Build a realistic ITMSystemState with position, order, risk, strategy."""
    state = ITMSystemState()
    instr = Instrument.btc_usdt_perp()

    # Position
    pos = Position(instrument=instr, direction=PositionDirection.LONG)
    pos.add_entry(
        PositionEntry(order_id="entry-001", quantity=Decimal("0.25"), price=Decimal("58000"))
    )
    state.positions[pos.position_id] = pos

    # Stop-loss order
    sl_order = Order(
        instrument=instr,
        side=OrderSide.SELL,
        order_type=OrderType.STOP_MARKET,
        quantity=Decimal("0.25"),
        price=Decimal("56840"),  # 2% below 58000
        status=OrderStatus.OPEN,
    )
    state.orders[sl_order.client_order_id] = sl_order

    # Risk snapshot
    state.risk = RiskSnapshot(
        account_heat=AccountHeat(max_heat=Decimal("10.0"), current_heat=Decimal("2.5")),
        capital_state=CapitalState(
            total_capital=Decimal("25000.00"),
            allocated=Decimal("14500.00"),
            locked=Decimal("0"),
        ),
        total_open_positions=1,
        total_pending_orders=1,
    )

    # Strategy state
    rp = RiskProfile(
        strategy_id="momentum-01",
        max_drawdown_pct=Decimal("0.05"),
        max_position_qty=Decimal("1.0"),
        heat_limit=Decimal("10.0"),
        max_daily_loss=Decimal("500.00"),
    )
    strategy = StrategyState(
        strategy_id="momentum-01",
        run_state=StrategyRunState.ACTIVE,
        instrument=instr,
        risk_profile=rp,
        active_position_id=pos.position_id,
        open_order_ids={sl_order.client_order_id},
        daily_pnl=Decimal("-75.00"),
    )
    state.strategies["momentum-01"] = strategy

    return state


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestSectionCIntegration:

    def test_full_checkpoint_and_recovery_no_divergence(self):
        """Full cycle: build state → checkpoint → recover → no divergence."""
        # --- Setup ---
        redis = InMemoryRedisStateStore()
        pg = InMemoryPgStateStore()
        redis.connect()
        pg.connect()
        manager = StateManager(redis_store=redis, pg_store=pg)
        manager.connect()

        initial_state = _make_full_state()

        # --- Checkpoint (simulate bar close) ---
        t0 = time.monotonic()
        cp = manager.checkpoint(initial_state, source="bar_close")
        latency_ms = (time.monotonic() - t0) * 1000

        assert cp.sequence == 1
        assert cp.source == "bar_close"
        # Acceptance criterion: <500ms checkpoint latency
        assert latency_ms < 500.0, f"Checkpoint took {latency_ms:.1f}ms, must be <500ms"

        # --- Simulate restart: state lost in memory ---
        live_state = None  # memory cleared

        # --- Recovery ---
        fetcher = MockBinancePositionFetcher([
            ExchangePosition(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                quantity=Decimal("0.25"),
                entry_price=Decimal("58000"),
            )
        ])
        protocol = RecoveryProtocol(fetcher)
        result = protocol.run(manager)

        # --- Assertions ---
        assert result.is_clean_start is False
        assert result.has_divergence is False
        assert result.orders_blocked is False
        assert result.recovery_duration_ms < 120_000  # <2 minutes
        assert len(result.state.positions) == 1
        assert len(result.state.orders) == 1
        assert len(result.state.strategies) == 1
        assert result.state.risk is not None

        # Verify strategy state restored correctly
        strat = result.state.strategies.get("momentum-01")
        assert strat is not None
        assert strat.run_state == StrategyRunState.ACTIVE
        assert strat.daily_pnl == Decimal("-75.00")

    def test_circuit_breaker_postgres_fallback(self):
        """Redis failures trip circuit breaker; Postgres-only mode continues."""
        from unittest.mock import MagicMock

        failing_redis = MagicMock()
        failing_redis.connect.return_value = None
        failing_redis.ping.return_value = True
        failing_redis.write.side_effect = Exception("Redis down")
        failing_redis.close.return_value = None

        pg = InMemoryPgStateStore()
        pg.connect()

        manager = StateManager(
            redis_store=failing_redis,
            pg_store=pg,
            config=StateManagerConfig(
                instance_id="test-fallback",
                cb_failure_threshold=3,
            ),
        )
        manager.connect()

        state = _make_full_state()

        # Trip the breaker
        for _ in range(3):
            manager.checkpoint(state)
        assert manager.circuit_breaker_state == CircuitBreakerState.OPEN

        # Next checkpoint succeeds on Postgres alone
        cp = manager.checkpoint(state, source="bar_close")
        assert cp.sequence == 4
        # Postgres has the checkpoint
        pg_latest = pg.read_latest()
        assert pg_latest is not None
        assert pg_latest.sequence == 4

    def test_graceful_shutdown_writes_final_checkpoint(self):
        """SIGTERM → checkpoint with source='shutdown' → stores closed."""
        redis = InMemoryRedisStateStore()
        pg = InMemoryPgStateStore()
        redis.connect()
        pg.connect()
        manager = StateManager(redis_store=redis, pg_store=pg)
        manager.connect()

        state = _make_full_state()
        # Initial bar-close checkpoint
        manager.checkpoint(state, source="bar_close")

        # Mutate state (simulate ongoing trading)
        state.risk.capital_state.allocated += Decimal("1000")

        current_state = [state]  # mutable container for getter

        handler = GracefulShutdownHandler(
            state_manager=manager,
            state_getter=lambda: current_state[0],
            checkpoint_timeout_s=5.0,
        )

        # Simulate SIGTERM
        handler.trigger_shutdown()

        assert handler.shutdown_event.is_set()

        # Verify the shutdown checkpoint was written
        cp = redis.read_latest()
        # Redis is closed at this point, but the in-memory store still has the data
        # Use the pg store (also closed, but in-memory has the data)
        latest = pg.read_latest()
        assert latest is not None
        assert latest.source == "shutdown"
        assert latest.sequence == 2  # bar_close was seq=1, shutdown is seq=2

    def test_recovery_from_24h_old_checkpoint(self):
        """Checkpoint from 23.9 hours ago → still valid (within 24h window)."""
        redis = InMemoryRedisStateStore()
        pg = InMemoryPgStateStore()
        redis.connect()
        pg.connect()
        manager = StateManager(redis_store=redis, pg_store=pg)
        manager.connect()

        state = _make_full_state()
        cp = StateCheckpoint(sequence=1, state=state, source="bar_close")
        # Set to 23.9 hours ago
        cp.checkpointed_at = datetime.now(timezone.utc) - timedelta(hours=23, minutes=54)
        pg.write(cp)
        redis.write(cp)

        fetcher = MockBinancePositionFetcher([
            ExchangePosition(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                quantity=Decimal("0.25"),
                entry_price=Decimal("58000"),
            )
        ])
        protocol = RecoveryProtocol(
            fetcher, config=RecoveryConfig(max_recovery_age_hours=24)
        )
        result = protocol.run(manager)

        assert result.is_clean_start is False
        assert result.has_divergence is False

    def test_divergence_blocks_orders_and_logs_critical(self, caplog):
        """Divergence → orders_blocked=True → CRITICAL log emitted."""
        import logging

        redis = InMemoryRedisStateStore()
        pg = InMemoryPgStateStore()
        redis.connect()
        pg.connect()
        manager = StateManager(redis_store=redis, pg_store=pg)
        manager.connect()

        state = _make_full_state()
        manager.checkpoint(state)

        # Exchange says no open positions (mismatch!)
        fetcher = MockBinancePositionFetcher([])

        protocol = RecoveryProtocol(fetcher)
        with caplog.at_level(logging.CRITICAL, logger="src.itm.state.recovery"):
            result = protocol.run(manager)

        assert result.has_divergence is True
        assert result.orders_blocked is True
        assert any(r.levelno >= logging.CRITICAL for r in caplog.records)

    def test_multiple_sequential_checkpoints_latest_wins(self):
        """Multiple bar-close checkpoints: load_latest returns the last one."""
        redis = InMemoryRedisStateStore()
        pg = InMemoryPgStateStore()
        redis.connect()
        pg.connect()
        manager = StateManager(redis_store=redis, pg_store=pg)
        manager.connect()

        state = ITMSystemState()
        for i in range(5):
            manager.checkpoint(state, source="bar_close")

        latest = manager.load_latest()
        assert latest is not None
        assert latest.sequence == 5

    def test_health_check_structure(self):
        """health_check() returns expected structure."""
        redis = InMemoryRedisStateStore()
        pg = InMemoryPgStateStore()
        redis.connect()
        pg.connect()
        manager = StateManager(redis_store=redis, pg_store=pg)
        manager.connect()

        health = manager.health_check()
        assert health["redis"]["ping"] is True
        assert health["postgres"]["ping"] is True
        assert health["redis"]["circuit_breaker"] == "closed"
        assert health["sequence"] == 0
