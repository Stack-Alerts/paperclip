# PARAMETER IMPLEMENTATION AUDIT
## Complete Investigation of Risk/Reward Parameters

**Date**: February 13, 2026  
**Investigation**: Deep audit using Sprint documentation  
**Scope**: All Risk/Reward UI parameters  

---

## 🔍 DISCOVERY

After reviewing **Sprint 2.0.3** (TP/SL Management - COMPLETE), I found that some parameters are WIRED but NOT IMPLEMENTED in backtest logic.

---

## 📊 PARAMETER STATUS MATRIX

### ✅ FULLY IMPLEMENTED (Changes Affect Results):

| Parameter | Status | Used In | Effect |
|-----------|--------|---------|--------|
| **Confluence Threshold** |✅ WORKING | `institutional_signal_evaluator.py` | Filters trade entries |
| **Max Bars Held** | ✅ WORKING | `multicore_backtest_engine.py` | Forces exit after N bars |
| **Adaptive SL Settings** | ✅ WORKING | `adaptive_sl_manager.py` | Adjusts SL each bar |
| **TP/SL Mode** | ✅ WORKING | `tpsl_calculator.py` | Calculates TP/SL levels |

---

### ⚠️ WIRED BUT NOT USED (No Effect on Results):

| Parameter | Status | Current Behavior | Should Do |
|-----------|--------|------------------|-----------|
| **Starting Capital** | 🟡 DISPLAY ONLY | Metrics calculations only | Position sizing? |
| **Min Risk:Reward** | 🟡 VALIDATED ONLY | Validates but doesn't filter | Filter low R:R trades |
| **Risk % per Trade** | ❌ NOT USED | Position size hardcoded `0.1 BTC` | Calculate position from % |
| **Leverage** | ❌ NOT USED | Hardcoded `1.0x` | Apply leverage multiplier |

---

## 🎯 DETAILED FINDINGS

### 1. STARTING CAPITAL ($10,000 in UI)

**Current Implementation**:
```python
# backtest_config_panel.py - Line 450
'starting_capital': self.capital_spin.value(),

# Used ONLY for display:
total_return = (total_pnl / starting_capital) * 100  # Metrics calc
```

**Problem**: ✅ Passed to backend, but ❌ NOT used in trading logic  
**Effect**: Changing $10k → $50k has NO impact on trades  
**Should**: Maybe use for risk% position sizing? (See param #3)

---

### 2. MIN RISK:REWARD (30 in UI = 30:1)

**Current Implementation**:
```python
# tpsl_calculator.py - Line 89
min_rr = config.get('min_risk_reward', 1.5)
if risk_reward_ratio < min_rr and risk > 0:
    # Validates and logs warning
    # BUT TRADE STILL ENTERS! ❌
```

**Problem**: ✅ Validated, ❌ Doesn't reject trades  
**Effect**: Changing 30:1 → 12:1 has NO impact on which trades enter  
**Should**: Reject entry if R:R too low

---

### 3. RISK % PER TRADE (15% in UI)

**Current Implementation**:
```python
# backtest_config_panel.py - Line 451
'risk_per_trade_pct': self.risk_spin.value(),

# multicore_backtest_engine.py - Line 180
# Position size is HARDCODED:
'size': 0.1  # ← ALWAYS 0.1 BTC regardless of risk%!
```

**Problem**: ✅ Passed to backend, ❌ NEVER USED  
**Effect**: Changing 15% → 5% has ZERO impact  
**Should**: Calculate position  size from: `(capital × risk%) / SL_distance`

**Example**:
```python
# With $10,000 capital, 2% risk, SL $500 away:
position_btc = ($10,000 × 0.02) / $500 = 0.4 BTC

# Currently:
position_btc = 0.1 BTC  # ← HARDCODED
```

---

### 4. LEVERAGE (30x in UI)

**Current Implementation**:
```python
# backtest_config_panel.py - Line 454
'max_leverage': self.leverage_spin.value(),

# NOWHERE in backtest logic! ❌
# Position size calculations don't use leverage
```

**Problem**: ✅ Passed to backend, ❌ COMPLETELY IGNORED  
**Effect**: Changing 30x → 5x has NO impact  
**Should**: Multiply position size: `position × leverage`

---

### 5. CONFLUENCE THRESHOLD (20 pts in UI) ✅

**Current Implementation**:
```python
# institutional_signal_evaluator.py - Line 340
min_confluence = getattr(self.strategy_config, 'confluence_threshold', 40)
should_enter = confluence >= min_confluence  # ✅ FILTERS ENTRIES

if confluence < min_confluence:
    return no_entry  # ✅ REJECTS TRADE
```

**Status**: ✅ FULLY WORKING  
**Effect**: Changing 20 → 30 DOES change which trades enter  
**Result**: CORRECT - This param works!

---

### 6. MAX BARS HELD (200 in UI) ✅

**Current Implementation**:
```python
# multicore_backtest_engine.py - Line 195
bars_held = i - evaluator.current_trade.entry_bar
max_bars = backtest_config.get('max_bars_held', 200)

if bars_held >= max_bars:  # ✅ FORCES EXIT
    result.should_exit = True
    result.exit_reason = f"Max Hold Time ({max_bars} bars)"
```

**Status**: ✅ FULLY WORKING  
**Effect**: Changing 200 → 50 DOES force earlier exits  
**Result**: CORRECT - This param works!

---

## 📋 SPRINT DOCUMENTATION REVIEW

### What Sprint 2.0.3 Delivered:

According to `SPRINT_2_0_3_TPSL_MANAGEMENT.md`:

✅ **Delivered & Working**:
- TP/SL Calculator (Fibonacci/Hybrid/Fixed)
- Adaptive SL v2.0 Manager  
- Emergency SL during delay
- SL updates each candle
- Partial exits (TP1/TP2/TP3)
- Max bars held enforcement
- Confluence filtering

❌ **NOT in Sprint Scope** (Never Built):
- Position sizing from risk%
- Leverage application
- Starting capital usage
- Min R:R filtering

---

## 🎯 ROOT CAUSE

**The parameters ARE wired correctly** ✅  
**But 4 out of 6 are NOT IMPLEMENTED in backtest logic** ❌

This is BY DESIGN - Sprint 2.0.3 focused on TP/SL management, NOT position sizing/leverage.

**Position sizing and leverage** were likely planned for a FUTURE sprint that hasn't been implemented yet.

---

## 💡 RECOMMENDED ACTIONS

### Option 1: Remove Non-Functional Params from UI
- Hide Starting Capital slider (display only after backtest)
- Hide Risk % (until position sizing implemented)
- Hide Leverage (until margin trading implemented)
- Hide Min R:R (until filtering implemented)
- **Keep**: Confluence, Max Bars, Adaptive SL params

### Option 2: Implement Missing Features
Would require NEW sprint to implement:
- Position sizing calculator
- Leverage multiplier
- Min R:R filter
- Capital-aware risk management

**Estimated Effort**: 2-3 days for full implementation

### Option 3: Document Current Behavior
- Add tooltips: "Display only - doesn't affect backtest"
- Update UI labels to clarify
- User guide explaining which params work

---

## ✅ CONCLUSION

**Investigation Result**: WIRING IS CORRECT ✅

**Real Issue**: Feature scope gap - Some UI controls exist but backend logic was never built for them.

**Working Parameters** (2/6):
1. Confluence Threshold ✅
2. Max Bars Held ✅

**Display-Only Parameters** (4/6):
3. Starting Capital (metrics only)
4. Min Risk:Reward (validation only)
5. Risk % (not used)
6. Leverage (not used)

**Next Step**: User decision on Option 1, 2, or 3 above.

---

**Audit Complete**: February 13, 2026 10:40 AM  
**Analyst**: Cline Institutional AI
