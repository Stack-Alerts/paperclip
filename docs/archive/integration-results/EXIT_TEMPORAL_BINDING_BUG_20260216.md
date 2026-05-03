# 🚨 CRITICAL BUG: Exit Conditions Ignore Temporal Session Boundaries

**Date Discovered**: 2026-02-16  
**Severity**: CRITICAL (Real money risk)  
**Status**: 🔴 ACTIVE BUG - NOT FIXED  
**Category**: Temporal Binding Violation

---

## Executive Summary

Exit conditions configured to fire during specific session windows (e.g., Asia session 00:00-08:00 UTC) are **completely ignoring temporal boundaries** and firing at arbitrary times outside their configured windows.

**Impact**: Trades are exiting due to signals that have NO temporal relationship to their entry context, making strategy behavior non-deterministic and unsuitable for live trading.

---

## Bug Evidence: Trade 3.1 Forensic Analysis

### Observed Behavior
```
Entry:  2025-08-25 02:30:00 UTC (DURING Asia session 00:00-08:00)
Exit:   2025-08-26 15:30:00 UTC (15:00 UTC - 7 HOURS AFTER Asia session ended!)

Entry Signal:    BELOW_ASIA_50 (asia_session_50_percent building block)
Exit Condition:  ABOVE_ASIA_50 (bound to same building block)

Expected: Exit should ONLY evaluate during 2025-08-25 Asia session (00:00-08:00)
Actual:   Exit fired at 15:00 UTC on NEXT DAY, completely outside Asia window
```

### Mathematical Proof of Bug
```
Asia Session Window:  00:00 - 08:00 UTC daily
Exit Timestamp:       15:30 UTC
Offset from window:   +7.5 hours AFTER window closed

Temporal Violation:   100% confirmed
```

### Financial Impact
```
Actual P&L:           $1,208.66
Expected P&L (TPs):   $1,186.64 (if TPs had fired correctly)
TP2 reached but didn't fire because exit closed position first
```

---

## Root Cause Analysis

### 1. Missing Session Window Validation

**Location**: `src/optimizer_v3/core/exit_hierarchy_evaluator.py`

**Current Implementation**:
```python
# Signal-level exit evaluation (line ~180)
if signal_id not in current_trade.entry_signals:
    continue  # ✅ Binding check exists

# But NO temporal window check!
# Missing:
if not self._is_within_signal_session_window(signal_id, current_bar_time):
    continue  # ❌ This check does NOT exist!
```

**What's Missing**:
- No tracking of when entry signals fired (date/time context)
- No extraction of session definition from building block metadata
- No validation that current bar time matches session window
- No temporal binding between entry signal timing and exit signal timing

### 2. Building Block Session Metadata Not Utilized

Asia session building blocks have session definitions in metadata:
```python
# asia_session_50_percent building block metadata
{
    "session_start": "00:00",
    "session_end": "08:00",
    "timezone": "UTC"
}
```

But this metadata is **NEVER CONSULTED** during exit evaluation!

### 3. Signal ID Contains Session Info But Not Used

Signal IDs have session context: `"asia_session_50_percent::BELOW_ASIA_50"`

The system checks if this exact signal was in entry_signals, but **NEVER validates** that the CURRENT BAR is within the Asia session window.

---

## Expected Behavior vs Actual Behavior

### Expected (CORRECT)
```
1. Trade enters at 2025-08-25 02:30 (DURING Asia session 00:00-08:00)
   Entry signals: ["asia_session_50_percent::BELOW_ASIA_50"]
   Record entry_date: 2025-08-25

2. Every bar, exit evaluator checks exit condition:
   - Is signal "asia_session_50_percent::BELOW_ASIA_50" in entry_signals? ✅ YES
   - Is current bar within 2025-08-25 Asia session (00:00-08:00)? 
   - If YES: Evaluate ABOVE_ASIA_50
   - If NO: SKIP (wrong session or wrong day)

3. At 2025-08-25 08:00:
   - Asia session ends
   - Exit condition STOPS evaluating (session window closed)
   - Trade continues to TP levels

4. At 2025-08-26 00:00-08:00:
   - Next day's Asia session
   - Exit condition DOES NOT evaluate (entry was on 2025-08-25, not 2025-08-26)
   - Trade still continues

5. TPs fire normally:
   - TP2 @ 1.45%: Closes 33% of position
   - TP3 @ 2.3%: Closes 34% of position
   - Remaining 33% continues or exits on other condition
```

### Actual (BUG)
```
1. Trade enters at 2025-08-25 02:30
   Entry signals: ["asia_session_50_percent::BELOW_ASIA_50"]

2. Every bar until exit:
   - Is signal in entry_signals? ✅ YES
   - (NO temporal window check performed!)
   - Evaluates ABOVE_ASIA_50 condition

3. At 2025-08-26 15:30 (15:00 UTC):
   - 39 hours after entry
   - 31 hours after Asia session ended (08:00 on 2025-08-25)
   - 7 hours after next day's Asia session ended (08:00 on 2025-08-26)
   - ABOVE_ASIA_50 triggers
   - Position closes 100%

4. TPs never fire:
   - Price reached TP2 level
   - But position already closed by exit condition
   - Financial outcome distorted
```

---

## Affected Building Blocks

ALL session-based building blocks are affected:

### 1. Asia Session (00:00-08:00 UTC)
- `asia_session_50_percent`
- `asia_session_high_rejection`
- `asia_session_low_rejection`
- Any Asia session liquidity blocks

### 2. London Session (08:00-16:00 UTC)
- `london_session_*`
- London Open building blocks

### 3. New York Session (13:00-21:00 UTC)
- `ny_session_*`
- NY Open building blocks

### 4. Specific Time Windows
- `market_structure_ict_*` (if time-bounded)
- Any building block with temporal constraints

**Impact Scope**: ~15-20 building blocks out of 83+ total

---

## Critical Violations

### 1. Temporal Binding Contract Violation
```
Contract: If entry signal has temporal context (session, time window),
          exit conditions bound to that signal MUST respect the same temporal context.

Violation: Exit conditions completely ignore temporal context.

Result: Non-deterministic exits, strategy behavior unpredictable.
```

### 2. Session Isolation Violation
```
Contract: Asia session on Day X is ISOLATED from Asia session on Day X+1.
          Entry in one session should NOT affect exits in a different session instance.

Violation: Session instances are not isolated. Entry on 2025-08-25 Asia session
           affects exits on 2025-08-26 and beyond.

Result: Trades can exit due to unrelated session instances days/weeks later.
```

### 3. Financial Integrity Violation
```
Contract: TP levels should be respected in order (TP1 → TP2 → TP3).
          Exit conditions should only fire in their configured windows.

Violation: Exit conditions fire at arbitrary times, preempting TPs.

Result: P&L differs from expected, partial exits don't work correctly.
```

---

## Required Fix: Implement Temporal Binding

### Phase 1: Track Entry Signal Timing Context

**File**: `src/optimizer_v3/core/trade_state.py`

```python
@dataclass
class TradeState:
    # ... existing fields ...
    entry_signals: List[str] = field(default_factory=list)  # ✅ EXISTS
    
    # NEW: Add temporal context
    entry_signal_contexts: Dict[str, dict] = field(default_factory=dict)
    # Format:
    # {
    #     "asia_session_50_percent::BELOW_ASIA_50": {
    #         "entry_bar": 100,
    #         "entry_date": "2025-08-25",
    #         "entry_time": "02:30:00",
    #         "session_start": "00:00",
    #         "session_end": "08:00",
    #         "session_date": "2025-08-25"  # Lock to SPECIFIC session instance
    #     }
    # }
```

### Phase 2: Capture Context at Entry

**File**: `src/optimizer_v3/core/multicore_backtest_engine.py` (or simulator)

```python
def enter_trade(..., entry_signals: List[str]):
    # Extract building block metadata for each signal
    signal_contexts = {}
    for signal_id in entry_signals:
        block_name = signal_id.split("::")[0]
        block_metadata = self.registry.get_block_metadata(block_name)
        
        if "session_start" in block_metadata:
            # Session-based signal
            signal_contexts[signal_id] = {
                "entry_bar": current_bar,
                "entry_date": str(current_bar_time.date()),
                "entry_time": str(current_bar_time.time()),
                "session_start": block_metadata["session_start"],
                "session_end": block_metadata["session_end"],
                "session_date": str(current_bar_time.date())  # Lock to entry date
            }
    
    trade_state = TradeState(
        entry_signals=entry_signals,
        entry_signal_contexts=signal_contexts,
        # ... other fields ...
    )
```

### Phase 3: Validate Temporal Windows at Exit

**File**: `src/optimizer_v3/core/exit_hierarchy_evaluator.py`

```python
def _evaluate_signal_level_exits(self, ...):
    for exit_cond in signal_level_exits:
        signal_id = f"{exit_cond.block_name}::{exit_cond.signal_name}"
        
        # ✅ Existing: Check if signal was part of entry
        if signal_id not in current_trade.entry_signals:
            continue
        
        # 🆕 NEW: Check temporal window
        if not self._is_within_signal_temporal_window(
            signal_id,
            current_trade.entry_signal_contexts,
            current_bar_time
        ):
            continue  # Skip - wrong session or outside window
        
        # ... rest of exit evaluation ...

def _is_within_signal_temporal_window(
    self, signal_id: str, contexts: Dict, current_time: datetime
) -> bool:
    """Validate that current bar is within the signal's temporal window."""
    if signal_id not in contexts:
        return True  # No temporal context = always valid
    
    context = contexts[signal_id]
    current_date = str(current_time.date())
    current_time_only = current_time.time()
    
    # Check 1: Must be SAME session instance (same date)
    if current_date != context["session_date"]:
        return False  # Different session instance
    
    # Check 2: Must be within session time window
    session_start = datetime.strptime(context["session_start"], "%H:%M").time()
    session_end = datetime.strptime(context["session_end"], "%H:%M").time()
    
    if not (session_start <= current_time_only <= session_end):
        return False  # Outside session window
    
    return True  # Within correct session instance and time window
```

---

## Testing Requirements

### Test Case 1: Session Instance Isolation
```python
def test_asia_session_instance_isolation():
    """Exit on 2025-08-25 Asia should NOT affect 2025-08-26 Asia"""
    entry_time = "2025-08-25 02:30"  # Day 1 Asia
    entry_signal = "asia_session_50_percent::BELOW_ASIA_50"
    
    # Check exit evaluation on Day 1 Asia (00:00-08:00)
    assert can_evaluate_exit("2025-08-25 03:00") == True
    assert can_evaluate_exit("2025-08-25 07:59") == True
    
    # Check exit stops after Day 1 Asia ends
    assert can_evaluate_exit("2025-08-25 08:01") == False
    
    # Check exit does NOT evaluate on Day 2 Asia
    assert can_evaluate_exit("2025-08-26 02:00") == False  # ❌ CURRENTLY FAILS
    assert can_evaluate_exit("2025-08-26 07:00") == False  # ❌ CURRENTLY FAILS
```

### Test Case 2: Outside Session Window
```python
def test_exit_only_fires_within_session():
    """Exit should NEVER fire outside session window"""
    entry_time = "2025-08-25 02:30"  # Asia session
    
    # Times OUTSIDE Asia session (08:00-24:00, next day 00:00)
    assert can_evaluate_exit("2025-08-25 09:00") == False  # ❌ CURRENTLY FAILS
    assert can_evaluate_exit("2025-08-25 12:00") == False  # ❌ CURRENTLY FAILS  
    assert can_evaluate_exit("2025-08-25 15:00") == False  # ❌ CURRENTLY FAILS
    assert can_evaluate_exit("2025-08-26 15:00 ") == False  # ❌ FAILS (Trade 3.1 bug)
```

### Test Case 3: TP Priority Over Late Exit
```python
def test_tp_fires_before_late_exit():
    """If exit window expires, TPs should take over"""
    entry_time = "2025-08-25 02:30"
    entry_price = 112265.72
    
    # Asia session ends at 08:00 - exit can no longer fire
    # Price moves to TP2 level at 12:00
    tp2_level = entry_price * 0.9855  # 1.45% for SHORT
    
    # At 12:00, price reaches TP2
    assert trade_status("2025-08-25 12:00") == "TP2_FIRED"  # ❌ CURRENTLY FAILS
    assert exit_condition_status("2025-08-25 12:00") == "EXPIRED"
```

---

## Implementation Plan

### Step 1: Add Temporal Context Tracking ✅
- Update TradeState with entry_signal_contexts
- Capture session metadata at entry time
- Store session date to lock to specific instance

### Step 2: Implement Window Validation ✅
- Add _is_within_signal_temporal_window() method
- Check session date matches entry date
- Check current time within session window
- Integrate into exit evaluator

### Step 3: Test All Session-Based Blocks 🔄
- Test Asia session isolation
- Test London session isolation
- Test NY session isolation
- Test multi-session strategies

### Step 4: Verify TP Priority 🔄
- Ensure TPs fire when exit window expires
- Verify financial integrity
- Check P&L matches expectations

### Step 5: Full Backtest Validation 🔄
- Run comprehensive backtests
- Verify exit counts are correct
- Check no exits fire outside windows
- Validate P&L accuracy

---

## Success Criteria

✅ **Exit Instance Isolation**: Exit conditions on Day X session do NOT evaluate on Day X+1 session  
✅ **Session Window Enforcement**: Exits NEVER fire outside their configured time windows  
✅ **TP Priority**: TPs fire normally when exit window expires  
✅ **Financial Integrity**: P&L matches expected values with correct TP sequencing  
✅ **Test Coverage**: All 50+ exit scenarios pass, including temporal binding tests  

---

## Related Documents

- `EXIT_HIERARCHY_RECHECK_BUG_20260216.md` - Signal binding and recheck bugs (FIXED)
- `EXIT_CONDITIONS_COMPREHENSIVE_SCENARIOS.md` - Full scenario documentation
- `TRADE_3_1_TEMPORAL_BINDING_ANALYSIS_20260216.txt` - Forensic analysis output
- `exit_hierarchy_evaluator.py` - Exit evaluation implementation
- `institutional_signal_evaluator.py` - Signal delay/recheck system

---

**CRITICAL**: This bug makes session-based strategies NON-DETERMINISTIC and UNSAFE for live trading. Must be fixed before any production deployment.
