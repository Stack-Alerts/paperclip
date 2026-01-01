"""
Premium and Discount Zones Building Block
Category: Market Structure
Purpose: Divides price range into premium (expensive) and discount (cheap) areas
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class PremiumDiscountZones:
    """Identifies premium and discount zones"""
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 20:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        recent_high = df['high'].iloc[-20:].max()
        recent_low = df['low'].iloc[-20:].min()
        equilibrium = (recent_high + recent_low) / 2
        current_price = df['close'].iloc[-1]
        
        if current_price > equilibrium:
            zone = 'PREMIUM'
            signal = 'PRICE_IN_PREMIUM'
            confidence = 70
            confluence_factors = [f'Price in premium zone (above ${equilibrium:.2f})']
        elif current_price < equilibrium:
            zone = 'DISCOUNT'
            signal = 'PRICE_IN_DISCOUNT'
            confidence = 70
            confluence_factors = [f'Price in discount zone (below ${equilibrium:.2f})']
        else:
            zone = 'EQUILIBRIUM'
            signal = 'PRICE_AT_EQUILIBRIUM'
            confidence = 65
            confluence_factors = ['Price at equilibrium']
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {'zone': zone, 'equilibrium': round(equilibrium, 2), 'high': round(recent_high, 2), 'low': round(recent_low, 2)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
