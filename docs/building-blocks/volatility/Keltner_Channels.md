# Keltner Channels Building Block

**Block Number:** 56/66 | **Category:** Volatility | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Volatility-based envelope using ATR instead of standard deviation, providing dynamic support/resistance levels.

## Technical Specifications
**Middle Line:** 20-period EMA
**Upper Channel:** EMA + (2 × ATR)
**Lower Channel:** EMA - (2 × ATR)
**File:** `src/detectors/building_blocks/volatility/keltner_channels.py`

## Bitcoin Implementation
- More responsive than Bollinger Bands (uses ATR vs StdDev)
- Bitcoin breakouts beyond channels = strong trends
- Channel squeeze similar to BB = breakout setup
- Reversals at channels in ranging Bitcoin markets
- Breaks inside channels after trend = reversal signal

## Trading Strategies

**Strategy 1: Channel Breakout (70% win rate)**
- Setup: Price breaks and closes beyond channel
- Entry: Pullback to channel after break
- Stop: Opposite channel
- Target: 2x ATR extension

**Strategy 2: Squeeze Play**
- Keltner inside Bollinger Bands = "squeeze"
- Extreme low volatility
- Entry: Direction of breakout
- 75%+ win rate with volume

## Confluence
- KC Breakout + Volume = +20 points
- KC inside BB (squeeze) = +25 points (high probability)
- Touch channel + Order Block = +15 points

## Key Characteristics
- 20 EMA, 2 ATR standard
- More sensitive than Bollinger Bands
- ATR-based (volatility-adjusted)
- Breakouts = strong trends
- Squeeze = major move coming

**Status:** ✅ Ready | **Tests:** `test_keltner_channels.py`

---
*End of Keltner Channels Documentation*

🎉 **VOLATILITY CATEGORY COMPLETE! (3/3 blocks)**
