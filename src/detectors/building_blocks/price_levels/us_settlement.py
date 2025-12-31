"""
US Settlement Price Building Block
Category: Price Levels
Purpose: CME Bitcoin futures settlement price (4 PM ET / 9 PM UTC)
"""

from typing import Dict, Any
from datetime import datetime, time
import pandas as pd
import numpy as np


class USSettlement:
    """
    US Settlement Price - CME Bitcoin Futures Settlement
    
    Tracks the CME settlement price (4 PM ET / 9 PM UTC).
    Critical for:
    - Futures expiry levels
    - Institutional activity
    - End-of-day positioning
    - Gap trading
    """
    
    def __init__(self, timeframe: str = '15min', settlement_hour_utc: int = 21, **kwargs):
        """Initialize US Settlement block"""
        self.timeframe = timeframe
        self.settlement_hour_utc = settlement_hour_utc
        
        self.btc_distance_thresholds = {
            'at_settlement': 0.15,
            'very_close': 0.75,
            'close': 1.5,
            'moderate': 3.0,
            'far': 3.0
        }
    
    def find_settlement_price(self, df: pd.DataFrame) -> float:
        """Find most recent settlement price (21:00 UTC / 4 PM ET)"""
        if 'timestamp' not in df.columns or 'close' not in df.columns:
            return None
        
        settlement_data = df[df['timestamp'].dt.hour == self.settlement_hour_utc]
        if len(settlement_data) == 0:
            return None
        
        return float(settlement_data['close'].iloc[-1])
    
    def calculate_distance(self, price: float, settlement: float) -> float:
        """Calculate percentage distance from settlement"""
        if settlement is None:
            return None
        return ((price - settlement) / settlement) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from settlement"""
        if distance_pct is None:
            return 'NO_SETTLEMENT'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_settlement']:
            return 'AT_SETTLEMENT'
        elif abs_dist < self.btc_distance_thresholds['very_close']:
            return 'VERY_CLOSE'
        elif abs_dist < self.btc_distance_thresholds['close']:
            return 'CLOSE'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        else:
            return 'FAR'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['timestamp', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No data provided'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        settlement = self.find_settlement_price(df)
        
        if settlement is None:
            return {
                'signal': 'NO_SETTLEMENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No settlement price found'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = self.calculate_distance(current_price, settlement)
        distance_class = self.classify_distance(distance_pct)
        
        confidence = 70
        if distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            confidence += 20
        confidence = min(100, confidence)
        
        confluence_factors = []
        if distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            confluence_factors.append('Price at/near US settlement - institutional level')
        
        confluence_factors.append(f'US Settlement: ${settlement:.2f}')
        confluence_factors.append(f'Distance: {distance_pct:+.2f}% ({distance_class})')
        
        if distance_pct > 0 and distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            signal = 'NEUTRAL'  # At resistance
        elif distance_pct < 0 and distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            signal = 'NEUTRAL'  # At support
        else:
            signal = 'NEUTRAL'
        
        metadata = {
            'settlement_price': round(settlement, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'is_institutional_level': distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE'],
            'settlement_hour_utc': self.settlement_hour_utc
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
