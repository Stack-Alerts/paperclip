"""
ILOD (Intraday Low of Day) Building Block
Category: Price Levels
Purpose: TODAY's lowest price for intraday support/resistance

This block tracks the lowest price reached SO FAR during the current trading day.
Differs from LOD which tracks YESTERDAY's low.
"""

from typing import Dict, Any
from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='ilod',
    category='PRICE_LEVELS',
    class_name='ILOD',
    default_weight=20,
    valid_signals=[
        'BEARISH_BREAK',      # Broke below previous ILOD
        'BULLISH_BOUNCE',     # Bounced at ILOD
        'AT_ILOD',           # Price at ILOD
        'ABOVE_ILOD',        # Price above ILOD
        'BELOW_ILOD',        # Price below ILOD (new ILOD)
        'NEUTRAL',
        'ERROR'
    ],
    signal_tiers={
        'BEARISH_BREAK': {
            'base_points': 22,
            'formula': 'scaled'
        },
        'BULLISH_BOUNCE': {
            'base_points': 20,
            'formula': 'scaled'
        },
        'AT_ILOD': {
            'max_points': 15,
            'formula': 'scaled'
        },
        'ABOVE_ILOD': {
            'max_points': 10,
            'formula': 'scaled'
        },
        'BELOW_ILOD': {
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
class ILOD:
    """
    ILOD - Intraday Low of Day
    
    Tracks TODAY's lowest price reached so far.
    
    Key Differences from LOD:
    - LOD = Yesterday's low (static reference)
    - ILOD = Today's low (dynamic, updates intraday)
    
    Use Cases:
    - Intraday breakdown trading
    - Day trading support levels
    - Scalping range boundaries
    - Real-time support tracking
    
    Signals:
    - BEARISH_BREAK: New ILOD made (breakdown)
    - BULLISH_BOUNCE: Bounced at ILOD (reversal)
    - AT_ILOD: Price testing ILOD
    - ABOVE_ILOD: Price above today's low
    - BELOW_ILOD: Price at new low
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
        self.prev_ilod = None
        self.proximity_threshold = 0.15  # 0.15% = ~$67 on $45k BTC
        
    def calculate_ilod(self, df: pd.DataFrame) -> float:
        """Calculate INTRADAY Low of Day (today's low so far)"""
        if 'timestamp' not in df.columns or 'low' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Filter for today's data only
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None
        
        # Return lowest low SO FAR today (dynamic, updates as day progresses)
        return float(today_data['low'].min())
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Analyze ILOD level and price relationship"""
        
        # Validation
        if not all(col in df.columns for col in ['timestamp', 'low', 'close']):
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
        
        # Calculate ILOD
        ilod = self.calculate_ilod(df)
        
        if ilod is None:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate ILOD'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = ((current_price - ilod) / ilod) * 100
        
        # Detect events
        is_new_ilod = False
        if self.prev_ilod is not None and ilod < self.prev_ilod:
            is_new_ilod = True
        
        # Determine signal
        if is_new_ilod and distance_pct < 0:
            signal = 'BEARISH_BREAK'
            confidence = 85
        elif abs(distance_pct) < self.proximity_threshold and distance_pct > 0:
            # At ILOD from above - bounce zone
            signal = 'BULLISH_BOUNCE'
            confidence = 80
        elif abs(distance_pct) < self.proximity_threshold:
            signal = 'AT_ILOD'
            confidence = 70
        elif distance_pct > 0.5:
            signal = 'ABOVE_ILOD'
            confidence = 60
        elif distance_pct < 0:
            signal = 'BELOW_ILOD'
            confidence = 65
        else:
            signal = 'NEUTRAL'
            confidence = 50
        
        # Update tracking
        self.prev_ilod = ilod
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'ilod': round(ilod, 2),
                'current_price': round(current_price, 2),
                'distance_pct': round(distance_pct, 2),
                'is_new_ilod': is_new_ilod,
                'description': f"Today's low: ${ilod:.2f}, Price: ${current_price:.2f} ({distance_pct:+.2f}%)"
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe
        }


if __name__ == "__main__":
    # Test
    print("="*80)
    print("ILOD (INTRADAY LOW OF DAY) TEST")
    print("="*80)
    
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    
    # Simulate intraday price action
    lows = 45000 - np.cumsum(np.random.uniform(-50, 100, 50))
    closes = lows + np.random.uniform(0, 50, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'low': lows,
        'close': closes,
        'open': closes + 20,
        'high': closes + 50,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    ilod = ILOD()
    result = ilod.analyze(data)
    
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Description: {result['metadata']['description']}")
    print(f"Is New ILOD: {result['metadata']['is_new_ilod']}")
    print("="*80)