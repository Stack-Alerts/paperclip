# Intelligent Trade Manager (ITM) Framework v1.5

**Comprehensive Technical Specification for NautilusTrader-Based BTC/USDT Trading System**

**Document Version:** 1.5  
**Last Updated:** January 7, 2026  
**Status:** Production Ready  
**Target Implementation:** NautilusTrader Actor Model with Python Integration

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Core Framework Specifications](#core-framework-specifications)
4. [Signal Processing & Data Aggregation](#signal-processing--data-aggregation)
5. [Central Intelligence Engine](#central-intelligence-engine)
6. [External Market Context Integration](#external-market-context-integration)
7. [Risk Management & Compounding System](#risk-management--compounding-system)
8. [Execution Optimization](#execution-optimization)
9. [State Management & Recovery](#state-management--recovery)
10. [Decision Framework & Scoring](#decision-framework--scoring)
11. [Technology Stack](#technology-stack)
12. [Implementation Examples](#implementation-examples)
13. [Performance Targets & Monitoring](#performance-targets--monitoring)
14. [Appendix: Data Structures](#appendix-data-structures)

---

## Executive Summary

The Intelligent Trade Manager (ITM) v1.5 is a sophisticated, multi-layered trading system built on the NautilusTrader framework for BTC/USDT pair trading on 15-minute candles. The system integrates:

- **Multi-strategy consensus engine** with dynamic risk adjustment
- **Human influence module** with OpenRouter AI processing for analyst inputs
- **External market context** (economic calendar, Polymarket predictions, dominance metrics, Fear & Greed Index)
- **Advanced state management** with sub-2-minute recovery for up to 24-hour gaps
- **Institutional-grade trade management** with DCA, multi-position monitoring, and intelligent scaling

**Core Objective:** Maximize risk/reward, minimize losses, generate sustained profits through confluence-based decision making finalized every 14:55 seconds of each 15-minute candle.

---

## Architecture Overview

### System Block Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      NAUTILUS TRADER ACTOR MODEL                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  MARKET DATA FEED    │  │  STRATEGY SIGNALS    │  │  BUILDING BLOCKS     │
│  (15min candles)     │  │  (Strategy 1..N)     │  │  (Technical, Macro)  │
│  (1min bar closes)   │  │  (TP1/TP2/TP3/SL)   │  │  (Custom Analysis)   │
└──────────────┬───────┘  └──────────┬───────────┘  └──────────┬───────────┘
               │                     │                         │
               └─────────────────────┴─────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │  CENTRAL REPOSITORY (Redis)    │
                    │  - Signal Aggregation           │
                    │  - Event Bus                    │
                    │  - Context Store                │
                    └────────────────┬────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│ HUMAN INFLUENCE      │   │ EXTERNAL MARKET      │   │ INTELLIGENT TRADE    │
│ MODULE               │   │ CONTEXT MODULE       │   │ MANAGER ENGINE       │
│ (OpenRouter API)     │   │ (Economic Calendar,  │   │ (Multi-Factor        │
│ (Chart Analysis)     │   │  Polymarket, Domi,  │   │  Decision Scoring)   │
│                      │   │  Fear & Greed, etc) │   │                      │
└──────────┬───────────┘   └──────────┬───────────┘   └──────────┬───────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      │
                    ┌─────────────────▼─────────────────┐
                    │  DECISION ENGINE                  │
                    │  (5-Dimension Scoring)            │
                    │  - Signal Quality                 │
                    │  - Market Regime                  │
                    │  - Event Risk                     │
                    │  - Session Timing                 │
                    │  - Position State                 │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────▼─────────────────┐
                    │  RISK MANAGEMENT ENGINE           │
                    │  - Capital Allocation             │
                    │  - Dynamic Leverage               │
                    │  - DCA Management                 │
                    │  - Compounding                    │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────▼─────────────────┐
                    │  EXECUTION ENGINE                 │
                    │  - Limit Order Optimization       │
                    │  - TWAP Position Building         │
                    │  - TP/SL Override Application     │
                    │  - DCA Execution                  │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────▼─────────────────┐
                    │  EXCHANGE INTERFACE               │
                    │  (Binance Futures API)            │
                    │  - Order Placement                │
                    │  - Position Management            │
                    │  - Fill Verification              │
                    └─────────────────┬─────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
   ┌─────────────┐        ┌──────────────────────┐      ┌────────────────────┐
   │  PostgreSQL │        │  TimescaleDB         │      │  Redis Cache       │
   │  (Config)   │        │  (Time-series Data)  │      │  (Real-time State) │
   │  (Metadata) │        │  (90-day/2-year ret) │      │  (Signal Cache)    │
   └─────────────┘        └──────────────────────┘      └────────────────────┘
```

### Component Interaction Flow

```
TIMING CYCLE: Every 15 Minutes
├── T+0:00 - 15min candle opens, begin 1-minute bar analysis
├── T+12:00 - PRELIMINARY EARLY DECISION (12th minute)
│   └─ Sufficient confluence triggers early position entry
├── T+13:00 - PRELIMINARY MID DECISION (13th minute)
│   └─ Additional analysis consolidates decision confidence
├── T+14:00 - PRELIMINARY DECISION (14th minute)
│   └─ Final review before execution window
├── T+14:55 - FINALIZED DECISION (by 14min:55sec)
│   ├─ All calculations complete
│   ├─ Execute pending orders
│   └─ Update state persistence
└── T+15:00 - New 15min candle opens, cycle repeats

CONTINUOUS BACKGROUND CYCLES:
├── Every 30 seconds: Exchange Verification Loop
│   ├─ Position status confirmation
│   ├─ Order fill verification
│   └─ P&L reconciliation
├── Every 1 minute: Signal Ingestion & Repository Update
│   ├─ Strategy signal reception
│   ├─ Building block data update
│   └─ Context refresh
├── Every 5 minutes: Human Influence Module Check
│   └─ Process new analyst inputs via OpenRouter
└── Every 1 hour: External Context Refresh
    ├─ Polymarket data sync
    ├─ Economic calendar check
    └─ Dominance metric update
```

---

## Core Framework Specifications

### 1. Trading Scope & Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Trading Pair** | BTC/USDT | Binance Futures |
| **Primary Timeframe** | 15-minute candles | Signal aggregation timeframe |
| **Analysis Granularity** | 1-minute bar closes | Intra-candle decision precision |
| **Leverage Range** | 1x - 15x | Dynamic based on signal quality |
| **Starting Capital** | $25,000 | Fixed governance balance |
| **Max Allocation** | 100% of compounded balance | With capital preservation thresholds |
| **Position Sizing** | Risk-based % of capital | Calculated per 5D scoring |
| **Max Concurrent Positions** | 5 active | Long + short + hedges |
| **Slippage Budget** | 0.05% for limit orders | 0.15% for market fallback |

### 2. Decision Finalization Timeline

**Critical Timing Requirements:**

```
Minute 12 (T+12:00)
├─ Receive all 11-minute bar closes
├─ Aggregate preliminary signals
└─ FLAG FOR EARLY DECISION: If convergence ≥85%
    └─ Execute early entries only if signal quality ≥80%

Minute 13 (T+13:00)
├─ Receive 12-minute bar close
├─ Update all technical indicators
├─ Refresh market context (dominance, Fear & Greed)
└─ FLAG FOR MID DECISION: If convergence ≥80%
    └─ Enable standard entry execution

Minute 14 (T+14:00)
├─ Receive 13-minute bar close
├─ Final indicator recalculation
├─ Apply human influence adjustments
└─ FLAG FOR PRELIMINARY DECISION: If ready
    └─ Standby for execution (final review stage)

Minute 14:55 (T+14:55) ⏰ CRITICAL DEADLINE
├─ Receive 14-minute bar close
├─ FINALIZE all calculations
├─ Apply all overrides from Central Intelligence
├─ Execute all pending orders
├─ Log all decisions
└─ Update state persistence (checkpoint)
    └─ System ready for next 15min cycle
```

### 3. Integration with Building Blocks & Strategies

**Building Block Categories:**

1. **Technical Analysis Building Blocks:**
   - Moving average convergence/divergence (MACD, EMA, SMA)
   - Oscillators (RSI, Stochastic, Williams %R)
   - Volatility indicators (Bollinger Bands, ATR, Standard Deviation)
   - Volume-based analysis (OBV, VWAP)
   - Trend confirmation (ADX, Supertrend)

2. **Macro Building Blocks:**
   - Dominance flows (BTC dominance, USDT dominance tracking)
   - Liquidity zones (Order book clustering)
   - Market regime detection (Volatility regimes, trend strength)
   - Correlation analysis (BTC-to-tech-index correlation)

3. **Custom Building Blocks:**
   - Price action pattern recognition
   - Support/resistance level detection
   - Liquidation level monitoring
   - MEV/order flow analysis

**Strategy Signal Format:**

```python
@dataclass
class StrategySignal:
    strategy_id: str                    # Unique strategy identifier
    signal_type: SignalType             # ENTRY_LONG, ENTRY_SHORT, EXIT, DCA, CLOSE
    confidence: float                   # 0.0-1.0 confidence score
    timestamp: datetime                 # Signal generation time
    bar_index: int                      # Which bar in cycle (0-14 for 15min)
    
    # Trade targets (when applicable)
    tp1_price: Optional[float]          # First take profit level
    tp1_percent: Optional[float]        # % of position to close at TP1
    tp2_price: Optional[float]          # Second take profit level
    tp2_percent: Optional[float]        # % of position to close at TP2
    tp3_price: Optional[float]          # Third take profit level
    tp3_percent: Optional[float]        # % of position to close at TP3
    trailing_stop_enabled: bool         # Enable trailing stop for remainder
    trailing_stop_percent: float        # Trailing stop distance %
    
    # Risk management
    stop_loss_price: Optional[float]    # Hard stop loss level
    stop_loss_percent: Optional[float]  # Stop loss % from entry
    entry_price_target: Optional[float] # Suggested entry price
    
    # Context
    market_regime: str                  # TRENDING_UP, TRENDING_DOWN, RANGE_BOUND, VOLATILE
    volatility_regime: str              # LOW, MEDIUM, HIGH, EXTREME
    reasoning: str                      # Human-readable signal rationale
    
    # Meta
    building_blocks_contrib: List[str]  # Contributing building block IDs
```

**Signal Aggregation:**
- All strategy signals published to Redis pub/sub channel `signals:*`
- Central repository consumes and maintains moving window of last 100 signals per strategy
- Signals decay in weight exponentially: age < 5 min (100%), 5-10 min (75%), 10-15 min (50%), >15 min (25%)
- Consensus calculation: weighted sum of confidence scores across strategies

---

## Signal Processing & Data Aggregation

### 1. Central Repository Architecture

**Redis Data Structures:**

```python
# Active Signal Store
SIGNALS:STRATEGY:{strategy_id} → Sorted Set (score=timestamp)
    Value: JSON serialized StrategySignal
    
# Aggregated Context
CONTEXT:MARKET → Hash
    - current_price: float
    - volatility_regime: string
    - trend_direction: string
    - session_type: string (ASIAN, LONDON, NEWYORK)
    - fear_greed_index: int (0-100)
    - btc_dominance: float (%)
    - usdt_dominance: float (%)
    
# Position State
POSITION:CURRENT → Hash
    - position_id: string
    - side: string (LONG/SHORT)
    - entry_price: float
    - entry_size: float
    - entry_time: datetime
    - current_pnl: float
    - current_pnl_percent: float
    - tp1_triggered: boolean
    - tp2_triggered: boolean
    - remaining_size: float
    - strategy_id: string (originating strategy)
    
# Trade History (per 15min candle)
TRADES:CANDLE:{candle_timestamp} → List
    Value: JSON serialized trade execution record
    
# Human Influence Store
HUMAN_INFLUENCE:ACTIVE → Hash
    - input_id: string
    - analyst_sentiment: string (BULLISH/BEARISH/NEUTRAL)
    - confidence: float (0.0-1.0)
    - timeframe: string (15m, 1h, 2h, 4h, 1d, 3d, 1w)
    - entry_date: datetime
    - expiration_date: datetime
    - status: string (ACTIVE/INVALIDATED/EXPIRED)
    - price_high: float
    - price_low: float
    - original_instruction: string
    - openrouter_analysis: string
    
# Capital Allocation
CAPITAL:ALLOCATION → Hash
    - starting_balance: float
    - current_balance: float
    - compounded_balance: float
    - allocated_capital: float
    - free_capital: float
    - risk_free_threshold: float
    - leverage_multiplier: float
    - update_timestamp: datetime
```

### 2. Signal Ingestion Pipeline

```python
class SignalIngestionEngine:
    """
    Ingests strategy signals and building block context into 
    central repository with decay-weighted aggregation.
    """
    
    def __init__(self, redis_client, config):
        self.redis = redis_client
        self.config = config
        self.signal_window = {}  # Per-strategy signal history
        self.aggregation_weights = {
            'age_0_5min': 1.0,      # < 5 min old
            'age_5_10min': 0.75,    # 5-10 min old
            'age_10_15min': 0.5,    # 10-15 min old
            'age_15plus': 0.25      # > 15 min old
        }
    
    async def ingest_signal(self, signal: StrategySignal) -> None:
        """
        Primary entry point for strategy signals.
        - Store signal with timestamp decay weight
        - Update strategy signal window
        - Trigger aggregation recalculation
        - Log decision factors
        """
        strategy_key = f"SIGNALS:STRATEGY:{signal.strategy_id}"
        
        # Store with TTL (signals valid for 15 minutes max)
        await self.redis.zadd(
            strategy_key,
            {signal.to_json(): signal.timestamp.timestamp()},
            xx=False
        )
        await self.redis.expire(strategy_key, 900)  # 15 minutes
        
        # Update in-memory window
        if signal.strategy_id not in self.signal_window:
            self.signal_window[signal.strategy_id] = []
        self.signal_window[signal.strategy_id].append(signal)
        
        # Keep only last 100 signals per strategy
        if len(self.signal_window[signal.strategy_id]) > 100:
            self.signal_window[signal.strategy_id] = \
                self.signal_window[signal.strategy_id][-100:]
        
        # Trigger consensus recalculation
        await self.recalculate_consensus()
    
    async def ingest_context(self, context_type: str, data: dict) -> None:
        """
        Ingest building block context data.
        """
        context_key = f"CONTEXT:{context_type}"
        await self.redis.hset(context_key, mapping=data)
        await self.redis.expire(context_key, 900)
    
    async def recalculate_consensus(self) -> AggregatedSignal:
        """
        Calculate weighted consensus across all active strategies.
        Returns aggregated signal with convergence metrics.
        """
        now = datetime.now()
        
        # Collect all active signals with decay weights
        weighted_signals = []
        
        for strategy_id, signals in self.signal_window.items():
            for signal in signals:
                age_minutes = (now - signal.timestamp).total_seconds() / 60
                
                # Apply age decay weight
                if age_minutes < 5:
                    decay_weight = 1.0
                elif age_minutes < 10:
                    decay_weight = 0.75
                elif age_minutes < 15:
                    decay_weight = 0.5
                else:
                    decay_weight = 0.25
                
                weighted_confidence = signal.confidence * decay_weight
                weighted_signals.append({
                    'strategy_id': strategy_id,
                    'signal_type': signal.signal_type,
                    'confidence': weighted_confidence,
                    'original_confidence': signal.confidence,
                    'decay_weight': decay_weight,
                    'timestamp': signal.timestamp
                })
        
        # Group by signal type
        signal_groups = {}
        for ws in weighted_signals:
            sig_type = ws['signal_type']
            if sig_type not in signal_groups:
                signal_groups[sig_type] = []
            signal_groups[sig_type].append(ws)
        
        # Calculate convergence metrics
        aggregated = AggregatedSignal(
            primary_signal_type=self._determine_primary_signal(signal_groups),
            convergence_strength=self._calculate_convergence(signal_groups),
            consensus_confidence=self._calculate_consensus_confidence(signal_groups),
            contributing_strategies=len(self.signal_window),
            signal_age_distribution=self._age_distribution(weighted_signals),
            dominant_market_regime=await self._get_dominant_regime(),
            timestamp=now
        )
        
        # Store aggregated signal
        await self.redis.hset(
            "AGGREGATED_SIGNAL",
            mapping=aggregated.to_dict()
        )
        
        return aggregated
    
    def _calculate_convergence(self, signal_groups: dict) -> float:
        """
        Convergence strength = normalized sum of weighted confidences
        for dominant signal type.
        Range: 0.0-1.0
        """
        if not signal_groups:
            return 0.0
        
        max_sum = max(
            sum(s['confidence'] for s in group)
            for group in signal_groups.values()
        )
        
        total_strategies = len(self.signal_window)
        return min(max_sum / total_strategies, 1.0)
    
    def _determine_primary_signal(self, signal_groups: dict) -> str:
        """Determine dominant signal type by weighted confidence sum."""
        if not signal_groups:
            return "NEUTRAL"
        
        return max(
            signal_groups.items(),
            key=lambda x: sum(s['confidence'] for s in x[1])
        )[0]
```

### 3. Building Block Modularity

**Adding New Building Blocks:**

```python
class BuildingBlockInterface:
    """
    Base interface for all building blocks.
    Enables plug-and-play expansion of analysis modules.
    """
    
    @abstractmethod
    async def analyze(self, ohlcv_data: pd.DataFrame) -> BuildingBlockOutput:
        """
        Analyze current candle and return findings.
        
        Args:
            ohlcv_data: DataFrame with OHLCV data (last 100 candles)
        
        Returns:
            BuildingBlockOutput with analysis results and signal contributions
        """
        pass
    
    @abstractmethod
    def get_config(self) -> dict:
        """Return block configuration for JSON storage."""
        pass
    
    @abstractmethod
    async def validate_signal(self, signal: StrategySignal) -> bool:
        """Secondary validation of strategy signal."""
        pass


@dataclass
class BuildingBlockOutput:
    block_id: str
    block_name: str
    analysis_timestamp: datetime
    findings: dict                  # Custom findings per block
    metrics: dict                   # Key metrics for decision engine
    signal_suggestions: List[str]   # Suggested signal types
    confidence_contribution: float  # 0.0-1.0 confidence modifier
    regime_assessment: str          # BULLISH, BEARISH, NEUTRAL, UNCERTAIN
    reasoning: str


# Example: Custom Building Block
class OrderFlowAnalysisBlock(BuildingBlockInterface):
    """Analyzes order flow imbalance on current candle."""
    
    def __init__(self, redis_client, binance_client):
        self.redis = redis_client
        self.binance = binance_client
        self.block_id = "ORDER_FLOW_001"
    
    async def analyze(self, ohlcv_data: pd.DataFrame) -> BuildingBlockOutput:
        # Get current orderbook
        orderbook = await self.binance.get_order_book(
            'BTCUSDT',
            limit=50
        )
        
        # Calculate bid/ask imbalance
        bid_volume = sum(b[1] for b in orderbook['bids'])
        ask_volume = sum(a[1] for a in orderbook['asks'])
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        
        # Determine regime
        if imbalance > 0.1:
            regime = "BULLISH"
            confidence = min(imbalance * 2, 1.0)
        elif imbalance < -0.1:
            regime = "BEARISH"
            confidence = min(abs(imbalance) * 2, 1.0)
        else:
            regime = "NEUTRAL"
            confidence = 0.3
        
        return BuildingBlockOutput(
            block_id=self.block_id,
            block_name="Order Flow Analysis",
            analysis_timestamp=datetime.now(),
            findings={
                'bid_volume': bid_volume,
                'ask_volume': ask_volume,
                'imbalance_ratio': imbalance,
                'dominant_side': 'BID' if imbalance > 0 else 'ASK'
            },
            metrics={
                'imbalance_score': imbalance,
                'volume_magnitude': bid_volume + ask_volume
            },
            signal_suggestions=[],
            confidence_contribution=confidence,
            regime_assessment=regime,
            reasoning=f"Bid/Ask imbalance: {imbalance:.4f}"
        )
```

---

## Central Intelligence Engine

### 1. Multi-Strategy Consensus & Override System

**Purpose:** Synthesize signals from multiple strategies, identify contradictions, and apply intelligent overrides to TP/SL/position management.

```python
class CentralIntelligenceEngine:
    """
    Multi-layered decision system that:
    1. Aggregates strategy signals
    2. Detects multi-strategy consensus
    3. Applies dynamic TP/SL overrides
    4. Manages DCA and position scaling
    5. Monitors for accumulation zones vs false signals
    """
    
    def __init__(self, redis_client, db_pool, config):
        self.redis = redis_client
        self.db = db_pool
        self.config = config
        self.consensus_threshold = config.get('consensus_threshold', 0.70)
        self.override_cache = {}
    
    async def evaluate_position_override(
        self,
        current_position: Position,
        aggregated_signal: AggregatedSignal,
        market_context: dict
    ) -> PositionOverride:
        """
        Determine if current position's TP/SL should be overridden
        based on multi-strategy confluence.
        
        Scenario 1: Strong reversal signals while position near SL
        → Assess if accumulation zone vs break (DCA vs close)
        
        Scenario 2: Signal consensus indicates trend continuation
        → Widen stops, move to breakeven, enable trailing
        
        Scenario 3: Conflicting signals (some strategies bullish, others bearish)
        → Tighten stops, reduce size if still in profit, OR close if SL approached
        """
        
        # Get all active strategies for this position direction
        contributing_strategies = await self._get_contributing_strategies(
            current_position.strategy_id
        )
        
        # Analyze signal distribution for position direction
        aligned_signals = []
        conflicting_signals = []
        
        for strategy in contributing_strategies:
            signals = await self.redis.zrange(
                f"SIGNALS:STRATEGY:{strategy}",
                0, -1
            )
            
            for sig_json in signals:
                sig = StrategySignal.from_json(sig_json)
                
                # Check if signal aligns with current position
                if self._is_signal_aligned(sig, current_position):
                    aligned_signals.append(sig)
                else:
                    conflicting_signals.append(sig)
        
        # Calculate alignment score
        total_signals = len(aligned_signals) + len(conflicting_signals)
        if total_signals == 0:
            return PositionOverride(
                override_type="NONE",
                reasoning="Insufficient signal data"
            )
        
        alignment_score = len(aligned_signals) / total_signals
        avg_aligned_confidence = (
            sum(s.confidence for s in aligned_signals) / len(aligned_signals)
            if aligned_signals else 0.0
        )
        
        # DECISION LOGIC
        override = PositionOverride()
        override.alignment_score = alignment_score
        override.signal_count = total_signals
        
        # Scenario 1: Potential reversal while near SL
        pnl_to_sl = self._calculate_pnl_to_sl(current_position)
        
        if pnl_to_sl < 2.0 and alignment_score < 0.4:  # <2% away, many conflicts
            
            # Check if accumulation zone or reversal
            accumulation_probability = await self._assess_accumulation_zone(
                current_position,
                conflicting_signals
            )
            
            if accumulation_probability > 0.6:
                # Enable DCA - add to position with adjusted SL
                override.override_type = "DCA"
                override.dca_amount_percent = 0.5  # Add 50% more
                override.new_stop_loss = self._calculate_new_sl_for_dca(
                    current_position,
                    accumulation_probability
                )
                override.reasoning = (
                    f"Accumulation zone detected (prob={accumulation_probability:.2f}). "
                    f"DCA into position with adjusted SL."
                )
            else:
                # Close position - likely reversal
                override.override_type = "CLOSE"
                override.close_reason = "Reversal signal with insufficient alignment"
                override.reasoning = (
                    f"Low alignment score ({alignment_score:.2f}) indicates reversal. "
                    f"Closing to preserve capital."
                )
        
        # Scenario 2: Strong continuation signal
        elif alignment_score > 0.75 and avg_aligned_confidence > 0.75:
            override.override_type = "ENHANCE"
            
            # Widen stops, enable trailing
            if not current_position.trailing_stop_enabled:
                override.enable_trailing_stop = True
                override.trailing_stop_percent = 2.0
            
            # If TP1 not yet triggered, consider expanding to TP2/TP3
            if not current_position.tp1_triggered:
                override.new_tp2 = self._calculate_enhanced_tp(
                    current_position,
                    'TP2'
                )
                override.new_tp3 = self._calculate_enhanced_tp(
                    current_position,
                    'TP3'
                )
            
            override.reasoning = (
                f"Strong continuation confluence (align={alignment_score:.2f}, "
                f"conf={avg_aligned_confidence:.2f}). Enhancing targets."
            )
        
        # Scenario 3: Mixed signals
        elif 0.4 <= alignment_score <= 0.75:
            if pnl_to_sl < 3.0:
                # Tighten stops
                override.override_type = "TIGHTEN"
                override.new_stop_loss = self._calculate_tightened_sl(
                    current_position,
                    0.5  # 50% closer to entry
                )
                override.reasoning = (
                    f"Mixed signals ({alignment_score:.2f}). Tightening SL for protection."
                )
            else:
                # Hold position, no action
                override.override_type = "HOLD"
        
        # Store override in cache for execution
        override.timestamp = datetime.now()
        override.position_id = current_position.position_id
        self.override_cache[current_position.position_id] = override
        
        return override
    
    def _calculate_pnl_to_sl(self, position: Position) -> float:
        """Calculate % profit/loss distance to stop loss."""
        if position.side == "LONG":
            return abs(position.current_price - position.stop_loss_price) / position.stop_loss_price * 100
        else:
            return abs(position.stop_loss_price - position.current_price) / position.current_price * 100
    
    async def _assess_accumulation_zone(
        self,
        position: Position,
        conflicting_signals: List[StrategySignal]
    ) -> float:
        """
        Assess probability that current price level is accumulation zone.
        Returns probability 0.0-1.0
        
        Factors:
        - Multiple strategies issuing same-direction signals
        - Volume profile clustering
        - Support/resistance proximity
        - Time-to-breakout estimate
        """
        
        # Get volume profile for last 20 candles
        volume_clustering = await self._analyze_volume_clustering(position)
        
        # Get support/resistance proximity
        support_resistance = await self._assess_sr_proximity(position)
        
        # Count same-direction signals in conflicting set
        opposite_direction_count = sum(
            1 for s in conflicting_signals
            if self._get_signal_direction(s) == position.opposite_direction
        )
        
        # Base probability
        probability = 0.0
        
        # Factor 1: Volume clustering (0-0.3)
        if volume_clustering['cluster_strength'] > 0.7:
            probability += 0.3
        elif volume_clustering['cluster_strength'] > 0.5:
            probability += 0.2
        else:
            probability += 0.1
        
        # Factor 2: Support/Resistance (0-0.4)
        if support_resistance['distance_to_sr'] < 1.0:
            probability += 0.4
        elif support_resistance['distance_to_sr'] < 2.0:
            probability += 0.25
        else:
            probability += 0.1
        
        # Factor 3: Same-direction signal conviction (0-0.3)
        total_signals = len(conflicting_signals)
        if total_signals > 0:
            direction_ratio = opposite_direction_count / total_signals
            probability += direction_ratio * 0.3
        
        return min(probability, 1.0)
```

### 2. Scaling and DCA Management

```python
class DCAAndScalingManager:
    """
    Manages Dollar Cost Averaging entries and intelligent position scaling
    in response to Central Intelligence signals.
    """
    
    def __init__(self, redis_client, capital_manager):
        self.redis = redis_client
        self.capital_manager = capital_manager
    
    async def calculate_dca_entry(
        self,
        position: Position,
        dca_amount_percent: float,
        new_stop_loss: float
    ) -> DCAAdjustment:
        """
        Calculate DCA entry details:
        - New entry size (% of original position)
        - Adjusted stop loss level
        - Updated risk/reward
        - Execution strategy (limit orders with TWAP)
        """
        
        # Get current available capital
        available_capital = await self.capital_manager.get_available_capital()
        
        # Calculate DCA position size
        original_risk = abs(position.entry_price - position.stop_loss_price)
        dca_amount = position.entry_size * (dca_amount_percent / 100)
        dca_cost = dca_amount * position.current_price
        
        if dca_cost > available_capital:
            dca_amount = available_capital / position.current_price
            dca_amount_percent = (dca_amount / position.entry_size) * 100
        
        # Calculate weighted average for new stop loss
        total_size = position.entry_size + dca_amount
        weighted_sl = (
            (position.entry_price * position.entry_size + 
             position.current_price * dca_amount) / total_size
        ) - (new_stop_loss - position.entry_price)
        
        # New TP levels (recalculate based on new entry avg)
        new_entry_avg = (
            (position.entry_price * position.entry_size + 
             position.current_price * dca_amount) / total_size
        )
        
        original_risk_per_unit = abs(new_entry_avg - new_stop_loss)
        
        dca_adj = DCAAdjustment(
            position_id=position.position_id,
            dca_entry_size=dca_amount,
            dca_entry_price_target=position.current_price,
            dca_amount_percent=dca_amount_percent,
            new_weighted_entry=new_entry_avg,
            new_stop_loss=weighted_sl,
            new_tp1=new_entry_avg + (original_risk_per_unit * 1.5),
            new_tp2=new_entry_avg + (original_risk_per_unit * 3.0),
            new_tp3=new_entry_avg + (original_risk_per_unit * 5.0),
            total_position_size=total_size,
            execution_strategy="TWAP_3_LEVELS"  # $0.50, $1, $2 from price
        )
        
        return dca_adj
    
    async def calculate_scaling_out(
        self,
        position: Position,
        market_context: dict
    ) -> PartialClosureStrategy:
        """
        Intelligent position scaling when:
        - TP reached but signal quality degraded
        - Trend change detected (reversal scoring)
        - Market regime shifted
        
        Returns: Which % to close and at what prices
        """
        
        # Analyze trend exhaustion
        reversal_score = await self._calculate_reversal_score(
            position,
            market_context
        )
        
        if reversal_score > 70:
            # High reversal probability - scale out 40-60%
            scale_percent = min(40 + (reversal_score - 70) * 2, 60)
        elif market_context.get('market_regime') != position.original_regime:
            # Regime shift - scale out 30%
            scale_percent = 30
        else:
            # Normal partial profit taking
            scale_percent = 20
        
        return PartialClosureStrategy(
            position_id=position.position_id,
            scale_out_percent=scale_percent,
            target_price=position.current_price + (
                position.current_price * market_context.get('atr_percent', 0.005)
            ),
            reversal_score=reversal_score,
            reasoning=f"Scale out {scale_percent}% (reversal={reversal_score})"
        )
```

---

## External Market Context Integration

### 1. Economic Calendar & Polymarket Integration

```python
class ExternalMarketContextModule:
    """
    Monitors external market factors:
    - ForexFactory economic calendar events
    - Polymarket predictions and probabilities
    - BTC/USDT dominance flows
    - Crypto Fear & Greed Index
    - Tech index correlation
    """
    
    def __init__(self, config):
        self.config = config
        self.forex_factory = ForexFactoryClient()
        self.polymarket = PolymarketClient(
            config['polymarket_api_key']
        )
        self.binance = BinanceClient(
            config['binance_api_key'],
            config['binance_api_secret']
        )
        self.fear_greed = FearGreedIndexClient()
    
    async def get_economic_event_risk(
        self,
        timestamp: datetime
    ) -> EconomicEventRisk:
        """
        Assess economic event risk for the trading day.
        
        Returns:
        - Event name
        - Expected impact level
        - Probability of event occurrence
        - Market expectation vs consensus
        - Polymarket prediction data
        """
        
        # Get events for today (cached, updated hourly)
        events_today = await self.forex_factory.get_daily_events(
            date=timestamp.date()
        )
        
        # Filter events happening within next 2 hours (trading window)
        upcoming_events = [
            e for e in events_today
            if e['time'] <= timestamp + timedelta(hours=2)
        ]
        
        risk_assessment = EconomicEventRisk(
            timestamp=timestamp,
            events=[]
        )
        
        for event in upcoming_events:
            # Get Polymarket prediction if available
            polymarket_data = await self.polymarket.get_market_prediction(
                event_name=event['title'],
                category='Economy and Finance'
            )
            
            event_risk = {
                'name': event['title'],
                'impact_level': event['impact'],  # LOW, MEDIUM, HIGH
                'country': event['country'],
                'forecast': event['forecast'],
                'previous': event['previous'],
                'actual': event.get('actual'),
                'polymarket_probability': polymarket_data['yes_prob'] if polymarket_data else None,
                'market_expectation': event['forecast'],
                'time_to_event': (event['time'] - timestamp).total_seconds() / 60
            }
            risk_assessment.events.append(event_risk)
        
        # Calculate overall risk score
        risk_assessment.overall_risk_score = self._calculate_event_risk_score(
            risk_assessment.events
        )
        
        return risk_assessment
    
    async def get_dominance_flows(self) -> DominanceFlowData:
        """
        Get current BTC and USDT dominance with trend analysis.
        """
        
        # Get 1-day, 1-week historical data
        btc_dominance = await self.binance.get_btc_dominance_historical(
            interval='1d',
            limit=30
        )
        usdt_dominance = await self.binance.get_usdt_dominance_historical(
            interval='1d',
            limit=30
        )
        
        # Analyze trend
        btc_trend = self._analyze_trend(btc_dominance)
        usdt_trend = self._analyze_trend(usdt_dominance)
        
        return DominanceFlowData(
            btc_dominance_current=btc_dominance[-1]['value'],
            btc_dominance_trend=btc_trend,
            usdt_dominance_current=usdt_dominance[-1]['value'],
            usdt_dominance_trend=usdt_trend,
            capital_flow_direction='TO_BTC' if btc_trend == 'UP' else 'TO_ALTS',
            dominance_histogram=[
                {'timestamp': d['timestamp'], 'btc': d['value']}
                for d in btc_dominance
            ]
        )
    
    async def get_fear_greed_index(self) -> dict:
        """
        Get current Crypto Fear & Greed Index with classification.
        """
        index_data = await self.fear_greed.get_current()
        
        # Classify sentiment
        value = index_data['value']
        if value < 25:
            sentiment = "EXTREME_FEAR"
        elif value < 45:
            sentiment = "FEAR"
        elif value < 55:
            sentiment = "NEUTRAL"
        elif value < 75:
            sentiment = "GREED"
        else:
            sentiment = "EXTREME_GREED"
        
        return {
            'index': value,
            'sentiment': sentiment,
            'classification': index_data['classification'],
            'timestamp': index_data['timestamp'],
            'description': index_data['description']
        }
    
    async def assess_event_impact_probability(
        self,
        event_data: dict
    ) -> float:
        """
        For high-impact events, assess probability of significant
        market move based on Polymarket data and historical patterns.
        
        Returns: Probability 0.0-1.0 of adverse move
        """
        
        polymarket_prob = event_data.get('polymarket_probability', 0.5)
        impact_level = event_data.get('impact_level', 'MEDIUM')
        
        # Base probability from Polymarket
        base_prob = polymarket_prob if polymarket_prob > 0.5 else (1 - polymarket_prob)
        
        # Apply impact multiplier
        impact_multiplier = {
            'LOW': 0.3,
            'MEDIUM': 0.7,
            'HIGH': 1.0
        }.get(impact_level, 0.7)
        
        return base_prob * impact_multiplier
    
    def _calculate_event_risk_score(self, events: list) -> float:
        """
        Overall risk score from 0.0-1.0
        Weighted by impact level and time proximity.
        """
        if not events:
            return 0.0
        
        weighted_scores = []
        
        for event in events:
            # Weight by impact
            impact_weight = {
                'LOW': 0.2,
                'MEDIUM': 0.5,
                'HIGH': 1.0
            }.get(event['impact_level'], 0.5)
            
            # Weight by proximity (closer = higher)
            proximity_weight = max(0.0, 1.0 - (event['time_to_event'] / 120))
            
            weighted_scores.append(impact_weight * proximity_weight)
        
        return min(sum(weighted_scores) / len(weighted_scores), 1.0)
```

### 2. Market Context Decision Rules

```python
class MarketContextDecisionEngine:
    """
    Applies market context to override/adjust position decisions.
    """
    
    async def apply_event_risk_override(
        self,
        current_decision: TradeDecision,
        event_risk: EconomicEventRisk
    ) -> TradeDecision:
        """
        If high-impact event within 30 min with >70% negative probability:
        - Reduce position size to 50%
        - Tighten stops to breakeven + 0.5% buffer
        - Close all pending limit orders
        """
        
        high_risk_events = [
            e for e in event_risk.events
            if e['impact_level'] == 'HIGH' 
            and e['time_to_event'] < 30
        ]
        
        negative_events = [
            e for e in high_risk_events
            if e.get('polymarket_probability', 0.5) > 0.70
        ]
        
        if negative_events:
            current_decision.position_size *= 0.5
            current_decision.stop_loss_tightened = True
            current_decision.cancel_pending_limit_orders = True
            current_decision.event_override_reason = (
                f"High-risk event: {negative_events[0]['name']}"
            )
        
        return current_decision
    
    async def apply_dominance_flow_bias(
        self,
        current_decision: TradeDecision,
        dominance_data: DominanceFlowData
    ) -> TradeDecision:
        """
        Adjust entry confidence based on dominance flows:
        - BTC dominance rising + USDT dominance falling = Capital flowing to BTC = bullish bias
        - BTC dominance falling + USDT dominance rising = Capital flowing to stables = bearish bias
        """
        
        btc_momentum = self._calculate_trend_momentum(
            dominance_data.btc_dominance_trend
        )
        usdt_momentum = self._calculate_trend_momentum(
            dominance_data.usdt_dominance_trend
        )
        
        # Net flow direction
        flow_direction = btc_momentum - usdt_momentum
        
        if flow_direction > 0.15:  # Strong capital to BTC
            current_decision.long_confidence_boost = 0.10
            current_decision.context_notes.append("BTC dominance rising - bullish")
        elif flow_direction < -0.15:  # Strong capital from BTC
            current_decision.short_confidence_boost = 0.10
            current_decision.context_notes.append("BTC dominance falling - bearish")
        
        return current_decision
```

---

## Risk Management & Compounding System

### 1. Capital Allocation & Compounding

```python
class CapitalManagementEngine:
    """
    Governs all trading by fixed $25,000 starting balance.
    Implements compounding where profits increase available capital.
    Maintains capital preservation thresholds.
    """
    
    def __init__(self, postgres_pool, redis_client, starting_balance: float = 25000.0):
        self.postgres = postgres_pool
        self.redis = redis_client
        self.starting_balance = starting_balance
        self.compounding_history = []
    
    async def initialize_capital(self, account_balance: float) -> None:
        """
        Initialize capital management on system start.
        Actual exchange balance is independent; this system uses fixed $25k.
        """
        
        await self.postgres.execute("""
            INSERT INTO capital_state (
                starting_balance,
                current_balance,
                compounded_balance,
                allocated_capital,
                free_capital,
                risk_free_threshold,
                initialization_time,
                status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, 
            self.starting_balance,
            self.starting_balance,
            self.starting_balance,
            0.0,
            self.starting_balance,
            self.starting_balance * 0.20,  # 20% risk-free
            datetime.now(),
            'ACTIVE'
        )
    
    async def get_available_capital(self) -> float:
        """
        Return available capital for new position entries.
        = Free capital (compounded - allocated - risk-free)
        """
        
        state = await self.postgres.fetchrow("""
            SELECT 
                compounded_balance,
                allocated_capital,
                risk_free_threshold
            FROM capital_state
            WHERE status = 'ACTIVE'
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        
        if not state:
            return 0.0
        
        available = (
            state['compounded_balance'] 
            - state['allocated_capital']
            - state['risk_free_threshold']
        )
        
        return max(available, 0.0)
    
    async def allocate_capital(
        self,
        position_id: str,
        capital_amount: float,
        risk_percent: float
    ) -> CapitalAllocation:
        """
        Allocate capital for a new position.
        
        Args:
            position_id: Unique position identifier
            capital_amount: Amount to allocate in USDT
            risk_percent: % risk of this position (stop loss distance)
        
        Returns:
            CapitalAllocation with position size calculation
        """
        
        available = await self.get_available_capital()
        
        if capital_amount > available:
            raise InsufficientCapitalException(
                f"Requested {capital_amount}, available {available}"
            )
        
        # Update allocated capital
        await self.postgres.execute("""
            UPDATE capital_state
            SET allocated_capital = allocated_capital + $1,
                updated_at = $2
            WHERE status = 'ACTIVE'
        """, capital_amount, datetime.now())
        
        # Calculate position size
        # Position size = (Capital * Risk%) / (Entry - SL in %)
        # This ensures fixed risk amount across positions
        
        allocation = CapitalAllocation(
            position_id=position_id,
            allocated_amount=capital_amount,
            risk_percent=risk_percent,
            timestamp=datetime.now()
        )
        
        await self.redis.hset(
            f"CAPITAL:ALLOCATION:{position_id}",
            mapping=allocation.to_dict()
        )
        
        return allocation
    
    async def compound_position_profit(
        self,
        position_id: str,
        realized_pnl: float
    ) -> None:
        """
        Add position profit to compounded balance.
        Increases available capital for future positions.
        """
        
        # Get allocation
        allocation = await self.redis.hgetall(
            f"CAPITAL:ALLOCATION:{position_id}"
        )
        
        if not allocation:
            return
        
        # Update capital state
        await self.postgres.execute("""
            UPDATE capital_state
            SET 
                compounded_balance = compounded_balance + $1,
                allocated_capital = allocated_capital - $2,
                updated_at = $3
            WHERE status = 'ACTIVE'
        """,
            realized_pnl,
            float(allocation['allocated_amount']),
            datetime.now()
        )
        
        # Record in history
        await self.postgres.execute("""
            INSERT INTO compounding_history (
                position_id,
                realized_pnl,
                compounded_balance_before,
                compounded_balance_after,
                timestamp
            ) VALUES ($1, $2, $3, $4, $5)
        """,
            position_id,
            realized_pnl,
            float(allocation['allocated_amount']) + realized_pnl - realized_pnl,
            float(allocation['allocated_amount']) + realized_pnl,
            datetime.now()
        )
    
    async def calculate_dynamic_leverage(
        self,
        signal_quality: float,
        market_regime: str,
        position_count: int
    ) -> float:
        """
        Calculate dynamic leverage 1x-15x based on:
        - Signal quality/confidence (0.0-1.0)
        - Market regime (trending = higher, range = lower)
        - Number of concurrent positions (diversification)
        """
        
        # Base leverage from signal quality
        base_leverage = 1.0 + (signal_quality * 10)  # 1x-11x
        
        # Regime adjustment
        regime_multiplier = {
            'TRENDING_UP': 1.2,
            'TRENDING_DOWN': 1.0,
            'RANGE_BOUND': 0.7,
            'VOLATILE': 0.8
        }.get(market_regime, 1.0)
        
        # Position count adjustment (reduce leverage as positions increase)
        diversification_factor = max(0.6, 1.0 - (position_count * 0.15))
        
        calculated_leverage = (
            base_leverage 
            * regime_multiplier 
            * diversification_factor
        )
        
        # Clamp to 1x-15x range
        return max(1.0, min(calculated_leverage, 15.0))
```

### 2. Risk-Based Position Sizing

```python
class PositionSizingEngine:
    """
    Calculates position sizes based on risk allocation,
    ensuring fixed risk amount per trade.
    """
    
    async def calculate_position_size(
        self,
        capital_allocation: CapitalAllocation,
        entry_price: float,
        stop_loss_price: float,
        leverage: float = 1.0
    ) -> PositionSize:
        """
        Calculate position size for given risk parameters.
        
        Formula:
        Position Size = (Allocated Capital * Risk % * Leverage) / (Entry - SL)
        
        Example:
        - Capital: $1000, Risk: 2%, Leverage: 5x
        - Entry: $25000, SL: $24800 (0.8% = $200 from entry)
        - Position Size = (1000 * 0.02 * 5) / 200 = 0.5 BTC
        """
        
        risk_amount = (
            capital_allocation.allocated_amount 
            * (capital_allocation.risk_percent / 100)
        )
        
        # Calculate entry to SL distance
        if entry_price > stop_loss_price:  # LONG
            sl_distance = entry_price - stop_loss_price
        else:  # SHORT
            sl_distance = stop_loss_price - entry_price
        
        # Position size calculation
        position_size = (risk_amount * leverage) / sl_distance
        
        # Verify against maximum position exposure
        max_exposure = capital_allocation.allocated_amount * 10  # 10x notional
        notional_exposure = position_size * entry_price
        
        if notional_exposure > max_exposure:
            position_size = max_exposure / entry_price
        
        return PositionSize(
            quantity=position_size,
            notional_value=position_size * entry_price,
            risk_amount=risk_amount,
            leverage=leverage,
            sl_distance=sl_distance,
            sl_distance_percent=(sl_distance / entry_price) * 100
        )
```

---

## Execution Optimization

### 1. Limit Order Strategy with TWAP

```python
class ExecutionEngine:
    """
    Optimizes order execution with intelligent limit order placement
    and TWAP-style position building.
    """
    
    def __init__(self, binance_client, config):
        self.binance = binance_client
        self.config = config
        self.order_attempts = {}  # Track attempt count per order
    
    async def execute_entry_with_optimization(
        self,
        position: Position,
        entry_price: float,
        position_size: float,
        max_attempts: int = 3,
        time_window_minutes: int = 15
    ) -> ExecutionResult:
        """
        Execute entry with 3-attempt limit order strategy before market order fallback.
        
        Attempt 1: Entry +$0.50 above price (faster fill, cost of convenience)
        Attempt 2: Entry +$1.00 above price (wait 5 minutes)
        Attempt 3: Entry +$2.00 above price (wait 5 minutes, final attempt)
        Fallback: Market order
        
        For larger positions/leverage, use TWAP (Time-Weighted Average Price):
        - Split position into 3 parts
        - Execute over 5-minute intervals within entry zone
        """
        
        order_id = f"ENTRY_{position.position_id}_{datetime.now().timestamp()}"
        self.order_attempts[order_id] = []
        
        # Determine if TWAP needed (large size or high leverage)
        notional_value = position_size * entry_price
        use_twap = (
            notional_value > self.config.get('twap_threshold', 50000) 
            or position.leverage > 5.0
        )
        
        if use_twap:
            return await self._execute_twap_entry(
                position, entry_price, position_size, order_id
            )
        else:
            return await self._execute_standard_entry(
                position, entry_price, position_size, order_id, max_attempts
            )
    
    async def _execute_standard_entry(
        self,
        position: Position,
        entry_price: float,
        position_size: float,
        order_id: str,
        max_attempts: int
    ) -> ExecutionResult:
        """Three-attempt limit order strategy."""
        
        offsets = [0.50, 1.00, 2.00]  # Dollar offsets
        wait_seconds = [0, 300, 300]   # Wait time between attempts
        
        for attempt in range(max_attempts):
            # Adjust limit order price based on side
            if position.side == "LONG":
                limit_price = entry_price + offsets[attempt]
            else:
                limit_price = entry_price - offsets[attempt]
            
            # Place limit order
            order = await self.binance.place_limit_order(
                symbol='BTCUSDT',
                side=position.side,
                quantity=position_size,
                price=limit_price,
                time_in_force='IOC'  # Immediate or Cancel
            )
            
            self.order_attempts[order_id].append({
                'attempt': attempt + 1,
                'order_id': order['orderId'],
                'limit_price': limit_price,
                'timestamp': datetime.now(),
                'status': order['status']
            })
            
            # Check if filled
            if order['status'] == 'FILLED':
                return ExecutionResult(
                    order_id=order_id,
                    executed=True,
                    fill_price=order['avgPrice'],
                    fill_quantity=order['executedQty'],
                    attempts=attempt + 1,
                    execution_method='LIMIT_ORDER',
                    slippage=(
                        abs(order['avgPrice'] - entry_price) / entry_price * 100
                    )
                )
            
            # Wait before next attempt
            if attempt < max_attempts - 1:
                await asyncio.sleep(wait_seconds[attempt])
        
        # All limit orders failed, execute market order
        market_order = await self.binance.place_market_order(
            symbol='BTCUSDT',
            side=position.side,
            quantity=position_size
        )
        
        return ExecutionResult(
            order_id=order_id,
            executed=True,
            fill_price=market_order['avgPrice'],
            fill_quantity=market_order['executedQty'],
            attempts=max_attempts + 1,
            execution_method='MARKET_ORDER_FALLBACK',
            slippage=(
                abs(market_order['avgPrice'] - entry_price) / entry_price * 100
            )
        )
    
    async def _execute_twap_entry(
        self,
        position: Position,
        entry_price: float,
        position_size: float,
        order_id: str
    ) -> ExecutionResult:
        """
        TWAP execution: split position into 3 parts, execute over 5 min intervals.
        """
        
        part_size = position_size / 3
        parts = []
        
        for part_num in range(3):
            # Stagger execution times
            wait_time = part_num * 300  # 5-minute intervals
            await asyncio.sleep(wait_time)
            
            # Execute part with limit order
            limit_price = (
                entry_price + (0.50 + part_num * 0.50)
                if position.side == "LONG"
                else entry_price - (0.50 + part_num * 0.50)
            )
            
            part_order = await self.binance.place_limit_order(
                symbol='BTCUSDT',
                side=position.side,
                quantity=part_size,
                price=limit_price,
                time_in_force='IOC'
            )
            
            parts.append({
                'part': part_num + 1,
                'fill_price': part_order['avgPrice'],
                'quantity': part_order['executedQty']
            })
        
        # Calculate weighted average fill
        total_filled = sum(p['quantity'] for p in parts)
        weighted_avg = sum(
            p['fill_price'] * p['quantity'] for p in parts
        ) / total_filled if total_filled > 0 else entry_price
        
        return ExecutionResult(
            order_id=order_id,
            executed=True,
            fill_price=weighted_avg,
            fill_quantity=total_filled,
            attempts=3,
            execution_method='TWAP',
            slippage=(
                abs(weighted_avg - entry_price) / entry_price * 100
            )
        )
```

### 2. Dynamic TP/SL Placement

```python
class TakeProfitStopLossEngine:
    """
    Places and manages take profit and stop loss orders
    with dynamic adjustments based on Central Intelligence overrides.
    """
    
    async def place_tp_sl_orders(
        self,
        position: Position,
        tp1_price: float,
        tp2_price: float,
        tp3_price: float,
        sl_price: float,
        tp1_percent: float = 30,
        tp2_percent: float = 40,
        tp3_percent: float = 30
    ) -> TakeProfitStopLossOrders:
        """
        Place OCO (One-Cancels-Other) orders for TP/SL management.
        
        Allocation:
        - TP1: 30% of position (quick profit lock)
        - TP2: 40% of position (main profit target)
        - TP3: 30% of position (trend continuation)
        """
        
        orders = TakeProfitStopLossOrders(
            position_id=position.position_id
        )
        
        # TP1: Partial close
        tp1_qty = position.entry_size * (tp1_percent / 100)
        tp1_order = await self.binance.place_limit_order(
            symbol='BTCUSDT',
            side='SELL' if position.side == 'LONG' else 'BUY',
            quantity=tp1_qty,
            price=tp1_price
        )
        orders.tp1_order = tp1_order
        orders.tp1_quantity = tp1_qty
        
        # TP2: Main profit
        tp2_qty = position.entry_size * (tp2_percent / 100)
        tp2_order = await self.binance.place_limit_order(
            symbol='BTCUSDT',
            side='SELL' if position.side == 'LONG' else 'BUY',
            quantity=tp2_qty,
            price=tp2_price
        )
        orders.tp2_order = tp2_order
        orders.tp2_quantity = tp2_qty
        
        # TP3: Trailing (placed as market order when TP2 triggered)
        orders.tp3_price_target = tp3_price
        orders.tp3_quantity = position.entry_size * (tp3_percent / 100)
        orders.tp3_trailing_stop_percent = 2.0  # Trail by 2%
        
        # Stop Loss
        sl_qty = position.entry_size
        sl_order = await self.binance.place_market_order(
            symbol='BTCUSDT',
            side='SELL' if position.side == 'LONG' else 'BUY',
            quantity=sl_qty,
            stop_price=sl_price
        )
        orders.stop_loss_order = sl_order
        
        return orders
    
    async def apply_tp_sl_override(
        self,
        position: Position,
        override: PositionOverride
    ) -> None:
        """
        Cancel existing TP/SL orders and place new ones per override.
        """
        
        # Cancel existing orders
        await self.binance.cancel_orders_for_position(
            position.position_id
        )
        
        # Place new orders based on override
        if override.override_type == "ENHANCE":
            await self.place_tp_sl_orders(
                position,
                tp1_price=override.current_tp1,
                tp2_price=override.new_tp2,
                tp3_price=override.new_tp3,
                sl_price=position.stop_loss_price
            )
        elif override.override_type == "TIGHTEN":
            await self.place_tp_sl_orders(
                position,
                tp1_price=position.tp1_price,
                tp2_price=position.tp2_price,
                tp3_price=position.tp3_price,
                sl_price=override.new_stop_loss
            )
```

---

## Human Influence Module

### 1. Human Input Processing with OpenRouter

```python
class HumanInfluenceModule:
    """
    Accepts human analyst inputs (chart analysis, market outlook) and
    processes them via OpenRouter API for integration into decisions.
    """
    
    def __init__(self, redis_client, postgres_pool, config):
        self.redis = redis_client
        self.postgres = postgres_pool
        self.openrouter_api_key = config['openrouter_api_key']
        self.openrouter_base_url = "https://openrouter.io/api/v1"
    
    async def process_analyst_input(
        self,
        analyst_input: str,
        timeframe: str,  # 15m, 1h, 2h, 4h, 1d, 3d, 1w
        chart_image_url: Optional[str] = None,
        current_price: float = None
    ) -> HumanInfluenceAnalysis:
        """
        Process analyst input through OpenRouter for standardization.
        
        Input: "BTC is forming a bearish divergence on the daily chart. 
                 RSI is rejecting from 70. Looking for a pullback to $25k"
        
        Output: Structured analysis with confidence scores for ITM consideration
        """
        
        # Build prompt for OpenRouter
        system_prompt = """You are a cryptocurrency trading analysis expert. 
Analyze the provided analyst input and extract:
1. Sentiment (BULLISH/BEARISH/NEUTRAL)
2. Confidence score (0.0-1.0)
3. Key technical levels (support/resistance)
4. Expected price targets
5. Risk factors
6. Time horizon

Return as JSON."""
        
        user_prompt = f"""
Analyze this trader's input for BTC/USDT at timeframe {timeframe}:

"{analyst_input}"

Current price: ${current_price}
"""
        
        if chart_image_url:
            user_prompt += f"\nChart image: {chart_image_url}"
        
        # Call OpenRouter API
        response = await self._call_openrouter(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model="meta-llama/llama-3.1-70b-instruct"
        )
        
        # Parse response into structured format
        analysis = self._parse_openrouter_response(response)
        
        # Determine expiration based on timeframe
        timeframe_hours = {
            '15m': 0.25,
            '1h': 1,
            '2h': 2,
            '4h': 4,
            '1d': 24,
            '3d': 72,
            '1w': 168
        }
        
        hours = timeframe_hours.get(timeframe, 1)
        
        human_input = HumanInfluenceAnalysis(
            input_id=f"HI_{datetime.now().timestamp()}",
            analyst_sentiment=analysis['sentiment'],
            confidence=analysis['confidence'],
            timeframe=timeframe,
            entry_date=datetime.now(),
            expiration_date=datetime.now() + timedelta(hours=hours),
            status="ACTIVE",
            price_high=analysis.get('price_high'),
            price_low=analysis.get('price_low'),
            original_instruction=analyst_input,
            openrouter_analysis=analysis,
            key_technical_levels=analysis.get('technical_levels', {}),
            expected_targets=analysis.get('targets', []),
            risk_factors=analysis.get('risks', [])
        )
        
        # Store in Redis
        await self.redis.hset(
            f"HUMAN_INFLUENCE:{human_input.input_id}",
            mapping=human_input.to_dict()
        )
        
        # Add to active set
        await self.redis.zadd(
            "HUMAN_INFLUENCE:ACTIVE",
            {human_input.input_id: human_input.entry_date.timestamp()}
        )
        
        return human_input
    
    async def _call_openrouter(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str
    ) -> str:
        """Call OpenRouter API with messages."""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,  # More deterministic
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            ) as resp:
                data = await resp.json()
                return data['choices'][0]['message']['content']
    
    def _parse_openrouter_response(self, response: str) -> dict:
        """Extract JSON from OpenRouter response."""
        
        # Try direct JSON parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Extract JSON block from text response
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {}
    
    async def validate_human_input_against_price(
        self,
        human_input: HumanInfluenceAnalysis,
        current_price: float
    ) -> None:
        """
        Check if price/trend contradicts human input.
        If yes, mark as INVALIDATED and exclude from decisions.
        """
        
        price_high = human_input.price_high
        price_low = human_input.price_low
        
        if human_input.analyst_sentiment == "BULLISH":
            # If price breaks below recent low, mark invalid
            if current_price < price_low * 0.98:  # 2% buffer
                await self.redis.hset(
                    f"HUMAN_INFLUENCE:{human_input.input_id}",
                    "status",
                    "INVALIDATED"
                )
                return
        
        elif human_input.analyst_sentiment == "BEARISH":
            # If price breaks above recent high, mark invalid
            if current_price > price_high * 1.02:  # 2% buffer
                await self.redis.hset(
                    f"HUMAN_INFLUENCE:{human_input.input_id}",
                    "status",
                    "INVALIDATED"
                )
    
    async def get_active_human_influence(self) -> List[HumanInfluenceAnalysis]:
        """
        Get all active human influence inputs, excluding:
        - Expired inputs
        - Invalidated inputs (price moved against sentiment)
        """
        
        now = datetime.now()
        active_ids = await self.redis.zrange(
            "HUMAN_INFLUENCE:ACTIVE",
            0, -1
        )
        
        active_influences = []
        
        for input_id in active_ids:
            data = await self.redis.hgetall(f"HUMAN_INFLUENCE:{input_id}")
            
            if not data:
                continue
            
            # Check if expired
            expiration = datetime.fromisoformat(data['expiration_date'])
            if expiration < now:
                data['status'] = 'EXPIRED'
                await self.redis.hset(
                    f"HUMAN_INFLUENCE:{input_id}",
                    "status",
                    "EXPIRED"
                )
                continue
            
            # Check if invalidated
            if data['status'] == 'INVALIDATED':
                continue
            
            active_influences.append(HumanInfluenceAnalysis.from_dict(data))
        
        return active_influences
```

---

## State Management & Recovery

### 1. Checkpoint-Based State Persistence

```python
class StateCheckpointManager:
    """
    Implements checkpoint-based state persistence for system recovery.
    Saves complete system state every decision cycle.
    """
    
    def __init__(self, postgres_pool, redis_client, timescale_client):
        self.postgres = postgres_pool
        self.redis = redis_client
        self.timescale = timescale_client
    
    async def create_checkpoint(
        self,
        checkpoint_type: str = "DECISION_CYCLE"
    ) -> StateCheckpoint:
        """
        Create comprehensive checkpoint of system state.
        Called every decision cycle (every 15 minutes).
        """
        
        checkpoint = StateCheckpoint(
            checkpoint_id=f"CHK_{datetime.now().timestamp()}",
            checkpoint_type=checkpoint_type,
            timestamp=datetime.now()
        )
        
        # Capture active positions
        active_positions = await self.redis.hgetall("POSITION:CURRENT")
        checkpoint.active_positions = [
            Position.from_dict(p) for p in active_positions.values()
        ]
        
        # Capture capital state
        capital_state = await self.postgres.fetchrow("""
            SELECT * FROM capital_state
            WHERE status = 'ACTIVE'
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        checkpoint.capital_state = dict(capital_state) if capital_state else {}
        
        # Capture recent signals
        signal_keys = await self.redis.keys("SIGNALS:STRATEGY:*")
        checkpoint.recent_signals = {}
        for key in signal_keys:
            signals = await self.redis.zrange(key, -10, -1)  # Last 10
            checkpoint.recent_signals[key] = signals
        
        # Capture market context
        context = await self.redis.hgetall("CONTEXT:MARKET")
        checkpoint.market_context = context
        
        # Save to PostgreSQL
        await self.postgres.execute("""
            INSERT INTO state_checkpoints (
                checkpoint_id,
                checkpoint_type,
                timestamp,
                state_data
            ) VALUES ($1, $2, $3, $4)
        """,
            checkpoint.checkpoint_id,
            checkpoint.checkpoint_type,
            checkpoint.timestamp,
            json.dumps(checkpoint.to_dict())
        )
        
        return checkpoint
    
    async def restore_from_checkpoint(
        self,
        checkpoint_id: Optional[str] = None
    ) -> StateCheckpoint:
        """
        Restore system state from most recent checkpoint or specified ID.
        """
        
        if checkpoint_id is None:
            # Get most recent checkpoint
            checkpoint_data = await self.postgres.fetchrow("""
                SELECT state_data FROM state_checkpoints
                ORDER BY timestamp DESC
                LIMIT 1
            """)
        else:
            checkpoint_data = await self.postgres.fetchrow("""
                SELECT state_data FROM state_checkpoints
                WHERE checkpoint_id = $1
            """, checkpoint_id)
        
        if not checkpoint_data:
            raise CheckpointNotFoundException("No checkpoint found")
        
        checkpoint = StateCheckpoint.from_dict(
            json.loads(checkpoint_data['state_data'])
        )
        
        # Restore to Redis
        for position in checkpoint.active_positions:
            await self.redis.hset(
                "POSITION:CURRENT",
                position.position_id,
                position.to_json()
            )
        
        # Restore capital state
        for key, value in checkpoint.capital_state.items():
            await self.redis.hset("CAPITAL:STATE", key, str(value))
        
        return checkpoint
    
    async def execute_catch_up_protocol(
        self,
        gap_duration_hours: int
    ) -> CatchUpResult:
        """
        On restart after offline period:
        1. Restore latest checkpoint
        2. Identify time gap
        3. Replay historical data for gap period
        4. Reconstruct signals that would have been generated
        5. Reconcile positions with exchange
        """
        
        result = CatchUpResult(
            catch_up_start=datetime.now(),
            gap_duration_hours=gap_duration_hours
        )
        
        # Step 1: Restore checkpoint
        checkpoint = await self.restore_from_checkpoint()
        result.checkpoint_restored = True
        result.restored_positions = len(checkpoint.active_positions)
        
        # Step 2: Get historical OHLCV data for gap period
        gap_start = checkpoint.timestamp
        gap_end = datetime.now()
        
        historical_data = await self._fetch_historical_candles(
            gap_start, gap_end
        )
        result.historical_candles_fetched = len(historical_data)
        
        # Step 3: Reconstruct signals for gap period
        reconstructed_signals = await self._reconstruct_signals(
            historical_data
        )
        result.signals_reconstructed = len(reconstructed_signals)
        
        # Step 4: Replay through decision engine to update state
        for signal in reconstructed_signals:
            await self.redis.zadd(
                f"SIGNALS:STRATEGY:{signal.strategy_id}",
                {signal.to_json(): signal.timestamp.timestamp()}
            )
        
        # Step 5: Exchange reconciliation
        reconciliation = await self._reconcile_positions_with_exchange(
            checkpoint.active_positions
        )
        result.reconciliation_status = reconciliation['status']
        result.discrepancies = reconciliation.get('discrepancies', [])
        
        result.catch_up_complete = datetime.now()
        result.catch_up_duration_seconds = (
            result.catch_up_complete - result.catch_up_start
        ).total_seconds()
        
        return result
    
    async def _fetch_historical_candles(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Fetch 1-minute candle data for gap period from TimescaleDB."""
        
        candles = await self.timescale.fetch("""
            SELECT 
                timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM ohlcv_1m
            WHERE timestamp >= %s AND timestamp <= %s
            ORDER BY timestamp
        """, start_time, end_time)
        
        return pd.DataFrame(candles)
    
    async def _reconcile_positions_with_exchange(
        self,
        restored_positions: List[Position]
    ) -> dict:
        """
        Verify restored positions against actual exchange positions.
        Alert on discrepancies.
        """
        
        reconciliation = {
            'status': 'OK',
            'discrepancies': []
        }
        
        # Get actual positions from exchange
        exchange_positions = await self.binance.get_open_positions('BTCUSDT')
        
        # Match restored vs actual
        for restored in restored_positions:
            matching = [
                e for e in exchange_positions
                if e['positionId'] == restored.position_id
            ]
            
            if not matching:
                reconciliation['discrepancies'].append({
                    'type': 'MISSING_POSITION',
                    'position_id': restored.position_id,
                    'size': restored.entry_size
                })
                reconciliation['status'] = 'DISCREPANCIES_FOUND'
            else:
                exchange_pos = matching[0]
                
                # Check size
                if abs(exchange_pos['quantity'] - restored.entry_size) > 0.001:
                    reconciliation['discrepancies'].append({
                        'type': 'SIZE_MISMATCH',
                        'position_id': restored.position_id,
                        'expected': restored.entry_size,
                        'actual': exchange_pos['quantity']
                    })
                    reconciliation['status'] = 'DISCREPANCIES_FOUND'
        
        return reconciliation
```

### 2. Continuous Exchange Verification Loop

```python
class ExchangeVerificationLoop:
    """
    Runs continuously every 30 seconds to verify:
    - Position status matches exchange
    - Orders are filled as expected
    - P&L calculations accurate
    """
    
    def __init__(self, binance_client, postgres_pool, redis_client):
        self.binance = binance_client
        self.postgres = postgres_pool
        self.redis = redis_client
    
    async def run_verification_loop(self) -> VerificationReport:
        """
        Execute verification cycle.
        Called every 30 seconds during active trading.
        """
        
        report = VerificationReport(
            verification_time=datetime.now(),
            checks_run=0,
            checks_passed=0,
            discrepancies=[]
        )
        
        # Check 1: Position status
        report.position_check = await self._verify_positions()
        report.checks_run += 1
        if report.position_check['status'] == 'OK':
            report.checks_passed += 1
        else:
            report.discrepancies.extend(report.position_check['issues'])
        
        # Check 2: Order fills
        report.order_check = await self._verify_orders()
        report.checks_run += 1
        if report.order_check['status'] == 'OK':
            report.checks_passed += 1
        else:
            report.discrepancies.extend(report.order_check['issues'])
        
        # Check 3: P&L accuracy
        report.pnl_check = await self._verify_pnl()
        report.checks_run += 1
        if report.pnl_check['status'] == 'OK':
            report.checks_passed += 1
        else:
            report.discrepancies.extend(report.pnl_check['issues'])
        
        # Store report in TimescaleDB
        await self._log_verification_report(report)
        
        # Alert if discrepancies
        if report.discrepancies:
            await self._alert_discrepancies(report.discrepancies)
        
        return report
    
    async def _verify_positions(self) -> dict:
        """Verify position status matches exchange."""
        
        local_positions = await self.redis.hgetall("POSITION:CURRENT")
        exchange_positions = await self.binance.get_open_positions('BTCUSDT')
        
        check = {'status': 'OK', 'issues': []}
        
        for pos_id, pos_data in local_positions.items():
            position = Position.from_dict(pos_data)
            
            exchange_match = [
                p for p in exchange_positions
                if p['positionId'] == pos_id
            ]
            
            if not exchange_match:
                check['status'] = 'MISMATCH'
                check['issues'].append({
                    'type': 'POSITION_NOT_FOUND',
                    'position_id': pos_id,
                    'local_size': position.entry_size
                })
            else:
                exchange_pos = exchange_match[0]
                
                # Verify size
                size_diff = abs(
                    float(exchange_pos['quantity']) - position.entry_size
                )
                if size_diff > 0.001:
                    check['status'] = 'MISMATCH'
                    check['issues'].append({
                        'type': 'SIZE_MISMATCH',
                        'position_id': pos_id,
                        'local': position.entry_size,
                        'exchange': float(exchange_pos['quantity'])
                    })
        
        return check
    
    async def _verify_orders(self) -> dict:
        """Verify pending orders are active on exchange."""
        
        local_orders = await self.redis.hgetall("ORDERS:PENDING")
        exchange_orders = await self.binance.get_open_orders('BTCUSDT')
        
        check = {'status': 'OK', 'issues': []}
        
        # Verify each local order exists on exchange
        for order_id, order_data in local_orders.items():
            order = json.loads(order_data)
            
            exchange_match = [
                o for o in exchange_orders
                if o['orderId'] == order_id
            ]
            
            if not exchange_match:
                check['status'] = 'MISMATCH'
                check['issues'].append({
                    'type': 'ORDER_NOT_FOUND',
                    'order_id': order_id,
                    'local_qty': order['quantity']
                })
        
        return check
    
    async def _verify_pnl(self) -> dict:
        """Verify P&L calculations match exchange."""
        
        positions = await self.redis.hgetall("POSITION:CURRENT")
        check = {'status': 'OK', 'issues': []}
        
        for pos_id, pos_data in positions.items():
            position = Position.from_dict(pos_data)
            
            # Get exchange position details
            exchange_pos = await self.binance.get_position(pos_id)
            
            # Calculate P&L
            if position.side == "LONG":
                calculated_pnl = (
                    (position.current_price - position.entry_price) 
                    * position.entry_size
                )
            else:
                calculated_pnl = (
                    (position.entry_price - position.current_price) 
                    * position.entry_size
                )
            
            exchange_pnl = float(exchange_pos['unrealizedProfit'])
            
            # Allow 0.5% tolerance for fees
            pnl_diff_percent = abs(
                (calculated_pnl - exchange_pnl) / exchange_pnl
            ) * 100 if exchange_pnl != 0 else 0
            
            if pnl_diff_percent > 0.5:
                check['status'] = 'MISMATCH'
                check['issues'].append({
                    'type': 'PNL_MISMATCH',
                    'position_id': pos_id,
                    'calculated': calculated_pnl,
                    'exchange': exchange_pnl,
                    'diff_percent': pnl_diff_percent
                })
        
        return check
```

---

## Decision Framework & Scoring

### 1. Five-Dimension Decision Scoring

```python
class DecisionScoringEngine:
    """
    Evaluates five dimensions on each 1-minute bar to generate
    unified trade decision with weighted scoring.
    """
    
    def __init__(self, config):
        self.config = config
        # Dimension weights (sum = 1.0)
        self.weights = {
            'signal_quality': 0.30,
            'market_regime': 0.20,
            'event_risk': 0.15,
            'session_timing': 0.15,
            'position_state': 0.20
        }
    
    async def evaluate_trade_decision(
        self,
        aggregated_signal: AggregatedSignal,
        market_context: dict,
        event_risk: EconomicEventRisk,
        position_state: Optional[Position],
        session_timing: str
    ) -> TradeDecision:
        """
        Comprehensive trade decision evaluation across 5 dimensions.
        """
        
        decision = TradeDecision(
            evaluation_time=datetime.now(),
            primary_signal=aggregated_signal.primary_signal_type
        )
        
        # DIMENSION 1: Signal Quality (0.30 weight)
        signal_score = await self._score_signal_quality(aggregated_signal)
        decision.signal_quality_score = signal_score
        
        # DIMENSION 2: Market Regime (0.20 weight)
        regime_score = await self._score_market_regime(market_context)
        decision.market_regime_score = regime_score
        
        # DIMENSION 3: Event Risk (0.15 weight)
        event_score = await self._score_event_risk(event_risk)
        decision.event_risk_score = event_score
        
        # DIMENSION 4: Session Timing (0.15 weight)
        session_score = self._score_session_timing(session_timing)
        decision.session_timing_score = session_score
        
        # DIMENSION 5: Position State (0.20 weight)
        position_score = await self._score_position_state(position_state)
        decision.position_state_score = position_score
        
        # Calculate weighted final score
        final_score = (
            signal_score * self.weights['signal_quality'] +
            regime_score * self.weights['market_regime'] +
            event_score * self.weights['event_risk'] +
            session_score * self.weights['session_timing'] +
            position_score * self.weights['position_state']
        )
        
        decision.final_score = final_score
        
        # Determine action based on score
        if final_score >= 0.75:
            decision.action = "EXECUTE_PRIMARY"
            decision.confidence = final_score
        elif final_score >= 0.60:
            decision.action = "EXECUTE_MODIFIED"
            decision.confidence = final_score
        elif final_score >= 0.50:
            decision.action = "MONITOR"
            decision.confidence = final_score
        else:
            decision.action = "WAIT"
            decision.confidence = 1.0 - final_score
        
        decision.reasoning = self._generate_decision_reasoning(decision)
        
        return decision
    
    async def _score_signal_quality(
        self,
        aggregated_signal: AggregatedSignal
    ) -> float:
        """
        Score quality of signal consensus.
        
        Factors:
        - Convergence strength (0.0-1.0)
        - Number of contributing strategies
        - Age distribution of signals (fresher = better)
        - Historical accuracy of strategies
        """
        
        # Base score from convergence
        convergence_score = aggregated_signal.convergence_strength
        
        # Bonus for multiple strategies aligned
        strategy_bonus = min(
            aggregated_signal.contributing_strategies / 10, 0.2
        )
        
        # Age distribution (fresher signals = higher score)
        age_dist = aggregated_signal.signal_age_distribution
        freshness_score = (
            age_dist.get('0-5min', 0) * 1.0 +
            age_dist.get('5-10min', 0) * 0.75 +
            age_dist.get('10-15min', 0) * 0.5
        )
        
        # Weighted combination
        quality_score = (
            convergence_score * 0.5 +
            strategy_bonus * 2.0 +
            min(freshness_score / 3, 1.0) * 0.5
        )
        
        return min(quality_score, 1.0)
    
    async def _score_market_regime(self, market_context: dict) -> float:
        """
        Score favorability of current market regime.
        
        Factors:
        - Trend direction (trending = higher score)
        - Volatility level (moderate > extreme > low)
        - Liquidity assessment
        """
        
        regime = market_context.get('market_regime', 'RANGE_BOUND')
        volatility = market_context.get('volatility_regime', 'MEDIUM')
        
        regime_scores = {
            'TRENDING_UP': 0.90,      # Best for longs
            'TRENDING_DOWN': 0.90,    # Best for shorts
            'RANGE_BOUND': 0.50,      # Difficult
            'VOLATILE': 0.60           # Higher risk
        }
        
        volatility_scores = {
            'LOW': 0.60,
            'MEDIUM': 0.85,
            'HIGH': 0.70,
            'EXTREME': 0.40
        }
        
        regime_score = regime_scores.get(regime, 0.5)
        vol_score = volatility_scores.get(volatility, 0.5)
        
        # Liquidity check
        order_book_imbalance = market_context.get('orderbook_imbalance', 0)
        liquidity_score = 1.0 if abs(order_book_imbalance) < 0.2 else 0.7
        
        return (regime_score * 0.5 + vol_score * 0.3 + liquidity_score * 0.2)
    
    async def _score_event_risk(
        self,
        event_risk: EconomicEventRisk
    ) -> float:
        """
        Score event risk impact on trading.
        
        High negative probability events = lower score
        Scoring: 1.0 (no risk) to 0.0 (extreme risk)
        """
        
        risk_score = 1.0 - event_risk.overall_risk_score
        
        return risk_score
    
    def _score_session_timing(self, session_timing: str) -> float:
        """
        Score favorable session timing for trading.
        
        Scoring:
        - LONDON/NEWYORK overlap: 0.9 (highest liquidity)
        - LONDON: 0.85
        - NEWYORK: 0.85
        - ASIAN: 0.60 (lower activity)
        """
        
        session_scores = {
            'LONDON_NEWYORK_OVERLAP': 0.90,
            'LONDON': 0.85,
            'NEWYORK': 0.85,
            'ASIAN': 0.60
        }
        
        return session_scores.get(session_timing, 0.5)
    
    async def _score_position_state(
        self,
        position: Optional[Position]
    ) -> float:
        """
        Score current position state for decision making.
        
        Open position factors:
        - Distance to TP/SL
        - Unrealized P&L
        - Position age
        
        No position: flat score (0.5)
        """
        
        if position is None:
            return 0.5  # Neutral - open to new positions
        
        # Position exists - score based on state
        pnl_to_tp = self._calculate_pnl_to_tp(position)
        pnl_to_sl = self._calculate_pnl_to_sl(position)
        
        # If close to TP, score is high (let it run)
        if pnl_to_tp < 2.0:
            return 0.80
        
        # If close to SL, score is low (manage risk)
        if pnl_to_sl < 2.0:
            return 0.30
        
        # Mid-range, score based on P&L
        if position.current_pnl > 0:
            return 0.70  # In profit, favorable
        else:
            return 0.50  # In loss, neutral
```

### 2. Reversal Scoring

```python
class ReversalScoringEngine:
    """
    Calculates reversal probability (0-100) to boost counter-trade confidence.
    Used when current trend exhaustion is detected.
    """
    
    async def calculate_reversal_score(
        self,
        ohlcv_data: pd.DataFrame,
        market_context: dict
    ) -> int:
        """
        Calculate reversal probability score (0-100).
        
        Factors:
        - Divergence confirmation (RSI, price)
        - Momentum exhaustion
        - Support/resistance proximity
        - Volume profile
        - Time-based reversal patterns
        """
        
        score = 0
        
        # Factor 1: RSI Divergence (0-25 points)
        rsi_divergence = await self._detect_rsi_divergence(ohlcv_data)
        if rsi_divergence:
            score += 25
        
        # Factor 2: Momentum Exhaustion (0-25 points)
        momentum = await self._calculate_momentum_exhaustion(ohlcv_data)
        score += momentum
        
        # Factor 3: Support/Resistance (0-20 points)
        sr_proximity = await self._assess_sr_reversal_proximity(
            ohlcv_data, market_context
        )
        score += sr_proximity
        
        # Factor 4: Volume Profile (0-20 points)
        volume_signal = await self._analyze_reversal_volume(ohlcv_data)
        score += volume_signal
        
        # Factor 5: Time-based Patterns (0-10 points)
        time_signal = await self._detect_time_reversal_patterns(ohlcv_data)
        score += time_signal
        
        return min(score, 100)
    
    async def _detect_rsi_divergence(self, ohlcv_data: pd.DataFrame) -> bool:
        """
        Detect RSI bullish/bearish divergence.
        Higher lows in price but lower lows in RSI = bullish divergence
        """
        
        rsi = ta.momentum.rsi(ohlcv_data['close'], window=14)
        
        # Find last 3 swing lows/highs
        if len(rsi) < 20:
            return False
        
        # Check for bearish divergence (price highs, RSI lows)
        recent_highs = ohlcv_data['close'][-20:].nlargest(3).index
        recent_lows_rsi = rsi[-20:][recent_highs].nsmallest(3)
        
        # If all recent RSI values at highs are declining, divergence exists
        if len(recent_lows_rsi) >= 2:
            return recent_lows_rsi.iloc[0] > recent_lows_rsi.iloc[1]
        
        return False
    
    async def _calculate_momentum_exhaustion(
        self,
        ohlcv_data: pd.DataFrame
    ) -> int:
        """
        Assess momentum exhaustion (0-25 points).
        
        Checks:
        - MACD histogram decreasing
        - Momentum oscillator flattening
        - Price making new highs but MACD not confirming
        """
        
        macd = ta.trend.MACD(ohlcv_data['close'])
        macd_diff = macd.macd_diff()
        
        score = 0
        
        # Check if MACD histogram decreasing
        if macd_diff.iloc[-1] < macd_diff.iloc[-5]:
            score += 15
        
        # Check if momentum is decelerating
        momentum = ta.momentum.roc(ohlcv_data['close'], window=10)
        if momentum.iloc[-1] < momentum.iloc[-5]:
            score += 10
        
        return min(score, 25)
```

---

## Technology Stack

### 1. Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Trading Framework** | NautilusTrader | Core trading engine with Actor model |
| **Language** | Python 3.10+ | Primary development language |
| **Message Bus** | Redis Pub/Sub | Inter-component communication |
| **State Storage** | PostgreSQL | Configuration, metadata, checkpoint |
| **Time-Series DB** | TimescaleDB | Historical OHLCV, verification reports |
| **Real-time Cache** | Redis | Current prices, positions, signals |
| **Exchange API** | Binance Futures WebSocket + REST | Market data and order execution |
| **AI Processing** | OpenRouter API | Human input analysis |
| **External Data** | ForexFactory, Polymarket API | Economic calendar, predictions |

### 2. Database Schema

**PostgreSQL Tables:**

```sql
-- Configuration and metadata
CREATE TABLE strategies (
    strategy_id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    version TEXT,
    config JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Capital state tracking
CREATE TABLE capital_state (
    id SERIAL PRIMARY KEY,
    starting_balance NUMERIC(15,2),
    current_balance NUMERIC(15,2),
    compounded_balance NUMERIC(15,2),
    allocated_capital NUMERIC(15,2),
    free_capital NUMERIC(15,2),
    risk_free_threshold NUMERIC(15,2),
    leverage_multiplier NUMERIC(5,2),
    initialization_time TIMESTAMP,
    updated_at TIMESTAMP,
    status TEXT
);

-- Trade execution history
CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY,
    position_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    side TEXT (LONG/SHORT),
    entry_price NUMERIC(15,2),
    entry_size NUMERIC(20,8),
    entry_time TIMESTAMP,
    exit_price NUMERIC(15,2),
    exit_time TIMESTAMP,
    realized_pnl NUMERIC(15,2),
    realized_pnl_percent NUMERIC(8,4),
    status TEXT (OPEN/CLOSED),
    execution_method TEXT (LIMIT/MARKET/TWAP),
    created_at TIMESTAMP
);

-- Position tracking
CREATE TABLE positions (
    position_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    side TEXT (LONG/SHORT),
    entry_price NUMERIC(15,2),
    entry_size NUMERIC(20,8),
    entry_time TIMESTAMP,
    current_price NUMERIC(15,2),
    current_pnl NUMERIC(15,2),
    current_pnl_percent NUMERIC(8,4),
    tp1_price NUMERIC(15,2),
    tp2_price NUMERIC(15,2),
    tp3_price NUMERIC(15,2),
    stop_loss_price NUMERIC(15,2),
    tp1_triggered BOOLEAN DEFAULT FALSE,
    tp2_triggered BOOLEAN DEFAULT FALSE,
    tp3_triggered BOOLEAN DEFAULT FALSE,
    trailing_stop_enabled BOOLEAN,
    trailing_stop_percent NUMERIC(6,2),
    status TEXT (ACTIVE/CLOSED),
    updated_at TIMESTAMP
);

-- State checkpoints for recovery
CREATE TABLE state_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    checkpoint_type TEXT,
    timestamp TIMESTAMP,
    state_data JSONB,
    created_at TIMESTAMP
);

-- Decision history (for analysis)
CREATE TABLE decisions (
    decision_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP,
    signal_type TEXT,
    decision_action TEXT,
    confidence NUMERIC(6,4),
    signal_quality_score NUMERIC(6,4),
    market_regime_score NUMERIC(6,4),
    event_risk_score NUMERIC(6,4),
    session_timing_score NUMERIC(6,4),
    position_state_score NUMERIC(6,4),
    final_score NUMERIC(6,4),
    reasoning TEXT,
    executed BOOLEAN,
    created_at TIMESTAMP
);

-- Error and discrepancy logging
CREATE TABLE error_log (
    error_id TEXT PRIMARY KEY,
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    component TEXT,
    timestamp TIMESTAMP,
    severity TEXT (CRITICAL/HIGH/MEDIUM/LOW),
    resolved BOOLEAN DEFAULT FALSE
);

-- Reconciliation reports
CREATE TABLE reconciliation_reports (
    report_id TEXT PRIMARY KEY,
    report_time TIMESTAMP,
    discrepancies_found INT,
    discrepancy_details JSONB,
    status TEXT,
    created_at TIMESTAMP
);

CREATE INDEX idx_trades_position ON trades(position_id);
CREATE INDEX idx_trades_strategy ON trades(strategy_id);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_decisions_timestamp ON decisions(timestamp);
CREATE INDEX idx_error_log_timestamp ON error_log(timestamp);
```

**TimescaleDB Hypertable:**

```sql
-- 1-minute OHLCV data (90-day retention)
CREATE TABLE ohlcv_1m (
    timestamp TIMESTAMP NOT NULL,
    symbol TEXT NOT NULL,
    open NUMERIC(15,2),
    high NUMERIC(15,2),
    low NUMERIC(15,2),
    close NUMERIC(15,2),
    volume NUMERIC(20,8)
);

SELECT create_hypertable('ohlcv_1m', 'timestamp', if_not_exists => TRUE);
SELECT add_retention_policy('ohlcv_1m', INTERVAL '90 days');

-- Aggregated daily OHLCV (2-year retention)
CREATE TABLE ohlcv_1d (
    timestamp TIMESTAMP NOT NULL,
    symbol TEXT NOT NULL,
    open NUMERIC(15,2),
    high NUMERIC(15,2),
    low NUMERIC(15,2),
    close NUMERIC(15,2),
    volume NUMERIC(20,8)
);

SELECT create_hypertable('ohlcv_1d', 'timestamp', if_not_exists => TRUE);
SELECT add_retention_policy('ohlcv_1d', INTERVAL '2 years');

-- Verification reports
CREATE TABLE verification_reports (
    timestamp TIMESTAMP NOT NULL,
    checks_run INT,
    checks_passed INT,
    discrepancies INT,
    report_data JSONB
);

SELECT create_hypertable('verification_reports', 'timestamp', if_not_exists => TRUE);
SELECT add_retention_policy('verification_reports', INTERVAL '6 months');

CREATE INDEX idx_ohlcv_1m_symbol ON ohlcv_1m(symbol, timestamp DESC);
CREATE INDEX idx_ohlcv_1d_symbol ON ohlcv_1d(symbol, timestamp DESC);
```

---

## Implementation Examples

### 1. Complete Decision Cycle Flow

```python
class IntegratedDecisionCycle:
    """
    Complete end-to-end decision cycle executed every 15-minute candle.
    Demonstrates how all components work together.
    """
    
    def __init__(
        self,
        central_intelligence: CentralIntelligenceEngine,
        decision_engine: DecisionScoringEngine,
        execution_engine: ExecutionEngine,
        state_manager: StateCheckpointManager,
        logger: Logger
    ):
        self.ci = central_intelligence
        self.decision = decision_engine
        self.execution = execution_engine
        self.state = state_manager
        self.logger = logger
    
    async def execute_15min_cycle(self) -> CycleResult:
        """
        Complete 15-minute trading cycle from signal to state persistence.
        """
        
        cycle_start = datetime.now()
        cycle_result = CycleResult(cycle_start=cycle_start)
        
        try:
            # PHASE 1: Signal Collection (T+0:00 to T+14:55)
            self.logger.info("Phase 1: Signal Collection")
            aggregated_signal = await self._collect_signals()
            cycle_result.primary_signal = aggregated_signal.primary_signal_type
            
            # PHASE 2: Market Context Assembly
            self.logger.info("Phase 2: Market Context Assembly")
            market_context = await self._assemble_market_context()
            event_risk = await self._assess_event_risk()
            cycle_result.market_regime = market_context.get('market_regime')
            
            # PHASE 3: Position Status Review
            self.logger.info("Phase 3: Position Status Review")
            active_positions = await self._get_active_positions()
            
            # PHASE 4: Decision Evaluation (at T+14:00)
            self.logger.info("Phase 4: Decision Evaluation")
            trade_decision = await self.decision.evaluate_trade_decision(
                aggregated_signal=aggregated_signal,
                market_context=market_context,
                event_risk=event_risk,
                position_state=active_positions[0] if active_positions else None,
                session_timing=await self._get_session_timing()
            )
            cycle_result.decision_action = trade_decision.action
            cycle_result.confidence = trade_decision.confidence
            
            # PHASE 5: Central Intelligence Overrides
            self.logger.info("Phase 5: Central Intelligence Processing")
            if active_positions:
                for position in active_positions:
                    override = await self.ci.evaluate_position_override(
                        position,
                        aggregated_signal,
                        market_context
                    )
                    if override.override_type != "NONE":
                        cycle_result.overrides.append(override)
                        self.logger.info(
                            f"Override applied: {override.override_type} "
                            f"(reason: {override.reasoning})"
                        )
            
            # PHASE 6: Execution (at T+14:55)
            self.logger.info("Phase 6: Order Execution")
            
            # Execute pending overrides
            for override in cycle_result.overrides:
                if override.override_type == "DCA":
                    dca_result = await self.execution.execute_dca(override)
                    cycle_result.executions.append(dca_result)
                elif override.override_type == "CLOSE":
                    close_result = await self.execution.close_position(override)
                    cycle_result.executions.append(close_result)
            
            # Execute primary decision if action indicates
            if trade_decision.action in ["EXECUTE_PRIMARY", "EXECUTE_MODIFIED"]:
                exec_result = await self.execution.execute_decision(
                    trade_decision,
                    market_context
                )
                cycle_result.executions.append(exec_result)
            
            # PHASE 7: State Persistence & Checkpoint
            self.logger.info("Phase 7: State Persistence")
            checkpoint = await self.state.create_checkpoint(
                checkpoint_type="DECISION_CYCLE"
            )
            cycle_result.checkpoint_id = checkpoint.checkpoint_id
            
            # PHASE 8: Decision Logging
            self.logger.info("Phase 8: Decision Logging")
            await self._log_decision(trade_decision)
            
            cycle_result.status = "COMPLETED"
            cycle_result.cycle_duration = (
                datetime.now() - cycle_start
            ).total_seconds()
            
        except Exception as e:
            self.logger.error(f"Cycle execution failed: {str(e)}")
            cycle_result.status = "FAILED"
            cycle_result.error = str(e)
        
        return cycle_result
    
    async def _collect_signals(self) -> AggregatedSignal:
        """Aggregate all strategy signals."""
        # Implementation calls signal ingestion engine
        pass
    
    async def _assemble_market_context(self) -> dict:
        """Gather all market context."""
        # Implementation collects dominance, fear&greed, etc
        pass
    
    async def _assess_event_risk(self) -> EconomicEventRisk:
        """Check economic calendar and Polymarket."""
        # Implementation gets event risk
        pass
```

### 2. Strategy Signal Publishing Example

```python
class ExampleStrategy:
    """
    Example strategy class for publishing signals to central repository.
    """
    
    def __init__(self, redis_client, capital_manager):
        self.redis = redis_client
        self.capital = capital_manager
        self.strategy_id = "EXAMPLE_RSI_MACD_001"
    
    async def analyze_and_signal(self, ohlcv_data: pd.DataFrame) -> None:
        """
        Analyze current bar and publish signal to repository.
        Called every 1-minute bar close.
        """
        
        # Technical analysis
        rsi = ta.momentum.rsi(ohlcv_data['close'], window=14)
        macd = ta.trend.MACD(ohlcv_data['close'])
        
        current_rsi = rsi.iloc[-1]
        current_macd = macd.macd().iloc[-1]
        current_signal_line = macd.signal().iloc[-1]
        
        # Generate signal
        signal = StrategySignal(
            strategy_id=self.strategy_id,
            signal_type="ENTRY_LONG",
            confidence=0.82,
            timestamp=datetime.now(),
            bar_index=ohlcv_data.shape[0] - 1,
            
            tp1_price=ohlcv_data['close'].iloc[-1] * 1.005,
            tp1_percent=30,
            tp2_price=ohlcv_data['close'].iloc[-1] * 1.015,
            tp2_percent=40,
            tp3_price=ohlcv_data['close'].iloc[-1] * 1.030,
            tp3_percent=30,
            trailing_stop_enabled=True,
            trailing_stop_percent=2.0,
            
            stop_loss_price=ohlcv_data['close'].iloc[-1] * 0.990,
            entry_price_target=ohlcv_data['close'].iloc[-1] + 0.50,
            
            market_regime="TRENDING_UP",
            volatility_regime="MEDIUM",
            reasoning=f"RSI={current_rsi:.1f} (oversold), MACD crossover "
                     f"(MACD={current_macd:.4f} > SL={current_signal_line:.4f})",
            
            building_blocks_contrib=["RSI_MOMENTUM_001", "MACD_TREND_001"]
        )
        
        # Publish to repository
        await self.redis.publish(
            f"signals:{self.strategy_id}",
            signal.to_json()
        )
```

---

## Performance Targets & Monitoring

### 1. Performance SLAs

| Target | Metric | Threshold | Notes |
|--------|--------|-----------|-------|
| **Recovery Time** | Gap ≤ 24 hours | < 2 minutes | Checkpoint restore + replay |
| **Recovery Time** | Gap ≤ 7 days | < 5 minutes | Historical data reconstruction |
| **Decision Latency** | Complete by | 14:55 seconds | Finalized decision deadline |
| **Verification Loop** | Exchange check | Every 30 sec | Position/order/P&L verification |
| **Signal Ingestion** | Latency | < 100 ms | Signal to repository |
| **Order Execution** | Latency | < 200 ms | Order placement to fill |
| **State Persistence** | Checkpoint creation | < 500 ms | Per decision cycle |

### 2. Monitoring Dashboard Metrics

```python
class PerformanceMonitor:
    """
    Tracks ITM performance metrics and system health.
    """
    
    @dataclass
    class SystemMetrics:
        # Decision cycle metrics
        decision_cycle_duration: float              # seconds
        signal_collection_duration: float          # seconds
        decision_evaluation_duration: float        # seconds
        execution_duration: float                   # seconds
        state_persistence_duration: float          # seconds
        
        # Signal metrics
        signals_received_per_cycle: int
        signal_convergence_average: float          # 0.0-1.0
        strategies_active: int
        
        # Execution metrics
        orders_executed_per_cycle: int
        order_fill_rate: float                      # % of orders filled
        average_slippage_percent: float
        
        # Position metrics
        positions_active: int
        positions_in_profit: int
        average_position_duration: float           # hours
        
        # Capital metrics
        total_capital_allocated: float              # USDT
        free_capital: float                         # USDT
        compounded_balance: float                   # USDT
        
        # Verification metrics
        verification_pass_rate: float               # % of checks passed
        discrepancies_per_day: int
        
        # Error metrics
        error_rate: float                           # errors per day
        critical_errors: int
        recovery_success_rate: float                # % successful restores
        
        timestamp: datetime = field(default_factory=datetime.now)
```

---

## Appendix: Data Structures

### 1. Core Type Definitions

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SignalType(Enum):
    ENTRY_LONG = "ENTRY_LONG"
    ENTRY_SHORT = "ENTRY_SHORT"
    EXIT = "EXIT"
    DCA = "DCA"
    CLOSE = "CLOSE"
    NEUTRAL = "NEUTRAL"

@dataclass
class Position:
    position_id: str
    strategy_id: str
    side: str  # LONG or SHORT
    entry_price: float
    entry_size: float
    entry_time: datetime
    current_price: float
    current_pnl: float
    current_pnl_percent: float
    tp1_price: Optional[float] = None
    tp2_price: Optional[float] = None
    tp3_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    tp1_triggered: bool = False
    tp2_triggered: bool = False
    tp3_triggered: bool = False
    trailing_stop_enabled: bool = False
    trailing_stop_percent: Optional[float] = None
    status: str = "OPEN"

@dataclass
class AggregatedSignal:
    primary_signal_type: str
    convergence_strength: float  # 0.0-1.0
    consensus_confidence: float  # 0.0-1.0
    contributing_strategies: int
    signal_age_distribution: Dict[str, float]
    dominant_market_regime: str
    timestamp: datetime

@dataclass
class TradeDecision:
    evaluation_time: datetime
    primary_signal: str
    signal_quality_score: float = 0.0
    market_regime_score: float = 0.0
    event_risk_score: float = 0.0
    session_timing_score: float = 0.0
    position_state_score: float = 0.0
    final_score: float = 0.0
    action: str = "WAIT"  # EXECUTE_PRIMARY, EXECUTE_MODIFIED, MONITOR, WAIT
    confidence: float = 0.0
    reasoning: str = ""

@dataclass
class PositionOverride:
    override_type: str  # NONE, DCA, CLOSE, ENHANCE, TIGHTEN, HOLD
    position_id: Optional[str] = None
    dca_amount_percent: Optional[float] = None
    new_stop_loss: Optional[float] = None
    new_tp1: Optional[float] = None
    new_tp2: Optional[float] = None
    new_tp3: Optional[float] = None
    enable_trailing_stop: bool = False
    trailing_stop_percent: Optional[float] = None
    close_reason: Optional[str] = None
    reasoning: str = ""
    timestamp: Optional[datetime] = None

@dataclass
class StateCheckpoint:
    checkpoint_id: str
    checkpoint_type: str
    timestamp: datetime
    active_positions: List[Position] = field(default_factory=list)
    capital_state: Dict[str, Any] = field(default_factory=dict)
    recent_signals: Dict[str, List[str]] = field(default_factory=dict)
    market_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CycleResult:
    cycle_start: datetime
    status: str = "PENDING"
    primary_signal: Optional[str] = None
    market_regime: Optional[str] = None
    decision_action: Optional[str] = None
    confidence: float = 0.0
    overrides: List[PositionOverride] = field(default_factory=list)
    executions: List[Any] = field(default_factory=list)
    checkpoint_id: Optional[str] = None
    cycle_duration: float = 0.0
    error: Optional[str] = None
```

---

## Error Handling & Logging

All system errors must be logged with:
- Error ID (unique identifier)
- Timestamp (precise moment)
- Component (which module generated error)
- Severity (CRITICAL, HIGH, MEDIUM, LOW)
- Stack trace (full context)
- Resolution status (auto-resolved or requires intervention)

**Critical Errors Requiring Immediate Alert:**
- Exchange connection loss > 30 seconds
- Position/order mismatch detected
- Capital allocation error (exceeds compounded balance)
- State checkpoint failure
- Verification loop failure > 2 consecutive cycles

---

## Conclusion

The Intelligent Trade Manager v1.5 provides a comprehensive, production-ready framework for sophisticated cryptocurrency trading with institutional-grade risk management, multi-strategy consensus, and advanced state management.

Key strengths:
1. **Modular architecture** enables easy expansion of strategies, building blocks, and intelligence modules
2. **Institutional-grade decision making** with 5-dimension scoring and multi-strategy consensus
3. **Robust state management** with sub-2-minute recovery capability
4. **Human-in-the-loop** via OpenRouter AI analysis of analyst inputs
5. **Complete market context integration** (economic calendar, predictions, dominance metrics)
6. **Aggressive optimization** of order execution with TWAP and limit order strategies
7. **Comprehensive monitoring** with 30-second verification cycles and detailed logging

Implementation can proceed immediately using provided data structures and integration examples. All 90-day and 2-year retention policies support walk-forward testing with historical data accuracy.

---

**Document End**

---

**Version History:**
- v1.0 - Initial framework specification
- v1.1 - Added human influence module with OpenRouter integration
- v1.2 - Enhanced DCA management and reversal scoring
- v1.3 - Added TWAP execution optimization and order flow analysis
- v1.4 - Comprehensive state management and recovery protocols
- v1.5 - Final production-ready specification with complete implementation examples
