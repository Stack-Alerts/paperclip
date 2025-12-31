# Double Bottom Pattern Building Block

**Block Number:** 37/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Bullish reversal pattern with two troughs at approximately same price level separated by peak (W-shaped).

## Technical Specifications
**Components:** Two troughs + Peak (neckline)  
**Confirmation:** Close above neckline  
**File:** `src/detectors/building_blocks/patterns/double_bottom.py`

## Bitcoin Implementation
- Strong bullish reversal signal in Bitcoin markets
- Forms at major support levels during corrections
- Second bottom often slightly higher than first (shows buying strength)
- Common at Fibonacci retracement levels (61.8%, 50%, 38.2%)
- Breakout volume >2x average increases success to 75-80%

## Trading Strategy
- Entry: LONG on neckline breakout or pullback retest
- Stop: Below second trough - 1-2%
- Target: Measured move (trough-to-neckline height added to breakout)
- Scale out: 50% at target, 50% at next resistance

## Confluence
- Double Bottom + RSI bullish divergence = +25 points
- Pattern at support = +20 points
- Volume spike on breakout = +15 points

**Status:** ✅ Ready | **Tests:** `test_double_bottom.py`

---
*End of Double Bottom Documentation*
