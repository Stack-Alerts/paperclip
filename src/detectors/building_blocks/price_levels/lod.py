"""
LOD (Low of Day) Building Block
Category: Price Levels
Purpose: Daily low price level for support/resistance and breakdown detection
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class LOD:
    """
    LOD - Low of Day Price Level
    
    Tracks the lowest price reached during the current trading day.
    Critical level for:
    - Support identification
    - Breakdown detection
    - Range trading
    - Day trading setups
    
    Parameters:
        timeframe: Data timeframe
        day_start_hour: Hour when day starts (default: 0 UTC)
    
    Returns:
        Standardized dict with LOD level, distance, and breakdown signals
    """
    
    def __init__(self, timeframe: str = '15min', day_start_hour: int = 0, **kwargs):
        """Initialize LOD block"""
        self.timeframe = timeframe
        self.day_start_hour = day_start_hour
        
        # Bitcoin-specific distance thresholds (% from LOD)
        self.btc_distance_thresholds = {
            'at_lod': 0.1,          # < 0.1% - at LOD
            'very_close': 0.5,      # 0.1-0.5% - very close
            'close': 1.0,           # 0.5-1% - close
            'moderate': 2.0,        # 1-2% - moderate distance
            'far': 2.0              # > 2% - far from LOD
        }
    
    def calculate_lod(self, df: pd.DataFrame) -> float:
        """Calculate Low of Day from intraday data"""
        if 'timestamp' not in df.columns or 'low' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None
        
        return float(today_data['low'].min())
    
    def detect_breakdown(self, current_price: float, lod: float, threshold_pct: float = 0.05) -> str:
        """Detect LOD breakdown"""
        if lod is None:
            return 'NO_LOD'
        
        distance_pct = ((current_price - lod) / lod) * 100
        
        if distance_pct < -threshold_pct:
            return 'BREAKDOWN_CONFIRMED'
        elif distance_pct < 0:
            return 'BREAKING_DOWN'
        else:
            return 'ABOVE_LOD'
    
    def calculate_distance(self, price: float, lod: float) -> float:
        """Calculate percentage distance from LOD"""
        if lod is None:
            return None
        return ((price - lod) / lod) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from LOD"""
        if distance_pct is None:
            return 'NO_LOD'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_lod']:
            return 'AT_LOD'
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
        if not all(col in df.columns for col in ['timestamp', 'low', 'close']):
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
        
        # Calculate LOD
        lod = self.calculate_lod(df)
        
        if lod is None:
            return {
                'signal': 'NO_LOD_DATA',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate LOD'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        
        # Detect breakdown
        breakdown = self.detect_breakdown(current_price, lod)
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, lod)
        distance_class = self.classify_distance(distance_pct)
        
        # Calculate confidence
        confidence = 70
        
        if breakdown == 'BREAKDOWN_CONFIRMED':
            confidence += 25
        elif distance_class in ['AT_LOD', 'VERY_CLOSE']:
            confidence += 15
        
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        
        if breakdown == 'BREAKDOWN_CONFIRMED':
            confluence_factors.append('LOD breakdown confirmed - bearish signal')
        elif breakdown == 'BREAKING_DOWN':
            confluence_factors.append('Price breaking below LOD - watch for confirmation')
        elif distance_class in ['AT_LOD', 'VERY_CLOSE']:
            confluence_factors.append('Price at/near LOD - potential support test')
        
        confluence_factors.append(f'LOD: ${lod:.2f}')
        confluence_factors.append(f'Distance from LOD: {distance_pct:+.2f}% ({distance_class})')
        
        # Determine signal
        if breakdown == 'BREAKDOWN_CONFIRMED':
            signal = 'BEARISH'
        elif breakdown == 'BREAKING_DOWN':
            signal = 'NEUTRAL'
        elif distance_class in ['AT_LOD', 'VERY_CLOSE'] and distance_pct > 0:
            signal = 'BULLISH'  # Bounce from LOD
        else:
            signal = 'NEUTRAL'
        
        # Metadata
        metadata = {
            'lod': round(lod, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'breakdown_status': breakdown,
            'is_at_support': distance_class in ['AT_LOD', 'VERY_CLOSE'] and distance_pct > 0,
            'is_breaking_down': breakdown in ['BREAKING_DOWN', 'BREAKDOWN_CONFIRMED']
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
    lows = base - np.random.uniform(0, 500, 50)
    closes = lows + np.random.uniform(0, 100, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'low': lows,
        'close': closes,
        'open': closes + 50,
        'high': closes + 100,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    lod_block = LOD()
    result = lod_block.analyze(data)
    
    print("=" * 80)
    print("LOD (LOW OF DAY) - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nLOD Analysis:")
    print(f"  LOD: ${result['metadata']['lod']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"  Breakdown Status: {result['metadata']['breakdown_status']}")
    print(f"  At Support: {result['metadata']['is_at_support']}")
    print(f"  Breaking Down: {result['metadata']['is_breaking_down']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
