"""
Sophisticated M-Pattern Layer - TradingView Methodology

Institutional-grade M-pattern detector using:
- Zigzag-based pivot detection (not simple peaks)
- Divergence analysis (price vs oscillator)
- Statistical pattern matching (64x3 matrix probabilities)
- Fibonacci-based target projection
- Multi-timeframe support

Based on: TradingView_Scripts/next_pivot_projection.pine
Author: BTC Scalp Bot V10 Framework
Version: 2.0.0 (Sophisticated)
Date: December 30, 2025
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass
from pathlib import Path

from src.layers.tbd_v2.base_tbd_pattern import BaseTBDPattern
from src.layers.tbd_v2.detectors import (
    ZigzagDetector,
    Oscillators,
    DivergenceDetector,
    DivergenceType,
    PatternStatistics,
    PivotType
)
from src.core.framework.base_layer import LayerSignal
from src.utils.logger import get_logger

import logging
logger = logging.getLogger(__name__)


logger = get_logger(__name__)


@dataclass
class SophisticatedMPatternConfig:
    """Configuration for sophisticated M-pattern detector"""
    
    # Zigzag parameters
    pivot_length: int = 8                    # Bars on each side for pivot (TradingView default)
    zigzag_threshold: float = 2.0            # Min % move for zigzag segment
    
    # Oscillator settings
    oscillator_type: str = 'rsi'             # 'rsi', 'cci', 'cmo', 'mfi', 'roc'
    oscillator_length: int = 14
    
    # Divergence settings
    divergence_enabled: bool = True
    divergence_min_strength: float = 1.0     # Minimum divergence strength
    
    # Statistical thresholds
    min_lh_probability: float = 0.55         # Min 55% LH probability for M-pattern
    max_hh_probability: float = 0.50         # Max 50% HH probability (want reversal)
    min_historical_samples: int = 10         # Need 10+ historical patterns
    use_statistical_targets: bool = True     # Use Fib ratios from statistics
    
    # Pattern geometry  
    peak_tolerance: float = 0.20             # 20% max asymmetry for M-pattern
    pattern_length_min: int = 10
    pattern_length_max: int = 100
    
    # Risk management
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5
    
    # Target multipliers (fallback if not using statistics)
    fallback_tp_multipliers: list = None
    
    # Statistics database
    stats_file: str = 'data/models/pattern_statistics/m_pattern_stats_v2.pkl'
    enable_statistics: bool = True           # Use statistical predictions
    
    def __post_init__(self):
        if self.fallback_tp_multipliers is None:
            self.fallback_tp_multipliers = [0.5, 1.0, 1.5]


class SophisticatedMPatternLayer(BaseTBDPattern):
    """
    Sophisticated M-Pattern detector using TradingView methodology
    
    Key Improvements over Simple Detector:
    1. Zigzag structure instead of simple peak detection
    2. Divergence analysis for confirmation
    3. Statistical probability thresholds
    4. Fibonacci-based target projection
    5. Ghost level tracking
    
    Expected Performance:
    - Detection: 30-50 patterns/month (same as simple)
    - Win Rate: >60% (vs 51.7% simple)
    - Profit Factor: >2.0 (vs 0.95 simple)
    - Total Return: >+5%/month (vs -0.66% simple)
    """
    
    def __init__(
        self,
        config: Optional[SophisticatedMPatternConfig] = None,
        weight: float = 1.0
    ):
        """
        Initialize sophisticated M-pattern layer
        
        Args:
            config: Sophisticated M-pattern configuration
            weight: Layer weight
        """
        self.soph_config = config or SophisticatedMPatternConfig()
        
        super().__init__(
            name="sophisticated_m_pattern_v2",
            config={
                'pattern_type': 'M-Pattern (Sophisticated)',
                'version': '2.0.0',
                'description': 'TradingView-based sophisticated M-pattern detector',
                'methodology': 'Zigzag + Divergence + Statistics'
            },
            weight=weight
        )
        
        # Initialize components
        self.zigzag = ZigzagDetector(
            length=self.soph_config.pivot_length,
            threshold_pct=self.soph_config.zigzag_threshold,
            track_ghosts=True
        )
        
        self.divergence = DivergenceDetector(
            oscillator_type=self.soph_config.oscillator_type,
            oscillator_length=self.soph_config.oscillator_length,
            min_divergence_strength=self.soph_config.divergence_min_strength
        )
        
        self.statistics = PatternStatistics(
            min_samples=self.soph_config.min_historical_samples
        )
        
        # Try to load pre-trained statistics
        if self.soph_config.enable_statistics:
            stats_path = Path(self.soph_config.stats_file)
            if stats_path.exists():
                self.statistics.load(str(stats_path))
                logger.info(f"✅ Loaded pre-trained pattern statistics")
            else:
                logger.warning(f"⚠️ Statistics file not found: {stats_path}")
                logger.warning(f"   Pattern detection will work but without statistical predictions")
                logger.warning(f"   Run training script to generate statistics")
        
        logger.info(f"Sophisticated M-Pattern initialized: "
                   f"pivot_len={self.soph_config.pivot_length}, "
                   f"osc={self.soph_config.oscillator_type}({self.soph_config.oscillator_length}), "
                   f"stats={self.soph_config.enable_statistics}")
    
    def initialize(self) -> None:
        """Initialize the layer"""
        logger.info("Sophisticated M-Pattern v2 layer initialized")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators (ATR + Oscillator)
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Data with indicators
        """
        # Calculate ATR
        data = self._calculate_atr(data, self.soph_config.atr_period)
        
        # Calculate oscillator
        data['oscillator'] = self.divergence.calculate_oscillator(data)
        
        return data
    
    def generate_signal(
        self,
        data: pd.DataFrame,
        current_price: float,
        current_position: Optional[str] = None
    ) -> LayerSignal:
        """
        Generate sophisticated M-pattern signal
        
        Args:
            data: OHLCV DataFrame with indicators
            current_price: Current market price
            current_position: Current position (if any)
            
        Returns:
            LayerSignal with M-pattern detection result
        """
        # Minimum data check
        min_required = self.soph_config.pivot_length * 2 + 50
        if len(data) < min_required:
            return self._neutral_signal(current_price, "insufficient_data")
        
        # Calculate oscillator if not present
        if 'oscillator' not in data.columns:
            data = data.copy()
            data['oscillator'] = self.divergence.calculate_oscillator(data)
        
        # Calculate ATR if not present
        if 'atr' not in data.columns:
            data = data.copy()
            data = self._calculate_atr(data, self.soph_config.atr_period)
        
        # Find zigzag pivots
        pivots = self.zigzag.find_pivots(data)
        
        if len(pivots) < 3:
            return self._neutral_signal(current_price, "insufficient_pivots")
        
        # Look for M-pattern structure in pivots
        m_structure = self.zigzag.find_m_pattern_structure()
        
        if m_structure is None:
            return self._neutral_signal(current_price, "no_m_pattern_structure")
        
        peak1, peak2, neckline = m_structure
        
        # Validate M-pattern geometry
        if not self._validate_m_geometry(peak1, peak2, neckline, data):
            return self._neutral_signal(current_price, "geometry_validation_failed")
        
        # Check divergence (if enabled)
        divergence_signal = None
        if self.soph_config.divergence_enabled:
            osc_data = data['oscillator']
            divergence_signal = self.divergence.check_m_pattern_divergence(
                peak1, peak2, osc_data
            )
        
        # Check statistical probability (if enabled)
        probability_check_passed = True
        projection = None
        
        if self.soph_config.enable_statistics:
            # Get pattern index (simplified - using just the M-pattern context)
            pattern_idx = self._get_pattern_index_for_m(peak1, peak2, data)
            
            # Predict next pivot (should be LH for successful M-pattern short)
            projection = self.statistics.predict_next_pivot(
                pattern_idx,
                PivotType.HIGH
            )
            
            # Check probability thresholds
            if projection.historical_samples < self.soph_config.min_historical_samples:
                logger.debug(f"Insufficient historical samples: {projection.historical_samples} "
                           f"< {self.soph_config.min_historical_samples}")
                probability_check_passed = False
            
            elif projection.hh_probability > self.soph_config.max_hh_probability:
                logger.debug(f"HH probability too high: {projection.hh_probability:.1%} "
                           f"> {self.soph_config.max_hh_probability:.1%} (likely to go higher)")
                probability_check_passed = False
            
            elif projection.lh_probability < self.soph_config.min_lh_probability:
                logger.debug(f"LH probability too low: {projection.lh_probability:.1%} "
                           f"< {self.soph_config.min_lh_probability:.1%}")
                probability_check_passed = False
        
        # If statistical check failed, skip this pattern
        if self.soph_config.enable_statistics and not probability_check_passed:
            return self._neutral_signal(current_price, "statistical_threshold_not_met")
        
        # All checks passed - create signal with sophisticated parameters
        pattern = self._create_sophisticated_signal(
            peak1, peak2, neckline,
            current_price, data,
            divergence_signal, projection
        )
        
        if pattern is None:
            return self._neutral_signal(current_price, "signal_creation_failed")
        
        return LayerSignal(
            direction=pattern['direction'],
            confidence=pattern['confidence'],
            strength=pattern['confidence'],
            metadata=pattern['metadata']
        )
    
    def _validate_m_geometry(
        self,
        peak1,
        peak2,
        neckline: float,
        data: pd.DataFrame
    ) -> bool:
        """
        Validate M-pattern geometry requirements
        
        Args:
            peak1: First peak pivot
            peak2: Second peak pivot
            neckline: Neckline level
            data: OHLCV data
            
        Returns:
            True if geometry is valid
        """
        # Check peak symmetry
        peak_diff = abs(peak1.price - peak2.price) / max(peak1.price, peak2.price)
        if peak_diff > self.soph_config.peak_tolerance:
            logger.debug(f"Peaks too asymmetric: {peak_diff*100:.1f}% > {self.soph_config.peak_tolerance*100:.1f}%")
            return False
        
        # Check pattern length
        pattern_length = peak2.index - peak1.index
        if pattern_length < self.soph_config.pattern_length_min:
            logger.debug(f"Pattern too short: {pattern_length} bars")
            return False
        if pattern_length > self.soph_config.pattern_length_max:
            logger.debug(f"Pattern too long: {pattern_length} bars")
            return False
        
        # Check depth (neckline should be significantly below peaks)
        pattern_height = max(peak1.price, peak2.price) - neckline
        depth_pct = pattern_height / max(peak1.price, peak2.price)
        if depth_pct < 0.01:  # At least 1% depth
            logger.debug(f"Pattern too shallow: {depth_pct*100:.1f}%")
            return False
        
        return True
    
    def _get_pattern_index_for_m(
        self,
        peak1,
        peak2,
        data: pd.DataFrame
    ) -> int:
        """Get pattern index for statistical lookup"""
        # Determine trend
        sma_50 = data['close'].rolling(50).mean()
        try:
            trend = 1 if data['close'].iloc[peak2.index] > sma_50.iloc[peak2.index] else -1
        except:
            trend = -1  # Assume downtrend for M-pattern
        
        # Price direction (comparing the two peaks)
        price_dir = 1 if peak2.price > peak1.price else -1
        
        # Oscillator direction
        try:
            osc1 = data['oscillator'].iloc[peak1.index]
            osc2 = data['oscillator'].iloc[peak2.index]
            osc_dir = 1 if osc2 > osc1 else -1
        except:
            osc_dir = price_dir
        
        return self.statistics.encode_pattern(price_dir, osc_dir, trend)
    
    def _create_sophisticated_signal(
        self,
        peak1, peak2, neckline,
        current_price: float,
        data: pd.DataFrame,
        divergence_signal,
        projection
    ) -> Optional[Dict]:
        """
        Create sophisticated M-pattern signal with all enhancements
        
        Args:
            peak1, peak2: M-pattern peaks
            neckline: Neckline level
            current_price: Current price
            data: OHLCV data
            divergence_signal: Divergence analysis result
            projection: Statistical projection
            
        Returns:
            Pattern dict with signal info
        """
        # Calculate pattern metrics
        pattern_height = max(peak1.price, peak2.price) - neckline
        pattern_length = peak2.index - peak1.index
        peak_diff_pct = abs(peak1.price - peak2.price) / max(peak1.price, peak2.price)
        
        # Calculate stop loss
        atr = self._get_atr(data, self.soph_config.atr_period)
        stop_loss = max(peak1.price, peak2.price) + (atr * self.soph_config.atr_stop_multiplier)
        
        # Calculate targets using statistics or fallback
        if self.soph_config.use_statistical_targets and projection is not None:
            # Use projected Fibonacci ratio from statistics
            fib_ratio = projection.avg_fib_ratio
            tp1 = neckline - (pattern_height * fib_ratio * 0.5)
            tp2 = neckline - (pattern_height * fib_ratio * 1.0)
            tp3 = neckline - (pattern_height * fib_ratio * 1.5)
            target_method = f"statistical_fib_{fib_ratio:.3f}"
        else:
            # Use fallback multipliers
            mult = self.soph_config.fallback_tp_multipliers
            tp1 = neckline - (pattern_height * mult[0])
            tp2 = neckline - (pattern_height * mult[1])
            tp3 = neckline - (pattern_height * mult[2])
            target_method = "fallback_multipliers"
        
        # Calculate base confidence
        base_confidence = 0.60  # Start with 60% for validated M-pattern
        
        # Adjust confidence based on divergence
        if divergence_signal and divergence_signal.divergence_type != DivergenceType.NONE:
            base_confidence += divergence_signal.probability_impact
            logger.info(f"  Divergence boost: +{divergence_signal.probability_impact:.1%}")
        
        # Adjust confidence based on statistical probability
        if projection and projection.confidence > 0:
            # Weight towards LH probability
            stat_boost = (projection.lh_probability - 0.50) * projection.confidence * 0.3
            base_confidence += stat_boost
            logger.info(f"  Statistical boost: +{stat_boost:.1%} "
                       f"(LH prob={projection.lh_probability:.1%})")
        
        # Cap confidence
        confidence = min(base_confidence, 0.95)
        
        # Get ghost levels
        ghost_levels = [g.price for g in self.zigzag.get_ghost_levels()[-5:]]
        
        # Get timeframe
        timeframe = self._get_timeframe(data)
        
        # Create comprehensive metadata
        pattern = {
            'direction': 'short',
            'confidence': confidence,
            'metadata': {
                # Detection flags
                'm_pattern_detected': True,
                'sophisticated_detector': True,
                'pattern_type': 'M-Pattern',
                'pattern': 'M-Pattern (Sophisticated)',
                'layer_name': self.name,
                'timeframe': timeframe,
                
                # M-pattern structure
                'mw_peak1_price': peak1.price,
                'mw_peak2_price': peak2.price,
                'mw_neckline_price': neckline,
                'peak1_index': peak1.index,
                'peak2_index': peak2.index,
                'peak1_timestamp': str(peak1.timestamp),
                'peak2_timestamp': str(peak2.timestamp),
                
                # Pattern metrics
                'pattern_length': pattern_length,
                'pattern_height': pattern_height,
                'pattern_depth_pct': (pattern_height / max(peak1.price, peak2.price)) * 100,
                'peak_diff_pct': peak_diff_pct * 100,
                
                # Trading parameters
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit_1': tp1,
                'take_profit_2': tp2,
                'take_profit_3': tp3,
                'target_method': target_method,
                
                # Divergence info
                'divergence_detected': divergence_signal.divergence_type != DivergenceType.NONE if divergence_signal else False,
                'divergence_type': divergence_signal.divergence_type.value if divergence_signal else 'none',
                'divergence_strength': divergence_signal.strength if divergence_signal else 0.0,
                
                # Statistical info
                'statistical_prediction': projection is not None,
                'hh_probability': projection.hh_probability if projection else 0.0,
                'lh_probability': projection.lh_probability if projection else 0.0,
                'projected_fib_ratio': projection.avg_fib_ratio if projection else 1.0,
                'expected_bars_to_target': projection.expected_bars if projection else 0,
                'historical_samples': projection.historical_samples if projection else 0,
                
                # Additional context
                'ghost_levels': ghost_levels,
                'pivot_count': len(self.zigzag.pivots),
                'current_price': current_price,
                'risk_reward': abs(tp1 - current_price) / abs(stop_loss - current_price) if stop_loss != current_price else 0
            }
        }
        
        # Log detailed detection
        logger.info(f"✅ SOPHISTICATED M-PATTERN DETECTED:")
        logger.info(f"  Peaks: ${peak1.price:.2f} / ${peak2.price:.2f} (diff: {peak_diff_pct*100:.1f}%)")
        logger.info(f"  Neckline: ${neckline:.2f}")
        logger.info(f"  Pattern: {pattern_length} bars, {(pattern_height/max(peak1.price,peak2.price))*100:.1f}% depth")
        logger.info(f"  Entry: ${current_price:.2f}, SL: ${stop_loss:.2f}")
        logger.info(f"  Targets: ${tp1:.2f} / ${tp2:.2f} / ${tp3:.2f} ({target_method})")
        logger.info(f"  Confidence: {confidence:.1%}")
        
        if divergence_signal and divergence_signal.divergence_type != DivergenceType.NONE:
            logger.info(f"  Divergence: {divergence_signal.divergence_type.value} (strength={divergence_signal.strength:.1f})")
        
        if projection:
            logger.info(f"  Statistics: LH={projection.lh_probability:.1%}, HH={projection.hh_probability:.1%} "
                       f"(samples={projection.historical_samples})")
        
        return pattern
    
    def _neutral_signal(self, current_price: float, reason: str) -> LayerSignal:
        """Generate neutral signal when no pattern detected"""
        return LayerSignal(
            direction='neutral',
            confidence=0.0,
            strength=0.0,
            metadata={
                'layer_name': self.name,
                'pattern_type': 'M-Pattern (Sophisticated)',
                'reason': reason,
                'current_price': current_price,
                'sophisticated_detector': True
            }
        )


# Factory function
def create_sophisticated_m_pattern_layer(
    config: Optional[SophisticatedMPatternConfig] = None,
    weight: float = 1.0
) -> SophisticatedMPatternLayer:
    """
    Create sophisticated M-pattern layer instance
    
    Args:
        config: Configuration
        weight: Layer weight
        
    Returns:
        SophisticatedMPatternLayer instance
    """
    return SophisticatedMPatternLayer(config, weight)
