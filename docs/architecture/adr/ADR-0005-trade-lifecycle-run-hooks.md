# ADR-0005: Trade Lifecycle Run Hooks — Plugin Architecture

**Issue:** [BTCAAAAA-26507](/BTCAAAAA/issues/BTCAAAAA-26507)
**Author:** Architect (73eaab54)
**Status:** In Review
**Date:** 2026-05-14
**Priority:** HIGH
**Parent:** [BTCAAAAA-26251](/BTCAAAAA/issues/BTCAAAAA-26251) — Investigate this plugins

---

## Context

BTC Trade Engine agents operate over multiple heartbeats within Paperclip. Every heartbeat that triggers a trading decision must be gated by safety checks, and every completed heartbeat must leave an immutable audit trail. Currently, there are no automated pre-run or post-run hooks — agents rely on ad-hoc checks embedded in their prompts, with no guarantee of execution.

The BTC Trade Engine infrastructure already provides:
- **Strategy validation** (`StrategyValidator` with BASIC/STANDARD/STRICT levels)
- **Exchange connectivity** (Binance REST + WebSocket clients with health checks)
- **Risk limits** (two-tier: `RiskEnforcer` in strategies + `RiskGate` in ITM execution)
- **Trade execution logging** (`TradeRegistry`, trade trace CSV)
- **Position reconciliation** (`PositionVerifier` with close-verify + periodic reconcile)
- **Audit trail** (`AuditWriter` to PostgreSQL + JSONL, `InstitutionalLogger`, `SignalEvaluatorLogger`)

However, these systems are invoked explicitly by agent code or human operators — there is no framework guarantee that they run on every heartbeat.

---

## Decision: Implement a PaperClip Plugin with Run Hook Architecture

We will implement **`@frenocorp/trade-lifecycle-hooks`**, a PaperClip plugin that hooks into the agent run lifecycle events to enforce safety gates and audit trail. The plugin uses PaperClip's native event system (`agent.run.started`, `agent.run.finished`, `agent.run.failed`) and provides tools for agents to call mid-run.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PaperClip Host                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Trade Lifecycle Hooks Plugin                  │  │
│  │                                                        │  │
│  │  agent.run.started ──► PreRunGate                      │  │
│  │    ├── StrategyValidator (DB-backed)                   │  │
│  │    ├── ExchangeProbe (HTTP + DB check)                 │  │
│  │    └── RiskLimitCheck (DB state query)                 │  │
│  │                                                        │  │
│  │  agent.run.finished ──► PostRunAudit                   │  │
│  │    ├── TradeExecutionLog (activity.log)                │  │
│  │    ├── PositionSnapshot (plugin state)                 │  │
│  │    └── AuditTrailWrite (activity + DB)                 │  │
│  │                                                        │  │
│  │  Agent Tools:                                           │  │
│  │    ├── trade_validate_strategy(strategy_id)            │  │
│  │    ├── trade_check_exchange(exchange)                  │  │
│  │    ├── trade_check_risk_limits()                       │  │
│  │    ├── trade_log_execution(trade_data)                 │  │
│  │    └── trade_reconcile_positions()                     │  │
│  │                                                        │  │
│  │  Data Sources:                                          │  │
│  │    ├── PostgreSQL DB (strategy state, risk config)     │  │
│  │    ├── Plugin State (run-level checkpoints)            │  │
│  │    └── Activity Log (immutable audit entries)          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Hook Specifications

### Pre-Run Hooks (fired on `agent.run.started`)

#### 1. Strategy Validation
- **Trigger:** Every `agent.run.started` event where the issuing issue is linked to a strategy
- **Query:** `SELECT id, name, status, blocks, signals, risk_management FROM strategies WHERE id = $1`
- **Validation:** BASIC level by default; STRICT when `config.preRunCheckLevel === "strict"`
- **Failure:** Logs a warning to `activity.log` and stores the validation result in `plugin.state` scoped to the run. Does NOT block execution (agents must check the validation result via tools).
- **Rationale:** Non-blocking validation avoids deadlock when strategy state is transitional. Agents are responsible for checking `trade_validate_strategy()` and aborting trades if the strategy is invalid.

#### 2. Exchange Connectivity Check
- **Trigger:** Every `agent.run.started` event
- **Check:** Verify the configured exchange health endpoint is reachable via `ctx.http.fetch()`
- **Config:** `config.exchanges` — array of `{ name, healthEndpoint, timeout }`
- **Failure:** Stores `exchange_health` in plugin state per run. Agents call `trade_check_exchange()` to get status.
- **Rationale:** Network conditions are transient; blocking execution on connectivity check would cause cascading failures during exchange maintenance windows.

#### 3. Risk Limit Check
- **Trigger:** Every `agent.run.started` event
- **Query:** Current position exposure, daily PnL, heat ratio from database or plugin state
- **Thresholds:** Configurable in plugin config (`maxHeatRatio`, `maxDailyLoss`, `maxPositionSizeBtc`)
- **Failure:** Stores risk snapshot in plugin state. Agents call `trade_check_risk_limits()`.
- **Rationale:** Risk limits are global state managed by the ITM Risk Gate. The plugin serves as an early-warning pre-check; actual trade gating happens in the ITM engine.

### Post-Run Hooks (fired on `agent.run.finished`)

#### 4. Trade Execution Logging
- **Trigger:** Every `agent.run.finished` event
- **Action:** Write an `activity.log` entry with run summary (agentId, runId, output length, duration)
- **Store:** Per-run trade metadata in `plugin.state` for later analysis
- **Rationale:** The Trade Registry in the optimizer database is the canonical trade record. The plugin provides a Paperclip-native audit view.

#### 5. Position Reconciliation
- **Trigger:** Every `agent.run.finished` event (deferred; async)
- **Action:** Compare last known position state against expected state
- **Divergence:** Creates a follow-up issue if position mismatch is detected
- **Rationale:** Position reconciliation is async because exchange API calls may be slow. The plugin flags anomalies for human attention.

---

## Data Contracts

### Plugin Configuration (`instanceConfigSchema`)

```json
{
  "databaseUrlRef": "string — Paperclip secret ref for PostgreSQL connection",
  "exchangeHealthEndpoint": "string — URL for exchange health check",
  "preRunCheckLevel": "basic | strict (default: basic)",
  "riskLimits": {
    "maxHeatRatio": "number (0-1, default: 0.8)",
    "maxDailyLoss": "number (USDT, default: 500)",
    "maxPositionSizeBtc": "number (default: 1.0)"
  },
  "auditEnabled": "boolean (default: true)",
  "reconciliationInterval": "number — seconds (default: 300)"
}
```

### Plugin State Keys

| Scope | Key | Value |
|-------|-----|-------|
| `run` | `pre-run-validation` | `{ strategyId, isValid, errors[], warnings[], checkedAt }` |
| `run` | `exchange-health` | `{ exchange, healthy, latencyMs, checkedAt }` |
| `run` | `risk-snapshot` | `{ heat, dailyPnl, dailyLossLimit, positionSize, maxPositionSize }` |
| `run` | `trade-executions` | `[{ tradeId, side, quantity, price, timestamp }]` |
| `instance` | `last-reconciliation` | ISO timestamp |
| `company` | `position-state` | `{ symbol, quantity, entryPrice, updatedAt }` |

### Agent Tools

| Tool Name | Parameters | Returns | Capability |
|-----------|-----------|---------|------------|
| `trade_validate_strategy` | `{ strategyId: string }` | `{ isValid, errors[], warnings[] }` | `agent.tools.register` |
| `trade_check_exchange` | `{ exchange?: string }` | `{ healthy, latencyMs, lastChecked }` | `agent.tools.register` |
| `trade_check_risk_limits` | `{}` | `{ passed, heatRatio, dailyPnl, breaches[] }` | `agent.tools.register` |
| `trade_log_execution` | `{ trade }` | `{ logged: true }` | `agent.tools.register` |
| `trade_reconcile_positions` | `{}` | `{ matched, divergences[] }` | `agent.tools.register` |

---

## Failure Modes and Resilience

| Failure | Behavior | Recovery |
|---------|----------|----------|
| DB unreachable | Log warning, skip DB-backed checks (strategy validation, risk query) | Auto-retry on next heartbeat |
| Exchange health HTTP timeout | Mark exchange as unhealthy, allow manual override | Agent re-checks via `trade_check_exchange` |
| Activity log write failure | Buffer to in-memory queue, flush on next write | Plugin worker restart clears queue |
| Plugin crash during audit | Host restarts worker; audit state recovered from plugin state | Run-scoped state is rebuilt from DB |

---

## Implementation Plan

### Phase 1: Plugin Scaffold (this issue)
- [x] ADR-0005 approved
- [ ] Manifest with capabilities, config schema, tools declaration
- [ ] Worker setup with event subscriptions
- [ ] Pre-run hook stubs (strategy validation, exchange check, risk check)
- [ ] Post-run hook stubs (trade logging, audit trail, position reconciliation)
- [ ] Agent tool registration

### Phase 2: BTC Trade Engine Integration (child issues)
- [ ] PostgreSQL connection and query layer (BTCAAAAA-26509)
- [ ] Strategy validation implementation (BTCAAAAA-26510)
- [ ] Exchange health probe implementation (BTCAAAAA-26511)
- [ ] Risk limit query implementation (BTCAAAAA-26512)

### Phase 3: Audit & Operations (child issues)
- [ ] Trade execution logging to activity stream (BTCAAAAA-26513)
- [ ] Position reconciliation workflow (BTCAAAAA-26514)
- [ ] Audit dashboard UI component (BTCAAAAA-26515)

---

## Alternatives Considered

### Option B: Agent Prompt Enforcement
Require all trading agents to include validation and audit steps in their AGENTS.md instructions.
- **Rejected:** Not enforceable — agents may skip steps, hallucinate checks, or fail silently. Requires maintenance across all agent prompts.

### Option C: External Cron Jobs
Run validation and audit via cron/scheduled GitHub Actions.
- **Rejected:** Not real-time, no integration with agent lifecycle. Separate failure domains.

---

## Consequences

### Positive
- Automated, framework-enforced safety gates on every trading heartbeat
- Immutable audit trail within Paperclip's activity log
- Agent tools provide standard, tested safety primitives
- Plugin state enables cross-run position tracking

### Negative
- Adds process overhead (~50-200ms for pre-run checks, depending on DB latency)
- One more plugin to maintain and monitor
- Requires PostgreSQL connectivity from Paperclip plugin sandbox

### Mitigations
- Pre-run checks are non-blocking by default — agents self-enforce via tool results
- Configurable check strictness per environment (testnet vs mainnet)
- Plugin health monitoring via `onHealth()` RPC method

---

## Related ADRs

- [ADR-0004](/BTCAAAAA/documents/ADR-0004-honcho-vs-hindsight-memory-plugin) — Memory Plugin Selection
- [ADR-0001](/BTCAAAAA/documents/ADR-0001-zero-trades-regression-audit) — Zero-Trades Regression Audit
