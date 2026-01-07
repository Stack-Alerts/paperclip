# Intelligent Trade Manager (ITM) v1.0 Specification

**Document Type:** Conceptual Specification (ITM_Concept_Specification.md)  
**Document Version:** 1.0  
**Status:** Concept Specification – Foundation for Developer Technical Spec  
**Target Implementation:** NautilusTrader Actor Model with Python Integration (Binance BTCUSDT Perpetual Futures)

---

## 0. Purpose, Scope, and Design Principles

### 0.1 Purpose

This document specifies the conceptual, functional, and non-functional requirements of the Intelligent Trade Manager (ITM) v1.6. It integrates the production-grade components from v1.5 Framework with the ML-enhanced decision system from v1.4, creating a complete, resilient trading system.

The ITM will ultimately manage real capital in production. Therefore:

- All functional behavior MUST be precisely defined
- All safety, risk, and explainability mechanisms MUST be preserved or strengthened
- Production resilience features (state recovery, exchange verification, data management) MUST be fully integrated

### 0.2 System Scope

| Aspect | Specification |
|--------|---------------|
| **Instrument** | BTCUSDT Perpetual Futures on Binance Futures |
| **Primary Timeframe** | 15-minute candles (decision cycle) |
| **Analysis Granularity** | 1-minute bars for intra-candle precision |
| **Operating Mode** | Fully automated, ML-enhanced, explainable trading system with human-influence overlay |
| **Risk Model** | Fixed notional governance capital of 25,000 USDT (configurable) with compounding; exchange balance may differ |
| **State Management** | Full persistence with offline recovery capability  |
| **Data Management** | Continuous updates from Binance & LakeAPI with validation  |
| **Strategy Control** | Multi-strategy dynamic loading and orchestration  |

### 0.3 Core Objectives

1. Deliver institutional-grade, explainable, ML-enhanced decisions
2. Maximize risk-adjusted return (Sharpe ratio, profit factor, drawdown targets)
3. Maintain strict risk constraints, including account heat control, capital preservation thresholds, and explainability gating
4. Guarantee deterministic 15-minute decision cycles, with final decisions ready no later than T+14:55 in each 15-minute bar
5. Ensure production resilience with state recovery, exchange verification, and continuous data synchronization 
6. Support multi-strategy framework with dynamic loading and performance monitoring 

### 0.4 High-Level Design Principles

| Principle | Description |
|-----------|-------------|
| **Confluence over single signals** | Decisions must be based on multi-strategy and multi-source confluence, not any single indicator |
| **Explainability first** | No trade is executed without economic and SHAP-based justification |
| **Configuration over hard-coding** | All thresholds (confidence, risk per trade, account heat, timing margins) are configurable and versioned |
| **Fail-safe defaults** | On uncertainty, missing data, or degraded state, the system MUST default to non-trading / risk-reducing actions |
| **Resilience** | State checkpointing and recovery must allow sub-2-minute recovery for ≤24h gaps, ≤5-minute recovery for ≤7-day gaps |
| **Exchange Verification** | All position closes MUST be verified on exchange within 30 seconds before capital updates  |
| **Data Freshness** | All market data must be <60 seconds old for signals to be valid  |

---

## 1. Executive Summary (Conceptual)

### 1.1 System Composition

**ITM v1.6 = v1.5 Production Architecture + v1.4 ML/AI Enhancements**

#### Production Architecture (v1.5)

- Central repository (Redis) for signals, state, and context
- 5-dimension (now 6 including ensemble) decision framework
- Central Intelligence Engine for multi-strategy overrides and DCA
- Risk & capital management, account heat enforcement
- Execution engine (limit optimization, TWAP, TP/SL, DCA)
- State management & recovery; monitoring & performance targets

#### Production Components 

- **Data Management & Synchronization Layer**
- **State Recovery & Historical Tracking**
- **Multi-Strategy Framework with Dynamic Loading**
- **Exchange Position Verification System**
- **Offline Recovery Capability**
- **Complete Event History Storage**

#### ML/AI Enhancements 

- 4-layer ensemble (TCN, LSTM-Transformer, LightGBM meta-learner, anomaly detector)
- SHAP explainability gate with stale signal penalty and economic-sense checks
- Enhanced capital metrics (Sharpe, max drawdown, profit factor, etc.)
- Signal Quality Comparator; explicit switching/DCA logic
- Account Heat Manager

> **Note:** The ensemble contributes 40% weight to the final score in the Decision Engine, making it the single largest dimension.

### 1.2 Section Flow

Each of the following sections defines:

- Responsibilities & boundaries of that component
- Inputs, outputs, and data contracts
- Process flows (stepwise, decision or state transitions)
- Risk, failure, and edge case behavior

---

## 2. Architecture Overview

### 2.1 Logical Architecture

The ITM runs inside the NautilusTrader actor model. The architecture is composed of the following major subsystems:

#### Market Data & Strategy Layer

Multiple strategies, each producing structured signals (StrategySignal). Building blocks (technical, macro, custom) generating analysis metrics and context.

#### DATA MANAGEMENT & SYNCHRONIZATION LAYER 

- **Data Acquisition Manager:** Binance WebSocket stream + LakeAPI historical sync
- **Data Validation Engine:** OHLCV validation, gap detection, freshness monitoring
- **Time Series Database:** Local caching for fast access with SQLite persistence
- **Data Freshness Enforcement:** <60 seconds data age requirement

#### Central Repository (Redis + TSDB)

Stores active strategy signals, market context, position state, human influence, and capital state snapshots.

**Enhanced with Event History Storage:** Complete audit trail of all trading events

#### STATE RECOVERY & PERSISTENCE LAYER 

- **State Persistence Engine:** System state snapshots every 1-minute bar
- **Offline Recovery Manager:** Automatic recovery after outages with signal replay
- **Checkpoint Management:** Recovery markers and validation

#### STRATEGY MANAGEMENT LAYER 

- **Strategy Registry:** Dynamic loading from Python modules
- **Multi-Strategy Orchestrator:** Combine decisions from multiple strategies
- **Strategy Performance Monitor:** Real-time performance tracking per strategy

#### Intelligence & Decision Layer

- 4-layer ML ensemble subsystem
- Decision Scoring Engine (multi-dimension scoring)
- SHAP Explainability Gate
- Central Intelligence Engine (overrides, DCA, scaling, TP/SL adjustments)

#### EXCHANGE POSITION VERIFICATION LAYER 

- **Real-Time Position Monitor:** Continuous verification every 30-60 seconds
- **Post-Close Verification Engine:** CRITICAL - verify position closes on exchange
- **Position Reconciliation Handler:** Detect and resolve mismatches

#### Risk & Capital Layer

- Capital Management & Compounding
- Position Sizing & Dynamic Leverage
- Account Heat & Risk Enforcement
- Capital Metrics Tracker (Sharpe, drawdown, etc.)

#### Execution & State Layer

- Execution Engine (order construction, TWAP, DCA execution, TP/SL enforcement)
- Exchange Interface (Binance Futures)
- State Management & Recovery (checkpoints, replay)
- Monitoring & Performance Metrics

#### Human & External Context Layer

- Human Influence Module (analyst views via OpenRouter)
- External Market Context: Economic calendar, Polymarket, dominance flows, Fear & Greed, tech correlation

### 2.2 Complete 1-Minute Bar Processing Flow (Enhanced)

```
EVERY 1-MINUTE BAR CLOSE (TACTICAL OPTIMIZATION):
════════════════════════════════════════════════════════════════

PHASE A: Data Management & Validation (0-50ms)
└─ 1-min Bar Close Event (from Binance + NautilusTrader)
   ├─ Validate bar OHLCV (range, volume, logic)
   ├─ Check data freshness (<60s old requirement)
   ├─ Insert into time series database
   ├─ Update 15-min aggregate bar (if bar_number % 15 == 0)
   ├─ Check for data gaps vs LakeAPI (if >5min gap: trigger sync)
   └─ Emit: bar_ready_for_analysis

PHASE B: Strategy Event Distribution (50-150ms)
└─ For each ACTIVE strategy (from Strategy Registry):
   ├─ Call strategy.on_bar(bar)
   ├─ Get strategy's decision (BULLISH/BEARISH/NEUTRAL)
   ├─ Get strategy's confidence (0-1)
   ├─ Allocate capital % to this strategy
   ├─ Weight decision by confidence × allocation_pct
   └─ Collect into meta-decision array

PHASE C: Multi-Timeframe Signal Aggregation (150-250ms)
└─ Building Blocks analyze 1-min OHLCV
   ├─ 80 blocks emit individual signals
   ├─ MultiTimeframeSignalAggregator computes consensus
   ├─ 1-min consensus: BULLISH/BEARISH/NEUTRAL + confidence
   ├─ 15-min consensus: (if bar_number % 15 == 0)
   ├─ Cross-timeframe alignment check
   ├─ Signal freshness validation
   └─ Emit: signals_ready_for_ensemble

PHASE D: Ensemble Processing (250-400ms)
└─ TCN Model: Analyzes last 60 × 1-min bars
   ├─ LSTM-Transformer: Analyzes block signal history
   ├─ LightGBM Meta-Learner: Routes decisions
   ├─ Anomaly Detector: Checks market stress
   ├─ Stacking Ensemble: Combines with regime-adaptive weights
   ├─ Apply anomaly gate (if stress high: reduce confidence)
   └─ Emit: ensemble_decision_ready

PHASE E: Validation & Explainability (400-500ms)
└─ SHAP TreeExplainer: Calculate top 3 feature drivers
   ├─ Decision Gate: Validate against constraints
   │  ├─ Signal freshness OK?
   │  ├─ Position constraints OK?
   │  ├─ Confidence > 55%?
   │  ├─ Economic sense OK?
   │  └─ If any check fails: BLOCK decision, return HOLD
   │
   ├─ Stale data penalty: If driving signals > 8 bars old, reduce confidence 30%
   ├─ Create explanation: {top_reasons, checks_passed, model_contributions}
   └─ Emit: decision_validated

PHASE F: Capital Checking (500-600ms)
└─ CapitalAllocationGuard validation:
   │  ├─ Available capital ≥ required capital?
   │  ├─ Account heat < 95% after entry?
   │  ├─ Leverage appropriate for signal quality?
   │  └─ If capital insufficient: BLOCK decision, return HOLD
   │
   ├─ Risk guard validation:
   │  ├─ Account drawdown within limit?
   │  ├─ Concurrent loss positions within limit?
   │  └─ If limits breached: Trigger emergency closeout
   │
   └─ Emit: capital_validated

PHASE G: Strategy Switching Evaluation (600-700ms)
└─ For each open position:
   ├─ Compare current signal quality vs incoming signal quality
   ├─ If incoming ≥ 1.2x better AND current position losing → DCA or SWITCH
   ├─ If incoming ≥ 1.0x better AND current position winning → SCALE_CURRENT
   ├─ Otherwise proceed with standard optimization
   └─ Emit: strategy_switch_decision

PHASE H: Decision Window Check (700-750ms)
└─ Current minute in 15-min bar = ?
   ├─ If minute > 13: Window CLOSED → Can't execute
   ├─ If minute ≤ 13: Window OPEN → Can execute
   └─ Emit: decision_window_status

PHASE I: Position Optimization & Execution (750-900ms)
└─ IF decision_window_open AND NOT gated AND capital_available:
   ├─ Execute optimization:
   │  ├─ SCALE_IN: Add capital to existing position
   │  ├─ SCALE_OUT: Reduce existing position
   │  ├─ REVERSE: Close current + counter position
   │  ├─ SWITCH: Close current + enter new signal
   │  ├─ DCA_NEW: Keep current + add to incoming signal
   │  ├─ CLOSE: Exit entire position
   │  └─ HOLD: No action
   │
   ├─ Submit orders to NautilusTrader:
   │  ├─ Order type: LIMIT or MARKET (strategy-specific)
   │  ├─ Order quantity: Calculated position size
   │  ├─ Order side: BUY or SELL
   │  └─ Emit: order_submitted
   │
   └─ Emit: position_optimization_complete

PHASE J: State Persistence & Checkpoint (900-950ms)
└─ Save checkpoint to persistent storage:
   ├─ System state snapshot (current bar, signals, decisions)
   ├─ Position snapshots (all active positions, P&L, ages)
   ├─ Capital state (balance, allocated, reserved, buffer)
   ├─ Order queue (pending, filled, cancelled)
   ├─ Data freshness timestamps
   ├─ Strategy states (each active strategy)
   └─ Emit: checkpoint_saved

PHASE K: Event History Logging (950-1000ms)
└─ Log all events to JSONL audit trail:
   ├─ Signal events (all 67 blocks per timeframe)
   ├─ Order events (submissions, fills, cancellations)
   ├─ Position events (opens, updates, closes)
   ├─ Capital events (allocations, profits, losses)
   ├─ Ensemble decisions (all 4 models + weights)
   ├─ Data sync events (source, gaps, errors)
   ├─ Exchange verification events
   ├─ Strategy events (per-strategy decisions)
   └─ Total latency: 950-1000ms from bar close ✓

════════════════════════════════════════════════════════════════
```

### 2.3 15-Minute Decision Cycle Flow

Primary cycle (15-minute candle, T = 0..15):

#### T+0:00 – Candle open

- Start 1-minute bar ingestion; building blocks and strategies update per 1-minute close
- Data Management Layer validates and stores each 1-minute bar

#### T+12:00 – Early decision window

- All bars up to minute 11 are processed
- If signal convergence ≥ 85% and signal/ensemble quality ≥ 80%, early entries MAY be executed

#### T+13:00 – Mid decision window

- Update all indicators, 1-minute data, and external context
- If convergence ≥ 80%, standard entries can be executed

#### T+14:00 – Preliminary finalization

- Apply human influence
- Prepare decision candidates for final scoring; all required inputs must be present or flagged
- Multi-Strategy Orchestrator combines decisions from all active strategies

#### T+14:55 – Hard deadline

- Ensemble evaluation, 5D scoring, SHAP explainability gate, and Central Intelligence overrides completed
- Execution Engine places/cancels/adjusts orders
- State checkpoint persisted

#### T+15:00 – Next cycle

- New 15-minute candle opens; process repeats

#### Background tasks (ENHANCED with v1.5 components)

| Interval | Task |
|----------|------|
| Every 30s | Exchange verification (positions, orders, P&L) + Real-Time Position Monitoring |
| Every 1m | Signal ingestion and context update + Data freshness check |
| Every 5m | Human influence polling + LakeAPI synchronization |
| Every 1h | External context refresh (dominance, Fear & Greed, macro) + Strategy health check |

### 2.4 Section Flow

```
Market and strategy actors publish events →
Data Management Layer validates and stores data →
Central Repository aggregates and stores state →
Multi-Strategy Orchestrator combines decisions →
Ensemble & Decision Engine compute scores →
SHAP & risk gates approve/block decisions →
Exchange Verification Layer validates execution →
Execution & Capital engines act and update state →
State Recovery Layer persists checkpoints →
Monitoring & checkpointing complete the cycle
```

---

## 3. Core Framework Specifications

### 3.1 Trading Scope & Parameters

Conceptual baseline (configurable):

| Parameter | Specification |
|-----------|---------------|
| **Trading Pair** | BTCUSDT Perpetual (Binance Futures, USDT-margined) |
| **Primary Timeframe** | 15-minute candles (decision cycle) |
| **Analysis Granularity** | 1-minute bars (microstructure, early entries) (configurable: 1min,3min,5min) |
| **Governance Capital** | 25,000 USDT fixed notional (configurable; compounded with realized P&L |
| **Leverage Range** | 1x–15x dynamic (below Binance maxima of up to 125x for BTCUSDT) |
| **Max Concurrent Positions** | 5 active positions (configurable)(long/short/hedging combinations) |
| **Max Account Heat** | Configurable cap, default 95% deployed, 85% danger zone |
| **Slippage Budget** | 0.05% for limit fills target, 0.15% budget for market fallback |
| **Default Risk/Trade (concept)** | Recommended 0.5–2% of compounded capital, configurable |
| **Data Freshness** | <60 seconds old requirement for valid signals |
| **Max Leverage** | 3.0x (only in best conditions: 90%+ signal quality + trending regime) |
| **Signal Minimum** | 55% confidence required to enter any trade |

### 3.2 Decision Finalization Timeline (Formal Requirements)

The system MUST:

- Produce a single, final decision per 15-minute candle before T+14:55
- Explicitly log if any early or mid-cycle decisions were executed
- Degrade to WAIT / MONITOR if critical inputs (data, ensemble, SHAP, external context) are absent or invalid
- Verify data freshness (<60 seconds) before any decision
- Complete position close verification within 30 seconds before capital updates

> **Critical:** Timing requirements are hard SLAs; violation is a critical error and MUST trigger alarms and optional automatic trading halt.

### 3.3 Building Blocks & Strategies

#### Building block categories (no removal, only clarification)

**Technical analysis blocks:**
- Moving averages (SMA/EMA), MACD, oscillators (RSI, Stochastics, Williams %R)
- Bollinger Bands, ATR, OBV/VWAP, ADX, Supertrend, etc.

**Macro/contextual blocks:**
- BTC and USDT dominance flows
- Liquidity zones / order book clustering
- Volatility regimes
- BTC vs tech indices correlation

**Custom blocks:**
- Price action (patterns, breakouts, fakeouts)
- Support & resistance detection
- Liquidation level monitoring
- Order flow / MEV-like microstructure analysis

#### Strategy requirements (ENHANCED with Multi-Strategy Framework)

Each strategy MUST:

- Emit standardized StrategySignal objects (see Appendix) per 1-minute bar as appropriate
- Include TP/SL suggestions, target entry price, regime tags, and a human-readable reasoning field
- Reference contributing building blocks via stable block IDs
- Inherit from StrategyBase abstract class
- Implement required methods: `on_bar()`, `on_position_close()`
- Support dynamic loading from Python modules in `./strategies/` directory

#### Signal lifecycle

Signals are:

- Valid for a maximum of 15 minutes (configurable)
- Stored with decaying weights (e.g., 0–5m: 100%, 5–10m: 75%, 10–15m: 50%, >15m: 25%)
- Aggregated into an AggregatedSignal that exposes:
  - Primary signal type (e.g., ENTRY_LONG, ENTRY_SHORT, DCA, CLOSE, NEUTRAL)
  - Convergence strength and consensus confidence
  - Dominant market regime and signal age distribution
  - Must pass data freshness validation (<60 seconds old)

### 3.4 Section Flow

```
Raw data ingested via Data Management Layer (Binance WebSocket + LakeAPI) →
Data Validation Engine validates OHLCV and freshness →
Strategies and building blocks compute signals and metrics on each 1-minute close →
StrategySignals are published to central channels (e.g., Redis pub/sub) →
Central Repository stores signals with decay and TTL →
Aggregation computes convergence and consensus →
AggregatedSignal is passed to Ensemble & Decision Engine
```

---

## 4. Signal Processing & Data Aggregation

### 4.1 Central Repository Responsibilities

The Central Repository (Redis + RDBMS/Timescale) MUST:

#### Maintain:

- Per-strategy active signals (sorted by time)
- Current market context (trend, volatility, session, dominance, Fear & Greed)
- Position state (open positions, P&L, TP/SL status)
- Trade history by candle/time
- Human influence records
- Capital allocation state and metrics
- Complete event history storage for audit trail
- Strategy states and performance metrics

#### Enforce:

- Strict TTLs to avoid stale data driving decisions
- Consistent key schema and versioning
- Data freshness validation (<60 seconds)

### 4.2 Signal Ingestion & Aggregation Requirements

The Signal Ingestion Engine MUST:

- Accept StrategySignal objects from any registered strategy
- Apply age-based decay to confidence
- Limit in-memory history per strategy (e.g., last 100 signals)
- Compute AggregatedSignal as:
  - Dominant signal type by total weighted confidence
  - Convergence strength = normalized sum of confidences for dominant type
  - Consensus confidence and age distribution
- Persist AggregatedSignal to Redis for consumption by Decision Engine and Central Intelligence
- Validate signal data freshness (<60 seconds old)

### 4.3 Building Block Modularity

Each building block MUST:

**Expose:**
- A stable block ID and configuration

**Return:**
- Findings (block-specific analysis)
- Metrics usable by the decision engine (e.g., strength scores)
- Regime assessment (BULLISH/BEARISH/NEUTRAL/UNCERTAIN)
- Confidence contribution and narrative reasoning

**New blocks MUST:**
- Plug into a common interface (conceptually: analyze, get_config, validate_signal)
- Be activatable/deactivatable via configuration without code change

### 4.4 Section Flow

```
Raw data (OHLCV, order book, dominance, etc.) ingested via Data Management Layer →
Data Validation Engine validates data quality and freshness →
Building blocks generate metrics; strategies generate StrategySignals →
Signal Ingestion Engine stores and decays signals →
AggregatedSignal computed and published to downstream consumers →
Capital, position, and context snapshots kept current for decisions
```

---

## 5. 4-Layer Ensemble ML System

*(Existing content preserved, enhanced with:)*

### Integration with Multi-Strategy Framework

- Ensemble MUST consider strategy-level decisions from Multi-Strategy Orchestrator
- TCN model input includes strategy consensus metrics
- LightGBM meta-learner incorporates per-strategy performance metrics

---

## 6. SHAP Explainability Module

*(Existing content preserved, enhanced with:)*

### Enhanced with Strategy-Level Explainability

- SHAP explanations MUST include strategy-level contributions
- Feature importance should show which strategies drove the decision
- Economic sense checks MUST validate multi-strategy consensus

---

## 9. Risk Management & Compounding System

### 9.1 Capital Management

The Capital Management Engine MUST:

- Operate against a fixed governance capital (e.g., 25,000 USDT baseline), independent of exchange balance

#### Track:

- `starting_balance`, `current_balance`, `compounded_balance`, `allocated_capital`, `free_capital`, `risk_free_threshold`

#### Define available_capital as:

```
available_capital = compounded_balance – allocated_capital – risk_free_threshold
(floored at 0)
```

#### Multi-Strategy Capital Allocation

- Distribute capital across active strategies based on allocation percentages
- Track capital usage per strategy
- Enforce strategy-level capital limits

#### Compounding behavior

- Realized P&L is added to compounded balance after position close
- **CRITICAL:** Position close P&L only added after successful exchange verification
- Allocated capital for closed positions is freed

### 9.2 Dynamic Leverage

Dynamic leverage MUST depend on:

- Signal/ensemble quality (0–1)
- Market regime (higher in clean trends, lower in ranges; strongly reduced under volatility spikes)
- Number of concurrent positions (diversification)
- Strategy-level leverage limits (per-strategy `max_leverage` parameter)

Output MUST be clamped to 2–15x, i.e., materially conservative vs Binance maxima.

> **Note:** For multi-strategy framework, effective leverage per strategy is further limited to 2–5x

---

## 17. DATA MANAGEMENT & SYNCHRONIZATION LAYER 

### 17.1 Purpose

The Data Management Layer ensures continuous, validated market data flow from multiple sources with automatic recovery and gap detection.

### 17.2 Components & Responsibilities

#### 17.2.1 Data Acquisition Manager

**Responsibilities:**
- Manage real-time Binance WebSocket stream for 1-minute klines, order book, and trade data
- Synchronize historical data with LakeAPI for gap filling and recovery
- Automatic reconnection and stream health monitoring

**Requirements:**
- MUST maintain <60 seconds data freshness
- MUST detect and fill data gaps automatically
- MUST validate data from multiple sources (Binance vs LakeAPI)
- MUST buffer data for rate limiting and network resilience

#### 17.2.2 Data Validation Engine

**Responsibilities:**
- Validate OHLCV data for consistency and sanity
- Detect outliers, gaps, and data quality issues
- Compare data from multiple sources for discrepancies

**Validation Checks MUST Include:**
- OHLCV range logic (low ≤ high, close in [low, high])
- Maximum single-bar change percentage (configurable, default 20%)
- Volume spike detection (configurable threshold)
- Timestamp ordering and gap detection
- Source comparison (Binance vs LakeAPI discrepancies)

#### 17.2.3 Time Series Database (TSDB)

**Responsibilities:**
- Local caching of OHLCV data for fast O(1) access
- SQLite persistence for offline analysis
- In-memory indexing for recent data
- Automatic aggregation (1-min → 15-min bars)

**Requirements:**
- MUST store at least 365 days of 1-minute bars
- MUST support fast time-range queries
- MUST maintain data versioning and source attribution
- MUST support efficient aggregation for different timeframes

### 17.3 Data Flow

```
Binance WebSocket (Real-time)
    ↓
Data Validation
    ↓
TimeSeriesDB (Cache)
    ↓
Gap Detection Engine
    ↓ (if gaps detected)
LakeAPI Sync
    ↓
Source Comparison
    ↓
Validated Data → Central Repository
```

### 17.4 Failure Handling

| Failure Type | Response |
|--------------|----------|
| **WebSocket disconnect** | Auto-reconnect with exponential backoff |
| **Data gaps** | Automatic fetch from LakeAPI |
| **Validation failures** | Log errors, optionally discard invalid bars |
| **Persistent failures** | Degrade to historical-only mode with alerts |

---

## 18. STATE RECOVERY & PERSISTENCE LAYER 

### 18.1 Purpose

Ensure system resilience with complete state persistence, allowing recovery from outages with automatic signal replay and position reconciliation.

### 18.2 Components & Responsibilities

#### 18.2.1 State Persistence Engine

**Responsibilities:**
- Create system state snapshots every 1-minute bar
- Persist position states, capital allocations, and signal cache
- Maintain checkpoint markers for recovery points

**Checkpoint Contents MUST Include:**
- Active positions with full state (P&L, TP/SL, ages)
- Capital state (balance, allocated, free, buffer)
- Signal cache with timestamps and decay states
- Order queue with execution status
- Data freshness timestamps
- Strategy states and performance metrics

#### 18.2.2 Offline Recovery Manager

**Responsibilities:**
- Detect outages on startup by comparing last checkpoint timestamp
- Fetch missing bar data from LakeAPI with gap analysis
- Replay signals for offline period
- Reconcile position states with exchange

**Recovery Process:**
1. Detect outage (gap > 2 minutes from last checkpoint)
2. Fetch missing data from LakeAPI
3. Replay building block signals for offline period
4. Reconcile positions with exchange state
5. Validate capital consistency
6. Resume normal operation

#### 18.2.3 Event History Storage

**Responsibilities:**
- Complete audit trail of all trading events
- Searchable history with timestamps
- Support for post-trade analysis and regulatory compliance

**Events MUST Include:**
- All signals (67 blocks × 2 timeframes)
- All order events (creation, fill, cancellation)
- All position events (open, modify, close)
- All capital events (profit, loss, allocation)
- All ensemble decisions with reasoning
- Data sync events (source, gaps, errors)
- Exchange verification events

### 18.3 Recovery SLAs

| Gap Duration | Recovery Time | Verification Requirement |
|--------------|---------------|-------------------------|
| **≤ 24 hours** | < 2 minutes | All positions match exchange within 30 seconds |
| **≤ 7 days** | < 5 minutes | Capital calculations validated after recovery |

### 18.4 Section Flow

```
On Outage Detection:
    ↓
Fetch Missing Data (LakeAPI)
    ↓
Replay Signals (Offline Period)
    ↓
Reconcile with Exchange
    ↓
Validate Capital State
    ↓
Resume Normal Operation
```

---

## 19. STRATEGY MANAGEMENT LAYER 

### 19.1 Purpose

Enable dynamic loading, orchestration, and performance monitoring of multiple trading strategies within the ITM framework.

### 19.2 Components & Responsibilities

#### 19.2.1 Strategy Registry

**Responsibilities:**
- Manage directory structure for strategy Python modules (`./strategies/`)
- Define required interface for all strategies
- Store strategy metadata and configuration

**Strategy Interface MUST Include:**
- `on_bar(bar)` → decision_dict
- `on_position_close(position_data)` → None
- `get_allocated_capital(total_available)` → Decimal
- `update_metrics(trade_data)` → None

**Required attributes:**
- `strategy_id`, `name`, `capital_allocation_pct`, `max_leverage`, `max_position_loss_pct`

#### 19.2.2 Dynamic Strategy Loader

**Responsibilities:**
- Import strategy Python files at startup
- Validate class structure and required methods
- Initialize strategies with configured parameters
- Support hot-reload during development (optional)

**Loading Process:**
1. Scan `./strategies/` directory for `.py` files
2. Import module and find StrategyBase subclass
3. Validate required methods are implemented
4. Instantiate with configuration parameters
5. Register in runtime registry

#### 19.2.3 Multi-Strategy Orchestrator

**Responsibilities:**
- Route bar events to all active strategies
- Collect decisions from each strategy
- Weight decisions by confidence and capital allocation
- Combine into meta-decision for ensemble processing
- Enforce capital constraints across strategies
- Track performance per strategy

**Decision Combination Logic:**
- Weight each strategy's decision by: `confidence × (capital_allocation_pct / 100)`
- Meta-direction = weighted majority of BULLISH/BEARISH/NEUTRAL
- Meta-confidence = normalized sum of weighted confidences
- Position size = average of confident strategies (confidence > 0.60)

#### 19.2.4 Strategy Performance Monitor

**Responsibilities:**
- Track performance metrics per strategy
- Monitor against thresholds for auto-disable
- Provide real-time performance dashboard

**Metrics per Strategy MUST Include:**
- Win rate, Sharpe ratio, max drawdown
- Total trades, winning trades, losing trades
- Total P&L, P&L today
- Capital allocated and utilized
- Recent decision history

### 19.3 Strategy Configuration

Each strategy MUST have a configuration file (`strategy_id.json`) defining:

```json
{
  "strategy_id": "unique_identifier",
  "name": "Human-readable name",
  "capital_allocation_pct": 25.0,
  "max_leverage": 2.0,
  "max_position_loss_pct": 2.5,
  "enabled": true,
  "target_instruments": ["BTC/USDT"],
  "target_timeframe": "1m"
}
```

### 19.4 Section Flow

```
Strategy Directory Scan
    ↓
Dynamic Loading & Validation
    ↓
Initialize with Configuration
    ↓
Route Bar Events to Strategies
    ↓
Collect & Weight Decisions
    ↓
Combine into Meta-Decision
    ↓
Pass to Ensemble & Decision Engine
```

---

## 20. EXCHANGE POSITION VERIFICATION LAYER 

### 20.1 Purpose

Ensure all trading operations match exchange state through continuous monitoring and critical verification of position closes.

### 20.2 Components & Responsibilities

#### 20.2.1 Real-Time Position Monitor

**Responsibilities:**
- Query exchange every 30-60 seconds for open positions
- Compare internal position state vs exchange positions
- Detect and alert on mismatches immediately
- Verify position sizing and entry prices

**Mismatch Types Detected:**

| Type | Description | Severity |
|------|-------------|----------|
| **INTERNAL_ONLY** | Position in system but NOT on exchange | CRITICAL |
| **EXCHANGE_ONLY** | Position on exchange but NOT in system | WARNING |
| **SIZE_MISMATCH** | Quantity discrepancy between system and exchange | ERROR |
| **PRICE_MISMATCH** | Entry price discrepancy (tolerance: $1) | WARNING |

**Automatic Mismatch Recovery**
If Position on exchange but not internal, immediately create the exact position internally and start monitoring.
- If close required, immediately close position on exchange.
- If SL/TP update required, immediately update exchange TP / SL
- If Trailing stop required, immediately update exchange Trailing Stop.
- If pricing mismatch, immediately update internal monitoring to exchange entry price.
- If size mismatch, immediately update internal monitoring to exchange size.

If position internally and not on exchange
- Identify if position entry is still valid and within entry range
- Create position on exchange if capital allocation check allows.


#### 20.2.2 Post-Close Verification Engine (CRITICAL)

**Responsibilities:**
- Verify position closes are actually executed on exchange
- 30-second verification window with retries
- **CRITICAL:** Block capital updates until verification successful

**Verification Process (CRITICAL PATH):**

| Time | Action |
|------|--------|
| **T+0** | Record close in internal state |
| **T+5** | Wait for network latency |
| **T+5** | Query exchange for position |
| **T+5** | Verify position NO LONGER EXISTS |
| **T+15, T+25** | If still exists, retry 2 more times |
| **T+30** | If not verified by T+30, CRITICAL ALERT |

**CRITICAL RULES:**
- If verification fails: DO NOT update capital
- If verification fails: DO NOT reuse capital for new trades
- If verification fails: Lock position state until manual resolution (DISPLAY WARNING & INFORMATION)
- If verification fails: Immediate operator alert (CRITICAL LEVEL VIA ONSCREEN, EMAIL)

#### 20.2.3 Position Reconciliation Handler

**Responsibilities:**
- Investigate and resolve position mismatches
- Handle orphaned and ghost positions
- Verify stop-loss and take-profit orders
- Check for position size drift over time

### 20.3 Verification SLAs

| Process | Frequency/Duration |
|---------|-------------------|
| **Continuous Monitoring** | Every 30-60 seconds |
| **Post-Close Verification** | ≤30 seconds with 3 retry attempts |
| **Mismatch Alerting** | Immediate notification on detection |
| **Critical Failure Response** | Trading halt until resolution |

### 20.4 Section Flow

```
Continuous Monitoring (every 30-60s):
    Query Exchange → Compare States → Alert Mismatches

On Position Close:
    Record Internal Close → Wait 5s → Query Exchange
        ↓ (if position gone)
    Verification SUCCESS → Update Capital
        ↓ (if position still exists)
    Retry (up to 3x) → If still exists → CRITICAL ALERT
```

---

## 21. Enhanced Execution Engine with Verification

### 21.1 Responsibilities (Enhanced)

The Execution Engine MUST:

- Translate TradeDecision + PositionOverride into concrete order instructions
- Support:
  - Limit orders with configurable offsets from mid/last price
  - TWAP-style position building for DCA and large orders (TWAP orders adjustment when required within acceptable range for target entry fills) 
  - Partial TP ladder (TP1/TP2/TP3 with position percentages)
  - Hard stop losses and trailing stops
- Coordinate with Exchange Verification Layer for all position closes
- Implement retry logic with verification checks

### 21.2 Enhanced Failure Handling

#### On partial fills:
- Adjust remaining order sizes and risk metrics accordingly
- Ensure account heat reflects actual exposure
- Verify partial fill matches exchange state

#### On exchange errors or connectivity issues:
- Retry with backoff within the decision window
- If unresolved, log a critical event and switch to fail-safe mode
- Trigger position verification checks
- Lock affected positions until verification complete

#### CRITICAL: On position close:
- MUST wait for Post-Close Verification Engine confirmation
- MUST NOT update capital until verification successful
- MUST alert operator if verification fails (CRITICAL LEVEL VIA ONSCREEN, EMAIL)

### 21.3 Section Flow

```
Receive approved decisions and overrides →
Build order plan: limits/markets, price levels, TWAP schedule, TP/SL →
Send orders to Binance via authorized API →
Monitor fills and update internal position state →
NEW: Initiate position close verification when closing positions →
NEW: Reconcile state with Real-Time Position Monitor →
Reconcile state in periodic verification loops
```

---

## 22. Enhanced State Management & Recovery

### 22.1 Checkpointing Requirements (Enhanced)

The State Checkpoint Manager MUST persist at each 1-minute cycle:

- Active positions with full state (including TP/SL status)
- Capital state and metrics snapshot
- Recent signals (limited history window)
- Market context snapshot
- Model and config versions in effect
- Strategy states and performance metrics
- Exchange verification status
- Data freshness timestamps

### 22.2 Enhanced Recovery SLA

**For gaps ≤ 24 hours:**
- Recovery (state reconstruction + resumption) MUST complete in < 2 minutes
- MUST include data fetch from LakeAPI and signal replay

**For gaps ≤ 7 days:**
- Recovery MUST complete in < 5 minutes (requiring historical data reconstruction)
- MUST reconcile all positions with exchange state

**CRITICAL:** Recovery MUST verify capital consistency before resuming trading

### 22.3 Enhanced Section Flow

```
End of each decision cycle ⇒ create checkpoint with full system state

On restart or failure:
    Load most recent checkpoint →
    Detect outage duration and missing data →
    Fetch missing data from LakeAPI →
    Replay signals for offline period →
    Reconcile with current exchange state (positions, balances, open orders) →
    Validate capital consistency →
    Resume from next appropriate decision cycle
```

---

## 23. Enhanced Decision Framework & Scoring

### 23.1 Dimensions and Weights (Enhanced)

The Decision Scoring Engine MUST combine:

| Dimension | Weight |
|-----------|--------|
| **Ensemble output** | 40% |
| **Signal quality** | 20% |
| **Market regime** | 15% |
| **Event risk** | 10% |
| **Session timing** | 10% |
| **Position state** | 5% |
| **Multi-Strategy Consensus Score** | +10% (when multiple active strategies) |

#### Multi-Strategy Integration

- Meta-decision from Multi-Strategy Orchestrator contributes to final score
- Strategy consensus strength amplifies confidence
- Divergent strategy signals reduce confidence

### 23.2 Enhanced Decision Thresholds

| Final Score | Action |
|-------------|--------|
| **≥ 0.75** | EXECUTE_PRIMARY |
| **0.60 ≤ score < 0.75** | EXECUTE_MODIFIED |
| **0.50 ≤ score < 0.60** | MONITOR |
| **< 0.50** | WAIT |

#### Strategy-Level Gating

- If any active strategy has status = 'PAUSED' or performance below threshold ⇒ reduce score
- If strategy consensus < 0.60 ⇒ require higher overall score for execution

---

## 24. Enhanced Performance Targets & Monitoring

### 24.1 Performance SLAs (Enhanced)

The following SLAs MUST be enforced and monitored:

| Category | Metric | Target / Threshold |
|----------|--------|-------------------|
| **Recovery** | ≤24h gap | < 2 minutes |
| **Recovery** | ≤7d gap | < 5 minutes |
| **Decision Latency** | Per 15m cycle | Completed by T+14:55 |
| **Signal Ingestion** | Signal to repository latency | < 100 ms |
| **Order Execution** | Placement to exchange ack | < 200 ms (excluding exchange) |
| **Checkpointing** | State snapshot per cycle | < 500 ms |
| **Verification** | Exchange reconciliation loop | Every 30 seconds |
| **Data Freshness** | Latest bar age | < 60 seconds |
| **Post-Close Verify** | Position close verification | ≤ 30 seconds |
| **Strategy Load** | Strategy initialization | < 5 seconds at startup |

### 24.2 Enhanced Monitoring Metrics

The Performance Monitor MUST track system-level metrics, including but not limited to:

- Decision cycle durations and per-phase timings
- Signal volume, convergence averages, active strategies
- Order counts, fill rate, average slippage
- Position counts, fraction in profit, average duration
- Capital allocation and free capital
- Verification pass rate, discrepancies, error rate, recovery success
- Per-strategy performance metrics (win rate, Sharpe, drawdown)
- Data freshness and gap statistics
- Exchange verification success rate and mismatch counts
- Recovery time and success metrics

### 24.3 Section Flow

```
Instrument each phase of the decision and execution cycle →
Emit structured metrics events per cycle →
NEW: Monitor data freshness and trigger alerts if >60 seconds →
NEW: Track exchange verification performance and mismatches →
NEW: Monitor strategy performance and auto-pause underperformers →
Aggregate, store, and visualize metrics; raise alerts on SLA breaches
```

---

## 25. Enhanced Testing & Validation

### 25.1 Required Test Layers (Enhanced)

The system MUST undergo:

#### Unit tests for:
- Signal aggregation, ensemble evaluation, decision scoring, SHAP gating, capital and account heat logic, etc.
- Data validation engine tests
- Strategy loader and validation tests
- Exchange verification tests

#### Integration tests for:
- End-to-end cycle with simulated exchange for walkforward tests and paper trading from historic start point
- External context integration and failure modes
- Data synchronization and gap recovery tests
- Multi-strategy orchestration tests
- State recovery and offline replay tests
- Exchange verification workflow tests

#### Backtests & Simulation:
- Historical testing of all models and decision rules on BTCUSDT with multiple market regimes
- Walk-forward and robustness testing to avoid overfitting
- Strategy performance benchmarking
- Recovery scenario testing

#### Shadow trading:
- Run ITM live in "paper" / shadow mode before enabling real capital (support for NautilusTrader paper trading)
- Test with real exchange API but paper trading account
- Verify exchange verification system works

### 25.2 Enhanced Acceptance Criteria

- Performance metrics (Sharpe ratio, max drawdown, win rate, etc.) must meet pre-defined targets consistent with objectives
- Risk controls (account heat, SHAP gate, capital constraints) must always trigger as specified under synthetic stress tests
- Latency and recovery SLAs must be demonstrated in controlled environments
- Data freshness must remain <60 seconds in production
- Exchange verification must succeed >99.9% of the time
- State recovery must work for outages up to 7 days
- Multi-strategy framework must load and orchestrate ≥3 strategies concurrently

### 25.3 Section Flow

```
Define test plans and scenarios per component and integration →
Implement automated test suites and CI pipelines →
Conduct backtests, simulations, and shadow runs →
NEW: Test recovery scenarios (simulated outages) →
NEW: Test exchange verification failure modes →
NEW: Test multi-strategy conflict resolution →
Review performance and risk metrics vs criteria; iterate models and rules →
Approve for production only after satisfying all acceptance gates
```

---

## 26. Technology Stack (Enhanced)

### 26.1 Core Technologies

| Component | Technology |
|-----------|-----------|
| **Execution & Orchestration** | NautilusTrader actor model for low-latency, event-driven operation |
| **Language & Runtime** | Python (with strong typing discipline in developer spec); optional C++/Rust for latency-critical kernels |
| **Data Stores** | Redis for real-time state (signals, context, positions); PostgreSQL / TimescaleDB for configuration, history, and metrics; SQLite for Time Series Database (local caching); JSONL files for event history audit trail |
| **ML Frameworks** | TensorFlow/Keras, LightGBM, scikit-learn, SHAP |
| **Data Sources** | Binance WebSocket client for real-time data; LakeAPI client for historical data synchronization |

### 26.2 Non-Functional Requirements (Enhanced)

#### Latency:
- End-to-end decision < 350ms within each cycle
- Data validation < 50ms per bar
- State checkpointing < 500ms

#### Throughput:
- Must handle all 1-minute and 15-minute cycles for BTCUSDT with safety margin
- Must support ≥50 concurrent strategies

#### Recovery:
- ≤2 minute recovery for ≤24h outages
- ≤5 minute recovery for ≤7 day outages
- Automatic data gap detection and filling

#### Verification:
- Position close verification ≤30 seconds
- Continuous position monitoring every 30-60 seconds

#### Security:
- API keys stored in secure vault or encrypted config
- Principle of least privilege for exchange API permissions
- Robust logging and access controls
- Audit trail for all trading decisions and executions

---

## 27. Integration Architecture (Enhanced)

### 27.1 Actor Model Integration (Enhanced)

The ITM MUST integrate with NautilusTrader as:

**A distinct strategy/engine actor consuming:**
- Market data feed actors
- Strategy actors (building blocks, signals)
- External context actors
- Data management actors (Binance stream, LakeAPI sync)
- State recovery actors (checkpointing, offline recovery)
- Exchange verification actors (position monitoring)

**Downstream, the Execution actor interacts with:**
- Binance Futures API client
- Position/account actors for reconciliation
- Post-Close Verification Engine for position close confirmation

### 27.2 External Integrations (Enhanced)

- Economic calendar client(s)
- Polymarket or equivalent prediction markets
- Fear & Greed index provider
- Dominance & correlation data providers (Binance or other)
- Binance WebSocket API for real-time market data
- LakeAPI for historical data synchronization
- Exchange API for position verification

**All integrations MUST support:**
- Timeouts and retries
- Fallback or degraded behavior (e.g., disable event-risk features if data unavailable)
- Automatic reconnection and data gap recovery
- Validation and discrepancy detection

### 27.3 Enhanced Section Flow

```
Market and context actors stream data via Data Management Layer →
Data Validation Engine validates and stores data →
Multi-Strategy Orchestrator routes to active strategies →
ITM actor aggregates, decides, and instructs Execution actor →
Execution actor calls Binance and updates shared state →
Exchange Verification actors monitor and verify all operations →
State Recovery actors persist checkpoints →
Monitoring and logging actors consume metrics and events
```

---

## 28. Implementation Flows (Enhanced)

### 28.1 Complete Decision Cycle Flow (Enhanced with v1.5 Components)

#### Phases:

**1. Data Collection & Validation**
- Binance WebSocket delivers real-time bars
- Data Validation Engine checks OHLCV and freshness
- Time Series Database caches for fast access
- Gap detection triggers LakeAPI sync if needed

**2. Strategy Orchestration**
- Dynamic Strategy Loader provides active strategies
- Multi-Strategy Orchestrator routes bar to all strategies
- Collect and weight decisions per strategy
- Generate meta-decision for ensemble

**3. Signal Collection**
- Strategies and building blocks publish signals and metrics to the Central Repository throughout the 15-minute window

**4. Market Context Assembly**
- External context and dominance/sentiment are fetched and normalized

**5. Position Status Review**
- Active positions, P&L, TP/SL state, and account heat are read
- Real-Time Position Monitor verifies against exchange

**6. Decision Evaluation (T+14:00)**
- Ensemble, decision scoring, and preliminary action selection

**7. Central Intelligence Overrides**
- Evaluate DCA, scaling, TP/SL enhancement, or closure per position

**8. Explainability & Risk Gates**
- SHAP explainability, stale penalties, economic sense check
- Account heat and capital constraints re-validated

**9. Exchange Verification**
- For position closes: Initiate Post-Close Verification
- Wait for exchange confirmation before capital updates
- **CRITICAL:** Block if verification fails

**10. Execution (T+14:55)**
- Place/modify/cancel orders based on final decisions
- Record execution outcomes

**11. State Persistence & Logging**
- Create checkpoint with full system state
- Log decision, explanation, and execution for audit
- Store to Event History for complete audit trail

### 28.2 Strategy Signal Publishing Flow (Enhanced)

Conceptual requirements:

**Strategies MUST:**
- Compute indicators and logic specific to their design
- Emit standard StrategySignal objects with:
  - signal type, confidence, time, bar index
  - TP/SL ladder, trailing flags
  - entry price target
  - regime tags and reasoning
  - contributing building blocks
- Inherit from StrategyBase abstract class
- Implement required interface methods
- Support dynamic configuration via JSON files

**Signals MUST:**
- Be published to a shared bus/channels where the Signal Ingestion Engine consumes them
- Multi-Strategy Orchestrator MUST combine signals from multiple strategies

---

## 29. Appendix: Enhanced Conceptual Data Structures

### 29.1 StrategySignal (Enhanced)

Fields (non-exhaustive):

| Field | Type | Description |
|-------|------|-------------|
| `strategy_id` | String | Unique strategy identifier |
| `signal_type` | ENUM | ENTRY_LONG, ENTRY_SHORT, EXIT, DCA, CLOSE, NEUTRAL |
| `confidence` | Float | 0.0–1.0 |
| `timestamp`, `bar_index` | DateTime, Int | Timing information |
| `tp1_price`, `tp1_percent` | Float | Take profit level 1 |
| `tp2_price`, `tp2_percent` | Float | Take profit level 2 |
| `tp3_price`, `tp3_percent` | Float | Take profit level 3 |
| `trailing_stop_enabled` | Boolean | Whether trailing stop is active |
| `trailing_stop_percent` | Float | Trailing stop percentage |
| `stop_loss_price`, `stop_loss_percent` | Float | Stop loss settings |
| `entry_price_target` | Float | Target entry price |
| `market_regime` | ENUM | TRENDING_UP, TRENDING_DOWN, RANGE_BOUND, VOLATILE |
| `volatility_regime` | ENUM | LOW, MEDIUM, HIGH, EXTREME |
| `reasoning` | String | Human-readable explanation |
| `building_blocks_contrib` | List | List of contributing block IDs |
| `data_freshness_seconds` | Int | Age of data used for signal |
| `strategy_version` | String | Version of strategy generating signal |

### 29.2 AggregatedSignal (Enhanced)

| Field | Description |
|-------|-------------|
| `primary_signal_type` | Dominant signal type |
| `convergence_strength` | 0–1 measure of agreement |
| `consensus_confidence` | 0–1 weighted confidence |
| `contributing_strategies` | Count of strategies contributing |
| `signal_age_distribution` | Breakdown by age buckets (0–5m, 5–10m, 10–15m, >15m) |
| `dominant_market_regime` | Most common regime assessment |
| `timestamp` | Signal timestamp |
| `strategy_consensus_breakdown` | Per-strategy contributions |
| `data_freshness_status` | OK/WARNING/ERROR based on age |

### 29.3 Position (Enhanced)

| Field | Description |
|-------|-------------|
| Identity and linkage | `position_id`, `strategy_id` |
| `side` | LONG/SHORT |
| Entry data | `entry_price`, `size`, `time` |
| Current data | `current_price`, `P&L`, `P&L%` |
| Risk management | `TP/SL levels`, `triggers` |
| Trailing configuration | Trailing stop settings |
| `status` | OPEN/CLOSED |
| `verification_status` | VERIFIED/UNVERIFIED/PENDING |
| `exchange_position_id` | Corresponding exchange position ID |
| `last_verification_time` | When last verified with exchange |

### 29.4 TradeDecision (Enhanced)

| Field | Description |
|-------|-------------|
| `evaluation_time` | When decision was made |
| `primary_signal` | Primary signal driving decision |
| Dimension scores | Signal, regime, event, session, position, ensemble |
| `final_score` | Combined final score |
| `action` | EXECUTE_PRIMARY / EXECUTE_MODIFIED / MONITOR / WAIT |
| `confidence` | Confidence level |
| `explanation` | SHAP + economic reasoning |
| Optional fields | Position size, leverage suggestion, event override reasons, context notes |
| `strategy_contributions` | Which strategies contributed to decision |
| `data_freshness_warning` | Flag if data age affected decision |
| `verification_required` | Flag if action requires exchange verification |

### 29.5 NEW: StrategyState

| Field | Description |
|-------|-------------|
| `strategy_id` | Unique identifier |
| `name` | Human-readable name |
| `status` | ACTIVE/PAUSED/DISABLED/BACKTEST |
| `capital_allocation_pct` | Percentage of total capital |
| `allocated_capital` | Actual capital allocated |
| `performance_metrics` | Win rate, Sharpe, drawdown, etc. |
| `recent_decisions` | Last N decisions with outcomes |
| `configuration` | Strategy-specific parameters |
| `last_updated` | Timestamp of last state update |

### 29.6 NEW: VerificationRecord

| Field | Description |
|-------|-------------|
| `position_id` | Position being verified |
| `request_id` | Unique verification request ID |
| `verification_type` | POST_CLOSE/CONTINUOUS/RECONCILIATION |
| `status` | PENDING/VERIFIED/UNVERIFIED/ERROR |
| `attempts` | Number of verification attempts |
| `start_time` | When verification started |
| `end_time` | When verification completed |
| `result` | Verification result details |
| `alert_sent` | Whether alert was sent for failure |

### 29.7 NEW: DataValidationRecord

| Field | Description |
|-------|-------------|
| `bar_timestamp` | Timestamp of validated bar |
| `validation_time` | When validation occurred |
| `valid` | True/False |
| `errors` | List of validation errors |
| `warnings` | List of validation warnings |
| `anomaly_score` | 0-1 anomaly score |
| `data_source` | BINANCE/LAKEAPI/AGGREGATED |
| `freshness_seconds` | Age of data at validation |

### 29.8 PositionOverride, StateCheckpoint, CycleResult

**PositionOverride:**
Fields describing override type (DCA, CLOSE, ENHANCE, TIGHTEN, HOLD), TP/SL adjustments, DCA sizing, trailing configuration, reasoning and timestamps.

**StateCheckpoint:**
Snapshot of positions, capital, recent signals, context, strategy states, verification status, and data freshness at a given time.

**CycleResult:**
Execution summary of a 15-minute cycle (status, decisions, overrides, executions, checkpoint ID, duration, errors, verification outcomes).

---

## Document Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | - | Initial Draft (this document) |


---

**End of Document**
