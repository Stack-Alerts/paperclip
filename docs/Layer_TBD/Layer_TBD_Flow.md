# Layer TBD Signal Generation Flow Diagram

**Document**: Complete data flow and logic diagrams for Layer TBD  
**Created**: December 27, 2025  
**Purpose**: Visual representation of all Layer TBD processes

---

## Table of Contents

1. [Main Signal Generation Flow](#1-main-signal-generation-flow)
2. [Pattern Detection Flows](#2-pattern-detection-flows)
3. [Level Management Flow](#3-level-management-flow)
4. [Session & Timing Flow](#4-session--timing-flow)
5. [Confirmation System Flow](#5-confirmation-system-flow)
6. [Metadata Construction Flow](#6-metadata-construction-flow)
7. [Error Handling Flow](#7-error-handling-flow)

---

## 1. Main Signal Generation Flow

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────┐
│  ENTRY POINT: generate_signal(data, current_price, position) │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │ Validate Input Data           │
        │ - Check DataFrame format      │
        │ - Verify required columns     │
        │ - Check minimum length (100)  │
        └──────────┬────────────────────┘
                   │ Invalid ──→ [EXCEPTION: SignalGenerationError]
                   │ Valid
                   ▼
        ┌───────────────────────────────┐
        │ Calculate Indicators          │
        │ - ATR (14 period)             │
        │ - Session identification      │
        │ - Weekly cycle phase          │
        │ - Day of week                 │
        └──────────┬────────────────────┘
                   │
                   ▼
        ┌───────────────────────────────┐
        │ Update Level Tracking         │
        │ - Weekly high/low             │
        │ - Daily high/low              │
        │ - Friday close                │
        │ - Touch counters              │
        └──────────┬────────────────────┘
                   │
                   ▼
        ┌───────────────────────────────┐
        │ Detect All Patterns           │
        │ (See Pattern Detection Flow)  │
        └──────────┬────────────────────┘
                   │
                   ▼
            ┌──────────────┐
            │ Pattern      │
            │ Found?       │
            └──┬────────┬──┘
               │ No     │ Yes
               │        │
               │        ▼
               │  ┌─────────────────────┐
               │  │ Analyze Timing      │
               │  │ - Session score     │
               │  │ - Day of week       │
               │  │ - Weekly cycle      │
               │  └──────┬──────────────┘
               │         │
               │         ▼
               │  ┌─────────────────────┐
               │  │ Analyze Levels      │
               │  │ - Weekly proximity  │
               │  │ - Three hits check  │
               │  │ - Level strength    │
               │  └──────┬──────────────┘
               │         │
               │         ▼
               │  ┌─────────────────────┐
               │  │ Check Confirmations │
               │  │ - Pattern ✓         │
               │  │ - Volume ✓/✗        │
               │  │ - Trend ✓/✗         │
               │  │ - Timing ✓/✗        │
               │  │ - Level ✓/✗         │
               │  └──────┬──────────────┘
               │         │
               │         ▼
               │  ┌──────────────┐
               │  │ Meets Min    │
               │  │ Confirmations│
               │  │ Required?    │
               │  └──┬────────┬──┘
               │     │ No     │ Yes
               │     │        │
               │     │        ▼
               │     │  ┌─────────────────────┐
               │     │  │ Calculate Confidence│
               │     │  │ - Pattern: 0.0-1.0  │
               │     │  │ - Timing: 0.0-1.0   │
               │     │  │ - Level: 0.0-1.0    │
               │     │  │ - Bonus: +0.1/conf  │
               │     │  └──────┬──────────────┘
               │     │         │
               │     │         ▼
               │     │  ┌─────────────────────┐
               │     │  │ Build Signal        │
               │     │  │ Metadata            │
               │     │  │ (See Metadata Flow) │
               │     │  └──────┬──────────────┘
               │     │         │
               ▼     ▼         ▼
        ┌──────────────────────────┐
        │ Return LayerSignal       │
        │ - direction: long/short  │
        │   or neutral             │
        │ - confidence: 0.0-1.0    │
        │ - strength: 0.0-1.0      │
        │ - metadata: {...}        │
        └──────────────────────────┘
```

### Detailed Step-by-Step Flow

```
START: generate_signal(data, current_price, position)
│
├─→ [1] INPUT VALIDATION
│   ├─ Check data is pandas DataFrame
│   ├─ Verify columns: ['open', 'high', 'low', 'close', 'volume']
│   ├─ Check DatetimeIndex present
│   ├─ Verify minimum length >= 100 bars
│   └─ Validate current_price is numeric
│       ├─ FAIL → raise SignalGenerationError
│       └─ PASS → Continue
│
├─→ [2] INDICATOR CALCULATION
│   ├─ calculate_indicators(data)
│   │   ├─ ATR(14) for stop loss calculations
│   │   ├─ Current session (Asian/London/NY/Overlap/Weekend)
│   │   ├─ Weekly cycle phase
│   │   └─ Day of week classification
│   └─ Store in self.indicators
│
├─→ [3] LEVEL UPDATES
│   ├─ _update_levels(data)
│   │   ├─ Check for week rollover (Monday)
│   │   │   └─ YES → Reset weekly_high, weekly_low, touches
│   │   ├─ Update weekly_high = max(recent highs)
│   │   ├─ Update weekly_low = min(recent lows)
│   │   ├─ Check for day rollover
│   │   │   └─ YES → Reset daily_high, daily_low
│   │   ├─ Check if first hour of day
│   │   │   └─ YES → Capture daily_high, daily_low
│   │   ├─ Check if Friday evening
│   │   │   └─ YES → Capture friday_close
│   │   └─ Track level touches (see Level Flow)
│   └─ Levels stored in instance variables
│
├─→ [4] PATTERN DETECTION (Parallel check all 7)
│   ├─ IF enable_m_pattern: _detect_m_pattern()
│   ├─ IF enable_w_pattern: _detect_w_pattern()
│   ├─ IF enable_weekend_trap: _detect_weekend_trap()
│   ├─ IF enable_board_meeting: _detect_board_meeting()
│   ├─ IF enable_three_hits: _detect_three_hits_reversal()
│   ├─ IF enable_trapping_volume: _detect_trapping_volume()
│   └─ IF enable_one_formation: _detect_one_formation()
│       │
│       └─ First valid pattern found → pattern_data
│           ├─ NO PATTERN FOUND → NEUTRAL SIGNAL
│           └─ PATTERN FOUND → Continue to scoring
│
├─→ [5] TIMING ANALYSIS
│   ├─ _analyze_timing(current_session, day_of_week)
│   │   ├─ Session score:
│   │   │   ├─ OVERLAP: 1.0
│   │   │   ├─ NY/LONDON: 0.8
│   │   │   ├─ ASIAN: 0.5
│   │   │   └─ WEEKEND: 0.3
│   │   ├─ Day of week score:
│   │   │   ├─ Tue/Wed/Thu: 1.0 (best)
│   │   │   ├─ Mon/Fri: 0.7
│   │   │   └─ Sat/Sun: 0.3
│   │   └─ Weekly cycle score: 0.0-1.0
│   └─ Return timing_score (weighted average)
│
├─→ [6] LEVEL ANALYSIS
│   ├─ _analyze_levels(pattern_data, current_price)
│   │   ├─ Calculate distance to weekly_high
│   │   ├─ Calculate distance to weekly_low
│   │   ├─ Check three_hits_rule status
│   │   ├─ Evaluate level strength (touch history)
│   │   └─ Return level_score (0.0-1.0)
│   └─ Higher score if pattern near key levels
│
├─→ [7] CONFIRMATION CHECKS
│   ├─ confirmations = {'pattern': True}  # Always true if pattern found
│   ├─ IF require_volume_confirmation:
│   │   └─ Check current_volume > avg_volume * multiplier
│   ├─ IF require_trend_alignment:
│   │   └─ Check pattern direction == trend direction
│   ├─ IF enable_session_filter:
│   │   └─ Check current_session in allowed_sessions
│   ├─ IF enable_timing_confirmation:
│   │   └─ Check timing_score >= threshold
│   └─ IF enable_level_confirmation:
│       └─ Check level_score >= threshold
│       │
│       └─ Count total confirmations met
│
├─→ [8] MINIMUM CONFIRMATION CHECK
│   ├─ confirmations_met >= minimum_confirmations?
│   │   ├─ NO → NEUTRAL SIGNAL
│   │   └─ YES → Continue to confidence calculation
│   └─
│
├─→ [9] CONFIDENCE CALCULATION
│   ├─ base_confidence = pattern_data.confidence
│   ├─ timing_weight = timing_score * 0.3
│   ├─ level_weight = level_score * 0.2
│   ├─ confirmation_bonus = (confirmations_met - minimum) * 0.1
│   ├─ final_confidence = min(1.0, base + timing + level + bonus)
│   └─ strength = confirmations_met / total_possible_confirmations
│
├─→ [10] METADATA CONSTRUCTION
│   ├─ Build comprehensive metadata dict:
│   │   ├─ 'layer_name': 'layer_tbd'
│   │   ├─ 'pattern_type': pattern_data.pattern_type
│   │   ├─ 'pattern_confidence': pattern_data.confidence
│   │   ├─ 'timing_score': timing_score
│   │   ├─ 'level_score': level_score
│   │   ├─ 'confirmations_met': confirmations_met
│   │   ├─ 'confirmations_required': minimum_confirmations
│   │   ├─ 'confirmations': {dict of all confirmation states}
│   │   ├─ 'entry_price': pattern_data.entry_price
│   │   ├─ 'stop_loss': pattern_data.stop_loss
│   │   ├─ 'take_profit_1/2/3': pattern_data.tp1/tp2/tp3
│   │   ├─ 'risk_reward_1/2/3': calculated R:R ratios
│   │   ├─ 'current_price': current_price
│   │   ├─ 'current_position': position
│   │   └─ 'pattern_metadata': pattern_data.metadata
│   └─
│
└─→ [11] RETURN SIGNAL
    └─ LayerSignal(
        direction='long' | 'short' | 'neutral',
        confidence=final_confidence,
        strength=strength,
        metadata=metadata_dict
    )

END
```

---

## 2. Pattern Detection Flows

### 2.1 M-Pattern Detection Flow

```
ENTRY: _detect_m_pattern(data, current_price)
│
├─→ [1] VALIDATE LOOKBACK
│   ├─ min_len = mw_pattern_length_min (default: 10)
│   ├─ max_len = mw_pattern_length_max (default: 50)
│   ├─ Check len(data) >= max_len
│   │   └─ NO → Return None
│   └─ lookback = min(max_len, len(data))
│
├─→ [2] EXTRACT RECENT DATA
│   ├─ recent = data.iloc[-lookback:]
│   ├─ highs = recent['high'].values
│   └─
│
├─→ [3] FIND PEAKS
│   ├─ peaks = _find_peaks(highs, order=3)
│   │   └─ Uses scipy.signal.argrelextrema
│   ├─ Check len(peaks) >= 2
│   │   └─ NO → Return None
│   └─ peak2_idx = peaks[-1]  # Most recent peak
│       peak1_idx = peaks[-2]  # Previous peak
│
├─→ [4] CHECK PEAK SYMMETRY
│   ├─ peak1_price = highs[peak1_idx]
│   ├─ peak2_price = highs[peak2_idx]
│   ├─ price_diff = abs(peak1 - peak2) / peak1
│   ├─ tolerance = mw_peak_tolerance (default: 0.15)
│   ├─ Check price_diff <= tolerance
│   │   └─ NO → Return None (peaks too different)
│   └─ YES → Peaks are symmetric
│
├─→ [5] CALCULATE NECKLINE
│   ├─ valley_data = recent.iloc[peak1_idx:peak2_idx+1]
│   ├─ neckline = valley_data['low'].min()
│   └─
│
├─→ [6] CHECK NECKLINE BREAK (BEARISH)
│   ├─ threshold = mw_neckline_break_threshold (default: 0.003)
│   ├─ Check current_price < neckline * (1 - threshold)
│   │   └─ NO → Return None (price hasn't broken below)
│   └─ YES → Neckline broken (bearish confirmation)
│
├─→ [7] VOLUME CONFIRMATION (if required)
│   ├─ IF require_volume_confirmation:
│   │   ├─ current_volume = recent.iloc[-1]['volume']
│   │   ├─ avg_volume = recent['volume'].mean()
│   │   ├─ multiplier = mw_volume_multiplier (default: 1.3)
│   │   ├─ Check current_volume >= avg_volume * multiplier
│   │   │   └─ NO → Return None
│   │   └─ YES → Volume confirmed
│   └─
│
├─→ [8] CALCULATE TRADE PARAMETERS
│   ├─ pattern_height = max(peak1_price, peak2_price) - neckline
│   ├─ entry_price = current_price
│   ├─ stop_loss = max(peak1, peak2) + (ATR * atr_stop_multiplier)
│   ├─ tp1 = neckline - (pattern_height * tp1_multiplier)
│   ├─ tp2 = neckline - (pattern_height * tp2_multiplier)
│   ├─ tp3 = neckline - (pattern_height * tp3_multiplier)
│   └─
│
├─→ [9] CALCULATE CONFIDENCE
│   ├─ peak_symmetry = 1.0 - price_diff
│   ├─ volume_confirmed = True/False
│   ├─ pattern_clarity = 0.8 (base)
│   ├─ confidence = _calculate_pattern_confidence(
│   │                   peak_symmetry, volume_confirmed, pattern_clarity)
│   └─ Weighted average: 0.0-1.0
│
└─→ [10] BUILD & RETURN PATTERN DATA
    └─ PatternData(
        pattern_type=PatternType.M_PATTERN,
        timeframe=_get_timeframe(data),
        confidence=confidence,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit_1=tp1,
        take_profit_2=tp2,
        take_profit_3=tp3,
        direction='short',
        neckline=neckline,
        peak1=peak1_price,
        peak2=peak2_price,
        pattern_height=pattern_height,
        formation_candles=peak2_idx - peak1_idx,
        metadata={'peak1_index': peak1_idx, ...}
    )

END
```

### 2.2 W-Pattern Detection Flow

```
ENTRY: _detect_w_pattern(data, current_price)
│
├─→ [1-2] VALIDATE & EXTRACT (Same as M-Pattern)
│
├─→ [3] FIND TROUGHS
│   ├─ lows = recent['low'].values
│   ├─ troughs = _find_troughs(lows, order=3)
│   │   └─ Uses scipy.signal.argrelextrema (inverse)
│   ├─ Check len(troughs) >= 2
│   │   └─ NO → Return None
│   └─ trough2_idx = troughs[-1]  # Most recent
│       trough1_idx = troughs[-2]  # Previous
│
├─→ [4] CHECK TROUGH SYMMETRY
│   ├─ trough1_price = lows[trough1_idx]
│   ├─ trough2_price = lows[trough2_idx]
│   ├─ price_diff = abs(trough1 - trough2) / trough1
│   ├─ Check price_diff <= tolerance
│   │   └─ NO → Return None
│   └─ YES → Troughs are symmetric
│
├─→ [5] CALCULATE NECKLINE
│   ├─ peak_data = recent.iloc[trough1_idx:trough2_idx+1]
│   ├─ neckline = peak_data['high'].max()
│   └─
│
├─→ [6] CHECK NECKLINE BREAK (BULLISH)
│   ├─ Check current_price > neckline * (1 + threshold)
│   │   └─ NO → Return None (price hasn't broken above)
│   └─ YES → Neckline broken (bullish confirmation)
│
├─→ [7-10] VOLUME, PARAMS, CONFIDENCE (Similar to M-Pattern)
│   └─ But direction='long' and TPs above neckline
│
└─→ RETURN PatternData(direction='long', ...)

END
```

### 2.3 Weekend Trap Detection Flow

```
ENTRY: _detect_weekend_trap(data, current_price)
│
├─→ [1] CHECK FRIDAY CLOSE CAPTURED
│   ├─ Check self.friday_close is not None
│   │   └─ NO → Return None (need Friday close)
│   └─ YES → Have reference price
│
├─→ [2] CHECK IF MONDAY
│   ├─ current_time = data.index[-1]
│   ├─ Check current_time.weekday() == 0 (Monday)
│   │   └─ NO → Return None (only trade Monday)
│   └─ YES → It's Monday
│
├─→ [3] CHECK TIME WINDOW
│   ├─ Check current_time.hour < 4  # First 4 hours
│   │   └─ NO → Return None (window closed)
│   └─ YES → Within Monday trap window
│
├─→ [4] CALCULATE WEEKEND MOVE
│   ├─ weekend_move = (current_price - friday_close) / friday_close
│   ├─ threshold = weekend_trap_threshold (default: 0.02)
│   ├─ Check abs(weekend_move) >= threshold
│   │   └─ NO → Return None (move too small)
│   └─ YES → Significant weekend move
│
├─→ [5] DETERMINE TRAP DIRECTION
│   ├─ IF weekend_move > 0:
│   │   ├─ Weekend was bullish
│   │   ├─ Expect bearish reversal (SHORT)
│   │   └─ direction = 'short'
│   └─ ELSE:
│       ├─ Weekend was bearish
│       ├─ Expect bullish reversal (LONG)
│       └─ direction = 'long'
│
├─→ [6] CALCULATE TRADE PARAMETERS
│   ├─ entry_price = current_price
│   ├─ IF direction == 'short':
│   │   ├─ stop_loss = recent_high + ATR
│   │   └─ tp1/2/3 = friday_close and below
│   └─ ELSE:
│       ├─ stop_loss = recent_low - ATR
│       └─ tp1/2/3 = friday_close and above
│
└─→ RETURN PatternData(
        pattern_type=PatternType.WEEKEND_TRAP,
        direction=direction,
        ...
    )

END
```

### 2.4 Board Meeting Detection Flow

```
ENTRY: _detect_board_meeting(data, current_price)
│
├─→ [1] VALIDATE LOOKBACK
│   ├─ min_len = board_meeting_length_min (default: 6)
│   ├─ max_len = board_meeting_length_max (default: 24)
│   ├─ Check len(data) >= max_len
│   │   └─ NO → Return None
│   └─ lookback = min(max_len, len(data))
│
├─→ [2] IDENTIFY CONSOLIDATION
│   ├─ recent = data.iloc[-lookback:]
│   ├─ high_range = recent['high'].max()
│   ├─ low_range = recent['low'].min()
│   ├─ range_pct = (high_range - low_range) / low_range
│   ├─ threshold = board_range_threshold (default: 0.02)
│   ├─ Check range_pct < threshold
│   │   └─ NO → Return None (range too wide)
│   └─ YES → Tight consolidation found
│
├─→ [3] CHECK VOLUME DECLINE
│   ├─ early_volume = recent.iloc[:len(recent)//2]['volume'].mean()
│   ├─ late_volume = recent.iloc[len(recent)//2:]['volume'].mean()
│   ├─ Check late_volume < early_volume * 0.8
│   │   └─ NO → Volume not declining
│   └─ YES → Volume declining (good sign)
│
├─→ [4] CHECK FOR BREAKOUT
│   ├─ current_candle = data.iloc[-1]
│   ├─ breakout_size = abs(current_candle['close'] - current_candle['open'])
│   ├─ consolidation_range = high_range - low_range
│   ├─ Check breakout_size > consolidation_range * 0.5
│   │   └─ NO → Return None (no breakout yet)
│   └─ YES → Breakout detected
│
├─→ [5] CHECK BREAKOUT VOLUME
│   ├─ current_volume = current_candle['volume']
│   ├─ avg_volume = recent['volume'].mean()
│   ├─ multiplier = board_volume_multiplier (default: 1.5)
│   ├─ Check current_volume >= avg_volume * multiplier
│   │   └─ NO → Return None (volume not confirmed)
│   └─ YES → Volume confirms breakout
│
├─→ [6] DETERMINE DIRECTION
│   ├─ IF current_price > high_range:
│   │   └─ direction = 'long' (bullish breakout)
│   └─ ELSE IF current_price < low_range:
│       └─ direction = 'short' (bearish breakout)
│
├─→ [7] CALCULATE MEASURED MOVE
│   ├─ entry_price = current_price
│   ├─ IF direction == 'long':
│   │   ├─ stop_loss = low_range - ATR
│   │   ├─ tp1 = high_range + (consolidation_range * 1.0)
│   │   ├─ tp2 = high_range + (consolidation_range * 2.0)
│   │   └─ tp3 = high_range + (consolidation_range * 3.0)
│   └─ ELSE (short):
│       ├─ stop_loss = high_range + ATR
│       └─ TPs below low_range
│
└─→ RETURN PatternData(
        pattern_type=PatternType.BOARD_MEETING,
        direction=direction,
        ...
    )

END
```

### 2.5 Three Hits Reversal Flow

```
ENTRY: _detect_three_hits_reversal(data, current_price)
│
├─→ [1] CHECK WEEKLY LEVELS SET
│   ├─ Check self.weekly_high is not None
│   ├─ Check self.weekly_low is not None
│   │   └─ NO → Return None (levels not initialized)
│   └─ YES → Have reference levels
│
├─→ [2] CHECK TOUCH COUNTS
│   ├─ Check self.weekly_high_touches >= 3
│   │   └─ YES → Test for resistance rejection
│   ├─ Check self.weekly_low_touches >= 3
│   │   └─ YES → Test for support rejection
│   └─ Neither >= 3 → Return None
│
├─→ [3] IDENTIFY REJECTION TYPE
│   ├─ IF weekly_high_touches >= 3:
│   │   ├─ Testing resistance (bearish)
│   │   ├─ level = weekly_high
│   │   └─ expected_direction = 'short'
│   └─ ELSE:
│       ├─ Testing support (bullish)
│       ├─ level = weekly_low
│       └─ expected_direction = 'long'
│
├─→ [4] CHECK CURRENT REJECTION
│   ├─ current_candle = data.iloc[-1]
│   ├─ IF testing resistance:
│   │   ├─ Check high touched level (within 0.5%)
│   │   ├─ Check close < level (rejected)
│   │   ├─ Check wick size > 30% of range
│   │   │   └─ NO → Return None (no rejection)
│   │   └─ YES → Rejection confirmed
│   └─ ELSE (testing support):
│       ├─ Check low touched level
│       ├─ Check close > level (rejected)
│       └─ Check wick size sufficient
│
├─→ [5] CALCULATE TRADE PARAMETERS
│   ├─ entry_price = current_price
│   ├─ IF direction == 'short':
│   │   ├─ stop_loss = weekly_high + ATR
│   │   ├─ weekly_range = weekly_high - weekly_low
│   │   ├─ tp1 = level - (weekly_range * 0.3)
│   │   ├─ tp2 = level - (weekly_range * 0.5)
│   │   └─ tp3 = weekly_low (opposite level)
│   └─ ELSE (long):
│       ├─ stop_loss = weekly_low - ATR
│       └─ TPs above level
│
└─→ RETURN PatternData(
        pattern_type=PatternType.THREE_HITS,
        direction=expected_direction,
        ...
    )

END
```

---

## 3. Level Management Flow

### Level Update Process

```
ENTRY: _update_levels(data)
│
├─→ [1] CHECK WEEK ROLLOVER
│   ├─ current_week = data.index[-1].isocalendar()[1]
│   ├─ IF current_week != self.current_week:
│   │   ├─ New week detected (Monday)
│   │   ├─ self.weekly_high = None
│   │   ├─ self.weekly_low = None
│   │   ├─ self.weekly_high_touches = 0
│   │   ├─ self.weekly_low_touches = 0
│   │   ├─ self.current_week = current_week
│   │   └─ Log: "Weekly levels reset"
│   └─
│
├─→ [2] UPDATE WEEKLY HIGH/LOW
│   ├─ recent_highs = data['high'].iloc[-168:]  # Last week
│   ├─ recent_lows = data['low'].iloc[-168:]
│   ├─ IF self.weekly_high is None:
│   │   └─ self.weekly_high = recent_highs.max()
│   │ ELSE:
│   │   └─ self.weekly_high = max(self.weekly_high, recent_highs.max())
│   ├─ IF self.weekly_low is None:
│   │   └─ self.weekly_low = recent_lows.min()
│   │ ELSE:
│   │   └─ self.weekly_low = min(self.weekly_low, recent_lows.min())
│   └─
│
├─→ [3] CHECK DAY ROLLOVER
│   ├─ current_day = data.index[-1].date()
│   ├─ IF current_day != self.current_day:
│   │   ├─ New day detected
│   │   ├─ self.daily_high = None
│   │   ├─ self.daily_low = None
│   │   ├─ self.daily_open_set = False
│   │   ├─ self.current_day = current_day
│   │   └─ Log: "Daily levels reset"
│   └─
│
├─→ [4] CAPTURE DAILY HIGH/LOW (First Hour)
│   ├─ current_hour = data.index[-1].hour
│   ├─ IF current_hour == 0 and not self.daily_open_set:
│   │   ├─ First hour of day
│   │   ├─ self.daily_high = data['high'].iloc[-1]
│   │   ├─ self.daily_low = data['low'].iloc[-1]
│   │   ├─ self.daily_open_set = True
│   │   └─ Log: "Daily open levels captured"
│   └─ Update as day progresses
│
├─→ [5] CAPTURE FRIDAY CLOSE
│   ├─ current_day_of_week = data.index[-1].weekday()
│   ├─ IF current_day_of_week == 4:  # Friday
│   │   ├─ current_hour = data.index[-1].hour
│   │   ├─ IF current_hour >= 22:  # Evening
│   │   │   ├─ self.friday_close = data['close'].iloc[-1]
│   │   │   └─ Log: "Friday close captured: {price}"
│   │   └─
│   └─
│
└─→ [6] TRACK LEVEL TOUCHES
    └─ _track_level_touches(data.iloc[-1])

END
```

### Level Touch Tracking

```
ENTRY: _track_level_touches(candle)
│
├─→ [1] CHECK WEEKLY HIGH TOUCH
│   ├─ IF self.weekly_high is not None:
│   │   ├─ high_distance = abs(candle['high'] - self.weekly_high)
│   │   ├─ threshold = self.weekly_high * 0.005  # 0.5%
│   │   ├─ IF high_distance <= threshold:
│   │   │   ├─ Price touched weekly high
│   │   │   ├─ self.weekly_high_touches += 1
│   │   │   └─ Log: "Weekly high touch #{count}"
│   │   └─
│   └─
│
├─→ [2] CHECK WEEKLY LOW TOUCH
│   ├─ IF self.weekly_low is not None:
│   │   ├─ low_distance = abs(candle['low'] - self.weekly_low)
│   │   ├─ threshold = self.weekly_low * 0.005
│   │   ├─ IF low_distance <= threshold:
│   │   │   ├─ Price touched weekly low
│   │   │   ├─ self.weekly_low_touches += 1
│   │   │   └─ Log: "Weekly low touch #{count}"
│   │   └─
│   └─
│
├─→ [3] CHECK FOR LEVEL BREAK
│   ├─ IF candle['close'] > self.weekly_high * 1.01:
│   │   ├─ Weekly high broken
│   │   ├─ self.weekly_high_touches = 0  # Reset counter
│   │   └─ Log: "Weekly high broken, counter reset"
│   ├─ IF candle['close'] < self.weekly_low * 0.99:
│   │   ├─ Weekly low broken
│   │   ├─ self.weekly_low_touches = 0  # Reset counter
│   │   └─ Log: "Weekly low broken, counter reset"
│   └─
│
└─→ [4] CHECK THREE HITS THRESHOLD
    ├─ IF self.weekly_high_touches >= 3:
    │   └─ Log: "WARNING: Three hits to weekly high - reversal likely"
    ├─ IF self.weekly_low_touches >= 3:
    │   └─ Log: "WARNING: Three hits to weekly low - reversal likely"
    └─

END
```

---

## 4. Session & Timing Flow (DST Auto-Adjusting)

### Session Identification with DST Detection

```
ENTRY: _get_current_session(timestamp)
│
├─→ [1] EXTRACT TIME COMPONENTS
│   ├─ hour = timestamp.hour (UTC)
│   ├─ day_of_week = timestamp.weekday()
│   └─
│
├─→ [2] CHECK WEEKEND
│   ├─ IF day_of_week in [5, 6]:  # Saturday or Sunday
│   │   └─ RETURN Session.WEEKEND
│   └─
│
├─→ [3] DETECT DST STATUS
│   ├─ uk_dst = _is_uk_dst(timestamp)
│   │   └─ TRUE if between last Sun March and last Sun October
│   ├─ us_dst = _is_us_dst(timestamp)
│   │   └─ TRUE if between 2nd Sun March and 1st Sun November
│   └─
│
├─→ [4] GET DST-ADJUSTED SESSION TIMES
│   ├─ session_times = _get_session_times(uk_dst, us_dst)
│   │   └─ Returns dict with adjusted hours:
│   │       {
│   │         'asian': (23, 8),      # No change (Japan no DST)
│   │         'uk': (8, 17) or (7, 16),      # Shifts in summer
│   │         'us': (13, 22) or (12, 21),    # Shifts in summer
│   │         'overlap': (13, 17) or (12, 16)  # Shifts in summer
│   │       }
│   └─
│
├─→ [5] CHECK SESSION BY ADJUSTED HOURS (UTC)
│   ├─ asian_start, asian_end = session_times['asian']
│   ├─ uk_start, uk_end = session_times['uk']
│   ├─ us_start, us_end = session_times['us']
│   ├─ overlap_start, overlap_end = session_times['overlap']
│   │
│   ├─ IF overlap_start <= hour < overlap_end:
│   │   └─ RETURN Session.OVERLAP  # Highest priority
│   ├─ IF uk_start <= hour < overlap_start:
│   │   └─ RETURN Session.LONDON  # London only (before US open)
│   ├─ IF overlap_end <= hour < us_end:
│   │   └─ RETURN Session.NEW_YORK  # NY only (after UK close)
│   ├─ IF asian_start <= hour or hour < asian_end:
│   │   └─ RETURN Session.ASIAN
│   └─ ELSE:
│       └─ RETURN Session.ASIAN  # Default
│
END

Notes:
- System automatically adjusts session boundaries based on DST
- UK: BST (GMT-1) from last Sunday March to last Sunday October
- US: EDT (EST-1) from 2nd Sunday March to 1st Sunday November
- No manual intervention required for DST transitions
```

### DST Detection Helper Functions

```
FUNCTION: _is_uk_dst(timestamp) -> bool
│
├─→ [1] CHECK MONTH BOUNDARIES
│   ├─ IF timestamp.month < 3 or timestamp.month > 10:
│   │   └─ RETURN False  # Nov-Feb, definitely not DST
│   ├─ IF 3 < timestamp.month < 10:
│   │   └─ RETURN True   # Apr-Sep, definitely DST
│   └─
│
├─→ [2] CHECK MARCH (transition in)
│   ├─ IF timestamp.month == 3:
│   │   ├─ Find last Sunday in March
│   │   ├─ IF timestamp >= last_sunday:
│   │   │   └─ RETURN True   # DST active
│   │   └─ ELSE:
│   │       └─ RETURN False  # Before transition
│   └─
│
└─→ [3] CHECK OCTOBER (transition out)
    ├─ IF timestamp.month == 10:
    │   ├─ Find last Sunday in October
    │   ├─ IF timestamp < last_sunday:
    │   │   └─ RETURN True   # Still DST
    │   └─ ELSE:
    │       └─ RETURN False  # After transition
    └─

END

FUNCTION: _is_us_dst(timestamp) -> bool
│
├─→ [1] CHECK MONTH BOUNDARIES
│   ├─ IF timestamp.month < 3 or timestamp.month > 11:
│   │   └─ RETURN False  # Dec-Feb, no DST
│   ├─ IF 3 < timestamp.month < 11:
│   │   └─ RETURN True   # Apr-Oct, definitely DST
│   └─
│
├─→ [2] CHECK MARCH (transition in)
│   ├─ IF timestamp.month == 3:
│   │   ├─ Find 2nd Sunday in March
│   │   ├─ IF timestamp >= second_sunday:
│   │   │   └─ RETURN True
│   │   └─ ELSE:
│   │       └─ RETURN False
│   └─
│
└─→ [3] CHECK NOVEMBER (transition out)
    ├─ IF timestamp.month == 11:
    │   ├─ Find 1st Sunday in November
    │   ├─ IF timestamp < first_sunday:
    │   │   └─ RETURN True
    │   └─ ELSE:
    │       └─ RETURN False
    └─

END

FUNCTION: _get_session_times(uk_dst: bool, us_dst: bool) -> dict
│
├─→ RETURN {
│     'asian': (23, 8),  # No DST adjustment (Japan)
│     'uk': (7, 16) if uk_dst else (8, 17),     # BST vs GMT
│     'us': (12, 21) if us_dst else (13, 22),   # EDT vs EST
│     'overlap': (12, 16) if (uk_dst and us_dst) else
│                 (12, 17) if (not uk_dst and us_dst) else
│                 (13, 16) if (uk_dst and not us_dst) else
│                 (13, 17)  # Both on standard time
│   }
│
END
```

### Timing Score Calculation

```
ENTRY: _analyze_timing(current_session, day_of_week, weekly_phase)
│
├─→ [1] SESSION SCORE
│   ├─ session_scores = {
│   │   Session.OVERLAP: 1.0,      # Best (high volume)
│   │   Session.NEW_YORK: 0.8,     # Very good
│   │   Session.LONDON: 0.8,       # Very good
│   │   Session.ASIAN: 0.5,        # Lower priority
│   │   Session.WEEKEND: 0.3       # Avoid if possible
│   │ }
│   ├─ session_score = session_scores[current_session]
│   └─
│
├─→ [2] DAY OF WEEK SCORE
│   ├─ day_scores = {
│   │   0: 0.7,  # Monday (post-weekend, moderate)
│   │   1: 1.0,  # Tuesday (excellent)
│   │   2: 1.0,  # Wednesday (excellent)
│   │   3: 1.0,  # Thursday (excellent)
│   │   4: 0.7,  # Friday (pre-weekend, moderate)
│   │   5: 0.3,  # Saturday (poor)
│   │   6: 0.3   # Sunday (poor)
│   │ }
│   ├─ day_score = day_scores[day_of_week]
│   └─
│
├─→ [3] WEEKLY CYCLE SCORE
│   ├─ IF weekly_phase == 'early':
│   │   └─ cycle_score = 0.7  # Building direction
│   ├─ IF weekly_phase == 'mid':
│   │   └─ cycle_score = 1.0  # Best for reversals
│   ├─ IF weekly_phase == 'late':
│   │   └─ cycle_score = 0.6  # Less reliable
│   └─
│
├─→ [4] WEIGHTED COMBINATION
│   ├─ timing_score = (
│   │     session_score * 0.5 +    # 50% weight
│   │     day_score * 0.3 +         # 30% weight
│   │     cycle_score * 0.2         # 20% weight
│   │ )
│   └─ RETURN timing_score (0.0-1.0)
│
END
```

---

## 5. Confirmation System Flow

### Confirmation Evaluation

```
ENTRY: _check_confirmations(pattern_data, current_price, data)
│
├─→ [1] INITIALIZE CONFIRMATIONS
│   ├─ confirmations = {
│   │   'pattern': True,          # Always true if we have a pattern
│   │   'volume': False,
│   │   'trend': False,
│   │   'timing': False,
│   │   'level': False
│   │ }
│   └─ confirmations_met = 1  # Pattern confirmation
│
├─→ [2] VOLUME CONFIRMATION
│   ├─ IF self.config.require_volume_confirmation:
│   │   ├─ current_volume = data.iloc[-1]['volume']
│   │   ├─ avg_volume = data['volume'].mean()
│   │   ├─ multiplier = self.config.volume_multiplier
│   │   ├─ IF current_volume >= avg_volume * multiplier:
│   │   │   ├─ confirmations['volume'] = True
│   │   │   ├─ confirmations_met += 1
│   │   │   └─ Log: "Volume confirmed: {vol:.0f} > {threshold:.0f}"
│   │   └─ ELSE:
│   │       └─ Log: "Volume NOT confirmed"
│   └─
│
├─→ [3] TREND ALIGNMENT CONFIRMATION
│   ├─ IF self.config.require_trend_alignment:
│   │   ├─ Calculate trend (e.g., 50-period SMA)
│   │   ├─ trend_direction = 'bullish' if price > SMA else 'bearish'
│   │   ├─ IF pattern_data.direction == 'long' and trend == 'bullish':
│   │   │   ├─ confirmations['trend'] = True
│   │   │   └─ confirmations_met += 1
│   │   ├─ IF pattern_data.direction == 'short' and trend == 'bearish':
│   │   │   ├─ confirmations['trend'] = True
│   │   │   └─ confirmations_met += 1
│   │   └─ ELSE:
│   │       └─ Log: "Trend NOT aligned with pattern"
│   └─
│
├─→ [4] TIMING CONFIRMATION
│   ├─ timing_score = self._analyze_timing(...)
│   ├─ threshold = self.config.timing_threshold (default: 0.6)
│   ├─ IF timing_score >= threshold:
│   │   ├─ confirmations['timing'] = True
│   │   ├─ confirmations_met += 1
│   │   └─ Log: "Timing confirmed: score {score:.2f}"
│   └─ ELSE:
│       └─ Log: "Timing NOT confirmed: score {score:.2f} < {threshold}"
│
├─→ [5] LEVEL CONFIRMATION
│   ├─ level_score = self._analyze_levels(pattern_data, current_price)
│   ├─ threshold = self.config.level_threshold (default: 0.5)
│   ├─ IF level_score >= threshold:
│   │   ├─ confirmations['level'] = True
│   │   ├─ confirmations_met += 1
│   │   └─ Log: "Level confirmed: score {score:.2f}"
│   └─ ELSE:
│       └─ Log: "Level NOT confirmed"
│
├─→ [6] CHECK MINIMUM REQUIREMENT
│   ├─ minimum = self.config.minimum_confirmations
│   ├─ IF confirmations_met >= minimum:
│   │   ├─ Log: "✓ Confirmations met: {met}/{min}"
│   │   └─ RETURN (True, confirmations, confirmations_met)
│   └─ ELSE:
│       ├─ Log: "✗ Insufficient confirmations: {met}/{min}"
│       └─ RETURN (False, confirmations, confirmations_met)
│
END
```

---

## 6. Metadata Construction Flow

### Complete Metadata Assembly

```
ENTRY: _build_signal_metadata(pattern_data, timing_score, level_score, 
                               confirmations, confirmations_met)
│
├─→ [1] BASIC LAYER INFO
│   ├─ metadata = {
│   │   'layer_name': 'layer_tbd',
│   │   'layer_version': '1.0',
│   │   'signal_timestamp': datetime.utcnow(),
│   │ }
│   └─
│
├─→ [2] PATTERN INFORMATION
│   ├─ metadata['pattern_type'] = pattern_data.pattern_type.value
│   ├─ metadata['pattern_confidence'] = pattern_data.confidence
│   ├─ metadata['pattern_timeframe'] = pattern_data.timeframe
│   ├─ metadata['formation_candles'] = pattern_data.formation_candles
│   └─
│
├─→ [3] SCORING INFORMATION
│   ├─ metadata['timing_score'] = timing_score
│   ├─ metadata['level_score'] = level_score
│   ├─ metadata['confirmations_met'] = confirmations_met
│   ├─ metadata['confirmations_required'] = self.config.minimum_confirmations
│   └─ metadata['confirmations'] = confirmations  # Dict of True/False
│
├─→ [4] TRADE PARAMETERS
│   ├─ metadata['entry_price'] = pattern_data.entry_price
│   ├─ metadata['stop_loss'] = pattern_data.stop_loss
│   ├─ metadata['take_profit_1'] = pattern_data.take_profit_1
│   ├─ metadata['take_profit_2'] = pattern_data.take_profit_2
│   ├─ metadata['take_profit_3'] = pattern_data.take_profit_3
│   └─
│
├─→ [5] RISK/REWARD CALCULATIONS
│   ├─ risk = abs(entry_price - stop_loss)
│   ├─ reward1 = abs(take_profit_1 - entry_price)
│   ├─ reward2 = abs(take_profit_2 - entry_price)
│   ├─ reward3 = abs(take_profit_3 - entry_price)
│   ├─ metadata['risk_amount'] = risk
│   ├─ metadata['risk_reward_1'] = reward1 / risk
│   ├─ metadata['risk_reward_2'] = reward2 / risk
│   ├─ metadata['risk_reward_3'] = reward3 / risk
│   └─
│
├─→ [6] CURRENT STATE
│   ├─ metadata['current_price'] = self.current_price
│   ├─ metadata['current_position'] = self.current_position
│   ├─ metadata['current_session'] = self.current_session.value
│   ├─ metadata['current_day'] = self.current_day
│   └─
│
├─→ [7] LEVEL CONTEXT
│   ├─ metadata['weekly_high'] = self.weekly_high
│   ├─ metadata['weekly_low'] = self.weekly_low
│   ├─ metadata['weekly_high_touches'] = self.weekly_high_touches
│   ├─ metadata['weekly_low_touches'] = self.weekly_low_touches
│   ├─ metadata['daily_high'] = self.daily_high
│   ├─ metadata['daily_low'] = self.daily_low
│   └─
│
└─→ [8] PATTERN-SPECIFIC METADATA
    ├─ metadata['pattern_metadata'] = pattern_data.metadata
    │   └─ Contains pattern-specific details like:
    │       - M/W: peak1, peak2, neckline, pattern_height
    │       - Weekend: friday_close, weekend_move
    │       - Board: consolidation_range, breakout_size
    │       - Three Hits: level, touch_count
    └─ RETURN metadata

END
```

---

## 7. Error Handling Flow

### Exception Handling Strategy

```
ENTRY: generate_signal() [with error handling]
│
├─→ TRY:
│   │
│   ├─→ [Main signal generation logic]
│   │
│   └─→ [Return LayerSignal]
│
└─→ EXCEPT SignalGenerationError as e:
    │   ├─ Log: "Signal generation error: {e}"
    │   ├─ Increment error counter
    │   └─ RETURN LayerSignal(
    │       direction='neutral',
    │       confidence=0.0,
    │       strength=0.0,
    │       metadata={'error': str(e)}
    │     )
    │
    └─→ EXCEPT Exception as e:
        ├─ Log: "Unexpected error in Layer TBD: {e}"
        ├─ Log stack trace
        ├─ Increment critical error counter
        └─ RETURN LayerSignal(
            direction='neutral',
            confidence=0.0,
            strength=0.0,
            metadata={'critical_error': str(e)}
          )

END
```

### Input Validation Flow

```
ENTRY: _validate_input(data, current_price)
│
├─→ [1] CHECK DATA TYPE
│   ├─ IF not isinstance(data, pd.DataFrame):
│   │   └─ RAISE SignalGenerationError("Data must be DataFrame")
│   └─
│
├─→ [2] CHECK REQUIRED COLUMNS
│   ├─ required = ['open', 'high', 'low', 'close', 'volume']
│   ├─ FOR col in required:
│   │   ├─ IF col not in data.columns:
│   │   │   └─ RAISE SignalGenerationError(f"Missing column: {col}")
│   │   └─
│   └─
│
├─→ [3] CHECK INDEX TYPE
│   ├─ IF not isinstance(data.index, pd.DatetimeIndex):
│   │   └─ RAISE SignalGenerationError("Index must be DatetimeIndex")
│   └─
│
├─→ [4] CHECK DATA LENGTH
│   ├─ minimum_length = 100
│   ├─ IF len(data) < minimum_length:
│   │   └─ RAISE SignalGenerationError(
│   │       f"Insufficient data: {len(data)} < {minimum_length}")
│   └─
│
├─→ [5] CHECK PRICE VALUE
│   ├─ IF not isinstance(current_price, (int, float)):
│   │   └─ RAISE SignalGenerationError("Price must be numeric")
│   ├─ IF current_price <= 0:
│   │   └─ RAISE SignalGenerationError("Price must be positive")
│   ├─ IF np.isnan(current_price) or np.isinf(current_price):
│   │   └─ RAISE SignalGenerationError("Price is NaN or Inf")
│   └─
│
└─→ [6] CHECK FOR NaN VALUES
    ├─ IF data[required].isnull().any().any():
    │   └─ RAISE SignalGenerationError("Data contains NaN values")
    └─ RETURN True  # Validation passed

END
```

---

## Summary Flow Diagram

### Complete System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER TBD ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────┐
            │    INPUT: OHLCV DataFrame         │
            │    current_price, position        │
            └────────────┬──────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Indicators  │ │    Levels    │ │   Patterns   │
│  - ATR       │ │  - Weekly    │ │  - M/W       │
│  - Session   │ │  - Daily     │ │  - Weekend   │
│  - Cycle     │ │  - Touches   │ │  - Board     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Pattern Found?       │
            └───┬───────────────┬───┘
                │ No            │ Yes
                │               │
                │               ▼
                │     ┌─────────────────┐
                │     │ Analyze Timing  │
                │     │ Analyze Levels  │
                │     └────────┬────────┘
                │              │
                │              ▼
                │     ┌─────────────────┐
                │     │ Check           │
                │     │ Confirmations   │
                │     └────────┬────────┘
                │              │
                │              ▼
                │     ┌─────────────────┐
                │     │ Calculate       │
                │     │ Confidence      │
                │     └────────┬────────┘
                │              │
                ▼              ▼
        ┌────────────────────────────┐
        │   Build LayerSignal        │
        │   - direction              │
        │   - confidence             │
        │   - strength               │
        │   - metadata               │
        └────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   RETURN SIGNAL       │
            └───────────────────────┘
```

---

**Document Version**: 1.0  
**Created**: December 27, 2025  
**Author**: BTC Scalp Bot Development Team  
**Purpose**: Complete flow visualization for Layer TBD implementation

**Usage**: Reference this document when:
- Understanding signal generation process
- Debugging pattern detection
- Implementing new patterns
- Troubleshooting confirmation logic
- Extending layer functionality
