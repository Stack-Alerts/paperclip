"""
LOW (Low of Week) Building Block
Category: Price Levels
Purpose: Weekly low price level for major support and breakdown detection
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class LOW:
    """
    LOW - Low of Week Price Level
    
    Tracks the lowest price reached during the current trading week.
    Critical level for:
    - Major support identification
    - Weekly breakdown detection
    - Swing trading setups
    - Higher timeframe analysis
    """
    
    def __init__(self, timeframe: str = '15min', week_start: int = 0, **kwargs):
        """Initialize LOW block"""
        self.timeframe = timeframe
        self.week_start = week_start
        
        # Bitcoin-specific distance thresholds (% from LOW)
        self.btc_distance_thresholds = {
            'at_low': 0.2,
            'very_close': 1.0,
            'close': 2.5,
            'moderate': 5.0,
            'far': 5.0
        }
    
    def calculate_low(self, df: pd.DataFrame) -> float:
        """Calculate Low of Week from intraday data"""
        if 'timestamp' not in df.columns or 'low' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_week = current_time.isocalendar()[1]
        current_year = current_time.isocalendar()[0]
        
        week_data = df[
            (df['timestamp'].dt.isocalendar().week == current_week) &
            (df['timestamp'].dt.isocalendar().year == current_year)
        ]
        
        if len(week_data) == 0:
            return None
        
        return float(week_data['low'].min())
    
    def detect_breakdown(self, current_price: float, low: float, threshold_pct: float = 0.1) -> str:
        """Detect LOW breakdown"""
        if low is None:
            return 'NO_LOW'
        
        distance_pct = ((current_price - low) / low) * 100
        
        if distance_pct < -threshold_pct:
            return 'BREAKDOWN_CONFIRMED'
        elif distance_pct < 0:
            return 'BREAKING_DOWN'
        else:
            return 'ABOVE_LOW'
    
    def calculate_distance(self, price: float, low: float) -> float:
        """Calculate percentage distance from LOW"""
        if low is None:
            return None
        return ((price - low) / low) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from LOW"""
        if distance_pct is None:
            return 'NO_LOW'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_low']:
            return 'AT_LOW'
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
        if not all(col in df.columns for col in ['timestamp', 'low', 'close']):
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
        
        low = self.calculate_low(df)
        
        if low is None:
            return {
                'signal': 'NO_LOW_DATA',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate LOW'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        breakdown = self.detect_breakdown(current_price, low)
        distance_pct = self.calculate_distance(current_price, low)
        distance_class = self.classify_distance(distance_pct)
        
        confidence = 75
        if breakdown == 'BREAKDOWN_CONFIRMED':
            confidence += 20
        elif distance_class in ['AT_LOW', 'VERY_CLOSE']:
            confidence += 15
        confidence = min(100, confidence)
        
        confluence_factors = []
        if breakdown == 'BREAKDOWN_CONFIRMED':
            confluence_factors.append('LOW breakdown confirmed - strong bearish signal')
        elif breakdown == 'BREAKING_DOWN':
            confluence_factors.append('Price breaking below LOW - major support test')
        elif distance_class in ['AT_LOW', 'VERY_CLOSE']:
            confluence_factors.append('Price at/near LOW - critical support level')
        
        confluence_factors.append(f'LOW: ${low:.2f}')
        confluence_factors.append(f'Distance from LOW: {distance_pct:+.2f}% ({distance_class})')
        
        if breakdown == 'BREAKDOWN_CONFIRMED':
            signal = 'BEARISH'
        elif breakdown == 'BREAKING_DOWN':
            signal = 'NEUTRAL'
        elif distance_class in ['AT_LOW', 'VERY_CLOSE'] and distance_pct > 0:
            signal = 'BULLISH'  # Bounce from LOW
        else:
            signal = 'NEUTRAL'
        
        metadata = {
            'low': round(low, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'breakdown_status': breakdown,
            'is_major_support': distance_class in ['AT_LOW', 'VERY_CLOSE'] and distance_pct > 0,
            'is_breaking_down': breakdown in ['BREAKING_DOWN', 'BREAKDOWN_CONFIRMED']
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
