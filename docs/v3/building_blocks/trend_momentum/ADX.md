# ADX (Average Directional Index) Building Block

**Block Number:** 18/66 | **Category:** Trend & Momentum | **Version:** 2.0 | **Status:** ✅ Complete

---

## ⚠️ CRITICAL USAGE NOTE

**ADX is an ENVIRONMENT DETECTOR, not a directional signal generator!**

**DO NOT USE:** ADX directional signals (BULLISH/BEARISH) for entries - Low confidence (44.11%)  
**DO USE:** ADX VALUE for environment detection (trending vs ranging markets)

---

## Overview

ADX measures trend **STRENGTH**, not direction. It identifies whether the market is trending (tradeable) or ranging (choppy), helping you select the right strategy for current market conditions.

## Correct Usage Model

### ✅ CORRECT: Environment Detection

```python
# Access ADX value from metadata
adx_value = metadata['adx']  # 0-100 scale
trend_strength = metadata['trend_strength']  # WEAK/MODERATE/STRONG/VERY_STRONG
is_tradeable = metadata['tradeable']  # True if adx >= 25

# Use for strategy selection
if adx_value >= 25:
    # TRENDING market - use trend-following strategies
    use_trend_strategies = True
    # Execute: Breakouts, momentum, trend trades
    
else:  # adx_value < 25
    # RANGING market - use mean-reversion strategies
    use_range_strategies = True
    # Execute: Support/resistance bounces, reversals

# Use for risk management
if adx_value > 50:
    position_size = 1.5x  # Strong trend = larger size
elif adx_value > 25:
    position_size = 1.0x  # Normal trend
else:
    position_size = 0.5x  # Weak/ranging = reduce size
```

### ❌ WRONG: Directional Signals

```python
# DON'T DO THIS - Low confidence (44.11%!)
if adx_signal == 'BULLISH':  # ❌ WRONG
    execute_long()  # Will be wrong 56% of the time!
```

---

## Technical Specifications

**ADX:** Based on 12-period (optimized) smoothed DI+ and DI-  
**Values:** 0-100 scale

### ADX Value Interpretation

- **0-25:** Weak/no trend (ranging/choppy)
  - **Action:** Avoid trend-following strategies
  - **Strategy:** Use mean-reversion, support/resistance trading
  
- **25-50:** Moderate trend strength
  - **Action:** Trend strategies workable
  - **Strategy:** Conservative trend-following
  
- **50-75:** Strong trend
  - **Action:** Optimal for trend-following
  - **Strategy:** Aggressive trend trades, larger positions
  
- **75-100:** Very strong trend (rare)
  - **Action:** Extreme trend conditions
  - **Strategy:** Maximum trend exposure

**File:** `src/detectors/building_blocks/trend/adx.py`

---

## Metadata Fields

ADX provides rich metadata for environment analysis:

```python
metadata = {
    'adx': 45.2,                    # ADX value (0-100)
    'plus_di': 28.5,                # +DI indicator
    'minus_di': 15.3,               # -DI indicator
    'trend_strength': 'MODERATE',   # WEAK/MODERATE/STRONG/VERY_STRONG
    'direction': 'BULLISH',         # Which way DI indicators point
    'tradeable': True               # True if adx >= 25
}
```

**Use these fields for:**
- Environment detection (`adx` value)
- Strategy selection (`tradeable`, `trend_strength`)
- Risk management (position sizing based on `adx`)
- Context awareness (`direction` for reference only)

---

## Bitcoin Implementation

### Optimal Usage

**15min Bitcoin Trading:**
- ADX >25 = Trending (use trend strategies: breakouts, momentum, BOS)
- ADX +20 = Ranging (use bounce strategies: S/R, mean-reversion, order block fills)
- Check ADX VALUE before each session to select strategy type

**Risk Management:**
- ADX >50 = Strong trend → Increase position size 1.5x
- ADX 25-50 = Normal → Standard position size 1.0x
- ADX <25 = Ranging → Reduce position size 0.5x or skip trend trades

**Session Trading:**
- Check ADX at session open (London/NY)
- ADX >25 = Execute session startup patterns (optimal expansion)
- ADX <25 = Wait for breakout or avoid trending setups

---

## Trading Strategies

### Strategy 1: Environment-Based Strategy Selection ✅

**Setup:**
1. Calculate ADX value at session start
2. Check `metadata['adx']` and `metadata['tradeable']`

**If ADX >= 25 (Trending):**
- Execute: Trend-following strategies
  - Breakout trades (BOS, CHoCH)
  - Momentum continuation
  - OTE retracement entries
  - Trend filter for all entries

**If ADX < 25 (Ranging):**
- Execute: Range-bound strategies
  - Support/resistance bounces
  - Order block fills
  - Mean reversion
  - Avoid breakout trades

**Risk:** Adjust position sizing based on ADX strength

### Strategy 2: Position Sizing Filter ✅

**Setup:**
- Base strategy generates entry signals
- Use ADX for position sizing

**Position Size Calculation:**
```python
if adx >= 50:
    # Very strong trend
    size = 1.5x to 2.0x
elif adx >= 25:
    # Tradeable trend
    size = 1.0x (standard)
else:
    # Weak/ranging
    size = 0.5x or skip
```

**Result:** Larger positions in strong trends, smaller in weak/choppy markets

### Strategy 3: Confluence Context ⚠️

**Setup:**
- Use ADX as supplementary context ONLY
- Do NOT use as required block

**If base strategy entry AND adx >= 25:**
- Context: "Trending market confirmed"
- Confidence boost: +5 to +10 points (minor)
- Position: Can slightly increase size

**If base strategy entry AND adx < 25:**
- Context: "Ranging market - reduce conviction"
- Confidence: May reduce or skip
- Position: Reduce size or require stronger confluence

---

## Confluence

**DO NOT use ADX for primary confluence** (44.11% directional confidence)

**CAN use for supplementary context:**
- ADX >25 + Trend setup = +5 points (environment confirmed)
- ADX +50 + Momentum setup = +10 points (strong trend)
- ADX <25 = Ignore trend setups OR -10 points (ranging market)

**Remember:** ADX adds ENVIRONMENT context, not directional conviction

---

## Key Characteristics

- **Measures:** Trend strength (0-100 scale)
- **Does NOT measure:** Trend direction reliably (44.11% directional confidence)
- **Best for:** Environment detection, strategy selection, risk management
- **NOT for:** Primary directional signals, required block status, entry triggers
- **Threshold:** 25 (below = ranging, above = trending)
- **Optimal:** 50-75 range for strongest trends

---

## Performance Notes

**Walkforward Test Results (180 days):**
- Signal Rate: 48.60%
- **Directional Confidence: 44.11%** ⚠️ (below 50% - not reliable for direction!)
- Balance: 47/53 (good)
- Errors: 0

**Interpretation:**
- ADX VALUE is useful for environment detection
- ADX DIRECTION (BULLISH/BEARISH signals) is NOT reliable (44.11%)
- Use ADX as environment filter, not signal generator

**Recommendation:**
- ✅ Use ADX value for trending vs ranging detection
- ✅ Use for strategy selection
- ✅ Use for position sizing
- ❌ Do NOT use directional signals for entries
- ❌ Do NOT make ADX a required block

---

## Implementation Example

```python
# In your strategy
def check_market_environment(self, adx_metadata):
    """Determine market environment using ADX"""
    adx_value = adx_metadata['adx']
    
    if adx_value >= 50:
        return {
            'environment': 'STRONG_TREND',
            'strategy_type': 'AGGRESSIVE_TREND_FOLLOWING',
            'position_multiplier': 1.5,
            'notes': 'Optimal trend conditions'
        }
    elif adx_value >= 25:
        return {
            'environment': 'TRENDING',
            'strategy_type': 'TREND_FOLLOWING',
            'position_multiplier': 1.0,
            'notes': 'Tradeable trend'
        }
    else:  # adx_value < 25
        return {
            'environment': 'RANGING',
            'strategy_type': 'MEAN_REVERSION',
            'position_multiplier': 0.5,
            'notes': 'Choppy market - reduce trend exposure'
        }

# Usage
environment = check_market_environment(adx_metadata)
if environment['strategy_type'] == 'TREND_FOLLOWING':
    execute_trend_strategy()
else:
    execute_range_strategy()
```

---

**Status:** ✅ Ready (as environment detector)  
**Tests:** `test_adx.py`  
**Role:** ⚠️ OPTIONAL supplementary context (environment detection ONLY)

---

## Summary

**ADX is a TREND STRENGTH indicator, not a directional signal!**

**Use ADX for:**
- ✅ Environment detection (trending vs ranging)
- ✅ Strategy selection (trend vs range strategies)
- ✅ Position sizing (larger in strong trends)
- ✅ Supplementary context (optional)

**Do NOT use ADX for:**
- ❌ Directional entry signals (44.11% confidence)
- ❌ Required block status
- ❌ Primary confluence calculations
- ❌ Critical decision making

**Key Insight:** ADX tells  you **HOW STRONG** the trend is, not **WHICH WAY** to trade!

---
*End of ADX Documentation - Updated 2026-01-02*
