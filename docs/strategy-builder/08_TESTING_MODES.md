# Testing Modes Design
**Document**: 08_TESTING_MODES.md  
**Status**: 🟢 Complete  
**Priority**: P1 - High

## Mode 1: Historical Walkforward

### Overview
Expand testing window candle-by-candle from X days back to current.

### Configuration
- **Testing Window**: Days to test (e.g., 180)
- **Training Window**: Optional days for training (e.g., 30)
- **Total Data**: training + testing days
- **Timeframe**: 1min, 5min, 15min, 1h, 4h, 1d

### Process Flow
1. Load data: (training + testing) days back
2. Start at: current_date - testing_days
3. For each candle:
   - Detect signals
   - Check entry conditions
   - Manage positions
   - Record metrics
4. Stop at current candle
5. Generate report

### Reporting
- Total signals triggered
- Trades executed
- Win rate, profit factor
- Max drawdown
- TP1/TP2/TP3 adjustment counts
- SL adjustment counts

## Mode 2: Live Continuation

### Overview
Historical walkforward then continue with live data indefinitely.

### Process Flow
1. Execute Mode 1 (historical phase)
2. Upon reaching current candle:
   - Display "Historical complete. Waiting for live candles..."
   - Switch to live data stream
3. For each new candle:
   - Process in real-time
   - Update metrics live
   - Continue indefinitely
4. User clicks "Stop Test"
5. Generate final report (historical + live period)

### Live Streaming
```python
class LiveTestEngine:
    def start_live_continuation(self, historical_results):
        self.results = historical_results
        self.live_start = datetime.now()
        
        # Subscribe to live feed
        self.data_provider.stream_live(
            symbol='BTC/USDT',
            timeframe=self.config.timeframe,
            callback=self.on_new_candle
        )
        
    def on_new_candle(self, candle):
        # Process new candle
        signals = self.detect_signals(candle)
        self.evaluate_entry(signals)
        self.manage_positions(candle)
        
        # Update UI
        self.emit_update({
            'total_days': self.historical_days + self.live_days,
            'live_candles': self.live_candle_count,
            'current_pnl': self.calculate_pnl()
        })
```

### UI Updates (Mode 2)
```
Test Status: 🟢 LIVE
Historical Period: 180 days (complete)
Live Period: 2 days 4 hours (ongoing)
Total Test Duration: 182 days 4 hours
New Candles Processed: 156
Live P&L: +$1,234.56

[Stop Test] button
```

**Version**: 1.0
