"""
AI Consultant — Read-only Query Engine
=======================================

Exposes 9 parameterised query tools that the LLM agent calls.
NO raw SQL ever passes from the LLM layer — every query is a named
Python function with typed parameters and a pre-written SQL template.

Connection pool:  separate pool connecting as the `ai_readonly` DB role,
                  distinct from the main app pool.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typed return types
# ---------------------------------------------------------------------------


@dataclass
class SignalStats:
    signal_name: str
    lookback_days: int
    fire_rate: Optional[float]       # fraction of bars where signal fired
    win_rate: Optional[float]
    avg_return: Optional[float]      # avg PnL per triggered trade (USD)
    total_occurrences: int
    trades_triggered: int


@dataclass
class StrategyPerformance:
    strategy_id: str
    period: str
    total_pnl: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown_pct: Optional[float]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    total_trades: Optional[int]
    test_type: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]


@dataclass
class Trade:
    trade_id: Any
    entry_time: Optional[str]
    exit_time: Optional[str]
    side: Optional[str]
    entry_price: Optional[str]
    exit_price: Optional[str]
    pnl: Optional[str]
    signal_name: Optional[str]


@dataclass
class OpenPosition:
    strategy_id: str
    strategy_name: str
    side: Optional[str]
    entry_price: Optional[str]
    entry_time: Optional[str]
    current_version: int


@dataclass
class BlockCorrelation:
    block_id_a: str
    block_id_b: str
    co_occurrence_count: int
    correlation_score: float          # normalised co-fire rate


@dataclass
class MarketRegime:
    period: str
    regime: str                       # BULL / BEAR / SIDEWAYS / VOLATILE
    avg_sharpe: float
    avg_win_rate: float
    strategy_count: int
    dominant_block_category: Optional[str]


@dataclass
class SignalCoactivation:
    signal_a: str
    signal_b: str
    co_fire_count: int
    total_fires_a: int
    total_fires_b: int
    co_fire_rate: float               # co_fire_count / min(a_fires, b_fires)


@dataclass
class PortfolioStats:
    period: str
    strategy_count: int
    avg_sharpe: Optional[float]
    avg_win_rate: Optional[float]
    avg_max_drawdown_pct: Optional[float]
    total_pnl: Optional[float]
    best_strategy_id: Optional[str]
    worst_strategy_id: Optional[str]


@dataclass
class ConfigDiff:
    strategy_id_a: str
    strategy_id_b: str
    blocks_only_in_a: List[str] = field(default_factory=list)
    blocks_only_in_b: List[str] = field(default_factory=list)
    blocks_in_both: List[str] = field(default_factory=list)
    parameter_diffs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    signal_diffs: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Connection pool for ai_readonly role
# ---------------------------------------------------------------------------


def _build_readonly_url() -> str:
    """Construct the DB URL for the ai_readonly role via pydantic-settings (BTCAAAAA-30576)."""
    from src.optimizer_v3.database.settings import get_database_settings

    return get_database_settings().readonly_url()


class _ReadonlyPool:
    """Lazy-initialised singleton connection pool for the ai_readonly role."""

    _instance: Optional[_ReadonlyPool] = None

    def __init__(self) -> None:
        from src.optimizer_v3.database.settings import get_database_settings

        s = get_database_settings()
        url = _build_readonly_url()
        self._engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=s.AI_READONLY_POOL_SIZE,
            max_overflow=s.AI_READONLY_MAX_OVERFLOW,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            execution_options={"no_parameters": False},
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        logger.info("ai_readonly connection pool initialised (%s)", url.split("@")[-1])

    @classmethod
    def get(cls) -> _ReadonlyPool:
        if cls._instance is None:
            cls._instance = _ReadonlyPool()
        return cls._instance

    def session(self) -> Session:
        return self._session_factory()

    def dispose(self) -> None:
        self._engine.dispose()
        _ReadonlyPool._instance = None


# ---------------------------------------------------------------------------
# QueryEngine
# ---------------------------------------------------------------------------


class QueryEngine:
    """
    The single entry-point for all AI Consultant DB queries.

    Usage::

        engine = QueryEngine()
        stats = engine.get_signal_stats("MACD_CROSS", lookback_days=90)

    All methods use parameterised queries; no f-string interpolation of
    caller-supplied values is permitted anywhere in this class.
    """

    def __init__(self, pool: Optional[_ReadonlyPool] = None) -> None:
        self._pool = pool or _ReadonlyPool.get()

    # ------------------------------------------------------------------
    # 1. get_signal_stats
    # ------------------------------------------------------------------

    def get_signal_stats(
        self,
        signal_id: str,
        lookback_days: int,
    ) -> SignalStats:
        """Fire rate, win rate, and avg return for a signal over the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        sql = text("""
            SELECT
                sm.signal_name,
                sm.total_occurrences,
                sm.trades_triggered,
                sm.trigger_rate   AS fire_rate,
                sm.win_rate,
                sm.avg_pnl::numeric AS avg_pnl
            FROM signal_metrics sm
            WHERE sm.signal_name = :signal_name
              AND sm.start_date  >= :cutoff
            ORDER BY sm.calculated_at DESC
            LIMIT 1
        """)
        with self._pool.session() as sess:
            row = sess.execute(sql, {"signal_name": signal_id, "cutoff": cutoff}).mappings().first()

        if row is None:
            return SignalStats(
                signal_name=signal_id,
                lookback_days=lookback_days,
                fire_rate=None,
                win_rate=None,
                avg_return=None,
                total_occurrences=0,
                trades_triggered=0,
            )
        return SignalStats(
            signal_name=row["signal_name"],
            lookback_days=lookback_days,
            fire_rate=float(row["fire_rate"]) if row["fire_rate"] is not None else None,
            win_rate=float(row["win_rate"]) if row["win_rate"] is not None else None,
            avg_return=float(row["avg_pnl"]) if row["avg_pnl"] is not None else None,
            total_occurrences=row["total_occurrences"] or 0,
            trades_triggered=row["trades_triggered"] or 0,
        )

    # ------------------------------------------------------------------
    # 2. get_strategy_performance
    # ------------------------------------------------------------------

    def get_strategy_performance(
        self,
        strategy_id: str,
        period: str = "latest",
    ) -> StrategyPerformance:
        """P&L, Sharpe, and drawdown for a strategy.

        ``period`` accepts:
        - ``"latest"``   — most recent test result
        - ``"backtest"`` — most recent backtest result
        - ``"90d"`` / ``"30d"`` / ``"365d"`` — test results whose end_date
          falls within the last N days
        """
        base_sql = """
            SELECT
                str.strategy_id,
                str.test_type,
                str.start_date,
                str.end_date,
                str.total_return_pct AS total_pnl,
                str.sharpe_ratio,
                str.max_drawdown_pct,
                str.win_rate,
                str.profit_factor,
                str.total_trades
            FROM strategy_test_results str
            WHERE str.strategy_id = :strategy_id
        """
        params: Dict[str, Any] = {"strategy_id": strategy_id}

        if period == "backtest":
            base_sql += " AND str.test_type = 'backtest'"
        elif period.endswith("d") and period[:-1].isdigit():
            days = int(period[:-1])
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            base_sql += " AND str.end_date >= :cutoff"
            params["cutoff"] = cutoff

        base_sql += " ORDER BY str.timestamp DESC LIMIT 1"

        with self._pool.session() as sess:
            row = sess.execute(text(base_sql), params).mappings().first()

        if row is None:
            return StrategyPerformance(
                strategy_id=strategy_id,
                period=period,
                total_pnl=None,
                sharpe_ratio=None,
                max_drawdown_pct=None,
                win_rate=None,
                profit_factor=None,
                total_trades=None,
                test_type="unknown",
                start_date=None,
                end_date=None,
            )
        return StrategyPerformance(
            strategy_id=row["strategy_id"],
            period=period,
            total_pnl=float(row["total_pnl"]) if row["total_pnl"] is not None else None,
            sharpe_ratio=float(row["sharpe_ratio"]) if row["sharpe_ratio"] is not None else None,
            max_drawdown_pct=float(row["max_drawdown_pct"]) if row["max_drawdown_pct"] is not None else None,
            win_rate=float(row["win_rate"]) if row["win_rate"] is not None else None,
            profit_factor=float(row["profit_factor"]) if row["profit_factor"] is not None else None,
            total_trades=row["total_trades"],
            test_type=row["test_type"],
            start_date=row["start_date"],
            end_date=row["end_date"],
        )

    # ------------------------------------------------------------------
    # 3. get_recent_trades
    # ------------------------------------------------------------------

    def get_recent_trades(
        self,
        strategy_id: str,
        limit: int = 20,
    ) -> List[Trade]:
        """Return the last ``limit`` trades for a strategy from the most recent test result."""
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")

        sql = text("""
            SELECT trades
            FROM strategy_test_results
            WHERE strategy_id = :strategy_id
              AND trades IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        with self._pool.session() as sess:
            row = sess.execute(sql, {"strategy_id": strategy_id}).mappings().first()

        if row is None or not row["trades"]:
            return []

        raw_trades: List[Dict[str, Any]] = row["trades"]
        # Trades are stored as a JSONB list; take the last N after sorting by entry_time.
        raw_trades.sort(key=lambda t: t.get("entry_time", ""), reverse=True)
        return [
            Trade(
                trade_id=t.get("trade_id"),
                entry_time=t.get("entry_time"),
                exit_time=t.get("exit_time"),
                side=t.get("side"),
                entry_price=t.get("entry_price"),
                exit_price=t.get("exit_price"),
                pnl=t.get("pnl") or t.get("realized_pnl"),
                signal_name=t.get("signal_name") or t.get("entry_signal"),
            )
            for t in raw_trades[:limit]
        ]

    # ------------------------------------------------------------------
    # 4. get_open_positions
    # ------------------------------------------------------------------

    def get_open_positions(self) -> List[OpenPosition]:
        """Return strategies whose most recent test result is a live/paper trade
        with no closed end date — i.e. positions still open."""
        sql = text("""
            SELECT
                s.strategy_id,
                s.name            AS strategy_name,
                sv.version_number AS current_version,
                sv.parameters     AS params
            FROM strategies s
            JOIN strategy_versions sv
              ON sv.strategy_id   = s.strategy_id
             AND sv.version_number = (
                   SELECT MAX(sv2.version_number)
                   FROM strategy_versions sv2
                   WHERE sv2.strategy_id = s.strategy_id
                 )
            JOIN strategy_test_results str
              ON str.strategy_id = s.strategy_id
             AND str.test_type   IN ('paper_trade', 'live')
             AND str.end_date    > now()
        """)
        with self._pool.session() as sess:
            rows = sess.execute(sql).mappings().all()

        positions = []
        for row in rows:
            params = row["params"] or {}
            positions.append(
                OpenPosition(
                    strategy_id=row["strategy_id"],
                    strategy_name=row["strategy_name"],
                    side=params.get("direction") or params.get("side"),
                    entry_price=params.get("entry_price"),
                    entry_time=params.get("entry_time"),
                    current_version=row["current_version"],
                )
            )
        return positions

    # ------------------------------------------------------------------
    # 5. get_block_correlation
    # ------------------------------------------------------------------

    def get_block_correlation(
        self,
        block_ids: Sequence[str],
    ) -> List[BlockCorrelation]:
        """Pairwise co-occurrence of signal events for the requested blocks.

        A 'block' signal is identified by matching ``signal_name`` against the
        block prefix (e.g. ``"MACD_CROSS"`` fires events whose ``signal_name``
        starts with ``"MACD"``).
        """
        if len(block_ids) < 2:
            raise ValueError("At least two block IDs are required for correlation")

        # Pull raw co-occurrence counts via a self-join on signal_events
        # within a ±1 bar window (same variation_id, bar_number within 1).
        sql = text("""
            SELECT
                se_a.signal_name AS signal_a,
                se_b.signal_name AS signal_b,
                COUNT(*)         AS co_count,
                COUNT(DISTINCT se_a.variation_id) AS shared_variations
            FROM signal_events se_a
            JOIN signal_events se_b
              ON se_b.variation_id  = se_a.variation_id
             AND se_b.signal_name  != se_a.signal_name
             AND ABS(se_b.bar_number - se_a.bar_number) <= 1
            WHERE se_a.signal_name = ANY(:block_ids)
              AND se_b.signal_name = ANY(:block_ids)
            GROUP BY se_a.signal_name, se_b.signal_name
        """)
        with self._pool.session() as sess:
            rows = sess.execute(sql, {"block_ids": list(block_ids)}).mappings().all()

        # Build total-fires lookup for normalisation
        total_sql = text("""
            SELECT signal_name, COUNT(*) AS total
            FROM signal_events
            WHERE signal_name = ANY(:block_ids)
            GROUP BY signal_name
        """)
        with self._pool.session() as sess:
            total_rows = sess.execute(total_sql, {"block_ids": list(block_ids)}).mappings().all()
        totals = {r["signal_name"]: r["total"] for r in total_rows}

        results = []
        seen = set()
        for row in rows:
            pair = tuple(sorted([row["signal_a"], row["signal_b"]]))
            if pair in seen:
                continue
            seen.add(pair)
            min_fires = min(totals.get(pair[0], 1), totals.get(pair[1], 1))
            results.append(
                BlockCorrelation(
                    block_id_a=pair[0],
                    block_id_b=pair[1],
                    co_occurrence_count=row["co_count"],
                    correlation_score=round(row["co_count"] / max(min_fires * 3, 1), 4),
                )
            )
        return results

    # ------------------------------------------------------------------
    # 6. get_market_regime
    # ------------------------------------------------------------------

    def get_market_regime(self, period: str = "90d") -> MarketRegime:
        """Classify the prevailing market regime from aggregated strategy results.

        Regime classification heuristic (based on avg Sharpe + win-rate across
        all completed backtests in the period):
        - avg_sharpe > 1.0 and avg_win_rate > 0.55  → BULL
        - avg_sharpe < 0.0 or avg_win_rate < 0.40   → BEAR
        - std(sharpe) > 1.5                          → VOLATILE
        - otherwise                                  → SIDEWAYS
        """
        days = int(period.rstrip("d")) if period.endswith("d") and period[:-1].isdigit() else 90
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        sql = text("""
            SELECT
                AVG(sharpe_ratio)       AS avg_sharpe,
                AVG(win_rate)           AS avg_win_rate,
                STDDEV(sharpe_ratio)    AS std_sharpe,
                COUNT(*)                AS strategy_count
            FROM strategy_test_results
            WHERE test_type   = 'backtest'
              AND end_date    >= :cutoff
              AND sharpe_ratio IS NOT NULL
        """)
        block_sql = text("""
            SELECT sv.blocks
            FROM strategy_versions sv
            JOIN strategy_test_results str
              ON str.strategy_id   = sv.strategy_id
             AND str.test_type     = 'backtest'
             AND str.end_date     >= :cutoff
             AND str.sharpe_ratio  > 1.0
            ORDER BY str.sharpe_ratio DESC
            LIMIT 10
        """)

        with self._pool.session() as sess:
            agg = sess.execute(sql, {"cutoff": cutoff}).mappings().first()
            block_rows = sess.execute(block_sql, {"cutoff": cutoff}).mappings().all()

        avg_sharpe = float(agg["avg_sharpe"]) if agg and agg["avg_sharpe"] is not None else 0.0
        avg_win_rate = float(agg["avg_win_rate"]) if agg and agg["avg_win_rate"] is not None else 0.0
        std_sharpe = float(agg["std_sharpe"]) if agg and agg["std_sharpe"] is not None else 0.0
        count = int(agg["strategy_count"]) if agg else 0

        if std_sharpe > 1.5:
            regime = "VOLATILE"
        elif avg_sharpe > 1.0 and avg_win_rate > 0.55:
            regime = "BULL"
        elif avg_sharpe < 0.0 or avg_win_rate < 0.40:
            regime = "BEAR"
        else:
            regime = "SIDEWAYS"

        # Dominant category = most common category string in top-performing strategy blocks
        category_counts: Dict[str, int] = {}
        for r in block_rows:
            for block in (r["blocks"] or []):
                cat = block.get("category", "")
                if cat:
                    category_counts[cat] = category_counts.get(cat, 0) + 1
        dominant = max(category_counts, key=category_counts.get) if category_counts else None

        return MarketRegime(
            period=period,
            regime=regime,
            avg_sharpe=round(avg_sharpe, 4),
            avg_win_rate=round(avg_win_rate, 4),
            strategy_count=count,
            dominant_block_category=dominant,
        )

    # ------------------------------------------------------------------
    # 7. get_signal_coactivation
    # ------------------------------------------------------------------

    def get_signal_coactivation(
        self,
        signal_ids: Sequence[str],
    ) -> List[SignalCoactivation]:
        """Co-fire statistics: how often two signals fire within the same bar."""
        if len(signal_ids) < 2:
            raise ValueError("At least two signal IDs required")

        sql = text("""
            SELECT
                se_a.signal_name   AS signal_a,
                se_b.signal_name   AS signal_b,
                COUNT(*)           AS co_fire_count
            FROM signal_events se_a
            JOIN signal_events se_b
              ON  se_b.variation_id = se_a.variation_id
             AND  se_b.timestamp   = se_a.timestamp
             AND  se_b.signal_name != se_a.signal_name
            WHERE se_a.signal_name = ANY(:signal_ids)
              AND se_b.signal_name = ANY(:signal_ids)
            GROUP BY se_a.signal_name, se_b.signal_name
        """)
        totals_sql = text("""
            SELECT signal_name, COUNT(*) AS total
            FROM signal_events
            WHERE signal_name = ANY(:signal_ids)
            GROUP BY signal_name
        """)
        with self._pool.session() as sess:
            rows = sess.execute(sql, {"signal_ids": list(signal_ids)}).mappings().all()
            total_rows = sess.execute(totals_sql, {"signal_ids": list(signal_ids)}).mappings().all()

        totals = {r["signal_name"]: r["total"] for r in total_rows}
        results = []
        seen: set = set()
        for row in rows:
            pair = tuple(sorted([row["signal_a"], row["signal_b"]]))
            if pair in seen:
                continue
            seen.add(pair)
            fires_a = totals.get(pair[0], 1)
            fires_b = totals.get(pair[1], 1)
            results.append(
                SignalCoactivation(
                    signal_a=pair[0],
                    signal_b=pair[1],
                    co_fire_count=row["co_fire_count"],
                    total_fires_a=fires_a,
                    total_fires_b=fires_b,
                    co_fire_rate=round(row["co_fire_count"] / max(min(fires_a, fires_b), 1), 4),
                )
            )
        return results

    # ------------------------------------------------------------------
    # 8. get_portfolio_stats
    # ------------------------------------------------------------------

    def get_portfolio_stats(self, period: str = "90d") -> PortfolioStats:
        """Portfolio-level aggregates across all strategies in the given period."""
        days = int(period.rstrip("d")) if period.endswith("d") and period[:-1].isdigit() else 90
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        sql = text("""
            SELECT
                COUNT(DISTINCT strategy_id)                            AS strategy_count,
                AVG(sharpe_ratio)                                      AS avg_sharpe,
                AVG(win_rate)                                          AS avg_win_rate,
                AVG(max_drawdown_pct)                                  AS avg_max_dd,
                SUM(total_return_pct)                                  AS total_pnl,
                MAX(sharpe_ratio)                                      AS best_sharpe,
                MIN(sharpe_ratio)                                      AS worst_sharpe
            FROM strategy_test_results
            WHERE test_type = 'backtest'
              AND end_date  >= :cutoff
        """)
        best_sql = text("""
            SELECT strategy_id
            FROM strategy_test_results
            WHERE test_type = 'backtest' AND end_date >= :cutoff
            ORDER BY sharpe_ratio DESC NULLS LAST
            LIMIT 1
        """)
        worst_sql = text("""
            SELECT strategy_id
            FROM strategy_test_results
            WHERE test_type = 'backtest' AND end_date >= :cutoff
            ORDER BY sharpe_ratio ASC NULLS LAST
            LIMIT 1
        """)
        with self._pool.session() as sess:
            agg = sess.execute(sql, {"cutoff": cutoff}).mappings().first()
            best = sess.execute(best_sql, {"cutoff": cutoff}).mappings().first()
            worst = sess.execute(worst_sql, {"cutoff": cutoff}).mappings().first()

        return PortfolioStats(
            period=period,
            strategy_count=int(agg["strategy_count"]) if agg else 0,
            avg_sharpe=float(agg["avg_sharpe"]) if agg and agg["avg_sharpe"] is not None else None,
            avg_win_rate=float(agg["avg_win_rate"]) if agg and agg["avg_win_rate"] is not None else None,
            avg_max_drawdown_pct=float(agg["avg_max_dd"]) if agg and agg["avg_max_dd"] is not None else None,
            total_pnl=float(agg["total_pnl"]) if agg and agg["total_pnl"] is not None else None,
            best_strategy_id=best["strategy_id"] if best else None,
            worst_strategy_id=worst["strategy_id"] if worst else None,
        )

    # ------------------------------------------------------------------
    # 9. get_config_diff
    # ------------------------------------------------------------------

    def get_config_diff(
        self,
        strategy_id_a: str,
        strategy_id_b: str,
    ) -> ConfigDiff:
        """Structural diff of the latest versions of two strategy configs."""
        sql = text("""
            SELECT sv.strategy_id, sv.blocks, sv.signals, sv.parameters
            FROM strategy_versions sv
            WHERE sv.strategy_id = ANY(:ids)
              AND sv.version_number = (
                    SELECT MAX(sv2.version_number)
                    FROM strategy_versions sv2
                    WHERE sv2.strategy_id = sv.strategy_id
                  )
        """)
        with self._pool.session() as sess:
            rows = sess.execute(
                sql, {"ids": [strategy_id_a, strategy_id_b]}
            ).mappings().all()

        configs: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            configs[row["strategy_id"]] = {
                "blocks": row["blocks"] or [],
                "signals": row["signals"] or {},
                "parameters": row["parameters"] or {},
            }

        if strategy_id_a not in configs or strategy_id_b not in configs:
            missing = [sid for sid in (strategy_id_a, strategy_id_b) if sid not in configs]
            raise ValueError(f"Strategy IDs not found: {missing}")

        cfg_a = configs[strategy_id_a]
        cfg_b = configs[strategy_id_b]

        # Block-level diff — use block 'name' field as identifier
        names_a = {b.get("name", str(i)) for i, b in enumerate(cfg_a["blocks"])}
        names_b = {b.get("name", str(i)) for i, b in enumerate(cfg_b["blocks"])}

        only_a = sorted(names_a - names_b)
        only_b = sorted(names_b - names_a)
        in_both = sorted(names_a & names_b)

        # Parameter diff — flat comparison
        param_diffs: Dict[str, Dict[str, Any]] = {}
        all_param_keys = set(cfg_a["parameters"]) | set(cfg_b["parameters"])
        for k in all_param_keys:
            val_a = cfg_a["parameters"].get(k)
            val_b = cfg_b["parameters"].get(k)
            if val_a != val_b:
                param_diffs[k] = {"a": val_a, "b": val_b}

        # Signal diff
        sig_diffs: Dict[str, Any] = {}
        all_sig_keys = set(cfg_a["signals"]) | set(cfg_b["signals"])
        for k in all_sig_keys:
            val_a = cfg_a["signals"].get(k)
            val_b = cfg_b["signals"].get(k)
            if val_a != val_b:
                sig_diffs[k] = {"a": val_a, "b": val_b}

        return ConfigDiff(
            strategy_id_a=strategy_id_a,
            strategy_id_b=strategy_id_b,
            blocks_only_in_a=only_a,
            blocks_only_in_b=only_b,
            blocks_in_both=in_both,
            parameter_diffs=param_diffs,
            signal_diffs=sig_diffs,
        )
