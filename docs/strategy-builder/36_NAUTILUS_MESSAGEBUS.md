# MessageBus Events Integration
**Document**: 36_NAUTILUS_MESSAGEBUS.md
**Status**: 🟢 Complete
**Priority**: P2 - Medium

## MessageBus Integration

### Event Publishing
```python
self.publish_event(event)
```

### Event Subscription
```python
self.subscribe(EventType.ORDER_FILLED, self.on_order_filled)
```

**Version**: 1.0
