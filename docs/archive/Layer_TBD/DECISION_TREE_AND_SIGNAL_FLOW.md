# Layer TBD Decision Tree & Signal Generation Flow

**Version:** 2.0.1  
**Date:** December 28, 2025  
**Purpose:** Complete decision tree showing which config switches are used and how signals are generated

---

## Overview

Layer TBD uses a **4-stage scoring system** where switches control which features are enabled:

1. **Pattern Detection** (35% weight)
2. **Timing Analysis** (25% weight)  
3. **Level Analysis** (25% weight)
4. **Confirmation Checks** (15% weight)

**Final Signal Requirements:**
- Minimum confirmations met (config: `minimum_confirmations = 3`)
- At least one valid pattern detected
- Weighted confidence ≥ threshold

---

## Stage 1: Pattern Detection (35% Weight)

### Pattern Enable Switches (7 patterns)

```python
# From config
'enable_m_pattern': True          # ✓ USED
'enable_w_pattern': False         # ✗ DISABLED (Phase 3G)
'enable_multi_session_mw': True   # Used by M/W patterns
'enable_one_formation': True      # ✓ USED
'enable_weekend_trap': True       # ✓ USED
'enable_board_meeting': True      # ✓ USED
'enable_trapping_volume': True    # ✓ USED
```

### Pattern Detection Flow

```
generate_signal()
    ↓
_detect_patterns(data, current_price)
    ↓
    ├─ if enable_m_pattern: _detect_m_pattern()
    │   ├─ Check for pending retest (if mw_enable_retest_entry)
    │   ├─ Find peaks in price data
    │   ├─ Validate pattern length (8-80 bars)
    │   ├─ Validate peak symmetry (±25%)
    │   ├─ Validate pattern depth (3%-25%)
    │   ├─ Validate volume profile
    │   ├─ Check neckline break
    │   ├─ PHASE 3B: Check for pattern on 1H/4H (HTF targets)
    │   └─ Return PatternData or store pending
    │
    ├─ if enable_w_pattern: _detect_w_pattern()
    │   └─ (Same logic, inverted for double bottom)
    │
    ├─ if enable_weekend_trap: _detect_weekend_trap()
    │   ├─ Check if Monday within 4 hours of open
    │   ├─ Compare to Friday close
    │   └─ Detect ≥2% weekend move reversal
    │
    ├─ if enable_board_meeting: _detect_board_meeting()
    │   ├─ Find 6-24 bar consolidation
    │   ├─ Validate ≤2% price range
    │   ├─ if board_require_volume_buildup: check volume increase
    │   └─ Detect breakout with 1.5x volume
    │
    ├─ if enable_three_hits_rule: _detect_three_hits_reversal()
    │   ├─ Check weekly_high_touches ≥ 3 or weekly_low_touches ≥ 3
    │   ├─ Validate touch quality (wick ratio ≥60%)
    │   ├─ Validate volume escalation (≤1.2x)
    │   ├─ Validate touch spacing (≥4 hours)
    │   ├─ if three_hits_require_confirmation: store pending
    │   └─ Wait for confirmation bar
    │
    ├─ if enable_trapping_volume: _detect_trapping_volume()
    │   ├─ Check for ≥60% wick rejection
    │   ├─ Validate volume (1.5x-5.0x avg)
    │   ├─ Validate body size (≤40%)
    │   ├─ Validate close position
    │   ├─ if trap_require_level_proximity: check S/R
    │   ├─ if trap_require_trend_context: check trend
    │   ├─ if trap_require_confirmation: store pending
    │   └─ Wait for confirmation bar
    │
    └─ if enable_one_formation: _detect_one_formation()
        ├─ Find 20-40 bar consolidation
        ├─ Validate ≤3% range
        ├─ Detect 2x average range breakout
        └─ Require 2x average volume
```

### Pattern Detection Results

**Returns:** `List[PatternData]` (0 or more patterns found)

**If no patterns:** Signal = NEUTRAL (exit early)

---

## Stage 2: Timing Analysis (25% Weight)

### Timing Switches

```python
'enable_session_filter': True          # ✓ USED
'enable_weekly_cycle': True            # ✓ USED  
'enable_three_day_swing': True         # ✓ USED
'avoid_weekend_trading': True          # ✓ USED
'avoid_first_30min_london': True       # ✓ USED
```

### Timing Scoring Flow

```
_analyze_timing(data)
    ↓
    if not enable_session_filter:
        return 0.5  # Neutral score
    ↓
    _get_current_session(timestamp)
        ├─ _is_uk_dst(timestamp)  # Check UK BST/GMT
        ├─ _is_us_dst(timestamp)  # Check US EDT/EST
        └─ _get_session_times(timestamp)  # DST-adjusted times
    ↓
    Assign base score:
        ├─ ASIAN: 0.3
        ├─ LONDON: 0.9 (or 0.2 if first 30min and avoid_first_30min_london)
        ├─ NEW_YORK: 0.85
        ├─ OVERLAP: 1.0  ← Best timing
        └─ WEEKEND: 0.1 (if avoid_weekend_trading) or 0.4
    ↓
    if enable_three_day_swing:
        if day in [Mon, Tue, Wed]: +0.1
        if day in [Thu, Fri]: +0.1
    ↓
    return min(score, 1.0)
```

**Result:** `timing_score` (0.0 - 1.0)

---

## Stage 3: Level Analysis (25% Weight)

### Level Switches

```python
'enable_weekly_hl': True              # ✓ USED
'enable_daily_hl': True               # ✓ USED
'enable_session_hl': True             # ✓ USED (tracked but not scored)
'enable_three_hits_rule': True        # ✓ USED (for touch tracking)
'enable_liquidation_levels': True     # ✓ USED
'enable_fibonacci_levels': True       # ✗ NOT IMPLEMENTED YET
'enable_support_resistance': True     # ✓ USED (in trapping volume)
```

### Level Scoring Flow

```
_analyze_levels(data, current_price)
    ↓
    base_score = 0.5
    ↓
    if enable_weekly_hl and weekly_high/low exist:
        distance = min(|price - weekly_high|, |price - weekly_low|) / price
        if distance < 1%: +0.3
        if distance < 2%: +0.2
        if distance < 5%: +0.1
    ↓
    if enable_daily_hl and daily_high/low exist:
        distance = min(|price - daily_high|, |price - daily_low|) / price
        if distance < 0.5%: +0.2
    ↓
    if enable_liquidation_levels and liq_tracker exists:
        clusters = get_nearby_clusters(price, within 2%)
        if clusters found:
            boost = min(num_clusters × 0.2, 0.3)  ← Max +0.3
            score += boost
    ↓
    return min(score, 1.0)
```

**Result:** `level_score` (0.0 - 1.0)

---

## Stage 4: Confirmation Checks (15% Weight)

### Confirmation Switches

```python
'require_volume_confirmation': True     # ✓ USED
'require_trend_alignment': False        # ✗ DISABLED (balanced preset)
'require_multiple_timeframe': False     # ✗ DISABLED (not implemented yet)
'minimum_confirmations': 3              # ✓ USED (threshold)
```

### Confirmation Flow

```
_check_confirmations(data, patterns, timing_score, level_score)
    ↓
    confirmations = {}
    ↓
    confirmations['pattern'] = len(patterns) > 0  ← Always checked
    ↓
    confirmations['timing'] = timing_score > 0.6  ← Always checked
    ↓
    confirmations['level'] = level_score > 0.6    ← Always checked
    ↓
    if require_volume_confirmation:
        current_vol = data[-1]['volume']
        avg_vol = data[-20:]['volume'].mean()
        confirmations['volume'] = current_vol > avg_vol × 1.2
    else:
        confirmations['volume'] = True
    ↓
    if require_trend_alignment:
        trend = _determine_trend(data)  # SMA-50 based
        pattern_dir = patterns[0].direction
        confirmations['trend'] = (trend matches pattern_dir)
    else:
        confirmations['trend'] = True  ← Always True (balanced)
    ↓
    if require_multiple_timeframe:
        # NOT IMPLEMENTED YET
        confirmations['mtf'] = check_higher_timeframe_alignment()
    ↓
    return confirmations
```

**Result:** `confirmations` dict with True/False for each check

---

## Final Signal Composition

### Signal Generation Flow

```
_compose_signal(data, patterns, timing_score, level_score, confirmations, ...)
    ↓
    confirmations_met = sum(confirmations.values())  # Count True values
    ↓
    if confirmations_met < minimum_confirmations:
        return NEUTRAL signal  ← EXIT (insufficient confirmations)
    ↓
    if not patterns:
        return NEUTRAL signal  ← EXIT (no patterns detected)
    ↓
    best_pattern = max(patterns, key=lambda p: p.confidence)
    ↓
    Calculate weighted_confidence:
        = (pattern.confidence × 0.35)     # Pattern weight
        + (timing_score × 0.25)           # Timing weight
        + (level_score × 0.25)            # Level weight
        + (confirmations_met/total × 0.15) # Confirmation weight
    ↓
    direction = best_pattern.direction  # 'long' or 'short'
    ↓
    metadata = {
        'pattern_type': best_pattern.pattern_type,
        'session': current_session.value,
        'entry_price': best_pattern.entry_price,
        'stop_loss': best_pattern.stop_loss,
        'take_profit_1/2/3': ...,
        'confirmations_met': confirmations_met,
        ...
    }
    ↓
    return LayerSignal(
        direction=direction,
        confidence=weighted_confidence,
        strength=best_pattern.confidence,
        metadata=metadata
    )
```

---

## Complete Decision Tree (Pseudo-code)

```
ENTRY POINT: generate_signal(data, current_price, current_position)
    │
    ├─ UPDATE LEVELS
    │   ├─ if enable_weekly_hl: update weekly_high, weekly_low
    │   ├─ if enable_daily_hl: update daily_high, daily_low
    │   └─ if enable_three_hits_rule: track touches to levels
    │
    ├─ STAGE 1: DETECT PATTERNS (35%)
    │   ├─ if enable_m_pattern: check M-pattern
    │   ├─ if enable_w_pattern: check W-pattern (DISABLED)
    │   ├─ if enable_weekend_trap: check weekend trap
    │   ├─ if enable_board_meeting: check board meeting
    │   ├─ if enable_three_hits_rule: check three hits
    │   ├─ if enable_trapping_volume: check trapping volume
    │   └─ if enable_one_formation: check one formation
    │   │
    │   └─ Result: patterns = [PatternData, ...]
    │
    ├─ STAGE 2: ANALYZE TIMING (25%)
    │   ├─ if enable_session_filter:
    │   │   ├─ Determine current session (DST-aware)
    │   │   ├─ if avoid_first_30min_london: reduce London score
    │   │   └─ if avoid_weekend_trading: reduce weekend score
    │   ├─ if enable_three_day_swing: boost Mon-Fri
    │   └─ Result: timing_score (0.0-1.0)
    │
    ├─ STAGE 3: ANALYZE LEVELS (25%)
    │   ├─ if enable_weekly_hl: check distance to weekly H/L
    │   ├─ if enable_daily_hl: check distance to daily H/L
    │   ├─ if enable_liquidation_levels: check liquidation clusters
    │   └─ Result: level_score (0.0-1.0)
    │
    ├─ STAGE 4: CHECK CONFIRMATIONS (15%)
    │   ├─ pattern = len(patterns) > 0
    │   ├─ timing = timing_score > 0.6
    │   ├─ level = level_score > 0.6
    │   ├─ if require_volume_confirmation: volume > avg × 1.2
    │   ├─ if require_trend_alignment: trend matches direction
    │   └─ Result: confirmations = {checks: True/False}
    │
    ├─ COMPOSE FINAL SIGNAL
    │   ├─ confirmations_met = sum(confirmations.values())
    │   │
    │   ├─ if confirmations_met < minimum_confirmations (3):
    │   │   └─ return NEUTRAL
    │   │
    │   ├─ if not patterns:
    │   │   └─ return NEUTRAL
    │   │
    │   ├─ best_pattern = patterns[0]
    │   │
    │   ├─ weighted_confidence = 
    │   │     (pattern.confidence × 0.35) +
    │   │     (timing_score × 0.25) +
    │   │     (level_score × 0.25) +
    │   │     (confirmations_met/total × 0.15)
    │   │
    │   └─ return LayerSignal(
    │         direction = best_pattern.direction,
    │         confidence = weighted_confidence,
    │         metadata = {...}
    │       )
    │
    └─ END
```

---

## Switch Usage Summary

### ✅ ACTIVELY USED IN WALK-FORWARD

**Pattern Switches:**
- ✅ `enable_m_pattern` - M-pattern detection (22 trades in test)
- ✅ `enable_one_formation` - One formation breakouts
- ✅ `enable_weekend_trap` - Weekend trap reversals (1 trade)
- ✅ `enable_board_meeting` - Board meeting breakouts (0 in test period)
- ✅ `enable_three_hits_rule` - Three hits reversals (6 trades)
- ✅ `enable_trapping_volume` - Trapping volume (24 trades)
- ✅ `enable_multi_session_mw` - Used by M/W patterns

**Timing Switches:**
- ✅ `enable_session_filter` - Session-based scoring (OVERLAP=1.0, LONDON=0.9, NY=0.85, ASIAN=0.3)
- ✅ `enable_weekly_cycle` - Marks day of week in data
- ✅ `enable_three_day_swing` - Boosts Mon-Fri scores (+0.1)
- ✅ `avoid_weekend_trading` - Reduces weekend score (0.1 vs 0.4)
- ✅ `avoid_first_30min_london` - Reduces first 30min London score (0.2 vs 0.9)

**Level Switches:**
- ✅ `enable_weekly_hl` - Weekly high/low tracking & scoring
- ✅ `enable_daily_hl` - Daily high/low tracking & scoring
- ✅ `enable_session_hl` - Session H/L tracking (not scored yet)
- ✅ `enable_three_hits_rule` - Touch counting for reversals
- ✅ `enable_liquidation_levels` - Liquidation cluster proximity scoring
- ✅ `enable_support_resistance` - Used in trapping volume validation

**Confirmation Switches:**
- ✅ `require_volume_confirmation` - Checks volume > avg × 1.2
- ✅ `minimum_confirmations` - Requires ≥3 confirmations to trade

### ✗ DISABLED/NOT IMPLEMENTED

**Pattern Switches:**
- ✗ `enable_w_pattern` - **DISABLED** (Phase 3G - 14% WR, -$927 loss)

**Timing Switches:**
- *(All timing switches are actively used)*

**Level Switches:**
- ✗ `enable_fibonacci_levels` - Not implemented yet
- *(Session HL tracked but not scored yet)*

**Confirmation Switches:**
- ✗ `require_trend_alignment` - **DISABLED** (balanced preset - too restrictive)
- ✗ `require_multiple_timeframe` - Not fully implemented (HTF check exists for M/W only)

---

## Example Signal Flow (Trapping Volume Trade)

```
1. generate_signal() called with 15m data
   ↓
2. _update_levels():
   - weekly_high = $43,250
   - weekly_low = $42,100
   - current_price = $42,800
   ↓
3. _detect_patterns():
   - M-pattern: ✗ No double top
   - Weekend trap: ✗ Not Monday
   - Board meeting: ✗ No consolidation
   - Three hits: ✗ Only 2 touches
   - **Trapping volume: ✓ Found!**
     - Upper wick = 65% of range
     - Volume = 2.3x average
     - Body = 25% of range
     - Close at 30% (near low)
   - One formation: ✗ No breakout
   ↓
4. _analyze_timing():
   - Current session: LONDON (09:15 UTC)
   - Day: Tuesday
   - Base score: 0.9 (LONDON)
   - three_day_swing bonus: +0.1
   - **timing_score = 1.0**
   ↓
5. _analyze_levels():
   - Distance to weekly_high: 1.05% → +0.3
   - Distance to daily_high: 0.8% → +0.2
   - Liquidation clusters: 2 found → +0.2
   - **level_score = 1.0** (capped)
   ↓
6. _check_confirmations():
   - pattern: ✓ (trapping volume found)
   - timing: ✓ (1.0 > 0.6)
   - level: ✓ (1.0 > 0.6)
   - volume: ✓ (2.3x > 1.2x)
   - trend: ✓ (disabled, auto-pass)
   - **confirmations_met = 5/5**
   ↓
7. _compose_signal():
   - confirmations_met (5) ≥ minimum (3): ✓
   - patterns exist: ✓
   - best_pattern = trapping_volume (conf=0.70)
   - weighted_confidence = 
       (0.70 × 0.35) + (1.0 × 0.25) + (1.0 × 0.25) + (1.0 × 0.15)
     = 0.245 + 0.25 + 0.25 + 0.15
     = **0.895**
   ↓
8. **SIGNAL: SHORT**
   - Confidence: 0.895
   - Entry: $42,800
   - Stop: $43,050 (trap high + 0.5 ATR)
   - TP1: $42,500 (trap low - 0.5 range)
   - TP2: $42,200 (trap low - 1.0 range)
   - TP3: $41,900 (trap low - 1.5 range)
```

---

## Key Insights

### What Drives Signals?

1. **Pattern Detection (35%)** - Must find valid pattern first
2. **Confirmations (Threshold)** - Must meet ≥3 confirmations
3. **Timing (25%)** - Session quality matters (OVERLAP > LONDON > NY > ASIAN)
4. **Levels (25%)** - Proximity to key levels boosts score
5. **Volume (Check)** - Must exceed 1.2x average

### Current Active Patterns (Walk-Forward Results)

- ✅ **Trapping Volume**: 24 trades (most active)
- ✅ **One Formation**: 22 trades (profitable: +$78)
- ✅ **Three Hits**: 6 trades
- ✅ **Weekend Trap**: 1 trade
- ✗ **W-Pattern**: 0 trades (disabled)
- ✗ **M-Pattern**: 0 trades in 30-day test (no patterns met criteria)

### Why Some Switches Don't Affect Trade Count

- **Timing/Level switches** affect **score** not **detection**
- They influence confidence but don't block trades
- Only **pattern switches** and **confirmations** act as gates

---

## Configuration Tuning Guide

### To Increase Trade Frequency

```python
'minimum_confirmations': 2,  # Reduce from 3
'require_volume_confirmation': False,  # Disable volume check
'avoid_weekend_trading': False,  # Trade weekends
```

### To Improve Quality

```python
'minimum_confirmations': 4,  # Increase from 3
'require_trend_alignment': True,  # Enable trend filter
'board_require_volume_buildup': True,  # Stricter board meetings
```

### To Focus on Best Timing

```python
'avoid_first_30min_london': True,  # Skip choppy open
'enable_session_filter': True,  # Use session scoring
# Trade only when timing_score > 0.8 (LONDON/NY/OVERLAP)
```

---

**End of Decision Tree Documentation**
