# Ichimoku Cloud Building Block

**Block Number:** 51/66 | **Category:** Trend & Momentum | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Comprehensive indicator system showing trend direction, momentum, support/resistance using 5 components forming a "cloud."

## Technical Specifications
**File:** `src/detectors/building_blocks/trend/ichimoku_cloud.py`

## 5 Components

**1. Tenkan-sen (Conversion Line):** (9-period high + 9-period low) / 2  
**2. Kijun-sen (Base Line):** (26-period high + 26-period low) / 2  
**3. Senkou Span A (Leading Span A):** (Tenkan + Kijun) / 2, plotted 26 periods ahead  
**4. Senkou Span B (Leading Span B):** (52-period high + 52-period low) / 2, plotted 26 periods ahead  
**5. Chikou Span (Lagging Span):** Current close plotted 26 periods back

**The Cloud (Kumo):** Area between Senkou Span A and B  
- Green cloud: Span A > Span B (bullish)
- Red cloud: Span B > Span A (bearish)

## Bitcoin Implementation
- Highly effective on Bitcoin 4hr and daily charts
- Price above green cloud = strong bullish signal
- Price below red cloud = strong bearish signal
- Thick Bitcoin cloud provides reliable support/resistance
- Breakout above cloud with volume = high-probability long
- Bitcoin bull runs often show price walking along cloud top

## Trading Strategy - Cloud Breakout
- Entry: Buy on close above cloud (bullish) or below (bearish)
- Confirm: Tenkan above Kijun, Chikou above price from 26 periods ago
- Stop: Below cloud or Kijun
- Target: Measured move or next major resistance
- Trail stop using Kijun line

## Confluence
- Price above cloud + all components aligned = +30 points
- Cloud twist (color change) = +20 points (reversal signal)
- Thick cloud = +15 points (strong S/R)

**Status:** ✅ Ready | **Tests:** `test_ichimoku_cloud.py`
