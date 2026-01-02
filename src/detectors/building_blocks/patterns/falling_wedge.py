"""
Falling Wedge Pattern Building Block
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd

class FallingWedgePattern:
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        if len(df) < 20:
            return {'signal': 'NO_PATTERN', 'confidence': 0, 'metadata': {},
                    'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                    'timeframe': self.timeframe, 'confluence_factors': []}

        section = df.iloc[-20:]
        mid = len(section) // 2
        first, second = section.iloc[:mid], section.iloc[mid:]

        is_lower = second['low'].min() < first['low'].min()
        first_range = first['high'].max() - first['low'].min()
        second_range = second['high'].max() - second['low'].min()
        is_compressing = second_range < first_range * 0.75

        if is_lower and is_compressing:
            current = float(df['close'].iloc[-1])
            resistance = second['high'].max()
            breakout = current > resistance

            return {
                'signal': 'BULLISH_BREAKOUT' if breakout else 'PATTERN_FORMING',
                'confidence': 70 if breakout else 55,
                'metadata': {'pattern_type': 'FALLING_WEDGE', 'resistance': round(resistance, 2)},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['Falling Wedge detected', 'Lower lows + compression']
            }

        return {'signal': 'NO_PATTERN', 'confidence': 0, 'metadata': {},
                'timestamp': df['timestamp'].iloc[-1], 'timeframe': self.timeframe, 'confluence_factors': []}
