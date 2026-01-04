"""
ATR (Average True Range) Building Block
Category: Volatility Indicators
Purpose: Measures market volatility by calculating the average range of price movement
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous Average True Range reference

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class ATR:
    """
    Average True Range (ATR) - Volatility Indicator (ENHANCED 2026-01-04)
    
    Measures market volatility by calculating the average range of price movement.
    Created by J. Welles Wilder Jr., ATR is essential for:
    - Stop-loss placement
    - Position sizing
    - Volatility assessment
    - Risk management
    
    Parameters:
        period: ATR calculation period (default: 14)
        timeframe: Timeframe string (e.g., '15min', '1hr', '4hr', '1D')
    
    ENHANCEMENTS (2026-01-04):
    - Variable Confidence: Differentiate extreme volatility states
    - Volatility Percentile: Historical context for ATR levels
    
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
        
        # ENHANCEMENT: Track historical ATR values for percentile calculation
        self.atr_history = []
        self.max_history = 500  # Keep last 500 ATR values
        
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
    
    def calculate_atr_percentile(self, current_atr: float) -> Dict[str, Any]:
        """
        ENHANCEMENT 2: Volatility Percentile (2026-01-04)
        Calculate where current ATR sits in historical distribution
        """
        if len(self.atr_history) < 20:
            return {
                'has_percentile': False,
                'percentile': None,
                'relative_level': None
            }
        
        # Calculate percentile rank
        percentile = (sum(1 for atr in self.atr_history if atr < current_atr) / len(self.atr_history)) * 100
        
        # Classify relative level
        if percentile >= 95:
            relative_level = 'EXTREME_HIGH'
        elif percentile >= 85:
            relative_level = 'VERY_HIGH'
        elif percentile >= 70:
            relative_level = 'HIGH'
        elif percentile >= 30:
            relative_level = 'NORMAL'
        elif percentile >= 15:
            relative_level = 'LOW'
        elif percentile >= 5:
            relative_level = 'VERY_LOW'
        else:
            relative_level = 'EXTREME_LOW'
        
        return {
            'has_percentile': True,
            'percentile': round(percentile, 1),
            'relative_level': relative_level,
            'history_size': len(self.atr_history)
        }
    
    def calculate_variable_confidence(self, signal: str, volatility_level: str, 
                                     atr_percentile_data: Dict[str, Any]) -> float:
        """
        ENHANCEMENT 1: Variable Confidence (2026-01-04)
        Calculate confidence based on volatility state and extremes
        """
        # Base confidence by signal type
        if signal == 'EXPANDING':
            if volatility_level in ['EXTREME', 'VERY_HIGH']:
                base_confidence = 100  # Extreme expansion = highest confidence
            elif volatility_level == 'HIGH':
                base_confidence = 90
            else:
                base_confidence = 85  # Moderate expansion
        elif signal == 'CONTRACTING':
            if volatility_level == 'CALM':
                base_confidence = 95  # Extreme contraction = very high confidence
            elif volatility_level == 'NORMAL':
                base_confidence = 85
            else:
                base_confidence = 80  # Moderate contraction
        elif signal == 'STABLE':
            base_confidence = 70  # Stable = moderate confidence
        else:
            base_confidence = 60  # Neutral/unknown
        
        # Adjust based on percentile (if available)
        if atr_percentile_data.get('has_percentile'):
            percentile = atr_percentile_data['percentile']
            relative_level = atr_percentile_data['relative_level']
            
            # Boost confidence for extreme percentiles
            if relative_level in ['EXTREME_HIGH', 'EXTREME_LOW']:
                base_confidence = min(100, base_confidence + 10)
            elif relative_level in ['VERY_HIGH', 'VERY_LOW']:
                base_confidence = min(100, base_confidence + 5)
        
        return base_confidence
    
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
        Main analysis method for ATR - tracks CONTINUOUS volatility regime and REGIME CHANGES
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            **kwargs: Additional parameters:
                - stop_multiplier: Multiplier for stop-loss calculation (default: 2.0)
                - lookback: Periods for trend detection (default: 5)
        
        Returns:
            {
                'signal': str,  # Volatility regime (EXPANDING/STABLE/CONTRACTING)
                'confidence': float,  # 0-100 confidence score
                'metadata': dict,  # ATR value, trend, stop suggestions, is_new_event
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
                'metadata': {'error': 'Invalid data format', 'is_new_event': False},
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
        
        # ENHANCEMENT 2: Update ATR history for percentile tracking
        self.atr_history.append(current_atr)
        if len(self.atr_history) > self.max_history:
            self.atr_history.pop(0)
        
        # Calculate percentile
        atr_percentile_data = self.calculate_atr_percentile(current_atr)
        
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
        
        # **NEW:** Event tracking - detect volatility REGIME changes
        is_new_event = False
        bars_in_regime = 0
        
        # Check if regime changed
        if len(df) > self.period + lookback:
            # Get previous regime
            prev_atr_trend = self.detect_atr_trend(atr_series[:-1], lookback)
            
            # Detect regime change
            is_new_event = (atr_trend != prev_atr_trend) and (prev_atr_trend != 'INSUFFICIENT_DATA')
            
            # If not changed, approximate bars in regime
            if not is_new_event:
                bars_in_regime = 1  # At least 1 bar in current regime
        
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
        
        # **DEFINE SIGNAL FIRST** - based on ATR trend (EXPANDING/CONTRACTING)
        # Primary use case: Detect volatility expansion (breakouts) or contraction (consolidation)
        if atr_trend == 'RISING':
            signal = 'EXPANDING'  # Volatility increasing - breakout potential
        elif atr_trend == 'FALLING':
            signal = 'CONTRACTING'  # Volatility decreasing - consolidation
        elif atr_trend == 'STABLE':
            signal = 'STABLE'  # Volatility stable - range-bound
        else:
            signal = 'NEUTRAL'  # Insufficient data
        
        # ENHANCEMENT 1: Calculate variable confidence
        confidence = self.calculate_variable_confidence(signal, volatility_level, atr_percentile_data)
        
        # Fresh regime change boost
        if is_new_event:
            confidence = min(100, confidence + 5)
        
        # Build confluence factors
        confluence_factors = []
        
        # Event-specific confluence (regime changes)
        if is_new_event:
            if signal == 'EXPANDING':
                confluence_factors.append('⭐ NEW VOLATILITY EXPANSION (breakout starting!)')
            elif signal == 'CONTRACTING':
                confluence_factors.append('⭐ NEW VOLATILITY CONTRACTION (consolidation starting!)')
            elif signal == 'STABLE':
                confluence_factors.append('⭐ VOLATILITY STABILIZED (range trading!)')
        elif bars_in_regime > 0:
            confluence_factors.append(f'Continuing {signal.lower()} regime ({bars_in_regime} bars)')
        
        if volatility_level == 'CALM':
            confluence_factors.append('Low volatility - tight stops possible')
        elif volatility_level in ['HIGH', 'VERY_HIGH', 'EXTREME']:
            confluence_factors.append('High volatility - wider stops required')
        
        if atr_trend == 'RISING':
            confluence_factors.append('Volatility increasing - breakout potential')
        elif atr_trend == 'FALLING':
            confluence_factors.append('Volatility decreasing - consolidation phase')
        
        # ENHANCEMENT 2: Add percentile context to confluence
        if atr_percentile_data.get('has_percentile'):
            percentile = atr_percentile_data['percentile']
            relative_level = atr_percentile_data['relative_level']
            
            if relative_level in ['EXTREME_HIGH', 'VERY_HIGH']:
                confluence_factors.append(f'⚠️ ATR at {percentile:.0f}th percentile - EXTREME volatility (+10 confidence)')
            elif relative_level == 'HIGH':
                confluence_factors.append(f'ATR at {percentile:.0f}th percentile - HIGH volatility')
            elif relative_level in ['EXTREME_LOW', 'VERY_LOW']:
                confluence_factors.append(f'ATR at {percentile:.0f}th percentile - VERY LOW volatility')
        
        # Prepare metadata (ENHANCED)
        metadata = {
            'atr_value': current_atr,
            'atr_percent': round(atr_percent, 2),
            'volatility_level': volatility_level,
            'atr_trend': atr_trend,
            'period': self.period,
            'current_price': current_price,
            'is_new_event': is_new_event,
            'bars_in_regime': bars_in_regime,
            # ENHANCEMENTS
            'has_percentile': atr_percentile_data.get('has_percentile', False),
            'atr_percentile': atr_percentile_data.get('percentile'),
            'relative_volatility_level': atr_percentile_data.get('relative_level'),
            'history_size': atr_percentile_data.get('history_size', len(self.atr_history)),
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
