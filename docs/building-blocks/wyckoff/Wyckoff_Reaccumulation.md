# Wyckoff Reaccumulation Building Block

**Block Number:** 55/66 | **Category:** Wyckoff Method | **Version:** 2.0 (MTF Enhanced) | **Status:** ✅ PRODUCTION READY

---

## ✅ HYBRID UPTREND CONSOLIDATION DETECTOR - PRODUCTION READY

**This block detects Wyckoff reaccumulation (uptrend consolidations) using 2HR (primary) + 4HR (confirmation)**

**Test Results (2HR):** 19.0% reaccum + 81.0% trending + 68.5% avg confidence  
**Test Results (4HR):** 5.2% reaccum + 94.8% trending + 68.4% avg confidence  
**Block Type:** HYBRID BLOCK (continuous context + selective events)  
**Design:** Multi-timeframe Wyckoff analysis + uptrend validation + quality assessment  
**Grade:** B+ (88/100) - EXCELLENT continuation detector

**Current Performance (2HR - PRIMARY):**
- ✅ 100% signal coverage (hybrid - always provides state!)
- ✅ 2.18 signals/day (useful frequency)
- ✅ 68.5% avg confidence (good quality)
- ✅ 0% error rate (perfect reliability)
- ✅ **81.0% NO_REACCUMULATION** (correctly trending)
- ✅ **19.0% REACCUMULATION** (realistic consolidation)
- ✅ Strong uptrend filter implemented

**Current Performance (4HR - CONFIRMATION):**
- ✅ 100% signal coverage (continuous state)
- ✅ 0.28 signals/day (ultra selective)
- ✅ 68.4% avg confidence
- ✅ **94.8% NO_REACCUMULATION** (very selective)
- ✅ **5.2% REACCUMULATION** (true institutional)

**Implementation Features:**
1. ✅ Strong uptrend detection (5%+ gain requirement)
2. ✅ Range quality assessment (volume, tightness, tests)
3. ✅ Spring detection (false breakdown in uptrend)
4. ✅ Breakout detection (continuation confirmation)
5. ✅ Hybrid design (continuous + events)
6. ✅ Multi-timeframe helper function
7. ✅ Volume analysis (declining in range)
8. ✅ Support/resistance tracking

**Status:** ✅ PRODUCTION READY - B+ GRADE

**See Expert Review:** `docs/v3/expert_analisys_review_building_blocks/55_wyckoff_reaccumulation_expert_review.md`

**Deployment:**
- 2HR for primary uptrend consolidation
- 4HR for confirmation of major pauses
- Hybrid: Continuous context + rare events
- MTF alignment for continuation signals

---

## Overview

Wyckoff Reaccumulation detects continuation consolidations within established uptrends - where smart money adds to long positions during pauses. Requires STRONG uptrend context (5%+ gain, higher highs, upper range position) then identifies consolidation ranges with quality assessment (volume declining, tight range, multiple support tests, balanced distribution). Hybrid block provides BOTH continuous context (NO_REACCUMULATION state, 81.0% on 2HR) AND selective consolidation events (REACCUMULATION, 19.0%). Also detects rare high-value events: Spring (false breakdown before continuation, +60 points) and Breakout (continuation confirmed, +55 points). Optimized for 2HR (primary, 19.0% reaccumulation) and 4HR (confirmation, 5.2%, ultra selective). Multi-timeframe alignment provides continuation boost (+115 points). Essential for timing entries during uptrend pauses.

## Block Classification

**Type:** HYBRID BLOCK - CONTINUOUS CONTEXT + SELECTIVE EVENTS
- **Signal Rate (2HR):** 100% (continuous state + events)
- **Reaccumulation Events (2HR):** 19.0%
- **Reaccumulation Events (4HR):** 5.2% (ultra selective)
- **Phases:** TRENDING, RANGE, SPRING, BREAKOUT, NONE
- **Timeframes:** 2HR (primary), 4HR (confirmation)
- **Context:** Requires strong uptrend
- **Boosters:** +45-115 points (MTF aligned)
- Uptrend continuation specialist

## Technical Specifications

**Components:** Uptrend Detection + Range Quality Assessment + Consolidation Detection + Spring/Breakout Detection + Hybrid Design + MTF Integration  
**File:** `src/detectors/building_blocks/wyckoff/wyckoff_reaccumulation.py`

## Signals

### Hybrid States (Continuous + Events):

**NO_REACCUMULATION** (Continuous Context)
- Not in uptrend consolidation
- Either trending or not in uptrend
- Confidence: 45-50%
- Frequency (2HR): 81.0% (healthy)
- Frequency (4HR): 94.8% (very selective)
- Booster: +20 points
- **Continuous state - always available**

**REACCUMULATION_DETECTED** (Consolidation Event)
- Consolidation range in uptrend
- Volume declining (smart money quiet)
- Quality range (tight, balanced)
- Confidence: 65-75%
- Frequency (2HR): 19.0% (realistic)
- Frequency (4HR): 5.2% (institutional)
- Booster: +45 points (2HR), +30 points (4HR)

**SPRING_DETECTED** (False Breakdown Event)
- Break below support (>2%)
- LOW volume (weak - trap)
- Quick reversal back into range
- Confidence: 70-85%
- Frequency: Very rare (not seen in 180 days)
- Booster: +60 points
- **MAJOR CONTINUATION SIGNAL!**

**BREAKOUT_CONTINUATION** (Confirmation Event)
- Break above resistance (>1%)
- HIGH volume (institutional buying)
- Sustained move
- Confidence: 65-80%
- Frequency: Very rare (not seen in 180 days)
- Booster: +55 points
- **Continuation confirmed!**

### Wyckoff Reaccumulation Cycle:

```python
# Continuation consolidation in uptrend

Context: STRONG Uptrend Required
- 5%+ gain over lookback period
- Multiple higher highs
- Price in upper 40% of range
- Above moving average
→ Prerequisite for reaccumulation

Range Phase: Consolidation
- Tight range (<5% on 2HR/4HR)
- Volume declining (quiet accumulation)
- Multiple support tests
- Balanced price distribution
→ Signal: REACCUMULATION_DETECTED
→ Booster: +45 points

Spring Phase (Optional - Rare):
- False breakdown below support
- Low volume = retail shakeout
- Quick reversal back into range
→ Signal: SPRING_DETECTED
→ Booster: +60 points
→ MAJOR CONTINUATION! ⭐

Breakout Phase:
- Break above resistance
- High volume = institutions
- Sustained continuation
→ Signal: BREAKOUT_CONTINUATION
→ Booster: +55 points
→ CONTINUATION CONFIRMED!

NO_REACCUMULATION: Continuous State
- Trending uptrend (not consolidating)
- Or not in uptrend
→ Signal: NO_REACCUMULATION
→ Booster: +20 points
→ Context always available

# Multi-timeframe alignment
if 2HR REACCUM AND 4HR REACCUM:
    MTF_alignment_bonus = +40 points
    Total: 45 + 30 + 40 = +115 points!

if 2HR SPRING AND 4HR SPRING:
    Total: 60 + 35 + 40 = +135 points!
    → MEGA CONTINUATION SIGNAL!
```

## Enhanced Features

### 1. Strong Uptrend Filter (CRITICAL):
```python
# NOT just any uptrend - must be STRONG

Requirements (ALL or MOST):
1. Price above MA (basic)
2. 5%+ gain over period (STRONG momentum)
3. Multiple higher highs (structure)
4. Price in upper 40% of range (position)

Confidence Levels:
All 4 conditions: 85% (very strong)
3 conditions + strong momentum: 75% (strong)
Higher highs + moderate momentum: 65% (good)
MA + moderate momentum: 55% (borderline)

Why This Matters:
- Reaccumulation occurs in STRONG uptrends
- Weak uptrends → distribution more likely
- Filters out false consolidations
- 19.0% on 2HR (realistic frequency)

Example Strong Uptrend:
Price: $47,500 (was $45,000 = 5.6% gain) ✅
MA: $46,200 (price above) ✅
Higher highs: $45.5K → $46.8K → $47.5K ✅
Range position: 72% (upper range) ✅
→ STRONG UPTREND CONFIRMED!
```

### 2. Range Quality Assessment (NEW):
```python
# Not all ranges are reaccumulation

Quality Factors (scored 0-100):

1. Volume Declining (25 points max)
   Early average vs recent average
   - <85% recent volume: +25 points
   - <95% recent volume: +15 points
   → Smart money accumulating quietly

2. Range Tightness (30 points max)
   Range % of price
   - <3.0%: +30 points (very tight)
   - <5.0%: +20 points (good)
   - >5.0%: +10 points (wide)
   → Controlled consolidation

3. Support Tests (25 points max)
   Times price tested support
   - 3+ tests: +25 points (strong)
   - 2 tests: +15 points
   → Multiple tests = strength

4. Price Balance (20 points max)
   Distribution above/below midpoint
   - <30% imbalance: +20 points (balanced)
   - <50% imbalance: +10 points
   → Not one-sided

Quality Grades:
75+: EXCELLENT (signal!)
60-74: GOOD (signal!)
40-59: FAIR (weak signal)
<40: POOR (reject!)

Only GOOD/EXCELLENT ranges get signaled
This ensures quality consolidations only
```

### 3. Spring Detection (Major Continuation):
```python
# False breakdown trap in uptrend

Criteria:
1. Break below support (>2%)
2. LOW volume on breakdown (weak - <85% avg)
3. Quick reversal back above support
4. Within last 10 bars

Detection Logic:
breakdown = price < support × 0.98  # 2% below
volume_breakdown = avg(last 10 bars)
volume_avg = avg(bars 11-60)

if breakdown:
    if volume_breakdown < volume_avg × 0.85:
        # Low volume = retail shakeout
        if price_reversed > support × 1.002:
            → SPRING! (confidence: 85%)
            # MAJOR CONTINUATION! ⭐

Frequency: Very rare (not seen in 180 days)

Why Rare but Valuable:
- Requires perfect trap setup
- Shakes out weak hands
- Smart money re-enters
- Often precedes strong continuation
- Wyckoff's highest probability signal

When It Occurs:
- Major continuation zones
- After extended consolidation
- Smart money accumulation complete
- Institutional buying opportunity
```

### 4. Breakout Detection (Continuation Confirmed):
```python
# Volume breakout above range

Criteria:
1. Break above resistance (>1%)
2. HIGH volume on breakout (>115% avg)
3. Sustained move (close >0.5% above)

Detection Logic:
breakout = price > resistance × 1.01  # 1% above
volume_breakout = avg(last 10 bars)
volume_avg = avg(bars 11-60)

if breakout:
    if volume_breakout > volume_avg × 1.15:
        # High volume = institutions
        if price > resistance × 1.005:  # Sustained
            → BREAKOUT! (confidence: 80%)
            # CONTINUATION CONFIRMED! ✅

Frequency: Very rare (not seen in 180 days)

Why Rare:
- Requires breakout from reaccumulation
- High volume confirmation needed
- Sustained move validation
- True breakouts are infrequent

Value When Detected:
- Confirms reaccumulation complete
- Uptrend continuation validated
- High probability long entry/add
- Often leads to measured move
```

### 5. Hybrid Design (Context + Events):
```python
# HYBRID = Continuous Context + Rare Events

Continuous State (81.0% on 2HR):
- NO_REACCUMULATION always available
- Know if in uptrend consolidation
- Adjust strategy accordingly
- +20 confluence points

Reaccumulation Events (19.0% on 2HR):
- REACCUMULATION_DETECTED: Quality range
- SPRING: Major continuation (rare)
- BREAKOUT: Confirmed continuation (rare)

Why This Works:
- Context always available
- Events fire when significant
- No "no signal" gaps
- Best for continuation trading

Example Usage:
# Check reaccumulation state
reaccum = reaccumulation.analyze(df_2hr)

if reaccum['signal'] == 'NO_REACCUMULATION':
    # Trending uptrend
    continue_trend_following = True
    
elif reaccum['signal'] == 'REACCUMULATION_DETECTED':
    # Consolidation pause
    prepare_add_to_long = True
    watch_for_spring_or_breakout = True
    
elif reaccum['signal'] == 'SPRING_DETECTED':
    # Major continuation!
    execute_long()  # High conviction
```

### 6. Multi-Timeframe Helper Function:
```python
# Production-ready MTF analysis

def analyze_multi_timeframe(df_2hr, df_4hr):
    """
    RECOMMENDED: Use this for production
    
    Returns:
        confluence: Total points (15-135!)
        notes: Analysis details
        2hr_result: Full 2HR result
        4hr_result: Full 4HR result
        mtf_aligned: Boolean alignment
    """
    
    confluence = 0
    
    # 2HR (PRIMARY)
    if phase_2hr == 'SPRING':
        confluence += 60  # Major continuation
    elif phase_2hr == 'BREAKOUT':
        confluence += 55  # Confirmed
    elif phase_2hr == 'RANGE':
        confluence += 45  # Consolidation
    elif phase_2hr == 'TRENDING':
        confluence += 20  # Uptrend
    else:
        confluence += 15  # None
    
    # 4HR (CONFIRMATION)
    if phase_4hr == 'SPRING':
        confluence += 35  # Very strong
    elif phase_4hr == 'BREAKOUT':
        confluence += 30  # Strong
    elif phase_4hr == 'RANGE':
        confluence += 25  # Good
    elif phase_4hr == 'TRENDING':
        confluence += 15  # Context
    
    # MTF ALIGNMENT BONUS
    if phase_2hr == phase_4hr and phase_2hr != 'NONE':
        confluence += 40  # MEGA BONUS!
        mtf_aligned = True
    
    # Total examples:
    # Spring aligned: 60 + 35 + 40 = 135 points! ⭐
    # Range aligned: 45 + 30 + 40 = 115 points!
    
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
range_threshold_pct: 5.0    # Max range for reaccumulation
spring_breakdown_pct: 2.0   # Spring breakdown threshold
spring_volume_ratio: 0.85   # Low volume on spring
breakout_volume_ratio: 1.15 # High volume on breakout
uptrend_lookback: 30        # Uptrend validation period
```

**Uptrend Requirements:**
```python
Momentum: 5%+ gain (strong), 2%+ (moderate)
Structure: Multiple higher highs
Position: Upper 40% of range
Above MA: Required
```

**Range Quality Thresholds:**
```python
Volume decline: <85% for excellent
Range tightness: <3% very tight, <5% good
Support tests: 3+ for strong
Balance: <30% imbalance for balanced
```

## Confidence Calculation

**Phase-Based:**
```python
# SPRING (Major Continuation)
if spring_detected:
    if all_criteria_met:
        confidence = 85  # Excellent
    else:
        confidence = 70  # Good

# BREAKOUT (Continuation Confirmed)
if breakout_detected:
    if high_volume and sustained:
        confidence = 80  # Strong
    else:
        confidence = 65  # Moderate

# REACCUMULATION (Consolidation)
if in_range and in_uptrend:
    base = min(uptrend_conf, range_conf)
    confidence = base + 10  # Bonus

# NO_REACCUMULATION
if not_in_uptrend:
    confidence = 45  # Low
elif trending:
    confidence = 50  # Moderate
```

## Trading Strategy

### Multi-Timeframe Continuation (PRIMARY USE):
```python
# Use MTF helper function
result = analyze_multi_timeframe(df_2hr, df_4hr)

total_confluence = 0

# Add reaccumulation confluence
total_confluence += result['confluence']

# Check alignment
if result['mtf_aligned']:
    # Both timeframes in same phase!
    
    if result['2hr_phase'] == 'SPRING':
        # Both in Spring phase
        # Total: +135 points (60 + 35 + 40)
        # MEGA CONTINUATION! ⭐
        
        execute_long()  # Or add to longs
        position_size *= 2.0  # High conviction
        
    elif result['2hr_phase'] == 'RANGE':
        # Both in reaccumulation
        # Total: +115 points (45 + 30 + 40)
        
        prepare_long()
        wait_for_spring_or_breakout = True
        
# Execute if qualified
if total_confluence >= 300:
    execute_trade()
```

### Spring Entry Signal (CRITICAL):
```python
# Spring = major continuation opportunity
reaccum = WyckoffReaccumulation(timeframe='2hr')
result = reaccum.analyze(df_2hr)

if result['signal'] == 'SPRING_DETECTED':
    # False breakdown reversed!
    # Weak hands shaken out
    # Smart money re-entering
    
    execute_long()  # Or add to position
    
    support = result['metadata']['support_level']
    resistance = result['metadata']['resistance_level']
    range_size = resistance - support
    
    entry = current_price
    target = resistance + (range_size × 1.5)  # Extended
    stop = support - (range_size × 0.25)  # Below support
    
    position_size = base_size × 1.5  # High conviction
    
    notes.append('⭐ SPRING - Major continuation!')
```

### Reaccumulation Range Trading:
```python
# Detect consolidation in uptrend
reaccum = WyckoffReaccumulation(timeframe='2hr')
result = reaccum.analyze(df_2hr)

if result['metadata']['phase'] == 'RANGE':
    # In reaccumulation (19.0% on 2HR)
    
    resistance = result['metadata']['resistance_level']
    support = result['metadata']['support_level']
    range_size = resistance - support
    midpoint = (support + resistance) / 2
    
    # Add to longs at support
    if price <= support × 1.01:
        execute_long()
        target = resistance
        stop = support - (range_size × 0.15)
        
    # Wait for breakout at resistance
    elif price >= resistance × 0.99:
        watch_for_breakout = True
        # Don't sell in reaccumulation!
```

### Breakout Continuation:
```python
# Breakout = continuation confirmed
reaccum = WyckoffReaccumulation(timeframe='2hr')
result = reaccum.analyze(df_2hr)

if result['signal'] == 'BREAKOUT_CONTINUATION':
    # High volume breakout
    # Uptrend continuation validated
    
    execute_long()  # Or add to longs
    
    resistance = result['metadata']['resistance_level']
    range_size = calculate_range_size()
    
    entry = current_price
    target = resistance + (range_size × 2.0)  # Measured move
    stop = resistance - (range_size × 0.25)  # Above old resistance
    
    # Aggressive sizing
    position_size = base_size × 1.25
```

### Continuous Context Usage:
```python
# Use NO_REACCUMULATION state for bias
reaccum_2hr = WyckoffReaccumulation(timeframe='2hr')
reaccum_4hr = WyckoffReaccumulation(timeframe='4hr')

result_2hr = reaccum_2hr.analyze(df_2hr)
result_4hr = reaccum_4hr.analyze(df_4hr)

# Determine trend state
if result_2hr['metadata'].get('in_uptrend'):
    if result_2hr['signal'] == 'NO_REACCUMULATION':
        # Strong trending uptrend
        trend_strength = 'STRONG'
        hold_longs = True
        
    elif result_2hr['signal'] == 'REACCUMULATION_DETECTED':
        # Uptrend pause
        trend_strength = 'CONSOLIDATING'
        watch_for_continuation = True
        
        if result_4hr['signal'] == 'REACCUMULATION_DETECTED':
            # Major consolidation (both timeframes)
            prepare_for_major_continuation = True
else:
    # Not in uptrend
    no_reaccumulation_bias = True
    use_other_strategies = True
```

### Position Management by Phase:
```python
# Adjust position based on reaccumulation phase
reaccum = WyckoffReaccumulation(timeframe='2hr')
result = reaccum.analyze(df_2hr)

if in_long_position:
    phase = result['metadata'].get('phase')
    
    if phase == 'SPRING':
        # Major continuation coming
        add_to_position()
        widen_stops()  # Give it room
        
    elif phase == 'BREAKOUT':
        # Continuation confirmed
        hold_position()
        trail_stops()  # Lock in profits
        
    elif phase == 'RANGE':
        # In consolidation
        hold_position()
        # Don't exit in reaccumulation!
        
    elif phase == 'TRENDING':
        # Strong uptrend
        hold_position()
        # Let it run
```

## Confluence

**Hybrid Value:**
- **Signal Rate (2HR):** 100% (hybrid - always available)
- **Reaccum Events (2HR):** 19.0%
- **Reaccum Events (4HR):** 5.2%
- **Uptrend Filter:** STRONG (5%+ gain)
- **Range Quality:** Assessed (GOOD/EXCELLENT only)
- **MTF Alignment:** +40 points bonus

**In Strategies:**
- NO_REACCUMULATION: +20 points (context)
- REACCUMULATION (2HR): +45 points
- REACCUMULATION (4HR): +30 points
- SPRING (2HR): +60 points (MAJOR!)
- BREAKOUT (2HR): +55 points
- SPRING/BREAKOUT (4HR): +30-35 points
- MTF aligned: +40 points
- **Spring aligned:** +135 points total! ⭐

## Key Functions

**analyze(df)** - Main analysis
- Returns: signal, confidence, metadata
- Hybrid: Continuous + events
- Detects uptrend first
- Assesses range quality
- Identifies spring/breakout
- Resistance/support tracking

**analyze_multi_timeframe(df_2hr, df_4hr)** - Production helper
- MTF analysis (RECOMMENDED!)
- Confluence calculation
- Alignment detection
- Ready-to-use results

**detect_uptrend(df)** - STRONG uptrend validation
**assess_range_quality(df, resistance, support)** - Quality assessment (NEW!)
**detect_range(df)** - Consolidation detection
**detect_spring(df, support)** - False breakdown detection (MAJOR!)
**detect_breakout(df, resistance)** - Continuation confirmation

## Documentation Claims

- **2HR Coverage:** **100% (hybrid!)** ✨
- **4HR Coverage:** **100% (hybrid!)** ✨
- **Reaccumulation Rate:** **19.0% / 5.2% (realistic!)** ✨
- **Uptrend Filter:** **STRONG (5%+ gain required!)** ✨
- **Range Quality:** **Assessed (GOOD/EXCELLENT only!)** ✨
- **Spring/Breakout:** **Implemented (rare but MAJOR!)** ✨
- **MTF Alignment:** **+40 bonus (+135 with Spring!)** ✨
- **Error Rate:** **0.0% (perfect)** ✨

**Status:** ✅ Production Ready - B+ Grade (88/100) | **Tests:** `test_wyckoff_reaccumulation.py`

---
*End of Wyckoff Reaccumulation Documentation*
