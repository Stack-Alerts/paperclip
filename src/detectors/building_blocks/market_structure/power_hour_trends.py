"""
Power Hour Trends - Building Block
==================================

MARKET STRUCTURE BLOCK - Provides power hour trendline analysis.

Extracts institutional trading hour data (15:00-16:00 NY time by default)
and builds linear regression trendlines to identify:
- Trend direction (uptrend/downtrend/ranging)
- Dynamic support/resistance levels
- Volatility regime (low/moderate/high/extreme)
- Channel width and position

Based on LuxAlgo Power Hour Trendlines concept.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime, time
from enum import Enum
import pandas as pd
import numpy as np


@register_block(
    name='power_hour_trends',
    category='MARKET_STRUCTURE',
    class_name='TrendDirection',
    default_weight=15,
    valid_signals=['BULLISH', 'BEARISH', 'NEUTRAL', 'ERROR', 'INSUFFICIENT_DATA'],
    signal_tiers={
        'BULLISH': {
                'base_points': 15,
                'formula': 'scaled'
        },
        'BEARISH': {
                'base_points': 15,
                'formula': 'scaled'
        },
        'NEUTRAL': {
                'points': 0
        },
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        }
}
)
class TrendDirection(Enum):
    """Trend direction classification."""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGING = "ranging"


class VolatilityRegime(Enum):
    """Volatility regime classification."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class PowerHourTrends:
    """
    Power Hour Trends Detector
    
    Building Block Classification: MARKET STRUCTURE BLOCK
    Mode: METADATA (provides context, not direct entry signals)
    
    Analyzes institutional trading hours to extract trendlines,
    support/resistance levels, and volatility regimes.
    
    Designed for intraday bars (1H or lower timeframe).
    """
    
    def __init__(
        self,
        timeframe: str = '15min',
        power_hour_start: int = 15,
        power_hour_end: int = 16,
        sessions_memory: int = 20,
        **kwargs
    ):
        """
        Initialize Power Hour Trends detector.
        
        Args:
            timeframe: Timeframe (e.g., '15min', '1H')
            power_hour_start: Power hour start (24-hour format)
            power_hour_end: Power hour end (24-hour format)
            sessions_memory: Number of power hour sessions to analyze
        """
        self.timeframe = timeframe
        self.power_hour_start = power_hour_start
        self.power_hour_end = power_hour_end
        self.sessions_memory = sessions_memory
        
        self.start_time = time(power_hour_start, 0)
        self.end_time = time(power_hour_end, 0)
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for power hour trends.
        
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
        
        min_bars = self.sessions_memory * 4  # Minimum for reliable analysis
        if len(df) < min_bars:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {min_bars} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Extract power hours
        power_hours = self._extract_power_hours(df)
        
        if len(power_hours) < self.sessions_memory:
            return self._generate_insufficient_signal(
                df['timestamp'].iloc[-1],
                df['close'].iloc[-1]
            )
        
        # Use last N sessions
        recent_power_hours = power_hours[-self.sessions_memory:]
        
        # Build trendlines
        middle = self._build_middle_trendline(recent_power_hours)
        upper = self._build_upper_trendline(recent_power_hours, middle)
        lower = self._build_lower_trendline(recent_power_hours, middle)
        
        # Calculate metrics
        channel_width = self._calculate_channel_width(upper, middle, lower)
        current_price = df['close'].iloc[-1]
        
        # Determine positions
        middle_val = middle['slope'] * (len(recent_power_hours) - 1) + middle['intercept']
        upper_val = upper['slope'] * (len(recent_power_hours) - 1) + upper['intercept'] if upper else middle_val
        lower_val = lower['slope'] * (len(recent_power_hours) - 1) + lower['intercept'] if lower else middle_val
        
        # Classify
        trend = self._classify_trend(middle['slope'])
        volatility = self._classify_volatility(channel_width, current_price)
        
        # Generate signal
        return self._generate_signal(
            df['timestamp'].iloc[-1],
            current_price,
            trend,
            volatility,
            middle_val,
            upper_val,
            lower_val,
            channel_width,
            middle['r_squared']
        )
    
    def _extract_power_hours(self, df: pd.DataFrame) -> list:
        """Extract power hour bars from DataFrame."""
        power_hours = []
        
        for idx, row in df.iterrows():
            timestamp = row['timestamp'] if 'timestamp' in row else idx
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            
            bar_time = timestamp.time()
            if self.start_time <= bar_time < self.end_time:
                power_hours.append({
                    'timestamp': timestamp,
                    'close': row['close'],
                    'high': row['high'],
                    'low': row['low'],
                })
        
        return power_hours
    
    def _build_middle_trendline(self, power_hours: list) -> dict:
        """Build middle trendline (all closes)."""
        closes = [ph['close'] for ph in power_hours]
        x_values = np.arange(len(closes))
        
        # Linear regression
        if len(closes) < 2:
            return {
                'slope': 0.0,
                'intercept': closes[0] if closes else 0.0,
                'r_squared': 0.0
            }
        
        coeffs = np.polyfit(x_values, closes, 1)
        slope = coeffs[0]
        intercept = coeffs[1]
        
        # R-squared
        y_pred = slope * x_values + intercept
        ss_res = np.sum((np.array(closes) - y_pred) ** 2)
        ss_tot = np.sum((np.array(closes) - np.mean(closes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared
        }
    
    def _build_upper_trendline(self, power_hours: list, middle: dict) -> Optional[dict]:
        """Build upper trendline (closes above middle)."""
        above_middle = []
        
        for i, ph in enumerate(power_hours):
            middle_val = middle['slope'] * i + middle['intercept']
            if ph['close'] > middle_val:
                above_middle.append(ph['close'])
        
        if len(above_middle) < 2:
            return None
        
        x_values = np.arange(len(above_middle))
        coeffs = np.polyfit(x_values, above_middle, 1)
        
        return {
            'slope': coeffs[0],
            'intercept': coeffs[1],
            'r_squared': 0.0  # Simplified
        }
    
    def _build_lower_trendline(self, power_hours: list, middle: dict) -> Optional[dict]:
        """Build lower trendline (closes below middle)."""
        below_middle = []
        
        for i, ph in enumerate(power_hours):
            middle_val = middle['slope'] * i + middle['intercept']
            if ph['close'] < middle_val:
                below_middle.append(ph['close'])
        
        if len(below_middle) < 2:
            return None
        
        x_values = np.arange(len(below_middle))
        coeffs = np.polyfit(x_values, below_middle, 1)
        
        return {
            'slope': coeffs[0],
            'intercept': coeffs[1],
            'r_squared': 0.0  # Simplified
        }
    
    def _calculate_channel_width(self, upper: Optional[dict], middle: dict, lower: Optional[dict]) -> float:
        """Calculate average channel width."""
        if not upper or not lower:
            return 0.0
        
        # Get final values
        final_upper = upper['slope'] * (self.sessions_memory - 1) + upper['intercept']
        final_lower = lower['slope'] * (self.sessions_memory - 1) + lower['intercept']
        
        return abs(final_upper - final_lower)
    
    def _classify_trend(self, slope: float) -> TrendDirection:
        """Classify trend direction from slope."""
        threshold = 0.0001
        
        if abs(slope) < threshold:
            return TrendDirection.RANGING
        elif slope > 0:
            return TrendDirection.UPTREND
        else:
            return TrendDirection.DOWNTREND
    
    def _classify_volatility(self, channel_width: float, price: float) -> VolatilityRegime:
        """Classify volatility regime."""
        if price == 0:
            return VolatilityRegime.LOW
        
        pct_width = (channel_width / price) * 100  # Percentage
        
        if pct_width > 5.0:
            return VolatilityRegime.EXTREME
        elif pct_width > 3.0:
            return VolatilityRegime.HIGH
        elif pct_width > 1.5:
            return VolatilityRegime.MODERATE
        else:
            return VolatilityRegime.LOW
    
    def _generate_signal(
        self,
        timestamp: datetime,
        current_price: float,
        trend: TrendDirection,
        volatility: VolatilityRegime,
        middle_val: float,
        upper_val: float,
        lower_val: float,
        channel_width: float,
        r_squared: float
    ) -> Dict[str, Any]:
        """Generate signal with power hour analysis."""
        # Calculate position in channel
        if upper_val != lower_val:
            position_pct = ((current_price - lower_val) / (upper_val - lower_val)) * 100
        else:
            position_pct = 50.0
        
        # Calculate confidence based on R²
        base_confidence = 60
        if r_squared > 0.8:
            base_confidence = 75
        elif r_squared > 0.6:
            base_confidence = 70
        elif r_squared > 0.4:
            base_confidence = 65
        
        # Adjust for volatility regime
        if volatility == VolatilityRegime.EXTREME:
            base_confidence -= 10
        elif volatility == VolatilityRegime.LOW:
            base_confidence += 5
        
        confidence = max(40, min(85, base_confidence))
        
        return {
            'signal': f'{trend.value.upper()}_{volatility.value.upper()}',
            'confidence': confidence,
            'metadata': {
                'trend_direction': trend.value,
                'volatility_regime': volatility.value,
                'current_price': round(current_price, 2),
                'middle_trendline': round(middle_val, 2),
                'upper_trendline': round(upper_val, 2),
                'lower_trendline': round(lower_val, 2),
                'support_level': round(lower_val, 2),
                'resistance_level': round(upper_val, 2),
                'channel_width': round(channel_width, 2),
                'channel_width_pct': round((channel_width / current_price) * 100, 3),
                'position_in_channel_pct': round(position_pct, 1),
                'r_squared': round(r_squared, 3),
                'trendline_confidence': confidence,
                'sessions_analyzed': self.sessions_memory,
                'is_new_event': False,  # Metadata block
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': self._get_confluence_factors(
                trend, volatility, position_pct, r_squared
            )
        }
    
    def _get_confluence_factors(
        self,
        trend: TrendDirection,
        volatility: VolatilityRegime,
        position_pct: float,
        r_squared: float
    ) -> list:
        """Get confluence factors."""
        factors = []
        
        factors.append(f'Trend: {trend.value}')
        factors.append(f'Volatility: {volatility.value}')
        factors.append(f'Position in channel: {position_pct:.0f}%')
        
        if r_squared > 0.7:
            factors.append(f'Strong trendline (R²={r_squared:.2f})')
        
        if position_pct > 75:
            factors.append('Near resistance')
        elif position_pct < 25:
            factors.append('Near support')
        else:
            factors.append('Mid-channel')
        
        return factors
    
    def _generate_insufficient_signal(
        self,
        timestamp: datetime,
        current_price: float
    ) -> Dict[str, Any]:
        """Generate signal when insufficient power hours."""
        return {
            'signal': 'INSUFFICIENT_POWER_HOURS',
            'confidence': 0,
            'metadata': {
                'current_price': round(current_price, 2),
                'error': f'Need {self.sessions_memory} power hour sessions',
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': ['Insufficient power hour data']
        }


if __name__ == "__main__":
    print("Power Hour Trends - Building Block")
    print("MARKET STRUCTURE BLOCK - Institutional trading hour analysis")
    print("Based on LuxAlgo Power Hour Trendlines")
