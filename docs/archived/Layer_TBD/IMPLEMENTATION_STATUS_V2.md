# Layer TBD v2.0 Implementation Status

**Date**: December 28, 2025  
**Status**: Configuration Complete, Detection Methods Ready for Implementation  
**Priority**: HIGH - 99.85% verification failure requires immediate fix

---

## Completed Work

### ✅ Phase 1: Configuration (COMPLETE)
- **TBDConfig updated** with 24 new parameters
- **Three comprehensive flow documents created**:
  - `THREE_HITS_COMPREHENSIVE_FLOW.md`
  - `MW_PATTERN_COMPREHENSIVE_FLOW.md`
  - `TRAPPING_VOLUME_COMPREHENSIVE_FLOW.md`
- **Implementation changelog created**: `IMPLEMENTATION_CHANGELOG_V2.md`
- **State tracking enhanced**: Added `touch_times`, `touch_volumes`, `pending_three_hits`

### ✅ Root Cause Analysis Complete
- Analyzed 30 sample trades from failed verification
- Identified 3 critical issues:
  1. **THREE_HITS**: Entry too early (no confirmation bar)
  2. **M/W**: Stopped on retest (need retest handling)
  3. **TRAPPING_VOLUME**: False traps (need strict validation)

---

## Next Steps (Implementation Required)

### 🔄 Priority 1: THREE_HITS Detection Method
**File**: `src/layers/layer_tbd_method.py`  
**Method**: `_detect_three_hits_reversal()`  
**Status**: Ready to implement (code examples in flow doc)

**Required Changes**:
```python
# 1. Add touch validation
def _validate_touch(candle, level):
    # Check wick ratio (60% minimum)
    # Check volume escalation (max 1.2x)
    # Check spacing (4 hours minimum)
    # Return bool

# 2. Add confirmation logic
def _check_three_hits_confirmation(current_candle, pending_setup):
    # Wait 1-2 bars for confirmation
    # Verify price moves away from level
    # Validate with volume
    # Return confirmed_signal or None

# 3. Update pattern invalidation
def _should_invalidate_three_hits(trade, current_price):
    # Don't invalidate if:
    # - Trade in profit AND past TP1
    # - Close to TP2/TP3
    # Return bool
```

**Expected Impact**:
- Win Rate: 41% → 55%+
- TP Hit Rate: 5.9% → 30%+
- Stop Hit Rate: 41.2% → 20-25%

---

### 🔄 Priority 2: M/W Pattern Methods
**File**: `src/layers/layer_tbd_method.py`  
**Methods**: `_detect_m_pattern()`, `_detect_w_pattern()`  
**Status**: Ready to implement (code examples in flow doc)

**Required Changes**:
```python
# 1. Track pending patterns
self.pending_mw_patterns = []  # Store patterns awaiting retest

# 2. Retest handling
def _detect_mw_retest(data, pending_pattern):
    # Wait for retest within 20 bars
    # Enter on retest rejection (better entry!)
    # Better R:R, fewer stop-outs

# 3. Multi-timeframe scanning
def _scan_mw_multi_tf(data_15m, data_1h, data_4h):
    # Scan all three timeframes
    # Prefer higher TF patterns
    # Cross-validate across TFs

# 4. Enhanced volume validation
def _validate_mw_volume_profile(pattern):
    # Check peak2 < peak1 (distribution)
    # Check trough2 > trough1 (accumulation)
    # Bounds: 0.8x - 3x average
```

**Expected Impact**:
- Frequency: 13.3% → 30%+ (2.5x increase!)
- Win Rate: Maintain 65-70%
- Better entries: +30% R:R improvement

---

### 🔄 Priority 3: TRAPPING_VOLUME Method
**File**: `src/layers/layer_tbd_method.py`  
**Method**: `_detect_trapping_volume()`  
**Status**: Ready to implement (code examples in flow doc)

**Required Changes**:
```python
# 1. Enhanced validation (11 checks vs 2)
def _validate_trap_candle(candle, avg_volume):
    # Wick >= 60% (was 50%)
    # Volume: 2-5x range (was 1.5x+)
    # Body <= 30%
    # Close position check
    # Return bool, validation_score

# 2. Level proximity check
def _find_nearby_support_resistance(data, price):
    # Identify S/R within 1%
    # Return level, distance

# 3. Trend context validation
def _check_trap_trend_context(data, direction):
    # Verify trap is against trend
    # Bearish trap in uptrend (bullish reversal)
    # Bullish trap in downtrend (bearish reversal)

# 4. Confirmation requirement
def _check_trap_confirmation(current_candle, trap_setup):
    # Wait 1 bar for confirmation
    # Price moves away from trap level
    # Return confirmed_signal or None

# 5. Pattern-specific exits
# - Tighter stops (0.5x ATR vs 1.5x)
# - Time limit (4 hours max - SCALP!)
# - Exit if price returns to trap level
```

**Expected Impact**:
- Win Rate: 37.5% → 55%+
- TP Hit Rate: 0% → 20-25%
- Stop Hit Rate: 50% → 25-30%

---

## Implementation Guide

### Step 1: Read Flow Documents
```bash
# Priority order
cat docs/Layer_TBD/THREE_HITS_COMPREHENSIVE_FLOW.md
cat docs/Layer_TBD/MW_PATTERN_COMPREHENSIVE_FLOW.md
cat docs/Layer_TBD/TRAPPING_VOLUME_COMPREHENSIVE_FLOW.md
```

### Step 2: Implement Detection Methods
Each flow document contains:
- Complete stage-by-stage logic
- Ready-to-implement code examples
- Validation thresholds
- Expected performance
- Common failure modes

### Step 3: Update Trade Monitoring
**File**: `src/backtesting/backtest_engine_tbd.py`  
- Implement pattern-specific exit rules
- Add time-based exits for traps (4 hours)
- Improve pattern invalidation logic

### Step 4: Test
```bash
# Run walk-forward test
python3 scripts/layer_testing/walk_forward_tbd.py --preset standard

# Verify trades
python3 scripts/layer_testing/verify_walkforward_tbd.py \
    --trades data/reports/walk_forward_trades.csv

# Expected: 0.15% → 60%+ pass rate
```

---

## Configuration Reference

### New Parameters Added (24 total)

#### THREE_HITS (7 new params)
```python
three_hits_require_confirmation: bool = True  # CRITICAL!
three_hits_confirmation_timeout_bars: int = 2
three_hits_min_wick_ratio: float = 0.6
three_hits_max_volume_escalation: float = 1.2
three_hits_min_touch_spacing_hours: int = 4
```

#### M/W PATTERNS (9 new params)
```python
mw_pattern_length_min: int = 8  # Was 10
mw_pattern_length_max: int = 80  # Was 50
mw_peak_tolerance: float = 0.25  # Was 0.15
mw_enable_retest_entry: bool = True
mw_retest_window_bars: int = 20
mw_enable_multi_tf_scan: bool = True
mw_min_pattern_depth: float = 0.03
mw_max_pattern_depth: float = 0.25
mw_volume_breakout_min: float = 0.8
mw_volume_breakout_max: float = 3.0
```

#### TRAPPING_VOLUME (13 new params)
```python
trap_wick_threshold: float = 0.6  # Was 0.5
trap_volume_multiplier_min: float = 2.0  # Was 1.5
trap_volume_multiplier_max: float = 5.0
trap_body_max_ratio: float = 0.3
trap_close_position_min: float = 0.6
trap_close_position_max: float = 0.4
trap_require_confirmation: bool = True  # CRITICAL!
trap_require_level_proximity: bool = True
trap_require_trend_context: bool = True
trap_max_hold_hours: int = 4  # SCALP!
trap_tight_stop_multiplier: float = 0.5  # Was 1.5
trap_exit_at_level_return: bool = True
```

---

## Testing Strategy

### Phase 1: Unit Tests
Test each detection method with known patterns:
```python
def test_three_hits_confirmation():
    # Test that entry waits for confirmation
    # Test that touch validation works
    # Test pattern invalidation logic

def test_mw_retest_handling():
    # Test retest detection
    # Test that entry waits for retest rejection
    # Test multi-TF scanning

def test_trap_strict_validation():
    # Test all 11 validation checks
    # Test confirmation requirement
    # Test time-based exits
```

### Phase 2: Walk-Forward Validation
Compare before/after on same 30-day period:
- **Before**: 0.15% pass rate (5 of 3357 trades)
- **After**: Target 60%+ pass rate

### Phase 3: Live Paper Trading
Deploy to paper account:
- Monitor 7-14 days
- Track metrics by pattern type
- Validate all logic working correctly

---

## Expected System Performance

| Metric | Before | After (Target) | Improvement |
|--------|--------|----------------|-------------|
| Overall Win Rate | ~40% | 50-55%+ | +25-37% |
| Verification Pass | 0.15% | 60%+ | +400x |
| TP Hit Rate | ~6% | 25-30%+ | +4-5x |
| Stop Hit Rate | ~41% | 20-25% | -40% |
| Exit Before TP | ~59% | 20-25% | -58% |

### By Pattern Type

| Pattern | Before Win | After Win | Notes |
|---------|-----------|-----------|-------|
| THREE_HITS | 41.2% | 55%+ | Confirmation is THE fix |
| M/W | 66.7% | 65-70% | Maintain quality, 2.5x frequency |
| TRAPPING_VOLUME | 37.5% | 55%+ | Strict validation + fast exits |

---

## Critical Success Factors

### 1. THREE_HITS Confirmation (Highest Priority)
- **Problem**: 90% of "exit before TP" due to early entry
- **Solution**: Wait 1-2 bars for confirmation
- **Impact**: Transforms 41% → 55%+ win rate

### 2. M/W Retest Handling
- **Problem**: Stopped out on normal retest
- **Solution**: Wait for retest rejection (better entry)
- **Impact**: +30% R:R improvement, 2.5x more patterns

### 3. TRAPPING_VOLUME Strict Validation
- **Problem**: Too many false traps (62.5% loss rate)
- **Solution**: 11 validation checks (was 2)
- **Impact**: 37.5% → 55%+ win rate

---

## Files Modified/Created

### Modified
- ✅ `src/layers/layer_tbd_method.py` - TBDConfig updated with 24 new params
- ✅ `src/layers/layer_tbd_method.py` - State tracking enhanced

### Created
- ✅ `docs/Layer_TBD/THREE_HITS_COMPREHENSIVE_FLOW.md`
- ✅ `docs/Layer_TBD/MW_PATTERN_COMPREHENSIVE_FLOW.md`
- ✅ `docs/Layer_TBD/TRAPPING_VOLUME_COMPREHENSIVE_FLOW.md`
- ✅ `docs/Layer_TBD/IMPLEMENTATION_CHANGELOG_V2.md`
- ✅ `docs/Layer_TBD/IMPLEMENTATION_STATUS_V2.md` (this file)

### Needs Implementation
- 🔄 `src/layers/layer_tbd_method.py` - Detection methods (THREE_HITS, M/W, TRAP)
- 🔄 `src/backtesting/backtest_engine_tbd.py` - Trade monitoring enhancements

---

## Next Session Checklist

When continuing this work:

1. ✅ Read `IMPLEMENTATION_STATUS_V2.md` (this file)
2. ✅ Read relevant flow document for pattern being implemented
3. ✅ Implement detection method using code examples from flow doc
4. ✅ Test detection method with known pattern examples
5. ✅ Update trade monitoring logic if needed
6. ✅ Run walk-forward test
7. ✅ Verify improvement in pass rate
8. ✅ Move to next priority pattern

---

## Contact & Questions

For implementation questions:
- Review flow documents - they contain complete working examples
- Check `IMPLEMENTATION_CHANGELOG_V2.md` for before/after config
- Reference `TRADE_FLOW_ANALYSIS_30_SAMPLES.md` for real failure examples

**Status**: Ready for implementation 🎯  
**Next Action**: Implement THREE_HITS confirmation logic (highest priority)

---

*Last Updated: December 28, 2025*  
*Version: 2.0.1*  
*Context Window: 84% (need new task)*
