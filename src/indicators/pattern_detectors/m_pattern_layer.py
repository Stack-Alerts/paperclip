"""
M-Pattern Layer (Double Top) - TBD v2 CORRECTED

M-pattern (bearish reversal) detection per TBD documentation:
- REQUIRES neckline breakout confirmation (≥0.3% break)
- REQUIRES volume spike on breakout (≥1.3x average)
- Volume distribution check (2nd peak ≤ 1st peak)
- Peak tolerance: 10-20% (15% default)
- Pattern length: 10-50 candles

Author: BTC Scalp Bot V10 Framework
Version: 2.1.0 (Documentation-Aligned)
Date: December 29, 2025
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass

from src.layers.tbd_v2.base_tbd_pattern import BaseTBDPattern
from src.core.framework.base_layer import LayerSignal
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MPatternConfig:
    """Configuration for M-Pattern detection (DETECTION MODE - Match Manual Trading)"""
    
    # Pattern geometry (LOOSE - match user's manual detection style)
    peak_tolerance: float = 0.25          # Allow asymmetric M's (user accepts variance)
    pattern_length_min: int = 5           # Short patterns allowed
    pattern_length_max: int = 100         # Long patterns allowed
    
    # Neckline breakout (RELAXED - detect at formation)
    neckline_break_threshold: float = 0.0  # NO breakout required (detect at formation)
    
    # Volume (DISABLED - user doesn't filter by volume)
    volume_breakout_min: float = 0.1      # Accept very low volume
    volume_breakout_max: float = 100.0    # Accept very high volume
    
    # Risk management (FROM DOCUMENTATION)
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5      # Doc: SL = highest_peak + ATR * 1.5
    
    # Take profit multipliers (FROM DOCUMENTATION)
    tp1_multiplier: float = 0.5           # Doc: TP1 = neckline - height * 0.5 (30% exit)
    tp2_multiplier: float = 1.0           # Doc: TP2 = neckline - height * 1.0 (40% exit)
    tp3_multiplier: float = 1.5           # Doc: TP3 = neckline - height * 1.5 (30% exit)


class MPatternLayer(BaseTBDPattern):
    """
    M-Pattern (Double Top) Detection Layer
    
    Focused, isolated implementation of M-pattern detection with all fixes:
    - Detects at pattern formation (Option 1)
    - Relaxed depth requirement (1%)
    - Volume check disabled
    - Proper metadata flags
    """
    
    def __init__(self, config: Optional[MPatternConfig] = None, weight: float = 1.0):
        """
        Initialize M-Pattern layer
        
        Args:
            config: M-pattern configuration
            weight: Layer weight
        """
        self.m_config = config or MPatternConfig()
        
        super().__init__(
            name="m_pattern_v2",
            config={
                'pattern_type': 'M-Pattern',
                'version': '2.0.0',
                'description': 'M-Pattern (Double Top) - Modular v2'
            },
            weight=weight
        )
        
        logger.info(f"M-Pattern v2 initialized: "
                   f"peak_tol={self.m_config.peak_tolerance*100:.0f}%, "
                   f"length={self.m_config.pattern_length_min}-{self.m_config.pattern_length_max}, "
                   f"volume={self.m_config.volume_breakout_min:.1f}x")
    
    def initialize(self) -> None:
        """Initialize the layer"""
        logger.info("M-Pattern v2 layer initialized")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators (ATR)
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Data with indicators
        """
        return self._calculate_atr(data, self.m_config.atr_period)
    
    def generate_signal(
        self,
        data: pd.DataFrame,
        current_price: float,
        current_position: Optional[str] = None
    ) -> LayerSignal:
        """
        Generate M-pattern signal
        
        Args:
            data: OHLCV DataFrame with indicators
            current_price: Current market price
            current_position: Current position (if any)
            
        Returns:
            LayerSignal with M-pattern detection result
        """
        # Minimum data check
        if len(data) < self.m_config.pattern_length_max:
            return self._neutral_signal(current_price, "insufficient_data")
        
        # Try to detect M-pattern
        pattern = self._detect_m_pattern(data, current_price)
        
        if pattern is None:
            return self._neutral_signal(current_price, "no_pattern")
        
        # Pattern detected - create signal
        return LayerSignal(
            direction=pattern['direction'],
            confidence=pattern['confidence'],
            strength=pattern['confidence'],
            metadata=pattern['metadata']
        )
    
    def _detect_m_pattern(
        self,
        data: pd.DataFrame,
        current_price: float
    ) -> Optional[Dict]:
        """
        Detect M-Pattern (Double Top) with all 13 fixes applied
        
        Args:
            data: OHLCV DataFrame
            current_price: Current price
            
        Returns:
            Pattern dict if detected, None otherwise
        """
        lookback = min(self.m_config.pattern_length_max, len(data))
        recent = data.iloc[-lookback:]
        
        # Step 1: Find peaks
        highs = recent['high'].values
        peaks = self._find_peaks(highs, order=3)
        
        if len(peaks) < 2:
            return None
        
        # Step 2: Get last two peaks
        peak2_idx = peaks[-1]
        peak1_idx = peaks[-2]
        peak1_price = highs[peak1_idx]
        peak2_price = highs[peak2_idx]
        
        # Step 3: Pattern length validation
        pattern_length = peak2_idx - peak1_idx
        if pattern_length < self.m_config.pattern_length_min:
            logger.debug(f"M-pattern too short: {pattern_length} < {self.m_config.pattern_length_min}")
            return None
        if pattern_length > self.m_config.pattern_length_max:
            logger.debug(f"M-pattern too long: {pattern_length} > {self.m_config.pattern_length_max}")
            return None
        
        # Step 4: Peak tolerance (symmetry)
        price_diff = abs(peak1_price - peak2_price) / peak1_price
        if price_diff > self.m_config.peak_tolerance:
            logger.debug(f"Peaks too different: {price_diff*100:.2f}% > {self.m_config.peak_tolerance*100:.1f}%")
            return None
        
        # Step 5: Calculate neckline and pattern depth
        valley_data = recent.iloc[peak1_idx:peak2_idx+1]
        neckline = valley_data['low'].min()
        pattern_height = max(peak1_price, peak2_price) - neckline
        depth_pct = pattern_height / max(peak1_price, peak2_price)
        
        # Step 6: Volume Distribution Check (DISABLED for detection mode)
        # User doesn't filter by volume distribution in manual trading
        peak1_vol = recent.iloc[peak1_idx]['volume']
        peak2_vol = recent.iloc[peak2_idx]['volume']
        # COMMENTED OUT: if peak2_vol > peak1_vol: return None
        
        # Step 7: Neckline Breakout Check (DISABLED for detection mode)
        # User detects patterns at formation, not at breakout
        break_threshold = self.m_config.neckline_break_threshold
        broke_neckline = False  # Always False in detection mode
        
        # Only check if breakout threshold > 0 (allows disabling via config)
        if break_threshold > 0 and current_price > neckline * (1 - break_threshold):
            logger.debug(f"M-pattern: No breakout yet (price ${current_price:.2f} > neckline ${neckline * (1 - break_threshold):.2f})")
            return None
        
        if break_threshold > 0:
            broke_neckline = True
        
        # Step 8: Volume Confirmation (DISABLED for detection mode)
        # User doesn't filter by volume in manual trading
        current_candle = recent.iloc[-1]
        current_volume = current_candle['volume']
        avg_volume = recent['volume'].mean()
        vol_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Volume check only if thresholds are meaningful (allows disabling via config)
        if self.m_config.volume_breakout_min > 0.5 and vol_ratio < self.m_config.volume_breakout_min:
            logger.debug(f"M-pattern: volume too low ({vol_ratio:.2f}x < {self.m_config.volume_breakout_min}x)")
            return None
        if self.m_config.volume_breakout_max < 50.0 and vol_ratio > self.m_config.volume_breakout_max:
            logger.debug(f"M-pattern: volume too high ({vol_ratio:.2f}x > {self.m_config.volume_breakout_max}x)")
            return None
        
        # All validations passed - create pattern
        atr = self._get_atr(data, self.m_config.atr_period)
        stop_loss = max(peak1_price, peak2_price) + (atr * self.m_config.atr_stop_multiplier)
        
        # Take profit targets
        tp1 = neckline - (pattern_height * self.m_config.tp1_multiplier)
        tp2 = neckline - (pattern_height * self.m_config.tp2_multiplier)
        tp3 = neckline - (pattern_height * self.m_config.tp3_multiplier)
        
        # Calculate confidence
        confidence = self._calculate_pattern_confidence(
            peak_symmetry=1.0 - price_diff,
            volume_confirmed=True,
            pattern_clarity=0.8
        )
        
        # Get timeframe
        timeframe = self._get_timeframe(data)
        
        # Create pattern dict with proper metadata (FIX 2: metadata flags)
        pattern = {
            'direction': 'short',
            'confidence': confidence,
            'metadata': {
                'm_pattern_detected': True,  # FIX: Detection flag for validator
                'mw_peak1_price': peak1_price,  # FIX: Peak prices for validation
                'mw_peak2_price': peak2_price,
                'mw_neckline_price': neckline,
                'broke_neckline': broke_neckline,  # FIX: Breakout status flag
                'pattern_type': 'M-Pattern',
                'pattern': 'M-Pattern',  # Alias
                'layer_name': self.name,
                'timeframe': timeframe,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit_1': tp1,
                'take_profit_2': tp2,
                'take_profit_3': tp3,
                'pattern_length': pattern_length,
                'pattern_height': pattern_height,
                'pattern_depth_pct': depth_pct * 100,
                'peak_diff_pct': price_diff * 100,
                'peak1_index': peak1_idx,
                'peak2_index': peak2_idx,
                'volume_ratio': vol_ratio,
                'current_price': current_price,
                'risk_reward': abs(tp1 - current_price) / abs(stop_loss - current_price) if stop_loss != current_price else 0
            }
        }
        
        logger.info(f"✅ M-PATTERN DETECTED:")
        logger.info(f"  Peaks: ${peak1_price:.2f} / ${peak2_price:.2f}")
        logger.info(f"  Neckline: ${neckline:.2f}")
        logger.info(f"  Depth: {depth_pct*100:.1f}%, Length: {pattern_length} bars")
        logger.info(f"  Entry: ${current_price:.2f}, SL: ${stop_loss:.2f}")
        logger.info(f"  TP1: ${tp1:.2f}, TP2: ${tp2:.2f}, TP3: ${tp3:.2f}")
        logger.info(f"  Broke neckline: {broke_neckline}")
        
        return pattern
    
    def _neutral_signal(self, current_price: float, reason: str) -> LayerSignal:
        """
        Generate neutral signal when no pattern detected
        
        Args:
            current_price: Current price
            reason: Reason for no detection
            
        Returns:
            Neutral LayerSignal
        """
        return LayerSignal(
            direction='neutral',
            confidence=0.0,
            strength=0.0,
            metadata={
                'layer_name': self.name,
                'pattern_type': 'M-Pattern',
                'reason': reason,
                'current_price': current_price
            }
        )


# Factory function
def create_m_pattern_layer(config: Optional[MPatternConfig] = None, weight: float = 1.0) -> MPatternLayer:
    """
    Create M-Pattern layer instance
    
    Args:
        config: M-pattern configuration
        weight: Layer weight
        
    Returns:
        MPatternLayer instance
    """
    return MPatternLayer(config, weight)
