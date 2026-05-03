# Signal Configuration System
**Document**: 05_SIGNAL_CONFIGURATION.md  
**Status**: 🟢 Complete  
**Priority**: P0 - Critical

## Signal Configuration Interface

### Button-Based Signal Addition
**Primary Control**: "Add Signal" button on each block
**Flow**:
1. Click "Add Signal" → Dropdown appears
2. Shows all valid signals for the block
3. Each signal displays: Name, Description, Occurrence %
4. User selects signal
5. Configuration panel appears

### Signal Configuration Panel
**Controls**:
- AND/OR Toggle Buttons (default: AND)
- "Within X Candles" Checkbox
- Candle Count Spinner (1-100)
- Reference Signal Dropdown
- Dependency Indicator
- Remove Signal Button

### AND/OR Logic
**AND (Mandatory)**:
- Default selection
- Adds to required signal count
- Must trigger for strategy to execute
- Visual: Green badge

**OR (Optional/Booster)**:
- Provides confluence bonus
- Increases position size when triggered
- Does not block strategy execution
- Visual: Blue badge

### Timing Constraints
**"Within X Candles" Feature**:
- Checkbox enables constraint
- Spinner sets candle count
- Dropdown selects reference:
  - "from Signal 1"
  - "from Signal 2"
  - "from any previous signal"
- Visual indicator shows constraint

### Auto Signal Count Calculation
```python
def calculate_required_signals(blocks):
    total = 0
    for block in blocks:
        if block.logic == 'AND':
            and_signals = [s for s in block.signals if s.logic == 'AND']
            total += max(len(and_signals), 1)
    return total
```

### Signal State Tracking
```python
class SignalState:
    def __init__(self):
        self.triggered_signals = []
        self.pending_constraints = []
        
    def add_signal_trigger(self, signal, candle_index):
        self.triggered_signals.append({
            'signal': signal,
            'candle': candle_index,
            'timestamp': datetime.now()
        })
        
    def check_timing_constraint(self, constraint):
        ref_signal = self.find_reference(constraint.reference)
        if not ref_signal:
            return False
        current_candle = self.current_candle_index
        elapsed = current_candle - ref_signal['candle']
        return elapsed <= constraint.candles
```

**Version**: 1.0
