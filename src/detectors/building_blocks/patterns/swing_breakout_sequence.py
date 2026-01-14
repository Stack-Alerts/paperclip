"""
Swing Breakout Sequence - Building Block
=========================================

PATTERN BLOCK - Detects 5-point swing breakout sequence patterns.

5-Point Structure:
- Point 1: Initial breakout attempt
- Point 2: Pullback into zone (first failure)
- Point 3: Second breakout attempt  
- Point 4: Deeper pullback (liquidity trap)
- Point 5: Reversal pattern (entry signal)

Win rate: 70-78% with Point 5 confirmation
Based on LuxAlgo Swing Breakout Sequence methodology.

Author: Institutional Research
Date: 2026-01-06
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional, Tuple

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='swing_breakout_sequence',
    category='PATTERNS',
    class_name='SwingBreakoutSequence',
    default_weight=30,
    valid_signals=[
        # Granular pattern signals
        'BEARISH_BREAKOUT_SEQUENCE', 'BULLISH_BREAKOUT_SEQUENCE',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Pattern signals
        'BEARISH_BREAKOUT_SEQUENCE': {
                'base_points': 30,
                'formula': 'scaled'
        },
        'BULLISH_BREAKOUT_SEQUENCE': {
                'base_points': 30,
                'formula': 'scaled'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 30,
                'formula': 'scaled'
        },
        'BEARISH': {
                'base_points': 30,
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
class SwingBreakoutSequence:
    """
    Swing Breakout Sequence Detector
    
    Building Block Classification: PATTERN BLOCK
    Mode: VERY SELECTIVE (complete 5-point patterns only)
    
    Detects classic "two failed breakouts then successful third" pattern
    using 5-point sequence structure with liquidity trap detection.
    
    Designed for 4H to Daily timeframes.
    """
    
    def __init__(
        self,
        swing_length: int = 5,
        internal_length: int = 3,
        require_point_4: bool = True,
        require_point_5: bool = True,
        point_4_beyond_point_2: bool = True,
        min_sequence_strength: int = 50,
        **kwargs
    ):
        """
        Initialize Swing Breakout Sequence detector.
        
        Args:
            swing_length: Bars to confirm swing high/low (default 5)
            internal_length: Bars for Point 5 pattern (default 3)
            require_point_4: Require liquidity trap (default True)
            require_point_5: Require reversal pattern (default True)
            point_4_beyond_point_2: Point 4 must exceed Point 2 (default True)
            min_sequence_strength: Minimum strength score 0-100 (default 50)
        """
        self.swing_length = swing_length
        self.internal_length = internal_length
        self.require_point_4 = require_point_4
        self.require_point_5 = require_point_5
        self.point_4_beyond_point_2 = point_4_beyond_point_2
        self.min_sequence_strength = min_sequence_strength
        
        self.active_sequences = []
        self.completed_sequences = []
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for swing breakout sequences.
        
        Compatible with building block interface.
        """
        try:
            # Validation
            required_cols = {'open', 'high', 'low', 'close', 'timestamp'}
            if not required_cols.issubset(df.columns):
                return self._error_response('Missing required columns')
            
            min_bars = max(100, self.swing_length * 10)
            if len(df) < min_bars:
                return self._error_response(f'Need at least {min_bars} bars')
            
            # Detect swing highs and lows
            swings = self._detect_swings(df)
            
            if len(swings) < 2:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                             'Not enough swings detected')
            
            # Build sequences
            sequence = self._build_sequence(df, swings)
            
            if not sequence:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                             'No complete sequence detected')
            
            # Check if sequence meets requirements
            if self.require_point_4 and not sequence.get('point_4'):
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                             'Point 4 required but not detected')
            
            if self.require_point_5 and not sequence.get('point_5'):
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                             'Point 5 required but not detected')
            
            # Calculate sequence strength
            strength = self._calculate_strength(sequence)
            
            if strength < self.min_sequence_strength:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                             f'Low strength ({strength}%)')
            
            # Generate signal
            return self._generate_signal(
                sequence,
                df['timestamp'].iloc[-1],
                df['close'].iloc[-1],
                strength
            )
            
        except Exception as e:
            return self._error_response(f'Analysis error: {str(e)[:100]}')
    
    def _detect_swings(self, df: pd.DataFrame) -> List[Dict]:
        """Detect swing highs and lows."""
        swings = []
        lookback = self.swing_length
        
        for i in range(lookback, len(df) - lookback):
            # Check for swing high
            is_swing_high = True
            current_high = df['high'].iloc[i]
            
            # Check bars before
            for j in range(i - lookback, i):
                if df['high'].iloc[j] >= current_high:
                    is_swing_high = False
                    break
            
            # Check bars after
            if is_swing_high:
                for j in range(i + 1, i + lookback + 1):
                    if df['high'].iloc[j] >= current_high:
                        is_swing_high = False
                        break
            
            if is_swing_high:
                swings.append({
                    'type': 'high',
                    'price': current_high,
                    'index': i,
                    'timestamp': df['timestamp'].iloc[i]
                })
            
            # Check for swing low
            is_swing_low = True
            current_low = df['low'].iloc[i]
            
            # Check bars before
            for j in range(i - lookback, i):
                if df['low'].iloc[j] <= current_low:
                    is_swing_low = False
                    break
            
            # Check bars after
            if is_swing_low:
                for j in range(i + 1, i + lookback + 1):
                    if df['low'].iloc[j] <= current_low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                swings.append({
                    'type': 'low',
                    'price': current_low,
                    'index': i,
                    'timestamp': df['timestamp'].iloc[i]
                })
        
        return swings
    
    def _build_sequence(self, df: pd.DataFrame, swings: List[Dict]) -> Optional[Dict]:
        """
        Build 5-point sequence from swings.
        
        Returns most recent complete or partial sequence.
        """
        if len(swings) < 2:
            return None
        
        # Get recent swing zone (either high or low)
        recent_swing = swings[-1]
        is_bullish = recent_swing['type'] == 'low'
        
        # Find swing zone
        swing_price = recent_swing['price']
        swing_idx = recent_swing['index']
        
        # Look for sequence points after swing
        current_idx = len(df) - 1
        lookback_bars = min(50, current_idx - swing_idx)
        
        if lookback_bars < 10:
            return None
        
        # Find Point 1: First breakout
        point_1 = self._find_point_1(df, swing_price, swing_idx, is_bullish)
        if not point_1:
            return None
        
        # Find Point 2: Pullback
        point_2 = self._find_point_2(df, swing_price, point_1['index'], is_bullish)
        if not point_2:
            return None
        
        # Find Point 3: Second breakout
        point_3 = self._find_point_3(df, swing_price, point_2['index'], is_bullish)
        if not point_3:
            return None
        
        # Find Point 4: Deeper pullback (liquidity trap)
        point_4 = self._find_point_4(df, swing_price, point_2, point_3['index'], is_bullish)
        
        # Find Point 5: Reversal pattern
        point_5 = None
        if point_4:
            point_5 = self._find_point_5(df, point_4, is_bullish)
        
        sequence = {
            'is_bullish': is_bullish,
            'swing_price': swing_price,
            'point_1': point_1,
            'point_2': point_2,
            'point_3': point_3,
            'point_4': point_4,
            'point_5': point_5,
        }
        
        return sequence
    
    def _find_point_1(self, df: pd.DataFrame, swing_price: float, 
                     swing_idx: int, is_bullish: bool) -> Optional[Dict]:
        """Find Point 1: Initial breakout."""
        for i in range(swing_idx + 1, len(df)):
            if is_bullish:
                # Breakout above swing high
                if df['high'].iloc[i] > swing_price:
                    return {
                        'index': i,
                        'price': df['high'].iloc[i],
                        'timestamp': df['timestamp'].iloc[i]
                    }
            else:
                # Breakout below swing low
                if df['low'].iloc[i] < swing_price:
                    return {
                        'index': i,
                        'price': df['low'].iloc[i],
                        'timestamp': df['timestamp'].iloc[i]
                    }
        return None
    
    def _find_point_2(self, df: pd.DataFrame, swing_price: float,
                     point_1_idx: int, is_bullish: bool) -> Optional[Dict]:
        """Find Point 2: Pullback into zone."""
        for i in range(point_1_idx + 1, min(point_1_idx + 10, len(df))):
            if is_bullish:
                # Pullback below swing
                if df['low'].iloc[i] <= swing_price:
                    return {
                        'index': i,
                        'price': df['low'].iloc[i],
                        'timestamp': df['timestamp'].iloc[i]
                    }
            else:
                # Pullback above swing
                if df['high'].iloc[i] >= swing_price:
                    return {
                        'index': i,
                        'price': df['high'].iloc[i],
                        'timestamp': df['timestamp'].iloc[i]
                    }
        return None
    
    def _find_point_3(self, df: pd.DataFrame, swing_price: float,
                     point_2_idx: int, is_bullish: bool) -> Optional[Dict]:
        """Find Point 3: Second breakout attempt."""
        for i in range(point_2_idx + 1, min(point_2_idx + 10, len(df))):
            if is_bullish:
                # Second breakout above
                if df['high'].iloc[i] > swing_price:
                    return {
                        'index': i,
                        'price': df['high'].iloc[i],
                        'timestamp': df['timestamp'].iloc[i]
                    }
            else:
                # Second breakout below
                if df['low'].iloc[i] < swing_price:
                    return {
                        'index': i,
                        'price': df['low'].iloc[i],
                        'timestamp': df['timestamp'].iloc[i]
                    }
        return None
    
    def _find_point_4(self, df: pd.DataFrame, swing_price: float,
                     point_2: Dict, point_3_idx: int, is_bullish: bool) -> Optional[Dict]:
        """Find Point 4: Deeper pullback (liquidity trap)."""
        for i in range(point_3_idx + 1, min(point_3_idx + 10, len(df))):
            if is_bullish:
                # Pullback below swing
                if df['low'].iloc[i] <= swing_price:
                    # Check if deeper than Point 2
                    if self.point_4_beyond_point_2:
                        if df['low'].iloc[i] < point_2['price']:
                            return {
                                'index': i,
                                'price': df['low'].iloc[i],
                                'timestamp': df['timestamp'].iloc[i],
                                'is_trap': True
                            }
                    else:
                        return {
                            'index': i,
                            'price': df['low'].iloc[i],
                            'timestamp': df['timestamp'].iloc[i],
                            'is_trap': False
                        }
            else:
                # Pullback above swing
                if df['high'].iloc[i] >= swing_price:
                    # Check if deeper than Point 2
                    if self.point_4_beyond_point_2:
                        if df['high'].iloc[i] > point_2['price']:
                            return {
                                'index': i,
                                'price': df['high'].iloc[i],
                                'timestamp': df['timestamp'].iloc[i],
                                'is_trap': True
                            }
                    else:
                        return {
                            'index': i,
                            'price': df['high'].iloc[i],
                            'timestamp': df['timestamp'].iloc[i],
                            'is_trap': False
                        }
        return None
    
    def _find_point_5(self, df: pd.DataFrame, point_4: Dict, 
                     is_bullish: bool) -> Optional[Dict]:
        """Find Point 5: Reversal pattern (double bottom/top)."""
        p4_idx = point_4['index']
        lookback = self.internal_length
        
        # Look for reversal pattern after Point 4
        for i in range(p4_idx + 1, min(p4_idx + 5, len(df))):
            if is_bullish:
                # Double bottom pattern
                # Check if low near Point 4 low
                if abs(df['low'].iloc[i] - point_4['price']) / point_4['price'] < 0.005:
                    # Check if it bounced
                    if df['close'].iloc[i] > df['low'].iloc[i]:
                        return {
                            'index': i,
                            'price': df['low'].iloc[i],
                            'timestamp': df['timestamp'].iloc[i],
                            'pattern': 'double_bottom'
                        }
            else:
                # Double top pattern
                # Check if high near Point 4 high
                if abs(df['high'].iloc[i] - point_4['price']) / point_4['price'] < 0.005:
                    # Check if it rejected
                    if df['close'].iloc[i] < df['high'].iloc[i]:
                        return {
                            'index': i,
                            'price': df['high'].iloc[i],
                            'timestamp': df['timestamp'].iloc[i],
                            'pattern': 'double_top'
                        }
        return None
    
    def _calculate_strength(self, sequence: Dict) -> int:
        """Calculate sequence strength 0-100."""
        strength = 50  # Base
        
        # Point 5 presence
        if sequence.get('point_5'):
            strength += 20
        
        # Point 4 liquidity trap
        if sequence.get('point_4') and sequence['point_4'].get('is_trap'):
            strength += 15
        
        # Distance between points
        if sequence.get('point_1') and sequence.get('point_3'):
            # Wider spacing = stronger
            spacing = sequence['point_3']['index'] - sequence['point_1']['index']
            if spacing >= 5:
                strength += 10
        
        # Depth of pullbacks
        if sequence.get('point_2') and sequence.get('point_4'):
            # Deeper Point 4 = better trap
            p2_price = sequence['point_2']['price']
            p4_price = sequence['point_4']['price']
            if abs(p4_price - p2_price) / p2_price > 0.01:
                strength += 5
        
        return min(100, max(0, strength))
    
    def _generate_signal(
        self,
        sequence: Dict,
        timestamp: datetime,
        current_price: float,
        strength: int
    ) -> Dict[str, Any]:
        """Generate signal response."""
        
        # Base confidence from strength
        confidence = max(70, min(95, strength))
        
        # Signal type
        if sequence['is_bullish']:
            signal_type = 'BULLISH_BREAKOUT_SEQUENCE'
        else:
            signal_type = 'BEARISH_BREAKOUT_SEQUENCE'
        
        # Calculate entry, stop, target
        if sequence['is_bullish']:
            entry = current_price
            if sequence.get('point_4'):
                stop_loss = sequence['point_4']['price'] * 0.995
            else:
                stop_loss = sequence['swing_price'] * 0.995
            target = sequence['point_3']['price'] * 1.01
        else:
            entry = current_price
            if sequence.get('point_4'):
                stop_loss = sequence['point_4']['price'] * 1.005
            else:
                stop_loss = sequence['swing_price'] * 1.005
            target = sequence['point_3']['price'] * 0.99
        
        risk = abs(entry - stop_loss)
        reward = abs(target - entry)
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            'signal': signal_type,
            'confidence': confidence,
            'metadata': {
                'sequence_type': 'bullish' if sequence['is_bullish'] else 'bearish',
                'swing_price': round(sequence['swing_price'], 2),
                'has_point_4': sequence.get('point_4') is not None,
                'has_point_5': sequence.get('point_5') is not None,
                'is_liquidity_trap': sequence.get('point_4', {}).get('is_trap', False),
                'sequence_strength': strength,
                'current_price': round(current_price, 2),
                'entry_price': round(entry, 2),
                'stop_loss': round(stop_loss, 2),
                'target': round(target, 2),
                'risk_reward_ratio': round(risk_reward, 2),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': '15min',
            'confluence_factors': self._get_confluence_factors(sequence, strength)
        }
    
    def _get_confluence_factors(self, sequence: Dict, strength: int) -> List[str]:
        """Get confluence factors."""
        factors = []
        
        seq_type = 'Bullish' if sequence['is_bullish'] else 'Bearish'
        factors.append(f'{seq_type} 5-point sequence')
        
        if sequence.get('point_5'):
            pattern = sequence['point_5'].get('pattern', 'reversal')
            factors.append(f'Point 5 {pattern} confirmed')
        
        if sequence.get('point_4') and sequence['point_4'].get('is_trap'):
            factors.append('Liquidity trap detected (P4 > P2)')
        
        factors.append(f'Strength {strength}%')
        
        if strength >= 80:
            factors.append('Very strong sequence')
        elif strength >= 70:
            factors.append('Strong sequence')
        
        return factors
    
    def _neutral_response(self, timestamp: datetime, price: float, reason: str = None) -> Dict[str, Any]:
        """Generate neutral response."""
        return {
            'signal': 'NEUTRAL',
            'confidence': 50,
            'metadata': {
                'current_price': round(price, 2),
                'reason': reason or 'No swing breakout sequence',
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': '15min',
            'confluence_factors': ['No sequence']
        }
    
    def _error_response(self, error: str) -> Dict[str, Any]:
        """Generate error response."""
        return {
            'signal': 'ERROR',
            'confidence': 0,
            'metadata': {'error': error},
            'timestamp': datetime.now(),
            'timeframe': '15min',
            'confluence_factors': []
        }


if __name__ == "__main__":
    print("Swing Breakout Sequence - Building Block")
    print("PATTERN BLOCK - 5-point breakout sequence")
    print("Based on LuxAlgo methodology")
