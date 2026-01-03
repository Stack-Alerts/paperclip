"""
Asia Session 50% Price Building Block
Category: Price Levels
Purpose: Mid-point of Asia session range for support/resistance
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class AsiaSession50Percent:
    """
    Asia Session 50% Price Level
    
    Calculates the 50% level (midpoint) of the Asia session range.
    Critical for:
    - ICT concepts (Asia session liquidity)
    - Mean reversion trading
    - Session transition setups
    - Equilibrium levels
    """
    
    def __init__(self, timeframe: str = '15min', 
                 asia_start_utc: int = 0, asia_end_utc: int = 8, **kwargs):
        """Initialize Asia Session 50% block"""
        self.timeframe = timeframe
        self.asia_start = asia_start_utc
        self.asia_end = asia_end_utc
        
        self.btc_distance_thresholds = {
            'at_50': 0.1,
            'very_close': 0.5,
            'close': 1.0,
            'moderate': 2.0,
            'far': 2.0
        }
    
    def calculate_asia_50(self, df: pd.DataFrame) -> float:
        """Calculate 50% of Asia session range"""
        if 'timestamp' not in df.columns or 'high' not in df.columns or 'low' not in df.columns:
            return None
        
        current_date = df['timestamp'].iloc[-1].date()
        
        # Get today's Asia session data
        asia_data = df[
            (df['timestamp'].dt.date == current_date) &
            (df['timestamp'].dt.hour >= self.asia_start) &
            (df['timestamp'].dt.hour < self.asia_end)
        ]
        
        if len(asia_data) == 0:
            # Try previous day
            import pandas as pd
            prev_date = current_date - pd.Timedelta(days=1)
            asia_data = df[
                (df['timestamp'].dt.date == prev_date) &
                (df['timestamp'].dt.hour >= self.asia_start) &
                (df['timestamp'].dt.hour < self.asia_end)
            ]
        
        if len(asia_data) == 0:
            return None
        
        asia_high = float(asia_data['high'].max())
        asia_low = float(asia_data['low'].min())
        
        return (asia_high + asia_low) / 2
    
    def calculate_distance(self, price: float, asia_50: float) -> float:
        """Calculate percentage distance from Asia 50%"""
        if asia_50 is None:
            return None
        return ((price - asia_50) / asia_50) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from Asia 50%"""
        if distance_pct is None:
            return 'NO_ASIA_50'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_50']:
            return 'AT_ASIA_50'
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
        if not all(col in df.columns for col in ['timestamp', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 50:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No data provided'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        asia_50 = self.calculate_asia_50(df)
        
        if asia_50 is None:
            return {
                'signal': 'NO_ASIA_DATA',
                'confidence': 0,
                'metadata': {'error': 'No Asia session data found'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = self.calculate_distance(current_price, asia_50)
        distance_class = self.classify_distance(distance_pct)
        
        confidence = 65
        if distance_class in ['AT_ASIA_50', 'VERY_CLOSE']:
            confidence += 25  # Strong mean reversion setup
        confidence = min(100, confidence)
        
        confluence_factors = []
        if distance_class in ['AT_ASIA_50', 'VERY_CLOSE']:
            confluence_factors.append('Price at/near Asia 50% - equilibrium level')
            confluence_factors.append('Mean reversion opportunity')
        
        confluence_factors.append(f'Asia 50%: ${asia_50:.2f}')
        confluence_factors.append(f'Distance: {distance_pct:+.2f}% ({distance_class})')
        
        # Signal based on position relative to Asia 50%
        if distance_class in ['AT_ASIA_50', 'VERY_CLOSE']:
            signal = 'NEUTRAL'  # At equilibrium
        else:
            signal = 'NEUTRAL'
        
        metadata = {
            'asia_50': round(asia_50, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'is_at_equilibrium': distance_class in ['AT_ASIA_50', 'VERY_CLOSE'],
            'asia_session_hours': f'{self.asia_start}:00-{self.asia_end}:00 UTC'
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
