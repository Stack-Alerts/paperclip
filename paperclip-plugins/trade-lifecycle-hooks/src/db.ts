// src/db.ts
// PostgreSQL connection and query layer for BTC Trade Engine.
// Connects to the optimizer_v3 database to query strategies,
// positions, and risk metrics.
//
// ADR: ADR-0005 (Trade Lifecycle Run Hooks)
// Issue: BTCAAAAA-26521 (P4.2a — DB connection and query layer)

import type { Pool, PoolClient, QueryResult, PoolConfig as PgPoolConfig } from "pg";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DbPoolConfig {
  connectionString: string;
  max?: number;
  idleTimeoutMillis?: number;
  connectionTimeoutMillis?: number;
}

export interface HealthCheckResult {
  ok: boolean;
  latencyMs: number;
  error?: string;
}

export interface StrategyRow {
  strategy_id: string;
  name: string;
  version_id: string | null;
  version_number: number | null;
  validation_status: string | null;
  blocks: unknown;
  signals: unknown;
  risk_management: unknown;
  strategy_type: string | null;
  metrics: unknown;
  exit_conditions: unknown;
  entry_conditions: unknown;
  version_timestamp: string | null;
  created_at: string;
  updated_at: string;
}

export interface StrategyQueryResult {
  strategy: StrategyRow | null;
  error?: string;
}

export interface PositionRow {
  instrument_id: string;
  total_signals: number;
  signals_led_to_trade: number;
  winning_trades: number;
  losing_trades: number;
  total_pnl: string | null;
  latest_trade_at: string | null;
}

export interface PositionQueryResult {
  positions: PositionRow[];
  error?: string;
}

export interface RiskMetricRow {
  result_id: string;
  strategy_id: string;
  strategy_name: string;
  test_type: string;
  risk_metrics: unknown;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  profit_factor: number | null;
  total_trades: number | null;
  win_rate: number | null;
  test_timestamp: string;
}

export interface RiskMetricsQueryResult {
  riskMetrics: RiskMetricRow[];
  error?: string;
}

// ---------------------------------------------------------------------------
// Pool management
// ---------------------------------------------------------------------------

let pool: Pool | null = null;

export async function createPool(config: DbPoolConfig): Promise<Pool> {
  const { default: pg } = await import("pg");

  const poolConfig: PgPoolConfig = {
    connectionString: config.connectionString,
    max: config.max ?? 5,
    idleTimeoutMillis: config.idleTimeoutMillis ?? 30_000,
    connectionTimeoutMillis: config.connectionTimeoutMillis ?? 10_000,
  };

  pool = new pg.Pool(poolConfig);

  pool.on("error", (err: Error) => {
    console.error("[db] Unexpected pool error:", err.message);
  });

  return pool;
}

export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}

export function getPool(): Pool | null {
  return pool;
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

export async function healthCheck(): Promise<HealthCheckResult> {
  if (!pool) {
    return { ok: false, latencyMs: 0, error: "Pool not initialized" };
  }

  const started = Date.now();
  try {
    const result = await pool.query<{ health: number }>("SELECT 1 AS health");
    const latencyMs = Date.now() - started;
    return { ok: result.rows[0]?.health === 1, latencyMs };
  } catch (err) {
    return {
      ok: false,
      latencyMs: Date.now() - started,
      error: String(err),
    };
  }
}

// ---------------------------------------------------------------------------
// queryStrategies — fetch strategy definition from strategies + latest version
// ---------------------------------------------------------------------------

export async function queryStrategies(
  strategyId: string
): Promise<StrategyQueryResult> {
  if (!pool) return { strategy: null, error: "Pool not initialized" };

  try {
    const result: QueryResult<StrategyRow> = await pool.query(
      `SELECT s.strategy_id,
              s.name,
              s.created_at,
              s.updated_at,
              sv.version_id,
              sv.version_number,
              sv.validation_status,
              sv.blocks,
              sv.signals,
              sv.risk_management,
              sv.strategy_type,
              sv.metrics,
              sv.exit_conditions,
              sv.entry_conditions,
              sv.timestamp AS version_timestamp
       FROM strategies s
       LEFT JOIN LATERAL (
         SELECT *
         FROM strategy_versions
         WHERE strategy_id = s.strategy_id
         ORDER BY version_number DESC
         LIMIT 1
       ) sv ON true
       WHERE s.strategy_id = $1`,
      [strategyId]
    );

    return { strategy: result.rows[0] ?? null };
  } catch (err) {
    return { strategy: null, error: String(err) };
  }
}

// ---------------------------------------------------------------------------
// queryPositions — aggregate position state from signal_events
// ---------------------------------------------------------------------------

export async function queryPositions(): Promise<PositionQueryResult> {
  if (!pool) return { positions: [], error: "Pool not initialized" };

  try {
    const result: QueryResult<PositionRow> = await pool.query(
      `SELECT instrument_id,
              COUNT(*)::int                                AS total_signals,
              COUNT(*) FILTER (WHERE led_to_trade = true)::int
                                                           AS signals_led_to_trade,
              COUNT(*) FILTER (WHERE trade_result = 'win')::int
                                                           AS winning_trades,
              COUNT(*) FILTER (WHERE trade_result = 'loss')::int
                                                           AS losing_trades,
              COALESCE(SUM(trade_pnl::numeric), 0)::text   AS total_pnl,
              MAX(timestamp)::text                         AS latest_trade_at
       FROM signal_events
       WHERE led_to_trade = true
         AND trade_result IS NOT NULL
       GROUP BY instrument_id
       ORDER BY instrument_id`
    );

    return { positions: result.rows };
  } catch (err) {
    return { positions: [], error: String(err) };
  }
}

// ---------------------------------------------------------------------------
// queryRiskMetrics — fetch risk metrics from strategy_test_results
// ---------------------------------------------------------------------------

export async function queryRiskMetrics(
  strategyId?: string
): Promise<RiskMetricsQueryResult> {
  if (!pool) return { riskMetrics: [], error: "Pool not initialized" };

  try {
    const params: string[] = [];
    let where = "WHERE str.risk_metrics IS NOT NULL";

    if (strategyId) {
      where += " AND str.strategy_id = $1";
      params.push(strategyId);
    }

    const limit = strategyId ? "LIMIT 5" : "LIMIT 20";

    const result: QueryResult<RiskMetricRow> = await pool.query(
      `SELECT str.result_id,
              str.strategy_id,
              s.name                          AS strategy_name,
              str.test_type,
              str.risk_metrics,
              str.sharpe_ratio,
              str.max_drawdown_pct,
              str.profit_factor,
              str.total_trades,
              str.win_rate,
              str.timestamp                   AS test_timestamp
       FROM strategy_test_results str
       JOIN strategies s ON s.strategy_id = str.strategy_id
       ${where}
       ORDER BY str.timestamp DESC
       ${limit}`,
      params
    );

    return { riskMetrics: result.rows };
  } catch (err) {
    return { riskMetrics: [], error: String(err) };
  }
}
