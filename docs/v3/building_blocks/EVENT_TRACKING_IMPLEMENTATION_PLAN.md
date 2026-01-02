# Event Tracking Implementation Plan

**Date:** 2026-01-02  
**Status:** IN PROGRESS  
**Completed:** 2/7 blocks (BOS ✅, MSS ✅)  
**Remaining:** 5 high/medium priority blocks

---

## Signal Rate Analysis Results

Analysis of all 67 blocks identified **7 blocks** needing event tracking:

### ⭐⭐⭐ HIGH PRIORITY (≥90% Signal Rate)

| Block | Signal Rate | Signals/Day | Status | Priority |
|-------|-------------|-------------|--------|----------|
| **ema_20_50_trend** | 100.0% | 95.5 | ❌ TODO | #1 |
| **market_structure_shift** | 100.0% | 95.5 | ✅ DONE | - |
| **breaker_block** | 96.1% | 91.7 | ❌ TODO | #2 |
| **fair_value_gap** | 91.8% | 87.6 | ❌ TODO | #3 |
| **break_of_structure** | 90.9% | 86.8 | ✅ DONE | - |

### ⭐⭐ MEDIUM PRIORITY (70-89% Signal Rate)

| Block | Signal Rate | Signals/Day | Status | Priority |
|-------|-------------|-------------|--------|----------|
| **ichimoku_cloud** | 76.2% | 72.7 | ❌ TODO | #4 |

### ⭐ LOW PRIORITY (50-69% Signal Rate)

| Block | Signal Rate | Signals/Day | Status | Priority |
|-------|-------------|-------------|--------|----------|
| **liquidity_sweep** | 51.8% | 49.5 | ❌ TODO | #5 |

**Note:** Liquidity Sweep has an inflated count due to NO_SWEEP not being excluded. True event rate likely much lower.

---

## Implementation Order

### Phase 1: Completed ✅
1. ✅ **Break of Structure (BOS)** - Continuation tracking (15.89 events/day)
2. ✅ **Market Structure Shift (MSS)** - Reversal tracking (20.88 events/day)
3. ✅ **EMA 20/50 Trend** - Trend state tracker (15.52 events/day) ⭐ NEW!

### Phase 2: Critical Continuous Trackers (Remaining)
4. **Breaker Block** - 96.1% rate, failed OB state tracker
5. **Fair Value Gap** - 91.8% rate, gap lifecycle tracker

### Phase 3: Supplementary Blocks
6. **Ichimoku Cloud** - 76.2% rate, cloud position tracker
7. **Liquidity Sweep** - 51.8% rate (fix NO_SWEEP first)

---

## Block Analysis & Implementation Strategy

### #1: EMA 20/50 Trend (NEXT - 100% rate)

**Current Behavior:**
- Tracks continuous trend position (above/below crossover)
- Returns BULLISH/BEARISH on every bar
- No NEUTRAL state (always has directional bias)

**Event Enhancement:**
- `is_new_event`: True when trend direction CHANGES
- `bars_since_trend_change`: Age of current trend
- `trend_strength`: How strong is current trend

**Use Case:**
- NEW event = trend reversal point (entry timing)
- Continuing state = trend filter (stay with trend)
- Age tracking = trend maturity assessment

**Expected Impact:**
- Total: 95.5 signals/day (continuous)
- NEW events: ~5-10/day (trend changes)
- Continuing: ~85-90/day (trend persistence)

---

### #2: Breaker Block (96.1% rate)

**Current Behavior:**
- Detects failed Order Blocks (OB swept + MSS)
- Once breaker detected, state persists
- Returns signals on every bar after detection

**Event Enhancement:**
- `is_new_event`: True when breaker JUST formed
- `bars_since_breaker`: Age of breaker block
- `retest_count`: Number of retests

**Use Case:**
- NEW event = fresh breaker formation (high probability entry)
- Continuing state = active breaker zone
- Retest tracking = confluence building

**Expected Impact:**
- Total: 91.7 signals/day (continuous)
- NEW events: ~8-12/day (fresh breakers)
- Continuing: ~80-83/day (active breaker zones)

---

### #3: Fair Value Gap (91.8% rate)

**Current Behavior:**
- Detects price gaps (FVG)
- Gap remains "active" until filled
- Returns signals while gap is open

**Event Enhancement:**
- `is_new_event`: True when gap JUST formed
- `bars_since_gap`: Gap age
- `gap_filled`: Boolean - is gap completely filled
- `gap_fill_percentage`: 0-100% filled

**Use Case:**
- NEW event = fresh gap (immediate entry opportunity)
- Continuing state = open gap (pending fill target)
- Fill tracking = mitigation monitoring

**Expected Impact:**
- Total: 87.6 signals/day (continuous)
- NEW events: ~10-15/day (new gaps)
- Continuing: ~72-77/day (open gaps)

---

### #4: Ichimoku Cloud (76.2% rate)

**Current Behavior:**
- Tracks price position relative to cloud
- State persists while in same cloud zone
- Returns BULLISH (above), BEARISH (below), NEUTRAL (in cloud)

**Event Enhancement:**
- `is_new_event`: True when cloud position CHANGES
- `bars_in_current_zone`: Time in current zone
- `cloud_thickness`: Strong vs weak cloud

**Use Case:**
- NEW event = cloud breakout/breakdown
- Continuing state = trend confirmation
- Zone duration = trend strength

**Expected Impact:**
- Total: 72.7 signals/day (continuous)
- NEW events: ~8-12/day (zone changes)
- Continuing: ~60-65/day (zone persistence)

---

### #5: Liquidity Sweep (51.8% rate - SPECIAL CASE)

**Current Issues:**
- NO_SWEEP not excluded (inflating count)
- True active rate likely 25-30%
- Already somewhat event-driven

**Event Enhancement (Lower Priority):**
- Fix NO_SWEEP exclusion FIRST
- Then add `is_new_event` for fresh sweeps
- Track sweep type and rejection strength

**Use Case:**
- NEW event = fresh sweep (reversal entry)
- Age tracking = sweep validity period

**Expected Impact (After Fix):**
- Total: ~30 signals/day (post-fix)
- NEW events: ~15-20/day
- Less continuous than others

---

## Implementation Checklist (Per Block)

### Code Changes
- [ ] Add `is_new_event` detection logic
- [ ] Add `bars_since_[event]` tracking
- [ ] Add event-specific fields
- [ ] Update confidence calculation (+5% for new events)
- [ ] Update confluence factors

### Documentation
- [ ] Update block .md file with dual-mode behavior
- [ ] Document new metadata fields
- [ ] Provide usage examples
- [ ] Update API reference

### Testing
- [ ] Run walkforward test
- [ ] Verify event detection
- [ ] Check terminal output (⭐ NEW EVENTS)
- [ ] Verify JSON event_tracking section

---

## Timeline Estimate

**Per Block:** ~45-60 minutes each
- Code: 15-20 min
- Documentation: 15-20 min
- Testing: 15-20 min

**Phase 2 (3 blocks):** 2.5-3 hours
**Phase 3 (2 blocks):** 1.5-2 hours
**Total Remaining:** 4-5 hours

---

## Success Criteria

For each enhanced block:
1. ✅ Event detection working (`is_new_event` accurate)
2. ✅ Age tracking functional (`bars_since_*` correct)
3. ✅ Terminal shows event counts (e.g., "⭐ NEW EVENTS: X")
4. ✅ JSON includes event_tracking section
5. ✅ Documentation complete and accurate  
6. ✅ 100% backward compatible

---

## Next Immediate Action

**START WITH:** EMA 20/50 Trend (100% signal rate, #1 priority)

**Reason:**
- Highest signal rate (tied with MSS)
- Critical trend filter for all strategies
- Simple to implement (trend direction change detection)
- High value - every strategy uses trend filters

---

## Master Template (Reusable)

```python
# Standard event tracking pattern for any continuous tracker:

def analyze(self, df, **kwargs):
    # ... existing detection logic ...
    
    # EVENT TRACKING ADDITION:
    current_bar_index = len(df) - 1
    is_new_event = (detected_event['index'] == current_bar_index)
    
    # Confidence boost
    if is_new_event:
        confidence += 5
    
    # Metadata
    metadata = {
        # ... existing fields ...
        'is_new_event': is_new_event,
        'bars_since_event': current_bar_index - detected_event['index']
    }
    
    # Confluence
    if is_new_event:
        factors.append('⭐ NEW EVENT (just occurred)')
    else:
        factors.append('Continuing state')
        
    return result
```

---

## Expected Final Results

**After All Implementations:**
- ✅ 7 blocks with event tracking (up from 2)
- ✅ Comprehensive state + event coverage
- ✅ Precise entry timing for all continuous trackers
- ✅ Institutional-grade dual-mode tracking across system

**Value:**
- Better entry timing (~5-15 fresh events/day per block)
- Clearer signal quality (age-based filtering)
- Enhanced confidence scoring (fresh = higher)
- Complete state awareness (position filtering)

---

**Status:** Ready to proceed with Phase 2  
**Next Block:** EMA 20/50 Trend  
**ETA:** 45-60 minutes per block
