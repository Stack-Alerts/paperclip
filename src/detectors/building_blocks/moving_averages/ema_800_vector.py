"""
800 EMA Vector Break Building Block
Category: Moving Average Indicators
Purpose: Identifies when price breaks 800 EMA (approx 3-year MA on daily) with high-volume decisive candle
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class EMA800VectorBreak:
    """
    800 EMA Vector Break Detector
    
    The 800 EMA represents approximately a 3-year moving average on daily charts.
    Extremely long-term trend indicator - rarely broken on intraday timeframes.
    On weekly/monthly charts, signals major Bitcoin market regime changes.
    Used for macro Bitcoin cycle analysis.
    
    Vector Break Criteria:
    - Price crosses 800 EMA
    - Volume > 1.5x average volume (vector candle)
    - Candle body size significant (>60% of candle range)
    - Close beyond EMA (not just a wick)
    
    Parameters:
        ema_period: EMA calculation period (default: 800)
        volume_threshold: Volume multiplier for vector detection (default: 1.5)
        body_threshold: Minimum body percentage of range (default: 0.6)
    """
    
    def __init__(self, timeframe: str = '15min', ema_period: int = 800,
                 volume_threshold: float = 1.5, body_threshold: float = 0.6, **kwargs):
        """Initialize 800 EMA Vector Break detector"""
        self.timeframe = timeframe
        self.ema_period = ema_period
        self.volume_threshold = volume_threshold
        self.body_threshold = body_threshold
        self.volume_avg_period = 20
    
    def calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        return pd.Series(data).ewm(span=period, adjust=False).mean().values
    
    def is_vector_candle(self, df: pd.DataFrame, idx: int) -> bool:
        """Check if candle is a vector candle (high volume + strong body)"""
        if idx < self.volume_avg_period:
            return False
        
        avg_volume = df['volume'].iloc[idx-self.volume_avg_period:idx].mean()
        current_volume = df['volume'].iloc[idx]
        if current_volume < avg_volume * self.volume_threshold:
            return False
        
        candle_range = df['high'].iloc[idx] - df['low'].iloc[idx]
        if candle_range == 0:
            return False
        
        body_size = abs(df['close'].iloc[idx] - df['open'].iloc[idx])
        body_pct = body_size / candle_range
        
        return body_pct >= self.body_threshold
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.ema_period + 10:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.ema_period + 10} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate 800 EMA
        ema_800 = self.calculate_ema(df['close'].values, self.ema_period)
        
        # Get current and previous values
        current_price = float(df['close'].iloc[-1])
        prev_price = float(df['close'].iloc[-2])
        current_ema = float(ema_800[-1])
        prev_ema = float(ema_800[-2])
        
        # Check for EMA cross
        crossed_above = prev_price <= prev_ema and current_price > current_ema
        crossed_below = prev_price >= prev_ema and current_price < current_ema
        
        # Default signal
        signal = 'NO_BREAK'
        confidence = 0
        
        # Check if current candle is a vector candle
        is_vector = self.is_vector_candle(df, len(df) - 1)
        
        # Determine break type
        if crossed_above and is_vector:
            signal = 'BULLISH_BREAK'
            confidence = 80  # Highest confidence for macro EMA breaks
        elif crossed_below and is_vector:
            signal = 'BEARISH_BREAK'
            confidence = 80
        elif crossed_above and not is_vector:
            signal = 'BULLISH_CROSS'
            confidence = 50
        elif crossed_below and not is_vector:
            signal = 'BEARISH_CROSS'
            confidence = 50
        
        # Calculate distance from EMA
        distance_pct = ((current_price - current_ema) / current_ema) * 100
        
        # Classify distance
        if abs(distance_pct) < 0.5:
            distance_class = 'VERY_CLOSE'
        elif abs(distance_pct) < 1.0:
            distance_class = 'CLOSE'
        elif abs(distance_pct) < 2.0:
            distance_class = 'MODERATE'
        elif abs(distance_pct) < 5.0:
            distance_class = 'FAR'
        else:
            distance_class = 'VERY_FAR'
        
        # Calculate EMA slope (very long lookback for 800 EMA)
        ema_slope = (current_ema - ema_800[-20]) / ema_800[-20] * 100
        if ema_slope > 0.1:
            ema_trend = 'RISING'
        elif ema_slope < -0.1:
            ema_trend = 'FALLING'
        else:
            ema_trend = 'FLAT'
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'800 EMA: ${current_ema:.2f}')
        confluence_factors.append(f'Price vs EMA: {distance_pct:+.2f}%')
        confluence_factors.append(f'Distance: {distance_class}')
        confluence_factors.append(f'EMA Trend: {ema_trend}')
        confluence_factors.append('Macro cycle indicator (~3-year MA on daily)')
        confluence_factors.append('Major market regime change signal')
        
        if is_vector:
            confluence_factors.append('Vector candle detected (high volume + strong body)')
            confidence += 10
        
        if signal != 'NO_BREAK':
            if abs(distance_pct) < 1.0:
                confluence_factors.append('Clean break - extremely significant')
                confidence += 10
            
            if (signal == 'BULLISH_BREAK' and ema_trend == 'RISING') or \
               (signal == 'BEARISH_BREAK' and ema_trend == 'FALLING'):
                confluence_factors.append('Break aligns with macro EMA trend')
                confluence_factors.append('Potential Bitcoin cycle shift')
                confidence += 5
        
        # Metadata
        metadata = {
            'ema_800': round(current_ema, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'ema_trend': ema_trend,
            'is_vector': is_vector,
            'ema_slope': round(ema_slope, 4),
            'period_type': '3-year cycle equivalent on daily charts',
            'significance': 'EXTREME - Macro Bitcoin cycle analysis'
        }
        
        return {
            'signal': signal,
            'confidence': min(100, round(confidence, 2)),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
