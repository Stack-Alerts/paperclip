# EXIT CONDITIONS - COMPREHENSIVE SCENARIOS & TEST CASES

**Document**: Complete Exit Condition Testing Framework  
**Date**: 2026-02-16  
**Status**: Institutional-Grade Quality Control  
**Purpose**: Verify every possible exit condition configuration works correctly

---

## 📋 OVERVIEW

This document defines **ALL possible exit condition scenarios** for the BTC_Engine_v3 system and provides test cases for each. The exit system has 3 dimensions of configuration:

1. **Binding Level** (3 options): STRATEGY | BLOCK | SIGNAL
2. **Exit Mode** (2 options): ABSOLUTE | FLEXIBLE (TP-aware)
3. **Recheck** (2 options): Enabled | Disabled
4. **Timing Mode** (2 options): AT | WITHIN (when recheck enabled)

**Total Combinations**: 3 × 2 × 2 × 2 = **24 base scenarios**

Plus edge cases, multiple exits, TP interactions = **50+ comprehensive test cases**

---

## 🎯 THREE-TIER EXIT HIERARCHY (ACCUMULATIVE)

```
┌─────────────────────────────────────────────┐
│  TIER 1: STRATEGY-LEVEL                     │
│  ├─ Applies to ALL trades                  │
│  ├─ ALL exits checked and accumulated      │
│  └─ Example: Global exits (25% + 10%)      │
└─────────────────────────────────────────────┘
              ↓ (accumulate)
┌─────────────────────────────────────────────┐
│  TIER 2: BLOCK-LEVEL                        │
│  ├─ Applies to specific building block     │
│  ├─ ALL exits checked and accumulated      │
│  └─ Example: HOD block exits (15%)         │
└─────────────────────────────────────────────┘
              ↓ (accumulate)
┌─────────────────────────────────────────────┐
│  TIER 3: SIGNAL-LEVEL                       │
│  ├─ Applies ONLY if bound signal fired     │
│  ├─ ALL binding-valid exits accumulated    │
│  └─ Example: BELOW_HOD exits (20%)         │
└─────────────────────────────────────────────┘
              ↓
     Total: 25% + 10% + 15% + 20% = 70% exit
     (Capped at remaining_position)
```

**CRITICAL RULE**: ALL exits accumulate! Multiple exits can fire on same bar across all tiers.

**Example**:
```
Bar 150: Multiple exits fire simultaneously
- STRATEGY: REVERSAL_PATTERN (25%)
- STRATEGY: MOMENTUM_FADE (10%)  
- BLOCK: ABOVE_ASIA_50 (15%)
- SIGNAL: BULLISH_CROSS (20%)
→ Total: 70% exit (all accumulated)
→ If remaining = 60%, actual exit = 60% (capped)
```

---

## 📊 SCENARIO TAXONOMY

### Category A: Binding Level Scenarios (Basic)

#### A1: STRATEGY-LEVEL EXIT (No Binding)
**Config**:
```yaml
exit_conditions:
  - level: STRATEGY
    signal: ABOVE_ASIA_50
    percentage: 50%
    mode: ABSOLUTE
    recheck: disabled
```

**Entry**: AT_ASIA_50 + BELOW_ASIA_50 (SHORT entry)  
**Exit Trigger**: ABOVE_ASIA_50 fires at bar 150  
**Expected**: Exit 50% of original position (regardless of which signals fired for entry)  
**Binding Check**: None (strategy-level applies to ALL trades)

---

#### A2: BLOCK-LEVEL EXIT
**Config**:
```yaml
blocks:
  - name: asia_session_50_percent
    exit_conditions:
      - signal: ABOVE_ASIA_50
        percentage: 50%
        mode: ABSOLUTE
        recheck: disabled
```

**Entry**: AT_ASIA_50 + BELOW_ASIA_50 (SHORT entry, using asia_session_50_percent block)  
**Exit Trigger**: ABOVE_ASIA_50 fires at bar 150  
**Expected**: Exit 50% of original position  
**Binding Check**: Entry used asia_session_50_percent block ✓

---

#### A3: SIGNAL-LEVEL EXIT (Bound to Specific Signal)
**Config**:
```yaml
blocks:
  - name: asia_session_50_percent
    signals:
      - name: BELOW_ASIA_50
        exit_conditions:
          - signal: ABOVE_ASIA_50
            percentage: 50%
            mode: FLEXIBLE
            recheck: disabled
```

**Entry Scenario 1**: AT_ASIA_50 + BELOW_ASIA_50 (BELOW_ASIA_50 fired ✓)  
**Exit Trigger**: ABOVE_ASIA_50 fires at bar 150  
**Expected**: Exit 50% of remaining position  
**Binding Check**: BELOW_ASIA_50 in entry_signals ✓ → Process exit

**Entry Scenario 2**: AT_ASIA_50 + OTHER_SIGNAL (BELOW_ASIA_50 did NOT fire ✗)  
**Exit Trigger**: ABOVE_ASIA_50 fires at bar 150  
**Expected**: NO EXIT (signal binding failed)  
**Binding Check**: BELOW_ASIA_50 NOT in entry_signals → Skip exit

---

### Category B: Exit Mode Scenarios

#### B1: ABSOLUTE Mode (No TP Awareness)
**Config**:
```yaml
exit_conditions:
  - signal: ABOVE_ASIA_50
    percentage: 50%
    mode: ABSOLUTE
```

**Trade State**:
- Original position: 100%
- TP1 hit (30%): Remaining = 70%
- TP2 hit (20%): Remaining = 50%

**Exit Trigger**: ABOVE_ASIA_50 fires  
**Calculation**: 50% ABSOLUTE = min(50%, remaining 50%) = 50%  
**Expected**: Exit 50% of original position  
**Result**: Position closed completely (no remaining)

---

#### B2: FLEXIBLE Mode (TP-Aware)
**Config**:
```yaml
exit_conditions:
  - signal: ABOVE_ASIA_50
    percentage: 50%
    mode: FLEXIBLE
```

**Trade State**:
- Original position: 100%
- TP1 hit (30%): Remaining = 70%
- TP2 hit (20%): Remaining = 50%

**Exit Trigger**: ABOVE_ASIA_50 fires  
**Calculation**: 50% FLEXIBLE = 50% × 50% remaining = 25%  
**Expected**: Exit 25% of original position  
**Result**: 25% remains (50% - 25% = 25%)

---

### Category C: Recheck Scenarios

#### C1: RECHECK Disabled (Immediate Exit)
**Config**:
```yaml
exit_conditions:
  - signal: ABOVE_ASIA_50
    percentage: 50%
    mode: ABSOLUTE
    recheck:
      enabled: false
```

**Exit Flow**:
```
Bar 100: ABOVE_ASIA_50 fires → EXIT IMMEDIATELY (50%)
```

**Expected**: Exit triggers on first signal fire

---

#### C2: RECHECK Enabled with AT Mode
**Config**:
```yaml
exit_conditions:
  - signal: ABOVE_ASIA_50
    percentage: 50%
    mode: ABSOLUTE
    recheck:
      enabled: true
      bar_delay: 5
      timing_mode: AT
      validation_mode: SIGNAL
```

**Exit Flow**:
```
Bar 100: ABOVE_ASIA_50 fires → Record as pending
Bar 101-104: (waiting...)
Bar 105: Check if ABOVE_ASIA_50 still true
  → If TRUE: EXIT (50%)
  → If FALSE: Invalidate, no exit
```

**Expected**: Exit ONLY if signal re-confirms at bar 105 (exactly 5 bars later)

---

#### C3: RECHECK Enabled with WITHIN Mode
**Config**:
```yaml
exit_conditions:
  - signal: ABOVE_ASIA_50
    percentage: 50%
    mode: ABSOLUTE
    recheck:
      enabled: true
      bar_delay: 5
      timing_mode: WITHIN
      validation_mode: SIGNAL
```

**Exit Flow (Success)**:
```
Bar 100: ABOVE_ASIA_50 fires → Record as pending
Bar 101: Check if re-fires → NO
Bar 102: Check if re-fires → YES → EXIT (50%)
```

**Exit Flow (Failure)**:
```
Bar 100: ABOVE_ASIA_50 fires → Record as pending
Bar 101-105: Check if re-fires → NO (all bars)
Bar 106: Window expired → Invalidate, no exit
```

**Expected**: Exit if signal re-fires WITHIN 5 bars of first fire

---

### Category D: Multiple Exit Conditions

#### D1: Multiple Exits at Same Level (ALL Accumulate)
**Config**:
```yaml
exit_conditions:
  - signal: ABOVE_ASIA_50
    percentage: 50%
    mode: ABSOLUTE
  - signal: BULLISH_CROSS
    percentage: 30%
    mode: ABSOLUTE
```

**Scenario 1**: ABOVE_ASIA_50 fires at bar 100  
**Expected**: Exit 50% (this exit fires)

**Scenario 2**: BULLISH_CROSS fires at bar 100 (ABOVE_ASIA_50 did not fire)  
**Expected**: Exit 30% (this exit fires)

**Scenario 3**: BOTH fire at bar 100  
**Expected**: Exit 80% (50% + 30% accumulated)  
**Note**: ALL firing exits accumulate!

---

#### D2: Exits at Different Tiers (ALL Accumulate)
**Config**:
```yaml
# STRATEGY-level
exit_conditions:
  - signal: REVERSAL_PATTERN
    percentage: 25%
    mode: ABSOLUTE

# BLOCK-level (asia_session_50_percent)
blocks:
  - name: asia_session_50_percent
    exit_conditions:
      - signal: ABOVE_ASIA_50
        percentage: 15%
        mode: ABSOLUTE

# SIGNAL-level (BELOW_ASIA_50)
    signals:
      - name: BELOW_ASIA_50
        exit_conditions:
          - signal: BULLISH_CROSS
            percentage: 10%
            mode: FLEXIBLE
```

**Scenario 1**: Only REVERSAL_PATTERN fires at bar 100  
**Expected**: Exit 25% (strategy exit only)

**Scenario 2**: Only ABOVE_ASIA_50 fires at bar 100  
**Expected**: Exit 15% (block exit only)

**Scenario 3**: Only BULLISH_CROSS fires at bar 100 (BELOW_ASIA_50 was in entry)  
**Expected**: Exit 10% of remaining (signal exit only)

**Scenario 4**: ALL THREE fire at bar 100  
**Expected**: Exit 50% (25% + 15% + 10% accumulated)  
**Note**: ALL tiers checked and accumulated!

---

### Category E: Complex Scenarios

#### E1: Signal Binding with Multiple Entry Signals
**Entry Configuration**:
```yaml
blocks:
  - name: asia_session_50_percent
    signals:
      - name: AT_ASIA_50      (weight: 25)
      - name: BELOW_ASIA_50   (weight: 30)
  
  - name: hod_rejection
    signals:
      - name: BELOW_HOD       (weight: 20)
```

**Exit Configuration**:
```yaml
# Exit bound to BELOW_ASIA_50
blocks:
  - name: asia_session_50_percent
    signals:
      - name: BELOW_ASIA_50
        exit_conditions:
          - signal: ABOVE_ASIA_50
            percentage: 50%
            mode: FLEXIBLE
```

**Entry Scenario 1**: AT_ASIA_50 + BELOW_ASIA_50 + BELOW_HOD fires  
**Entry Signals**: ['asia_session_50_percent::AT_ASIA_50', 'asia_session_50_percent::BELOW_ASIA_50', 'hod_rejection::BELOW_HOD']  
**Exit Trigger**: ABOVE_ASIA_50 fires  
**Binding Check**: 'BELOW_ASIA_50' in entry_signals? → YES ✓  
**Expected**: Exit 50% of remaining

**Entry Scenario 2**: AT_ASIA_50 + BELOW_HOD fires (BELOW_ASIA_50 did NOT fire)  
**Entry Signals**: ['asia_session_50_percent::AT_ASIA_50', 'hod_rejection::BELOW_HOD']  
**Exit Trigger**: ABOVE_ASIA_50 fires  
**Binding Check**: 'BELOW_ASIA_50' in entry_signals? → NO ✗  
**Expected**: NO EXIT (binding failed)

---

#### E2: Multiple Partial Exits (Sequential)
**Config**:
```yaml
# STRATEGY-level
exit_conditions:
  - signal: WARNING_SIGNAL
    percentage: 20%
    mode: FLEXIBLE

# SIGNAL-level  
signals:
  - name: BELOW_ASIA_50
    exit_conditions:
      - signal: REVERSAL_HINT
        percentage: 30%
        mode: FLEXIBLE
```

**Trade Flow**:
```
Bar 100: Enter SHORT (100%)
Bar 120: TP1 hit (30%) → Remaining: 70%
Bar 130: WARNING_SIGNAL fires → Exit 20% × 70% = 14% → Remaining: 56%
Bar 140: TP2 hit (20%) → Remaining: 36%
Bar 150: REVERSAL_HINT fires → Exit 30% × 36% = 10.8% → Remaining: 25.2%
```

**Expected**: Each exit applies to REMAINING position at that time

---

#### E3: RECHECK with Nested Chains
**Config**:
```yaml
exit_conditions:
  - signal: ABOVE_ASIA_50
    percentage: 50%
    mode: ABSOLUTE
    recheck:
      enabled: true
      bar_delay: 3
      timing_mode: AT
      recheck_chain:
        - bar_delay: 2
          timing_mode: AT
          validation_mode: RECHECK
```

**Exit Flow**:
```
Bar 100: ABOVE_ASIA_50 fires → Record as pending (level 1)
Bar 103: Recheck at bar 103 (3 bars later)
  Signal still true? → YES → Record as pending (level 2)
Bar 105: Recheck at bar 105 (2 bars after level 1)
  Level 1 recheck still valid? → YES → EXIT (50%)
```

**Expected**: Double confirmation required (3 bars + 2 bars)

---

#### E4: Exit After Multiple TP Hits (TP-Aware Calculation)
**Trade State**:
```
Entry: 100% SHORT
TP1 (30%): Remaining 70%
TP2 (25%): Remaining 45%
TP3 (15%): Remaining 30%
```

**Exit Scenario 1 (FLEXIBLE)**:
```yaml
exit: 50% FLEXIBLE
Calculation: 50% × 30% remaining = 15%
Result: Exit 15%, Remaining: 15%
```

**Exit Scenario 2 (ABSOLUTE)**:
```yaml
exit: 50% ABSOLUTE
Calculation: min(50%, 30% remaining) = 30%
Result: Exit 30%, Remaining: 0% (fully closed)
```

---

## 🧪 EDGE CASE SCENARIOS

### E-1: Exit Signal Fires BEFORE Entry
**Flow**:
```
Bar 50: ABOVE_ASIA_50 fires (no trade open)
Bar 100: Enter SHORT
Bar 150: ABOVE_ASIA_50 fires again
```

**Expected**: 
- Bar 50: Ignore (no trade to exit)
- Bar 150: Process exit normally

---

### E-2: Same Signal Used for Entry AND Exit
**Config**:
```yaml
entry:
  signals:
    - AT_ASIA_50  (entry signal)

exit:
  - signal: AT_ASIA_50  (also exit signal)
    percentage: 100%
```

**Flow**:
```
Bar 100: AT_ASIA_50 fires → ENTRY
Bar 110: AT_ASIA_50 fires again → EXIT
```

**Expected**: Valid configuration, signal can trigger both entry and exit

---

### E-3: Exit Percentage Exceeds Remaining
**Config**:
```yaml
exit: 80% FLEXIBLE
```

**Trade State**: Remaining 30%

**Calculation**: 80% × 30% = 24%
**Expected**: Exit 24% (not 80%, TP-aware applies to remaining)

---

### E-4: Multiple Exits Fire Simultaneously
**Config**:
```yaml
exit_conditions:
  - signal: ABOVE_ASIA_50
    percentage: 50%
  - signal: BULLISH_CROSS
    percentage: 30%
```

**Bar 100**: Both ABOVE_ASIA_50 AND BULLISH_CROSS fire

**Expected**: 
- Process ABOVE_ASIA_50: 50% accumulated
- Process BULLISH_CROSS: 30% accumulated
- Total: 80% exit (both accumulate)
- **ALL firing exits accumulate!**

---

### E-5: Recheck Window Expires
**Config**:
```yaml
recheck:
  enabled: true
  bar_delay: 5
  timing_mode: WITHIN
```

**Flow**:
```
Bar 100: ABOVE_ASIA_50 fires → Record as pending
Bar 101-105: Signal does NOT re-fire
Bar 106: Window expired
```

**Expected**: 
- No exit triggered
- Pending recheck removed from queue
- If signal fires again at bar 110 → New recheck cycle starts

---

### E-6: Recheck Confirms but Position Already Closed
**Config**:
```yaml
recheck:
  enabled: true
  bar_delay: 5
  timing_mode: AT
```

**Flow**:
```
Bar 100: Exit signal fires → Pending recheck (check at bar 105)
Bar 103: SL hit → Position fully closed (remaining = 0%)
Bar 105: Recheck confirms signal still valid
```

**Expected**: 
- Recheck validation runs
- Exit calculation: 50% × 0% = 0%
- No exit executed (position already closed)
- Or: Check if trade exists before processing exit

---

## 📝 TEST CASE MATRIX

| ID | Binding Level | Exit Mode | Recheck | Timing Mode | Priority |
|----|--------------|-----------|---------|-------------|----------|
| TC-001 | STRATEGY | ABSOLUTE | Disabled | N/A | HIGH |
| TC-002 | STRATEGY | FLEXIBLE | Disabled | N/A | HIGH |
| TC-003 | BLOCK | ABSOLUTE | Disabled | N/A | HIGH |
| TC-004 | BLOCK | FLEXIBLE | Disabled | N/A | HIGH |
| TC-005 | SIGNAL | ABSOLUTE | Disabled | N/A | CRITICAL |
| TC-006 | SIGNAL | FLEXIBLE | Disabled | N/A | CRITICAL |
| TC-007 | STRATEGY | ABSOLUTE | Enabled | AT | HIGH |
| TC-008 | STRATEGY | ABSOLUTE | Enabled | WITHIN | HIGH |
| TC-009 | STRATEGY | FLEXIBLE | Enabled | AT | MEDIUM |
| TC-010 | STRATEGY | FLEXIBLE | Enabled | WITHIN | MEDIUM |
| TC-011 | BLOCK | ABSOLUTE | Enabled | AT | MEDIUM |
| TC-012 | BLOCK | ABSOLUTE | Enabled | WITHIN | MEDIUM |
| TC-013 | BLOCK | FLEXIBLE | Enabled | AT | LOW |
| TC-014 | BLOCK | FLEXIBLE | Enabled | WITHIN | LOW |
| TC-015 | SIGNAL | ABSOLUTE | Enabled | AT | HIGH |
| TC-016 | SIGNAL | ABSOLUTE | Enabled | WITHIN | HIGH |
| TC-017 | SIGNAL | FLEXIBLE | Enabled | AT | CRITICAL |
| TC-018 | SIGNAL | FLEXIBLE | Enabled | WITHIN | CRITICAL |
| TC-019 | Multi-Tier | Mixed | Disabled | N/A | CRITICAL |
| TC-020 | Multi-Tier | Mixed | Enabled | Mixed | CRITICAL |
| TC-021 | SIGNAL | FLEXIBLE | Disabled | N/A | CRITICAL |
| TC-022 | SIGNAL | FLEXIBLE | Enabled | WITHIN | CRITICAL |
| TC-023 | Multiple | FLEXIBLE | Disabled | N/A | HIGH |
| TC-024 | SIGNAL + Block | Mixed | Enabled | WITHIN | HIGH |

---

## ✅ VALIDATION CHECKLIST

For EACH test case, verify:

### Binding Validation
- [ ] Strategy-level exits apply to ALL trades
- [ ] Block-level exits apply only to trades using that block
- [ ] Signal-level exits apply ONLY if bound signal fired for entry
- [ ] entry_signals list correctly populated on entry
- [ ] Binding check extracts signal name correctly from signal_id

### Exit Mode Validation
- [ ] ABSOLUTE: Percentage of original position
- [ ] FLEXIBLE: Percentage of remaining position  
- [ ] ABSOLUTE capped at remaining position (can't exit more than exists)
- [ ] FLEXIBLE accurately multiplies: requested × remaining

### Recheck Validation
- [ ] Disabled: Exit fires immediately when signal appears
- [ ] Enabled + AT: Exit fires ONLY at exact bar (fire_bar + bar_delay)
- [ ] Enabled + WITHIN: Exit fires if signal re-confirms within window
- [ ] Enabled + WITHIN: Window expiration handled correctly
- [ ] Nested rechecks: Chain of confirmations required
- [ ] Pending rechecks tracked in evaluator state

### Hierarchy Validation
- [ ] STRATEGY-level: ALL exits checked and accumulated
- [ ] BLOCK-level: ALL exits checked and accumulated
- [ ] SIGNAL-level: ALL binding-valid exits checked and accumulated
- [ ] ALL firing exits accumulate across all tiers
- [ ] Total percentage capped at remaining_position
- [ ] Multiple exits at same level: ALL accumulate

### Edge Case Validation
- [ ] Exit signal fires when no trade open → Ignored
- [ ] Exit after position fully closed → Graceful handling
- [ ] Exit percentage > remaining → Capped correctly
- [ ] Multiple exits fire simultaneously → ALL accumulate
- [ ] Same signal used for entry and exit → Valid

---

## 🎯 IMPLEMENTATION STATUS

### ✅ IMPLEMENTED
1. **Binding Enforcement** (BUG #1 from EXIT_HIERARCHY_RECHECK_BUG_20260216.md)
   - TradeState.entry_signals tracks which signals fired
   - exit_hierarchy_evaluator checks signal binding
   - Signal-level exits ONLY fire if bound signal in entry_signals

2. **3-Tier Hierarchy**
   - STRATEGY → BLOCK → SIGNAL evaluation order
   - ALL exits checked, percentages accumulated

3. **TP-Aware Calculations**
   - ABSOLUTE and FLEXIBLE modes
   - Remaining position tracking

### 🔴 NOT IMPLEMENTED (CRITICAL)
1. **Recheck Validation** (BUG #2 from EXIT_HIERARCHY_RECHECK_BUG_20260216.md)
   - exit_hierarchy_evaluator._check_exit_signal() has NO recheck logic
   - Exits fire immediately regardless of recheck config
   - Requires state machine for pending exit rechecks
   - Must implement AT and WITHIN timing modes
   - Must Track recheck windows and expiration

### 🟡 PARTIALLY IMPLEMENTED
1. **Exit Condition Data Structure**
   - ExitCondition has recheck_config field
   - Config properly stored in database
   - NOT used by exit evaluator

---

## 🔧 REQUIRED FIXES

### Fix #1: Add Pending Exit Rechecks State
```python
class ExitHierarchyEvaluator:
    def __init__(self):
        self.pending_exit_rechecks: Dict[str, PendingExitRecheck] = {}
```

### Fix #2: Implement Recheck Logic in _check_exit_signal()
```python
def _check_exit_signal(self, exit_cond, bar, bar_index, lookback, blocks) -> bool:
    recheck_config = exit_cond.recheck_config
    
    if recheck_config and recheck_config.get('enabled'):
        # Implement state machine
        return self._validate_exit_recheck(...)
    else:
        # Simple check (existing logic)
        return self._signal_currently_firing(...)
```

### Fix #3: Add Recheck State Cleanup
```python
def reset(self):
    """Reset for new backtest"""
    self.pending_exit_rechecks.clear()
```

---

## 📌 NEXT STEPS

1. ✅ Create this comprehensive scenarios document
2. ⏭️ Implement recheck validation in exit_hierarchy_evaluator.py
3. ⏭️ Create comprehensive test script (test_exit_conditions_comprehensive.py)
4. ⏭️ Execute all 24+ test cases
5. ⏭️ Update EXIT_HIERARCHY_RECHECK_BUG_20260216.md with results
6. ⏭️ Verify institutional-grade quality

---

**END OF EXIT CONDITIONS COMPREHENSIVE SCENARIOS**
