# Adaptive SL/TP Integration
**Document**: 12_ADAPTIVE_SL_TP.md
**Status**: 🟢 Complete
**Priority**: P2 - Medium

## Integration Overview
Leverage existing Adaptive SL v2.0 and Dynamic TP systems.

## Stop Loss Configuration
**Modes**:
- Fibonacci: Based on swing points
- Aggressive: Tighter stops
- Conservative: Wider stops

**Parameters**:
- Fibonacci level: 0.236, 0.382, 0.5, 0.618
- Aggressive factor: 0.8-1.5
- Conservative factor: 1.2-2.0

## Take Profit Configuration
**Modes**:
- Fibonacci: Based on target levels
- Hybrid: Mix of Fibonacci and risk/reward
- Static: Fixed percentage

**Parameters**:
- TP1: 1st target (e.g., 1.5%)
- TP2: 2nd target (e.g., 3.0%)
- TP3: 3rd target (e.g., 5.0%)
- Partial close percentages

## Integration with Strategy Builder
Strategy config includes SL/TP section:
```python
{
    'sl_mode': 'fibonacci',
    'sl_fibonacci_level': 0.618,
    'tp_mode': 'hybrid',
    'tp1': 1.5,
    'tp2': 3.0,
    'tp3': 5.0
}
```

Generated code uses existing classes:
```python
from src.strategies.modules.adaptive_sl_v2 import AdaptiveSLv2
self.sl_manager = AdaptiveSLv2(self.config['sl_config'])
```

**Version**: 1.0
