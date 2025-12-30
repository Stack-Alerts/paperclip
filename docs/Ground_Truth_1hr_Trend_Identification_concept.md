Bitcoin 1-Hour Trend Detection System: Vetted Technical Indicators
Based on academic research and validated trading strategies, here is a comprehensive framework for detecting bullish and bearish trends on the 1-hour timeframe using your 6.3-year dataset.

Core Trend Identification Indicators
1. Exponential Moving Average (EMA) Crossover System
Primary trend direction filter

Fast EMA: 12-period

Slow EMA: 26-period

Trend EMA: 50-period

Macro EMA: 200-period

Bullish Criteria: Price > 50 EMA > 200 EMA AND 12 EMA > 26 EMA
Bearish Criteria: Price < 50 EMA < 200 EMA AND 12 EMA < 26 EMA
Validation: Research shows EMA crossovers on 1H BTC charts achieve 52% net profit with 70-80% win rates. The 12/26 EMA combination is particularly effective for crypto momentum detection.
​

2. MACD (Moving Average Convergence Divergence)
Momentum confirmation layer

Fast Length: 12

Slow Length: 26

Signal Smoothing: 9

Source: Close price

Bullish Criteria: MACD line > Signal line > 0 AND histogram increasing for 3+ consecutive periods
Bearish Criteria: MACD line < Signal line < 0 AND histogram decreasing for 3+ consecutive periods
Validation: Machine learning models using MACD achieve 86-92% accuracy for BTC trend prediction. The histogram's slope provides early trend strength signals.
​

3. Relative Strength Index (RSI)
Overbought/oversold with trend bias

Length: 14 periods (standard)

Overbought: 70

Oversold: 30

Trend Threshold: 55 (bullish bias), 45 (bearish bias)

Bullish Criteria: RSI > 55 and rising for 3+ periods
Bearish Criteria: RSI < 45 and falling for 3+ periods
Validation: RSI30 and RSI14 rank among the top 8 most important features in BTC price prediction models. The 55-45 zone provides better trend confirmation than traditional 70-30 levels.
​

4. Bollinger Bands
Volatility-adjusted trend channels

Length: 20 periods

Standard Deviations: 2

Source: Close price

Bullish Criteria: Price riding upper band with band expansion for 5+ periods
Bearish Criteria: Price riding lower band with band expansion for 5+ periods
Validation: Bollinger Bands are critical features in machine learning models with high feature importance scores. Band expansion confirms genuine trend strength versus mean-reversion.
​

Confirmation Indicators
5. Volume Profile
Trend validation through participation

Lookback: 20 periods

Threshold: 150% of 20-period average volume

Bullish Criteria: Volume > 1.5× average on green candles during uptrend
Bearish Criteria: Volume > 1.5× average on red candles during downtrend
Validation: Volume confirmation reduces false breakout probability by 40-60%. Genuine breakouts show sustained high volume participation.
​

6. Average Directional Index (ADX)
Trend strength quantification

Length: 14 periods

DI Length: 14

Bullish Criteria: ADX > 25 AND +DI > -DI
Bearish Criteria: ADX > 25 AND -DI > +DI
Neutral: ADX < 20 (avoid trading)
Validation: ADX > 25 confirms strong trends while filtering choppy markets. This prevents whipsaws in ranging conditions.
​

7. Stochastic Oscillator
Momentum fine-tuning

%K Length: 14

%K Smoothing: 3

%D Smoothing: 3

Bullish Criteria: %K > %D AND both > 50 in uptrend
Bearish Criteria: %K < %D AND both < 50 in downtrend
Validation: Stochastic parameters (%D30, %K200) appear in top 8 BTC prediction features. Values above/below 50 provide trend-direction bias.
​

Multi-Timeframe Confirmation
8. Higher Timeframe Alignment
Macro trend filter

4-Hour Confirmation: Check 4H EMA 50/200 alignment

Daily Confirmation: Verify daily trend direction

Bullish Criteria: 1H, 4H, and Daily all show bullish EMA alignment
Bearish Criteria: 1H, 4H, and Daily all show bearish EMA alignment
Validation: Multi-timeframe alignment increases win rate from 52% to 68% on 1H strategies. Daily chart validation provides macro context for 1H entries.
​

Implementation Script Structure
python
# Core Trend Detection Logic
def detect_trend(dataframe):
    """
    Returns: 1 (bullish), -1 (bearish), 0 (neutral)
    """
    # EMA Calculations
    dataframe['EMA_12'] = dataframe['close'].ewm(span=12).mean()
    dataframe['EMA_26'] = dataframe['close'].ewm(span=26).mean()
    dataframe['EMA_50'] = dataframe['close'].ewm(span=50).mean()
    dataframe['EMA_200'] = dataframe['close'].ewm(span=200).mean()
    
    # MACD
    macd_line = dataframe['EMA_12'] - dataframe['EMA_26']
    signal_line = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal_line
    
    # RSI
    delta = dataframe['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    dataframe['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    bb_middle = dataframe['close'].rolling(20).mean()
    bb_std = dataframe['close'].rolling(20).std()
    dataframe['BB_upper'] = bb_middle + (2 * bb_std)
    dataframe['BB_lower'] = bb_middle - (2 * bb_std)
    
    # ADX
    # [Implementation details for +DI, -DI, ADX calculation]
    
    # Trend Scoring
    score = 0
    
    # EMA Trend (40% weight)
    if dataframe['EMA_50'].iloc[-1] > dataframe['EMA_200'].iloc[-1]:
        score += 0.4
    
    # MACD Momentum (25% weight)
    if macd_line.iloc[-1] > signal_line.iloc[-1] > 0:
        score += 0.25
    
    # RSI Bias (15% weight)
    if dataframe['RSI'].iloc[-1] > 55:
        score += 0.15
    
    # Volume Confirmation (10% weight)
    avg_volume = dataframe['volume'].rolling(20).mean().iloc[-1]
    if dataframe['volume'].iloc[-1] > 1.5 * avg_volume:
        score += 0.1
    
    # ADX Strength (10% weight)
    # [ADX calculation and threshold check]
    
    # Final Classification
    if score >= 0.7:
        return 1  # Strong Bullish
    elif score >= 0.5:
        return 0.5  # Weak Bullish
    elif score <= -0.7:
        return -1  # Strong Bearish
    elif score <= -0.5:
        return -0.5  # Weak Bearish
    else:
        return 0  # Neutral
Backtesting Parameters
Performance Metrics to Track
Total Trades: Target 100-200 trades over 6.3 years (1H timeframe)

Win Rate: Minimum 55% for viable strategy
​

Profit Factor: > 1.5 (gross profit / gross loss)

Average Win/Average Loss: Target ratio > 2.0

Maximum Drawdown: < 25% of equity

Sharpe Ratio: > 1.0 for risk-adjusted returns

Parameter Optimization
In-Sample Period: First 4.5 years (training)

Out-of-Sample Period: Last 1.8 years (validation)

Walk-Forward Analysis: Re-optimize parameters quarterly to avoid overfitting
​

Risk Management Integration
Position Sizing
Risk Per Trade: 1-2% of capital

Stop Loss: Below/above recent swing low/high (minimum 1.5× ATR)

Take Profit: 2:1 risk-reward minimum or trailing stop using 12 EMA

Trend Invalidation Rules
Bullish Invalidation: Price closes below 50 EMA AND MACD crosses below signal line

Bearish Invalidation: Price closes above 50 EMA AND MACD crosses above signal line

Time Stop: Exit after 24-48 hours if trend doesn't progress