"""
Zigzag Detector - Structural Pivot Detection

Replicates TradingView's ta.pivothigh() and ta.pivotlow() logic.
Unlike scipy.find_peaks, this requires confirmation bars on BOTH sides.

Key Differences from Simple Peak Detection:
-------------------------------------------
1. Requires LENGTH bars on EACH SIDE for confirmation
2. Tracks ghost levels (missed reversals that become support/resistance)
3. Builds structural pattern sequences (HH/LH/HL/LL)
4. No false positives from noise

TradingView Reference: pivot_points_detector.pine

Author: BTC_Engine_v3
Date: December 30, 2025
"""

from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
from enum import Enum


class PivotType(Enum):
    """Pivot type enumeration"""
    HIGH = 'H'
    LOW = 'L'


class PatternDirection(Enum):
    """Pattern direction for sequence analysis"""
    HIGHER_HIGH = 'HH'
    LOWER_HIGH = 'LH'
    HIGHER_LOW = 'HL'
    LOWER_LOW = 'LL'


@dataclass
class Pivot:
    """
    Structural pivot point.
    
    A pivot is a bar that is highest/lowest within LENGTH bars on EACH side.
    This is fundamentally different from simple local maxima.
    
    Attributes:
        index: Bar index in the data
        timestamp: Timestamp of the pivot bar
        price: Pivot price (high for pivot high, low for pivot low)
        pivot_type: 'H' for high, 'L' for low
        confirmed_at: Bar index where pivot was confirmed (index + length)
        oscillator_value: RSI/CCI value at pivot (for divergence)
    """
    index: int
    timestamp: pd.Timestamp
    price: float
    pivot_type: PivotType
    confirmed_at: int
    oscillator_value: Optional[float] = None
    
    def __repr__(self) -> str:
        return (f"Pivot({self.pivot_type.value} @ {self.timestamp.strftime('%Y-%m-%d %H:%M')}, "
                f"price=${self.price:.2f}, confirmed={self.confirmed_at})")


@dataclass
class GhostLevel:
    """
    Missed pivot (potential reversal that didn't confirm).
    
    Ghost levels are important because they often act as support/resistance.
    When price approaches a ghost level, it may bounce or reject.
    
    Attributes:
        index: Bar index where ghost was identified
        price: Price level
        level_type: 'resistance' (from missed high) or 'support' (from missed low)
        strength: How close it came to being a pivot (0.0-1.0)
    """
    index: int
    timestamp: pd.Timestamp
    price: float
    level_type: str  # 'resistance' or 'support'
    strength: float = 0.5
    
    def __repr__(self) -> str:
        return (f"Ghost({self.level_type} @ ${self.price:.2f}, "
                f"strength={self.strength:.2f})")


class ZigzagDetector:
    """
    Zigzag detector using TradingView methodology.
    
    This detector finds structural pivots that require confirmation,
    unlike simple peak detection which finds noisy local maxima.
    
    Key Concepts:
    -------------
    1. Pivot Confirmation: Requires LENGTH bars on EACH side
       - Total window: 2*LENGTH+1 bars
       - Example: length=50 needs 101-bar window
       - Pivot at index i is only confirmed at index i+LENGTH
    
    2. Ghost Levels: Potential pivots that didn't confirm
       - Still important as support/resistance
       - Track for risk management
    
    3. Pattern Sequences: HH/LH/HL/LL tracking
       - Used for trend identification
       - Critical for statistical matching
    
    Reference:
    ----------
    TradingView: ta.pivothigh(length, length) and ta.pivotlow(length, length)
    Script: TradingView_Scripts/pivot_points_detector.pine
    
    Example:
    --------
    >>> detector = ZigzagDetector(length=50, threshold_percent=2.0)
    >>> pivots = detector.find_pivots(df)
    >>> print(f"Found {len(pivots)} structural pivots")
    >>> sequence = detector.get_pattern_sequence()
    >>> print(f"Last 5 patterns: {sequence[-5:]}")
    """
    
    def __init__(
        self, 
        length: int = 50, 
        threshold_percent: float = 2.0,
        track_ghosts: bool = True
    ):
        """
        Initialize zigzag detector.
        
        Args:
            length: Bars required on each side for pivot confirmation (default: 50)
                   Higher = fewer, stronger pivots
                   Lower = more, weaker pivots
            threshold_percent: Minimum % move to consider (optional filter, default: 2.0)
                              Set to 0.0 to disable
            track_ghosts: Whether to track ghost levels (default: True)
        """
        self.length = length
        self.threshold = threshold_percent / 100.0
        self.track_ghosts = track_ghosts
        
        # Storage
        self.pivots: List[Pivot] = []
        self.ghost_levels: List[GhostLevel] = []
        
        # Statistics
        self.total_bars_analyzed: int = 0
        self.pivot_high_count: int = 0
        self.pivot_low_count: int = 0
        self.ghost_count: int = 0
    
    def find_pivots(
        self, 
        data: pd.DataFrame,
        oscillator_data: Optional[pd.Series] = None
    ) -> List[Pivot]:
        """
        Find all confirmed structural pivots in data.
        
        This is the main method that scans data for pivot points.
        
        Args:
            data: DataFrame with 'high', 'low', 'close' columns and DatetimeIndex
            oscillator_data: Optional oscillator values (RSI, CCI, etc.) for divergence
        
        Returns:
            List of confirmed Pivot objects
            
        Raises:
            ValueError: If data is missing required columns or too short
            
        Example:
        --------
        >>> df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
        >>> rsi = calculate_rsi(df, 14)
        >>> detector = ZigzagDetector(length=50)
        >>> pivots = detector.find_pivots(df, oscillator_data=rsi)
        """
        # Validation
        self._validate_data(data)
        
        self.total_bars_analyzed = len(data)
        pivots = []
        ghosts = []
        
        # Start from length (need bars before)
        # End at len-length (need bars after for confirmation)
        for i in range(self.length, len(data) - self.length):
            # Check pivot high
            if self._is_pivot_high(data, i):
                osc_value = oscillator_data.iloc[i] if oscillator_data is not None else None
                
                pivot = Pivot(
                    index=i,
                    timestamp=data.index[i],
                    price=data['high'].iloc[i],
                    pivot_type=PivotType.HIGH,
                    confirmed_at=i + self.length,
                    oscillator_value=osc_value
                )
                pivots.append(pivot)
                self.pivot_high_count += 1
            
            # Check pivot low
            elif self._is_pivot_low(data, i):
                osc_value = oscillator_data.iloc[i] if oscillator_data is not None else None
                
                pivot = Pivot(
                    index=i,
                    timestamp=data.index[i],
                    price=data['low'].iloc[i],
                    pivot_type=PivotType.LOW,
                    confirmed_at=i + self.length,
                    oscillator_value=osc_value
                )
                pivots.append(pivot)
                self.pivot_low_count += 1
            
            # Track ghost levels (if enabled)
            elif self.track_ghosts:
                ghost = self._check_ghost_level(data, i)
                if ghost:
                    ghosts.append(ghost)
                    self.ghost_count += 1
        
        self.pivots = pivots
        self.ghost_levels = ghosts
        
        return pivots
    
    def _validate_data(self, data: pd.DataFrame) -> None:
        """Validate input data has required columns and length"""
        required_columns = ['high', 'low', 'close']
        missing = [col for col in required_columns if col not in data.columns]
        if missing:
            raise ValueError(f"Data missing required columns: {missing}")
        
        min_length = 2 * self.length + 1
        if len(data) < min_length:
            raise ValueError(
                f"Data too short: {len(data)} bars, need at least {min_length} "
                f"(2*length+1 for confirmation)"
            )
        
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data index must be DatetimeIndex")
    
    def _is_pivot_high(self, data: pd.DataFrame, index: int) -> bool:
        """
        Check if data[index] is a pivot high.
        
        TradingView Logic: ta.pivothigh(length, length)
        - Must be highest in LENGTH bars to the LEFT
        - Must be highest in LENGTH bars to the RIGHT
        
        Args:
            data: Price data
            index: Index to check
            
        Returns:
            True if confirmed pivot high
        """
        center = data['high'].iloc[index]
        
        # Check LEFT side (length bars before)
        left_start = index - self.length
        left_end = index
        left_max = data['high'].iloc[left_start:left_end].max()
        if center <= left_max:
            return False
        
        # Check RIGHT side (length bars after)
        right_start = index + 1
        right_end = index + 1 + self.length
        right_max = data['high'].iloc[right_start:right_end].max()
        if center <= right_max:
            return False
        
        # Optional: Check threshold (minimum % move from previous pivot)
        if self.threshold > 0.0 and len(self.pivots) > 0:
            last_pivot = self.pivots[-1]
            pct_move = abs(center - last_pivot.price) / last_pivot.price
            if pct_move < self.threshold:
                return False
        
        return True
    
    def _is_pivot_low(self, data: pd.DataFrame, index: int) -> bool:
        """
        Check if data[index] is a pivot low.
        
        TradingView Logic: ta.pivotlow(length, length)
        - Must be lowest in LENGTH bars to the LEFT
        - Must be lowest in LENGTH bars to the RIGHT
        
        Args:
            data: Price data
            index: Index to check
            
        Returns:
            True if confirmed pivot low
        """
        center = data['low'].iloc[index]
        
        # Check LEFT side (length bars before)
        left_start = index - self.length
        left_end = index
        left_min = data['low'].iloc[left_start:left_end].min()
        if center >= left_min:
            return False
        
        # Check RIGHT side (length bars after)
        right_start = index + 1
        right_end = index + 1 + self.length
        right_min = data['low'].iloc[right_start:right_end].min()
        if center >= right_min:
            return False
        
        # Optional: Check threshold
        if self.threshold > 0.0 and len(self.pivots) > 0:
            last_pivot = self.pivots[-1]
            pct_move = abs(center - last_pivot.price) / last_pivot.price
            if pct_move < self.threshold:
                return False
        
        return True
    
    def _check_ghost_level(self, data: pd.DataFrame, index: int) -> Optional[GhostLevel]:
        """
        Check for ghost level (near-pivot that didn't confirm).
        
        A ghost level is created when:
        - Price made a local high/low
        - But didn't meet full pivot requirements
        - Still important as potential support/resistance
        
        Args:
            data: Price data
            index: Index to check
            
        Returns:
            GhostLevel if detected, None otherwise
        """
        # Check if it's a shorter-term high (half the length)
        short_length = self.length // 2
        
        if index < short_length or index >= len(data) - short_length:
            return None
        
        # Check for local high
        center_high = data['high'].iloc[index]
        left_high = data['high'].iloc[index-short_length:index].max()
        right_high = data['high'].iloc[index+1:index+1+short_length].max()
        
        if center_high > left_high and center_high > right_high:
            # It's a local high, but not strong enough for pivot
            strength = min(1.0, (center_high - left_high) / left_high / self.threshold)
            return GhostLevel(
                index=index,
                timestamp=data.index[index],
                price=center_high,
                level_type='resistance',
                strength=strength
            )
        
        # Check for local low
        center_low = data['low'].iloc[index]
        left_low = data['low'].iloc[index-short_length:index].min()
        right_low = data['low'].iloc[index+1:index+1+short_length].min()
        
        if center_low < left_low and center_low < right_low:
            # It's a local low, but not strong enough for pivot
            strength = min(1.0, (left_low - center_low) / center_low / self.threshold)
            return GhostLevel(
                index=index,
                timestamp=data.index[index],
                price=center_low,
                level_type='support',
                strength=strength
            )
        
        return None
    
    def get_pattern_sequence(self, max_length: int = 10) -> List[PatternDirection]:
        """
        Get pattern sequence for recent pivots.
        
        Builds sequence of HH/LH/HL/LL patterns from pivot history.
        This is critical for statistical pattern matching (Day 9).
        
        Args:
            max_length: Maximum number of patterns to return (default: 10)
            
        Returns:
            List of PatternDirection enums
            
        Example:
        --------
        >>> sequence = detector.get_pattern_sequence()
        >>> print(sequence)
        [PatternDirection.HH, PatternDirection.LH, PatternDirection.LL]
        # This means: Higher High, then Lower High, then Lower Low (downtrend!)
        """
        if len(self.pivots) < 3:
            return []
        
        sequence = []
        
        # Compare consecutive pivots of same type
        for i in range(1, len(self.pivots)):
            prev = self.pivots[i-1]
            curr = self.pivots[i]
            
            # Only compare same type (highs to highs, lows to lows)
            if prev.pivot_type != curr.pivot_type:
                continue
            
            if curr.pivot_type == PivotType.HIGH:
                # Comparing pivot highs
                if curr.price > prev.price:
                    sequence.append(PatternDirection.HIGHER_HIGH)
                else:
                    sequence.append(PatternDirection.LOWER_HIGH)
            
            else:  # PivotType.LOW
                # Comparing pivot lows
                if curr.price > prev.price:
                    sequence.append(PatternDirection.HIGHER_LOW)
                else:
                    sequence.append(PatternDirection.LOWER_LOW)
        
        # Return last max_length patterns
        return sequence[-max_length:]
    
    def get_recent_pivots(
        self, 
        n: int = 5,
        pivot_type: Optional[PivotType] = None
    ) -> List[Pivot]:
        """
        Get most recent pivots.
        
        Args:
            n: Number of recent pivots to return
            pivot_type: Filter by pivot type (None = all types)
            
        Returns:
            List of recent Pivot objects
        """
        if pivot_type is None:
            return self.pivots[-n:]
        else:
            filtered = [p for p in self.pivots if p.pivot_type == pivot_type]
            return filtered[-n:]
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get detector statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_bars': self.total_bars_analyzed,
            'total_pivots': len(self.pivots),
            'pivot_highs': self.pivot_high_count,
            'pivot_lows': self.pivot_low_count,
            'ghost_levels': self.ghost_count,
            'pivot_rate': len(self.pivots) / self.total_bars_analyzed if self.total_bars_analyzed > 0 else 0,
            'avg_bars_between_pivots': self.total_bars_analyzed / len(self.pivots) if len(self.pivots) > 0 else 0,
        }
    
    def is_m_pattern_candidate(self) -> bool:
        """
        Quick check if recent pivots form potential M-pattern structure.
        
        M-pattern requires:
        - At least 2 recent pivot highs
        - Both highs are relatively similar (within 15%)
        - A valley (pivot low) between them
        
        Returns:
            True if potential M-pattern structure exists
        """
        if len(self.pivots) < 3:
            return False
        
        # Get last 3-5 pivots
        recent = self.pivots[-5:]
        
        # Find pivot highs
        highs = [p for p in recent if p.pivot_type == PivotType.HIGH]
        if len(highs) < 2:
            return False
        
        # Check if two highs are similar (within 15%)
        h1, h2 = highs[-2], highs[-1]
        price_diff = abs(h1.price - h2.price) / max(h1.price, h2.price)
        
        if price_diff > 0.15:  # More than 15% difference
            return False
        
        # Check for valley between
        lows = [p for p in recent if p.pivot_type == PivotType.LOW and h1.index < p.index < h2.index]
        
        return len(lows) > 0
    
    def __repr__(self) -> str:
        return (f"ZigzagDetector(length={self.length}, pivots={len(self.pivots)}, "
                f"highs={self.pivot_high_count}, lows={self.pivot_low_count})")


# Helper function for quick testing
def quick_test(data_path: str = 'data/raw/BTC_USDT_PERP_30m.pkl', n_bars: int = 1000):
    """
    Quick test of zigzag detector.
    
    Args:
        data_path: Path to data file
        n_bars: Number of bars to test
    """
    import pickle
    
    print("="*60)
    print("ZIGZAG DETECTOR TEST")
    print("="*60)
    
    # Load data
    with open(data_path, 'rb') as f:
        df = pickle.load(f)
    
    df = df[df.index >= '2024-01-01'].iloc[:n_bars]
    print(f"\nData: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Test different lengths
    for length in [30, 50, 70]:
        print(f"\n{'='*60}")
        print(f"Testing with length={length}")
        print(f"{'='*60}")
        
        detector = ZigzagDetector(length=length, threshold_percent=2.0)
        pivots = detector.find_pivots(df)
        
        stats = detector.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total pivots: {stats['total_pivots']}")
        print(f"  Pivot highs: {stats['pivot_highs']}")
        print(f"  Pivot lows: {stats['pivot_lows']}")
        print(f"  Ghost levels: {stats['ghost_levels']}")
        print(f"  Pivot rate: {stats['pivot_rate']:.2%}")
        print(f"  Avg bars between pivots: {stats['avg_bars_between_pivots']:.1f}")
        
        print(f"\nFirst 5 pivots:")
        for p in pivots[:5]:
            print(f"  {p}")
        
        sequence = detector.get_pattern_sequence()
        print(f"\nPattern sequence (last 10): {[s.value for s in sequence]}")
        
        m_candidate = detector.is_m_pattern_candidate()
        print(f"M-pattern candidate: {m_candidate}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    # Run quick test
    quick_test()
