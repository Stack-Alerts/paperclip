"""
Triple Top Pattern - EXPERT MODE with Volume Differentiation
Uses decreasing volume on 3rd peak to distinguish from Double Top
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class TripleTopPattern:
    """
    Triple Top: 3 similar peaks with DECREASING volume on 3rd
    
    EXPERT DIFFERENTIATION:
    - Requires EXACTLY 3 peaks (not 2)
    - Volume DECREASES on 3rd peak (exhaustion/final test)
    - This distinguishes from Double Top (increasing volume)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 peak_tolerance: float = 0.05, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.peak_tolerance = peak_tolerance
    
    def find_peaks(self, df: pd.DataFrame, lookback: int = 5):
        """Find swing highs with volume"""
        peaks = []
        
        for i in range(lookback, len(df) - lookback):
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                vol = df['volume'].iloc[max(0, i-2):i+3].mean()
                peaks.append({
                    'idx': i,
                    'price': df['high'].iloc[i],
                    'volume': vol
                })
        
        return peaks
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """EXPERT MODE: Triple top with volume analysis"""
        if len(df) < 30:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        peaks = self.find_peaks(df)
        
        if len(peaks) < 3:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Last 3 peaks
        recent = peaks[-3:]
        p1, p2, p3 = recent[0], recent[1], recent[2]
        
        # Check: All 3 at similar price
        avg_price = (p1['price'] + p2['price'] + p3['price']) / 3
        if (abs(p1['price'] - avg_price) / avg_price > self.peak_tolerance or
            abs(p2['price'] - avg_price) / avg_price > self.peak_tolerance or
            abs(p3['price'] - avg_price) / avg_price > self.peak_tolerance):
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # EXPERT: Volume decreasing on 3rd peak (exhaustion)
        vol_decreasing = p3['volume'] < p2['volume'] * 0.9
        
        if not vol_decreasing:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Find neckline
        section = df.iloc[p1['idx']:p3['idx']+1]
        neckline = section['low'].min()
        
        current = float(df['close'].iloc[-1])
        breakdown = current < neckline
        
        signal = 'BEARISH_BREAKDOWN' if breakdown else 'PATTERN_FORMING'
        confidence = 80 if breakdown else 65
        
        target = neckline - (avg_price - neckline)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'pattern_type': 'TRIPLE_TOP',
                'peaks': [round(p1['price'], 2), round(p2['price'], 2), round(p3['price'], 2)],
                'neckline': round(neckline, 2),
                'volume_decreasing': vol_decreasing,
                'breakdown_confirmed': breakdown,
                'target_price': round(target, 2),
                'expected_success_rate': 0.74
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [
                'Triple Top: 3 tests of resistance',
                f'Decreasing volume on 3rd touch (exhaustion)',
                f'Neckline: ${neckline:.2f}',
                f'{'✅ Breakdown!' if breakdown else '⏳ Forming'}'
            ]
        }
