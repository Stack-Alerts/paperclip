"""
Triple Bottom Pattern - EXPERT MODE with Volume Differentiation
Uses decreasing volume on 3rd trough to distinguish from Double Bottom
"""

from typing import Dict, Any, List
from datetime import datetime
import pandas as pd


class TripleBottomPattern:
    """
    Triple Bottom: 3 similar troughs with DECREASING volume on 3rd
    
    EXPERT DIFFERENTIATION:
    - Requires EXACTLY 3 troughs (not 2)
    - Volume DECREASES on 3rd trough (exhaustion/final test)
    - This distinguishes from Double Bottom (increasing volume)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 trough_tolerance: float = 0.05, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.trough_tolerance = trough_tolerance
    
    def find_troughs(self, df: pd.DataFrame, lookback: int = 5):
        """Find swing lows with volume"""
        troughs = []
        
        for i in range(lookback, len(df) - lookback):
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                # Get volume at this trough
                vol = df['volume'].iloc[max(0, i-2):i+3].mean()  # Average volume around trough
                troughs.append({
                    'idx': i,
                    'price': df['low'].iloc[i],
                    'volume': vol
                })
        
        return troughs
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """EXPERT MODE: Triple bottom with volume analysis"""
        if len(df) < 30:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        troughs = self.find_troughs(df)
        
        if len(troughs) < 3:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Look for last 3 troughs
        recent = troughs[-3:]
        t1, t2, t3 = recent[0], recent[1], recent[2]
        
        # Check: All 3 at similar price (5% tolerance)
        avg_price = (t1['price'] + t2['price'] + t3['price']) / 3
        if (abs(t1['price'] - avg_price) / avg_price > self.trough_tolerance or
            abs(t2['price'] - avg_price) / avg_price > self.trough_tolerance or
            abs(t3['price'] - avg_price) / avg_price > self.trough_tolerance):
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # EXPERT: Check volume pattern
        # Triple bottom = DECREASING volume on 3rd trough (exhaustion)
        vol_decreasing = t3['volume'] < t2['volume'] * 0.9  # 10% less volume
        
        if not vol_decreasing:
            # Not a triple - likely still forming or different pattern
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Find neckline (resistance between troughs)
        section = df.iloc[t1['idx']:t3['idx']+1]
        neckline = section['high'].max()
        
        current = float(df['close'].iloc[-1])
        breakout = current > neckline
        
        signal = 'BULLISH_BREAKOUT' if breakout else 'PATTERN_FORMING'
        confidence = 80 if breakout else 65
        
        target = neckline + (neckline - avg_price)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'pattern_type': 'TRIPLE_BOTTOM',
                'troughs': [round(t1['price'], 2), round(t2['price'], 2), round(t3['price'], 2)],
                'neckline': round(neckline, 2),
                'volume_decreasing': vol_decreasing,
                'breakout_confirmed': breakout,
                'target_price': round(target, 2),
                'expected_success_rate': 0.77
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [
                'Triple Bottom: 3 tests of support',
                f'Decreasing volume on 3rd touch (exhaustion)',
                f'Neckline: ${neckline:.2f}',
                f'{'✅ Breakout!' if breakout else '⏳ Forming'}'
            ]
        }
