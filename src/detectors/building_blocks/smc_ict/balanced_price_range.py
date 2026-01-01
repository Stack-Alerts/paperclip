"""
Balanced Price Range Building Block
Category: SMC/ICT
Purpose: Detect balanced price ranges - ICT equilibrium concept
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class BalancedPriceRange:
    """
    Balanced Price Range Detector - ICT/SMC Concept
    
    Identifies when price is in a balanced, consolidating range where
    neither bulls nor bears have control. These ranges often precede
    major moves as institutions accumulate positions.
    
    Balanced Range Characteristics:
    - Price oscillates around midpoint
    - Equal highs and lows (balance)
    - Low volatility consolidation
    - Precedes expansion/breakout
    
    Trading Application:
    - Anticipate breakout direction
    - Trade mean reversion within range
    - Wait for directional move
    
    Parameters:
        lookback: Periods for range detection (default: 20)
        balance_threshold: Max % deviation from midpoint (default: 5%)
    """
    
    def __init__(self, timeframe: str = '15min',
                 lookback: int = 20,
                 balance_threshold: float = 15.0, **kwargs):
        """
        Initialize Balanced Price Range detector
        
        CRITICAL FIX: Increased default balance_threshold from 5% to 15%
        Bitcoin is volatile - perfect balance (5%) extremely rare
        15% allows detection of consolidation ranges in volatile markets
        """
        self.timeframe = timeframe
        self.lookback = lookback
        self.balance_threshold = balance_threshold
    
    def detect_balanced_range(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect if price is in balanced range"""
        if len(df) < self.lookback:
            return None
        
        recent = df.tail(self.lookback)
        
        # Calculate range
        range_high = float(recent['high'].max())
        range_low = float(recent['low'].min())
        range_mid = (range_high + range_low) / 2
        range_size = range_high - range_low
        
        if range_size == 0:
            return None
        
        # Check if price oscillates around midpoint
        closes = recent['close'].values
        deviations_from_mid = [(c - range_mid) / range_size * 100 for c in closes]
        avg_deviation = np.mean(np.abs(deviations_from_mid))
        
        # Check balance
        is_balanced = avg_deviation <= self.balance_threshold
        
        if is_balanced:
            # Calculate additional metrics
            current_price = float(df['close'].iloc[-1])
            position_in_range = ((current_price - range_low) / range_size) * 100 if range_size > 0 else 50
            
            # Detect compression (tightening range)
            first_half = recent.iloc[:len(recent)//2]
            second_half = recent.iloc[len(recent)//2:]
            
            first_half_range = first_half['high'].max() - first_half['low'].min()
            second_half_range = second_half['high'].max() - second_half['low'].min()
            
            is_compressing = second_half_range < first_half_range * 0.8
            
            return {
                'type': 'BALANCED_RANGE',
                'range_high': range_high,
                'range_low': range_low,
                'range_mid': range_mid,
                'range_size': range_size,
                'current_price': current_price,
                'position_in_range': round(position_in_range, 2),
                'avg_deviation': round(avg_deviation, 2),
                'is_compressing': is_compressing,
                'timestamp': df['timestamp'].iloc[-1]
            }
        
        return None
    
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
        
        if len(df) < self.lookback + 5:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.lookback + 5} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect balanced range
        balanced = self.detect_balanced_range(df)
        
        if not balanced:
            return {
                'signal': 'NEUTRAL',
                'confidence': 0,
                'metadata': {'message': 'No balanced range detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['Not in balanced range - trending or expanding']
            }
        
        # Determine signal based on position in range
        # CRITICAL FIX: Always generate directional signal (no NEUTRAL at mid)
        if balanced['position_in_range'] <= 50:
            signal = 'BULLISH'  # Low half of range = bullish bias
            bias = 'Buy low in range'
        else:
            signal = 'BEARISH'  # High half of range = bearish bias
            bias = 'Sell high in range'
        
        # Calculate confidence based on position in range and compression
        confidence = 60  # Base confidence
        
        # More extreme position = higher confidence
        position_extremity = abs(balanced['position_in_range'] - 50)
        if position_extremity > 30:  # Near edges (0-20% or 80-100%)
            confidence += 15
        elif position_extremity > 20:  # Moderately away from mid
            confidence += 10
        
        if balanced['is_compressing']:
            confidence += 10  # Compression = coiling for breakout
        
        confidence = min(100, confidence)
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'Balanced Range: ${balanced["range_low"]:.2f} - ${balanced["range_high"]:.2f}')
        confluence_factors.append(f'Midpoint: ${balanced["range_mid"]:.2f}')
        confluence_factors.append(f'Position: {balanced["position_in_range"]:.1f}% ({bias})')
        confluence_factors.append(f'Balance Tightness: {balanced["avg_deviation"]:.1f}%')
        
        if balanced['is_compressing']:
            confluence_factors.append('Range COMPRESSING - anticipate breakout')
        else:
            confluence_factors.append('Balanced consolidation - mean reversion')
        
        confluence_factors.append('Institutional accumulation/distribution zone')
        
        # Metadata
        metadata = {
            'range_type': balanced['type'],
            'range_high': balanced['range_high'],
            'range_low': balanced['range_low'],
            'range_mid': balanced['range_mid'],
            'range_size': balanced['range_size'],
            'current_price': balanced['current_price'],
            'position_in_range': balanced['position_in_range'],
            'avg_deviation': balanced['avg_deviation'],
            'is_compressing': balanced['is_compressing'],
            'bias': bias,
            'balance_timestamp': balanced['timestamp']
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
