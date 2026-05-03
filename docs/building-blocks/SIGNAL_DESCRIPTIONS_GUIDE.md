# Signal Descriptions Guide - Strategy Builder UX Enhancement
**Date:** 2026-01-15  
**Purpose:** Add user-friendly descriptions to all 83 building blocks for strategy builder

## Overview

Every signal in every building block must include a `description` field in the signal_tiers dictionary. This enhances strategy builder UX by:
- Explaining what each signal means to traders
- Providing trading implications and recommendations
- Helping users make informed decisions when building strategies
- Reducing learning curve for new users

## Pattern - How to Add Descriptions

### BEFORE (No descriptions):
```python
signal_tiers={
    'BULLISH_SIGNAL': {
        'base_points': 25,
        'formula': 'scaled'
    },
    'BEARISH_SIGNAL': {
        'base_points': 25,
        'formula': 'scaled'
    },
    'NEUTRAL': {
        'points': 0
    }
}
```

### AFTER (With descriptions):
```python
signal_tiers={
    'BULLISH_SIGNAL': {
        'base_points': 25,
        'formula': 'scaled',
        'description': 'Bullish pattern detected - Price likely to rise. Enter long positions. Use tight stops below pattern support.'
    },
    'BEARISH_SIGNAL': {
        'base_points': 25,
        'formula': 'scaled',
        'description': 'Bearish pattern detected - Price likely to fall. Enter short positions. Use tight stops above pattern resistance.'
    },
    'NEUTRAL': {
        'points': 0,
        'description': 'No pattern detected - Market in equilibrium. Wait for clear signal before entering.'
    }
}
```

## Description Writing Guidelines

### 1. Structure (3 parts)
Each description should follow this structure:
```
[What it is] - [Trading implication] - [Action recommendation]
```

### 2. Length
- **Ideal:** 1-2 sentences (10-20 words)
- **Maximum:** 3 sentences
- **Minimum:** 1 complete sentence

### 3. Tone
- **Clear and direct** - No jargon unless necessary
- **Action-oriented** - Tell traders what to do
- **Professional** - Trading language, not casual
- **Educational** - Explain the "why" briefly

### 4. Content Requirements
All descriptions MUST include:
- ✅ What the signal indicates
- ✅ Trading direction or bias
- ✅ At least ONE actionable recommendation

### 5. Examples by Signal Type

#### Pattern Signals
```python
'M_TOP_CONFIRMED': {
    'description': 'M pattern (double top) confirmed - Bearish reversal. Short position favorable. Set stops above second peak.'
}

'W_BOTTOM_CONFIRMED': {
    'description': 'W pattern (double bottom) confirmed - Bullish reversal. Long position favorable. Set stops below second trough.'
}
```

#### Directional Signals (BULLISH/BEARISH/NEUTRAL)
```python
'BULLISH': {
    'description': 'Bullish bias - Upward momentum detected. Long positions favorable. Trail stops during uptrend.'
}

'BEARISH': {
    'description': 'Bearish bias - Downward momentum detected. Short positions favorable. Trail stops during downtrend.'
}

'NEUTRAL': {
    'description': 'No directional bias - Market in equilibrium. Wait for confirmation before entering.'
}
```

#### Status Signals (ERROR/INSUFFICIENT_DATA)
```python
'ERROR': {
    'description': 'Data validation error - Cannot calculate indicator. Check data quality and format.'
}

'INSUFFICIENT_DATA': {
    'description': 'Insufficient data - Need more candles to calculate. Wait for additional data.'
}
```

#### Level/Regime Signals
```python
'EXTREME_HIGH': {
    'description': 'Extreme high level detected - Unsustainable. Expect reversal or consolidation. Reduce position sizes.'
}

'EXTREME_LOW': {
    'description': 'Extreme low level detected - Oversold condition. Expect bounce or accumulation. Watch for reversal setup.'
}
```

## Complete Example: ATR Building Block

See `src/detectors/building_blocks/volatility/atr.py` for the complete implementation.

Key signals:
```python
'EXTREME': {
    'base_points': 10,
    'formula': 'scaled',
    'description': 'Extreme volatility - Market moving >2000 USD per 15min. Use very wide stops (3x+ ATR).'
}

'VERY_HIGH': {
    'base_points': 10,
    'formula': 'scaled',
    'description': 'Very high volatility - Large price swings. Use wider stops (2.5x ATR). Favorable for breakouts.'
}

'NORMAL': {
    'base_points': 7,
    'formula': 'scaled',
    'description': 'Normal volatility - Regular market activity. Use standard stops (2x ATR). Suitable for all strategies.'
}

'CALM': {
    'base_points': 6,
    'formula': 'scaled',
    'description': 'Low volatility - Tight consolidation. Use conservative stops (1.5x ATR). Range trading favorable.'
}
```

## Category-Specific Guidelines

### Pattern Blocks (M/W patterns, Triangles, etc.)
Focus on:
- Pattern type and direction
- Entry timing
- Stop placement relative to pattern structure

Example:
```python
'ASCENDING_TRIANGLE_BULLISH': {
    'description': 'Ascending triangle forming - Bullish consolidation. Wait for breakout above resistance. Stop below support line.'
}
```

### Oscillator Blocks (RSI, Stochastic, etc.)
Focus on:
- Overbought/oversold conditions
- Divergences
- Momentum shifts

Example:
```python
'RSI_OVERSOLD': {
    'description': 'RSI below 30 - Oversold condition. Potential bounce setup. Wait for confirmation before long entry.'
}
```

### Price Level Blocks (HOD/LOD, S/R, etc.)
Focus on:
- Level significance
- Rejection vs. breakthrough
- Support/resistance flips

Example:
```python
'HOD_REJECTION': {
    'description': 'Price rejected at HOD - Resistance confirmed. Short setup if breakdown occurs. Stop above HOD.'
}
```

### Session Blocks (Kill zones, sessions)
Focus on:
- Time-based context
- Liquidity expectations
- Session characteristics

Example:
```python
'LONDON_KILL_ZONE': {
    'description': 'London kill zone active - High liquidity period. Institutional activity peaks. Breakouts more reliable.'
}
```

### Wyckoff Blocks (Accumulation, Distribution)
Focus on:
- Phase identification
- Smart money activity
- Volume characteristics

Example:
```python
'ACCUMULATION_PHASE_B': {
    'description': 'Accumulation Phase B - Smart money building positions. Consolidation before markup. Wait for spring or breakout.'
}
```

## Implementation Checklist

For each of the 83 building blocks:

- [ ] 1. Locate the `@register_block` decorator
- [ ] 2. Find the `signal_tiers` dictionary
- [ ] 3. Add `'description':` field to EVERY signal
- [ ] 4. Write clear, actionable descriptions
- [ ] 5. Verify description length (1-2 sentences ideal)
- [ ] 6. Test that description makes sense to non-expert
- [ ] 7. Commit with message: `feat: Add signal descriptions to [block_name]`

## Quality Checklist

Before committing, verify each description:

✅ **Clarity** - Can a beginner understand it?
✅ **Actionable** - Does it tell traders what to do?
✅ **Accurate** - Does it match what the signal actually means?
✅ **Concise** - Is it 1-2 sentences? (3 max)
✅ **Professional** - Appropriate trading language?
✅ **Complete** - All signals have descriptions?

## Testing Descriptions

After adding descriptions, verify they appear correctly:

```python
from src.detectors.building_blocks.registry import BlockRegistry

# Get block metadata
metadata = BlockRegistry.get_block('atr')

# Check signal descriptions
for signal, tier_data in metadata.signal_tiers.items():
    print(f"{signal}: {tier_data.get('description', 'MISSING!')}")
```

## Common Mistakes to Avoid

❌ **Too technical:** "Bollinger Band standard deviation exceeds 2 sigma threshold"
✅ **Better:** "High volatility - Price outside normal range. Expect mean reversion or breakout."

❌ **Too vague:** "Something might happen"
✅ **Better:** "Bullish signal - Upward momentum building. Long positions favorable."

❌ **Too long:** "This signal indicates that the market has entered a consolidation phase where price action is constrained within a tight range and traders should consider reducing position sizes while waiting for a clear breakout signal before entering new positions."
✅ **Better:** "Tight consolidation - Low volatility range. Reduce positions. Wait for breakout."

❌ **Missing action:** "Volatility is high"
✅ **Better:** "High volatility - Use wider stops (2.5x ATR). Breakout trading favorable."

## File Locations

All 83 building blocks are in:
```
src/detectors/building_blocks/
├── patterns/         (M/W patterns, triangles, etc.)
├── oscillators/      (RSI, Stochastic, etc.)
├── price_levels/     (HOD/LOD, support/resistance)
├── sessions/         (Kill zones, sessions)
├── moving_averages/  (EMA, SMA crossovers)
├── market_structure/ (BOS, CHOCH, etc.)
├── volatility/       (ATR, Bollinger Bands) ← ATR already done!
├── institutional/    (Order blocks, FVG, etc.)
├── smc_ict/         (SMC/ICT concepts)
├── wyckoff/         (Accumulation, Distribution)
├── elliott_wave/    (Wave analysis)
├── fibonacci/       (Fib retracements, extensions)
├── price_action/    (Pin bars, engulfing, etc.)
├── supply_demand/   (Supply/demand zones)
└── trend/           (Trend detection, strength)
```

## Strategy Builder Integration

Descriptions will be used in strategy builder UI:

```python
# Strategy Builder uses descriptions like this:
signal_info = registry.get_block('atr').signal_tiers['EXTREME']

# Display to user:
# Signal: EXTREME
# Points: 10
# Description: "Extreme volatility - Market moving >2000 USD per 15min. 
#               Use very wide stops (3x+ ATR)."
#
# [ ] Include this signal in strategy
```

## Completion Goal

**Target:** All 83 building blocks with complete signal descriptions
**Priority:** High - Required for strategy builder UX
**Timeline:** Complete before strategy builder deployment

**Current Status:**
- ✅ ATR (1/83) - Complete with all 13 signal descriptions
- ⏳ Remaining 82 blocks - Need descriptions added

## Next Steps

1. **Choose a category** (e.g., patterns, oscillators)
2. **Open first file** in that category
3. **Find `signal_tiers`** dictionary
4. **Add descriptions** to all signals
5. **Test** that descriptions are clear
6. **Commit** with descriptive message
7. **Repeat** for all files in category
8. **Move to next category**

## Support

If you need examples for specific signal types, refer to:
- **Volatility:** `src/detectors/building_blocks/volatility/atr.py` (complete)
- **This guide:** Examples for all major signal categories above

---

**Remember:** Clear, actionable descriptions = Better strategy builder UX = Happier users! 🎯
