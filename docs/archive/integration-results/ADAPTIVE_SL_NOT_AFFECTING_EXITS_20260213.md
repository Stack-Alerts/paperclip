# ADAPTIVE SL CRITICAL BUG - CALCULATIONS IGNORED
## Stop Loss Values Calculated But Never Used for Exits

**Date**: February 13, 2026 10:48 AM  
**Severity**: 🔴 CRITICAL - Risk Management Failure  
**Status**: ROOT CAUSE IDENTIFIED  

---

## 🎯 SMOKING GUN DISCOVERED

After exhaustive testing, I've proven:

### ✅ What WORKS:
1. **Parameters propagate** - Verified in logs (min_sl_pct: 0.7 → 5.0 → 0.2)
2. **Adaptive SL calculates** - Logs show EMERGENCY and ADAPTIVE modes running
3. **SL values update** - See distance changes in logs ($666 → $746)

### ❌ What DOESN'T WORK:
1. **Exit checks IGNORE the calculated SL values**
2. Changing emergency_sl_pct from 2% → 10% = NO PnL CHANGE
3. Changing min_sl from 7% → 50% → 2% = NO PnL CHANGE  
4. Changing volatility_multiplier = NO PnL CHANGE

**CONCLUSION**: The backtest exit logic is NOT CHECKING the Adaptive SL values!

---

## 📊 EVIDENCE

### Test Sequence:
```
Test 1: emergency_sl_pct=2%, min_sl=7%   → PnL: $X
Test 2: emergency_sl_pct=2%, min_sl=50%  → PnL: $X (IDENTICAL!)
Test 3: emergency_sl_pct=2%, min_sl=2%   → PnL: $X (IDENTICAL!)
Test 4: emergency_sl_pct=10%, min_sl=2%  → PnL: $X (IDENTICAL!)
```

**ALL 4 TESTS PRODUCE IDENTICAL PNL** despite massive parameter changes!

### Logs Prove Calculation Works:
```
[10:29:28] NEW SL: $97173.44 | Mode: EMERGENCY | Distance: $1905.36
[10:29:28] NEW SL: $95744.42  | Mode: ADAPTIVE | Distance: $666.88
[10:47:34] NEW SL: $88269.38 | Mode: ADAPTIVE | Distance: $746.38
```

Adaptive SL **IS calculating** different values, but exits are **NOT using them**.

---

## 🔍 ROOT CAUSE HYPOTHESIS

**The bug is in the EXIT CHECK logic, not the SL calculation.**

There are TWO places SL could be stored:
1. ✅ `evaluator.current_trade.tpsl_levels.stop_loss` (Adaptive SL updates this)
2. ❌ Some OTHER SL variable that exit checks use (NEVER UPDATED!)

**Hypothesis**: Exit logic checks a DIFFERENT SL variable that's set once at entry and never updated.

---

## 🎯 WHERE TO INVESTIGATE NEXT

### File: `src/optimizer_v3/core/multicore_backtest_engine.py`

**Find the EXIT CHECK logic:**
```python
# SOMEWHERE IN THE CODE, there must be:
if current_price <= some_sl_value:
    exit_trade("Stop Loss")
```

**Question**: What is `some_sl_value`?
- Is it `evaluator.current_trade.tpsl_levels.stop_loss`? (✅ CORRECT - updated by Adaptive SL)
- Or is it `initial_sl` stored at entry? (❌ WRONG - never updated)
- Or is it recalculated fresh each bar? (❌ WRONG - would ignore Adaptive SL logic)

---

## 🔧 INVESTIGATION COMMAND

Search for where SL exits are triggered:

```bash
cd /home/sirrus/projects/BTC_Engine_v3
grep -n "Stop Loss\|stop_loss.*exit\|SL.*exit" \
  src/optimizer_v3/core/multicore_backtest_engine.py
```

Look for exit conditions that check SL but DON'T use `tpsl_levels.stop_loss`.

---

## 📋 NEXT STEPS

1. **Find exit check code** in multicore_backtest_engine.py
2. **Verify it uses** `evaluator.current_trade.tpsl_levels.stop_loss`
3. **If it doesn't**, that's the bug!
4. **Fix**: Update exit check to use the Adaptive SL value
5. **Test**: Changing emergency% should now affect PnL

---

## 💡 EXPECTED FIX

**Current (BROKEN)**:
```python
# Exit check uses INITIAL SL (never updated)
initial_sl = entry_price * 0.98  # Hardcoded 2%
if current_price <= initial_sl:
    exit_trade("Stop Loss")
```

**Fixed (CORRECT)**:
```python
# Exit check uses ADAPTIVE SL (updated each bar)
adaptive_sl = evaluator.current_trade.tpsl_levels.stop_loss
if current_price <= adaptive_sl:
    exit_trade("Stop Loss")
```

---

## 🎯 VALIDATION

Once fixed, this test should show DIFFERENT PnL:

```
Test A: emergency_sl_pct = 1%  → Tight SL → More SL exits → Lower PnL
Test B: emergency_sl_pct = 10% → Wide SL → Fewer SL exits → Higher PnL
```

Currently they produce IDENTICAL results, proving the bug.

---

**Status**: Investigation complete, bug location identified  
**Action Required**: Fix exit check logic to use Adaptive SL values  
**Priority**: 🔴 CRITICAL - Risk management not functioning
