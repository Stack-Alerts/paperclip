"""
EMA Crossover Systems Building Block
Category: Institutional & Volume
Purpose: Standard EMA crossovers (20/50/200) for trend identification
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class EMACrossover:
    """EMA Cross over detection"""
    
    def __init__(self, timeframe: str = '15min', fast: int = 50, slow: int = 200, **kwargs):
        self.timeframe = timeframe
        self.fast = fast
        self.slow = slow
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < self.slow:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        ema_fast = df['close'].ewm(span=self.fast).mean()
        ema_slow = df['close'].ewm(span=self.slow).mean()
        
        current_fast = float(ema_fast.iloc[-1])
        current_slow = float(ema_slow.iloc[-1])
        prev_fast = float(ema_fast.iloc[-2])
        prev_slow = float(ema_slow.iloc[-2])
        
        # Golden cross / Death cross
        if current_fast > current_slow and prev_fast <= prev_slow:
            signal = 'GOLDEN_CROSS'
            confidence = 75
            confluence_factors = [f'Golden Cross: EMA{self.fast} crossed above EMA{self.slow}']
        elif current_fast < current_slow and prev_fast >= prev_slow:
            signal = 'DEATH_CROSS'
            confidence = 75
            confluence_factors = [f'Death Cross: EMA{self.fast} crossed below EMA{self.slow}']
        elif current_fast > current_slow:
            signal = 'BULLISH_ALIGNMENT'
            confidence = 60
            confluence_factors = ['EMAs bullishly aligned']
        else:
            signal = 'BEARISH_ALIGNMENT'
            confidence = 60
            confluence_factors = ['EMAs bearishly aligned']
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {'fast_ema': round(current_fast, 2), 'slow_ema': round(current_slow, 2)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
       }
