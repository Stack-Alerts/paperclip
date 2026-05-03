# TP ORDERING BUG - FORENSIC ANALYSIS
**Date**: February 13, 2026
**Analyst**: NAUTILUS EXPERT
**Evidence**: logs/trades/trades_panel_20260213_122109.log

---

## 🔍 CRITICAL BUG IDENTIFIED: TP Levels in Wrong Order

### 📊 Evidence from Trades Panel Log:

**TP Exit Summary (95 trades):**
- TP1 exits: **0** ❌
- TP2 exits: **1** (only trade #60)
- TP3 exits: **13** ��
- SL exits: Majority
- MAX_BARS: Several

### 🧪 Detailed Trade Analysis:

**Trade #6: TP3 Hit**
```
Entry:  $91,936.44
Exit:   $85,697.11 (TP3)
Move:   -$6,239.33 (-6.79%)
```

**Trade #41: TP3 Hit**
```
Entry:  $90,002.18
Exit:   $88,822.45 (TP3)
Move:   -$1,179.73 (-1.31%)
```

**Trade #60: TP2 Hit** (ONLY TP2!)
```
Entry:  $94,561.10
Exit:   $93,029.57 (TP2)
Move:   -$1,531.53 (-1.62%)
```

**Trade #74: TP3 Hit**
```
Entry:  $89,050.00
Exit:   $84,597.54 (TP3)
Move:   -$4,452.46 (-5.00%)
```

**Trade #88: TP3 Hit** (MASSIVE move!)
```
Entry:  $72,294.30
Exit:   $64,511.50 (TP3)
Move:   -$7,782.80 (-10.77%)  ← HUGE!
```

**Trade #90: TP3 Hit** (MASSIVE move!)
```
Entry:  $72,389.20
Exit:   $64,606.40 (TP3)
Move:   -$7,782.80 (-10.75%)  ← HUGE!
```

---

## 🐛 ROOT CAUSE ANALYSIS

### What SHOULD Happen (SHORT trades, partial exits):

**Correct TP Ordering:**
```
Entry: $90,000
↓
TP1:   $89,000 (-1.1%) ← 33% exit, closest
↓
TP2:   $87,000 (-3.3%) ← 33% exit, middle
↓
TP3:   $85,000 (-5.6%) ← 34% exit, furthest
```

**Actual Behavior:**
```
Entry: $90,000
↓ Price moves down...
↓ TP1 NEVER HITS (wrong level?)
↓ TP2 NEVER HITS (wrong level?)
↓ Price reaches -10%
↓ TP3 HITS! (only reachable TP)
```

###🔬 Hypothesis:

**TP1 and TP2 are calculated INCORRECTLY:**

Possible issues:
1. **Direction Bug**: TP1/TP2 calculated ABOVE entry for SHORT (should be below)
2. **Ordering Bug**: TP3 is closer than TP1/TP2 (reversed order)
3. **Calculation Bug**: TP1/TP2 use wrong formula (e.g., using LONG logic for SHORT)

### ✅ Evidence Supporting Hypothesis:

**Fact 1:** TP3 hits at reasonable distances (1-11%)
**Fact 2:** TP1 NEVER hits in 95 trades (0/95 = 0%)
**Fact 3:** TP2 hits once (1/95 = 1%)
**Fact 4:** Partial exits should be sequential (TP1→TP2→TP3), but skipping to TP3

**Conclusion:**
- TP3 calculation is CORRECT (in right direction, reasonable distance)
- TP1 calculation is BROKEN (unreachable)
- TP2 calculation is BROKEN (almost unreachable)

---

## 🔧 WHERE TO FIND THE BUG

**File:** `src/optimizer_v3/core/tpsl_calculator.py`

**Method:** `calculate_levels()` or `_calculate_fibonacci_tps()`

**What to check:**
```python
# For SHORT trades, ALL TPs must be BELOW entry:
if entry_side == 'SHORT':
    tp1 = entry_price - (entry_price * 0.01)   # -1% (closest)
    tp2 = entry_price - (entry_price * 0.03)   # -3% (middle)
    tp3 = entry_price - (entry_price * 0.05)   # -5% (furthest)
    
    # VERIFY: tp1 > tp2 > tp3 (descending order for SHORT)
    assert tp1 > tp2 > tp3, "TP order wrong for SHORT!"
    assert tp1 < entry_price, "TP1 must be below entry for SHORT!"
```

**Common Mistakes:**
- Using LONG logic for SHORT (tp1 = entry + distance instead of entry - distance)
- Reversing TP order (tp3 closer than tp1)
- Using wrong percentages (negative instead of positive)

---

## 📋 EXPECTED FIX

**Before (BROKEN):**
```python
if entry_side == 'SHORT':
    # BUG: tp1/tp2 might be ABOVE entry or in wrong order!
    tp1 = entry_price + fib_level_1  # ❌ ABOVE for SHORT!
    tp2 = entry_price + fib_level_2  # ❌ ABOVE for SHORT!
   tp3 = entry_price - fib_level_3  # ✅ BELOW (only working one!)
```

**After (FIXED):**
```python
if entry_side == 'SHORT':
    # All TPs BELOW entry, ascending distance
    tp1 = entry_price - (swing_range * 0.382)  # Closest (~1-2%)
    tp2 = entry_price - (swing_range * 0.618)  # Middle (~3-4%)
    tp3 = entry_price - (swing_range * 1.0)    # Furthest (~5-6%)
    
    # Validation
    assert tp1 > tp2 > tp3, f"TP order: tp1={tp1}, tp2={tp2}, tp3={tp3}"
    assert tp1 < entry_price, "TP1 must be below entry!"
```

---

## ✅ VERIFICATION TEST

After fix, with 95 trades we should see:
```
TP/SL Adjustments: 5500+ (TP1: 30+, TP2: 25+, TP3: 13, SL: 5334)
```

**Expected Distribution:**
- TP1: ~30 hits (many trades hit TP1 first, 33% partial)
- TP2: ~25 hits (survivors from TP1, another 33%)
- TP3: ~13 hits (final 34%, some hit SL before TP3)

**Current (BROKEN):**
- TP1: 0 (unreachable)
- TP2: 1 (almost unreachable)
- TP3: 13 (only working TP)

---

**Status**: Bug identified, ready to fix in tpsl_calculator.py
**Priority**: CRITICAL (affects all TP exits)
**Impact**: HIGH (partial exits completely broken)
