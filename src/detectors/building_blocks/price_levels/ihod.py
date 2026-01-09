"""
IHOD (Intraday High of Day) Building Block
Category: Price Levels
Purpose: TODAY's highest price for intraday support/resistance

This block tracks the highest price reached SO FAR during the current trading day.
Differs from HOD which tracks YESTERDAY's high.
"""

from typing import Dict, Any
from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='ihod',
    category='PRICE_LEVELS',
    class_name='IHOD',
    default_weight=20,
    valid_signals=[
        'BULLISH_BREAK',      # Broke above previous IHOD
        'BEARISH_REJECTION',  # Rejected at IHOD  
        'AT_IHOD',           # Price at IHOD
        'BELOW_IHOD',        # Price below IHOD
        'ABOVE_IHOD',        # Price above IHOD (new IHOD)
        'NEUTRAL',
        'ERROR'
    ],
    signal_tiers={
        'BULLISH_BREAK': {
            'base_points': 22,
            'formula': 'scaled'
        },
        'BEARISH_REJECTION': {
            'base_points': 20,
            'formula': 'scaled'
        },
        'AT_IHOD': {
            'max_points': 15,
            'formula': 'scaled'
        },
        'BELOW_IHOD': {
            'max_points': 10,
            'formula': 'scaled'
        },
        'ABOVE_IHOD': {
            'max_points': 10,
            'formula': 'scaled'
        },
        'NEUTRAL': {
            'points': 0
        },
        'ERROR': {
            'points': 0
        }
    }
)
class IHOD:
    """
    IHOD - Intraday High of Day
    
    Tracks TODAY's highest price reached so far.
    
    Key Differences from HOD:
    - HOD = Yesterday's high (static reference)
    - IHOD = Today's high (dynamic, updates intraday)
    
    Use Cases:
    - Intraday breakout trading
    - Day trading resistance levels
    - Scalping range boundaries
    - Real-time resistance tracking
    
    Signals:
    - BULLISH_BREAK: New IHOD made (breakout)
    - BEARISH_REJECTION: Rejected at IHOD (reversal)
    - AT_IHOD: Price testing IHOD
    - BELOW_IHOD: Price below today's high
    - ABOVE_IHOD: Price at new high
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
        self.prev_ihod = None
        self.proximity_threshold = 0.15  # 0.15% = ~$67 on $45k BTC
        
    def calculate_ihod(self, df: pd.DataFrame) -> float:
        """Calculate INTRADAY High of Day (today's high so far)"""
        if 'timestamp' not in df.columns or 'high' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Filter for today's data only
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None
        
        # Return highest high SO FAR today (dynamic, updates as day progresses)
        return float(today_data['high'].max())
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Analyze IHOD level and price relationship"""
        
        # Validation
        if not all(col in df.columns for col in ['timestamp', 'high', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe
            }
        
        if len(df) < 5:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Insufficient data'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        # Calculate IHOD
        ihod = self.calculate_ihod(df)
        
        if ihod is None:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate IHOD'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = ((current_price - ihod) / ihod) * 100
        
        # Detect events
        is_new_ihod = False
        if self.prev_ihod is not None and ihod > self.prev_ihod:
            is_new_ihod = True
        
        # Determine signal
        if is_new_ihod and distance_pct > 0:
            signal = 'BULLISH_BREAK'
            confidence = 85
        elif abs(distance_pct) < self.proximity_threshold and distance_pct < 0:
            # At IHOD from below - rejection zone
            signal = 'BEARISH_REJECTION'
            confidence = 80
        elif abs(distance_pct) < self.proximity_threshold:
            signal = 'AT_IHOD'
            confidence = 70
        elif distance_pct < -0.5:
            signal = 'BELOW_IHOD'
            confidence = 60
        elif distance_pct > 0:
            signal = 'ABOVE_IHOD'
            confidence = 65
        else:
            signal = 'NEUTRAL'
            confidence = 50
        
        # Update tracking
        self.prev_ihod = ihod
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'ihod': round(ihod, 2),
                'current_price': round(current_price, 2),
                'distance_pct': round(distance_pct, 2),
                'is_new_ihod': is_new_ihod,
                'description': f"Today's high: ${ihod:.2f}, Price: ${current_price:.2f} ({distance_pct:+.2f}%)"
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe
        }


if __name__ == "__main__":
    # Test
    print("="*80)
    print("IHOD (INTRADAY HIGH OF DAY) TEST")
    print("="*80)
    
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    
    # Simulate intraday price action
    highs = 45000 + np.cumsum(np.random.uniform(-50, 100, 50))
    closes = highs - np.random.uniform(0, 50, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'close': closes,
        'open': closes - 20,
        'low': closes - 50,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    ihod = IHOD()
    result = ihod.analyze(data)
    
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Description: {result['metadata']['description']}")
    print(f"Is New IHOD: {result['metadata']['is_new_ihod']}")
    print("="*80)