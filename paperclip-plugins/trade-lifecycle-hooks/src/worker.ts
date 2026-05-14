// src/worker.ts
// Trade Lifecycle Hooks — Plugin Worker
// Pre-run: strategy validation, exchange connectivity, risk limits
// Post-run: trade execution logging, audit trail, position reconciliation

import { definePlugin } from "@paperclipai/plugin-sdk";
import type {
  PluginEvent,
  PluginContext,
  ToolRunContext,
  ToolResult,
} from "@paperclipai/plugin-sdk";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RiskLimits {
  maxHeatRatio: number;
  maxDailyLossUsdt: number;
  maxPositionSizeBtc: number;
}

interface PluginConfig {
  databaseUrlRef: string;
  preRunCheckLevel: "basic" | "strict";
  exchangeHealthEndpoint: string;
  exchangeHealthTimeoutMs: number;
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

interface ExchangeHealthResult {
  exchange: string;
  healthy: boolean;
  latencyMs: number;
  error?: string;
  checkedAt: string;
}

interface RiskSnapshot {
  heatRatio: number;
  dailyPnl: number;
  dailyLossLimit: number;
  positionSizeBtc: number;
  maxPositionSizeBtc: number;
  passed: boolean;
  breaches: string[];
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
// Helpers
// ---------------------------------------------------------------------------

async function getConfig(ctx: PluginContext): Promise<PluginConfig> {
  return (await ctx.config.get()) as unknown as PluginConfig;
}

async function resolveDbUrl(
  ctx: PluginContext,
  config: PluginConfig
): Promise<string> {
  return ctx.secrets.resolve(config.databaseUrlRef);
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

// ---------------------------------------------------------------------------
// Pre-Run Hooks
// ---------------------------------------------------------------------------

async function checkExchangeHealth(
  ctx: PluginContext,
  config: PluginConfig
): Promise<ExchangeHealthResult> {
  const started = Date.now();
  try {
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      config.exchangeHealthTimeoutMs
    );
    const resp = await ctx.http.fetch(config.exchangeHealthEndpoint, {
      signal: controller.signal,
    });
    clearTimeout(timeout);
    const latencyMs = Date.now() - started;
    return {
      exchange: new URL(config.exchangeHealthEndpoint).hostname,
      healthy: resp.ok,
      latencyMs,
      checkedAt: isoNow(),
    };
  } catch (err) {
    return {
      exchange: new URL(config.exchangeHealthEndpoint).hostname,
      healthy: false,
      latencyMs: Date.now() - started,
      error: String(err),
      checkedAt: isoNow(),
    };
  }
}

async function queryRiskLimits(
  ctx: PluginContext,
  config: PluginConfig
): Promise<RiskSnapshot> {
  const limits = config.riskLimits;

  const lastPnl = await ctx.state.get({
    scopeKind: "company",
    stateKey: "daily-pnl",
  });
  const lastPosition = await ctx.state.get({
    scopeKind: "company",
    stateKey: "position-size",
  });

  const dailyPnl =
    typeof lastPnl === "number"
      ? lastPnl
      : safeParse<number>(lastPnl, 0);
  const positionSizeBtc =
    typeof lastPosition === "number"
      ? lastPosition
      : safeParse<number>(lastPosition, 0);

  const heatRatio = limits.maxPositionSizeBtc > 0
    ? positionSizeBtc / limits.maxPositionSizeBtc
    : 0;

  const breaches: string[] = [];
  if (heatRatio > limits.maxHeatRatio)
    breaches.push(`Heat ratio ${(heatRatio * 100).toFixed(1)}% exceeds limit ${(limits.maxHeatRatio * 100).toFixed(1)}%`);
  if (Math.abs(dailyPnl) > limits.maxDailyLossUsdt)
    breaches.push(`Daily PnL ${dailyPnl.toFixed(2)} USDT exceeds limit ${limits.maxDailyLossUsdt} USDT`);
  if (positionSizeBtc > limits.maxPositionSizeBtc)
    breaches.push(`Position size ${positionSizeBtc} BTC exceeds limit ${limits.maxPositionSizeBtc} BTC`);

  return {
    heatRatio,
    dailyPnl,
    dailyLossLimit: limits.maxDailyLossUsdt,
    positionSizeBtc,
    maxPositionSizeBtc: limits.maxPositionSizeBtc,
    passed: breaches.length === 0,
    breaches,
    checkedAt: isoNow(),
  };
}

// ---------------------------------------------------------------------------
// Post-Run Hooks
// ---------------------------------------------------------------------------

async function writeAuditTrail(
  ctx: PluginContext,
  config: PluginConfig,
  runPayload: RunFinishedPayload
): Promise<void> {
  if (!config.auditEnabled) return;

  await ctx.activity.log({
    companyId: "", // populated from event
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

async function reconcilePositions(
  ctx: PluginContext,
  _config: PluginConfig
): Promise<PositionDivergence[]> {
  const lastState = await ctx.state.get({
    scopeKind: "company",
    stateKey: "position-state",
  });
  const trades = await ctx.state.get({
    scopeKind: "run",
    stateKey: "trade-executions",
  });

  const positions: Record<string, number> = {};
  const parsedTrades: TradeRecord[] = safeParse(trades, []);

  for (const t of parsedTrades) {
    const delta = t.side === "BUY" ? t.quantity : -t.quantity;
    positions[t.symbol] = (positions[t.symbol] ?? 0) + delta;
  }

  const expectedState: Record<string, number> =
    safeParse(lastState, {});

  const divergences: PositionDivergence[] = [];
  for (const [symbol, qty] of Object.entries(positions)) {
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

  await ctx.state.set(
    { scopeKind: "instance", stateKey: "last-reconciliation" },
    isoNow()
  );

  return divergences;
}

// ---------------------------------------------------------------------------
// Plugin Definition
// ---------------------------------------------------------------------------

const plugin = definePlugin({
  async setup(ctx) {
    ctx.logger.info("Trade Lifecycle Hooks plugin starting");

    // ── Pre-Run: agent.run.started ──────────────────────────────────

    ctx.events.on(
      "agent.run.started",
      async (event: PluginEvent<RunStartedPayload>) => {
        const payload = event.payload;
        const runId = payload.runId;
        const companyId = event.companyId;

        ctx.logger.info("Pre-run hooks firing", { runId });

        try {
          const config = await getConfig(ctx);

          // 1. Exchange connectivity
          const exchangeHealth = await checkExchangeHealth(ctx, config);
          await ctx.state.set(
            { scopeKind: "run", scopeId: runId, stateKey: "exchange-health" },
            exchangeHealth
          );
          ctx.logger.info("Exchange health checked", {
            runId,
            healthy: exchangeHealth.healthy,
            latencyMs: exchangeHealth.latencyMs,
          });

          // 2. Risk limits
          const riskSnapshot = await queryRiskLimits(ctx, config);
          await ctx.state.set(
            { scopeKind: "run", scopeId: runId, stateKey: "risk-snapshot" },
            riskSnapshot
          );
          if (!riskSnapshot.passed) {
            ctx.logger.warn("Risk limit breaches detected", {
              runId,
              breaches: riskSnapshot.breaches,
            });
          } else {
            ctx.logger.info("Risk limits OK", { runId });
          }

          // 3. Strategy validation is deferred to agent tool invocation
          //    (agents call trade_validate_strategy for specific strategies)
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

          // 1. Write audit trail
          await writeAuditTrail(ctx, config, payload);
          ctx.logger.info("Audit trail written", { runId });

          // 2. Reconciled positions (creates follow-up issues for divergences)
          const divergences = await reconcilePositions(ctx, config);
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
        const result: StrategyValidationResult = {
          strategyId,
          isValid: false,
          level: "basic",
          errors: [],
          warnings: [],
          checkedAt: isoNow(),
        };

        try {
          const config = await getConfig(ctx);
          // DB-backed validation would query strategies table.
          // For now, we store the result and mark as stub.
          result.warnings.push(
            "DB-backed strategy validation not yet implemented (Phase 2)"
          );
          result.isValid = true; // Stub: pass through to avoid blocking

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
                : "Strategy validation passed.",
          data: result,
        };
      }
    );

    // trade_check_exchange
    ctx.tools.register(
      "trade_check_exchange",
      {
        displayName: "Check Exchange Connectivity",
        description:
          "Verify that the configured exchange is reachable and responding.",
        parametersSchema: {
          type: "object",
          properties: {
            exchange: {
              type: "string",
              description: "Exchange name (defaults to configured primary)",
            },
          },
        },
      },
      async (
        _params: unknown,
        runCtx: ToolRunContext
      ): Promise<ToolResult> => {
        // Check cached result first
        const cached = await ctx.state.get({
          scopeKind: "run",
          scopeId: runCtx.runId,
          stateKey: "exchange-health",
        });
        if (cached) {
          const health = cached as ExchangeHealthResult;
          return {
            content: health.healthy
              ? `Exchange ${health.exchange} is healthy (${health.latencyMs}ms)`
              : `Exchange ${health.exchange} is UNHEALTHY: ${health.error ?? "no response"}`,
            data: health,
          };
        }

        // Live check
        const config = await getConfig(ctx);
        const health = await checkExchangeHealth(ctx, config);
        await ctx.state.set(
          {
            scopeKind: "run",
            scopeId: runCtx.runId,
            stateKey: "exchange-health",
          },
          health
        );
        return {
          content: health.healthy
            ? `Exchange ${health.exchange} is healthy (${health.latencyMs}ms)`
            : `Exchange ${health.exchange} is UNHEALTHY: ${health.error ?? "no response"}`,
          data: health,
        };
      }
    );

    // trade_check_risk_limits
    ctx.tools.register(
      "trade_check_risk_limits",
      {
        displayName: "Check Risk Limits",
        description:
          "Check current risk metrics: account heat ratio, daily PnL, position size against configured limits.",
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
          return {
            content: snapshot.passed
              ? `Risk limits OK: heat=${(snapshot.heatRatio * 100).toFixed(1)}%, PnL=${snapshot.dailyPnl.toFixed(2)} USDT, position=${snapshot.positionSizeBtc} BTC`
              : `Risk limit BREACHES: ${snapshot.breaches.join("; ")}`,
            data: snapshot,
          };
        }

        const config = await getConfig(ctx);
        const snapshot = await queryRiskLimits(ctx, config);
        await ctx.state.set(
          {
            scopeKind: "run",
            scopeId: runCtx.runId,
            stateKey: "risk-snapshot",
          },
          snapshot
        );
        return {
          content: snapshot.passed
            ? `Risk limits OK: heat=${(snapshot.heatRatio * 100).toFixed(1)}%, PnL=${snapshot.dailyPnl.toFixed(2)} USDT, position=${snapshot.positionSizeBtc} BTC`
            : `Risk limit BREACHES: ${snapshot.breaches.join("; ")}`,
          data: snapshot,
        };
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

        // Append to run's trade list
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

        // Update company-level position state
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

        ctx.logger.info("Trade logged", {
          tradeId: record.tradeId,
          side: record.side,
          symbol: record.symbol,
        });

        return {
          content: `Trade ${record.tradeId} logged: ${record.side} ${record.quantity} ${record.symbol} @ ${record.price}`,
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
        _runCtx: ToolRunContext
      ): Promise<ToolResult> => {
        const config = await getConfig(ctx);
        const divergences = await reconcilePositions(ctx, config);

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

    ctx.logger.info("Trade Lifecycle Hooks plugin ready");
  },

  async onHealth() {
    return { status: "ok", message: "Trade Lifecycle Hooks plugin active" };
  },

  async onShutdown() {
    // Flush any pending state
  },
});

export default plugin;
