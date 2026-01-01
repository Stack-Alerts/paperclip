"""
Wyckoff Re-accumulation Phase Detector
Category: Wyckoff Method  
Purpose: Identifies continuation consolidation within uptrends
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class WyckoffReaccumulation:
    """Detects Wyckoff re-accumulation phases"""
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 50:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        # Re-accumulation: uptrend + consolidation
        trend_up = df['close'].iloc[-1] > df['close'].iloc[-30]
        recent_range = df['high'].iloc[-10:].max() - df['low'].iloc[-10:].min()
        full_range = df['high'].max() - df['low'].min()
        
        consolidating = recent_range < full_range * 0.4
        
        if trend_up and consolidating:
            signal = 'REACCUMULATION_DETECTED'
            confidence = 77
            confluence_factors = ['Uptrend with consolidation', 'Potential re-accumulation']
        else:
            signal = 'NO_REACCUMULATION'
            confidence = 45
            confluence_factors = ['Pattern not detected']
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {'phase': 'REACCUMULATION' if confidence > 50 else 'NONE'},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
