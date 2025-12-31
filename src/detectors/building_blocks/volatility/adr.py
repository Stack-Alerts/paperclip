"""
ADR (Average Daily Range) Building Block
Category: Volatility Indicators
Purpose: Measures average daily price range for position sizing and target setting
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class ADR:
    """
    ADR (Average Daily Range) - Volatility Indicator
    
    Measures the average daily range (high - low) over a specified period.
    Used for:
    - Position sizing based on daily volatility
    - Setting profit targets (multiples of ADR)
    - Identifying unusually large/small daily moves
    - Comparing current range to historical average
    
    Unlike ATR which uses exponential weighting, ADR uses simple average
    and focuses specifically on daily timeframe ranges.
    
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
        
        # Bitcoin-specific ADR thresholds (as percentage of price)
        # These represent typical daily ranges for BTC
        self.btc_range_thresholds = {
            'calm': 2.0,      # < 2% daily range
            'normal': 4.0,    # 2-4% daily range
            'elevated': 6.0,  # 4-6% daily range
            'high': 8.0,      # 6-8% daily range
            'extreme': 8.0    # > 8% daily range
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
    
    def classify_range(self, range_percent: float) -> str:
        """
        Classify daily range as calm, normal, elevated, high, or extreme
        
        Args:
            range_percent: Range as percentage of price
            
        Returns:
            Range classification
        """
        if range_percent < self.btc_range_thresholds['calm']:
            return 'CALM'
        elif range_percent < self.btc_range_thresholds['normal']:
            return 'NORMAL'
        elif range_percent < self.btc_range_thresholds['elevated']:
            return 'ELEVATED'
        elif range_percent < self.btc_range_thresholds['high']:
            return 'HIGH'
        else:
            return 'EXTREME'
    
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
        Main analysis method for ADR building block
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            **kwargs: Additional parameters
        
        Returns:
            {
                'signal': str,  # Range classification
                'confidence': float,  # 0-100 confidence score
                'metadata': dict,  # ADR values, targets, etc.
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
                'metadata': {'error': 'Invalid data format'},
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
        
        # Get current values
        current_price = float(df['close'].iloc[-1])
        current_high = float(df['high'].iloc[-1]) if self.timeframe == '1D' else float(df.groupby(pd.to_datetime(df['timestamp']).dt.date)['high'].max().iloc[-1])
        current_low = float(df['low'].iloc[-1]) if self.timeframe == '1D' else float(df.groupby(pd.to_datetime(df['timestamp']).dt.date)['low'].min().iloc[-1])
        current_range = current_high - current_low
        
        # Calculate percentages
        adr_percent = (adr_value / current_price) * 100
        current_range_percent = (current_range / current_price) * 100
        
        # Classify range
        range_classification = self.classify_range(current_range_percent)
        
        # Calculate range percentile
        range_percentile = self.calculate_range_percentile(current_range, daily_ranges)
        
        # Determine expansion/contraction
        range_trend = self.calculate_expansion_contraction(daily_ranges, lookback=5)
        
        # Suggest targets
        targets = self.suggest_targets(adr_value, current_price)
        
        # Calculate position sizing factor
        position_sizing = self.calculate_position_sizing_factor(current_range_percent, adr_percent)
        
        # Calculate confidence
        data_completeness = min(100, (len(daily_ranges) / self.period) * 100)
        confidence = data_completeness
        
        # Build confluence factors
        confluence_factors = []
        
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
        
        if position_sizing < 1.0:
            confluence_factors.append(f'Position sizing: {position_sizing}x - reduce size due to high volatility')
        elif position_sizing > 1.0:
            confluence_factors.append(f'Position sizing: {position_sizing}x - can increase size due to low volatility')
        
        # Prepare metadata
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
            'recent_ranges': daily_ranges.tail(10).tolist() if len(daily_ranges) > 0 else []
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
