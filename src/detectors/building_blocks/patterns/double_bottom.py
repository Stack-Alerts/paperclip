"""
Double Bottom Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Identifies bullish reversal with 2 similar troughs and neckline resistance
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


class DoubleBottomPattern:
    """
    Double Bottom Pattern Detector
    
    Bullish reversal: Two similar troughs with neckline resistance
    - First Trough: Initial low
    - Second Trough: Similar depth to first (within tolerance)
    - Neckline: Resistance connecting peak between troughs
    
    Success Rate: 79% (research validated - higher than Double Top)
    
    Parameters:
        min_pattern_bars: Minimum bars (default: 15)
        trough_tolerance: Max % difference between troughs (default: 0.03)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 trough_tolerance: float = 0.03, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.trough_tolerance = trough_tolerance
    
    def find_peaks_troughs(self, df: pd.DataFrame, lookback: int = 5) -> Tuple[List, List]:
        """Find swing highs and lows"""
        peaks = []
        troughs = []
        
        for i in range(lookback, len(df) - lookback):
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                peaks.append({'idx': i, 'price': df['high'].iloc[i], 'timestamp': df['timestamp'].iloc[i]})
            
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                troughs.append({'idx': i, 'price': df['low'].iloc[i], 'timestamp': df['timestamp'].iloc[i]})
        
        return peaks, troughs
    
    def detect_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect Double Bottom pattern"""
        if len(df) < self.min_pattern_bars:
            return None
        
        peaks, troughs = self.find_peaks_troughs(df)
        
        if len(troughs) < 2 or len(peaks) < 1:
            return None
        
        recent_troughs = troughs[-min(5, len(troughs)):]
        
        for i in range(len(recent_troughs) - 1):
            trough1 = recent_troughs[i]
            trough2 = recent_troughs[i + 1]
            
            # Troughs should be similar depth
            trough_diff = abs(trough1['price'] - trough2['price']) / trough1['price']
            if trough_diff > self.trough_tolerance:
                continue
            
            # Find peak between troughs for neckline
            peaks_between = [p for p in peaks if trough1['idx'] < p['idx'] < trough2['idx']]
            
            if len(peaks_between) < 1:
                continue
            
            neckline_price = peaks_between[0]['price']
            pattern_height = neckline_price - ((trough1['price'] + trough2['price']) / 2)
            
            return {
                'trough1': trough1,
                'trough2': trough2,
                'neckline_price': neckline_price,
                'pattern_height': pattern_height,
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
        confidence = 80 if neckline_broken else 60
        
        target_price = pattern['neckline_price'] + pattern['pattern_height']
        
        confluence_factors = []
        confluence_factors.append("Double Bottom pattern detected")
        confluence_factors.append(f"Trough 1: ${pattern['trough1']['price']:.2f}")
        confluence_factors.append(f"Trough 2: ${pattern['trough2']['price']:.2f}")
        confluence_factors.append(f"Neckline: ${pattern['neckline_price']:.2f}")
        
        if neckline_broken:
            confluence_factors.append("✅ Neckline BROKEN - Bullish confirmed")
            confidence += 10
        else:
            confluence_factors.append("⏳ Awaiting neckline break")
        
        confluence_factors.append(f"Target: ${target_price:.2f}")
        confluence_factors.append("Success rate: 79%")
        
        metadata = {
            'pattern_type': 'DOUBLE_BOTTOM',
            'trough1_price': round(pattern['trough1']['price'], 2),
            'trough2_price': round(pattern['trough2']['price'], 2),
            'neckline_price': round(pattern['neckline_price'], 2),
            'neckline_broken': neckline_broken,
            'target_price': round(target_price, 2),
            'pattern_height': round(pattern['pattern_height'], 2),
            'expected_success_rate': 0.79
        }
        
        return {
            'signal': signal,
            'confidence': min(100, round(confidence, 2)),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
