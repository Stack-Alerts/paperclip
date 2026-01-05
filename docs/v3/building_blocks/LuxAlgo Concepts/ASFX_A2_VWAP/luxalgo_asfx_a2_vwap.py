"""
LuxAlgo ASFX A2 VWAP - Core Implementation
==========================================

ASFX A2 VWAP toolkit combining A2 entry signals with daily anchored VWAP
bands and Fibonacci-based stop-loss management designed by Austin Silver.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta


class SignalType(Enum):
    """A2 signal type classification."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NEUTRAL = 'neutral'


@dataclass
class A2Signal:
    """A2 entry signal detection result."""
    timestamp: pd.Timestamp
    signal_type: SignalType
    strength: float  # 0-100
    ema_21_value: float
    price_close: float
    price_low: float
    price_high: float
    confirmation: bool
    vwap_filtered: bool = False


@dataclass
class VWAPBand:
    """VWAP band at specific timestamp."""
    timestamp: pd.Timestamp
    vwap: float
    upper_band_1: float  # 1x StDev
    upper_band_2: float  # 2x StDev
    upper_band_3: float  # 3x StDev
    lower_band_1: float  # 1x StDev
    lower_band_2: float  # 2x StDev
    lower_band_3: float  # 3x StDev
    cumulative_volume: float


@dataclass
class StopLoss:
    """Stop-loss level derived from A2 signal."""
    signal_timestamp: pd.Timestamp
    signal_type: SignalType
    stop_level: float
    fibonacci_ratio: float  # 1.618
    base_range: float
    distance_from_entry: float


class EMACalculator:
    """Calculate Exponential Moving Average."""
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """
        Calculate EMA for price series.
        
        Args:
            prices: List of prices
            period: EMA period
        
        Returns:
            List of EMA values
        """
        if len(prices) < period:
            return [np.nan] * len(prices)
        
        ema_values = []
        multiplier = 2 / (period + 1)
        
        # Initial SMA
        sma = np.mean(prices[:period])
        ema_values = [np.nan] * (period - 1) + [sma]
        
        # Calculate EMA
        for i in range(period, len(prices)):
            ema = prices[i] * multiplier + ema_values[-1] * (1 - multiplier)
            ema_values.append(ema)
        
        return ema_values
    
    @staticmethod
    def get_ema_at_index(prices: List[float], period: int, index: int) -> float:
        """Get EMA value at specific index."""
        ema_values = EMACalculator.calculate_ema(prices, period)
        if index < len(ema_values):
            return ema_values[index]
        return np.nan


class A2SignalDetector:
    """Detect A2 entry signals based on Austin Silver methodology."""
    
    def __init__(self, trigger_ema_period: int = 21,
                 validation_ema_period: int = 21):
        """
        Initialize A2 signal detector.
        
        Args:
            trigger_ema_period: EMA period for trigger
            validation_ema_period: EMA period for validation
        """
        self.trigger_ema_period = trigger_ema_period
        self.validation_ema_period = validation_ema_period
    
    def detect_bullish_signal(self, bar: pd.Series, ema_21: float,
                            prev_bar: Optional[pd.Series] = None) -> Optional[A2Signal]:
        """
        Detect bullish A2 signal.
        
        Conditions:
        - Price closes below 21 EMA
        - Less than 50% of candle's closing price above it
        
        Args:
            bar: Current OHLC bar
            ema_21: Current 21 EMA value
            prev_bar: Previous bar for context
        
        Returns:
            A2Signal if detected
        """
        # Close below EMA check
        if bar['close'] >= ema_21:
            return None
        
        # Less than 50% of close above EMA
        candle_range = bar['high'] - bar['low']
        price_above_ema = bar['close'] - bar['low']
        
        if candle_range > 0:
            pct_above = price_above_ema / candle_range
        else:
            pct_above = 0.5
        
        # Bullish if price mostly below EMA
        if pct_above < 0.5:
            strength = (1 - pct_above) * 100  # Higher strength = more below EMA
            
            return A2Signal(
                timestamp=bar.name if hasattr(bar, 'name') else None,
                signal_type=SignalType.BULLISH,
                strength=strength,
                ema_21_value=ema_21,
                price_close=bar['close'],
                price_low=bar['low'],
                price_high=bar['high'],
                confirmation=pct_above < 0.3,  # Strong if very below
            )
        
        return None
    
    def detect_bearish_signal(self, bar: pd.Series, ema_21: float,
                             prev_bar: Optional[pd.Series] = None) -> Optional[A2Signal]:
        """
        Detect bearish A2 signal.
        
        Conditions:
        - Price closes above 21 EMA
        - Less than 50% of candle below it
        
        Args:
            bar: Current OHLC bar
            ema_21: Current 21 EMA value
            prev_bar: Previous bar for context
        
        Returns:
            A2Signal if detected
        """
        # Close above EMA check
        if bar['close'] <= ema_21:
            return None
        
        # Less than 50% of close below EMA
        candle_range = bar['high'] - bar['low']
        price_below_ema = bar['high'] - bar['close']
        
        if candle_range > 0:
            pct_below = price_below_ema / candle_range
        else:
            pct_below = 0.5
        
        # Bearish if price mostly above EMA
        if pct_below < 0.5:
            strength = (1 - pct_below) * 100  # Higher strength = more above EMA
            
            return A2Signal(
                timestamp=bar.name if hasattr(bar, 'name') else None,
                signal_type=SignalType.BEARISH,
                strength=strength,
                ema_21_value=ema_21,
                price_close=bar['close'],
                price_low=bar['low'],
                price_high=bar['high'],
                confirmation=pct_below < 0.3,  # Strong if very above
            )
        
        return None


class AnchoredVWAPCalculator:
    """Calculate anchored VWAP with standard deviation bands."""
    
    @staticmethod
    def calculate_vwap(df: pd.DataFrame, anchor_date: Optional[pd.Timestamp] = None,
                      source: str = 'close') -> Tuple[List[float], List[float]]:
        """
        Calculate daily anchored VWAP from anchor date.
        
        Args:
            df: OHLCV DataFrame
            anchor_date: Anchor date (default: daily reset)
            source: Price source ('close', 'hl2', 'hlc3', 'ohlc4')
        
        Returns:
            Tuple of (vwap_values, cumulative_volumes)
        """
        if anchor_date is None:
            anchor_date = df.index[0].normalize()
        
        # Get data from anchor date
        anchor_mask = df.index.normalize() >= anchor_date
        anchor_df = df[anchor_mask].copy()
        
        vwap_values = []
        cumulative_volumes = []
        cumulative_pv = 0  # Price * Volume
        cumulative_vol = 0
        
        for idx, row in anchor_df.iterrows():
            # Select price source
            if source == 'close':
                price = row['close']
            elif source == 'hl2':
                price = (row['high'] + row['low']) / 2
            elif source == 'hlc3':
                price = (row['high'] + row['low'] + row['close']) / 3
            else:  # ohlc4
                price = (row['open'] + row['high'] + row['low'] + row['close']) / 4
            
            volume = row.get('volume', 1)
            
            cumulative_pv += price * volume
            cumulative_vol += volume
            
            if cumulative_vol > 0:
                vwap = cumulative_pv / cumulative_vol
            else:
                vwap = price
            
            vwap_values.append(vwap)
            cumulative_volumes.append(cumulative_vol)
        
        return vwap_values, cumulative_volumes
    
    @staticmethod
    def calculate_bands(vwap: List[float], prices: List[float],
                       multipliers: List[float] = None) -> Dict[str, List[float]]:
        """
        Calculate VWAP bands using standard deviation.
        
        Args:
            vwap: VWAP values
            prices: Price values (for StDev calculation)
            multipliers: StDev multipliers (default: [1, 2, 3])
        
        Returns:
            Dictionary with band values
        """
        if multipliers is None:
            multipliers = [1.0, 2.0, 3.0]
        
        # Calculate standard deviation of deviation from VWAP
        deviations = [abs(p - v) for p, v in zip(prices, vwap)]
        std_dev = np.std(deviations) if deviations else 0
        
        bands = {}
        for mult in multipliers:
            upper = [v + (std_dev * mult) for v in vwap]
            lower = [v - (std_dev * mult) for v in vwap]
            bands[f'upper_{mult}'] = upper
            bands[f'lower_{mult}'] = lower
        
        return bands


class StopLossCalculator:
    """Calculate stop-loss using Fibonacci retracement."""
    
    FIBONACCI_RATIO = 1.618
    
    @staticmethod
    def calculate_bullish_stop(signal: A2Signal, daily_high: float) -> StopLoss:
        """
        Calculate bullish stop-loss using Fibonacci.
        
        From candle low to daily high, apply 1.618 ratio.
        
        Args:
            signal: A2 bullish signal
            daily_high: Current day's high
        
        Returns:
            StopLoss object
        """
        base_range = daily_high - signal.price_low
        fib_extension = base_range * StopLossCalculator.FIBONACCI_RATIO
        stop_level = signal.price_low - fib_extension
        
        return StopLoss(
            signal_timestamp=signal.timestamp,
            signal_type=SignalType.BULLISH,
            stop_level=stop_level,
            fibonacci_ratio=StopLossCalculator.FIBONACCI_RATIO,
            base_range=base_range,
            distance_from_entry=signal.price_close - stop_level,
        )
    
    @staticmethod
    def calculate_bearish_stop(signal: A2Signal, daily_low: float) -> StopLoss:
        """
        Calculate bearish stop-loss using Fibonacci.
        
        From candle high to daily low, apply 1.618 ratio.
        
        Args:
            signal: A2 bearish signal
            daily_low: Current day's low
        
        Returns:
            StopLoss object
        """
        base_range = signal.price_high - daily_low
        fib_extension = base_range * StopLossCalculator.FIBONACCI_RATIO
        stop_level = signal.price_high + fib_extension
        
        return StopLoss(
            signal_timestamp=signal.timestamp,
            signal_type=SignalType.BEARISH,
            stop_level=stop_level,
            fibonacci_ratio=StopLossCalculator.FIBONACCI_RATIO,
            base_range=base_range,
            distance_from_entry=stop_level - signal.price_close,
        )


class ASFXA2VWAP:
    """Complete ASFX A2 VWAP analysis system."""
    
    def __init__(self, trigger_ema: int = 21,
                 validation_ema: int = 21,
                 stddev_multipliers: List[float] = None,
                 filter_by_vwap: bool = True,
                 source: str = 'close'):
        """
        Initialize ASFX A2 VWAP indicator.
        
        Args:
            trigger_ema: EMA period for A2 trigger
            validation_ema: EMA period for validation
            stddev_multipliers: StDev multipliers for bands
            filter_by_vwap: Filter signals by VWAP position
            source: VWAP calculation source
        """
        self.trigger_ema = trigger_ema
        self.validation_ema = validation_ema
        self.stddev_multipliers = stddev_multipliers or [1.0, 2.0, 3.0]
        self.filter_by_vwap = filter_by_vwap
        self.source = source
        self.signal_detector = A2SignalDetector(trigger_ema, validation_ema)
        self.vwap_calc = AnchoredVWAPCalculator()
        self.stop_loss_calc = StopLossCalculator()
    
    def analyze(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Complete A2 VWAP analysis.
        
        Args:
            df: OHLCV DataFrame (daily or intraday)
        
        Returns:
            Tuple of (DataFrame with analysis, results dict)
        """
        # Calculate EMA
        ema_21 = EMACalculator.calculate_ema(df['close'].tolist(), self.trigger_ema)
        
        # Calculate VWAP
        vwap_values, cum_vols = self.vwap_calc.calculate_vwap(df, source=self.source)
        
        # Calculate bands
        bands = self.vwap_calc.calculate_bands(vwap_values, df['close'].tolist(),
                                              self.stddev_multipliers)
        
        # Detect A2 signals
        signals = []
        stop_losses = []
        
        for i in range(len(df)):
            bar = df.iloc[i]
            ema_val = ema_21[i] if i < len(ema_21) else np.nan
            
            if np.isnan(ema_val):
                continue
            
            # Detect signals
            bullish = self.signal_detector.detect_bullish_signal(bar, ema_val)
            bearish = self.signal_detector.detect_bearish_signal(bar, ema_val)
            
            signal = bullish or bearish
            
            if signal:
                # Filter by VWAP if enabled
                if self.filter_by_vwap and i < len(vwap_values):
                    if signal.signal_type == SignalType.BULLISH:
                        signal.vwap_filtered = bar['close'] > vwap_values[i]
                    else:
                        signal.vwap_filtered = bar['close'] < vwap_values[i]
                    
                    if not signal.vwap_filtered:
                        continue
                
                signals.append(signal)
                
                # Calculate stop-loss
                daily_high = df['high'].iloc[:i+1].max()
                daily_low = df['low'].iloc[:i+1].min()
                
                if signal.signal_type == SignalType.BULLISH:
                    sl = self.stop_loss_calc.calculate_bullish_stop(signal, daily_high)
                else:
                    sl = self.stop_loss_calc.calculate_bearish_stop(signal, daily_low)
                
                stop_losses.append(sl)
        
        # Add to DataFrame
        df_result = df.copy()
        df_result['ema_21'] = ema_21
        
        if len(vwap_values) == len(df):
            df_result['vwap'] = vwap_values
            df_result['vwap_upper_1'] = bands['upper_1.0']
            df_result['vwap_lower_1'] = bands['lower_1.0']
            df_result['vwap_upper_2'] = bands['upper_2.0']
            df_result['vwap_lower_2'] = bands['lower_2.0']
            df_result['vwap_upper_3'] = bands['upper_3.0']
            df_result['vwap_lower_3'] = bands['lower_3.0']
        
        df_result['a2_signal'] = ''
        for sig in signals:
            idx = df.index.get_loc(sig.timestamp) if sig.timestamp in df.index else None
            if idx is not None:
                df_result.loc[sig.timestamp, 'a2_signal'] = sig.signal_type.value
        
        return df_result, {
            'signals': signals,
            'stop_losses': stop_losses,
            'vwap': vwap_values[:len(df)] if vwap_values else [],
            'bands': bands,
        }


if __name__ == "__main__":
    import numpy as np
    
    dates = pd.date_range('2024-01-01', periods=100, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(100) * 1)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(100) * 0.5,
        'high': prices + np.abs(np.random.randn(100) * 1),
        'low': prices - np.abs(np.random.randn(100) * 1),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 100),
    }, index=dates)
    
    asfx = ASFXA2VWAP(trigger_ema=21, filter_by_vwap=True)
    df_result, results = asfx.analyze(df)
    
    print("=" * 70)
    print("ASFX A2 VWAP - ANALYSIS")
    print("=" * 70)
    
    print(f"\n✓ A2 Signals: {len(results['signals'])}")
    for sig in results['signals'][-3:]:
        print(f"  {sig.timestamp}: {sig.signal_type.value.upper()} (strength: {sig.strength:.0f}%)")
    
    print(f"\n✓ Stop Losses: {len(results['stop_losses'])}")
    if results['stop_losses']:
        sl = results['stop_losses'][-1]
        print(f"  Latest: {sl.stop_level:.2f}")
