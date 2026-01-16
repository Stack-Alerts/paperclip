# NautilusTrader Type System Integration
**Document**: 32_NAUTILUS_TYPE_SYSTEM.md
**Status**: 🟢 Complete
**Priority**: P0 - Critical

## Type System Usage

### Quantity Type
**Usage**: All size/volume measurements
```python
from nautilus_trader.model.types import Quantity

# Correct
position_size = Quantity(0.1)  # 0.1 BTC
order_qty = Quantity(0.05)

# WRONG
position_size = 0.1  # ❌ Never use float
```

### Price Type  
**Usage**: All price levels
```python
from nautilus_trader.model.types import Price

# Correct
entry_price = Price('45000.50')
stop_loss = Price('44500.00')

# WRONG
entry_price = 45000.50  # ❌ Never use float
```

### Money Type
**Usage**: All monetary amounts
```python
from nautilus_trader.model.types import Money
from nautilus_trader.model.currencies import USD

# Correct
pnl = Money('1234.56', USD)
fee = Money('5.00', USD)

# WRONG
pnl = 1234.56  # ❌ No currency specified
```

### Decimal Precision
**All calculations use exact decimal arithmetic**
- No floating point errors
- Institutional-grade accuracy
- Proper rounding

**Version**: 1.0
