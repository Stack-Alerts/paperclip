# EXIT RECHECK NEVER CALLED - CRITICAL BUG FORENSIC

**Date**: 2026-02-16 10:30 AM  
**Severity**: 🔴 CRITICAL - Production Impact  
**Status**: 🔍 ROOT CAUSE IDENTIFIED

---

## 🚨 SYMPTOM

ALL exit conditions log "no recheck" regardless of configuration:
```
🎯 EXIT (no recheck): ABOVE_ASIA_50 at bar 344
🎯 EXIT (no recheck): ABOVE_ASIA_50 at bar 414
🎯 EXIT (no recheck): ABOVE_ASIA_50 at bar 464
```

**Expected**: Different delays (5 bars, 10 bars, AT mode, WITHIN mode) should produce different exit behavior.

**Actual**: Changing recheck delays from 5→10 bars or timing_mode AT→WITHIN has ZERO effect.

---

## 🔬 ROOT CAUSE ANALYSIS

### Evidence Chain:

1. **Log Evidence** (`logs/wiring-test/exit_conditions.log`):
   - 100% of exits show "(no recheck)"
   - Zero "RECHECK PENDING" messages
   - Zero "RECHECK CONFIRMED" messages
   
2. **Code Entry Point** (`exit_hierarchy_evaluator.py:290-303`):
```python
def _check_exit_signal(...):
    recheck_config = exit_cond.recheck_config  # Line 296
    
    # BRANCH 1: RECHECK DISABLED
    if not recheck_config or not recheck_config.get('enabled'):
        if signal_firing_now:
            exit_logger.info(f"🎯 EXIT (no recheck): {exit_signal_name}")
        return signal_firing_now  # ← ALL exits take this path!
```

3. **Data Flow Trace**:
```
Strategy Config (DB/UI)
  ↓
exit_cond.recheck_config = {...}  ← User configures this
  ↓
institutional_signal_evaluator.py:398
recheck_config=getattr(exit_cond, 'recheck_config', None)  ← Returns None!
  ↓
ExitCondition.recheck_config = None  ← ALWAYS None!
  ↓
exit_hierarchy_evaluator.py:296
if not recheck_config ...  ← TRUE (recheck_config is None)
  ↓
ALL exits fire immediately (no validation)
```

---

## 🎯 ROOT CAUSE

**File**: `src/optimizer_v3/core/institutional_signal_evaluator.py`  
**Line**: 398  
**Method**: `_organize_exit_conditions()`

```python
exits['STRATEGY'].append(ExitCondition(
    signal_name=exit_cond.signal_name,
    percentage=exit_cond.percentage,
    mode=exit_cond.exit_mode,
    binding_level='STRATEGY',
    recheck_config=getattr(exit_cond, 'recheck_config', None)  ← BUG!
))
```

**Problem**: `getattr(exit_cond, 'recheck_config', None)` **ALWAYS returns None**

**Why**: One of:
1. Attribute name mismatch (DB stores `recheck` not `recheck_config`)
2. Config object structure different than expected
3. Recheck config not loaded from database
4. Strategy config loader doesn't parse recheck data

---

## 💥 IMPACT

**Production**: Every exit condition fires immediately, bypassing ALL confirmations:
- ✅ UI shows: "Recheck: WITHIN 5 bars"
- ❌ Actual behavior: Exits on first signal (0 bars delay)
- 💸 Financial risk: False exits on market noise

**Scope**: Affects ALL strategies with exit recheck enabled:
- HOD Rejection v9 ✓
- Custom user strategies ✓
- All 470+ signal combinations ✓

---

## 🔧 REQUIRED FIX

### Step 1: Identify Correct Attribute Name

Need to check what the strategy config object ACTUALLY has:

```python
# Add debug logging in _organize_exit_conditions()
print(f"EXIT COND ATTRIBUTES: {dir(exit_cond)}")
print(f"EXIT COND DICT: {exit_cond.__dict__ if hasattr(exit_cond, '__dict__') else 'NO DICT'}")
```

### Step 2: Fix Data Extraction

Once correct attribute found, update lines 398, 413, 428 in institutional_signal_evaluator.py:

```python
# BEFORE (broken):
recheck_config=getattr(exit_cond, 'recheck_config', None)

# AFTER (fixed):
recheck_config=getattr(exit_cond, 'CORRECT_ATTR_NAME', None)
# OR if nested:
recheck_config=exit_cond.recheck.to_dict() if hasattr(exit_cond, 'recheck') else None
```

### Step 3: Verify Database Schema

Check if `exit_conditions` table has recheck columns:
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'exit_conditions' 
AND column_name LIKE '%recheck%';
```

### Step 4: Verify ORM Model

Check `src/optimizer_v3/database/models.py` - ExitCondition model definition

---

## 📊 VERIFICATION CHECKLIST

After fix:
- [ ] Logs show "📝 EXIT RECHECK PENDING" messages
- [ ] Logs show "✅ EXIT RECHECK CONFIRMED" messages  
- [ ] Changing delay 5→10 changes exit bar
- [ ] AT vs WITHIN modes produce different behavior
- [ ] Zero "🎯 EXIT (no recheck)" with recheck enabled

---

## 🎓 LESSONS LEARNED

1. **Silent Failures Are Deadly**: Code defaulted to `None` without error
2. **Integration Testing Critical**: Unit tests passed, integration revealed bug
3. **Log Forensics Essential**: Logs showed 100% "(no recheck)" pattern
4. **Data Flow Validation**: Must verify config through ENTIRE pipeline

---

## 📝 NEXT STEPS

1. ✅ Document root cause (this file)
2. ⏭️ Debug config object structure
3. ⏭️ Fix attribute extraction
4. ⏭️ Verify database schema
5. ⏭️ Re-run integration tests
6. ⏭️ Update implementation report

---

**Reported by**: System Forensic Analysis  
**Assigned to**: Development Team  
**Priority**: P0 - CRITICAL (Production Impact)  
**ETA**: Immediate

---

**END OF FORENSIC REPORT**
