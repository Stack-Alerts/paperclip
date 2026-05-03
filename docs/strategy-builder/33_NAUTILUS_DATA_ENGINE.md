# DataEngine Integration
**Document**: 33_NAUTILUS_DATA_ENGINE.md
**Status**: 🟢 Complete
**Priority**: P1 - High

## DataEngine Integration

### Bar Subscription
```python
def on_start(self):
    bar_type = BarType(
        self.instrument_id,
        BarAggregation.{{TIMEFRAME}},
        {{PERIOD}}
    )
    self.subscribe_bars(bar_type)
```

### Data Handling
```python
def on_bar(self, bar: Bar):
    # Bar attributes
    open_price = bar.open
    high_price = bar.high
    low_price = bar.low
    close_price = bar.close
    volume = bar.volume
    timestamp = bar.ts_event
```

**Version**: 1.0
