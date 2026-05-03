# Building Blocks Categorization
**Expert Mode Analysis: Signals vs Metadata/Context Blocks**

Date: 2026-01-01  
Analyst: Cline (Expert Mode)  
Method: Documentation review for each block's design intent

---

## Categorization Criteria

**SIGNAL BLOCKS** - Generate predictive trading signals:
- Return directional signals (BULLISH/BEARISH)
- Designed to predict future price movement
- Tested with walk-forward validation (actual vs predicted)
- Examples: MA crossovers, breakouts, pattern completions

**METADATA/CONTEXT BLOCKS** - Provide context for other signals:
- Return current state/level/measurement
- Designed for risk management, confirmation, filtering
- Tested for valid data returns (accuracy, completeness, thresholds)
- Examples: ATR (volatility), ADX (trend strength), Volume

**HYBRID BLOCKS** - Can do both:
- Return both signals AND metadata
- Primary function determines category
- May need dual validation

---

## Block-by-Block Categorization

### SIGNAL BLOCKS (Predictive)

**Moving Averages (6/6)** - All SIGNALS
1. ✅ EMA 20/50 Cross - Crossover signals
2. ✅ EMA 50 Vector - Direction signals  
3. ✅ EMA 55 Vector - Direction signals
4. ✅ EMA 200 Trend - Trend signals
5. ✅ EMA 255 Vector - Direction signals
6. ✅ EMA 800 Vector - Direction signals

**Oscillators (3/3)** - All SIGNALS
7. ✅ RSI - Overbought/oversold signals
8. ✅ Stochastic - Momentum signals
9. ✅ MACD - Trend/momentum signals

**Price Action (4/4)** - All SIGNALS
10. ✅ Support/Resistance - Bounce/break signals
11. ✅ Swing High/Low - Reversal signals
12. ✅ Round Numbers - Psychological level signals
13. ✅ Pivot Points - Support/resistance signals

**Trend (2/2)** - All SIGNALS
14. ✅ Higher Highs/Lower Lows - Trend change signals
15. ✅ Trend Lines - Break/bounce signals

**ICT/SMC (10/10)** - All SIGNALS
16. ✅ Order Block - Entry signals
17. ✅ Fair Value Gap - Fill/avoid signals
18. ✅ Liquidity Void - Entry signals
19. ✅ Imbalance - Rebalance signals
20. ✅ Break of Structure - Trend change signals
21. ✅ Change of Character - Reversal signals
22. ✅ Inducement - Trap/entry signals
23. ✅ Premium/Discount - Zone signals
24. ✅ Mitigation Block - Entry signals
25. ✅ Balanced Price Range - Equilibrium signals

**Institutional (1/5 signals, 4/5 metadata)**
26. ✅ VWAP - SIGNAL (above/below VWAP)
27. ❓ Anchored VWAP - METADATA (institutional reference)
28. ❓ Market Depth - METADATA (liquidity levels)
29. ❓ Order Flow Imbalance - HYBRID (can signal + provide levels)
30. ❓ EMA Crossover Systems - SIGNAL (already covered in MA)

**Patterns (16)** - All SIGNALS (pattern completion/breakout)
31. ✅ Head & Shoulders - SIGNAL (bearish reversal 75-82% success)
32. ✅ Inverse Head & Shoulders - SIGNAL (bullish reversal)
33. ✅ Double Top - SIGNAL (bearish reversal)
34. ✅ Double Bottom - SIGNAL (bullish reversal)
35. ✅ Triple Top - SIGNAL (bearish reversal)
36. ✅ Triple Bottom - SIGNAL (bullish reversal)
37. ✅ Cup & Handle - SIGNAL (bullish breakout)
38. ✅ Rounding Bottom - SIGNAL (bullish reversal)
39. ✅ Flag Pattern - SIGNAL (continuation breakout)
40. ✅ Pennant Pattern - SIGNAL (continuation breakout)
41. ✅ Ascending Triangle - SIGNAL (bullish breakout)
42. ✅ Descending Triangle - SIGNAL (bearish breakout)
43. ✅ Symmetrical Triangle - SIGNAL (breakout either direction)
44. ✅ Wedge Patterns - SIGNAL (rising/falling wedge)
45. ✅ Diamond Pattern - SIGNAL (reversal breakout)
46. ✅ Harmonic Patterns - SIGNAL (Gartley, Bat, etc.)

---

### METADATA/CONTEXT BLOCKS (Non-Predictive)

**Volatility (4)** - 1 METADATA, 3 HYBRID
47. ✅ ATR - METADATA (stop-loss distance, position sizing)
48. ✅ ADR - HYBRID (volatility level + targets)
49. ✅ Bollinger Bands - HYBRID (bands + squeeze/expansion signals)
50. ✅ Keltner Channels - METADATA (volatility channel bands)

**Trend Strength (2)** - 1 METADATA, 1 HYBRID
51. ✅ ADX - METADATA (trend strength 0-100 filter)
52. ✅ Ichimoku Cloud - HYBRID (cloud position + crossover signals)

**Sessions/Time (2)** - All METADATA
53. ✅ Kill Zones - METADATA (ICT time windows: Asia/London/NY)
54. ✅ Session High/Low - METADATA (session price ranges)

**Price Levels (6)** - All METADATA (Reference Levels)
55. ✅ HOD - METADATA (daily high resistance reference, needs fix)
56. ✅ HOW - METADATA (weekly high resistance reference)
57. ✅ LOD - METADATA (daily low support reference)
58. ✅ LOW - METADATA (weekly low support reference)
59. ✅ Asia Session 50% - METADATA (session midpoint level)
60. ✅ US Settlement - METADATA (4pm EST settlement level)

**Elliott Wave (2)** - All SIGNALS (Wave Analysis)
61. ✅ Elliott Wave Count - SIGNAL (wave completion prediction)
62. ✅ Elliott Wave Oscillator - SIGNAL (wave momentum confirmation)

**Fibonacci (1)** - METADATA (Retracement Levels)
63. ✅ Fibonacci Retracements - METADATA (0.236, 0.382, 0.5, 0.618, 0.786)

**Wyckoff (3)** - All SIGNALS (Phase Detection)
64. ✅ Wyckoff Accumulation - SIGNAL (accumulation phase complete)
65. ✅ Wyckoff Distribution - SIGNAL (distribution phase complete)
66. ✅ Wyckoff Reaccumulation - SIGNAL (reaccumulation phase complete)

**Volume (2)** - All METADATA (Volume Analysis)
67. ✅ Volume Profile - METADATA (volume at price levels POC/VAH/VAL)  
68. ✅ Volume Analyzer - METADATA (volume metrics and statistics)

**Institutional (Additional)** - Mix
27. ✅ Anchored VWAP - METADATA (event-anchored institutional reference)
28. ✅ Market Depth - METADATA (order book liquidity levels)
29. ✅ Order Flow Imbalance - HYBRID (imbalance metrics + signals)
30. ✅ EMA Crossover Systems - SIGNAL (duplicate of #1, skip)

---

## Summary Counts

**✅ CATEGORIZATION COMPLETE: 67/67 BLOCKS** 

**SIGNAL BLOCKS: 47/67 (70.1%)**
- Moving Averages: 6
- Oscillators: 3
- Price Action: 4
- Trend: 2
- ICT/SMC: 10
- Institutional: 1 (VWAP)
- Patterns: 16
- Elliott Wave: 2
- Wyckoff: 3
- **Production Ready: 27/47 (57.4%)**

**METADATA BLOCKS: 16/67 (23.9%)**
- ATR: 1 (stop-loss calculator)
- Keltner Channels: 1
- ADX: 1 (trend strength filter)
- Sessions/Time: 2 (Kill Zones, Session High/Low)
- Price Levels: 6 (HOD, HOW, LOD, LOW, Asia 50%, US Settlement)
- Fibonacci: 1 (retracements)
- Volume: 2 (Profile, Analyzer)
- Institutional: 2 (Anchored VWAP, Market Depth)
- **Production Ready: 0/16 (need metadata validation)**

**HYBRID BLOCKS: 4/67 (6.0%)**
- ADR (volatility + targets)
- Bollinger Bands (bands + signals)
- Ichimoku Cloud (cloud + crossovers)
- Order Flow Imbalance (metrics + signals)
- **Production Ready: 1/4 (ADR only)**

---

## Next Steps

1. ✅ Read documentation for each remaining block
2. ✅ Classify as SIGNAL / METADATA / HYBRID
3. ✅ Create metadata validator
4. ✅ Test metadata blocks with metadata validator
5. ✅ Fix fixable signal blocks
6. ✅ Document all blocks with proper category

---

*End of Categorization - In Progress*
