"""
Balanced Price Range Building Block
Category: SMC/ICT
Purpose: Detect balanced price ranges - ICT equilibrium concept
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous fair value range state

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='balanced_price_range',
    category='SMC_ICT',
    class_name='BalancedPriceRange',
    default_weight=20,
    valid_signals=[
        # Granular position signals
        'IN_RANGE_LOW', 'IN_RANGE_HIGH', 'NOT_IN_RANGE',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Granular signals
        'IN_RANGE_LOW': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'IN_RANGE_HIGH': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'NOT_IN_RANGE': {
                'points': 0
        },
        # Simple directional
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'NEUTRAL': {
                'points': 0
        },
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        }
}
)
class BalancedPriceRange:
    """
    Balanced Price Range Detector - ICT/SMC Concept (ENHANCED 2026-01-04)
    
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
    
    ENHANCEMENTS (2026-01-04):
    - Compression Detection: Tracks range tightening over time
    - Volume Context: Monitors volume decrease during consolidation
    - Breakout Proximity: Estimates time until breakout based on history
    
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
        
        # ENHANCEMENT 3: Breakout Proximity (2026-01-04)
        self.range_history = []  # Track range durations
        self.max_history = 20
    
    def _determine_dual_signals(self, position_in_range: float, in_range: bool) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        if not in_range:
            granular = 'NOT_IN_RANGE'
            simple = 'NEUTRAL'
        elif position_in_range <= 50:
            granular = 'IN_RANGE_LOW'
            simple = 'BULLISH'
        else:
            granular = 'IN_RANGE_HIGH'
            simple = 'BEARISH'
        return granular, simple
    
    def detect_compression(self, df: pd.DataFrame, range_size: float) -> Dict[str, Any]:
        """
        ENHANCEMENT 1: Compression Detection (2026-01-04)
        Detect if range is tightening over time (coiling for breakout)
        """
        if len(df) < self.lookback:
            return {'has_compression': False}
        
        recent = df.tail(self.lookback)
        
        # Split into thirds to measure compression
        third = len(recent) // 3
        early_third = recent.iloc[:third]
        middle_third = recent.iloc[third:2*third]
        late_third = recent.iloc[2*third:]
        
        # Calculate range size for each third
        early_range = early_third['high'].max() - early_third['low'].min()
        middle_range = middle_third['high'].max() - middle_third['low'].min()
        late_range = late_third['high'].max() - late_third['low'].min()
        
        # Check for compression (range getting smaller)
        is_compressing = (late_range < middle_range < early_range)
        
        if is_compressing:
            compression_rate = ((early_range - late_range) / early_range * 100) if early_range > 0 else 0
            
            return {
                'has_compression': True,
                'compression_rate': round(compression_rate, 2),
                'early_range': float(early_range),
                'late_range': float(late_range),
                'compression_strength': 'STRONG' if compression_rate > 30 else 'MODERATE'
            }
        
        return {'has_compression': False}
    
    def analyze_volume_context(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ENHANCEMENT 2: Volume Context (2026-01-04)
        Analyze volume during consolidation (decreasing = true consolidation)
        """
        if 'volume' not in df.columns or len(df) < self.lookback:
            return {'has_volume_data': False}
        
        recent = df.tail(self.lookback)
        
        # Split into halves
        first_half = recent.iloc[:len(recent)//2]
        second_half = recent.iloc[len(recent)//2:]
        
        # Calculate average volumes
        first_half_vol = first_half['volume'].mean()
        second_half_vol = second_half['volume'].mean()
        
        # Check for volume decrease
        vol_decrease = ((first_half_vol - second_half_vol) / first_half_vol * 100) if first_half_vol > 0 else 0
        is_decreasing = second_half_vol < first_half_vol * 0.8  # 20% decrease
        
        # Compare to longer-term average
        if len(df) >= 50:
            long_term_vol = df.tail(50)['volume'].mean()
            is_below_average = second_half_vol < long_term_vol * 0.9
        else:
            is_below_average = False
        
        return {
            'has_volume_data': True,
            'is_volume_decreasing': is_decreasing,
            'volume_decrease_pct': round(vol_decrease, 2),
            'is_below_long_term_avg': is_below_average,
            'first_half_vol': float(first_half_vol),
            'second_half_vol': float(second_half_vol)
        }
    
    def estimate_breakout_proximity(self, bars_in_range: int) -> Dict[str, Any]:
        """
        ENHANCEMENT 3: Breakout Proximity (2026-01-04)
        Estimate when breakout might occur based on historical patterns
        """
        if len(self.range_history) < 5:
            return {
                'has_history': False,
                'bars_in_range': bars_in_range
            }
        
        # Calculate average range duration from history
        avg_duration = np.mean(self.range_history)
        std_duration = np.std(self.range_history)
        
        # Estimate breakout proximity
        if bars_in_range >= avg_duration * 1.5:
            proximity = 'IMMINENT'
        elif bars_in_range >= avg_duration:
            proximity = 'NEAR'
        elif bars_in_range >= avg_duration * 0.7:
            proximity = 'APPROACHING'
        else:
            proximity = 'EARLY'
        
        return {
            'has_history': True,
            'bars_in_range': bars_in_range,
            'avg_range_duration': round(avg_duration, 1),
            'std_range_duration': round(std_duration, 1),
            'breakout_proximity': proximity,
            'pct_of_avg_duration': round((bars_in_range / avg_duration * 100), 1) if avg_duration > 0 else 0
        }
    
    def detect_balanced_range(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect if price is in balanced range (ENHANCED 2026-01-04)"""
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
            
            # Legacy compression check (kept for backward compatibility)
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
        """Main analysis method - tracks both RANGE PRESENCE and NEW range entries"""
        if not all(col in df.columns for col in ['timestamp', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.lookback + 5:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.lookback + 5} bars', 'is_new_event': False},
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
                'metadata': {'message': 'No balanced range detected', 'is_new_event': False},
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
        
        # **NEW:** Event tracking - detect when range entered or signal changed
        is_new_event = False
        bars_in_range = 0
        range_just_ended = False
        
        # Check if we just entered range or signal changed
        if len(df) > self.lookback + 6:
            # Check previous bar's state
            prev_balanced = self.detect_balanced_range(df.iloc[:-1])
            
            if prev_balanced is None:
                # Just entered range (wasn't in range last bar, is now)
                is_new_event = True
            else:
                # Still in range - check if signal changed
                prev_signal = 'BULLISH' if prev_balanced['position_in_range'] <= 50 else 'BEARISH'
                is_new_event = (signal != prev_signal)
                
                # If continuing, approximate bars in range
                if not is_new_event:
                    bars_in_range = 1  # At least 1 bar in range
        
        # ENHANCEMENT 1: Detailed compression analysis
        compression_data = self.detect_compression(df, balanced['range_size'])
        
        # ENHANCEMENT 2: Volume analysis
        volume_data = self.analyze_volume_context(df)
        
        # ENHANCEMENT 3: Breakout proximity estimation
        proximity_data = self.estimate_breakout_proximity(bars_in_range)
        
        # Calculate confidence based on position in range and compression (ENHANCED)
        confidence = 60  # Base confidence
        
        # More extreme position = higher confidence
        position_extremity = abs(balanced['position_in_range'] - 50)
        if position_extremity > 30:  # Near edges (0-20% or 80-100%)
            confidence += 15
        elif position_extremity > 20:  # Moderately away from mid
            confidence += 10
        
        if balanced['is_compressing']:
            confidence += 10  # Compression = coiling for breakout
        
        # ENHANCEMENT BONUSES
        if compression_data.get('has_compression'):
            if compression_data['compression_strength'] == 'STRONG':
                confidence += 10
            else:
                confidence += 5
        
        if volume_data.get('has_volume_data'):
            if volume_data['is_volume_decreasing'] and volume_data['is_below_long_term_avg']:
                confidence += 10  # Strong consolidation confirmation
            elif volume_data['is_volume_decreasing']:
                confidence += 5
        
        if proximity_data.get('has_history'):
            if proximity_data['breakout_proximity'] == 'IMMINENT':
                confidence += 10  # Breakout likely soon
            elif proximity_data['breakout_proximity'] == 'NEAR':
                confidence += 5
        
        # Fresh event boost
        if is_new_event:
            confidence += 5
        confidence = min(100, confidence)
        
        # Build confluence factors (ENHANCED)
        confluence_factors = []
        
        # Event-specific confluence
        if is_new_event:
            if prev_balanced is None:
                confluence_factors.append('⭐ NEW BALANCED RANGE ENTRY (fresh consolidation zone!)')
            else:
                confluence_factors.append(f'⭐ RANGE POSITION SHIFT ({signal} half entry!)')
        elif bars_in_range > 0:
            confluence_factors.append(f'Continuing in balanced range ({bars_in_range} bars)')
        
        confluence_factors.append(f'Balanced Range: ${balanced["range_low"]:.2f} - ${balanced["range_high"]:.2f}')
        confluence_factors.append(f'Midpoint: ${balanced["range_mid"]:.2f}')
        confluence_factors.append(f'Position: {balanced["position_in_range"]:.1f}% ({bias})')
        confluence_factors.append(f'Balance Tightness: {balanced["avg_deviation"]:.1f}%')
        
        # ENHANCEMENT 1: Compression confluence
        if compression_data.get('has_compression'):
            confluence_factors.append(f'Compression: {compression_data["compression_strength"]} ({compression_data["compression_rate"]:.1f}% tighter) (+{10 if compression_data["compression_strength"]=="STRONG" else 5} confidence)')
        elif balanced['is_compressing']:
            confluence_factors.append('Range COMPRESSING - anticipate breakout')
        else:
            confluence_factors.append('Balanced consolidation - mean reversion')
        
        # ENHANCEMENT 2: Volume confluence
        if volume_data.get('has_volume_data'):
            if volume_data['is_volume_decreasing']:
                confluence_factors.append(f'Volume decreasing: {volume_data["volume_decrease_pct"]:.1f}% lower (confirms consolidation)')
            if volume_data['is_below_long_term_avg']:
                confluence_factors.append('Volume below average (true consolidation)')
        
        # ENHANCEMENT 3: Breakout proximity
        if proximity_data.get('has_history'):
            confluence_factors.append(f'Breakout proximity: {proximity_data["breakout_proximity"]} ({proximity_data["pct_of_avg_duration"]:.0f}% of avg duration)')
        
        confluence_factors.append('Institutional accumulation/distribution zone')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(balanced['position_in_range'], True)
        
        # Metadata (ENHANCED)
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
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
            'balance_timestamp': balanced['timestamp'],
            'is_new_event': is_new_event,
            'bars_in_range': bars_in_range,
            # ENHANCEMENTS
            'has_compression': compression_data.get('has_compression', False),
            'compression_strength': compression_data.get('compression_strength'),
            'compression_rate': compression_data.get('compression_rate'),
            'has_volume_data': volume_data.get('has_volume_data', False),
            'is_volume_decreasing': volume_data.get('is_volume_decreasing', False),
            'volume_decrease_pct': volume_data.get('volume_decrease_pct'),
            'breakout_proximity': proximity_data.get('breakout_proximity'),
            'pct_of_avg_duration': proximity_data.get('pct_of_avg_duration')
        }
        
        # Update range history for breakout proximity tracking
        if is_new_event and bars_in_range == 0:
            # Starting new range - will track duration
            pass
        elif prev_balanced is None and len(self.range_history) < self.max_history:
            # Range just ended - add duration to history
            if bars_in_range > 0:
                self.range_history.append(bars_in_range)
                if len(self.range_history) > self.max_history:
                    self.range_history.pop(0)
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
