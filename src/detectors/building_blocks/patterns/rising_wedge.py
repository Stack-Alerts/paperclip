"""
Rising Wedge Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Bearish reversal pattern with converging upward trendlines
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class RisingWedgePattern:
    """
    Rising Wedge Pattern Detector
    
    Bearish reversal: Both trendlines rising but converging
    - Higher highs and higher lows (uptrend)
    - But converging (wedge shape)
    - Typically breaks down
    
    Success Rate: 70% bearish (research validated)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 20,
                 convergence_threshold: float = 0.5, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.convergence_threshold = convergence_threshold
    
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
    
    def is_rising_wedge(self, highs: List, lows: List) -> bool:
        """Check if pattern forms rising wedge"""
        if len(highs) < 2 or len(lows) < 2:
            return False
        
        # Both should be rising
        for i in range(len(highs) - 1):
            if highs[i+1]['price'] <= highs[i]['price']:
                return False
        
        for i in range(len(lows) - 1):
            if lows[i+1]['price'] <= lows[i]['price']:
                return False
        
        # Must be converging
        initial_range = highs[0]['price'] - lows[0]['price']
        final_range = highs[-1]['price'] - lows[-1]['price']
        
        if initial_range == 0:
            return False
        
        return (final_range / initial_range) < self.convergence_threshold
    
    
        # Adaptive lookback based on data size
        adaptive_lookback = min(lookback, len(df) // 4)
        lookback = max(lookback // 2, adaptive_lookback)

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
        
        highs, lows = self.find_swing_points(df)
        
        if len(highs) < 2 or len(lows) < 2:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        recent_highs = highs[-min(4, len(highs)):]
        recent_lows = lows[-min(4, len(lows)):]
        
        if not self.is_rising_wedge(recent_highs, recent_lows):
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        lower_trendline = recent_lows[-1]['price']
        
        breakdown = current_price < lower_trendline
        signal = 'BREAKDOWN_CONFIRMED' if breakdown else 'PATTERN_FORMING'
        confidence = 90 if breakdown else 60
        
        pattern_height = recent_highs[0]['price'] - recent_lows[0]['price']
        target = lower_trendline - pattern_height
        
        confluence_factors = []
        confluence_factors.append("Rising Wedge detected")
        confluence_factors.append("Bearish reversal pattern")
        confluence_factors.append(f"Converging upward trendlines")
        
        if breakdown:
            confluence_factors.append("✅ BREAKDOWN confirmed!")
            confidence += 15
        else:
            confluence_factors.append("⏳ Awaiting breakdown")
        
        confluence_factors.append(f"Target: ${target:.2f}")
        confluence_factors.append("Success rate: 70% bearish")
        
        metadata = {
            'pattern_type': 'RISING_WEDGE',
            'breakdown_confirmed': breakdown,
            'target_price': round(target, 2),
            'pattern_height': round(pattern_height, 2),
            'expected_success_rate': 0.70
        }
        
        return {
            'signal': signal,
            'confidence': min(100, round(confidence, 2)),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
