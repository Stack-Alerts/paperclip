# Trade Opportunity Detection Tools & Indicators

**BTC Scalp Bot V10 - Complete Signal Toolkit**

This document lists ALL tools, indicators, and methods used to identify trading opportunities across all layers.

---

## Layer 0: Multi-Timeframe Trend Foundation

### Purpose
Establishes directional bias (LONG_ONLY / SHORT_ONLY / NONE) - NOT an entry signal itself, but gates all other signals.

### Timeframes Analyzed
- **4H** (Primary - Absolute Authority): 50% weight
- **2H** (Intermediate): 25% weight
- **1H** (Micro Trend): 15% weight
- **30m** (Local Bias): 7% weight (planned)
- **15m** (Execution): 3% weight (planned)

### 4-Pillar Analysis (Per Timeframe)

#### 1. Market Structure (40% weight)
**What It Detects**: Price action patterns
- **Higher Highs (HH) + Higher Lows (HL)** → Bullish structure
- **Lower Highs (LH) + Lower Lows (LL)** → Bearish structure
- **Mixed pattern** → Ranging/Consolidation

**Lookback**: 50 bars
**Scoring**: -1.0 (strong bearish) to +1.0 (strong bullish)

#### 2. Moving Average Alignment (30% weight)
**Indicators Used**:
- **EMA 9** (Fast)
- **EMA 21** (Medium)
- **EMA 50** (Slow)

**What It Detects**:
- **Bullish**: Price > EMA9 > EMA21 > EMA50 (perfect stack)
- **Bearish**: Price < EMA9 < EMA21 < EMA50 (reverse stack)
- **EMA Slope**: Confirms direction (rising vs falling)
- **EMA Fanning**: Expanding distance = stronger trend

**Scoring**: -1.0 to +1.0

#### 3. MACD (20% weight)
**Parameters**: 12/26/9 (standard)

**What It Detects**:
- **MACD Line vs Signal Line**: Crossovers and position
- **Histogram**: Above/below zero, expanding/contracting
- **Rising MACD** → Bullish momentum
- **Falling MACD** → Bearish momentum

**Scoring**: -1.0 to +1.0

#### 4. RSI Context (10% weight)
**Parameter**: 14-period RSI

**What It Detects**:
- **Bullish Zone**: RSI 50-80 and rising
- **Bearish Zone**: RSI 20-50 and falling
- **Overextended**: RSI > 80 or < 20 (caution flag)

**Scoring**: -1.0 to +1.0

### Alignment Scoring
Combines all timeframes with hierarchical weights:
- **ALIGNED**: All 3 TFs agree → Confidence 1.0
- **PARTIAL**: 2 TFs agree → Confidence 0.6
- **CONFLICTED**: TFs disagree → Confidence 0.3

---

## Layer 1: Traditional Technical Analysis

### Purpose
Generate trading opportunities using classic technical indicators. Now configured as "opportunity generator" to produce 20-30 signals for filtering.

### Trend Analysis

#### 1. EMA Crossovers
**Indicators**:
- **EMA 9** (Fast)
- **EMA 20** (Slow)
- **EMA 50** (Trend)

**Signals**:
- **Bullish Crossover**: EMA 9 crosses above EMA 20
  - Strong if aligned with EMA 50 uptrend
  - Moderate if EMA 50 neutral
  - Weak if against EMA 50
- **Bearish Crossover**: EMA 9 crosses below EMA 20
- **Continuous Signals**: Also generates signals when already above/below (not just crossovers)

**Weight in Layer 1**: 10%

#### 2. Price-EMA Distance
**What It Detects**:
- Distance from EMA 9 → Overextension or pullback
- Distance from EMA 20 → Medium-term deviation
- Distance from EMA 50 → Long-term trend strength

**Usage**: Identifies pullback opportunities in trends

#### 3. EMA Slope Analysis
**What It Detects**:
- **Rising EMAs** → Uptrend confirmation
- **Falling EMAs** → Downtrend confirmation
- **Flat EMAs** → Ranging/consolidation

**Lookback**: 20 bars for slope calculation

### Momentum Analysis

#### 4. RSI (Relative Strength Index)
**Parameters**: 14-period, 21-period, 28-period

**Current Settings (Opportunity Generator)**:
- **Oversold**: 52 (nearly neutral - catches any downward momentum)
- **Overbought**: 48 (nearly neutral - catches any upward momentum)

**Traditional Settings** (when not in opportunity mode):
- Oversold: < 30
- Overbought: > 70

**Signals**:
- RSI < 48 → Potential long opportunity
- RSI > 52 → Potential short opportunity
- Divergence detection (planned)

**Weight in Layer 1**: 45% (PRIMARY signal generator)

#### 5. Stochastic Oscillator
**Parameters**: %K and %D lines

**Signals**:
- Overbought/Oversold conditions
- %K/%D crossovers
- Divergences

#### 6. Williams %R
**Parameter**: 14-period

**Signals**:
- < -80: Oversold
- > -20: Overbought
- Reversal signals

#### 7. Rate of Change (ROC)
**Periods**: 10, 21

**What It Detects**:
- Momentum strength and direction
- Velocity of price changes
- Divergence with price

#### 8. CCI (Commodity Channel Index)
**Periods**: 14, 20

**Signals**:
- > +100: Overbought
- < -100: Oversold
- Trend strength

#### 9. MFI (Money Flow Index)
**Parameter**: 14-period

**What It Detects**:
- Money flowing in/out (volume-weighted RSI)
- Overbought (>80) / Oversold (<20)
- Divergences

#### 10. MACD
**Parameters**: 12/26/9

**Signals**:
- MACD line crossing signal line
- Histogram expansion/contraction
- Zero-line crosses
- Divergences

**Weight in Layer 1**: Part of momentum (45%)

### Volatility Analysis

#### 11. ATR (Average True Range)
**Periods**: 14, 21

**What It Detects**:
- Current volatility level
- Volatility expansion/contraction
- Used for stop-loss and take-profit sizing

#### 12. Bollinger Bands
**Parameters**: 20-period SMA, 2 standard deviations

**Signals**:
- Price touching lower band → Potential bounce (long)
- Price touching upper band → Potential reversal (short)
- Band squeeze → Breakout imminent
- Band expansion → High volatility

**Weight in Layer 1**: 35% (SECONDARY signal generator)

#### 13. Keltner Channels
**What It Detects**:
- Volatility-based channels using ATR
- Similar to Bollinger but ATR-based
- Trend strength

#### 14. Donchian Channels
**What It Detects**:
- Price breakouts above/below channel
- Range boundaries
- Trend following signals

#### 15. Historical Volatility
**Calculation**: 20-period standard deviation of returns

**What It Detects**:
- Current volatility vs historical average
- High/low volatility regimes

**Weight in Layer 1**: 35%

### Volume Analysis

#### 16. OBV (On-Balance Volume)
**What It Detects**:
- Cumulative buying/selling pressure
- Volume trend vs price trend
- Divergences (price up, OBV down = bearish)

#### 17. VWAP (Volume Weighted Average Price)
**What It Detects**:
- Average price weighted by volume
- Support/resistance level
- Price above VWAP = bullish, below = bearish

#### 18. Volume Ratio
**Calculation**: Current volume / 20-period average

**Signals**:
- > 1.5x: High volume (confirmation)
- < 1.0x: Low volume (weak signal)

#### 19. ADI (Accumulation/Distribution Index)
**What It Detects**:
- Buying/selling pressure based on close position in range
- Divergences with price

#### 20. CMF (Chaikin Money Flow)
**What It Detects**:
- Money flow over period
- Positive CMF = accumulation
- Negative CMF = distribution

#### 21. PVT (Price Volume Trend)
**What It Detects**:
- Volume flow direction
- Trend confirmation

**Weight in Layer 1**: 5%

### Support/Resistance Analysis

#### 22. Swing Highs/Lows
**Lookback**: 50 bars

**What It Detects**:
- Recent resistance (swing highs)
- Recent support (swing lows)
- Distance to key levels

**Signals**:
- Near support → Bounce opportunity (long)
- Near resistance → Rejection opportunity (short)

**Weight in Layer 1**: 5%

### Trend Confirmation

#### 23. ADX (Average Directional Index)
**Parameter**: 14-period

**Current Setting**: 10 (very low - accepts weak trends)

**Traditional Setting**: 25+ for strong trend

**What It Detects**:
- Trend strength (not direction)
- ADX > 25: Strong trend
- ADX < 20: Weak/ranging

**Signals**:
- Rising ADX → Strengthening trend
- Falling ADX → Weakening trend

#### 24. Aroon Indicator
**What It Detects**:
- Aroon Up/Down lines
- Time since highest high / lowest low
- Trend strength and direction

#### 25. Supertrend
**What It Detects**:
- ATR-based trend following indicator
- Buy signal: Price > Supertrend
- Sell signal: Price < Supertrend

### Custom Scalping Indicators

#### 26. Price Momentum
**Periods**: 5, 10 bars

**Calculation**: (Close - Close[N]) / Close[N] * 100

**What It Detects**:
- Short-term momentum bursts
- Scalping opportunities

#### 27. EMA Cross Strength
**Calculation**: Distance between EMA 9 and EMA 20

**What It Detects**:
- Strength of crossover signal
- Larger distance = stronger signal

#### 28. Candle Pattern Analysis
**Patterns Analyzed**:
- **Body Size**: abs(close - open)
- **Upper Wick**: high - max(close, open)
- **Lower Wick**: min(close, open) - low
- **Body Ratio**: body / (high - low)

**What It Detects**:
- Hammer/Shooting Star
- Engulfing patterns
- Doji patterns
- Pin bars

#### 29. High-Low Range
**Calculation**: (high - low) / close * 100

**What It Detects**:
- Current candle volatility
- Expansion/contraction vs average

#### 30. Close-Open Range
**Calculation**: (close - open) / open * 100

**What It Detects**:
- Directional strength
- Bullish/bearish conviction

---

## Layer 2: Volume Delta Analysis

### Purpose
Analyze buy/sell volume imbalance and order flow.

### Tools

#### 31. Volume Delta
**Calculation**: Buy Volume - Sell Volume (per candle)

**What It Detects**:
- Buying pressure vs selling pressure
- Aggressive buyers vs sellers
- Hidden accumulation/distribution

#### 32. Cumulative Volume Delta (CVD)
**Calculation**: Running sum of Volume Delta

**Signals**:
- Rising CVD + Flat price → Accumulation (bullish)
- Falling CVD + Flat price → Distribution (bearish)
- CVD divergence → Reversal signal

#### 33. Buy/Sell Ratio
**Calculation**: Buy Volume / Sell Volume

**Signals**:
- > 1.2: Strong buying pressure
- < 0.8: Strong selling pressure

#### 34. Large Trade Detection
**What It Detects**:
- Unusually large volume candles
- Institutional activity
- Potential reversal or continuation

---

## Layer 3: Weis Wave Analysis

### Purpose
Analyze cumulative volume waves and wave strength.

### Tools

#### 35. Weis Waves
**What It Detects**:
- Volume waves (up waves vs down waves)
- Wave completion and reversals
- Wave strength comparison

#### 36. Wave Volume Analysis
**What It Detects**:
- Cumulative volume in each wave
- Strength of buying vs selling waves
- Wave exhaustion signals

#### 37. Wave Duration
**What It Detects**:
- Time/bars per wave
- Acceleration/deceleration
- Momentum shifts

---

## Layer 4: XGBoost Machine Learning

### Purpose
Use gradient boosting to predict price direction based on features.

### Input Features (50+)

#### 38. Technical Indicators
- All indicators from Layers 1-3
- Lagged values (T-1, T-2, T-3)
- Rate of change of indicators

#### 39. Price Patterns
- Recent price changes (1-bar, 2-bar, 3-bar)
- High/low positions
- Open/close relationships

#### 40. Volume Features
- Volume trends
- Volume-price correlations
- Volume acceleration

#### 41. Market Microstructure
- Bid-ask spread (when available)
- Order book depth (when available)
- Tick direction

### Model Output
- **Probability** of upward movement
- **Confidence score** (0-1)
- **Feature importance** ranking

---

## Layer 5: CNN-LSTM Deep Learning

### Purpose
Use deep learning to detect complex patterns in price/volume data.

### Input Features

#### 42. Multi-Timeframe OHLCV
- 15m, 1H, 4H bars
- Normalized price series
- Volume patterns

#### 43. Technical Indicator Sequences
- 50-bar sequences of key indicators
- Captures temporal patterns
- Learns market regimes

#### 44. Candlestick Patterns (Image-based)
- Visual pattern recognition
- Converts OHLC to images
- CNN extracts spatial features

#### 45. Volume Profile
- Price-volume distribution
- High-volume nodes
- Low-volume gaps

### Model Architecture
- **CNN**: Spatial pattern detection
- **LSTM**: Temporal sequence learning
- **Dense layers**: Classification

### Output
- **Directional probability**: Long/Short/Neutral
- **Confidence**: Based on model certainty
- **Pattern type**: What pattern was detected

---

## Layer 6: TradingView Alert Confluence (Planned)

### Purpose
Aggregate external signals from TradingView alerts.

### Signal Sources

#### 46. TradingView Strategies
**Integrated Strategies**:
- EMA crossover strategies
- RSI divergence strategies
- Volume breakout strategies
- Custom Pine Script indicators

#### 47. Alert Types
- **Entry signals**: Long/Short
- **Exit signals**: Take Profit/Stop Loss
- **Confirmation signals**: Trend/Volume/Momentum

#### 48. Multi-Indicator Confluence
**Tracks**:
- Number of alerts in same direction
- Time clustering of alerts
- Alert strength weighting

#### 49. External Indicator Feeds
- Premium indicators from TradingView marketplace
- Community signals
- Professional trader alerts

---

## Signal Combination & Weighting

### Layer Weights (Example Strategy)
```
Layer 0: N/A (Directional gatekeeper)
Layer 1: 25% (Traditional TA)
Layer 2: 15% (Volume Delta)
Layer 3: 10% (Weis Wave)
Layer 4: 25% (XGBoost ML)
Layer 5: 20% (CNN-LSTM DL)
Layer 6: 5% (TV Alerts)
```

### Compositor Logic
1. **Layer 0** establishes allowed direction
2. **Layers 1-6** generate signals (blocked if counter-trend)
3. **Weighted voting** combines signals
4. **Confidence threshold** filters weak signals
5. **Final signal** only if multiple layers agree

---

## Risk Management Indicators

### 50. ATR-Based Stop Loss
**Calculation**: Entry ± (2.0 × ATR)

**What It Does**:
- Adapts to volatility
- Wider stops in high volatility
- Tighter stops in low volatility

### 51. Risk-Reward Ratio
**Target**: 2:1 minimum

**Calculation**: Take Profit / Stop Loss distance

### 52. Drawdown Monitoring
**Tracks**:
- Current drawdown from peak
- Maximum historical drawdown
- Drawdown duration

### 53. Win Rate Tracking
**Monitors**:
- Recent win rate (last 10, 20, 50 trades)
- Win streak / Loss streak
- Adjusts position sizing based on performance

### 54. Correlation Analysis
**Monitors**:
- BTC correlation with ETH, alts
- Correlation with macro assets (DXY, SPX)
- Changes in correlation (regime shifts)

---

## Planned Enhancements (Exchange Data)

### 55. Order Book Imbalance
**Top 5-10 levels**:
- Bid volume vs Ask volume
- >65% bids = Bullish
- <35% bids = Bearish

### 56. Order Book Depth
**What It Detects**:
- Buy/sell walls
- Support/resistance from liquidity
- Absorption levels

### 57. Taker Buy/Sell Ratio
**What It Detects**:
- Aggressive buying vs selling
- Market vs limit order flow
- Institutional activity

### 58. Open Interest (Futures)
**What It Detects**:
- Total open positions
- Rising OI + Rising price = New longs (bullish)
- Rising OI + Falling price = New shorts (bearish)

### 59. Funding Rate (Perpetuals)
**What It Detects**:
- Long/Short imbalance
- Negative funding = Short squeeze setup
- Positive funding = Long squeeze setup

### 60. Liquidation Levels
**What It Detects**:
- Concentrated liquidation zones
- Potential cascading liquidations
- Stop hunt levels

### 61. Exchange Netflows
**What It Detects**:
- Coins moving to/from exchanges
- Outflow = Accumulation (bullish)
- Inflow = Distribution (bearish)

---

## Summary: Complete Signal Toolkit

### Core Entry Signals (30)
1. EMA Crossovers (9/20/50)
2. RSI Oversold/Overbought
3. MACD Crossovers
4. Bollinger Band Touches
5. Volume Confirmation
6. Support/Resistance Levels
7. Market Structure (HH/HL)
8. MA Alignment
9. Stochastic Signals
10. Williams %R
11. CCI Signals
12. MFI Signals
13. ADX Trend Strength
14. Aroon Signals
15. Supertrend
16. Volume Delta
17. CVD Divergence
18. Weis Wave Reversals
19. XGBoost Predictions
20. CNN-LSTM Patterns
21. TradingView Alerts
22. Price Momentum
23. Candle Patterns
24. ROC Signals
25. Keltner Touches
26. Donchian Breakouts
27. OBV Divergence
28. VWAP Position
29. CMF Signals
30. PVT Trends

### Confirmation Tools (20)
31-50: Various confirmation methods from ATR, volatility, volume, correlation, etc.

### Risk Management (10)
51-60: Stop loss, take profit, drawdown monitoring, position sizing

### Exchange Data (Planned) (11)
61-71: Order book, funding, OI, liquidations, netflows

**Total Tools**: 71+ indicators and methods for comprehensive market analysis

---

## Configuration Philosophy

### Layer 0 (Trend Foundation)
- **Conservative thresholds** for trend detection
- **High confidence required** for directional bias
- **Blocks all counter-trend signals**

### Layer 1 (Opportunity Generator)
- **Aggressive thresholds** to maximize opportunities
- **Low barriers** for signal generation
- **Produces 20-30 candidates for filtering**

### Layers 2-5 (Quality Filters)
- **Moderate to strict thresholds**
- **Filter out weak opportunities**
- **Keep only high-quality signals**

### Final Result
- **10-20 trades per 60 days**
- **60%+ win rate target**
- **All trend-aligned with Layer 0**

---

**Last Updated**: December 17, 2025  
**Version**: 1.0  
**Status**: Layer 0-5 Implemented, Layer 6 Planned
