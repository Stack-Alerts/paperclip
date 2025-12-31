# Stochastic Oscillator Building Block

**Block Number:** 17/66 | **Category:** Oscillators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Momentum indicator comparing closing price to price range over period, identifying overbought/oversold conditions.

## Technical Specifications
**%K (Fast):** [(Close - Low14) / (High14 - Low14)] × 100
**%D (Slow):** 3-period SMA of %K
**Range:** 0-100
- **80-100:** Overbought
- **20-0:** Oversold
**File:** `src/detectors/building_blocks/oscillators/stochastic.py`

## Bitcoin Implementation
- Bitcoin Stochastic >80 on 4hr = overbought (reversal possible)
- <20 = oversold (rally possible)
- %K crossing %D = trade signal
- More sensitive than RSI (faster reversals)
- Divergence signals powerful in Bitcoin

## Trading Strategies

**Strategy 1: Stochastic Cross (65-70% win rate)**
- Setup: Stochastic in extreme zone
- Bullish: %K crosses above %D below 20
- Bearish: %K crosses below %D above 80
- Entry: After cross with confirmation
- Not effective mid-range (40-60)

**Strategy 2: Divergence**
- Price higher high, Stochastic lower high = bearish
- Price lower low, Stochastic higher low = bullish
- 75%+ win rate with support/resistance

## Confluence
- Stochastic Divergence + RSI Divergence = +30 points
- Cross in extreme + Order Block = +25 points
- Stochastic + Volume confirmation = +15 points

## Key Characteristics
- 14, 3, 3 standard settings
- 80 = overbought, 20 = oversold
- %K/%D crossovers = signals
- More sensitive than RSI
- Divergence powerful

**Status:** ✅ Ready | **Tests:** `test_stochastic.py`

---
*End of Stochastic Oscillator Documentation*

🎉 **OSCILLATORS CATEGORY COMPLETE! (2/2 blocks)**
