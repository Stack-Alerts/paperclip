"""
Pattern Encoder - Convert Pivot Patterns to 64-Index System

This module encodes pivot patterns into a 64-index system (0-63) based on:
- Trend direction (up/down)
- Price direction (HH/LH for highs, HL/LL for lows)
- Oscillator direction (HH/LH for highs, HL/LL for lows)

The encoding allows us to track historical outcomes for each pattern
combination and predict future pivot behavior.

Formula: index = trend_bit * 4 + price_bit * 2 + osc_bit * 1

Reference: TradingView next_pivot_projection.pine
Author: BTC_Engine_v3
Date: December 30, 2025
"""

from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

# Handle both package import and standalone execution
try:
    from .zigzag_detector import Pivot, PivotType
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from detectors.zigzag_detector import Pivot, PivotType


class TrendDirection(Enum):
    """Trend direction enumeration (2-bit encoding)"""
    UP = 0         # 00 binary
    SIDEWAYS = 1   # 01 binary
    DOWN = 2       # 10 binary
    # Reserved = 3 (for future use)


class PriceDirection(Enum):
    """Price direction for consecutive pivots (2-bit encoding)"""
    LOWER_LOW = 0     # 00 binary - LL (for lows)
    LOWER_HIGH = 1    # 01 binary - LH (for highs)
    HIGHER_LOW = 2    # 10 binary - HL (for lows)
    HIGHER_HIGH = 3   # 11 binary - HH (for highs)


class OscillatorDirection(Enum):
    """Oscillator direction for consecutive pivots (2-bit encoding)"""
    LOWER_LOW = 0     # 00 binary - LL
    LOWER_HIGH = 1    # 01 binary - LH
    HIGHER_LOW = 2    # 10 binary - HL
    HIGHER_HIGH = 3   # 11 binary - HH


@dataclass
class EncodedPattern:
    """
    Encoded pattern information.
    
    Attributes:
        index: Pattern index (0-63)
        trend_direction: Overall trend
        price_direction: Price movement (HH/LH/HL/LL)
        oscillator_direction: Oscillator movement (HH/LH/HL/LL)
        pivot1: First pivot in the pattern
        pivot2: Second pivot in the pattern
        pivot3: Third pivot in the pattern (current)
    """
    index: int
    trend_direction: TrendDirection
    price_direction: PriceDirection
    oscillator_direction: OscillatorDirection
    pivot1: Pivot
    pivot2: Pivot
    pivot3: Pivot
    
    def __repr__(self) -> str:
        return (f"Pattern(idx={self.index}, trend={self.trend_direction.name}, "
                f"price={self.price_direction.name}, osc={self.oscillator_direction.name})")


class PatternEncoder:
    """
    Pattern encoder for 64-index system.
    
    This encoder converts sequences of 3 pivots into a unique index (0-63)
    based on trend, price direction, and oscillator direction.
    
    Encoding Formula:
    -----------------
    index = trend_bit * 4 + price_bit * 2 + osc_bit * 1
    
    Where:
    - trend_bit: 0 if uptrend, 1 if downtrend
    - price_bit: 1 if HH (abs > 1), 0 if LH/LL (abs <= 1)
    - osc_bit: 1 if HH (abs > 1), 0 if LH/LL (abs <= 1)
    
    Index Range: 0-63 (64 total combinations)
    
    Example Patterns:
    -----------------
    - Uptrend + HH price + HH osc = 0*4 + 1*2 + 1*1 = 3 (strong uptrend)
    - Downtrend + LH price + LH osc = 1*4 + 0*2 + 0*1 = 4 (strong downtrend)
    - Downtrend + HH price + LH osc = 1*4 + 1*2 + 0*1 = 6 (bearish div!)
    
    Reference:
    ----------
    TradingView: next_pivot_projection.pine - getTrendIndex()
    
    Example:
    --------
    >>> encoder = PatternEncoder()
    >>> pattern = encoder.encode(pivot1, pivot2, pivot3)
    >>> print(f"Pattern index: {pattern.index}")
    >>> print(f"Trend: {pattern.trend_direction.name}")
    """
    
    def __init__(self, trend_lookback: int = 20):
        """
        Initialize pattern encoder.
        
        Args:
            trend_lookback: Bars to look back for trend determination (default: 20)
        """
        self.trend_lookback = trend_lookback
        
    def encode(
        self,
        pivot1: Pivot,
        pivot2: Pivot,
        pivot3: Pivot
    ) -> Optional[EncodedPattern]:
        """
        Encode a 3-pivot sequence into pattern index.
        
        This is the main encoding method. It takes 3 consecutive pivots
        of the same type (all highs or all lows) and encodes them into
        a unique pattern index.
        
        Args:
            pivot1: First pivot (oldest)
            pivot2: Second pivot (middle)
            pivot3: Third pivot (current/newest)
            
        Returns:
            EncodedPattern if successful, None if pivots invalid
            
        Raises:
            ValueError: If pivots are not same type or missing oscillator values
            
        Example:
        --------
        >>> # Get last 3 pivot highs
        >>> highs = [p for p in pivots if p.pivot_type == PivotType.HIGH]
        >>> p1, p2, p3 = highs[-3], highs[-2], highs[-1]
        >>> 
        >>> encoder = PatternEncoder()
        >>> pattern = encoder.encode(p1, p2, p3)
        >>> print(f"Pattern {pattern.index}: {pattern}")
        """
        # Validate pivots
        if not self._validate_pivots(pivot1, pivot2, pivot3):
            return None
        
        # Determine trend direction
        trend = self._get_trend_direction(pivot1, pivot2, pivot3)
        
        # Determine price direction
        price_dir = self._get_price_direction(pivot2, pivot3)
        
        # Determine oscillator direction
        osc_dir = self._get_oscillator_direction(pivot2, pivot3)
        
        # Calculate index
        index = self._calculate_index(trend, price_dir, osc_dir)
        
        return EncodedPattern(
            index=index,
            trend_direction=trend,
            price_direction=price_dir,
            oscillator_direction=osc_dir,
            pivot1=pivot1,
            pivot2=pivot2,
            pivot3=pivot3
        )
    
    def _validate_pivots(self, p1: Pivot, p2: Pivot, p3: Pivot) -> bool:
        """Validate that pivots are suitable for encoding"""
        # Must all be same type
        if not (p1.pivot_type == p2.pivot_type == p3.pivot_type):
            return False
        
        # Must have oscillator values
        if None in [p1.oscillator_value, p2.oscillator_value, p3.oscillator_value]:
            return False
        
        # Must be in chronological order
        if not (p1.index < p2.index < p3.index):
            return False
        
        return True
    
    def _get_trend_direction(self, p1: Pivot, p2: Pivot, p3: Pivot) -> TrendDirection:
        """
        Determine overall trend direction with sideways detection.
        
        Enhanced logic:
        - If price change < 2%: SIDEWAYS (ranging market)
        - If p3 > p1 by > 2%: UPTREND
        - If p3 < p1 by > 2%: DOWNTREND
        
        This captures ranging/consolidating markets which behave differently
        from trending markets.
        
        Args:
            p1, p2, p3: Consecutive pivots
            
        Returns:
            TrendDirection
        """
        # Calculate percentage price change from p1 to p3
        price_change_pct = abs(p3.price - p1.price) / p1.price
        
        # Sideways threshold: 2% (adjustable based on asset volatility)
        sideways_threshold = 0.02
        
        # Detect sideways/ranging market
        if price_change_pct < sideways_threshold:
            return TrendDirection.SIDEWAYS
        # Uptrend: p3 significantly higher than p1
        elif p3.price > p1.price:
            return TrendDirection.UP
        # Downtrend: p3 significantly lower than p1
        else:
            return TrendDirection.DOWN
    
    def _get_price_direction(self, p2: Pivot, p3: Pivot) -> PriceDirection:
        """
        Determine price direction between two pivots.
        
        For pivot highs:
        - p3 > p2: Higher High (HH)
        - p3 < p2: Lower High (LH)
        
        For pivot lows:
        - p3 > p2: Higher Low (HL)
        - p3 < p2: Lower Low (LL)
        
        Args:
            p2: Previous pivot
            p3: Current pivot
            
        Returns:
            PriceDirection
        """
        if p3.pivot_type == PivotType.HIGH:
            # Comparing highs
            if p3.price > p2.price:
                return PriceDirection.HIGHER_HIGH
            else:
                return PriceDirection.LOWER_HIGH
        else:  # PivotType.LOW
            # Comparing lows
            if p3.price > p2.price:
                return PriceDirection.HIGHER_LOW
            else:
                return PriceDirection.LOWER_LOW
    
    def _get_oscillator_direction(self, p2: Pivot, p3: Pivot) -> OscillatorDirection:
        """
        Determine oscillator direction between two pivots.
        
        Args:
            p2: Previous pivot
            p3: Current pivot
            
        Returns:
            OscillatorDirection
        """
        osc2 = p2.oscillator_value
        osc3 = p3.oscillator_value
        
        if p3.pivot_type == PivotType.HIGH:
            # Comparing oscillator at highs
            if osc3 > osc2:
                return OscillatorDirection.HIGHER_HIGH
            else:
                return OscillatorDirection.LOWER_HIGH
        else:  # PivotType.LOW
            # Comparing oscillator at lows
            if osc3 > osc2:
                return OscillatorDirection.HIGHER_LOW
            else:
                return OscillatorDirection.LOWER_LOW
    
    def _calculate_index(
        self,
        trend: TrendDirection,
        price_dir: PriceDirection,
        osc_dir: OscillatorDirection
    ) -> int:
        """
        Calculate pattern index (0-63) from directions.
        
        Enhanced 6-Bit Formula (Option 1):
        index = trend_bits * 16 + price_bits * 4 + osc_bits * 1
        
        Bit Encoding (2 bits each = 6 total):
        - trend_bits: UP=0, SIDEWAYS=1, DOWN=2 (2 bits, 3 values used)
        - price_bits: LL=0, LH=1, HL=2, HH=3 (2 bits, 4 values)
        - osc_bits: LL=0, LH=1, HL=2, HH=3 (2 bits, 4 values)
        
        Total combinations: 3 * 4 * 4 = 48 realistic patterns (0-47)
        Maximum index: 2*16 + 3*4 + 3 = 47
        
        Args:
            trend: Trend direction
            price_dir: Price direction
            osc_dir: Oscillator direction
            
        Returns:
            Pattern index (0-63, though 0-47 are used)
        """
        # Enhanced 6-bit encoding using enum values directly
        trend_bits = trend.value      # 0 (UP), 1 (SIDEWAYS), or 2 (DOWN)
        price_bits = price_dir.value  # 0 (LL), 1 (LH), 2 (HL), or 3 (HH)
        osc_bits = osc_dir.value      # 0 (LL), 1 (LH), 2 (HL), or 3 (HH)
        
        # Calculate 6-bit index (0-63 range, 0-47 realistic)
        index = (trend_bits * 16) + (price_bits * 4) + (osc_bits * 1)
        
        # Ensure within bounds
        return max(0, min(63, index))
    
    def decode_index(self, index: int) -> Tuple[int, int, int]:
        """
        Decode pattern index back to values (6-bit enhanced).
        
        Useful for understanding what a pattern index represents.
        
        Args:
            index: Pattern index (0-63)
            
        Returns:
            Tuple of (trend_value, price_value, osc_value)
            
        Example:
        --------
        >>> encoder = PatternEncoder()
        >>> trend, price, osc = encoder.decode_index(37)
        >>> print(f"Index 37: trend={trend}, price={price}, osc={osc}")
        Index 37: trend=2 (DOWN), price=1 (LH), osc=1 (LH)
        """
        # Enhanced 6-bit decoding
        trend_value = index // 16      # Bits 5-4: 0=UP, 1=SIDEWAYS, 2=DOWN
        price_value = (index // 4) % 4  # Bits 3-2: 0=LL, 1=LH, 2=HL, 3=HH
        osc_value = index % 4          # Bits 1-0: 0=LL, 1=LH, 2=HL, 3=HH
        
        return (trend_value, price_value, osc_value)
    
    def get_pattern_description(self, index: int) -> str:
        """
        Get human-readable description of pattern index (6-bit enhanced).
        
        Args:
            index: Pattern index (0-63)
            
        Returns:
            Description string
            
        Example:
        --------
        >>> encoder = PatternEncoder()
        >>> print(encoder.get_pattern_description(37))
        "Downtrend + Price LH + Oscillator LH (Bearish Confirmation ⚠️)"
        """
        trend_val, price_val, osc_val = self.decode_index(index)
        
        # Trend description
        trend_map = {0: "Uptrend", 1: "Sideways", 2: "Downtrend"}
        trend_str = trend_map.get(trend_val, "Unknown")
        
        # Price direction description
        price_map = {0: "LL", 1: "LH", 2: "HL", 3: "HH"}
        price_str = price_map.get(price_val, "Unknown")
        
        # Oscillator direction description
        osc_map = {0: "LL", 1: "LH", 2: "HL", 3: "HH"}
        osc_str = osc_map.get(osc_val, "Unknown")
        
        desc = f"{trend_str} + Price {price_str} + Oscillator {osc_str}"
        
        # Detect special patterns
        # Bearish divergence: Downtrend + HH price + LH osc
        if trend_val == 2 and price_val == 3 and osc_val in [0, 1]:
            desc += " (Bearish Divergence ⚠️)"
        # Bullish divergence: Uptrend + LL price + HL osc
        elif trend_val == 0 and price_val == 0 and osc_val in [2, 3]:
            desc += " (Bullish Divergence ⚠️)"
        # Hidden bearish divergence: Downtrend + LH price + HH osc
        elif trend_val == 2 and price_val == 1 and osc_val == 3:
            desc += " (Hidden Bearish Div ⚠️)"
        # Hidden bullish divergence: Uptrend + HL price + LL osc
        elif trend_val == 0 and price_val == 2 and osc_val == 0:
            desc += " (Hidden Bullish Div ⚠️)"
        
        return desc
    
    def __repr__(self) -> str:
        return f"PatternEncoder(trend_lookback={self.trend_lookback})"


# Helper functions for quick testing
def quick_test():
    """Quick test of pattern encoder"""
    print("="*60)
    print("PATTERN ENCODER TEST")
    print("="*60)
    
    encoder = PatternEncoder()
    
    print("\nPattern Index Decoding:")
    print("-" * 60)
    for idx in [0, 3, 4, 6, 7, 63]:
        print(f"Index {idx:2d}: {encoder.get_pattern_description(idx)}")
    
    print("\n" + "="*60)
    print("All 64 pattern combinations:")
    print("="*60)
    for idx in range(64):
        trend_bit, price_bit, osc_bit = encoder.decode_index(idx)
        print(f"{idx:2d}: T={trend_bit} P={price_bit} O={osc_bit} | {encoder.get_pattern_description(idx)}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    quick_test()
