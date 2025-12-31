"""
VWAP Building Block
Category: Institutional & Volume
Purpose: Volume Weighted Average Price - institutional benchmark
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class VWAP:
    """Volume Weighted Average Price"""
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 10:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        # Calculate VWAP: sum(price * volume) / sum(volume)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        current_vwap = float(vwap.iloc[-1])
        current_price = float(df['close'].iloc[-1])
        
        if current_price > current_vwap:
            signal = 'ABOVE_VWAP'
            confidence = 60
            confluence_factors = [f'Price above VWAP (${current_vwap:.2f}) - premium']
        else:
            signal = 'BELOW_VWAP'
            confidence = 60
            confluence_factors = [f'Price below VWAP (${current_vwap:.2f}) - discount']
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {'vwap': round(current_vwap, 2), 'current_price': round(current_price, 2)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
