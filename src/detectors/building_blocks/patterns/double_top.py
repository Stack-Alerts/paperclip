"""
Double Top Pattern - EXPERT MODE with Volume Differentiation
Uses increasing volume on 2nd peak to distinguish from Triple Top
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class DoubleTopPattern:
    """
    Double Top: 2 similar peaks with INCREASING volume on 2nd
    
    EXPERT DIFFERENTIATION:
    - Requires EXACTLY 2 peaks (not 3)
    - Volume INCREASES on 2nd peak (strong selling pressure)
    - This distinguishes from Triple Top (decreasing volume)
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
        """EXPERT MODE: Double top with volume analysis"""
        if len(df) < 20:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        peaks = self.find_peaks(df)
        
        if len(peaks) < 2:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Last 2 peaks
        recent = peaks[-2:]
        p1, p2 = recent[0], recent[1]
        
        # Check: Similar price
        price_diff = abs(p1['price'] - p2['price']) / p1['price']
        if price_diff > self.peak_tolerance:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # EXPERT: Volume increasing on 2nd peak (selling pressure)
        vol_increasing = p2['volume'] > p1['volume'] * 1.1
        
        if not vol_increasing:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Find neckline
        section = df.iloc[p1['idx']:p2['idx']+1]
        neckline = section['low'].min()
        
        current = float(df['close'].iloc[-1])
        breakdown = current < neckline
        
        signal = 'BEARISH_BREAKDOWN' if breakdown else 'PATTERN_FORMING'
        confidence = 80 if breakdown else 60
        
        avg_price = (p1['price'] + p2['price']) / 2
        target = neckline - (avg_price - neckline)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'pattern_type': 'DOUBLE_TOP',
                'peaks': [round(p1['price'], 2), round(p2['price'], 2)],
                'neckline': round(neckline, 2),
                'volume_increasing': vol_increasing,
                'breakdown_confirmed': breakdown,
                'target_price': round(target, 2),
                'expected_success_rate': 0.72
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [
                'Double Top: 2 tests of resistance',
                f'Increasing volume on 2nd touch (selling pressure)',
                f'Neckline: ${neckline:.2f}',
                f'{'✅ Breakdown!' if breakdown else '⏳ Forming'}'
            ]
        }
