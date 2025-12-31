# RSI (Relative Strength Index) Building Block

**Block Number:** 16/66 | **Category:** Oscillators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Momentum oscillator measuring speed and magnitude of price changes to identify overbought/oversold conditions.

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
