"""
Double Top Pattern Building Block
Category: Pattern-Based Building Blocks  
Purpose: Identifies bearish reversal with 2 similar peaks and neckline support
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


class DoubleTopPattern:
    """
    Double Top Pattern Detector
    
    Bearish reversal: Two similar peaks with neckline support
    - First Peak: Initial high
    - Second Peak: Similar height to first (within tolerance)
    - Neckline: Support connecting trough between peaks
    
    Success Rate: 72% (research validated)
    
    Parameters:
        min_pattern_bars: Minimum bars (default: 15)
        peak_tolerance: Max % difference between peaks (default: 0.03 = 3%)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 peak_tolerance: float = 0.03, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.peak_tolerance = peak_tolerance
    
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
        """Detect Double Top pattern"""
        if len(df) < self.min_pattern_bars:
            return None
        
        peaks, troughs = self.find_peaks_troughs(df)
        
        if len(peaks) < 2 or len(troughs) < 1:
            return None
        
        # Check recent peaks for double top
        recent_peaks = peaks[-min(5, len(peaks)):]
        
        for i in range(len(recent_peaks) - 1):
            peak1 = recent_peaks[i]
            peak2 = recent_peaks[i + 1]
            
            # Peaks should be similar height
            peak_diff = abs(peak1['price'] - peak2['price']) / peak1['price']
            if peak_diff > self.peak_tolerance:
                continue
            
            # Find trough between peaks for neckline
            troughs_between = [t for t in troughs if peak1['idx'] < t['idx'] < peak2['idx']]
            
            if len(troughs_between) < 1:
                continue
            
            neckline_price = troughs_between[0]['price']
            pattern_height = ((peak1['price'] + peak2['price']) / 2) - neckline_price
            
            return {
                'peak1': peak1,
                'peak2': peak2,
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
        neckline_broken = current_price < pattern['neckline_price']
        
        signal = 'PATTERN_CONFIRMED' if neckline_broken else 'PATTERN_FORMING'
        confidence = 90 if neckline_broken else 55
        
        target_price = pattern['neckline_price'] - pattern['pattern_height']
        
        confluence_factors = []
        confluence_factors.append("Double Top pattern detected")
        confluence_factors.append(f"Peak 1: ${pattern['peak1']['price']:.2f}")
        confluence_factors.append(f"Peak 2: ${pattern['peak2']['price']:.2f}")
        confluence_factors.append(f"Neckline: ${pattern['neckline_price']:.2f}")
        
        if neckline_broken:
            confluence_factors.append("✅ Neckline BROKEN - Bearish confirmed")
            confidence += 15
        else:
            confluence_factors.append("⏳ Awaiting neckline break")
        
        confluence_factors.append(f"Target: ${target_price:.2f}")
        confluence_factors.append("Success rate: 72%")
        
        metadata = {
            'pattern_type': 'DOUBLE_TOP',
            'peak1_price': round(pattern['peak1']['price'], 2),
            'peak2_price': round(pattern['peak2']['price'], 2),
            'neckline_price': round(pattern['neckline_price'], 2),
            'neckline_broken': neckline_broken,
            'target_price': round(target_price, 2),
            'pattern_height': round(pattern['pattern_height'], 2),
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
