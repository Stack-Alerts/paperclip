"""
ATR (Average True Range) Building Block
Category: Volatility Indicators
Purpose: Measures market volatility by calculating the average range of price movement
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class ATR:
    """
    Average True Range (ATR) - Volatility Indicator
    
    Measures market volatility by calculating the average range of price movement.
    Created by J. Welles Wilder Jr., ATR is essential for:
    - Stop-loss placement
    - Position sizing
    - Volatility assessment
    - Risk management
    
    Parameters:
        period: ATR calculation period (default: 14)
        timeframe: Timeframe string (e.g., '15min', '1hr', '4hr', '1D')
    
    Returns:
        Standardized dict with ATR value, volatility level, and stop-loss suggestions
    """
    
    def __init__(self, period: int = 14, timeframe: str = '15min', **kwargs):
        """
        Initialize ATR block with parameters
        
        Args:
            period: ATR calculation period (default: 14)
            timeframe: Timeframe for the data
        """
        self.period = period
        self.timeframe = timeframe
        
        # Bitcoin-specific volatility thresholds (in USD for BTC)
        # These can be tuned based on current market conditions
        self.btc_volatility_thresholds = {
            '1min': {'calm': 50, 'normal': 150, 'high': 300, 'extreme': 500},
            '5min': {'calm': 100, 'normal': 300, 'high': 600, 'extreme': 1000},
            '15min': {'calm': 200, 'normal': 500, 'high': 1000, 'extreme': 2000},
            '30min': {'calm': 300, 'normal': 700, 'high': 1500, 'extreme': 3000},
            '1hr': {'calm': 400, 'normal': 1000, 'high': 2000, 'extreme': 4000},
            '4hr': {'calm': 800, 'normal': 2000, 'high': 4000, 'extreme': 8000},
            '1D': {'calm': 1500, 'normal': 3000, 'high': 6000, 'extreme': 12000},
        }
    
    def calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range for each period
        
        True Range = Max of:
        1. High - Low
        2. |High - Previous Close|
        3. |Low - Previous Close|
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Series of True Range values
        """
        high_low = df['high'] - df['low']
        high_prev_close = abs(df['high'] - df['close'].shift(1))
        low_prev_close = abs(df['low'] - df['close'].shift(1))
        
        true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
        return true_range
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate ATR as moving average of True Range
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Series of ATR values
        """
        true_range = self.calculate_true_range(df)
        
        # Use Wilder's smoothing (exponential moving average)
        # Alpha = 1/period for Wilder's smoothing
        atr = true_range.ewm(alpha=1/self.period, adjust=False).mean()
        
        return atr
    
    def classify_volatility(self, atr_value: float) -> str:
        """
        Classify current volatility level based on ATR value
        
        Args:
            atr_value: Current ATR value
            
        Returns:
            Volatility classification string
        """
        thresholds = self.btc_volatility_thresholds.get(
            self.timeframe, 
            self.btc_volatility_thresholds['15min']
        )
        
        if atr_value < thresholds['calm']:
            return 'CALM'
        elif atr_value < thresholds['normal']:
            return 'NORMAL'
        elif atr_value < thresholds['high']:
            return 'HIGH'
        elif atr_value < thresholds['extreme']:
            return 'VERY_HIGH'
        else:
            return 'EXTREME'
    
    def calculate_stop_distance(self, atr_value: float, multiplier: float = 2.0) -> float:
        """
        Calculate suggested stop-loss distance based on ATR
        
        Standard practice: Stop = Entry ± (ATR × Multiplier)
        - Conservative: 1.5x ATR
        - Standard: 2.0x ATR
        - Aggressive: 2.5-3.0x ATR
        
        Args:
            atr_value: Current ATR value
            multiplier: ATR multiplier for stop distance (default: 2.0)
            
        Returns:
            Suggested stop-loss distance
        """
        return atr_value * multiplier
    
    def detect_atr_trend(self, atr_series: pd.Series, lookback: int = 5) -> str:
        """
        Detect if ATR is rising (volatility increasing) or falling (volatility decreasing)
        
        Args:
            atr_series: ATR values series
            lookback: Periods to look back for trend detection
            
        Returns:
            'RISING', 'FALLING', or 'STABLE'
        """
        if len(atr_series) < lookback:
            return 'INSUFFICIENT_DATA'
        
        recent_atr = atr_series.iloc[-lookback:].values
        
        # Calculate linear regression slope
        x = np.arange(lookback)
        slope = np.polyfit(x, recent_atr, 1)[0]
        
        # Classify based on slope
        avg_atr = recent_atr.mean()
        slope_threshold = avg_atr * 0.02  # 2% threshold (more sensitive than 5%)
        
        if slope > slope_threshold:
            return 'RISING'
        elif slope < -slope_threshold:
            return 'FALLING'
        else:
            return 'STABLE'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method for ATR building block
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            **kwargs: Additional parameters:
                - stop_multiplier: Multiplier for stop-loss calculation (default: 2.0)
                - lookback: Periods for trend detection (default: 5)
        
        Returns:
            {
                'signal': str,  # Volatility level classification
                'confidence': float,  # 0-100 confidence score
                'metadata': dict,  # ATR value, trend, stop suggestions
                'timestamp': datetime,
                'timeframe': str,
                'confluence_factors': list
            }
        """
        # Validate input data
        if not self.validate_data(df):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Invalid data format'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Need minimum periods for ATR calculation (need extra period for change detection)
        if len(df) < self.period + 2:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {
                    'error': f'Need at least {self.period + 2} periods, got {len(df)}',
                    'required_periods': self.period + 2,
                    'provided_periods': len(df)
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate ATR
        atr_series = self.calculate_atr(df)
        current_atr = float(atr_series.iloc[-1])
        previous_atr = float(atr_series.iloc[-2])
        
        # Get parameters
        stop_multiplier = kwargs.get('stop_multiplier', 2.0)
        lookback = kwargs.get('lookback', 5)
        
        # Classify volatility (current and previous)
        volatility_level = self.classify_volatility(current_atr)
        previous_volatility_level = self.classify_volatility(previous_atr)
        
        # Detect volatility level change
        volatility_changed = volatility_level != previous_volatility_level
        
        # Detect ATR trend
        atr_trend = self.detect_atr_trend(atr_series, lookback)
        
        # Calculate stop-loss suggestions
        stop_distance_conservative = self.calculate_stop_distance(current_atr, 1.5)
        stop_distance_standard = self.calculate_stop_distance(current_atr, 2.0)
        stop_distance_aggressive = self.calculate_stop_distance(current_atr, 2.5)
        stop_distance_custom = self.calculate_stop_distance(current_atr, stop_multiplier)
        
        # Calculate confidence based on data availability and ATR stability
        confidence = min(100, (len(df) / (self.period * 3)) * 100)  # Full confidence at 3x period
        
        # Adjust confidence based on ATR trend stability
        if atr_trend == 'STABLE':
            confidence = min(100, confidence * 1.1)  # Boost for stability
        elif atr_trend == 'INSUFFICIENT_DATA':
            confidence *= 0.8
        
        # Get current price for percentage calculations
        current_price = float(df['close'].iloc[-1])
        atr_percent = (current_atr / current_price) * 100
        
        # Build confluence factors
        confluence_factors = []
        
        if volatility_level == 'CALM':
            confluence_factors.append('Low volatility - tight stops possible')
        elif volatility_level in ['HIGH', 'VERY_HIGH', 'EXTREME']:
            confluence_factors.append('High volatility - wider stops required')
        
        if atr_trend == 'RISING':
            confluence_factors.append('Volatility increasing - breakout potential')
        elif atr_trend == 'FALLING':
            confluence_factors.append('Volatility decreasing - consolidation phase')
        
        # Prepare metadata
        metadata = {
            'atr_value': current_atr,
            'atr_percent': round(atr_percent, 2),
            'volatility_level': volatility_level,
            'atr_trend': atr_trend,
            'period': self.period,
            'current_price': current_price,
            'stop_suggestions': {
                'conservative': {
                    'distance': round(stop_distance_conservative, 2),
                    'multiplier': 1.5,
                    'long_stop': round(current_price - stop_distance_conservative, 2),
                    'short_stop': round(current_price + stop_distance_conservative, 2)
                },
                'standard': {
                    'distance': round(stop_distance_standard, 2),
                    'multiplier': 2.0,
                    'long_stop': round(current_price - stop_distance_standard, 2),
                    'short_stop': round(current_price + stop_distance_standard, 2)
                },
                'aggressive': {
                    'distance': round(stop_distance_aggressive, 2),
                    'multiplier': 2.5,
                    'long_stop': round(current_price - stop_distance_aggressive, 2),
                    'short_stop': round(current_price + stop_distance_aggressive, 2)
                },
                'custom': {
                    'distance': round(stop_distance_custom, 2),
                    'multiplier': stop_multiplier,
                    'long_stop': round(current_price - stop_distance_custom, 2),
                    'short_stop': round(current_price + stop_distance_custom, 2)
                }
            },
            'recent_atr_values': atr_series.tail(10).tolist(),
            'position_sizing_factor': round(1.0 / max(atr_percent / 100, 0.01), 2)  # Inverse of volatility
        }
        
        # Signal ONLY on volatility level changes, not continuously
        # This prevents signaling on every bar (reduces noise)
        if volatility_changed:
            signal = f'VOLATILITY_{volatility_level}'  # e.g., VOLATILITY_HIGH
        else:
            signal = 'NEUTRAL'  # No change in volatility level
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate input data has required columns
        
        Args:
            df: Input DataFrame
            
        Returns:
            True if valid, False otherwise
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required_cols)


# Usage example
if __name__ == "__main__":
    # Test with sample Bitcoin data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    
    # Create sample data with realistic Bitcoin prices
    np.random.seed(42)
    base_price = 45000
    data = {
        'timestamp': dates,
        'open': base_price + np.random.randn(100).cumsum() * 100,
        'high': base_price + np.random.randn(100).cumsum() * 100 + np.random.uniform(50, 200, 100),
        'low': base_price + np.random.randn(100).cumsum() * 100 - np.random.uniform(50, 200, 100),
        'close': base_price + np.random.randn(100).cumsum() * 100,
        'volume': np.random.uniform(100, 1000, 100)
    }
    
    df = pd.DataFrame(data)
    
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    # Test ATR block
    atr_block = ATR(period=14, timeframe='15min')
    result = atr_block.analyze(df)
    
    print("=" * 80)
    print("ATR BUILDING BLOCK - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"ATR Value: ${result['metadata']['atr_value']:.2f}")
    print(f"ATR %: {result['metadata']['atr_percent']:.2f}%")
    print(f"Volatility Level: {result['metadata']['volatility_level']}")
    print(f"ATR Trend: {result['metadata']['atr_trend']}")
    print(f"\nStop-Loss Suggestions (Standard 2.0x ATR):")
    print(f"  Long Stop: ${result['metadata']['stop_suggestions']['standard']['long_stop']:.2f}")
    print(f"  Short Stop: ${result['metadata']['stop_suggestions']['standard']['short_stop']:.2f}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
