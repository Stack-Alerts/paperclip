# Signal Statistics Incremental Update Guide

**Purpose**: Keep signal occurrence statistics up-to-date as strategies run on new data  
**Critical**: NEVER double-count signals on already-analyzed dates  
**Status**: Production-Ready  
**Date**: 2026-01-17

---

## Overview

The Signal Statistics Updater maintains accurate occurrence counts by:
1. **Tracking analyzed dates** per building block
2. **Filtering new dates** to prevent double-counting
3. **Atomic updates** with backups
4. **Thread-safe** for concurrent strategy runs

## Files

### Core Module
- **Path**: `src/strategy_builder/utils/signal_statistics_updater.py`
- **Class**: `SignalStatisticsUpdater`
- **Convenience functions**: `update_block_statistics()`, `is_date_analyzed()`

### Data Files
- **Statistics**: `data/catalog/signal_occurrence_statistics.json`
- **Date Tracking**: `data/catalog/signal_statistics_analyzed_dates.json` (auto-created)
- **Backup**: `data/catalog/signal_occurrence_statistics.backup` (auto-created before updates)

---

## Integration Points

### When to Update Statistics

Update signal statistics whenever a strategy runs on new data:

1. **Backtest Mode** - After backtest completes on new dates
2. **Paper Trading** - End of each trading day
3. **Live Trading** - End of each trading day
4. **Walk-Forward Testing** - After each window completes

### How to Integrate

#### Example 1: Backtest Completion

```python
from src.strategy_builder.utils.signal_statistics_updater import update_block_statistics
from datetime import datetime

def on_backtest_complete(strategy_name, results):
    """Called when backtest completes"""
    
    # Get blocks used in strategy
    blocks_used = strategy_config.blocks  # From your strategy config
    
    for block in blocks_used:
        block_name = block.name
        
        # Collect signal occurrences from backtest results
        # Format: {signal_name: [list of date strings where it occurred]}
        signal_occurrences = {}
        
        for result in results:
            signal = result.signal
            date_str = result.timestamp.date().isoformat()  # YYYY-MM-DD format
            
            if signal not in signal_occurrences:
                signal_occurrences[signal] = []
            
            signal_occurrences[signal].append(date_str)
        
        # Update statistics (automatically filters already-analyzed dates)
        success = update_block_statistics(
            block_name=block_name,
            signal_occurrences=signal_occurrences
        )
        
        if success:
            print(f"✅ Updated statistics for {block_name}")
        else:
            print(f"❌ Failed to update statistics for {block_name}")
```

#### Example 2: Paper/Live Trading End-of-Day

```python
from src.strategy_builder.utils.signal_statistics_updater import (
    update_block_statistics,
    is_date_analyzed
)
from datetime import date

def on_trading_day_end(strategy_blocks, signals_detected_today):
    """Called at end of trading day to update statistics"""
    
    today = date.today().isoformat()  # YYYY-MM-DD
    
    for block_name, signals in signals_detected_today.items():
        # signals = ['BULLISH', 'DIVERGENCE', 'BREAKOUT']
        
        # Check if already analyzed (skip if yes)
        if is_date_analyzed(block_name, today):
            print(f"ℹ️  {today} already analyzed for {block_name} - skipping")
            continue
        
        # Format as signal_occurrences dict
        signal_occurrences = {
            signal: [today] for signal in signals
        }
        
        # Update
        update_block_statistics(
            block_name=block_name,
            signal_occurrences=signal_occurrences
        )
```

#### Example 3: Manual Check Before Update

```python
from src.strategy_builder.utils.signal_statistics_updater import (
    SignalStatisticsUpdater,
    is_date_analyzed
)

# Get updater instance
updater = SignalStatisticsUpdater()

# Check which dates are new
block_name = "macd_crossover"
potential_dates = ['2026-01-15', '2026-01-16', '2026-01-17']

new_dates = [d for d in potential_dates if not is_date_analyzed(block_name, d)]

print(f"New dates to analyze: {new_dates}")

# Only update if there are truly new dates
if new_dates:
    signal_occurrences = {
        'BULLISH_CROSS': ['2026-01-15', '2026-01-17'],
        'BEARISH_CROSS': ['2026-01-16']
    }
    
    updater.update_statistics(block_name, signal_occurrences)
```

---

## API Reference

### Class: SignalStatisticsUpdater

#### Methods

**`__init__(stats_file: Optional[Path] = None)`**
```python
updater = SignalStatisticsUpdater()  # Uses default path
# Or specify custom path:
updater = SignalStatisticsUpdater(Path("/custom/path/stats.json"))
```

**`update_statistics(block_name, signal_occurrences, new_dates=None) -> bool`**
```python
success = updater.update_statistics(
    block_name="macd_crossover",
    signal_occurrences={
        'BULLISH': ['2026-01-17', '2026-01-18'],
        'BEARISH': ['2026-01-19']
    },
    new_dates=None  # Optional - auto-inferred if not provided
)
```

**`is_date_analyzed(block_name, date_string) -> bool`**
```python
already_done = updater.is_date_analyzed("macd_crossover", "2026-01-17")
```

**`get_analyzed_dates(block_name) -> Set[str]`**
```python
analyzed = updater.get_analyzed_dates("macd_crossover")
# Returns: {'2025-06-19', '2025-06-20', ..., '2026-01-17'}
```

**`get_statistics_summary() -> Dict`**
```python
summary = updater.get_statistics_summary()
# Returns: {
#     'status': 'ok',
#     'total_blocks': 83,
#     'total_signals': 586,
#     'total_dates_tracked': 14940,  # 180 days * 83 blocks
#     'data_days': 180,
#     'update_count': 5
# }
```

### Convenience Functions

```python
from src.strategy_builder.utils.signal_statistics_updater import (
    update_block_statistics,
    is_date_analyzed,
    get_statistics_summary
)

# Update (uses global singleton)
update_block_statistics("macd_crossover", signal_occurrences)

# Check date
if not is_date_analyzed("macd_crossover", "2026-01-17"):
    # Process new date
    pass

# Get summary
summary = get_statistics_summary()
```

---

## Data Format

### Signal Occurrences Input

```python
{
    'BULLISH': ['2026-01-17', '2026-01-18', '2026-01-19'],
    'BEARISH': ['2026-01-20'],
    'NEUTRAL': ['2026-01-17', '2026-01-18', '2026-01-19', '2026-01-20']
}
```

**Requirements**:
- Keys: Signal names (strings)
- Values: Lists of date strings in ISO format (YYYY-MM-DD)
- Same date can appear in multiple signals

### Analyzed Dates File

**Path**: `data/catalog/signal_statistics_analyzed_dates.json`

```json
{
  "macd_crossover": [
    "2025-06-19",
    "2025-06-20",
    "2025-06-21",
    ...
    "2026-01-17"
  ],
  "rsi_divergence": [
    "2025-06-19",
    "2025-06-20",
    ...
  ]
}
```

### Statistics File Updates

**Path**: `data/catalog/signal_occurrence_statistics.json`

**New Fields Added**:
```json
{
  "analysis_date": "2026-01-17T12:35:00",
  "last_updated": "2026-01-17T14:15:00",  // NEW
  "data_days": 180,
  "total_blocks": 83,
  "update_history": [  // NEW
    {
      "timestamp": "2026-01-17T14:15:00",
      "block": "macd_crossover",
      "new_dates_count": 3,
      "new_signals_count": 12,
      "updated_total_candles": 17284
    }
  ],
  "blocks": {
    "macd_crossover": {
      "block_name": "macd_crossover",
      "total_candles": 17284,  // UPDATED (was 17281)
      "errors": 0,
      "signals": {
        "BULLISH_CROSS": {
          "count": 1439,  // UPDATED (was 1436)
          "percentage": 8.32,  // RECALCULATED
          "total_candles": 17284
        }
      }
    }
  }
}
```

---

## Critical Features

### 1. Double-Counting Prevention

**How it works**:
```python
# Get already-analyzed dates
analyzed = {'2026-01-01', '2026-01-02', '2026-01-03'}

# New dates from strategy run
new_dates = {'2026-01-02', '2026-01-03', '2026-01-04'}

# Filter to truly new dates only
truly_new = new_dates - analyzed
# Result: {'2026-01-04'}  ← Only this date's signals will be counted
```

**Prevents**:
- Re-running backtest on same dates
- Overlapping trading periods
- Manual re-processing

### 2. Atomic Updates

**Process**:
1. Create backup: `signal_occurrence_statistics.backup`
2. Write to temp file: `signal_occurrence_statistics.tmp`
3. Atomic rename: `tmp` → `json`

**Benefits**:
- No partial writes (all-or-nothing)
- Backup available if corruption occurs
- Safe for concurrent access

### 3. Thread Safety

**Implementation**:
```python
with self._lock:
    # Critical section - only one thread at a time
    # 1. Load statistics
    # 2. Update counts
    # 3. Save statistics
```

**Allows**:
- Multiple strategies running simultaneously
- Concurrent paper trading instances
- Safe parallel backtesting

### 4. Metadata Tracking

**Update History** (last 100 updates):
```json
{
  "timestamp": "2026-01-17T14:15:00",
  "block": "macd_crossover",
  "new_dates_count": 3,
  "new_signals_count": 12,
  "updated_total_candles": 17284
}
```

**Benefits**:
- Audit trail of all updates
- Debugging data integrity issues
- Understanding statistics evolution

---

## Testing

### Test Script

```python
# File: scripts/test_signal_statistics_updater.py

from src.strategy_builder.utils.signal_statistics_updater import (
    SignalStatisticsUpdater,
    update_block_statistics,
    is_date_analyzed
)

def test_updater():
    """Test signal statistics updater"""
    
    # Initialize
    updater = SignalStatisticsUpdater()
    
    # Get summary
    summary = updater.get_statistics_summary()
    print(f"Current state: {summary}")
    
    # Test block
    block_name = "macd_crossover"
    
    # Check analyzed dates
    analyzed = updater.get_analyzed_dates(block_name)
    print(f"Analyzed dates for {block_name}: {len(analyzed)}")
    
    # Simulate new data
    new_signal_occurrences = {
        'BULLISH_CROSS': ['2026-01-20', '2026-01-21'],
        'BEARISH_CROSS': ['2026-01-22'],
        'NEUTRAL': ['2026-01-20', '2026-01-21', '2026-01-22']
    }
    
    # Update (should only count truly new dates)
    success = updater.update_statistics(block_name, new_signal_occurrences)
    
    if success:
        print("✅ Update successful!")
        
        # Verify dates were added
        new_analyzed = updater.get_analyzed_dates(block_name)
        print(f"New analyzed dates count: {len(new_analyzed)}")
        print(f"Added: {len(new_analyzed) - len(analyzed)} dates")
    else:
        print("❌ Update failed!")

if __name__ == '__main__':
    test_updater()
```

---

## Best Practices

### ✅ DO

1. **Always use date strings in ISO format** (YYYY-MM-DD)
2. **Update at end of trading period** (not real-time)
3. **Batch updates** for efficiency (one call per block per day)
4. **Check `is_date_analyzed()`** before collecting data
5. **Handle update failures gracefully** (log and continue)

### ❌ DON'T

1. **Don't update same date twice** (updater prevents this, but avoid in code)
2. **Don't modify JSON files manually** (use updater methods)
3. **Don't delete analyzed_dates.json** (will lose tracking)
4. **Don't update during active trading** (wait for day end)
5. **Don't ignore return value** (False = failure, investigate)

---

## Troubleshooting

### Issue: "All dates already processed"

**Cause**: Strategy ran on dates already in `analyzed_dates.json`

**Solution**: This is expected behavior - statistics are already up-to-date

### Issue: Update returns False

**Causes**:
1. Statistics file not found
2. Block not in statistics
3. File permissions issue
4. JSON corruption

**Solution**:
```python
# Check file exists
from pathlib import Path
stats_file = Path('data/catalog/signal_occurrence_statistics.json')
print(f"Exists: {stats_file.exists()}")

# Check block exists
with open(stats_file) as f:
    stats = json.load(f)
    print(f"Blocks: {list(stats['blocks'].keys())}")

# Check permissions
print(f"Writable: {os.access(stats_file, os.W_OK)}")
```

### Issue: Percentages don't add to 100%

**Cause**: Multiple signals can occur on same candle

**Explanation**: This is correct behavior! A candle can produce:
- BULLISH signal
- DIVERGENCE signal  
- BREAKOUT signal

All three are counted, so percentages sum > 100%

### Issue: Statistics file corrupted

**Solution**:
```bash
# Restore from backup
cd data/catalog
cp signal_occurrence_statistics.backup signal_occurrence_statistics.json

# Or regenerate from scratch
python scripts/test_all_building_blocks.py --days 180
```

---

## Future Enhancements

### Planned Features

1. **Per-timeframe statistics** - Separate counts for 15m, 1h, 4h, 1d
2. **Market condition filters** - Bull vs bear market statistics
3. **Seasonal patterns** - Day of week, month statistics
4. **Performance correlation** - Link signal occurrence to strategy performance
5. **Anomaly detection** - Alert when signal frequency changes significantly

### Integration Wishlist

1. **Auto-update from live trading** - Seamless end-of-day updates
2. **Dashboard visualization** - Real-time statistics charts
3. **Comparison tool** - Compare signal frequencies across timeframes
4. **Export functionality** - CSV export for external analysis
5. **API endpoint** - REST API for statistics queries

---

## Summary

The Signal Statistics Updater ensures accurate, up-to-date occurrence counts by:

✅ **Preventing double-counting** with date tracking  
✅ **Atomic updates** with backups  
✅ **Thread-safe** for concurrent runs  
✅ **Simple API** for easy integration  
✅ **Metadata tracking** for audit trail  

**Integration**: Add one `update_block_statistics()` call after each strategy run on new dates.

**Maintenance**: Zero maintenance required - fully automatic with safeguards.

---

**Author**: Strategy Builder Team  
**Date**: 2026-01-17  
**Version**: 1.0  
**Status**: Production-Ready ✅
