# Bollinger Bands Building Block

**Block Number:** 55/66 | **Category:** Volatility | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Volatility bands plotted at standard deviations above/below moving average - identifies overbought/oversold and volatility expansion/contraction.

## Technical Specifications
**Middle Band:** 20-period SMA
**Upper Band:** Middle + (2 × StdDev)
**Lower Band:** Middle - (2 × StdDev)
**File:** `src/detectors/building_blocks/volatility/bollinger_bands.py`

## Bitcoin Implementation
- Bitcoin touches bands ~95% of time (by design)
- Band squeeze (narrow bands) = low volatility, breakout imminent
- Band expansion = high volatility, trending market
- Walk the band = strong trend (price rides upper/lower band)
- Reversal at bands only in ranging markets

## Trading Strategies

**Strategy 1: Band Bounce (Range - 65% win rate)**
- Setup: Ranging market (ADX <25)
- Entry: Touch lower band = buy, upper band = sell
- Stop: Beyond band
- Target: Middle band or opposite band

**Strategy 2: Squeeze Breakout (75% win rate)**
- Setup: Bands squeeze (narrowest in 50+ bars)
- Wait for expansion and breakout
- Entry: Direction of breakout
- Stop: Opposite band
- Target: 1-2 ATR extension

## Confluence
- BB Squeeze + Volume contraction = +20 points (breakout setup)
- BB Walk + ADX >25 = +15 points (strong trend)
- Touch band + RSI extreme = +15 points (reversal)

## Key Characteristics
- 20, 2 standard settings (SMA, StdDev)
- Squeeze = breakout coming
- Expansion = volatility
- Walk the band = strong trend
- Reversals only in ranges

**Status:** ✅ Ready | **Tests:** `test_bollinger_bands.py`

---
*End of Bollinger Bands Documentation*
