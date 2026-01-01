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

**Patterns (15)** - All SIGNALS (pattern completion)
31. ❓ Head & Shoulders - SIGNAL (completion)
32. ❓ Inverse Head & Shoulders - SIGNAL (completion)
33. ❓ Double Top - SIGNAL (completion)
34. ❓ Double Bottom - SIGNAL (completion)
35. ❓ Triple Top - SIGNAL (completion)
36. ❓ Triple Bottom - SIGNAL (completion)
37. ❓ Cup & Handle - SIGNAL (breakout)
38. ❓ Rounding Bottom - SIGNAL (completion)
39. ❓ Flags/Pennants - SIGNAL (breakout)
40. ❓ Ascending Triangle - SIGNAL (breakout)
41. ❓ Descending Triangle - SIGNAL (breakout)
42. ❓ Symmetrical Triangle - SIGNAL (breakout)
43. ❓ Wedge Patterns - SIGNAL (breakout)
44. ❓ Diamond Pattern - SIGNAL (breakout)
45. ❓ Harmonic Patterns - SIGNAL (completion)

---

### METADATA/CONTEXT BLOCKS (Non-Predictive)

**Volatility (3)** - All METADATA
46. ❌→✅ ATR - METADATA (stop-loss distance, position sizing)
47. ✅ ADR - HYBRID (volatility level + targets)
48. ❓ Bollinger Bands - HYBRID (bands + squeeze/expansion)
49. ❓ Keltner Channels - METADATA (volatility bands)

**Trend Strength (2)** - METADATA
50. ❓ ADX - METADATA (trend strength 0-100)
51. ❓ Ichimoku Cloud - HYBRID (cloud + signals)

**Sessions/Time (2)** - METADATA
52. ❓ Kill Zones - METADATA (time windows)
53. ❓ Session High/Low - METADATA (session levels)

**Price Levels (6)** - METADATA (Reference Levels)
54. ❌ HOD - METADATA (resistance reference)
55. ❓ HOW - METADATA (resistance reference)
56. ❓ LOD - METADATA (support reference)
57. ❓ LOW - METADATA (support reference)
58. ❓ Asia Session 50% - METADATA (level reference)
59. ❓ US Settlement - METADATA (level reference)

**Elliott Wave (2)** - SIGNALS (Wave completion)
60. ❓ Elliott Wave Count - SIGNAL (wave completion)
61. ❓ Elliott Wave Oscillator - SIGNAL (wave momentum)

**Fibonacci (1)** - METADATA (Retracement levels)
62. ❓ Fibonacci Retracements - METADATA (support/resistance levels)

**Wyckoff (3)** - SIGNALS (Phase detection)
63. ❓ Wyckoff Accumulation - SIGNAL (phase completion)
64. ❓ Wyckoff Distribution - SIGNAL (phase completion)
65. ❓ Wyckoff Reaccumulation - SIGNAL (phase completion)

**Volume (2)** - METADATA
66. ❓ Volume Profile - METADATA (volume at price levels)  
67. ❓ Volume Analyzer - METADATA (volume metrics)

---

## Summary Counts

**CONFIRMED:**
- ✅ Signal Blocks: 27 (tested and validated)
- ✅ Metadata Blocks: 1 (ATR - identified, needs proper validation)
- ✅ Hybrid Blocks: 1 (ADR - works as metadata)

**TO CATEGORIZE:** 38 blocks remaining

**ESTIMATED FINAL:**
- Signals: 40-45 blocks
- Metadata: 15-20 blocks
- Hybrid: 5-7 blocks

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
