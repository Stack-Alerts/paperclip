"""
Symmetrical Triangle Pattern Building Block
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd

class SymmetricalTrianglePattern:
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        if len(df) < 20:
            return {'signal': 'NO_PATTERN', 'confidence': 0, 'metadata': {},
                    'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                    'timeframe': self.timeframe, 'confluence_factors': []}

        section = df.iloc[-20:]
        first_5, last_5 = section.iloc[:5], section.iloc[-5:]

        first_range = first_5['high'].max() - first_5['low'].min()
        last_range = last_5['high'].max() - last_5['low'].min()

        if last_range < first_range * 0.75:
            current = float(df['close'].iloc[-1])
            upper, lower = last_5['high'].max(), last_5['low'].min()

            if current > upper:
                signal, conf = 'BULLISH_BREAKOUT', 65
            elif current < lower:
                signal, conf = 'BEARISH_BREAKOUT', 65
            else:
                signal, conf = 'PATTERN_FORMING', 55

            return {
                'signal': signal, 'confidence': conf,
                'metadata': {'pattern_type': 'SYMMETRICAL_TRIANGLE', 'upper_bound': round(upper, 2)},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['Triangle detected', 'Range compression']
            }

        return {'signal': 'NO_PATTERN', 'confidence': 0, 'metadata': {},
                'timestamp': df['timestamp'].iloc[-1], 'timeframe': self.timeframe, 'confluence_factors': []}
