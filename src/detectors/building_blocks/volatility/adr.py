"""
ADR (Average Daily Range) Building Block
Category: Volatility Indicators
Purpose: Measures average daily price range for position sizing and target setting
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous Average Daily Range reference

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


@register_block(
    name='adr',
    category='VOLATILITY',
    class_name='ADR',
    default_weight=8,
    valid_signals=[
        # Granular volatility level signals
        'CALM', 'NORMAL', 'ELEVATED', 'HIGH', 'EXTREME', 'VOLATILE', 'NEAR_ADR', 'ABOVE_ADR', 'BELOW_ADR', 'WITHIN_ADR',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Granular volatility signals
        'CALM': {
                'max_points': 4,
                'formula': 'scaled'
        },
        'NORMAL': {
                'base_points': 6,
                'formula': 'scaled'
        },
        'ELEVATED': {
                'base_points': 7,
                'formula': 'scaled'
        },
        'HIGH': {
                'base_points': 8,
                'formula': 'scaled'
        },
        'EXTREME': {
                'base_points': 10,
                'formula': 'scaled'
        },
        'VOLATILE': {
                'base_points': 8,
                'formula': 'scaled'
        },
        'NEAR_ADR': {
                'base_points': 8,
                'formula': 'scaled'
        },
        'ABOVE_ADR': {
                'base_points': 8,
                'formula': 'scaled'
        },
        'BELOW_ADR': {
                'base_points': 8,
                'formula': 'scaled'
        },
        'WITHIN_ADR': {
                'base_points': 8,
                'formula': 'scaled'
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
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        }
}
)
class ADR:
    """
    ADR (Average Daily Range) - Volatility Indicator (ENHANCED 2026-01-04)
    
    Measures the average daily range (high - low) over a specified period.
    Used for:
    - Position sizing based on daily volatility
    - Setting profit targets (multiples of ADR)
    - Identifying unusually large/small daily moves
    - Comparing current range to historical average
    
    Unlike ATR which uses exponential weighting, ADR uses simple average
    and focuses specifically on daily timeframe ranges.
    
    ENHANCEMENTS (2026-01-04):
    - Fixed threshold calibration (ADR-relative instead of absolute %)
    - Added timeframe detection and auto-adjustment
    - Added variable confidence scoring
    - Added percentile tracking for historical context
    
    Parameters:
        period: Number of days to average (default: 14)
        timeframe: Data timeframe (e.g., '15min', '1hr', '4hr', '1D')
    
    Returns:
        Standardized dict with ADR value, range analysis, and target suggestions
    """
    
    def __init__(self, period: int = 14, timeframe: str = '1D', **kwargs):
        """
        Initialize ADR block with parameters
        
        Args:
            period: Number of days to average (default: 14)
            timeframe: Timeframe of the data
        """
        self.period = period
        self.timeframe = timeframe
        
        # ENHANCEMENT: Track historical ADR values for percentile calculation
        self.adr_history = []
        self.max_history = 500  # Keep last 500 ADR values
        
        # FIXED: ADR-relative thresholds instead of absolute %
        # Thresholds now based on ratio to ADR, not absolute price %
        self.adr_relative_thresholds = {
            'calm': 0.7,      # < 70% of ADR
            'normal': 1.3,    # 70-130% of ADR
            'elevated': 1.7,  # 130-170% of ADR
            'high': 2.0,      # 170-200% of ADR
            'extreme': 2.0    # > 200% of ADR
        }
    
    def calculate_daily_range(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate daily range (high - low) for each day
        
        Args:
            df: OHLCV DataFrame with timestamp, high, low columns
            
        Returns:
            Series of daily ranges
        """
        # Convert to daily data if intraday
        if self.timeframe != '1D':
            # Group by date and aggregate
            df = df.copy()
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            
            daily_data = df.groupby('date').agg({
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }).reset_index()
            
            daily_range = daily_data['high'] - daily_data['low']
        else:
            # Already daily data
            daily_range = df['high'] - df['low']
        
        return daily_range
    
    def calculate_adr(self, daily_ranges: pd.Series) -> float:
        """
        Calculate Average Daily Range
        
        Args:
            daily_ranges: Series of daily range values
            
        Returns:
            Average daily range
        """
        if len(daily_ranges) < self.period:
            return daily_ranges.mean() if len(daily_ranges) > 0 else 0.0
        
        return daily_ranges.iloc[-self.period:].mean()
    
    def calculate_range_percentile(self, current_range: float, daily_ranges: pd.Series) -> float:
        """
        Calculate where current range ranks in historical distribution
        
        Args:
            current_range: Today's range
            daily_ranges: Historical daily ranges
            
        Returns:
            Percentile rank (0-100)
        """
        if len(daily_ranges) == 0:
            return 50.0
        
        percentile = (np.sum(daily_ranges < current_range) / len(daily_ranges)) * 100
        return percentile
    
    def classify_range(self, current_range: float, adr_value: float) -> str:
        """
        FIXED: Classify daily range relative to ADR, not absolute thresholds
        
        Args:
            current_range: Current day's range (dollars)
            adr_value: Average daily range (dollars)
            
        Returns:
            Range classification
        """
        if adr_value == 0:
            return 'NORMAL'
        
        # Calculate ratio to ADR
        adr_ratio = current_range / adr_value
        
        # Classify based on ADR ratio
        if adr_ratio < self.adr_relative_thresholds['calm']:
            return 'CALM'
        elif adr_ratio < self.adr_relative_thresholds['normal']:
            return 'NORMAL'
        elif adr_ratio < self.adr_relative_thresholds['elevated']:
            return 'ELEVATED'
        elif adr_ratio < self.adr_relative_thresholds['high']:
            return 'HIGH'
        else:
            return 'EXTREME'
    
    def calculate_adr_percentile(self, current_adr: float) -> Dict[str, Any]:
        """
        ENHANCEMENT 4: Calculate ADR percentile for historical context
        """
        if len(self.adr_history) < 20:
            return {
                'has_percentile': False,
                'percentile': None,
                'relative_level': None
            }
        
        # Calculate percentile rank
        percentile = (sum(1 for adr in self.adr_history if adr < current_adr) / len(self.adr_history)) * 100
        
        # Classify relative level
        if percentile >= 95:
            relative_level = 'EXTREME_HIGH'
        elif percentile >= 85:
            relative_level = 'VERY_HIGH'
        elif percentile >= 70:
            relative_level = 'HIGH'
        elif percentile >= 30:
            relative_level = 'NORMAL'
        elif percentile >= 15:
            relative_level = 'LOW'
        elif percentile >= 5:
            relative_level = 'VERY_LOW'
        else:
            relative_level = 'EXTREME_LOW'
        
        return {
            'has_percentile': True,
            'percentile': round(percentile, 1),
            'relative_level': relative_level,
            'history_size': len(self.adr_history)
        }
    
    def calculate_variable_confidence(self, classification: str, adr_percentile_data: Dict[str, Any]) -> float:
        """
        ENHANCEMENT 3: Variable confidence based on classification and percentile
        """
        # Base confidence by classification
        if classification == 'EXTREME':
            base_confidence = 100  # Extreme volatility = highest confidence
        elif classification == 'HIGH':
            base_confidence = 90
        elif classification == 'ELEVATED':
            base_confidence = 85
        elif classification == 'NORMAL':
            base_confidence = 75
        elif classification == 'CALM':
            base_confidence = 70
        else:
            base_confidence = 60
        
        # Adjust based on percentile (if available)
        if adr_percentile_data.get('has_percentile'):
            percentile = adr_percentile_data['percentile']
            relative_level = adr_percentile_data['relative_level']
            
            # Boost confidence for extreme percentiles
            if relative_level in ['EXTREME_HIGH', 'EXTREME_LOW']:
                base_confidence = min(100, base_confidence + 10)
            elif relative_level in ['VERY_HIGH', 'VERY_LOW']:
                base_confidence = min(100, base_confidence + 5)
        
        return base_confidence
    
    def calculate_expansion_contraction(self, daily_ranges: pd.Series, lookback: int = 5) -> str:
        """
        Determine if daily ranges are expanding or contracting
        
        Args:
            daily_ranges: Series of daily ranges
            lookback: Periods to analyze
            
        Returns:
            'EXPANDING', 'CONTRACTING', or 'STABLE'
        """
        if len(daily_ranges) < lookback + 1:
            return 'INSUFFICIENT_DATA'
        
        recent_ranges = daily_ranges.iloc[-lookback:].values
        previous_ranges = daily_ranges.iloc[-(lookback*2):-lookback].values
        
        if len(previous_ranges) == 0:
            return 'INSUFFICIENT_DATA'
        
        recent_avg = np.mean(recent_ranges)
        previous_avg = np.mean(previous_ranges)
        
        # Handle division by zero
        if previous_avg == 0:
            return 'STABLE' if recent_avg == 0 else 'EXPANDING'
        
        change_pct = ((recent_avg - previous_avg) / previous_avg) * 100
        
        if change_pct > 10:
            return 'EXPANDING'
        elif change_pct < -10:
            return 'CONTRACTING'
        else:
            return 'STABLE'
    
    def suggest_targets(self, adr: float, current_price: float, 
                       multipliers: List[float] = [0.5, 1.0, 1.5, 2.0]) -> Dict[str, Dict[str, float]]:
        """
        Suggest profit targets based on ADR multiples
        
        Args:
            adr: Average daily range
            current_price: Current price
            multipliers: List of ADR multipliers for targets
            
        Returns:
            Dictionary of target suggestions
        """
        targets = {}
        
        for mult in multipliers:
            target_name = f'{mult}x_ADR'
            distance = adr * mult
            
            targets[target_name] = {
                'multiplier': mult,
                'distance': round(distance, 2),
                'long_target': round(current_price + distance, 2),
                'short_target': round(current_price - distance, 2),
                'percent': round((distance / current_price) * 100, 2)
            }
        
        return targets
    
    def calculate_position_sizing_factor(self, current_range_pct: float, adr_pct: float) -> float:
        """
        Calculate position sizing factor based on current volatility vs average
        
        Higher volatility = smaller position size
        
        Args:
            current_range_pct: Current daily range as % of price
            adr_pct: ADR as % of price
            
        Returns:
            Position sizing factor (0.5 to 1.5)
        """
        if adr_pct == 0:
            return 1.0
        
        volatility_ratio = current_range_pct / adr_pct
        
        # Inverse relationship: higher volatility = smaller size
        if volatility_ratio > 1.5:
            return 0.5  # Very high volatility - reduce position by 50%
        elif volatility_ratio > 1.2:
            return 0.75  # High volatility - reduce position by 25%
        elif volatility_ratio < 0.7:
            return 1.25  # Low volatility - increase position by 25%
        elif volatility_ratio < 0.5:
            return 1.5  # Very low volatility - increase position by 50%
        else:
            return 1.0  # Normal volatility - standard position
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method for ADR - tracks CONTINUOUS volatility level and LEVEL CHANGES
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            **kwargs: Additional parameters
        
        Returns:
            {
                'signal': str,  # Range classification (CALM/NORMAL/ELEVATED/HIGH/EXTREME)
                'confidence': float,  # 0-100 confidence score
                'metadata': dict,  # ADR values, targets, is_new_event
                'timestamp': datetime,
                'timeframe': str,
                'confluence_factors': list
            }
        """
        # Validate input data
        if not self.validate_data(df):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Invalid data format', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Need minimum data
        if len(df) < 2:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {
                    'error': f'Need at least 2 periods, got {len(df)}',
                    'required_periods': 2,
                    'provided_periods': len(df)
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate daily ranges
        daily_ranges = self.calculate_daily_range(df)
        
        # Calculate ADR
        adr_value = self.calculate_adr(daily_ranges)
        
        # ENHANCEMENT 4: Update ADR history for percentile tracking
        self.adr_history.append(adr_value)
        if len(self.adr_history) > self.max_history:
            self.adr_history.pop(0)
        
        # Calculate ADR percentile
        adr_percentile_data = self.calculate_adr_percentile(adr_value)
        
        # Get current values
        current_price = float(df['close'].iloc[-1])
        
        # ENHANCEMENT 2: Timeframe detection - get TODAY'S complete range
        if self.timeframe != '1D':
            # For intraday data, get TODAY'S aggregated range
            df_today = df.copy()
            df_today['date'] = pd.to_datetime(df_today['timestamp']).dt.date
            today = df_today['date'].iloc[-1]
            today_data = df_today[df_today['date'] == today]
            current_high = float(today_data['high'].max())
            current_low = float(today_data['low'].min())
        else:
            # For daily data, use current bar
            current_high = float(df['high'].iloc[-1])
            current_low = float(df['low'].iloc[-1])
        
        current_range = current_high - current_low
        
        # Calculate percentages
        adr_percent = (adr_value / current_price) * 100
        current_range_percent = (current_range / current_price) * 100
        
        # FIXED: Classify range using ADR-relative thresholds
        range_classification = self.classify_range(current_range, adr_value)
        
        # **NEW:** Event tracking - detect volatility LEVEL changes
        is_new_event = False
        bars_in_level = 0
        
        # Check if level changed
        if len(df) > 2:
            # Get previous bar's range and classification
            if self.timeframe == '1D':
                prev_high = float(df['high'].iloc[-2])
                prev_low = float(df['low'].iloc[-2])
            else:
                # For intraday, get previous day's range
                df_temp = df.iloc[:-1].copy()
                df_temp['date'] = pd.to_datetime(df_temp['timestamp']).dt.date
                prev_daily = df_temp.groupby('date').agg({'high': 'max', 'low': 'min', 'close': 'last'})
                if len(prev_daily) > 0:
                    prev_high = float(prev_daily['high'].iloc[-1])
                    prev_low = float(prev_daily['low'].iloc[-1])
                    prev_price = float(prev_daily['close'].iloc[-1])
                else:
                    prev_high = current_high
                    prev_low = current_low
                    prev_price = current_price
            
            prev_range = prev_high - prev_low
            prev_range_percent = (prev_range / current_price) * 100  # Use current price for consistency
            prev_classification = self.classify_range(prev_range, adr_value)
            
            # Detect level change
            is_new_event = (range_classification != prev_classification)
            
            # If not changed, approximate bars in level
            if not is_new_event:
                bars_in_level = 1  # At least 1 bar in current level
        
        # Calculate range percentile
        range_percentile = self.calculate_range_percentile(current_range, daily_ranges)
        
        # Determine expansion/contraction
        range_trend = self.calculate_expansion_contraction(daily_ranges, lookback=5)
        
        # Suggest targets
        targets = self.suggest_targets(adr_value, current_price)
        
        # Calculate position sizing factor
        position_sizing = self.calculate_position_sizing_factor(current_range_percent, adr_percent)
        
        # ENHANCEMENT 3: Calculate variable confidence
        confidence = self.calculate_variable_confidence(range_classification, adr_percentile_data)
        
        # Fresh level change boost
        if is_new_event:
            confidence = min(100, confidence + 5)
        
        # Build confluence factors
        confluence_factors = []
        
        # Event-specific confluence (volatility level changes)
        if is_new_event:
            confluence_factors.append(f'⭐ NEW VOLATILITY LEVEL: {range_classification} (range regime changed!)')
        elif bars_in_level > 0:
            confluence_factors.append(f'Continuing {range_classification.lower()} volatility ({bars_in_level} bars)')
        
        if range_classification == 'CALM':
            confluence_factors.append(f'Daily range: {range_classification} ({current_range_percent:.1f}%) - Low volatility, potential breakout setup')
        elif range_classification == 'EXTREME':
            confluence_factors.append(f'Daily range: {range_classification} ({current_range_percent:.1f}%) - Extreme volatility, reduce position size')
        elif range_classification in ['HIGH', 'ELEVATED']:
            confluence_factors.append(f'Daily range: {range_classification} ({current_range_percent:.1f}%) - Elevated volatility, widen stops')
        else:
            confluence_factors.append(f'Daily range: {range_classification} ({current_range_percent:.1f}%) - Normal volatility conditions')
        
        if range_trend == 'EXPANDING':
            confluence_factors.append('Daily ranges expanding - increasing volatility trend')
        elif range_trend == 'CONTRACTING':
            confluence_factors.append('Daily ranges contracting - decreasing volatility, compression phase')
        
        if range_percentile > 80:
            confluence_factors.append(f'Current range at {range_percentile:.0f}th percentile - unusually large move')
        elif range_percentile < 20:
            confluence_factors.append(f'Current range at {range_percentile:.0f}th percentile - unusually small move')
        
        # ENHANCEMENT 4: Add ADR percentile context
        if adr_percentile_data.get('has_percentile'):
            percentile = adr_percentile_data['percentile']
            relative_level = adr_percentile_data['relative_level']
            
            if relative_level in ['EXTREME_HIGH', 'VERY_HIGH']:
                confluence_factors.append(f'⚠️ ADR at {percentile:.0f}th percentile - EXTREME average volatility (+10 confidence)')
            elif relative_level in ['EXTREME_LOW', 'VERY_LOW']:
                confluence_factors.append(f'ADR at {percentile:.0f}th percentile - VERY LOW average volatility')
        
        if position_sizing < 1.0:
            confluence_factors.append(f'Position sizing: {position_sizing}x - reduce size due to high volatility')
        elif position_sizing > 1.0:
            confluence_factors.append(f'Position sizing: {position_sizing}x - can increase size due to low volatility')
        
        # Prepare metadata (ENHANCED)
        metadata = {
            'adr_value': round(adr_value, 2),
            'adr_percent': round(adr_percent, 2),
            'current_range': round(current_range, 2),
            'current_range_percent': round(current_range_percent, 2),
            'current_price': round(current_price, 2),
            'range_classification': range_classification,
            'range_percentile': round(range_percentile, 2),
            'range_trend': range_trend,
            'period': self.period,
            'targets': targets,
            'position_sizing_factor': position_sizing,
            'daily_ranges_analyzed': len(daily_ranges),
            'recent_ranges': daily_ranges.tail(10).tolist() if len(daily_ranges) > 0 else [],
            'is_new_event': is_new_event,
            'bars_in_level': bars_in_level,
            # ENHANCEMENTS
            'adr_ratio': round(current_range / adr_value, 2) if adr_value > 0 else 0,
            'has_adr_percentile': adr_percentile_data.get('has_percentile', False),
            'adr_percentile': adr_percentile_data.get('percentile'),
            'relative_adr_level': adr_percentile_data.get('relative_level'),
            'history_size': adr_percentile_data.get('history_size', len(self.adr_history))
        }
        
        return {
            'signal': range_classification,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate input data has required columns
        
        Args:
            df: Input DataFrame
            
        Returns:
            True if valid, False otherwise
        """
        required_cols = ['high', 'low', 'close', 'timestamp']
        return all(col in df.columns for col in required_cols)


# Usage example
if __name__ == "__main__":
    # Test with sample Bitcoin data
    dates = pd.date_range(start='2024-01-01', periods=30, freq='1D')
    
    # Create sample daily data with varying ranges
    np.random.seed(42)
    base_price = 45000
    
    # Simulate daily price action with different volatility regimes
    ranges = []
    for i in range(30):
        if i < 10:
            daily_range = np.random.uniform(500, 1000)  # Low volatility
        elif i < 20:
            daily_range = np.random.uniform(1500, 2500)  # Normal volatility
        else:
            daily_range = np.random.uniform(3000, 5000)  # High volatility
        ranges.append(daily_range)
    
    data = {
        'timestamp': dates,
        'open': [base_price] * 30,
        'high': [base_price + r/2 for r in ranges],
        'low': [base_price - r/2 for r in ranges],
        'close': [base_price] * 30,
        'volume': np.random.uniform(1000, 10000, 30)
    }
    
    df = pd.DataFrame(data)
    
    # Test ADR block
    adr_block = ADR(period=14, timeframe='1D')
    result = adr_block.analyze(df)
    
    print("=" * 80)
    print("ADR (AVERAGE DAILY RANGE) BUILDING BLOCK - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nADR Analysis:")
    print(f"  ADR Value: ${result['metadata']['adr_value']:.2f}")
    print(f"  ADR %: {result['metadata']['adr_percent']:.2f}%")
    print(f"  Current Range: ${result['metadata']['current_range']:.2f}")
    print(f"  Current Range %: {result['metadata']['current_range_percent']:.2f}%")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"\nClassification:")
    print(f"  Range Classification: {result['metadata']['range_classification']}")
    print(f"  Range Percentile: {result['metadata']['range_percentile']:.1f}th")
    print(f"  Range Trend: {result['metadata']['range_trend']}")
    print(f"\nPosition Sizing:")
    print(f"  Factor: {result['metadata']['position_sizing_factor']}x")
    print(f"\nProfit Targets:")
    for target_name, target_data in result['metadata']['targets'].items():
        print(f"  {target_name}: ${target_data['long_target']:.2f} (+{target_data['percent']:.1f}%)")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
