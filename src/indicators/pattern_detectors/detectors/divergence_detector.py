"""
Divergence Detector - Price vs Oscillator Divergence Analysis

Detects divergences between price pivots and oscillator values:
- Regular Bullish/Bearish Divergence
- Hidden Bullish/Bearish Divergence
- Strength scoring based on magnitude

Based on: TradingView divergence methodology
Author: BTC Scalp Bot V10 Framework
Version: 1.0.0
Date: December 30, 2025
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from .zigzag_detector import Pivot, PivotType
from .oscillators import Oscillators, OscillatorType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DivergenceType(Enum):
    """Types of divergence"""
    NONE = "none"
    REGULAR_BULLISH = "regular_bullish"      # Price LL, Osc HL  -> Strong buy
    REGULAR_BEARISH = "regular_bearish"      # Price HH, Osc LH  -> Strong sell
    HIDDEN_BULLISH = "hidden_bullish"        # Price HL, Osc LL  -> Trend continuation
    HIDDEN_BEARISH = "hidden_bearish"        # Price LH, Osc HH  -> Trend continuation


@dataclass
class DivergenceSignal:
    """
    Represents a detected divergence
    
    Attributes:
        divergence_type: Type of divergence detected
        strength: Strength score (-2 to +2, negative=bearish, positive=bullish)
        price_pattern: Price pivot pattern (e.g., 'HH', 'LH')
        osc_pattern: Oscillator pivot pattern (e.g., 'LH', 'HH')
        price_pivots: The two price pivots involved
        osc_values: Oscillator values at those pivots
        probability_impact: How much this affects trade probability (0.0-0.30)
    """
    divergence_type: DivergenceType
    strength: float  # -2 (strong bearish) to +2 (strong bullish)
    price_pattern: str
    osc_pattern: str
    price_pivots: List[Pivot]
    osc_values: List[float]
    probability_impact: float = 0.0
    
    def __str__(self) -> str:
        return (f"Divergence({self.divergence_type.value}, "
                f"strength={self.strength:.1f}, "
                f"price={self.price_pattern}, osc={self.osc_pattern})")


class DivergenceDetector:
    """
    Detect price vs oscillator divergences
    
    Key Concepts:
    - Regular Divergence: Price and oscillator move in opposite directions
      * Bearish: Price makes HH, oscillator makes LH (reversal signal)
      * Bullish: Price makes LL, oscillator makes HL (reversal signal)
    
    - Hidden Divergence: Indicates trend continuation
      * Hidden Bearish: Price makes LH, oscillator makes HH
      * Hidden Bullish: Price makes HL, oscillator makes LL
    
    Parameters:
        oscillator_type: Which oscillator to use ('rsi', 'cci', 'cmo', 'mfi', 'roc')
        oscillator_length: Period for oscillator calculation
        min_divergence_strength: Minimum strength to report (0.5-2.0)
    """
    
    def __init__(
        self,
        oscillator_type: OscillatorType = 'rsi',
        oscillator_length: int = 14,
        min_divergence_strength: float = 1.0
    ):
        """
        Initialize DivergenceDetector
        
        Args:
            oscillator_type: Oscillator to use
            oscillator_length: Oscillator period
            min_divergence_strength: Minimum strength threshold
        """
        self.osc_type = oscillator_type
        self.osc_length = oscillator_length
        self.min_strength = min_divergence_strength
        
        logger.info(f"DivergenceDetector initialized: {oscillator_type}({oscillator_length})")
    
    def calculate_oscillator(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate oscillator values for data
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Series of oscillator values
        """
        return Oscillators.calculate(data, self.osc_type, self.osc_length)
    
    def detect(
        self,
        price_pivots: List[Pivot],
        osc_data: pd.Series
    ) -> DivergenceSignal:
        """
        Detect divergence between last two price pivots and oscillator
        
        Args:
            price_pivots: List of price pivots from ZigzagDetector
            osc_data: Oscillator series (same length as price data)
            
        Returns:
            DivergenceSignal (NONE if no divergence)
        """
        if len(price_pivots) < 2:
            return self._no_divergence()
        
        # Get last two pivots of same type
        p2 = price_pivots[-1]
        
        # Find previous pivot of same type
        p1 = None
        for i in range(len(price_pivots) - 2, -1, -1):
            if price_pivots[i].pivot_type == p2.pivot_type:
                p1 = price_pivots[i]
                break
        
        if p1 is None:
            return self._no_divergence()
        
        # Get oscillator values at pivots
        try:
            osc1 = osc_data.iloc[p1.index]
            osc2 = osc_data.iloc[p2.index]
        except (IndexError, KeyError):
            logger.warning(f"Could not get oscillator values at pivot indices {p1.index}, {p2.index}")
            return self._no_divergence()
        
        if pd.isna(osc1) or pd.isna(osc2):
            return self._no_divergence()
        
        # Determine price and oscillator directions
        if p1.pivot_type == PivotType.HIGH:
            # Comparing highs
            if p2.price > p1.price:
                price_pattern = 'HH'  # Higher High
                price_dir = 1
            else:
                price_pattern = 'LH'  # Lower High
                price_dir = -1
            
            if osc2 > osc1:
                osc_pattern = 'HH'
                osc_dir = 1
            else:
                osc_pattern = 'LH'
                osc_dir = -1
        
        else:  # PivotType.LOW
            # Comparing lows
            if p2.price < p1.price:
                price_pattern = 'LL'  # Lower Low
                price_dir = -1
            else:
                price_pattern = 'HL'  # Higher Low
                price_dir = 1
            
            if osc2 < osc1:
                osc_pattern = 'LL'
                osc_dir = -1
            else:
                osc_pattern = 'HL'
                osc_dir = 1
        
        # Detect divergence
        divergence_type = DivergenceType.NONE
        strength = 0.0
        
        if p1.pivot_type == PivotType.HIGH:
            # Looking at highs
            if price_dir == 1 and osc_dir == -1:
                # Price HH, Osc LH = Regular Bearish Divergence
                divergence_type = DivergenceType.REGULAR_BEARISH
                strength = -2.0
            elif price_dir == -1 and osc_dir == 1:
                # Price LH, Osc HH = Hidden Bearish Divergence  
                divergence_type = DivergenceType.HIDDEN_BEARISH
                strength = -1.0
        
        else:  # PivotType.LOW
            # Looking at lows
            if price_dir == -1 and osc_dir == 1:
                # Price LL, Osc HL = Regular Bullish Divergence
                divergence_type = DivergenceType.REGULAR_BULLISH
                strength = 2.0
            elif price_dir == 1 and osc_dir == -1:
                # Price HL, Osc LL = Hidden Bullish Divergence
                divergence_type = DivergenceType.HIDDEN_BULLISH
                strength = 1.0
        
        # Calculate magnitude-based adjustment
        if divergence_type != DivergenceType.NONE:
            price_change_pct = abs(p2.price - p1.price) / p1.price
            osc_change_pct = abs(osc2 - osc1) / abs(osc1) if osc1 != 0 else 0
            
            # Stronger divergence if price/osc changes are large
            magnitude_factor = min(price_change_pct * 10 + osc_change_pct * 0.5, 1.0)
            strength *= magnitude_factor
            
            # Check minimum strength
            if abs(strength) < self.min_strength:
                return self._no_divergence()
        
        # Calculate probability impact
        probability_impact = self._calculate_probability_impact(divergence_type, strength)
        
        signal = DivergenceSignal(
            divergence_type=divergence_type,
            strength=strength,
            price_pattern=price_pattern,
            osc_pattern=osc_pattern,
            price_pivots=[p1, p2],
            osc_values=[float(osc1), float(osc2)],
            probability_impact=probability_impact
        )
        
        if divergence_type != DivergenceType.NONE:
            logger.info(f"Divergence detected: {signal}")
        
        return signal
    
    def _calculate_probability_impact(
        self,
        div_type: DivergenceType,
        strength: float
    ) -> float:
        """
        Calculate how much divergence affects trade probability
        
        Args:
            div_type: Type of divergence
            strength: Divergence strength
            
        Returns:
            Probability boost (0.0 - 0.30)
        """
        if div_type == DivergenceType.NONE:
            return 0.0
        
        # Regular divergence has stronger impact than hidden
        if div_type in [DivergenceType.REGULAR_BEARISH, DivergenceType.REGULAR_BULLISH]:
            base_impact = 0.20  # Up to 20% probability boost
        else:  # Hidden divergence
            base_impact = 0.10  # Up to 10% probability boost
        
        # Scale by strength
        return base_impact * min(abs(strength) / 2.0, 1.0)
    
    def _no_divergence(self) -> DivergenceSignal:
        """Return a no-divergence signal"""
        return DivergenceSignal(
            divergence_type=DivergenceType.NONE,
            strength=0.0,
            price_pattern="",
            osc_pattern="",
            price_pivots=[],
            osc_values=[],
            probability_impact=0.0
        )
    
    def check_m_pattern_divergence(
        self,
        peak1: Pivot,
        peak2: Pivot,
        osc_data: pd.Series
    ) -> DivergenceSignal:
        """
        Check for bearish divergence in M-pattern
        
        For M-pattern (bearish), we want:
        - Price makes HH or similar high -> then makes another high
        - But oscillator makes LH (lower high)
        = Regular bearish divergence (strong signal)
        
        Args:
            peak1: First M-pattern peak
            peak2: Second M-pattern peak
            osc_data: Oscillator series
            
        Returns:
            DivergenceSignal
        """
        # Treat as two highs and check divergence
        return self.detect([peak1, peak2], osc_data)
    
    def check_w_pattern_divergence(
        self,
        trough1: Pivot,
        trough2: Pivot,
        osc_data: pd.Series
    ) -> DivergenceSignal:
        """
        Check for bullish divergence in W-pattern
        
        For W-pattern (bullish), we want:
        - Price makes LL or similar low -> then makes another low
        - But oscillator makes HL (higher low)
        = Regular bullish divergence (strong signal)
        
        Args:
            trough1: First W-pattern trough
            trough2: Second W-pattern trough
            osc_data: Oscillator series
            
        Returns:
            DivergenceSignal
        """
        # Treat as two lows and check divergence
        return self.detect([trough1, trough2], osc_data)
