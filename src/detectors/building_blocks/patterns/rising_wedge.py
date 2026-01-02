"""
Rising Wedge Pattern Building Block - EXPERT MODE OPTIMIZED
Realistic detection for 15min timeframe
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class RisingWedgePattern:
    """
    Rising Wedge: Bearish reversal with upward but converging price action
    
    EXPERT MODE: Relaxed for 15min realistic detection
    - Overall uptrend (higher highs + higher lows)
    - Range compression (wedge converging)
    - Breakdown signals bearish reversal
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """EXPERT MODE: Simplified rising wedge detection"""
        if len(df) < 20:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Analyze last 25 bars for pattern
        section = df.iloc[-25:] if len(df) >= 25 else df
        
        # Split into two halves for comparison
        mid = len(section) // 2
        first_half = section.iloc[:mid]
        second_half = section.iloc[mid:]
        
        # Check: Higher highs (uptrend)
        first_high = first_half['high'].max()
        second_high = second_half['high'].max()
        is_higher_highs = second_high > first_high * 0.995  # Allow tiny drops (0.5%)
        
        # Check: Higher lows (uptrend)
        first_low = first_half['low'].min()
        second_low = second_half['low'].min()
        is_higher_lows = second_low > first_low * 0.995  # Allow tiny drops (0.5%)
        
        # Check: Range compression (converging)
        first_range = first_half['high'].max() - first_half['low'].min()
        second_range = second_half['high'].max() - second_half['low'].min()
        is_compressing = second_range < first_range * 0.85  # 15% narrower
        
        # Rising wedge = uptrend + compression
        if is_higher_highs and is_higher_lows and is_compressing:
            current = float(df['close'].iloc[-1])
            support = second_half['low'].min()
            
            breakdown = current < support
            signal = 'BEARISH_BREAKDOWN' if breakdown else 'PATTERN_FORMING'
            confidence = 75 if breakdown else 55
            
            target = support - first_range
            
            return {
                'signal': signal,
                'confidence': confidence,
                'metadata': {
                    'pattern_type': 'RISING_WEDGE',
                    'support': round(support, 2),
                    'breakdown_confirmed': breakdown,
                    'target_price': round(target, 2),
                    'expected_success_rate': 0.70
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': [
                    'Rising Wedge detected',
                    'Uptrend + convergence',
                    'Bearish reversal pattern',
                    f'{'✅ Breakdown!' if breakdown else '⏳ Forming'}'
                ]
            }
        
        return {
            'signal': 'NO_PATTERN',
            'confidence': 0,
            'metadata': {},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': []
        }
