# RSI (Relative Strength Index) Building Block

**Block Number:** 16/66 | **Category:** Oscillators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Momentum oscillator measuring speed and magnitude of price changes to identify overbought/oversold conditions.

## 🚨 CRITICAL: MULTIPLE FILTERS REQUIRED

**RSI Divergence generates 11 signals/day (11.52% signal rate).**

**THIS IS THE HIGHEST SIGNAL RATE OF ALL 67 BLOCKS TESTED.**

**DO NOT use standalone or with single filter - EXTREME whipsaw risk.**

### Signal Frequency Analysis

```
Without Filters:
  - 1,980 signals per 180 days (11/day)
  - Result: SEVERE WHIPSAW RISK - Account destruction potential
  - Drawdown: Catastrophic

With Trend Filter Only:
  - ~514 signals per 180 days (2.86/day)
  - Result: STILL TOO MANY - High whipsaw risk
  - NOT SAFE with single filter alone

With Trend + 1 Confluence Block:
  - ~62 signals per 180 days (0.34/day)
  - Result: Acceptable frequency
  - Much higher quality

With Trend + 2 Confluence Blocks:
  - ~12 signals per 180 days (0.07/day)
  - Result: Premium quality setups
  - Optimal risk/reward
```

### ✅ MINIMUM SAFE Usage (Triple Filter Required)

```python
# MINIMUM SAFE: RSI with trend filter + confluence (REQUIRED)
from src.detectors.building_blocks.moving_averages.ema_20_50_trend import EMA2050Trend
from src.detectors.building_blocks.oscillators.rsi import RSIDivergence
from src.detectors.building_blocks.structure.order_blocks import OrderBlockDetector

def generate_signal_MINIMUM_SAFE(df):
    # MANDATORY: Trend filter + at least 1 confluence
    trend = EMA2050Trend()
    rsi = RSIDivergence()
    order_block = OrderBlockDetector()  # REQUIRED confluence
    
    trend_result = trend.analyze(df)
    rsi_result = rsi.analyze(df)
    order_block_result = order_block.analyze(df)
    
    if (
        trend_result['signal'] == 'BULLISH' and      # Filter 1: Trend (cuts 50%)
        rsi_result['signal'] == 'BULLISH' and         # Generator: RSI oversold
        order_block_result['signal'] == 'BULLISH'     # Filter 2: Confluence (cuts 88%)
    ):
        return 'ENTER_LONG'  # ✅ Acceptable - triple filtered (0.34/day)
    
    return 'NO_SIGNAL'
```

### ⚠️ INSUFFICIENT: Single Filter (NOT SAFE)

```python
# INSUFFICIENT: RSI with only trend filter (STILL TOO MANY SIGNALS)
def generate_signal_INSUFFICIENT(df):
    trend = EMA2050Trend()
    rsi = RSIDivergence()
    
    trend_result = trend.analyze(df)
    rsi_result = rsi.analyze(df)
    
    if (
        trend_result['signal'] == 'BULLISH' and  # Only 1 filter
        rsi_result['signal'] == 'BULLISH'
    ):
        return 'ENTER_LONG'  # ⚠️ NOT SAFE - 514 signals (2.86/day) - still too many
    
    return 'NO_SIGNAL'
```

### ❌ CATASTROPHIC: RSI Standalone (ACCOUNT DESTRUCTION)

```python
# EXTREMELY DANGEROUS: RSI standalone - NEVER DO THIS
def generate_signal_CATASTROPHIC(df):
    rsi = RSIDivergence()
    rsi_result = rsi.analyze(df)
    
    if rsi_result['signal'] == 'BULLISH':
        return 'ENTER_LONG'  # ❌ ACCOUNT DESTRUCTION - 11 signals/day!
    
    return 'NO_SIGNAL'
```

### Required Filters (MANDATORY)

**MINIMUM REQUIREMENTS:**
1. **Trend Filter** (EMA 20/50 Trend - MANDATORY) - cuts signals by 50%
2. **At least 1 Confluence Block** (REQUIRED) - cuts signals by 88%+

**RECOMMENDED:**
1. **Trend Filter** (EMA 20/50 Trend)
2. **Confluence 1** (Order blocks, structure, liquidity)
3. **Confluence 2** (Volume, momentum, time-based)

**Result:** ~12 premium signals per 180 days (0.07/day) = Safe trading frequency

**Bottom Line:** RSI is THE MOST FREQUENT GENERATOR (11.52%). Single filter is INSUFFICIENT. Requires trend filter + AT LEAST 1-2 confluence blocks. Never use standalone - account destruction risk.

## Technical Specifications
**RSI:** 100 - [100 / (1 + RS)], where RS = Average Gain / Average Loss over 14 periods
**Range:** 0-100
- **70-100:** Overbought (potential reversal down)
- **30-0:** Oversold (potential reversal up)
- **50:** Neutral/equilibrium
**File:** `src/detectors/building_blocks/oscillators/rsi.py`

## Bitcoin Implementation
- Bitcoin RSI >70 on 4hr chart = caution (overbought but can stay there in trends)
- RSI <30 = oversold (bullish reversal possible)
- **RSI Divergence = most powerful signal** (75-80% accuracy)
- In strong Bitcoin trends, RSI can stay >70 or <30 for extended periods
- Use with trend confirmation - don't fade trends based solely on RSI

## Trading Strategies

**Strategy 1: RSI Divergence (75-80% win rate)**
- Bullish Divergence: Price lower low, RSI higher low = buy signal
- Bearish Divergence: Price higher high, RSI lower high = sell signal
- Most reliable reversal indicator
- Combine with support/resistance

**Strategy 2: Oversold Bounce (65-70% win rate)**
- RSI <30 in uptrend = pullback opportunity
- Wait for RSI to turn up from <30
- Entry on bullish confirmation
- Not effective in downtrends

## Confluence
- RSI Divergence + MACD Divergence = +30 points (double divergence)
- RSI <30 + Order Block = +25 points
- RSI >70/<30 + Support/Resistance = +20 points

## Key Characteristics
- 14-period standard
- 70 = overbought, 30 = oversold
- Divergence most reliable
- Can stay extreme in trends
- 50 = momentum shift

**Status:** ✅ Ready | **Tests:** `test_rsi.py`

---
*End of RSI Documentation*
