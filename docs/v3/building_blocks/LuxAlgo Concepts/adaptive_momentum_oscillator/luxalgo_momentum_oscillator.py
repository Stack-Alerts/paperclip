"""
LuxAlgo Adaptive Momentum Oscillator - Core Implementation
==========================================================

Adaptive momentum oscillator using maximum delta with adaptive moving average
smoothing, divergence detection, and signal line crossover analysis.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class DataSource(Enum):
    """Data source for momentum calculation."""
    CLOSE = 'close'
    HIGH = 'high'
    LOW = 'low'
    HL2 = 'hl2'
    HLC3 = 'hlc3'
    OHLC4 = 'ohlc4'


class MomentumSignal(Enum):
    """Momentum signal type."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    ACCELERATION = 'acceleration'
    DECELERATION = 'deceleration'
    DIVERGENCE_BULLISH = 'divergence_bullish'
    DIVERGENCE_BEARISH = 'divergence_bearish'
    NONE = 'none'


@dataclass
class MomentumValue:
    """Momentum value at a point in time."""
    timestamp: pd.Timestamp
    momentum: float
    signal_line: float
    histogram: float
    adaptive_ma: float
    direction: str


@dataclass
class MomentumSignalPoint:
    """Momentum signal occurrence."""
    timestamp: pd.Timestamp
    momentum: float
    signal_line: float
    histogram: float
    signal_type: MomentumSignal
    strength: float
    momentum_velocity: float


@dataclass
class DivergenceDetection:
    """Detected divergence."""
    timestamp: pd.Timestamp
    divergence_type: MomentumSignal
    price_level: float
    momentum_level: float
    divergence_bars: int
    severity: float


class AdaptiveMovingAverage:
    """Adaptive moving average using efficiency ratio."""
    
    def __init__(self, length: int = 10):
        self.length = length
    
    def calculate_ama(self, series: pd.Series, smoothing_length: int = 10) -> pd.Series:
        """Calculate Adaptive Moving Average using Kaufman's AMA."""
        change = (series - series.shift(self.length)).abs()
        volatility = (series.diff()).abs().rolling(self.length).sum()
        
        er = change / (volatility + 1e-10)
        
        fastest = 2.0 / (2 + 1)
        slowest = 2.0 / (30 + 1)
        smoothing = er * (fastest - slowest) + slowest
        ssc = smoothing ** 2
        
        ama_val = series.iloc[0]
        ama_list = [ama_val]
        
        for i in range(1, len(series)):
            ama_val = ama_val + ssc.iloc[i] * (series.iloc[i] - ama_val)
            ama_list.append(ama_val)
        
        return pd.Series(ama_list, index=series.index)


class MomentumCalculator:
    """Calculate adaptive momentum oscillator."""
    
    def __init__(
        self,
        data_length: int = 20,
        smoothing_length: int = 10,
        data_source: DataSource = DataSource.CLOSE,
    ):
        self.data_length = data_length
        self.smoothing_length = smoothing_length
        self.data_source = data_source
        self.ama_calculator = AdaptiveMovingAverage(length=data_length)
    
    def get_source_data(self, df: pd.DataFrame) -> pd.Series:
        """Extract data source from DataFrame."""
        if self.data_source == DataSource.CLOSE:
            return df['close']
        elif self.data_source == DataSource.HIGH:
            return df['high']
        elif self.data_source == DataSource.LOW:
            return df['low']
        elif self.data_source == DataSource.HL2:
            return (df['high'] + df['low']) / 2
        elif self.data_source == DataSource.HLC3:
            return (df['high'] + df['low'] + df['close']) / 3
        elif self.data_source == DataSource.OHLC4:
            return (df['open'] + df['high'] + df['low'] + df['close']) / 4
        else:
            return df['close']
    
    def calculate_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate adaptive momentum oscillator."""
        df_result = df.copy()
        
        source = self.get_source_data(df)
        
        max_delta = source.rolling(self.data_length).apply(
            lambda x: np.max(np.abs(np.diff(x))),
            raw=False
        )
        
        momentum = source.diff(self.data_length) / (max_delta + 1e-10)
        
        ama = self.ama_calculator.calculate_ama(momentum, self.smoothing_length)
        
        signal_line = momentum.ewm(span=self.smoothing_length, adjust=False).mean()
        
        histogram = momentum - signal_line
        
        df_result['momentum'] = momentum
        df_result['momentum_ama'] = ama
        df_result['momentum_signal'] = signal_line
        df_result['momentum_histogram'] = histogram
        df_result['momentum_direction'] = momentum.apply(
            lambda x: 'positive' if x > 0 else 'negative'
        )
        
        return df_result
    
    def detect_signals(self, df: pd.DataFrame) -> List[MomentumSignalPoint]:
        """Detect momentum signals (crossovers)."""
        signals = []
        
        for i in range(1, len(df)):
            prev_momentum = df.iloc[i-1]['momentum']
            curr_momentum = df.iloc[i]['momentum']
            prev_signal = df.iloc[i-1]['momentum_signal']
            curr_signal = df.iloc[i]['momentum_signal']
            
            signal_type = MomentumSignal.NONE
            strength = 0.0
            
            if prev_momentum <= prev_signal and curr_momentum > curr_signal:
                signal_type = MomentumSignal.BULLISH
            elif prev_momentum >= prev_signal and curr_momentum < curr_signal:
                signal_type = MomentumSignal.BEARISH
            
            if prev_momentum <= 0 and curr_momentum > 0:
                signal_type = MomentumSignal.BULLISH
            elif prev_momentum >= 0 and curr_momentum < 0:
                signal_type = MomentumSignal.BEARISH
            
            if i > 1:
                prev_prev_momentum = df.iloc[i-2]['momentum']
                momentum_change = curr_momentum - prev_momentum
                
                if abs(momentum_change) > 0 and prev_momentum != 0:
                    if curr_momentum > prev_momentum:
                        signal_type = MomentumSignal.ACCELERATION
                    else:
                        signal_type = MomentumSignal.DECELERATION
            
            if signal_type != MomentumSignal.NONE:
                strength = min(1.0, abs(curr_momentum))
                momentum_velocity = curr_momentum - prev_momentum
                
                signal = MomentumSignalPoint(
                    timestamp=df.index[i],
                    momentum=curr_momentum,
                    signal_line=curr_signal,
                    histogram=df.iloc[i]['momentum_histogram'],
                    signal_type=signal_type,
                    strength=strength,
                    momentum_velocity=momentum_velocity,
                )
                signals.append(signal)
        
        return signals


class DivergenceDetector:
    """Detect divergences in price and momentum."""
    
    def __init__(self, divergence_length: int = 14):
        self.divergence_length = divergence_length
    
    def find_peaks_troughs(
        self, series: pd.Series, window: int
    ) -> Tuple[List[int], List[int]]:
        """Find peaks and troughs in series."""
        peaks = []
        troughs = []
        
        for i in range(window, len(series) - window):
            window_data = series.iloc[i-window:i+window+1]
            
            if series.iloc[i] == window_data.max():
                peaks.append(i)
            elif series.iloc[i] == window_data.min():
                troughs.append(i)
        
        return peaks, troughs
    
    def detect_divergences(
        self, df: pd.DataFrame, price_col: str = 'close'
    ) -> List[DivergenceDetection]:
        """Detect divergences between price and momentum."""
        divergences = []
        
        if 'momentum' not in df.columns:
            return divergences
        
        prices = df[price_col]
        momentum = df['momentum']
        
        price_peaks, price_troughs = self.find_peaks_troughs(prices, self.divergence_length)
        mom_peaks, mom_troughs = self.find_peaks_troughs(momentum, self.divergence_length)
        
        for i in range(len(price_troughs) - 1):
            idx1 = price_troughs[i]
            idx2 = price_troughs[i + 1]
            
            if prices.iloc[idx2] < prices.iloc[idx1]:
                mom_idx1 = None
                mom_idx2 = None
                
                for m_idx in mom_troughs:
                    if abs(m_idx - idx1) < self.divergence_length:
                        mom_idx1 = m_idx
                    if abs(m_idx - idx2) < self.divergence_length:
                        mom_idx2 = m_idx
                
                if mom_idx1 and mom_idx2 and momentum.iloc[mom_idx2] > momentum.iloc[mom_idx1]:
                    divergence = DivergenceDetection(
                        timestamp=df.index[idx2],
                        divergence_type=MomentumSignal.DIVERGENCE_BULLISH,
                        price_level=prices.iloc[idx2],
                        momentum_level=momentum.iloc[mom_idx2],
                        divergence_bars=idx2 - idx1,
                        severity=min(1.0, abs(momentum.iloc[mom_idx2] - momentum.iloc[mom_idx1])),
                    )
                    divergences.append(divergence)
        
        for i in range(len(price_peaks) - 1):
            idx1 = price_peaks[i]
            idx2 = price_peaks[i + 1]
            
            if prices.iloc[idx2] > prices.iloc[idx1]:
                mom_idx1 = None
                mom_idx2 = None
                
                for m_idx in mom_peaks:
                    if abs(m_idx - idx1) < self.divergence_length:
                        mom_idx1 = m_idx
                    if abs(m_idx - idx2) < self.divergence_length:
                        mom_idx2 = m_idx
                
                if mom_idx1 and mom_idx2 and momentum.iloc[mom_idx2] < momentum.iloc[mom_idx1]:
                    divergence = DivergenceDetection(
                        timestamp=df.index[idx2],
                        divergence_type=MomentumSignal.DIVERGENCE_BEARISH,
                        price_level=prices.iloc[idx2],
                        momentum_level=momentum.iloc[mom_idx2],
                        divergence_bars=idx2 - idx1,
                        severity=min(1.0, abs(momentum.iloc[mom_idx1] - momentum.iloc[mom_idx2])),
                    )
                    divergences.append(divergence)
        
        return divergences


class AdaptiveMomentumOscillator:
    """Complete adaptive momentum oscillator system."""
    
    def __init__(
        self,
        data_length: int = 20,
        smoothing_length: int = 10,
        divergence_length: int = 14,
        data_source: DataSource = DataSource.CLOSE,
    ):
        """Initialize oscillator."""
        self.calculator = MomentumCalculator(data_length, smoothing_length, data_source)
        self.divergence_detector = DivergenceDetector(divergence_length)
    
    def analyze(
        self, df: pd.DataFrame, detect_divergences: bool = True
    ) -> Tuple[pd.DataFrame, List[MomentumSignalPoint], List[DivergenceDetection]]:
        """Complete momentum analysis."""
        df_momentum = self.calculator.calculate_momentum(df)
        signals = self.calculator.detect_signals(df_momentum)
        
        divergences = []
        if detect_divergences:
            divergences = self.divergence_detector.detect_divergences(df_momentum)
        
        return df_momentum, signals, divergences
    
    def identify_trend_strength(self, df: pd.DataFrame) -> Dict[str, any]:
        """Identify overall trend strength."""
        if 'momentum' not in df.columns:
            return {'strength': 0, 'direction': 'none'}
        
        recent_momentum = df['momentum'].tail(14)
        strength = recent_momentum.abs().mean()
        avg_momentum = recent_momentum.mean()
        direction = 'bullish' if avg_momentum > 0 else 'bearish'
        above_signal = (recent_momentum > df['momentum_signal'].tail(14)).sum() / 14
        
        return {
            'strength': strength,
            'direction': direction,
            'signal_alignment': above_signal,
            'momentum_value': df['momentum'].iloc[-1],
            'signal_value': df['momentum_signal'].iloc[-1],
        }
    
    def identify_reversal_points(
        self, df: pd.DataFrame, threshold: float = 0.5
    ) -> List[Dict]:
        """Identify potential reversal points."""
        reversals = []
        divergences = self.divergence_detector.detect_divergences(df)
        
        for div in divergences:
            if div.severity >= threshold:
                reversals.append({
                    'timestamp': div.timestamp,
                    'type': div.divergence_type.value,
                    'price': div.price_level,
                    'momentum': div.momentum_level,
                    'severity': div.severity,
                    'bars_back': div.divergence_bars,
                })
        
        return reversals


if __name__ == "__main__":
    import numpy as np
    
    dates = pd.date_range('2023-01-01', periods=500, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(500) * 0.8)
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(500) * 0.5),
        'low': prices - np.abs(np.random.randn(500) * 0.5),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 500),
    }, index=dates)
    
    osc = AdaptiveMomentumOscillator(
        data_length=20,
        smoothing_length=10,
        divergence_length=14,
    )
    
    df_momentum, signals, divergences = osc.analyze(df, detect_divergences=True)
    
    print(f"✓ Signals: {len(signals)}")
    print(f"✓ Divergences: {len(divergences)}")
    
    trend = osc.identify_trend_strength(df_momentum)
    print(f"\nTrend: {trend['direction'].upper()}")
    
    reversals = osc.identify_reversal_points(df_momentum)
    print(f"Reversals: {len(reversals)}")
