"""
Supply & Demand Zones Building Block
Category: Supply/Demand & Fibonacci
Purpose: Identifies institutional accumulation/distribution zones
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class SupplyDemandZones:
    """Identifies supply and demand zones"""
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 20:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        # Find zones: consolidation before strong move
        recent_high = df['high'].iloc[-10:].max()
        recent_low = df['low'].iloc[-10:].min()
        current_price = df['close'].iloc[-1]
        
        # Demand zone (support)
        if current_price <= recent_low * 1.02:
            signal = 'DEMAND_ZONE'
            confidence = 80
            confluence_factors = [f'At demand zone (support ${recent_low:.2f})']
            zone_type = 'DEMAND'
        # Supply zone (resistance)
        elif current_price >= recent_high * 0.98:
            signal = 'SUPPLY_ZONE'
            confidence = 80
            confluence_factors = [f'At supply zone (resistance ${recent_high:.2f})']
            zone_type = 'SUPPLY'
        else:
            signal = 'NO_ZONE'
            confidence = 55
            confluence_factors = ['No zone detected']
            zone_type = 'NONE'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {'zone_type': zone_type, 'support': round(recent_low, 2), 'resistance': round(recent_high, 2)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
