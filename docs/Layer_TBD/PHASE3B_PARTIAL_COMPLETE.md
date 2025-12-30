# Phase 3B: Higher Timeframe Pattern Detection - PARTIAL COMPLETE

**Date**: December 28, 2025, 8:22 AM  
**Status**: Phase 3B - 50% Complete (M-Pattern Done, W-Pattern Needed)  
**Next**: Complete W-pattern HTF integration, then Phases 3C-3E

---

## ✅ COMPLETED WORK

### 1. Higher Timeframe Infrastructure (Phase 3A) - 100% Done
- Added `data_1h` and `data_4h` storage to LayerTBD
- Created `set_higher_timeframe_data()` method
- Version updated to 2.1.0

### 2. HTF Pattern Detection Methods (Phase 3B) - 100% Done
- Created `_detect_pattern_on_higher_tf()` - main detection coordinator
- Created `_detect_htf_m_pattern()` - simplified M-pattern detection on 1H/4H
- Created `_detect_htf_w_pattern()` - simplified W-pattern detection on 1H/4H
- Both methods check 1H first, then 4H if available
- Return pattern measurements without full validation

### 3. M-Pattern HTF Integration (Phase 3B) - 100% Done
- Modified `_detect_m_pattern()` to call HTF detection
- When HTF pattern found:
  - Uses HTF pattern_height for targets
  - Uses HTF ATR for wider stops (2.0x vs 1.5x)
  - Boosts confidence by 20% (1H) or 30% (4H)
  - Sets `using_htf_targets=True` in metadata
  - Logs info message with 🎯 emoji
- Falls back to 15m targets if no HTF pattern

### 4. Metadata Tracking
- Added `using_htf_targets` flag to pending_mw_patterns
- Added `htf_timeframe` ('1H' or '4H') to pending_mw_patterns
- This ensures retest entries also use HTF measurements

---

## 🔄 IN PROGRESS: W-Pattern HTF Integration (Phase 3B) - 0% Done

### What Needs to Be Done

The W-pattern method (`_detect_w_pattern()`) needs the **EXACT SAME** integration as M-pattern:

1. **Call HTF Detection** (after volume confirmation check):
```python
# PHASE 3B: Check for pattern on higher timeframe
htf_pattern = self._detect_pattern_on_higher_tf(
    PatternType.W_PATTERN,
    current_price
)
```

2. **Use HTF Measurements** (if pattern found):
```python
if htf_pattern:
    logger.info(f"🎯 Using {htf_pattern['timeframe']} targets for W-pattern (better R:R)")
    pattern_height = htf_pattern['pattern_height']
    trough1_price = htf_pattern['peak1']
    trough2_price = htf_pattern['peak2']
    neckline = htf_pattern['neckline']
    atr = htf_pattern['atr']
    confidence_adjustment = htf_pattern['confidence_boost']
    
    # Wider stop using HTF ATR
    stop_loss = min(trough1_price, trough2_price) - (atr * 2.0)
    
    # Farther targets using HTF pattern height
    tp1 = neckline + (pattern_height * self.layer_config.tp1_multiplier)
    tp2 = neckline + (pattern_height * self.layer_config.tp2_multiplier)
    tp3 = neckline + (pattern_height * self.layer_config.tp3_multiplier)
    
    using_htf_targets = True
    htf_timeframe = htf_pattern['timeframe']
else:
    # Use 15m measurements (existing code)
    ...
```

3. **Update Pattern Creation**:
```python
pattern = PatternData(
    ...
    metadata={
        ...
        'using_htf_targets': using_htf_targets,
        'htf_timeframe': htf_timeframe
    }
)
```

### Location
File: `src/layers/layer_tbd_method.py`  
Method: `_detect_w_pattern()`  
Line: ~1250 (after volume confirmation check, before entry_price assignment)

---

## 📝 REMAINING WORK (Phases 3C-3E)

### Phase 3C: Trailing Stops in Backtest Engine

**File**: `src/backtesting/backtest_engine_tbd.py`  
**Method**: `_check_exits()`  
**Location**: After stop loss check, before TP checks

```python
def _check_exits(self, current_candle: pd.Series) -> None:
    # ... existing stop loss check ...
    
    # NEW: Trailing stop for HTF patterns (Phase 3C)
    if self.position and self.position.metadata.get('using_htf_targets', False):
        current_price = float(current_candle['close'])
        
        # Calculate profit and distance to TP1
        if self.position.direction == 'long':
            profit = (current_price - self.position.entry_price) * self.position.qty_remaining
            distance_to_tp1 = self.position.take_profit_1 - current_price
        else:  # short
            profit = (self.position.entry_price - current_price) * self.position.qty_remaining
            distance_to_tp1 = current_price - self.position.take_profit_1
        
        # Activate trailing stop at 50% to TP1
        if profit > 0 and distance_to_tp1 < (abs(self.position.take_profit_1 - self.position.entry_price) * 0.5):
            trailing_stop_distance = profit * 0.5  # Trail at 50% of profit
            
            if self.position.direction == 'long':
                trailing_stop = self.position.entry_price + trailing_stop_distance
                if current_price < trailing_stop:
                    self._close_position_full(current_candle, 'trailing_stop', trailing_stop)
                    return
            else:  # short
                trailing_stop = self.position.entry_price - trailing_stop_distance
                if current_price > trailing_stop:
                    self._close_position_full(current_candle, 'trailing_stop', trailing_stop)
                    return
    
    # ... existing TP checks ...
```

### Phase 3D: Fix Pattern Change Exits

**File**: `src/backtesting/backtest_engine_tbd.py`  
**Method**: `_process_signal()`

Add new method:
```python
def _should_exit_on_pattern_change(self, new_signal, current_candle) -> bool:
    """Only exit if opposite direction AND not profitable"""
    if not self.position:
        return False
    
    # Check if opposite direction
    opposite = (
        (self.position.direction == 'long' and new_signal.direction == 'short') or
        (self.position.direction == 'short' and new_signal.direction == 'long')
    )
    
    if not opposite:
        return False  # Same direction, keep position
    
    # Calculate current P&L
    current_price = float(current_candle['close'])
    if self.position.direction == 'long':
        pnl = (current_price - self.position.entry_price) * self.position.qty_remaining
    else:
        pnl = (self.position.entry_price - current_price) * self.position.qty_remaining
    
    # If profitable, keep position (let trailing stop handle it)
    if pnl > 0:
        return False
    
    # Opposite direction + not profitable = exit
    return True
```

Modify `_process_signal()`:
```python
if current_pattern != self.active_pattern:
    if self.position:
        # NEW: Check if should exit
        if self._should_exit_on_pattern_change(signal, current_candle):
            self._close_position_full(...)
        else:
            logger.debug("Keeping position (profitable, not exiting on pattern change)")
            return  # Keep position, don't open new one
    
    # Open new position if no position or exited
    self._open_position(signal, current_candle)
    self.active_pattern = current_pattern
```

### Phase 3E: Testing & Validation

1. **Update walk-forward test** to load and set HTF data:
```python
# In scripts/layer_testing/walk_forward_tbd.py
data_15m = load_data('15m')
data_1h = resample_to_1h(data_15m)  # Need to add this function
data_4h = resample_to_4h(data_15m)  # Optional

layer_tbd.set_higher_timeframe_data(data_1h, data_4h)
```

2. **Run tests** and verify metrics:
   - Win Rate: 43.8% → 55%+
   - Total Return: -8.98% → +75-300%
   - TP1 Exits: -$50 avg → +$10-20
   - Avg Hold Time: 1.9h → 6h+

3. **Create success summary** document

---

## 🎯 KEY INSIGHTS

### Why This Fix Works

1. **Proper R:R**: 1H pattern height is ~4-6x larger than 15m
   - 15m: TP1 at $50 away, Stop at $100 away (R:R <1:1)
   - 1H: TP1 at $300 away, Stop at $200 away (R:R 1.5:1) ✅

2. **Room to Breathe**: 1H ATR is ~3x larger than 15m ATR
   - 15m stop: $50 above peaks (gets hit by noise)
   - 1H stop: $200 above peaks (survives volatility) ✅

3. **Let Winners Run**: Farther TP1 means more profit potential
   - 15m TP1: Hit in 30min for $10 profit (if lucky)
   - 1H TP1: Hit in 2-4h for $50-100 profit ✅

### Expected Before/After

**Current (15m only)**:
```
Entry: $43,000
Stop: $43,100 (15m peaks + $50)
TP1: $42,950 (15m height * 0.5 = $50)
Risk: $100, Reward: $50
R:R = 0.5:1 ❌
Result: Stop hit OR TP1 for loss
```

**After HTF (1H targets)**:
```
Entry: $43,000
Stop: $43,200 (1H peaks + $200) 
TP1: $42,700 (1H height * 0.5 = $300)
Risk: $200, Reward: $300
R:R = 1.5:1 ✅
Result: TP1 profitable, wider stop survives
```

---

## 📊 COMPLETION STATUS

| Phase | Task | Status | %  |
|-------|------|--------|----|
| 3A | Multi-TF Infrastructure | ✅ Done | 100% |
| 3B | HTF Detection Methods | ✅ Done | 100% |
| 3B | M-Pattern Integration | ✅ Done | 100% |
| 3B | W-Pattern Integration | 🔄 Next | 0% |
| 3C | Trailing Stops | 📝 Todo | 0% |
| 3D | Pattern Change Fix | 📝 Todo | 0% |
| 3E | Testing & Validation | 📝 Todo | 0% |

**Overall Progress**: 40% Complete

---

## 🚀 NEXT SESSION ACTIONS

1. Complete W-pattern HTF integration (5 min)
2. Add trailing stops to backtest engine (10 min)
3. Fix pattern change exit logic (10 min)
4. Update walk-forward test with HTF data loading (10 min)
5. Run tests and validate improvements (15 min)
6. Document success (5 min)

**Estimated Time**: 55 minutes to completion

---

*Last Updated: December 28, 2025, 8:22 AM*  
*Document: PHASE3B_PARTIAL_COMPLETE.md*  
*Next Step: Complete W-pattern HTF integration*
