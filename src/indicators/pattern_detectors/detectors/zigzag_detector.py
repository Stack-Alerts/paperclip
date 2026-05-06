"""
Zigzag Detector - TradingView-style Pivot Detection

Implements sophisticated zigzag algorithm matching TradingView's pivot detection:
- Confirmed pivots (requires N bars on each side)
- Threshold-based filtering (minimum % move)
- Ghost level tracking (missed reversals)
- Pattern sequence generation (HH, LH, LL, HL)

Based on: TradingView_Scripts/pivot_points_detector.pine
Author: BTC Scalp Bot V10 Framework
Version: 1.0.0
Date: December 30, 2025
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import get_logger

import logging
logger = logging.getLogger(__name__)


logger = get_logger(__name__)


class PivotType(Enum):
    """Pivot types"""
    HIGH = "H"
    LOW = "L"


@dataclass
class Pivot:
    """
    Represents a confirmed pivot point
    
    Attributes:
        index: Bar index in the data
        price: Pivot price level
        pivot_type: High or Low
        timestamp: Timestamp of the pivot
        confirmed: Whether pivot is confirmed (has enough bars on both sides)
    """
    index: int
    price: float
    pivot_type: PivotType
    timestamp: pd.Timestamp
    confirmed: bool = True
    
    def __str__(self) -> str:
        return f"Pivot({self.pivot_type.value} @ ${self.price:.2f}, idx={self.index}, confirmed={self.confirmed})"


@dataclass
class GhostLevel:
    """
    Represents a 'ghost' level - a potential reversal that didn't confirm
    
    These act as resistance/support levels from failed pivot attempts
    """
    price: float
    level_type: PivotType  # What kind of pivot failed
    timestamp: pd.Timestamp
    strength: float = 1.0  # How close it came to being a real pivot


class ZigzagDetector:
    """
    Zigzag-based pivot detector matching TradingView methodology
    
    Unlike simple peak detection (scipy.signal), this:
    1. Requires confirmation: N bars on each side of pivot
    2. Applies threshold: Minimum % move between pivots
    3. Tracks ghost levels: Failed reversal attempts
    4. Generates pattern sequences: HH, LH, LL, HL
    
    Parameters:
        length: Bars required on each side for pivot confirmation (default: 50)
        threshold_pct: Minimum % move for zigzag segment (default: 2.0%)
        track_ghosts: Whether to track ghost levels (default: True)
    """
    
    def __init__(
        self,
        length: int = 50,
        threshold_pct: float = 2.0,
        track_ghosts: bool = True
    ):
        """
        Initialize ZigzagDetector
        
        Args:
            length: Pivot confirmation length (bars on each side)
            threshold_pct: Minimum % move threshold
            track_ghosts: Track ghost levels
        """
        self.length = length
        self.threshold = threshold_pct / 100.0
        self.track_ghosts = track_ghosts
        
        # State
        self.pivots: List[Pivot] = []
        self.ghost_levels: List[GhostLevel] = []
        self.current_max: float = 0.0
        self.current_min: float = float('inf')
        self.last_confirmed_pivot_idx: int = -1
        
        logger.info(f"ZigzagDetector initialized: length={length}, threshold={threshold_pct}%")
    
    def find_pivots(self, data: pd.DataFrame) -> List[Pivot]:
        """
        Find confirmed pivots in OHLCV data
        
        Args:
            data: OHLCV DataFrame with DatetimeIndex
            
        Returns:
            List of confirmed Pivot objects
        """
        if len(data) < self.length * 2 + 1:
            logger.warning(f"Insufficient data for zigzag: {len(data)} < {self.length * 2 + 1}")
            return []
        
        # Reset state
        self.pivots = []
        self.ghost_levels = []
        
        # Find pivot highs
        pivot_highs = self._find_pivot_highs(data)
        
        # Find pivot lows
        pivot_lows = self._find_pivot_lows(data)
        
        # Combine and sort by index
        all_pivots = pivot_highs + pivot_lows
        all_pivots.sort(key=lambda p: p.index)
        
        # Filter by threshold and alternation
        filtered_pivots = self._filter_by_threshold(all_pivots, data)
        
        self.pivots = filtered_pivots
        
        logger.debug(f"Found {len(self.pivots)} confirmed pivots "
                    f"({len(pivot_highs)} highs, {len(pivot_lows)} lows)")
        
        return self.pivots
    
    def _find_pivot_highs(self, data: pd.DataFrame) -> List[Pivot]:
        """
        Find pivot highs using TradingView methodology
        
        Requires: high[i] > high[i±1], high[i±2], ..., high[i±length]
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            List of pivot high candidates
        """
        highs = data['high'].values
        timestamps = data.index
        pivot_highs = []
        
        # Need length bars on each side
        for i in range(self.length, len(data) - self.length):
            is_pivot = True
            
            # Check left side
            for j in range(1, self.length + 1):
                if highs[i] <= highs[i - j]:
                    is_pivot = False
                    break
            
            if not is_pivot:
                continue
            
            # Check right side
            for j in range(1, self.length + 1):
                if highs[i] <= highs[i + j]:
                    is_pivot = False
                    break
            
            if is_pivot:
                pivot = Pivot(
                    index=i,
                    price=highs[i],
                    pivot_type=PivotType.HIGH,
                    timestamp=timestamps[i],
                    confirmed=True
                )
                pivot_highs.append(pivot)
        
        return pivot_highs
    
    def _find_pivot_lows(self, data: pd.DataFrame) -> List[Pivot]:
        """
        Find pivot lows using TradingView methodology
        
        Requires: low[i] < low[i±1], low[i±2], ..., low[i±length]
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            List of pivot low candidates
        """
        lows = data['low'].values
        timestamps = data.index
        pivot_lows = []
        
        # Need length bars on each side
        for i in range(self.length, len(data) - self.length):
            is_pivot = True
            
            # Check left side
            for j in range(1, self.length + 1):
                if lows[i] >= lows[i - j]:
                    is_pivot = False
                    break
            
            if not is_pivot:
                continue
            
            # Check right side
            for j in range(1, self.length + 1):
                if lows[i] >= lows[i + j]:
                    is_pivot = False
                    break
            
            if is_pivot:
                pivot = Pivot(
                    index=i,
                    price=lows[i],
                    pivot_type=PivotType.LOW,
                    timestamp=timestamps[i],
                    confirmed=True
                )
                pivot_lows.append(pivot)
        
        return pivot_lows
    
    def _filter_by_threshold(
        self,
        pivots: List[Pivot],
        data: pd.DataFrame
    ) -> List[Pivot]:
        """
        Filter pivots by zigzag threshold and enforce alternation
        
        Args:
            pivots: All pivot candidates
            data: OHLCV data
            
        Returns:
            Filtered pivots forming valid zigzag
        """
        if len(pivots) == 0:
            return []
        
        filtered = [pivots[0]]  # Start with first pivot
        
        for i in range(1, len(pivots)):
            current = pivots[i]
            last = filtered[-1]
            
            # Enforce alternation (High -> Low -> High -> ...)
            if current.pivot_type == last.pivot_type:
                # Same type - keep the more extreme one
                if current.pivot_type == PivotType.HIGH:
                    if current.price > last.price:
                        filtered[-1] = current  # Replace with higher high
                    # Track ghost level for rejected pivot
                    elif self.track_ghosts:
                        self._add_ghost_level(current, data)
                else:  # LOW
                    if current.price < last.price:
                        filtered[-1] = current  # Replace with lower low
                    elif self.track_ghosts:
                        self._add_ghost_level(current, data)
                continue
            
            # Different type - check threshold
            price_change = abs(current.price - last.price) / last.price
            
            if price_change >= self.threshold:
                # Valid zigzag segment
                filtered.append(current)
            elif self.track_ghosts:
                # Failed to meet threshold - track as ghost
                self._add_ghost_level(current, data)
        
        return filtered
    
    def _add_ghost_level(self, pivot: Pivot, data: pd.DataFrame) -> None:
        """
        Add a ghost level for a failed pivot
        
        Args:
            pivot: The pivot that didn't confirm
            data: OHLCV data
        """
        # Calculate strength based on how close it came
        if len(self.pivots) > 0:
            last_pivot = self.pivots[-1]
            price_change = abs(pivot.price - last_pivot.price) / last_pivot.price
            strength = min(price_change / self.threshold, 1.0)
        else:
            strength = 0.5
        
        ghost = GhostLevel(
            price=pivot.price,
            level_type=pivot.pivot_type,
            timestamp=pivot.timestamp,
            strength=strength
        )
        
        self.ghost_levels.append(ghost)
    
    def get_pattern_sequence(self, last_n: int = 5) -> List[str]:
        """
        Get pattern sequence (HH, LH, LL, HL) for last N pivots
        
        Args:
            last_n: Number of recent pivots to analyze
            
        Returns:
            List of pattern strings like ['HH', 'LH', 'LL']
        """
        if len(self.pivots) < 2:
            return []
        
        # Get recent pivots
        recent = self.pivots[-last_n:] if len(self.pivots) >= last_n else self.pivots
        
        sequence = []
        
        for i in range(1, len(recent)):
            prev = recent[i-1]
            curr = recent[i]
            
            if curr.pivot_type == PivotType.HIGH:
                # Compare highs
                if curr.price > prev.price:
                    sequence.append('HH')  # Higher High
                else:
                    sequence.append('LH')  # Lower High
            else:  # LOW
                # Compare lows
                if curr.price < prev.price:
                    sequence.append('LL')  # Lower Low
                else:
                    sequence.append('HL')  # Higher Low
        
        return sequence
    
    def get_ghost_levels(self) -> List[GhostLevel]:
        """
        Get all tracked ghost levels
        
        Returns:
            List of GhostLevel objects
        """
        return self.ghost_levels
    
    def get_recent_pivots(self, n: int = 5) -> List[Pivot]:
        """
        Get N most recent pivots
        
        Args:
            n: Number of pivots to return
            
        Returns:
            List of recent pivots
        """
        return self.pivots[-n:] if len(self.pivots) >= n else self.pivots
    
    def find_m_pattern_structure(self) -> Optional[Tuple[Pivot, Pivot, float]]:
        """
        Find M-pattern structure in recent pivots
        
        M-pattern requires:
        - Two pivot highs at similar levels
        - A valley (pivot low) between them
        
        Returns:
            (peak1, peak2, neckline) or None
        """
        if len(self.pivots) < 3:
            return None
        
        # Look at last 10 pivots
        recent = self.get_recent_pivots(10)
        
        # Find potential M patterns (need H-L-H structure)
        for i in range(len(recent) - 2):
            p1 = recent[i]
            valley = recent[i + 1]
            p2 = recent[i + 2]
            
            # Must be High-Low-High
            if (p1.pivot_type == PivotType.HIGH and
                valley.pivot_type == PivotType.LOW and
                p2.pivot_type == PivotType.HIGH):
                
                # Check if peaks are at similar levels (within threshold)
                peak_diff = abs(p1.price - p2.price) / max(p1.price, p2.price)
                
                if peak_diff <= self.threshold * 2:  # Allow 2x threshold for M
                    neckline = valley.price
                    return (p1, p2, neckline)
        
        return None
    
    def find_w_pattern_structure(self) -> Optional[Tuple[Pivot, Pivot, float]]:
        """
        Find W-pattern structure in recent pivots
        
        W-pattern requires:
        - Two pivot lows at similar levels
        - A peak (pivot high) between them
        
        Returns:
            (trough1, trough2, neckline) or None
        """
        if len(self.pivots) < 3:
            return None
        
        # Look at last 10 pivots
        recent = self.get_recent_pivots(10)
        
        # Find potential W patterns (need L-H-L structure)
        for i in range(len(recent) - 2):
            t1 = recent[i]
            peak = recent[i + 1]
            t2 = recent[i + 2]
            
            # Must be Low-High-Low
            if (t1.pivot_type == PivotType.LOW and
                peak.pivot_type == PivotType.HIGH and
                t2.pivot_type == PivotType.LOW):
                
                # Check if troughs are at similar levels
                trough_diff = abs(t1.price - t2.price) / max(t1.price, t2.price)
                
                if trough_diff <= self.threshold * 2:  # Allow 2x threshold for W
                    neckline = peak.price
                    return (t1, t2, neckline)
        
        return None
