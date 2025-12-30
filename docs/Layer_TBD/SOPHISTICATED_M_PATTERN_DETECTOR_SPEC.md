# Sophisticated M-Pattern Detector Implementation Specification

**Branch**: `M_Pattern_Detector`  
**Base Commit**: `09e2f96` (TBD Corrective Action Complete)  
**Date**: December 30, 2025  
**Status**: Ready for Full Rebuild (Option C)

---

## Executive Summary

### Problem Identified
Current M-Pattern detector achieves correct **detection count** (43 trades/month matching manual) but is **unprofitable** (-0.66% vs user's +75-300% manual trading). Root cause: Using simple scipy peak detection instead of sophisticated TradingView methodology.

### Solution Required
Build institutional-grade M-Pattern detector mirroring user's proven TradingView methodology:
- **Zigzag structure** (not simple peaks)
- **Divergence analysis** (price vs oscillator)
- **Statistical pattern matching** (HH/LH/LL/HL probabilities)
- **Projected pivot levels** (Fibonacci ratios)
- **Multi-timeframe support**

---

## Current State (What We Have)

### Files Created
```
src/layers/tbd_v2/
├── __init__.py
├── base_tbd_pattern.py          # Base class for all patterns
├── m_pattern_layer.py            # Current simple M-pattern (detection mode)
└── w_pattern_layer.py            # W-pattern mirror (LONG trades)

scripts/optimization/
├── run_m_pattern_v2_profit_optimizer.py    # Multiprocessing optimizer
└── run_w_pattern_v2_profit_optimizer.py    # W-pattern optimizer

TradingView_Scripts/
├── pivot_points_detector.pine                      # Ghost levels + pivots
├── next_pivot_projection.pine                      # Statistical projection
├── pivot_points_high_low_multi_time_frame.pine    # Multi-TF pivots
└── pivots_fibonacci_retracement_study.pine        # Fibonacci analysis
```

### Current Detection Results
**December 1-20, 2025 Test**:
- **Trades**: 29 (43/month projected) ✅ Matches manual count
- **Win Rate**: 51.7% ❌ Barely break-even
- **Profit Factor**: 0.95 ❌ Below 1.0 (losing)
- **Total Profit**: -0.66% ❌ LOSING
- **Parameters**: `peak_tolerance=0.25, length=5-100, no volume filter`

### Gap Analysis
| Aspect | Current (Simple) | User's TradingView | Required |
|--------|------------------|-------------------|----------|
| Peak Detection | scipy.signal | Zigzag structure | **Zigzag** |
| Divergence | None | Price vs RSI/CCI | **Add divergence** |
| Pattern Stats | None | 64x3 HH/LH matrix | **Add statistics** |
| Projection | Fixed TPs | Fib ratio projection | **Add projection** |
| Multi-TF | Single | Multiple TFs | **Add multi-TF** |
| Ghost Levels | None | Tracks missed pivots | **Add ghosts** |

---

## TradingView Methodology (User's Proven Approach)

### 1. Zigzag Foundation (`pivot_points_detector.pine`)

**Key Concepts**:
- **Not simple peaks**: Uses `ta.pivothigh(length, length)` which requires confirmation
- **Structural pivots**: Only significant swings (filters noise)
- **Ghost levels** 👻: Tracks "missed pivots" (failed reversal attempts)
- **Oscillator state tracking**: Monitors trend direction changes

**Pine Code Pattern**:
```pine
length = input(50, 'Pivot Length')
ph = ta.pivothigh(length, length)  // Requires length bars on each side
pl = ta.pivotlow(length, length)

// Track max/min between pivots
max := math.max(high[length], max)
min := math.min(low[length], min)

// "Ghost" pivot when new extreme before confirmed pivot
if max > max[1] and no_pivot_confirmed:
    mark_ghost_level(max)  // This becomes resistance
```

**Python Equivalent Needed**:
```python
class ZigzagDetector:
    def __init__(self, length=50, threshold_percent=2.0):
        self.length = length
        self.threshold = threshold_percent / 100
        self.pivots = []  # List of (index, price, type)
        self.ghost_levels = []  # Missed reversals
    
    def update(self, data):
        # Find confirmed pivots (need length bars on each side)
        for i in range(self.length, len(data) - self.length):
            if self._is_pivot_high(data, i):
                self.pivots.append((i, data['high'][i], 'H'))
            elif self._is_pivot_low(data, i):
                self.pivots.append((i, data['low'][i], 'L'))
```

### 2. Statistical Pattern Matching (`next_pivot_projection.pine`)

**Revolutionary Concept**: Builds 64x3 matrix of historical outcomes!

**How It Works**:
1. **Pattern Classification**: Each pivot sequence gets indexed 0-63
   - Trend: Up(0) or Down(1) → bit 1
   - Price: HH(1) or LH(0) → bit 2  
   - Oscillator: HH(1) or LH(0) → bit 3
   - Example: U-HH/HH = 0*4 + 1*2 + 1*1 = 3

2. **Outcome Tracking**: After pattern X, track what happens:
   - Column 0: Higher High count
   - Column 1: Lower High count
   - Column 2: Total count
   
3. **Projection**: When pattern X detected now:
   - Probability: `HH_count / Total`
   - Fib Ratio: `average(price_ratios for all HH outcomes)`
   - Expected Bars: `average(bar_counts for all HH outcomes)`

**Pine Code Pattern**:
```pine
var pivotHighStats = matrix.new<int>(64, 3, 0)
var pivotHighRatios = matrix.new<float>(64, 3, 0)

trendIndex = gettrendindex(priceDir, oscDir, trendDir)
totalIndex = lastTrendIndex*8 + llastTrendIndex

// Update statistics when pivot confirms
if changePriceDirection:
    increment(pivotHighStats, totalIndex, colLast)
    increment(pivotHighRatios, totalIndex, colLast, priceRatio)

// Project next pivot
hhStats = matrix.get(pivotHighStats, totalIndex, 0)
tStats = matrix.get(pivotHighStats, totalIndex, 2)
hhProbability = hhStats / tStats
hhRatio = matrix.get(pivotHighRatios, totalIndex, 0) / hhStats
```

**Python Equivalent Needed**:
```python
class PatternStatistics:
    def __init__(self):
        # 64 possible pattern combinations
        self.pivot_high_stats = np.zeros((64, 3))  # [pattern][HH/LH/Total]
        self.pivot_high_ratios = np.zeros((64, 3))  # Average Fib ratios
        self.pivot_high_bars = np.zeros((64, 3))   # Average bar counts
        
        self.pivot_low_stats = np.zeros((64, 3))
        self.pivot_low_ratios = np.zeros((64, 3))
        self.pivot_low_bars = np.zeros((64, 3))
    
    def get_pattern_index(self, price_dir, osc_dir, trend_dir):
        """Encode pattern to 0-63 index"""
        trend_bit = 0 if trend_dir > 0 else 1
        price_bit = 1 if abs(price_dir) > 1 else 0
        osc_bit = 1 if abs(osc_dir) > 1 else 0
        return trend_bit * 4 + price_bit * 2 + osc_bit
    
    def update_outcome(self, pattern_index, outcome_type, fib_ratio, bars):
        """Track historical outcome"""
        col = 0 if outcome_type == 'HH' else 1
        self.pivot_high_stats[pattern_index, col] += 1
        self.pivot_high_ratios[pattern_index, col] += fib_ratio
        self.pivot_high_bars[pattern_index, col] += bars
        # Update total
        self.pivot_high_stats[pattern_index, 2] += 1
        self.pivot_high_ratios[pattern_index, 2] += fib_ratio
        self.pivot_high_bars[pattern_index, 2] += bars
    
    def predict_next_pivot(self, pattern_index):
        """Get probability + Fib ratio + expected bars"""
        hh_count = self.pivot_high_stats[pattern_index, 0]
        lh_count = self.pivot_high_stats[pattern_index, 1]
        total = self.pivot_high_stats[pattern_index, 2]
        
        if total == 0:
            return 0.50, 1.0, 10  # Default
        
        hh_prob = hh_count / total
        lh_prob = lh_count / total
        
        # Get dominant outcome
        if hh_prob > lh_prob:
            avg_ratio = self.pivot_high_ratios[pattern_index, 0] / hh_count
            avg_bars = self.pivot_high_bars[pattern_index, 0] / hh_count
            return hh_prob, avg_ratio, int(avg_bars)
        else:
            avg_ratio = self.pivot_high_ratios[pattern_index, 1] / lh_count
            avg_bars = self.pivot_high_bars[pattern_index, 1] / lh_count
            return lh_prob, avg_ratio, int(avg_bars)
```

### 3. Divergence Analysis

**Concept**: Price makes HH but RSI makes LH = Bearish divergence (high probability reversal)

**Required Oscillators**:
- RSI (most common)
- CCI
- CMO
- MFI
- ROC

**Python Implementation**:
```python
class DivergenceDetector:
    def __init__(self, oscillator='rsi', length=14):
        self.osc_type = oscillator
        self.length = length
    
    def calculate_oscillator(self, data):
        if self.osc_type == 'rsi':
            return ta.rsi(data['close'], self.length)
        # Add others...
    
    def check_divergence(self, price_pivots, osc_data):
        """
        Compare last 2 price pivots to oscillator pivots
        
        Returns:
            +2: Strong bullish divergence (price LL, osc HL)
            +1: Weak bullish divergence
            -1: Weak bearish divergence
            -2: Strong bearish divergence (price HH, osc LH)
            0: No divergence
        """
        if len(price_pivots) < 2:
            return 0
        
        p1_idx, p1_price, p1_type = price_pivots[-2]
        p2_idx, p2_price, p2_type = price_pivots[-1]
        
        if p1_type != p2_type:
            return 0  # Need same type
        
        p1_osc = osc_data[p1_idx]
        p2_osc = osc_data[p2_idx]
        
        if p1_type == 'H':  # Pivot highs
            price_dir = 1 if p2_price > p1_price else -1  # HH or LH
            osc_dir = 1 if p2_osc > p1_osc else -1
            
            if price_dir == 1 and osc_dir == -1:
                return -2  # Bearish divergence (strong signal!)
            elif price_dir == -1 and osc_dir == 1:
                return -1  # Hidden bearish
        
        # Similar for lows...
        return 0
```

### 4. Multi-Timeframe Support

**Concept**: Higher timeframe pivots are stronger support/resistance

**Pine Pattern**:
```pine
timeframe = input.timeframe('240')  // 4h
[ph, pl] = request.security(syminfo.tickerid, timeframe, get_phpl())
```

**Python Implementation**:
```python
class MultiTimeframeDetector:
    def __init__(self, base_tf='15m', higher_tfs=['1h', '4h']):
        self.base_tf = base_tf
        self.higher_tfs = higher_tfs
        self.detectors = {}
        
        for tf in [base_tf] + higher_tfs:
            self.detectors[tf] = ZigzagDetector()
    
    def update(self, data_dict):
        """data_dict: {'15m': df, '1h': df, '4h': df}"""
        pivots = {}
        for tf, data in data_dict.items():
            pivots[tf] = self.detectors[tf].update(data)
        return pivots
    
    def check_alignment(self, pivots):
        """Check if all timeframes agree on pattern"""
        # If 15m shows M-pattern AND 1h shows downtrend = strong
        pass
```

---

## Implementation Plan (Option C - Full Rebuild)

### Phase 1: Zigzag Foundation (Day 1: 8-10 hours)

**Goals**:
- Replace scipy peak detection with zigzag structure
- Implement pivot confirmation (requires N bars on each side)
- Track ghost levels (missed pivots)

**Files to Create**:
```
src/layers/tbd_v2/detectors/
├── __init__.py
├── zigzag_detector.py          # Core zigzag logic
├── pivot_detector.py           # Pivot confirmation
└── ghost_level_tracker.py      # Missed pivot tracking
```

**Key Classes**:
```python
# zigzag_detector.py
class ZigzagDetector:
    def __init__(self, length=50, threshold=2.0):
        pass
    
    def find_pivots(self, data) -> List[Pivot]:
        """Return confirmed structural pivots"""
        pass
    
    def get_ghost_levels(self) -> List[GhostLevel]:
        """Return missed reversal levels"""
        pass
    
    def get_pattern_sequence(self) -> List[str]:
        """Return ['HH', 'LH', 'LL'] etc."""
        pass
```

**Testing**:
- Compare against TradingView pivot detection
- Verify ghost levels match user's charts
- Validate pattern sequences

### Phase 2: Divergence Analysis (Day 1-2: 6-8 hours)

**Goals**:
- Calculate multiple oscillators (RSI, CCI, CMO, MFI)
- Detect price/oscillator divergence at pivots
- Classify divergence strength

**Files to Create**:
```
src/layers/tbd_v2/detectors/
├── oscillators.py              # RSI, CCI, CMO, MFI, ROC
└── divergence_detector.py      # Divergence analysis
```

**Key Classes**:
```python
# divergence_detector.py
class DivergenceDetector:
    def __init__(self, oscillator='rsi', length=14):
        pass
    
    def detect(self, price_pivots, osc_data) -> DivergenceSignal:
        """
        Returns:
            type: 'regular_bearish', 'hidden_bearish', etc.
            strength: -2 to +2
            probability_impact: How much this affects trade probability
        """
        pass
```

**Testing**:
- Verify divergence detected matches TradingView
- Test on known divergence examples
- Validate probability adjustments

### Phase 3: Statistical Pattern Matcher (Day 2-3: 10-12 hours)

**Goals**:
- Build 64x3 outcome matrices (like TradingView)
- Track HH/LH/LL/HL probabilities
- Calculate Fibonacci ratio projections
- Predict next pivot location

**Files to Create**:
```
src/layers/tbd_v2/detectors/
├── pattern_statistics.py       # 64x3 matrix tracking
├── pattern_encoder.py          # Pattern → index conversion
└── pivot_projector.py          # Future pivot prediction
```

**Key Classes**:
```python
# pattern_statistics.py
class PatternStatistics:
    def __init__(self):
        self.pivot_high_stats = np.zeros((64, 3))
        self.pivot_high_ratios = np.zeros((64, 3))
        self.pivot_high_bars = np.zeros((64, 3))
        # Same for lows
    
    def train(self, historical_data):
        """Build statistics from historical zigzag"""
        pass
    
    def predict(self, current_pattern) -> PivotProjection:
        """
        Returns:
            hh_probability: 0-100%
            lh_probability: 0-100%
            avg_fib_ratio: e.g., 1.618
            expected_bars: e.g., 12
        """
        pass
```

**Data Requirements**:
- Need 1year+ historical zigzag data for training
- Build initial statistics database
- Save/load for reuse

**Testing**:
- Compare projection accuracy to TradingView
- Backtest on known patterns
- Validate Fibonacci ratios

### Phase 4: Sophisticated M-Pattern Detector (Day 3-4: 8-10 hours)

**Goals**:
- Integrate all components
- Detect M-patterns using zigzag structure
- Apply divergence filters
- Use statistical probability thresholds
- Project target levels

**Files to Create/Modify**:
```
src/layers/tbd_v2/
├── sophisticated_m_pattern_layer.py    # New sophisticated detector
└── pattern_config.py                    # Configuration for all detectors
```

**Key Logic**:
```python
class SophisticatedMPatternDetector(BaseTBDPattern):
    def __init__(self, config):
        self.zigzag = ZigzagDetector(length=config.pivot_length)
        self.divergence = DivergenceDetector(osc=config.oscillator)
        self.statistics = PatternStatistics()
        self.statistics.load(config.stats_file)  # Pre-trained
    
    def detect(self, data):
        # 1. Get zigzag pivots
        pivots = self.zigzag.find_pivots(data)
        
        # 2. Check for M-structure (2 highs around same level)
        m_pattern = self._find_m_structure(pivots)
        if not m_pattern:
            return None
        
        # 3. Check divergence
        osc_data = self.divergence.calculate_oscillator(data)
        divergence = self.divergence.detect(pivots, osc_data)
        
        # 4. Get pattern sequence
        sequence = self.zigzag.get_pattern_sequence()
        pattern_index = self.statistics.encode_pattern(sequence)
        
        # 5. Get statistical projection
        projection = self.statistics.predict(pattern_index)
        
        # 6. Apply probability threshold
        if projection.hh_probability > 0.60:  # 60% HH probability
            return None  # Don't trade, likely to go higher
        
        if projection.lh_probability < 0.55:  # Less than 55% LH
            return None  # Not confident enough
        
        # 7. Adjust probability based on divergence
        if divergence.type == 'regular_bearish':
            projection.lh_probability += 0.15  # Boost confidence
        
        # 8. Calculate entry/targets
        entry = m_pattern.neckline_break_level
        sl = m_pattern.highest_peak + atr * 1.5
        
        # Use projected Fibonacci ratio for targets
        height = m_pattern.height
        tp1 = entry - height * projection.avg_fib_ratio * 0.5
        tp2 = entry - height * projection.avg_fib_ratio * 1.0
        tp3 = entry - height * projection.avg_fib_ratio * 1.5
        
        # 9. Create signal
        return TradeSignal(
            direction='short',
            entry=entry,
            stop_loss=sl,
            targets=[tp1, tp2, tp3],
            confidence=projection.lh_probability,
            divergence=divergence.type,
            expected_bars=projection.expected_bars,
            metadata={...}
        )
```

**Testing**:
- Run on December 2024 data
- Target: 30-50 detections, 60%+ profitability
- Compare to simple detector results

### Phase 5: Multi-Timeframe Integration (Day 4: 4-6 hours)

**Goals**:
- Add higher timeframe context
- Confirm patterns across timeframes
- Use HTF pivots as S/R levels

**Files to Create**:
```
src/layers/tbd_v2/
└── multi_timeframe_detector.py
```

**Testing**:
- Verify improved win rate
- Test timeframe alignment filters

### Phase 6: Optimization & Validation (Day 5: 6-8 hours)

**Goals**:
- Optimize all parameters
- Build statistics database
- Validate on full year data
- Compare to manual trading

**Tasks**:
1. Train statistics on 2023-2024 data
2. Optimize pivot lengths, divergence weights
3. Find optimal probability thresholds
4. Backtest on December 2024
5. Compare results to manual trading

**Success Criteria**:
- Detection: 30-50 patterns/month ✓ (already have)
- Win Rate: >60% (vs current 51.7%)
- Profit Factor: >2.0 (vs current 0.95)
- Total Profit: POSITIVE (vs current -0.66%)

---

## Technical Specifications

### Data Requirements

**Input Data** (per detection):
```python
{
    'timeframe': '15m',
    'data': pd.DataFrame({
        'timestamp': [...],
        'open': [...],
        'high': [...],
        'low': [...],
        'close': [...],
        'volume': [...]
    }),
    'lookback': 200  # Minimum bars for zigzag
}
```

**Higher Timeframe Data** (for multi-TF):
```python
{
    '1h': pd.DataFrame(...),
    '4h': pd.DataFrame(...),
    '1d': pd.DataFrame(...)
}
```

### Configuration Schema

```python
@dataclass
class SophisticatedMPatternConfig:
    """Configuration for sophisticated M-pattern detector"""
    
    # Zigzag parameters
    pivot_length: int = 50           # Bars on each side for pivot
    zigzag_threshold: float = 2.0    # Min % move for zigzag
    
    # Oscillator settings
    oscillator_type: str = 'rsi'     # 'rsi', 'cci', 'cmo', 'mfi'
    oscillator_length: int = 14
    
    # Divergence settings
    divergence_enabled: bool = True
    divergence_weight: float = 0.15  # Probability boost
    
    # Statistical thresholds
    min_probability: float = 0.55    # Min 55% confidence
    min_historical_samples: int = 10  # Need 10+ historical patterns
    
    # Pattern geometry
    peak_tolerance: float = 0.15     # 15% max asymmetry
    pattern_length_min: int = 10
    pattern_length_max: int = 50
    
    # Multi-timeframe
    enable_multi_tf: bool = True
    higher_timeframes: List[str] = ['1h', '4h']
    
    # Risk management
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5
    
    # Target multipliers (use projected Fib ratios)
    use_statistical_targets: bool = True
    fallback_tp_multipliers: List[float] = [0.5, 1.0, 1.5]
    
    # Statistics database
    stats_file: str = 'data/pattern_statistics/m_pattern_stats.pkl'
```

### Output Schema

```python
@dataclass
class SophisticatedSignal:
    """Enhanced signal with statistical data"""
    
    # Standard fields
    direction: str              # 'short'
    confidence: float           # 0.0-1.0 (from statistics)
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    
    # Sophisticated additions
    pattern_sequence: List[str]     # ['HH', 'LH', 'LL']
    pattern_index: int              # 0-63
    hh_probability: float           # e.g., 0.35 (35%)
    lh_probability: float           # e.g., 0.65 (65%)
    projected_fib_ratio: float      # e.g., 1.618
    expected_bars_to_target: int    # e.g., 12
    
    divergence_type: str            # 'regular_bearish', 'hidden_bearish', etc.
    divergence_strength: int        # -2 to +2
    
    ghost_levels: List[float]       # Nearby resistance levels
    zigzag_pivots: List[Pivot]      # Last 5 zigzag pivots
    
    # Multi-timeframe
    htf_alignment: Dict[str, str]   # {'1h': 'downtrend', '4h': 'downtrend'}
    htf_pivots: Dict[str, List[float]]  # HTF pivot levels
    
    # Metadata
    historical_samples: int         # How many times this pattern seen
    avg_win_rate_historical: float  # Historical win rate for this pattern
    avg_profit_historical: float    # Historical avg profit
```

---

## Success Metrics

### Detection Quality
- **Count**: 30-50 patterns/month ✓ (already achieving)
- **Precision**: >70% of detected patterns are tradeable
- **Recall**: >80% of actual M-patterns detected

### Profitability
- **Win Rate**: >60% (vs current 51.7%)
- **Profit Factor**: >2.0 (vs current 0.95)
- **Total Return**: >+5% per month (vs current -0.66%)
- **Expectancy**: >+0.20% per trade (vs current -0.02%)

### Statistical Validation
- **HH/LH Probability**: >60% accuracy when predicted
- **Fibonacci Projection**: Targets hit within 10% of projection
- **Bar Count Projection**: Within 20% of projected timing

---

## Files Reference

### TradingView Scripts to Study
- `TradingView_Scripts/pivot_points_detector.pine` - Ghost levels & zigzag
- `TradingView_Scripts/next_pivot_projection.pine` - Statistical matching (main algorithm)
- `TradingView_Scripts/pivot_points_high_low_multi_time_frame.pine` - Multi-TF pivots
- `TradingView_Scripts/pivots_fibonacci_retracement_study.pine` - Fib analysis

### Current Simple Implementation (Reference)
- `src/layers/tbd_v2/m_pattern_layer.py` - Current simple detector (losing money)
- `src/layers/tbd_v2/base_tbd_pattern.py` - Base class to inherit from

### Optimizers (Keep and Adapt)
- `scripts/optimization/run_m_pattern_v2_profit_optimizer.py` - Multiprocessing optimizer
- Adapt for new sophisticated detector

---

## Next Steps for New Task

1. **Start Fresh**: Use `/newtask` to begin with clean context
2. **Phase 1**: Build zigzag detector (Day 1)
3. **Phase 2**: Add divergence (Day 1-2)
4. **Phase 3**: Build statistics engine (Day 2-3)
5. **Phase 4**: Integrate sophisticated detector (Day 3-4)
6. **Phase 5**: Multi-timeframe (Day 4)
7. **Phase 6**: Optimize & validate (Day 5)

**Timeline**: 5 days intensive work  
**Outcome**: Institutional-grade M-pattern detector matching user's 75-300% profitability

---

## Questions to Address in New Task

1. Should we train statistics on historical data first, or build incrementally during backtesting?
2. Which oscillator is primary? (User likely uses RSI based on Pine scripts)
3. What's minimum pattern count before we trust statistics? (Suggest 10+)
4. Should ghost levels block entries or just reduce confidence?
5. Multi-TF: How strict should alignment be? (All TFs agree or just majority?)

---

**End of Specification**  
**Branch**: M_Pattern_Detector  
**Ready for**: `/newtask` clean implementation  
**Estimated Completion**: 5 days (40 hours)
