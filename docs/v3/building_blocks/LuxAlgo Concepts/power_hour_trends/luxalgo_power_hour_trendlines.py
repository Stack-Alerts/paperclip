"""
LuxAlgo Power Hour Trendlines - Core Implementation
===================================================

Power hour trendline analysis using linear regression on institutional
trading hours, with dynamic support/resistance extraction and volatility
measurement.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import time


class TrendDirection(Enum):
    """Trend direction classification."""
    UPTREND = 'uptrend'
    DOWNTREND = 'downtrend'
    RANGING = 'ranging'
    UNKNOWN = 'unknown'


class VolatilityRegime(Enum):
    """Volatility regime classification."""
    HIGH = 'high'
    MODERATE = 'moderate'
    LOW = 'low'
    EXTREME = 'extreme'


@dataclass
class Trendline:
    """Represents a single trendline."""
    name: str  # 'upper', 'middle', 'lower'
    slope: float
    intercept: float
    r_squared: float
    price_points: List[float]
    timestamp_points: List[pd.Timestamp]
    direction: TrendDirection
    
    def calculate_value(self, bar_index: int) -> float:
        """Calculate trendline value at given bar index."""
        return self.slope * bar_index + self.intercept
    
    def calculate_distance(self, price: float, bar_index: int) -> float:
        """Calculate distance from price to trendline."""
        trendline_value = self.calculate_value(bar_index)
        return price - trendline_value


@dataclass
class PowerHourBar:
    """Data from a single power hour candle."""
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float
    session_date: pd.Timestamp


@dataclass
class TrendlineAnalysis:
    """Complete trendline analysis result."""
    timestamp: pd.Timestamp
    upper_trendline: Optional[Trendline]
    middle_trendline: Trendline
    lower_trendline: Optional[Trendline]
    channel_width: float
    trend_direction: TrendDirection
    volatility_regime: VolatilityRegime
    support_level: float
    resistance_level: float
    distance_from_middle: float


class PowerHourExtractor:
    """Extract power hour data from OHLCV DataFrame."""
    
    def __init__(self, start_hour: int = 15, start_minute: int = 0,
                 end_hour: int = 16, end_minute: int = 0):
        """
        Initialize power hour extractor.
        
        Args:
            start_hour: Power hour start (24-hour format, NY time)
            start_minute: Power hour start minute
            end_hour: Power hour end
            end_minute: Power hour end minute
        """
        self.start_time = time(start_hour, start_minute)
        self.end_time = time(end_hour, end_minute)
    
    def is_power_hour(self, timestamp: pd.Timestamp) -> bool:
        """Check if timestamp is within power hour."""
        bar_time = timestamp.time()
        return self.start_time <= bar_time < self.end_time
    
    def extract_power_hours(self, df: pd.DataFrame) -> List[PowerHourBar]:
        """
        Extract all power hour bars from DataFrame.
        
        Args:
            df: OHLCV DataFrame with DatetimeIndex
        
        Returns:
            List of PowerHourBar objects
        """
        power_hours = []
        
        for idx, row in df.iterrows():
            if self.is_power_hour(idx):
                power_hour_bar = PowerHourBar(
                    timestamp=idx,
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row.get('volume', 0),
                    session_date=idx.normalize(),
                )
                power_hours.append(power_hour_bar)
        
        return power_hours
    
    def group_by_session(self, power_hours: List[PowerHourBar]) -> Dict[pd.Timestamp, List[PowerHourBar]]:
        """Group power hour bars by trading session."""
        sessions = {}
        for ph in power_hours:
            if ph.session_date not in sessions:
                sessions[ph.session_date] = []
            sessions[ph.session_date].append(ph)
        return sessions


class LinearRegressionCalculator:
    """Calculate linear regression trendlines."""
    
    @staticmethod
    def calculate_regression(y_values: List[float]) -> Tuple[float, float, float]:
        """
        Calculate linear regression line.
        
        Args:
            y_values: Price values
        
        Returns:
            Tuple of (slope, intercept, r_squared)
        """
        if len(y_values) < 2:
            return 0.0, np.mean(y_values) if y_values else 0.0, 0.0
        
        x_values = np.arange(len(y_values))
        
        # Calculate regression
        coeffs = np.polyfit(x_values, y_values, 1)
        slope = coeffs[0]
        intercept = coeffs[1]
        
        # Calculate R-squared
        y_pred = slope * x_values + intercept
        ss_res = np.sum((np.array(y_values) - y_pred) ** 2)
        ss_tot = np.sum((np.array(y_values) - np.mean(y_values)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return slope, intercept, r_squared


class TrendlineBuilder:
    """Build trendlines from power hour data."""
    
    def __init__(self):
        self.calculator = LinearRegressionCalculator()
    
    def classify_direction(self, slope: float, threshold: float = 0.0001) -> TrendDirection:
        """
        Classify trend direction by slope.
        
        Args:
            slope: Trendline slope
            threshold: Threshold for ranging vs trending
        
        Returns:
            TrendDirection enum
        """
        if abs(slope) < threshold:
            return TrendDirection.RANGING
        elif slope > 0:
            return TrendDirection.UPTREND
        else:
            return TrendDirection.DOWNTREND
    
    def build_middle_trendline(self, power_hours: List[PowerHourBar]) -> Trendline:
        """Build middle trendline (all closes)."""
        closes = [ph.close for ph in power_hours]
        timestamps = [ph.timestamp for ph in power_hours]
        
        slope, intercept, r_squared = self.calculator.calculate_regression(closes)
        direction = self.classify_direction(slope)
        
        return Trendline(
            name='middle',
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            price_points=closes,
            timestamp_points=timestamps,
            direction=direction,
        )
    
    def build_upper_trendline(self, power_hours: List[PowerHourBar], 
                             middle_trendline: Trendline) -> Optional[Trendline]:
        """Build upper trendline (closes above middle)."""
        above_middle = []
        above_timestamps = []
        
        for i, ph in enumerate(power_hours):
            middle_value = middle_trendline.calculate_value(i)
            if ph.close > middle_value:
                above_middle.append(ph.close)
                above_timestamps.append(ph.timestamp)
        
        if len(above_middle) < 2:
            return None
        
        slope, intercept, r_squared = self.calculator.calculate_regression(above_middle)
        direction = self.classify_direction(slope)
        
        return Trendline(
            name='upper',
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            price_points=above_middle,
            timestamp_points=above_timestamps,
            direction=direction,
        )
    
    def build_lower_trendline(self, power_hours: List[PowerHourBar],
                             middle_trendline: Trendline) -> Optional[Trendline]:
        """Build lower trendline (closes below middle)."""
        below_middle = []
        below_timestamps = []
        
        for i, ph in enumerate(power_hours):
            middle_value = middle_trendline.calculate_value(i)
            if ph.close < middle_value:
                below_middle.append(ph.close)
                below_timestamps.append(ph.timestamp)
        
        if len(below_middle) < 2:
            return None
        
        slope, intercept, r_squared = self.calculator.calculate_regression(below_middle)
        direction = self.classify_direction(slope)
        
        return Trendline(
            name='lower',
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            price_points=below_middle,
            timestamp_points=below_timestamps,
            direction=direction,
        )


class VolatilityAnalyzer:
    """Analyze volatility from trendlines."""
    
    @staticmethod
    def calculate_channel_width(upper: Optional[Trendline], 
                               middle: Trendline,
                               lower: Optional[Trendline]) -> float:
        """Calculate average distance between upper and lower trendlines."""
        if not upper or not lower:
            return 0.0
        
        widths = []
        for i in range(len(middle.price_points)):
            upper_val = upper.calculate_value(i)
            lower_val = lower.calculate_value(i)
            widths.append(upper_val - lower_val)
        
        return np.mean(widths) if widths else 0.0
    
    @staticmethod
    def classify_volatility(channel_width: float, 
                           price_level: float,
                           extreme_threshold: float = 0.02) -> VolatilityRegime:
        """
        Classify volatility regime.
        
        Args:
            channel_width: Width of trendline channel
            price_level: Current price level
            extreme_threshold: % threshold for extreme volatility
        
        Returns:
            VolatilityRegime enum
        """
        pct_width = channel_width / price_level if price_level > 0 else 0
        
        if pct_width > extreme_threshold:
            return VolatilityRegime.EXTREME
        elif pct_width > extreme_threshold / 2:
            return VolatilityRegime.HIGH
        elif pct_width > extreme_threshold / 4:
            return VolatilityRegime.MODERATE
        else:
            return VolatilityRegime.LOW


class PowerHourTrendlines:
    """Complete power hour trendlines analysis system."""
    
    def __init__(self, start_hour: int = 15, start_minute: int = 0,
                 end_hour: int = 16, end_minute: int = 0,
                 sessions_memory: int = 20):
        """Initialize power hour trendlines."""
        self.extractor = PowerHourExtractor(start_hour, start_minute, end_hour, end_minute)
        self.builder = TrendlineBuilder()
        self.volatility = VolatilityAnalyzer()
        self.sessions_memory = sessions_memory
    
    def analyze(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TrendlineAnalysis]]:
        """
        Complete power hour trendline analysis.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            Tuple of (df with trendline values, list of analyses)
        """
        # Extract power hours
        power_hours = self.extractor.extract_power_hours(df)
        
        if len(power_hours) < self.sessions_memory:
            return df.copy(), []
        
        # Use last N sessions
        recent_power_hours = power_hours[-self.sessions_memory:]
        
        # Build trendlines
        middle = self.builder.build_middle_trendline(recent_power_hours)
        upper = self.builder.build_upper_trendline(recent_power_hours, middle)
        lower = self.builder.build_lower_trendline(recent_power_hours, middle)
        
        # Create analysis
        channel_width = self.volatility.calculate_channel_width(upper, middle, lower)
        
        # Add to DataFrame
        df_result = df.copy()
        df_result['power_hour_middle'] = np.nan
        df_result['power_hour_upper'] = np.nan
        df_result['power_hour_lower'] = np.nan
        
        for i, ph in enumerate(recent_power_hours):
            if ph.timestamp in df_result.index:
                df_result.loc[ph.timestamp, 'power_hour_middle'] = middle.calculate_value(i)
                if upper:
                    df_result.loc[ph.timestamp, 'power_hour_upper'] = upper.calculate_value(i)
                if lower:
                    df_result.loc[ph.timestamp, 'power_hour_lower'] = lower.calculate_value(i)
        
        # Create comprehensive analysis
        analyses = self._create_analyses(
            recent_power_hours, middle, upper, lower, channel_width
        )
        
        return df_result, analyses
    
    def _create_analyses(self, power_hours: List[PowerHourBar],
                        middle: Trendline,
                        upper: Optional[Trendline],
                        lower: Optional[Trendline],
                        channel_width: float) -> List[TrendlineAnalysis]:
        """Create analysis objects for each power hour bar."""
        analyses = []
        
        for i, ph in enumerate(power_hours):
            middle_val = middle.calculate_value(i)
            upper_val = upper.calculate_value(i) if upper else middle_val
            lower_val = lower.calculate_value(i) if lower else middle_val
            
            # Support/resistance
            support = lower_val if lower else middle_val
            resistance = upper_val if upper else middle_val
            
            # Volatility
            vol_regime = self.volatility.classify_volatility(
                channel_width, ph.close
            )
            
            analysis = TrendlineAnalysis(
                timestamp=ph.timestamp,
                upper_trendline=upper,
                middle_trendline=middle,
                lower_trendline=lower,
                channel_width=channel_width,
                trend_direction=middle.direction,
                volatility_regime=vol_regime,
                support_level=support,
                resistance_level=resistance,
                distance_from_middle=ph.close - middle_val,
            )
            analyses.append(analysis)
        
        return analyses
    
    def get_support_resistance_levels(self, analyses: List[TrendlineAnalysis]) -> Dict[str, List[float]]:
        """Extract support and resistance clusters from analyses."""
        supports = []
        resistances = []
        
        for analysis in analyses:
            supports.append(analysis.support_level)
            resistances.append(analysis.resistance_level)
        
        # Cluster nearby levels
        def cluster_levels(levels: List[float], tolerance: float = 0.0005) -> List[float]:
            if not levels:
                return []
            
            sorted_levels = sorted(levels)
            clusters = []
            current_cluster = [sorted_levels[0]]
            
            for level in sorted_levels[1:]:
                if abs(level - current_cluster[0]) < tolerance:
                    current_cluster.append(level)
                else:
                    clusters.append(np.mean(current_cluster))
                    current_cluster = [level]
            
            clusters.append(np.mean(current_cluster))
            return clusters
        
        return {
            'support_levels': cluster_levels(supports),
            'resistance_levels': cluster_levels(resistances),
        }
    
    def detect_breakout(self, analyses: List[TrendlineAnalysis],
                       current_price: float) -> Optional[Dict]:
        """Detect breakout from trendlines."""
        if not analyses:
            return None
        
        latest = analyses[-1]
        
        # Breakout above upper
        if latest.upper_trendline and current_price > latest.resistance_level:
            return {
                'type': 'bullish_breakout',
                'level': latest.resistance_level,
                'distance': current_price - latest.resistance_level,
                'timestamp': latest.timestamp,
            }
        
        # Breakout below lower
        if latest.lower_trendline and current_price < latest.support_level:
            return {
                'type': 'bearish_breakout',
                'level': latest.support_level,
                'distance': latest.support_level - current_price,
                'timestamp': latest.timestamp,
            }
        
        return None


if __name__ == "__main__":
    import numpy as np
    
    dates = pd.date_range('2023-12-01', periods=250, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(250) * 0.5)
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(250) * 0.3),
        'low': prices - np.abs(np.random.randn(250) * 0.3),
        'close': prices,
        'volume': np.random.randint(100000, 500000, 250),
    }, index=dates)
    
    pht = PowerHourTrendlines(start_hour=15, end_hour=16, sessions_memory=20)
    df_result, analyses = pht.analyze(df)
    
    print(f"✓ Power hours found: {len(analyses)}")
    
    if analyses:
        latest = analyses[-1]
        print(f"\nLatest Analysis:")
        print(f"  Trend: {latest.trend_direction.value.upper()}")
        print(f"  Volatility: {latest.volatility_regime.value.upper()}")
        print(f"  Support: ${latest.support_level:.2f}")
        print(f"  Resistance: ${latest.resistance_level:.2f}")
        print(f"  Channel width: ${latest.channel_width:.2f}")
    
    levels = pht.get_support_resistance_levels(analyses)
    print(f"\n✓ Support levels: {len(levels['support_levels'])}")
    print(f"✓ Resistance levels: {len(levels['resistance_levels'])}")
