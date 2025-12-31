"""
200 EMA Trend Filter Building Block
Category: Moving Averages
Purpose: Long-term trend identification and filter using 200-period EMA
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class EMA200Trend:
    """
    200 EMA Trend Filter - Long-Term Trend Indicator
    
    The 200 EMA is the gold standard for identifying long-term market trends.
    Acts as major support/resistance and trend filter for all strategies.
    
    Signals:
    - Above 200 EMA: Bullish long-term trend (only take longs)
    - Below 200 EMA: Bearish long-term trend (only take shorts)
    - Price distance from 200 EMA: Overextension detection
    - 200 EMA slope: Trend strength
    
    Parameters:
        period: EMA period (default: 200)
        timeframe: Data timeframe
    """
    
    def __init__(self, period: int = 200, timeframe: str = '15min', **kwargs):
        """Initialize 200 EMA Trend Filter block"""
        self.period = period
        self.timeframe = timeframe
        
        # Bitcoin-specific distance thresholds (% from 200 EMA)
        self.btc_distance_thresholds = {
            'touching': 0.5,       # < 0.5% - at EMA
            'near': 2.0,           # 0.5-2% - near EMA
            'moderate': 5.0,       # 2-5% - moderate distance
            'extended':  10.0,     # 5-10% - extended
            'overextended': 10.0   # > 10% - very overextended
        }
    
    def calculate_ema(self, close: pd.Series) -> pd.Series:
        """Calculate 200 EMA"""
        return close.ewm(span=self.period, adjust=False).mean()
    
    def calculate_slope(self, ema: pd.Series, lookback: int = 20) -> str:
        """
        Calculate 200 EMA slope for trend strength
        
        Args:
            ema: EMA series
            lookback: Periods for slope calculation
        """
        if len(ema) < lookback:
            return 'INSUFFICIENT_DATA'
        
        recent = ema.iloc[-lookback:]
        x = np.arange(len(recent))
        y = recent.values
        
        slope = np.polyfit(x, y, 1)[0]
        avg_price = y.mean()
        slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0
        
        if slope_pct > 0.02:
            return 'STRONG_UPTREND'
        elif slope_pct > 0.005:
            return 'UPTREND'
        elif slope_pct < -0.02:
            return 'STRONG_DOWNTREND'
        elif slope_pct < -0.005:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'
    
    def classify_position(self, price: float, ema: float) -> str:
        """Classify price position relative to 200 EMA"""
        if price > ema:
            return 'ABOVE_200EMA'
        elif price < ema:
            return 'BELOW_200EMA'
        else:
            return 'AT_200EMA'
    
    def calculate_distance(self, price: float, ema: float) -> float:
        """Calculate percentage distance from 200 EMA"""
        return ((price - ema) / ema) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from 200 EMA"""
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['touching']:
            return 'TOUCHING'
        elif abs_dist < self.btc_distance_thresholds['near']:
            return 'NEAR'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        elif abs_dist < self.btc_distance_thresholds['extended']:
            return 'EXTENDED'
        else:
            return 'OVEREXTENDED'
    
    def determine_trend_filter(self, position: str, slope: str) -> str:
        """
        Determine trading bias based on 200 EMA
        
        Returns trade direction filter
        """
        if position == 'ABOVE_200EMA' and slope in ['UPTREND', 'STRONG_UPTREND']:
            return 'LONGS_ONLY'
        elif position == 'ABOVE_200EMA':
            return 'LONGS_PREFERRED'
        elif position == 'BELOW_200EMA' and slope in ['DOWNTREND', 'STRONG_DOWNTREND']:
            return 'SHORTS_ONLY'
        elif position == 'BELOW_200EMA':
            return 'SHORTS_PREFERRED'
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
        min_required = self.period + 20
        if len(df) < min_required:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need {min_required} periods, got {len(df)}'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate 200 EMA
        ema = self.calculate_ema(df['close'])
        
        current_price = float(df['close'].iloc[-1])
        current_ema = float(ema.iloc[-1])
        
        # Calculate slope
        slope = self.calculate_slope(ema, lookback=20)
        
        # Classify position
        position = self.classify_position(current_price, current_ema)
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, current_ema)
        distance_class = self.classify_distance(distance_pct)
        
        # Determine trend filter
        trend_filter = self.determine_trend_filter(position, slope)
        
        # Calculate confidence
        data_quality = min(100, (len(df) / min_required) * 100)
        confidence = data_quality * 0.7
        
        if slope in ['STRONG_UPTREND', 'STRONG_DOWNTREND']:
            confidence += 15
        if distance_class in ['TOUCHING', 'NEAR']:
            confidence += 10  # Near EMA = good entry
        
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        
        if position == 'ABOVE_200EMA':
            confluence_factors.append('Price above 200 EMA - long-term bullish')
        elif position == 'BELOW_200EMA':
            confluence_factors.append('Price below 200 EMA - long-term bearish')
        
        if slope == 'STRONG_UPTREND':
            confluence_factors.append('200 EMA strongly rising - powerful uptrend')
        elif slope == 'UPTREND':
            confluence_factors.append('200 EMA rising - uptrend intact')
        elif slope == 'STRONG_DOWNTREND':
            confluence_factors.append('200 EMA strongly falling - powerful downtrend')
        elif slope == 'DOWNTREND':
            confluence_factors.append('200 EMA falling - downtrend intact')
        elif slope == 'SIDEWAYS':
            confluence_factors.append('200 EMA flat - no clear trend')
        
        confluence_factors.append(f'Distance from 200 EMA: {distance_pct:+.2f}% ({distance_class})')
        confluence_factors.append(f'Trend Filter: {trend_filter}')
        
        # Determine signal
        if trend_filter in ['LONGS_ONLY', 'LONGS_PREFERRED']:
            signal = 'BULLISH'
        elif trend_filter in ['SHORTS_ONLY', 'SHORTS_PREFERRED']:
            signal = 'BEARISH'
        else:
            signal = 'NEUTRAL'
        
        # Metadata
        metadata = {
            'ema_200': round(current_ema, 2),
            'current_price': round(current_price, 2),
            'position': position,
            'slope': slope,
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'trend_filter': trend_filter,
            'period': self.period,
            'is_overextended': distance_class == 'OVEREXTENDED',
            'recent_ema': ema.tail(10).tolist()
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
    dates = pd.date_range(start='2024-01-01', periods=250, freq='15min')
    np.random.seed(42)
    base = 45000
    trend = np.linspace(0, 5000, 250)
    data = pd.DataFrame({
        'timestamp': dates,
        'close': base + trend + np.random.randn(250).cumsum() * 100,
        'open': base + trend,
        'high': base + trend + 200,
        'low': base + trend - 200,
        'volume': np.random.uniform(100, 1000, 250)
    })
    
    ema200 = EMA200Trend()
    result = ema200.analyze(data)
    
    print("=" * 80)
    print("200 EMA TREND FILTER - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\n200 EMA Analysis:")
    print(f"  200 EMA: ${result['metadata']['ema_200']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Position: {result['metadata']['position']}")
    print(f"  Slope: {result['metadata']['slope']}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"  Trend Filter: {result['metadata']['trend_filter']}")
    print(f"  Overextended: {result['metadata']['is_overextended']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
