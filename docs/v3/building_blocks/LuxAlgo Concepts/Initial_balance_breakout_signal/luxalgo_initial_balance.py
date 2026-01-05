"""
LuxAlgo Initial Balance Breakout Signals Implementation
========================================================

A robust, production-ready implementation of LuxAlgo's Initial Balance (IB)
Breakout Signals indicator for identifying high-probability intraday breakout
opportunities based on institutional trading logic.

Features:
    - Automatic Initial Balance detection (first hour of session)
    - Custom session support (ORB strategies)
    - Breakout signal generation
    - Fibonacci retracement levels
    - IB extensions (25%, 50%, 100%)
    - Forecasting engine (vs previous open / by day of week)
    - Multi-session visualization

Author: Advanced Trading Systems
Date: 2026
Python: 3.8+

Dependencies:
    - pandas>=1.3.0
    - numpy>=1.21.0
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime, time, timedelta
import warnings


class SessionType(Enum):
    """Types of session configurations."""
    AUTO = "auto"  # First hour of trading day
    CUSTOM = "custom"  # User-defined session
    ORB_1MIN = "orb_1min"  # 1-minute open range
    ORB_3MIN = "orb_3min"  # 3-minute open range
    ORB_5MIN = "orb_5min"  # 5-minute open range
    ORB_30MIN = "orb_30min"  # 30-minute open range


class ForecastMethod(Enum):
    """Forecasting methods for IB analysis."""
    IB_VS_PREVIOUS_OPEN = "vs_previous_open"
    FILTER_BY_WEEKDAY = "filter_by_weekday"


class BreakoutDirection(Enum):
    """Breakout direction classification."""
    BULLISH = "bullish"  # Break above IB high
    BEARISH = "bearish"  # Break below IB low
    NONE = "none"  # No breakout or inside IB


@dataclass
class InitialBalance:
    """Data structure for Initial Balance information."""
    session_start: datetime
    session_end: datetime
    high: float
    low: float
    range_size: float
    midpoint: float
    timestamp: datetime
    
    def get_ib_range(self) -> float:
        """Get the size of the IB range."""
        return self.high - self.low
    
    def is_inside_ib(self, price: float) -> bool:
        """Check if price is inside IB range."""
        return self.low <= price <= self.high
    
    def is_above_ib(self, price: float) -> bool:
        """Check if price is above IB high."""
        return price > self.high
    
    def is_below_ib(self, price: float) -> bool:
        """Check if price is below IB low."""
        return price < self.low


@dataclass
class BreakoutSignal:
    """Data structure for breakout signals."""
    timestamp: datetime
    direction: BreakoutDirection
    price: float
    ib_reference: InitialBalance
    signal_strength: str  # 'weak', 'medium', 'strong'
    volume_confirmed: bool
    confirmation_bars: int  # How many bars above/below IB high/low
    
    def get_distance_from_ib(self) -> float:
        """Get distance from IB extreme."""
        if self.direction == BreakoutDirection.BULLISH:
            return self.price - self.ib_reference.high
        elif self.direction == BreakoutDirection.BEARISH:
            return self.ib_reference.low - self.price
        return 0.0


@dataclass
class FibonacciLevels:
    """Data structure for Fibonacci retracement levels."""
    level_0_0: float  # 0% (top)
    level_23_6: float  # 23.6%
    level_38_2: float  # 38.2%
    level_50_0: float  # 50%
    level_61_8: float  # 61.8%
    level_78_6: float  # 78.6%
    level_100_0: float  # 100% (bottom)
    
    def get_all_levels(self) -> Dict[str, float]:
        """Get all Fibonacci levels as dictionary."""
        return {
            '0.0': self.level_0_0,
            '23.6': self.level_23_6,
            '38.2': self.level_38_2,
            '50.0': self.level_50_0,
            '61.8': self.level_61_8,
            '78.6': self.level_78_6,
            '100.0': self.level_100_0,
        }


@dataclass
class IBExtensions:
    """Data structure for IB extensions."""
    top_25: float  # 25% extension above IB high
    top_50: float  # 50% extension above IB high
    top_100: float  # 100% extension above IB high
    bottom_25: float  # 25% extension below IB low
    bottom_50: float  # 50% extension below IB low
    bottom_100: float  # 100% extension below IB low
    
    def get_all_extensions(self) -> Dict[str, float]:
        """Get all extensions as dictionary."""
        return {
            'top_25': self.top_25,
            'top_50': self.top_50,
            'top_100': self.top_100,
            'bottom_25': self.bottom_25,
            'bottom_50': self.bottom_50,
            'bottom_100': self.bottom_100,
        }


@dataclass
class IBForecast:
    """Data structure for IB forecasting."""
    forecast_high: float
    forecast_low: float
    forecast_range: float
    forecast_method: ForecastMethod
    historical_average: float
    multiplier: float
    current_vs_average: str  # 'above', 'below', 'near'
    
    def get_forecast_bounds(self) -> Tuple[float, float]:
        """Get upper and lower forecast bounds."""
        center = (self.forecast_high + self.forecast_low) / 2
        half_range = self.forecast_range / 2
        return center - half_range, center + half_range


class InitialBalanceDetector:
    """
    Main class for detecting Initial Balance and generating breakout signals.
    
    The Initial Balance (IB) is the high and low formed during the first hour
    of a trading session, representing institutional order flow and early sentiment.
    """
    
    def __init__(
        self,
        session_type: SessionType = SessionType.AUTO,
        session_start_hour: int = 9,
        session_start_min: int = 30,
        session_duration_minutes: int = 60,
        ib_lookback_days: int = 20,
        forecast_method: ForecastMethod = ForecastMethod.IB_VS_PREVIOUS_OPEN,
        forecast_multiplier: float = 1.0,
        fib_reverse: bool = False,
        display_past_ibs: int = 5,
    ):
        """
        Initialize the Initial Balance Detector.
        
        Args:
            session_type: Type of session (AUTO, CUSTOM, ORB_*MIN)
            session_start_hour: Start hour of session (default: 9 = 9:30 AM)
            session_start_min: Start minute of session (default: 30)
            session_duration_minutes: Duration of IB in minutes (default: 60)
            ib_lookback_days: Historical days for forecasting (default: 20)
            forecast_method: How to forecast IB (default: VS_PREVIOUS_OPEN)
            forecast_multiplier: Scale factor for forecast width (default: 1.0)
            fib_reverse: Reverse Fibonacci levels (default: False)
            display_past_ibs: How many past IBs to display (default: 5)
        """
        self.session_type = session_type
        self.session_start_hour = session_start_hour
        self.session_start_min = session_start_min
        self.session_duration_minutes = session_duration_minutes
        self.ib_lookback_days = ib_lookback_days
        self.forecast_method = forecast_method
        self.forecast_multiplier = forecast_multiplier
        self.fib_reverse = fib_reverse
        self.display_past_ibs = display_past_ibs
        
        self._validate_parameters()
    
    def _validate_parameters(self) -> None:
        """Validate initialization parameters."""
        if not 0 <= self.session_start_hour <= 23:
            raise ValueError(f"session_start_hour must be 0-23, got {self.session_start_hour}")
        if not 0 <= self.session_start_min <= 59:
            raise ValueError(f"session_start_min must be 0-59, got {self.session_start_min}")
        if self.session_duration_minutes < 1:
            raise ValueError(f"session_duration_minutes must be > 0, got {self.session_duration_minutes}")
        if self.ib_lookback_days < 5:
            raise ValueError(f"ib_lookback_days should be >= 5, got {self.ib_lookback_days}")
        if self.forecast_multiplier <= 0:
            raise ValueError(f"forecast_multiplier must be > 0, got {self.forecast_multiplier}")
    
    def detect_initial_balance(self, df: pd.DataFrame) -> InitialBalance:
        """
        Detect the Initial Balance for the current session.
        
        Args:
            df: DataFrame with OHLCV data and DatetimeIndex
        
        Returns:
            InitialBalance object with session details
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain {required_cols}")
        
        # Get current trading session
        session_start = self._get_session_start(df.index[-1])
        session_end = session_start + timedelta(minutes=self.session_duration_minutes)
        
        # Filter bars within IB session
        ib_mask = (df.index >= session_start) & (df.index < session_end)
        ib_df = df[ib_mask]
        
        if len(ib_df) == 0:
            warnings.warn("No bars found in IB session, extending search")
            ib_mask = (df.index >= session_start) & (df.index <= df.index[-1])
            ib_df = df[ib_mask]
        
        # Calculate IB
        ib_high = ib_df['high'].max()
        ib_low = ib_df['low'].min()
        ib_range = ib_high - ib_low
        ib_midpoint = (ib_high + ib_low) / 2
        
        return InitialBalance(
            session_start=session_start,
            session_end=session_end,
            high=ib_high,
            low=ib_low,
            range_size=ib_range,
            midpoint=ib_midpoint,
            timestamp=df.index[-1],
        )
    
    def _get_session_start(self, timestamp: datetime) -> datetime:
        """Get the start time of the trading session."""
        session_start = timestamp.replace(
            hour=self.session_start_hour,
            minute=self.session_start_min,
            second=0,
            microsecond=0,
        )
        
        # If we're before session start, session started yesterday
        if timestamp < session_start:
            session_start -= timedelta(days=1)
        
        return session_start
    
    def detect_breakouts(
        self,
        df: pd.DataFrame,
        ib: InitialBalance,
        volume_multiplier: float = 1.5,
        confirmation_bars: int = 1,
    ) -> List[BreakoutSignal]:
        """
        Detect breakout signals based on IB.
        
        Args:
            df: OHLCV DataFrame
            ib: InitialBalance object
            volume_multiplier: Volume threshold multiplier for confirmation
            confirmation_bars: Bars needed to confirm breakout
        
        Returns:
            List of BreakoutSignal objects
        """
        signals = []
        
        avg_volume = df['volume'].tail(20).mean()
        
        # Look for breakouts after IB session
        after_ib_mask = df.index >= ib.session_end
        after_ib_df = df[after_ib_mask].copy()
        
        if len(after_ib_df) == 0:
            return signals
        
        # Track consecutive bars above/below IB
        bars_above_ib = 0
        bars_below_ib = 0
        last_signal_idx = -confirmation_bars
        
        for idx, (bar_idx, row) in enumerate(after_ib_df.iterrows()):
            # Bullish breakout (above IB high)
            if row['close'] > ib.high:
                bars_above_ib += 1
                bars_below_ib = 0
                
                if bars_above_ib >= confirmation_bars and idx - last_signal_idx >= confirmation_bars:
                    volume_confirmed = row['volume'] > avg_volume * volume_multiplier
                    strength = self._calculate_signal_strength(
                        row['close'], ib.high, ib.range_size
                    )
                    
                    signals.append(BreakoutSignal(
                        timestamp=bar_idx,
                        direction=BreakoutDirection.BULLISH,
                        price=row['close'],
                        ib_reference=ib,
                        signal_strength=strength,
                        volume_confirmed=volume_confirmed,
                        confirmation_bars=bars_above_ib,
                    ))
                    last_signal_idx = idx
            
            # Bearish breakout (below IB low)
            elif row['close'] < ib.low:
                bars_below_ib += 1
                bars_above_ib = 0
                
                if bars_below_ib >= confirmation_bars and idx - last_signal_idx >= confirmation_bars:
                    volume_confirmed = row['volume'] > avg_volume * volume_multiplier
                    strength = self._calculate_signal_strength(
                        row['close'], ib.low, ib.range_size, is_bearish=True
                    )
                    
                    signals.append(BreakoutSignal(
                        timestamp=bar_idx,
                        direction=BreakoutDirection.BEARISH,
                        price=row['close'],
                        ib_reference=ib,
                        signal_strength=strength,
                        volume_confirmed=volume_confirmed,
                        confirmation_bars=bars_below_ib,
                    ))
                    last_signal_idx = idx
            
            # Back inside IB
            else:
                bars_above_ib = 0
                bars_below_ib = 0
        
        return signals
    
    def _calculate_signal_strength(
        self,
        price: float,
        ib_extreme: float,
        ib_range: float,
        is_bearish: bool = False,
    ) -> str:
        """Calculate breakout signal strength based on distance from IB."""
        if ib_range == 0:
            return 'medium'
        
        distance_pct = abs(price - ib_extreme) / ib_range
        
        if distance_pct < 0.25:
            return 'weak'
        elif distance_pct < 0.75:
            return 'medium'
        else:
            return 'strong'
    
    def calculate_fibonacci_levels(
        self, ib: InitialBalance
    ) -> FibonacciLevels:
        """
        Calculate Fibonacci retracement levels based on IB range.
        
        Args:
            ib: InitialBalance object
        
        Returns:
            FibonacciLevels object
        """
        # Standard Fibonacci ratios
        fib_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        
        if self.fib_reverse:
            # Reverse direction (flip top and bottom)
            top = ib.low
            bottom = ib.high
        else:
            top = ib.high
            bottom = ib.low
        
        ib_range = ib.get_ib_range()
        
        levels = {}
        for ratio in fib_ratios:
            level = top - (ratio * ib_range)
            levels[f'{ratio*100:.1f}'] = level
        
        return FibonacciLevels(
            level_0_0=levels['0.0'],
            level_23_6=levels['23.6'],
            level_38_2=levels['38.2'],
            level_50_0=levels['50.0'],
            level_61_8=levels['61.8'],
            level_78_6=levels['78.6'],
            level_100_0=levels['100.0'],
        )
    
    def calculate_extensions(
        self, ib: InitialBalance
    ) -> IBExtensions:
        """
        Calculate IB extensions (25%, 50%, 100%).
        
        Args:
            ib: InitialBalance object
        
        Returns:
            IBExtensions object
        """
        ib_range = ib.get_ib_range()
        
        # Top extensions (above IB high)
        top_25 = ib.high + (ib_range * 0.25)
        top_50 = ib.high + (ib_range * 0.50)
        top_100 = ib.high + (ib_range * 1.00)
        
        # Bottom extensions (below IB low)
        bottom_25 = ib.low - (ib_range * 0.25)
        bottom_50 = ib.low - (ib_range * 0.50)
        bottom_100 = ib.low - (ib_range * 1.00)
        
        return IBExtensions(
            top_25=top_25,
            top_50=top_50,
            top_100=top_100,
            bottom_25=bottom_25,
            bottom_50=bottom_50,
            bottom_100=bottom_100,
        )
    
    def forecast_ib(
        self, df: pd.DataFrame
    ) -> IBForecast:
        """
        Forecast IB range based on historical data.
        
        Methods:
        - IB_VS_PREVIOUS_OPEN: Compare IB to previous day's open
        - FILTER_BY_WEEKDAY: Compare IB to same day of week
        
        Args:
            df: Historical OHLCV DataFrame
        
        Returns:
            IBForecast object
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        
        # Get current session IB
        current_ib = self.detect_initial_balance(df)
        
        if self.forecast_method == ForecastMethod.IB_VS_PREVIOUS_OPEN:
            return self._forecast_vs_previous_open(df, current_ib)
        elif self.forecast_method == ForecastMethod.FILTER_BY_WEEKDAY:
            return self._forecast_by_weekday(df, current_ib)
        else:
            raise ValueError(f"Unknown forecast method: {self.forecast_method}")
    
    def _forecast_vs_previous_open(
        self, df: pd.DataFrame, current_ib: InitialBalance
    ) -> IBForecast:
        """
        Forecast by comparing IB to previous day's open.
        
        Average distance from previous open to IB high/low.
        """
        # Get lookback data (exclude current day)
        lookback_df = df.iloc[:-len(df[df.index.date == df.index[-1].date()])]
        
        if len(lookback_df) < self.ib_lookback_days:
            warnings.warn(f"Less than {self.ib_lookback_days} days of data available")
        
        lookback_df = lookback_df.tail(self.ib_lookback_days * 390)  # ~390 bars per trading day
        
        # Calculate average distances
        distances = []
        for date in lookback_df.index.date[-self.ib_lookback_days:]:
            daily_df = lookback_df[lookback_df.index.date == date]
            if len(daily_df) == 0:
                continue
            
            prev_open = daily_df['open'].iloc[0]
            daily_high = daily_df['high'].max()
            daily_low = daily_df['low'].min()
            
            distance_high = daily_high - prev_open
            distance_low = prev_open - daily_low
            distances.append((distance_high, distance_low))
        
        if not distances:
            # Fallback: use current IB range
            avg_distance = current_ib.get_ib_range() / 2
        else:
            avg_distance = np.mean([d[0] for d in distances])
        
        # Apply multiplier and calculate forecast
        forecast_distance = avg_distance * self.forecast_multiplier
        prev_open = df['open'].iloc[-len(df[df.index.date == df.index[-1].date()])]
        
        forecast_high = prev_open + forecast_distance
        forecast_low = prev_open - forecast_distance
        
        current_vs_average = 'near'
        if current_ib.high > forecast_high:
            current_vs_average = 'above'
        elif current_ib.low < forecast_low:
            current_vs_average = 'below'
        
        return IBForecast(
            forecast_high=forecast_high,
            forecast_low=forecast_low,
            forecast_range=forecast_distance * 2,
            forecast_method=self.forecast_method,
            historical_average=avg_distance,
            multiplier=self.forecast_multiplier,
            current_vs_average=current_vs_average,
        )
    
    def _forecast_by_weekday(
        self, df: pd.DataFrame, current_ib: InitialBalance
    ) -> IBForecast:
        """
        Forecast by comparing to average IB of same weekday.
        """
        lookback_df = df.iloc[:-len(df[df.index.date == df.index[-1].date()])]
        
        if len(lookback_df) < self.ib_lookback_days:
            warnings.warn(f"Less than {self.ib_lookback_days} days of data available")
        
        lookback_df = lookback_df.tail(self.ib_lookback_days * 390)
        
        # Get current weekday
        current_weekday = df.index[-1].weekday()
        
        # Find all IBs for same weekday
        same_weekday_ranges = []
        for date in lookback_df.index.date[-self.ib_lookback_days:]:
            if pd.Timestamp(date).weekday() != current_weekday:
                continue
            
            daily_df = lookback_df[lookback_df.index.date == date]
            if len(daily_df) < self.session_duration_minutes / 5:  # Minimum bars
                continue
            
            session_start = self._get_session_start(daily_df.index[0])
            session_end = session_start + timedelta(minutes=self.session_duration_minutes)
            
            session_df = daily_df[(daily_df.index >= session_start) & (daily_df.index < session_end)]
            if len(session_df) > 0:
                ib_range = session_df['high'].max() - session_df['low'].min()
                same_weekday_ranges.append(ib_range)
        
        if not same_weekday_ranges:
            avg_range = current_ib.get_ib_range()
        else:
            avg_range = np.mean(same_weekday_ranges)
        
        # Calculate forecast
        forecast_range = avg_range * self.forecast_multiplier
        forecast_center = current_ib.midpoint
        
        forecast_high = forecast_center + (forecast_range / 2)
        forecast_low = forecast_center - (forecast_range / 2)
        
        current_vs_average = 'near'
        if current_ib.get_ib_range() > avg_range:
            current_vs_average = 'above'
        elif current_ib.get_ib_range() < avg_range:
            current_vs_average = 'below'
        
        return IBForecast(
            forecast_high=forecast_high,
            forecast_low=forecast_low,
            forecast_range=forecast_range,
            forecast_method=self.forecast_method,
            historical_average=avg_range,
            multiplier=self.forecast_multiplier,
            current_vs_average=current_vs_average,
        )
    
    def get_past_ibs(self, df: pd.DataFrame) -> List[InitialBalance]:
        """
        Get historical Initial Balances.
        
        Args:
            df: Historical OHLCV DataFrame
        
        Returns:
            List of past InitialBalance objects
        """
        past_ibs = []
        unique_dates = df.index.date
        
        for i in range(min(self.display_past_ibs, len(np.unique(unique_dates)))):
            # Get data for this date
            target_date = np.unique(unique_dates)[-(i+1)]
            daily_df = df[df.index.date == target_date]
            
            if len(daily_df) == 0:
                continue
            
            # Calculate IB for this date
            session_start = self._get_session_start(daily_df.index[0])
            session_end = session_start + timedelta(minutes=self.session_duration_minutes)
            
            session_df = daily_df[(daily_df.index >= session_start) & (daily_df.index < session_end)]
            
            if len(session_df) > 0:
                ib_high = session_df['high'].max()
                ib_low = session_df['low'].min()
                
                past_ibs.append(InitialBalance(
                    session_start=session_start,
                    session_end=session_end,
                    high=ib_high,
                    low=ib_low,
                    range_size=ib_high - ib_low,
                    midpoint=(ib_high + ib_low) / 2,
                    timestamp=daily_df.index[-1],
                ))
        
        return past_ibs


def example_usage():
    """Example usage of the Initial Balance detector."""
    import numpy as np
    
    # Generate synthetic intraday data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01 09:30', periods=390*5, freq='5min')
    
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.1)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(len(dates)) * 0.05,
        'high': prices + np.abs(np.random.randn(len(dates)) * 0.2),
        'low': prices - np.abs(np.random.randn(len(dates)) * 0.2),
        'close': prices,
        'volume': np.random.randint(100, 1000, len(dates)),
    }, index=dates)
    
    # Create detector
    detector = InitialBalanceDetector(
        session_type=SessionType.AUTO,
        session_duration_minutes=60,
    )
    
    # Detect IB
    print("=== INITIAL BALANCE ===")
    ib = detector.detect_initial_balance(df)
    print(f"Session: {ib.session_start.time()} - {ib.session_end.time()}")
    print(f"High: {ib.high:.2f}, Low: {ib.low:.2f}")
    print(f"Range: {ib.range_size:.4f}")
    print(f"Midpoint: {ib.midpoint:.2f}")
    
    # Detect breakouts
    print("\n=== BREAKOUT SIGNALS ===")
    signals = detector.detect_breakouts(df, ib)
    for sig in signals[:5]:
        print(f"{sig.direction.value.upper()}: {sig.timestamp} at {sig.price:.2f}")
        print(f"  Strength: {sig.signal_strength}, Volume: {sig.volume_confirmed}")
    
    # Fibonacci levels
    print("\n=== FIBONACCI LEVELS ===")
    fibs = detector.calculate_fibonacci_levels(ib)
    for level, price in fibs.get_all_levels().items():
        print(f"  {level}%: {price:.2f}")
    
    # Extensions
    print("\n=== IB EXTENSIONS ===")
    exts = detector.calculate_extensions(ib)
    print(f"Top 25%: {exts.top_25:.2f}")
    print(f"Top 50%: {exts.top_50:.2f}")
    print(f"Top 100%: {exts.top_100:.2f}")
    print(f"Bottom 25%: {exts.bottom_25:.2f}")
    print(f"Bottom 50%: {exts.bottom_50:.2f}")
    print(f"Bottom 100%: {exts.bottom_100:.2f}")
    
    # Forecast
    print("\n=== IB FORECAST ===")
    forecast = detector.forecast_ib(df)
    print(f"Method: {forecast.forecast_method.value}")
    print(f"Forecast High: {forecast.forecast_high:.2f}")
    print(f"Forecast Low: {forecast.forecast_low:.2f}")
    print(f"Current vs Average: {forecast.current_vs_average}")


if __name__ == "__main__":
    example_usage()
