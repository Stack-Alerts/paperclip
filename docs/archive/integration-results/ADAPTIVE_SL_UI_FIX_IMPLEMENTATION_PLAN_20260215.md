# ADAPTIVE SL UI FIX - IMPLEMENTATION PLAN
**Date:** 2026-02-15  
**Status:** OPTION C APPROVED BY USER  
**Mode:** NAUTILUS EXPERT

---

## OBJECTIVE

**Make UI show EXACTLY what backend uses - zero conversion ambiguity**

Before: UI shows "7" labeled as "7%" but backend uses 0.7%  
After: UI shows "0.7%" and backend uses 0.7% ✅

---

## CHANGES REQUIRED

### 1. UI LAYER (backtest_config_panel.py)

#### A. Change SpinBox Types
```python
# BEFORE:
self.min_sl_spin = QSpinBox()  # Integer only (1, 2, 3...)
self.max_sl_spin = QSpinBox()

# AFTER:
self.min_sl_spin = QDoubleSpinBox()  # Decimal (0.5, 0.7, 1.0...)
self.max_sl_spin = QDoubleSpinBox()
```

#### B. Update Ranges & Defaults
```python
# BEFORE:
self.min_sl_spin.setRange(1, 50)  # Integer 1-50
self.min_sl_spin.setValue(7)
self.max_sl_spin.setRange(1, 50)
self.max_sl_spin.setValue(20)

# AFTER:
self.min_sl_spin.setRange(0.1, 10.0)  # Decimal 0.1-10.0%
self.min_sl_spin.setValue(0.7)  # 0.7% (was 7)
self.min_sl_spin.setDecimals(1)  # Show 1 decimal place
self.min_sl_spin.setSingleStep(0.1)  # Increment by 0.1%
self.min_sl_spin.setSuffix("%")  # Show % symbol

self.max_sl_spin.setRange(0.1, 10.0)
self.max_sl_spin.setValue(2.0)  # 2.0% (was 20)
self.max_sl_spin.setDecimals(1)
self.max_sl_spin.setSingleStep(0.1)
self.max_sl_spin.setSuffix("%")
```

#### C. Remove Division When Sending to Backend
```python
# BEFORE (line 1245-1246):
'min_sl_pct': self.min_sl_spin.value() / 10.0,  # 7 → 0.7
'max_sl_pct': self.max_sl_spin.value() / 10.0,  # 20 → 2.0

# AFTER:
'min_sl_pct': self.min_sl_spin.value(),  # 0.7 → 0.7 (no division!)
'max_sl_pct': self.max_sl_spin.value(),  # 2.0 → 2.0 (no division!)
```

#### D. Update Load From Config
```python
# BEFORE (line ~1309-1312):
if 'min_sl_pct' in asl:
    self.min_sl_spin.setValue(int(asl['min_sl_pct'] * 10))  # 0.7 → 7

# AFTER:
if 'min_sl_pct' in asl:
    self.min_sl_spin.setValue(asl['min_sl_pct'])  # 0.7 → 0.7 (no multiplication!)
```

#### E. Update Log Messages
```python
# BEFORE:
self.live_message.emit(f"   SL Range: {asl['min_sl_pct']}% to {asl['max_sl_pct']}%", ...)

# AFTER: (Actually this is already correct since we're showing the actual value!)
# No change needed - will now show "0.7% to 2.0%" correctly
```

---

### 2. BACKEND LAYER (adaptive_sl_manager.py)

#### A. Update Conversion Logic
```python
# BEFORE (line 196-203):
if 'min_sl_pct' in config:
    # NEW format - UI sends percentage (0.7 = 0.7%)
    min_sl_percent = config['min_sl_pct'] / 100.0  # 0.7 → 0.007 ❌ WRONG!
    max_sl_percent = config['max_sl_pct'] / 100.0

# AFTER:
if 'min_sl_pct' in config:
    # UI sends actual percentage (0.7 = 0.7%)
    # Convert to decimal: 0.7% → 0.007
    min_sl_percent = config['min_sl_pct'] / 100.0  # 0.7 → 0.007 ✅ CORRECT!
    max_sl_percent = config['max_sl_pct'] / 100.0  # 2.0 → 0.020 ✅ CORRECT!
```

**Wait - this is already correct! The backend code DOESN'T need changing!**

The bug was the double division:
- OLD: UI sends 0.7 (from 7/10), backend divides by 100 → 0.007 (0.7%)
- NEW: UI sends 0.7 (actual), backend divides by 100 → 0.007 (0.7%) ✅

So backend stays the same! Only UI changes needed.

---

### 3. VOLATILITY MULTIPLIER (Check if needs same treatment)

**Current State:**
```python
self.vol_multi_spin = QSpinBox()
self.vol_multi_spin.setRange(5, 30)  # 5-30
self.vol_multi_spin.setValue(12)  # Default 12

# When sending:
'volatility_multiplier': self.vol_multi_spin.value() / 10.0  # 12 → 1.2
```

**Analysis:** This is a multiplier (1.2x ATR), not a percentage.  
**Decision:** Change to QDoubleSpinBox for consistency!

```python
# AFTER:
self.vol_multi_spin = QDoubleSpinBox()
self.vol_multi_spin.setRange(0.5, 3.0)  # 0.5x - 3.0x
self.vol_multi_spin.setValue(1.2)  # Default 1.2x
self.vol_multi_spin.setDecimals(1)
self.vol_multi_spin.setSingleStep(0.1)
self.vol_multi_spin.setSuffix("x")  # Show multiplier symbol

# When sending:
'volatility_multiplier': self.vol_multi_spin.value()  # 1.2 → 1.2 (no division!)
```

---

## FILES TO MODIFY

1. **src/strategy_builder/ui/backtest_config_panel.py**
   - Line ~990: Change min_sl_spin to QDoubleSpinBox
   - Line ~991: Update range, decimals, step, suffix
   - Line ~995: Change max_sl_spin to QDoubleSpinBox  
   - Line ~996: Update range, decimals, step, suffix
   - Line ~1000: Change vol_multi_spin to QDoubleSpinBox
   - Line ~1001: Update range, decimals, step, suffix
   - Line 1244-1246: Remove /10.0 divisions
   - Line ~1309-1314: Remove *10 multiplications when loading

2. **src/optimizer_v3/core/adaptive_sl_manager.py**
   - Line 193: Remove /10.0 from vol_multi  
   - NO OTHER CHANGES NEEDED! Backend logic already correct.

---

## MIGRATION STRATEGY FOR EXISTING CONFIGS

**Problem:** Old saved configs have values like `min_sl_pct: 7`  
**New system** expects: `min_sl_pct: 0.7`

**Solution:** Version detection and auto-conversion

```python
# When loading config:
if 'min_sl_pct' in asl:
    value = asl['min_sl_pct']
    # Detect old format: values > 10 are probably old format
    if value > 10:
        value = value / 10.0  # Convert: 70 → 7.0, 20 → 2.0
    self.min_sl_spin.setValue(value)
```

---

## TESTING CHECKLIST

- [ ] UI spinbox shows decimal (0.7)
- [ ] UI spinbox has % suffix
- [ ] Slider range works (0.1 - 10.0)
- [ ] Config save/load works
- [ ] Backend receives correct value (0.7)
- [ ] Backend calculates correct percentage (0.7% = 0.007)
- [ ] Actual SL distance matches user expectation
- [ ] Old configs auto-convert correctly
- [ ] Wiring test shows consistent values

---

## EXPECTED RESULT

### User Experience:
1. User sees "Min SL: 0.7%"
2. User thinks: "Okay, 0.7% stop loss"
3. System uses: 0.7% (entry_price * 0.007)
4. ✅ Perfect match! No confusion!

### Example (BTC @ $90,000):
- UI shows: 0.7%
- User expects: $90,000 × 0.007 = $630 stop
- System calculates: $90,000 × 0.007 = $630 stop
- ✅ Exactly what user expects!

---

## IMPLEMENTATION ORDER

1. Update UI spinbox types & ranges
2. Remove divisions in config building
3. Remove multiplications in config loading
4. Update vol_multi same pattern
5. Remove backend division for vol_multi
6. Test with simple backtest
7. Verify log output shows correct values
8. Run wiring test to confirm consistency

---

**STATUS:** Ready to implement ✅  
**ESTIMATED CHANGES:** ~20 lines across 2 files  
**RISK:** Low (isolated to Adaptive SL controls)  
**TESTING:** Required before commit

---

**END OF PLAN**
