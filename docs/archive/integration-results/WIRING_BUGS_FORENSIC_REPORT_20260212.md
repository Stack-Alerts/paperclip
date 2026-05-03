# WIRING BUGS FORENSIC REPORT
**Date:** 2026-02-12 14:55:00  
**Severity:** CRITICAL - Real money at risk  
**Impact:** 90% of UI parameters have NO EFFECT on backtest results

---

## EXECUTIVE SUMMARY

The backtest wiring verification test revealed **catastrophic parameter isolation**:
- **23 different configurations** produced only **3 unique results** (60, 56, 71 trades)
- Only **TP/SL Mode** affects outcomes (Fibonacci/Hybrid/Fixed)
- **ALL other parameters** are completely ignored by the backtest engine

### Test Results Analysis
```
Fibonacci mode:  60 trades (17 occurrences!) ← IDENTICAL despite different params
Hybrid mode:     56 trades (2 occurrences)
Fixed mode:      71 trades (4 occurrences)
```

**Critical Finding:** Changing these parameters produced ZERO impact:
- Adaptive SL presets (Conservative/Balanced/Aggressive)
- SL delay, emergency SL, volatility settings
- **Max bars held: 5 vs 200** ← NO DIFFERENCE!
- Risk/reward ratios, capital levels
- Starting capital ($5k vs $25k)
- Min risk:reward (1.5 vs 2.5)

---

## ROOT CAUSE ANALYSIS

### The Configuration Journey (Where It Breaks)

```
UI Panel (backtest_config_panel.py)
  ↓ [✓ ALL params collected correctly in get_config()]
  ↓
BacktestWorker.__init__()
  ↓ [✓ Config stored in self.config]
  ↓
BacktestWorker.run()
  ↓ [✓ Config logged to Live Output (looks good!)]
  ↓ [❌ BREAK #1: Config not passed to tpsl_calculator!]
  ↓ [❌ BREAK #2: Config not passed to adaptive_sl_manager!]
  ↓ [❌ BREAK #3: Config not properly passed to multicore engine!]
  ↓
Result: Parameters logged but NEVER USED in calculations!
```

---

## DETAILED WIRING BREAKS

### BREAK #1: TP/SL Calculator Ignores Config

**Location:** `src/optimizer_v3/core/tpsl_calculator.py`

**Problem:** Calculator receives `config` parameter but only uses 2 fields:
- `fixed_sl_percent` (Fixed mode only)
- `fixed_tp_percent` (Fixed mode only)

**Missing Usage:**
```python
# These config values are NEVER read:
config['min_risk_reward']        # Min R:R ratio ← IGNORED
config['adaptive_sl'][...]       # All Adaptive SL params ← IGNORED
config['max_bars_held']          # Max hold time ← IGNORED (in calc)
config['starting_capital']       # Capital amount ← IGNORED
config['risk_per_trade_pct']     # Risk % ← IGNORED
config['max_leverage']           # Leverage ← IGNORED
```

**Evidence:** Lines 139-157 in `tpsl_calculator.py`
```python
def _calculate_hybrid_levels(..., config: Dict, ...):
    # WIRING BUG: config parameter is NEVER USED!
    # Should read config['hybrid_atr_multiplier'] etc.
    # Instead uses hardcoded values
```

---

### BREAK #2: Adaptive SL Manager Not Receiving Config Properly

**Location:** `src/strategy_builder/ui/backtest_config_panel.py` line 1089

**Current Code:**
```python
# Line 1089-1096: Adaptive SL call
sl_result = adaptive_sl_manager.update_sl(
    position_entry_price=float(evaluator.current_trade.entry_price),
    current_bar=current_bar,
    bars_since_entry=bars_since_entry,
    lookback_bars=lookback_bars[-self.config['adaptive_sl']['volatility_lookback']:],
    config=self.config['adaptive_sl'],  # ← Nested dict passed
    entry_side=side
)
```

**Problem:** Passes `self.config['adaptive_sl']` but this is a NESTED dict that may not align with what AdaptiveSLManager expects.

**Test Evidence:** PARAM_VOL_LB_LOW vs PARAM_VOL_LB_HIGH both produced **60 trades** (IDENTICAL!)
- Volatility lookback 10 vs 30 bars should cause different SL distances
- Zero impact = parameter not wired

---

### BREAK #3: Max Bars Held Not Checked Correctly

**Location:** `src/strategy_builder/ui/backtest_config_panel.py` line 1106

**Current Code:**
```python
# Line 1106-1113: Max bars check
bars_held = i - evaluator.current_trade.entry_bar
max_bars = self.config.get('max_bars_held', 200)

if bars_held >= max_bars:
    result.should_exit = True
    result.exit_reason = f"Max Hold Time ({max_bars} bars)"
```

**Test Evidence:** EDGE_001 set `max_bars_held=5` vs default `200`
- Result: **BOTH produced 60 trades** (IDENTICAL!)
- This means the `if bars_held >= max_bars` check is NEVER triggering
- Likely because `evaluator.current_trade` is None most of the time

---

### BREAK #4: Multicore Path Missing Full Config

**Location:** `src/strategy_builder/ui/backtest_config_panel.py` line 1053-1058

**Current Code:**
```python
# Serialize config for subprocess
mc_config = {
    'tpsl_mode': self.config.get('tpsl_mode', 'Fibonacci'),
    'max_bars_held': self.config.get('max_bars_held', 200),
    'strategy_type': strategy_config.get('strategy_type', 'Bullish')
}
```

**Problem:** Only passes 3 fields! Missing:
- adaptive_sl config (all 9 parameters!)
- risk_per_trade_pct
- min_risk_reward
- starting_capital
- max_leverage
- confluence_threshold

**Impact:** Multicore path can NEVER use these parameters

---

### BREAK #5: Confluence Threshold Not Injected

**Location:** `src/strategy_builder/ui/backtest_config_panel.py` line 1756

**Current Code:**
```python
strategy_config_dict = self.orchestrator.serialize_config_for_backtest()
```

**Problem:** `serialize_config_for_backtest()` returns database config, which doesn't include UI-only values like `confluence_threshold`!

**Evidence:** Line 1759 tries to fix this:
```python
# CRITICAL FIX: Inject UI confluence threshold
strategy_config_dict['confluence_threshold'] = self.confluence_spin.value()
```

But this only happens in `_on_run_clicked()`, not in `_run_test_and_wait()` (used by wiring tests!)

---

## PARAMETERS TESTED BUT NOT WIRED

| Parameter | UI Widget | Config Key | Where It Should Be Used | Status |
|-----------|-----------|------------|-------------------------|--------|
| **Adaptive SL Preset** | Radio buttons | `adaptive_preset` | AdaptiveSLManager | ❌ NOT USED |
| **SL Delay** | `delay_spin` | `adaptive_sl.delay_bars` | Worker exit check | ⚠️ LOGGED ONLY |
| **Emergency SL** | `emergency_spin` | `adaptive_sl.emergency_sl_pct` | AdaptiveSLManager | ⚠️ LOGGED ONLY |
| **Volatility Lookback** | `vol_lookback_spin` | `adaptive_sl.volatility_lookback` | AdaptiveSLManager | ❌ NOT USED |
| **Volatility Multiplier** | `vol_multi_spin` | `adaptive_sl.volatility_multiplier` | AdaptiveSLManager | ❌ NOT USED |
| **Min SL %** | `min_sl_spin` | `adaptive_sl.min_sl_pct` | AdaptiveSLManager | ❌ NOT USED |
| **Max SL %** | `max_sl_spin` | `adaptive_sl.max_sl_pct` | AdaptiveSLManager | ❌ NOT USED |
| **Starting Capital** | `capital_spin` | `starting_capital` | Position sizer | ❌ NOT USED |
| **Risk %** | `risk_spin` | `risk_per_trade_pct` | Position sizer | ❌ NOT USED |
| **Min R:R** | `rr_spin` | `min_risk_reward` | Entry filter | ❌ NOT USED |
| **Leverage** | `leverage_spin` | `max_leverage` | Position sizer | ❌ NOT USED |
| **Confluence** | `confluence_spin` | `confluence_threshold` | SignalEvaluator | ⚠️ PARTIAL (missing in test path) |
| **Max Bars Held** | `max_bars_spin` | `max_bars_held` | Worker exit check | ❌ CHECK BROKEN |

**Legend:**
- ✓ WORKING: Parameter affects results
- ⚠️ LOGGED ONLY: Displayed in UI but not used in calculations
- ❌ NOT USED: Completely ignored
- ❌ CHECK BROKEN: Logic exists but doesn't trigger

---

## FINANCIAL IMPACT

**Scenario:** User optimizes these parameters for weeks:
1. Tests 100 combinations of Adaptive SL settings
2. Finds "optimal" volatility lookback = 25 bars, multiplier = 1.5x
3. Sees good backtest results, deploys to live trading
4. **DISCOVERS:** Those parameters had ZERO effect! Results were from TP/SL mode only
5. **RESULT:** False confidence, wrong parameter optimization, real money loss

**Estimated Impact:** 
- User wastes 80+ hours optimizing dead parameters
- False backtest validation (thinks strategy is robust when <kbd>it isn't)
- Live trading with unvalidated risk parameters
- Potential: **$10,000+ losses** from incorrect risk management

---

## RECOMMENDED FIXES

### Priority 1: Fix TP/SL Calculator Wiring

**File:** `src/optimizer_v3/core/tpsl_calculator.py`

```python
def _calculate_hybrid_levels(..., config: Dict, ...):
    # START with Fibonacci
    fib_levels = self._calculate_fibonacci_levels(...)
    
    # FIX: Actually USE config parameters!
    atr_multiplier = config.get('hybrid_atr_multiplier', 1.0)  # From UI!
    min_rr = config.get('min_risk_reward', 1.5)  # Validate R:R!
    
    # Apply ATR buffer
    atr = self._calculate_atr(lookback_bars[-14:])
    if entry_side == 'LONG':
        fib_levels.stop_loss -= (atr * atr_multiplier)
    else:
        fib_levels.stop_loss += (atr * atr_multiplier)
    
    # VALIDATE min R:R
    risk = abs(entry_price - fib_levels.stop_loss)
    reward = abs(fib_levels.take_profit_1 - entry_price)
    actual_rr = reward / risk if risk > 0 else 0
    
    if actual_rr < min_rr:
        # Adjust TP to meet min R:R requirement
        fib_levels.take_profit_1 = entry_price + (risk * min_rr)
```

### Priority 2: Fix Adaptive SL Manager Calls

**File:** `src/strategy_builder/ui/backtest_config_panel.py`

```python
# Line 1089: Ensure FULL config passed
if adaptive_sl_manager and evaluator.current_trade:
    sl_result = adaptive_sl_manager.update_sl(
        position_entry_price=float(evaluator.current_trade.entry_price),
        current_bar=current_bar,
        bars_since_entry=bars_since_entry,
        lookback_bars=lookback_bars[-self.config['adaptive_sl']['volatility_lookback']:],
        config=self.config,  # ← Pass FULL config, not just nested dict!
        entry_side=side
    )
```

### Priority 3: Fix Max Bars Check

**File:** `src/strategy_builder/ui/backtest_config_panel.py`

```python
# Line 1106: Add defensive checks
if evaluator.current_trade and hasattr(evaluator.current_trade, 'entry_bar'):
    bars_held = i - evaluator.current_trade.entry_bar
    max_bars = self.config.get('max_bars_held', 200)
    
    # DEBUG: Log when close to limit
    if bars_held >= max_bars * 0.9:
        self.live_message.emit(
            f"Trade approaching max hold: {bars_held}/{max_bars} bars",
            "WARNING",
            "RISK"
        )
    
    if bars_held >= max_bars:
        result.should_exit = True
        result.exit_reason = f"Max Hold Time ({max_bars} bars)"
        self.live_message.emit(
            f"Max bars triggered: {bars_held} >= {max_bars}",
            "ACTION",
            "EXIT"
        )
```

### Priority 4: Fix Multicore Config Serialization

**File:** `src/strategy_builder/ui/backtest_config_panel.py`

```python
# Line 1053: Pass FULL config to multicore
mc_config = {
    'tpsl_mode': self.config.get('tpsl_mode', 'Fibonacci'),
    'max_bars_held': self.config.get('max_bars_held', 200),
    'strategy_type': strategy_config.get('strategy_type', 'Bullish'),
    
    # FIX: Add missing parameters!
    'adaptive_sl': self.config.get('adaptive_sl', {}),
    'risk_per_trade_pct': self.config.get('risk_per_trade_pct', 10),
    'min_risk_reward': self.config.get('min_risk_reward', 1.5),
    'starting_capital': self.config.get('starting_capital', 10000),
    'max_leverage': self.config.get('max_leverage', 10),
    'confluence_threshold': self.config.get('confluence_threshold', 40)
}
```

### Priority 5: Add Parameter Usage Validation

**New File:** `tests/integration/test_parameter_usage.py`

```python
def test_parameter_actually_used(param_name, value1, value2):
    """Test that changing a parameter changes results"""
    # Run backtest with value1
    result1 = run_backtest_with_param(param_name, value1)
    
    # Run backtest with value2
    result2 = run_backtest_with_param(param_name, value2)
    
    # ASSERT: Results should differ!
    assert result1['trades'] != result2['trades'] or \
           result1['total_pnl'] != result2['total_pnl'], \
           f"Parameter {param_name} has NO EFFECT on results!"
```

---

## TESTING RECOMMENDATIONS

1. **Re-run wiring tests** after each fix
2. **Add unit tests** for each calculator to verify config usage
3. **Add integration tests** that assert different configs produce different results
4. **Add logging** to show which config values are being READ during backtest

---

## CONCLUSION

This is a **textbook case of parameter illusion**:
- UI shows parameters
- Config logs parameters  
- User thinks parameters are working
- **Reality: Parameters have ZERO effect**

**Severity: CRITICAL** - This affects ALL backtesting, ALL parameter optimization, and could lead to significant live trading losses.

**Recommendation:** Fix ALL wiring breaks before ANY further development or live deployment.

---

**Report Generated:** 2026-02-12 14:55:00  
**Author:** NAUTILUS EXPERT - Forensic Analysis  
**Next Steps:** Systematic repair of all 5 breaks + verification testing
