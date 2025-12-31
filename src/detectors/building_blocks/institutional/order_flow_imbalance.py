"""
Order Flow Imbalance Building Block
Category: Institutional & Volume
Purpose: Measures buy/sell imbalance at price levels
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class OrderFlowImbalance:
    """Detects order flow imbalances"""
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 10:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        # Simplified: up volume vs down volume
        up_volume = df[df['close'] > df['open']]['volume'].sum()
        down_volume = df[df['close'] < df['open']]['volume'].sum()
        
        if up_volume > down_volume * 1.5:
            signal = 'BUY_IMBALANCE'
            confidence = 65
            confluence_factors = ['Strong buy pressure detected']
        elif down_volume > up_volume * 1.5:
            signal = 'SELL_IMBALANCE'
            confidence = 65
            confluence_factors = ['Strong sell pressure detected']
        else:
            signal = 'BALANCED'
            confidence = 50
            confluence_factors = ['Order flow balanced']
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {'up_volume': int(up_volume), 'down_volume': int(down_volume)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
