# Phase 4: Daily Three-Hits Implementation - Task Handoff

**Date:** December 28, 2025  
**Status:** READY FOR IMPLEMENTATION  
**Session:** New task required

---

## Context

This is a handoff document for implementing the daily three-hits rule feature. The specification is complete and ready for implementation.

---

## What Was Done (Previous Session)

1. ✅ Fixed configuration management issues
   - All 89 TBDConfig parameters properly mapped
   - Config file corrected and validated
   - Walk-forward test runs successfully

2. ✅ Created comprehensive decision tree documentation
   - File: `docs/Layer_TBD/DECISION_TREE_AND_SIGNAL_FLOW.md`
   - Explains all 24 active switches and their usage
   - Shows 4-stage scoring system (35/25/25/15% weights)

3. ✅ Created Phase 4 specification
   - File: `docs/Layer_TBD/PHASE4_DAILY_THREE_HITS_SPEC.md`
   - Complete implementation plan
   - All code changes specified
   - Testing plan included

---

## What Needs To Be Done (This Session)

### Implementation Task: Add Daily Three-Hits Rule

**Goal:** Extend three-hits reversal pattern to detect setups at daily high/low in addition to weekly high/low.

**Why:** 
- Increase trade frequency (6 → 15-20 trades per month)
- Tighter stops (daily range 1-3% vs weekly 5-10%)
- More opportunities during active sessions

**Reference Document:** `docs/Layer_TBD/PHASE4_DAILY_THREE_HITS_SPEC.md`

---

## Implementation Checklist

### Step 1: Add Parameters to TBDConfig (5 new)

File: `src/layers/layer_tbd_method.py`

Add to TBDConfig dataclass after existing three_hits parameters:

```python
# Three Hits (Daily - NEW in v2.1)
three_hits_daily_enabled: bool = True
three_hits_daily_touch_tolerance: float = 0.003  # 0.3% (tighter than weekly 0.5%)
three_hits_daily_min_touch_spacing_hours: int = 1  # 1h (vs weekly 4h)
three_hits_daily_min_wick_ratio: float = 0.55  # 55% (vs weekly 60%)
three_hits_daily_require_confirmation: bool = True
```

### Step 2: Add State Tracking

File: `src/layers/layer_tbd_method.py`

Add to `LayerTBD.__init__()` after existing weekly tracking:

```python
# Daily three-hits tracking (v2.1)
self.daily_high_touches = 0
self.daily_low_touches = 0
self.daily_touch_times = []  # Separate from weekly touch_times
```

### Step 3: Update `_track_level_touches()`

File: `src/layers/layer_tbd_method.py`

Add daily tracking logic after weekly tracking:

```python
# DAILY touches (NEW v2.1)
if self.daily_high and self.layer_config.three_hits_daily_enabled:
    tolerance_daily = self.layer_config.three_hits_daily_touch_tolerance
    high_diff = abs(candle['high'] - self.daily_high) / self.daily_high
    if high_diff <= tolerance_daily and candle['close'] < candle['high']:
        self.daily_high_touches += 1

if self.daily_low and self.layer_config.three_hits_daily_enabled:
    tolerance_daily = self.layer_config.three_hits_daily_touch_tolerance
    low_diff = abs(candle['low'] - self.daily_low) / self.daily_low
    if low_diff <= tolerance_daily and candle['close'] > candle['low']:
        self.daily_low_touches += 1
```

### Step 4: Update `_update_levels()`

File: `src/layers/layer_tbd_method.py`

Add daily touch counter reset when daily levels reset:

```python
if self.layer_config.enable_daily_hl and self.layer_config.daily_hl_first_hour:
    current_hour = current_time.hour
    if current_hour == self.layer_config.london_session_start.hour:
        self.daily_high = current_candle['high']
        self.daily_low = current_candle['low']
        self.daily_high_touches = 0  # NEW: Reset counter
        self.daily_low_touches = 0   # NEW: Reset counter
        self.daily_touch_times = []  # NEW: Clear history
```

### Step 5: Create `_validate_three_hits_touch_daily()`

File: `src/layers/layer_tbd_method.py`

Add new method (similar to weekly validation but with daily parameters):

```python
def _validate_three_hits_touch_daily(self, data: pd.DataFrame, candle: pd.Series, 
                                     level: float, is_high: bool) -> bool:
    """
    Validate touch quality for DAILY three-hits (v2.1)
    
    Uses daily-specific thresholds:
    - Touch spacing: 1 hour (vs 4 hours weekly)
    - Wick ratio: 55% (vs 60% weekly)
    - Touch tolerance: 0.3% (vs 0.5% weekly)
    """
    # 1. Check wick ratio (55% for daily)
    candle_range = candle['high'] - candle['low']
    if candle_range == 0:
        return False
    
    if is_high:
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        wick_ratio = upper_wick / candle_range
    else:
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        wick_ratio = lower_wick / candle_range
    
    if wick_ratio < self.layer_config.three_hits_daily_min_wick_ratio:
        logger.debug(f"Daily touch rejected: wick_ratio={wick_ratio:.2f}")
        return False
    
    # 2. Check volume escalation (same as weekly)
    if len(data) >= 20:
        avg_volume = data.iloc[-20:-1]['volume'].mean()
        volume_ratio = candle['volume'] / avg_volume if avg_volume > 0 else 1.0
        
        if volume_ratio > self.layer_config.three_hits_max_volume_escalation:
            logger.debug(f"Daily touch rejected: volume_ratio={volume_ratio:.2f}")
            return False
    
    # 3. Check touch spacing (1 hour for daily)
    current_time = candle.name if isinstance(candle.name, pd.Timestamp) else pd.Timestamp.now()
    
    if self.daily_touch_times:
        time_since_last = (current_time - self.daily_touch_times[-1]).total_seconds() / 3600
        if time_since_last < self.layer_config.three_hits_daily_min_touch_spacing_hours:
            logger.debug(f"Daily touch rejected: spacing={time_since_last:.1f}h")
            return False
    
    # 4. Not a strong breakout
    body_size = abs(candle['close'] - candle['open'])
    if body_size > candle_range * 0.7:
        logger.debug("Daily touch rejected: strong breakout body")
        return False
    
    # Record this daily touch
    self.daily_touch_times.append(current_time)
    if len(self.daily_touch_times) > 5:
        self.daily_touch_times = self.daily_touch_times[-5:]
    
    logger.debug(f"Daily touch validated: wick={wick_ratio:.2f}")
    return True
```

### Step 6: Extend `_detect_three_hits_reversal()`

File: `src/layers/layer_tbd_method.py`

Add daily detection after weekly detection:

```python
# DAILY three-hits detection (NEW v2.1)
if self.layer_config.three_hits_daily_enabled:
    # Check daily high
    if self.daily_high_touches >= 3:
        if self._is_touching_level(current_candle, self.daily_high, is_high=True):
            if self._validate_three_hits_touch_daily(data, current_candle, self.daily_high, is_high=True):
                # Create pending or immediate pattern
                if self.layer_config.three_hits_daily_require_confirmation:
                    # Store pending (similar to weekly logic)
                    ...
                else:
                    return self._create_three_hits_pattern(
                        'short', 'daily_high', self.daily_high,
                        current_price, data, self.daily_high_touches
                    )
    
    # Check daily low
    if self.daily_low_touches >= 3:
        if self._is_touching_level(current_candle, self.daily_low, is_high=False):
            if self._validate_three_hits_touch_daily(data, current_candle, self.daily_low, is_high=False):
                if self.layer_config.three_hits_daily_require_confirmation:
                    # Store pending
                    ...
                else:
                    return self._create_three_hits_pattern(
                        'long', 'daily_low', self.daily_low,
                        current_price, data, self.daily_low_touches
                    )
```

### Step 7: Update `_create_three_hits_pattern()`

File: `src/layers/layer_tbd_method.py`

Add daily timeframe handling:

```python
def _create_three_hits_pattern(self, direction, level, level_price, current_price, data, touches):
    """Create three hits pattern (weekly or daily)"""
    
    # Determine timeframe and range
    if level in ['weekly_high', 'weekly_low']:
        timeframe = "Weekly"
        range_height = self.weekly_high - self.weekly_low
    elif level in ['daily_high', 'daily_low']:  # NEW
        timeframe = "Daily"
        range_height = self.daily_high - self.daily_low
    else:
        timeframe = "Unknown"
        range_height = 0
    
    # ... rest of method ...
    
    return PatternData(
        pattern_type=PatternType.THREE_HITS,
        timeframe=timeframe,  # "Weekly" or "Daily"
        # ...
        metadata={
            'level': level,
            'timeframe': timeframe,  # Add to metadata
            'touches': touches
        }
    )
```

### Step 8: Update Config File

File: `config/strategies/layer_tbd_only.py`

Add after existing three_hits parameters:

```python
# Three Hits (Weekly - existing)
'three_hits_touch_tolerance': 0.005,
'three_hits_min_candles_between': 4,
'three_hits_require_confirmation': True,
'three_hits_confirmation_timeout_bars': 2,
'three_hits_min_wick_ratio': 0.6,
'three_hits_max_volume_escalation': 1.2,
'three_hits_min_touch_spacing_hours': 4,

# Three Hits (Daily - NEW v2.1)
'three_hits_daily_enabled': True,
'three_hits_daily_touch_tolerance': 0.003,
'three_hits_daily_min_touch_spacing_hours': 1,
'three_hits_daily_min_wick_ratio': 0.55,
'three_hits_daily_require_confirmation': True,
```

### Step 9: Create Unit Tests

File: `tests/test_layer_tbd_daily_three_hits.py` (NEW FILE)

```python
"""
Unit tests for daily three-hits rule feature

Tests:
1. Daily level tracking and reset at London open
2. Touch counting with 0.3% tolerance
3. 1-hour spacing validation
4. Both weekly and daily can trigger
5. Proper timeframe labeling in patterns
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.layers.layer_tbd_method import LayerTBD, TBDConfig

def test_daily_touch_counter_resets_at_london_open():
    """Test that daily_high_touches resets at London open (08:00 UTC)"""
    # Create config with daily enabled
    config = TBDConfig(three_hits_daily_enabled=True)
    layer = LayerTBD(config)
    
    # Create data with touches building up
    # Then cross London open boundary
    # Assert counters reset

def test_daily_touch_tolerance():
    """Test 0.3% tolerance for daily (vs 0.5% weekly)"""
    # Test that 0.3% touch is detected
    # Test that 0.4% touch is NOT detected

def test_daily_touch_spacing_1_hour():
    """Test 1-hour minimum spacing for daily touches"""
    # Test that touches 30min apart are rejected
    # Test that touches 1h+ apart are accepted

def test_both_weekly_and_daily_can_trigger():
    """Test that both weekly and daily three-hits can be active"""
    # Set up scenario where both have 3 touches
    # Verify both patterns can be detected

def test_daily_pattern_metadata():
    """Test that daily patterns have correct timeframe label"""
    # Generate daily three-hits pattern
    # Assert metadata['timeframe'] == 'Daily'
    # Assert pattern uses daily range for targets
```

### Step 10: Run Tests

```bash
# Unit tests
pytest tests/test_layer_tbd_daily_three_hits.py -v

# Integration test (walk-forward)
python3 scripts/layer_testing/walk_forward_tbd.py --preset quick

# Analyze results
python3 scripts/layer_testing/analyze_trades_detailed.py data/reports/walk_forward_trades.json
```

---

## Expected Results

### Before (Weekly Only - Current)
```
Three-hits trades: 6
Pattern breakdown: All weekly
Average hold: 12-24 hours
```

### After (Weekly + Daily - Target)
```
Three-hits trades: 15-20
Pattern breakdown:
  - Weekly: 6-8 trades
  - Daily: 9-12 trades
Average hold: 
  - Weekly: 12-24 hours
  - Daily: 4-8 hours
```

---

## Success Criteria

1. ✅ All unit tests pass
2. ✅ Walk-forward test runs without errors
3. ✅ Daily three-hits patterns detected in results
4. ✅ Both weekly and daily can trigger in same run
5. ✅ Metadata correctly labels timeframe
6. ✅ Trade count increases significantly
7. ✅ Win rate remains similar (~40-50%)

---

## Files to Modify

1. `src/layers/layer_tbd_method.py` - Core implementation
2. `config/strategies/layer_tbd_only.py` - Add parameters
3. `tests/test_layer_tbd_daily_three_hits.py` - NEW unit tests
4. `docs/Layer_TBD/DECISION_TREE_AND_SIGNAL_FLOW.md` - Update docs

---

## Reference Documents

- Specification: `docs/Layer_TBD/PHASE4_DAILY_THREE_HITS_SPEC.md`
- Decision Tree: `docs/Layer_TBD/DECISION_TREE_AND_SIGNAL_FLOW.md`
- Current Config: `config/strategies/layer_tbd_only.py`

---

## Notes

- Daily and weekly three-hits are independent (both can be active)
- Daily uses tighter parameters (0.3% tolerance vs 0.5%)
- Daily resets at London open (08:00 UTC or 07:00 UTC during BST)
- Touch spacing: 1 hour for daily vs 4 hours for weekly
- Both use same confirmation logic (wait for price to move away)

---

**Status:** READY FOR IMPLEMENTATION  
**Estimated Time:** 2-3 hours  
**Priority:** HIGH  
**Risk:** LOW (extends existing proven pattern)

---

**Last Updated:** December 28, 2025, 10:36 AM CET
