"""
HOW (High of Week) Building Block
Category: Price Levels
Purpose: Weekly high price level for major resistance and breakout detection
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class HOW:
    """
    HOW - High of Week Price Level
    
    Tracks the highest price reached during the current trading week.
    Critical level for:
    - Major resistance identification
    - Weekly breakout detection
    - Swing trading setups
    - Higher timeframe analysis
    
    Parameters:
        timeframe: Data timeframe
        week_start: Day week starts (0=Monday, default: 0)
    """
    
    def __init__(self, timeframe: str = '15min', week_start: int = 0, **kwargs):
        """Initialize HOW block"""
        self.timeframe = timeframe
        self.week_start = week_start
        
        # Bitcoin-specific distance thresholds (% from HOW)
        self.btc_distance_thresholds = {
            'at_how': 0.2,          # < 0.2% - at HOW
            'very_close': 1.0,      # 0.2-1% - very close
            'close': 2.5,           # 1-2.5% - close
            'moderate': 5.0,        # 2.5-5% - moderate
            'far': 5.0              # > 5% - far from HOW
        }
    
    def calculate_how(self, df: pd.DataFrame) -> float:
        """Calculate High of Week from intraday data"""
        if 'timestamp' not in df.columns or 'high' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_week = current_time.isocalendar()[1]
        current_year = current_time.isocalendar()[0]
        
        week_data = df[
            (df['timestamp'].dt.isocalendar().week == current_week) &
            (df['timestamp'].dt.isocalendar().year == current_year)
        ]
        
        if len(week_data) == 0:
            return None
        
        return float(week_data['high'].max())
    
    def detect_breakout(self, current_price: float, how: float, threshold_pct: float = 0.1) -> str:
        """Detect HOW breakout"""
        if how is None:
            return 'NO_HOW'
        
        distance_pct = ((current_price - how) / how) * 100
        
        if distance_pct > threshold_pct:
            return 'BREAKOUT_CONFIRMED'
        elif distance_pct > 0:
            return 'BREAKING_OUT'
        else:
            return 'BELOW_HOW'
    
    def calculate_distance(self, price: float, how: float) -> float:
        """Calculate percentage distance from HOW"""
        if how is None:
            return None
        return ((price - how) / how) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from HOW"""
        if distance_pct is None:
            return 'NO_HOW'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_how']:
            return 'AT_HOW'
        elif abs_dist < self.btc_distance_thresholds['very_close']:
            return 'VERY_CLOSE'
        elif abs_dist < self.btc_distance_thresholds['close']:
            return 'CLOSE'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        else:
            return 'FAR'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        # Validate
        if not all(col in df.columns for col in ['timestamp', 'high', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No data provided'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate HOW
        how = self.calculate_how(df)
        
        if how is None:
            return {
                'signal': 'NO_HOW_DATA',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate HOW'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        
        # Detect breakout
        breakout = self.detect_breakout(current_price, how)
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, how)
        distance_class = self.classify_distance(distance_pct)
        
        # Calculate confidence
        confidence = 75  # Higher base for weekly levels
        
        if breakout == 'BREAKOUT_CONFIRMED':
            confidence += 20
        elif distance_class in ['AT_HOW', 'VERY_CLOSE']:
            confidence += 15
        
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        
        if breakout == 'BREAKOUT_CONFIRMED':
            confluence_factors.append('HOW breakout confirmed - strong bullish signal')
        elif breakout == 'BREAKING_OUT':
            confluence_factors.append('Price breaking above HOW - major resistance test')
        elif distance_class in ['AT_HOW', 'VERY_CLOSE']:
            confluence_factors.append('Price at/near HOW - critical resistance level')
        
        confluence_factors.append(f'HOW: ${how:.2f}')
        confluence_factors.append(f'Distance from HOW: {distance_pct:+.2f}% ({distance_class})')
        
        # Determine signal
        if breakout == 'BREAKOUT_CONFIRMED':
            signal = 'BULLISH'
        elif breakout == 'BREAKING_OUT':
            signal = 'NEUTRAL'
        elif distance_class in ['AT_HOW', 'VERY_CLOSE'] and distance_pct < 0:
            signal = 'BEARISH'  # Rejection at HOW
        else:
            signal = 'NEUTRAL'
        
        # Metadata
        metadata = {
            'how': round(how, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'breakout_status': breakout,
            'is_major_resistance': distance_class in ['AT_HOW', 'VERY_CLOSE'] and distance_pct < 0,
            'is_breaking_out': breakout in ['BREAKING_OUT', 'BREAKOUT_CONFIRMED']
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
    np.random.seed(42)
    base = 45000
    highs = base + np.random.uniform(-500, 1000, 200)
    closes = highs - np.random.uniform(0, 200, 200)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'close': closes,
        'open': closes - 50,
        'low': closes - 100,
        'volume': np.random.uniform(100, 1000, 200)
    })
    
    how_block = HOW()
    result = how_block.analyze(data)
    
    print("=" * 80)
    print("HOW (HIGH OF WEEK) - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nHOW Analysis:")
    print(f"  HOW: ${result['metadata']['how']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"  Breakout Status: {result['metadata']['breakout_status']}")
    print(f"  Major Resistance: {result['metadata']['is_major_resistance']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
