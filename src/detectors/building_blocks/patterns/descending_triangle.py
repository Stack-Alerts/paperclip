"""
Descending Triangle Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Identifies bearish continuation with falling highs and flat support
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: Pattern formation detection, fires when complete

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


class DescendingTrianglePattern:
    """
    Descending Triangle Pattern Detector
    
    Bearish continuation: Falling resistance + horizontal support
    - Lower highs (descending trendline)
    - Flat support level
    - Converging price action
    - Breakout typically bearish
    
    Success Rate: 68% bearish (research validated)
    
    Parameters:
        min_pattern_bars: Minimum bars (default: 20)
        support_tolerance: Tolerance for flat support (default: 0.01)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 support_tolerance: float = 0.01, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.support_tolerance = support_tolerance
    
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
    
    def is_descending_resistance(self, highs: List) -> bool:
        """Check if highs are falling"""
        if len(highs) < 2:
            return False
        
        for i in range(len(highs) - 1):
            if highs[i+1]['price'] >= highs[i]['price']:
                return False
        return True
    
    def is_flat_support(self, lows: List) -> bool:
        """Check if lows form flat support"""
        if len(lows) < 2:
            return False
        
        prices = [l['price'] for l in lows]
        avg_price = np.mean(prices)
        
        for price in prices:
            if abs(price - avg_price) / avg_price > self.support_tolerance:
                return False
        return True
    
    def detect_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect Descending Triangle"""
        if len(df) < self.min_pattern_bars:
            return None
        
        highs, lows = self.find_swing_points(df)
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        recent_highs = highs[-min(4, len(highs)):]
        recent_lows = lows[-min(4, len(lows)):]
        
        if not self.is_flat_support(recent_lows):
            return None
        
        if not self.is_descending_resistance(recent_highs):
            return None
        
        support_level = np.mean([l['price'] for l in recent_lows])
        resistance_slope = (recent_highs[-1]['price'] - recent_highs[0]['price']) / len(recent_highs)
        
        return {
            'support_level': support_level,
            'resistance_start': recent_highs[0]['price'],
            'resistance_end': recent_highs[-1]['price'],
            'resistance_slope': resistance_slope,
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
        support_broken = current_price < pattern['support_level']
        
        signal = 'BREAKDOWN_CONFIRMED' if support_broken else 'PATTERN_FORMING'
        confidence = 85 if support_broken else 55
        
        pattern_height = pattern['resistance_start'] - pattern['support_level']
        target_price = pattern['support_level'] - pattern_height
        
        confluence_factors = []
        confluence_factors.append("Descending Triangle detected")
        confluence_factors.append(f"Support: ${pattern['support_level']:.2f}")
        confluence_factors.append(f"Falling resistance: ${pattern['resistance_start']:.2f} → ${pattern['resistance_end']:.2f}")
        confluence_factors.append(f"Bearish continuation pattern")
        
        if support_broken:
            confluence_factors.append("✅ BREAKDOWN confirmed - Bearish!")
            confidence += 15
        else:
            confluence_factors.append("⏳ Awaiting breakdown")
        
        confluence_factors.append(f"Target: ${target_price:.2f}")
        confluence_factors.append("Success rate: 68% bearish")
        
        metadata = {
            'pattern_type': 'DESCENDING_TRIANGLE',
            'support_level': round(pattern['support_level'], 2),
            'resistance_start': round(pattern['resistance_start'], 2),
            'resistance_end': round(pattern['resistance_end'], 2),
            'breakdown_confirmed': support_broken,
            'target_price': round(target_price, 2),
            'pattern_height': round(pattern_height, 2),
            'expected_success_rate': 0.68
        }
        
        return {
            'signal': signal,
            'confidence': min(100, round(confidence, 2)),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
