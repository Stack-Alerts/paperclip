"""
Market Depth Analysis Building Block
Category: Institutional & Volume
Purpose: Analyzes bid/ask depth for liquidity assessment
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class MarketDepth:
    """Analyzes market depth characteristics"""
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 10:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors':[]}
        
        # Simplified depth analysis using volume at price levels
        avg_volume = df['volume'].mean()
        recent_volume = df['volume'].iloc[-5:].mean()
        
        depth_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        if depth_ratio > 1.5:
            signal = 'HIGH_LIQUIDITY'
            confidence = 75
            confluence_factors = ['High liquidity detected']
        elif depth_ratio < 0.5:
            signal = 'LOW_LIQUIDITY'
            confidence = 75
            confluence_factors = ['Low liquidity - caution']
        else:
            signal = 'NORMAL_LIQUIDITY'
            confidence = 65
            confluence_factors = ['Normal liquidity conditions']
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {'depth_ratio': round(depth_ratio, 2)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
