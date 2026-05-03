# 🔬 WIRING VERIFICATION TEST - BUG ANALYSIS REPORT

**Date:** February 10, 2026  
**Test Run:** wiring_test_2026-02-10_15-09-55.csv  
**Total Scenarios:** 23  
**Success Rate:** 100% (all tests ran)  
**Unique Results:** 6 out of 23 (26% variation)  
**Status:** ⚠️ **CRITICAL WIRING BUGS DETECTED**

---

## 📊 TRADE COUNT DISTRIBUTION

| Trade Count | Test Count | Scenarios |
|-------------|------------|-----------|
| **76 trades** | **14 tests** | CRITICAL_001, CRITICAL_005, CRITICAL_006, EDGE_002-005, PARAM_VOL_* (all), PARAM_SL_RANGE_*, PARAM_MIN_RR_*, PARAM_CAPITAL_* |
| 77 trades | 1 test | CRITICAL_002 |
| 81 trades | 1 test | CRITICAL_003 |
| 45 trades | 2 tests | CRITICAL_004, EDGE_001 |
| 43 trades | 1 test | CRITICAL_007 |
| 57 trades | 1 test | CRITICAL_008 |

---

## ✅ PARAMETERS THAT WORK (Properly Wired)

These parameters **DO affect backtest results**:

### 1. TP/SL Mode ✅
- **Fibonacci:** 76 trades (CRITICAL_001)
- **Hybrid:** 77 trades (CRITICAL_002)
- **Fixed:** 81 trades (CRITICAL_003)
- **Status:** WORKING - Different modes produce different trade counts

### 2. SL Adjustment Mode ✅
- **Adaptive v2.0:** 76 trades (CRITICAL_001)
- **Static:** 45 trades (CRITICAL_004)
- **Status:** WORKING - Adaptive vs Static produces significantly different results

### 3. Max Bars Held ✅
- **200 bars:** 76 trades (CRITICAL_001)
- **5 bars:** 45 trades (EDGE_001)
- **Status:** WORKING - Time limit affects trade count

### 4. Risk/Leverage Combination ✅
- **10% risk + 10x leverage:** 76 trades (EDGE_005)
- **5% risk + 5x leverage:** 43 trades (CRITICAL_007)
- **Status:** WORKING - Risk profile affects results

---

## ❌ PARAMETERS THAT DON'T WORK (Wiring Bugs!)

These parameters **DO NOT affect backtest results** (always produce 76 trades):

### 1. Adaptive SL Presets ❌ CRITICAL BUG
**All presets produce identical 76 trades:**
- **Conservative** (delay=3, emergency=3%, vol_multi=1.5x): 76 trades
- **Balanced** (delay=2, emergency=2%, vol_multi=1.2x): 76 trades  
- **Aggressive** (delay=1, emergency=2%, vol_multi=1.0x): 76 trades

**Expected:** Conservative should have widest SLs (most trades), Aggressive should have tightest SLs (fewest trades)

**Actual:** All identical - presets are ignored!

**Bug Location:** Adaptive SL Manager not reading preset configuration from backtest_config

---

### 2. Volatility Lookback ❌ CRITICAL BUG
**All lookback periods produce identical 76 trades:**
- **10 bars:** 76 trades
- **20 bars (default):** 76 trades
- **30 bars:** 76 trades

**Expected:** Different lookback periods should calculate different ATR values, affecting SL distance

**Actual:** All identical - lookback parameter is ignored!

**Bug Location:** Adaptive SL Manager hardcoded to 20 bars OR not reading volatility_lookback from config

---

### 3. Volatility Multiplier ❌ CRITICAL BUG
**All multipliers produce identical 76 trades:**
- **1.0x (tight SL):** 76 trades
- **1.2x (balanced):** 76 trades
- **1.8x (loose SL):** 76 trades

**Expected:** Higher multiplier = wider SL = fewer stop-outs = more trades

**Actual:** All identical - multiplier is ignored!

**Bug Location:** Adaptive SL Manager using hardcoded multiplier OR not reading from config

---

### 4. Min/Max SL Range ❌ CRITICAL BUG
**All SL ranges produce identical 76 trades:**
- **Tight (0.6% - 1.0%):** 76 trades
- **Loose (1.2% - 2.5%):** 76 trades

**Expected:** Tighter range = more frequent stop-outs = fewer trades

**Actual:** All identical - range is ignored!

**Bug Location:** Adaptive SL Manager using hardcoded min/max OR not reading from config

---

### 5. Min Risk:Reward Ratio ❌ MEDIUM BUG
**All R:R ratios produce identical 76 trades:**
- **1.5:1 (lower threshold):** 76 trades
- **2.5:1 (higher threshold):** 76 trades

**Expected:** Higher R:R requirement = fewer trades (harder to meet)

**Actual:** All identical - R:R filter not applied!

**Bug Location:** Signal evaluator not checking min_risk_reward from config

---

### 6. Starting Capital ❌ LOW PRIORITY BUG
**All capital amounts produce identical 76 trades:**
- **$5,000:** 76 trades
- **$10,000:** 76 trades
- **$25,000:** 76 trades

**Expected:** Capital shouldn't affect trade COUNT (but should affect position sizing)

**Actual:** Correctly doesn't affect count (expected behavior)

**Status:** This is CORRECT behavior - capital affects position size not entry decisions

**No bug** - this is expected!

---

## 🔍 ROOT CAUSE ANALYSIS

### Primary Issue: Adaptive SL v2.0 Configuration Not Passed to Manager

**Evidence:**
1. All Adaptive SL v2.0 parameters produce identical results (76 trades)
2. Only top-level SL mode (Adaptive vs Static) makes a difference
3. Detailed Adaptive SL settings (volatility, multipliers, ranges) are ignored

**Hypothesis:**
The `adaptive_sl` config dictionary is not being passed to `AdaptiveSLManager.update_sl()` OR the manager is using hardcoded defaults instead of config values.

**Code Path to Investigate:**
```python
# backtest_config_panel.py - Line ~2310
config['adaptive_sl'] = {
    'enabled': True,
    'delay_enabled': True,
    'delay_bars': 2,  # ← User selects this
    'emergency_sl_pct': 2,  # ← User selects this
    'volatility_lookback': 20,  # ← User selects this
    'volatility_multiplier': 1.2,  # ← User selects this
    'min_sl_pct': 0.7,  # ← User selects this
    'max_sl_pct': 2.0,  # ← User selects this
    ...
}

# ↓ Passed to BacktestWorker
# ↓ Passed to AdaptiveSLManager.update_sl()

# adaptive_sl_manager.py - Does it READ these values?
# SUSPECT: Uses hardcoded defaults instead!
```

---

## 🛠️ CORRECTION PLAN

### Phase 1: Fix Adaptive SL Manager Config Reading (CRITICAL)

**File:** `src/optimizer_v3/core/adaptive_sl_manager.py`

**Issue:** Manager likely using hardcoded defaults instead of config values

**Fix Required:**
1. Verify `update_sl()` accepts `config` parameter ✓ (already does)
2. Check if it READS from config or uses defaults
3. Replace any hardcoded values with `config.get('param', default)`

**Example Fix:**
```python
# BEFORE (suspected)
volatility_lookback = 20  # Hardcoded!
volatility_multiplier = 1.2  # Hardcoded!

# AFTER
volatility_lookback = config.get('volatility_lookback', 20)
volatility_multiplier = config.get('volatility_multiplier', 1.2)
```

**Verification:** Re-run wiring test - should see variation in PARAM_VOL_* tests

---

### Phase 2: Fix Min Risk:Reward Filter (MEDIUM)

**File:** `src/optimizer_v3/core/institutional_signal_evaluator.py`

**Issue:** R:R ratio not checked before trade entry

**Fix Required:**
1. In `evaluate_bar()`, after calculating TP/SL levels
2. Calculate R:R ratio: `(TP1 - entry) / (entry - SL)`
3. Compare to `config.get('min_risk_reward', 1.2)`
4. If R:R too low, don't enter trade

**Example Fix:**
```python
# After TP/SL calculation
if tpsl_levels:
    risk = abs(entry_price - tpsl_levels.stop_loss)
    reward = abs(tpsl_levels.take_profit_1 - entry_price)
    rr_ratio = reward / risk if risk > 0 else 0
    
    min_rr = self.config.get('min_risk_reward', 1.2)
    if rr_ratio < min_rr:
        result.should_enter = False
        result.rejection_reason = f"R:R too low: {rr_ratio:.2f} < {min_rr}"
```

**Verification:** Re-run wiring test - should see variation in PARAM_MIN_RR_* tests

---

### Phase 3: Verify Preset Mapping (LOW)

**File:** `src/strategy_builder/ui/backtest_config_panel.py`

**Issue:** Presets may not be translating to config values correctly

**Fix Required:**
1. Check `_apply_conservative_preset()`, `_apply_balanced_preset()`, `_apply_aggressive_preset()`
2. Verify they set UI widget values correctly
3. Verify `get_config()` reads these values into `adaptive_sl` dict

**Already Verified:** UI widgets DO get set correctly (visual inspection during test)

**Likely Not the Issue:** Values are reaching config correctly

---

## 📋 TESTING CHECKLIST

After applying fixes, re-run wiring test and verify:

- [ ] PARAM_VOL_LB_LOW (10 bars) produces DIFFERENT trade count than default
- [ ] PARAM_VOL_LB_HIGH (30 bars) produces DIFFERENT trade count than default
- [ ] PARAM_VOL_MULTI_TIGHT (1.0x) produces DIFFERENT trade count than default
- [ ] PARAM_VOL_MULTI_LOOSE (1.8x) produces DIFFERENT trade count than default
- [ ] PARAM_SL_RANGE_TIGHT produces DIFFERENT trade count than default
- [ ] PARAM_SL_RANGE_LOOSE produces DIFFERENT trade count than default
- [ ] PARAM_MIN_RR_LOW (1.5) produces DIFFERENT trade count than default
- [ ] PARAM_MIN_RR_HIGH (2.5) produces DIFFERENT trade count than default
- [ ] CRITICAL_005 (Conservative) produces DIFFERENT trade count than CRITICAL_001 (Balanced)
- [ ] CRITICAL_006 (Aggressive) produces DIFFERENT trade count than CRITICAL_001 (Balanced)

**Expected Result:** Unique trade counts should increase from 6 to 16-20

---

## 🎯 PRIORITY

**P0 - CRITICAL (Fix Immediately):**
1. Adaptive SL Manager config reading (affects ALL Adaptive SL parameters)

**P1 - HIGH (Fix Soon):**
2. Min Risk:Reward filter implementation

**P2 - LOW (Nice to Have):**
3. Starting Capital is WORKING AS DESIGNED (no fix needed)

---

## 📝 CONCLUSION

**Major Finding:** Adaptive SL v2.0 detailed configuration is NOT being applied during backtests. The system acknowledges "Adaptive SL enabled" but uses hardcoded defaults for all parameters.

**Impact:** Users adjusting Adaptive SL settings (volatility lookback, multipliers, ranges, presets) see NO effect on backtest results.

**Root Cause:** `AdaptiveSLManager.update_sl()` likely ignores config parameter and uses hardcoded defaults.

**Fix Effort:** 30-60 minutes (simple config reading fix)

**Risk:** Low (just reading existing config values instead of hardcoding)
