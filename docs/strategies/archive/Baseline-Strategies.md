# Baseline Trading Strategies for NautilusTrader
## Building Block Combination System

**Version:** v1.0  
**Date:** January 1, 2026  
**Framework:** NautilusTrader  
**Market:** Bitcoin (BTC) 24/7 Cryptocurrency  
**Purpose:** High-quality baseline strategies for rapid testing and optimization

---

## Strategy Index

### **Trend Following Strategies (1-15)**
1. 50 EMA Vector Breakout Long
2. 200 EMA Momentum Continuation
3. Triple EMA Confluence Breakout
4. MACD Divergence Reversal Long
5. ADX Strong Trend Rider
6. Ichimoku Cloud Breakout Long
7. Moving Average Golden Cross
8. EMA Pullback Entry System
9. Trend Momentum Scalper
10. Dynamic EMA Support Bounce
11. Vector Break with Volume Surge
12. Multi-Timeframe EMA Alignment
13. MACD Histogram Expansion
14. Trend Exhaustion Reversal
15. EMA Ribbon Breakout

### **Mean Reversion Strategies (16-25)**
16. Asia Session 50% Reversion
17. Bollinger Band Bounce Long
18. RSI Oversold Divergence Entry
19. Stochastic RSI Mean Reversion
20. Fair Value Gap Fill Long
21. Order Block Retest Entry
22. Premium Zone Fade
23. Discount Zone Accumulation
24. Fibonacci Golden Ratio Bounce
25. Supply Demand Zone Reversal

### **Smart Money Concepts Strategies (26-40)**
26. Liquidity Sweep Reversal Long
27. Breaker Block Retest Entry
28. Optimal Trade Entry (OTE) System
29. Market Structure Shift Long
30. Fair Value Gap + Order Block
31. Displacement Continuation
32. Liquidity Pool Target System
33. Kill Zone Breakout Long
34. ICT Power of Three Setup
35. Smart Money Divergence
36. Inducement and Mitigation
37. Premium to Discount Swing
38. External Liquidity Grab
39. Break of Structure Continuation
40. Change of Character Reversal

### **Pattern Recognition Strategies (41-55)**
41. Inverse Head and Shoulders Long
42. Double Bottom Breakout
43. Ascending Triangle Breakout
44. Bullish Flag Continuation
45. Falling Wedge Reversal
46. Triple Bottom Accumulation
47. Symmetrical Triangle Breakout
48. Bullish Pennant Momentum
49. Cup and Handle Breakout
50. Rounding Bottom Reversal
51. Harmonic Gartley Pattern Long
52. Harmonic Butterfly Reversal
53. Harmonic Bat Pattern Entry
54. Harmonic Crab Pattern Long
55. W-Bottom Bollinger Pattern

### **Institutional & Volume Strategies (56-65)**
56. Wyckoff Accumulation Phase D
57. Wyckoff Spring Entry
58. Volume Profile POC Bounce
59. High Volume Node Support
60. Order Flow Imbalance Long
61. Absorption Pattern Entry
62. Volume Climax Reversal
63. Pivot Point Support Bounce
64. Session Opening Range Breakout
65. HOD/LOD Liquidity System

### **Elliott Wave & Cycle Strategies (66-75)**
66. Elliott Wave 3 Momentum Entry
67. Wave 4 Pullback Entry
68. Elliott Wave 5 Exhaustion Short
69. ABC Correction Completion
70. Wave Extension Continuation
71. Elliott Oscillator Divergence
72. Cycle Bottom Accumulation
73. Impulse Wave Identification
74. Corrective Wave C Entry
75. Multi-Wave Confluence System

### **Multi-Confluence Strategies (76-90)**
76. Triple Confluence Long Setup
77. Institutional Footprint Entry
78. Multi-Timeframe Alignment
79. Session + Structure Confluence
80. ICT Unicorn Model Setup
81. High Probability Reversal System
82. Momentum Breakout Confluence
83. Support Cluster Entry
84. Resistance Rejection Short
85. Divergence + Pattern Confluence
86. Volume + Price Action Setup
87. Kill Zone + OTE System
88. Complete Market Profile Entry
89. Advanced Smart Money Setup
90. Ultimate Confluence Strategy

---

## TREND FOLLOWING STRATEGIES

---

### Strategy 1: 50 EMA Vector Breakout Long

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Enter long when price breaks above 50 EMA with a vector candle (high volume), confirmed by bullish RSI divergence, stochastic RSI crossing up from oversold, and price trading above Asia Session 50% level during favorable session timing.

**Building Blocks Used:**
- 50_EMA_Vector_Break
- rsi_divergence
- stochastic_rsi_cross
- asia_session_50_percent
- session_time

**Entry Conditions:**
1. Price breaks above 50 EMA with vector candle (volume > 1.5x average)
2. RSI shows bullish divergence OR RSI > 50
3. Stochastic RSI crosses up from below 20
4. Price above Asia Session 50% level
5. Entry during London or New York AM Kill Zone

**Exit Conditions:**
- Take Profit 1: +1.5% (50% position)
- Take Profit 2: +2.5% (30% position)
- Take Profit 3: Trailing stop at 50 EMA (20% position)
- Stop Loss: Below recent swing low or -1.2%

**Filters:**
- ADX > 25 (trending market)
- Volume on breakout candle > 1.5x average
- ATR > $500 (sufficient volatility)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - High probability trend continuation strategy

---

### Strategy 2: 200 EMA Momentum Continuation

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Major trend following system using 200 EMA breaks with MACD confirmation, targeting continuation after brief pullbacks during strong trending conditions.

**Building Blocks Used:**
- 200_ema_vector_break
- macd_signal
- adr
- hod
- adx

**Entry Conditions:**
1. Price breaks above 200 EMA with vector candle (volume > 1.5x)
2. MACD line crosses above signal line
3. MACD histogram positive and expanding
4. ADR completion < 75% (room to run)
5. ADX > 30 (strong trend)

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +4% (40% position)
- Take Profit 3: ADR 100% target (20% position)
- Stop Loss: Below 200 EMA or -1.5%

**Filters:**
- Price must close above 200 EMA
- Higher timeframe (4hr) also above 200 EMA
- No bearish divergence on MACD

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Strong trend continuation, lower frequency

---

### Strategy 3: Triple EMA Confluence Breakout

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Multi-EMA system using 50, 200, and 255 EMA alignment with stochastic confirmation for high-probability breakout entries in established trends.

**Building Blocks Used:**
- 50_ema_vector_break
- 200_ema_vector_break
- 255_ema_vector_break
- stochastic_rsi_cross
- displacement

**Entry Conditions:**
1. Price above all three EMAs (50, 200, 255)
2. 50 EMA > 200 EMA > 255 EMA (bullish alignment)
3. Price breaks above recent consolidation with displacement
4. Stochastic RSI crosses up in oversold or neutral zone
5. Displacement candle with >2x average volume

**Exit Conditions:**
- Take Profit 1: +2.5% (50% position)
- Take Profit 2: +4% (30% position)
- Take Profit 3: Trailing stop below 50 EMA (20% position)
- Stop Loss: Below 50 EMA or -1.5%

**Filters:**
- All EMAs must be rising (uptrend confirmation)
- Minimum consolidation period of 20 bars before breakout
- Entry during high volume sessions only

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Multi-timeframe trend alignment

---

### Strategy 4: MACD Divergence Reversal Long

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Counter-trend reversal strategy identifying bullish divergence between price and MACD at support levels, combined with oversold stochastic conditions.

**Building Blocks Used:**
- macd_signal
- rsi_divergence
- stochastic_rsi_cross
- lod
- volume_profile

**Entry Conditions:**
1. MACD shows bullish divergence (price lower low, MACD higher low)
2. RSI shows bullish divergence
3. Stochastic RSI crosses up from below 20
4. Price near LOD or major support level
5. Volume Profile POC nearby (high volume node support)

**Exit Conditions:**
- Take Profit 1: +3% (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: MACD bearish crossover (20% position)
- Stop Loss: Below divergence low or -2%

**Filters:**
- Must have clear divergence on both MACD and RSI
- Minimum 2 pivot points for valid divergence
- Higher timeframe (daily) not in strong downtrend

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Reversal strategy, moderate frequency

---

### Strategy 5: ADX Strong Trend Rider

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Pure trend-following system entering on pullbacks during confirmed strong trends, using ADX for trend strength validation and EMAs for entry timing.

**Building Blocks Used:**
- adx
- 50_ema_vector_break
- fibonacci_retracements
- break_of_structure
- atr

**Entry Conditions:**
1. ADX > 40 (very strong trend)
2. +DI > -DI (uptrend direction)
3. Price pulls back to 50 EMA or Fibonacci 38.2-50% level
4. Price breaks above recent high (BOS continuation)
5. Entry candle closes above 50 EMA

**Exit Conditions:**
- Take Profit 1: 1x ATR (40% position)
- Take Profit 2: 2x ATR (40% position)
- Take Profit 3: ADX falls below 25 (20% position)
- Stop Loss: 1.5x ATR below entry or below 50 EMA

**Filters:**
- ADX must be rising (strengthening trend)
- Pullback must not exceed Fibonacci 61.8%
- Volume on entry candle > average

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Strong trend only, high win rate

---

### Strategy 6: Ichimoku Cloud Breakout Long

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Comprehensive Ichimoku system waiting for price to break above cloud with all components aligned bullishly, targeting sustained trend development.

**Building Blocks Used:**
- ichimoku_cloud
- macd_signal
- volume_profile
- adx
- kill_zones

**Entry Conditions:**
1. Price breaks above green cloud (Senkou Span A > Span B)
2. Tenkan-sen > Kijun-sen (bullish crossover)
3. Chikou Span above price from 26 periods ago
4. MACD bullish crossover
5. Entry during New York AM Kill Zone

**Exit Conditions:**
- Take Profit 1: +3% (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: Price falls back into cloud (20% position)
- Stop Loss: Below Kijun-sen or cloud bottom

**Filters:**
- Cloud must be thick (strong support/resistance)
- ADX > 25 for trend confirmation
- Volume on breakout > 1.5x average

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Comprehensive trend system

---

### Strategy 7: Moving Average Golden Cross

**Trade Direction:** Long Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Classic long-term trend following strategy entering when 50 EMA crosses above 200 EMA, with multi-timeframe confirmation and momentum filters.

**Building Blocks Used:**
- 50_ema_vector_break
- 200_ema_vector_break
- macd_signal
- adx
- elliott_wave_count

**Entry Conditions:**
1. 50 EMA crosses above 200 EMA (Golden Cross)
2. Price above both 50 and 200 EMAs
3. MACD bullish crossover and above zero line
4. ADX rising and > 20
5. Elliott Wave suggesting Wave 3 or Wave 5 potential

**Exit Conditions:**
- Take Profit 1: +8% (30% position)
- Take Profit 2: +15% (40% position)
- Take Profit 3: 50 EMA crosses below 200 EMA (30% position)
- Stop Loss: Below 200 EMA or -5%

**Filters:**
- Golden Cross must occur after established downtrend
- Volume on cross day > 1.5x average
- Higher timeframe (weekly) supportive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Position trading, low frequency

---

### Strategy 8: EMA Pullback Entry System

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Scalping system entering on brief pullbacks to 50 EMA during strong uptrends, using stochastic and volume confirmation for precise entries.

**Building Blocks Used:**
- 50_ema_vector_break
- stochastic_rsi_cross
- atr
- session_time
- hod

**Entry Conditions:**
1. Price in confirmed uptrend (above 50 EMA on higher timeframe)
2. Price pulls back and touches 50 EMA on 15min chart
3. Stochastic RSI crosses up from below 30
4. Entry during London or New York AM session
5. Price has not yet reached HOD

**Exit Conditions:**
- Take Profit 1: +1% (50% position)
- Take Profit 2: +1.8% (30% position)
- Take Profit 3: Near HOD resistance (20% position)
- Stop Loss: Below 50 EMA or -0.8%

**Filters:**
- ATR sufficient for scalping ($400+)
- Volume normal or elevated
- No major resistance nearby

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - High frequency scalping

---

### Strategy 9: Trend Momentum Scalper

**Trade Direction:** Long Trade  
**Trade Chart:** 5 Min Candles  
**Strategy Description:** Ultra-short-term momentum scalping during high-volume sessions, capturing quick moves using displacement and volume surge confirmation.

**Building Blocks Used:**
- displacement
- volume_profile
- macd_signal
- kill_zones
- atr

**Entry Conditions:**
1. Displacement candle (3x average volume, large body)
2. MACD histogram expanding in bullish direction
3. Entry during active Kill Zone (London or NY AM)
4. Volume surge confirming institutional activity
5. ATR > $300 (minimum volatility requirement)

**Exit Conditions:**
- Take Profit 1: +0.5% (60% position)
- Take Profit 2: +0.8% (30% position)
- Take Profit 3: MACD momentum fading (10% position)
- Stop Loss: -0.4% or below displacement candle low

**Filters:**
- Only trade during Kill Zones
- Minimum 3x volume on displacement candle
- No entry if near major resistance

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:1.5 - Very high frequency, tight stops

---

### Strategy 10: Dynamic EMA Support Bounce

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Mean reversion strategy buying bounces from 50 EMA support during uptrends, with RSI and price action confirmation.

**Building Blocks Used:**
- 50_ema_vector_break
- rsi_divergence
- bollinger_bands
- asia_session_50_percent
- order_block

**Entry Conditions:**
1. Price in uptrend (above 50 EMA on 1hr+)
2. Price touches or wicks below 50 EMA without breaking
3. RSI bounces from 40-50 level (not oversold)
4. Bullish rejection candle (long wick, bullish close)
5. Order Block nearby for additional support

**Exit Conditions:**
- Take Profit 1: +1.5% (50% position)
- Take Profit 2: +2.5% (30% position)
- Take Profit 3: Bollinger Band upper band (20% position)
- Stop Loss: Below 50 EMA or -1%

**Filters:**
- 50 EMA must be rising
- No break below 50 EMA on close
- Volume on rejection candle > average

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - High frequency EMA bounce

---

### Strategy 11: Vector Break with Volume Surge

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Breakout strategy combining EMA vector breaks with volume analysis and fair value gap identification for high-probability momentum entries.

**Building Blocks Used:**
- 50_ema_vector_break
- fair_value_gap
- volume_profile
- displacement
- break_of_structure

**Entry Conditions:**
1. Price breaks above 50 EMA with vector candle (2x volume)
2. Fair Value Gap created on breakout candle
3. Break of Structure confirming trend continuation
4. Displacement confirming strong momentum
5. Volume Profile POC below current price (support)

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +3.5% (40% position)
- Take Profit 3: FVG fill or trend exhaustion (20% position)
- Stop Loss: Below FVG or -1.5%

**Filters:**
- Minimum 2x volume on breakout candle
- Fair Value Gap size > 0.5% of price
- Break of Structure clear and decisive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Momentum breakout with volume

---

### Strategy 12: Multi-Timeframe EMA Alignment

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles (Entry), 1 Hour (Trend), 4 Hour (Bias)  
**Strategy Description:** High-confluence strategy requiring EMA alignment across three timeframes, entering on lower timeframe pullbacks during confirmed higher timeframe trends.

**Building Blocks Used:**
- 50_ema_vector_break (multiple timeframes)
- adx (1hr timeframe)
- fibonacci_retracements
- stochastic_rsi_cross
- session_time

**Entry Conditions:**
1. 4hr: Price above 50 EMA (major trend bias)
2. 1hr: Price above 50 EMA, ADX > 25 (intermediate trend)
3. 15min: Price pulls back to 50 EMA (entry timeframe)
4. Fibonacci 38.2-50% retracement of recent 1hr impulse
5. Stochastic RSI crosses up on 15min chart

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +3.5% (40% position)
- Take Profit 3: 15min falls below 50 EMA (20% position)
- Stop Loss: Below 15min 50 EMA or -1.3%

**Filters:**
- All three timeframes must be aligned bullish
- ADX on 1hr must show trend strength
- Entry during high-volume sessions

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Multi-timeframe confluence

---

### Strategy 13: MACD Histogram Expansion

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Momentum entry strategy based on MACD histogram expansion, confirming acceleration of trend strength with volume validation.

**Building Blocks Used:**
- macd_signal
- 50_ema_vector_break
- volume_profile
- atr
- kill_zones

**Entry Conditions:**
1. MACD histogram positive and expanding for 3+ bars
2. MACD line above signal line and both above zero
3. Price above 50 EMA
4. Volume increasing with histogram expansion
5. Entry during active Kill Zone

**Exit Conditions:**
- Take Profit 1: +1.5% (50% position)
- Take Profit 2: +2.5% (30% position)
- Take Profit 3: MACD histogram contraction (20% position)
- Stop Loss: MACD histogram turns negative or -1.2%

**Filters:**
- Histogram must expand for minimum 3 bars
- Volume must be above average
- ATR > $400 for sufficient movement

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - Momentum acceleration system

---

### Strategy 14: Trend Exhaustion Reversal

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Counter-trend reversal strategy identifying exhaustion through multiple divergences, volume climax, and Elliott Wave 5 completion.

**Building Blocks Used:**
- elliott_wave_count
- rsi_divergence
- macd_signal
- volume_profile
- bollinger_bands

**Entry Conditions:**
1. Elliott Wave count suggests Wave 5 completion
2. RSI bearish divergence at wave 5 peak (for longs, after bearish wave 5)
3. MACD bearish divergence
4. Volume climax on final wave
5. Price reaches Bollinger Band extreme

**Exit Conditions:**
- Take Profit 1: +4% (40% position)
- Take Profit 2: +7% (40% position)
- Take Profit 3: Elliott Wave ABC correction complete (20% position)
- Stop Loss: Above Wave 5 high or -2.5%

**Filters:**
- Must have clear 5-wave structure
- Divergence on both RSI and MACD required
- Higher timeframe supportive of reversal

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Reversal at exhaustion, lower frequency

---

### Strategy 15: EMA Ribbon Breakout

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Breakout strategy using multiple EMA confirmation (50, 55, 200, 255) with all EMAs crossed simultaneously during strong institutional moves.

**Building Blocks Used:**
- 50_ema_vector_break
- 55_ema_vector_break
- 200_ema_vector_break
- 255_ema_vector_break
- displacement

**Entry Conditions:**
1. Price breaks above all EMAs (50, 55, 200, 255) within 3 bars
2. Displacement candle with 3x+ volume
3. All EMAs trending in same direction (ribbon alignment)
4. No resistance level within 2% above entry
5. Strong momentum confirmed by large-body candle

**Exit Conditions:**
- Take Profit 1: +3% (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: Price falls back below 50 EMA (20% position)
- Stop Loss: Below 50 EMA or -2%

**Filters:**
- All four EMAs must be crossed simultaneously
- Minimum 3x volume on breakout
- Clear trend resumption setup

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Major trend reversal entry

---

## MEAN REVERSION STRATEGIES

---

### Strategy 16: Asia Session 50% Reversion

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Mean reversion strategy targeting return to Asia session equilibrium (50% level) during US session after UK manipulation phase, common ICT pattern.

**Building Blocks Used:**
- asia_session_50_percent
- session_time
- fair_value_gap
- us_settlement
- stochastic_rsi_cross

**Entry Conditions:**
1. During US session (13:00-21:00 UTC)
2. Price swept below Asia 50% during London session
3. Price shows reversal pattern (liquidity sweep)
4. Fair Value Gap created pointing toward Asia 50%
5. Stochastic RSI crosses up from oversold

**Exit Conditions:**
- Take Profit 1: Asia 50% level (60% position)
- Take Profit 2: Asia high (30% position)
- Take Profit 3: Trailing stop (10% position)
- Stop Loss: Below recent swing low or -1.5%

**Filters:**
- Asia range must be clearly defined
- UK session must have created liquidity sweep
- Entry during high-volume US session only

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - ICT session-based mean reversion

---

### Strategy 17: Bollinger Band Bounce Long

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Classic mean reversion buying at lower Bollinger Band with RSI oversold confirmation, targeting return to middle band (SMA 20).

**Building Blocks Used:**
- bollinger_bands
- rsi_divergence
- stochastic_rsi_cross
- volume_profile
- 50_ema_vector_break

**Entry Conditions:**
1. Price touches or penetrates lower Bollinger Band
2. RSI < 30 (oversold) or shows bullish divergence
3. Stochastic RSI crosses up from below 20
4. Bollinger Band width not in extreme squeeze
5. Price above 50 EMA on higher timeframe (uptrend bias)

**Exit Conditions:**
- Take Profit 1: Middle Bollinger Band/20 SMA (50% position)
- Take Profit 2: Upper Bollinger Band (30% position)
- Take Profit 3: Trailing stop at middle band (20% position)
- Stop Loss: 1.5x ATR below entry or below lower band extension

**Filters:**
- Must be in ranging or pullback phase, not downtrend
- Volume on reversal candle > average
- No breakdown below recent structure

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Classic mean reversion

---

### Strategy 18: RSI Oversold Divergence Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Reversal strategy combining RSI oversold conditions with bullish divergence at support levels, enhanced by stochastic confirmation.

**Building Blocks Used:**
- rsi_divergence
- stochastic_rsi_cross
- lod
- volume_profile
- fibonacci_retracements

**Entry Conditions:**
1. RSI shows bullish divergence (price lower low, RSI higher low)
2. RSI below 35 on first divergence pivot
3. Price near LOD or Fibonacci 61.8-78.6% retracement
4. Stochastic RSI crosses up from oversold
5. Volume Profile POC or HVN nearby (support)

**Exit Conditions:**
- Take Profit 1: +2.5% (40% position)
- Take Profit 2: +4% (40% position)
- Take Profit 3: RSI overbought >70 (20% position)
- Stop Loss: Below divergence low or -1.8%

**Filters:**
- Clear divergence required (minimum 2 pivot points)
- Must be at support structure
- Higher timeframe not in strong downtrend

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Divergence reversal system

---

### Strategy 19: Stochastic RSI Mean Reversion

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Fast mean reversion scalping using stochastic RSI crossovers in oversold zone, combined with support level confirmation.

**Building Blocks Used:**
- stochastic_rsi_cross
- 50_ema_vector_break
- lod
- pivot_points
- session_time

**Entry Conditions:**
1. Stochastic RSI %K crosses above %D in oversold zone (<20)
2. Price near 50 EMA or daily pivot point support
3. Entry during high-volume session (London/NY)
4. Price not breaking LOD (holding support)
5. Bullish rejection candle (long lower wick)

**Exit Conditions:**
- Take Profit 1: +1.2% (50% position)
- Take Profit 2: +2% (30% position)
- Take Profit 3: Stochastic RSI reaches overbought (20% position)
- Stop Loss: Below support level or -0.9%

**Filters:**
- Stochastic cross must occur below 20 level
- Price must respect support level
- Sufficient volatility (ATR > $400)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - Fast mean reversion scalping

---

### Strategy 20: Fair Value Gap Fill Long

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Smart Money Concept strategy entering on return to unfilled Fair Value Gaps, expecting price to "fill the gap" before continuing trend.

**Building Blocks Used:**
- fair_value_gap
- order_block
- kill_zones
- displacement
- volume_profile

**Entry Conditions:**
1. Bullish Fair Value Gap created by displacement move
2. Price returns to FVG zone (gap fill)
3. Order Block within or near FVG for confluence
4. Entry during active Kill Zone (London/NY AM)
5. FVG size > 0.5% of price (significant gap)

**Exit Conditions:**
- Take Profit 1: +1.5% (50% position)
- Take Profit 2: +2.5% (30% position)
- Take Profit 3: Next FVG or structure level (20% position)
- Stop Loss: Below FVG or -1%

**Filters:**
- FVG must be unfilled (no previous retest)
- Displacement that created FVG must be strong
- Higher timeframe trend supportive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - SMC gap fill system

---

### Strategy 21: Order Block Retest Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Institutional footprint strategy entering on retest of bullish order blocks, where smart money previously accumulated positions.

**Building Blocks Used:**
- order_block
- fair_value_gap
- displacement
- kill_zones
- volume_profile

**Entry Conditions:**
1. Bullish Order Block identified (last bearish candle before impulse)
2. Price returns to retest Order Block zone
3. Bullish rejection candle at Order Block (long wick, bullish close)
4. Fair Value Gap within Order Block adds confluence
5. Entry during Kill Zone for institutional activity

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +3.5% (40% position)
- Take Profit 3: Order Block violated (closes below) (20% position)
- Stop Loss: Below Order Block or -1.5%

**Filters:**
- Order Block must be "fresh" (first retest preferred)
- Clear displacement/impulse move away from OB
- Volume on rejection candle > average

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Institutional retest entry

---

### Strategy 22: Premium Zone Fade

**Trade Direction:** Short Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Contrarian strategy shorting premium zones (above 50% Fibonacci of range), expecting reversion to equilibrium or discount zone.

**Building Blocks Used:**
- premium_discount_zones
- fibonacci_retracements
- rsi_divergence
- hod
- stochastic_rsi_cross

**Entry Conditions:**
1. Price in Premium Zone (above 62% of recent range)
2. RSI showing bearish divergence
3. Price near HOD or key resistance
4. Stochastic RSI crosses down from overbought (>80)
5. Bearish rejection candle at premium zone

**Exit Conditions:**
- Take Profit 1: Equilibrium (50% level) (50% position)
- Take Profit 2: Discount Zone entry (30% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Above premium zone high or +1.5%

**Filters:**
- Must be clear dealing range (not trending)
- Premium zone rejection confirmed by volume
- Higher timeframe supportive of reversion

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - Mean reversion to equilibrium

---

### Strategy 23: Discount Zone Accumulation

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Value-based strategy accumulating positions in discount zone (below 38% of range), expecting reversion to equilibrium and premium.

**Building Blocks Used:**
- premium_discount_zones
- fibonacci_retracements
- order_block
- lod
- stochastic_rsi_cross

**Entry Conditions:**
1. Price in Discount Zone (below 38.2% of recent range)
2. Price near LOD or major support
3. Bullish Order Block in discount zone
4. Stochastic RSI crosses up from oversold
5. Bullish reversal candle pattern

**Exit Conditions:**
- Take Profit 1: Equilibrium (50% level) (50% position)
- Take Profit 2: Premium Zone (38.2% from top) (30% position)
- Take Profit 3: Trailing stop at equilibrium (20% position)
- Stop Loss: Below discount zone low or -1.5%

**Filters:**
- Clear ranging structure (not breakdown)
- Support level must hold (no LOD break)
- Volume on reversal candle elevated

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Value accumulation system

---

### Strategy 24: Fibonacci Golden Ratio Bounce

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** High-probability reversal at Fibonacci 61.8% golden ratio level, combined with bullish price action and momentum confirmation.

**Building Blocks Used:**
- fibonacci_retracements
- rsi_divergence
- stochastic_rsi_cross
- volume_profile
- order_block

**Entry Conditions:**
1. Price retraces to Fibonacci 61.8% level
2. RSI shows bullish divergence OR holding above 40
3. Stochastic RSI crosses up
4. Order Block or Volume Profile HVN at 61.8% level
5. Bullish hammer or engulfing candle at level

**Exit Conditions:**
- Take Profit 1: Fibonacci 38.2% level (40% position)
- Take Profit 2: Previous swing high (40% position)
- Take Profit 3: Fibonacci 161.8% extension (20% position)
- Stop Loss: Below 78.6% Fib level or -2%

**Filters:**
- Clear trend before retracement
- 61.8% level must align with support structure
- Volume confirmation on reversal

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Golden ratio reversal

---

### Strategy 25: Supply Demand Zone Reversal

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Price action strategy entering at fresh demand zones where previous strong moves originated, expecting institutional support.

**Building Blocks Used:**
- supply_demand_zones
- order_block
- volume_profile
- displacement
- fair_value_gap

**Entry Conditions:**
1. Fresh demand zone identified (base before strong upward move)
2. Price returns to demand zone for first time
3. Bullish engulfing or pin bar at zone
4. Volume surge on reversal candle
5. Order Block within demand zone for confluence

**Exit Conditions:**
- Take Profit 1: +2.5% (40% position)
- Take Profit 2: Next supply zone (40% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Below demand zone or -1.8%

**Filters:**
- Demand zone must be "fresh" (untested)
- Strong displacement from zone previously
- Higher timeframe trend supportive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Institutional zone entry

---

## SMART MONEY CONCEPTS STRATEGIES

---

### Strategy 26: Liquidity Sweep Reversal Long

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** ICT liquidity sweep strategy entering after stop-hunt below support, expecting rapid reversal as institutions fill positions from triggered stops.

**Building Blocks Used:**
- liquidity_sweep
- lod
- fair_value_gap
- breaker_block
- kill_zones

**Entry Conditions:**
1. Liquidity sweep below LOD or swing low (stop hunt)
2. Price rapidly reverses back above swept level within 1-3 candles
3. Bullish Fair Value Gap created on reversal
4. Entry during active Kill Zone (London/NY AM)
5. High volume on reversal candle (2x+ average)

**Exit Conditions:**
- Take Profit 1: +1.5% (50% position)
- Take Profit 2: +2.5% (30% position)
- Take Profit 3: Opposite liquidity pool (20% position)
- Stop Loss: Below sweep extreme or -1%

**Filters:**
- Sweep must be brief (1-2 candles below level)
- Reversal must be decisive (strong bullish candle)
- Volume must confirm institutional activity

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Liquidity grab reversal

---

### Strategy 27: Breaker Block Retest Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Advanced SMC strategy entering on retest of breaker blocks (failed order blocks that signal market structure shift).

**Building Blocks Used:**
- breaker_block
- market_structure_shift
- fair_value_gap
- order_block
- kill_zones

**Entry Conditions:**
1. Bearish Order Block fails (swept and market structure shifts)
2. Failed OB becomes bullish Breaker Block
3. Price returns to retest Breaker Block zone
4. Fair Value Gap within Breaker Block adds confluence
5. Entry during Kill Zone with bullish confirmation candle

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +3.5% (40% position)
- Take Profit 3: Next market structure level (20% position)
- Stop Loss: Below Breaker Block or -1.5%

**Filters:**
- Clear Market Structure Shift required
- Liquidity sweep must have occurred
- First retest of Breaker Block preferred

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Advanced SMC setup

---

### Strategy 28: Optimal Trade Entry (OTE) System

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** ICT signature setup entering at 62-79% Fibonacci retracement (OTE zone), ideally at 70.5% precise level during Kill Zones.

**Building Blocks Used:**
- optimal_trade_entry
- fibonacci_retracements
- kill_zones
- order_block
- fair_value_gap

**Entry Conditions:**
1. Clear trend established with Break of Structure
2. Price retraces to 62-79% Fibonacci zone (OTE)
3. Ideally enters at 70.5% precise OTE level
4. Order Block or Fair Value Gap at OTE level
5. Entry during New York AM Kill Zone (08:00-11:00 EST)

**Exit Conditions:**
- Take Profit 1: Previous high (40% position)
- Take Profit 2: -0.5 Fibonacci extension (40% position)
- Take Profit 3: -1.0 Fibonacci extension (20% position)
- Stop Loss: Below 100% Fib level (start of move)

**Filters:**
- Must be during Kill Zone timing
- Higher timeframe trend must support entry
- Clear Break of Structure before retracement

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - ICT signature setup

---

### Strategy 29: Market Structure Shift Long

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Trend reversal strategy entering on confirmed Market Structure Shift, waiting for retest of broken structure for optimal entry.

**Building Blocks Used:**
- market_structure_shift
- breaker_block
- order_block
- fair_value_gap
- volume_profile

**Entry Conditions:**
1. Market Structure Shift occurs (breaks recent lower high in downtrend)
2. Decisive break with strong volume (2x+ average)
3. Price retraces to retest broken structure (now support)
4. Breaker Block or Order Block at retest level
5. Bullish confirmation candle at retest

**Exit Conditions:**
- Take Profit 1: +3% (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: Opposite MSS occurs (20% position)
- Stop Loss: Below broken structure or -2%

**Filters:**
- MSS must be clear and decisive
- Volume confirmation essential
- Higher timeframe supportive of reversal

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Trend reversal confirmation

---

### Strategy 30: Fair Value Gap + Order Block

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** "Unicorn Model" combining Fair Value Gap fill with Order Block retest, highest probability SMC setup per ICT methodology.

**Building Blocks Used:**
- fair_value_gap
- order_block
- displacement
- kill_zones
- optimal_trade_entry

**Entry Conditions:**
1. Bullish displacement creates Fair Value Gap
2. Order Block within or overlapping the FVG
3. Price returns to fill FVG and retest Order Block simultaneously
4. Entry during active Kill Zone
5. OTE level (62-79%) alignment adds confluence

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +3.5% (40% position)
- Take Profit 3: Next FVG or liquidity pool (20% position)
- Stop Loss: Below FVG/OB or -1.3%

**Filters:**
- FVG and OB must overlap significantly
- First retest of both structures (fresh setup)
- Kill Zone timing mandatory

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Highest probability SMC setup

---

### Strategy 31: Displacement Continuation

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Momentum continuation strategy entering on pullback after strong displacement move, expecting trend continuation with institutional flow.

**Building Blocks Used:**
- displacement
- fair_value_gap
- break_of_structure
- fibonacci_retracements
- volume_profile

**Entry Conditions:**
1. Strong displacement move (3%+ on 30min, high volume)
2. Fair Value Gap created during displacement
3. Break of Structure confirming trend continuation
4. Price pulls back to FVG (38.2-50% Fibonacci)
5. Bullish continuation candle at FVG

**Exit Conditions:**
- Take Profit 1: Equal length of displacement (40% position)
- Take Profit 2: 161.8% extension (40% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Below FVG or 61.8% Fib retracement

**Filters:**
- Displacement must be >3% move with 3x+ volume
- FVG must be clear and unfilled
- Higher timeframe trend supportive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Strong momentum continuation

---

### Strategy 32: Liquidity Pool Target System

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Strategic entry targeting price movement toward identified liquidity pools (equal highs/lows), following institutional order flow.

**Building Blocks Used:**
- liquidity_pool_identification
- order_block
- fair_value_gap
- kill_zones
- displacement

**Entry Conditions:**
1. Identify liquidity pool (equal highs, round numbers)
2. Price shows institutional positioning (OB, FVG) targeting pool
3. Enter after liquidity sweep creates entry setup
4. Clear path to target liquidity pool
5. Entry during Kill Zone for institutional flow

**Exit Conditions:**
- Take Profit 1: 50% distance to liquidity pool (40% position)
- Take Profit 2: At liquidity pool target (50% position)
- Take Profit 3: Beyond pool if momentum continues (10% position)
- Stop Loss: Setup invalidation or -1.8%

**Filters:**
- Clear liquidity pool must be identified
- Institutional footprints (OB/FVG) required
- No major resistance before target

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Liquidity targeting system

---

### Strategy 33: Kill Zone Breakout Long

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Session-based strategy entering breakouts specifically during high-activity Kill Zones (London/NY AM) when institutional traders are most active.

**Building Blocks Used:**
- kill_zones
- break_of_structure
- displacement
- fair_value_gap
- volume_profile

**Entry Conditions:**
1. Active Kill Zone (London 02:00-05:00 or NY AM 08:00-11:00 EST)
2. Break of Structure during Kill Zone
3. Displacement candle with high volume
4. Fair Value Gap created on breakout
5. No immediate resistance level nearby

**Exit Conditions:**
- Take Profit 1: +1.5% (50% position)
- Take Profit 2: +2.5% (30% position)
- Take Profit 3: End of Kill Zone or momentum fade (20% position)
- Stop Loss: Below Kill Zone entry level or -1%

**Filters:**
- Must enter during active Kill Zone only
- Volume must be 2x+ average
- Clear break of recent structure

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Session-based institutional flow

---

### Strategy 34: ICT Power of Three Setup

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Classic ICT three-phase pattern: Asia accumulation, London manipulation (Judas Swing), US distribution targeting Asia 50%.

**Building Blocks Used:**
- asia_session_50_percent
- session_time
- liquidity_sweep
- fair_value_gap
- kill_zones

**Entry Conditions:**
1. Asia session creates clear range (accumulation)
2. London session sweeps Asia high or low (manipulation/Judas)
3. Price reverses during London close or NY open
4. Target: Return to Asia 50% level (distribution)
5. Entry on FVG fill with reversal confirmation

**Exit Conditions:**
- Take Profit 1: Asia 50% level (60% position)
- Take Profit 2: Opposite side of Asia range (30% position)
- Take Profit 3: Trailing stop (10% position)
- Stop Loss: Beyond manipulation extreme or -1.5%

**Filters:**
- Clear three-session pattern required
- London manipulation must be obvious (liquidity sweep)
- US session must show institutional reversal

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - Classic ICT session play

---

### Strategy 35: Smart Money Divergence

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Combining price/indicator divergence with SMC concepts (Order Blocks, FVGs) at market structure levels for high-probability reversals.

**Building Blocks Used:**
- rsi_divergence
- macd_signal
- order_block
- fair_value_gap
- market_structure_shift

**Entry Conditions:**
1. RSI and MACD both show bullish divergence
2. Divergence occurs at bullish Order Block
3. Fair Value Gap created on reversal
4. Market Structure Shift potential (at key level)
5. Volume surge on reversal confirmation

**Exit Conditions:**
- Take Profit 1: +3% (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: Divergence negated (20% position)
- Stop Loss: Below divergence low or -2%

**Filters:**
- Double divergence required (RSI + MACD)
- Must be at SMC structure level
- Higher timeframe supportive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Divergence + SMC confluence

---

### Strategy 36: Inducement and Mitigation

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Advanced ICT concept entering after price "induces" (traps) traders with false move, then mitigates back through key level.

**Building Blocks Used:**
- liquidity_sweep
- breaker_block
- fair_value_gap
- order_block
- kill_zones

**Entry Conditions:**
1. Inducement: Liquidity sweep below support (trap move)
2. Price rapidly mitigates back above swept level
3. Breaker Block forms at failed support
4. Fair Value Gap or Order Block at mitigation zone
5. Entry during Kill Zone with confirmation

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +3.5% (40% position)
- Take Profit 3: Next liquidity target (20% position)
- Stop Loss: Below inducement extreme or -1.5%

**Filters:**
- Inducement must be clear (below obvious level)
- Mitigation must be rapid (1-3 candles)
- Volume confirmation on both moves

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Advanced ICT setup

---

### Strategy 37: Premium to Discount Swing

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Swing trading strategy entering in discount zone after price clears premium zone, expecting full range retracement.

**Building Blocks Used:**
- premium_discount_zones
- fibonacci_retracements
- order_block
- market_structure_shift
- volume_profile

**Entry Conditions:**
1. Price reaches premium zone (creates high)
2. Market Structure Shift signals reversal
3. Price retraces to discount zone (below 38.2%)
4. Order Block in discount zone
5. Bullish reversal confirmation at discount zone

**Exit Conditions:**
- Take Profit 1: Equilibrium (50%) (30% position)
- Take Profit 2: Premium zone (38.2% from top) (40% position)
- Take Profit 3: Previous high (30% position)
- Stop Loss: Below discount zone or -2.5%

**Filters:**
- Clear ranging structure required
- MSS must confirm potential reversal
- Volume profile supportive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Full range swing trade

---

### Strategy 38: External Liquidity Grab

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Entering after institutions grab external liquidity (beyond range boundaries) before reversing to trade back into range.

**Building Blocks Used:**
- liquidity_pool_identification
- internal_external_range_liquidity
- liquidity_sweep
- fair_value_gap
- order_block

**Entry Conditions:**
1. Identify trading range with external liquidity beyond boundaries
2. Price sweeps external liquidity (equal lows below range)
3. Rapid reversal back into range within 1-3 candles
4. Fair Value Gap or Order Block at reversal point
5. High volume on sweep and reversal

**Exit Conditions:**
- Take Profit 1: Range midpoint (40% position)
- Take Profit 2: Opposite range boundary (40% position)
- Take Profit 3: Opposite external liquidity (20% position)
- Stop Loss: Beyond external liquidity or -1.5%

**Filters:**
- Clear range structure required
- External liquidity must be obvious (equal lows/highs)
- Reversal must be decisive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Range-based liquidity play

---

### Strategy 39: Break of Structure Continuation

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Trend continuation strategy entering on pullback after confirmed Break of Structure, riding established momentum.

**Building Blocks Used:**
- break_of_structure
- order_block
- fibonacci_retracements
- optimal_trade_entry
- kill_zones

**Entry Conditions:**
1. Clear Break of Structure above recent high (continuation)
2. Price pulls back to 38.2-61.8% Fibonacci or OTE zone
3. Order Block in pullback zone
4. Entry during Kill Zone with bullish candle
5. BOS confirmed with volume and clean break

**Exit Conditions:**
- Take Profit 1: Next BOS level (40% position)
- Take Profit 2: 161.8% extension (40% position)
- Take Profit 3: CHoCH occurs (20% position)
- Stop Loss: Below Order Block or -1.8%

**Filters:**
- BOS must be decisive (clear break, not marginal)
- Pullback must not exceed 61.8%
- Higher timeframe trend aligned

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Strong continuation setup

---

### Strategy 40: Change of Character Reversal

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Early reversal entry on Change of Character (CHoCH) signal, entering at supply/demand zone retest after market character shifts.

**Building Blocks Used:**
- change_of_character
- supply_demand_zones
- order_block
- fair_value_gap
- volume_profile

**Entry Conditions:**
1. Change of Character (breaks lower high in downtrend)
2. CHoCH signals potential trend reversal
3. Price retraces to demand zone or Order Block
4. Fair Value Gap at retest level adds confluence
5. Bullish confirmation candle at zone

**Exit Conditions:**
- Take Profit 1: +4% (40% position)
- Take Profit 2: +7% (40% position)
- Take Profit 3: Opposite CHoCH occurs (20% position)
- Stop Loss: Below demand zone or -2.5%

**Filters:**
- CHoCH must be clear and significant
- Demand zone must be fresh or tested once
- Higher timeframe showing reversal signs

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Early reversal signal

---

## PATTERN RECOGNITION STRATEGIES

---

### Strategy 41: Inverse Head and Shoulders Long

**Trade Direction:** Long Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Classic bullish reversal pattern with three troughs (left shoulder, head, right shoulder) breaking above neckline resistance with volume confirmation.

**Building Blocks Used:**
- inverse_head_and_shoulders
- rsi_divergence
- volume_profile
- macd_signal
- fibonacci_retracements

**Entry Conditions:**
1. Inverse H&S pattern complete with three troughs identified
2. Head is lowest point, shoulders approximately equal height
3. Price breaks above neckline with strong volume (2x+ average)
4. RSI shows bullish divergence at head
5. MACD bullish crossover near neckline break

**Exit Conditions:**
- Take Profit 1: Measured move (head-to-neckline height) (50% position)
- Take Profit 2: +12% or next major resistance (30% position)
- Take Profit 3: Trailing stop at neckline (20% position)
- Stop Loss: Below right shoulder or -4%

**Filters:**
- Pattern must take 2-6 months to form
- Volume decreasing during formation, spike on breakout
- Neckline retest provides safer entry

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - 86% success rate pattern

---

### Strategy 42: Double Bottom Breakout

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** W-shaped bullish reversal with two equal troughs at support, entering on neckline breakout or retest with volume confirmation.

**Building Blocks Used:**
- double_bottom
- volume_profile
- stochastic_rsi_cross
- fibonacci_retracements
- pivot_points

**Entry Conditions:**
1. Two troughs at approximately same price (within 1-3%)
2. Second trough forms with lower volume (seller exhaustion)
3. Price breaks above neckline (peak between troughs)
4. Volume surge on breakout (2x+ average)
5. Stochastic RSI crosses up or RSI bullish divergence between troughs

**Exit Conditions:**
- Take Profit 1: Measured move (trough to neckline height) (50% position)
- Take Profit 2: +6% or next resistance (30% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Below second trough or -2.5%

**Filters:**
- Pattern takes 1-4 weeks to form
- Second trough should not break below first
- Support level must hold on second test

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - High reliability reversal

---

### Strategy 43: Ascending Triangle Breakout

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Bullish continuation pattern with horizontal resistance and rising support, entering on upward breakout with volume confirmation.

**Building Blocks Used:**
- ascending_triangle
- volume_profile
- break_of_structure
- adx
- displacement

**Entry Conditions:**
1. Horizontal resistance line (2-3 touches)
2. Rising support line (2-3 higher lows)
3. Triangle 50-75% complete (approaching apex)
4. Price breaks above resistance with volume (1.5x+ average)
5. Displacement candle confirms strong breakout

**Exit Conditions:**
- Take Profit 1: Triangle height added to breakout (50% position)
- Take Profit 2: +4% or 161.8% extension (30% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Below rising support line or -2%

**Filters:**
- Pattern minimum 3-8 weeks formation
- Volume declining into apex, spike on breakout
- Preceding uptrend increases success rate

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - 70-75% success rate

---

### Strategy 44: Bullish Flag Continuation

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Short-term continuation with strong flagpole followed by parallel downward/sideways channel, breaking upward to continue trend.

**Building Blocks Used:**
- flag_pattern
- displacement
- volume_profile
- fibonacci_retracements
- kill_zones

**Entry Conditions:**
1. Strong upward flagpole (15-30% move in Bitcoin) with high volume
2. Flag forms (parallel downward or sideways channel)
3. Flag duration 5-15 days, volume declining in flag
4. Price breaks above flag upper boundary with volume surge
5. Entry during Kill Zone for best probability

**Exit Conditions:**
- Take Profit 1: Flagpole height added to breakout (60% position)
- Take Profit 2: +4% or 161.8% (30% position)
- Take Profit 3: Trailing stop (10% position)
- Stop Loss: Below flag lower boundary or -1.5%

**Filters:**
- Flagpole must be near-vertical with >3x volume
- Flag consolidation must be parallel lines
- Breakout volume minimum 1.5x average

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - 70-80% success rate

---

### Strategy 45: Falling Wedge Reversal

**Trade Direction:** Long Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Bullish reversal pattern with both support and resistance falling, converging into wedge, breaking upward signaling trend reversal.

**Building Blocks Used:**
- wedge_patterns
- rsi_divergence
- volume_profile
- elliott_wave_count
- wyckoff_accumulation

**Entry Conditions:**
1. Both trendlines falling and converging (falling wedge)
2. Minimum 3 touches on each trendline
3. Volume declining throughout pattern formation
4. RSI bullish divergence during wedge
5. Price breaks above upper resistance with volume surge

**Exit Conditions:**
- Take Profit 1: Widest part of wedge added to breakout (40% position)
- Take Profit 2: +10% (40% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Below wedge lower support or -3%

**Filters:**
- Pattern minimum 3-6 months for reliability
- Volume must decline significantly during formation
- Elliott Wave 5 or Wyckoff spring adds confluence

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Strong reversal pattern

---

### Strategy 46: Triple Bottom Accumulation

**Trade Direction:** Long Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Powerful bullish reversal with three tests of support level without breaking, indicating strong accumulation before upward breakout.

**Building Blocks Used:**
- triple_bottom
- wyckoff_accumulation
- volume_profile
- rsi_divergence
- stochastic_rsi_cross

**Entry Conditions:**
1. Three troughs at approximately same price level
2. Third trough shows lowest volume (seller exhaustion)
3. RSI bullish divergence across troughs
4. Wyckoff accumulation Phase C or D identified
5. Price breaks above neckline (peak resistance) with volume

**Exit Conditions:**
- Take Profit 1: Measured move (trough to neckline) (40% position)
- Take Profit 2: +12% (40% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Below lowest trough or -3%

**Filters:**
- Pattern spans 6-12 weeks minimum
- Volume declining at each successive trough
- Third test most significant (lowest volume)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - 78-82% success rate

---

### Strategy 47: Symmetrical Triangle Breakout

**Trade Direction:** Either Direction (Trade Breakout)  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Neutral consolidation pattern with converging trendlines, trading whichever direction breaks out with volume confirmation.

**Building Blocks Used:**
- symmetrical_triangle
- volume_profile
- adx
- break_of_structure
- displacement

**Entry Conditions:**
1. Converging trendlines (higher lows, lower highs)
2. Both lines converging at similar angles
3. Volume declining during triangle formation
4. Breakout at 50-75% of pattern completion
5. Direction determined by breakout: Long if up, Short if down
6. Volume spike >2x average on breakout

**Exit Conditions:**
- Take Profit 1: Triangle height from breakout point (50% position)
- Take Profit 2: +5% (30% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Opposite side of triangle or -2%

**Filters:**
- Minimum 4 touches (2 upper, 2 lower)
- Follow prevailing trend direction (~75% continuation)
- Higher timeframe trend alignment preferred

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Direction-neutral continuation

---

### Strategy 48: Bullish Pennant Momentum

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Quick continuation pattern with sharp flagpole followed by small symmetrical triangle, breaking upward to continue momentum.

**Building Blocks Used:**
- pennant_pattern
- displacement
- volume_profile
- kill_zones
- fibonacci_retracements

**Entry Conditions:**
1. Sharp upward flagpole (15-40% in short time, high volume)
2. Small symmetrical triangle pennant forms (1-2 weeks max)
3. Pennant much smaller than flagpole
4. Volume declining in pennant, explosion on breakout
5. Entry during Kill Zone preferred

**Exit Conditions:**
- Take Profit 1: Flagpole length from breakout (60% position)
- Take Profit 2: +4% (30% position)
- Take Profit 3: Momentum fade (10% position)
- Stop Loss: Below pennant or -1.5%

**Filters:**
- Pennant must be compact (1-3 weeks)
- Flagpole with 3x+ volume
- Clear breakout direction matching flagpole

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - 65-75% success rate

---

### Strategy 49: Cup and Handle Breakout

**Trade Direction:** Long Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Bullish continuation pattern with rounded bottom (cup) followed by small consolidation (handle), breaking upward to new highs.

**Building Blocks Used:**
- cup_and_handle (custom combination of rounding_bottom + flag_pattern)
- volume_profile
- fibonacci_retracements
- wyckoff_reaccumulation
- adx

**Entry Conditions:**
1. Rounded bottom "cup" forms (3-6 months)
2. Price reaches near previous high (cup rim)
3. Small handle consolidation forms (downward drift or flag)
4. Handle retraces 38.2-50% of cup height
5. Price breaks above handle and cup rim with volume

**Exit Conditions:**
- Take Profit 1: Cup depth added to rim (40% position)
- Take Profit 2: +15% (40% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Below handle or -4%

**Filters:**
- Cup must be U-shaped (not V-shaped)
- Handle smaller than cup, downward/sideways drift
- Volume declining in handle, surge on breakout

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - High reliability, low frequency

---

### Strategy 50: Rounding Bottom Reversal

**Trade Direction:** Long Trade  
**Trade Chart:** Weekly Candles  
**Strategy Description:** Long-term reversal pattern with gradual U-shaped curve, indicating slow accumulation transitioning to bullish trend.

**Building Blocks Used:**
- rounding_bottom
- wyckoff_accumulation
- elliott_wave_count
- volume_profile
- adx

**Entry Conditions:**
1. Gradual U-shaped price curve (6-12 months)
2. Volume follows U-shape (high at left, low at bottom, high at right)
3. ADX shows trend strength increasing on right side
4. Wyckoff Accumulation Phase D or E
5. Price breaks above neckline (bowl rim)

**Exit Conditions:**
- Take Profit 1: Bowl depth added to rim (30% position)
- Take Profit 2: +20% (40% position)
- Take Profit 3: Long-term hold or Elliott Wave 5 complete (30% position)
- Stop Loss: Re-entry into bowl or -5%

**Filters:**
- Minimum 6-month formation period
- Volume must follow U-curve pattern
- No sharp V-reversals (gradual curve required)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - Position trade, very low frequency

---

### Strategy 51: Harmonic Gartley Pattern Long

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** 5-point harmonic pattern (X-A-B-C-D) with specific Fibonacci ratios, entering at D completion for high-probability reversal.

**Building Blocks Used:**
- harmonic_patterns (Gartley)
- fibonacci_retracements
- rsi_divergence
- volume_profile
- order_block

**Entry Conditions:**
1. Gartley pattern identified: B = 61.8% of XA
2. C = 38.2-88.6% of AB
3. D = 78.6% retracement of XA (Pattern Completion Zone)
4. CD = 127-161.8% extension of AB
5. RSI divergence at D point adds confluence
6. Bullish reversal candle at D (PCZ)

**Exit Conditions:**
- Take Profit 1: A point level (40% position)
- Take Profit 2: 61.8% retracement of AD (40% position)
- Take Profit 3: 161.8% extension (20% position)
- Stop Loss: Below D point or X point (conservative)

**Filters:**
- All Fibonacci ratios must align precisely
- Pattern takes 3-8 weeks to form
- Volume confirmation on reversal at D

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - 80-90% accuracy

---

### Strategy 52: Harmonic Butterfly Reversal

**Trade Direction:** Short Trade (also Long inverted)  
**Trade Chart:** Daily Candles  
**Strategy Description:** Extreme harmonic pattern with D point extending beyond X, signaling major reversal at over-extended levels.

**Building Blocks Used:**
- harmonic_patterns (Butterfly)
- fibonacci_retracements
- rsi_divergence
- elliott_wave_count
- volume_profile

**Entry Conditions:**
1. Butterfly pattern: B = 78.6% of XA
2. C = 38.2-88.6% of AB
3. D = 127% or 161.8% extension of XA (beyond X point)
4. CD = 161.8-261.8% extension of BC
5. D point shows RSI divergence (major exhaustion)
6. Entry at D completion in Pattern Completion Zone

**Exit Conditions:**
- Take Profit 1: C level (40% position)
- Take Profit 2: A level (40% position)
- Take Profit 3: 61.8% AD retracement (20% position)
- Stop Loss: Beyond D extension or +3%

**Filters:**
- D must extend significantly beyond X point
- Common at major tops/bottoms
- Volume climax at D point

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Major reversal pattern

---

### Strategy 53: Harmonic Bat Pattern Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Tight harmonic pattern with shallow B retracement and precise 88.6% D completion, offering tight stop with high R:R.

**Building Blocks Used:**
- harmonic_patterns (Bat)
- fibonacci_retracements
- stochastic_rsi_cross
- order_block
- volume_profile

**Entry Conditions:**
1. Bat pattern: B = 38.2-50% of XA (shallow retracement)
2. C = 38.2-88.6% of AB
3. D = 88.6% retracement of XA (precise PCZ)
4. CD = 161.8-261.8% extension of BC
5. Stochastic RSI crosses up at D point
6. Order Block at D level adds confluence

**Exit Conditions:**
- Take Profit 1: 38.2% AD retracement (40% position)
- Take Profit 2: A point (40% position)
- Take Profit 3: 161.8% extension (20% position)
- Stop Loss: Tight below D (88.6% allows tight stop) or -1.5%

**Filters:**
- 88.6% D level critical (tighter than Gartley)
- Allows very tight stop-loss
- Best risk:reward ratio among harmonic patterns

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - Tight stop, high R:R

---

### Strategy 54: Harmonic Crab Pattern Long

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Deepest harmonic extension pattern with D at 161.8% of XA, indicating extreme reversal potential at stretched levels.

**Building Blocks Used:**
- harmonic_patterns (Crab)
- fibonacci_retracements
- rsi_divergence
- elliott_wave_count
- volume_profile

**Entry Conditions:**
1. Crab pattern: B = 38.2-61.8% of XA
2. C = 38.2-88.6% of AB
3. D = 161.8% extension of XA (deep extension PCZ)
4. CD = 224-361.8% extension of BC (extreme extension)
5. RSI extreme divergence at D (oversold/overbought)
6. Volume climax at D point

**Exit Conditions:**
- Take Profit 1: 61.8% AD retracement (40% position)
- Take Profit 2: A point (40% position)
- Take Profit 3: C level (20% position)
- Stop Loss: Beyond D extension or -2.5%

**Filters:**
- D must reach 161.8% XA extension minimum
- Extreme price levels (support/resistance)
- Major reversal setup (low frequency)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Extreme reversal pattern

---

### Strategy 55: W-Bottom Bollinger Pattern

**Trade Direction:** Long Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Bollinger Band-specific pattern with double bottom where second low stays inside bands, confirming trend reversal per Bollinger.

**Building Blocks Used:**
- bollinger_bands
- double_bottom
- rsi_divergence
- volume_profile
- macd_signal

**Entry Conditions:**
1. First bottom touches or breaks lower Bollinger Band
2. Second bottom stays inside lower band (shows strength)
3. RSI bullish divergence between bottoms
4. MACD bullish crossover after second bottom
5. Price breaks above neckline and middle Bollinger Band

**Exit Conditions:**
- Take Profit 1: Upper Bollinger Band (50% position)
- Take Profit 2: +8% (30% position)
- Take Profit 3: Trailing stop at middle band (20% position)
- Stop Loss: Below second bottom or -3%

**Filters:**
- Second bottom must be inside lower band
- Volume declining on second bottom
- John Bollinger's signature pattern

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Bollinger-specific reversal

---

## INSTITUTIONAL & VOLUME STRATEGIES

---

### Strategy 56: Wyckoff Accumulation Phase D

**Trade Direction:** Long Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Entering during Wyckoff Accumulation Phase D after Spring, on Sign of Strength (SOS) and Last Point of Support (LPS).

**Building Blocks Used:**
- wyckoff_accumulation
- volume_profile
- break_of_structure
- order_block
- displacement

**Entry Conditions:**
1. Wyckoff Accumulation Phase C complete (Spring occurred)
2. Phase D: Sign of Strength (SOS) breaks above trading range
3. Price retraces to Last Point of Support (LPS)
4. Volume on SOS breakout >2x average
5. LPS retest with reduced volume (accumulation confirmed)

**Exit Conditions:**
- Take Profit 1: +8% (30% position)
- Take Profit 2: +15% (40% position)
- Take Profit 3: Phase E markup exhaustion (30% position)
- Stop Loss: Below LPS or back into trading range -4%

**Filters:**
- Must have clear Spring in Phase C
- SOS must be decisive with strong volume
- LPS should show lower volume (strength)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - High probability after accumulation

---

### Strategy 57: Wyckoff Spring Entry

**Trade Direction:** Long Trade  
**Trade Chart:** Weekly Candles  
**Strategy Description:** Entering on Wyckoff Spring - false breakdown below support that quickly reverses, shaking out weak holders before markup.

**Building Blocks Used:**
- wyckoff_accumulation
- liquidity_sweep
- volume_profile
- breaker_block
- displacement

**Entry Conditions:**
1. Wyckoff Accumulation Phase B or C identified
2. Spring: Price breaks below support/trading range
3. Rapid reversal back above support within 1-2 weeks
4. Volume spike on spring, strong volume on reversal
5. Entry on LPS (Last Point of Support) retest after spring

**Exit Conditions:**
- Take Profit 1: +10% (30% position)
- Take Profit 2: +20% (40% position)
- Take Profit 3: Wyckoff Distribution signals (30% position)
- Stop Loss: Below spring low or -5%

**Filters:**
- Spring must be brief (1-2 weeks maximum)
- Reversal must be strong and decisive
- Best after months of accumulation

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - Major accumulation completion

---

### Strategy 58: Volume Profile POC Bounce

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Mean reversion strategy entering on bounces from Point of Control (POC) - the price level with highest traded volume.

**Building Blocks Used:**
- volume_profile
- pivot_points
- stochastic_rsi_cross
- order_block
- fair_value_gap

**Entry Conditions:**
1. POC identified from recent session or range
2. Price pulls back to test POC level
3. POC acts as magnetic support/resistance
4. Stochastic RSI crosses up at POC level
5. Order Block or Fair Value Gap at POC adds confluence

**Exit Conditions:**
- Take Profit 1: Value Area High (VAH) (50% position)
- Take Profit 2: +2.5% (30% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Beyond Value Area Low or -1.5%

**Filters:**
- POC must be clearly defined with significant volume
- Price returns to POC act as magnet
- Works in both trending and ranging markets

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - Volume-based mean reversion

---

### Strategy 59: High Volume Node Support

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Entering at High Volume Nodes (HVN) where significant trading activity occurred, expecting support during pullbacks.

**Building Blocks Used:**
- volume_profile
- fibonacci_retracements
- order_block
- rsi_divergence
- pivot_points

**Entry Conditions:**
1. High Volume Node identified (significant price level with heavy trading)
2. Price retraces to HVN during uptrend pullback
3. HVN aligns with Fibonacci level (38.2%, 50%, 61.8%)
4. Order Block or pivot point at HVN adds confluence
5. Bullish rejection candle at HVN (long wick, bullish close)

**Exit Conditions:**
- Take Profit 1: Previous high (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: Next HVN resistance (20% position)
- Stop Loss: Below HVN or -2%

**Filters:**
- HVN must have significant volume concentration
- Higher timeframe uptrend required
- Multiple timeframe HVN alignment preferred

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Volume cluster support

---

### Strategy 60: Order Flow Imbalance Long

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Identifying order flow imbalances (excess buying pressure) through aggressive candles and delta volume, entering on continuation.

**Building Blocks Used:**
- volume_profile
- displacement
- fair_value_gap
- order_block
- kill_zones

**Entry Conditions:**
1. Order flow imbalance: Displacement candle with 3x+ volume
2. Fair Value Gap created (price imbalance)
3. Aggressive buying (positive delta if available)
4. Entry on first pullback to FVG or Order Block
5. During Kill Zone for institutional flow

**Exit Conditions:**
- Take Profit 1: +1.5% (50% position)
- Take Profit 2: +2.5% (30% position)
- Take Profit 3: Order flow reversal (20% position)
- Stop Loss: Below FVG or -1%

**Filters:**
- Clear order flow direction (one-sided volume)
- Displacement with minimal retracement
- High-volume session required

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Order flow momentum

---

### Strategy 61: Absorption Pattern Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Identifying price absorption zones where large orders are being filled, entering after absorption complete and price released.

**Building Blocks Used:**
- volume_profile
- order_block
- wyckoff_accumulation
- displacement
- fair_value_gap

**Entry Conditions:**
1. Absorption: Price consolidates with high volume but minimal movement
2. Wyckoff accumulation or Order Block forming
3. Volume spike without price movement (absorption occurring)
4. Price breaks out of absorption zone with displacement
5. Fair Value Gap created on breakout

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +3.5% (40% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Back into absorption zone or -1.5%

**Filters:**
- High volume with low price movement (consolidation)
- Clear breakout from absorption zone required
- Volume surge on breakout confirms completion

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Institutional accumulation

---

### Strategy 62: Volume Climax Reversal

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Entering after volume climax (extreme volume spike with price exhaustion), expecting reversal as panic subsides.

**Building Blocks Used:**
- volume_profile
- wyckoff_accumulation
- rsi_divergence
- stochastic_rsi_cross
- elliott_wave_count

**Entry Conditions:**
1. Volume climax: 5x+ average volume on selling candle
2. Price makes low with extreme fear/panic selling
3. RSI extremely oversold (<25) or bullish divergence
4. Stochastic RSI crosses up from extreme oversold
5. Wyckoff Selling Climax or Elliott Wave 5 exhaustion

**Exit Conditions:**
- Take Profit 1: +4% (40% position)
- Take Profit 2: +7% (40% position)
- Take Profit 3: Volume climax in opposite direction (20% position)
- Stop Loss: Below climax low or -2.5%

**Filters:**
- Extreme volume required (5x+ average)
- Price exhaustion pattern (long wick reversal)
- Capitulation characteristics present

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Capitulation reversal

---

### Strategy 63: Pivot Point Support Bounce

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Mathematical support/resistance strategy entering on bounces from daily pivot points, especially at S1 and S2 levels.

**Building Blocks Used:**
- pivot_points
- stochastic_rsi_cross
- volume_profile
- order_block
- session_time

**Entry Conditions:**
1. Daily Pivot Points calculated from previous day
2. Price tests Pivot Point (PP), S1, or S2 support
3. Bullish rejection candle at pivot level
4. Stochastic RSI crosses up
5. Volume Profile POC or Order Block at pivot adds confluence

**Exit Conditions:**
- Take Profit 1: Pivot Point (if entered at S1) (50% position)
- Take Profit 2: R1 resistance (30% position)
- Take Profit 3: R2 resistance (20% position)
- Stop Loss: Below next pivot support or -1.5%

**Filters:**
- Price must be above PP for bullish bias
- Pivot level holds on first test (no break)
- Session timing important (best during active hours)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - Mathematical support levels

---

### Strategy 64: Session Opening Range Breakout

**Trade Direction:** Long Trade  
**Trade Chart:** 5 Min Candles  
**Strategy Description:** Trading breakouts from first 30-60 minutes of London or New York session, capturing institutional opening range expansion.

**Building Blocks Used:**
- session_time
- kill_zones
- displacement
- fair_value_gap
- volume_profile

**Entry Conditions:**
1. Identify opening range: First 30 min of London or NY session
2. Mark opening range high and low
3. Price breaks above opening range high with volume
4. Displacement candle confirms strong breakout
5. Fair Value Gap created on breakout

**Exit Conditions:**
- Take Profit 1: Opening range height added to breakout (50% position)
- Take Profit 2: +1.5% (30% position)
- Take Profit 3: End of session or momentum fade (20% position)
- Stop Loss: Back into opening range or -0.8%

**Filters:**
- Only trade London or NY session opens
- Volume on breakout >2x opening range average
- Clear directional move required

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - Session breakout scalping

---

### Strategy 65: HOD/LOD Liquidity System

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Trading liquidity sweeps and bounces at High/Low of Day levels, where stops cluster and institutional players hunt liquidity.

**Building Blocks Used:**
- hod
- lod
- liquidity_sweep
- fair_value_gap
- order_block
- kill_zones

**Entry Conditions:**
1. HOD or LOD established (intraday high/low)
2. Multiple tests of level (liquidity building)
3. Liquidity sweep: Brief break of LOD, rapid reversal
4. Fair Value Gap or Order Block at reversal point
5. Entry during Kill Zone with confirmation candle

**Exit Conditions:**
- Take Profit 1: Midpoint between LOD and HOD (50% position)
- Take Profit 2: HOD (if entered at LOD sweep) (30% position)
- Take Profit 3: New HOD (20% position)
- Stop Loss: Beyond sweep extreme or -1.2%

**Filters:**
- Level must be tested 2+ times (liquidity pool)
- Sweep must be brief (1-2 candles)
- Reversal must be strong with volume

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Intraday liquidity play

---

## ELLIOTT WAVE & CYCLE STRATEGIES

---

### Strategy 66: Elliott Wave 3 Momentum Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Entering during Elliott Wave 3 - the strongest wave with highest momentum, after Wave 2 retracement completes.

**Building Blocks Used:**
- elliott_wave_count
- elliott_wave_oscillator
- fibonacci_retracements
- displacement
- adx

**Entry Conditions:**
1. Elliott Wave count identifies completed Wave 1 and Wave 2
2. Wave 2 retraces 50-61.8% of Wave 1 (typical correction)
3. Wave 2 does not exceed Wave 1 start (invalidation level)
4. Entry as Wave 3 begins (displacement candle)
5. Elliott Wave Oscillator shows sharp spike (Wave 3 momentum)
6. ADX rising above 30 (strong trend)

**Exit Conditions:**
- Take Profit 1: 161.8% extension of Wave 1 (40% position)
- Take Profit 2: +8% or when Wave 3 characteristics fade (40% position)
- Take Profit 3: Wave 4 pullback begins (20% position)
- Stop Loss: Below Wave 2 low or -2.5%

**Filters:**
- Wave 3 never shortest wave (usually longest)
- EWO momentum spike confirms Wave 3
- Volume expansion on Wave 3

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Strongest wave momentum

---

### Strategy 67: Wave 4 Pullback Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Entering after Wave 4 retracement completes, targeting Wave 5 final move. Wave 4 typically retraces 38.2% of Wave 3.

**Building Blocks Used:**
- elliott_wave_count
- fibonacci_retracements
- rsi_divergence
- order_block
- stochastic_rsi_cross

**Entry Conditions:**
1. Wave 3 completed and identified
2. Wave 4 retraces 38.2% of Wave 3 (typical correction)
3. Wave 4 does NOT overlap Wave 1 territory (invalidation rule)
4. Fibonacci 38.2% level with Order Block confluence
5. Stochastic RSI crosses up after Wave 4 completion

**Exit Conditions:**
- Take Profit 1: 61.8-100% of Wave 1 length (40% position)
- Take Profit 2: +5% or RSI divergence signal (40% position)
- Take Profit 3: Wave 5 exhaustion signals (20% position)
- Stop Loss: Wave 4 overlaps Wave 1 or -2%

**Filters:**
- Wave 4 must not overlap Wave 1 price territory
- Typically 38.2% retracement of Wave 3
- Look for RSI/MACD divergence at Wave 5 completion

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Final wave entry

---

### Strategy 68: Elliott Wave 5 Exhaustion Short

**Trade Direction:** Short Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Reversal strategy entering short when Elliott Wave 5 shows exhaustion through divergence and reduced momentum.

**Building Blocks Used:**
- elliott_wave_count
- elliott_wave_oscillator
- rsi_divergence
- macd_signal
- volume_profile

**Entry Conditions:**
1. Wave 5 identified and approaching completion
2. RSI bearish divergence (price higher high, RSI lower high)
3. MACD bearish divergence at Wave 5 peak
4. Elliott Wave Oscillator showing lower high than Wave 3
5. Volume declining on Wave 5 compared to Wave 3

**Exit Conditions:**
- Take Profit 1: Wave 4 low (40% position)
- Take Profit 2: 61.8% retracement of entire 5-wave structure (40% position)
- Take Profit 3: ABC correction completion (20% position)
- Stop Loss: Above Wave 5 high or +3%

**Filters:**
- Multiple divergence signals required (RSI, MACD, EWO)
- Wave 5 should show declining volume
- Best at major cycle tops

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Wave exhaustion reversal

---

### Strategy 69: ABC Correction Completion

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Entering at completion of ABC corrective wave structure, expecting resumption of primary trend after correction ends.

**Building Blocks Used:**
- elliott_wave_count
- fibonacci_retracements
- rsi_divergence
- stochastic_rsi_cross
- order_block

**Entry Conditions:**
1. 5-wave impulse completed, ABC correction underway
2. Wave A completes (initial counter-trend move)
3. Wave B retraces 50-61.8% of Wave A
4. Wave C extends to 100% or 161.8% of Wave A length
5. C wave completion at Fibonacci level (38.2-61.8% of impulse)
6. Stochastic RSI crosses up, RSI shows bullish divergence

**Exit Conditions:**
- Take Profit 1: Previous impulse high (40% position)
- Take Profit 2: 161.8% extension (40% position)
- Take Profit 3: New 5-wave impulse completes (20% position)
- Stop Loss: C wave extends beyond 161.8% or -2.5%

**Filters:**
- ABC structure must be clear
- C wave typically equals or extends A wave
- Fibonacci confluence at C completion

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Correction completion entry

---

### Strategy 70: Wave Extension Continuation

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Trading extended waves (Wave 3 or Wave 5 extending beyond typical Fibonacci levels), riding exceptional momentum.

**Building Blocks Used:**
- elliott_wave_count
- fibonacci_retracements
- adx
- displacement
- volume_profile

**Entry Conditions:**
1. Wave extends beyond typical Fibonacci levels
2. Wave 3 extending past 161.8% of Wave 1, or Wave 5 past 100% of Wave 1
3. ADX > 40 (very strong trend)
4. Elliott Wave Oscillator extremely elevated
5. Enter on brief pullback within extended wave

**Exit Conditions:**
- Take Profit 1: 261.8% extension (40% position)
- Take Profit 2: 361.8% extension (30% position)
- Take Profit 3: Momentum exhaustion (30% position)
- Stop Loss: Breakdown of wave structure or -2.5%

**Filters:**
- Extensions occur in strongest trends
- Typically only one wave extends (3 or 5, rarely both)
- ADX must show exceptional strength

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - Parabolic extension riding

---

### Strategy 71: Elliott Oscillator Divergence

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Using Elliott Wave Oscillator specifically to identify Wave 5 exhaustion through momentum divergence.

**Building Blocks Used:**
- elliott_wave_oscillator
- elliott_wave_count
- rsi_divergence
- fibonacci_retracements
- volume_profile

**Entry Conditions:**
1. EWO (5 EMA - 35 EMA) tracked throughout wave structure
2. Wave 5 identified in progress
3. EWO shows lower high than Wave 3 peak (divergence)
4. Price makes higher high but momentum declining
5. Additional RSI divergence confirms

**Exit Conditions:**
- Take Profit 1: +4% (40% position)
- Take Profit 2: ABC correction target (40% position)
- Take Profit 3: Opposite trend develops (20% position)
- Stop Loss: Wave 5 extends beyond projections or +2.5%

**Filters:**
- EWO must show clear divergence
- Works best at major degree wave completions
- Combine with volume analysis

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Momentum divergence system

---

### Strategy 72: Cycle Bottom Accumulation

**Trade Direction:** Long Trade  
**Trade Chart:** Weekly Candles  
**Strategy Description:** Long-term position entry at Bitcoin cycle bottoms (-80% drawdowns), combining Elliott Wave, Wyckoff, and multi-year cycle analysis.

**Building Blocks Used:**
- elliott_wave_count
- wyckoff_accumulation
- rsi_divergence
- volume_profile
- fibonacci_retracements

**Entry Conditions:**
1. Bitcoin -70% to -85% drawdown from cycle peak
2. Elliott Wave suggests cycle wave completion
3. Wyckoff Accumulation Phase C (Spring) or Phase D
4. RSI extreme oversold <25 with bullish divergence
5. Volume climax followed by accumulation

**Exit Conditions:**
- Take Profit 1: +100% (20% position)
- Take Profit 2: +200% (30% position)
- Take Profit 3: +400% or next cycle peak signals (50% position)
- Stop Loss: New all-time low below cycle bottom or -20%

**Filters:**
- Only at major 4-year Bitcoin cycle bottoms
- Multiple timeframe confirmation (weekly, monthly)
- Historical precedent (-85% typical bottom)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:5+ - Multi-year position, very low frequency

---

### Strategy 73: Impulse Wave Identification

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Identifying start of new 5-wave impulse structure early, entering on Wave 1 or early Wave 3 for maximum profit potential.

**Building Blocks Used:**
- elliott_wave_count
- displacement
- break_of_structure
- adx
- volume_profile

**Entry Conditions:**
1. Potential Wave 1: Displacement candle breaking structure
2. Break of Structure (BOS) or Market Structure Shift (MSS)
3. Wave 1 shows strong momentum and volume
4. Entry on Wave 2 retracement (50-61.8% of Wave 1)
5. ADX rising, confirming trend development

**Exit Conditions:**
- Take Profit 1: Wave 3 completion (~161.8%) (40% position)
- Take Profit 2: Wave 5 completion (40% position)
- Take Profit 3: Entire impulse wave structure completes (20% position)
- Stop Loss: Wave 2 exceeds Wave 1 start or -2%

**Filters:**
- Wave 1 must have clear impulse characteristics
- Wave 2 cannot retrace >61.8% (preferred) or >100% (invalidation)
- Volume and momentum support impulse structure

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - Early impulse entry

---

### Strategy 74: Corrective Wave C Entry

**Trade Direction:** Short Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Shorting at completion of corrective Wave B, targeting Wave C decline which often equals or exceeds Wave A length.

**Building Blocks Used:**
- elliott_wave_count
- fibonacci_retracements
- rsi_divergence
- head_and_shoulders (Wave B can form complex tops)
- stochastic_rsi_cross

**Entry Conditions:**
1. ABC correction identified, Wave A complete
2. Wave B retraces 50-61.8% of Wave A (bear market rally)
3. Wave B shows exhaustion (RSI divergence, lower volume)
4. Wave B completion at Fibonacci resistance
5. Stochastic RSI crosses down from overbought

**Exit Conditions:**
- Take Profit 1: 100% of Wave A length (40% position)
- Take Profit 2: 161.8% of Wave A length (40% position)
- Take Profit 3: ABC correction completes (20% position)
- Stop Loss: Wave B extends beyond 100% of previous impulse or +2.5%

**Filters:**
- Wave B typically 50-76.4% retracement
- Wave C often equals or extends Wave A (100-161.8%)
- Corrective structures have lower volume

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Correction Wave C short

---

### Strategy 75: Multi-Wave Confluence System

**Trade Direction:** Long Trade  
**Trade Chart:** Multiple Timeframes (Daily trend, 4H setup, 1H entry)  
**Strategy Description:** Advanced system requiring Elliott Wave alignment across multiple timeframes for highest-probability entries.

**Building Blocks Used:**
- elliott_wave_count (multiple timeframes)
- fibonacci_retracements
- optimal_trade_entry
- order_block
- adx

**Entry Conditions:**
1. Daily: Wave 3 of larger degree in progress
2. 4 Hour: Wave 2 of smaller degree completing
3. 1 Hour: Wave 1 identified, entering on Wave 2 pullback
4. All timeframes show bullish wave structure
5. Entry at Fibonacci confluence across timeframes

**Exit Conditions:**
- Take Profit 1: 1H Wave 3 completion (40% position)
- Take Profit 2: 4H Wave 3 completion (40% position)
- Take Profit 3: Daily wave structure targets (20% position)
- Stop Loss: 1H wave structure invalidation or -2%

**Filters:**
- All three timeframes must align in wave count
- Fibonacci levels should overlap across timeframes
- ADX confirming trend on all timeframes

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - Multi-timeframe wave confluence

---

## MULTI-CONFLUENCE STRATEGIES

---

### Strategy 76: Triple Confluence Long Setup

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Requiring three major confluence factors: Technical pattern + SMC concept + Fibonacci level for highest-probability setups.

**Building Blocks Used:**
- double_bottom OR inverse_head_and_shoulders
- order_block OR fair_value_gap
- fibonacci_retracements
- volume_profile
- kill_zones

**Entry Conditions:**
1. Technical Pattern: Double Bottom or Inverse H&S completing
2. SMC Concept: Order Block or Fair Value Gap at pattern completion
3. Fibonacci: Pattern completes at 61.8% or 78.6% Fib level
4. Volume Profile: POC or HVN at entry level
5. Kill Zone: Entry during London or NY AM session

**Exit Conditions:**
- Take Profit 1: Pattern measured move (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: Trailing stop (20% position)
- Stop Loss: Pattern invalidation or -2%

**Filters:**
- Minimum 3 confluence factors required
- All factors must align at same price zone
- Higher timeframe trend supportive

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Maximum confluence setup

---

### Strategy 77: Institutional Footprint Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Combining all institutional/smart money indicators: Liquidity Sweep + Order Block + FVG + Breaker Block for ultimate SMC setup.

**Building Blocks Used:**
- liquidity_sweep
- order_block
- fair_value_gap
- breaker_block
- optimal_trade_entry
- kill_zones

**Entry Conditions:**
1. Liquidity Sweep below support (stop hunt)
2. Breaker Block forms at failed support
3. Fair Value Gap created on reversal
4. Order Block within or near FVG
5. Entry aligns with OTE (62-79%) zone
6. During active Kill Zone

**Exit Conditions:**
- Take Profit 1: +2.5% (40% position)
- Take Profit 2: +4% (40% position)
- Take Profit 3: Next liquidity pool (20% position)
- Stop Loss: Below setup or -1.5%

**Filters:**
- All SMC components must be present
- Kill Zone timing mandatory
- Highest probability ICT setup

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Complete institutional setup

---

### Strategy 78: Multi-Timeframe Alignment

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min entry, 1H setup, 4H trend, Daily bias  
**Strategy Description:** Requiring bullish alignment across 4 timeframes: Daily bias, 4H structure, 1H setup, 15min entry for maximum probability.

**Building Blocks Used:**
- 50_ema_vector_break (all timeframes)
- market_structure_shift (4H)
- optimal_trade_entry (1H)
- order_block (15min)
- adx (4H)

**Entry Conditions:**
1. Daily: Price above 50 EMA (macro bullish bias)
2. 4 Hour: Market Structure Shift bullish, ADX > 25
3. 1 Hour: OTE zone (62-79%) retracement in progress
4. 15 Min: Order Block + bullish entry candle
5. All timeframes showing bullish structure

**Exit Conditions:**
- Take Profit 1: 1H target (40% position)
- Take Profit 2: 4H target (40% position)
- Take Profit 3: Daily structure level (20% position)
- Stop Loss: 15min structure breaks or -1.5%

**Filters:**
- All 4 timeframes must be aligned
- No counter-trend signals on higher timeframes
- Entry only when all conditions met

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Complete timeframe alignment

---

### Strategy 79: Session + Structure Confluence

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Combining session-based timing with market structure: Asia accumulation + London manipulation + US distribution targeting Asia 50%.

**Building Blocks Used:**
- asia_session_50_percent
- session_time
- liquidity_sweep
- market_structure_shift
- fair_value_gap
- kill_zones

**Entry Conditions:**
1. Asia Session: Clear range established (accumulation)
2. London Session: Liquidity sweep creates manipulation
3. Market Structure Shift during London close or NY open
4. Fair Value Gap pointing toward Asia 50%
5. Entry during NY Kill Zone targeting Asia 50%

**Exit Conditions:**
- Take Profit 1: Asia 50% level (60% position)
- Take Profit 2: Opposite Asia boundary (30% position)
- Take Profit 3: Trailing stop (10% position)
- Stop Loss: Setup invalidation or -1.5%

**Filters:**
- Three-session pattern must be clear
- MSS must occur during session transition
- Asia range must be well-defined

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2 - ICT session model

---

### Strategy 80: ICT Unicorn Model Setup

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** The "perfect" ICT setup: FVG + Order Block + OTE + Breaker Block + Kill Zone timing - highest probability per ICT methodology.

**Building Blocks Used:**
- fair_value_gap
- order_block
- optimal_trade_entry
- breaker_block
- kill_zones
- liquidity_sweep

**Entry Conditions:**
1. Fair Value Gap created by displacement
2. Order Block overlapping or within FVG
3. FVG/OB combo at OTE level (62-79%, ideally 70.5%)
4. Breaker Block adds additional confluence
5. Entry during New York AM Kill Zone (08:00-11:00 EST)
6. Optional: Liquidity sweep before setup

**Exit Conditions:**
- Take Profit 1: +2% (40% position)
- Take Profit 2: +3.5% (40% position)
- Take Profit 3: Next structural target (20% position)
- Stop Loss: Below FVG/OB or -1.3%

**Filters:**
- All ICT components must align at same zone
- Kill Zone timing is mandatory
- First retest of FVG/OB preferred (fresh setup)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - ICT perfect setup

---

### Strategy 81: High Probability Reversal System

**Trade Direction:** Long Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Major reversal setup combining: Elliott Wave 5 exhaustion + Double divergence + Harmonic pattern + Wyckoff distribution.

**Building Blocks Used:**
- elliott_wave_count
- rsi_divergence
- macd_signal
- harmonic_patterns
- wyckoff_distribution
- volume_profile

**Entry Conditions:**
1. Elliott Wave 5 identified with exhaustion characteristics
2. RSI and MACD both show bearish divergence (for longs after Wave 5 down)
3. Harmonic pattern (Gartley, Butterfly, Bat) completion at Wave 5 end
4. Wyckoff showing Accumulation Phase C or D
5. Volume climax at bottom

**Exit Conditions:**
- Take Profit 1: +7% (40% position)
- Take Profit 2: +12% (40% position)
- Take Profit 3: New Elliott impulse completes (20% position)
- Stop Loss: Pattern/wave invalidation or -3%

**Filters:**
- Minimum 3 reversal signals required
- Must be at major support/resistance
- Higher timeframe supportive of reversal

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - Major reversal confluence

---

### Strategy 82: Momentum Breakout Confluence

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Breakout strategy with maximum confirmation: Pattern breakout + EMA break + Volume surge + ADX strength + Displacement.

**Building Blocks Used:**
- ascending_triangle OR flag_pattern
- 50_ema_vector_break
- displacement
- adx
- volume_profile
- break_of_structure

**Entry Conditions:**
1. Pattern: Ascending Triangle or Flag near completion
2. Price breaks above 50 EMA with vector candle
3. Displacement candle (3x+ volume, large body)
4. ADX > 30 and rising (strong trend)
5. Break of Structure confirming breakout
6. Volume surge >2x average

**Exit Conditions:**
- Take Profit 1: Pattern measured move (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: ADX starts declining (20% position)
- Stop Loss: Below breakout level or -2%

**Filters:**
- All momentum indicators must confirm
- Volume critical (minimum 2x average)
- Clean breakout (no false breaks)

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Confirmed momentum breakout

---

### Strategy 83: Support Cluster Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Multiple support confluence: Fibonacci + Pivot Point + Order Block + Volume Profile POC + EMA all at same level.

**Building Blocks Used:**
- fibonacci_retracements
- pivot_points
- order_block
- volume_profile
- 50_ema_vector_break

**Entry Conditions:**
1. Fibonacci 61.8% retracement level
2. Daily Pivot Point S1 or PP at same level
3. Order Block at the confluence zone
4. Volume Profile POC or HVN at level
5. 50 EMA at or near the support cluster
6. Bullish rejection candle at cluster

**Exit Conditions:**
- Take Profit 1: Fibonacci 38.2% (40% position)
- Take Profit 2: Previous high (40% position)
- Take Profit 3: Fibonacci 161.8% extension (20% position)
- Stop Loss: Below support cluster or -2%

**Filters:**
- Minimum 4 of 5 support factors must align
- Support cluster within tight price range (<1%)
- Higher timeframe uptrend

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Maximum support confluence

---

### Strategy 84: Resistance Rejection Short

**Trade Direction:** Short Trade  
**Trade Chart:** 4 Hour Candles  
**Strategy Description:** Shorting at major resistance confluence: Premium Zone + HOW + Fibonacci + Supply Zone + RSI divergence.

**Building Blocks Used:**
- premium_discount_zones
- how
- fibonacci_retracements
- supply_demand_zones
- rsi_divergence
- stochastic_rsi_cross

**Entry Conditions:**
1. Price in Premium Zone (above 62% of range)
2. At or near High of Week (HOW) resistance
3. Fibonacci 78.6% or 88.6% resistance level
4. Supply Zone at the confluence area
5. RSI bearish divergence
6. Stochastic RSI crosses down from overbought

**Exit Conditions:**
- Take Profit 1: Equilibrium (50% level) (50% position)
- Take Profit 2: Discount Zone (30% position)
- Take Profit 3: Low of Week (20% position)
- Stop Loss: Above resistance cluster or +2%

**Filters:**
- Minimum 4 resistance factors at same level
- Clear ranging or topping structure
- Volume declining on approach to resistance

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Maximum resistance rejection

---

### Strategy 85: Divergence + Pattern Confluence

**Trade Direction:** Long Trade  
**Trade Chart:** Daily Candles  
**Strategy Description:** Reversal setup combining bullish chart pattern with double divergence for high-probability major reversals.

**Building Blocks Used:**
- inverse_head_and_shoulders OR double_bottom OR falling_wedge
- rsi_divergence
- macd_signal
- stochastic_rsi_cross
- volume_profile

**Entry Conditions:**
1. Bullish pattern completing (IH&S, Double Bottom, Falling Wedge)
2. RSI shows bullish divergence at pattern lows
3. MACD shows bullish divergence
4. Stochastic RSI crosses up from oversold
5. Volume decreasing during pattern, spike on breakout

**Exit Conditions:**
- Take Profit 1: Pattern measured move (40% position)
- Take Profit 2: +10% (40% position)
- Take Profit 3: Opposite divergence appears (20% position)
- Stop Loss: Pattern invalidation or -3%

**Filters:**
- Both RSI and MACD divergence required
- Pattern must be well-formed
- At major support zone

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Pattern + divergence power

---

### Strategy 86: Volume + Price Action Setup

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Institutional volume footprint combined with price action: Volume Climax + Absorption + Wyckoff + Order Block.

**Building Blocks Used:**
- volume_profile
- wyckoff_accumulation
- order_block
- displacement
- fair_value_gap

**Entry Conditions:**
1. Volume climax (5x+ average volume on selling)
2. Price absorption (high volume, minimal movement)
3. Wyckoff Accumulation Phase C (Spring) or Phase D (SOS)
4. Order Block forms during accumulation
5. Displacement breakout from accumulation zone
6. Fair Value Gap created on breakout

**Exit Conditions:**
- Take Profit 1: +3% (40% position)
- Take Profit 2: +5% (40% position)
- Take Profit 3: Wyckoff markup exhaustion (20% position)
- Stop Loss: Below accumulation zone or -2%

**Filters:**
- Volume characteristics must be clear
- Wyckoff structure well-defined
- Breakout with strong displacement

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Volume-based institutional play

---

### Strategy 87: Kill Zone + OTE System

**Trade Direction:** Long Trade  
**Trade Chart:** 15 Min Candles  
**Strategy Description:** Perfect ICT timing setup: OTE retracement completing specifically during New York AM Kill Zone with FVG/OB confluence.

**Building Blocks Used:**
- kill_zones
- optimal_trade_entry
- fair_value_gap
- order_block
- fibonacci_retracements
- displacement

**Entry Conditions:**
1. Clear uptrend with displacement move
2. Retracement to OTE zone (62-79%, ideally 70.5%)
3. Fair Value Gap or Order Block at OTE level
4. Entry MUST occur during NY AM Kill Zone (08:00-11:00 EST)
5. Bullish confirmation candle at OTE

**Exit Conditions:**
- Take Profit 1: Previous high (40% position)
- Take Profit 2: Fibonacci -0.5 extension (40% position)
- Take Profit 3: Kill Zone ends or momentum fades (20% position)
- Stop Loss: Below OTE zone or -1.5%

**Filters:**
- Kill Zone timing is mandatory
- OTE level must have FVG or OB confluence
- Higher timeframe trend must support

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Timed OTE precision entry

---

### Strategy 88: Complete Market Profile Entry

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** Volume Profile system: Entry at POC with Value Area support, HVN confluence, and session context.

**Building Blocks Used:**
- volume_profile
- session_time
- asia_session_50_percent
- pivot_points
- order_block

**Entry Conditions:**
1. POC (Point of Control) identified
2. Price pulls back to POC or Value Area Low
3. High Volume Node at entry level
4. Session context: Asia 50% or session pivot alignment
5. Order Block at POC adds confluence
6. Entry during high-volume session

**Exit Conditions:**
- Take Profit 1: Value Area High (50% position)
- Take Profit 2: +3% (30% position)
- Take Profit 3: Opposite session level (20% position)
- Stop Loss: Below Value Area Low or -1.8%

**Filters:**
- POC must be clearly defined with heavy volume
- Entry at VAL (support) or VAH (resistance for shorts)
- Session context supporting trade direction

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:2.5 - Complete volume profile system

---

### Strategy 89: Advanced Smart Money Setup

**Trade Direction:** Long Trade  
**Trade Chart:** 30 Min Candles  
**Strategy Description:** Ultimate SMC setup: Market Structure Shift + Breaker Block + FVG + OTE + Liquidity Sweep + Premium/Discount + Kill Zone.

**Building Blocks Used:**
- market_structure_shift
- breaker_block
- fair_value_gap
- optimal_trade_entry
- liquidity_sweep
- premium_discount_zones
- kill_zones

**Entry Conditions:**
1. Market Structure Shift confirms potential reversal
2. Liquidity Sweep below structure (inducement)
3. Breaker Block forms at failed level
4. Fair Value Gap created on reversal
5. Entry aligns with OTE (62-79%) of recent swing
6. Price moves from Premium to Discount zone
7. Entry during active Kill Zone

**Exit Conditions:**
- Take Profit 1: +2.5% (40% position)
- Take Profit 2: +4% (40% position)
- Take Profit 3: Next MSS or structure level (20% position)
- Stop Loss: Setup invalidation or -1.5%

**Filters:**
- All 7 SMC components must be present
- This is the "ultimate" ICT setup
- Very rare but extremely high probability

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:3 - Perfect SMC storm

---

### Strategy 90: Ultimate Confluence Strategy

**Trade Direction:** Long Trade  
**Trade Chart:** 1 Hour Candles  
**Strategy Description:** The "everything" strategy requiring maximum possible confluence across all categories: Pattern + SMC + Elliott Wave + Wyckoff + Volume + Session + Divergence.

**Building Blocks Used:**
- inverse_head_and_shoulders OR harmonic_patterns
- fair_value_gap + order_block
- elliott_wave_count
- wyckoff_accumulation
- volume_profile
- kill_zones
- rsi_divergence + macd_signal
- fibonacci_retracements
- premium_discount_zones
- market_structure_shift

**Entry Conditions:**
1. **Pattern:** Bullish chart pattern or harmonic at completion
2. **SMC:** FVG + Order Block confluence
3. **Elliott:** Wave 2 or Wave 4 retracement, or ABC correction end
4. **Wyckoff:** Accumulation Phase D (LPS) or Spring
5. **Volume:** POC or HVN at entry level, volume climax reversal
6. **Session:** Active Kill Zone (London/NY AM)
7. **Divergence:** RSI and MACD bullish divergence
8. **Fibonacci:** Entry at 61.8% or OTE zone
9. **Zone:** Discount Zone entry
10. **Structure:** Market Structure Shift or BOS supporting entry

**Exit Conditions:**
- Take Profit 1: +5% (30% position)
- Take Profit 2: +8% (40% position)
- Take Profit 3: +12% or all signals reverse (30% position)
- Stop Loss: Multiple structure levels broken or -2%

**Filters:**
- Minimum 7 of 10 confluence factors required
- The more factors present, the higher probability
- Very rare setup (maybe 1-2 per month)
- When it appears, highest conviction trade

**BackTest 180 Days Results:** [Pending]  
**WalkForward 180 Days Test Results:** [Pending]  
**Strategy Assessment:** Risk:Reward 1:4 - **Maximum possible confluence, ultra-rare setup**

---

## USAGE GUIDELINES

### Strategy Selection Process

1. **Market Condition Assessment**
   - Trending Market: Use Trend Following Strategies (1-15)
   - Ranging Market: Use Mean Reversion Strategies (16-25)
   - High Volatility: Use Momentum/Breakout Strategies
   - Low Volatility: Use Session-based or Support/Resistance Strategies

2. **Time Commitment**
   - Scalping (5-15 min charts): Strategies 9, 16, 19, 26, 33, 64
   - Day Trading (15-30 min charts): Strategies 1, 8, 20, 21, 27, 28, 34
   - Swing Trading (1-4 hour charts): Strategies 2, 4, 6, 29, 37, 42, 43, 56
   - Position Trading (Daily-Weekly): Strategies 7, 41, 45, 46, 50, 72

3. **Skill Level**
   - Beginner: Start with Strategies 1, 8, 17, 19, 42
   - Intermediate: Strategies 26-40 (SMC), 41-55 (Patterns)
   - Advanced: Strategies 66-75 (Elliott Wave), 76-90 (Multi-Confluence)

4. **Risk Profile**
   - Conservative: Strategies requiring 5+ confluence factors (76-90)
   - Moderate: Pattern-based strategies (41-55)
   - Aggressive: Momentum and scalping strategies (9, 16, 33)

### Testing Protocol

1. **BackTest Phase (180 Days)**
   - Test on historical data
   - Record: Win Rate, Profit Factor, Maximum Drawdown, Average R:R
   - Minimum 100 trades for statistical significance

2. **Walk-Forward Phase (180 Days)**
   - Test on out-of-sample data
   - Validate strategy robustness
   - Compare to backtest results (should be within 10-15%)

3. **Optimization**
   - Adjust building block parameters
   - Fine-tune entry/exit conditions
   - Optimize for current market regime

4. **Live Paper Trading**
   - Test with real-time data
   - No real capital risk
   - Validate execution and psychology

5. **Live Trading**
   - Start with minimum position size
   - Scale up after proven results
   - Continuous monitoring and adjustment

### Risk Management Rules

1. **Position Sizing**
   - Risk 0.5-1% of account per trade
   - Higher confluence = larger position size (up to 2%)
   - Scale in/out according to exit conditions

2. **Stop Loss**
   - Always use stop loss
   - Place below structure, not arbitrary levels
   - Typical stop: 1-2% for scalping, 2-4% for swing trading

3. **Take Profit**
   - Use multiple take profit levels
   - Scale out: 40-50% at TP1, 30-40% at TP2, 10-20% trailing
   - Move stop to breakeven after TP1 hit

4. **Maximum Drawdown**
   - Stop trading if drawdown exceeds 10%
   - Review strategy and market conditions
   - Resume after analysis and adjustment

---

## CONCLUSION

This document provides **90 baseline strategies** built from your comprehensive building blocks system. Each strategy is designed to be:

- **Testable:** Clear entry/exit conditions
- **Modular:** Built from standardized building blocks
- **Scalable:** Can be adjusted for different timeframes
- **Optimizable:** Parameters can be tuned through backtesting

**Next Steps:**

1. Select 5-10 strategies matching your trading style
2. BackTest on 180 days of historical data
3. Walk-Forward test on next 180 days
4. Optimize top-performing strategies
5. Paper trade before live deployment

**Remember:** No strategy works 100% of the time. The key is finding strategies that match:
- Your personality and discipline
- Your available time and resources  
- Current market conditions
- Your risk tolerance

Good luck with your systematic strategy development using NautilusTrader!

---

**Document Version:** v1.0  
**Created:** January 1, 2026  
**Framework:** NautilusTrader  
**Building Blocks Source:** 0_Building_Blocks_Master.md v1