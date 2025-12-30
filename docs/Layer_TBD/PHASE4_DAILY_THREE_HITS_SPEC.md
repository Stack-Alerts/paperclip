# Phase 4: Daily Three-Hits Rule Implementation

**Date:** December 28, 2025  
**Status:** SPECIFICATION  
**Priority:** HIGH - More trading opportunities with tighter timeframes

---

## Overview

Add daily timeframe support for the three-hits rule pattern. Currently, three-hits only detects reversals at weekly high/low levels. Adding daily support will:

- Increase trade frequency (more opportunities per day)
- Provide tighter stop losses (daily levels closer than weekly)
- Better risk:reward ratios on intraday moves
- Capture shorter-term institutional behavior

---

## Current Implementation (Weekly Only)

### Existing Parameters
```python
# In TBDConfig
three_hits_touch_tolerance: float = 0.005  # 0.5%
three_hits_min_candles_between: int = 4
three_hits_require_confirmation: bool = True
three_hits_confirmation_timeout_bars: int = 2
three_hits_min_wick_ratio: float = 0.6  # 60% rejection wick
three_hits_max_volume_escalation: float = 1.2  # Max 1.2x volume
three_hits_min_touch_spacing_hours: int = 4  # Min hours between touches ← WEEKLY SPECIFIC!
```

### Existing State Tracking
```python
# In LayerTBD.__init__()
self.weekly_high = None
self.weekly_low = None
self.weekly_high_touches = 0
self.weekly_low_touches = 0
```

### Current Logic
```python
def _detect_three_hits_reversal(self, data, current_price):
    # Only checks weekly_high_touches and weekly_low_touches
    if self.weekly_high_touches >= 3:
        # Validate and create setup...
    if self.weekly_low_touches >= 3:
        # Validate and create setup...
```

---

## Required Changes

### 1. Add Daily-Specific Parameters to TBDConfig

```python
# NEW DAILY THREE-HITS PARAMETERS
three_hits_daily_enabled: bool = True  # Enable daily three-hits
three_hits_daily_touch_tolerance: float = 0.003  # Tighter for daily (0.3% vs 0.5%)
three_hits_daily_min_touch_spacing_hours: int = 1  # 1 hour vs 4 hours for weekly
three_hits_daily_min_wick_ratio: float = 0.55  # Slightly looser (55% vs 60%)
three_hits_daily_require_confirmation: bool = True  # Same as weekly
```

**Rationale for different parameters:**
- **Touch tolerance:** 0.3% for daily (tighter, more precise level)
- **Touch spacing:** 1 hour minimum (daily moves faster than weekly)
- **Wick ratio:** 55% (slightly looser to catch more setups)

### 2. Add Daily State Tracking

```python
# In LayerTBD.__init__()
self.daily_high_touches = 0  # NEW
self.daily_low_touches = 0   # NEW
```

### 3. Update Level Tracking

```python
def _track_level_touches(self, candle: pd.Series) -> None:
    """Track touches to weekly AND daily levels"""
    tolerance_weekly = self.layer_config.three_hits_touch_tolerance
    tolerance_daily = self.layer_config.three_hits_daily_touch_tolerance
    
    # WEEKLY touches (existing)
    if self.weekly_high:
        high_diff = abs(candle['high'] - self.weekly_high) / self.weekly_high
        if high_diff <= tolerance_weekly and candle['close'] < candle['high']:
            self.weekly_high_touches += 1
    
    if self.weekly_low:
        low_diff = abs(candle['low'] - self.weekly_low) / self.weekly_low
        if low_diff <= tolerance_weekly and candle['close'] > candle['low']:
            self.weekly_low_touches += 1
    
    # DAILY touches (NEW)
    if self.daily_high and self.layer_config.three_hits_daily_enabled:
        high_diff = abs(candle['high'] - self.daily_high) / self.daily_high
        if high_diff <= tolerance_daily and candle['close'] < candle['high']:
            self.daily_high_touches += 1
    
    if self.daily_low and self.layer_config.three_hits_daily_enabled:
        low_diff = abs(candle['low'] - self.daily_low) / self.daily_low
        if low_diff <= tolerance_daily and candle['close'] > candle['low']:
            self.daily_low_touches += 1
```

### 4. Update Daily Level Reset Logic

```python
def _update_levels(self, data: pd.DataFrame) -> None:
    """Update weekly, daily, and session levels"""
    # ... existing weekly code ...
    
    # DAILY level tracking (NEW RESET LOGIC)
    if self.layer_config.enable_daily_hl and self.layer_config.daily_hl_first_hour:
        current_hour = current_time.hour
        
        # Reset at London open
        if current_hour == self.layer_config.london_session_start.hour:
            self.daily_high = current_candle['high']
            self.daily_low = current_candle['low']
            self.daily_high_touches = 0  # NEW: Reset touch counter
            self.daily_low_touches = 0   # NEW: Reset touch counter
        else:
            # Update highs/lows
            if self.daily_high is None or current_candle['high'] > self.daily_high:
                self.daily_high = current_candle['high']
            if self.daily_low is None or current_candle['low'] < self.daily_low:
                self.daily_low = current_candle['low']
```

### 5. Extend Three-Hits Detection

```python
def _detect_three_hits_reversal(self, data, current_price):
    """Detect three hits at WEEKLY or DAILY levels"""
    
    # ... existing pending confirmation check ...
    
    # WEEKLY three-hits (existing code)
    if self.weekly_high_touches >= 3:
        if self._is_touching_level_weekly(current_candle, self.weekly_high, is_high=True):
            if self._validate_three_hits_touch_weekly(data, current_candle, ...):
                # Create setup with 'weekly' timeframe
                ...
    
    if self.weekly_low_touches >= 3:
        # ... similar ...
    
    # DAILY three-hits (NEW)
    if self.layer_config.three_hits_daily_enabled:
        if self.daily_high_touches >= 3:
            if self._is_touching_level_daily(current_candle, self.daily_high, is_high=True):
                if self._validate_three_hits_touch_daily(data, current_candle, ...):
                    # Create setup with 'daily' timeframe
                    ...
        
        if self.daily_low_touches >= 3:
            # ... similar ...
```

### 6. Add Daily-Specific Validation

```python
def _validate_three_hits_touch_daily(self, data, candle, level, is_high):
    """
    Validate daily touch with DAILY parameters
    
    Key differences from weekly:
    - Use three_hits_daily_touch_tolerance (0.3% vs 0.5%)
    - Use three_hits_daily_min_touch_spacing_hours (1h vs 4h)
    - Use three_hits_daily_min_wick_ratio (55% vs 60%)
    """
    # 1. Check wick ratio (55% threshold)
    if wick_ratio < self.layer_config.three_hits_daily_min_wick_ratio:
        return False
    
    # 2. Check volume escalation (same as weekly: 1.2x)
    if volume_ratio > self.layer_config.three_hits_max_volume_escalation:
        return False
    
    # 3. Check touch spacing (1 hour minimum vs 4 hours for weekly)
    if self.daily_touch_times:  # Track separately from weekly
        time_since_last = (current_time - self.daily_touch_times[-1]).total_seconds() / 3600
        if time_since_last < self.layer_config.three_hits_daily_min_touch_spacing_hours:
            return False
    
    # 4. Not a strong breakout (same as weekly)
    if body_size > candle_range * 0.7:
        return False
    
    return True
```

### 7. Update Pattern Creation

```python
def _create_three_hits_pattern(self, direction, level, level_price, current_price, data, touches):
    """Create three hits pattern with proper timeframe labeling"""
    
    if level in ['weekly_high', 'weekly_low']:
        timeframe = "Weekly"
        range_height = self.weekly_high - self.weekly_low
    elif level in ['daily_high', 'daily_low']:
        timeframe = "Daily"  # NEW
        range_height = self.daily_high - self.daily_low  # NEW: Use daily range
    
    # ... rest of pattern creation ...
    
    return PatternData(
        pattern_type=PatternType.THREE_HITS,
        timeframe=timeframe,  # "Weekly" or "Daily"
        confidence=0.75,
        # ...
        metadata={
            'level': level,
            'level_price': level_price,
            'touches': touches,
            'timeframe': timeframe  # Add to metadata
        }
    )
```

---

## Configuration File Updates

### Add to config/strategies/layer_tbd_only.py

```python
'layer_tbd_params': {
    # ... existing params ...
    
    # Three Hits (Weekly - existing)
    'three_hits_touch_tolerance': 0.005,
    'three_hits_min_candles_between': 4,
    'three_hits_require_confirmation': True,
    'three_hits_confirmation_timeout_bars': 2,
    'three_hits_min_wick_ratio': 0.6,
    'three_hits_max_volume_escalation': 1.2,
    'three_hits_min_touch_spacing_hours': 4,
    
    # Three Hits (Daily - NEW)
    'three_hits_daily_enabled': True,
    'three_hits_daily_touch_tolerance': 0.003,  # Tighter
    'three_hits_daily_min_touch_spacing_hours': 1,  # 1h vs 4h
    'three_hits_daily_min_wick_ratio': 0.55,  # Slightly looser
    'three_hits_daily_require_confirmation': True,
    
    # ... rest of config ...
}
```

---

## Expected Benefits

### Trade Frequency
- **Current:** 6 three-hits trades in 30-day test (weekly only)
- **Expected:** 15-20 three-hits trades (weekly + daily combined)

### Risk:Reward
- **Daily range typically 1-3%** vs weekly range 5-10%
- Tighter stops → Better R:R for scalping
- More opportunities during London/NY sessions

### Win Rate
- Expected similar win rate (~40-50%)
- But smaller losses due to tighter stops
- Daily levels tested more frequently = more reliable

---

## Testing Plan

1. **Unit Tests**
   - Test daily level tracking resets at London open
   - Test touch counting with 0.3% tolerance
   - Test 1-hour spacing validation
   - Test both weekly and daily can trigger in same run

2. **Integration Test**
   - Run walk-forward with daily enabled
   - Verify both weekly and daily setups detected
   - Check metadata shows correct timeframe

3. **Performance Comparison**
   ```
   python3 scripts/layer_testing/walk_forward_tbd.py --preset standard
   
   Compare:
   - Trade count (should increase)
   - Win rate (should stay similar)
   - Average trade duration (daily should be shorter)
   - P&L per trade (daily should be smaller but more frequent)
   ```

---

## Implementation Checklist

- [ ] Add 5 new daily-specific parameters to TBDConfig
- [ ] Add daily_high_touches and daily_low_touches state tracking
- [ ] Add daily_touch_times list for spacing validation
- [ ] Update _track_level_touches() to track daily touches
- [ ] Update _update_levels() to reset daily touches at London open
- [ ] Create _validate_three_hits_touch_daily() method
- [ ] Create _is_touching_level_daily() method
- [ ] Extend _detect_three_hits_reversal() to check daily levels
- [ ] Update _create_three_hits_pattern() to handle daily timeframe
- [ ] Add new parameters to config/strategies/layer_tbd_only.py
- [ ] Update decision tree documentation
- [ ] Run walk-forward test
- [ ] Analyze results

---

## Expected Output Example

```
Three hits CONFIRMED at daily_high:
  direction=short
  touches=3
  level=$43,250.00
  range=$430 (1% daily range vs 3% weekly)
  stop=$43,280 (tighter!)
  tp1=$43,100 (30% of daily range)
  timeframe=Daily
```

---

## Notes

- Daily and weekly three-hits can both be active simultaneously
- Priority: Check daily first (more frequent), then weekly
- Both use same confirmation logic (wait for price to move away)
- Daily patterns should have shorter max_hold_hours (4h vs 24h)

---

**Status:** Ready for implementation  
**Estimated Effort:** 2-3 hours  
**Dependencies:** None (extends existing three-hits code)
