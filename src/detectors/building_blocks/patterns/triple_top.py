"""
Triple Top Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Bearish reversal with 3 similar peaks
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class TripleTopPattern:
    """
    Triple Top Pattern Detector
    
    Bearish reversal: 3 similar peaks with neckline support
    - Extension of double top
    - 3rd peak confirms resistance
    
    Success Rate: 70% bearish (research validated)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 20,
                 peak_tolerance: float = 0.03, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.peak_tolerance = peak_tolerance
    
    def find_peaks_troughs(self, df: pd.DataFrame, lookback: int = 5):
        """Find swing highs and lows"""
        peaks = []
        troughs = []
        
        for i in range(lookback, len(df) - lookback):
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                peaks.append({'idx': i, 'price': df['high'].iloc[i]})
            
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                troughs.append({'idx': i, 'price': df['low'].iloc[i]})
        
        return peaks, troughs
    
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
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        peaks, troughs = self.find_peaks_troughs(df)
        
        if len(peaks) < 3 or len(troughs) < 2:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        recent_peaks = peaks[-min(5, len(peaks)):]
        
        # Look for 3 similar peaks
        for i in range(len(recent_peaks) - 2):
            p1 = recent_peaks[i]
            p2 = recent_peaks[i + 1]
            p3 = recent_peaks[i + 2]
            
            # All 3 should be similar height
            diff12 = abs(p1['price'] - p2['price']) / p1['price']
            diff23 = abs(p2['price'] - p3['price']) / p2['price']
            diff13 = abs(p1['price'] - p3['price']) / p1['price']
            
            if diff12 > self.peak_tolerance or diff23 > self.peak_tolerance or diff13 > self.peak_tolerance:
                continue
            
            # Find neckline
            troughs_between = [t for t in troughs if p1['idx'] < t['idx'] < p3['idx']]
            
            if len(troughs_between) < 1:
               continue
            
            neckline_price = min([t['price'] for t in troughs_between])
            
            current_price = float(df['close'].iloc[-1])
            neckline_broken = current_price < neckline_price
            
            signal = 'PATTERN_CONFIRMED' if neckline_broken else 'PATTERN_FORMING'
            confidence = 75 if neckline_broken else 60
            
            avg_peak = (p1['price'] + p2['price'] + p3['price']) / 3
            pattern_height = avg_peak - neckline_price
            target = neckline_price - pattern_height
            
            confluence_factors = []
            confluence_factors.append("Triple Top detected")
            confluence_factors.append(f"3 peaks: ${p1['price']:.2f}, ${p2['price']:.2f}, ${p3['price']:.2f}")
            confluence_factors.append(f"Neckline: ${neckline_price:.2f}")
            
            if neckline_broken:
                confluence_factors.append("✅ NECKLINE BROKEN - Bearish!")
                confidence += 10
            else:
                confluence_factors.append("⏳ Awaiting neckline break")
            
            confluence_factors.append(f"Target: ${target:.2f}")
            confluence_factors.append("Success rate: 70%")
            
            metadata = {
                'pattern_type': 'TRIPLE_TOP',
                'peak1': round(p1['price'], 2),
                'peak2': round(p2['price'], 2),
                'peak3': round(p3['price'], 2),
                'neckline_price': round(neckline_price, 2),
                'neckline_broken': neckline_broken,
                'target_price': round(target, 2),
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
        
        return {
            'signal': 'NO_PATTERN',
            'confidence': 0,
            'metadata': {},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': []
        }
