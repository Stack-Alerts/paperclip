# EXPERT MODE: Statistical System Walk-Forward Fix Research

**Date:** December 30, 2025  
**Objective:** Fix Statistical system to work in walk-forward (real-time) trading  
**Current Status:** 57.3% backtest (lookahead bias) → 0% walk-forward (realistic)

---

## PROBLEM DIAGNOSIS

### Root Cause: Future Pivot Knowledge

**Backtest Method (INVALID):**
```python
# Gets ALL pivots first (includes future)
pivots_test = zigzag.find_pivots(df_test)
highs_test = [p for p in pivots_test if p.pivot_type == 'HIGH']

# Then iterates through them
for i in range(3, len(highs_test) - 1):
    p1, p2, p3 = highs_test[i-3], highs_test[i-2], highs_test[i-1]
    p4 = highs_test[i]  # ← KNOWS FUTURE PIVOT!
```

**Why This Fails in Real-Time:**
- Pivot requires 50 bars AFTER to confirm
- You don't know WHERE the next pivot will be
- By the time p3 confirms, you're 50 bars past potential entry
- Cannot predict p4 because you don't know when/where it is

---

## SOLUTION RESEARCH

### Option 1: Reduce Pivot Confirmation Window ✅

**Current:** Pivots need 50 bars on each side (100 bars total)  
**Problem:** Too slow for real-time trading  

**Solution:** Use shorter confirmation (10-20 bars)
- Faster detection
- More pivots (more signals)
- Trade-off: Slightly less reliable pivots

**Implementation:**
```python
# Instead of length=50
zigzag = ZigzagDetector(length=10)  # 10 bars each side

# Pivots confirm faster:
# - 50 bars: Confirms after 50 bars (25 hours on 30min)
# - 10 bars: Confirms after 10 bars (5 hours on 30min)
```

**Pros:**
- Can actually detect patterns in real-time
- More trading opportunities
- Still uses pivot-based logic

**Cons:**
- More noise (weaker pivots)
- May need to retrain patterns

---

### Option 2: Use Swing Highs/Lows Instead of Pivots

**Concept:** Don't wait for pivot confirmation
- Use recent swing highs/lows (last N bars)
- Detect patterns on "almost-pivots"
- Trade immediately when pattern appears

**Implementation:**
```python
def find_swing_high(data, lookback=20):
    """Find recent swing high (not confirmed pivot)"""
    high_idx = data['high'].iloc[-lookback:].idxmax()
    return high_idx, data.loc[high_idx, 'high']

# Use swings instead of pivots for pattern detection
```

**Pros:**
- No wait for pivot confirmation
- Can trade immediately
- More responsive

**Cons:**
- Less reliable than confirmed pivots
- More false signals
- Need different pattern encoding

---

### Option 3: Rolling Pivot Detection (RECOMMENDED) ⭐

**Concept:** Detect pivots incrementally as bars arrive
- Use partially-confirmed pivots (e.g., 20 bars instead of 50)
- Update patterns as new data arrives
- Trade when enough confirmation exists

**Implementation:**
```python
# Walk-forward compatible
for idx in range(len(df)):
    historical_data = df.iloc[:idx+1]  # Only past
    
    # Detect pivots with shorter window (tradeable)
    zigzag = ZigzagDetector(length=20)  # Faster confirmation
    pivots = zigzag.find_pivots(historical_data)
    
    if len(pivots) >= 3:
        # Get last 3 pivots
        p1, p2, p3 = pivots[-3], pivots[-2], pivots[-1]
        
        # Encode pattern
        pattern_id = encoder.encode(p1, p2, p3)
        
        # Check if high-edge pattern
        if pattern_id in HIGH_EDGE_PATTERNS:
            # Generate signal NOW (tradeable)
            prediction = stats.predict(pattern_id)
            # ... trade
```

**Pros:**
- Works in walk-forward (no future knowledge)
- Uses familiar pivot logic
- Tradeable in real-time

**Cons:**
- Pivots less reliable (20 vs 50 bars)
- May need to retrain with shorter window

---

## RECOMMENDED SOLUTION

**Use Option 3: Rolling Pivot Detection with length=20**

**Rationale:**
1. Maintains pivot-based approach (proven concept)
2. Works in real-time (no lookahead)
3. Reasonable trade-off (20 bars = 10 hours on 30min)
4. Can be validated with walk-forward

**Implementation Steps:**

### Step 1: Retrain with length=20
```python
# Train using shorter pivot window
zigzag_train = ZigzagDetector(length=20)
pivots_train = zigzag_train.find_pivots(df_train)
# ... train pattern statistics
```

### Step 2: Walk-Forward with length=20
```python
# Test using same shorter window
for idx in range(len(df_test)):
    hist_data = df_test.iloc[:idx+1]
    zigzag_test = ZigzagDetector(length=20)
    pivots = zigzag_test.find_pivots(hist_data)
    
    if len(pivots) >= 3:
        # Detect pattern and trade
```

### Step 3: Validate
- Run walk-forward test
- Compare vs backtest
- Ensure signals appear (not 0 like before)
- Check win rate is realistic

---

## EXPECTED RESULTS

**With length=20 pivots:**

**Training:**
- More pivots detected (less strict)
- More pattern samples
- May have slightly lower individual pattern accuracy

**Testing:**
- Should generate signals in walk-forward (not 0)
- Win rate likely 52-58% (lower than 57.3% due to noise)
- But REALISTIC and TRADEABLE

**Success Criteria:**
- Walk-forward generates >50 signals
- Win rate ≥52% (profitable after adjustments)
- Backtest and walk-forward consistent (±5%)

---

## ALTERNATIVE: Pattern Recognition on Price Action

If pivot-based approach still fails, consider:

**Direct Price Pattern Recognition:**
- Detect patterns from OHLC bars directly
- Don't use pivots at all
- Examples: Engulfing, Doji, Hammer, etc.
- More signals, immediate trading

**This would be a PHASE 2 approach** if pivot fix doesn't work.

---

## NEXT STEPS

1. ✅ Reduce pivot length from 50 → 20
2. ✅ Retrain Statistical system with length=20
3. ✅ Run walk-forward with length=20
4. ✅ Validate results (should have >0 signals)
5. ✅ Compare backtest vs walk-forward consistency
6. ✅ If successful: Deploy statistical as building block
7. ❌ If fails: Move to price action patterns (Phase 2)

---

**Status:** Research complete - Ready to implement  
**Recommended Fix:** Use ZigzagDetector(length=20) for faster pivot confirmation  
**Expected Outcome:** 52-58% walk-forward win rate with actual signals
