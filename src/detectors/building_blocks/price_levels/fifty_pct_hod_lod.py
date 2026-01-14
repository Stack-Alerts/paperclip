"""
50%H-LOD (50% of Yesterday's HOD-LOD Range) Building Block
Category: Price Levels
Purpose: Yesterday's 50% equilibrium level (midpoint between yesterday's high and low)

This is a key institutional level representing yesterday's fair value.
"""

from typing import Dict, Any
from src.detectors.building_blocks.registry import register_block
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


@register_block(
    name='fifty_pct_hod_lod',
    category='PRICE_LEVELS',
    class_name='FiftyPctHODLOD',
    default_weight=18,
    valid_signals=[
        # Granular position signals
        'ABOVE_EQUILIBRIUM',      # Price above yesterday's 50%
        'BELOW_EQUILIBRIUM',      # Price below yesterday's 50%
        'AT_EQUILIBRIUM',         # Price at yesterday's 50%
        'REJECTION_AT_EQ',        # Rejected at equilibrium
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR'
    ],
    signal_tiers={
        'ABOVE_EQUILIBRIUM': {
            'base_points': 14,
            'formula': 'scaled'
        },
        'BELOW_EQUILIBRIUM': {
            'base_points': 14,
            'formula': 'scaled'
        },
        'AT_EQUILIBRIUM': {
            'base_points': 18,
            'formula': 'scaled'
        },
        'REJECTION_AT_EQ': {
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
class FiftyPctHODLOD:
    """
    50%H-LOD - Yesterday's 50% Equilibrium Level
    
    Calculates the midpoint between YESTERDAY's high and low.
    This level represents fair value from yesterday's range.
    
    Key Concepts:
    - HOD = Yesterday's high
    - LOD = Yesterday's low
    - 50% = (HOD + LOD) / 2
    
    Use Cases:
    - Daily bias determination
    - Mean reversion trading
    - Range trading pivot
    - Fair value reference
    
    Signals:
    - ABOVE_EQUILIBRIUM: Bullish bias (above yesterday's midpoint)
    - BELOW_EQUILIBRIUM: Bearish bias (below yesterday's midpoint)
    - AT_EQUILIBRIUM: At fair value (mean reversion setup)
    - REJECTION_AT_EQ: Rejected at equilibrium (reversal)
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
        self.proximity_threshold = 0.15  # 0.15% proximity to equilibrium
        self.prev_fifty_pct = None
    
    def _determine_dual_signals(self, distance_pct: float) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        # Granular: specific position relative to equilibrium
        if abs(distance_pct) < self.proximity_threshold:
            granular = 'AT_EQUILIBRIUM'
            simple = 'NEUTRAL'
        elif distance_pct > 0.5:
            granular = 'ABOVE_EQUILIBRIUM'
            simple = 'BULLISH'
        elif distance_pct < -0.5:
            granular = 'BELOW_EQUILIBRIUM'
            simple = 'BEARISH'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        
        return granular, simple
        
    def calculate_fifty_pct(self, df: pd.DataFrame) -> tuple:
        """
        Calculate yesterday's 50% level (HOD-LOD midpoint)
        
        Returns:
            (fifty_pct_level, hod, lod) or (None, None, None)
        """
        if not all(col in df.columns for col in ['timestamp', 'high', 'low']):
            return None, None, None
        
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Get yesterday's date
        yesterday_date = current_date - timedelta(days=1)
        
        # Filter for yesterday's data
        yesterday_data = df[df['timestamp'].dt.date == yesterday_date]
        
        if len(yesterday_data) == 0:
            # Try most recent previous day
            available_dates = df['timestamp'].dt.date.unique()
            available_dates = sorted([d for d in available_dates if d < current_date])
            
            if len(available_dates) == 0:
                return None, None, None
            
            prev_date = available_dates[-1]
            yesterday_data = df[df['timestamp'].dt.date == prev_date]
            
            if len(yesterday_data) == 0:
                return None, None, None
        
        # Calculate yesterday's HOD and LOD
        hod = float(yesterday_data['high'].max())
        lod = float(yesterday_data['low'].min())
        
        # Calculate 50% level
        fifty_pct = (hod + lod) / 2.0
        
        return fifty_pct, hod, lod
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Analyze price relationship to yesterday's 50% level"""
        
        # Validation
        if not all(col in df.columns for col in ['timestamp', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe
            }
        
        if len(df) < 10:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Insufficient data'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        # Calculate 50% level
        fifty_pct, hod, lod = self.calculate_fifty_pct(df)
        
        if fifty_pct is None:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate 50% level'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = ((current_price - fifty_pct) / fifty_pct) * 100
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(distance_pct)
        
        # Determine confidence
        if abs(distance_pct) < self.proximity_threshold:
            confidence = 85
        elif abs(distance_pct) > 0.5:
            confidence = 75
        else:
            confidence = 60
        
        # Build description
        range_size = hod - lod
        position_in_range = ((current_price - lod) / range_size) * 100 if range_size > 0 else 50
        
        return {
            'signal': granular_signal,  # Granular signal (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
            'confidence': confidence,
            'metadata': {
                'fifty_pct': round(fifty_pct, 2),
                'yesterday_hod': round(hod, 2),
                'yesterday_lod': round(lod, 2),
                'current_price': round(current_price, 2),
                'distance_pct': round(distance_pct, 2),
                'position_in_range_pct': round(position_in_range, 2),
                'description': f"Yesterday 50%: ${fifty_pct:.2f}, Price: ${current_price:.2f} ({distance_pct:+.2f}%, {position_in_range:.1f}% of range)",
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe
        }


if __name__ == "__main__":
    print("="*80)
    print("50%H-LOD (YESTERDAY'S 50% EQUILIBRIUM) TEST")
    print("="*80)
    
    # Create 2 days of data
    dates = pd.date_range(start='2024-01-01 00:00', periods=200, freq='15min')
    np.random.seed(42)
    
    highs = 45000 + np.random.uniform(-200, 500, 200)
    lows = highs - np.random.uniform(100, 300, 200)
    closes = lows + (highs - lows) * 0.5
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes,
        'open': closes,
        'volume': np.random.uniform(100, 1000, 200)
    })
    
    fifty_pct = FiftyPctHODLOD()
    result = fifty_pct.analyze(data)
    
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Description: {result['metadata']['description']}")
    print(f"Yesterday HOD: ${result['metadata']['yesterday_hod']:.2f}")
    print(f"Yesterday LOD: ${result['metadata']['yesterday_lod']:.2f}")
    print(f"50% Level: ${result['metadata']['fifty_pct']:.2f}")
    print(f"Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"Position in Range: {result['metadata']['position_in_range_pct']:.1f}%")
    print("="*80)
