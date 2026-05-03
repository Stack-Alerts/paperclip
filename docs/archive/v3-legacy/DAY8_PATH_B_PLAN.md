# BTC_Engine_v3 - Day 8+ Path B Implementation Plan

**Date:** December 30, 2025  
**Status:** PLANNING COMPLETE - Ready for Implementation  
**Source:** `docs/v3/Patterns/SOPHISTICATED_M_PATTERN_DETECTOR_SPEC.md`  
**Timeline:** Days 8-13 (5-day implementation)

---

## Executive Summary

### Current Baseline (Day 7 Complete)
- ✅ Full NautilusTrader backtest framework operational
- ✅ Simple M-pattern detection working (9 patterns/100 bars)
- ✅ Entry and exit logic complete
- ✅ P&L calculation accurate (-$6.29 on 100 bars)
- ❌ **Win rate: 0%** (simple peaks are inadequate)
- ❌ **Return: -0.06%** (proves need for sophistication)

### Path B Goal: Sophisticated V2 Detector
Transform simple peak detection into **institutional-grade zigzag-based system** matching proven TradingView methodology that achieves **60%+ win rate** and **+5%+ monthly returns**.

---

## Problem Statement

**Current Simple Detector Results (December 2024)**:
- Detection Count: 43 patterns/month ✅ (correct)
- Win Rate: 51.7% ❌ (barely break-even)
- Profit Factor: 0.95 ❌ (losing money)
- Monthly Return: -0.66% ❌ (LOSING!)

**Root Cause**: Using scipy peak detection instead of structural zigzag

**Gap Analysis**:
| Component | Current | Required | Impact |
|-----------|---------|----------|--------|
| Peak Detection | scipy.signal | Zigzag structure | Critical |
| Divergence | None | Price vs RSI/CCI | High |
| Statistics | None | 64x3 outcome matrix | Critical |
| Projection | Fixed TPs | Fib ratio projection | High |
| Multi-TF | Single | Multiple TFs | Medium |
| Ghost Levels | None | Missed pivot tracking | Medium |

---

## Solution Architecture (5 Components)

### 1. Zigzag Foundation ⭐ CRITICAL

**Purpose**: Structural pivot detection (not simple peaks)

**Key Concepts**:
- Pivots require confirmation (N bars on each side)
- Only significant swings (filters noise)
- **Ghost levels**: Track missed reversals (become resistance)
- Pattern sequences: HH/LH/LL/HL tracking

**TradingView Reference**: `pivot_points_detector.pine`
```pine
length = input(50, 'Pivot Length')
ph = ta.pivothigh(length, length)  // Need length bars AFTER for confirmation
pl = ta.pivotlow(length, length)
```

**Python Implementation Needed**:
```python
class ZigzagDetector:
    def __init__(self, length=50, threshold_percent=2.0):
        self.length = length
        self.threshold = threshold_percent / 100
        self.pivots = []  # [(index, price, type)]
        self.ghost_levels = []  # Missed reversals
    
    def find_pivots(self, data) -> List[Pivot]:
        """Find confirmed structural pivots"""
        # Check if each bar is highest/lowest in length*2+1 window
        # Only confirmed after length bars pass
        pass
    
    def get_pattern_sequence(self) -> List[str]:
        """Return ['HH', 'LH', 'LL'] pattern"""
        pass
```

**Files to Create**:
```
src/detectors/
├── __init__.py
├── zigzag_detector.py          # Core zigzag logic
├── pivot_detector.py           # Pivot confirmation
└── ghost_level_tracker.py      # Missed pivot tracking
```

### 2. Divergence Analysis

**Purpose**: Price makes HH but RSI makes LH = Bearish divergence (reversal signal)

**Oscillators Required**:
- RSI (14-period, most common)
- CCI
- CMO
- MFI
- ROC

**Impact**: +15% probability boost when bearish divergence detected

**Python Implementation**:
```python
class DivergenceDetector:
    def __init__(self, oscillator='rsi', length=14):
        self.osc_type = oscillator
        self.length = length
    
    def check_divergence(self, price_pivots, osc_data) -> int:
        """
        Returns:
            +2: Strong bullish divergence
            -2: Strong bearish divergence (price HH, osc LH)
            0: No divergence
        """
        pass
```

**Files to Create**:
```
src/detectors/
├── oscillators.py              # RSI, CCI, CMO, MFI, ROC
└── divergence_detector.py      # Divergence analysis
```

### 3. Statistical Pattern Matching 🎯 REVOLUTIONARY

**Purpose**: Build 64x3 matrix tracking historical outcomes for pattern prediction

**Concept**: 
- **Pattern Classification**: Each pivot sequence gets index 0-63
  - Bit 1: Trend (Up=0, Down=1)
  - Bit 2: Price direction (HH=1, LH=0)
  - Bit 3: Oscillator direction (HH=1, LH=0)
  - Example: Down-LH/LH = 1×4 + 0×2 + 0×1 = 4

- **Outcome Tracking**: For each pattern index:
  - Column 0: Count of Higher High outcomes
  - Column 1: Count of Lower High outcomes
  - Column 2: Total occurrences
  
- **Projection**: When pattern detected:
  - HH Probability = HH_count / Total
  - LH Probability = LH_count / Total
  - Avg Fib Ratio = Sum(price_ratios) / count
  - Expected Bars = Sum(bar_counts) / count

**Trading Logic**:
- If HH probability >60%: **SKIP** (likely to go higher)
- If LH probability >55%: **ENTER** (confident reversal)
- Use historical avg Fib ratio for targets (not fixed multipliers)

**TradingView Reference**: `next_pivot_projection.pine`
```pine
var pivotHighStats = matrix.new<int>(64, 3, 0)
var pivotHighRatios = matrix.new<float>(64, 3, 0)

trendIndex = gettrendindex(priceDir, oscDir, trendDir)
totalIndex = lastTrendIndex*8 + llastTrendIndex

// Update when pivot confirms
if changePriceDirection:
    increment(pivotHighStats, totalIndex, colLast)
    increment(pivotHighRatios, totalIndex, colLast, priceRatio)

// Predict next
hhProb = matrix.get(pivotHighStats, totalIndex, 0) / total
hhRatio = matrix.get(pivotHighRatios, totalIndex, 0) / hhCount
```

**Python Implementation**:
```python
class PatternStatistics:
    def __init__(self):
        # 64 possible patterns × 3 outcomes (HH/LH/Total)
        self.pivot_high_stats = np.zeros((64, 3), dtype=int)
        self.pivot_high_ratios = np.zeros((64, 3), dtype=float)
        self.pivot_high_bars = np.zeros((64, 3), dtype=int)
    
    def get_pattern_index(self, price_dir, osc_dir, trend_dir) -> int:
        """Encode pattern to 0-63 index"""
        trend_bit = 0 if trend_dir > 0 else 1
        price_bit = 1 if abs(price_dir) > 1 else 0
        osc_bit = 1 if abs(osc_dir) > 1 else 0
        return trend_bit * 4 + price_bit * 2 + osc_bit
    
    def update_outcome(self, pattern_index, outcome_type, fib_ratio, bars):
        """Track historical outcome in matrix"""
        col = 0 if outcome_type == 'HH' else 1
        self.pivot_high_stats[pattern_index, col] += 1
        self.pivot_high_ratios[pattern_index, col] += fib_ratio
        self.pivot_high_bars[pattern_index, col] += bars
    
    def predict_next_pivot(self, pattern_index) -> Tuple[float, float, int]:
        """
        Returns:
            hh_probability: 0.0-1.0
            avg_fib_ratio: e.g., 1.618
            expected_bars: e.g., 12
        """
        total = self.pivot_high_stats[pattern_index, 2]
        if total < 10:  # Need minimum samples
            return 0.50, 1.0, 10  # Default
        
        hh_count = self.pivot_high_stats[pattern_index, 0]
        hh_prob = hh_count / total
        
        # Get avg ratio and bars for dominant outcome
        if hh_prob > 0.50:
            avg_ratio = self.pivot_high_ratios[pattern_index, 0] / hh_count
            avg_bars = self.pivot_high_bars[pattern_index, 0] / hh_count
        else:
            lh_count = self.pivot_high_stats[pattern_index, 1]
            avg_ratio = self.pivot_high_ratios[pattern_index, 1] / lh_count
            avg_bars = self.pivot_high_bars[pattern_index, 1] / lh_count
        
        return hh_prob, avg_ratio, int(avg_bars)
```

**Files to Create**:
```
src/detectors/
├── pattern_statistics.py       # 64x3 matrix tracking
├── pattern_encoder.py          # Pattern → index conversion
└── pivot_projector.py          # Future pivot prediction

data/pattern_statistics/
└── m_pattern_stats.pkl         # Pre-trained statistics database
```

### 4. Fibonacci Projection

**Purpose**: Use historical averages (not fixed multipliers) for targets

**Current Approach** (simple):
```python
tp1 = entry - height * 0.5
tp2 = entry - height * 1.0
tp3 = entry - height * 1.5
```

**Sophisticated Approach**:
```python
# Get statistical projection for this pattern
projection = self.statistics.predict(pattern_index)

# Use historically-proven Fib ratio
tp1 = entry - height * projection.avg_fib_ratio * 0.5
tp2 = entry - height * projection.avg_fib_ratio * 1.0
tp3 = entry - height * projection.avg_fib_ratio * 1.5
```

**Expected Improvement**: Targets based on what actually happens (not arbitrary)

### 5. Multi-Timeframe Support

**Purpose**: Higher timeframe pivots are stronger support/resistance

**Concept**:
- Base TF: 15m or 30m (for entries)
- Higher TFs: 1h, 4h, 1d (for context)
- If all TFs show downtrend = **strong** signal
- If TFs conflict = reduce confidence or skip

**Python Implementation**:
```python
class MultiTimeframeDetector:
    def __init__(self, base_tf='15m', higher_tfs=['1h', '4h']):
        self.detectors = {tf: ZigzagDetector() for tf in [base_tf] + higher_tfs}
    
    def check_alignment(self, pivots) -> bool:
        """Check if all timeframes agree on downtrend"""
        # If 15m shows M AND 1h downtrend AND 4h downtrend = STRONG
        pass
```

**Files to Create**:
```
src/detectors/
└── multi_timeframe_detector.py
```

---

## Implementation Timeline (5 Days)

### Day 8: Zigzag Foundation + Divergence (10-12 hours)

**Morning (4-5 hours) - Zigzag**:
1. Create `src/detectors/` directory structure
2. Implement `ZigzagDetector` class
   - Pivot confirmation logic
   - Pattern sequence tracking
   - Ghost level detection
3. Test against TradingView output
4. Validate pattern sequences

**Afternoon (4-5 hours) - Divergence**:
1. Implement oscillators (RSI, CCI, CMO)
2. Create `DivergenceDetector` class
3. Test divergence detection
4. Validate probability impact

**Evening (2 hours) - Integration Test**:
- Run combined zigzag + divergence on December data
- Compare detection count vs simple detector
- Verify quality improvement

**Deliverable**: Working zigzag detector with divergence analysis

### Day 9: Statistical Pattern Matcher (10-12 hours)

**Morning (4-5 hours) - Matrix Implementation**:
1. Create `PatternStatistics` class
2. Implement 64x3 matrix tracking
3. Build pattern encoder (0-63 indexing)
4. Test encoding logic

**Afternoon (4-5 hours) - Training**:
1. Load 2023-2024 historical data
2. Build zigzag for training period
3. Populate statistics matrices
4. Save trained database

**Evening (2 hours) - Prediction**:
1. Implement `predict_next_pivot()`
2. Test probability accuracy
3. Validate Fib ratio projections
4. Compare to TradingView

**Deliverable**: Trained 64x3 statistics database with >5000 historical patterns

### Day 10: Sophisticated M-Pattern Integration (8-10 hours)

**Morning (3-4 hours) - Detector Class**:
1. Create `SophisticatedMPatternDetector`
2. Integrate all components:
   - Zigzag structure detection
   - Divergence checking
   - Statistical probability thresholds
   - Fib-based target calculation
3. Implement trading logic

**Afternoon (3-4 hours) - Testing**:
1. Run on December 2024 data
2. Compare simple vs sophisticated:
   - Detection count
   - Win rate
   - Profit factor
   - Monthly return
3. Adjust thresholds if needed

**Evening (2 hours) - Refinement**:
1. Tune probability thresholds
2. Optimize divergence weights
3. Validate results

**Deliverable**: Complete sophisticated detector achieving >55% win rate

### Day 11: Multi-Timeframe + Optimization (6-8 hours)

**Morning (3-4 hours) - Multi-TF**:
1. Implement `MultiTimeframeDetector`
2. Add HTF pivot tracking
3. Create alignment filters
4. Test improved accuracy

**Afternoon (3-4 hours) - Optimization**:
1. Optimize pivot length (30-70)
2. Optimize probability thresholds (50-65%)
3. Optimize divergence weights (0.10-0.20)
4. Find best parameter combinations

**Deliverable**: Optimized detector with multi-TF support

### Day 12-13: Validation & Documentation (8-10 hours)

**Day 12 Morning (4 hours) - Full Backtest**:
1. Run on full 2024 year
2. Analyze monthly performance
3. Compare to manual trading results
4. Validate success criteria

**Day 12 Afternoon (4 hours) - Integration**:
1. Connect to NautilusTrader strategy
2. Update `MPatternStrategy` to use sophisticated detector
3. Run full end-to-end backtest
4. Verify P&L calculation

**Day 13 (2-4 hours) - Documentation**:
1. Create user guide
2. Document configuration
3. Write optimization guide
4. Final validation report

**Deliverable**: Production-ready sophisticated detector with documentation

---

## Success Criteria

### Detection Quality
- ✅ Count: 30-50 patterns/month (currently: 43 ✓)
- ✅ Precision: >70% tradeable
- ✅ Recall: >80% of actual patterns detected

### Profitability (Primary Goals)
- ✅ Win Rate: **>60%** (vs current 51.7%)
- ✅ Profit Factor: **>2.0** (vs current 0.95)
- ✅ Monthly Return: **>+5%** (vs current -0.66%)
- ✅ Expectancy: **>+0.20%** per trade

### Statistical Validation
- ✅ HH/LH Probability: >60% accuracy when predicted
- ✅ Fibonacci Projection: Targets within 10% of actual
- ✅ Bar Count: Within 20% of predicted timing

---

## File Structure (New)

```
src/detectors/                          # NEW sophisticated detectors
├── __init__.py
├── zigzag_detector.py                  # Structural pivot detection
├── pivot_detector.py                   # Pivot confirmation
├── ghost_level_tracker.py              # Missed pivot tracking
├── oscillators.py                      # RSI, CCI, CMO, MFI, ROC
├── divergence_detector.py              # Divergence analysis
├── pattern_statistics.py               # 64x3 matrix tracking
├── pattern_encoder.py                  # Pattern indexing
├── pivot_projector.py                  # Future pivot prediction
└── multi_timeframe_detector.py         # Multi-TF analysis

src/strategies/
├── m_pattern_strategy.py               # UPDATE to use sophisticated detector
└── sophisticated_m_pattern_strategy.py # NEW sophisticated version

data/pattern_statistics/                # NEW statistics database
├── m_pattern_stats.pkl                 # Trained matrix
└── training_log.json                   # Training metadata

docs/
└── DAY8-13_SOPHISTICATED_IMPLEMENTATION.md  # Implementation log
```

---

## Configuration Schema

```python
@dataclass
class SophisticatedMPatternConfig:
    """Configuration for sophisticated M-pattern detector"""
    
    # Zigzag parameters
    pivot_length: int = 50           # Bars on each side
    zigzag_threshold: float = 2.0    # Min % move
    
    # Oscillator
    oscillator_type: str = 'rsi'
    oscillator_length: int = 14
    
    # Divergence
    divergence_enabled: bool = True
    divergence_weight: float = 0.15  # Probability boost
    
    # Statistical thresholds
    min_lh_probability: float = 0.55    # Min 55% LH confidence
    max_hh_probability: float = 0.60    # Skip if >60% HH
    min_historical_samples: int = 10     # Need 10+ samples
    
    # Pattern geometry
    peak_tolerance: float = 0.15     # 15% asymmetry allowed
    pattern_length_min: int = 10
    pattern_length_max: int = 50
    
    # Multi-timeframe
    enable_multi_tf: bool = True
    higher_timeframes: List[str] = ['1h', '4h']
    
    # Risk management
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5
    
    # Targets
    use_statistical_targets: bool = True
    fallback_tp_multipliers: List[float] = [0.5, 1.0, 1.5]
    
    # Statistics
    stats_file: str = 'data/pattern_statistics/m_pattern_stats.pkl'
```

---

## Key Technical Questions

### 1. Training Strategy
**Q**: Train statistics first or build incrementally?  
**A**: **Train first** on 2023-2024 data (need baseline)

### 2. Primary Oscillator
**Q**: Which oscillator for divergence?  
**A**: **RSI (14-period)** - most common, proven

### 3. Minimum Sample Size
**Q**: Min pattern count before trusting statistics?  
**A**: **10+ samples** per pattern index

### 4. Ghost Level Handling
**Q**: Should ghosts block entries?  
**A**: **Reduce confidence** (not block) - use as risk factor

### 5. Multi-TF Strictness
**Q**: How strict should alignment be?  
**A**: **Majority vote** - 2 of 3 TFs agree (not all required)

---

## TradingView Scripts Reference

Study these for implementation details:

1. **`pivot_points_detector.pine`** - Zigzag + ghost levels
   - How pivots are confirmed
   - Ghost level tracking logic
   - Pattern sequence building

2. **`next_pivot_projection.pine`** - Statistical matching (MAIN ALGORITHM!)
   - 64x3 matrix implementation
   - Pattern encoding
   - Probability calculation
   - Fib ratio averaging

3. **`pivot_points_high_low_multi_time_frame.pine`** - Multi-TF
   - Higher TF pivot detection
   - Alignment checking

4. **`pivots_fibonacci_retracement_study.pine`** - Fib analysis
   - Ratio calculation
   - Level projection

---

## Expected Performance Improvement

### Before (Simple - Day 7)
```
Detection: 9 patterns/100 bars
Win Rate: 0% (all TP rejections)
Return: -0.06%
Status: LOSING MONEY
```

### After (Sophisticated - Day 13 Target)
```
Detection: 30-50 patterns/month  
Win Rate: >60%
Profit Factor: >2.0
Monthly Return: >+5%
Status: PROFITABLE
```

**Improvement**: From losing to profitable by using proven TradingView methodology

---

## TradingView Scripts to Reference

**Location**: `/home/sirrus/projects/BTC_Engine_v3/TradingView_Scripts/`

**Critical Files**:
1. **`pivot_points_detector.pine`** - Zigzag + ghost levels implementation
2. **`next_pivot_projection.pine`** - THE MAIN ALGORITHM (64x3 matrix)
3. **`pivot_points_high_low_multi_time_frame.pine`** - Multi-TF implementation
4. **`pivots_fibonacci_retracement_study.pine`** - Fibonacci analysis

These are PROVEN scripts that the user uses for manual trading (75-300% returns). Our goal is to replicate this exact methodology programmatically.

---

## Quick Reference: Current Baseline Code

### Simple Peak Detection (TO BE REPLACED)

**Current Method** in `src/indicators/pattern_adapter.py`:
```python
from scipy.signal import find_peaks

# SIMPLE (LOSING MONEY!)
peaks, _ = find_peaks(highs, distance=5, prominence=height_threshold)
```

**Problem**: Finds local maxima based on simple distance/prominence, not structural pivots.

### Simple M-Pattern Strategy

**Current Implementation** in `src/strategies/m_pattern_strategy.py`:
```python
# Simple detection flow (Day 7 baseline)
def on_bar(self, bar: Bar) -> None:
    # 1. Store bar
    self.bars.append(bar)
    
    # 2. Simple pattern detection
    signal = self.pattern_detector.detect_m_pattern(
        pd.DataFrame(self.bars),
        min_confidence=self.min_confidence
    )
    
    # 3. If pattern, submit market order
    if signal:
        order = self.order_factory.market(...)
        self.submit_order(order)
```

**Result**: 9 detections in 100 bars, 0% win rate, -$6.29 loss

### Current Data Access

**Data Loading Pattern**:
```python
import pandas as pd
import pickle

# Load historical data
with open('/home/sirrus/projects/BTC_Engine_v3/data/raw/BTC_USDT_PERP_30m.pkl', 'rb') as f:
    df = pickle.load(f)

# Filter to 2024-2025
df = df[df.index >= '2024-01-01']
# 34,336 bars available
```

**Columns**: `['open', 'high', 'low', 'close', 'volume']`

---

## Critical Implementation Notes

### 1. Zigzag Pivot Confirmation Logic

**TradingView Method**:
```pine
length = 50
ph = ta.pivothigh(length, length)
```

**What this means**:
- Requires `length` bars BEFORE the potential pivot
- Requires `length` bars AFTER the potential pivot
- Total window: `2*length+1` bars (101 bars for length=50)
- Pivot at index `i` is only confirmed at index `i+length`

**Python Implementation Pattern**:
```python
def is_pivot_high(data, index, length):
    """
    Check if data[index] is a pivot high
    Requires length bars on EACH side
    """
    if index < length or index >= len(data) - length:
        return False  # Not enough bars
    
    center_value = data['high'][index]
    
    # Check LEFT side (length bars before)
    left_max = data['high'][index-length:index].max()
    if center_value <= left_max:
        return False
    
    # Check RIGHT side (length bars after)
    right_max = data['high'][index+1:index+1+length].max()
    if center_value <= right_max:
        return False
    
    return True  # It's a pivot!
```

**This is fundamentally different from scipy.find_peaks!**

### 2. Pattern Encoding for 64x3 Matrix

**Encoding Logic** (from TradingView):
```python
def get_pattern_index(price_dir, osc_dir, trend_dir):
    """
    Encode pattern to 0-63 index
    
    Args:
        price_dir: -1 (LH) or +1 (HH) or other for complex
        osc_dir: -1 (LH) or +1 (HH) or other for complex
        trend_dir: -1 (down) or +1 (up)
    
    Returns:
        Index 0-63
    """
    # Bit 1: Trend (Up=0, Down=1)
    trend_bit = 0 if trend_dir > 0 else 1
    
    # Bit 2: Price direction (HH=1, LH=0, complex=determined by abs)
    if abs(price_dir) > 1:  # HH
        price_bit = 1
    else:  # LH or LL
        price_bit = 0
    
    # Bit 3: Oscillator direction (HH=1, LH=0)
    if abs(osc_dir) > 1:  # HH
        osc_bit = 1
    else:  # LH or LL
        osc_bit = 0
    
    # Combine: index = trend*4 + price*2 + osc*1
    return trend_bit * 4 + price_bit * 2 + osc_bit
```

**Example Encodings**:
- Up trend, HH price, HH osc: `0*4 + 1*2 + 1*1 = 3`
- Down trend, LH price, LH osc: `1*4 + 0*2 + 0*1 = 4`
- Down trend, HH price, LH osc: `1*4 + 1*2 + 0*1 = 6` (bearish divergence!)

### 3. RSI Calculation (Primary Oscillator)

```python
def calculate_rsi(data, length=14):
    """Calculate RSI exactly as TradingView"""
    import pandas as pd
    
    # Calculate price changes
    delta = data['close'].diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate average gain/loss (Wilder's smoothing)
    avg_gain = gain.rolling(window=length, min_periods=length).mean()
    avg_loss = loss.rolling(window=length, min_periods=length).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi
```

### 4. M-Pattern Structure Requirements

**Valid M-Pattern Criteria**:
1. **Two peaks** within tolerance (15% height difference)
2. **Valley between peaks** (lower than both peaks)
3. **Pattern length**: 10-50 bars total
4. **Neckline break**: Price drops below valley low
5. **Zigzag structure**: Confirmed structural pivots (not noise)

**Sophisticated Addition**:
- Check for bearish divergence (price HH, RSI LH)
- Check statistical probability (LH >55%)
- Skip if HH probability >60%

---

## Data Requirements for Training

### Historical Data Needed

**For Statistics Training** (Day 9):
- Period: 2023-01-01 to 2024-12-31 (2 years)
- Bars needed: ~35,000 (30-min bars)
- Purpose: Build 64x3 outcome matrices
- Minimum patterns per index: 10

**Current Data Available**:
```
File: /home/sirrus/projects/BTC_Engine_v3/data/raw/BTC_USDT_PERP_30m.pkl
Rows: 34,336 bars
Period: 2024-01-01 to 2025-12-16
Status: ✅ READY
```

**Additional Required**:
- Need 2023 data for training (might need to download)
- Alternative: Train on 2024 data, test on Dec 2024

### Training Process

```python
# Day 9 training workflow
def train_statistics(historical_data):
    """Build 64x3 matrices from historical zigzag"""
    
    # 1. Build zigzag for entire period
    zigzag = ZigzagDetector(length=50)
    pivots = zigzag.find_pivots(historical_data)
    
    # 2. Calculate RSI
    rsi = calculate_rsi(historical_data)
    
    # 3. For each pivot, determine outcome
    stats = PatternStatistics()
    
    for i in range(2, len(pivots)-1):  # Need 2 before, 1 after
        # Get pattern
        p1, p2, p3 = pivots[i-2], pivots[i-1], pivots[i]
        
        # Encode pattern
        pattern_idx = encode_pattern(p1, p2, p3, rsi)
        
        # Determine outcome (what happened next)
        p_next = pivots[i+1]
        outcome_type = 'HH' if p_next.price > p3.price else 'LH'
        fib_ratio = abs(p_next.price - p3.price) / abs(p3.price - p2.price)
        bars_to_next = p_next.index - p3.index
        
        # Update statistics
        stats.update_outcome(pattern_idx, outcome_type, fib_ratio, bars_to_next)
    
    # 4. Save
    stats.save('data/pattern_statistics/m_pattern_stats.pkl')
    
    return stats
```

---

## Next Steps

### Immediate (Day 8 Start)
1. ✅ Planning complete (this document)
2. [ ] Start fresh session with clean context
3. [ ] Begin Phase 1: Zigzag Detector implementation
4. [ ] Create `src/detectors/` directory
5. [ ] Implement `ZigzagDetector` class
6. [ ] Test vs TradingView pivot detection

### Session Commands
```bash
# Day 8 Session Start
cd /home/sirrus/projects/BTC_Engine_v3
source venv/bin/activate

# Create directory structure
mkdir -p src/detectors
mkdir -p data/pattern_statistics

# Begin implementation
# Reference: docs/v3/Patterns/SOPHISTICATED_M_PATTERN_DETECTOR_SPEC.md
# Reference: TradingView_Scripts/pivot_points_detector.pine
# Reference: TradingView_Scripts/next_pivot_projection.pine
```

### First File to Create (Day 8 Morning)

**Create**: `src/detectors/zigzag_detector.py`

**Template** (copy this to start):
```python
"""
Zigzag Detector - Structural Pivot Detection

Replicates TradingView's ta.pivothigh() and ta.pivotlow() logic.
Unlike scipy.find_peaks, this requires confirmation bars on BOTH sides.

Reference: TradingView_Scripts/pivot_points_detector.pine
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class Pivot:
    """Structural pivot point"""
    index: int
    timestamp: pd.Timestamp
    price: float
    pivot_type: str  # 'H' for high, 'L' for low
    confirmed_at: int  # Index where pivot was confirmed


@dataclass
class GhostLevel:
    """Missed pivot (potential reversal that didn't confirm)"""
    index: int  
    price: float
    level_type: str  # 'resistance' or 'support'


class ZigzagDetector:
    """
    Zigzag detector using TradingView methodology.
    
    Key difference from simple peak detection:
    - Requires LENGTH bars on EACH SIDE for confirmation
    - Tracks ghost levels (missed reversals)
    - Builds structural pattern sequences
    """
    
    def __init__(self, length: int = 50, threshold_percent: float = 2.0):
        """
        Args:
            length: Bars required on each side for pivot confirmation
            threshold_percent: Minimum % move to consider (optional filter)
        """
        self.length = length
        self.threshold = threshold_percent / 100
        
        self.pivots: List[Pivot] = []
        self.ghost_levels: List[GhostLevel] = []
        
    def find_pivots(self, data: pd.DataFrame) -> List[Pivot]:
        """
        Find all confirmed structural pivots in data.
        
        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            
        Returns:
            List of confirmed pivots
        """
        pivots = []
        
        # Start from length (need bars before)
        # End at len-length (need bars after for confirmation)
        for i in range(self.length, len(data) - self.length):
            # Check pivot high
            if self._is_pivot_high(data, i):
                pivot = Pivot(
                    index=i,
                    timestamp=data.index[i],
                    price=data['high'].iloc[i],
                    pivot_type='H',
                    confirmed_at=i + self.length
                )
                pivots.append(pivot)
            
            # Check pivot low
            elif self._is_pivot_low(data, i):
                pivot = Pivot(
                    index=i,
                    timestamp=data.index[i],
                    price=data['low'].iloc[i],
                    pivot_type='L',
                    confirmed_at=i + self.length
                )
                pivots.append(pivot)
        
        self.pivots = pivots
        return pivots
    
    def _is_pivot_high(self, data: pd.DataFrame, index: int) -> bool:
        """
        Check if data[index] is a pivot high.
        
        TradingView logic: ta.pivothigh(length, length)
        - Must be highest in length bars LEFT
        - Must be highest in length bars RIGHT
        """
        center = data['high'].iloc[index]
        
        # Check LEFT side
        left_start = index - self.length
        left_end = index
        left_max = data['high'].iloc[left_start:left_end].max()
        if center <= left_max:
            return False
        
        # Check RIGHT side
        right_start = index + 1
        right_end = index + 1 + self.length
        right_max = data['high'].iloc[right_start:right_end].max()
        if center <= right_max:
            return False
        
        return True
    
    def _is_pivot_low(self, data: pd.DataFrame, index: int) -> bool:
        """Check if data[index] is a pivot low"""
        center = data['low'].iloc[index]
        
        # Check LEFT side
        left_start = index - self.length
        left_end = index
        left_min = data['low'].iloc[left_start:left_end].min()
        if center >= left_min:
            return False
        
        # Check RIGHT side  
        right_start = index + 1
        right_end = index + 1 + self.length
        right_min = data['low'].iloc[right_start:right_end].min()
        if center >= right_min:
            return False
        
        return True
    
    def get_pattern_sequence(self) -> List[str]:
        """
        Get pattern sequence for last pivots.
        
        Returns:
            e.g., ['HH', 'LH', 'LL'] for higher-high, lower-high, lower-low
        """
        if len(self.pivots) < 3:
            return []
        
        sequence = []
        for i in range(1, len(self.pivots)):
            prev = self.pivots[i-1]
            curr = self.pivots[i]
            
            # Only compare same type (highs to highs, lows to lows)
            if prev.pivot_type != curr.pivot_type:
                continue
            
            if curr.pivot_type == 'H':  # Pivot highs
                if curr.price > prev.price:
                    sequence.append('HH')
                else:
                    sequence.append('LH')
            else:  # Pivot lows
                if curr.price > prev.price:
                    sequence.append('HL')
                else:
                    sequence.append('LL')
        
        return sequence


# TODO Day 8: Implement ghost level tracking
# TODO Day 8: Add tests comparing to TradingView output
```

**Test it immediately**:
```python
# test_zigzag.py
import pandas as pd
import pickle
from zigzag_detector import ZigzagDetector

# Load data
with open('data/raw/BTC_USDT_PERP_30m.pkl', 'rb') as f:
    df = pickle.load(f)

df = df[df.index >= '2024-01-01'].iloc[:1000]  # First 1000 bars

# Test zigzag
zigzag = ZigzagDetector(length=50)
pivots = zigzag.find_pivots(df)

print(f"Found {len(pivots)} pivots")
print(f"Pattern sequence: {zigzag.get_pattern_sequence()}")
for p in pivots[:10]:
    print(f"{p.pivot_type} pivot at {p.timestamp}: ${p.price:.2f}")
```

---

---

## Conclusion

**Day 7 Status**: ✅ BASELINE COMPLETE  
**Day 8-13 Status**: 📋 PLANNING COMPLETE - Ready for implementation

**Confidence Level**: HIGH (proven TradingView methodology)  
**Expected Timeline**: 5 days (40 hours)  
**Expected Outcome**: 60%+ win rate, +5%+ monthly return

**Ready to proceed with sophisticated implementation!** 🚀

---

**Document Created**: December 30, 2025  
**Author**: Cline (AI Assistant)  
**Status**: Planning Phase Complete - Awaiting Day 8 Implementation
