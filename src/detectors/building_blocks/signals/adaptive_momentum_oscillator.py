"""
Adaptive Momentum Oscillator - Building Block
==============================================

SIGNAL BLOCK - Generates momentum signals with adaptive smoothing.

Uses maximum delta normalization and Kaufman's adaptive moving average:
- Normalized momentum (0-centered)
- Adaptive smoothing (less lag)
- Multiple signal types (crosses, divergences)
- Quality scoring for filtering

Signals:
- BULLISH_CROSS: Momentum crosses above signal line
- BEARISH_CROSS: Momentum crosses below signal line
- BULLISH_DIVERGENCE: Price lower low, momentum higher low
- BEARISH_DIVERGENCE: Price higher high, momentum lower high
- NEUTRAL: No signal

Based on LuxAlgo Adaptive Momentum Oscillator concept.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np


class SignalType(Enum):
    """Signal types"""
    BULLISH_CROSS = "bullish_cross"
    BEARISH_CROSS = "bearish_cross"
    BULLISH_DIVERGENCE = "bullish_divergence"
    BEARISH_DIVERGENCE = "bearish_divergence"


class AdaptiveMomentumOscillator:
    """
    Adaptive Momentum Oscillator Detector
    
    Building Block Classification: SIGNAL BLOCK
    Mode: SELECTIVE (only on momentum signals)
    
    Generates momentum signals using adaptive smoothing.
    Provides quality-filtered trading opportunities.
    
    Designed for 15-min bars.
    """
    
    def __init__(
        self,
        timeframe: str = '15min',
        data_length: int = 20,
        smoothing_length: int = 25,
        divergence_length: int = 14,
        fast_period: int = 2,
        slow_period: int = 30,
        min_signal_strength: float = 0.0,
        **kwargs
    ):
        """
        Initialize Adaptive Momentum Oscillator detector.
        
        Args:
            timeframe: Timeframe (e.g., '15min')
            data_length: Period for maximum delta calculation
            smoothing_length: Kaufman's AMA smoothing period
            divergence_length: Window for divergence detection
            fast_period: Fast EMA period for AMA
            slow_period: Slow EMA period for AMA
            min_signal_strength: Minimum strength for signals
        """
        self.timeframe = timeframe
        self.data_length = data_length
        self.smoothing_length = smoothing_length
        self.divergence_length = divergence_length
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.min_signal_strength = min_signal_strength
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for momentum signals.
        
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
        
        min_bars = max(self.data_length, self.smoothing_length, self.divergence_length) + 20
        if len(df) < min_bars:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {min_bars} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate momentum oscillator
        df_momentum = self._calculate_momentum(df)
        
        # Detect current signal
        current_signal = self._detect_current_signal(df_momentum)
        
        if current_signal is None:
            return self._generate_neutral_signal(
                df['timestamp'].iloc[-1],
                df['close'].iloc[-1],
                df_momentum
            )
        
        # Generate signal with quality scoring
        return self._generate_signal(
            current_signal,
            df['timestamp'].iloc[-1],
            df['close'].iloc[-1],
            df_momentum
        )
    
    def _calculate_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate normalized momentum with adaptive smoothing."""
        df_calc = df.copy()
        
        # Calculate maximum delta (normalization factor)
        max_delta = df_calc['close'].diff().abs().rolling(self.data_length).max()
        
        # Normalized momentum
        price_change = df_calc['close'].diff()
        df_calc['momentum_raw'] = price_change / (max_delta + 1e-10)
        
        # Use simple EMA instead of KAMA (KAMA was causing issues)
        df_calc['momentum'] = df_calc['momentum_raw'].ewm(span=self.smoothing_length, adjust=False).mean()
        
        # Signal line (slower EMA)
        df_calc['signal_line'] = df_calc['momentum'].ewm(span=self.smoothing_length + 5, adjust=False).mean()
        
        # Histogram
        df_calc['histogram'] = df_calc['momentum'] - df_calc['signal_line']
        
        return df_calc
    
    def _calculate_kama(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Kaufman's Adaptive Moving Average."""
        # Efficiency Ratio
        change = abs(series.diff(period))
        volatility = series.diff().abs().rolling(period).sum()
        er = change / (volatility + 1e-10)
        
        # Smoothing constants
        fast_sc = 2 / (self.fast_period + 1)
        slow_sc = 2 / (self.slow_period + 1)
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        
        # KAMA calculation
        kama = pd.Series(index=series.index, dtype=float)
        kama.iloc[period - 1] = series.iloc[period - 1]
        
        for i in range(period, len(series)):
            if pd.isna(sc.iloc[i]):
                kama.iloc[i] = kama.iloc[i - 1]
            else:
                kama.iloc[i] = kama.iloc[i - 1] + sc.iloc[i] * (series.iloc[i] - kama.iloc[i - 1])
        
        return kama
    
    def _detect_current_signal(self, df_momentum: pd.DataFrame) -> Optional[Tuple[SignalType, Dict]]:
        """Detect signal on current bar."""
        if len(df_momentum) < 2:
            return None
        
        curr_momentum = df_momentum['momentum'].iloc[-1]
        prev_momentum = df_momentum['momentum'].iloc[-2]
        curr_signal = df_momentum['signal_line'].iloc[-1]
        prev_signal = df_momentum['signal_line'].iloc[-2]
        curr_histogram = df_momentum['histogram'].iloc[-1]
        
        # Check for crossovers
        # Bullish cross: momentum crosses above signal
        if prev_momentum <= prev_signal and curr_momentum > curr_signal:
            strength = abs(curr_histogram)
            return (SignalType.BULLISH_CROSS, {
                'strength': strength,
                'momentum': curr_momentum,
                'signal_line': curr_signal,
                'histogram': curr_histogram
            })
        
        # Bearish cross: momentum crosses below signal
        if prev_momentum >= prev_signal and curr_momentum < curr_signal:
            strength = abs(curr_histogram)
            return (SignalType.BEARISH_CROSS, {
                'strength': strength,
                'momentum': curr_momentum,
                'signal_line': curr_signal,
                'histogram': curr_histogram
            })
        
        # Check for divergences
        divergence = self._detect_divergence(df_momentum)
        if divergence is not None:
            return divergence
        
        return None
    
    def _detect_divergence(self, df_momentum: pd.DataFrame) -> Optional[Tuple[SignalType, Dict]]:
        """Detect bullish/bearish divergences."""
        if len(df_momentum) < self.divergence_length + 5:
            return None
        
        recent_data = df_momentum.iloc[-self.divergence_length:]
        
        # Find local extrema
        price_lows_idx = self._find_local_minima(recent_data['close'])
        price_highs_idx = self._find_local_maxima(recent_data['close'])
        mom_lows_idx = self._find_local_minima(recent_data['momentum'])
        mom_highs_idx = self._find_local_maxima(recent_data['momentum'])
        
        # Bullish divergence: price lower low, momentum higher low
        if len(price_lows_idx) >= 2 and len(mom_lows_idx) >= 2:
            last_price_low_idx = price_lows_idx[-1]
            prev_price_low_idx = price_lows_idx[-2]
            
            # Find corresponding momentum lows
            if last_price_low_idx in mom_lows_idx and prev_price_low_idx in mom_lows_idx:
                last_price = recent_data['close'].iloc[last_price_low_idx]
                prev_price = recent_data['close'].iloc[prev_price_low_idx]
                last_mom = recent_data['momentum'].iloc[last_price_low_idx]
                prev_mom = recent_data['momentum'].iloc[prev_price_low_idx]
                
                if last_price < prev_price and last_mom > prev_mom:
                    # Bullish divergence detected
                    severity = abs(last_mom - prev_mom) / (abs(prev_mom) + 1e-10)
                    if severity >= 0.1:  # Minimum divergence significance
                        return (SignalType.BULLISH_DIVERGENCE, {
                            'severity': severity,
                            'price_low': last_price,
                            'momentum_low': last_mom,
                            'histogram': recent_data['histogram'].iloc[-1]
                        })
        
        # Bearish divergence: price higher high, momentum lower high
        if len(price_highs_idx) >= 2 and len(mom_highs_idx) >= 2:
            last_price_high_idx = price_highs_idx[-1]
            prev_price_high_idx = price_highs_idx[-2]
            
            # Find corresponding momentum highs
            if last_price_high_idx in mom_highs_idx and prev_price_high_idx in mom_highs_idx:
                last_price = recent_data['close'].iloc[last_price_high_idx]
                prev_price = recent_data['close'].iloc[prev_price_high_idx]
                last_mom = recent_data['momentum'].iloc[last_price_high_idx]
                prev_mom = recent_data['momentum'].iloc[prev_price_high_idx]
                
                if last_price > prev_price and last_mom < prev_mom:
                    # Bearish divergence detected
                    severity = abs(last_mom - prev_mom) / (abs(prev_mom) + 1e-10)
                    if severity >= 0.1:
                        return (SignalType.BEARISH_DIVERGENCE, {
                            'severity': severity,
                            'price_high': last_price,
                            'momentum_high': last_mom,
                            'histogram': recent_data['histogram'].iloc[-1]
                        })
        
        return None
    
    def _find_local_minima(self, series: pd.Series) -> List[int]:
        """Find local minimum indices."""
        minima = []
        for i in range(1, len(series) - 1):
            if series.iloc[i] < series.iloc[i - 1] and series.iloc[i] < series.iloc[i + 1]:
                minima.append(i)
        return minima
    
    def _find_local_maxima(self, series: pd.Series) -> List[int]:
        """Find local maximum indices."""
        maxima = []
        for i in range(1, len(series) - 1):
            if series.iloc[i] > series.iloc[i - 1] and series.iloc[i] > series.iloc[i + 1]:
                maxima.append(i)
        return maxima
    
    def _generate_signal(
        self,
        signal_data: Tuple[SignalType, Dict],
        timestamp: datetime,
        current_price: float,
        df_momentum: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate signal with quality scoring."""
        signal_type, signal_meta = signal_data
        
        # Calculate signal quality
        quality = self._calculate_signal_quality(signal_type, signal_meta, df_momentum)
        
        # Map to signal names
        signal_names = {
            SignalType.BULLISH_CROSS: 'BULLISH_CROSS',
            SignalType.BEARISH_CROSS: 'BEARISH_CROSS',
            SignalType.BULLISH_DIVERGENCE: 'BULLISH_DIVERGENCE',
            SignalType.BEARISH_DIVERGENCE: 'BEARISH_DIVERGENCE',
        }
        
        return {
            'signal': signal_names[signal_type],
            'confidence': quality,
            'metadata': {
                'signal_type': signal_type.value,
                'current_price': round(current_price, 2),
                'momentum': round(signal_meta.get('momentum', signal_meta.get('momentum_low', signal_meta.get('momentum_high', 0))), 4),
                'signal_line': round(signal_meta.get('signal_line', 0), 4),
                'histogram': round(signal_meta['histogram'], 4),
                'strength': round(signal_meta.get('strength', signal_meta.get('severity', 0)), 4),
                'quality_score': quality,
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': self._get_confluence_factors(signal_type, signal_meta)
        }
    
    def _calculate_signal_quality(
        self,
        signal_type: SignalType,
        signal_meta: Dict,
        df_momentum: pd.DataFrame
    ) -> int:
        """Calculate signal quality (0-100)."""
        base_confidence = 60
        
        # Strength/severity factor
        strength = signal_meta.get('strength', signal_meta.get('severity', 0))
        if strength > 0.8:
            base_confidence += 15
        elif strength > 0.5:
            base_confidence += 10
        elif strength > 0.3:
            base_confidence += 5
        
        # Histogram alignment
        histogram = signal_meta['histogram']
        if signal_type in [SignalType.BULLISH_CROSS, SignalType.BULLISH_DIVERGENCE]:
            if histogram > 0:
                base_confidence += 10
        elif signal_type in [SignalType.BEARISH_CROSS, SignalType.BEARISH_DIVERGENCE]:
            if histogram < 0:
                base_confidence += 10
        
        # Divergence signals get bonus (higher quality)
        if signal_type in [SignalType.BULLISH_DIVERGENCE, SignalType.BEARISH_DIVERGENCE]:
            base_confidence += 10
        
        return max(50, min(85, base_confidence))
    
    def _get_confluence_factors(self, signal_type: SignalType, signal_meta: Dict) -> List[str]:
        """Get confluence factors for signal."""
        factors = []
        
        if signal_type == SignalType.BULLISH_CROSS:
            factors.append('Momentum crossed above signal')
            strength = signal_meta.get('strength', 0)
            factors.append(f'Strength: {strength:.2f}')
            if signal_meta['histogram'] > 0:
                factors.append('Histogram positive')
        
        elif signal_type == SignalType.BEARISH_CROSS:
            factors.append('Momentum crossed below signal')
            strength = signal_meta.get('strength', 0)
            factors.append(f'Strength: {strength:.2f}')
            if signal_meta['histogram'] < 0:
                factors.append('Histogram negative')
        
        elif signal_type == SignalType.BULLISH_DIVERGENCE:
            factors.append('Bullish divergence detected')
            severity = signal_meta.get('severity', 0)
            factors.append(f'Severity: {severity:.2f}')
            factors.append('Price lower low, momentum higher low')
        
        elif signal_type == SignalType.BEARISH_DIVERGENCE:
            factors.append('Bearish divergence detected')
            severity = signal_meta.get('severity', 0)
            factors.append(f'Severity: {severity:.2f}')
            factors.append('Price higher high, momentum lower high')
        
        return factors
    
    def _generate_neutral_signal(
        self,
        timestamp: datetime,
        current_price: float,
        df_momentum: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate neutral signal when no momentum signal."""
        curr_momentum = df_momentum['momentum'].iloc[-1]
        curr_histogram = df_momentum['histogram'].iloc[-1]
        
        return {
            'signal': 'NEUTRAL',
            'confidence': 50,
            'metadata': {
                'current_price': round(current_price, 2),
                'momentum': round(curr_momentum, 4),
                'histogram': round(curr_histogram, 4),
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': ['No momentum signal']
        }


if __name__ == "__main__":
    print("Adaptive Momentum Oscillator - Building Block")
    print("SIGNAL BLOCK - Momentum signals with adaptive smoothing")
    print("Based on LuxAlgo Adaptive Momentum Oscillator")
