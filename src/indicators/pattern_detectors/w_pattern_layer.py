"""
W-Pattern Layer (Double Bottom) - TBD v2

W-pattern (bullish reversal) detection - mirror of M-pattern for LONG trades.
- REQUIRES neckline breakout confirmation (≥0.3% break)
- REQUIRES volume spike on breakout (≥1.3x average)
- Volume distribution check (2nd trough ≤ 1st trough)
- Peak tolerance: 10-20% (15% default)
- Pattern length: 10-50 candles

Author: BTC Scalp Bot V10 Framework
Version: 2.1.0 (Mirror of M-Pattern)
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
class WPatternConfig:
    """Configuration for W-Pattern detection (Mirror of M-Pattern)"""
    
    # Pattern geometry (DEFAULT - will be optimized)
    trough_tolerance: float = 0.15        # Max % difference between troughs
    pattern_length_min: int = 10          # Min candles for pattern
    pattern_length_max: int = 50          # Max candles for pattern
    
    # Neckline breakout (REQUIRED)
    neckline_break_threshold: float = 0.003  # 0.3% above neckline
    
    # Volume (REQUIRED on breakout)
    volume_breakout_min: float = 1.3      # >= 1.3x avg volume
    volume_breakout_max: float = 5.0      # Cap at 5x
    
    # Risk management
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5      # SL = lowest_trough - ATR * 1.5
    
    # Take profit multipliers
    tp1_multiplier: float = 0.5           # TP1 = neckline + height * 0.5
    tp2_multiplier: float = 1.0           # TP2 = neckline + height * 1.0
    tp3_multiplier: float = 1.5           # TP3 = neckline + height * 1.5


class WPatternLayer(BaseTBDPattern):
    """W-Pattern (Double Bottom) Detection Layer - Mirror of M-Pattern for LONG"""
    
    def __init__(self, config: Optional[WPatternConfig] = None, weight: float = 1.0):
        self.w_config = config or WPatternConfig()
        
        super().__init__(
            name="w_pattern_v2",
            config={
                'pattern_type': 'W-Pattern',
                'version': '2.0.0',
                'description': 'W-Pattern (Double Bottom) - Modular v2'
            },
            weight=weight
        )
        
        logger.info(f"W-Pattern v2 initialized: "
                   f"trough_tol={self.w_config.trough_tolerance*100:.0f}%, "
                   f"length={self.w_config.pattern_length_min}-{self.w_config.pattern_length_max}")
    
    def initialize(self) -> None:
        logger.info("W-Pattern v2 layer initialized")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        return self._calculate_atr(data, self.w_config.atr_period)
    
    def generate_signal(
        self,
        data: pd.DataFrame,
        current_price: float,
        current_position: Optional[str] = None
    ) -> LayerSignal:
        if len(data) < self.w_config.pattern_length_max:
            return self._neutral_signal(current_price, "insufficient_data")
        
        pattern = self._detect_w_pattern(data, current_price)
        
        if pattern is None:
            return self._neutral_signal(current_price, "no_pattern")
        
        return LayerSignal(
            direction=pattern['direction'],
            confidence=pattern['confidence'],
            strength=pattern['confidence'],
            metadata=pattern['metadata']
        )
    
    def _detect_w_pattern(self, data: pd.DataFrame, current_price: float) -> Optional[Dict]:
        """Detect W-Pattern (Double Bottom) - mirror of M-pattern for LONG"""
        lookback = min(self.w_config.pattern_length_max, len(data))
        recent = data.iloc[-lookback:]
        
        # Find troughs (lows)
        lows = recent['low'].values
        troughs = self._find_troughs(lows, order=3)
        
        if len(troughs) < 2:
            return None
        
        # Get last two troughs
        trough2_idx = troughs[-1]
        trough1_idx = troughs[-2]
        trough1_price = lows[trough1_idx]
        trough2_price = lows[trough2_idx]
        
        # Pattern length validation
        pattern_length = trough2_idx - trough1_idx
        if pattern_length < self.w_config.pattern_length_min or pattern_length > self.w_config.pattern_length_max:
            return None
        
        # Trough tolerance (symmetry)
        price_diff = abs(trough1_price - trough2_price) / trough1_price
        if price_diff > self.w_config.trough_tolerance:
            return None
        
        # Calculate neckline (peak between troughs)
        peak_data = recent.iloc[trough1_idx:trough2_idx+1]
        neckline = peak_data['high'].max()
        pattern_height = neckline - min(trough1_price, trough2_price)
        
        # Volume distribution check (2nd trough ≤ 1st trough for absorption)
        trough1_vol = recent.iloc[trough1_idx]['volume']
        trough2_vol = recent.iloc[trough2_idx]['volume']
        if trough2_vol > trough1_vol:
            logger.debug(f"W-pattern: 2nd trough volume > 1st (absorption failure)")
            return None
        
        # REQUIRE neckline breakout (price ABOVE neckline)
        break_threshold = self.w_config.neckline_break_threshold
        if current_price < neckline * (1 + break_threshold):
            return None
        
        # Volume confirmation
        current_volume = recent.iloc[-1]['volume']
        avg_volume = recent['volume'].mean()
        vol_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        if vol_ratio < self.w_config.volume_breakout_min or vol_ratio > self.w_config.volume_breakout_max:
            return None
        
        # Calculate trade params
        atr = self._get_atr(data, self.w_config.atr_period)
        stop_loss = min(trough1_price, trough2_price) - (atr * self.w_config.atr_stop_multiplier)
        
        tp1 = neckline + (pattern_height * self.w_config.tp1_multiplier)
        tp2 = neckline + (pattern_height * self.w_config.tp2_multiplier)
        tp3 = neckline + (pattern_height * self.w_config.tp3_multiplier)
        
        confidence = self._calculate_pattern_confidence(
            peak_symmetry=1.0 - price_diff,
            volume_confirmed=True,
            pattern_clarity=0.8
        )
        
        timeframe = self._get_timeframe(data)
        
        pattern = {
            'direction': 'long',
            'confidence': confidence,
            'metadata': {
                'w_pattern_detected': True,
                'mw_trough1_price': trough1_price,
                'mw_trough2_price': trough2_price,
                'mw_neckline_price': neckline,
                'broke_neckline': True,
                'pattern_type': 'W-Pattern',
                'pattern': 'W-Pattern',
                'layer_name': self.name,
                'timeframe': timeframe,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit_1': tp1,
                'take_profit_2': tp2,
                'take_profit_3': tp3,
                'pattern_length': pattern_length,
                'pattern_height': pattern_height,
                'volume_ratio': vol_ratio,
                'current_price': current_price
            }
        }
        
        logger.info(f"✅ W-PATTERN DETECTED:")
        logger.info(f"  Troughs: ${trough1_price:.2f} / ${trough2_price:.2f}")
        logger.info(f"  Neckline: ${neckline:.2f}")
        logger.info(f"  Entry: ${current_price:.2f}, SL: ${stop_loss:.2f}")
        logger.info(f"  TP1: ${tp1:.2f}, TP2: ${tp2:.2f}, TP3: ${tp3:.2f}")
        
        return pattern
    
    def _find_troughs(self, data: np.ndarray, order: int = 3) -> list:
        """Find troughs (local minima) in price data"""
        from scipy.signal import argrelmin
        troughs = argrelmin(data, order=order)[0]
        return list(troughs)
    
    def _neutral_signal(self, current_price: float, reason: str) -> LayerSignal:
        return LayerSignal(
            direction='neutral',
            confidence=0.0,
            strength=0.0,
            metadata={
                'layer_name': self.name,
                'pattern_type': 'W-Pattern',
                'reason': reason,
                'current_price': current_price
            }
        )


def create_w_pattern_layer(config: Optional[WPatternConfig] = None, weight: float = 1.0) -> WPatternLayer:
    """Create W-Pattern layer instance"""
    return WPatternLayer(config, weight)
