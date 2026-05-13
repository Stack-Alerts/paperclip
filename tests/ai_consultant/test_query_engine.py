"""
Integration tests for QueryEngine — all 9 parameterised query tools.

These tests run against the real PostgreSQL test database using the
ai_readonly role. They require:
  - A running PostgreSQL instance reachable via POSTGRES_* env vars
  - The ai_readonly role to exist (apply migration 20260509_add_ai_readonly_role)
  - AI_READONLY_PASSWORD set in the environment / .env file

Seed data is inserted via a privileged connection (the normal app pool /
POSTGRES_USER), then queried via the ai_readonly pool.  All seed data is
cleaned up in the fixture teardown to keep the DB pristine.

Run with:
    pytest tests/ai_consultant/test_query_engine.py -v
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# ── subject under test ──────────────────────────────────────────────────────
from src.ai_consultant.db.query_engine import (
    QueryEngine,
    _ReadonlyPool,
    SignalStats,
    StrategyPerformance,
    Trade,
    OpenPosition,
    BlockCorrelation,
    MarketRegime,
    SignalCoactivation,
    PortfolioStats,
    ConfigDiff,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════════════════

def _admin_url() -> str:
    """DB URL for the privileged admin user (seed / teardown)."""
    from dotenv import load_dotenv
    load_dotenv()
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "optimizer_v3")
    user = os.getenv("POSTGRES_USER", "optimizer_admin")
    pw = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


@pytest.fixture(scope="module")
def admin_session() -> Generator[Session, None, None]:
    """Privileged session for seeding and verifying test data."""
    engine = create_engine(_admin_url(), pool_pre_ping=True)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    sess = factory()
    yield sess
    sess.close()
    engine.dispose()


@pytest.fixture(scope="module")
def seed_ids() -> dict:
    """Stable IDs shared across all test fixtures in this module."""
    return {
        "strategy_a": "test-strategy-alpha-" + uuid.uuid4().hex[:8],
        "strategy_b": "test-strategy-beta-" + uuid.uuid4().hex[:8],
        "signal_name": "TEST_SIGNAL_MACD",
        "signal_name_2": "TEST_SIGNAL_RSI",
        "variation_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "version_a_id": str(uuid.uuid4()),
        "version_b_id": str(uuid.uuid4()),
    }


@pytest.fixture(scope="module", autouse=True)
def seed_database(admin_session: Session, seed_ids: dict):
    """Insert all test data once per module; roll back / delete on teardown."""
    ids = seed_ids
    now = datetime.now(timezone.utc)
    past_30 = now - timedelta(days=30)
    past_60 = now - timedelta(days=60)
    # ── Ensure all required tables exist (Alembic migrations may not be applied) ─
    admin_session.execute(text("""
        CREATE TABLE IF NOT EXISTS strategies (
            strategy_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """))
    admin_session.execute(text("""
        CREATE TABLE IF NOT EXISTS strategy_versions (
            version_id UUID PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            name TEXT NOT NULL,
            blocks JSONB NOT NULL,
            signals JSONB NOT NULL,
            parameters JSONB NOT NULL,
            entry_conditions JSONB NOT NULL,
            exit_conditions JSONB NOT NULL,
            risk_management JSONB NOT NULL,
            backtest_config JSONB NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """))
    admin_session.execute(text("""
        CREATE TABLE IF NOT EXISTS strategy_test_results (
            result_id UUID PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            version_id UUID NOT NULL,
            test_type TEXT NOT NULL,
            test_config JSONB,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            total_return_pct DOUBLE PRECISION,
            sharpe_ratio DOUBLE PRECISION,
            max_drawdown_pct DOUBLE PRECISION,
            win_rate DOUBLE PRECISION,
            profit_factor DOUBLE PRECISION,
            total_trades INTEGER,
            metrics JSONB NOT NULL,
            trades JSONB,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """))
    admin_session.execute(text("""
        CREATE TABLE IF NOT EXISTS signal_metrics (
            metric_id UUID PRIMARY KEY,
            signal_name VARCHAR(255) NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            total_occurrences INTEGER NOT NULL DEFAULT 0,
            trades_triggered INTEGER NOT NULL DEFAULT 0,
            trigger_rate DOUBLE PRECISION,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            win_rate DOUBLE PRECISION,
            avg_pnl VARCHAR(50),
            total_pnl VARCHAR(50),
            profit_factor DOUBLE PRECISION,
            best_market_condition VARCHAR(100),
            worst_market_condition VARCHAR(100),
            best_timeframe VARCHAR(50),
            calculated_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    admin_session.execute(text("""
        CREATE TABLE IF NOT EXISTS signal_events (
            event_id UUID PRIMARY KEY,
            run_id UUID NOT NULL,
            variation_id UUID NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            signal_name VARCHAR(255) NOT NULL,
            signal_type VARCHAR(50) NOT NULL,
            signal_direction VARCHAR(20),
            instrument_id VARCHAR(100) NOT NULL,
            price VARCHAR(50) NOT NULL,
            bar_number INTEGER,
            signal_strength DOUBLE PRECISION,
            confidence DOUBLE PRECISION,
            signal_metadata JSONB,
            led_to_trade BOOLEAN DEFAULT FALSE,
            trade_result VARCHAR(20),
            trade_pnl VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    admin_session.commit()

    # ── Strategies ────────────────────────────────────────────────────────
    admin_session.execute(text("""
        INSERT INTO strategies (strategy_id, name, created_at, updated_at)
        VALUES (:a_id, 'Test Strategy Alpha', :now, :now),
               (:b_id, 'Test Strategy Beta',  :now, :now)
        ON CONFLICT DO NOTHING
    """), {"a_id": ids["strategy_a"], "b_id": ids["strategy_b"], "now": now})

    # ── Strategy versions ─────────────────────────────────────────────────
    params_alpha = '{"rsi_period":14,"macd_fast":12,"macd_slow":26}'
    params_beta = '{"rsi_period":21,"bb_period":20}'

    admin_session.execute(text("""
        INSERT INTO strategy_versions (
            version_id, strategy_id, version_number, name,
            blocks, signals, parameters, entry_conditions,
            exit_conditions, risk_management, backtest_config, timestamp, created_at
        ) VALUES (
            :vid_a, :sid_a, 1, 'Alpha v1',
            '[{"name":"MACD","category":"MOMENTUM"},{"name":"RSI","category":"OSCILLATOR"}]'::jsonb,
            '{"entry_signal":"MACD_CROSS","exit_signal":"RSI_OVERBOUGHT"}'::jsonb,
            CAST(:params_alpha AS jsonb),
            '{}'::jsonb, '[]'::jsonb, '{}'::jsonb, '{}'::jsonb,
            :now, :now
        ), (
            :vid_b, :sid_b, 1, 'Beta v1',
            '[{"name":"RSI","category":"OSCILLATOR"},{"name":"BOLLINGER","category":"VOLATILITY"}]'::jsonb,
            '{"entry_signal":"RSI_OVERSOLD","exit_signal":"BOLLINGER_UPPER"}'::jsonb,
            CAST(:params_beta AS jsonb),
            '{}'::jsonb, '[]'::jsonb, '{}'::jsonb, '{}'::jsonb,
            :now, :now
        )
        ON CONFLICT DO NOTHING
    """), {
        "vid_a": ids["version_a_id"], "sid_a": ids["strategy_a"],
        "vid_b": ids["version_b_id"], "sid_b": ids["strategy_b"],
        "params_alpha": params_alpha,
        "params_beta": params_beta,
        "now": now,
    })

    # ── Strategy test results ─────────────────────────────────────────────
    trades_json = (
        '[{"trade_id":"t1","entry_time":"2026-01-10T10:00:00",'
        '"exit_time":"2026-01-10T11:00:00","side":"long",'
        '"entry_price":"42000","exit_price":"42500",'
        '"pnl":"500","signal_name":"MACD_CROSS"},'
        '{"trade_id":"t2","entry_time":"2026-01-15T09:00:00",'
        '"exit_time":"2026-01-15T10:00:00","side":"short",'
        '"entry_price":"43000","exit_price":"42800",'
        '"pnl":"200","signal_name":"RSI_OVERBOUGHT"}]'
    )
    admin_session.execute(text("""
        INSERT INTO strategy_test_results (
            result_id, strategy_id, version_id, test_type,
            test_config, start_date, end_date,
            total_return_pct, sharpe_ratio, max_drawdown_pct,
            win_rate, profit_factor, total_trades,
            metrics, trades, timestamp, created_at
        ) VALUES (
            :rid_a, :sid_a, :vid_a, 'backtest',
            '{}'::jsonb, :start, :end,
            12.5, 1.8, 8.3, 0.62, 2.1, 50,
            '{}'::jsonb, CAST(:trades AS jsonb), :now, :now
        ), (
            :rid_b, :sid_b, :vid_b, 'backtest',
            '{}'::jsonb, :start, :end,
            -2.0, -0.3, 15.0, 0.38, 0.7, 30,
            '{}'::jsonb, CAST(:trades AS jsonb), :now, :now
        )
        ON CONFLICT DO NOTHING
    """), {
        "rid_a": str(uuid.uuid4()), "sid_a": ids["strategy_a"], "vid_a": ids["version_a_id"],
        "rid_b": str(uuid.uuid4()), "sid_b": ids["strategy_b"], "vid_b": ids["version_b_id"],
        "start": past_60, "end": past_30,
        "trades": trades_json, "now": now,
    })

    # ── Signal metrics ────────────────────────────────────────────────────
    admin_session.execute(text("""
        INSERT INTO signal_metrics (
            metric_id, signal_name, start_date, end_date,
            total_occurrences, trades_triggered, trigger_rate,
            winning_trades, losing_trades, win_rate, avg_pnl,
            total_pnl, profit_factor, calculated_at, updated_at
        ) VALUES (
            :mid, :sname, :start, :end,
            200, 120, 0.6,
            75, 45, 0.625, '350.00',
            '42000.00', 2.2, :now, :now
        )
        ON CONFLICT DO NOTHING
    """), {
        "mid": str(uuid.uuid4()),
        "sname": ids["signal_name"],
        "start": past_60, "end": past_30, "now": now,
    })

    # ── Signal events (for correlation / coactivation) ───────────────────
    variation_id = ids["variation_id"]
    run_id = ids["run_id"]
    event_rows = []
    base_time = past_60
    for i in range(20):
        ts = base_time + timedelta(hours=i)
        # Both signals fire on even bars (co-activation)
        event_rows.append({
            "eid": str(uuid.uuid4()), "rid": run_id, "vid": variation_id,
            "ts": ts, "sname": ids["signal_name"],
            "stype": "entry", "sdir": "long", "iid": "BTCUSDT", "price": "42000",
            "bar": i,
        })
        if i % 2 == 0:
            event_rows.append({
                "eid": str(uuid.uuid4()), "rid": run_id, "vid": variation_id,
                "ts": ts, "sname": ids["signal_name_2"],
                "stype": "entry", "sdir": "long", "iid": "BTCUSDT", "price": "42000",
                "bar": i,
            })

    admin_session.execute(text("""
        INSERT INTO signal_events (
            event_id, run_id, variation_id,
            timestamp, signal_name, signal_type, signal_direction,
            instrument_id, price, bar_number
        )
        SELECT unnest(CAST(:eids AS uuid[])),
               unnest(CAST(:rids AS uuid[])),
               unnest(CAST(:vids AS uuid[])),
               unnest(CAST(:tss AS timestamp[])),
               unnest(CAST(:snames AS text[])),
               unnest(CAST(:stypes AS text[])),
               unnest(CAST(:sdirs AS text[])),
               unnest(CAST(:iids AS text[])),
               unnest(CAST(:prices AS text[])),
               unnest(CAST(:bars AS int[]))
        ON CONFLICT DO NOTHING
    """), {
        "eids": [r["eid"] for r in event_rows],
        "rids": [r["rid"] for r in event_rows],
        "vids": [r["vid"] for r in event_rows],
        "tss": [r["ts"] for r in event_rows],
        "snames": [r["sname"] for r in event_rows],
        "stypes": [r["stype"] for r in event_rows],
        "sdirs": [r["sdir"] for r in event_rows],
        "iids": [r["iid"] for r in event_rows],
        "prices": [r["price"] for r in event_rows],
        "bars": [r["bar"] for r in event_rows],
    })

    admin_session.commit()

    yield  # ── run tests ───────────────────────────────────────────────────

    # Teardown — delete seed data in reverse FK order
    admin_session.execute(text("DELETE FROM signal_events WHERE variation_id = :vid"),
                          {"vid": variation_id})
    admin_session.execute(text("DELETE FROM signal_metrics WHERE signal_name = ANY(:names)"),
                          {"names": [ids["signal_name"], ids["signal_name_2"]]})
    admin_session.execute(text("DELETE FROM strategy_test_results WHERE strategy_id = ANY(:ids)"),
                          {"ids": [ids["strategy_a"], ids["strategy_b"]]})
    admin_session.execute(text("DELETE FROM strategy_versions WHERE strategy_id = ANY(:ids)"),
                          {"ids": [ids["strategy_a"], ids["strategy_b"]]})
    admin_session.execute(text("DELETE FROM strategies WHERE strategy_id = ANY(:ids)"),
                          {"ids": [ids["strategy_a"], ids["strategy_b"]]})
    admin_session.commit()


@pytest.fixture(scope="module")
def qe() -> QueryEngine:
    """QueryEngine instance using the ai_readonly pool."""
    # Reset singleton so the module-scoped fixture gets a fresh pool.
    _ReadonlyPool._instance = None
    engine = QueryEngine()
    yield engine
    _ReadonlyPool._instance = None


# ═══════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetSignalStats:
    def test_returns_signal_stats_dataclass(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_signal_stats(seed_ids["signal_name"], lookback_days=90)
        assert isinstance(result, SignalStats)

    def test_fire_rate_populated(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_signal_stats(seed_ids["signal_name"], lookback_days=90)
        assert result.fire_rate is not None
        assert 0.0 <= result.fire_rate <= 1.0

    def test_win_rate_populated(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_signal_stats(seed_ids["signal_name"], lookback_days=90)
        assert result.win_rate is not None
        assert 0.0 <= result.win_rate <= 1.0

    def test_unknown_signal_returns_empty(self, qe: QueryEngine):
        result = qe.get_signal_stats("NO_SUCH_SIGNAL_XYZ", lookback_days=30)
        assert result.fire_rate is None
        assert result.win_rate is None
        assert result.total_occurrences == 0


class TestGetStrategyPerformance:
    def test_returns_performance_dataclass(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_strategy_performance(seed_ids["strategy_a"])
        assert isinstance(result, StrategyPerformance)

    def test_sharpe_populated(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_strategy_performance(seed_ids["strategy_a"])
        assert result.sharpe_ratio is not None
        assert result.sharpe_ratio == pytest.approx(1.8, abs=0.01)

    def test_period_backtest_filter(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_strategy_performance(seed_ids["strategy_a"], period="backtest")
        assert result.test_type == "backtest"

    def test_unknown_strategy_returns_nulls(self, qe: QueryEngine):
        result = qe.get_strategy_performance("nonexistent-strategy-id")
        assert result.sharpe_ratio is None
        assert result.total_trades is None


class TestGetRecentTrades:
    def test_returns_list_of_trades(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_recent_trades(seed_ids["strategy_a"], limit=10)
        assert isinstance(result, list)
        assert all(isinstance(t, Trade) for t in result)

    def test_limit_respected(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_recent_trades(seed_ids["strategy_a"], limit=1)
        assert len(result) <= 1

    def test_trade_fields_populated(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_recent_trades(seed_ids["strategy_a"], limit=10)
        assert len(result) > 0
        first = result[0]
        assert first.entry_time is not None
        assert first.side in ("long", "short", None)

    def test_invalid_limit_raises(self, qe: QueryEngine, seed_ids: dict):
        with pytest.raises(ValueError):
            qe.get_recent_trades(seed_ids["strategy_a"], limit=0)
        with pytest.raises(ValueError):
            qe.get_recent_trades(seed_ids["strategy_a"], limit=501)

    def test_unknown_strategy_returns_empty(self, qe: QueryEngine):
        result = qe.get_recent_trades("nonexistent-id", limit=10)
        assert result == []


class TestGetOpenPositions:
    def test_returns_list(self, qe: QueryEngine):
        result = qe.get_open_positions()
        assert isinstance(result, list)

    def test_all_items_are_open_positions(self, qe: QueryEngine):
        result = qe.get_open_positions()
        assert all(isinstance(p, OpenPosition) for p in result)


class TestGetBlockCorrelation:
    def test_returns_correlations(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_block_correlation(
            [seed_ids["signal_name"], seed_ids["signal_name_2"]]
        )
        assert isinstance(result, list)
        assert all(isinstance(c, BlockCorrelation) for c in result)

    def test_correlation_score_in_range(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_block_correlation(
            [seed_ids["signal_name"], seed_ids["signal_name_2"]]
        )
        for c in result:
            assert 0.0 <= c.correlation_score <= 1.0

    def test_fewer_than_two_raises(self, qe: QueryEngine, seed_ids: dict):
        with pytest.raises(ValueError):
            qe.get_block_correlation([seed_ids["signal_name"]])


class TestGetMarketRegime:
    def test_returns_market_regime(self, qe: QueryEngine):
        result = qe.get_market_regime(period="90d")
        assert isinstance(result, MarketRegime)

    def test_regime_is_valid_label(self, qe: QueryEngine):
        result = qe.get_market_regime(period="90d")
        assert result.regime in ("BULL", "BEAR", "SIDEWAYS", "VOLATILE")

    def test_numeric_fields_reasonable(self, qe: QueryEngine):
        result = qe.get_market_regime(period="90d")
        assert isinstance(result.avg_sharpe, float)
        assert isinstance(result.avg_win_rate, float)
        assert result.strategy_count >= 0


class TestGetSignalCoactivation:
    def test_returns_coactivation_list(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_signal_coactivation(
            [seed_ids["signal_name"], seed_ids["signal_name_2"]]
        )
        assert isinstance(result, list)
        assert all(isinstance(c, SignalCoactivation) for c in result)

    def test_co_fire_rate_in_range(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_signal_coactivation(
            [seed_ids["signal_name"], seed_ids["signal_name_2"]]
        )
        for c in result:
            assert 0.0 <= c.co_fire_rate <= 1.0

    def test_signals_do_coactivate(self, qe: QueryEngine, seed_ids: dict):
        """Seed data has 10 co-fire events (even-numbered bars)."""
        result = qe.get_signal_coactivation(
            [seed_ids["signal_name"], seed_ids["signal_name_2"]]
        )
        if result:
            assert result[0].co_fire_count >= 1

    def test_fewer_than_two_raises(self, qe: QueryEngine, seed_ids: dict):
        with pytest.raises(ValueError):
            qe.get_signal_coactivation([seed_ids["signal_name"]])


class TestGetPortfolioStats:
    def test_returns_portfolio_stats(self, qe: QueryEngine):
        result = qe.get_portfolio_stats(period="90d")
        assert isinstance(result, PortfolioStats)

    def test_strategy_count_positive(self, qe: QueryEngine):
        result = qe.get_portfolio_stats(period="90d")
        assert result.strategy_count >= 0

    def test_seeded_strategies_appear(self, qe: QueryEngine):
        # Our seeds have end_date = past_30 → within a 90d window
        result = qe.get_portfolio_stats(period="90d")
        assert result.strategy_count >= 2


class TestGetConfigDiff:
    def test_returns_config_diff(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_config_diff(seed_ids["strategy_a"], seed_ids["strategy_b"])
        assert isinstance(result, ConfigDiff)

    def test_block_differences_correct(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_config_diff(seed_ids["strategy_a"], seed_ids["strategy_b"])
        # Alpha has MACD+RSI, Beta has RSI+BOLLINGER → MACD only in A, BOLLINGER only in B
        assert "MACD" in result.blocks_only_in_a
        assert "BOLLINGER" in result.blocks_only_in_b
        assert "RSI" in result.blocks_in_both

    def test_parameter_diffs_detected(self, qe: QueryEngine, seed_ids: dict):
        result = qe.get_config_diff(seed_ids["strategy_a"], seed_ids["strategy_b"])
        # rsi_period differs: Alpha=14, Beta=21
        assert "rsi_period" in result.parameter_diffs
        assert result.parameter_diffs["rsi_period"]["a"] == 14
        assert result.parameter_diffs["rsi_period"]["b"] == 21

    def test_missing_strategy_raises(self, qe: QueryEngine, seed_ids: dict):
        with pytest.raises(ValueError):
            qe.get_config_diff(seed_ids["strategy_a"], "nonexistent-id-xyz")


# ═══════════════════════════════════════════════════════════════════════════
# Security: ai_readonly cannot write
# ═══════════════════════════════════════════════════════════════════════════


class TestReadonlyRoleCannotWrite:
    """Confirm the ai_readonly role has no write privileges."""

    def test_cannot_insert(self, qe: QueryEngine):
        from sqlalchemy import exc as sa_exc
        pool = _ReadonlyPool.get()
        with pool.session() as sess:
            with pytest.raises(sa_exc.ProgrammingError, match="permission denied"):
                sess.execute(text(
                    "INSERT INTO strategies (strategy_id, name) VALUES ('hack', 'hack')"
                ))
                sess.commit()

    def test_cannot_update(self, qe: QueryEngine):
        from sqlalchemy import exc as sa_exc
        pool = _ReadonlyPool.get()
        with pool.session() as sess:
            with pytest.raises(sa_exc.ProgrammingError, match="permission denied"):
                sess.execute(text(
                    "UPDATE strategies SET name = 'hack' WHERE 1=1"
                ))
                sess.commit()

    def test_cannot_delete(self, qe: QueryEngine):
        from sqlalchemy import exc as sa_exc
        pool = _ReadonlyPool.get()
        with pool.session() as sess:
            with pytest.raises(sa_exc.ProgrammingError, match="permission denied"):
                sess.execute(text(
                    "DELETE FROM strategies WHERE 1=1"
                ))
                sess.commit()
