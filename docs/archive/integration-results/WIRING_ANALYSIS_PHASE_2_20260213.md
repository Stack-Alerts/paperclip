# WIRING TEST ANALYSIS - PHASE 2
## Date: 2026-02-13 09:53 AM
## Status: PARTIAL FIX - Secondary Issue Discovered

---

## ✅ PHASE 1 FIX: SUCCESS (Config Propagation)

**Evidence**: Unique results increased from ~1 to **5 different outcomes**

### Working Parameters (Produce Different Trade Counts):

| Parameter | Values Tested | Results | Status |
|-----------|--------------|---------|--------|
| **TP/SL Mode** | Fibonacci/Hybrid/Fixed | 94/94/96 trades | ✅ WORKING |
| **SL Adjustment** | Static vs Adaptive | 61 vs 94 trades | ✅ WORKING |
| **Risk % + Leverage** | (5%,5x) vs (10%,10x) | 57 vs 94 trades | ✅ WORKING |

---

## ⚠️ PHASE 2 ISSUE: Adaptive SL Parameters NOT Affecting Results

### Non-Working Parameters (All Produce 94 Trades):

| Scenario | Parameter Varied | Expected | Actual | Status |
|----------|-----------------|----------|--------|--------|
| **CRITICAL_001** | Balanced preset | Baseline | 94 | 📍 Baseline |
| **CRITICAL_005** | Conservative (wider SLs) | More/different trades | 94 | ❌ IDENTICAL |
| **CRITICAL_006** | Aggressive (tighter SLs) | Fewer/different trades | 94 | ❌ IDENTICAL |
| **PARAM_VOL_LB_LOW** | Vol Lookback = 10 bars | Different | 94 | ❌ IDENTICAL |
| **PARAM_VOL_LB_HIGH** | Vol Lookback = 30 bars | Different | 94 | ❌ IDENTICAL |
| **PARAM_VOL_MULTI_TIGHT** | Vol Multiplier = 1.0x | Different | 94 | ❌ IDENTICAL |
| **PARAM_VOL_MULTI_LOOSE** | Vol Multiplier = 1.8x | Different | 94 | ❌ IDENTICAL |
| **PARAM_SL_RANGE_TIGHT** | Min=0.6%, Max=1.0% | Different | 94 | ❌ IDENTICAL |
| **PARAM_SL_RANGE_LOOSE** | Min=1.2%, Max=2.5% | Different | 94 | ❌ IDENTICAL |
| **PARAM_MIN_RR_LOW** | Min R:R = 1.5 | Different | 94 | ❌ IDENTICAL |
| **PARAM_MIN_RR_HIGH** | Min R:R = 2.5 | Different | 94 | ❌ IDENTICAL |
| **PARAM_CAPITAL_LOW** | $5,000 capital | Different | 94 | ❌ IDENTICAL |
| **PARAM_CAPITAL_HIGH** | $25,000 capital | Different | 94 | ❌ IDENTICAL |

**Pattern**: ALL adaptive_sl sub-parameters produce identical 94 trades!

---

## 🔬 ROOT CAUSE HYPOTHESIS

### Config IS Being Passed (✓) BUT NOT USED (✗)

**Evidence from logs/wiring-test/multicore_config.log:**
```
Config keys: 23+, adaptive_sl: 9 sub-keys
```
✅ Config contains all parameters

**But trade counts show:**
- Changing `volatility_lookback` from 10 to 30 bars → **NO EFFECT**
- Changing `volatility_multiplier` from 1.0x to 1.8x → **NO EFFECT**
- Changing `min_sl_pct`/`max_sl_pct` ranges → **NO EFFECT**

### Possible Causes:

1. **Multicore engine not using adaptive_sl config**
   - Config received but ignored in subprocess execution
   - Falls back to default/hardcoded values

2. **Adaptive SL Manager not initialized in multicore path**
   - Single-core path: Creates adaptive_sl_manager
   - Multicore path: Missing initialization?

3. **Parameters used for SL calculation but entries drive trade count**
   - SL levels vary (not visible in trade count)
   - But entries are identical → same trade count
   - **NEED TO CHECK EXIT REASONS/PNL** (not just trade count!)

---

## 🎯 NEXT INVESTIGATION STEPS

### Hypothesis Testing:

**Test #1**: Check if EXIT REASONS differ (even if count is same)
- Same 94 trades but different exit types?
- Different PnL distributions?
- Different bars_held averages?

**Test #2**: Verify multicore subprocess uses adaptive_sl
- Does multicore_backtest_engine.py initialize adaptive_sl_manager?
- Are adaptive_sl parameters passed to simulation logic?

**Test #3**: Single-core comparison
- Run same tests in **single-core mode** (use_multicore=False)
- Check if parameters affect results there

---

## 📊 RECOMMENDATION

Test results suggest **TRADE COUNT is insufficient metric** for parameter validation.

**Better Metrics to Check:**
1. Exit type distribution (TP1/TP2/TP3/SL/TIME_LIMIT)
2. Average bars held (should vary with max_bars_held)
3. PnL distribution (should vary with SL tightness)
4. Win rate (should vary with SL strategy)

**Action Items**:
1. ✅ Phase 1 complete: Config propagation fixed
2. ⏳ Phase 2 needed: Verify config USAGE in multicore execution
3. ⏳ Phase 3 needed: Expand test metrics beyond trade count

---

## CONCLUSION

**Progress**: Config wiring partially fixed (3 params → 23+ params passed)

**Remaining Issue**: Adaptive SL parameters reach multicore but may not be USED by execution logic.

**Impact**: Entry logic works, exit logic needs investigation.
