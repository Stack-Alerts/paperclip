# BUILDING BLOCK EMISSIONS AUDIT REPORT

**Date:** 2026-01-11 19:16:32
**Total Blocks Tested:** 83
**Blocks with Issues:** 83
**Total Mismatches:** 118

## 🚨 EXECUTIVE SUMMARY

❌ **83 BLOCKS HAVE ISSUES**

- **Critical Issues:** 35 (blocks emit undeclared signals)
- **High Priority:** 83 (declared signals never emitted)

**Impact:** These mismatches cause:
- Silent signal filtering bugs (50% signal loss in HOD strategy)
- User confusion (GUI shows signals that never fire)
- Strategy configuration errors
- Confluence calculation issues

---

## 📊 DETAILED FINDINGS

### ❌ adaptive_momentum_oscillator

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_CROSS, BEARISH_DIVERGENCE, BULLISH_CROSS, BULLISH_DIVERGENCE
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_CROSS', 'BEARISH_DIVERGENCE', 'BULLISH_DIVERGENCE', 'BULLISH_CROSS'} from valid_signals OR update analyze() to emit them

### ❌ adr

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_ADR, BELOW_ADR, CALM, NEAR_ADR, VOLATILE, WITHIN_ADR
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NEAR_ADR', 'WITHIN_ADR', 'BELOW_ADR', 'CALM', 'ABOVE_ADR', 'VOLATILE'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NORMAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NORMAL'} to valid_signals in @register_block decorator

### ❌ adx

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH'} from valid_signals OR update analyze() to emit them

### ❌ anchored_vwap

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_ANCHORED_VWAP
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'ABOVE_ANCHORED_VWAP'} from valid_signals OR update analyze() to emit them

### ❌ ascending_triangle

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BULLISH_BREAKOUT, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_BREAKOUT', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ asfx_a2_vwap

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BULLISH_A2
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH_A2'} to valid_signals in @register_block decorator

### ❌ asia_session_50_percent

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH'} from valid_signals OR update analyze() to emit them

### ❌ atr

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** EXTREME_HIGH, EXTREME_LOW, VERY_HIGH, VERY_LOW
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'EXTREME_LOW', 'EXTREME_HIGH', 'VERY_HIGH', 'VERY_LOW'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** STABLE
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'STABLE'} to valid_signals in @register_block decorator

### ❌ balanced_price_range

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH'} from valid_signals OR update analyze() to emit them

### ❌ bollinger_bands

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_REVERSAL, BULLISH_REVERSAL, LOWER_BAND_WALK, LOWER_HALF, MEDIUM_HIGH, MEDIUM_LOW, SQUEEZE_BREAKOUT, SQUEEZE_BREAKOUT_BEAR, SQUEEZE_BREAKOUT_BULL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'SQUEEZE_BREAKOUT_BEAR', 'MEDIUM_HIGH', 'MEDIUM_LOW', 'BULLISH_REVERSAL', 'SQUEEZE_BREAKOUT', 'SQUEEZE_BREAKOUT_BULL', 'LOWER_BAND_WALK', 'LOWER_HALF', 'BEARISH_REVERSAL'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** UPPER_HALF
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'UPPER_HALF'} to valid_signals in @register_block decorator

### ❌ break_of_structure

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BOS, BULLISH_BOS
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BOS', 'BULLISH_BOS'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH', 'BEARISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ breaker_block

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKER, BULLISH_BREAKER
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_BREAKER', 'BEARISH_BREAKER'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH', 'BEARISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ candle_2_close

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH'} from valid_signals OR update analyze() to emit them

### ❌ change_of_character

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_CHOCH, BEARISH_MSS, BULLISH_CHOCH, BULLISH_MSS, HIGH_SWEEP, LOW_SWEEP, UNUSUALLY_SLOW
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_MSS', 'UNUSUALLY_SLOW', 'BEARISH_MSS', 'BEARISH_CHOCH', 'BULLISH_CHOCH', 'LOW_SWEEP', 'HIGH_SWEEP'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BEARISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ cup_and_handle

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BREAKOUT_CONFIRMED, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BREAKOUT_CONFIRMED', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ descending_triangle

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKDOWN, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKDOWN', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ displacement

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_DISPLACEMENT, BEARISH_FVG, BULLISH_DISPLACEMENT, BULLISH_FVG
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_FVG', 'BULLISH_DISPLACEMENT', 'BEARISH_FVG', 'BEARISH_DISPLACEMENT'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NO_DISPLACEMENT
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NO_DISPLACEMENT'} to valid_signals in @register_block decorator

### ❌ double_bottom

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BULLISH_BREAKOUT, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_BREAKOUT', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ double_top

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKDOWN, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKDOWN', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ elliott_wave_count

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** NO_PATTERN
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NO_PATTERN'} from valid_signals OR update analyze() to emit them

### ❌ elliott_wave_oscillator

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_DIVERGENCE, BEARISH_MOMENTUM_WEAKENING, BULLISH_DIVERGENCE
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_MOMENTUM_WEAKENING', 'BEARISH_DIVERGENCE', 'BULLISH_DIVERGENCE'} from valid_signals OR update analyze() to emit them

### ❌ ema_200_trend

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH', 'NEUTRAL'} from valid_signals OR update analyze() to emit them

### ❌ ema_20_50_cross

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** DEATH_CROSS, GOLDEN_CROSS, NO_CROSS
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'GOLDEN_CROSS', 'NO_CROSS', 'DEATH_CROSS'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ ema_20_50_trend

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NEUTRAL'} from valid_signals OR update analyze() to emit them

### ❌ ema_255_vector

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_EMA, BELOW_EMA
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BELOW_EMA', 'ABOVE_EMA'} from valid_signals OR update analyze() to emit them

### ❌ ema_50_vector

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_EMA, BEARISH_BREAK, BELOW_EMA, BULLISH_BREAK, NO_BREAK
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NO_BREAK', 'BEARISH_BREAK', 'BELOW_EMA', 'BULLISH_BREAK', 'ABOVE_EMA'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ ema_55_vector

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_EMA, BELOW_EMA
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BELOW_EMA', 'ABOVE_EMA'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ ema_800_vector

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_EMA, BELOW_EMA
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BELOW_EMA', 'ABOVE_EMA'} from valid_signals OR update analyze() to emit them

### ❌ ema_crossover

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_ALIGNMENT, BULLISH_ALIGNMENT, DEATH_CROSS, GOLDEN_CROSS
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'GOLDEN_CROSS', 'BEARISH_ALIGNMENT', 'DEATH_CROSS', 'BULLISH_ALIGNMENT'} from valid_signals OR update analyze() to emit them

### ❌ fair_value_gap

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_FVG, BULLISH_FVG
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_FVG', 'BULLISH_FVG'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NO_FVG
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NO_FVG'} to valid_signals in @register_block decorator

### ❌ falling_wedge

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BULLISH_BREAKOUT, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_BREAKOUT', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ fibonacci_retracements

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH', 'NEUTRAL'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** AT_FIB_23, AT_FIB_38, AT_FIB_50, BETWEEN_LEVELS
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'AT_FIB_38', 'AT_FIB_23', 'BETWEEN_LEVELS', 'AT_FIB_50'} to valid_signals in @register_block decorator

### ❌ fifty_pct_hod_lod

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** REJECTION_AT_EQ
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'REJECTION_AT_EQ'} from valid_signals OR update analyze() to emit them

### ❌ fifty_pct_intra_hod_lod

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_INTRA_EQ, BELOW_INTRA_EQ, REJECTION_AT_INTRA_EQ
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BELOW_INTRA_EQ', 'ABOVE_INTRA_EQ', 'REJECTION_AT_INTRA_EQ'} from valid_signals OR update analyze() to emit them

### ❌ flag_pattern

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKOUT, BULLISH_BREAKOUT, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKOUT', 'BULLISH_BREAKOUT', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ head_and_shoulders

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** PATTERN_CONFIRMED, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'PATTERN_CONFIRMED', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ hod

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_HOD, AT_HOD, BEARISH, BELOW_HOD, HOD_REJECTION
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH', 'ABOVE_HOD', 'HOD_REJECTION', 'BELOW_HOD', 'AT_HOD'} from valid_signals OR update analyze() to emit them

### ❌ how

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BELOW_HOW, BREAKING_OUT, BREAKOUT_CONFIRMED
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BREAKOUT_CONFIRMED', 'BELOW_HOW', 'BREAKING_OUT'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BULLISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ ichimoku_cloud

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_CLOUD, BELOW_CLOUD
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'ABOVE_CLOUD', 'BELOW_CLOUD'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH', 'BEARISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ ict_silver_bullet

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_FVG_IN_ZONE, BEARISH_FVG_RETEST, BULLISH_FVG_IN_ZONE, BULLISH_FVG_RETEST
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_FVG_RETEST', 'BULLISH_FVG_RETEST', 'BEARISH_FVG_IN_ZONE', 'BULLISH_FVG_IN_ZONE'} from valid_signals OR update analyze() to emit them

### ❌ ihod

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_IHOD, AT_IHOD, BULLISH_BREAK
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'AT_IHOD', 'ABOVE_IHOD', 'BULLISH_BREAK'} from valid_signals OR update analyze() to emit them

### ❌ ilod

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** AT_ILOD, BEARISH_BREAK, BELOW_ILOD
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAK', 'BELOW_ILOD', 'AT_ILOD'} from valid_signals OR update analyze() to emit them

### ❌ inducement

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_INDUCEMENT, BULLISH_INDUCEMENT
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_INDUCEMENT', 'BULLISH_INDUCEMENT'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NO_INDUCEMENT
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NO_INDUCEMENT'} to valid_signals in @register_block decorator

### ❌ initial_balance_breakout

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_IB, BEARISH_BREAKOUT, BELOW_IB, BULLISH_BREAKOUT, LOWER_IB
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKOUT', 'LOWER_IB', 'ABOVE_IB', 'BULLISH_BREAKOUT', 'BELOW_IB'} from valid_signals OR update analyze() to emit them

### ❌ internal_pivot_pattern

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BULLISH_PIVOT_LOW, PIVOT_HIGH, PIVOT_LOW
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'PIVOT_LOW', 'PIVOT_HIGH', 'BULLISH_PIVOT_LOW'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ inverse_head_and_shoulders

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** PATTERN_CONFIRMED, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'PATTERN_CONFIRMED', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ kill_zones

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ASIAN_KZ, INACTIVE, LONDON_KZ, NY_AM_KZ, NY_PM_KZ
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NY_AM_KZ', 'NY_PM_KZ', 'LONDON_KZ', 'INACTIVE', 'ASIAN_KZ'} from valid_signals OR update analyze() to emit them

### ❌ liquidity

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** VOID_DETECTED
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'VOID_DETECTED'} from valid_signals OR update analyze() to emit them

### ❌ liquidity_sweep

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_SWEEP, BULLISH_SWEEP
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_SWEEP', 'BEARISH_SWEEP'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, NO_SWEEP
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BEARISH', 'NO_SWEEP'} to valid_signals in @register_block decorator

### ❌ lod

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_LOD, AT_LOD, BELOW_LOD, BULLISH, LOD_BOUNCE
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'AT_LOD', 'LOD_BOUNCE', 'BULLISH', 'BELOW_LOD', 'ABOVE_LOD'} from valid_signals OR update analyze() to emit them

### ❌ low

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** ABOVE_LOW, AT_LOW, BREAKDOWN_CONFIRMED, BREAKING_DOWN, NO_LOW, NO_LOW_DATA
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NO_LOW_DATA', 'BREAKING_DOWN', 'ABOVE_LOW', 'NO_LOW', 'BREAKDOWN_CONFIRMED', 'AT_LOW'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BEARISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ macd_price_forecasting

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_FORECAST, BULLISH_FORECAST
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_FORECAST', 'BEARISH_FORECAST'} from valid_signals OR update analyze() to emit them

### ❌ macd_signal

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_CROSS, BEARISH_ZERO_CROSS, BULLISH_CROSS, BULLISH_ZERO_CROSS, NO_CROSS, NO_ZERO_CROSS, STRONG_BEARISH, STRONG_BULLISH, WEAKENING_BEARISH, WEAKENING_BULLISH
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NO_CROSS', 'BULLISH_CROSS', 'WEAKENING_BULLISH', 'STRONG_BULLISH', 'BULLISH_ZERO_CROSS', 'WEAKENING_BEARISH', 'BEARISH_ZERO_CROSS', 'NO_ZERO_CROSS', 'BEARISH_CROSS', 'STRONG_BEARISH'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH', 'BEARISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ market_depth

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** LOW_LIQUIDITY
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'LOW_LIQUIDITY'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NORMAL_LIQUIDITY
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NORMAL_LIQUIDITY'} to valid_signals in @register_block decorator

### ❌ market_structure_shift

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_MSS, BEARISH_RETEST, BULLISH_MSS, BULLISH_RETEST
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_RETEST', 'BULLISH_RETEST', 'BULLISH_MSS', 'BEARISH_MSS'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, BULLISH
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH', 'BEARISH'} to valid_signals in @register_block decorator

### ❌ mitigation_block

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_MITIGATION, BULLISH_MITIGATION
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_MITIGATION', 'BEARISH_MITIGATION'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH', 'BEARISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ optimal_trade_entry

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_OTE, BULLISH_OTE
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_OTE', 'BEARISH_OTE'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BULLISH, NEUTRAL, NO_OTE
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BULLISH', 'NEUTRAL', 'NO_OTE'} to valid_signals in @register_block decorator

### ❌ order_block

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_OB, BULLISH_OB
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_OB', 'BULLISH_OB'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NO_ORDER_BLOCK
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NO_ORDER_BLOCK'} to valid_signals in @register_block decorator

### ❌ order_flow_imbalance

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH', 'NEUTRAL'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BALANCED, BUY_IMBALANCE
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BALANCED', 'BUY_IMBALANCE'} to valid_signals in @register_block decorator

### ❌ pennant_pattern

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKOUT, BULLISH_BREAKOUT, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKOUT', 'BULLISH_BREAKOUT', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ power_hour_trends

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH', 'NEUTRAL'} from valid_signals OR update analyze() to emit them

### ❌ premium_discount_zones

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** AT_EQUILIBRIUM, NO_ZONE
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NO_ZONE', 'AT_EQUILIBRIUM'} from valid_signals OR update analyze() to emit them

### ❌ range_liquidity

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH', 'NEUTRAL'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NEAR_BUY_SIDE_LIQUIDITY, NEAR_SELL_SIDE_LIQUIDITY
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NEAR_SELL_SIDE_LIQUIDITY', 'NEAR_BUY_SIDE_LIQUIDITY'} to valid_signals in @register_block decorator

### ❌ rising_wedge

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKDOWN, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKDOWN', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ rounding_bottom

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BREAKOUT_CONFIRMED, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BREAKOUT_CONFIRMED', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ rsi_divergence

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_DIVERGENCE, BULLISH_DIVERGENCE, OVERBOUGHT, OVERSOLD
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'OVERSOLD', 'OVERBOUGHT', 'BEARISH_DIVERGENCE', 'BULLISH_DIVERGENCE'} from valid_signals OR update analyze() to emit them

### ❌ session_time

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** HIGH_VOLUME_SESSION, LOW_VOLUME_SESSION, SESSION_CLOSE, SESSION_OPEN
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'HIGH_VOLUME_SESSION', 'SESSION_OPEN', 'SESSION_CLOSE', 'LOW_VOLUME_SESSION'} from valid_signals OR update analyze() to emit them

### ❌ stochastic_rsi

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_CROSS, BULLISH_CROSS, NEUTRAL_HIGH, NEUTRAL_LOW, NO_CROSS
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NO_CROSS', 'NEUTRAL_LOW', 'BULLISH_CROSS', 'BEARISH_CROSS', 'NEUTRAL_HIGH'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** BEARISH, NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'BEARISH', 'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ supply_demand_zones

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH', 'NEUTRAL'} from valid_signals OR update analyze() to emit them

### ❌ swing_breakout_sequence

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKOUT_SEQUENCE, BULLISH_BREAKOUT_SEQUENCE
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKOUT_SEQUENCE', 'BULLISH_BREAKOUT_SEQUENCE'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ swing_failure_pattern

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_SFP, BULLISH_SFP
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_SFP', 'BEARISH_SFP'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ swing_points

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** MAJOR_SWING_HIGH_DETECTED, MINOR_SWING_HIGH_DETECTED, MINOR_SWING_LOW_DETECTED, NO_SWINGS
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NO_SWINGS', 'MINOR_SWING_LOW_DETECTED', 'MAJOR_SWING_HIGH_DETECTED', 'MINOR_SWING_HIGH_DETECTED'} from valid_signals OR update analyze() to emit them

### ❌ symmetrical_triangle

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKOUT, BULLISH_BREAKOUT, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKOUT', 'BULLISH_BREAKOUT', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ three_bar_reversal

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH'} from valid_signals OR update analyze() to emit them

### ❌ trailing_stop

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH, BULLISH, NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH', 'BEARISH', 'NEUTRAL'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** LONG_STOP_HOLD
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'LONG_STOP_HOLD'} to valid_signals in @register_block decorator

### ❌ triple_bottom

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BULLISH_BREAKOUT, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BULLISH_BREAKOUT', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ triple_top

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_BREAKDOWN, PATTERN_FORMING
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_BREAKDOWN', 'PATTERN_FORMING'} from valid_signals OR update analyze() to emit them

### ❌ us_settlement

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NEUTRAL'} from valid_signals OR update analyze() to emit them

### ❌ vwap

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** NEUTRAL
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'NEUTRAL'} from valid_signals OR update analyze() to emit them

### ❌ wave_consolidation

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BEARISH_ZONE_BREAK, BEARISH_ZONE_REJECTION, BULLISH_ZONE_BREAK, BULLISH_ZONE_REJECTION
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'BEARISH_ZONE_BREAK', 'BULLISH_ZONE_BREAK', 'BULLISH_ZONE_REJECTION', 'BEARISH_ZONE_REJECTION'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NEUTRAL
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NEUTRAL'} to valid_signals in @register_block decorator

### ❌ wyckoff_accumulation

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** SOS_BREAKOUT, SPRING_DETECTED
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'SOS_BREAKOUT', 'SPRING_DETECTED'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** ACCUMULATION_PHASE_B
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'ACCUMULATION_PHASE_B'} to valid_signals in @register_block decorator

### ❌ wyckoff_distribution

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** SOW_BREAKDOWN, UTAD_DETECTED
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'UTAD_DETECTED', 'SOW_BREAKDOWN'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** DISTRIBUTION_PHASE_B
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'DISTRIBUTION_PHASE_B'} to valid_signals in @register_block decorator

### ❌ wyckoff_reaccumulation

**Type:** DECLARED_BUT_NEVER_EMITTED
**Severity:** HIGH
**Signals:** BREAKOUT_CONTINUATION, REACCUMULATION_DETECTED, SPRING_DETECTED
**Impact:** Users can select these in GUI but they never fire - causes confusion and filter bugs
**Fix:** Remove {'SPRING_DETECTED', 'BREAKOUT_CONTINUATION', 'REACCUMULATION_DETECTED'} from valid_signals OR update analyze() to emit them

**Type:** EMITTED_BUT_NOT_DECLARED
**Severity:** CRITICAL
**Signals:** NO_REACCUMULATION
**Impact:** Block emits signals not in valid_signals - breaks validation and confluence calculation
**Fix:** Add {'NO_REACCUMULATION'} to valid_signals in @register_block decorator

---

## 📋 COMPLETE EMISSIONS REFERENCE

This section documents what each block ACTUALLY emits (tested on synthetic data).

### ELLIOTT_WAVE

#### ❌ `elliott_wave_count`

**Declared:** `ERROR, INSUFFICIENT_DATA, NO_PATTERN`
**Actually Emits:** ``
**Errors:** 5 errors during testing

#### ❌ `elliott_wave_oscillator`

**Declared:** `BEARISH_DIVERGENCE, BEARISH_MOMENTUM_INCREASING, BEARISH_MOMENTUM_WEAKENING, BULLISH_DIVERGENCE, BULLISH_MOMENTUM_INCREASING, BULLISH_MOMENTUM_WEAKENING, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BEARISH_MOMENTUM_INCREASING, BULLISH_MOMENTUM_INCREASING, BULLISH_MOMENTUM_WEAKENING`
**Frequency:** BEARISH_MOMENTUM_INCREASING(2), BULLISH_MOMENTUM_INCREASING(1), BULLISH_MOMENTUM_WEAKENING(2)

### FIBONACCI

#### ❌ `fibonacci_retracements`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `AT_FIB_23, AT_FIB_38, AT_FIB_50, BETWEEN_LEVELS`
**Frequency:** AT_FIB_23(1), AT_FIB_38(1), AT_FIB_50(1), BETWEEN_LEVELS(2)

### INSTITUTIONAL

#### ❌ `anchored_vwap`

**Declared:** `ABOVE_ANCHORED_VWAP, BELOW_ANCHORED_VWAP, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BELOW_ANCHORED_VWAP, ERROR`
**Frequency:** BELOW_ANCHORED_VWAP(1), ERROR(4)

#### ❌ `ema_crossover`

**Declared:** `BEARISH_ALIGNMENT, BULLISH_ALIGNMENT, DEATH_CROSS, ERROR, GOLDEN_CROSS, INSUFFICIENT_DATA`
**Actually Emits:** `INSUFFICIENT_DATA`
**Frequency:** INSUFFICIENT_DATA(5)

#### ❌ `market_depth`

**Declared:** `ERROR, HIGH_LIQUIDITY, INSUFFICIENT_DATA, LOW_LIQUIDITY`
**Actually Emits:** `HIGH_LIQUIDITY, NORMAL_LIQUIDITY`
**Frequency:** HIGH_LIQUIDITY(1), NORMAL_LIQUIDITY(4)

#### ❌ `order_flow_imbalance`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `BALANCED, BUY_IMBALANCE`
**Frequency:** BALANCED(4), BUY_IMBALANCE(1)

#### ❌ `vwap`

**Declared:** `BEARISH, BULLISH, ERROR, NEUTRAL`
**Actually Emits:** `BEARISH, BULLISH`
**Frequency:** BEARISH(2), BULLISH(3)

### MARKET_STRUCTURE

#### ❌ `liquidity`

**Declared:** `ERROR, INSUFFICIENT_DATA, VOID_DETECTED`
**Actually Emits:** ``
**Errors:** 1 errors during testing

#### ❌ `power_hour_trends`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** ``
**Errors:** 1 errors during testing

#### ❌ `premium_discount_zones`

**Declared:** `AT_EQUILIBRIUM, ERROR, INSUFFICIENT_DATA, NO_ZONE, PRICE_IN_DISCOUNT, PRICE_IN_PREMIUM`
**Actually Emits:** `PRICE_IN_DISCOUNT, PRICE_IN_PREMIUM`
**Frequency:** PRICE_IN_DISCOUNT(3), PRICE_IN_PREMIUM(2)

#### ❌ `range_liquidity`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `NEAR_BUY_SIDE_LIQUIDITY, NEAR_SELL_SIDE_LIQUIDITY`
**Frequency:** NEAR_BUY_SIDE_LIQUIDITY(2), NEAR_SELL_SIDE_LIQUIDITY(3)

#### ❌ `swing_points`

**Declared:** `ERROR, INSUFFICIENT_DATA, MAJOR_SWING_HIGH_DETECTED, MAJOR_SWING_LOW_DETECTED, MINOR_SWING_HIGH_DETECTED, MINOR_SWING_LOW_DETECTED, NO_SWINGS, SWING_HIGH_DETECTED, SWING_LOW_DETECTED`
**Actually Emits:** `MAJOR_SWING_LOW_DETECTED, SWING_HIGH_DETECTED, SWING_LOW_DETECTED`
**Frequency:** MAJOR_SWING_LOW_DETECTED(2), SWING_HIGH_DETECTED(2), SWING_LOW_DETECTED(1)

#### ❌ `wave_consolidation`

**Declared:** `BEARISH_ZONE_BREAK, BEARISH_ZONE_REJECTION, BULLISH_ZONE_BREAK, BULLISH_ZONE_REJECTION, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

### MOVING_AVERAGES

#### ❌ `ema_200_trend`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `INSUFFICIENT_DATA`
**Frequency:** INSUFFICIENT_DATA(5)

#### ❌ `ema_20_50_cross`

**Declared:** `DEATH_CROSS, ERROR, GOLDEN_CROSS, INSUFFICIENT_DATA, NO_CROSS`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `ema_20_50_trend`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `BEARISH, BULLISH`
**Frequency:** BEARISH(3), BULLISH(2)

#### ❌ `ema_255_vector`

**Declared:** `ABOVE_EMA, BELOW_EMA, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `INSUFFICIENT_DATA`
**Frequency:** INSUFFICIENT_DATA(5)

#### ❌ `ema_50_vector`

**Declared:** `ABOVE_EMA, BEARISH_BREAK, BELOW_EMA, BULLISH_BREAK, ERROR, INSUFFICIENT_DATA, NO_BREAK`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `ema_55_vector`

**Declared:** `ABOVE_EMA, BELOW_EMA, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `ema_800_vector`

**Declared:** `ABOVE_EMA, BELOW_EMA, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `INSUFFICIENT_DATA`
**Frequency:** INSUFFICIENT_DATA(5)

### OSCILLATORS

#### ❌ `macd_signal`

**Declared:** `BEARISH_CROSS, BEARISH_ZERO_CROSS, BULLISH_CROSS, BULLISH_ZERO_CROSS, ERROR, INSUFFICIENT_DATA, NO_CROSS, NO_ZERO_CROSS, STRONG_BEARISH, STRONG_BULLISH, WEAKENING_BEARISH, WEAKENING_BULLISH`
**Actually Emits:** `BEARISH, BULLISH, NEUTRAL`
**Frequency:** BEARISH(1), BULLISH(1), NEUTRAL(3)

#### ❌ `rsi_divergence`

**Declared:** `BEARISH_DIVERGENCE, BULLISH_DIVERGENCE, ERROR, NEUTRAL, OVERBOUGHT, OVERSOLD`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `stochastic_rsi`

**Declared:** `BEARISH_CROSS, BULLISH_CROSS, ERROR, INSUFFICIENT_DATA, NEUTRAL_HIGH, NEUTRAL_LOW, NO_CROSS`
**Actually Emits:** `BEARISH, NEUTRAL`
**Frequency:** BEARISH(1), NEUTRAL(4)

### PATTERNS

#### ❌ `ascending_triangle`

**Declared:** `BULLISH_BREAKOUT, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `candle_2_close`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `cup_and_handle`

**Declared:** `BREAKOUT_CONFIRMED, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `descending_triangle`

**Declared:** `BEARISH_BREAKDOWN, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `double_bottom`

**Declared:** `BULLISH_BREAKOUT, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `double_top`

**Declared:** `BEARISH_BREAKDOWN, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `falling_wedge`

**Declared:** `BULLISH_BREAKOUT, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `flag_pattern`

**Declared:** `BEARISH_BREAKOUT, BULLISH_BREAKOUT, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `head_and_shoulders`

**Declared:** `ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_CONFIRMED, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `initial_balance_breakout`

**Declared:** `ABOVE_IB, BEARISH_BREAKOUT, BELOW_IB, BULLISH_BREAKOUT, ERROR, INSUFFICIENT_DATA, LOWER_IB`
**Actually Emits:** ``
**Errors:** 1 errors during testing

#### ❌ `internal_pivot_pattern`

**Declared:** `BEARISH_PIVOT_HIGH, BULLISH_PIVOT_LOW, ERROR, INSUFFICIENT_DATA, PIVOT_HIGH, PIVOT_LOW`
**Actually Emits:** `BEARISH_PIVOT_HIGH, NEUTRAL`
**Frequency:** BEARISH_PIVOT_HIGH(1), NEUTRAL(4)

#### ❌ `inverse_head_and_shoulders`

**Declared:** `ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_CONFIRMED, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `pennant_pattern`

**Declared:** `BEARISH_BREAKOUT, BULLISH_BREAKOUT, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `rising_wedge`

**Declared:** `BEARISH_BREAKDOWN, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `rounding_bottom`

**Declared:** `BREAKOUT_CONFIRMED, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `swing_breakout_sequence`

**Declared:** `BEARISH_BREAKOUT_SEQUENCE, BULLISH_BREAKOUT_SEQUENCE, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `symmetrical_triangle`

**Declared:** `BEARISH_BREAKOUT, BULLISH_BREAKOUT, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `three_bar_reversal`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `triple_bottom`

**Declared:** `BULLISH_BREAKOUT, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

#### ❌ `triple_top`

**Declared:** `BEARISH_BREAKDOWN, ERROR, INSUFFICIENT_DATA, NO_PATTERN, PATTERN_FORMING`
**Actually Emits:** `NO_PATTERN`
**Frequency:** NO_PATTERN(5)

### PRICE_ACTION

#### ❌ `breaker_block`

**Declared:** `BEARISH_BREAKER, BULLISH_BREAKER, ERROR, INSUFFICIENT_DATA, NO_BREAKER`
**Actually Emits:** `BEARISH, BULLISH, NEUTRAL, NO_BREAKER`
**Frequency:** BEARISH(1), BULLISH(2), NEUTRAL(1), NO_BREAKER(1)

#### ❌ `fair_value_gap`

**Declared:** `BEARISH_FVG, BULLISH_FVG, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `NO_FVG`
**Frequency:** NO_FVG(5)

#### ❌ `liquidity_sweep`

**Declared:** `BEARISH_SWEEP, BULLISH_SWEEP, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BEARISH, NO_SWEEP`
**Frequency:** BEARISH(3), NO_SWEEP(2)

#### ❌ `order_block`

**Declared:** `BEARISH_OB, BULLISH_OB, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `NO_ORDER_BLOCK`
**Frequency:** NO_ORDER_BLOCK(5)

### PRICE_LEVELS

#### ❌ `asia_session_50_percent`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `fifty_pct_hod_lod`

**Declared:** `ABOVE_EQUILIBRIUM, AT_EQUILIBRIUM, BELOW_EQUILIBRIUM, ERROR, NEUTRAL, REJECTION_AT_EQ`
**Actually Emits:** `ABOVE_EQUILIBRIUM, AT_EQUILIBRIUM, BELOW_EQUILIBRIUM, NEUTRAL`
**Frequency:** ABOVE_EQUILIBRIUM(1), AT_EQUILIBRIUM(1), BELOW_EQUILIBRIUM(2), NEUTRAL(1)

#### ❌ `fifty_pct_intra_hod_lod`

**Declared:** `ABOVE_INTRA_EQ, AT_INTRA_EQ, BELOW_INTRA_EQ, ERROR, NEUTRAL, REJECTION_AT_INTRA_EQ`
**Actually Emits:** `AT_INTRA_EQ, NEUTRAL`
**Frequency:** AT_INTRA_EQ(1), NEUTRAL(4)

#### ❌ `hod`

**Declared:** `ABOVE_HOD, AT_HOD, BEARISH, BELOW_HOD, BULLISH, ERROR, HOD_REJECTION, NEUTRAL`
**Actually Emits:** `BULLISH, NEUTRAL`
**Frequency:** BULLISH(1), NEUTRAL(4)

#### ❌ `how`

**Declared:** `BELOW_HOW, BREAKING_OUT, BREAKOUT_CONFIRMED, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BULLISH, NEUTRAL`
**Frequency:** BULLISH(1), NEUTRAL(4)

#### ❌ `ihod`

**Declared:** `ABOVE_IHOD, AT_IHOD, BEARISH_REJECTION, BELOW_IHOD, BULLISH_BREAK, ERROR, NEUTRAL`
**Actually Emits:** `BEARISH_REJECTION, BELOW_IHOD, NEUTRAL`
**Frequency:** BEARISH_REJECTION(1), BELOW_IHOD(2), NEUTRAL(2)

#### ❌ `ilod`

**Declared:** `ABOVE_ILOD, AT_ILOD, BEARISH_BREAK, BELOW_ILOD, BULLISH_BOUNCE, ERROR, NEUTRAL`
**Actually Emits:** `ABOVE_ILOD, BULLISH_BOUNCE, NEUTRAL`
**Frequency:** ABOVE_ILOD(3), BULLISH_BOUNCE(1), NEUTRAL(1)

#### ❌ `lod`

**Declared:** `ABOVE_LOD, AT_LOD, BEARISH, BELOW_LOD, BULLISH, ERROR, LOD_BOUNCE, NEUTRAL`
**Actually Emits:** `BEARISH, NEUTRAL`
**Frequency:** BEARISH(1), NEUTRAL(4)

#### ❌ `low`

**Declared:** `ABOVE_LOW, AT_LOW, BREAKDOWN_CONFIRMED, BREAKING_DOWN, ERROR, INSUFFICIENT_DATA, NO_LOW, NO_LOW_DATA`
**Actually Emits:** `BEARISH, NEUTRAL`
**Frequency:** BEARISH(1), NEUTRAL(4)

#### ❌ `us_settlement`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `BEARISH, BULLISH`
**Frequency:** BEARISH(3), BULLISH(2)

### RISK_MANAGEMENT

#### ❌ `trailing_stop`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `LONG_STOP_HOLD`
**Frequency:** LONG_STOP_HOLD(5)

### SESSIONS

#### ❌ `kill_zones`

**Declared:** `ACTIVE, ASIAN_KZ, ERROR, INACTIVE, LONDON_KZ, NO_SIGNAL, NY_AM_KZ, NY_PM_KZ`
**Actually Emits:** `ACTIVE`
**Frequency:** ACTIVE(5)

#### ❌ `session_time`

**Declared:** `ERROR, HIGH_VOLUME_SESSION, LOW_VOLUME_SESSION, MODERATE_SESSION, NO_SIGNAL, SESSION_CLOSE, SESSION_OPEN`
**Actually Emits:** `MODERATE_SESSION`
**Frequency:** MODERATE_SESSION(5)

### SIGNALS

#### ❌ `adaptive_momentum_oscillator`

**Declared:** `BEARISH_CROSS, BEARISH_DIVERGENCE, BULLISH_CROSS, BULLISH_DIVERGENCE, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** ``
**Errors:** 1 errors during testing

#### ❌ `asfx_a2_vwap`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `BULLISH_A2, NEUTRAL`
**Frequency:** BULLISH_A2(1), NEUTRAL(4)

#### ❌ `ict_silver_bullet`

**Declared:** `BEARISH_FVG_IN_ZONE, BEARISH_FVG_RETEST, BULLISH_FVG_IN_ZONE, BULLISH_FVG_RETEST, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** ``
**Errors:** 1 errors during testing

#### ❌ `macd_price_forecasting`

**Declared:** `BEARISH_FORECAST, BULLISH_FORECAST, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** ``
**Errors:** 1 errors during testing

### SMC_ICT

#### ❌ `balanced_price_range`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `break_of_structure`

**Declared:** `BEARISH_BOS, BULLISH_BOS, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BEARISH, BULLISH, NEUTRAL`
**Frequency:** BEARISH(3), BULLISH(1), NEUTRAL(1)

#### ❌ `change_of_character`

**Declared:** `BEARISH_CHOCH, BEARISH_MSS, BULLISH_CHOCH, BULLISH_MSS, ERROR, HIGH_SWEEP, INSUFFICIENT_DATA, LOW_SWEEP, UNUSUALLY_SLOW`
**Actually Emits:** `BEARISH, NEUTRAL`
**Frequency:** BEARISH(1), NEUTRAL(4)

#### ❌ `displacement`

**Declared:** `BEARISH_DISPLACEMENT, BEARISH_FVG, BULLISH_DISPLACEMENT, BULLISH_FVG, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `NO_DISPLACEMENT`
**Frequency:** NO_DISPLACEMENT(5)

#### ❌ `inducement`

**Declared:** `BEARISH_INDUCEMENT, BULLISH_INDUCEMENT, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `NO_INDUCEMENT`
**Frequency:** NO_INDUCEMENT(5)

#### ❌ `market_structure_shift`

**Declared:** `BEARISH_MSS, BEARISH_RETEST, BULLISH_MSS, BULLISH_RETEST, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BEARISH, BULLISH`
**Frequency:** BEARISH(3), BULLISH(2)

#### ❌ `mitigation_block`

**Declared:** `BEARISH_MITIGATION, BULLISH_MITIGATION, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BEARISH, BULLISH, NEUTRAL`
**Frequency:** BEARISH(1), BULLISH(3), NEUTRAL(1)

#### ❌ `optimal_trade_entry`

**Declared:** `BEARISH_OTE, BULLISH_OTE, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BULLISH, NEUTRAL, NO_OTE`
**Frequency:** BULLISH(1), NEUTRAL(1), NO_OTE(3)

#### ❌ `swing_failure_pattern`

**Declared:** `BEARISH_SFP, BULLISH_SFP, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

### SUPPLY_DEMAND

#### ❌ `supply_demand_zones`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** ``
**Errors:** 1 errors during testing

### TREND

#### ❌ `adx`

**Declared:** `BEARISH, BULLISH, ERROR, INSUFFICIENT_DATA, NEUTRAL`
**Actually Emits:** `NEUTRAL`
**Frequency:** NEUTRAL(5)

#### ❌ `ichimoku_cloud`

**Declared:** `ABOVE_CLOUD, BELOW_CLOUD, ERROR, INSUFFICIENT_DATA`
**Actually Emits:** `BEARISH, BULLISH, NEUTRAL`
**Frequency:** BEARISH(2), BULLISH(1), NEUTRAL(2)

### VOLATILITY

#### ❌ `adr`

**Declared:** `ABOVE_ADR, BELOW_ADR, CALM, ERROR, NEAR_ADR, VOLATILE, WITHIN_ADR`
**Actually Emits:** `NORMAL`
**Frequency:** NORMAL(5)

#### ❌ `atr`

**Declared:** `ERROR, EXTREME_HIGH, EXTREME_LOW, INSUFFICIENT_DATA, VERY_HIGH, VERY_LOW`
**Actually Emits:** `STABLE`
**Frequency:** STABLE(5)

#### ❌ `bollinger_bands`

**Declared:** `ABOVE_UPPER, BEARISH_REVERSAL, BELOW_LOWER, BULLISH_REVERSAL, ERROR, INSUFFICIENT_DATA, LOWER_BAND_WALK, LOWER_HALF, MEDIUM_HIGH, MEDIUM_LOW, NEAR_LOWER, SQUEEZE_BREAKOUT, SQUEEZE_BREAKOUT_BEAR, SQUEEZE_BREAKOUT_BULL`
**Actually Emits:** `ABOVE_UPPER, BELOW_LOWER, NEAR_LOWER, UPPER_HALF`
**Frequency:** ABOVE_UPPER(1), BELOW_LOWER(2), NEAR_LOWER(1), UPPER_HALF(1)

### WYCKOFF

#### ❌ `wyckoff_accumulation`

**Declared:** `ERROR, INSUFFICIENT_DATA, SOS_BREAKOUT, SPRING_DETECTED`
**Actually Emits:** `ACCUMULATION_PHASE_B`
**Frequency:** ACCUMULATION_PHASE_B(5)

#### ❌ `wyckoff_distribution`

**Declared:** `ERROR, INSUFFICIENT_DATA, SOW_BREAKDOWN, UTAD_DETECTED`
**Actually Emits:** `DISTRIBUTION_PHASE_B`
**Frequency:** DISTRIBUTION_PHASE_B(5)

#### ❌ `wyckoff_reaccumulation`

**Declared:** `BREAKOUT_CONTINUATION, ERROR, INSUFFICIENT_DATA, REACCUMULATION_DETECTED, SPRING_DETECTED`
**Actually Emits:** `NO_REACCUMULATION`
**Frequency:** NO_REACCUMULATION(5)

---

## 💡 RECOMMENDATIONS

### Immediate Actions (Priority 1)

1. **Fix Critical Mismatches** - Blocks emitting undeclared signals
2. **Update Registry Metadata** - Add missing signals to valid_signals
3. **Remove Never-Emitted Signals** - Clean up declarations

### System Improvements (Priority 2)

1. **Add CI/CD Test** - Run this audit on every commit
2. **GUI Validation** - Prevent selecting never-emitted signals
3. **Runtime Validation** - Warn if emitted signal not in valid_signals
