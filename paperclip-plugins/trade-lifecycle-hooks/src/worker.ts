// src/worker.ts
// Trade Lifecycle Hooks — Plugin Worker
// Phase 2: Real exchange health probe (multi-exchange), risk limit query,
// and DB-backed strategy validation, position tracking, and risk metrics.
//
// Pre-run: strategy validation, exchange connectivity, risk limits
// Post-run: trade execution logging, audit trail, position reconciliation

import { definePlugin } from "@paperclipai/plugin-sdk";
import type {
  PluginEvent,
  PluginContext,
  ToolRunContext,
  ToolResult,
} from "@paperclipai/plugin-sdk";
import {
  createPool,
  closePool,
  healthCheck as dbHealthCheck,
  queryStrategies,
  queryPositions,
  queryRiskMetrics,
} from "./db.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExchangeConfig {
  name: string;
  healthEndpoint: string;
  timeoutMs: number;
  expectedStatus: number;
}

interface RiskLimits {
  maxHeatRatio: number;
  maxDailyLossUsdt: number;
  maxPositionSizeBtc: number;
}

interface PluginConfig {
  databaseUrlRef: string;
  preRunCheckLevel: "basic" | "strict";
  exchanges?: ExchangeConfig[];
  exchangeHealthEndpoint?: string;
  exchangeHealthTimeoutMs?: number;
  riskDataEndpoint?: string;
  riskDataEndpointTimeoutMs?: number;
  riskLimits: RiskLimits;
  auditEnabled: boolean;
  reconciliationIntervalSeconds: number;
}

interface StrategyValidationResult {
  strategyId: string;
  isValid: boolean;
  level: string;
  errors: string[];
  warnings: string[];
  checkedAt: string;
}

type ExchangeHealthStatus =
  | "healthy"
  | "degraded"
  | "unhealthy"
  | "timeout"
  | "unknown";

interface ExchangeHealthResult {
  exchange: string;
  status: ExchangeHealthStatus;
  latencyMs: number;
  statusCode?: number;
  error?: string;
  endpoint: string;
  checkedAt: string;
}

interface ExchangeHealthSummary {
  allHealthy: boolean;
  healthyCount: number;
  unhealthyCount: number;
  totalCount: number;
  results: ExchangeHealthResult[];
}

type BreachSeverity = "WARNING" | "CRITICAL";

interface RiskBreach {
  metric: string;
  current: number;
  limit: number;
  unit: string;
  severity: BreachSeverity;
  message: string;
}

interface RiskSnapshot {
  heatRatio: number;
  dailyPnl: number;
  dailyLossLimit: number;
  positionSizeBtc: number;
  maxPositionSizeBtc: number;
  passed: boolean;
  breaches: RiskBreach[];
  severity: "OK" | "WARNING" | "CRITICAL";
  source: "plugin-state" | "http-endpoint" | "config-defaults";
  checkedAt: string;
}

interface TradeRecord {
  tradeId: string;
  side: string;
  quantity: number;
  price: number;
  symbol: string;
  strategyId?: string;
  stopLossPrice?: number;
  takeProfitPrice?: number;
  timestamp: string;
  runId: string;
  agentId: string;
}

interface PositionDivergence {
  symbol: string;
  expectedQuantity: number;
  actualQuantity: number;
  severity: "WARNING" | "CRITICAL";
  message: string;
}

interface RunStartedPayload {
  agentId: string;
  runId: string;
  issueTitle?: string;
  issueDescription?: string;
}

interface RunFinishedPayload {
  agentId: string;
  runId: string;
  output?: string;
  result?: string;
  duration?: number;
  error?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_TIMEOUT_MS = 5000;
const DEFAULT_RISK_ENDPOINT_TIMEOUT_MS = 3000;
const DEFAULT_RISK_LIMITS: RiskLimits = {
  maxHeatRatio: 0.8,
  maxDailyLossUsdt: 500,
  maxPositionSizeBtc: 1.0,
};

const HEAT_WARNING_THRESHOLD = 0.5; // 50% heat triggers WARNING (before maxHeatRatio)
const PNL_WARNING_RATIO = 0.7; // 70% of maxDailyLoss triggers WARNING

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function getConfig(ctx: PluginContext): Promise<PluginConfig> {
  return (await ctx.config.get()) as unknown as PluginConfig;
}

function isoNow(): string {
  return new Date().toISOString();
}

function safeParse<T>(raw: unknown, fallback: T): T {
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw) as T;
    } catch {
      return fallback;
    }
  }
  return (raw as T) ?? fallback;
}

function classifyExchangeError(err: unknown): {
  status: ExchangeHealthStatus;
  message: string;
} {
  const msg = String(err);
  if (msg.includes("AbortError") || msg.includes("timeout")) {
    return { status: "timeout", message: "Connection timed out" };
  }
  if (msg.includes("ENOTFOUND") || msg.includes("DNS") || msg.includes("getaddrinfo")) {
    return { status: "unhealthy", message: "DNS resolution failed" };
  }
  if (msg.includes("ECONNREFUSED")) {
    return { status: "unhealthy", message: "Connection refused" };
  }
  if (msg.includes("rate limit") || msg.includes("429")) {
    return { status: "degraded", message: "Rate limited" };
  }
  return { status: "unhealthy", message: msg };
}

function resolveExchanges(config: PluginConfig): ExchangeConfig[] {
  if (config.exchanges && config.exchanges.length > 0) {
    return config.exchanges;
  }
  if (config.exchangeHealthEndpoint) {
    return [
      {
        name: "default",
        healthEndpoint: config.exchangeHealthEndpoint,
        timeoutMs: config.exchangeHealthTimeoutMs ?? DEFAULT_TIMEOUT_MS,
        expectedStatus: 200,
      },
    ];
  }
  return [
    {
      name: "binance-testnet",
      healthEndpoint: "https://testnet.binancefuture.com/fapi/v1/ping",
      timeoutMs: config.exchangeHealthTimeoutMs ?? DEFAULT_TIMEOUT_MS,
      expectedStatus: 200,
    },
  ];
}

// ---------------------------------------------------------------------------
// Database Connection
// ---------------------------------------------------------------------------

async function resolveDbUrl(ctx: PluginContext, config: PluginConfig): Promise<string> {
  return ctx.secrets.resolve(config.databaseUrlRef);
}

let dbAvailable = false;

async function initDatabase(ctx: PluginContext, config: PluginConfig): Promise<void> {
  try {
    const dbUrl = await resolveDbUrl(ctx, config);
    ctx.logger.info("Connecting to BTC Trade Engine database");
    await createPool({ connectionString: dbUrl });
    const health = await dbHealthCheck();
    if (health.ok) {
      dbAvailable = true;
      ctx.logger.info("BTC Trade Engine database connected", {
        latencyMs: health.latencyMs,
      });
    } else {
      ctx.logger.warn("BTC Trade Engine database health check failed", {
        error: health.error,
      });
    }
  } catch (err) {
    ctx.logger.warn("BTC Trade Engine database unavailable — DB-backed checks disabled", {
      error: String(err),
    });
  }
}

// ---------------------------------------------------------------------------
// Exchange Health Probe
// ---------------------------------------------------------------------------

async function checkSingleExchange(
  ctx: PluginContext,
  exchange: ExchangeConfig
): Promise<ExchangeHealthResult> {
  const started = Date.now();
  try {
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      exchange.timeoutMs
    );
    const resp = await ctx.http.fetch(exchange.healthEndpoint, {
      signal: controller.signal,
      method: "GET",
    });
    clearTimeout(timeout);
    const latencyMs = Date.now() - started;

    const statusOk = resp.status === exchange.expectedStatus;
    let status: ExchangeHealthStatus;
    if (statusOk) {
      status = "healthy";
    } else if (resp.status === 429) {
      status = "degraded";
    } else if (resp.status >= 500) {
      status = "unhealthy";
    } else {
      status = "degraded";
    }

    let error: string | undefined;
    if (!statusOk) {
      error = `Unexpected HTTP ${resp.status}, expected ${exchange.expectedStatus}`;
    }

    return {
      exchange: exchange.name,
      status,
      latencyMs,
      statusCode: resp.status,
      error,
      endpoint: exchange.healthEndpoint,
      checkedAt: isoNow(),
    };
  } catch (err) {
    const classified = classifyExchangeError(err);
    return {
      exchange: exchange.name,
      status: classified.status,
      latencyMs: Date.now() - started,
      error: classified.message,
      endpoint: exchange.healthEndpoint,
      checkedAt: isoNow(),
    };
  }
}

async function checkExchangeHealth(
  ctx: PluginContext,
  config: PluginConfig
): Promise<ExchangeHealthSummary> {
  const exchanges = resolveExchanges(config);
  const results = await Promise.all(
    exchanges.map((ex) => checkSingleExchange(ctx, ex))
  );

  const healthyCount = results.filter(
    (r) => r.status === "healthy" || r.status === "degraded"
  ).length;
  const unhealthyCount = results.length - healthyCount;

  return {
    allHealthy: unhealthyCount === 0,
    healthyCount,
    unhealthyCount,
    totalCount: results.length,
    results,
  };
}

// ---------------------------------------------------------------------------
// Risk Limit Query
// ---------------------------------------------------------------------------

async function fetchRiskFromEndpoint(
  ctx: PluginContext,
  config: PluginConfig
): Promise<Partial<RiskSnapshot> | null> {
  if (!config.riskDataEndpoint) return null;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      config.riskDataEndpointTimeoutMs ?? DEFAULT_RISK_ENDPOINT_TIMEOUT_MS
    );
    const resp = await ctx.http.fetch(config.riskDataEndpoint, {
      signal: controller.signal,
      method: "GET",
      headers: { Accept: "application/json" },
    });
    clearTimeout(timeout);

    if (!resp.ok) {
      ctx.logger.warn("Risk data endpoint returned non-OK", {
        status: resp.status,
        endpoint: config.riskDataEndpoint,
      });
      return null;
    }

    const data = (await resp.json()) as Record<string, unknown>;
    return {
      heatRatio: typeof data.heatRatio === "number" ? data.heatRatio : undefined,
      dailyPnl: typeof data.dailyPnl === "number" ? data.dailyPnl : undefined,
      positionSizeBtc:
        typeof data.positionSizeBtc === "number"
          ? data.positionSizeBtc
          : undefined,
    };
  } catch (err) {
    ctx.logger.warn("Risk data endpoint fetch failed", {
      error: String(err),
      endpoint: config.riskDataEndpoint,
    });
    return null;
  }
}

function computeRiskBreaches(
  heatRatio: number,
  dailyPnl: number,
  positionSizeBtc: number,
  limits: RiskLimits
): RiskBreach[] {
  const breaches: RiskBreach[] = [];

  // Heat ratio checks with severity levels
  if (heatRatio > limits.maxHeatRatio) {
    breaches.push({
      metric: "heat_ratio",
      current: Math.round(heatRatio * 10000) / 100,
      limit: Math.round(limits.maxHeatRatio * 10000) / 100,
      unit: "%",
      severity: "CRITICAL",
      message: `Account heat ${(heatRatio * 100).toFixed(1)}% exceeds critical limit ${(limits.maxHeatRatio * 100).toFixed(1)}%`,
    });
  } else if (heatRatio > HEAT_WARNING_THRESHOLD) {
    breaches.push({
      metric: "heat_ratio",
      current: Math.round(heatRatio * 10000) / 100,
      limit: Math.round(HEAT_WARNING_THRESHOLD * 10000) / 100,
      unit: "%",
      severity: "WARNING",
      message: `Account heat ${(heatRatio * 100).toFixed(1)}% approaching limit (${(limits.maxHeatRatio * 100).toFixed(1)}% max)`,
    });
  }

  // Daily PnL checks with severity levels
  const absPnl = Math.abs(dailyPnl);
  if (absPnl > limits.maxDailyLossUsdt) {
    breaches.push({
      metric: "daily_pnl",
      current: Math.round(dailyPnl * 100) / 100,
      limit: limits.maxDailyLossUsdt,
      unit: "USDT",
      severity: "CRITICAL",
      message: `Daily loss ${absPnl.toFixed(2)} USDT exceeds limit ${limits.maxDailyLossUsdt} USDT`,
    });
  } else if (absPnl > limits.maxDailyLossUsdt * PNL_WARNING_RATIO) {
    breaches.push({
      metric: "daily_pnl",
      current: Math.round(dailyPnl * 100) / 100,
      limit: Math.round(limits.maxDailyLossUsdt * PNL_WARNING_RATIO),
      unit: "USDT",
      severity: "WARNING",
      message: `Daily loss ${absPnl.toFixed(2)} USDT approaching limit (${limits.maxDailyLossUsdt} USDT max)`,
    });
  }

  // Position size check
  if (positionSizeBtc > limits.maxPositionSizeBtc) {
    breaches.push({
      metric: "position_size",
      current: Math.round(positionSizeBtc * 100000) / 100000,
      limit: limits.maxPositionSizeBtc,
      unit: "BTC",
      severity: "CRITICAL",
      message: `Position size ${positionSizeBtc} BTC exceeds limit ${limits.maxPositionSizeBtc} BTC`,
    });
  }

  return breaches;
}

function overallSeverity(breaches: RiskBreach[]): "OK" | "WARNING" | "CRITICAL" {
  if (breaches.some((b) => b.severity === "CRITICAL")) return "CRITICAL";
  if (breaches.some((b) => b.severity === "WARNING")) return "WARNING";
  return "OK";
}

async function queryRiskLimits(
  ctx: PluginContext,
  config: PluginConfig,
  runId?: string
): Promise<RiskSnapshot> {
  const limits = config.riskLimits ?? DEFAULT_RISK_LIMITS;

  // 1. Try HTTP endpoint for live data
  const endpointData = await fetchRiskFromEndpoint(ctx, config);

  // 2. Read plugin state for persisted risk metrics
  const [lastPnl, lastPosition, lastHeat] = await Promise.all([
    ctx.state.get({ scopeKind: "company", stateKey: "daily-pnl" }),
    ctx.state.get({ scopeKind: "company", stateKey: "position-size" }),
    ctx.state.get({ scopeKind: "company", stateKey: "heat-ratio" }),
  ]);

  // 3. Fall back to config defaults if no data available
  const dailyPnl: number =
    typeof endpointData?.dailyPnl === "number"
      ? endpointData.dailyPnl
      : typeof lastPnl === "number"
        ? lastPnl
        : safeParse<number>(lastPnl, 0);

  const positionSizeBtc: number =
    typeof endpointData?.positionSizeBtc === "number"
      ? endpointData.positionSizeBtc
      : typeof lastPosition === "number"
        ? lastPosition
        : safeParse<number>(lastPosition, 0);

  let heatRatio: number;
  if (typeof endpointData?.heatRatio === "number") {
    heatRatio = endpointData.heatRatio;
  } else if (typeof lastHeat === "number") {
    heatRatio = lastHeat;
  } else if (limits.maxPositionSizeBtc > 0) {
    heatRatio = positionSizeBtc / limits.maxPositionSizeBtc;
  } else {
    heatRatio = safeParse<number>(lastHeat, 0);
  }

  // 4. Compute breaches and severity
  const breaches = computeRiskBreaches(
    heatRatio,
    dailyPnl,
    positionSizeBtc,
    limits
  );
  const severity = overallSeverity(breaches);

  const snapshot: RiskSnapshot = {
    heatRatio,
    dailyPnl,
    dailyLossLimit: limits.maxDailyLossUsdt,
    positionSizeBtc,
    maxPositionSizeBtc: limits.maxPositionSizeBtc,
    passed: !breaches.some((b) => b.severity === "CRITICAL"),
    breaches,
    severity,
    source: endpointData ? "http-endpoint" : lastPnl !== null ? "plugin-state" : "config-defaults",
    checkedAt: isoNow(),
  };

  // 5. Persist snapshot for cross-run tracking
  if (runId) {
    await ctx.state.set(
      { scopeKind: "run", scopeId: runId, stateKey: "risk-snapshot" },
      snapshot
    );
  }

  // 6. Update company-level risk state for next runs
  await ctx.state.set(
    { scopeKind: "company", stateKey: "daily-pnl" },
    dailyPnl
  );
  await ctx.state.set(
    { scopeKind: "company", stateKey: "position-size" },
    positionSizeBtc
  );
  await ctx.state.set(
    { scopeKind: "company", stateKey: "heat-ratio" },
    heatRatio
  );

  // 7. Store a historical snapshot for trend analysis
  const historyKey = `risk-history-${new Date().toISOString().slice(0, 10)}`;
  const existingHistory = await ctx.state.get({
    scopeKind: "company",
    stateKey: historyKey,
  });
  const history: Array<{ heatRatio: number; dailyPnl: number; checkedAt: string }> =
    safeParse(existingHistory, []);
  history.push({
    heatRatio,
    dailyPnl,
    checkedAt: isoNow(),
  });
  if (history.length > 288) history.shift();
  await ctx.state.set(
    { scopeKind: "company", stateKey: historyKey },
    history
  );

  return snapshot;
}

// ---------------------------------------------------------------------------
// Pre-Run Hooks
// ---------------------------------------------------------------------------

const BULLISH_KEYWORDS = [
  "BULLISH", "LONG", "BUY", "ABOVE", "OVER", "UP", "HIGHER",
  "BREAKOUT", "SUPPORT", "BOUNCE", "REVERSAL_UP", "UPTREND",
  "ACCUMULATION", "REACCUMULATION", "SPRING", "SOS", "LPS",
];

const BEARISH_KEYWORDS = [
  "BEARISH", "SHORT", "SELL", "BELOW", "UNDER", "DOWN", "LOWER",
  "BREAKDOWN", "RESISTANCE", "REJECTION", "REVERSAL_DOWN", "DOWNTREND",
  "DISTRIBUTION", "REDISTRIBUTION", "UPTHRUST", "SOW", "LPSY",
];

function parseJsonbField(value: unknown, fallback: unknown): unknown {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "string") {
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }
  if (typeof value === "object") return value;
  return fallback;
}

interface StrategyRow {
  strategy_id: string;
  name: string;
  version_id?: string | null;
  version_number?: number | null;
  version_timestamp?: string | null;
  validation_status: string | null;
  blocks: unknown;
  signals: unknown;
  risk_management?: unknown;
  strategy_type: string | null;
  entry_conditions?: unknown;
  exit_conditions: unknown;
  metrics?: unknown;
  created_at?: string;
  updated_at?: string;
}

function checkDirectionConsistency(
  blocks: unknown[],
  strategyType: string | null
): string[] {
  const errors: string[] = [];
  if (!strategyType || blocks.length === 0) return errors;

  const st = strategyType.toUpperCase();
  const expected = st === "BULLISH" ? BULLISH_KEYWORDS : BEARISH_KEYWORDS;
  const opposite = st === "BULLISH" ? BEARISH_KEYWORDS : BULLISH_KEYWORDS;

  let totalSignals = 0;
  let oppositeCount = 0;

  for (const block of blocks) {
    const signals = (block as Record<string, unknown>).signals;
    if (!Array.isArray(signals)) continue;
    for (const signal of signals) {
      totalSignals++;
      const sigName = ((signal as Record<string, unknown>).name as string ?? "").toUpperCase();
      if (opposite.some((kw) => sigName.includes(kw))) {
        oppositeCount++;
      }
    }
  }

  if (totalSignals > 0 && oppositeCount / totalSignals > 0.7) {
    errors.push(
      `Direction mismatch: ${Math.round((oppositeCount / totalSignals) * 100)}% of signals are opposite to strategy type "${strategyType}"`
    );
  }

  return errors;
}

async function validateStrategyFromDb(
  ctx: PluginContext,
  strategyId: string,
  level: "basic" | "strict"
): Promise<StrategyValidationResult> {
  const result: StrategyValidationResult = {
    strategyId,
    isValid: false,
    level,
    errors: [],
    warnings: [],
    checkedAt: isoNow(),
  };

  try {
    const rows = await ctx.db.query(
      `SELECT s.strategy_id, s.name,
              sv.validation_status,
              sv.blocks, sv.signals, sv.strategy_type,
              sv.exit_conditions
       FROM strategies s
       JOIN strategy_versions sv ON s.strategy_id = sv.strategy_id
       WHERE s.strategy_id = $1
       ORDER BY sv.version_number DESC
       LIMIT 1`,
      [strategyId]
    );

    if (!rows || rows.length === 0) {
      result.errors.push(`Strategy "${strategyId}" not found in database`);
      return result;
    }

    const row = rows[0] as unknown as StrategyRow;
    const blocks = parseJsonbField(row.blocks, []) as Record<string, unknown>[];
    const strategyType = row.strategy_type ?? null;

    // ── BASIC validation ──
    if (!row.name || row.name.trim() === "") {
      result.errors.push("Strategy must have a non-empty name");
    }

    if (!Array.isArray(blocks) || blocks.length === 0) {
      result.errors.push("Strategy must have at least one block");
    } else {
      for (const block of blocks) {
        const blockName = (block.name as string) ?? "unnamed";
        const sigs = block.signals;
        if (!Array.isArray(sigs) || sigs.length === 0) {
          result.errors.push(`Block "${blockName}" has no signals`);
        }
        const logic = block.logic as string | undefined;
        if (logic && !["AND", "OR"].includes(logic.toUpperCase())) {
          result.errors.push(
            `Block "${blockName}" has invalid logic: "${logic}" (expected AND or OR)`
          );
        }
      }
    }

    // ── STRICT validation ──
    if (level === "strict") {
      // Duplicate detection
      if (Array.isArray(blocks)) {
        const blockNames = blocks
          .map((b) => (b.name as string) ?? "")
          .filter(Boolean);
        const seen = new Set<string>();
        const dupBlocks: string[] = [];
        for (const name of blockNames) {
          if (seen.has(name)) dupBlocks.push(name);
          seen.add(name);
        }
        if (dupBlocks.length > 0) {
          result.errors.push(`Duplicate block names: ${[...new Set(dupBlocks)].join(", ")}`);
        }

        for (const block of blocks) {
          const sigs = block.signals as Record<string, unknown>[] | undefined;
          if (Array.isArray(sigs)) {
            const sigNames = sigs
              .map((s) => (s.name as string) ?? "")
              .filter(Boolean);
            const sigSeen = new Set<string>();
            const dupSigs: string[] = [];
            for (const name of sigNames) {
              if (sigSeen.has(name)) dupSigs.push(name);
              sigSeen.add(name);
            }
            if (dupSigs.length > 0) {
              result.errors.push(
                `Block "${block.name}" has duplicate signal names: ${[...new Set(dupSigs)].join(", ")}`
              );
            }
          }
        }
      }

      // Direction consistency
      if (Array.isArray(blocks)) {
        const dirErrors = checkDirectionConsistency(blocks, strategyType);
        result.errors.push(...dirErrors);
      }

      // Size warnings
      if (blocks.length > 15) {
        result.warnings.push(`Strategy has ${blocks.length} blocks (recommended max: 15)`);
      }
      for (const block of blocks) {
        const sigs = block.signals as unknown[] | undefined;
        if (Array.isArray(sigs) && sigs.length > 10) {
          result.warnings.push(
            `Block "${block.name}" has ${sigs.length} signals (recommended max: 10)`
          );
        }
      }
    }

    result.isValid = result.errors.length === 0;

    // Update validation_status in the database
    const newStatus = result.isValid ? "Pass" : "Fail";
    await ctx.db.execute(
      `UPDATE strategy_versions
       SET validation_status = $1, validation_timestamp = NOW()$
       WHERE strategy_id = $2
       ORDER BY version_number DESC
       LIMIT 1`,
      [newStatus, strategyId]
    );

    ctx.logger.info("Strategy validation complete", {
      strategyId,
      isValid: result.isValid,
      level,
      errorCount: result.errors.length,
      warningCount: result.warnings.length,
    });
  } catch (err) {
    result.errors.push(`Database query failed: ${String(err)}`);
    ctx.logger.error("Strategy validation DB query failed", {
      strategyId,
      error: String(err),
    });
  }

  return result;
}

// ---------------------------------------------------------------------------
// Pre-Run Hooks
// ---------------------------------------------------------------------------

async function writeAuditTrail(
  ctx: PluginContext,
  config: PluginConfig,
  runPayload: RunFinishedPayload
): Promise<void> {
  if (!config.auditEnabled) return;

  await ctx.activity.log({
    companyId: "",
    message: [
      `Agent run completed: agent=${runPayload.agentId}`,
      `run=${runPayload.runId}`,
      `duration=${runPayload.duration ?? "unknown"}ms`,
      runPayload.error ? `error=${runPayload.error}` : "status=ok",
    ].join(" "),
    entityType: "run",
    entityId: runPayload.runId,
    metadata: {
      outputLength: runPayload.output?.length ?? 0,
      hasError: !!runPayload.error,
      durationMs: runPayload.duration,
    },
  });
}

async function writeTradeExecutionLog(
  ctx: PluginContext,
  runId: string,
  agentId: string
): Promise<TradeRecord[]> {
  const rawTrades = await ctx.state.get({
    scopeKind: "run",
    scopeId: runId,
    stateKey: "trade-executions",
  });
  const trades: TradeRecord[] = safeParse(rawTrades, []);

  if (trades.length === 0) return trades;

  for (const trade of trades) {
    const slInfo = trade.stopLossPrice
      ? ` SL=${trade.stopLossPrice}`
      : "";
    const tpInfo = trade.takeProfitPrice
      ? ` TP=${trade.takeProfitPrice}`
      : "";
    const strategyInfo = trade.strategyId
      ? ` strategy=${trade.strategyId}`
      : "";

    await ctx.activity.log({
      companyId: "",
      message: [
        `Trade executed: ${trade.side} ${trade.quantity} ${trade.symbol}`,
        `@ ${trade.price}`,
        `tradeId=${trade.tradeId}`,
        `run=${runId}`,
        `agent=${agentId}`,
        `${slInfo}${tpInfo}${strategyInfo}`,
      ].join(" "),
      entityType: "run",
      entityId: runId,
      metadata: {
        tradeId: trade.tradeId,
        side: trade.side,
        symbol: trade.symbol,
        quantity: trade.quantity,
        price: trade.price,
        strategyId: trade.strategyId,
        stopLossPrice: trade.stopLossPrice,
        takeProfitPrice: trade.takeProfitPrice,
        timestamp: trade.timestamp,
      },
    });
  }

  return trades;
}

async function reconcilePositions(
  ctx: PluginContext,
  config: PluginConfig,
  runId?: string,
  agentId?: string
): Promise<PositionDivergence[]> {
  const lastState = await ctx.state.get({
    scopeKind: "company",
    stateKey: "position-state",
  });
  const expectedState: Record<string, number> =
    safeParse(lastState, {});

  const tradesRaw = await ctx.state.get({
    scopeKind: "run",
    scopeId: runId,
    stateKey: "trade-executions",
  });
  const trades: TradeRecord[] = safeParse(tradesRaw, []);

  const actualPositions: Record<string, number> = {};
  for (const t of trades) {
    const delta = t.side === "BUY" ? t.quantity : -t.quantity;
    actualPositions[t.symbol] =
      (actualPositions[t.symbol] ?? 0) + delta;
  }

  const divergences: PositionDivergence[] = [];
  for (const [symbol, qty] of Object.entries(actualPositions)) {
    const expected = expectedState[symbol] ?? 0;
    if (Math.abs(qty - expected) > 0.0001) {
      divergences.push({
        symbol,
        expectedQuantity: expected,
        actualQuantity: qty,
        severity:
          Math.abs(qty - expected) > 0.01 ? "CRITICAL" : "WARNING",
        message: `Position mismatch for ${symbol}: expected ${expected}, got ${qty}`,
      });
    }
  }

  if (divergences.length > 0 && runId) {
    ctx.logger.warn("Position divergences detected, creating follow-up issue", {
      runId,
      count: divergences.length,
    });

    try {
      const criticalDivs = divergences.filter(
        (d) => d.severity === "CRITICAL"
      );
      const severityLabel =
        criticalDivs.length > 0 ? "CRITICAL" : "WARNING";

      const divLines = divergences
        .map(
          (d) =>
            `- [${d.severity}] ${d.symbol}: expected ${d.expectedQuantity}, actual ${d.actualQuantity}`
        )
        .join("\n");

      await ctx.issues.create({
        title: `[${severityLabel}] Position reconciliation divergence detected`,
        description: [
          `## Position Reconciliation Alert`,
          ``,
          `**Severity:** ${severityLabel}`,
          `**Source Run:** \`${runId}\``,
          `**Agent:** \`${agentId ?? "unknown"}\``,
          `**Reconciled At:** ${isoNow()}`,
          ``,
          `### Divergences`,
          ``,
          divLines,
          ``,
          `Review the trade executions in this run and reconcile against exchange state.`,
        ].join("\n"),
        priority: criticalDivs.length > 0 ? "high" : "medium",
        status: "todo",
      });

      ctx.logger.info("Position reconciliation follow-up issue created", {
        runId,
        severity: severityLabel,
      });
    } catch (err) {
      ctx.logger.error("Failed to create position reconciliation issue", {
        runId,
        error: String(err),
      });
    }
  }

  await ctx.state.set(
    { scopeKind: "instance", stateKey: "last-reconciliation" },
    isoNow()
  );

  return divergences;
}

// ---------------------------------------------------------------------------
// Strategy Validation (DB-backed)
// ---------------------------------------------------------------------------

function validateStrategyRow(
  strategy: StrategyRow,
  level: "basic" | "strict",
  result: StrategyValidationResult
): void {
  result.isValid = true;

  if (!strategy.version_id) {
    result.warnings.push("Strategy has no versioned configuration");
    return;
  }

  if (strategy.validation_status === "Fail") {
    result.errors.push(
      `Strategy validation status is 'Fail' (last validated at ${strategy.version_timestamp ?? "unknown"})`
    );
    result.isValid = false;
    return;
  }

  if (strategy.validation_status === "Un-Validated") {
    result.warnings.push("Strategy has not been validated yet (status: Un-Validated)");
  }

  const blocks = Array.isArray(strategy.blocks) ? strategy.blocks : [];
  if (blocks.length === 0) {
    result.errors.push("Strategy has no building blocks defined");
    result.isValid = false;
    return;
  }

  const signals = strategy.signals as Record<string, unknown> | undefined;
  if (!signals || Object.keys(signals).length === 0) {
    result.warnings.push("Strategy has no signals configured");
  }

  if (level === "strict") {
    const riskMgmt = strategy.risk_management as Record<string, unknown> | undefined;
    if (!riskMgmt || Object.keys(riskMgmt).length === 0) {
      result.warnings.push("Strict mode: risk_management config is empty");
    }

    const entryConditions = Array.isArray(strategy.entry_conditions)
      ? strategy.entry_conditions
      : [];
    const exitConditions = Array.isArray(strategy.exit_conditions)
      ? strategy.exit_conditions
      : [];
    if (entryConditions.length === 0 && exitConditions.length === 0) {
      result.warnings.push("Strict mode: no entry or exit conditions defined");
    }

    const blockNames = blocks.map((b: Record<string, unknown>) => b.block_name).filter(Boolean);
    const signalBlockRefs = blocks.flatMap(
      (b: Record<string, unknown>) => (Array.isArray(b.signals) ? b.signals : [])
    );
    if (blockNames.length > 0 && signalBlockRefs.length > 0) {
      result.warnings.push(
        `Strict mode: verify signal dependency graph for blocks: ${blockNames.join(", ")}`
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Plugin Definition
// ---------------------------------------------------------------------------

const plugin = definePlugin({
  async setup(ctx) {
    ctx.logger.info("Trade Lifecycle Hooks plugin starting (v0.3.0)");

    // ── Database initialisation ─────────────────────────────────────

    const config = await getConfig(ctx);
    await initDatabase(ctx, config);

    // ── Pre-Run: agent.run.started ──────────────────────────────────

    ctx.events.on(
      "agent.run.started",
      async (event: PluginEvent<RunStartedPayload>) => {
        const payload = event.payload;
        const runId = payload.runId;

        ctx.logger.info("Pre-run hooks firing", { runId });

        try {
          const config = await getConfig(ctx);

          // 1. Exchange connectivity (multi-exchange)
          const exchangeHealth = await checkExchangeHealth(ctx, config);
          await ctx.state.set(
            { scopeKind: "run", scopeId: runId, stateKey: "exchange-health" },
            exchangeHealth
          );
          if (!exchangeHealth.allHealthy) {
            ctx.logger.warn("Exchange health checks found unhealthy exchanges", {
              runId,
              healthyCount: exchangeHealth.healthyCount,
              unhealthyCount: exchangeHealth.unhealthyCount,
              results: exchangeHealth.results
                .filter((r) => r.status !== "healthy")
                .map((r) => ({ exchange: r.exchange, status: r.status })),
            });
          } else {
            ctx.logger.info("All exchanges healthy", {
              runId,
              exchangeCount: exchangeHealth.totalCount,
            });
          }

          // 2. Risk limits (enhanced: state + endpoint + history)
          const riskSnapshot = await queryRiskLimits(ctx, config, runId);
          if (!riskSnapshot.passed) {
            ctx.logger.warn("Risk limit breaches detected", {
              runId,
              severity: riskSnapshot.severity,
              breaches: riskSnapshot.breaches,
            });
          } else if (riskSnapshot.severity === "WARNING") {
            ctx.logger.info("Risk limits with warnings", {
              runId,
              severity: riskSnapshot.severity,
              breaches: riskSnapshot.breaches,
            });
          } else {
            ctx.logger.info("Risk limits OK", { runId });
          }

          // 3. Strategy validation is deferred to agent tool invocation
          ctx.logger.info("Pre-run hooks complete", { runId });
        } catch (err) {
          ctx.logger.error("Pre-run hooks failed", {
            runId,
            error: String(err),
          });
        }
      }
    );

    // ── Post-Run: agent.run.finished ────────────────────────────────

    ctx.events.on(
      "agent.run.finished",
      async (event: PluginEvent<RunFinishedPayload>) => {
        const payload = event.payload;
        const runId = payload.runId;

        ctx.logger.info("Post-run hooks firing", { runId });

        try {
          const config = await getConfig(ctx);

          // 1. Write run-level audit entry
          await writeAuditTrail(ctx, config, payload);

          // 2. Write per-trade execution log entries to activity stream
          const trades = await writeTradeExecutionLog(
            ctx,
            runId,
            payload.agentId
          );
          ctx.logger.info("Audit trail and trade execution log written", {
            runId,
            tradeCount: trades.length,
          });

          // 3. Reconciled positions (creates follow-up issue if divergences)
          const divergences = await reconcilePositions(
            ctx,
            config,
            runId,
            payload.agentId
          );
          if (divergences.length > 0) {
            ctx.logger.warn("Position divergences detected", {
              runId,
              count: divergences.length,
            });
          }
        } catch (err) {
          ctx.logger.error("Post-run hooks failed", {
            runId,
            error: String(err),
          });
        }
      }
    );

    // ── agent.run.failed ────────────────────────────────────────────

    ctx.events.on(
      "agent.run.failed",
      async (event: PluginEvent<RunFinishedPayload>) => {
        const payload = event.payload;
        ctx.logger.error("Agent run failed", {
          runId: payload.runId,
          agentId: payload.agentId,
          error: payload.error ?? "unknown",
        });

        if (payload.error) {
          await ctx.activity.log({
            companyId: event.companyId,
            message: `Agent run FAILED: agent=${payload.agentId} run=${payload.runId} error="${payload.error}"`,
            entityType: "run",
            entityId: payload.runId,
            metadata: { error: payload.error, durationMs: payload.duration },
          });
        }
      }
    );

    // ── Agent Tools ─────────────────────────────────────────────────

    // trade_validate_strategy
    ctx.tools.register(
      "trade_validate_strategy",
      {
        displayName: "Validate Trading Strategy",
        description:
          "Validate a trading strategy against schema and signal dependency rules.",
        parametersSchema: {
          type: "object",
          required: ["strategyId"],
          properties: {
            strategyId: {
              type: "string",
              description: "UUID of the strategy to validate",
            },
          },
        },
      },
      async (
        params: unknown,
        runCtx: ToolRunContext
      ): Promise<ToolResult> => {
        const { strategyId } = params as { strategyId: string };
        const config = await getConfig(ctx);
        const result: StrategyValidationResult = {
          strategyId,
          isValid: false,
          level: config.preRunCheckLevel,
          errors: [],
          warnings: [],
          checkedAt: isoNow(),
        };

        try {
          if (!dbAvailable) {
            result.warnings.push(
              "BTC Trade Engine database unavailable — strategy validation skipped"
            );
            result.isValid = true;
          } else {
            const { strategy, error } = await queryStrategies(strategyId);

            if (error) {
              result.errors.push(`Database query failed: ${error}`);
            } else if (!strategy) {
              result.errors.push(`Strategy '${strategyId}' not found in database`);
            } else {
              validateStrategyRow(strategy, config.preRunCheckLevel, result);
            }
          }

          await ctx.state.set(
            {
              scopeKind: "run",
              scopeId: runCtx.runId,
              stateKey: "pre-run-validation",
            },
            result
          );
        } catch (err) {
          result.errors.push(String(err));
        }

        return {
          content:
            result.errors.length > 0
              ? `Strategy validation FAILED: ${result.errors.join("; ")}`
              : result.warnings.length > 0
                ? `Strategy validation passed with warnings: ${result.warnings.join("; ")}`
                : `Strategy '${strategyId}' validation passed.`,
          data: result,
        };
      }
    );

    // trade_check_exchange (enhanced: multi-exchange, filter by name, richer output)
    ctx.tools.register(
      "trade_check_exchange",
      {
        displayName: "Check Exchange Connectivity",
        description:
          "Verify that the configured exchange(s) are reachable and responding. Returns health status for all exchanges, or a specific one by name.",
        parametersSchema: {
          type: "object",
          properties: {
            exchange: {
              type: "string",
              description: "Exchange name to check (defaults to all configured exchanges)",
            },
          },
        },
      },
      async (
        params: unknown,
        runCtx: ToolRunContext
      ): Promise<ToolResult> => {
        const { exchange: filterExchange } = params as {
          exchange?: string;
        };

        // Check cached result first
        const cached = await ctx.state.get({
          scopeKind: "run",
          scopeId: runCtx.runId,
          stateKey: "exchange-health",
        });

        if (cached) {
          const summary = cached as ExchangeHealthSummary;

          if (filterExchange) {
            const target = summary.results.find(
              (r) => r.exchange === filterExchange
            );
            if (target) {
              const icon =
                target.status === "healthy"
                  ? "OK"
                  : target.status === "degraded"
                    ? "WARN"
                    : "FAIL";
              return {
                content: `[${icon}] Exchange ${target.exchange}: ${target.status} (${target.latencyMs}ms)${target.error ? ` — ${target.error}` : ""}`,
                data: target,
              };
            }
            return {
              content: `Exchange "${filterExchange}" not found in configuration. Available: ${summary.results.map((r) => r.exchange).join(", ")}`,
              data: null,
            };
          }

          const statusLine = summary.allHealthy
            ? "All exchanges healthy"
            : `${summary.unhealthyCount}/${summary.totalCount} exchanges unhealthy`;
          const details = summary.results
            .map(
              (r) =>
                `  ${r.status === "healthy" ? "OK" : r.status === "degraded" ? "WARN" : "FAIL"} ${r.exchange}: ${r.latencyMs}ms${r.error ? ` (${r.error})` : ""}`
            )
            .join("\n");
          return {
            content: `${statusLine}\n${details}`,
            data: summary,
          };
        }

        // Live check
        const config = await getConfig(ctx);
        const summary = await checkExchangeHealth(ctx, config);
        await ctx.state.set(
          { scopeKind: "run", scopeId: runCtx.runId, stateKey: "exchange-health" },
          summary
        );

        if (filterExchange) {
          const target = summary.results.find(
            (r) => r.exchange === filterExchange
          );
          if (target) {
            const icon =
              target.status === "healthy" ? "OK" : target.status === "degraded" ? "WARN" : "FAIL";
            return {
              content: `[${icon}] Exchange ${target.exchange}: ${target.status} (${target.latencyMs}ms)${target.error ? ` — ${target.error}` : ""}`,
              data: target,
            };
          }
          return {
            content: `Exchange "${filterExchange}" not found. Available: ${summary.results.map((r) => r.exchange).join(", ")}`,
            data: null,
          };
        }

        const statusLine = summary.allHealthy
          ? "All exchanges healthy"
          : `${summary.unhealthyCount}/${summary.totalCount} exchanges unhealthy`;
        const details = summary.results
          .map(
            (r) =>
              `  ${r.status === "healthy" ? "OK" : r.status === "degraded" ? "WARN" : "FAIL"} ${r.exchange}: ${r.latencyMs}ms${r.error ? ` (${r.error})` : ""}`
          )
          .join("\n");
        return {
          content: `${statusLine}\n${details}`,
          data: summary,
        };
      }
    );

    // trade_check_risk_limits (enhanced: severity levels, source tracking)
    ctx.tools.register(
      "trade_check_risk_limits",
      {
        displayName: "Check Risk Limits",
        description:
          "Check current risk metrics: account heat ratio, daily PnL, position size against configured limits. Identifies breaches by severity (WARNING / CRITICAL).",
        parametersSchema: {
          type: "object",
          properties: {},
        },
      },
      async (
        _params: unknown,
        runCtx: ToolRunContext
      ): Promise<ToolResult> => {
        const cached = await ctx.state.get({
          scopeKind: "run",
          scopeId: runCtx.runId,
          stateKey: "risk-snapshot",
        });
        if (cached) {
          const snapshot = cached as RiskSnapshot;
          let content: string;
          if (snapshot.severity === "OK") {
            content = `Risk limits OK [source: ${snapshot.source}]: heat=${(snapshot.heatRatio * 100).toFixed(1)}%, PnL=${snapshot.dailyPnl.toFixed(2)} USDT, position=${snapshot.positionSizeBtc} BTC`;
          } else {
            const breachLines = snapshot.breaches
              .map(
                (b) =>
                  `  [${b.severity}] ${b.message}`
              )
              .join("\n");
            content = `Risk limits ${snapshot.severity} [source: ${snapshot.source}]:\n${breachLines}`;
          }
          return { content, data: snapshot };
        }

        const config = await getConfig(ctx);
        const snapshot = await queryRiskLimits(ctx, config, runCtx.runId);
        let content: string;
        if (snapshot.severity === "OK") {
          content = `Risk limits OK [source: ${snapshot.source}]: heat=${(snapshot.heatRatio * 100).toFixed(1)}%, PnL=${snapshot.dailyPnl.toFixed(2)} USDT, position=${snapshot.positionSizeBtc} BTC`;
        } else {
          const breachLines = snapshot.breaches
            .map((b) => `  [${b.severity}] ${b.message}`)
            .join("\n");
          content = `Risk limits ${snapshot.severity} [source: ${snapshot.source}]:\n${breachLines}`;
        }
        return { content, data: snapshot };
      }
    );

    // trade_log_execution
    ctx.tools.register(
      "trade_log_execution",
      {
        displayName: "Log Trade Execution",
        description:
          "Record a trade execution in the audit trail.",
        parametersSchema: {
          type: "object",
          required: ["tradeId", "side", "quantity", "price", "symbol"],
          properties: {
            tradeId: { type: "string" },
            side: { type: "string", enum: ["BUY", "SELL"] },
            quantity: { type: "number" },
            price: { type: "number" },
            symbol: { type: "string" },
            strategyId: { type: "string" },
            stopLossPrice: { type: "number" },
            takeProfitPrice: { type: "number" },
          },
        },
      },
      async (
        params: unknown,
        runCtx: ToolRunContext
      ): Promise<ToolResult> => {
        const trade = params as Record<string, unknown>;
        const record: TradeRecord = {
          tradeId: trade.tradeId as string,
          side: trade.side as string,
          quantity: trade.quantity as number,
          price: trade.price as number,
          symbol: trade.symbol as string,
          strategyId: trade.strategyId as string | undefined,
          stopLossPrice: trade.stopLossPrice as number | undefined,
          takeProfitPrice: trade.takeProfitPrice as number | undefined,
          timestamp: isoNow(),
          runId: runCtx.runId,
          agentId: runCtx.agentId,
        };

        const existing = await ctx.state.get({
          scopeKind: "run",
          scopeId: runCtx.runId,
          stateKey: "trade-executions",
        });
        const trades: TradeRecord[] = safeParse(existing, []);
        trades.push(record);
        await ctx.state.set(
          {
            scopeKind: "run",
            scopeId: runCtx.runId,
            stateKey: "trade-executions",
          },
          trades
        );

        const posState = await ctx.state.get({
          scopeKind: "company",
          stateKey: "position-state",
        });
        const positions: Record<string, number> = safeParse(posState, {});
        const delta =
          record.side === "BUY" ? record.quantity : -record.quantity;
        positions[record.symbol] =
          (positions[record.symbol] ?? 0) + delta;
        await ctx.state.set(
          { scopeKind: "company", stateKey: "position-state" },
          positions
        );

        await ctx.activity.log({
          companyId: "",
          message: [
            `Trade executed: ${record.side} ${record.quantity} ${record.symbol}`,
            `@ ${record.price}`,
            `tradeId=${record.tradeId}`,
            `run=${record.runId}`,
            `agent=${record.agentId}`,
            record.stopLossPrice
              ? ` SL=${record.stopLossPrice}`
              : "",
            record.takeProfitPrice
              ? ` TP=${record.takeProfitPrice}`
              : "",
            record.strategyId
              ? ` strategy=${record.strategyId}`
              : "",
          ]
            .filter(Boolean)
            .join(" "),
          entityType: "run",
          entityId: record.runId,
          metadata: {
            tradeId: record.tradeId,
            side: record.side,
            symbol: record.symbol,
            quantity: record.quantity,
            price: record.price,
            strategyId: record.strategyId,
            stopLossPrice: record.stopLossPrice,
            takeProfitPrice: record.takeProfitPrice,
            timestamp: record.timestamp,
          },
        });

        ctx.logger.info("Trade logged", {
          tradeId: record.tradeId,
          side: record.side,
          symbol: record.symbol,
        });

        return {
          content: `Trade ${record.tradeId} logged and audited: ${record.side} ${record.quantity} ${record.symbol} @ ${record.price}`,
          data: record,
        };
      }
    );

    // trade_reconcile_positions
    ctx.tools.register(
      "trade_reconcile_positions",
      {
        displayName: "Reconcile Positions",
        description:
          "Compare tracked positions against expected state. Reports any divergences.",
        parametersSchema: {
          type: "object",
          properties: {
            symbol: {
              type: "string",
              description: "Trading symbol to reconcile (defaults to all)",
            },
          },
        },
      },
      async (
        _params: unknown,
        runCtx: ToolRunContext
      ): Promise<ToolResult> => {
        const config = await getConfig(ctx);
        const divergences = await reconcilePositions(
          ctx,
          config,
          runCtx.runId,
          runCtx.agentId
        );

        if (divergences.length === 0) {
          return {
            content: "All positions reconciled successfully. No divergences found.",
            data: { matched: true, divergences: [] },
          };
        }

        return {
          content: `${divergences.length} position divergence(s) found: ${divergences.map((d) => d.message).join("; ")}`,
          data: { matched: divergences.length === 0, divergences },
        };
      }
    );

    ctx.logger.info("Trade Lifecycle Hooks plugin ready (v0.3.0)");
  },

  async onHealth() {
    const checks: Record<string, string> = {};

    if (dbAvailable) {
      const dbHealth = await dbHealthCheck();
      checks.db = dbHealth.ok
        ? `connected (${dbHealth.latencyMs}ms)`
        : `error: ${dbHealth.error ?? "unknown"}`;
    } else {
      checks.db = "unavailable";
    }

    return {
      status: "ok",
      message: "Trade Lifecycle Hooks plugin v0.3.0 active",
      checks,
    };
  },

  async onShutdown() {
    await closePool();
  },
});

export default plugin;
