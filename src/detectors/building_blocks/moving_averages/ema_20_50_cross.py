"""
20/50 EMA Cross Building Block
Category: Moving Averages
Purpose: Medium-term trend identification using 20 and 50 EMA crossovers
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class EMA2050Cross:
    """
    20/50 EMA Cross - Medium-Term Trend Indicator
    
    Classic moving average crossover system:
    - Golden Cross: 20 EMA crosses above 50 EMA (bullish)
    - Death Cross: 20 EMA crosses below 50 EMA (bearish)
    - EMA separation: Distance between EMAs shows trend strength
    
    Parameters:
        fast_period: Fast EMA period (default: 20)
        slow_period: Slow EMA period (default: 50)
        timeframe: Data timeframe
    
    Returns:
        Standardized dict with cross signals, separation, and trend strength
    """
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50, timeframe: str = '15min', **kwargs):
        """Initialize 20/50 EMA Cross block"""
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.timeframe = timeframe
        
        # Bitcoin-specific separation thresholds (% between EMAs)
        self.btc_separation_levels = {
            'tight': 0.3,      # < 0.3% - very close
            'normal': 1.0,     # 0.3-1% - normal separation
            'wide': 2.0,       # 1-2% - wide separation
            'very_wide': 2.0   # > 2% - very wide (strong trend)
        }
    
    def calculate_ema(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return close.ewm(span=period, adjust=False).mean()
    
    def detect_cross(self, fast_ema: pd.Series, slow_ema: pd.Series, lookback: int = 3) -> str:
        """
        Detect EMA crossovers
        
        Args:
            fast_ema: Fast EMA series
            slow_ema: Slow EMA series
            lookback: Periods to confirm cross
            
        Returns:
            'GOLDEN_CROSS', 'DEATH_CROSS', or 'NO_CROSS'
        """
        if len(fast_ema) < lookback + 1:
            return 'INSUFFICIENT_DATA'
        
        # Current position
        current_above = fast_ema.iloc[-1] > slow_ema.iloc[-1]
        
        # Previous position
        previous_above = fast_ema.iloc[-(lookback+1)] > slow_ema.iloc[-(lookback+1)]
        
        # Check if crossed
        if current_above == previous_above:
            return 'NO_CROSS'
        
        # Verify cross is sustained
        recent_fast = fast_ema.iloc[-lookback:]
        recent_slow = slow_ema.iloc[-lookback:]
        
        if current_above:
            # Golden cross: fast crossed above slow
            stays_above = sum(recent_fast > recent_slow) >= lookback - 1
            if stays_above:
                return 'GOLDEN_CROSS'
        else:
            # Death cross: fast crossed below slow
            stays_below = sum(recent_fast < recent_slow) >= lookback - 1
            if stays_below:
                return 'DEATH_CROSS'
        
        return 'NO_CROSS'
    
    def calculate_separation(self, fast_ema: float, slow_ema: float) -> float:
        """Calculate percentage separation between EMAs"""
        return ((fast_ema - slow_ema) / slow_ema) * 100
    
    def classify_separation(self, separation_pct: float) -> str:
        """Classify separation level"""
        abs_sep = abs(separation_pct)
        
        if abs_sep < self.btc_separation_levels['tight']:
            return 'TIGHT'
        elif abs_sep < self.btc_separation_levels['normal']:
            return 'NORMAL'
        elif abs_sep < self.btc_separation_levels['wide']:
            return 'WIDE'
        else:
            return 'VERY_WIDE'
    
    def determine_trend(self, fast_ema: float, slow_ema: float, price: float) -> str:
        """
        Determine overall trend based on EMA alignment
        
        Args:
            fast_ema: Fast EMA value
            slow_ema: Slow EMA value
            price: Current price
            
        Returns:
            Trend classification
        """
        if price > fast_ema > slow_ema:
            return 'STRONG_UPTREND'
        elif price > fast_ema and fast_ema < slow_ema:
            return 'EARLY_UPTREND'
        elif price < fast_ema < slow_ema:
            return 'STRONG_DOWNTREND'
        elif price < fast_ema and fast_ema > slow_ema:
            return 'EARLY_DOWNTREND'
        else:
            return 'NEUTRAL'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        # Validate
        if 'close' not in df.columns:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Invalid data format'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check minimum data
        min_required = self.slow_period + 3
        if len(df) < min_required:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need {min_required} periods, got {len(df)}'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate EMAs
        fast_ema = self.calculate_ema(df['close'], self.fast_period)
        slow_ema = self.calculate_ema(df['close'], self.slow_period)
        
        current_price = float(df['close'].iloc[-1])
        current_fast = float(fast_ema.iloc[-1])
        current_slow = float(slow_ema.iloc[-1])
        
        # Detect cross
        cross = self.detect_cross(fast_ema, slow_ema, lookback=3)
        
        # Calculate separation
        separation_pct = self.calculate_separation(current_fast, current_slow)
        separation_class = self.classify_separation(separation_pct)
        
        # Determine trend
        trend = self.determine_trend(current_fast, current_slow, current_price)
        
        # Calculate confidence
        data_quality = min(100, (len(df) / min_required) * 100)
        confidence = data_quality * 0.7
        
        if cross in ['GOLDEN_CROSS', 'DEATH_CROSS']:
            confidence += 25  # Strong signal
        if separation_class in ['WIDE', 'VERY_WIDE']:
            confidence += 10  # Strong trend
        
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        
        if cross == 'GOLDEN_CROSS':
            confluence_factors.append('Golden Cross - 20 EMA crossed above 50 EMA (bullish signal)')
        elif cross == 'DEATH_CROSS':
            confluence_factors.append('Death Cross - 20 EMA crossed below 50 EMA (bearish signal)')
        
        if trend == 'STRONG_UPTREND':
            confluence_factors.append('Strong uptrend - price > 20 EMA > 50 EMA (perfect alignment)')
        elif trend == 'STRONG_DOWNTREND':
            confluence_factors.append('Strong downtrend - price < 20 EMA < 50 EMA (perfect alignment)')
        elif trend == 'EARLY_UPTREND':
            confluence_factors.append('Early uptrend - price above 20 EMA, awaiting 50 EMA cross')
        elif trend == 'EARLY_DOWNTREND':
            confluence_factors.append('Early downtrend - price below 20 EMA, awaiting 50 EMA cross')
        
        confluence_factors.append(f'EMA separation: {separation_pct:+.2f}% ({separation_class})')
        
        # Determine signal
        if cross == 'GOLDEN_CROSS' or trend in ['STRONG_UPTREND', 'EARLY_UPTREND']:
            signal = 'BULLISH'
        elif cross == 'DEATH_CROSS' or trend in ['STRONG_DOWNTREND', 'EARLY_DOWNTREND']:
            signal = 'BEARISH'
        else:
            signal = 'NEUTRAL'
        
        # Metadata
        metadata = {
            'fast_ema': round(current_fast, 2),
            'slow_ema': round(current_slow, 2),
            'current_price': round(current_price, 2),
            'cross': cross,
            'separation_pct': round(separation_pct, 2),
            'separation_class': separation_class,
            'trend': trend,
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'recent_fast_ema': fast_ema.tail(10).tolist(),
            'recent_slow_ema': slow_ema.tail(10).tolist()
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base = 45000
    trend = np.linspace(0, 2000, 100)
    data = pd.DataFrame({
        'timestamp': dates,
        'close': base + trend + np.random.randn(100).cumsum() * 50,
        'open': base + trend,
        'high': base + trend + 100,
        'low': base + trend - 100,
        'volume': np.random.uniform(100, 1000, 100)
    })
    
    cross = EMA2050Cross()
    result = cross.analyze(data)
    
    print("=" * 80)
    print("20/50 EMA CROSS - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nEMA Analysis:")
    print(f"  20 EMA: ${result['metadata']['fast_ema']:.2f}")
    print(f"  50 EMA: ${result['metadata']['slow_ema']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Cross: {result['metadata']['cross']}")
    print(f"  Separation: {result['metadata']['separation_pct']:+.2f}% ({result['metadata']['separation_class']})")
    print(f"  Trend: {result['metadata']['trend']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
