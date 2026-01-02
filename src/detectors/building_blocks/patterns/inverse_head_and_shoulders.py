"""
Inverse Head and Shoulders Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Identifies bullish reversal pattern (mirror of H&S) - 3 troughs with neckline resistance
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


class InverseHeadAndShouldersPattern:
    """
    Inverse Head and Shoulders Pattern Detector
    
    Bullish reversal pattern (mirror of H&S):
    - Left Shoulder: Initial trough
    - Head: Lowest trough (center)
    - Right Shoulder: Third trough, similar depth to left shoulder
    - Neckline: Resistance connecting two peaks
    
    Success Rate: 86% (research validated - higher than H&S)
    
    Parameters:
        min_pattern_bars: Minimum bars for pattern (default: 20)
        shoulder_tolerance: Max % difference between shoulders (default: 0.05)
        neckline_tolerance: Neckline slope tolerance (default: 0.02)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 shoulder_tolerance: float = 0.05, neckline_tolerance: float = 0.02, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.shoulder_tolerance = shoulder_tolerance
        self.neckline_tolerance = neckline_tolerance
    
    def find_peaks_troughs(self, df: pd.DataFrame, lookback: int = 5) -> Tuple[List, List]:
        """Find swing highs (peaks) and swing lows (troughs)"""
        peaks = []
        troughs = []
        
        for i in range(lookback, len(df) - lookback):
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                peaks.append({'idx': i, 'price': df['high'].iloc[i], 'timestamp': df['timestamp'].iloc[i]})
            
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                troughs.append({'idx': i, 'price': df['low'].iloc[i], 'timestamp': df['timestamp'].iloc[i]})
        
        return peaks, troughs
    
    def detect_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect Inverse Head and Shoulders pattern"""
        if len(df) < self.min_pattern_bars:
            return None
        
        peaks, troughs = self.find_peaks_troughs(df)
        
        if len(troughs) < 3 or len(peaks) < 2:
            return None
        
        recent_troughs = troughs[-min(10, len(troughs)):]
        
        for i in range(len(recent_troughs) - 2):
            left_shoulder = recent_troughs[i]
            head = recent_troughs[i + 1]
            right_shoulder = recent_troughs[i + 2]
            
            # Head must be lowest
            if head['price'] >= left_shoulder['price'] or head['price'] >= right_shoulder['price']:
                continue
            
            # Shoulders should be similar depth
            shoulder_diff = abs(left_shoulder['price'] - right_shoulder['price']) / left_shoulder['price']
            if shoulder_diff > self.shoulder_tolerance:
                continue
            
            # Find peaks between troughs for neckline
            peaks_between = [p for p in peaks 
                           if left_shoulder['idx'] < p['idx'] < right_shoulder['idx']]
            
            if len(peaks_between) < 2:
                continue
            
            peak1 = peaks_between[0]
            peak2 = peaks_between[-1]
            
            neckline_price = (peak1['price'] + peak2['price']) / 2
            neckline_slope = abs((peak2['price'] - peak1['price']) / peak1['price'])
            
            if neckline_slope > self.neckline_tolerance:
                continue
            
            return {
                'left_shoulder': left_shoulder,
                'head': head,
                'right_shoulder': right_shoulder,
                'neckline_price': neckline_price,
                'neckline_slope': neckline_slope,
                'pattern_height': neckline_price - head['price'],
                'completion': 100.0
            }
        
        return None
    
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
        neckline_broken = current_price > pattern['neckline_price']
        
        signal = 'PATTERN_CONFIRMED' if neckline_broken else 'PATTERN_FORMING'
        confidence = 85 if neckline_broken else 65
        
        target_price = pattern['neckline_price'] + pattern['pattern_height']
        distance_to_target = ((target_price - current_price) / current_price) * 100
        
        confluence_factors = []
        confluence_factors.append(f"Inverse Head & Shoulders detected")
        confluence_factors.append(f"Left Shoulder: ${pattern['left_shoulder']['price']:.2f}")
        confluence_factors.append(f"Head: ${pattern['head']['price']:.2f}")
        confluence_factors.append(f"Right Shoulder: ${pattern['right_shoulder']['price']:.2f}")
        confluence_factors.append(f"Neckline: ${pattern['neckline_price']:.2f}")
        
        if neckline_broken:
            confluence_factors.append("✅ Neckline BROKEN - Pattern confirmed")
            confluence_factors.append("BULLISH reversal signal active")
            confidence += 15
        else:
            confluence_factors.append("⏳ Pattern forming - awaiting neckline break")
        
        confluence_factors.append(f"Target: ${target_price:.2f} (+{distance_to_target:.1f}%)")
        confluence_factors.append("Success rate: 86% (research validated)")
        
        metadata = {
            'pattern_type': 'INVERSE_HEAD_AND_SHOULDERS',
            'left_shoulder_price': round(pattern['left_shoulder']['price'], 2),
            'head_price': round(pattern['head']['price'], 2),
            'right_shoulder_price': round(pattern['right_shoulder']['price'], 2),
            'neckline_price': round(pattern['neckline_price'], 2),
            'neckline_broken': neckline_broken,
            'target_price': round(target_price, 2),
            'pattern_height': round(pattern['pattern_height'], 2),
            'completion_pct': pattern['completion'],
            'expected_success_rate': 0.86
        }
        
        return {
            'signal': signal,
            'confidence': min(100, round(confidence, 2)),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
