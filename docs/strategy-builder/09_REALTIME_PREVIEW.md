# Real-time Preview System
**Document**: 09_REALTIME_PREVIEW.md  
**Status**: 🟢 Complete  
**Priority**: P1 - High

## Preview System Overview
Provide live backtest preview as user builds strategy, updating on every configuration change.

## Preview Configuration
**Data Window**: Last 30 days (quick preview)
**Update Trigger**: Any strategy modification
**Execution**: Background thread
**Display**: Chart with signals + quick metrics

## Preview Engine
```python
class RealtimePreviewEngine:
    def __init__(self, data_provider, code_gen):
        self.data_provider = data_provider
        self.code_gen = code_gen
        self.preview_thread = None
        self.last_config = None
        
    def start(self, config, callback):
        if self.preview_thread:
            self.stop()
            
        self.last_config = config
        self.callback = callback
        
        # Load last 30 days
        df = self.data_provider.load_historical(
            'BTC/USDT',
            config.timeframe,
            start_days_ago=30
        )
        
        # Run in background
        self.preview_thread = threading.Thread(
            target=self._run_preview,
            args=(config, df)
        )
        self.preview_thread.start()
        
    def update_config(self, new_config):
        if self._config_changed(new_config):
            self.start(new_config, self.callback)
            
    def _run_preview(self, config, df):
        try:
            # Generate strategy code
            code = self.code_gen.generate_strategy(config)
            
            # Quick backtest
            engine = QuickBacktestEngine()
            results = engine.run(code, df)
            
            # Extract signals for chart
            signals = self._extract_signals(results)
            
            # Callback with results
            self.callback(PreviewResults(
                chart_data=df,
                signals=signals,
                metrics=self._quick_metrics(results)
            ))
        except Exception as e:
            self.callback(PreviewError(str(e)))
```

## Quick Metrics
- Signals triggered: XX
- Potential trades: XX
- Estimated win rate: XX%
- Est. P&L: $XXX

## Chart Visualization
- Price candlesticks
- Signal markers (color-coded by block)
- Entry/exit points
- Interactive zoom/pan

## Performance Optimization
- Debounce config changes (500ms)
- Cancel in-progress preview on new change
- Cache recent data
- Limit to last 30 days
- Use simplified backtest (skip detailed reporting)

**Version**: 1.0
