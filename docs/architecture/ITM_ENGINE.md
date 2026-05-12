# ITM — Intelligent Trade Manager Architecture

**Version:** 0.6.0
**Last updated:** 2026-05-12
**Owner:** DocWriter / CTO

---

## 1. Overview

The ITM is the live execution layer for the BTC Trade Engine. It owns all order submission, fill tracking, position management, and risk gate enforcement. It delegates execution to NautilusTrader but keeps the domain layer framework-agnostic for unit testability.

### 1.1 Module Map

```
src/itm/
  domain/        — Pure domain model (entities, events, state machines, config)
  data/          — Live data: Binance WS stream, bar builder, gap detection, freshness gate
  state/         — Dual-write checkpointing (Redis + Postgres), circuit breaker, recovery, shutdown
  orchestrator/  — Multi-strategy lifecycle, signal aggregation, capital allocation, performance monitoring
  risk/          — Pre-trade risk gate, position sizing, capital governor, emergency closeout
  engine/        — Execution engine, order factory, state machine, bracket manager, Binance REST/WS client
  dry_run/       — Testnet runner for 48-72h continuous validation
```

### 1.2 Data Flow

```
Signal (from Strategy Builder)
    │
    ▼
MultiStrategyOrchestrator (Section D)
    │  route signal → aggregate → produce Decision
    ▼
ExecutionEngine (Section G)
    │  RiskGate.approve() → OrderFactory → BinanceClient → OrderStateMachine
    ▼
BracketManager (Section G)
    │  on_entry_filled → place TP + SL brackets
    ▼
StateManager (Section C)
    │  dual-write checkpoint (Redis + Postgres)
    ▼
PerformanceMonitor (Section D)
    │  PnL tracking, drawdown alerts, auto-pause
```

---

## 2. Domain Layer (Section A)

**Location:** `src/itm/domain/`

Pure Python dataclasses with no NautilusTrader or I/O dependencies.

| File | Contents |
|---|---|
| `entities.py` | Value objects: `Instrument`, `Order`, `Position`, `Signal`, `Decision`, `CapitalState`. Enums: `OrderSide`, `OrderType`, `OrderStatus`, `PositionDirection`, `SignalDirection`, `DecisionAction`, `ContractType` |
| `events.py` | Domain events: `TradeOpened`, `TradeFilled`, `TradeClosed`, `TradeCancelled`, `SignalReceived`, `DecisionMade`, `RiskLimitBreached`, `CapitalStateChanged` |
| `state.py` | `TradeStateMachine` — validates all `OrderStatus` transitions with `InvalidStateTransition` exceptions |
| `config.py` | `ITMConfig` — Pydantic-style frozen dataclass with layered config (env defaults → YAML → env vars → runtime overrides). Supports `dev`, `test`, `prod` environments |
| `nt_mapping.py` | Bidirectional mappers between ITM domain types and NautilusTrader types |

### 2.1 Order State Machine

```
pending ──→ open ──→ partial ──→ closed
  │           │         │
  ├──→ cancelled  ←────┤
  └──→ error     ←─────┘
```

Terminal states: `closed`, `cancelled`, `error`

---

## 3. Data Layer (Section B)

**Location:** `src/itm/data/`

Real-time market data foundation. All downstream sections depend on gap-free, freshness-gated data.

| Component | Role |
|---|---|
| `BinanceWebSocketStream` | Binance BTCUSDT Perpetual Futures tick feed with auto-reconnect. States: `DISCONNECTED → CONNECTING → CONNECTED → RECONNECTING` |
| `RealtimeBarBuilder` | Assembles 1m / 15m OHLCV bars from tick stream. Handles partial bars, gaps, and clock alignment |
| `GapDetector` | Detects bar gaps from missed ticks. Triggers LakeAPI / REST historical backfill. Returns `BarGap` with start/end timestamps |
| `DataFreshnessGate` | Enforces <60s data freshness. Blocks downstream consumers when stale. Can raise `StaleDataError` |
| `NTDataAdapter` | Bridge implementing NautilusTrader's `Data` component interface. Converts ITM bars → `NTBarEvent`, ticks → `NTTickEvent` |

---

## 4. State Management (Section C)

**Location:** `src/itm/state/`

| Component | Role |
|---|---|
| `StateManager` | Dual-write checkpointing: Redis (hot) + PostgreSQL (cold). Configurable failure threshold and cooldown |
| `RedisStore` | In-memory state store with TTL expiry. Fast reads for real-time operations |
| `PGStore` | Persistent state store via SQLAlchemy/PostgreSQL. Source of truth for recovery |
| `CircuitBreakerState` | `CLOSED` (both stores) → `OPEN` (Redis failed, PG only) → `HALF_OPEN` (probing Redis after cooldown) |
| `ITMSystemState` | Schema for checkpoint payload: strategy states, positions, capital, timestamp |
| `Recovery` | Reads latest checkpoint on startup, replays in-flight orders, reconciles with exchange |
| `GracefulShutdownHandler` | SIGTERM/SIGINT handler. Writes final checkpoint before exit. Configurable callbacks |

### 4.1 Checkpoint Flow

```
checkpoint(state, source)
    │
    ├── RedisStore.set() ──→ success? ──→ CLOSED
    │                           │ fail
    │                           ▼
    │                       OPEN circuit
    │                           │
    └── PGStore.save() ──────→ both failed? → raise CheckpointError
```

---

## 5. Orchestrator (Section D)

**Location:** `src/itm/orchestrator/`

Central coordinator that wires strategy lifecycle, signal processing, and capital allocation.

| Component | Role |
|---|---|
| `MultiStrategyOrchestrator` | Top-level coordinator. Loads strategies, routes signals, guards entries. Max position: 1.0 BTC, min: 0.001 BTC, leverage = 1.0 |
| `SBExportImporter` | Parses Strategy Builder export documents (JSON/YAML/dict) into `StrategyConfig` |
| `StrategyRegistry` | Manages strategy lifecycle: `LOADING → ACTIVE → PAUSED → STOPPED`. Thread-safe registry |
| `SignalAggregator` | Aggregates signals from multiple strategies. Produces a single `Decision` per bar |
| `CapitalAllocator` | Enforces per-strategy capital ceilings and total pool limits |
| `PerformanceMonitor` | Tracks PnL, drawdown, Sharpe ratio per strategy. Auto-pauses strategies on drawdown breach |
| `OrchestratorConfig` | Frozen config: `total_capital`, `auto_activate_on_load` |

### 5.1 Pre-trade Guards (in order)

1. Quantity ≤ MAX_POSITION_SIZE (1.0 BTC)
2. Quantity ≥ MIN_POSITION_SIZE (0.001 BTC)
3. Strategy is ACTIVE
4. Capital available for the strategy
5. Daily loss limit not breached
6. Stop-loss attached on entry

---

## 6. Risk Module (Section F)

**Location:** `src/itm/risk/`

Synchronous pre-trade risk enforcement. Called before every order submission.

| Component | Role |
|---|---|
| `RiskGate` | `approve(OrderRequest) → RiskDecision`. Checks leverage cap, position limits, heat, daily loss, stop-loss enforcement |
| `CapitalGovernor` | Fixed-notional model with heat tracking (GREEN/YELLOW/RED). YELLOW = 50% quantity reduction, RED = reject |
| `PositionSizer` | Position sizing: fixed-fraction and Kelly Criterion. Adjusts quantity based on account equity and risk per trade |
| `EmergencyCloseout` | Drawdown/loss trigger monitoring. Can force-close all positions on breach |
| `CapitalMetrics` | Calculates Sharpe ratio, max drawdown, profit factor from trade history |
| `RiskDecision` | Result dataclass: `approved: bool`, `reason: str | None`, `adjusted_quantity: Decimal`, `stop_loss_price: Decimal` |

### 6.1 Risk Gate Checks (in order)

1. Leverage == 1.0 (hard-coded, no margin)
2. Quantity ≥ 0.001 BTC (MIN_POSITION_SIZE)
3. Quantity ≤ 1.0 BTC (MAX_POSITION_SIZE)
4. Strategy not in emergency closeout
5. Account heat level (RED → reject, YELLOW → 50% quantity)
6. Capital notional fits within per-trade and total limits
7. Daily loss limit not breached
8. Stop-loss at 2% from entry (mandatory, enforced)

---

## 7. Execution Engine (Section G)

**Location:** `src/itm/engine/`

Top-level execution orchestration: risk gate → order creation → exchange submission → bracket management.

| Component | Role |
|---|---|
| `ExecutionEngine` | `handle_decision(Decision)`. Pipeline: RiskGate.approve → OrderFactory → BinanceClient.place_order → OrderStateMachine → BracketManager |
| `OrderFactory` | Creates LIMIT/MARKET/TWAP/DCA `OrderSpec` objects. `clientOrderId` deduplication via `derive_client_order_id(strategy_id, signal_id, leg)` |
| `OrderStateMachine` | Per-order lifecycle tracker. Transitions: `SUBMITTED → ACKNOWLEDGED → FILLED / CANCELLED / REJECTED`. Timeout watchdog cancels orders past TTL |
| `BracketManager` | On entry fill, places TP + SL (optional trailing stop). OCO-style bracket management. Supports dynamic trail price updates |
| `BinanceClient` | HMAC-SHA256 REST client + WebSocket user-data stream. Handles order placement, cancellation, position queries |
| `RateLimiter` | 1200 weight/min budget with 429/418 backoff. Implements token bucket algorithm |
| `PositionVerifier` | Cross-checks ITM position state against exchange. Alerts on discrepancies |

### 7.1 Execution Flow

```
Decision (from Orchestrator)
    ↓
ExecutionEngine.handle_decision()
    ↓
1. RiskGate.approve() → rejected? log + return
    ↓ approved
2. OrderFactory.limit() → OrderSpec
    ↓
3. BinanceClient.place_order(spec)
    ↓ exchange_id
4. OrderStateMachine created → SUBMITTED → ACK
    ↓ fill via WS
5. BracketManager.on_entry_filled() → TP + SL placed
    ↓
6. Timeout watchdog cancels ACKNOWLEDGED orders past TTL
```

### 7.2 Order Types

| Type | Builder Method | Behavior |
|---|---|---|
| LIMIT | `OrderFactory.limit()` | Default. Single limit order at specified price |
| MARKET | `OrderFactory.market()` | Market order, uses best available price |
| TWAP | `ExecutionEngine` (via metadata) | Multiple LIMIT slices submitted immediately. Caller schedules intervals |
| DCA | `ExecutionEngine` (via metadata) | Ladder of LIMIT orders in sequence |

---

## 8. Dry Run (Section H)

**Location:** `src/itm/dry_run/`

Testnet validation runner for 48-72 hour continuous runs.

| Component | Role |
|---|---|
| `DryRunRunner` | Wires Orchestrator + ExecutionEngine + PositionVerifier. Hard-coded to Binance Futures TESTNET. Refuses to start with placeholder credentials |
| `DryRunMonitor` | Tracks success criteria: fill rate, error rate, position reconciliation, drawdown limits |
| `DryRunReport` | Generates final report with all metrics and pass/fail status |

**Usage:**
```bash
python scripts/run_testnet_dry_run.py [--min-hours 48] [--strategy-dir user_strategies]
```

---

## 9. Configuration

Layered config system in `src/itm/domain/config.py`:

| Layer | Priority | Source |
|---|---|---|
| Environment defaults | 1 (lowest) | `_ENV_DEFAULTS` dict |
| YAML file | 2 | `load_from_yaml()` |
| `base_config` dict | 3 | Passed to `load()` |
| Environment variables | 4 | `ITM_*` prefix |
| `overrides` dict | 5 (highest) | Passed to `load()` / `load_from_yaml()` |

Key env vars: `ITM_EXCHANGE`, `ITM_SYMBOL`, `ITM_CAPITAL_BASE`, `ITM_PAPER_TRADING`, `ITM_RISK_MAX_DRAWDOWN_PCT`, `ITM_RISK_HEAT_LIMIT`, `ITM_EXEC_ORDER_TIMEOUT_MS`

---

## 10. State Model

```
┌──────────────────┐
│   ITMSystemState │
├──────────────────┤
│ strategies: dict │────┐  ┌──────────────────┐
│ positions: list  │────┤  │  StrategyState   │
│ capital: Capital │    │  ├──────────────────┤
│ circuit_breaker  │    │  │ strategy_id      │
│ updated_at       │    │  │ status (ACTIVE…) │
└──────────────────┘    │  │ capital_alloc    │
                        │  │ positions: list  │
                        │  │ metrics          │
                        │  └──────────────────┘
                        │
                        │  ┌──────────────────┐
                        └──┤  PositionState   │
                           ├──────────────────┤
                           │ instrument       │
                           │ side             │
                           │ quantity         │
                           │ entry_price      │
                           │ current_pnl      │
                           └──────────────────┘
```

---

## 11. Related Documents

- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) — PostgreSQL schema and connection management
- [runbook-database-migration.md](../runbook-database-migration.md) — Alembic migration procedures
- [runbook-incident-response.md](../runbook-incident-response.md) — escalation matrix for trading system issues
- [src/itm/\_\_init\_\_.py](../../src/itm/__init__.py) — authoritative section breakdown
