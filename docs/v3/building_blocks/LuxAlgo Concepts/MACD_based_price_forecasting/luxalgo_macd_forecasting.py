"""
LuxAlgo MACD Based Price Forecasting - Core Implementation
===========================================================

MACD-based price forecasting using historical price trajectories
and percentile analysis to generate forward-looking price ranges
and reversal predictions.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict


class TrendDetermination(Enum):
    """Methods to determine trend from MACD."""
    MACD = 'macd'  # MACD > 0 = uptrend, < 0 = downtrend
    MACD_SIGNAL = 'macd_signal'  # MACD > Signal = uptrend, < = downtrend


class SignalType(Enum):
    """Type of MACD signal."""
    BULLISH = 'bullish'  # MACD crosses above signal
    BEARISH = 'bearish'  # MACD crosses below signal
    NONE = 'none'


@dataclass
class MACDValue:
    """MACD calculation at a point in time."""
    timestamp: pd.Timestamp
    macd: float
    signal: float
    histogram: float
    trend: str  # 'uptrend' or 'downtrend'
    signal_type: SignalType


@dataclass
class PriceTrajectory:
    """Historical price movement after a MACD signal."""
    signal_timestamp: pd.Timestamp
    signal_price: float
    future_prices: List[float]
    bars_ahead: int
    signal_type: SignalType


@dataclass
class ForecastRange:
    """Price forecast range based on historical trajectories."""
    timestamp: pd.Timestamp
    signal_price: float
    top_percentile_price: float
    upper_bound: float
    average_price: float
    middle_price: float
    lower_bound: float
    bottom_percentile_price: float
    confidence_range: float
    signal_type: SignalType
    forecast_bars: int


@dataclass
class PriceSignal:
    """MACD signal occurrence."""
    timestamp: pd.Timestamp
    price: float
    macd_value: float
    signal_value: float
    histogram: float
    signal_type: SignalType
    trend: str


class MACDCalculator:
    """MACD indicator calculation."""
    
    def __init__(self, fast_length: int = 12, slow_length: int = 26, signal_length: int = 9):
        """
        Initialize MACD calculator.
        
        Args:
            fast_length: Period for fast EMA (default: 12)
            slow_length: Period for slow EMA (default: 26)
            signal_length: Period for signal line EMA (default: 9)
        """
        self.fast_length = fast_length
        self.slow_length = slow_length
        self.signal_length = signal_length
    
    def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()
    
    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD, Signal, and Histogram.
        
        Args:
            df: DataFrame with 'close' column
        
        Returns:
            DataFrame with MACD values added
        """
        df_result = df.copy()
        
        # Calculate EMAs
        fast_ema = self.calculate_ema(df['close'], self.fast_length)
        slow_ema = self.calculate_ema(df['close'], self.slow_length)
        
        # MACD line
        df_result['macd'] = fast_ema - slow_ema
        
        # Signal line
        df_result['signal'] = self.calculate_ema(df_result['macd'], self.signal_length)
        
        # Histogram
        df_result['histogram'] = df_result['macd'] - df_result['signal']
        
        return df_result
    
    def detect_signals(
        self, df: pd.DataFrame, trend_method: TrendDetermination = TrendDetermination.MACD
    ) -> List[PriceSignal]:
        """
        Detect MACD crossover signals.
        
        Args:
            df: DataFrame with MACD calculated
            trend_method: How to determine trend
        
        Returns:
            List of signals
        """
        signals = []
        
        for i in range(1, len(df)):
            prev_macd = df.iloc[i-1]['macd']
            curr_macd = df.iloc[i]['macd']
            prev_signal = df.iloc[i-1]['signal']
            curr_signal = df.iloc[i]['signal']
            
            signal_type = SignalType.NONE
            trend = None
            
            # Detect crossover
            if trend_method == TrendDetermination.MACD:
                if prev_macd <= 0 and curr_macd > 0:
                    signal_type = SignalType.BULLISH
                    trend = 'uptrend'
                elif prev_macd >= 0 and curr_macd < 0:
                    signal_type = SignalType.BEARISH
                    trend = 'downtrend'
                
                # Current trend
                if trend is None:
                    trend = 'uptrend' if curr_macd > 0 else 'downtrend'
            
            elif trend_method == TrendDetermination.MACD_SIGNAL:
                if prev_macd <= prev_signal and curr_macd > curr_signal:
                    signal_type = SignalType.BULLISH
                    trend = 'uptrend'
                elif prev_macd >= prev_signal and curr_macd < curr_signal:
                    signal_type = SignalType.BEARISH
                    trend = 'downtrend'
                
                if trend is None:
                    trend = 'uptrend' if curr_macd > curr_signal else 'downtrend'
            
            if signal_type != SignalType.NONE:
                signal = PriceSignal(
                    timestamp=df.index[i],
                    price=df.iloc[i]['close'],
                    macd_value=curr_macd,
                    signal_value=curr_signal,
                    histogram=df.iloc[i]['histogram'],
                    signal_type=signal_type,
                    trend=trend,
                )
                signals.append(signal)
        
        return signals


class PriceForecaster:
    """Forecast future prices based on MACD signals."""
    
    def __init__(
        self,
        max_memory: int = 100,
        forecasting_length: int = 20,
        top_percentile: int = 95,
        average_percentile: int = 50,
        bottom_percentile: int = 5,
    ):
        """
        Initialize price forecaster.
        
        Args:
            max_memory: Maximum number of past trajectories to record
            forecasting_length: Number of bars ahead to forecast
            top_percentile: Upper boundary percentile (0-100)
            average_percentile: Middle forecast percentile (0-100)
            bottom_percentile: Lower boundary percentile (0-100)
        """
        self.max_memory = max_memory
        self.forecasting_length = forecasting_length
        self.top_percentile = top_percentile
        self.average_percentile = average_percentile
        self.bottom_percentile = bottom_percentile
    
    def collect_trajectories(
        self, df: pd.DataFrame, signals: List[PriceSignal]
    ) -> Dict[str, List[PriceTrajectory]]:
        """
        Collect historical price trajectories after MACD signals.
        
        Args:
            df: OHLCV DataFrame
            signals: List of MACD signals
        
        Returns:
            Dictionary mapping signal type to trajectories
        """
        trajectories = defaultdict(list)
        
        for signal in signals:
            try:
                signal_idx = df.index.get_loc(signal.timestamp)
            except KeyError:
                continue
            
            # Get future prices
            future_start = signal_idx + 1
            future_end = min(signal_idx + self.forecasting_length + 1, len(df))
            
            if future_start >= len(df):
                continue
            
            future_prices = df.iloc[future_start:future_end]['close'].tolist()
            
            if future_prices:
                trajectory = PriceTrajectory(
                    signal_timestamp=signal.timestamp,
                    signal_price=signal.price,
                    future_prices=future_prices,
                    bars_ahead=len(future_prices),
                    signal_type=signal.signal_type,
                )
                
                key = f"{signal.signal_type.value}"
                trajectories[key].append(trajectory)
        
        return trajectories
    
    def calculate_percentile_price(
        self, trajectories: List[PriceTrajectory], percentile: float, bars_ahead: int
    ) -> Optional[float]:
        """
        Calculate price at specific percentile and bar offset.
        
        Args:
            trajectories: List of trajectories
            percentile: Percentile (0-100)
            bars_ahead: Number of bars into the future
        
        Returns:
            Price at that percentile, or None
        """
        if not trajectories or bars_ahead < 1:
            return None
        
        # Collect prices at this bar offset
        prices_at_offset = []
        
        for traj in trajectories:
            if len(traj.future_prices) >= bars_ahead:
                prices_at_offset.append(traj.future_prices[bars_ahead - 1])
        
        if not prices_at_offset:
            return None
        
        return np.percentile(prices_at_offset, percentile)
    
    def generate_forecast(
        self,
        df: pd.DataFrame,
        signal: PriceSignal,
        trajectories: Dict[str, List[PriceTrajectory]],
    ) -> Optional[ForecastRange]:
        """
        Generate price forecast for a MACD signal.
        
        Args:
            df: OHLCV DataFrame
            signal: The MACD signal
            trajectories: Collected historical trajectories
        
        Returns:
            ForecastRange object or None
        """
        signal_key = signal.signal_type.value
        
        if signal_key not in trajectories or not trajectories[signal_key]:
            return None
        
        relevant_trajectories = trajectories[signal_key][-self.max_memory:]
        
        # Calculate prices at each percentile for forecasting_length bars
        prices_top = []
        prices_avg = []
        prices_mid = []
        prices_bot = []
        
        for bar in range(1, self.forecasting_length + 1):
            top = self.calculate_percentile_price(relevant_trajectories, self.top_percentile, bar)
            avg = self.calculate_percentile_price(relevant_trajectories, self.average_percentile, bar)
            bot = self.calculate_percentile_price(relevant_trajectories, self.bottom_percentile, bar)
            
            if top:
                prices_top.append(top)
            if avg:
                prices_avg.append(avg)
            if bot:
                prices_bot.append(bot)
        
        if not prices_top or not prices_bot:
            return None
        
        # Get bounds at forecasting_length bars
        top_bound = prices_top[-1] if prices_top else signal.price
        avg_price = prices_avg[-1] if prices_avg else signal.price
        bot_bound = prices_bot[-1] if prices_bot else signal.price
        
        mid_price = (top_bound + bot_bound) / 2
        confidence_range = top_bound - bot_bound
        
        # Get immediate percentile prices
        top_percentile_price = self.calculate_percentile_price(
            relevant_trajectories, self.top_percentile, 1
        ) or signal.price
        
        bot_percentile_price = self.calculate_percentile_price(
            relevant_trajectories, self.bottom_percentile, 1
        ) or signal.price
        
        forecast = ForecastRange(
            timestamp=signal.timestamp,
            signal_price=signal.price,
            top_percentile_price=top_percentile_price,
            upper_bound=top_bound,
            average_price=avg_price,
            middle_price=mid_price,
            lower_bound=bot_bound,
            bottom_percentile_price=bot_percentile_price,
            confidence_range=confidence_range,
            signal_type=signal.signal_type,
            forecast_bars=self.forecasting_length,
        )
        
        return forecast


class MACDPriceForecaster:
    """Complete MACD-based price forecasting system."""
    
    def __init__(
        self,
        fast_length: int = 12,
        slow_length: int = 26,
        signal_length: int = 9,
        max_memory: int = 100,
        forecasting_length: int = 20,
        top_percentile: int = 95,
        average_percentile: int = 50,
        bottom_percentile: int = 5,
    ):
        """Initialize forecaster."""
        self.macd_calc = MACDCalculator(fast_length, slow_length, signal_length)
        self.forecaster = PriceForecaster(
            max_memory, forecasting_length, top_percentile, average_percentile, bottom_percentile
        )
    
    def forecast(
        self,
        df: pd.DataFrame,
        trend_method: TrendDetermination = TrendDetermination.MACD,
    ) -> Tuple[pd.DataFrame, List[PriceSignal], List[ForecastRange]]:
        """
        Generate complete price forecast.
        
        Args:
            df: OHLCV DataFrame
            trend_method: How to determine trend
        
        Returns:
            Tuple of (df_with_macd, signals, forecasts)
        """
        # Calculate MACD
        df_macd = self.macd_calc.calculate_macd(df)
        
        # Detect signals
        signals = self.macd_calc.detect_signals(df_macd, trend_method)
        
        # Collect trajectories
        trajectories = self.forecaster.collect_trajectories(df_macd, signals)
        
        # Generate forecasts for each signal
        forecasts = []
        for signal in signals:
            forecast = self.forecaster.generate_forecast(df_macd, signal, trajectories)
            if forecast:
                forecasts.append(forecast)
        
        return df_macd, signals, forecasts
    
    def identify_reversals(
        self, forecasts: List[ForecastRange], reversal_threshold: float = 0.02
    ) -> List[Dict]:
        """
        Identify potential reversal points from forecasts.
        
        Args:
            forecasts: List of forecast ranges
            reversal_threshold: Percentage change to consider reversal
        
        Returns:
            List of potential reversals
        """
        reversals = []
        
        for i in range(1, len(forecasts)):
            prev_forecast = forecasts[i-1]
            curr_forecast = forecasts[i]
            
            # Check if forecast direction changed significantly
            if prev_forecast.signal_type != curr_forecast.signal_type:
                # Potential reversal
                price_change = abs(curr_forecast.signal_price - prev_forecast.signal_price)
                pct_change = price_change / prev_forecast.signal_price if prev_forecast.signal_price > 0 else 0
                
                if pct_change >= reversal_threshold:
                    reversals.append({
                        'timestamp': curr_forecast.timestamp,
                        'price': curr_forecast.signal_price,
                        'previous_signal': prev_forecast.signal_type.value,
                        'current_signal': curr_forecast.signal_type.value,
                        'change_pct': pct_change,
                        'prev_forecast': prev_forecast,
                        'curr_forecast': curr_forecast,
                    })
        
        return reversals
    
    def identify_support_resistance(
        self, forecasts: List[ForecastRange]
    ) -> Dict[str, List[float]]:
        """
        Identify support and resistance from forecast ranges.
        
        Args:
            forecasts: List of forecast ranges
        
        Returns:
            Dictionary with support and resistance levels
        """
        supports = []
        resistances = []
        
        for forecast in forecasts:
            if forecast.signal_type == SignalType.BULLISH:
                # For bullish, lower bound is support
                supports.append(forecast.lower_bound)
            elif forecast.signal_type == SignalType.BEARISH:
                # For bearish, upper bound is resistance
                resistances.append(forecast.upper_bound)
        
        # Cluster nearby levels
        def cluster_prices(prices, tolerance=0.01):
            if not prices:
                return []
            
            prices_sorted = sorted(prices)
            clusters = []
            current_cluster = [prices_sorted[0]]
            
            for price in prices_sorted[1:]:
                if abs(price - current_cluster[-1]) <= tolerance * current_cluster[-1]:
                    current_cluster.append(price)
                else:
                    clusters.append(np.mean(current_cluster))
                    current_cluster = [price]
            
            if current_cluster:
                clusters.append(np.mean(current_cluster))
            
            return clusters
        
        return {
            'support_levels': cluster_prices(supports),
            'resistance_levels': cluster_prices(resistances),
        }


if __name__ == "__main__":
    # Example usage
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
    
    # Setup forecaster
    forecaster = MACDPriceForecaster(
        fast_length=12,
        slow_length=26,
        signal_length=9,
        max_memory=100,
        forecasting_length=20,
    )
    
    # Generate forecast
    df_macd, signals, forecasts = forecaster.forecast(df)
    
    print("=" * 70)
    print("MACD PRICE FORECASTING ANALYSIS")
    print("=" * 70)
    
    print(f"\n✓ MACD calculated")
    print(f"  MACD columns: {[c for c in df_macd.columns if 'macd' in c.lower() or 'signal' in c.lower() or 'histogram' in c.lower()]}")
    
    print(f"\n✓ Signals detected: {len(signals)}")
    for sig in signals[-3:]:
        print(f"  {sig.timestamp}: {sig.signal_type.value.upper()} @ {sig.price:.2f}")
    
    print(f"\n✓ Forecasts generated: {len(forecasts)}")
    if forecasts:
        f = forecasts[-1]
        print(f"  Latest forecast: {f.timestamp}")
        print(f"    Signal: {f.signal_type.value.upper()} @ {f.signal_price:.2f}")
        print(f"    Range: {f.lower_bound:.2f} - {f.upper_bound:.2f}")
        print(f"    Confidence: {f.confidence_range:.2f}")
    
    # Find reversals
    reversals = forecaster.identify_reversals(forecasts)
    print(f"\n✓ Potential reversals: {len(reversals)}")
    for rev in reversals[-2:]:
        print(f"  {rev['timestamp']}: {rev['previous_signal']} → {rev['current_signal']} ({rev['change_pct']:.2%})")
    
    # Find support/resistance
    sr_levels = forecaster.identify_support_resistance(forecasts)
    print(f"\n✓ Support/Resistance")
    print(f"  Support levels: {[f'{p:.2f}' for p in sr_levels['support_levels'][:3]]}")
    print(f"  Resistance levels: {[f'{p:.2f}' for p in sr_levels['resistance_levels'][:3]]}")
