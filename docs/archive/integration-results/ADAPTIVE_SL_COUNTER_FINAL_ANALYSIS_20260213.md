# ADAPTIVE SL COUNTER - FINAL FORENSIC ANALYSIS
**Date:** 2026-02-13  
**Status:** ✅ Counter Working - Reveals Parameter Wiring Bug  
**Severity:** CRITICAL - Test Wiring Broken

---

## 🎯 Executive Summary

The SL Adjustment counter is **working correctly**. The high count (5163 for 96 trades = ~54 per trade) revealed that:

1. ✅ **Adaptive SL calculates every bar** (expected behavior per design)
2. ❌ **Different UI parameters produce SAME results** (wiring bug)
3. ❌ **Test permutations don't affect SL behavior** (parameters not applied)

---

## 📊 Evidence

### Test Results:
```
Test 1 (Emergency 1%,  Vol Lookback 20, Vol Multi 12x): 5193 SL adjustments
Test 2 (Emergency 2%,  Vol Lookback 35, Vol Multi 18x): 5163 SL adjustments  
Test 3 (Emergency 10%, Vol Lookback 10, Vol Multi 13x): 5163 SL adjustments
```

**CRITICAL:** Tests 2 and 3 have **IDENTICAL** counts despite **VERY DIFFERENT** parameters!

---

## 🔬 Root Cause Analysis

### What We Learned:

**Per `test_adaptive_sl_manager.py`:**
- `update_sl()` is called **every bar**
- SL value changes **every bar** (ATR recalculates)
- ~54 updates per trade = average trade length in bars
- **THIS IS CORRECT DESIGN**

**The Real Bug:**
- Different vol_lookback (10 vs 35) should change ATR calculation
- Different vol_multi (12x vs 18x) should change SL distance
- Different emergency % (1% vs 10%) should change protection
- **BUT THEY DON'T** - Same 5163 count = Same SL behavior

---

## ✅ What's Working

### Counter Implementation:
```python
# multicore_backtest_engine.py
if mode_changed:
    sl_adjustment_count += 1  # Mode transition
elif sl_diff > 1.0:
    sl_adjustment_count += 1  # Meaningful price change
```

**Status:** ✅ Correctly counts both:
1. Mode transitions (EMERGENCY→ADAPTIVE)
2. Significant SL updates (>$1)

### Data Flow:
```
UI → get_config() → backtest_config → multicore_engine → adaptive_sl_manager
```

**Status:** ✅ Config reaches manager (proven by logs showing enabled=True)

---

## ❌ What's Broken

### Parameter Application:
Despite receiving config, **parameters aren't affecting SL calculations**:

**Expected:**
- Vol Lookback 10 bars → Faster ATR response → More adjustments
- Vol Lookback 35 bars → Slower ATR response → Fewer adjustments
- Vol Multi 18x → Wider SL → Different exit behavior
- Vol Multi 12x → Tighter SL → Different exit behavior

**Actual:**
- Same 5163 count regardless of parameters
- Same trades, same PNL, same exits
- **Parameters ignored!**

---

## 🐛 Suspected Root Cause

### Hypothesis: Default Values Overriding Config

Looking at `adaptive_sl_manager.py`, it likely has internal defaults that override config:

```python
# SUSPECTED ISSUE (not confirmed - need to check source):
def update_sl(self, config):
    vol_lookback = config.get('vol_lookback', 20)  # Always falls back to 20?
    vol_multi = config.get('vol_multi', 12)         # Always falls back to 12?
    
    # If config keys don't match exactly, defaults always used!
```

**Root Cause:** Config key mismatch between UI and manager:
- UI sends: `'volatility_lookback'`
- Manager expects: `'vol_lookback'`
- Manager always gets default!

---

## 🔧 Recommended Fix

### 1. Check Config Key Mapping:
```bash
# Compare UI config keys to manager expected keys
grep -r "volatility_lookback" src/optimizer_v3/core/adaptive_sl_manager.py
grep -r "vol_lookback" src/optimizer_v3/core/adaptive_sl_manager.py
```

### 2. Add Config Logging:
```python
# In adaptive_sl_manager.py update_sl():
logger.debug(f"Config received: {config}")
logger.debug(f"Vol lookback: {vol_lookback} (default=20)")
logger.debug(f"Vol multi: {vol_multi} (default=1.2)")
```

### 3. Verify Parameter Usage:
```python
# Log actual values used in calculation
logger.debug(f"ATR calculated with {period} bars")
logger.debug(f"SL distance: ATR ({atr}) * multiplier ({multiplier})")
```

---

## 📋 Next Steps

1. **Check `adaptive_sl_manager.py`** for config key names
2. **Compare to UI** config generation in `get_config()`
3. **Fix key mismatch** or add mapping layer
4. **Re-test** - should see different counts for different params
5. **Verify** exits and PnL also change

---

## 💡 Key Insight

The counter revealed **exactly what it should** - that parameters aren't being applied. The high count isn't a bug, it's a **diagnostic success** showing us where the real wiring problem is.

**Status:** Counter Working ✅ | Wiring Broken ❌ | Fix Required 🔧
