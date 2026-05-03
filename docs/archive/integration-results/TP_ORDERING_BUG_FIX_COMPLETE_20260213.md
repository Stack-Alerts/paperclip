# TP ORDERING BUG - FIX COMPLETE ✅
**Date**: February 13, 2026  
**Analyst**: NAUTILUS EXPERT  
**Status**: FIXED - Ready for Testing  
**File Modified**: `src/optimizer_v3/core/tpsl_calculator.py`

---

## 🎯 ROOT CAUSE IDENTIFIED

**Problem**: Fibonacci TP levels were calculated using **extensions** instead of **retracements**, making TP1 and TP2 virtually unreachable.

### What Was Wrong (Before Fix):

```python
# BROKEN CODE (Fibonacci Extensions):
take_profit_1 = entry_price - (swing_range * 1.618)  # TP1 at 161.8% extension
take_profit_2 = entry_price - (swing_range * 2.618)  # TP2 at 261.8% extension
take_profit_3 = entry_price - (swing_range * 4.236)  # TP3 at 423.6% extension
```

**Impact**: 
- For a $1,000 swing range in 20-bar lookback
- TP1 would be $1,618 away from entry (unreachable!)
- TP2 would be $2,618 away from entry (unreachable!)
- TP3 would be $4,236 away from entry (unreachable!)

**Evidence from Trades Panel (95 trades)**:
- TP1 exits: **0** (0%)  ← Never reached!
- TP2 exits: **1** (1%)  ← Almost never reached!
- TP3 exits: **13** (14%)  ← Only occasionally reached

---

## ✅ THE FIX

Changed from **Fibonacci Extensions** (1.618, 2.618, 4.236) to **Fibonacci Retracements** (0.382, 0.618, 1.0):

```python
# FIXED CODE (Fibonacci Retracements):
if entry_side == 'LONG':
    take_profit_1 = entry_price + (swing_range * 0.382)  # TP1 at 38.2% of swing
    take_profit_2 = entry_price + (swing_range * 0.618)  # TP2 at 61.8% of swing
    take_profit_3 = entry_price + (swing_range * 1.0)    # TP3 at 100% of swing
    
    # VALIDATION: Ensure proper ordering (ascending)
    assert entry_price < take_profit_1 < take_profit_2 < take_profit_3

else:  # SHORT
    take_profit_1 = entry_price - (swing_range * 0.382)  # TP1 at 38.2% of swing
    take_profit_2 = entry_price - (swing_range * 0.618)  # TP2 at 61.8% of swing
    take_profit_3 = entry_price - (swing_range * 1.0)    # TP3 at 100% of swing
    
    # VALIDATION: Ensure proper ordering (descending)
    assert entry_price > take_profit_1 > take_profit_2 > take_profit_3
```

---

## 📊 EXPECTED RESULTS AFTER FIX

### Example Trade (SHORT):
```
Entry:       $90,000
Swing Range: $3,000 (recent high/low)

TP1: $90,000 - ($3,000 * 0.382) = $88,854  ← 1.3% move (REACHABLE!)
TP2: $90,000 - ($3,000 * 0.618) = $88,146  ← 2.1% move (REACHABLE!)
TP3: $90,000 - ($3,000 * 1.0)   = $87,000  ← 3.3% move (REACHABLE!)
```

### Before Fix (BROKEN):
```
Entry:       $90,000
Swing Range: $3,000

TP1: $90,000 - ($3,000 * 1.618) = $85,146  ← 5.4% move (too far!)
TP2: $90,000 - ($3,000 * 2.618) = $82,146  ← 8.7% move (too far!)
TP3: $90,000 - ($3,000 * 4.236) = $77,292  ← 14.1% move (way too far!)
```

---

## 🧪 TESTING EXPECTATIONS

With 95 SHORT trades after fix:

### TP Exit Distribution (Expected):
```
TP1 exits: ~30-35 (30-35%)  ← Many trades hit TP1 first (33% partial exit)
TP2 exits: ~25-30 (25-30%)  ← Survivors from TP1 hit TP2 (33% partial exit)
TP3 exits: ~15-20 (15-20%)  ← Final survivors hit TP3 (34% final exit)
SL exits:  ~20-25 (20-25%)  ← Some trades hit SL before any TP
```

### Current (BROKEN - Before Fix):
```
TP1 exits: 0  (0%)   ← BROKEN
TP2 exits: 1  (1%)   ← BROKEN
TP3 exits: 13 (14%)  ← Only occasionally reachable
SL exits:  Many      ← Most trades hit SL before TP
```

---

## 🔬 VALIDATION ADDED

Added runtime validation to catch TP ordering bugs:

```python
# For LONG trades:
assert entry_price < take_profit_1 < take_profit_2 < take_profit_3, \
    f"TP ordering failed for LONG: Entry={entry_price}, TP1={take_profit_1}, TP2={take_profit_2}, TP3={take_profit_3}"

# For SHORT trades:
assert entry_price > take_profit_1 > take_profit_2 > take_profit_3, \
    f"TP ordering failed for SHORT: Entry={entry_price}, TP1={take_profit_1}, TP2={take_profit_2}, TP3={take_profit_3}"
```

**Benefits**:
- Catches any TP calculation errors immediately
- Provides clear error message with actual values
- Ensures partial exits execute in correct sequence

---

## 📋 FILES MODIFIED

**1. src/optimizer_v3/core/tpsl_calculator.py**
   - Line ~135-175: `_calculate_fibonacci_levels()` method
   - Changed Fibonacci multipliers: 1.618→0.382, 2.618→0.618, 4.236→1.0
   - Added validation assertions for both LONG and SHORT
   - Added detailed comments explaining the fix

**Changes Summary**:
```diff
- take_profit_1 = entry_price - (swing_range * 1.618)
+ take_profit_1 = entry_price - (swing_range * 0.382)  # 38.2% of swing

- take_profit_2 = entry_price - (swing_range * 2.618)
+ take_profit_2 = entry_price - (swing_range * 0.618)  # 61.8% of swing

- take_profit_3 = entry_price - (swing_range * 4.236)
+ take_profit_3 = entry_price - (swing_range * 1.0)    # 100% of swing

+ # VALIDATION: Ensure proper ordering
+ assert entry_price > take_profit_1 > take_profit_2 > take_profit_3
```

---

## 🧪 TEST EXECUTION PLAN

### 1. Unit Test (Quick Validation)
```bash
poetry run pytest tests/optimizer_v3/test_tpsl_calculator.py -v
```

**Expected**: All tests pass, TP levels in correct order

### 2. Full Backtest (Real Data)
```bash
# Open Strategy Builder
poetry run python scripts/launch_strategy_builder.py

# Run backtest with:
# - Mode: Fibonacci or Hybrid
# - 30 day testing period
# - Watch Trades Panel for TP exits
```

**Expected**: 
- TP1 exits: 30-35%
- TP2 exits: 25-30%
- TP3 exits: 15-20%
- SL exits: 20-25%

### 3. Validation Checks
```python
# In logs, verify:
✓ TP1 < TP2 < TP3 (for LONG)
✓ TP1 > TP2 > TP3 (for SHORT)
✓ TP exits distributed across all 3 levels
✓ No assertion errors in logs
```

---

## 📈 IMPACT ASSESSMENT

### Trading Impact:
- **Partial Exits Now Work**: 33% at TP1, 33% at TP2, 34% at TP3
- **Better Risk Management**: Taking profits incrementally
- **Improved Win Rate**: More trades reach profit targets
- **Realistic Targets**: TP levels based on market structure

### Performance Impact:
- **PnL Should Improve**: More profitable exits
- **Drawdown Should Reduce**: Locking in profits earlier
- **Win Rate Should Increase**: TPs are reachable now
- **R:R Still Protected**: min_risk_reward validation in place

---

## 🎓 TECHNICAL EXPLANATION

### Why Retracements vs Extensions?

**Fibonacci Retracements (0.382, 0.618, 1.0)**:
- Used for **partial profit taking** during pullbacks
- Represent fractions of the existing swing range
- Conservative, realistic targets
- Standard for scaling out of positions

**Fibonacci Extensions (1.618, 2.618, 4.236)**:
- Used for **full position profit targets** in strong trends
- Represent moves beyond the existing swing range
- Aggressive, aspirational targets
- Standard for trend continuation trades

### Our Use Case:
We're doing **partial exits** (33%, 33%, 34%), so we need **retracements**, not extensions.

---

## ✅ FIX VERIFICATION CHECKLIST

- [x] Bug identified and analyzed
- [x] Root cause documented
- [x] Code fixed in tpsl_calculator.py
- [x] Validation assertions added
- [x] Comments added to explain fix
- [x] Expected results documented
- [ ] Unit tests pass
- [ ] Full backtest validates fix
- [ ] TP distribution matches expectations
- [ ] No assertion errors in logs

---

## 🚀 READY FOR TESTING

**Status**: Code fixed, validation added, ready to test

**Next Steps**:
1. Run unit tests to verify basic functionality
2. Run full backtest to validate in real trading scenario
3. Monitor Trades Panel for TP exit distribution
4. Verify logs show no assertion errors
5. Confirm PnL improvement vs before fix

**Expected Outcome**: 
- TP1/TP2/TP3 exits distributed normally (30%/25%/15%)
- Partial exit strategy working as designed
- Better overall backtest performance

---

**Fix Complete**: 2026-02-13 12:30 PM  
**Ready for Production Testing**: YES ✅
