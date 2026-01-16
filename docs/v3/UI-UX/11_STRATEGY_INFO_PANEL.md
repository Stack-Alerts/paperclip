# Strategy Information Panel
**Document**: 11_STRATEGY_INFO_PANEL.md
**Status**: 🟢 Complete
**Priority**: P2 - Medium

## Panel Components

### Strategy Name
- Text input (required)
- Unique validation
- Max 100 characters

### Strategy Description  
- Auto-generated from blocks and signals
- Editable textarea
- Updates on block/signal changes
- Example: "Double Top (REQUIRED) + Volume Spike (REQUIRED) + RSI (OPTIONAL BOOSTER)"

### Strategy Type Indicator
- Auto-detected: Bullish/Bearish
- Visual badge with color
- Based on dominant signals

### Required Signals Count
- Auto-calculated
- Only counts AND blocks
- Updates on config changes
- Display: "Required Signals: 3"

### Auto-Description Generator
```python
def generate_description(config):
    parts = []
    for block in config.blocks:
        logic = "REQUIRED" if block.logic == 'AND' else "OPTIONAL"
        signals = [s.name for s in block.signals[:2]]
        parts.append(f"{block.name} ({logic}): {', '.join(signals)}")
    return " + ".join(parts)
```

**Version**: 1.0
