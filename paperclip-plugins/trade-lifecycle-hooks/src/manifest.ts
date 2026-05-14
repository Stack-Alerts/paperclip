// src/manifest.ts
// Plugin manifest for @frenocorp/trade-lifecycle-hooks
// See ADR-0005 for full architecture.

const manifest = {
  id: "paperclip-plugin-trade-lifecycle",
  apiVersion: 1 as const,
  version: "0.1.0",
  displayName: "Trade Lifecycle Hooks",
  author: "FrenoCorp",
  description:
    "Pre-run safety gates (strategy validation, exchange connectivity, risk limits) and post-run audit trail (trade execution logging, position reconciliation) for BTC Trade Engine agent workflows.",
  categories: ["automation"] as const,
  capabilities: [
    "events.subscribe",
    "agent.tools.register",
    "activity.log.write",
    "plugin.state.read",
    "plugin.state.write",
    "http.outbound",
    "secrets.read-ref",
    "issues.read",
    "issues.create",
    "issues.update",
    "issue.comments.create",
    "agents.read",
  ],
  entrypoints: {
    worker: "./dist/worker.js",
  },
  instanceConfigSchema: {
    type: "object",
    required: ["databaseUrlRef"],
    properties: {
      databaseUrlRef: {
        type: "string",
        title: "PostgreSQL Connection String (secret ref)",
        description:
          "PaperClip secret reference for the BTC Trade Engine PostgreSQL database. Used to query strategy state, positions, and risk limits.",
      },
      preRunCheckLevel: {
        type: "string",
        title: "Pre-Run Check Strictness",
        description:
          "basic = name+structure checks only. strict = full signal dependency graph analysis.",
        enum: ["basic", "strict"],
        default: "basic",
      },
      exchangeHealthEndpoint: {
        type: "string",
        title: "Exchange Health Endpoint",
        description: "HTTP endpoint to verify exchange connectivity.",
        default: "https://testnet.binancefuture.com/fapi/v1/ping",
      },
      exchangeHealthTimeoutMs: {
        type: "number",
        title: "Exchange Health Check Timeout (ms)",
        default: 5000,
      },
      riskLimits: {
        type: "object",
        title: "Risk Limits",
        properties: {
          maxHeatRatio: {
            type: "number",
            title: "Max Heat Ratio (0-1)",
            description: "Maximum account heat before pre-run check warns.",
            default: 0.8,
          },
          maxDailyLossUsdt: {
            type: "number",
            title: "Max Daily Loss (USDT)",
            default: 500,
          },
          maxPositionSizeBtc: {
            type: "number",
            title: "Max Position Size (BTC)",
            default: 1.0,
          },
        },
      },
      auditEnabled: {
        type: "boolean",
        title: "Enable Audit Trail",
        description: "Write activity.log entries for every trade action.",
        default: true,
      },
      reconciliationIntervalSeconds: {
        type: "number",
        title: "Reconciliation Interval (seconds)",
        description:
          "How often to perform position reconciliation (0 = only on run.finished).",
        default: 300,
      },
    },
  },
  tools: [
    {
      name: "trade_validate_strategy",
      displayName: "Validate Trading Strategy",
      description:
        "Validate a trading strategy against schema and signal dependency rules. Returns validation errors and warnings.",
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
    {
      name: "trade_check_exchange",
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
    {
      name: "trade_check_risk_limits",
      displayName: "Check Risk Limits",
      description:
        "Check current risk metrics: account heat ratio, daily PnL, position size against configured limits.",
      parametersSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "trade_log_execution",
      displayName: "Log Trade Execution",
      description:
        "Record a trade execution in the audit trail. Stores trade metadata for post-run reconciliation.",
      parametersSchema: {
        type: "object",
        required: ["tradeId", "side", "quantity", "price", "symbol"],
        properties: {
          tradeId: {
            type: "string",
            description: "Unique trade identifier",
          },
          side: {
            type: "string",
            enum: ["BUY", "SELL"],
          },
          quantity: {
            type: "number",
            description: "Trade quantity in BTC",
          },
          price: {
            type: "number",
            description: "Execution price in USDT",
          },
          symbol: {
            type: "string",
            description: "Trading symbol (e.g. BTCUSDT)",
          },
          strategyId: {
            type: "string",
            description: "Strategy that initiated this trade",
          },
          stopLossPrice: {
            type: "number",
            description: "Attached stop-loss price",
          },
          takeProfitPrice: {
            type: "number",
            description: "Attached take-profit price",
          },
        },
      },
    },
    {
      name: "trade_reconcile_positions",
      displayName: "Reconcile Positions",
      description:
        "Compare tracked positions against expected state. Reports any divergences found.",
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
  ],
};

export default manifest;
