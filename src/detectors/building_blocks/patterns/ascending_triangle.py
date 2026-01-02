"""
Ascending Triangle Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Identifies bullish continuation with rising lows and flat resistance
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class AscendingTrianglePattern:
    """
    Ascending Triangle Pattern Detector
    
    Bullish continuation: Rising support + horizontal resistance
    - Higher lows (ascending trendline)
    - Flat resistance level
    - Converging price action
    - Breakout typically bullish
    
    Success Rate: 72% bullish (research validated)
    
    Parameters:
        min_pattern_bars: Minimum bars (default: 20)
        resistance_tolerance: Tolerance for flat resistance (default: 0.01)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 resistance_tolerance: float = 0.01, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.resistance_tolerance = resistance_tolerance
    
    def find_swing_points(self, df: pd.DataFrame, lookback: int = 5):
        """Find swing highs and lows"""
        highs = []
        lows = []
        
        for i in range(lookback, len(df) - lookback):
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                highs.append({'idx': i, 'price': df['high'].iloc[i]})
            
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                lows.append({'idx': i, 'price': df['low'].iloc[i]})
        
        return highs, lows
    
    def is_ascending_support(self, lows: List) -> bool:
        """Check if lows are rising"""
        if len(lows) < 2:
            return False
        
        for i in range(len(lows) - 1):
            if lows[i+1]['price'] <= lows[i]['price']:
                return False
        return True
    
    def is_flat_resistance(self, highs: List) -> bool:
        """Check if highs form flat resistance"""
        if len(highs) < 2:
            return False
        
        prices = [h['price'] for h in highs]
        avg_price = np.mean(prices)
        
        for price in prices:
            if abs(price - avg_price) / avg_price > self.resistance_tolerance:
                return False
        return True
    
    def detect_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect Ascending Triangle"""
        if len(df) < self.min_pattern_bars:
            return None
        
        highs, lows = self.find_swing_points(df)
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        # Take recent points
        recent_highs = highs[-min(4, len(highs)):]
        recent_lows = lows[-min(4, len(lows)):]
        
        # Check pattern conditions
        if not self.is_flat_resistance(recent_highs):
            return None
        
        if not self.is_ascending_support(recent_lows):
            return None
        
        resistance_level = np.mean([h['price'] for h in recent_highs])
        support_slope = (recent_lows[-1]['price'] - recent_lows[0]['price']) / len(recent_lows)
        
        return {
            'resistance_level': resistance_level,
            'support_start': recent_lows[0]['price'],
            'support_end': recent_lows[-1]['price'],
            'support_slope': support_slope,
            'highs_count': len(recent_highs),
            'lows_count': len(recent_lows),
            'completion': 100.0
        }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.min_pattern_bars:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.min_pattern_bars} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        pattern = self.detect_pattern(df)
        
        if pattern is None:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        resistance_broken = current_price > pattern['resistance_level']
        
        signal = 'BREAKOUT_CONFIRMED' if resistance_broken else 'PATTERN_FORMING'
        confidence = 90 if resistance_broken else 60
        
        # Target = pattern height projected upward
        pattern_height = pattern['resistance_level'] - pattern['support_start']
        target_price = pattern['resistance_level'] + pattern_height
        
        confluence_factors = []
        confluence_factors.append("Ascending Triangle detected")
        confluence_factors.append(f"Resistance: ${pattern['resistance_level']:.2f}")
        confluence_factors.append(f"Rising support: ${pattern['support_start']:.2f} → ${pattern['support_end']:.2f}")
        confluence_factors.append(f"Bullish continuation pattern")
        
        if resistance_broken:
            confluence_factors.append("✅ BREAKOUT confirmed - Bullish!")
            confidence += 15
        else:
            confluence_factors.append("⏳ Awaiting breakout")
        
        confluence_factors.append(f"Target: ${target_price:.2f}")
        confluence_factors.append("Success rate: 72% bullish")
        
        metadata = {
            'pattern_type': 'ASCENDING_TRIANGLE',
            'resistance_level': round(pattern['resistance_level'], 2),
            'support_start': round(pattern['support_start'], 2),
            'support_end': round(pattern['support_end'], 2),
            'breakout_confirmed': resistance_broken,
            'target_price': round(target_price, 2),
            'pattern_height': round(pattern_height, 2),
            'expected_success_rate': 0.72
        }
        
        return {
            'signal': signal,
            'confidence': min(100, round(confidence, 2)),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
