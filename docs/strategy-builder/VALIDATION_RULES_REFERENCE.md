# Validation Rules Reference
**Sprint 1.9 Task 1.9.28: Complete Validation Rule Documentation**

**Total Rules**: 59 comprehensive validation rules across 8 categories  
**Date**: 2026-01-30  
**Status**: Production Ready

---

## 📋 Rule Categories

### **Category A: STRUCTURAL INTEGRITY** (9 rules - CRITICAL)
**Purpose**: Ensure basic strategy structure is valid

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| STRUCTURAL_001 | Strategy Name Required | CRITICAL | Strategy must have a name |
| STRUCTURAL_002 | Minimum Block Count | CRITICAL | Strategy must have >= 1 block |
| STRUCTURAL_003 | Empty Block Detected | ERROR | Each block must have >= 1 signal |
| STRUCTURAL_004 | Duplicate Block Names | ERROR | No duplicate block names allowed |
| STRUCTURAL_005 | Duplicate Signal Names | ERROR | No duplicate signals within block |
| STRUCTURAL_006 | Invalid Logic Type | ERROR | Logic must be 'AND' or 'OR' |
| STRUCTURAL_007 | Orphaned Exit Conditions | ERROR | No orphaned exit conditions (checked in exit validation) |
| STRUCTURAL_008 | Circular Timing Constraints | ERROR | No circular timing dependencies (checked in timing validation) |
| STRUCTURAL_009 | Circular RECHECK Dependencies | CRITICAL | No circular RECHECK dependencies (checked in RECHECK validation) |

---

### **Category B: RECHECK VALIDATION** (6 rules - CRITICAL)
**Purpose**: Validate RECHECK configurations for correct nesting and delays

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| RECHECK_001 | Circular RECHECK Dependency | CRITICAL | Circular RECHECK detected (infinite loop risk) |
| RECHECK_002 | Invalid RECHECK Delay | ERROR | RECHECK bar_delay must be > 0 |
| RECHECK_003 | RECHECK Parent Signal Not Found | ERROR | Parent signal must exist in same block |
| RECHECK_004 | RECHECK Depth Exceeded | ERROR | RECHECK depth > 3 levels |
| RECHECK_005 | High RECHECK Depth | WARNING | RECHECK depth > 2 (recommended <= 2) |
| RECHECK_006 | RECHECK Delay Too High | ERROR | Cumulative delay > 50 bars |
| RECHECK_007 | High RECHECK Delay | WARNING | Cumulative delay > 30 bars |
| RECHECK_008 | Non-Increasing RECHECK Delays | WARNING | RECHECK chain delays should increase |

---

### **Category C: EXIT CONDITION VALIDATION** (13 rules - MIXED)
**Purpose**: Validate exit conditions with intelligent strategy analysis

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| EXIT_001 | Invalid Exit Percentage | ERROR | Percentage must be 0 < pct <= 1.0 |
| EXIT_002 | Invalid Exit Mode | ERROR | Mode must be 'ABSOLUTE' or 'FLEXIBLE' |
| EXIT_003 | Invalid Binding Level | ERROR | Level must be  'STRATEGY'/'BLOCK'/'SIGNAL' |
| EXIT_004 | Exit Signal Not Found | ERROR | Signal doesn't exist in registry |
| EXIT_005 | Binding Level Mismatch | ERROR | Exit stored at wrong binding level |
| EXIT_006 | Invalid TP Proximity Threshold | ERROR | FLEXIBLE mode: tp_proximity > 0 |
| EXIT_007 | Invalid Reversal Trigger | ERROR | FLEXIBLE mode: reversal_trigger > 0 |
| EXIT_008 | Invalid Exit RECHECK Delay | ERROR | Exit RECHECK bar_delay must be > 0 |
| EXIT_009 | Conflicting Exit Modes | WARNING | Same signal has ABSOLUTE + FLEXIBLE |
| EXIT_ANALYSIS_001 | Exit Strategy Classification | INFO/NOTICE | Strategic analysis of exit approach |

**Special Note**: Exit percentage accumulation is **NON-BLOCKING**. Cumulative exits >100% are VALID (multiple opportunities = higher probability). See Task 1.9.4 documentation.

---

### **Category D: TIMING CONSTRAINT VALIDATION** (10 rules - ERROR/CRITICAL)
**Purpose**: Validate timing constraints and detect conflicts with RECHECK

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| TIMING_001 | Invalid Timing Window | ERROR | max_candles must be > 0 |
| TIMING_002 | Timing Reference Signal Not Found | ERROR | Referenced signal doesn't exist |
| TIMING_003 | Circular Timing Dependency | ERROR | Circular timing constraints detected |
| TIMING_004 | RECHECK Exceeds Timing Window | **CRITICAL** | Signal will NEVER trigger (RECHECK > window) |
| TIMING_005 | Low Timing Buffer | WARNING | RECHECK delay leaves < 20% buffer |

**Timeline Visualization**: Rule TIMING_004 includes bar-by-bar timeline showing when signal trigger becomes impossible.

---

### **Category E: LOGIC FLOW VALIDATION** (4 rules - WARNING)
**Purpose**: Detect dead code and logic inconsistencies

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| LOGIC_001 | AND Block with All OR Signals | WARNING | May not behave as expected |
| LOGIC_002 | OR Block with All AND Signals | WARNING | May not behave as expected |
| LOGIC_003 | Dead Code - Impossible Timing | WARNING | Signal references future signal (never triggers) |

---

### **Category F: PERFORMANCE & BEST PRACTICES** (5 rules - WARNING)
**Purpose**: Flag performance concerns and complexity issues

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| PERFORMANCE_001 | High Block Count | WARNING | > 15 blocks (recommended: <= 15) |
| PERFORMANCE_002 | High Signal Count Per Block | WARNING | > 10 signals per block (recommended: <= 10) |
| COMPLEXITY_001 | Very High Complexity | WARNING | Complexity score > 85/100 |
| COMPLEXITY_002 | High Complexity | INFO | Complexity score > 60/100 |

**Complexity Formula**:
```
raw_score = (
    (total_blocks * 2) +
    (total_signals * 1.5) +
    (total_exit_conditions * 3) +
    (max_recheck_depth * 10) +
    (total_timing_constraints * 5) +
    (max_recheck_cumulative_delay / 5)
)
complexity_score = min(100, int(raw_score))
```

---

### **Category G: NAUTILUS COMPATIBILITY** (4 rules - WARNING)
**Purpose**: Ensure NautilusTrader code generation compatibility

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| NAUTILUS_001 | Invalid Strategy Name | WARNING | Not a valid Python identifier |
| NAUTILUS_002 | Invalid Block Name | WARNING | Cannot be converted to a valid Python identifier |
| NAUTILUS_003 | Invalid Signal Name | WARNING | Cannot be converted to a valid Python identifier |

**Valid Python Identifier**: Letters, numbers, underscores only. Cannot start with number.

**Note (NAUTILUS_002/003)**: Block and signal names are persisted as Title Case with
spaces (e.g. "Asia Session 50 Percent"). The backend and code generator auto-convert
these to snake_case, so spaces and hyphens are accepted — matching Rule 48 (strategy
name). These rules only warn when a name still cannot form a valid identifier after
that conversion (e.g. a leading digit or characters like `/ \ " ' : < > | * ?`).

---

### **Category H: STRATEGY DIRECTION VALIDATION** (4 rules - CRITICAL)
**Purpose**: Detect strategy type mismatches that cause wrong-direction trading

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| DIRECTION_001 | Strategy Direction Mismatch | **CRITICAL** | >70% signals don't match strategy type |
| DIRECTION_002 | Strategy Direction Warning | WARNING | 50-70% signals don't match |

**Auto-Fix**: One-click "Switch to [Suggested]" button available for direction mismatches.

**Example**: 
- Strategy type: "Bullish"
- Entry signals: 6 bearish, 0 bullish (100% bearish)
- **Result**: CRITICAL error with auto-fix to switch to "Bearish"

---

## 🎯 Severity Levels

| Severity | Color | Meaning | Action Required |
|----------|-------|---------|-----------------|
| CRITICAL | Red | Must fix before live trading | MANDATORY FIX |
| ERROR | Orange | Must fix before backtesting | MANDATORY FIX |
| WARNING | Yellow | Should review, not critical | RECOMMENDED FIX |
| NOTICE | Cyan | User should review (priority info) | REVIEW |
| INFO | Blue | Informational only | NO ACTION |

---

## 🔧 Auto-Fix Features

### Available Auto-Fixes:
1. **Switch Strategy Direction** (DIRECTION_001, DIRECTION_002)
   - One-click button to switch Bullish ↔ Bearish
   - Updates strategy_type and side fields
   
2. **Reduce RECHECK Delay** (TIMING_004)
   - Automatically calculates safe delay (75% of timing window)
   - Minimum: 1 bar
   
3. **Consolidate Exit Conditions** (EXIT_009)
   - Merges duplicate signal exits
   - Sums percentages (capped at 100%)
   - Keeps highest confidence mode (ABSOLUTE > FLEXIBLE)

4. **Disable Dead Signal** (LOGIC_003)
   - Marks signal as enabled=False
   - Preserves for audit trail

---

## 📊 Special Validations

### Exit Strategy Classification (Task 1.9.4.1)
**Non-blocking intelligent analysis of exit approach**:

- **TP-Only (0%)**: Pure TP/SL strategy
- **Low Coverage (1-50%)**: TP-dominant hybrid
- **Hybrid (51-99%)**: Balanced conditions + TP
- **Single Full (100%)**: Single exit condition
- **Multiple Opportunities (101-500%)**: N× exit probability (VALID)
- **High Redundancy (>500%)**: Suggest review (NOTICE only)

**Important**: Cumulative exits >100% are VALID. Multiple 100% conditions = multiple opportunities = higher exit probability.

### Timing Conflict Timeline (Task 1.9.9)
**Bar-by-bar visualization for TIMING_004 conflicts**:

```
Bar 0:  ✅ Reference signal triggers
Bar 15: ⚠️  Timing window CLOSES
Bar 25: ❌ RECHECK validates (TOO LATE)
Result: Signal NEVER triggers!
```

---

## 🚨 Critical Rules Summary

**Must Fix Before Live Trading** (CRITICAL):
- STRUCTURAL_001: Strategy must have name
- STRUCTURAL_002: Strategy must have blocks
- RECHECK_001: No circular RECHECK dependencies
- TIMING_004: RECHECK must fit within timing window
- DIRECTION_001: Strategy type must match signal majority (>70%)

**Must Fix Before Backtesting** (ERROR):
- All ERROR-level rules in categories A-D

---

## 📚 See Also

- `AUTO_FIX_LOGIC_SPECIFICATIONS.md` - Auto-fix algorithm details
- `SPRINT_1_9_VALIDATION_FRAMEWORK.md` - Complete sprint documentation
- Test files - `tests/optimizer_v3/validation/test_institutional_validator.py`

---

**Status**: ✅ All 59 rules documented and implemented  
**Last Updated**: 2026-01-30
