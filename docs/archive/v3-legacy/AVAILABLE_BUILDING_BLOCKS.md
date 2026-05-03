# Available Building Blocks for Strategy Construction

**Date:** December 30, 2025  
**Purpose:** Comprehensive inventory of all modules, indicators, and systems available for building confluence-based trading strategies  
**Vision:** Modular system with ~16+ pattern modules + statistical/technical components that can be combined

---

## ARCHITECTURE OVERVIEW

### Modular Strategy Framework

```
┌─────────────────────────────────────────────────────────────┐
│                    STRATEGY LAYER                           │
│  (Combine multiple modules with confluence logic)           │
│                                                             │
│  Example: IF Statistical_Trend=UP AND                      │
│             Volume_Breakout=50EMA AND                       │
│             RSI=Oversold AND                                │
│             W_Pattern=Detected                              │
│           THEN LONG_ENTRY                                   │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │
         ┌─────────────────┴──────────────────┐
         │                                     │
┌────────▼─────────┐              ┌───────────▼──────────┐
│  PATTERN MODULES │              │ TECHNICAL COMPONENTS │
│  (16+ modules)   │              │  (+indicators)       │
└──────────────────┘              └──────────────────────┘
```

---

## PATTERN MODULES (Current + Planned)

### Currently Implemented ✅

**1. M-Pattern Module**
- **File:** `src/strategies/m_pattern_strategy.py`, `src/indicators/pattern_adapter.py`
- **Type:** Geometric reversal pattern
- **Signal:** SHORT on M-pattern completion
- **Confidence:** 65-95% based on pattern quality
- **Entry:** Current price when pattern detected
- **Stop Loss:** Above peaks
- **Take Profit:** Below neckline (multiple targets)
- **Status:** Production ready (not backtested)

**2. W-Pattern Module**
- **File:** `src/strategies/w_pattern_strategy.py`, `src/indicators/pattern_adapter.py`
- **Type:** Geometric reversal pattern
- **Signal:** LONG on W-pattern completion
- **Confidence:** 65-95% based on pattern quality
- **Entry:** Current price when pattern detected
- **Stop Loss:** Below troughs
- **Take Profit:** Above neckline (multiple targets)
- **Status:** Production ready (not backtested)

**3. Statistical Pivot Pattern Module**
- **Files:** `src/detectors/pattern_encoder.py`, `src/detectors/pattern_statistics.py`
- **Type:** 48-pattern statistical classification
- **Signal:** Predict next pivot direction (HH/LH)
- **Confidence:** Based on historical probability (50-70%)
- **Entry:** When probability >55% + divergence filter
- **Status:** Backtested (53.8% win rate, improving)

### Planned Pattern Modules (15 more to build)

**4. Head & Shoulders Pattern**
- Type: Reversal pattern
- Signal: SHORT on neckline break
- Components needed: Pivot detection, neckline, volume confirmation

**5. Inverse Head & Shoulders Pattern**
- Type: Reversal pattern  
- Signal: LONG on neckline break
- Components needed: Pivot detection, neckline, volume confirmation

**6. Double Top Pattern**
- Type: Reversal pattern
- Signal: SHORT on second peak rejection
- Components needed: Similar to M-pattern (simplified)

**7. Double Bottom Pattern**
- Type: Reversal pattern
- Signal: LONG on second trough bounce
- Components needed: Similar to W-pattern (simplified)

**8. Triple Top Pattern**
- Type: Strong reversal pattern
- Signal: SHORT after third rejection
- Components needed: Extended M-pattern logic

**9. Triple Bottom Pattern**
- Type: Strong reversal pattern
- Signal: LONG after third bounce
- Components needed: Extended W-pattern logic

**10. Ascending Triangle**
- Type: Bullish continuation
- Signal: LONG on breakout above resistance
- Components needed: Trend lines, breakout detection

**11. Descending Triangle**
- Type: Bearish continuation
- Signal: SHORT on breakdown below support
- Components needed: Trend lines, breakdown detection

**12. Symmetrical Triangle**
- Type: Continuation pattern (direction-neutral)
- Signal: Trade breakout direction
- Components needed: Converging trend lines

**13. Flag Pattern (Bullish/Bearish)**
- Type: Continuation pattern
- Signal: Trade in trend direction after consolidation
- Components needed: Pole + flag detection, parallel channels

**14. Pennant Pattern**
- Type: Continuation pattern
- Signal: Trade breakout direction
- Components needed: Similar to symmetrical triangle (smaller)

**15. Wedge Patterns (Rising/Falling)**
- Type: Reversal patterns
- Signal: Rising wedge = bearish, Falling wedge = bullish
- Components needed: Converging trend lines with slope

**16. Cup & Handle Pattern**
- Type: Bullish continuation
- Signal: LONG on handle breakout
- Components needed: Rounded bottom + consolidation detection

**17. Rounding Bottom/Top**
- Type: Reversal pattern
- Signal: LONG (bottom) or SHORT (top)
- Components needed: Curve fitting, volume analysis

**18. Diamond Pattern**
- Type: Reversal pattern
- Signal: Trade breakout direction
- Components needed: Expanding then contracting range

---

## TECHNICAL COMPONENTS (Indicators & Systems)

### Currently Implemented ✅

**1. Zigzag Pivot Detector**
- **File:** `src/detectors/zigzag_detector.py`
- **Function:** Finds pivot highs and lows
- **Parameters:** Length (bars each side for pivot)
- **Output:** List of Pivot objects with price, index, type, oscillator value
- **Use Cases:** All pattern detection, trend analysis, support/resistance

**2. RSI Oscillator**
- **File:** `src/detectors/oscillators.py` (calculate_rsi)
- **Function:** Relative Strength Index calculation
- **Parameters:** Length (default 14)
- **Output:** RSI values (0-100)
- **Use Cases:** Divergences, overbought/oversold, statistical patterns

**3. Pattern Encoder (48 patterns)**
- **File:** `src/detectors/pattern_encoder.py`
- **Function:** Encodes 3-pivot sequences into pattern index
- **Components:** Trend + Price momentum + RSI divergence
- **Output:** Pattern index 0-47 with metadata
- **Use Cases:** Statistical prediction, divergence detection

**4. Pattern Statistics System**
- **File:** `src/detectors/pattern_statistics.py`
- **Function:** Tracks historical outcomes for each pattern
- **Metrics:** Win rate, Fibonacci ratios, bar counts
- **Output:** Predictions with probabilities
- **Use Cases:** Probability-based entries, confluence validation

**5. Volume Analyzer (needs revision)**
- **File:** `src/detectors/volume_analyzer.py`
- **Function:** Volume state classification (CLIMAX/HIGH/NORMAL/LOW)
- **Note:** Current logic needs crypto-specific adjustments
- **Use Cases:** Volume confirmation, institutional activity detection

**6. Divergence Detector**
- **File:** `src/detectors/divergence_detector.py`
- **Function:** Detects price/oscillator divergences
- **Types:** Regular, Hidden, Bullish, Bearish
- **Use Cases:** Pattern filtering, entry confirmation

### Available to Implement (From Resources)

**7. VWAP (Volume Weighted Average Price)**
- **Research:** Anchored VWAP institutional trading
- **Function:** Fair value line, institutional reference
- **Use Cases:** Entry/exit near VWAP, breakout trades
- **Implementation:** TradingView has built-in, can replicate

**8. Anchored VWAP**
- **Function:** VWAP from specific event (pivot, gap, news)
- **Use Cases:** Track institutional accumulation/distribution
- **Implementation:** 2-3 hours

**9. EMA (Exponential Moving Average)**
- **Lengths:** 20, 50, 200 (standard institutional levels)
- **Use Cases:** Trend direction, dynamic support/resistance, breakout confirmation
- **Example Strategy:** 50 EMA break + retest + RSI oversold = LONG
- **Implementation:** 30 minutes (simple)

**10. Volume Profile**
- **Research:** 90% reaction rate at key levels (University of Lodz)
- **Function:** Horizontal volume distribution shows POC, VAH, VAL
- **Use Cases:** Support/resistance, fair value areas
- **Implementation:** 4-6 hours (complex)

**11. Order Flow Imbalance (OFI)**
- **Research:** 60% forecast improvement (ScienceDirect)
- **Function:** Buy vs sell pressure at each level
- **Use Cases:** Institutional activity, reversal signals
- **Implementation:** 6-8 hours (requires order book data)

**12. Market Depth Analysis**
- **Research:** 60% price impact prediction
- **Function:** Bid/ask depth at price levels
- **Use Cases:** Liquidity analysis, support/resistance
- **Implementation:** 4-6 hours (requires Level 2 data)

**13. Supply & Demand Zones**
- **Research:** Institutional trading zones
- **Function:** Areas where large orders accumulated/distributed
- **Use Cases:** High-probability reversal areas
- **Implementation:** 3-4 hours

**14. Break of Structure (BOS) Detector**
- **Research:** Smart Money Concepts, ICT method
- **Function:** Detects when market structure shifts
- **Use Cases:** Trend change confirmation, entry timing
- **Implementation:** 2-3 hours

**15. Liquidity Pool Detector**
- **Function:** Identifies stop-loss clusters above/below key levels
- **Use Cases:** Anticipate stop hunts, reversal zones
- **Implementation:** 3-4 hours

**16. Fibonacci Retracements**
- **Research:** 60% success rate (UPV 2021), profitable in energy/crypto
- **Levels:** 23.6%, 38.2%, 50%, 61.8%, 78.6%
- **Use Cases:** Pullback entries, target levels
- **Implementation:** 1-2 hours

**17. Harmonic Patterns (Gartley, Butterfly, Bat, Crab)**
- **Research:** 80-90% accuracy (LiteFinance)
- **Function:** Fibonacci-based geometric patterns
- **Use Cases:** High-probability reversal zones
- **Implementation:** 6-8 hours each pattern

**18. MACD (Moving Average Convergence Divergence)**
- **Research:** 73% win rate with RSI (Quantified Strategies)
- **Function:** Trend and momentum indicator
- **Use Cases:** Divergences, trend confirmation
- **Implementation:** 1 hour

**19. Ichimoku Cloud**
- **Research:** 11 citations, profitable in Vietnam market
- **Components:** Tenkan, Kijun, Senkou A/B, Chikou
- **Use Cases:** Trend, support/resistance, momentum
- **Implementation:** 2-3 hours

**20. Wyckoff Accumulation/Distribution Phases**
- **Research:** Institutional accumulation/distribution framework
- **Phases:** Spring, Test, Markup (accumulation); Upthrust, Distribution
- **Use Cases:** Detect institutional positioning
- **Implementation:** 4-6 hours

**21. ADX (Average Directional Index)**
- **Function:** Trend strength measurement
- **Use Cases:** Filter weak vs strong trends
- **Implementation:** 1 hour

**22. ATR (Average True Range)**
- **Function:** Volatility measurement
- **Use Cases:** Position sizing, stop loss placement
- **Implementation:** 30 minutes

**23. Bollinger Bands**
- **Function:** Volatility bands around moving average
- **Use Cases:** Overbought/oversold, squeeze setups
- **Implementation:** 1 hour

---

## CONFLUENCE STRATEGY FRAMEWORK

### How to Combine Modules

**Example 1: EMA Breakout + Statistical Confirmation**
```python
class EMA_Statistical_Strategy(Strategy):
    def on_bar(self, bar):
        # Component 1: Statistical trend classification
        pattern = pattern_encoder.encode(p1, p2, p3)
        trend = pattern_statistics.get_trend(pattern)  # UP, SIDEWAYS, DOWN
        
        # Component 2: EMA breakout
        ema_50 = calculate_ema(bars, 50)
        volume_breakout = bar.volume > avg_volume * 1.5
        price_above_ema = bar.close > ema_50
        
        # Component 3: RSI oversold
        rsi = calculate_rsi(bars, 14)
        rsi_oversold = rsi < 30
        
        # Component 4: Retest confirmation
        retesting = previous_bar.close < ema_50 and bar.close > ema_50
        
        # CONFLUENCE: All conditions must align
        if (trend == 'UP' and 
            volume_breakout and 
            price_above_ema and 
            rsi_oversold and 
            retesting):
            
            → ENTER LONG (high confidence)
```

**Example 2: M-Pattern + Statistical Validation**
```python
class M_Pattern_Enhanced_Strategy(Strategy):
    def on_bar(self, bar):
        # Component 1: M-pattern detection
        m_signal = m_pattern_detector.detect(bars)
        
        if m_signal.pattern_type == 'M':
            # Component 2: Statistical validation
            pattern = encoder.encode(p1, p2, p3)
            stats = pattern_statistics.predict(pattern)
            
            # Component 3: Volume confirmation
            vol_state = volume_analyzer.get_state(bar)
            
            # Component 4: Fibonacci level
            at_fib_level = check_fibonacci_level(bar.close, swing_high, swing_low)
            
            # CONFLUENCE
            if (m_signal.confidence >= 70% and 
                stats.lh_probability > 60% and 
                vol_state in ['HIGH', 'CLIMAX'] and 
                at_fib_level):
                
                → ENTER SHORT (very high confidence)
```

**Example 3: Supply Zone + BOS + Liquidity Pool**
```python
class Supply_BOS_Strategy(Strategy):
    def on_bar(self, bar):
        # Component 1: Supply zone detection
        in_supply_zone = supply_demand.check_supply_zone(bar.close)
        
        # Component 2: Break of Structure
        bos_detected = bos_detector.check_bearish_bos(bars)
        
        # Component 3: Liquidity pool above
        liquidity_above = liquidity_detector.find_pools_above(bar.close)
        
        # Component 4: Statistical bearish divergence
        pattern = encoder.encode(p1, p2, p3)
        is_bearish_div = pattern in [44, 45]  # Regular bearish divergence
        
        # CONFLUENCE
        if (in_supply_zone and 
            bos_detected and 
            liquidity_above and 
            is_bearish_div):
            
            → ENTER SHORT (hunt liquidity then reverse)
```

---

## MODULAR COMPONENT LIBRARY

### Data Structures

**1. Pivot Class**
```python
@dataclass
class Pivot:
    index: int           # Position in dataframe
    price: float         # Pivot price
    pivot_type: PivotType  # HIGH or LOW
    oscillator_value: Optional[float]  # RSI at pivot
    timestamp: datetime  # When pivot occurred
    volume: Optional[float]  # Volume at pivot
```

**2. PatternSignal Class**
```python
@dataclass
class PatternSignal:
    pattern_type: str    # 'M', 'W', 'none', etc.
    direction: str       # 'long', 'short', 'neutral'
    confidence: float    # 0.0 to 1.0
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float]
    take_profit_3: Optional[float]
    metadata: Optional[Dict]  # Additional context
```

**3. StatisticalPrediction Class**
```python
@dataclass
class StatisticalPrediction:
    pattern_index: int
    lh_probability: float
    hh_probability: float
    sample_count: int
    avg_fib_ratio: float
    avg_bars_to_next: float
    confidence: str  # 'LOW', 'MEDIUM', 'HIGH'
```

### Detector Interfaces

**All detectors follow consistent interface:**
```python
class DetectorInterface:
    def detect(self, data) -> Signal:
        """Detect pattern/signal in data"""
        pass
    
    def validate(self, signal) -> bool:
        """Validate signal quality"""
        pass
    
    def get_confidence(self, signal) -> float:
        """Calculate confidence score"""
        pass
```

---

## IMPLEMENTATION PRIORITY

### Phase 1: Core Components (Current Session)
- [x] M/W patterns
- [x] Statistical pivot system  
- [x] RSI
- [x] Volume analyzer (needs revision)
- [ ] Iteration 2: Simplify statistical patterns (IN PROGRESS)

### Phase 2: Essential Indicators (Week 1)
- [ ] EMA (20, 50, 200)
- [ ] VWAP + Anchored VWAP
- [ ] MACD
- [ ] Fibonacci retracements
- [ ] ATR for position sizing

### Phase 3: Advanced Patterns (Week 2)
- [ ] Head & Shoulders
- [ ] Double Top/Bottom
- [ ] Triangle patterns
- [ ] Flag/Pennant patterns

### Phase 4: Institutional Components (Week 3)
- [ ] Supply/Demand zones
- [ ] Break of Structure detector
- [ ] Liquidity pool detection
- [ ] Order flow imbalance (if data available)
- [ ] Volume profile

### Phase 5: Harmonic Patterns (Week 4)
- [ ] Gartley pattern
- [ ] Butterfly pattern
- [ ] Bat pattern
- [ ] Crab pattern

### Phase 6: Advanced Systems (Week 5+)
- [ ] Wyckoff analysis
- [ ] Ichimoku Cloud
- [ ] Market microstructure
- [ ] Sentiment analysis (if applicable)

---

## CONFLUENCE STRATEGY TEMPLATES

### Template 1: Trend Following with Confluence
```python
Components:
├── Statistical trend (UP/DOWN)
├── 50 EMA alignment
├── MACD bullish/bearish
├── RSI not extreme
└── Volume confirmation

Entry: All align → Trade with trend
Win Rate Target: 60-65%
```

### Template 2: Reversal with Multiple Confirmations
```python
Components:
├── M or W pattern detected
├── Statistical divergence pattern (44-45 or 2-3)
├── At Fibonacci level (61.8% or 78.6%)
├── Volume climax
└── RSI extreme (>70 or <30)

Entry: 3+ conditions → Reversal trade
Win Rate Target: 70-75%
```

### Template 3: Breakout with Institutional Validation
```python
Components:
├── Supply/Demand zone
├── Break of Structure
├── Liquidity pool above/below
├── Statistical trend aligned
└── Volume breakout

Entry: BOS + liquidity sweep → Trade
Win Rate Target: 65-70%
```

### Template 4: Harmonic + Statistical
```python
Components:
├── Harmonic pattern (Gartley, Butterfly, etc.)
├── Statistical prediction aligned
├── RSI divergence
├── VWAP support/resistance
└── Fibonacci confluence

Entry: Harmonic complete + confluence → Trade
Win Rate Target: 75-80%
```

---

## RESEARCH RESOURCES MAPPED TO COMPONENTS

### From TRADING_QUANT_ML_RESOURCES.md

**Order Flow & Market Microstructure:**
- Papers: 7+ academic PDFs
- Use for: Institutional activity detection, order flow imbalance
- Priority: High (60% forecast improvement documented)

**Volume Profile:**
- Papers: University of Lodz (90% WIG20 reaction)
- Use for: POC, VAH, VAL support/resistance
- Priority: High (institutional reference)

**Wyckoff Method:**
- Resources: 6+ comprehensive guides
- Use for: Accumulation/distribution phase detection
- Priority: Medium (institutional positioning)

**Break of Structure:**
- Resources: MQL5, FXOpen, Flux Charts guides
- Use for: Trend change detection, smart money concepts
- Priority: High (institutional order flow)

**Supply & Demand Zones:**
- Resources: 6+ practical guides
- Use for: Institutional price levels
- Priority: High (reversal zones)

**Fibonacci Retracements:**
- Papers: UPV 2021, PMC 2022 (profitable in crypto)
- Use for: Pullback entries, target levels
- Priority: High (proven profitable)

**Harmonic Patterns:**
- Resources: StockCharts, NAGA, LiteFinance (80-90% accuracy)
- Use for: High-probability reversals
- Priority: Medium-High (complex but effective)

**VWAP:**
- Resources: Quantified Strategies, TrendSpider guides
- Use for: Institutional reference, mean reversion
- Priority: High (simple, effective)

**RSI & MACD:**
- Papers: ITB Wigalumajang (RSI 97% accuracy), SSRN optimization
- Strategies: 73% win rate documented (Quantified Strategies)
- Priority: High (already implemented RSI, add MACD)

**Ichimoku Cloud:**
- Papers: PMC 2022 (11 citations, profitable)
- Use for: All-in-one trend/support/momentum
- Priority: Medium (complex indicator)

**Machine Learning:**
- Papers: Deep learning reviews, reinforcement learning
- Use for: Pattern recognition optimization, strategy optimization
- Priority: Low (future advanced features)

---

## NEXT STEPS

### Immediate (This Session):
1. ✅ Document all building blocks (this file)
2. Continue Iteration 2: Simplify statistical patterns (48 → 8)
3. Target: 53.8% → 58-60% win rate

### Short-term (This Week):
1. Complete Iterations 2-6 on statistical system
2. Target: 65-70% win rate
3. Prepare for M/W pattern backtesting

### Medium-term (Next 2 Weeks):
1. Backtest M/W patterns independently
2. Implement EMA, VWAP, MACD, Fibonacci
3. Create first confluence strategy (M-pattern + Statistical + Volume)

### Long-term (Month 1-2):
1. Build remaining 13 pattern modules
2. Implement institutional components (Supply/Demand, BOS, Liquidity)
3. Create comprehensive confluence framework
4. Target: 75-80% win rate with full confluence

---

## SUMMARY

**Available Now:**
- 3 pattern detection systems (M, W, Statistical-48)
- 6 technical components (Zigzag, RSI, Encoder, Statistics, Volume, Divergence)
- 2 production strategies (NautilusTrader ready)
- 1 research backtest (Custom Python)

**Ready to Implement (Resources Available):**
- 15+ additional pattern modules
- 20+ technical indicators
- Institutional components (Order flow, Volume profile, Supply/Demand)
- Harmonic patterns (4 types)
- Advanced systems (Wyckoff, Ichimoku, ML)

**Framework Capability:**
- ✅ Modular architecture
- ✅ Composable components
- ✅ Confluence-based strategies
- ✅ Institutional-grade research backing
- ✅ Clear implementation roadmap

**Next Action:**
🚀 Continue Iteration 2 - Simplify statistical patterns for robust foundation

---

**Document Status:** COMPLETE - All building blocks documented  
**Purpose:** Reference for future development and strategy composition  
**Maintained:** Living document, update as new components added
