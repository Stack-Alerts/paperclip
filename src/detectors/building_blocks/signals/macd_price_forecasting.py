"""
MACD Price Forecasting - Building Block
========================================

SIGNAL BLOCK - Generates MACD signals with forward-looking price ranges.

Uses historical trajectory analysis after MACD signals to forecast:
- Upper bound (95th percentile) - aggressive upside
- Average price (50th percentile) - expected value
- Lower bound (5th percentile) - downside support

Signals:
- BULLISH_FORECAST: MACD crosses above signal, forecasted range provided
- BEARISH_FORECAST: MACD crosses below signal, forecasted range provided
- NEUTRAL: No signal

Based on LuxAlgo MACD Price Forecasting concept.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional, Tuple

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
from collections import deque

import logging
logger = logging.getLogger(__name__)

class SignalType(Enum):
    """MACD signal types"""
    BULLISH = "bullish"
    BEARISH = "bearish"


@register_block(
    name='macd_price_forecasting',
    category='SIGNALS',
    class_name='MACDPriceForecasting',
    default_weight=20,
    valid_signals=[
        # Granular forecast signals
        'BEARISH_FORECAST', 'BULLISH_FORECAST',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BEARISH_FORECAST': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish MACD forecast - MACD prediction shows bearish trend. Downside momentum forecasted. Enter shorts or take profit on longs. Machine learning price prediction bearish.'
        },
        'BULLISH_FORECAST': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish MACD forecast - MACD prediction shows bullish trend. Upside momentum forecasted. Enter longs or take profit on shorts. Machine learning price prediction bullish.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot calculate MACD forecasting. Check data quality and required columns.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need enough bars for MACD calculation and forecasting. Wait for more price history.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish MACD - MACD forecast shows upside. Momentum prediction bullish. Long positions favorable. ML-predicted uptrend.'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish MACD - MACD forecast shows downside. Momentum prediction bearish. Short positions favorable. ML-predicted downtrend.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Neutral MACD - No clear MACD forecast direction. No momentum prediction. Wait for clearer signals.'
        }
}
)
class MACDPriceForecasting:
    """
    MACD Price Forecasting Detector
    
    Building Block Classification: SIGNAL BLOCK
    Mode: SELECTIVE (only on MACD signals)
    
    Generates forecasts using historical trajectory analysis.
    Provides percentile-based price ranges.
    
    Designed for 15-min bars.
    """
    
    def __init__(
        self,
        timeframe: str = '15min',
        fast_length: int = 12,
        slow_length: int = 26,
        signal_length: int = 9,
        max_memory: int = 100,
        forecasting_length: int = 20,
        top_percentile: float = 95.0,
        average_percentile: float = 50.0,
        bottom_percentile: float = 5.0,
        min_trajectories: int = 10,
        **kwargs
    ):
        """
        Initialize MACD Price Forecasting detector.
        
        Args:
            <br>timeframe: Timeframe (e.g., '15min')
            fast_length: MACD fast EMA period
            slow_length: MACD slow EMA period
            signal_length: Signal line EMA period
            max_memory: Max historical signals to remember
            forecasting_length: Bars ahead to forecast
            top_percentile: Upper bound percentile
            average_percentile: Mid-range percentile
            bottom_percentile: Lower bound percentile
            min_trajectories: Min signals needed for forecast
        """
        self.timeframe = timeframe
        self.fast_length = fast_length
        self.slow_length = slow_length
        self.signal_length = signal_length
        self.max_memory = max_memory
        self.forecasting_length = forecasting_length
        self.top_percentile = top_percentile
        self.average_percentile = average_percentile
        self.bottom_percentile = bottom_percentile
        self.min_trajectories = min_trajectories
        
        # Historical trajectories storage
        self.bullish_trajectories = deque(maxlen=max_memory)
        self.bearish_trajectories = deque(maxlen=max_memory)
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if granular == 'BULLISH_FORECAST':
            simple = 'BULLISH'
        elif granular == 'BEARISH_FORECAST':
            simple = 'BEARISH'
        else:
            simple = 'NEUTRAL'
        return granular, simple
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for MACD signals and generate forecasts.
        
        Compatible with building block interface.
        """
        # Validation
        required_cols = {'open', 'high', 'low', 'close', 'timestamp'}
        if not required_cols.issubset(df.columns):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        min_bars = max(self.slow_length, self.signal_length) + 50
        if len(df) < min_bars:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {min_bars} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate MACD
        df_macd = self._calculate_macd(df)
        
        # Detect signal on last bar
        current_signal = self._detect_current_signal(df_macd)
        
        if current_signal is None:
            return self._generate_neutral_signal(df['timestamp'].iloc[-1], df['close'].iloc[-1])
        
        # Collect historical trajectories
        self._update_trajectories(df_macd)
        
        # Generate forecast
        return self._generate_forecast_signal(
            current_signal,
            df['timestamp'].iloc[-1],
            df['close'].iloc[-1],
            df_macd
        )
    
    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD, Signal, and Histogram."""
        df_calc = df.copy()
        
        # Calculate EMAs
        fast_ema = df_calc['close'].ewm(span=self.fast_length, adjust=False).mean()
        slow_ema = df_calc['close'].ewm(span=self.slow_length, adjust=False).mean()
        
        # MACD line
        df_calc['macd'] = fast_ema - slow_ema
        
        # Signal line
        df_calc['signal'] = df_calc['macd'].ewm(span=self.signal_length, adjust=False).mean()
        
        # Histogram
        df_calc['histogram'] = df_calc['macd'] - df_calc['signal']
        
        return df_calc
    
    def _detect_current_signal(self, df_macd: pd.DataFrame) -> Optional[SignalType]:
        """Detect if there's a signal on the current bar."""
        if len(df_macd) < 2:
            return None
        
        curr_macd = df_macd['macd'].iloc[-1]
        curr_signal = df_macd['signal'].iloc[-1]
        prev_macd = df_macd['macd'].iloc[-2]
        prev_signal = df_macd['signal'].iloc[-2]
        
        # Bullish cross: MACD crosses above signal
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            return SignalType.BULLISH
        
        # Bearish cross: MACD crosses below signal
        if prev_macd >= prev_signal and curr_macd < curr_signal:
            return SignalType.BEARISH
        
        return None
    
    def _update_trajectories(self, df_macd: pd.DataFrame):
        """Update historical trajectory storage with past signals."""
        # Skip if not enough data
        if len(df_macd) < self.slow_length + self.forecasting_length + 10:
            return
        
        # Scan for historical signals (skip last bar - that's current)
        for i in range(self.slow_length + 10, len(df_macd) - self.forecasting_length - 1):
            signal_type = self._detect_signal_at_index(df_macd, i)
            
            if signal_type is not None:
                # Collect trajectory after this signal
                trajectory = self._collect_trajectory(df_macd, i)
                
                if signal_type == SignalType.BULLISH:
                    if len(self.bullish_trajectories) < self.max_memory:
                        self.bullish_trajectories.append(trajectory)
                else:
                    if len(self.bearish_trajectories) < self.max_memory:
                        self.bearish_trajectories.append(trajectory)
    
    def _detect_signal_at_index(self, df_macd: pd.DataFrame, index: int) -> Optional[SignalType]:
        """Detect signal at specific index."""
        if index < 1:
            return None
        
        curr_macd = df_macd['macd'].iloc[index]
        curr_signal = df_macd['signal'].iloc[index]
        prev_macd = df_macd['macd'].iloc[index - 1]
        prev_signal = df_macd['signal'].iloc[index - 1]
        
        # Bullish cross
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            return SignalType.BULLISH
        
        # Bearish cross
        if prev_macd >= prev_signal and curr_macd < curr_signal:
            return SignalType.BEARISH
        
        return None
    
    def _collect_trajectory(self, df_macd: pd.DataFrame, signal_index: int) -> List[float]:
        """Collect price trajectory after signal."""
        trajectory = []
        
        for i in range(1, self.forecasting_length + 1):
            if signal_index + i < len(df_macd):
                trajectory.append(df_macd['close'].iloc[signal_index + i])
        
        return trajectory
    
    def _generate_forecast_signal(
        self,
        signal_type: SignalType,
        timestamp: datetime,
        current_price: float,
        df_macd: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate forecast signal with percentile ranges."""
        # Get relevant trajectories
        if signal_type == SignalType.BULLISH:
            trajectories = list(self.bullish_trajectories)
            signal_name = 'BULLISH_FORECAST'
        else:
            trajectories = list(self.bearish_trajectories)
            signal_name = 'BEARISH_FORECAST'
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal_name)
        
        # Check if we have enough data
        if len(trajectories) < self.min_trajectories:
            return {
                'signal': signal_name,
                'signal_simple': simple_signal,
                'confidence': 40,  # Low confidence, insufficient history
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': signal_name,
                    'signal_type': signal_type.value,
                    'current_price': round(current_price, 2),
                    'insufficient_history': True,
                    'trajectories_count': len(trajectories),
                    'min_required': self.min_trajectories,
                    'is_new_event': True,
                },
                'timestamp': timestamp,
                'timeframe': self.timeframe,
                'confluence_factors': [
                    f'MACD {signal_type.value} cross',
                    f'Insufficient history ({len(trajectories)}/{self.min_trajectories})',
                ]
            }
        
        # Calculate percentiles
        percentiles = self._calculate_percentiles(trajectories, current_price)
        
        # MACD strength
        macd_value = df_macd['macd'].iloc[-1]
        histogram = df_macd['histogram'].iloc[-1]
        macd_strength = abs(histogram) / (abs(macd_value) + 1e-10)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            len(trajectories),
            percentiles['range_width_pct'],
            macd_strength
        )
        
        return {
            'signal': signal_name,
            'signal_simple': simple_signal,
            'confidence': confidence,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': signal_name,
                'signal_type': signal_type.value,
                'current_price': round(current_price, 2),
                'forecast_upper': round(percentiles['upper'], 2),
                'forecast_average': round(percentiles['average'], 2),
                'forecast_lower': round(percentiles['lower'], 2),
                'forecast_range_width': round(percentiles['range_width'], 2),
                'forecast_range_width_pct': round(percentiles['range_width_pct'], 2),
                'forecast_bars': self.forecasting_length,
                'trajectories_count': len(trajectories),
                'macd': round(macd_value, 4),
                'histogram': round(histogram, 4),
                'macd_strength': round(macd_strength, 4),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'MACD {signal_type.value} cross',
                f'Forecast range: {percentiles["range_width_pct"]:.1f}%',
                f'{len(trajectories)} historical signals',
                f'Target: ${percentiles["upper"]:.2f}',
                f'Support: ${percentiles["lower"]:.2f}',
            ]
        }
    
    def _calculate_percentiles(self, trajectories: List[List[float]], current_price: float) -> Dict[str, float]:
        """Calculate percentile-based forecast ranges."""
        # Get final prices from all trajectories
        final_prices = []
        for traj in trajectories:
            if len(traj) > 0:
                final_prices.append(traj[-1])
        
        if len(final_prices) < 3:
            # Not enough data, use current price with simple range
            return {
                'upper': current_price * 1.02,
                'average': current_price,
                'lower': current_price * 0.98,
                'range_width': current_price * 0.04,
                'range_width_pct': 4.0,
            }
        
        # Calculate percentiles
        upper = np.percentile(final_prices, self.top_percentile)
        average = np.percentile(final_prices, self.average_percentile)
        lower = np.percentile(final_prices, self.bottom_percentile)
        
        range_width = upper - lower
        range_width_pct = (range_width / current_price) * 100
        
        return {
            'upper': upper,
            'average': average,
            'lower': lower,
            'range_width': range_width,
            'range_width_pct': range_width_pct,
        }
    
    def _calculate_confidence(
        self,
        trajectory_count: int,
        range_width_pct: float,
        macd_strength: float
    ) -> int:
        """Calculate forecast confidence."""
        # Base confidence on trajectory count
        if trajectory_count >= 50:
            base = 75
        elif trajectory_count >= 30:
            base = 70
        elif trajectory_count >= 20:
            base = 65
        else:
            base = 60
        
        # Adjust for range width (tighter = more confident)
        if range_width_pct < 2.0:
            base += 10
        elif range_width_pct < 4.0:
            base += 5
        elif range_width_pct > 8.0:
            base -= 5
        elif range_width_pct > 12.0:
            base -= 10
        
        # Adjust for MACD strength
        if macd_strength > 0.5:
            base += 5
        elif macd_strength < 0.2:
            base -= 5
        
        return max(40, min(85, base))
    
    def _generate_neutral_signal(self, timestamp: datetime, current_price: float) -> Dict[str, Any]:
        """Generate neutral signal when no MACD cross."""
        return {
            'signal': 'NEUTRAL',
            'confidence': 50,
            'metadata': {
                'current_price': round(current_price, 2),
                'bullish_trajectories': len(self.bullish_trajectories),
                'bearish_trajectories': len(self.bearish_trajectories),
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                'No MACD signal',
            ]
        }


if __name__ == "__main__":
    logger.info("MACD Price Forecasting - Building Block")
    logger.info("SIGNAL BLOCK - Forward-looking MACD with percentile ranges")
    logger.info("Based on LuxAlgo MACD Price Forecasting")
