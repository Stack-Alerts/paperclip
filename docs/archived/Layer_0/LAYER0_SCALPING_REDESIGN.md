# Layer 0 Redesign: Multi-Timeframe Trend Master

## Critical Understanding

**Layer 0's ONLY Purpose**: Be absolutely incredible at determining trend direction and setting overall bias.

- Layer 0 does NOT generate trades
- Layer 0 does NOT look for opportunities  
- Layer 0 provides TREND CONTEXT for other layers
- Layer 1/6 find opportunities WITHIN Layer 0's identified trend

## Problem Statement  

Current Layer 0 FAILS at its core purpose - trend identification:
- 12.5% accuracy identifying LONG trends
- 9.5% accuracy identifying SHORT trends
- 70% accuracy on NEUTRAL (good, but missing opportunities)
- Only useful output 10 times in 365 days

**The validation proves Layer 0 cannot be trusted to identify trend direction.**

## Root Cause

Layer 0 uses overly simplistic logic:
- Requires ALL timeframes to align (4H+2H+1H)
- Binary thinking (ONLY bullish or ONLY bearish)
- Ignores the reality of nested timeframes
- Too conservative for scalping timeframes

## Multi-Timeframe Trend Reality

### Timeframe Hierarchy for 15-Minute Trading

**4-Hour (Master Trend)**:
- Provides PRIMARY BIAS
- Changes infrequently (days/weeks)
- Cannot be ignored, but doesn't dictate every scalp
- Example: 4H bullish means look for LONG setups primarily, but SHORT scalps valid during pullbacks

**2-Hour (Intermediate Trend)**:
- Defines the current SWING
- More responsive than 4H
- Critical for understanding if we're in a pullback or continuation
- Example: 4H bullish + 2H bearish = Bearish pullback in bullish trend

**1-Hour (Short-Term Trend)**:
- PRIMARY TIMEFRAME for scalp context
- Most important for 15m entries
- Defines immediate market structure
- Example: 1H bullish = Look for LONG 15m entries

**30-Minute (Micro Trend)**:
- Direct context for 15m scalps
- Shows acceleration/deceleration
- Helps time entries precisely
- Example: 30m reversal signals potential 1H reversal

**15-Minute (Entry Timeframe)**:
- NOT analyzed by Layer 0 (Layer 1's job)
- Layer 1 uses this for entry signals
- Layer 0 provides the context, Layer 1 finds the entry

## Intelligent Multi-Timeframe Trend Logic

Layer 0 must be SMART about nested timeframes, not just require alignment.

### Scenario 1: Full Alignment (STRONG BIAS)
```
4H: BULLISH (strong, score >1.2)
2H: BULLISH  
1H: BULLISH
30m: BULLISH
→ Bias: STRONG_LONG
→ Message: "All timeframes bullish - high confidence longs"
→ Risk Manager: Increase position size, wider stops
```

### Scenario 2: Pullback in Uptrend (LONG_PREFERRED)
```
4H: BULLISH (strong)
2H: BEARISH (pullback)
1H: BEARISH (pullback)
30m: BULLISH (reversal starting)
→ Bias: LONG_PREFERRED
→ Message: "Pullback ending in uptrend - look for long entries"
→ This is PERFECT for 15m scalps!
```

### Scenario 3: Trend Change in Progress (MIXED)
```
4H: BULLISH (weakening)
2H: BEARISH (new trend)
1H: BEARISH (confirming)
30m: BEARISH (strong)
→ Bias: SHORT_EMERGING
→ Message: "Trend changing bearish - cautious shorts, avoid longs"
→ Risk Manager: Smaller positions, tight stops
```

### Scenario 4: Ranging Market (BOTH)
```
4H: NEUTRAL
2H: NEUTRAL
1H: NEUTRAL (choppy)
30m: Mixed (alternating)
→ Bias: RANGE_BOUND
→ Message: "No clear trend - range trading only, tight stops"
→ Risk Manager: Reduce size significantly
```

### Scenario 5: Counter-Trend Opportunity (BOTH_CAUTIOUS)
```
4H: BULLISH (strong)
2H: BULLISH
1H: BEARISH (strong reversal, score <-1.0)
30m: BEARISH (confirming)
→ Bias: BOTH_CAUTIOUS
→ Message: "1H counter-trend - allow short scalps with tight stops, prefer longs"
→ Risk Manager: Normal long size, reduced short size
```

## Proposed Changes

### 1. Tiered Trend Authority

```python
TIMEFRAME_AUTHORITY = {
    '4h': {
        'weight': 0.30,  # Reduced from 0.50
        'veto_power': False,  # Can't veto lower TF signals
        'influence': 'bias_only'  # Provides context, not mandate
    },
    '2h': {
        'weight': 0.25,
        'veto_power': False,
        'influence': 'moderate'  # Strong influence but not absolute
    },
    '1h': {
        'weight': 0.25,  # Increased from 0.15
        'veto_power': True,  # Can veto if STRONG counter-trend
        'influence': 'strong'  # Primary timeframe for scalps
    },
    '30m': {
        'weight': 0.15,  # Increased from 0.07
        'veto_power': False,
        'influence': 'direct'  # Direct context for entries
    },
    '15m': {
        'weight': 0.05,  # NEW!
        'veto_power': False,
        'influence': 'entry_timing'  # Entry/exit signals only
    }
}
```

### 2. Intelligent Trend Determination Logic

```python
def determine_multi_tf_trend(tf_signals):
    """
    Layer 0's CORE LOGIC: Determine trend with intelligence about nested timeframes.
    
    This is what makes Layer 0 incredible at trend identification.
    """
    
    tf_4h = tf_signals['4h']
    tf_2h = tf_signals['2h']
    tf_1h = tf_signals['1h']
    tf_30m = tf_signals['30m']
    
    # Extract trends and scores
    trend_4h = tf_4h['trend']
    trend_2h = tf_2h['trend']
    trend_1h = tf_1h['trend']
    trend_30m = tf_30m['trend']
    
    score_4h = tf_4h['score']
    score_2h = tf_2h['score']
    score_1h = tf_1h['score']
    score_30m = tf_30m['score']
    
    # === SCENARIO 1: FULL ALIGNMENT (Strongest signal) ===
    if (trend_4h == trend_2h == trend_1h and abs(score_4h) > 0.8):
        if trend_4h == 'BULLISH':
            return {
                'bias': 'STRONG_LONG',
                'confidence': 0.95,
                'message': 'All major timeframes bullish - strong uptrend',
                'allowed_directions': ['LONG'],
                'risk_level': 'LOW'
            }
        elif trend_4h == 'BEARISH':
            return {
                'bias': 'STRONG_SHORT',
                'confidence': 0.95,
                'message': 'All major timeframes bearish - strong downtrend',
                'allowed_directions': ['SHORT'],
                'risk_level': 'LOW'
            }
    
    # === SCENARIO 2: PULLBACK IN TREND (Best scalping!) ===
    # 4H strong one direction, but 1H/30m opposite (pullback ending)
    if abs(score_4h) > 1.0:
        # Bullish 4H, bearish pullback ending
        if trend_4h == 'BULLISH' and trend_1h == 'BEARISH':
            # Check if pullback is ending (30m reversing)
            if trend_30m == 'BULLISH' or (score_1h > -0.5):  # Weak bearish = ending
                return {
                    'bias': 'LONG_PULLBACK_ENTRY',
                    'confidence': 0.85,
                    'message': 'Bullish pullback ending - prime long entry zone',
                    'allowed_directions': ['LONG', 'SHORT_SCALP'],
                    'risk_level': 'LOW'
                }
        
        # Bearish 4H, bullish pullback ending
        elif trend_4h == 'BEARISH' and trend_1h == 'BULLISH':
            if trend_30m == 'BEARISH' or (score_1h < 0.5):
                return {
                    'bias': 'SHORT_PULLBACK_ENTRY',
                    'confidence': 0.85,
                    'message': 'Bearish pullback ending - prime short entry zone',
                    'allowed_directions': ['SHORT', 'LONG_SCALP'],
                    'risk_level': 'LOW'
                }
    
    # === SCENARIO 3: TREND CHANGING ===
    # Higher TF one way, lower TFs reversing
    if trend_4h != trend_1h and abs(score_1h) > 0.8:
        # 1H strongly against 4H = potential trend change
        if trend_1h == 'BEARISH' and trend_30m == 'BEARISH':
            return {
                'bias': 'SHORT_EMERGING',
                'confidence': 0.70,
                'message': 'Bearish trend emerging on lower timeframes',
                'allowed_directions': ['SHORT', 'LONG_CAUTION'],
                'risk_level': 'MODERATE'
            }
        elif trend_1h == 'BULLISH' and trend_30m == 'BULLISH':
            return {
                'bias': 'LONG_EMERGING',
                'confidence': 0.70,
                'message': 'Bullish trend emerging on lower timeframes',
                'allowed_directions': ['LONG', 'SHORT_CAUTION'],
                'risk_level': 'MODERATE'
            }
    
    # === SCENARIO 4: 1H + 30M AGREEMENT (Scalp timeframe) ===
    if trend_1h == trend_30m and trend_1h != 'NEUTRAL':
        if trend_1h == 'BULLISH':
            return {
                'bias': 'LONG_PREFERRED',
                'confidence': 0.75,
                'message': '1H and 30m bullish - favor long scalps',
                'allowed_directions': ['LONG', 'SHORT_SCALP'],
                'risk_level': 'MODERATE'
            }
        else:
            return {
                'bias': 'SHORT_PREFERRED',
                'confidence': 0.75,
                'message': '1H and 30m bearish - favor short scalps',
                'allowed_directions': ['SHORT', 'LONG_SCALP'],
                'risk_level': 'MODERATE'
            }
    
    # === SCENARIO 5: RANGING / NEUTRAL ===
    neutral_count = sum(1 for t in [trend_4h, trend_2h, trend_1h] if t == 'NEUTRAL')
    if neutral_count >= 2:
        return {
            'bias': 'RANGE_BOUND',
            'confidence': 0.60,
            'message': 'No clear trend - range trading conditions',
            'allowed_directions': ['BOTH'],
            'risk_level': 'HIGH'
        }
    
    # === SCENARIO 6: MIXED / UNCLEAR ===
    return {
        'bias': 'MIXED',
        'confidence': 0.50,
        'message': 'Mixed signals across timeframes - trade with caution',
        'allowed_directions': ['BOTH'],
        'risk_level': 'HIGH'
    }
```

### 3. Rich Trend Context Output

Layer 0 returns comprehensive trend intelligence:

```python
{
    # Primary outputs (for compositor)
    'bias': 'LONG_PULLBACK_ENTRY',  # Descriptive bias
    'allowed_directions': ['LONG', 'SHORT_SCALP'],  # What's allowed
    'confidence': 0.85,  # 0-1, how confident
    
    # Context for other layers
    'message': 'Bullish pullback ending - prime long entry zone',
    'risk_level': 'LOW',  # LOW, MODERATE, HIGH
    
    # Detailed timeframe breakdown
    'timeframes': {
        '4h': {'trend': 'BULLISH', 'score': 1.2, 'strength': 'STRONG'},
        '2h': {'trend': 'BEARISH', 'score': -0.3, 'strength': 'WEAK'},
        '1h': {'trend': 'BEARISH', 'score': -0.4, 'strength': 'WEAK'},
        '30m': {'trend': 'BULLISH', 'score': 0.6, 'strength': 'MODERATE'}
    },
    
    # Alignment status
    'alignment': {
        'status': 'PULLBACK',  # ALIGNED, PULLBACK, DIVERGING, MIXED
        'primary_tf': '4h',  # Which TF dominates
        'counter_tf': '1h'   # Which TF counters (if any)
    },
    
    # Risk management guidance
    'position_guidance': {
        'long_size_multiplier': 1.2,  # Increase longs
        'short_size_multiplier': 0.5,  # Reduce shorts
        'stop_distance_multiplier': 1.0  # Normal stops
    }
}
```

## Expected Improvements

### Before (Current - FAILING):
- 12.5% LONG trend accuracy ❌
- 9.5% SHORT trend accuracy ❌  
- 70% NEUTRAL accuracy ✅
- Only 10 useful signals in 365 days
- Binary thinking (ONLY or NONE)

### After (Proposed - INCREDIBLE):
- 70%+ trend accuracy across all directions ✅
- 50-100 LONG_PREFERRED periods per 60 days
- 30-60 SHORT_PREFERRED periods per 60 days
- 20-30 PULLBACK_ENTRY signals per 60 days (best scalps!)
- 10-15 EMERGING trends caught early
- Intelligent nested timeframe understanding
- Rich context for risk management

## Implementation Plan

1. ✅ Documented current Layer 0 failure
2. ✅ Validated 365 days (12.5% / 9.5% accuracy)
3. ✅ Designed intelligent multi-TF logic
4. [ ] Implement new `determine_multi_tf_trend()` function
5. [ ] Update Layer 0 to output rich trend context
6. [ ] Test on 365 days with new logic
7. [ ] Validate: Should achieve 70%+ accuracy
8. [ ] Update compositor to use new bias types
9. [ ] Update risk manager to use position guidance

## Success Criteria - Layer 0 ONLY

**Layer 0 must be INCREDIBLE at trend identification**:

✅ **Accuracy**: 70%+ on trend direction (up from 12.5% / 9.5%)
✅ **Coverage**: Identify 100+ trend periods per 60 days (up from ~3)
✅ **Intelligence**: Detect pullbacks, trend changes, ranging
✅ **Context**: Provide rich information for risk manager
✅ **Confidence**: High confidence on clear trends, low on mixed

**NOT Layer 0's job** (other layers handle this):
❌ Generate trade signals (Layer 1/6)
❌ Find entry points (Layer 1/6)
❌ Filter quality (Layers 2-5)
❌ Execute trades (Trading engine)

**Layer 0 = Trend Master. Nothing more, nothing less.**
