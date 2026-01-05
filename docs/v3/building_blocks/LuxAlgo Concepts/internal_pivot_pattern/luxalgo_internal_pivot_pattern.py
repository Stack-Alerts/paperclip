"""
LuxAlgo Internal Pivot Pattern - Core Implementation
==================================================

Internal pivot detection using lower timeframe data within current candle
for real-time trend identification and market structure analysis.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta


class PivotType(Enum):
    """Pivot classification."""
    HIGH = 'high'
    LOW = 'low'
    NONE = 'none'


class TrendDirection(Enum):
    """Trend classification."""
    UPTREND = 'uptrend'
    DOWNTREND = 'downtrend'
    NEUTRAL = 'neutral'


@dataclass
class InternalPivot:
    """Detected internal pivot point."""
    timestamp: pd.Timestamp
    pivot_type: PivotType
    pivot_price: float
    bar_index: int
    intrabar_index: int  # Position within lower TF bars
    
    # For zigzag
    previous_pivot: Optional['InternalPivot'] = None
    
    # Strength metrics
    pivot_depth: float = 0.0  # How deep the pivot
    num_touches: int = 0  # Times this level was tested
    

@dataclass
class PivotAccuracy:
    """Measure pivot accuracy."""
    pivot: InternalPivot
    is_accurate: bool
    higher_after: Optional[float] = None  # Price reached after pivot
    bars_to_confirm: int = 0


class InternalPivotDetector:
    """Detect internal pivots from lower timeframe data."""
    
    def __init__(self, pivot_lookback: int = 21):
        """
        Initialize pivot detector.
        
        Args:
            pivot_lookback: Bars to look back for pivot detection
        """
        self.pivot_lookback = pivot_lookback
    
    def detect_pivot_low(self, intrabar_closes: List[float],
                        intrabar_highs: List[float],
                        intrabar_lows: List[float]) -> Optional[float]:
        """
        Detect pivot low from intrabar data.
        
        Pivot Low: Middle bar is lowest within lookback period
        
        Args:
            intrabar_closes: Intrabar closing prices
            intrabar_highs: Intrabar highs
            intrabar_lows: Intrabar lows
        
        Returns:
            Pivot low price if detected
        """
        if len(intrabar_lows) < self.pivot_lookback:
            return None
        
        # Get middle bar
        mid_idx = len(intrabar_lows) // 2
        
        if mid_idx == 0 or mid_idx == len(intrabar_lows) - 1:
            return None
        
        mid_low = intrabar_lows[mid_idx]
        
        # Check if middle is lowest within lookback
        left_bound = max(0, mid_idx - self.pivot_lookback // 2)
        right_bound = min(len(intrabar_lows), mid_idx + self.pivot_lookback // 2 + 1)
        
        lookback_slice = intrabar_lows[left_bound:right_bound]
        
        if mid_low == min(lookback_slice):
            return mid_low
        
        return None
    
    def detect_pivot_high(self, intrabar_closes: List[float],
                         intrabar_highs: List[float],
                         intrabar_lows: List[float]) -> Optional[float]:
        """
        Detect pivot high from intrabar data.
        
        Pivot High: Middle bar is highest within lookback period
        
        Args:
            intrabar_closes: Intrabar closing prices
            intrabar_highs: Intrabar highs
            intrabar_lows: Intrabar lows
        
        Returns:
            Pivot high price if detected
        """
        if len(intrabar_highs) < self.pivot_lookback:
            return None
        
        # Get middle bar
        mid_idx = len(intrabar_highs) // 2
        
        if mid_idx == 0 or mid_idx == len(intrabar_highs) - 1:
            return None
        
        mid_high = intrabar_highs[mid_idx]
        
        # Check if middle is highest within lookback
        left_bound = max(0, mid_idx - self.pivot_lookback // 2)
        right_bound = min(len(intrabar_highs), mid_idx + self.pivot_lookback // 2 + 1)
        
        lookback_slice = intrabar_highs[left_bound:right_bound]
        
        if mid_high == max(lookback_slice):
            return mid_high
        
        return None
    
    def calculate_pivot_depth(self, pivot_price: float,
                             prices: List[float],
                             pivot_type: PivotType) -> float:
        """
        Calculate how deep/strong the pivot is.
        
        Args:
            pivot_price: Pivot level
            prices: Price data around pivot
            pivot_type: High or low
        
        Returns:
            Depth score (0-100)
        """
        if not prices or len(prices) < 2:
            return 50.0
        
        if pivot_type == PivotType.LOW:
            # How much lower is pivot vs surrounding
            surrounding_avg = np.mean([p for p in prices if p > pivot_price])
            if surrounding_avg == 0:
                return 50.0
            depth = ((surrounding_avg - pivot_price) / surrounding_avg) * 100
        else:  # HIGH
            # How much higher is pivot vs surrounding
            surrounding_avg = np.mean([p for p in prices if p < pivot_price])
            if surrounding_avg == 0:
                return 50.0
            depth = ((pivot_price - surrounding_avg) / surrounding_avg) * 100
        
        return min(100, max(0, depth * 10))  # Scale to 0-100


class ZigzagBuilder:
    """Build zigzag lines connecting pivots."""
    
    @staticmethod
    def build_zigzag(pivots: List[InternalPivot]) -> List[Tuple[InternalPivot, InternalPivot]]:
        """
        Connect pivots into zigzag lines.
        
        Args:
            pivots: List of detected pivots (chronological)
        
        Returns:
            List of tuples (from_pivot, to_pivot)
        """
        if len(pivots) < 2:
            return []
        
        zigzag = []
        valid_pivots = []
        
        for pivot in pivots:
            if not valid_pivots:
                valid_pivots.append(pivot)
            else:
                # Only add if different type from last
                last_pivot = valid_pivots[-1]
                if pivot.pivot_type != last_pivot.pivot_type:
                    valid_pivots.append(pivot)
        
        # Create connections
        for i in range(len(valid_pivots) - 1):
            zigzag.append((valid_pivots[i], valid_pivots[i + 1]))
        
        return zigzag


class AccuracyDashboard:
    """Measure pivot detection accuracy."""
    
    @staticmethod
    def measure_accuracy(pivots: List[InternalPivot],
                        df: pd.DataFrame,
                        lookforward_bars: int = 10) -> List[PivotAccuracy]:
        """
        Measure accuracy of detected pivots.
        
        Pivot Low Accurate: If next pivot detected is higher
        Pivot High Accurate: If next pivot detected is lower
        
        Args:
            pivots: List of detected pivots
            df: OHLCV DataFrame
            lookforward_bars: Bars to look forward
        
        Returns:
            List of accuracy measurements
        """
        accuracies = []
        
        for i, pivot in enumerate(pivots):
            if i == len(pivots) - 1:
                continue  # Can't measure last pivot
            
            next_pivot = pivots[i + 1]
            
            if pivot.pivot_type == PivotType.LOW:
                # Accurate if next pivot is higher
                is_accurate = next_pivot.pivot_price > pivot.pivot_price
            else:  # HIGH
                # Accurate if next pivot is lower
                is_accurate = next_pivot.pivot_price < pivot.pivot_price
            
            bars_between = next_pivot.bar_index - pivot.bar_index
            
            accuracies.append(PivotAccuracy(
                pivot=pivot,
                is_accurate=is_accurate,
                higher_after=next_pivot.pivot_price,
                bars_to_confirm=bars_between,
            ))
        
        return accuracies
    
    @staticmethod
    def calculate_accuracy_percentage(accuracies: List[PivotAccuracy]) -> float:
        """
        Calculate overall accuracy percentage.
        
        Args:
            accuracies: List of accuracy measurements
        
        Returns:
            Accuracy percentage (0-100)
        """
        if not accuracies:
            return 0.0
        
        correct = sum(1 for a in accuracies if a.is_accurate)
        return (correct / len(accuracies)) * 100


class TrendDeterminer:
    """Determine trend from pivots."""
    
    @staticmethod
    def determine_trend(pivots: List[InternalPivot]) -> TrendDirection:
        """
        Determine overall trend from recent pivots.
        
        Uptrend: Last pivot is LOW, higher than previous
        Downtrend: Last pivot is HIGH, lower than previous
        
        Args:
            pivots: List of detected pivots
        
        Returns:
            Trend direction
        """
        if len(pivots) < 2:
            return TrendDirection.NEUTRAL
        
        last_pivot = pivots[-1]
        second_last = pivots[-2]
        
        if last_pivot.pivot_type == PivotType.LOW and last_pivot.pivot_price > second_last.pivot_price:
            return TrendDirection.UPTREND
        elif last_pivot.pivot_type == PivotType.HIGH and last_pivot.pivot_price < second_last.pivot_price:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.NEUTRAL


class InternalPivotPattern:
    """Complete internal pivot pattern detection system."""
    
    def __init__(self, pivot_lookback: int = 21,
                 timeframe_ratio: int = 4,
                 show_accuracy_dashboard: bool = True):
        """
        Initialize internal pivot detector.
        
        Args:
            pivot_lookback: Bars to look back for pivot
            timeframe_ratio: Ratio of intrabar to main timeframe
            show_accuracy_dashboard: Display accuracy stats
        """
        self.pivot_lookback = pivot_lookback
        self.timeframe_ratio = timeframe_ratio
        self.show_accuracy_dashboard = show_accuracy_dashboard
        self.detector = InternalPivotDetector(pivot_lookback)
    
    def analyze(self, df: pd.DataFrame,
               intrabar_df: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        Detect internal pivots and analyze trends.
        
        Args:
            df: Main timeframe OHLCV DataFrame
            intrabar_df: Lower timeframe OHLCV data (optional)
        
        Returns:
            Tuple of (DataFrame with analysis, results dict)
        """
        pivots = []
        
        if intrabar_df is None:
            # Simulate lower timeframe from main bars
            intrabar_df = self._simulate_intrabar_data(df)
        
        # Detect pivots for each main bar
        for i in range(self.pivot_lookback, len(df)):
            bar_time = df.index[i]
            
            # Get intrabar data for this bar
            intrabar_mask = (intrabar_df.index >= df.index[i-1]) & (intrabar_df.index <= df.index[i])
            intrabar_slice = intrabar_df[intrabar_mask]
            
            if len(intrabar_slice) < 3:
                continue
            
            closes = intrabar_slice['close'].tolist()
            highs = intrabar_slice['high'].tolist()
            lows = intrabar_slice['low'].tolist()
            
            # Try to detect pivot low
            pivot_low = self.detector.detect_pivot_low(closes, highs, lows)
            if pivot_low is not None:
                depth = self.detector.calculate_pivot_depth(pivot_low, lows, PivotType.LOW)
                pivots.append(InternalPivot(
                    timestamp=bar_time,
                    pivot_type=PivotType.LOW,
                    pivot_price=pivot_low,
                    bar_index=i,
                    intrabar_index=len(intrabar_slice) // 2,
                    pivot_depth=depth,
                ))
            
            # Try to detect pivot high
            pivot_high = self.detector.detect_pivot_high(closes, highs, lows)
            if pivot_high is not None:
                depth = self.detector.calculate_pivot_depth(pivot_high, highs, PivotType.HIGH)
                pivots.append(InternalPivot(
                    timestamp=bar_time,
                    pivot_type=PivotType.HIGH,
                    pivot_price=pivot_high,
                    bar_index=i,
                    intrabar_index=len(intrabar_slice) // 2,
                    pivot_depth=depth,
                ))
        
        # Build zigzag
        zigzag = ZigzagBuilder.build_zigzag(pivots)
        
        # Calculate accuracy
        accuracies = AccuracyDashboard.measure_accuracy(pivots, df)
        accuracy_pct = AccuracyDashboard.calculate_accuracy_percentage(accuracies)
        
        # Determine trend
        trend = TrendDeterminer.determine_trend(pivots)
        
        # Create result DataFrame
        df_result = df.copy()
        df_result['pivot_type'] = ''
        df_result['pivot_price'] = np.nan
        df_result['pivot_depth'] = 0.0
        df_result['trend'] = TrendDirection.NEUTRAL.value
        
        for pivot in pivots:
            if pivot.bar_index < len(df_result):
                df_result.iloc[pivot.bar_index, df_result.columns.get_loc('pivot_type')] = pivot.pivot_type.value
                df_result.iloc[pivot.bar_index, df_result.columns.get_loc('pivot_price')] = pivot.pivot_price
                df_result.iloc[pivot.bar_index, df_result.columns.get_loc('pivot_depth')] = pivot.pivot_depth
        
        # Apply trend color to all bars after pivot
        current_trend = TrendDirection.NEUTRAL
        for i in range(len(df_result)):
            if df_result.iloc[i]['pivot_type'] != '':
                if df_result.iloc[i]['pivot_type'] == PivotType.LOW.value:
                    current_trend = TrendDirection.UPTREND
                else:
                    current_trend = TrendDirection.DOWNTREND
            df_result.iloc[i, df_result.columns.get_loc('trend')] = current_trend.value
        
        return df_result, {
            'pivots': pivots,
            'pivot_lows': [p for p in pivots if p.pivot_type == PivotType.LOW],
            'pivot_highs': [p for p in pivots if p.pivot_type == PivotType.HIGH],
            'total_pivots': len(pivots),
            'zigzag': zigzag,
            'accuracies': accuracies,
            'accuracy_percentage': accuracy_pct,
            'current_trend': trend,
        }
    
    def _simulate_intrabar_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Simulate lower timeframe data from main bars.
        
        Args:
            df: Main timeframe DataFrame
        
        Returns:
            Simulated intrabar DataFrame
        """
        intrabar_data = []
        
        for i in range(len(df)):
            bar = df.iloc[i]
            
            # Create timeframe_ratio bars within this bar
            for j in range(self.timeframe_ratio):
                # Simulate intrabar movement
                frac = j / self.timeframe_ratio
                
                # Linear interpolation from open to close
                mid_price = bar['open'] + (bar['close'] - bar['open']) * frac
                
                # Add some noise within the bar
                noise = (bar['high'] - bar['low']) * 0.1 * np.sin(j)
                
                intrabar_data.append({
                    'timestamp': bar.name + timedelta(minutes=(j+1) * 60 // self.timeframe_ratio),
                    'open': mid_price - noise,
                    'high': max(mid_price, bar['high']),
                    'low': min(mid_price, bar['low']),
                    'close': mid_price + noise,
                })
        
        intrabar_df = pd.DataFrame(intrabar_data)
        intrabar_df.set_index('timestamp', inplace=True)
        
        return intrabar_df


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=100, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(100) * 0.2,
        'high': prices + np.abs(np.random.randn(100) * 0.5),
        'low': prices - np.abs(np.random.randn(100) * 0.5),
        'close': prices,
    }, index=dates)
    
    ipp = InternalPivotPattern(pivot_lookback=21, timeframe_ratio=4)
    df_result, results = ipp.analyze(df)
    
    print("=" * 70)
    print("INTERNAL PIVOT PATTERN - ANALYSIS")
    print("=" * 70)
    
    print(f"\n✓ Total Pivots: {results['total_pivots']}")
    print(f"  Pivot Lows: {len(results['pivot_lows'])}")
    print(f"  Pivot Highs: {len(results['pivot_highs'])}")
    
    print(f"\n✓ Accuracy: {results['accuracy_percentage']:.1f}%")
    print(f"✓ Current Trend: {results['current_trend'].value.upper()}")
    
    if results['pivots']:
        print(f"\nRecent Pivots:")
        for pivot in results['pivots'][-5:]:
            print(f"  {pivot.timestamp.date()}: {pivot.pivot_type.value.upper()} @ ${pivot.pivot_price:.2f}")
