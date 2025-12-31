"""
Range Liquidity Building Block
Category: Market Structure  
Purpose: Identifies internal/external liquidity pools
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class RangeLiquidity:
    """Identifies range liquidity pools"""
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 20:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        range_high = df['high'].iloc[-20:].max()
        range_low = df['low'].iloc[-20:].min()
        current_price = df['close'].iloc[-1]
        
        # External liquidity above/below range
        buy_side_liquidity = range_high
        sell_side_liquidity = range_low
        
        distance_to_high = ((range_high - current_price) / current_price) * 100
        distance_to_low = ((current_price - range_low) / current_price) * 100
        
        if distance_to_high < distance_to_low:
            signal = 'NEAR_BUY_SIDE_LIQUIDITY'
            confidence = 60
            confluence_factors = [f'Approaching buy-side liquidity at ${range_high:.2f}']
        else:
            signal = 'NEAR_SELL_SIDE_LIQUIDITY'
            confidence = 60
            confluence_factors = [f'Approaching sell-side liquidity at ${range_low:.2f}']
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {'buy_side': round(buy_side_liquidity, 2), 'sell_side': round(sell_side_liquidity, 2)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
