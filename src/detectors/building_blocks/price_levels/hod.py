"""
HOD (High of Day) Building Block
Category: Price Levels
Purpose: Daily high price level for support/resistance and breakout detection
"""

from typing import Dict, Any
from datetime import datetime, time
import pandas as pd
import numpy as np


class HOD:
    """
    HOD - High of Day Price Level
    
    Tracks the highest price reached during the current trading day.
    Critical level for:
    - Resistance identification
    - Breakout detection
    - Range trading
    - Day trading setups
    
    Parameters:
        timeframe: Data timeframe
        day_start_hour: Hour when day starts (default: 0 UTC)
    
    Returns:
        Standardized dict with HOD level, distance, and breakout signals
    """
    
    def __init__(self, timeframe: str = '15min', day_start_hour: int = 0, **kwargs):
        """Initialize HOD block"""
        self.timeframe = timeframe
        self.day_start_hour = day_start_hour
        
        # Bitcoin-specific distance thresholds (% from HOD)
        self.btc_distance_thresholds = {
            'at_hod': 0.1,          # < 0.1% - at HOD
            'very_close': 0.5,      # 0.1-0.5% - very close
            'close': 1.0,           # 0.5-1% - close
            'moderate': 2.0,        # 1-2% - moderate distance
            'far': 2.0              # > 2% - far from HOD
        }
    
    def calculate_hod(self, df: pd.DataFrame) -> float:
        """
        Calculate High of Day from intraday data
        
        Args:
            df: DataFrame with timestamp and high columns
            
        Returns:
            HOD value
        """
        if 'timestamp' not in df.columns or 'high' not in df.columns:
            return None
        
        # Get current date
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Filter for today's data
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None
        
        # Return highest high of the day
        return float(today_data['high'].max())
    
    def detect_breakout(self, current_price: float, hod: float, threshold_pct: float = 0.05) -> str:
        """
        Detect HOD breakout
        
        Args:
            current_price: Current price
            hod: High of Day
            threshold_pct: Threshold for breakout confirmation (default: 0.05%)
        """
        if hod is None:
            return 'NO_HOD'
        
        distance_pct = ((current_price - hod) / hod) * 100
        
        if distance_pct > threshold_pct:
            return 'BREAKOUT_CONFIRMED'
        elif distance_pct > 0:
            return 'BREAKING_OUT'
        else:
            return 'BELOW_HOD'
    
    def calculate_distance(self, price: float, hod: float) -> float:
        """Calculate percentage distance from HOD"""
        if hod is None:
            return None
        return ((price - hod) / hod) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from HOD"""
        if distance_pct is None:
            return 'NO_HOD'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_hod']:
            return 'AT_HOD'
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
        
        # Check minimum data
        if len(df) < 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No data provided'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate HOD
        hod = self.calculate_hod(df)
        
        if hod is None:
            return {
                'signal': 'NO_HOD_DATA',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate HOD'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        
        # Detect breakout
        breakout = self.detect_breakout(current_price, hod)
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, hod)
        distance_class = self.classify_distance(distance_pct)
        
        # Calculate confidence
        confidence = 70  # Base confidence
        
        if breakout == 'BREAKOUT_CONFIRMED':
            confidence += 25
        elif distance_class in ['AT_HOD', 'VERY_CLOSE']:
            confidence += 15
        
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        
        if breakout == 'BREAKOUT_CONFIRMED':
            confluence_factors.append('HOD breakout confirmed - bullish signal')
        elif breakout == 'BREAKING_OUT':
            confluence_factors.append('Price breaking above HOD - watch for confirmation')
        elif distance_class in ['AT_HOD', 'VERY_CLOSE']:
            confluence_factors.append('Price at/near HOD - potential resistance test')
        
        confluence_factors.append(f'HOD: ${hod:.2f}')
        confluence_factors.append(f'Distance from HOD: {distance_pct:+.2f}% ({distance_class})')
        
        # Determine signal
        if breakout == 'BREAKOUT_CONFIRMED':
            signal = 'BULLISH'
        elif breakout == 'BREAKING_OUT':
            signal = 'NEUTRAL'
        elif distance_class in ['AT_HOD', 'VERY_CLOSE'] and distance_pct < 0:
            signal = 'BEARISH'  # Rejection at HOD
        else:
            signal = 'NEUTRAL'
        
        # Metadata
        metadata = {
            'hod': round(hod, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'breakout_status': breakout,
            'is_at_resistance': distance_class in ['AT_HOD', 'VERY_CLOSE'] and distance_pct < 0,
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
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    base = 45000
    highs = base + np.random.uniform(-200, 500, 50)
    closes = highs - np.random.uniform(0, 100, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'close': closes,
        'open': closes - 50,
        'low': closes - 100,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    hod_block = HOD()
    result = hod_block.analyze(data)
    
    print("=" * 80)
    print("HOD (HIGH OF DAY) - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nHOD Analysis:")
    print(f"  HOD: ${result['metadata']['hod']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"  Breakout Status: {result['metadata']['breakout_status']}")
    print(f"  At Resistance: {result['metadata']['is_at_resistance']}")
    print(f"  Breaking Out: {result['metadata']['is_breaking_out']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
