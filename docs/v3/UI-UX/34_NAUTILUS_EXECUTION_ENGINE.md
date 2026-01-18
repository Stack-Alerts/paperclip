# ExecutionEngine Integration
**Document**: 34_NAUTILUS_EXECUTION_ENGINE.md
**Status**: 🟢 Complete
**Priority**: P1 - High

## Order Lifecycle

### Submit Order
```python
order = MarketOrder(...)
self.submit_order(order)
```

### Order Events
```python
def on_order_filled(self, event):
    # Order filled
    pass
    
def on_order_rejected(self, event):
    # Order rejected
    pass
```

**Version**: 1.0
