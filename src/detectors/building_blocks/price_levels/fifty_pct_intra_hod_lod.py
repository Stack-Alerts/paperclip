"""
50%Intra-H-LOD (50% of Today's IHOD-ILOD Range) Building Block
Category: Price Levels
Purpose: TODAY's 50% equilibrium level (midpoint between today's high and low)

This is a dynamic intraday level representing today's fair value.
Updates throughout the day as new highs/lows are made.
"""

from typing import Dict, Any
from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='fifty_pct_intra_hod_lod',
    category='PRICE_LEVELS',
    class_name='FiftyPctIntraHODLOD',
    default_weight=18,
    valid_signals=[
        # Granular position signals
        'ABOVE_INTRA_EQ',         # Price above today's 50%
        'BELOW_INTRA_EQ',         # Price below today's 50%
        'AT_INTRA_EQ',            # Price at today's 50%
        'REJECTION_AT_INTRA_EQ',  # Rejected at today's equilibrium
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR'
    ],
    signal_tiers={
        'ABOVE_INTRA_EQ': {
            'base_points': 14,
            'formula': 'scaled'
        },
        'BELOW_INTRA_EQ': {
            'base_points': 14,
            'formula': 'scaled'
        },
        'AT_INTRA_EQ': {
            'base_points': 18,
            'formula': 'scaled'
        },
        'REJECTION_AT_INTRA_EQ': {
            'base_points': 18,
            'formula': 'scaled'
        },
        'NEUTRAL': {
            'points': 0
        },
        'ERROR': {
            'points': 0
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
            'base_points': 14,
            'formula': 'scaled'
        },
        'BEARISH': {
            'base_points': 14,
            'formula': 'scaled'
        }
    }
)
class FiftyPctIntraHODLOD:
    """
    50%Intra-H-LOD - Today's 50% Equilibrium Level (Intraday)
    
    Calculates the midpoint between TODAY's high and low SO FAR.
    This level represents current fair value for today's range.
    
    Key Differences from 50%H-LOD:
    - 50%H-LOD = Yesterday's 50% (static reference)
    - 50%Intra-H-LOD = Today's 50% (dynamic, updates intraday)
    
    Key Concepts:
    - IHOD = Today's high (so far)
    - ILOD = Today's low (so far)
    - 50% = (IHOD + ILOD) / 2
    
    Use Cases:
    - Intraday bias determination
    - Scalping pivot points
    - Mean reversion setups
    - Real-time fair value
    
    Signals:
    - ABOVE_INTRA_EQ: Bullish intraday bias
    - BELOW_INTRA_EQ: Bearish intraday bias
    - AT_INTRA_EQ: At fair value (mean reversion)
    - REJECTION_AT_INTRA_EQ: Rejected at equilibrium
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
        self.proximity_threshold = 0.15  # 0.15% proximity to equilibrium
        self.prev_fifty_pct = None
        
    def calculate_intra_fifty_pct(self, df: pd.DataFrame) -> tuple:
        """
        Calculate TODAY's 50% level (IHOD-ILOD midpoint)
        
        Returns:
            (fifty_pct_level, ihod, ilod) or (None, None, None)
        """
        if not all(col in df.columns for col in ['timestamp', 'high', 'low']):
            return None, None, None
        
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Filter for TODAY's data only
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None, None, None
        
        # Calculate TODAY's IHOD and ILOD (so far)
        ihod = float(today_data['high'].max())
        ilod = float(today_data['low'].min())
        
        # Calculate 50% level (dynamic, updates as day progresses)
        fifty_pct = (ihod + ilod) / 2.0
        
        return fifty_pct, ihod, ilod
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Analyze price relationship to today's 50% level"""
        
        # Validation
        if not all(col in df.columns for col in ['timestamp', 'high', 'low', 'close']):
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
        
        # Calculate intraday 50% level
        fifty_pct, ihod, ilod = self.calculate_intra_fifty_pct(df)
        
        if fifty_pct is None:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate intraday 50% level'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = ((current_price - fifty_pct) / fifty_pct) * 100
        
        # Determine signal
        if abs(distance_pct) < self.proximity_threshold:
            # At intraday equilibrium - high value signal
            signal = 'AT_INTRA_EQ'
            confidence = 85
        elif distance_pct > 0.5:
            signal = 'ABOVE_INTRA_EQ'
            confidence = 75
        elif distance_pct < -0.5:
            signal = 'BELOW_INTRA_EQ'
            confidence = 75
        else:
            signal = 'NEUTRAL'
            confidence = 60
        
        # Build description
        range_size = ihod - ilod
        position_in_range = ((current_price - ilod) / range_size) * 100 if range_size > 0 else 50
        
        # Track if equilibrium changed (dynamic level)
        eq_changed = False
        if self.prev_fifty_pct is not None and abs(fifty_pct - self.prev_fifty_pct) > 1.0:
            eq_changed = True
        
        self.prev_fifty_pct = fifty_pct
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'intra_fifty_pct': round(fifty_pct, 2),
                'today_ihod': round(ihod, 2),
                'today_ilod': round(ilod, 2),
                'current_price': round(current_price, 2),
                'distance_pct': round(distance_pct, 2),
                'position_in_range_pct': round(position_in_range, 2),
                'equilibrium_changed': eq_changed,
                'description': f"Today 50%: ${fifty_pct:.2f}, Price: ${current_price:.2f} ({distance_pct:+.2f}%, {position_in_range:.1f}% of intraday range)"
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe
        }


if __name__ == "__main__":
    print("="*80)
    print("50%INTRA-H-LOD (TODAY'S 50% EQUILIBRIUM) TEST")
    print("="*80)
    
    # Create intraday data
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    
    # Simulate expanding intraday range
    highs = 45000 + np.cumsum(np.random.uniform(-50, 100, 50))
    lows = highs - np.random.uniform(100, 300, 50)
    closes = lows + (highs - lows) * np.random.uniform(0.3, 0.7, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes,
        'open': closes,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    fifty_pct_intra = FiftyPctIntraHODLOD()
    result = fifty_pct_intra.analyze(data)
    
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Description: {result['metadata']['description']}")
    print(f"Today IHOD: ${result['metadata']['today_ihod']:.2f}")
    print(f"Today ILOD: ${result['metadata']['today_ilod']:.2f}")
    print(f"Intraday 50%: ${result['metadata']['intra_fifty_pct']:.2f}")
    print(f"Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"Position in Intraday Range: {result['metadata']['position_in_range_pct']:.1f}%")
    print(f"Equilibrium Changed: {result['metadata']['equilibrium_changed']}")
    print("="*80)
