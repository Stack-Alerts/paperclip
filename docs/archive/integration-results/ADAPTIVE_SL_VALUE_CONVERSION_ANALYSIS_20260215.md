# ADAPTIVE SL VALUE CONVERSION ANALYSIS
**Date:** 2026-02-15  
**Status:** CRITICAL BUG IDENTIFIED - DOUBLE DIVISION  
**Mode:** NAUTILUS EXPERT

---

## PROBLEM STATEMENT

User sees "7%" in UI but system uses **0.7%** (10x tighter!)  
User sees "20%" in UI but system uses **2%** (10x tighter!)

This creates massive confusion about actual stop loss percentages.

---

## FULL CONVERSION TRACE

### 1. Emergency SL (✅ CORRECT)

**UI Layer:** `src/strategy_builder/ui/backtest_config_panel.py`
```python
'emergency_sl_pct': self.emergency_spin.value()  # No division
```

**User sees:** 2  
**UI sends:** 2  
**Backend receives:** 2  

**Backend Layer:** `src/optimizer_v3/core/adaptive_sl_manager.py` (line 158)
```python
emergency_sl_pct = config.get('emergency_sl_pct', 1.0)
emergency_sl_percent = emergency_sl_pct / 100.0  # ÷100
```

**Backend uses:** 2 / 100 = 0.02 = **2%**  
**Result:** ✅ **CORRECT** - User sees 2, system uses 2%

---

### 2. Min/Max SL (❌ DOUBLE DIVISION BUG!)

**UI Layer:** `src/strategy_builder/ui/backtest_config_panel.py` (lines 1245-1246)
```python
'min_sl_pct': self.min_sl_spin.value() / 10.0,  # ÷10 ← FIRST DIVISION
'max_sl_pct': self.max_sl_spin.value() / 10.0,  # ÷10 ← FIRST DIVISION
```

**User sees:** 7 (labeled as "7%")  
**UI sends:** 7 / 10 = **0.7**  
**Backend receives:** 0.7  

**Backend Layer:** `src/optimizer_v3/core/adaptive_sl_manager.py` (lines 196-197)
```python
if 'min_sl_pct' in config:
    min_sl_percent = config['min_sl_pct'] / 100.0  # ÷100 ← SECOND DIVISION
    max_sl_percent = config['max_sl_pct'] / 100.0  # ÷100 ← SECOND DIVISION
```

**Backend uses:**  
- Min: 0.7 / 100 = 0.007 = **0.7%** (NOT 7%!)  
- Max: 2.0 / 100 = 0.020 = **2%** (NOT 20%!)  

**Result:** ❌ **CRITICAL BUG** - 10x discrepancy!

---

### 3. Volatility Multiplier (✅ CORRECT)

**UI Layer:**
```python
'volatility_multiplier': self.vol_multi_spin.value() / 10.0  # ÷10
```

**User sees:** 12 (labeled as "12x")  
**UI sends:** 12 / 10 = 1.2  
**Backend receives:** 1.2  

**Backend Layer:** `src/optimizer_v3/core/adaptive_sl_manager.py` (line 193)
```python
vol_multi = config.get('volatility_multiplier', 15) / 10.0
```

**Backend uses:** 1.2 (no further division)  
**Result:** ✅ **CORRECT** - User sees 12x, system uses 1.2x

---

## EXAMPLE SCENARIO (BTC @ $90,000)

### What User THINKS is happening:
- **Min SL = 7%:** $90,000 × 0.07 = $6,300 stop distance
- **Max SL = 20%:** $90,000 × 0.20 = $18,000 stop distance

### What ACTUALLY happens:
- **Min SL = 0.7%:** $90,000 × 0.007 = **$630** stop distance (10x tighter!)
- **Max SL = 2%:** $90,000 × 0.02 = **$1,800** stop distance (10x tighter!)

**Impact:** Stops are **10x closer** than user expects, causing premature exits!

---

## ROOT CAUSE

**Double Division Bug:**
1. UI divides by 10: `7 → 0.7`
2. Backend divides by 100: `0.7 → 0.007`
3. Total division: 1000x (not 100x as intended!)

**Why Emergency SL works:**
- UI: No division (sends raw value)
- Backend: Single division by 100
- Result: Correct percentage

**Why Min/Max SL broken:**
- UI: Divides by 10 (legacy code comment says "UI shows 10x")
- Backend: Divides by 100 (expecting raw percentage)
- Result: 1000x division total!

---

## SOLUTION OPTIONS

### OPTION 1: Fix Backend (Remove Double Division) ⭐ RECOMMENDED

**Change:** Remove `/100` division in adaptive_sl_manager.py  
**Impact:** Minimal - only affects adaptive SL calculation  
**Risk:** Low - isolated to one function  

```python
# BEFORE (WRONG):
min_sl_percent = config['min_sl_pct'] / 100.0  # 0.7 → 0.007

# AFTER (CORRECT):
min_sl_percent = config['min_sl_pct'] / 100.0  # 7 → 0.07
```

**But wait - UI already divides by 10!**

So correct fix is:
```python
# BEFORE (WRONG):
min_sl_percent = config['min_sl_pct'] / 100.0  # 0.7 → 0.007 (double division!)

# AFTER (CORRECT):
min_sl_percent = config['min_sl_pct'] / 10.0  # 0.7 → 0.07 (single division!)
```

---

### OPTION 2: Fix UI (Remove First Division)

**Change:** Stop dividing by 10 in UI, send raw values  
**Impact:** Moderate - affects config save/load  
**Risk:** Medium - could break existing saved configs  

```python
# BEFORE:
'min_sl_pct': self.min_sl_spin.value() / 10.0,  # 7 → 0.7

# AFTER:
'min_sl_pct': self.min_sl_spin.value(),  # 7 → 7
```

Then backend:
```python
min_sl_percent = config['min_sl_pct'] / 100.0  # 7 → 0.07 ✅
```

---

### OPTION 3: Improve UI Labels (Show Actual Values) ⭐ BEST UX

**Change:** Add hover tooltips showing actual percentages

**Before:**
```
Min Stop Loss: [7] 7%
```

**After:**
```
Min Stop Loss: [7] 0.7%  💡 (Hover: "Actual SL = 0.7% of entry price")
```

Or even better - show BOTH representations:
```
Min Stop Loss: [7] → 0.7%  📊
                     ↑ basis points
```

Or most clear - dual display:
```
Min Stop Loss: [7] basis points = 0.7%
```

---

## RECOMMENDED FIX (COMBINATION)

**Fix #1:** Backend correction (immediate)
- Change division from /100 to /10 in adaptive_sl_manager.py
- Matches UI's existing division pattern

**Fix #2:** UI labels (clarity)
- Add actual percentage display next to slider
- Add tooltip explaining basis point vs percentage

**Fix #3:** Migration (safety)
- Add version check for old configs
- Auto-convert old values to new format

---

## FILES TO MODIFY

1. **src/optimizer_v3/core/adaptive_sl_manager.py**
   - Line 196-197: Change `/100.0` to `/10.0`
   - Reason: UI already divides by 10

2. **src/strategy_builder/ui/backtest_config_panel.py**
   - Add computed label showing actual percentage
   - Add tooltip explaining value meaning

3. **tests/integration/test_adaptive_sl_values.py** (NEW)
   - Test UI→Backend conversion
   - Verify actual percentages match expectations

---

## VERIFICATION TEST

```python
# Test case: User sets Min SL = 7
ui_value = 7
ui_sent = ui_value / 10.0  # = 0.7
backend_old = ui_sent / 100.0  # = 0.007 (0.7%) ← WRONG!
backend_new = ui_sent / 10.0  # = 0.07 (7%) ← CORRECT!

# For BTC @ $90,000:
entry_price = 90000
sl_distance_old = entry_price * 0.007  # $630 (too tight!)
sl_distance_new = entry_price * 0.07  # $6,300 (user expected!)
```

---

## ACTUAL VALUE TABLE

| UI Display | UI Label | UI Sends | Backend (OLD) | Backend (NEW) | BTC $90k (OLD) | BTC $90k (NEW) |
|------------|----------|----------|---------------|---------------|----------------|----------------|
| 6          | 6%       | 0.6      | 0.6%          | 6.0%          | $540           | $5,400         |
| 7          | 7%       | 0.7      | 0.7%          | 7.0%          | $630           | $6,300         |
| 10         | 10%      | 1.0      | 1.0%          | 10.0%         | $900           | $9,000         |
| 12         | 12%      | 1.2      | 1.2%          | 12.0%         | $1,080         | $10,800        |
| 20         | 20%      | 2.0      | 2.0%          | 20.0%         | $1,800         | $18,000        |

**OLD:** All values 10x too tight!  
**NEW:** Matches user expectations!

---

## NEXT STEPS

1. ✅ Analysis complete
2. ⏳ Implement backend fix (change /100 to /10)
3. ⏳ Add UI label showing actual percentage
4. ⏳ Test with real backtest
5. ⏳ Verify SL distances match user expectations

---

**END OF ANALYSIS**
