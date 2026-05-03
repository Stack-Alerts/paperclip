# Wyckoff SPRING/SOS Research - Root Cause Analysis
**Date:** 2026-01-15
**Issue:** Zero SPRING/SOS signals in 180 days (unrealistic)
**Status:** RESEARCH PROTOCOL ACTIVATED

## Problem Statement

In 180 days of BTC 2HR data (2,160+ bars), we detect:
- ✅ ACCUMULATION_PHASE_B: 12,618 (73.4%) - Many ranges
- ❌ SPRING_DETECTED: 0 (0.0%) - None!
- ❌ SOS_BREAKOUT: 0 (0.0%) - None!

**This is impossible.** With 73% of time in accumulation ranges, we should see multiple springs and SOS breakouts.

---

## Wyckoff Theory Review

### What is a SPRING (Phase C)?
1. Market is in accumulation range (Phase B)
2. Price breaks BELOW support (false breakdown)
3. Weak hands panic sell
4. Price RECOVERS back above support
5. **This is an EVENT that OCCURRED, not a current state**

### What is SOS - Sign of Strength (Phase D)?
1. Market is in accumulation range (Phase B)
2. Price breaks ABOVE resistance
3. High volume confirms institutional buying
4. Price SUSTAINS above resistance
5. **This is an EVENT that OCCURRED, not a current state**

---

## Current Logic Analysis

### Our Current Spring Detection:
```python
def detect_spring(self, df: pd.DataFrame, support_level: float) -> tuple:
    # Check if price broke BELOW support in last 50 bars
    broke_support = recent_lows.min() < support_level * 0.98
    
    # Check if price RECOVERED above support NOW
    recovered = current_price > support_level * 0.998
    
    if broke_support and recovered:
        return True, confidence
```

### CRITICAL FLAW IDENTIFIED ⚠️

**Problem:** We only detect spring if:
1. Price broke support in last 50 bars AND
2. Current price is ABOVE support RIGHT NOW

**Why this fails:**
- A spring is an EVENT that occurred DAYS/WEEKS ago
- After a spring, price moves UP away from support
- By bar 50-100, price is FAR above support
- We no longer detect the spring because we only look at last 50 bars
- **The spring event is "forgotten" after 50 bars**

**Example Timeline:**
```
Bar 100: Price breaks below support (spring starts)
Bar 105: Price recovers above support (spring completes) ← Should detect HERE
Bar 110: Still above support (spring in recent memory) ← Should still detect
Bar 120: Moving higher (spring aging out)
Bar 150: Far above support (spring completely forgotten) ← Our current code forgets it!
```

---

## Solution: Event Memory System

### Current Approach (WRONG):
- Check if spring is happening RIGHT NOW
- Forget about springs that happened >50 bars ago

### Correct Approach (NEEDED):
- Detect when spring EVENT occurs
- REMEMBER the event for X bars (event persistence)
- Emit SPRING_DETECTED signal during event persistence window
- Clear event after persistence window expires

---

## Proposed Fix

### Option 1: Event Persistence (Recommended)
```python
class WyckoffAccumulation:
    def __init__(self):
        self.last_spring_bar = None
        self.spring_persistence = 20  # Remember for 20 bars
        
    def detect_spring_event(self, df):
        # Check if spring JUST COMPLETED (within last 5 bars)
        for i in range(len(df)-5, len(df)):
            # Did price break below support?
            # Did it recover above support?
            # If yes, record: self.last_spring_bar = i
        
        # Is spring event still fresh? (within persistence window)
        if self.last_spring_bar and (len(df) - self.last_spring_bar) < self.spring_persistence:
            return True, confidence
        return False, 0
```

### Option 2: Scan Recent History (Simpler)
```python
def detect_spring(self, df):
    # Look for spring pattern in RECENT PAST (last 20-30 bars)
    for i in range(len(df)-30, len(df)):
        window = df.iloc[max(0, i-10):i+1]
        
        # Did price break below support in this window?
        broke_support = window['low'].min() < support
        
        # Did price recover by end of window?
        recovered = window['close'].iloc[-1] > support
        
        if broke_support and recovered:
            # Spring detected in recent history!
            return True, confidence
```

---

## Test Plan

1. ✅ Implement event persistence OR recent history scan
2. ✅ Test on 180-day dataset
3. ✅ Expect realistic spring frequency (5-15 per 180 days)
4. ✅ Expect realistic SOS frequency (10-20 per 180 days)
5. ✅ Verify signals don't spam (persistence prevents duplicates)

---

## Expected Results After Fix

**Current (BROKEN):**
- SPRING: 0 (0%)
- SOS: 0 (0%)

**Expected (REALISTIC):**
- SPRING: 10-20 (0.5-1.0%)
- SOS: 15-30 (0.7-1.5%)
- Both signals rare but present

---

## Implementation Priority

**CRITICAL:** This is blocking Wyckoff from working properly
**Effort:** 1-2 hours
**Value:** High - Makes Wyckoff Phase C/D detection functional
**Risk:** Low - Well-defined problem with clear solution
