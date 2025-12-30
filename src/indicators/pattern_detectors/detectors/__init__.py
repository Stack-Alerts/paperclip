"""
TBD v2 Sophisticated Detectors

Advanced pattern detection components based on TradingView methodology:
- Zigzag-based pivot detection
- Divergence analysis
- Statistical pattern matching
- Fibonacci projection

Author: BTC Scalp Bot V10 Framework
Version: 2.0.0 (Sophisticated)
Date: December 30, 2025
"""

from .zigzag_detector import ZigzagDetector, Pivot, PivotType
from .oscillators import Oscillators
from .divergence_detector import DivergenceDetector, DivergenceSignal, DivergenceType
from .pattern_statistics import PatternStatistics, PatternProjection

__all__ = [
    'ZigzagDetector',
    'Pivot',
    'PivotType',
    'Oscillators',
    'DivergenceDetector',
    'DivergenceSignal',
    'DivergenceType',
    'PatternStatistics',
    'PatternProjection',
]
