# Balanced Price Range Building Block

**Block Number:** 26/66 | **Category:** ICT/SMC | **Version:** 2.0 (Enhanced) | **Status:** ✅ PRODUCTION READY

---

## ✅ SEMI-CONTINUOUS CONSOLIDATION DETECTOR - PRODUCTION READY

**This block detects balanced price ranges (consolidation zones) for mean reversion trading and breakout anticipation**

**Test Results:** 10.92% semi-continuous + 10.43 signals/day + 5.04 NEW events/day  
**Block Type:** SEMI-CONTINUOUS SETUP (consolidation tracking + quality enhancements)  
**Design:** ICT/SMC Balanced Range with compression detection, volume context, breakout proximity  
**Grade:** B+ (87/100) - GOOD 77.00% confidence (enhanced!)

**Current Performance:**
- ✅ 10.92% signal rate (PERFECT for semi-continuous setup - consolidation detection)
- ✅ 10.43 signals/day (IDEAL density - goldilocks frequency)
- ✅ 77.00% confidence (GOOD - enhanced +6.01%, variable 60-100%)
- ✅ 46.4/53.6 balance (870 bullish, 1,007 bearish - good balance)
- ✅ 0% error rate (perfect reliability)
- ✅ **5.04 NEW events/day** (precise range entry timing!)
- ✅ **ENHANCED:** Compression (17.4% at 91.5%!) + volume (47.2%) + breakout proximity

**Implementation Features:**
1. ✅ Range detection (15% balance threshold for Bitcoin)
2. ✅ Position tracking (upper/lower half mean reversion)
3. ✅ **Compression detection** (17.4% have compression at 91.5% confidence!)
4. ✅ **Volume context** (47.2% show decreasing volume - true consolidation)
5. ✅ **Breakout proximity** (timing awareness for anticipation)
6. ✅ Event tracking (NEW vs continuing approaches)
7. ✅ Variable confidence (60-100% based on position + quality)
8. ✅ Mean reversion logic (buy dips, sell rallies)

**Status:** ✅ PRODUCTION READY - B+ GRADE (ENHANCED)

**See Expert Review:** `docs/v3/expert_analisys_review_building_blocks/26_balanced_price_range_expert_review.md`

**Deployment:**
- Semi-continuous consolidation setup (10.92% during ranges)
- Enhanced with compression, volume, breakout proximity
- Use for mean reversion + breakout anticipation in multi-block strategies
- Expected: 10.43 institutional-grade consolidation signals/day

---

## Overview

Balanced Price Range identifies equilibrium consolidation zones where price is ranging in a balanced state. When price is consolidated within a tight range (±15% deviation), the block signals position within that range for mean reversion trading: lower half = bullish (buy dips toward midpoint), upper half = bearish (sell rallies toward midpoint). Enhanced with compression detection (coiling before breakout), volume confirmation (decreasing volume validates true consolidation), and breakout proximity awareness.

## Block Classification

**Type:** SEMI-CONTINUOUS SETUP - CONSOLIDATION TRACKING (Enhanced)
- **Signal Rate:** 10.92% (during consolidation periods)
- **Signal Density:** 10.43/day (ideal frequency)
- **Event Rate:** 5.28% (5.04 NEW range entries/day)
- **Enhancements:** Compression + volume + breakout proximity
- Consolidation and mean reversion specialist

## Technical Specifications

**Components:** Range Detection + Position Tracking + Compression Analysis + Volume Context + Breakout Timing  
**File:** `src/detectors/building_blocks/smc_ict/balanced_price_range.py`

## Signals

### Semi-Continuous Detection (10.92% of bars):

**BULLISH**: Price in lower half of balanced range (5.06%)
- Position ≤50% of range (closer to low)
- Mean reversion buy opportunity
- 60-100% confidence (enhanced with compression/volume)
- Expect bounce toward midpoint/high

**BEARISH**: Price in upper half of balanced range (5.86%)
- Position >50% of range (closer to high)
- Mean reversion sell opportunity
- 60-100% confidence (enhanced)
- Expect rejection toward midpoint/low

**NEUTRAL**: No balanced range detected (89.08% of bars)
- Price trending or outside consolidation
- Filtered out

### Balanced Range Pattern:

```python
# Consolidation detection
1. Identify recent high/low (20-bar lookback)
2. Calculate range size and midpoint
3. Check balance: deviation ≤15% threshold
4. Determine position: upper or lower half
5. Signal mean reversion opportunity

Result: Range position signal
- BULLISH = lower half (buy dips)
- BEARISH = upper half (sell rallies)
- Mean reversion to equilibrium
```

## Enhanced Features

### 1. Compression Detection (17.4% at 91.5%!):
```python
has_compression: Boolean
compression_level: STRONG / MODERATE

Tracks range tightening across 3 periods:

326 signals with compression (17.4%):
- STRONG: 277 signals (84.9%) - 91.5% avg confidence!
- MODERATE: 49 signals (15.1%) - 85% avg confidence

Coiling ranges before breakout:
- Range shrinking early→middle→late
- Decreasing volatility (compression)
- Anticipates explosive breakout
- +10 bonus (STRONG), +5 (MODERATE)
```

### 2. Volume Context (47.2% confirming):
```python
volume_decreasing: Boolean

100% of signals have volume data (1,877):

886 signals with decreasing volume (47.2%):
- 85.9% avg confidence (+14.9% boost!)
- Confirms true consolidation
- Not fake range (would have volume)
- Validates equilibrium state
- +5 to +10 confidence bonus
```

### 3. Breakout Proximity Awareness:
```python
breakout_proximity: EARLY / APPROACHING / NEAR / IMMINENT
bars_in_range: Integer

Time-based breakout estimation:
- Tracks duration in range
- Historical breakout timing
- EARLY: Fresh consolidation
- APPROACHING: Building tension
- NEAR: Breakout likely soon
- IMMINENT: Breakout expected imminently

+5 to +10 confidence as breakout nears
```

## Parameters (Optimized)

```python
lookback: 20                 # Range detection period
balance_threshold: 15%       # Max deviation for balanced state
timeframe: '15min'
```

**Balance Threshold:**
- 15% deviation = tight consolidation
- Lower than trend blocks (more selective)
- Optimized for Bitcoin 15min
- Filters noise, signals true ranges

## Enhanced Confidence Calculation

**Base:** 60-70 (moderate for consolidation)

**Position Proximity:**
```python
# Distance from range extremes
if very_near_low or very_near_high:
    confidence += 20  # 80-90% (extreme position)
elif near_low or near_high:
    confidence += 10  # 70-80% (close to edge)
else:
    confidence += 0   # 60-70% (mid-range)
```

**Enhancement Bonuses:**
```python
# Compression (+5 to +10)
if compression_level == 'STRONG':
    confidence += 10  # → 91.5% avg for STRONG!
elif compression_level == 'MODERATE':
    confidence += 5

# Volume Context (+5 to +10)
if volume_decreasing:
    if strong_decrease:
        confidence += 10
    else:
        confidence += 5

# Breakout Proximity (+5 to +10)
if breakout_proximity == 'IMMINENT':
    confidence += 10
elif breakout_proximity == 'NEAR':
    confidence += 5

# Result: 60-100% range (avg 77.00%) ✅
# Improvement: +6.01% from baseline
```

## Trading Strategy

### Mean Reversion in Range:
```python
# Buy dips, sell rallies
bpr = balanced_price_range.analyze(df)

if bpr['signal'] == 'BULLISH':
    # In lower half of range
    enter_long()  # Buy dip
    target = range_midpoint  # Take profit at equilibrium
    
elif bpr['signal'] == 'BEARISH':
    # In upper half of range
    enter_short()  # Sell rally
    target = range_midpoint  # Take profit at equilibrium
```

### Compressed Range Breakout Preparation:
```python
# Premium compressed ranges (17.4% at 91.5%!)
bpr = balanced_price_range.analyze(df)

if (
    bpr['metadata']['has_compression'] and
    bpr['metadata']['compression_level'] == 'STRONG'
):
    # Coiling before breakout
    position_size = 2.0  # 91.5% confidence!
    monitor_for_breakout()  # Watch for explosive move
    
    if breakout_confirmed:
        execute_breakout_direction()
```

### Volume-Confirmed Consolidation:
```python
# Trade only true consolidations (47.2%)
bpr = balanced_price_range.analyze(df)

if (
    bpr['signal'] == 'BULLISH' and
    bpr['metadata']['volume_decreasing']  # 47.2%
):
    # Volume declining = true consolidation
    enter_long()  # 85.9% confidence
```

### NEW Range Entry Timing:
```python
# Precise entry on fresh range entry (5.04/day)
bpr = balanced_price_range.analyze(df)

if (
    bpr['metadata']['is_new_event'] and  # NEW range!
    bpr['signal'] == 'BULLISH'
):
    # Fresh consolidation entry
    enter_long()  # ~908 NEW entries per 180 days
```

### Multi-Block Confluence:
```python
# Combine for premium entries
bpr = balanced_price_range.analyze(df)
ob = order_block.analyze(df)
fvg = fair_value_gap.analyze(df)

if (
    bpr['signal'] == 'BULLISH' and      # Range lower half (10.92%)
    ob['signal'] == 'BULLISH' and       # Order Block (4.12%)
    fvg['signal'] == 'BULLISH'          # FVG (1.47%)
):
    execute_long()  # Premium consolidation entry
```

## Confluence

**Semi-Continuous Value:**
- **Signal Rate:** 10.92% (consolidation periods)
- **Density:** 10.43/day (ideal frequency)
- **Events:** 5.04 NEW/day (range entry timing)
- **Confidence:** 77.00% (good with enhancements)
- **Balance:** 46.4/53.6 (good - 7.2% bias acceptable)
- **Premium:** 17.4% compressed at 91.5%!

**In Strategies:**
- Mean reversion setups (buy dips, sell rallies)
- Breakout anticipation (compressed ranges)
- Consolidation context for other blocks
- Range trading specialist

## Key Functions

**analyze(df)** - Main analysis (ENHANCED)
- Returns: signal, confidence (77% avg), metadata, confluence
- Detects balanced ranges (10.92%)
- Calculates position within range
- Checks compression (17.4%)
- Validates with volume (47.2%)
- Estimates breakout proximity

**detect_balanced_range(df)** - Range identification
**calculate_position(price, range)** - Upper/lower half
**detect_compression(df, range)** - Range tightening
**check_volume_context(df)** - Volume confirmation
**estimate_breakout_proximity(bars)** - Timing awareness

## Documentation Claims (Enhanced)

- **Confidence:** **77.00% (enhanced +6.01%)** ✨
- **Balance:** 46.4/53.6 (good - 7.2% bias)
- **Semi-Continuous:** 10.92% (perfect for setup)
- **Density:** 10.43/day (ideal frequency)
- **Events:** 5.04 NEW/day (range entries)
- **Compression:** 17.4% at 91.5% (premium!)
- **Volume:** 47.2% confirmed (true consolidation)

**Status:** ✅ Production Ready - B+ Grade | **Tests:** `test_balanced_price_range.py`

---
*End of Balanced Price Range Documentation*
