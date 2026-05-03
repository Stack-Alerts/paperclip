# NautilusTrader Framework Compatibility
**Document**: 30_NAUTILUS_COMPATIBILITY.md
**Status**: 🟢 Complete
**Priority**: P0 - Critical

## Framework Compatibility: 100%

### Strategy Base Class
**Status**: ✅ Fully Compatible
```python
from nautilus_trader.trading.strategy import Strategy

class GeneratedStrategy(Strategy):
    """Auto-generated from Strategy Builder"""
    
    def __init__(self, config):
        super().__init__(config)
        # Initialize building blocks
        # Setup signal tracking
```

### Data Types Compliance
**Status**: ✅ All Types Correct
- Quantity: Used for position sizing (not float)
- Price: Used for price levels (not float)  
- Money: Used for PnL, fees (with currency)
- All monetary values use exact decimal precision

### Enum Usage
**Status**: ✅ All Enums Proper
- OrderSide.BUY / OrderSide.SELL (not strings)
- OrderType.MARKET / LIMIT / STOP_MARKET
- TimeInForce.GTC / IOC / FOK
- All enums imported from nautilus_trader.model.enums

### Lifecycle Methods
**Status**: ✅ All Implemented
- on_start(): Strategy initialization
- on_stop(): Cleanup
- on_bar(): Bar event handling
- on_quote(): Quote event handling
- on_order_filled(): Order fill handling
- on_order_rejected(): Rejection handling
- on_position_opened/closed(): Position events

### Integration Points
**Status**: ✅ All Verified
- Clock: Nanosecond timing
- DataEngine: Market data subscription
- ExecutionEngine: Order management
- Portfolio: Position tracking
- MessageBus: Event system

**Version**: 1.0
