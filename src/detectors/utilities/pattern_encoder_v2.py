"""
Pattern Encoder V2 - Simplified 8-Core Pattern System

This is a simplified version that focuses on the 8 most important patterns:
1. Regular Bearish Divergence (Price HH + Osc LH/LL)
2. Hidden Bearish Divergence (Price LH + Osc HH)
3. Regular Bullish Divergence (Price LL + Osc HL/HH)
4. Hidden Bullish Divergence (Price HL + Osc LL)
5. Strong Uptrend (Price HH + Osc HH)
6. Strong Downtrend (Price LL + Osc LL)
7. Weak Uptrend (Price HH + Osc LH)
8. Weak Downtrend (Price LH + Osc LH)

Benefits:
- 540 samples / 8 patterns = 67.5 samples per pattern (vs 11.25 with 48 patterns)
- 6x more robust statistics
- Focus on what actually matters (divergences and trend strength)
- Ignore sideways/trend noise

Author: BTC_Engine_v3
Date: December 30, 2025
Reference: EXPERT_MODE_ITERATION1_ANALYSIS.md - Iteration 2 Plan
"""

from typing import Optional
from dataclasses import dataclass
from enum import Enum

import logging
logger = logging.getLogger(__name__)


# Import from original encoder
try:
    from .pattern_encoder import Pivot, PivotType, PriceDirection, OscillatorDirection
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from .pattern_encoder import Pivot, PivotType, PriceDirection, OscillatorDirection
class CorePattern(Enum):
    """
    8 Core Pattern Types (Simplified System)
    
    Focus on divergences and trend strength, ignore trend direction (UP/DOWN/SIDEWAYS)
    """
    REGULAR_BEARISH_DIVERGENCE = 0    # Price HH + Osc LH or LL
    HIDDEN_BEARISH_DIVERGENCE = 1     # Price LH + Osc HH
    REGULAR_BULLISH_DIVERGENCE = 2    # Price LL + Osc HL or HH
    HIDDEN_BULLISH_DIVERGENCE = 3     # Price HL + Osc LL
    STRONG_UPTREND = 4                # Price HH + Osc HH (both aligned up)
    STRONG_DOWNTREND = 5              # Price LL + Osc LL (both aligned down)
    WEAK_UPTREND = 6                  # Price HH + Osc LH (losing momentum)
    WEAK_DOWNTREND = 7                # Price LH + Osc LH (weak downtrend)


@dataclass
class SimplifiedPattern:
    """
    Simplified pattern information (8 core patterns only)
    
    Attributes:
        index: Pattern index (0-7)
        core_pattern: CorePattern enum
        price_direction: Price movement (HH/LH/HL/LL)
        oscillator_direction: Oscillator movement (HH/LH/HL/LL)
        pivot1: First pivot
        pivot2: Second pivot
        pivot3: Third pivot (current)
    """
    index: int
    core_pattern: CorePattern
    price_direction: PriceDirection
    oscillator_direction: OscillatorDirection
    pivot1: Pivot
    pivot2: Pivot
    pivot3: Pivot
    
    def __repr__(self) -> str:
        return (f"SimplifiedPattern(idx={self.index}, "
                f"pattern={self.core_pattern.name}, "
                f"price={self.price_direction.name}, "
                f"osc={self.oscillator_direction.name})")


class SimplifiedPatternEncoder:
    """
    Simplified pattern encoder for 8-core pattern system
    
    This encoder focuses on the patterns that matter most:
    - Divergences (regular and hidden, bullish and bearish)
    - Trend strength (strong vs weak trends)
    
    It ignores:
    - Overall trend direction (UP/SIDEWAYS/DOWN)
    - Edge case patterns with low samples
    
    Benefits:
    - 6x more samples per pattern (67 vs 11)
    - More robust statistics
    - Clearer interpretation
    - Better edge identification
    
    Example:
        >>> encoder = SimplifiedPatternEncoder()
        >>> pattern = encoder.encode(pivot1, pivot2, pivot3)
        >>> print(f"Pattern: {pattern.core_pattern.name}")
        Pattern: REGULAR_BEARISH_DIVERGENCE
    """
    
    def __init__(self):
        """Initialize simplified encoder"""
        pass
    
    def encode(
        self,
        pivot1: Pivot,
        pivot2: Pivot,
        pivot3: Pivot
    ) -> Optional[SimplifiedPattern]:
        """
        Encode a 3-pivot sequence into one of 8 core patterns
        
        Args:
            pivot1: First pivot (oldest)
            pivot2: Second pivot (middle)
            pivot3: Third pivot (current/newest)
            
        Returns:
            SimplifiedPattern if successful, None if invalid
        """
        # Validate pivots
        if not self._validate_pivots(pivot1, pivot2, pivot3):
            return None
        
        # Determine price and oscillator directions
        price_dir = self._get_price_direction(pivot2, pivot3)
        osc_dir = self._get_oscillator_direction(pivot2, pivot3)
        
        # Map to core pattern
        core_pattern, index = self._map_to_core_pattern(price_dir, osc_dir)
        
        return SimplifiedPattern(
            index=index,
            core_pattern=core_pattern,
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
    
    def _get_price_direction(self, p2: Pivot, p3: Pivot) -> PriceDirection:
        """Determine price direction between two pivots"""
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
        """Determine oscillator direction between two pivots"""
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
    
    def _map_to_core_pattern(
        self,
        price_dir: PriceDirection,
        osc_dir: OscillatorDirection
    ) -> tuple[CorePattern, int]:
        """
        Map price and oscillator directions to one of 8 core patterns
        
        Core Pattern Mapping:
        0. Regular Bearish Divergence: Price HH + Osc LH or LL
        1. Hidden Bearish Divergence: Price LH + Osc HH
        2. Regular Bullish Divergence: Price LL + Osc HL or HH
        3. Hidden Bullish Divergence: Price HL + Osc LL
        4. Strong Uptrend: Price HH + Osc HH
        5. Strong Downtrend: Price LL + Osc LL
        6. Weak Uptrend: Price HH + Osc LH (duplicate of bearish div - keep separate for clarity)
        7. Weak Downtrend: Price LH + Osc LH
        
        Args:
            price_dir: Price direction (HH/LH/HL/LL)
            osc_dir: Oscillator direction (HH/LH/HL/LL)
            
        Returns:
            Tuple of (CorePattern, index)
        """
        price_val = price_dir.value
        osc_val = osc_dir.value
        
        # Pattern 0: Regular Bearish Divergence (Price HH + Osc LH or LL)
        if price_val == 3 and osc_val in [0, 1]:  # HH + (LL or LH)
            return CorePattern.REGULAR_BEARISH_DIVERGENCE, 0
        
        # Pattern 1: Hidden Bearish Divergence (Price LH + Osc HH)
        elif price_val == 1 and osc_val == 3:  # LH + HH
            return CorePattern.HIDDEN_BEARISH_DIVERGENCE, 1
        
        # Pattern 2: Regular Bullish Divergence (Price LL + Osc HL or HH)
        elif price_val == 0 and osc_val in [2, 3]:  # LL + (HL or HH)
            return CorePattern.REGULAR_BULLISH_DIVERGENCE, 2
        
        # Pattern 3: Hidden Bullish Divergence (Price HL + Osc LL)
        elif price_val == 2 and osc_val == 0:  # HL + LL
            return CorePattern.HIDDEN_BULLISH_DIVERGENCE, 3
        
        # Pattern 4: Strong Uptrend (Price HH + Osc HH)
        elif price_val == 3 and osc_val == 3:  # HH + HH
            return CorePattern.STRONG_UPTREND, 4
        
        # Pattern 5: Strong Downtrend (Price LL + Osc LL)
        elif price_val == 0 and osc_val == 0:  # LL + LL
            return CorePattern.STRONG_DOWNTREND, 5
        
        # Pattern 6: Weak Uptrend (redundant with bearish div, but keep for clarity)
        # This is actually the same as Regular Bearish Divergence (HH + LH)
        # But we can treat it as a separate pattern for interpretation
        # NOTE: This will be counted with pattern 0 in the mapping
        
        # Pattern 7: Weak Downtrend (Price LH + Osc LH)
        elif price_val == 1 and osc_val == 1:  # LH + LH
            return CorePattern.WEAK_DOWNTREND, 7
        
        # Remaining combinations - map to closest pattern
        # These are edge cases that will get fewer samples
        
        # Price HH + Osc HL → Weak uptrend
        elif price_val == 3 and osc_val == 2:  # HH + HL
            return CorePattern.WEAK_UPTREND, 6
        
        # Price LH + Osc LL → Weak downtrend
        elif price_val == 1 and osc_val == 0:  # LH + LL
            return CorePattern.WEAK_DOWNTREND, 7
        
        # Price LH + Osc HL → Weak downtrend (sideways)
        elif price_val == 1 and osc_val == 2:  # LH + HL
            return CorePattern.WEAK_DOWNTREND, 7
        
        # Price HL + Osc LH → Weak uptrend (sideways)
        elif price_val == 2 and osc_val == 1:  # HL + LH
            return CorePattern.WEAK_UPTREND, 6
        
        # Price HL + Osc HL → Weak uptrend (continuation)
        elif price_val == 2 and osc_val == 2:  # HL + HL
            return CorePattern.WEAK_UPTREND, 6
        
        # Price HL + Osc HH → Strong uptrend (building momentum)
        elif price_val == 2 and osc_val == 3:  # HL + HH
            return CorePattern.STRONG_UPTREND, 4
        
        # Price LL + Osc LH → Strong downtrend (continuation)
        elif price_val == 0 and osc_val == 1:  # LL + LH
            return CorePattern.STRONG_DOWNTREND, 5
        
        # Default - should not reach here
        else:
            # Fallback to weak downtrend
            return CorePattern.WEAK_DOWNTREND, 7
    
    def get_pattern_description(self, index: int) -> str:
        """
        Get human-readable description of pattern index
        
        Args:
            index: Pattern index (0-7)
            
        Returns:
            Description string
        """
        descriptions = {
            0: "Regular Bearish Divergence (Price HH + Osc LH/LL) - Expect reversal down",
            1: "Hidden Bearish Divergence (Price LH + Osc HH) - Expect continuation down",
            2: "Regular Bullish Divergence (Price LL + Osc HL/HH) - Expect reversal up",
            3: "Hidden Bullish Divergence (Price HL + Osc LL) - Expect continuation up",
            4: "Strong Uptrend (Price HH + Osc HH) - Strong momentum up",
            5: "Strong Downtrend (Price LL + Osc LL) - Strong momentum down",
            6: "Weak Uptrend (Price HH + Osc LH) - Losing upward momentum",
            7: "Weak Downtrend (Price LH + Osc LH) - Weak downward pressure",
        }
        return descriptions.get(index, "Unknown pattern")
    
    def __repr__(self) -> str:
        return "SimplifiedPatternEncoder(8 core patterns)"


# Helper function for testing
def quick_test():
    """Quick test of simplified encoder"""
    logger.info("="*80)
    logger.info("SIMPLIFIED PATTERN ENCODER TEST (8 Core Patterns)")
    logger.info("="*80)
    
    encoder = SimplifiedPatternEncoder()
    
    logger.info("\nCore Pattern Descriptions:")
    logger.info("-" * 80)
    for idx in range(8):
        logger.info(f"Pattern {idx}: {encoder.get_pattern_description(idx)}")
    
    logger.info("\n" + "="*80)
    logger.info("Benefits of 8-Pattern System:")
    logger.info("="*80)
    logger.info("Current (48 patterns): 540 samples / 48 = 11.25 samples/pattern")
    logger.info("Simplified (8 patterns): 540 samples / 8 = 67.5 samples/pattern")
    logger.info("Improvement: 6x more robust statistics!")
    logger.info("\n" + "="*80)


if __name__ == "__main__":
    quick_test()
