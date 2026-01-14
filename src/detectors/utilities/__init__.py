"""
Detector Utilities Package
==========================

Support utilities for advanced pattern analysis and detection.

These utilities are NOT building blocks - they are support modules that
can be used to enhance building block analysis with features like:
- Divergence detection
- Higher timeframe confirmation
- Statistical pattern analysis
- Pivot detection (ZigZag)
- Technical oscillators

Modules:
--------
- divergence_detector: Price vs oscillator divergence analysis
- htf_confirmation: Higher timeframe (4H) confluence confirmation
- oscillators: Technical oscillators (RSI, CCI, CMO, MFI, ROC)
- pattern_encoder: Pattern encoding for statistical analysis
- pattern_encoder_v2: Simplified pattern encoder
- pattern_statistics: Historical pattern statistics and predictions
- volume_analyzer: Volume analysis utility
- zigzag_detector: Pivot detection using ZigZag methodology

Usage:
------
>>> from src.detectors.utilities.oscillators import calculate_rsi
>>> from src.detectors.utilities.zigzag_detector import ZigzagDetector

Author: BTC_Engine_v3
Date: 2026-01-14
"""

# Import commonly used utilities for convenience
from .oscillators import (
    calculate_rsi,
    calculate_cci,
    calculate_cmo,
    calculate_mfi,
    calculate_roc,
    calculate_all_oscillators
)

from .zigzag_detector import (
    ZigzagDetector,
    Pivot,
    PivotType,
    PatternDirection,
    GhostLevel
)

from .divergence_detector import (
    DivergenceDetector,
    DivergenceSignal,
    DivergenceType
)

__all__ = [
    # Oscillators
    'calculate_rsi',
    'calculate_cci',
    'calculate_cmo',
    'calculate_mfi',
    'calculate_roc',
    'calculate_all_oscillators',
    
    # ZigZag
    'ZigzagDetector',
    'Pivot',
    'PivotType',
    'PatternDirection',
    'GhostLevel',
    
    # Divergence
    'DivergenceDetector',
    'DivergenceSignal',
    'DivergenceType',
]
