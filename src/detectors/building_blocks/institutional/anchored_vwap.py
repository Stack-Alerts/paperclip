"""
Anchored VWAP Building Block
Category: Institutional & Volume
Purpose: VWAP from custom anchor point
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class AnchoredVWAP:
    """Anchored VWAP from specific point"""
    
    def __init__(self, timeframe: str = '15min', anchor_idx: int = 0, **kwargs):
        self.timeframe = timeframe
        self.anchor_idx = anchor_idx
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 10:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        # Anchored from specified index
        anchor_data = df.iloc[self.anchor_idx:]
        typical_price = (anchor_data['high'] + anchor_data['low'] + anchor_data['close']) / 3
        vwap = (typical_price * anchor_data['volume']).cumsum() / anchor_data['volume'].cumsum()
        
        current_vwap = float(vwap.iloc[-1])
        current_price = float(df['close'].iloc[-1])
        
        signal = 'ABOVE_ANCHORED_VWAP' if current_price > current_vwap else 'BELOW_ANCHORED_VWAP'
        
        return {
            'signal': signal,
            'confidence': 62,
            'metadata': {'anchored_vwap': round(current_vwap, 2)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [f'Anchored VWAP: ${current_vwap:.2f}']
        }
