"""
Triple Bottom Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Bullish reversal with 3 similar troughs
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class TripleBottomPattern:
    """
    Triple Bottom Pattern Detector
    
    Bullish reversal: 3 similar troughs with neckline resistance
    - Extension of double bottom
    - 3rd trough confirms support
    
    Success Rate: 77% bullish (research validated)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 20,
                 trough_tolerance: float = 0.03, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.trough_tolerance = trough_tolerance
    
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
        
        if len(troughs) < 3 or len(peaks) < 2:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        recent_troughs = troughs[-min(5, len(troughs)):]
        
        # Look for 3 similar troughs
        for i in range(len(recent_troughs) - 2):
            t1 = recent_troughs[i]
            t2 = recent_troughs[i + 1]
            t3 = recent_troughs[i + 2]
            
            # All 3 should be similar depth
            diff12 = abs(t1['price'] - t2['price']) / t1['price']
            diff23 = abs(t2['price'] - t3['price']) / t2['price']
            diff13 = abs(t1['price'] - t3['price']) / t1['price']
            
            if diff12 > self.trough_tolerance or diff23 > self.trough_tolerance or diff13 > self.trough_tolerance:
                continue
            
            # Find neckline
            peaks_between = [p for p in peaks if t1['idx'] < p['idx'] < t3['idx']]
            
            if len(peaks_between) < 1:
                continue
            
            neckline_price = max([p['price'] for p in peaks_between])
            
            current_price = float(df['close'].iloc[-1])
            neckline_broken = current_price > neckline_price
            
            signal = 'PATTERN_CONFIRMED' if neckline_broken else 'PATTERN_FORMING'
            confidence = 80 if neckline_broken else 65
            
            avg_trough = (t1['price'] + t2['price'] + t3['price']) / 3
            pattern_height = neckline_price - avg_trough
            target = neckline_price + pattern_height
            
            confluence_factors = []
            confluence_factors.append("Triple Bottom detected")
            confluence_factors.append(f"3 troughs: ${t1['price']:.2f}, ${t2['price']:.2f}, ${t3['price']:.2f}")
            confluence_factors.append(f"Neckline: ${neckline_price:.2f}")
            
            if neckline_broken:
                confluence_factors.append("✅ NECKLINE BROKEN - Bullish!")
                confidence += 10
            else:
                confluence_factors.append("⏳ Awaiting neckline break")
            
            confluence_factors.append(f"Target: ${target:.2f}")
            confluence_factors.append("Success rate: 77%")
            
            metadata = {
                'pattern_type': 'TRIPLE_BOTTOM',
                'trough1': round(t1['price'], 2),
                'trough2': round(t2['price'], 2),
                'trough3': round(t3['price'], 2),
                'neckline_price': round(neckline_price, 2),
                'neckline_broken': neckline_broken,
                'target_price': round(target, 2),
                'expected_success_rate': 0.77
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
