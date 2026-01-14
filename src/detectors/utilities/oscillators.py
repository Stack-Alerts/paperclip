"""
Technical Oscillators for Divergence Analysis

Implements institutional-grade oscillators matching TradingView calculations:
- RSI (Relative Strength Index) - Primary oscillator
- CCI (Commodity Channel Index)
- CMO (Chande Momentum Oscillator)
- MFI (Money Flow Index) - requires volume
- ROC (Rate of Change)

These oscillators are used to detect divergence between price and momentum,
which is a critical signal for M-pattern reversal confirmation.

Reference: TradingView built-in indicators
Author: BTC_Engine_v3
Date: December 30, 2025
"""

from typing import Optional, Union
import pandas as pd
import numpy as np


def calculate_rsi(
    data: Union[pd.DataFrame, pd.Series], 
    length: int = 14,
    source: str = 'close'
) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index).
    
    The RSI is the most widely used oscillator for divergence detection.
    Ranges from 0-100, with 70+ overbought and 30- oversold

.
    
    Formula:
    --------
    1. Calculate price changes
    2. Separate gains and losses
    3. Calculate average gain/loss using Wilder's smoothing
    4. RS = avg_gain / avg_loss
    5. RSI = 100 - (100 / (1 + RS))
    
    Args:
        data: DataFrame with price data or Series of prices
        length: Lookback period (default: 14, TradingView standard)
        source: Column to use if DataFrame (default: 'close')
        
    Returns:
        pd.Series with RSI values
        
    Example:
    --------
    >>> df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
    >>> rsi = calculate_rsi(df, length=14)
    >>> print(f"Current RSI: {rsi.iloc[-1]:.2f}")
    >>> 
    >>> # Detect overbought
    >>> overbought = rsi > 70
    >>> print(f"Overbought bars: {overbought.sum()}")
    
    Reference:
    ----------
    TradingView: ta.rsi(close, 14)
    Wilder, J. Welles (1978). New Concepts in Technical Trading Systems
    """
    # Extract price series
    if isinstance(data, pd.DataFrame):
        if source not in data.columns:
            raise ValueError(f"Column '{source}' not found in DataFrame")
        prices = data[source]
    else:
        prices = data
    
    # Calculate price changes
    delta = prices.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # Calculate average gain/loss (Wilder's smoothing = EMA with alpha=1/length)
    # First value is simple average
    avg_gain = gain.ewm(com=length-1, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(com=length-1, min_periods=length, adjust=False).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Handle edge cases (div by zero)
    rsi = rsi.fillna(50.0)  # Neutral when no clear trend
    
    return rsi


def calculate_cci(
    data: pd.DataFrame,
    length: int = 20,
    constant: float = 0.015
) -> pd.Series:
    """
    Calculate CCI (Commodity Channel Index).
    
    CCI measures deviation from average price. Good for detecting overbought/oversold
    and divergences. Typically ranges -100 to +100, but can exceed.
    
    Formula:
    --------
    1. Typical Price = (High + Low + Close) / 3
    2. SMA = Simple Moving Average of Typical Price
    3. Mean Deviation = Average absolute deviation from SMA
    4. CCI = (Typical Price - SMA) / (constant * Mean Deviation)
    
    Args:
        data: DataFrame with 'high', 'low', 'close' columns
        length: Lookback period (default: 20, TradingView standard)
        constant: Scaling constant (default: 0.015, ensures ~70-80% values within ±100)
        
    Returns:
        pd.Series with CCI values
        
    Example:
    --------
    >>> df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
    >>> cci = calculate_cci(df, length=20)
    >>> print(f"Current CCI: {cci.iloc[-1]:.2f}")
    >>> 
    >>> # Detect extreme conditions
    >>> extreme_high = cci > 100
    >>> extreme_low = cci < -100
    
    Reference:
    ----------
    TradingView: ta.cci(close, 20)
    Lambert, Donald (1980). Commodities Channel Index
    """
    # Validate columns
    required = ['high', 'low', 'close']
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Calculate Typical Price
    tp = (data['high'] + data['low'] + data['close']) / 3.0
    
    # Calculate Simple Moving Average of TP
    sma_tp = tp.rolling(window=length, min_periods=length).mean()
    
    # Calculate Mean Deviation
    # Mean Deviation = Average of |TP - SMA|
    mad = (tp - sma_tp).abs().rolling(window=length, min_periods=length).mean()
    
    # Calculate CCI
    cci = (tp - sma_tp) / (constant * mad)
    
    # Handle edge cases
    cci = cci.fillna(0.0)
    
    return cci


def calculate_cmo(
    data: Union[pd.DataFrame, pd.Series],
    length: int = 14,
    source: str = 'close'
) -> pd.Series:
    """
    Calculate CMO (Chande Momentum Oscillator).
    
    CMO is similar to RSI but uses sum of gains/losses instead of averages.
    Ranges from -100 to +100. More sensitive to recent price changes than RSI.
    
    Formula:
    --------
    CMO = 100 * (Sum(Gains) - Sum(Losses)) / (Sum(Gains) + Sum(Losses))
    
    Args:
        data: DataFrame with price data or Series of prices
        length: Lookback period (default: 14)
        source: Column to use if DataFrame (default: 'close')
        
    Returns:
        pd.Series with CMO values (-100 to +100)
        
    Example:
    --------
    >>> df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
    >>> cmo = calculate_cmo(df, length=14)
    >>> print(f"Current CMO: {cmo.iloc[-1]:.2f}")
    >>> 
    >>> # Strong uptrend when CMO > 50
    >>> strong_uptrend = cmo > 50
    
    Reference:
    ----------
    TradingView: ta.cmo(close, 14)
    Chande, Tushar (1994). The New Technical Trader
    """
    # Extract price series
    if isinstance(data, pd.DataFrame):
        if source not in data.columns:
            raise ValueError(f"Column '{source}' not found in DataFrame")
        prices = data[source]
    else:
        prices = data
    
    # Calculate price changes
    delta = prices.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # Sum over length period
    sum_gain = gain.rolling(window=length, min_periods=length).sum()
    sum_loss = loss.rolling(window=length, min_periods=length).sum()
    
    # Calculate CMO
    cmo = 100.0 * (sum_gain - sum_loss) / (sum_gain + sum_loss)
    
    # Handle edge cases
    cmo = cmo.fillna(0.0)
    
    return cmo


def calculate_mfi(
    data: pd.DataFrame,
    length: int = 14
) -> pd.Series:
    """
    Calculate MFI (Money Flow Index).
    
    MFI is volume-weighted RSI. Incorporates both price and volume.
    Ranges from 0-100. Useful when volume data is available.
    
    Formula:
    --------
    1. Typical Price = (High + Low + Close) / 3
    2. Raw Money Flow = Typical Price * Volume
    3. Positive Flow = sum when TP increases
    4. Negative Flow = sum when TP decreases
    5. Money Flow Ratio = Positive Flow / Negative Flow
    6. MFI = 100 - (100 / (1 + Money Flow Ratio))
    
    Args:
        data: DataFrame with 'high', 'low', 'close', 'volume' columns
        length: Lookback period (default: 14)
        
    Returns:
        pd.Series with MFI values (0-100)
        
    Example:
    --------
    >>> df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
    >>> mfi = calculate_mfi(df, length=14)
    >>> print(f"Current MFI: {mfi.iloc[-1]:.2f}")
    >>> 
    >>> # Overbought/oversold with volume
    >>> overbought = mfi > 80
    >>> oversold = mfi < 20
    
    Reference:
    ----------
    TradingView: ta.mfi(close, 14)
    Quong, Gene and Avrum Soudack (1989)
    """
    # Validate columns
    required = ['high', 'low', 'close', 'volume']
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Calculate Typical Price
    tp = (data['high'] + data['low'] + data['close']) / 3.0
    
    # Calculate Raw Money Flow
    mf = tp * data['volume']
    
    # Determine direction (compare to previous TP)
    tp_change = tp.diff()
    
    # Positive and negative money flow
    positive_mf = mf.where(tp_change > 0, 0.0)
    negative_mf = mf.where(tp_change < 0, 0.0)
    
    # Sum over length period
    positive_flow = positive_mf.rolling(window=length, min_periods=length).sum()
    negative_flow = negative_mf.rolling(window=length, min_periods=length).sum()
    
    # Money Flow Ratio
    mfr = positive_flow / negative_flow
    
    # Calculate MFI
    mfi = 100.0 - (100.0 / (1.0 + mfr))
    
    # Handle edge cases
    mfi = mfi.fillna(50.0)
    
    return mfi


def calculate_roc(
    data: Union[pd.DataFrame, pd.Series],
    length: int = 14,
    source: str = 'close'
) -> pd.Series:
    """
    Calculate ROC (Rate of Change).
    
    ROC measures percentage change over N periods. Simple but effective
    for detecting momentum and divergences.
    
    Formula:
    --------
    ROC = ((Price - Price[n periods ago]) / Price[n periods ago]) * 100
    
    Args:
        data: DataFrame with price data or Series of prices
        length: Lookback period (default: 14)
        source: Column to use if DataFrame (default: 'close')
        
    Returns:
        pd.Series with ROC values (percentage)
        
    Example:
    --------
    >>> df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
    >>> roc = calculate_roc(df, length=14)
    >>> print(f"Current ROC: {roc.iloc[-1]:.2f}%")
    >>> 
    >>> # Strong momentum when ROC > 10%
    >>> strong_up = roc > 10
    
    Reference:
    ----------
    TradingView: ta.roc(close, 14)
    """
    # Extract price series
    if isinstance(data, pd.DataFrame):
        if source not in data.columns:
            raise ValueError(f"Column '{source}' not found in DataFrame")
        prices = data[source]
    else:
        prices = data
    
    # Calculate ROC
    roc = ((prices - prices.shift(length)) / prices.shift(length)) * 100.0
    
    # Handle edge cases
    roc = roc.fillna(0.0)
    
    return roc


def calculate_all_oscillators(
    data: pd.DataFrame,
    rsi_length: int = 14,
    cci_length: int = 20,
    cmo_length: int = 14,
    mfi_length: int = 14,
    roc_length: int = 14
) -> pd.DataFrame:
    """
    Calculate all oscillators at once.
    
    Convenience function that returns DataFrame with all oscillators.
    Useful for divergence analysis where you want to check multiple indicators.
    
    Args:
        data: DataFrame with OHLCV data
        rsi_length: RSI period (default: 14)
        cci_length: CCI period (default: 20)
        cmo_length: CMO period (default: 14)
        mfi_length: MFI period (default: 14, requires volume)
        roc_length: ROC period (default: 14)
        
    Returns:
        DataFrame with columns: ['rsi', 'cci', 'cmo', 'mfi', 'roc']
        
    Example:
    --------
    >>> df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
    >>> oscillators = calculate_all_oscillators(df)
    >>> print(oscillators.tail())
    >>> 
    >>> # Check if all oscillators show overbought
    >>> overbought_consensus = (
    ...     (oscillators['rsi'] > 70) & 
    ...     (oscillators['cci'] > 100) & 
    ...     (oscillators['mfi'] > 80)
    ... ).sum()
    """
    result = pd.DataFrame(index=data.index)
    
    # Calculate each oscillator
    result['rsi'] = calculate_rsi(data, length=rsi_length)
    result['cci'] = calculate_cci(data, length=cci_length)
    result['cmo'] = calculate_cmo(data, length=cmo_length)
    result['roc'] = calculate_roc(data, length=roc_length)
    
    # MFI only if volume available
    if 'volume' in data.columns:
        result['mfi'] = calculate_mfi(data, length=mfi_length)
    else:
        result['mfi'] = np.nan
    
    return result


# Helper function for quick testing
def quick_test(data_path: str = 'data/raw/BTC_USDT_PERP_30m.pkl', n_bars: int = 1000):
    """
    Quick test of all oscillators.
    
    Args:
        data_path: Path to data file
        n_bars: Number of bars to test
    """
    import pickle
    
    print("="*60)
    print("OSCILLATORS TEST")
    print("="*60)
    
    # Load data
    with open(data_path, 'rb') as f:
        df = pickle.load(f)
    
    df = df[df.index >= '2024-01-01'].iloc[:n_bars]
    print(f"\nData: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Calculate all oscillators
    print(f"\n{'='*60}")
    print("Calculating all oscillators...")
    print(f"{'='*60}")
    
    oscillators = calculate_all_oscillators(df)
    
    print(f"\nLast 5 values:")
    print(oscillators.tail().to_string())
    
    print(f"\n{'='*60}")
    print("Statistics:")
    print(f"{'='*60}")
    print(oscillators.describe().to_string())
    
    # Check extremes
    print(f"\n{'='*60}")
    print("Extreme Conditions:")
    print(f"{'='*60}")
    
    rsi_overbought = (oscillators['rsi'] > 70).sum()
    rsi_oversold = (oscillators['rsi'] < 30).sum()
    print(f"RSI Overbought (>70): {rsi_overbought} bars ({rsi_overbought/len(df)*100:.1f}%)")
    print(f"RSI Oversold (<30): {rsi_oversold} bars ({rsi_oversold/len(df)*100:.1f}%)")
    
    cci_extreme_high = (oscillators['cci'] > 100).sum()
    cci_extreme_low = (oscillators['cci'] < -100).sum()
    print(f"CCI Extreme High (>100): {cci_extreme_high} bars ({cci_extreme_high/len(df)*100:.1f}%)")
    print(f"CCI Extreme Low (<-100): {cci_extreme_low} bars ({cci_extreme_low/len(df)*100:.1f}%)")
    
    cmo_strong_up = (oscillators['cmo'] > 50).sum()
    cmo_strong_down = (oscillators['cmo'] < -50).sum()
    print(f"CMO Strong Up (>50): {cmo_strong_up} bars ({cmo_strong_up/len(df)*100:.1f}%)")
    print(f"CMO Strong Down (<-50): {cmo_strong_down} bars ({cmo_strong_down/len(df)*100:.1f}%)")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    # Run quick test
    quick_test()
