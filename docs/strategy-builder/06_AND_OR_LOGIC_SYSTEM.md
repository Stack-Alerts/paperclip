# AND/OR Logic System
**Document**: 06_AND_OR_LOGIC_SYSTEM.md  
**Status**: 🟢 Complete  
**Priority**: P0 - Critical

## Logic System Overview

### AND Logic (Mandatory Blocks)
**Purpose**: Required conditions that must all be met
**Behavior**:
- All AND blocks must trigger
- All AND signals within block must trigger
- Adds to total required signal count
- Entry only when requirement met

**Example**:
```
Required Signals: 3
Block 1 (AND): Double Top → BEARISH_BREAKDOWN
Block 2 (AND): Volume → HIGH_VOLUME  
Block 3 (AND): RSI → OVERBOUGHT

Entry: Only when all 3 signals present
```

### OR Logic (Optional/Booster Blocks)
**Purpose**: Confluence boosters that enhance strategy
**Behavior**:
- Not required for entry
- Increases position size when present
- Adds leverage multiplier
- Provides confidence boost

**Example**:
```
Required Signals: 2 (from AND blocks)
Block 1 (AND): Pattern signal
Block 2 (AND): Volume signal
Block 3 (OR): Momentum signal ← Booster

Entry: Triggers with 2 AND signals
Position: 1.0x base
If Block 3 triggers: 1.1x position size
```

### Mixed Logic Strategy
```python
class LogicEvaluator:
    def evaluate_entry(self, signal_state, config):
        # Count AND block signals
        and_count = 0
        for block in config.blocks:
            if block.logic == 'AND':
                if self.block_triggered(block, signal_state):
                    and_count += 1
        
        # Check if required met
        entry_valid = and_count >= config.required_signals
        
        # Calculate booster multiplier
        or_boost = 1.0
        for block in config.blocks:
            if block.logic == 'OR':
                if self.block_triggered(block, signal_state):
                    or_boost += 0.1  # 10% boost per OR block
        
        return {
            'entry': entry_valid,
            'position_multiplier': or_boost if entry_valid else 1.0
        }
```

### Cascade Reset Logic
**Trigger**: AND block timing constraint fails
**Action**:
1. Reset all signal counters
2. Clear signal history
3. Wait for first signal to restart
4. Log reset event

**OR Block Behavior**:
- OR block failures don't reset strategy
- Continue accumulating if triggered
- Provide boost when final entry occurs

**Version**: 1.0
