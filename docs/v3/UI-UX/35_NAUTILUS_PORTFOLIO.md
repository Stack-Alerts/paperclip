# Portfolio Tracking Integration
**Document**: 35_NAUTILUS_PORTFOLIO.md
**Status**: 🟢 Complete
**Priority**: P1 - High

## Portfolio Integration

### Position Tracking
```python
position = self.portfolio.net_position(self.instrument)
if position:
    size = position.quantity
    pnl = position.unrealized_pnl
```

### Account Balance
```python
account = self.portfolio.account
balance = account.balance_total()
```

**Version**: 1.0
