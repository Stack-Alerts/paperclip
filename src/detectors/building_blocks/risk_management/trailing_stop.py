"""
Trailing Stop - Building Block
===============================

CONTEXT BLOCK - Provides dynamic trailing stop levels based on volatility.

Statistical trailing stop using ATR and volatility distribution:
- Calculates 4 levels from responsive (0) to stable (3)
- Level 0: 0.8x ATR (tight, responsive)
- Level 1: 1.2x ATR (standard)
- Level 2: 1.6x ATR (balanced) ← Most popular
- Level 3: 2.0x ATR (wide, trend-following)

Signals:
- LONG_STOP_TEST: Price testing long stop (potential bounce up)
- SHORT_STOP_TEST: Price testing short stop (potential bounce down)
- LONG_STOP_HOLD: Price above long stop (hold)
- SHORT_STOP_HOLD: Price below short stop (hold)
- NEUTRAL: No stop interaction

Based on LuxAlgo Statistical Trailing Stop concept.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='trailing_stop',
    category='RISK_MANAGEMENT',
    class_name='TrailingStop',
    default_weight=8,
    valid_signals=[
        # Granular risk signals
        'STOP_TRIGGERED', 'STOP_UPDATED', 'STOP_ACTIVE', 'NO_STOP',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Granular risk signals
        'STOP_TRIGGERED': {
                'base_points': 12,
                'formula': 'scaled'
        },
        'STOP_UPDATED': {
                'base_points': 8,
                'formula': 'scaled'
        },
        'STOP_ACTIVE': {
                'base_points': 5,
                'formula': 'scaled'
        },
        'NO_STOP': {
                'points': 0
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 8,
                'formula': 'scaled'
        },
        'BEARISH': {
                'base_points': 8,
                'formula': 'scaled'
        },
        'NEUTRAL': {
                'points': 0
        },
        
        # Status
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        }
}
)
class TrailingStop:
    """
    Trailing Stop Detector
    
    Building Block Classification: CONTEXT BLOCK
    Mode: ALWAYS ACTIVE (provides stop levels continuously)
    
    Calculates dynamic trailing stops based on ATR and volatility.
    Provides 4 levels for different trading styles.
    
    Designed for 15-min bars.
    """
    
    def __init__(
        self,
        timeframe: str = '15min',
        atr_period: int = 14,
        level_0_mult: float = 0.8,  # Responsive
        level_1_mult: float = 1.2,  # Standard
        level_2_mult: float = 1.6,  # Balanced
        level_3_mult: float = 2.0,  # Stable
        test_threshold: float = 0.005,  # 0.5% for "test" detection (tuned)
        **kwargs
    ):
        """
        Initialize Trailing Stop detector.
        
        Args:
            timeframe: Timeframe (e.g., '15min')
            atr_period: Period for ATR calculation
            level_0_mult: Multiplier for level 0 (tight)
            level_1_mult: Multiplier for level 1 (standard)
            level_2_mult: Multiplier for level 2 (balanced)
            level_3_mult: Multiplier for level 3 (wide)
            test_threshold: Distance threshold for "testing" stop
        """
        self.timeframe = timeframe
        self.atr_period = atr_period
        self.level_multipliers = [
            level_0_mult,
            level_1_mult,
            level_2_mult,
            level_3_mult
        ]
        self.test_threshold = test_threshold
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if 'LONG' in granular:
            simple = 'BULLISH'  # Long stops = bullish context
        elif 'SHORT' in granular:
            simple = 'BEARISH'  # Short stops = bearish context
        else:
            simple = 'NEUTRAL'
        return granular, simple
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for trailing stop levels and signals.
        
        Compatible with building block interface.
        """
        # Validation
        required_cols = {'open', 'high', 'low', 'close', 'timestamp'}
        if not required_cols.issubset(df.columns):
            granular_signal, simple_signal = self._determine_dual_signals('ERROR')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'error': 'Missing required columns'
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.atr_period + 10:
            granular_signal, simple_signal = self._determine_dual_signals('INSUFFICIENT_DATA')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'error': f'Need at least {self.atr_period + 10} bars'
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_time = df['timestamp'].iloc[-1]
        current_close = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # Calculate ATR
        atr = self._calculate_atr(df)
        
        # Calculate trailing stops for all levels
        stops_long, stops_short = self._calculate_stops(df, atr)
        
        # Determine signal based on price vs stops
        return self._generate_signal(
            current_time, current_close, current_high, current_low,
            stops_long, stops_short, atr
        )
    
    def _calculate_atr(self, df: pd.DataFrame) -> float:
        """Calculate Average True Range."""
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # True Range calculation
        tr_list = []
        for i in range(1, len(df)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
            tr_list.append(tr)
        
        # ATR is average of recent TRs
        atr = np.mean(tr_list[-self.atr_period:]) if tr_list else 0.0
        return atr
    
    def _calculate_stops(
        self, df: pd.DataFrame, atr: float
    ) -> tuple:
        """Calculate trailing stops for all 4 levels."""
        current_close = df['close'].iloc[-1]
        
        # Long stops (below price)
        stops_long = [
            current_close - (atr * mult)
            for mult in self.level_multipliers
        ]
        
        # Short stops (above price)
        stops_short = [
            current_close + (atr * mult)
            for mult in self.level_multipliers
        ]
        
        return stops_long, stops_short
    
    def _generate_signal(
        self,
        timestamp: datetime,
        close: float,
        high: float,
        low: float,
        stops_long: List[float],
        stops_short: List[float],
        atr: float
    ) -> Dict[str, Any]:
        """Generate signal based on price vs stops."""
        # Check if testing any long stop (price dipping toward stop)
        for level, stop in enumerate(stops_long):
            # Calculate how close low came to stop
            distance_to_stop = abs(low - stop)
            distance_pct = distance_to_stop / close
            
            # Only test if low came close to stop AND is below close (dip)
            if distance_pct <= self.test_threshold and low < stop:
                # Testing long stop (potential bounce)
                return self._generate_long_test_signal(
                    timestamp, close, stops_long, stops_short, level, atr
                )
        
        # Check if testing any short stop (price rising toward stop)
        for level, stop in enumerate(stops_short):
            # Calculate how close high came to stop
            distance_to_stop = abs(high - stop)
            distance_pct = distance_to_stop / close
            
            # Only test if high came close to stop AND is above close (spike)
            if distance_pct <= self.test_threshold and high > stop:
                # Testing short stop (potential bounce down)
                return self._generate_short_test_signal(
                    timestamp, close, stops_long, stops_short, level, atr
                )
        
        # Check if holding above long stops
        if close > stops_long[2]:  # Above level 2 (balanced)
            return self._generate_long_hold_signal(
                timestamp, close, stops_long, stops_short, atr
            )
        
        # Check if holding below short stops
        if close < stops_short[2]:  # Below level 2 (balanced)
            return self._generate_short_hold_signal(
                timestamp, close, stops_long, stops_short, atr
            )
        
        # Neutral - between stops
        return self._generate_neutral_signal(
            timestamp, close, stops_long, stops_short, atr
        )
    
    def _generate_long_test_signal(
        self,
        timestamp: datetime,
        close: float,
        stops_long: List[float],
        stops_short: List[float],
        level: int,
        atr: float
    ) -> Dict[str, Any]:
        """Generate signal when testing long stop."""
        distance_from_stop = close - stops_long[level]
        distance_pct = (distance_from_stop / close) * 100
        
        # Confidence based on how close to stop
        if distance_pct < 0.1:
            confidence = 70
        elif distance_pct < 0.3:
            confidence = 65
        else:
            confidence = 60
        
        granular_signal, simple_signal = self._determine_dual_signals('LONG_STOP_TEST')
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': confidence,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'tested_level': level,
                'level_name': ['Tight', 'Standard', 'Balanced', 'Wide'][level],
                'stop_long_0': round(stops_long[0], 2),
                'stop_long_1': round(stops_long[1], 2),
                'stop_long_2': round(stops_long[2], 2),
                'stop_long_3': round(stops_long[3], 2),
                'stop_short_2': round(stops_short[2], 2),
                'atr': round(atr, 2),
                'atr_pct': round((atr / close) * 100, 2),
                'distance_from_stop': round(distance_from_stop, 2),
                'distance_from_stop_pct': round(distance_pct, 2),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Testing long stop L{level}',
                f'Potential bounce zone',
                f'ATR: {atr:.2f} ({(atr/close)*100:.1f}%)',
                f'Stop: {stops_long[level]:.2f}',
            ]
        }
    
    def _generate_short_test_signal(
        self,
        timestamp: datetime,
        close: float,
        stops_long: List[float],
        stops_short: List[float],
        level: int,
        atr: float
    ) -> Dict[str, Any]:
        """Generate signal when testing short stop."""
        distance_from_stop = stops_short[level] - close
        distance_pct = (distance_from_stop / close) * 100
        
        # Confidence based on how close to stop
        if distance_pct < 0.1:
            confidence = 70
        elif distance_pct < 0.3:
            confidence = 65
        else:
            confidence = 60
        
        granular_signal, simple_signal = self._determine_dual_signals('SHORT_STOP_TEST')
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': confidence,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'tested_level': level,
                'level_name': ['Tight', 'Standard', 'Balanced', 'Wide'][level],
                'stop_short_0': round(stops_short[0], 2),
                'stop_short_1': round(stops_short[1], 2),
                'stop_short_2': round(stops_short[2], 2),
                'stop_short_3': round(stops_short[3], 2),
                'stop_long_2': round(stops_long[2], 2),
                'atr': round(atr, 2),
                'atr_pct': round((atr / close) * 100, 2),
                'distance_from_stop': round(distance_from_stop, 2),
                'distance_from_stop_pct': round(distance_pct, 2),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Testing short stop L{level}',
                f'Potential bounce down',
                f'ATR: {atr:.2f} ({(atr/close)*100:.1f}%)',
                f'Stop: {stops_short[level]:.2f}',
            ]
        }
    
    def _generate_long_hold_signal(
        self,
        timestamp: datetime,
        close: float,
        stops_long: List[float],
        stops_short: List[float],
        atr: float
    ) -> Dict[str, Any]:
        """Generate signal when holding above long stop."""
        granular_signal, simple_signal = self._determine_dual_signals('LONG_STOP_HOLD')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 55,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'stop_long_0': round(stops_long[0], 2),
                'stop_long_1': round(stops_long[1], 2),
                'stop_long_2': round(stops_long[2], 2),
                'stop_long_3': round(stops_long[3], 2),
                'atr': round(atr, 2),
                'atr_pct': round((atr / close) * 100, 2),
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                'Above long stops',
                'Hold long position',
                f'ATR: {atr:.2f}',
            ]
        }
    
    def _generate_short_hold_signal(
        self,
        timestamp: datetime,
        close: float,
        stops_long: List[float],
        stops_short: List[float],
        atr: float
    ) -> Dict[str, Any]:
        """Generate signal when holding below short stop."""
        granular_signal, simple_signal = self._determine_dual_signals('SHORT_STOP_HOLD')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 55,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'stop_short_0': round(stops_short[0], 2),
                'stop_short_1': round(stops_short[1], 2),
                'stop_short_2': round(stops_short[2], 2),
                'stop_short_3': round(stops_short[3], 2),
                'atr': round(atr, 2),
                'atr_pct': round((atr / close) * 100, 2),
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                'Below short stops',
                'Hold short position',
                f'ATR: {atr:.2f}',
            ]
        }
    
    def _generate_neutral_signal(
        self,
        timestamp: datetime,
        close: float,
        stops_long: List[float],
        stops_short: List[float],
        atr: float
    ) -> Dict[str, Any]:
        """Generate neutral signal."""
        granular_signal, simple_signal = self._determine_dual_signals('NEUTRAL')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 50,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'stop_long_2': round(stops_long[2], 2),
                'stop_short_2': round(stops_short[2], 2),
                'atr': round(atr, 2),
                'atr_pct': round((atr / close) * 100, 2),
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                'Between stop levels',
                f'ATR: {atr:.2f}',
            ]
        }


if __name__ == "__main__":
    print("Trailing Stop - Building Block")
    print("CONTEXT BLOCK - Dynamic stop levels based on volatility")
    print("Based on LuxAlgo Statistical Trailing Stop")
