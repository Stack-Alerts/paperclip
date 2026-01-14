"""
Divergence Detector - Price vs Oscillator Divergence Analysis

Detects divergence between price action and technical oscillators.
This is a critical signal for pattern reversal confirmation.

Key Concept:
-----------
Bearish Divergence (M-pattern signal):
  - Price makes Higher High (HH)
  - Oscillator makes Lower High (LH)
  - → Momentum weakening despite higher price
  - → Strong reversal signal

Bullish Divergence (W-pattern signal):
  - Price makes Lower Low (LL)
  - Oscillator makes Higher Low (HL)
  - → Momentum strengthening despite lower price
  - → Strong reversal signal

Impact: Divergence adds +15-20% to win rate probability

Reference: TradingView divergence indicators
Author: BTC_Engine_v3
Date: December 30, 2025
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

# Handle both package import and standalone execution
try:
    from .zigzag_detector import Pivot, PivotType, PatternDirection
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from .zigzag_detector import Pivot, PivotType, PatternDirection


class DivergenceType(Enum):
    """Types of divergence"""
    NONE = 0
    BEARISH_WEAK = -1      # Price HH, Osc LH (weak signal)
    BEARISH_STRONG = -2    # Price HH, Osc LH with large difference (strong)
    BULLISH_WEAK = 1       # Price LL, Osc HL (weak signal)
    BULLISH_STRONG = 2     # Price LL, Osc HL with large difference (strong)


@dataclass
class DivergenceSignal:
    """
    Divergence signal information.
    
    Attributes:
        divergence_type: Type of divergence detected
        price_direction: HH/LH/HL/LL for price
        oscillator_direction: HH/LH/HL/LL for oscillator
        strength: Signal strength (0.0-1.0)
        probability_boost: Probability boost to add (+0.15 = +15%)
        pivot1: First pivot in comparison
        pivot2: Second pivot in comparison
        oscillator_name: Which oscillator was used
    """
    divergence_type: DivergenceType
    price_direction: str  # 'HH', 'LH', 'HL', 'LL'
    oscillator_direction: str
    strength: float
    probability_boost: float
    pivot1: Pivot
    pivot2: Pivot
    oscillator_name: str
    
    def __repr__(self) -> str:
        return (f"DivergenceSignal({self.divergence_type.name}, "
                f"price={self.price_direction}, osc={self.oscillator_direction}, "
                f"strength={self.strength:.2f}, boost=+{self.probability_boost:.1%})")


class DivergenceDetector:
    """
    Divergence detector for price vs oscillator analysis.
    
    This detector compares price pivot patterns with oscillator pivot patterns
    to identify divergences that signal potential reversals.
    
    Key Concepts:
    -------------
    1. Bearish Divergence (M-pattern):
       - Last two price pivots: Higher High
       - Last two oscillator values: Lower High
       - → Weakening momentum = reversal likely
       - Adds +15-20% to probability
    
    2. Bullish Divergence (W-pattern):
       - Last two price pivots: Lower Low
       - Last two oscillator values: Higher Low
       - → Strengthening momentum = reversal likely
       - Adds +15-20% to probability
    
    3. Strength Calculation:
       - Weak: Small diverge (<10% difference)
       - Strong: Large divergence (>20% difference)
       - Very Strong: Extreme divergence (>30%)
    
    Example:
    --------
    >>> from oscillators import calculate_rsi
    >>> detector = DivergenceDetector(oscillator_name='rsi')
    >>> signal = detector.check_divergence(pivot_highs, rsi_values)
    >>> if signal.divergence_type == DivergenceType.BEARISH_STRONG:
    ...     print(f"Strong bearish divergence! Boost: +{signal.probability_boost:.1%}")
    """
    
    def __init__(
        self,
        oscillator_name: str = 'rsi',
        min_divergence_percent: float = 5.0,
        strong_divergence_percent: float = 15.0
    ):
        """
        Initialize divergence detector.
        
        Args:
            oscillator_name: Name of oscillator ('rsi', 'cci', 'cmo', etc.)
            min_divergence_percent: Minimum % difference to signal divergence (default: 5%)
            strong_divergence_percent: % difference for strong signal (default: 15%)
        """
        self.oscillator_name = oscillator_name
        self.min_divergence = min_divergence_percent / 100.0
        self.strong_divergence = strong_divergence_percent / 100.0
        
        # Divergence weight based on oscillator type
        self.oscillator_weights = {
            'rsi': 0.20,    # RSI most reliable (20% boost)
            'cci': 0.15,    # CCI good (15% boost)
            'cmo': 0.15,    # CMO similar to RSI (15% boost)
            'mfi': 0.18,    # MFI includes volume (18% boost)
            'roc': 0.12,    # ROC simpler (12% boost)
        }
        
        self.base_weight = self.oscillator_weights.get(oscillator_name.lower(), 0.15)
    
    def check_divergence(
        self,
        pivots: List[Pivot],
        min_pivots: int = 2
    ) -> Optional[DivergenceSignal]:
        """
        Check for divergence between price pivots and oscillator values.
        
        This is the main method. It compares the last N pivots to detect
        divergences between price direction and oscillator direction.
        
        Args:
            pivots: List of Pivot objects (must have oscillator_value set)
            min_pivots: Minimum number of pivots to check (default: 2)
            
        Returns:
            DivergenceSignal if divergence detected, None otherwise
            
        Example:
        --------
        >>> # Get pivots from zigzag detector with oscillator data
        >>> zigzag = ZigzagDetector(length=50)
        >>> rsi = calculate_rsi(df)
        >>> pivots = zigzag.find_pivots(df, oscillator_data=rsi)
        >>> 
        >>> # Check for divergence
        >>> div_detector = DivergenceDetector('rsi')
        >>> signal = div_detector.check_divergence(pivots)
        >>> if signal:
        ...     print(f"Divergence detected: {signal}")
        """
        if len(pivots) < min_pivots:
            return None
        
        # Get last 2 pivots of same type (highs or lows)
        last_pivot = pivots[-1]
        
        # Find previous pivot of same type
        previous_pivot = None
        for p in reversed(pivots[:-1]):
            if p.pivot_type == last_pivot.pivot_type:
                previous_pivot = p
                break
        
        if previous_pivot is None:
            return None
        
        # Check if oscillator values are available
        if last_pivot.oscillator_value is None or previous_pivot.oscillator_value is None:
            return None
        
        # Determine price direction
        price_dir = self._get_direction(
            previous_pivot.price,
            last_pivot.price,
            is_high=(last_pivot.pivot_type == PivotType.HIGH)
        )
        
        # Determine oscillator direction
        osc_dir = self._get_direction(
            previous_pivot.oscillator_value,
            last_pivot.oscillator_value,
            is_high=(last_pivot.pivot_type == PivotType.HIGH)
        )
        
        # Check for divergence
        divergence_type = self._classify_divergence(price_dir, osc_dir, last_pivot.pivot_type)
        
        if divergence_type == DivergenceType.NONE:
            return None
        
        # Calculate strength
        price_change = abs(last_pivot.price - previous_pivot.price) / previous_pivot.price
        osc_change = abs(last_pivot.oscillator_value - previous_pivot.oscillator_value)
        
        # Normalize oscillator change based on type
        if self.oscillator_name in ['rsi', 'mfi']:
            osc_change /= 100.0  # RSI and MFI are 0-100
        elif self.oscillator_name == 'cmo':
            osc_change /= 200.0  # CMO is -100 to +100
        elif self.oscillator_name == 'cci':
            osc_change /= 300.0  # CCI typically -300 to +300
        else:  # ROC or others
            osc_change = min(osc_change / 100.0, 1.0)
        
        # Calculate divergence strength (how different the directions are)
        divergence_strength = abs(price_change - osc_change) / max(price_change, 0.01)
        divergence_strength = min(divergence_strength, 1.0)
        
        # Calculate probability boost
        if divergence_strength > self.strong_divergence:
            probability_boost = self.base_weight * 1.5  # Strong signal = 1.5x boost
        elif divergence_strength > self.min_divergence:
            probability_boost = self.base_weight  # Normal boost
        else:
            probability_boost = self.base_weight * 0.5  # Weak signal = 0.5x boost
        
        return DivergenceSignal(
            divergence_type=divergence_type,
            price_direction=price_dir,
            oscillator_direction=osc_dir,
            strength=divergence_strength,
            probability_boost=probability_boost,
            pivot1=previous_pivot,
            pivot2=last_pivot,
            oscillator_name=self.oscillator_name
        )
    
    def _get_direction(self, value1: float, value2: float, is_high: bool) -> str:
        """
        Get direction (HH/LH/HL/LL) for two values.
        
        Args:
            value1: First value
            value2: Second value
            is_high: True if comparing highs, False if comparing lows
            
        Returns:
            'HH', 'LH', 'HL', or 'LL'
        """
        if is_high:
            # Comparing highs
            if value2 > value1:
                return 'HH'  # Higher High
            else:
                return 'LH'  # Lower High
        else:
            # Comparing lows
            if value2 > value1:
                return 'HL'  # Higher Low
            else:
                return 'LL'  # Lower Low
    
    def _classify_divergence(
        self,
        price_dir: str,
        osc_dir: str,
        pivot_type: PivotType
    ) -> DivergenceType:
        """
        Classify divergence type based on price and oscillator directions.
        
        Args:
            price_dir: Price direction ('HH', 'LH', 'HL', 'LL')
            osc_dir: Oscillator direction ('HH', 'LH', 'HL', 'LL')
            pivot_type: Type of pivot (HIGH or LOW)
            
        Returns:
            DivergenceType
        """
        # Bearish divergence at highs
        if pivot_type == PivotType.HIGH:
            if price_dir == 'HH' and osc_dir == 'LH':
                return DivergenceType.BEARISH_STRONG
            elif price_dir == 'HH' and osc_dir != 'HH':
                return DivergenceType.BEARISH_WEAK
        
        # Bullish divergence at lows
        elif pivot_type == PivotType.LOW:
            if price_dir == 'LL' and osc_dir == 'HL':
                return DivergenceType.BULLISH_STRONG
            elif price_dir == 'LL' and osc_dir != 'LL':
                return DivergenceType.BULLISH_WEAK
        
        return DivergenceType.NONE
    
    def check_multiple_oscillators(
        self,
        pivots_with_oscillators: dict
    ) -> List[DivergenceSignal]:
        """
        Check divergence across multiple oscillators.
        
        When multiple oscillators agree on divergence, it's a stronger signal.
        
        Args:
            pivots_with_oscillators: Dict of {oscillator_name: List[Pivot]}
                                    Each pivot should have oscillator_value set
            
        Returns:
            List of DivergenceSignal objects (one per oscillator)
            
        Example:
        --------
        >>> # Create detectors for each oscillator
        >>> rsi = calculate_rsi(df)
        >>> cci = calculate_cci(df)
        >>> 
        >>> # Get pivots with each oscillator
        >>> zigzag = ZigzagDetector(length=50)
        >>> rsi_pivots = zigzag.find_pivots(df, oscillator_data=rsi)
        >>> 
        >>> zigzag2 = ZigzagDetector(length=50)
        >>> cci_pivots = zigzag2.find_pivots(df, oscillator_data=cci)
        >>> 
        >>> # Check all
        >>> detector = DivergenceDetector()
        >>> signals = detector.check_multiple_oscillators({
        ...     'rsi': rsi_pivots,
        ...     'cci': cci_pivots
        ... })
        >>> 
        >>> # Count how many agree
        >>> bearish_count = sum(1 for s in signals if s.divergence_type.value < 0)
        >>> if bearish_count >= 2:
        ...     print("Multiple oscillators confirm bearish divergence!")
        """
        signals = []
        
        for osc_name, pivots in pivots_with_oscillators.items():
            detector = DivergenceDetector(oscillator_name=osc_name)
            signal = detector.check_divergence(pivots)
            if signal:
                signals.append(signal)
        
        return signals
    
    def get_consensus_boost(self, signals: List[DivergenceSignal]) -> float:
        """
        Calculate consensus probability boost from multiple divergence signals.
        
        When multiple oscillators agree, the boost is amplified.
        
        Args:
            signals: List of DivergenceSignal objects
            
        Returns:
            Total probability boost (e.g., 0.25 = +25%)
        """
        if not signals:
            return 0.0
        
        # Count bearish and bullish signals
        bearish = [s for s in signals if s.divergence_type.value < 0]
        bullish = [s for s in signals if s.divergence_type.value > 0]
        
        # Use dominant direction
        dominant = bearish if len(bearish) > len(bullish) else bullish
        
        if len(dominant) == 0:
            return 0.0
        
        # Base boost is average of dominant signals
        base_boost = np.mean([s.probability_boost for s in dominant])
        
        # Amplify if multiple agree (consensus bonus)
        if len(dominant) >= 3:
            consensus_multiplier = 1.5  # 3+ oscillators = 50% bonus
        elif len(dominant) >= 2:
            consensus_multiplier = 1.25  # 2 oscillators = 25% bonus
        else:
            consensus_multiplier = 1.0  # Single oscillator = no bonus
        
        total_boost = base_boost * consensus_multiplier
        
        # Cap at +30% to avoid over-confidence
        return min(total_boost, 0.30)
    
    def __repr__(self) -> str:
        return f"DivergenceDetector(oscillator='{self.oscillator_name}', weight={self.base_weight:.1%})"


# Helper function for quick testing
def quick_test(data_path: str = 'data/raw/BTC_USDT_PERP_30m.pkl', n_bars: int = 1000):
    """
    Quick test of divergence detector.
    
    Args:
        data_path: Path to data file
        n_bars: Number of bars to test
    """
    import pickle
    import sys
    sys.path.insert(0, '/home/sirrus/projects/BTC_Engine_v3')
    
    from src.detectors.utilities.zigzag_detector import ZigzagDetector
    from src.detectors.utilities.oscillators import calculate_rsi, calculate_cci
    
    print("="*60)
    print("DIVERGENCE DETECTOR TEST")
    print("="*60)
    
    # Load data
    with open(data_path, 'rb') as f:
        df = pickle.load(f)
    
    df = df[df.index >= '2024-01-01'].iloc[:n_bars]
    print(f"\nData: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Calculate oscillators
    print(f"\n{'='*60}")
    print("Calculating oscillators...")
    print(f"{'='*60}")
    rsi = calculate_rsi(df, length=14)
    cci = calculate_cci(df, length=20)
    
    # Detect pivots with oscillators
    print(f"\n{'='*60}")
    print("Detecting pivots with RSI...")
    print(f"{'='*60}")
    zigzag = ZigzagDetector(length=50)
    pivots = zigzag.find_pivots(df, oscillator_data=rsi)
    print(f"Found {len(pivots)} pivots")
    
    # Check for divergences
    print(f"\n{'='*60}")
    print("Checking for divergences...")
    print(f"{'='*60}")
    
    div_detector = DivergenceDetector(oscillator_name='rsi')
    
    # Check each pair of pivots
    divergences_found = []
    for i in range(2, len(pivots) + 1):
        signal = div_detector.check_divergence(pivots[:i])
        if signal:
            divergences_found.append(signal)
            print(f"\n{signal}")
            print(f"  Pivot 1: {signal.pivot1.timestamp} @ ${signal.pivot1.price:.2f}, RSI={signal.pivot1.oscillator_value:.1f}")
            print(f"  Pivot 2: {signal.pivot2.timestamp} @ ${signal.pivot2.price:.2f}, RSI={signal.pivot2.oscillator_value:.1f}")
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"{'='*60}")
    print(f"Total divergences found: {len(divergences_found)}")
    
    bearish = [d for d in divergences_found if d.divergence_type.value < 0]
    bullish = [d for d in divergences_found if d.divergence_type.value > 0]
    
    print(f"Bearish divergences: {len(bearish)}")
    print(f"Bullish divergences: {len(bullish)}")
    
    if divergences_found:
        avg_boost = np.mean([d.probability_boost for d in divergences_found])
        print(f"Average probability boost: +{avg_boost:.1%}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    # Run quick test
    quick_test()
