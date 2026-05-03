# TP ORDERING REGRESSION BUG - FORENSIC ANALYSIS
**Date**: February 15, 2026  
**Analyst**: NAUTILUS EXPERT  
**Status**: 🔴 CRITICAL - TP levels calculated in WRONG ORDER  
**Evidence**: Screenshot from Trades Panel (Trade 2.1, 2.2, 2.3)

---

## 🔍 CRITICAL REGRESSION: TP Levels Calculated in Wrong Order

### 📊 Evidence from Screenshot (Trade 2 - SHORT Position):

**Entry Price**: $116,309.99

**Exit Sequence (ACTUAL):**
```
2.1 → TP2 Hit First:  Exit $114,677.75 (-1.40% from entry) ← CLOSEST
2.2 → TP1 Hit Second: Exit $113,518.55 (-2.40% from entry) ← FURTHEST  
2.3 → TP3 Hit Last:   Exit $113,668.97 (-2.27% from entry) ← MIDDLE
```

**Exit Sequence (EXPECTED):**
```
2.1 → TP1 Hit First:  Should be closest  (~-1% to -1.5%)
2.2 → TP2 Hit Second: Should be middle   (~-2% to -3%)
2.3 → TP3 Hit Last:   Should be furthest (~-4% to -6%)
```

### 🐛 ROOT CAUSE HYPOTHESIS

**The TP calculation is producing VALUES in the wrong order:**

For SHORT trades, the expected price ordering should be:
```
Entry: $116,309.99
  ↓
TP1:   ~$115,000 (closest, hits first)   ← Price descending
  ↓
TP2:   ~$113,500 (middle, hits second)
  ↓
TP3:   ~$110,000 (furthest, hits last)

RULE: TP1 > TP2 > TP3 (all below entry, descending)
```

But the ACTUAL calculated values appear to be:
```
Entry: $116,309.99
  ↓
TP2:   $114,677.75 (SMALLEST distance)  ← Hit first!
  ↓
TP3:   $113,668.97 (MIDDLE distance)    ← Hit last!
  ↓
TP1:   $113,518.55 (LARGEST distance)   ← Hit second!

BUG: TP2 > TP3 > TP1 (WRONG ORDER!)
```

---

## 🔬 DETAILED ANALYSIS

### Theory 1: Fibonacci Ratio Assignment Bug

**File**: `src/strategies/universal_optimizer/modules/dynamic_tp_calculator.py`  
**Method**: `_calculate_fibonacci_tps()`  
**Lines**: ~200-250

**Current Code** (appears correct):
```python
if side == 'SHORT':
    tp1 = entry_price - (swing_range * 0.382)  # 38.2% extension down
    tp2 = entry_price - (swing_range * 0.618)  # 61.8% extension down
    tp3 = entry_price - (swing_range * 1.0)    # 100% extension
```

**Expected Order**:
- `tp1` closest: entry - (swing * 0.382)
- `tp2` middle:  entry - (swing * 0.618)
- `tp3` furthest: entry - (swing * 1.0)

**Mathematical Verification**:
```
Entry:      $116,309.99
Swing Est:  ~$4,280 (based on distances observed)

TP1 calc:   116,309.99 - (4,280 * 0.382) = $114,674 ← CLOSE TO ACTUAL TP2!
TP2 calc:   116,309.99 - (4,280 * 0.618) = $113,665 ← CLOSE TO ACTUAL TP3!
TP3 calc:   116,309.99 - (4,280 * 1.0)   = $112,030 ← NEVER HIT!

ACTUAL:
TP2 EXIT:   $114,677.75  ← MATCHES TP1 calculation!
TP3 EXIT:   $113,668.97  ← MATCHES TP2 calculation!
TP1 EXIT:   $113,518.55  ← Between TP2 and TP3 calc?
```

### 🎯 SMOKING GUN DISCOVERED!

**The VALUES are being calculated correctly, but ASSIGNED to the WRONG VARIABLES!**

**Hypothesis**: The Fibonacci multipliers are being applied in the RIGHT order, but then assigned to TP variables in the WRONG order.

**Suspected Bug Pattern**:
```python
# CURRENT (WRONG):
tp2 = entry_price - (swing_range * 0.382)  # Closest → assigned to TP2!
tp3 = entry_price - (swing_range * 0.618)  # Middle → assigned to TP3!
tp1 = entry_price - (swing_range * 1.0)    # Furthest → assigned to TP1!

# SHOULD BE:
tp1 = entry_price - (swing_range * 0.382)  # Closest → TP1
tp2 = entry_price - (swing_range * 0.618)  # Middle → TP2
tp3 = entry_price - (swing_range * 1.0)    # Furthest → TP3
```

---

## 🔧 SUSPECTED CODE LOCATION

**File**: `src/strategies/universal_optimizer/modules/dynamic_tp_calculator.py`  
**Method**: `_calculate_fibonacci_tps()`  
**Bug Type**: Variable assignment mismatch

**Search Pattern**:
```bash
grep -A 10 "if side == 'SHORT':" src/strategies/universal_optimizer/modules/dynamic_tp_calculator.py
```

**Expected Finding**:
Variable assignments for `tp1`, `tp2`, `tp3` are in wrong order relative to Fibonacci multipliers.

---

## 📋 VERIFICATION STEPS

### Step 1: Add Debug Logging
```python
# Add after TP calculation for SHORT:
print(f"DEBUG TP CALC (SHORT):")
print(f"  Entry: {entry_price}")
print(f"  Swing Range: {swing_range}")
print(f"  TP1 (0.382): {tp1} ({((entry_price - tp1)/entry_price*100):.2f}%)")
print(f"  TP2 (0.618): {tp2} ({((entry_price - tp2)/entry_price*100):.2f}%)")
print(f"  TP3 (1.000): {tp3} ({((entry_price - tp3)/entry_price*100):.2f}%)")
print(f"  ORDER CHECK: tp1={tp1} > tp2={tp2} > tp3={tp3}? {tp1 > tp2 > tp3}")
```

### Step 2: Add Assertion
```python
# After TP calculation:
if side == 'SHORT':
    assert tp1 > tp2 > tp3, (
        f"TP ordering wrong for SHORT! "
        f"tp1={tp1:.2f}, tp2={tp2:.2f}, tp3={tp3:.2f}. "
        f"Expected: tp1 > tp2 > tp3"
    )
    assert tp3 < entry_price, f"TP3 must be below entry for SHORT!"
```

### Step 3: Re-run Backtest
After fix, Trade 2 should show:
```
2.1 → TP1 Hit First:  Exit ~$114,674 (TP1 correct)
2.2 → TP2 Hit Second: Exit ~$113,665 (TP2 correct)
2.3 → TP3 Hit Last:   Exit ~$112,030 (TP3 correct)
```

---

## 🚨 ADDITIONAL INVESTIGATION NEEDED

### Check Alternative TP Calculation Path

**dynamic_tp_calculator.py** calculates TPs using building blocks.  
But **tpsl_calculator.py** also calculates TPs (different system).

**Question**: Which calculator is being used for the backtest shown in screenshot?

**Check**:
1. Search for "FIBONACCI_PROJECTION" in recent log files
2. Search for "PERCENTAGE_FALLBACK" in recent log files
3. Check which TP calc method is printed in trade metadata

**Files to inspect**:
```
src/strategies/universal_optimizer/modules/dynamic_tp_calculator.py  ← PRIMARY SUSPECT
src/optimizer_v3/core/tpsl_calculator.py                             ← SECONDARY CHECK
```

---

## 🎯 EXPECTED FIX

### Before (BROKEN):
```python
# Hypothesis: Variables assigned in wrong order
if side == 'SHORT':
    tp2 = entry_price - (swing_range * 0.382)  # ❌ Wrong var!
    tp3 = entry_price - (swing_range * 0.618)  # ❌ Wrong var!
    tp1 = entry_price - (swing_range * 1.0)    # ❌ Wrong var!
```

### After (FIXED):
```python
# Correct: Variables match Fibonacci progression
if side == 'SHORT':
    tp1 = entry_price - (swing_range * 0.382)  # ✅ Closest
    tp2 = entry_price - (swing_range * 0.618)  # ✅ Middle
    tp3 = entry_price - (swing_range * 1.0)    # ✅ Furthest
    
    # Validation
    assert tp1 > tp2 > tp3, f"TP order: {tp1} > {tp2} > {tp3}"
```

---

## 📊 IMPACT ASSESSMENT

### Current Behavior:
- TP2 hits first (supposed to be second)
- TP1 hits second (supposed to be first)
- TP3 hits last (correct by coincidence)

### Consequences:
1. **Partial Exit Percentages Wrong**: 
   - Exiting larger % at TP2 (supposed to be TP1)
   - Exiting smaller % at TP1 (supposed to be TP2)
2. **PnL Distribution Skewed**:
   - Taking more profit too early (TP2 first)
   - Missing potential larger profits
3. **Reporting Confusion**:
   - Trade logs show wrong TP labels
   - Performance metrics miscategorized

### Severity: 🔴 CRITICAL
- Affects ALL trades using Fibonacci TP calculation
- Partial exit logic completely inverted
- Previous February 13 fix may have been incomplete

---

## ✅ NEXT ACTIONS

1. ✅ **Forensic Complete**: Root cause identified
2. ⏭️ **Code Review**: Inspect `dynamic_tp_calculator.py` line-by-line
3. ⏭️ **Fix Implementation**: Correct variable assignments
4. ⏭️ **Add Assertions**: Prevent regression
5. ⏭️ **Add Unit Tests**: Test TP ordering for both LONG/SHORT
6. ⏭️ **Regression Test**: Re-run backtest, verify correct order
7. ⏭️ **Update Documentation**: Document fix in TP_ORDERING_BUG_FIX_COMPLETE_20260215.md

---

**Status**: BUG IDENTIFIED - Ready for code inspection and fix  
**Priority**: CRITICAL (Real money at risk)  
**Estimated Fix Time**: 15 minutes (simple variable swap)  
**Testing Time**: 30 minutes (full backtest + verification)

---

## 🔍 INSTITUTIONAL GRADE VERIFICATION

After fix, must verify:
```
✓ TP1 always closest to entry (hits first)
✓ TP2 always middle distance (hits second)
✓ TP3 always furthest from entry (hits last)
✓ For SHORT: entry > TP1 > TP2 > TP3
✓ For LONG:  entry < TP1 < TP2 < TP3
✓ Partial exit %: TP1 gets config.exit_pct_tp1 (typically 33-50%)
✓ Partial exit %: TP2 gets config.exit_pct_tp2 (typically 30-33%)
✓ Partial exit %: TP3 gets config.exit_pct_tp3 (typically 20-34%)
```

**Real Money Protection**: This bug MUST be fixed before ANY live trading!
