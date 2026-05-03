# Timing Constraints System
**Document**: 07_TIMING_CONSTRAINTS.md  
**Status**: 🟢 Complete  
**Priority**: P1 - High

## Timing Constraint Overview
"Within X Candles" feature allows signals to be time-dependent, requiring them to fire within a specific window relative to another signal.

## Constraint Configuration
**UI Components**:
- Checkbox: "Within X Candles"
- Spinner: Candle count (1-100)
- Dropdown: Reference signal selection
- Visual indicator: Shows constraint in UI

## Reference Signal Options
1. **From Signal 1**: Count from first signal in current block
2. **From Signal 2**: Count from second signal
3. **From any previous signal**: Use most recent qualifying signal
4. **From Block X Signal Y**: Cross-block reference

## Constraint Validation Logic
```python
class TimingValidator:
    def validate_constraint(self, signal, constraint, history):
        # Find reference signal
        ref_signal = self.find_reference(constraint.reference, history)
        if not ref_signal:
            return False  # Reference not found
            
        # Calculate candles elapsed
        current_idx = history.current_candle_index
        ref_idx = ref_signal.candle_index
        elapsed = current_idx - ref_idx
        
        # Check if within limit
        return elapsed <= constraint.max_candles
```

## Cascade Reset Mechanism
**Trigger**: Timing constraint fails on AND signal
**Process**:
1. Log constraint failure
2. Reset ALL signal counters
3. Clear signal history
4. Set state to "waiting for first signal"
5. Restart accumulation

## Visual Indicators
```
Signal 1: BREAKDOWN (triggered at candle 100)
Signal 2: HIGH_VOLUME ⏱ Within 20 candles
  Status: ⏳ 5 candles elapsed (15 remaining)
  
If candle 121 reached without Signal 2:
  Status: ❌ Constraint failed - Strategy reset
```

**Version**: 1.0
