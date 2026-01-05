"""
LuxAlgo Swing Breakout Sequence - Core Implementation
===================================================

Swing breakout sequence detection: identifies failed breakout attempts
and anticipates successful third breakout with liquidity traps.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class BreakoutDirection(Enum):
    """Breakout direction classification."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NONE = 'none'


class SequenceStatus(Enum):
    """Sequence completion status."""
    INCOMPLETE = 'incomplete'
    COMPLETE = 'complete'
    FAILED = 'failed'


@dataclass
class SwingZone:
    """Identified swing high or low."""
    swing_type: str  # 'high' or 'low'
    swing_price: float
    bar_index: int
    timestamp: pd.Timestamp


@dataclass
class BreakoutPoint:
    """Breakout attempt in sequence."""
    point_number: int  # 1, 2, 3, 4, 5
    bar_index: int
    timestamp: pd.Timestamp
    price: float
    breakout_type: str  # 'high' or 'low'
    is_successful: bool  # Did it break through?


@dataclass
class SwingBreakoutSequence:
    """Complete 5-point swing breakout sequence."""
    point_1: BreakoutPoint  # First breakout attempt
    point_2: BreakoutPoint  # Pullback within zone
    point_3: BreakoutPoint  # Second breakout attempt
    point_4: BreakoutPoint  # Second pullback (optional)
    point_5: Optional[BreakoutPoint] = None  # Reversal pattern
    
    swing_zone: Optional[SwingZone] = None
    sequence_direction: BreakoutDirection = BreakoutDirection.NONE
    status: SequenceStatus = SequenceStatus.INCOMPLETE
    sequence_strength: float = 0.0  # 0-100
    
    # Trade setup
    expected_breakout_price: Optional[float] = None
    stop_loss_price: Optional[float] = None


class SwingHighLowDetector:
    """Detect swing highs and swing lows."""
    
    def __init__(self, swing_length: int = 5):
        """
        Initialize swing detector.
        
        Args:
            swing_length: Number of bars to confirm swing
        """
        self.swing_length = swing_length
    
    def detect_swings(self, df: pd.DataFrame) -> List[SwingZone]:
        """
        Detect all swing highs and lows.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            List of SwingZone objects
        """
        swings = []
        half_length = self.swing_length // 2
        
        for i in range(half_length, len(df) - half_length):
            # Check for swing high
            center_high = df.iloc[i]['high']
            left_range = df.iloc[i - half_length:i]['high'].max()
            right_range = df.iloc[i + 1:i + half_length + 1]['high'].max()
            
            if center_high >= left_range and center_high >= right_range:
                swings.append(SwingZone(
                    swing_type='high',
                    swing_price=center_high,
                    bar_index=i,
                    timestamp=df.index[i],
                ))
            
            # Check for swing low
            center_low = df.iloc[i]['low']
            left_range = df.iloc[i - half_length:i]['low'].min()
            right_range = df.iloc[i + 1:i + half_length + 1]['low'].min()
            
            if center_low <= left_range and center_low <= right_range:
                swings.append(SwingZone(
                    swing_type='low',
                    swing_price=center_low,
                    bar_index=i,
                    timestamp=df.index[i],
                ))
        
        return swings
    
    def find_nearest_swing(self, bar_index: int,
                          swings: List[SwingZone],
                          lookback: int = 50) -> Optional[SwingZone]:
        """
        Find nearest swing relative to bar index.
        
        Args:
            bar_index: Current bar
            swings: List of swings
            lookback: How far back to look
        
        Returns:
            Nearest swing or None
        """
        candidates = [s for s in swings 
                     if bar_index - lookback <= s.bar_index <= bar_index]
        
        if not candidates:
            return None
        
        return max(candidates, key=lambda s: abs(s.bar_index - bar_index))


class BreakoutDetector:
    """Detect breakout attempts and failures."""
    
    @staticmethod
    def detect_breakout(df: pd.DataFrame,
                       swing_zone: SwingZone,
                       lookforward_bars: int = 10) -> Optional[BreakoutPoint]:
        """
        Detect if price breaks out from swing zone.
        
        Args:
            df: OHLCV DataFrame
            swing_zone: Reference swing zone
            lookforward_bars: Bars to look forward
        
        Returns:
            BreakoutPoint if detected
        """
        # Find next bar that breaks the zone
        bar_idx = swing_zone.bar_index
        
        for i in range(bar_idx + 1, min(bar_idx + lookforward_bars, len(df))):
            bar = df.iloc[i]
            
            if swing_zone.swing_type == 'high':
                if bar['high'] > swing_zone.swing_price:
                    return BreakoutPoint(
                        point_number=0,
                        bar_index=i,
                        timestamp=df.index[i],
                        price=bar['high'],
                        breakout_type='high',
                        is_successful=True,
                    )
            else:  # low
                if bar['low'] < swing_zone.swing_price:
                    return BreakoutPoint(
                        point_number=0,
                        bar_index=i,
                        timestamp=df.index[i],
                        price=bar['low'],
                        breakout_type='low',
                        is_successful=True,
                    )
        
        return None
    
    @staticmethod
    def detect_pullback(df: pd.DataFrame,
                       breakout_point: BreakoutPoint,
                       swing_zone: SwingZone,
                       lookforward_bars: int = 20) -> Optional[BreakoutPoint]:
        """
        Detect pullback into swing zone after failed breakout.
        
        Args:
            df: OHLCV DataFrame
            breakout_point: Prior breakout attempt
            swing_zone: Reference swing zone
            lookforward_bars: Bars to look forward
        
        Returns:
            BreakoutPoint (pullback) if detected
        """
        start_idx = breakout_point.bar_index
        
        for i in range(start_idx + 1, min(start_idx + lookforward_bars, len(df))):
            bar = df.iloc[i]
            
            if swing_zone.swing_type == 'high':
                # Pullback means low went back into zone
                if bar['low'] < swing_zone.swing_price:
                    return BreakoutPoint(
                        point_number=0,
                        bar_index=i,
                        timestamp=df.index[i],
                        price=bar['low'],
                        breakout_type='low',
                        is_successful=False,
                    )
            else:  # low zone
                # Pullback means high went back into zone
                if bar['high'] > swing_zone.swing_price:
                    return BreakoutPoint(
                        point_number=0,
                        bar_index=i,
                        timestamp=df.index[i],
                        price=bar['high'],
                        breakout_type='high',
                        is_successful=False,
                    )
        
        return None


class ReversalPatternDetector:
    """Detect reversal patterns (double tops/bottoms)."""
    
    @staticmethod
    def detect_double_top_bottom(df: pd.DataFrame,
                                bar_index: int,
                                internal_length: int = 3,
                                threshold_pct: float = 1.0) -> Tuple[bool, str]:
        """
        Detect double top or double bottom pattern.
        
        Args:
            df: OHLCV DataFrame
            bar_index: Current bar
            internal_length: Bars to check for equal highs/lows
            threshold_pct: % threshold for "equal"
        
        Returns:
            Tuple of (is_pattern, pattern_type)
        """
        if bar_index < internal_length:
            return False, 'none'
        
        current_bar = df.iloc[bar_index]
        
        # Check recent highs
        recent_highs = df.iloc[max(0, bar_index - internal_length):bar_index]['high'].values
        if len(recent_highs) > 1:
            max_high = np.max(recent_highs)
            min_high = np.min(recent_highs)
            high_range_pct = ((max_high - min_high) / min_high) * 100
            
            if high_range_pct <= threshold_pct:
                return True, 'double_top'
        
        # Check recent lows
        recent_lows = df.iloc[max(0, bar_index - internal_length):bar_index]['low'].values
        if len(recent_lows) > 1:
            max_low = np.max(recent_lows)
            min_low = np.min(recent_lows)
            low_range_pct = ((max_low - min_low) / min_low) * 100
            
            if low_range_pct <= threshold_pct:
                return True, 'double_bottom'
        
        return False, 'none'


class SequenceBuilder:
    """Build complete swing breakout sequences."""
    
    @staticmethod
    def build_sequence(df: pd.DataFrame,
                      swing_zone: SwingZone,
                      require_point_4: bool = True,
                      require_point_5: bool = True) -> Optional[SwingBreakoutSequence]:
        """
        Build complete 5-point sequence.
        
        Args:
            df: OHLCV DataFrame
            swing_zone: Starting swing zone
            require_point_4: Require point 4 beyond point 2
            require_point_5: Require point 5 (reversal)
        
        Returns:
            Complete sequence or None
        """
        # Point 1: First breakout attempt
        point_1 = BreakoutDetector.detect_breakout(df, swing_zone, lookforward_bars=15)
        if not point_1:
            return None
        
        # Point 2: Pullback into zone
        point_2 = BreakoutDetector.detect_pullback(df, point_1, swing_zone, lookforward_bars=20)
        if not point_2:
            return None
        
        # Point 3: Second breakout attempt
        point_3 = BreakoutDetector.detect_breakout(df, swing_zone, lookforward_bars=20)
        if not point_3 or point_3.bar_index <= point_2.bar_index:
            return None
        
        # Point 4: Second pullback (optional)
        point_4 = None
        if require_point_4:
            point_4 = BreakoutDetector.detect_pullback(df, point_3, swing_zone, lookforward_bars=20)
            if not point_4:
                return None
            
            # Point 4 should go beyond Point 2
            if swing_zone.swing_type == 'high':
                if point_4.price >= point_2.price:
                    point_4 = None
            else:
                if point_4.price <= point_2.price:
                    point_4 = None
        
        # Point 5: Reversal pattern (optional)
        point_5 = None
        if require_point_5 and point_4:
            is_reversal, reversal_type = ReversalPatternDetector.detect_double_top_bottom(
                df, point_4.bar_index, internal_length=3
            )
            if is_reversal:
                point_5 = BreakoutPoint(
                    point_number=5,
                    bar_index=point_4.bar_index,
                    timestamp=df.index[point_4.bar_index],
                    price=point_4.price,
                    breakout_type=reversal_type,
                    is_successful=False,
                )
        
        # Determine direction
        if swing_zone.swing_type == 'high':
            direction = BreakoutDirection.BEARISH
            expected_breakout = swing_zone.swing_price * 0.99
            stop_loss = swing_zone.swing_price * 1.01
        else:
            direction = BreakoutDirection.BULLISH
            expected_breakout = swing_zone.swing_price * 1.01
            stop_loss = swing_zone.swing_price * 0.99
        
        # Calculate strength
        strength = SequenceBuilder._calculate_strength(point_1, point_2, point_3, point_4, point_5)
        
        sequence = SwingBreakoutSequence(
            point_1=point_1,
            point_2=point_2,
            point_3=point_3,
            point_4=point_4,
            point_5=point_5,
            swing_zone=swing_zone,
            sequence_direction=direction,
            status=SequenceStatus.COMPLETE if point_5 else SequenceStatus.INCOMPLETE,
            sequence_strength=strength,
            expected_breakout_price=expected_breakout,
            stop_loss_price=stop_loss,
        )
        
        return sequence
    
    @staticmethod
    def _calculate_strength(p1, p2, p3, p4, p5) -> float:
        """Calculate sequence strength 0-100."""
        strength = 50.0
        
        # Points 4 and 5 increase strength
        if p4:
            strength += 15
        if p5:
            strength += 20
        
        # Multiple failed breakouts increase strength
        strength += min(10, strength)  # Cap at reasonable value
        
        return min(100, max(0, strength))


class SwingBreakoutSequenceDetector:
    """Main swing breakout sequence detection engine."""
    
    def __init__(self, swing_length: int = 5,
                 internal_length: int = 3,
                 require_point_4: bool = True,
                 require_point_5: bool = True,
                 point_4_beyond_point_2: bool = True):
        """
        Initialize sequence detector.
        
        Args:
            swing_length: Bars to confirm swing
            internal_length: Bars for pattern detection
            require_point_4: Require point 4
            require_point_5: Require point 5 reversal
            point_4_beyond_point_2: Point 4 must exceed Point 2
        """
        self.swing_detector = SwingHighLowDetector(swing_length)
        self.internal_length = internal_length
        self.require_point_4 = require_point_4
        self.require_point_5 = require_point_5
        self.point_4_beyond_point_2 = point_4_beyond_point_2
    
    def analyze(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Detect all swing breakout sequences.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            Tuple of (DataFrame with analysis, results dict)
        """
        # Detect swings
        swings = self.swing_detector.detect_swings(df)
        
        # Build sequences
        sequences = []
        for swing in swings:
            seq = SequenceBuilder.build_sequence(
                df, swing,
                require_point_4=self.require_point_4,
                require_point_5=self.require_point_5
            )
            if seq:
                sequences.append(seq)
        
        # Create result DataFrame
        df_result = df.copy()
        df_result['sequence_point'] = 0
        df_result['sequence_type'] = ''
        df_result['in_zone'] = False
        
        for sequence in sequences:
            for point in [sequence.point_1, sequence.point_2, sequence.point_3, 
                         sequence.point_4, sequence.point_5]:
                if point and point.bar_index < len(df_result):
                    df_result.iloc[point.bar_index, 
                                  df_result.columns.get_loc('sequence_point')] = point.point_number
                    df_result.iloc[point.bar_index,
                                  df_result.columns.get_loc('sequence_type')] = sequence.sequence_direction.value
        
        return df_result, {
            'sequences': sequences,
            'total_sequences': len(sequences),
            'bullish_sequences': len([s for s in sequences 
                                     if s.sequence_direction == BreakoutDirection.BULLISH]),
            'bearish_sequences': len([s for s in sequences 
                                     if s.sequence_direction == BreakoutDirection.BEARISH]),
            'complete_sequences': len([s for s in sequences 
                                      if s.status == SequenceStatus.COMPLETE]),
            'swings': swings,
        }


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=200, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(200) * 0.2)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(200) * 0.1,
        'high': prices + np.abs(np.random.randn(200) * 0.3),
        'low': prices - np.abs(np.random.randn(200) * 0.3),
        'close': prices,
    }, index=dates)
    
    detector = SwingBreakoutSequenceDetector(
        swing_length=5,
        require_point_4=True,
        require_point_5=True
    )
    
    df_result, results = detector.analyze(df)
    
    print("=" * 70)
    print("SWING BREAKOUT SEQUENCE - ANALYSIS")
    print("=" * 70)
    
    print(f"\n✓ Total Sequences: {results['total_sequences']}")
    print(f"  Bullish: {results['bullish_sequences']}")
    print(f"  Bearish: {results['bearish_sequences']}")
    print(f"  Complete (with Point 5): {results['complete_sequences']}")
    
    if results['sequences']:
        print(f"\nMost Recent Sequence:")
        seq = results['sequences'][-1]
        print(f"  Direction: {seq.sequence_direction.value.upper()}")
        print(f"  Strength: {seq.sequence_strength:.0f}%")
        print(f"  Status: {seq.status.value}")
