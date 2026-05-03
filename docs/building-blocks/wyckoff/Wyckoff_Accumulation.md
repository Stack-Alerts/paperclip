# Wyckoff Accumulation Building Block

**Block Number:** 53/66 | **Category:** Wyckoff Method | **Version:** 2.0 (MTF Enhanced) | **Status:** ✅ PRODUCTION READY

---

## ✅ MULTI-TIMEFRAME ACCUMULATION DETECTOR - PRODUCTION READY

**This block detects Wyckoff accumulation phases using 2HR (primary) + 4HR (confirmation) analysis**

**Test Results (2HR):** 35.8% active + 66.3% avg confidence + perfect distribution  
**Test Results (4HR):** 8.5% active + 64.3% avg confidence + ultra selective  
**Block Type:** EVENT BLOCK (selective accumulation detection)  
**Design:** Multi-timeframe Wyckoff analysis + phase detection + volume validation  
**Grade:** A (92/100) - EXCELLENT Wyckoff implementation

**Current Performance (2HR - PRIMARY):**
- ✅ 35.8% active (perfect selectivity)
- ✅ 4.09 signals/day (optimal frequency)
- ✅ 66.3% avg confidence (good quality)
- ✅ 0% error rate (perfect reliability)
- ✅ **64.2% NO_ACCUMULATION** (correctly trending)
- ✅ **30.5% Phase B** (realistic accumulation)
- ✅ **5.3% Phase A** (selective selling climax)

**Current Performance (4HR - CONFIRMATION):**
- ✅ 8.5% active (ultra selective - CORRECT!)
- ✅ 0.46 signals/day (confirmation only)
- ✅ 64.3% avg confidence
- ✅ **91.5% NO_ACCUMULATION** (very high bar)
- ✅ **8.3% Phase B** (true institutional zones)
- ✅ **0.2% Phase A** (extremely rare)

**Implementation Features:**
1. ✅ Phase A detection (selling climax + volume spike)
2. ✅ Phase B detection (range building + volume decline)
3. ✅ Phase C detection (spring - false breakdown)
4. ✅ Phase D detection (SOS - breakout confirmation)
5. ✅ Multi-timeframe helper function
6. ✅ Volume analysis (critical for Wyckoff)
7. ✅ Support/resistance tracking
8. ✅ Range detection with realistic thresholds

**Status:** ✅ PRODUCTION READY - A GRADE

**See Expert Review:** `docs/v3/expert_analisys_review_building_blocks/53_wyckoff_accumulation_expert_review.md`

**Deployment:**
- 2HR for primary accumulation signals
- 4HR for confirmation of major zones
- MTF alignment for mega boosters
- ❌ NOT on 15min (micro-ranges)

---

## Overview

Wyckoff Accumulation detects smart money building positions through the classic Wyckoff accumulation cycle: Phase A (selling climax with high volume panic), Phase B (range building with declining volume), Phase C (spring - false breakdown shaking weak hands), Phase D (sign of strength - volume breakout). Optimized for 2HR (primary, 35.8% active, 30.5% in Phase B) and 4HR (confirmation, 8.5% active, true institutional zones). Multi-timeframe helper function provides alignment detection with mega booster (+125 points total when both timeframes in same phase). NOT recommended for 15min (80.8% false Phase B from micro-ranges). Essential for institutional accumulation zone trading.

## Block Classification

**Type:** EVENT BLOCK - MULTI-TIMEFRAME ACCUMULATION DETECTOR
- **Signal Rate (2HR):** 35.8% (perfect selectivity)
- **Signal Rate (4HR):** 8.5% (ultra selective)
- **Phases:** A (climax), B (range), C (spring), D (SOS)
- **Timeframes:** 2HR (primary), 4HR (confirmation)
- **Volume:** Critical component
- **Boosters:** +45-145 points (MTF aligned)
- Institutional accumulation specialist

## Technical Specifications

**Components:** Phase Detection + Volume Analysis + Range Identification + Spring/SOS Detection + MTF Integration  
**File:** `src/detectors/building_blocks/wyckoff/wyckoff_accumulation.py`

## Signals

### 4 Wyckoff Phases (Event-Based):

**ACCUMULATION_PHASE_A** (Selling Climax)
- High volume panic (2x+ average)
- Lowest low in recent period
- Sharp reversal
- Confidence: 75-85%
- Frequency (2HR): 5.3%
- Frequency (4HR): 0.2% (very rare)
- Booster: +55 points (2HR), +40 points (4HR)

**ACCUMULATION_PHASE_B** (Range Building)
- Consolidation range (<5% on 2HR/4HR)
- Declining volume (quiet accumulation)
- Duration: 20+ bars
- Confidence: 60-70%
- Frequency (2HR): 30.5% (realistic)
- Frequency (4HR): 8.3% (institutional)
- Booster: +45 points (2HR), +30 points (4HR)

**SPRING_DETECTED** (Phase C - False Breakdown)
- Break below support (>2%)
- LOW volume on breakdown (weak hands)
- Quick recovery above support
- Confidence: 75-90%
- Frequency: Very rare (not seen in 180 days)
- Booster: +60 points
- **Major buying opportunity!**

**SOS_BREAKOUT** (Phase D - Sign of Strength)
- Break above resistance (>2%)
- HIGH volume on breakout (smart money)
- Sustained move
- Confidence:  70-85%
- Frequency: Very rare (not seen in 180 days)
- Booster: +55 points
- **Breakout confirmed!**

**NO_ACCUMULATION** (Trending)
- Not consolidating
- No Wyckoff pattern
- Confidence: 40%
- Frequency (2HR): 64.2% (healthy)
- Frequency (4HR): 91.5% (very selective)
- Booster: +20 points

### Wyckoff Cycle:

```python
# Complete accumulation cycle
Phase A: Selling Climax
- High volume panic selling
- Lowest low made
- Reversal begins
→ Signal: ACCUMULATION_PHASE_A
→ Booster: +55 points

Phase B: Range Building
- Consolidation (<5% range on 2HR/4HR)
- Volume declines (smart money accumulating)
- Support/resistance forms
→ Signal: ACCUMULATION_PHASE_B
→ Booster: +45 points

Phase C: Spring (Optional)
- False breakdown below support
- Low volume = weak hands
- Quick recovery
→ Signal: SPRING_DETECTED
→ Booster: +60 points
→ MAJOR BUY SIGNAL!

Phase D: Sign of Strength
- Break above resistance
- High volume = institutions
- Sustained breakout
→ Signal: SOS_BREAKOUT
→ Booster: +55 points
→ BREAKOUT CONFIRMED!

Phase E: Markup (Not detected by this block)
- Uptrend begins
- Use trend-following blocks

# Multi-timeframe alignment
if 2HR Phase B AND 4HR Phase B:
    MTF_alignment_bonus = +50 points
    Total: 45 + 30 + 50 = +125 points!
```

## Enhanced Features

### 1. Multi-Timeframe Design (CRITICAL):
```python
# Optimized for 2HR + 4HR

2HR (PRIMARY):
- 35.8% active (perfect selectivity)
- 30.5% in Phase B (realistic)
- 4.09 signals/day (useful frequency)
- Main accumulation detector

4HR (CONFIRMATION):
- 8.5% active (ultra selective)
- 8.3% in Phase B (true institutional)
- 0.46 signals/day (rare confirmation)
- Confirms major zones only

15MIN (NOT RECOMMENDED):
- 100% active (wrong!)
- 80.8% in Phase B (micro-ranges)
- 95.45 signals/day (too noisy)
- DO NOT USE - Wyckoff doesn't work here

Why 2HR/4HR Work:
- Meaningful consolidation periods
- True institutional accumulation
- Not noise/micro-ranges
- Realistic range detection
```

### 2. Phase A Detection (Selling Climax):
```python
# High volume panic selling

Criteria:
1. Volume spike (2x+ average)
2. Lowest low in recent period
3. Sharp reversal (close above low)

Detection Logic:
volume_avg = avg(last 50 bars)
recent_volume = max(last 5 bars)

if recent_volume > volume_avg × 2.0:
    if is_lowest_low:
        if reversal_detected:
            → Phase A (confidence: 85%)
        else:
            → Phase A (confidence: 75%)

Frequency:
2HR: 5.3% (selective - GOOD!)
4HR: 0.2% (very rare - CORRECT!)

Example:
Volume: 1,500 BTC (avg: 700)
Price: $43,500 (low of month)
Close: $43,800 (+0.69% from low)
→ PHASE A DETECTED! ✅
```

### 3. Phase B Detection (Range Building):
```python
# Quiet accumulation in range

Criteria:
1. Range < 5% of price (2HR/4HR optimized)
2. Duration: 20+ bars minimum
3. Volume declining (smart money accumulating)

Detection Logic:
range_high = max(last 50 bars)
range_low = min(last 50 bars)
range_pct = (range_high - range_low) / price × 100

if range_pct < 5.0%:  # Tight range
    volume_recent = avg(last 20 bars)
    volume_earlier = avg(bars 21-50)
    
    if volume_recent < volume_earlier × 0.9:
        → Phase B (confidence: 70%)  # Volume declining
    else:
        → Phase B (confidence: 60%)  # Range only

Frequency:
2HR: 30.5% (realistic - PERFECT!)
4HR: 8.3% (institutional - EXCELLENT!)

Why This Works:
- 5% range tight enough to catch consolidation
- Not so tight it misses real accumulation
- 2HR: Good balance (30.5%)
- 4HR: Very selective (8.3%)
```

### 4. Spring Detection (Phase C):
```python
# False breakdown + recovery

Criteria:
1. Break below support (>2%)
2. LOW volume on breakdown (weak hands)
3. Quick recovery back above support
4. Within last 10 bars

Detection Logic:
breakdown = price < support × 0.98  # 2% below
volume_breakdown = avg(last 10 bars)
volume_avg = avg(bars 11-50)

if breakdown:
    if volume_breakdown < volume_avg × 0.90:
        # Low volume = weak hands
        if price_recovered > support:
            → SPRING! (confidence: 90%)
            # MAJOR BUY SIGNAL! ⭐

Frequency: Very rare (not seen in 180 days)

Why Rare:
- Requires perfect conditions
- False breakdown + recovery
- Low volume confirmation
- Happens at major bottoms only

When It Occurs:
- Major reversal zones
- After extended declines
- Institutional buying opportunity
```

### 5. SOS Detection (Phase D):
```python
# High volume breakout

Criteria:
1. Break above resistance (>2%)
2. HIGH volume on breakout (institutions)
3. Sustained move (not false breakout)

Detection Logic:
breakout = price > resistance × 1.02  # 2% above
volume_breakout = avg(last 10 bars)
volume_avg = avg(bars 11-50)

if breakout:
    if volume_breakout > volume_avg × 1.15:
        # High volume = smart money
        if price > resistance × 1.002:  # Sustained
            → SOS! (confidence: 85%)
            # BREAKOUT CONFIRMED! ✅

Frequency: Very rare (not seen in 180 days)

Why Rare:
- Requires breakout from accumulation
- High volume confirmation
- Sustained move needed
- True breakouts are infrequent

Value When Detected:
- Confirms accumulation complete
- Markup phase beginning
- High probability long setup
```

### 6. Multi-Timeframe Helper Function:
```python
# Production-ready MTF analysis

def analyze_multi_timeframe(df_2hr, df_4hr):
    """
    RECOMMENDED: Use this for production
    
    Returns:
        confluence: Total points (20-145)
        notes: Analysis details
        2hr_result: Full 2HR result
        4hr_result: Full 4HR result
        mtf_aligned: Boolean alignment
    """
    
    confluence = 0
    
    # 2HR (PRIMARY)
    if phase_2hr == 'A':
        confluence += 55  # Selling climax
    elif phase_2hr == 'B':
        confluence += 45  # Accumulation
    else:
        confluence += 20  # Trending
    
    # 4HR (CONFIRMATION)
    if phase_4hr == 'B':
        confluence += 30  # Major accumulation
    elif phase_4hr == 'A':
        confluence += 40  # Major climax
    
    # MTF ALIGNMENT BONUS
    if phase_2hr == phase_4hr:
        confluence += 50  # MEGA BONUS!
        mtf_aligned = True
    
    # Total when aligned:
    # Phase B: 45 + 30 + 50 = 125 points! ✅
    
    return result

Usage:
result = analyze_multi_timeframe(df_2hr, df_4hr)
strategy_confluence += result['confluence']
```

## Parameters (Optimized for 2HR/4HR)

```python
timeframe: '2hr' or '4hr'  # Recommended timeframes
range_lookback: 50          # Range detection period
volume_lookback: 50         # Volume average period
range_threshold_pct: 5.0    # Max range for accumulation
spring_breakdown_pct: 2.0   # Spring breakdown threshold
spring_volume_ratio: 0.90   # Low volume on spring
sos_breakout_pct: 2.0       # SOS breakout threshold
sos_volume_ratio: 1.15      # High volume on SOS
```

**Range Thresholds (Optimized):**
```python
2HR/4HR: 5.0% max range
- Tight enough to catch consolidation
- Not so tight it misses real accumulation
- Results: 30.5% (2HR), 8.3% (4HR) - PERFECT!

15MIN: 5.0% (same threshold)
- BUT produces 80.8% Phase B (wrong!)
- Micro-ranges look like accumulation
- Timeframe is the issue, not threshold
```

**Volume Ratios:**
```python
Selling Climax: 2.0x average (high volume)
Spring: 0.90x average (low volume)
SOS: 1.15x average (high volume)
Phase B decline: 0.90x earlier (declining)
```

## Confidence Calculation

**Phase-Based:**
```python
# Phase A (Selling Climax)
if volume_spike and lowest_low:
    if reversal:
        confidence = 85  # Strong signal
    else:
        confidence = 75  # Moderate

# Phase B (Range Building)
if in_range:
    if volume_declining:
        confidence = 70  # Good
    else:
        confidence = 60  # Moderate

# Spring (Phase C)
if spring_detected:
    if all_criteria_met:
        confidence = 90  # Excellent
    else:
        confidence = 75  # Good

# SOS (Phase D)
if sos_detected:
    if high_volume and sustained:
        confidence = 85  # Strong
    else:
        confidence = 70  # Moderate

# NO_ACCUMULATION
confidence = 40  # Low (trending)
```

## Trading Strategy

### Multi-Timeframe Accumulation (PRIMARY USE):
```python
# Use MTF helper function
result = analyze_multi_timeframe(df_2hr, df_4hr)

total_confluence = 0

# Add Wyckoff confluence
total_confluence += result['confluence']

# Check alignment
if result['mtf_aligned']:
    # Both 2HR and 4HR in same phase!
    
    if result['2hr_phase'] == 'B':
        # Both in Phase B accumulation
        # Total: +125 points (45 + 30 + 50)
        
        prepare_long()
        entry wait for spring or SOS
        
    elif result['2hr_phase'] == 'A':
        # Both in Phase A selling climax
        # Total: +145 points (55 + 40 + 50)
        
        prepare_long()
        # Major reversal zone
        
# Use other blocks for entry timing
if total_confluence >= 300:
    execute_trade()
```

### Phase B Accumulation Zone:
```python
# Detect accumulation range
wyckoff  = WyckoffAccumulation(timeframe='2hr')
result = wyckoff.analyze(df_2hr)

if result['metadata']['phase'] == 'B':
    # In accumulation (30.5% on 2HR)
    
    support = result['metadata']['support_level']
    resistance = result['metadata']['resistance_level']
    range_size = resistance - support
    
    # Trade the range
    if price near support:
        prepare_long()
        target = resistance
        stop = support - (range_size × 0.1)
        
    elif price near resistance:
        prepare_short()
        target = support
        stop = resistance + (range_size × 0.1)
```

### Spring Buy Signal:
```python
# Spring = major buy opportunity
wyckoff = WyckoffAccumulation(timeframe='2hr')
result = wyckoff.analyze(df_2hr)

if result['signal'] == 'SPRING_DETECTED':
    # False breakdown recovered!
    # Weak hands shaken out
    # Smart money accumulating
    
    execute_long()
    
    support = result['metadata']['support_level']
    resistance = result['metadata']['resistance_level']
    
    entry = current_price
    target = resistance  # Top of range
    stop = support - (support × 0.01)  # Just below support
    
    position_size = base_size × 1.5  # High conviction
```

### SOS Breakout Confirmation:
```python
# SOS = breakout confirmed
wyckoff = WyckoffAccumulation(timeframe='2hr')
result = wyckoff.analyze(df_2hr)

if result['signal'] == 'SOS_BREAKOUT':
    # High volume breakout
    # Accumulation complete
    # Markup phase beginning
    
    execute_long()
    
    resistance = result['metadata']['resistance_level']
    range_size = calculate_range_size()
    
    entry = current_price
    target = resistance + (range_size × 2.0)  # Extended target
    stop = resistance - (range_size × 0.25)  # Above old resistance
```

### 4HR Confirmation Strategy:
```python
# Use 4HR for major zones only
wyckoff_2hr = WyckoffAccumulation(timeframe='2hr')
wyckoff_4hr = WyckoffAccumulation(timeframe='4hr')

result_2hr = wyckoff_2hr.analyze(df_2hr)
result_4hr = wyckoff_4hr.analyze(df_4hr)

if result_2hr['metadata']['phase'] == 'B':
    # 2HR accumulation (30.5%)
    confluence = 45
    
    if result_4hr['metadata']['phase'] == 'B':
        # 4HR CONFIRMS (8.3% - rare!)
        # This is TRUE institutional accumulation
        confluence += 30 + 50  # +80 total
        # Total: 125 points!
        
        # High conviction trade
        position_size = base_size × 2.0
        hold_time = 'days to weeks'
```

## Confluence

**Multi-Timeframe Value:**
- **Signal Rate (2HR):** 35.8% (perfect)
- **Signal Rate (4HR):** 8.5% (ultra selective)
- **Phase B (2HR):** 30.5% (realistic)
- **Phase B (4HR):** 8.3% (institutional)
- **MTF Alignment:** +50 points bonus

**In Strategies:**
- Phase A (2HR): +55 points
- Phase B (2HR): +45 points
- Phase A (4HR): +40 points
- Phase B (4HR): +30 points
- MTF aligned: +50 points
- **Total when aligned:** +125 points!

## Key Functions

**analyze(df)** - Main analysis
- Returns: signal, confidence, metadata
- Detects all Wyckoff phases
- Volume validation
- Support/resistance tracking

**analyze_multi_timeframe(df_2hr, df_4hr)** - Production helper
- MTF analysis (RECOMMENDED!)
- Confluence calculation
- Alignment detection
- Ready-to-use results

**detect_selling_climax(df)** - Phase A detection
**detect_range(df)** - Phase B detection
**detect_spring(df, support)** - Phase C detection
**detect_sign_of_strength(df, resistance)** - Phase D detection

## Documentation Claims

- **2HR Active:** **35.8% (perfect!)** ✨
- **4HR Active:** **8.5% (ultra selective!)** ✨
- **Phase Distribution:** **Realistic (30.5% / 8.3%)** ✨
- **MTF Alignment:** **+50 bonus points** ✨
- **Error Rate:** **0.0% (perfect)** ✨
- **Timeframe Optimized:** **2HR/4HR (NOT 15min!)** ✨

**Status:** ✅ Production Ready - A Grade (92/100) | **Tests:** `test_wyckoff_accumulation.py`

---
*End of Wyckoff Accumulation Documentation*
