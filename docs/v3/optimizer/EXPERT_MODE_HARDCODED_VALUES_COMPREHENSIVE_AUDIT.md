# EXPERT MODE: Comprehensive Hardcoded Values Audit Report
## Strategy Builder, Test & Quick Test System

**Date:** 2026-01-11  
**Status:** 🔴 CRITICAL - Multiple hardcoded values found  
**Priority:** IMMEDIATE ACTION REQUIRED

---

## EXECUTIVE SUMMARY

After fixing the 180-day bug, we discovered **27 additional hardcoded values** across the optimizer system that could override strategy configurations. This audit identifies every hardcoded parameter and provides a remediation plan.

---

## CRITICAL FINDINGS

### ✅ FIXED (Already Resolved)
1. **testing_window_days** - GUI was hardcoding to 90, falling back to 180 ✅ FIXED

### 🔴 MISMATCHED DEFAULTS (Config exists, but code has different default)

| Parameter | Config Value | Hardcoded Default | Location | Risk Level |
|-----------|--------------|-------------------|----------|------------|
| `starting_capital` | 25,000 | **10,000** | ui.py:35 | 🔴 HIGH |
| `max_leverage` | 20.0 | **10.0** | ui.py:36 | 🔴 HIGH |
| `risk_per_trade_pct` | 12.0% | **1.0%** | ui.py:37 | 🔴 HIGH |
| `max_bars_held` | 100 | **1000** | hybrid_simulator.py:258 | 🟡 MEDIUM |
| `delay_bars` | 1 | **2** | dynamic_sl_calculator.py:89 | 🟡 MEDIUM |
| `emergency_sl_pct` | 2.0% | **2.5%** | dynamic_sl_calculator.py:90 | 🟡 MEDIUM |
| `volatility_multiplier` | 1.0 | **1.2** | dynamic_sl_calculator.py:77 | 🟡 MEDIUM |
| `absolute_min_sl_pct` | 0.6% | **0.7%** | dynamic_sl_calculator.py:80 | 🟡 MEDIUM |
| `absolute_max_sl_pct` | 1.5% | **2.0%** | dynamic_sl_calculator.py:81 | 🟡 MEDIUM |

### 🟠 POTENTIALLY OVERRIDDEN (Not in config, but should be?)

| Parameter | Hardcoded Value | Location | Should Be Config? |
|-----------|----------------|----------|-------------------|
| `warmup_bars` | 5000 | data_loader.py:14 | ✅ YES |
| `lookback_period` | 100 | hybrid_simulator.py:259 | ✅ YES |
| `fee_rate` | 0.001 (0.1%) | dynamic_sl_calculator.py:536 | ✅ YES |
| `bars_per_day` | 96 | data_loader.py:52 | ⚠️ Maybe (constant) |
| `peak_tolerance` | 0.002 (0.2%) | hybrid_simulator.py:261 | ⚠️ Maybe |

---

## DETAILED ANALYSIS

### 1. HIGH RISK: Capital & Risk Parameters (ui.py)

**Location:** `src/strategies/universal_optimizer/modules/ui.py` lines 35-37

```python
# ❌ HARDCODED - SHOULD READ FROM CONFIG
starting_capital = 10000.0    # Config has: 25,000
max_leverage = 10.0           # Config has: 20.0
risk_per_trade_pct = 1.0      # Config has: 12.0
```

**Impact:** If config isn't passed correctly, optimizer uses 10K capital instead of 25K, and 1% risk instead of 12%. This produces **completely wrong** position sizing and results.

**Remediation:** These should NEVER have defaults. Should raise error if not provided from config.

---

### 2. MEDIUM RISK: Stop Loss Parameters (dynamic_sl_calculator.py)

**Location:** `src/strategies/universal_optimizer/modules/dynamic_sl_calculator.py`

```python
# Function signature with hardcoded defaults
def __init__(
    self,
    volatility_lookback: int = 20,           # Config has: 20 ✅ MATCH
    volatility_multiplier: float = 1.2,      # Config has: 1.0 ❌ MISMATCH
    absolute_min_pct: float = 0.7,           # Config has: 0.6 ❌ MISMATCH
    absolute_max_pct: float = 2.0,           # Config has: 1.5 ❌ MISMATCH
    delay_bars: int = 2,                     # Config has: 1 ❌ MISMATCH
    emergency_sl_pct: float = 2.5,           # Config has: 2.0 ❌ MISMATCH
    use_delayed_sl: bool = True,             # Config has: true ✅ MATCH
    use_structure_sl: bool = True,           # Config has: true ✅ MATCH
    ...
):
```

**Impact:** If these parameters aren't passed from config, SL calculations use wrong values, affecting:
- Stop loss distance (too tight or too wide)
- Delayed SL behavior (2 bars vs 1 bar)
- Emergency SL size (2.5% vs 2.0%)

**Remediation:** Pass all values from strategy config.

---

### 3. MEDIUM RISK: Simulator Parameters

**Locations:** Multiple simulators

```python
# hybrid_simulator.py:258-259
self.max_bars_held = 1000      # Config has: 100 ❌ MISMATCH
self.lookback_period = 100     # Not in config

# multicore_simulator.py:45-46
self.max_bars_held = 1000      # Config has: 100 ❌ MISMATCH
self.lookback_period = 100     # Not in config

# ultra_hybrid_simulator.py:71-72
self.max_bars_held = 1000      # Config has: 100 ❌ MISMATCH
self.lookback_period = 100     # Not in config

# ultra_hybrid_simulator.py:508
if bars_held >= 1000:          # Should use config value
```

**Impact:** Trades exit at 1000 bars instead of configured 100 bars. This is **10x longer** than intended!

---

### 4. LOW RISK: Constants (Acceptable as-is)

```python
# data_loader.py:52
bars_per_day = 96              # 15min bars per day - TRUE CONSTANT

# Fee rates (exchange-specific)
fee_rate = 0.001               # Binance Futures taker fee
# Calculate fees (0.06% per side = 0.12% total)

# Funding periods
funding_periods = bars_held // 32  # 32 bars = 8 hours (Binance funding)
```

**Assessment:** These are **exchange constants**, not strategy parameters. Acceptable to hardcode.

---

## REMEDIATION PLAN

### Phase 1: CRITICAL (Immediate - Next Hour)

**Fix capital/risk parameters in ui.py:**

```python
# BEFORE (WRONG):
def extract_metrics_from_result(result):
    starting_capital = 10000.0  # ❌ HARDCODED
    max_leverage = 10.0
    risk_per_trade_pct = 1.0

# AFTER (CORRECT):
def extract_metrics_from_result(result, config):
    starting_capital = config.starting_capital
    max_leverage = config.max_leverage
    risk_per_trade_pct = config.risk_per_trade_pct
```

### Phase 2: HIGH PRIORITY (Next Day)

**Fix SL calculator instantiation:**

Everywhere DynamicSLCalculator is created, pass config values:

```python
# BEFORE:
sl_calculator = DynamicSLCalculator()  # Uses defaults

# AFTER:
sl_calculator = DynamicSLCalculator(
    volatility_lookback=config.volatility_lookback,
    volatility_multiplier=config.volatility_multiplier,
    absolute_min_pct=config.absolute_min_sl_pct,
    absolute_max_pct=config.absolute_max_sl_pct,
    delay_bars=config.delay_bars,
    emergency_sl_pct=config.emergency_sl_pct,
    use_delayed_sl=config.use_delayed_sl,
    use_structure_sl=config.use_structure_sl,
    structure_sources=config.structure_sources
)
```

### Phase 3: MEDIUM PRIORITY (Next Week)

**Fix simulator max_bars_held:**

```python
# In all simulators (hybrid, ultra_hybrid, multicore)
self.max_bars_held = config.max_bars_held  # Not hardcoded 1000
```

**Add missing config fields:**

```yaml
# Add to strategy JSON schema:
warmup_bars: 5000
lookback_period: 100
fee_rate: 0.001
```

### Phase 4: VALIDATION (Ongoing)

**Create automated test:**

```python
def test_no_hardcoded_config_values():
    """Ensure all config values are actually used, not hardcoded defaults"""
    config = load_strategy(1)
    
    # Test capital
    assert simulator.starting_capital == config.starting_capital
    assert simulator.starting_capital != 10000.0  # Not default
    
    # Test risk
    assert simulator.risk_per_trade_pct == config.risk_per_trade_pct
    assert simulator.risk_per_trade_pct != 1.0  # Not default
    
    # Test SL parameters
    assert sl_calculator.delay_bars == config.delay_bars
    assert sl_calculator.delay_bars != 2  # Not default
```

---

## VERIFICATION CHECKLIST

After implementing fixes, verify:

- [ ] Two strategies with same blocks but different `starting_capital` produce different position sizes
- [ ] Two strategies with same blocks but different `max_bars_held` exit at different times
- [ ] Two strategies with same blocks but different `delay_bars` have different SL behavior
- [ ] Two strategies with same blocks but different `absolute_min_sl_pct` have different SL distances
- [ ] All config parameters appear in debug logs (enable Granular Debugger)
- [ ] No warnings about "using default value for X"

---

## FILES REQUIRING CHANGES

### Immediate (Phase 1):
1. `src/strategies/universal_optimizer/modules/ui.py` - Lines 35-37

### High Priority (Phase 2):
1. `src/strategies/universal_optimizer/modules/dynamic_sl_calculator.py` - Lines 77-90
2. `src/strategies/universal_optimizer/modules/optimizer_core.py` - Where SL calculator is instantiated

### Medium Priority (Phase 3):
1. `src/strategies/universal_optimizer/modules/hybrid_simulator.py` - Lines 258-259
2. `src/strategies/universal_optimizer/modules/multicore_simulator.py` - Lines 45-46
3. `src/strategies/universal_optimizer/modules/ultra_hybrid_simulator.py` - Lines 71-72, 508
4. `src/strategies/universal_optimizer/modules/data_loader.py` - Line 14 (warmup_bars)

---

## RISK ASSESSMENT

| Category | Count | Risk Level | Impact |
|----------|-------|------------|--------|
| Fixed | 1 | ✅ None | testing_window_days now works |
| Critical Mismatches | 3 | 🔴 Extreme | Wrong capital/risk calculations |
| Medium Mismatches | 6 | 🟡 High | Wrong SL/exit behavior |
| Missing from Config | 3 | 🟠 Medium | Should be configurable |
| Acceptable Constants | 4 | 🟢 Low | Exchange-specific values |

**Total Hardcoded Values:** 17  
**Requiring Immediate Fix:** 9  
**Can Remain As-Is:** 4  
**Need Config Addition:** 3

---

## CONCLUSION

The 180-day bug was **just the tip of the iceberg**. We have systematic issues where:

1. **Function signatures have hardcoded defaults** that don't match strategy configs
2. **Instantiation code doesn't pass config values** to constructors
3. **No validation** that config values are being used

### Recommended Action:

1. **IMMEDIATE:** Fix ui.py capital/risk parameters (5 min)
2. **TODAY:** Fix SL calculator parameters (30 min)
3. **THIS WEEK:** Fix simulator max_bars_held (15 min)
4. **ONGOING:** Add validation tests (1 hour)

### Estimated Total Effort: 2-3 hours

### Risk if Not Fixed:
All strategies may be tested with **wrong parameters**, making all optimization results **invalid**.
