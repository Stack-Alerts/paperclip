# AUTO-FIX LOGIC SPECIFICATIONS
**Sprint 1.9 Task 1.9.0.4: One-Click Fix Algorithms**

**Date**: 2026-01-30  
**Status**: SPECIFICATION  
**Purpose**: Define how automated fixes modify strategy configuration

---

## 🎯 OVERVIEW

This document defines the exact algorithms used by one-click fix buttons in the validation report window. All auto-fixes modify the StrategyConfig object directly without changing other UI components.

---

## 🔧 AUTO-FIX IMPLEMENTATIONS

### **Fix 1: Switch Strategy Type**

**Trigger**: Strategy direction mismatch (CRITICAL or WARNING severity)  
**Detection**: Task 1.9.8 - Bearish/Bullish signal ratio analysis

**Algorithm**:
```python
def auto_fix_strategy_type(config: StrategyConfig, suggested_type: str) -> bool:
    """
    Switch strategy type to match signal direction
    
    Args:
        config: Current strategy configuration
        suggested_type: "Bullish" or "Bearish"
    
    Returns:
        True if fixed, False on error
    """
    # Validation
    if suggested_type not in ["Bullish", "Bearish"]:
        return False
    
    # Apply fix
    setattr(config, 'strategy_type', suggested_type)
    
    # Update corresponding side if needed
    if suggested_type == "Bullish":
        config.side = "LONG"
    elif suggested_type == "Bearish":
        config.side = "SHORT"
    
    return True
```

**Effects**:
- Updates `config.strategy_type` field
- Updates `config.side` for consistency
- NO changes to signals or blocks (those are user-defined)

---

### **Fix 2: Reduce RECHECK Delay**

**Trigger**: Timing window < RECHECK delay conflict (ERROR severity)  
**Detection**: Task 1.9.9 - Timing vs RECHECK validation

**Algorithm**:
```python
def auto_fix_recheck_delay(
    recheck_config: RecheckConfig,
    timing_window: int,
    buffer: float = 0.75
) -> bool:
    """
    Reduce RECHECK delay to fit within timing window
    
    Args:
        recheck_config: RECHECK configuration to modify
        timing_window: Maximum candles available
        buffer: Safety buffer (0.75 = 75% of window)
    
    Returns:
        True if fixed, False on error
    """
    # Calculate safe delay (75% of timing window)
    safe_delay = int(timing_window * buffer)
    
    # Enforce minimum of 1 bar
    safe_delay = max(1, safe_delay)
    
    # Apply fix
    recheck_config.bar_delay = safe_delay
    
    return True
```

**Effects**:
- Updates `bar_delay` to 75% of timing window
- Minimum delay: 1 bar
- Preserves all other RECHECK settings

**Example**:
- Timing window: 15 candles
- Original RECHECK: 25 bars (ERROR)
- Fixed RECHECK: 11 bars (15 * 0.75 = 11.25 → 11)

---

### **Fix 3: Consolidate Duplicate Exit Conditions**

**Trigger**: Multiple exit conditions with same signal_name (WARNING severity)  
**Detection**: Task 1.9.10 - Exit mode conflict detection

**Algorithm**:
```python
def auto_fix_duplicate_exits(
    exit_conditions: List[ExitCondition],
    signal_name: str
) -> List[ExitCondition]:
    """
    Consolidate duplicate exit conditions for same signal
    
    Args:
        exit_conditions: List of exit conditions
        signal_name: Signal name to consolidate
    
    Returns:
        New exit conditions list with duplicates merged
    """
    # Find all conditions for this signal
    matching_conditions = [
        ec for ec in exit_conditions
        if ec.signal_name == signal_name
    ]
    
    if len(matching_conditions) <= 1:
        return exit_conditions  # No duplicates
    
    # Calculate merged values
    total_percentage = sum(ec.percentage for ec in matching_conditions)
    
    # Select highest confidence mode
    # ABSOLUTE > FLEXIBLE (ABSOLUTE is more strict)
    merged_mode = "ABSOLUTE"
    if any(ec.exit_mode == "ABSOLUTE" for ec in matching_conditions):
        merged_mode = "ABSOLUTE"
    else:
        merged_mode = "FLEXIBLE"
    
    # Use first condition's binding level and RECHECK (keep original)
    first_condition = matching_conditions[0]
    
    # Create consolidated condition
    consolidated = ExitCondition(
        signal_name=signal_name,
        percentage=min(1.0, total_percentage),  # Cap at 100%
        exit_mode=merged_mode,
        binding_level=first_condition.binding_level,
        tp_proximity_threshold=first_condition.tp_proximity_threshold,
        reversal_trigger=first_condition.reversal_trigger,
        recheck_config=first_condition.recheck_config
    )
    
    # Remove old conditions and add consolidated one
    new_conditions = [
        ec for ec in exit_conditions
        if ec.signal_name != signal_name
    ]
    new_conditions.append(consolidated)
    
    return new_conditions
```

**Effects**:
- Merges all exit conditions with same signal_name
- Sums percentages (capped at 100%)
- Keeps ABSOLUTE mode if any condition uses it
- Preserves first condition's binding level and RECHECK
- Removes duplicate definitions

**Example**:
- Original: 
  - Exit1: BEARISH_BREAKDOWN, 50%, ABSOLUTE
  - Exit2: BEARISH_BREAKDOWN, 30%, FLEXIBLE
- Consolidated:
  - Exit: BEARISH_BREAKDOWN, 80%, ABSOLUTE (higher confidence mode)

---

### **Fix 4: Remove Dead Code**

**Trigger**: Unreachable signals detected (WARNING severity)  
**Detection**: Task 1.9.7 - Dead code detection

**Algorithm**:
```python
def auto_fix_dead_code(
    block: BlockConfig,
    dead_signal_names: List[str],
    preserve_history: bool = True
) -> bool:
    """
    Remove or disable unreachable signals
    
    Args:
        block: Block containing dead code
        dead_signal_names: Signals that are unreachable
        preserve_history: If True, mark disabled instead of deleting
    
    Returns:
        True if fixed, False on error
    """
    for signal in block.signals:
        if signal.name in dead_signal_names:
            if preserve_history:
                # Mark as disabled (preserves for reference)
                signal.enabled = False
            else:
                # Remove completely
                block.signals.remove(signal)
    
    return True
```

**Effects**:
- Sets `signal.enabled = False` (default behavior)
- OR removes signal entirely (if preserve_history=False)
- Preserves signal for audit trail by default
- User can manually delete later if not needed

**Rationale**: Disabled signals remain visible but inactive, allowing users to understand why validation flagged them.

---

## 📊 FIX PRIORITY LEVELS

### **CRITICAL Fixes (Must Apply)**:
1. Switch Strategy Type (wrong direction = loses money)
2. Timing vs RECHECK conflicts (signals never trigger)

### **ERROR Fixes (Should Apply)**:
3. Exit percentage overflow (>100% total)
4. RECHECK delay reduction (impossible timing)

### **WARNING Fixes (Optional)**:
5. Consolidate duplicate exits
6. Remove dead code

---

## 🔄 FIX APPLICATION WORKFLOW

```
1. User clicks "Validate" button
2. Validation engine runs all 59 rules
3. Validation report window opens with issues
4. User sees one-click fix buttons for applicable issues
5. User clicks "Apply Fix" button
6. Confirmation dialog: "Apply fix: [description]?"
7. User confirms
8. Auto-fix algorithm modifies config
9. Validation re-runs automatically
10. Report updates with new results
11. User reviews updated validation
12. User saves strategy if satisfied
```

---

## ⚠️ IMPORTANT NOTES

### **What Auto-Fixes DO**:
- ✅ Modify StrategyConfig object directly
- ✅ Update validation status immediately
- ✅ Re-run validation after fix
- ✅ Show before/after comparison

### **What Auto-Fixes DON'T DO**:
- ❌ Change main window UI components
- ❌ Modify database directly (save required)
- ❌ Edit other strategies
- ❌ Change building block definitions
- ❌ Affect NautilusTrader code generation

### **User Responsibility**:
- User must SAVE strategy after applying fixes
- User can UNDO fixes by reloading without saving
- User should REVIEW fixes before backtest
- User has final approval on all changes

---

## 🧪 TESTING REQUIREMENTS

Each auto-fix must have:
1. Unit test with before/after config
2. Integration test with validation flow
3. Edge case tests (null values, boundaries)
4. Undo test (reload without save)
5. Multiple fixes applied in sequence

---

## 📝 EXAMPLE USE CASE

**Scenario**: User creates HOD Rejection strategy

**Issues Detected**:
1. CRITICAL: Strategy type Bullish, but 100% signals are Bearish
2. ERROR: Timing window 15 candles, RECHECK delay 25 bars
3. WARNING: Signal "BEARISH_BREAKDOWN" appears in 2 exit conditions

**Auto-Fixes Available**:
1. "Switch to Bearish" button → Changes strategy_type to "Bearish"
2. "Reduce RECHECK to 11 bars" button → Updates bar_delay to 11
3. "Consolidate Exits" button → Merges duplicate exit conditions

**Result**: User clicks all 3 buttons, reviews changes, saves strategy. Validation passes.

---

## 🔐 SAFETY MECHANISMS

### **Confirmation Required**:
- All fixes require user confirmation
- Dialog shows exact changes being made
- User can cancel at any point

### **Reversibility**:
- Fixes only modify in-memory config
- User must explicitly save
- Reload file to undo all fixes

### **Validation Loop**:
- Validation re-runs after each fix
- New issues may appear (rare)
- User sees updated report immediately

### **Audit Trail**:
- Log all auto-fixes applied
- Include in validation report export
- Track fix timestamp and user

---

**Status**: SPECIFICATION COMPLETE  
**Next**: Implement auto-fix buttons in ValidationReportWindow (Phase 2, Task 1.9.20)
