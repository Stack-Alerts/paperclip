"""
Symmetrical Triangle Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Identifies neutral pattern with converging trendlines (both sloping)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class SymmetricalTrianglePattern:
    """
    Symmetrical Triangle Pattern Detector
    
    Neutral/Continuation: Converging trendlines (both sloping)
    - Lower highs (descending resistance)
    - Higher lows (ascending support)
    - Converging wedge shape
    - Breakout can be either direction
    
    Success Rate: 54% direction of prior trend (research validated)
    
    Parameters:
        min_pattern_bars: Minimum bars (default: 20)
        convergence_threshold: Min convergence (default: 0.5)
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
    
    def is_converging(self, highs: List, lows: List) -> bool:
        """Check if trendlines are converging"""
        if len(highs) < 2 or len(lows) < 2:
            return False
        
        # Highs should be descending
        for i in range(len(highs) - 1):
            if highs[i+1]['price'] >= highs[i]['price']:
                return False
        
        # Lows should be ascending
        for i in range(len(lows) - 1):
            if lows[i+1]['price'] <= lows[i]['price']:
                return False
        
        # Check convergence
        initial_range = highs[0]['price'] - lows[0]['price']
        final_range = highs[-1]['price'] - lows[-1]['price']
        convergence_ratio = final_range / initial_range
        
        return convergence_ratio < self.convergence_threshold
    
    def detect_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect Symmetrical Triangle"""
        if len(df) < self.min_pattern_bars:
            return None
        
        highs, lows = self.find_swing_points(df)
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        recent_highs = highs[-min(4, len(highs)):]
        recent_lows = lows[-min(4, len(lows)):]
        
        if not self.is_converging(recent_highs, recent_lows):
            return None
        
        resistance_start = recent_highs[0]['price']
        resistance_end = recent_highs[-1]['price']
        support_start = recent_lows[0]['price']
        support_end = recent_lows[-1]['price']
        
        apex_price = (resistance_end + support_end) / 2
        
        return {
            'resistance_start': resistance_start,
            'resistance_end': resistance_end,
            'support_start': support_start,
            'support_end': support_end,
            'apex_price': apex_price,
            'completion': 100.0
        }
    
    
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
        resistance_broken = current_price > pattern['resistance_end']
        support_broken = current_price < pattern['support_end']
        
        if resistance_broken:
            signal = 'BREAKOUT_UP'
            confidence = 75
        elif support_broken:
            signal = 'BREAKOUT_DOWN'
            confidence = 75
        else:
            signal = 'PATTERN_FORMING'
            confidence = 65
        
        pattern_height = pattern['resistance_start'] - pattern['support_start']
        target_up = pattern['apex_price'] + pattern_height
        target_down = pattern['apex_price'] - pattern_height
        
        confluence_factors = []
        confluence_factors.append("Symmetrical Triangle detected")
        confluence_factors.append(f"Converging trendlines")
        confluence_factors.append(f"Resistance: ${pattern['resistance_start']:.2f} → ${pattern['resistance_end']:.2f}")
        confluence_factors.append(f"Support: ${pattern['support_start']:.2f} → ${pattern['support_end']:.2f}")
        confluence_factors.append(f"Neutral pattern - breakout determines direction")
        
        if resistance_broken:
            confluence_factors.append("✅ BULLISH breakout confirmed!")
            confluence_factors.append(f"Target: ${target_up:.2f}")
            confidence += 15
        elif support_broken:
            confluence_factors.append("✅ BEARISH breakout confirmed!")
            confluence_factors.append(f"Target: ${target_down:.2f}")
            confidence += 15
        else:
            confluence_factors.append("⏳ Awaiting breakout direction")
            confluence_factors.append(f"Bullish target: ${target_up:.2f}")
            confluence_factors.append(f"Bearish target: ${target_down:.2f}")
        
        confluence_factors.append("Success rate: 54% in trend direction")
        
        metadata = {
            'pattern_type': 'SYMMETRICAL_TRIANGLE',
            'resistance_start': round(pattern['resistance_start'], 2),
            'resistance_end': round(pattern['resistance_end'], 2),
            'support_start': round(pattern['support_start'], 2),
            'support_end': round(pattern['support_end'], 2),
            'apex_price': round(pattern['apex_price'], 2),
            'breakout_up': resistance_broken,
            'breakout_down': support_broken,
            'target_up': round(target_up, 2),
            'target_down': round(target_down, 2),
            'expected_success_rate': 0.54
        }
        
        return {
            'signal': signal,
            'confidence': min(100, round(confidence, 2)),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
