"""
LuxAlgo Island Reversal Pattern Detection Implementation
=========================================================

A robust, production-ready implementation of LuxAlgo's Island Reversal
indicator. Detects powerful reversal formations that mark key turning points
in market trends with advanced filtering options.

Features:
    - Bullish and bearish island reversal detection
    - Gap identification and measurement
    - Consolidation phase analysis
    - Trend filter (preceding trend strength)
    - Volume filter (activity during island phase)
    - Horizontality filter (R² statistical measure)
    - Volatility filter (range control)
    - Pattern quality scoring
    - Reversal signal generation

Author: Advanced Trading Systems
Date: 2026
Python: 3.8+

Dependencies:
    - pandas>=1.3.0
    - numpy>=1.21.0
    - scipy>=1.7.0 (for linear regression R²)

Island Reversal Pattern:
    Classic structure:
    1. Strong preceding trend
    2. First gap (trend direction)
    3. Consolidation/island phase
    4. Second gap (opposite direction)
    5. Trend reversal confirmation
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime, timedelta
import warnings

try:
    from scipy import stats
except ImportError:
    stats = None


class ReversalDirection(Enum):
    """Direction of island reversal."""
    BULLISH = "bullish"  # Reversal from downtrend to uptrend
    BEARISH = "bearish"  # Reversal from uptrend to downtrend


class PatternQuality(Enum):
    """Quality assessment of island reversal pattern."""
    EXCELLENT = "excellent"  # All filters pass, strong signals
    GOOD = "good"  # Most filters pass, solid pattern
    FAIR = "fair"  # Some filters pass, weaker pattern
    POOR = "poor"  # Few filters pass, weak pattern


@dataclass
class Gap:
    """Data structure for gap information."""
    gap_start_timestamp: datetime
    gap_end_timestamp: datetime
    gap_size: float
    gap_size_pct: float
    gap_direction: str  # 'up' or 'down'
    open_price: float
    close_price: float
    gap_high: float
    gap_low: float
    
    def get_gap_body(self) -> float:
        """Get the size of gap body (open to close)."""
        return abs(self.close_price - self.open_price)
    
    def get_wick_size(self) -> float:
        """Get the size of wick within gap."""
        if self.gap_direction == 'up':
            return self.gap_high - self.gap_low
        else:
            return self.gap_high - self.gap_low


@dataclass
class IslandConsolidation:
    """Data structure for the consolidation island phase."""
    start_timestamp: datetime
    end_timestamp: datetime
    bar_count: int
    high_price: float
    low_price: float
    close_price: float
    range_size: float
    volume_sum: float
    volume_avg: float
    
    def get_range_pct(self, reference_price: float) -> float:
        """Get range as percentage of reference price."""
        return (self.range_size / reference_price) * 100
    
    def get_horizontality_r_squared(self, prices: List[float]) -> float:
        """Calculate R² for consolidation horizontality."""
        if stats is None or len(prices) < 2:
            return 0.0
        
        x = np.arange(len(prices))
        y = np.array(prices)
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        return r_value ** 2  # R²


@dataclass
class IslandReversalPattern:
    """Data structure for complete island reversal pattern."""
    direction: ReversalDirection
    first_gap: Gap
    island_consolidation: IslandConsolidation
    second_gap: Gap
    pattern_start_timestamp: datetime
    pattern_end_timestamp: datetime
    total_bars: int
    trend_strength: float  # 0-1, how strong preceding trend was
    quality: PatternQuality
    quality_score: float  # 0-1 composite score
    
    # Filter results
    trend_filter_pass: bool
    volume_filter_pass: bool
    horizontality_filter_pass: bool
    volatility_filter_pass: bool
    
    # Support/Resistance
    reversal_level: float  # Island consolidation midpoint
    support_level: Optional[float] = None  # For bullish reversal
    resistance_level: Optional[float] = None  # For bearish reversal
    
    def get_total_pattern_size(self) -> float:
        """Get total vertical size of pattern."""
        return abs(self.second_gap.gap_high - self.first_gap.gap_low)
    
    def get_pattern_purity(self) -> float:
        """Measure how 'clean' the pattern is (0-1)."""
        # Perfect purity when gaps don't overlap with island
        if self.direction == ReversalDirection.BULLISH:
            no_overlap = self.second_gap.gap_low > self.island_consolidation.high_price
        else:
            no_overlap = self.second_gap.gap_high < self.island_consolidation.low_price
        
        purity = 1.0 if no_overlap else 0.7
        return purity


class IslandReversalDetector:
    """
    Main class for detecting island reversal patterns.
    
    Island reversals are powerful technical patterns indicating trend exhaustion
    and reversal. They consist of:
    1. Initial gap continuing the existing trend
    2. Consolidation phase (the "island")
    3. Final gap in opposite direction
    4. Often marks significant trend reversal
    """
    
    def __init__(
        self,
        min_gap_size_pct: float = 0.5,  # Minimum gap size as % of price
        trend_length: int = 20,  # Bars for trend calculation
        min_island_bars: int = 2,
        max_island_bars: int = 50,
        trend_filter_enabled: bool = True,
        trend_threshold: float = 0.5,
        volume_filter_enabled: bool = True,
        horizontality_filter_enabled: bool = True,
        horizontality_threshold: float = 0.5,  # R² threshold
        volatility_filter_enabled: bool = True,
        volatility_multiplier: float = 1.5,
        min_quality_score: float = 0.5,
    ):
        """
        Initialize the Island Reversal Detector.
        
        Args:
            min_gap_size_pct: Minimum gap as % of price
            trend_length: Bars to measure trend strength
            min_island_bars: Minimum bars in consolidation
            max_island_bars: Maximum bars in consolidation
            trend_filter_enabled: Apply trend filter
            trend_threshold: Trend strength requirement (0-1)
            volume_filter_enabled: Apply volume filter
            horizontality_filter_enabled: Apply R² filter
            horizontality_threshold: R² threshold (0-1)
            volatility_filter_enabled: Apply volatility filter
            volatility_multiplier: Range size multiplier
            min_quality_score: Minimum pattern quality
        """
        self.min_gap_size_pct = min_gap_size_pct
        self.trend_length = trend_length
        self.min_island_bars = min_island_bars
        self.max_island_bars = max_island_bars
        self.trend_filter_enabled = trend_filter_enabled
        self.trend_threshold = trend_threshold
        self.volume_filter_enabled = volume_filter_enabled
        self.horizontality_filter_enabled = horizontality_filter_enabled
        self.horizontality_threshold = horizontality_threshold
        self.volatility_filter_enabled = volatility_filter_enabled
        self.volatility_multiplier = volatility_multiplier
        self.min_quality_score = min_quality_score
        
        self._validate_parameters()
    
    def _validate_parameters(self) -> None:
        """Validate initialization parameters."""
        if self.min_gap_size_pct < 0.1:
            raise ValueError(f"min_gap_size_pct must be >= 0.1, got {self.min_gap_size_pct}")
        if self.trend_length < 5:
            raise ValueError(f"trend_length must be >= 5, got {self.trend_length}")
        if self.min_island_bars < 1:
            raise ValueError(f"min_island_bars must be >= 1, got {self.min_island_bars}")
        if not 0 <= self.trend_threshold <= 1:
            raise ValueError(f"trend_threshold must be 0-1, got {self.trend_threshold}")
    
    def detect_gaps(self, df: pd.DataFrame) -> List[Gap]:
        """
        Detect gaps in price action.
        
        Args:
            df: OHLCV DataFrame with DatetimeIndex
        
        Returns:
            List of Gap objects
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        
        required_cols = {'open', 'high', 'low', 'close'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain {required_cols}")
        
        gaps = []
        
        for i in range(1, len(df)):
            current_bar = df.iloc[i]
            previous_bar = df.iloc[i - 1]
            
            # Check for gap up
            if current_bar['open'] > previous_bar['high']:
                gap_size = current_bar['open'] - previous_bar['high']
                gap_size_pct = (gap_size / previous_bar['high']) * 100
                
                if gap_size_pct >= self.min_gap_size_pct:
                    gap = Gap(
                        gap_start_timestamp=df.index[i - 1],
                        gap_end_timestamp=df.index[i],
                        gap_size=gap_size,
                        gap_size_pct=gap_size_pct,
                        gap_direction='up',
                        open_price=current_bar['open'],
                        close_price=current_bar['close'],
                        gap_high=current_bar['high'],
                        gap_low=min(previous_bar['high'], current_bar['low']),
                    )
                    gaps.append(gap)
            
            # Check for gap down
            elif current_bar['open'] < previous_bar['low']:
                gap_size = previous_bar['low'] - current_bar['open']
                gap_size_pct = (gap_size / previous_bar['low']) * 100
                
                if gap_size_pct >= self.min_gap_size_pct:
                    gap = Gap(
                        gap_start_timestamp=df.index[i - 1],
                        gap_end_timestamp=df.index[i],
                        gap_size=gap_size,
                        gap_size_pct=gap_size_pct,
                        gap_direction='down',
                        open_price=current_bar['open'],
                        close_price=current_bar['close'],
                        gap_high=max(previous_bar['low'], current_bar['high']),
                        gap_low=current_bar['low'],
                    )
                    gaps.append(gap)
        
        return gaps
    
    def detect_island_reversals(
        self, df: pd.DataFrame, gaps: Optional[List[Gap]] = None
    ) -> List[IslandReversalPattern]:
        """
        Detect complete island reversal patterns.
        
        Args:
            df: OHLCV DataFrame with DatetimeIndex
            gaps: List of gaps (will detect if None)
        
        Returns:
            List of IslandReversalPattern objects
        """
        if gaps is None:
            gaps = self.detect_gaps(df)
        
        patterns = []
        
        # Look for pairs of opposite-direction gaps with consolidation between
        for i in range(len(gaps) - 1):
            first_gap = gaps[i]
            
            for j in range(i + 1, len(gaps)):
                second_gap = gaps[j]
                
                # Check if gaps are opposite direction
                if first_gap.gap_direction == second_gap.gap_direction:
                    continue
                
                # Get consolidation period between gaps
                consolidation_start_idx = df.index.get_loc(first_gap.gap_end_timestamp)
                consolidation_end_idx = df.index.get_loc(second_gap.gap_start_timestamp)
                
                if consolidation_end_idx <= consolidation_start_idx:
                    continue
                
                consolidation_df = df.iloc[consolidation_start_idx:consolidation_end_idx + 1]
                
                # Check consolidation criteria
                bar_count = len(consolidation_df)
                if not (self.min_island_bars <= bar_count <= self.max_island_bars):
                    continue
                
                # Create consolidation object
                island = IslandConsolidation(
                    start_timestamp=consolidation_df.index[0],
                    end_timestamp=consolidation_df.index[-1],
                    bar_count=bar_count,
                    high_price=consolidation_df['high'].max(),
                    low_price=consolidation_df['low'].min(),
                    close_price=consolidation_df['close'].iloc[-1],
                    range_size=consolidation_df['high'].max() - consolidation_df['low'].min(),
                    volume_sum=consolidation_df['volume'].sum() if 'volume' in consolidation_df else 0,
                    volume_avg=consolidation_df['volume'].mean() if 'volume' in consolidation_df else 0,
                )
                
                # Determine reversal direction
                if first_gap.gap_direction == 'up':
                    direction = ReversalDirection.BULLISH
                else:
                    direction = ReversalDirection.BEARISH
                
                # Calculate trend strength
                trend_idx = consolidation_start_idx - self.trend_length
                if trend_idx < 0:
                    trend_idx = 0
                
                trend_strength = self._calculate_trend_strength(
                    df.iloc[trend_idx:consolidation_start_idx],
                    direction
                )
                
                # Apply filters
                trend_pass = not self.trend_filter_enabled or trend_strength >= self.trend_threshold
                volume_pass = self._check_volume_filter(df, consolidation_df, first_gap, consolidation_end_idx)
                horizontal_pass, r_squared = self._check_horizontality_filter(consolidation_df)
                volatility_pass = self._check_volatility_filter(consolidation_df)
                
                # Calculate quality score
                quality_score = self._calculate_quality_score(
                    trend_strength, r_squared,
                    trend_pass, volume_pass, horizontal_pass, volatility_pass
                )
                
                if quality_score < self.min_quality_score:
                    continue
                
                # Determine quality level
                passing_filters = sum([
                    trend_pass if self.trend_filter_enabled else True,
                    volume_pass if self.volume_filter_enabled else True,
                    horizontal_pass if self.horizontality_filter_enabled else True,
                    volatility_pass if self.volatility_filter_enabled else True,
                ])
                total_filters = sum([
                    self.trend_filter_enabled,
                    self.volume_filter_enabled,
                    self.horizontality_filter_enabled,
                    self.volatility_filter_enabled,
                ])
                
                if passing_filters >= total_filters:
                    quality = PatternQuality.EXCELLENT
                elif passing_filters >= total_filters * 0.75:
                    quality = PatternQuality.GOOD
                elif passing_filters >= total_filters * 0.5:
                    quality = PatternQuality.FAIR
                else:
                    quality = PatternQuality.POOR
                
                # Create pattern
                pattern = IslandReversalPattern(
                    direction=direction,
                    first_gap=first_gap,
                    island_consolidation=island,
                    second_gap=second_gap,
                    pattern_start_timestamp=first_gap.gap_start_timestamp,
                    pattern_end_timestamp=second_gap.gap_end_timestamp,
                    total_bars=consolidation_end_idx - consolidation_start_idx + 2,
                    trend_strength=trend_strength,
                    quality=quality,
                    quality_score=quality_score,
                    trend_filter_pass=trend_pass,
                    volume_filter_pass=volume_pass,
                    horizontality_filter_pass=horizontal_pass,
                    volatility_filter_pass=volatility_pass,
                    reversal_level=island.get_range_pct(island.high_price if direction == ReversalDirection.BEARISH else island.low_price),
                )
                
                # Set support/resistance
                if direction == ReversalDirection.BULLISH:
                    pattern.support_level = island.low_price
                else:
                    pattern.resistance_level = island.high_price
                
                patterns.append(pattern)
        
        return patterns
    
    def _calculate_trend_strength(
        self, df: pd.DataFrame, expected_direction: ReversalDirection
    ) -> float:
        """
        Calculate strength of preceding trend.
        
        Higher values = stronger trend preceding reversal.
        """
        if len(df) < 2:
            return 0.0
        
        # Calculate trend using high/low extremes
        if expected_direction == ReversalDirection.BULLISH:
            # For bullish reversal, trend should be downward
            high = df['high'].max()
            low = df['low'].min()
            trend = (high - low) / low  # Downtrend strength
        else:
            # For bearish reversal, trend should be upward
            high = df['high'].max()
            low = df['low'].min()
            trend = (high - low) / low  # Uptrend strength
        
        # Normalize to 0-1 range
        strength = min(trend * 10, 1.0)  # Scale factor
        return strength
    
    def _check_volume_filter(
        self,
        df: pd.DataFrame,
        island_df: pd.DataFrame,
        first_gap: Gap,
        consolidation_end_idx: int,
    ) -> bool:
        """
        Check volume filter: Island volume should exceed preceding trend volume.
        """
        if not self.volume_filter_enabled or 'volume' not in df.columns:
            return True
        
        island_volume = island_df['volume'].sum()
        
        # Get volume in preceding trend (gap + trend before it)
        trend_start = max(0, consolidation_end_idx - self.trend_length - 1)
        trend_volume = df.iloc[trend_start:consolidation_end_idx - len(island_df)]['volume'].sum()
        
        if trend_volume == 0:
            return True
        
        return island_volume > trend_volume
    
    def _check_horizontality_filter(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """
        Check horizontality filter using R² statistic.
        
        Higher R² = flatter consolidation.
        """
        if not self.horizontality_filter_enabled:
            return True, 1.0
        
        if stats is None or len(df) < 2:
            return True, 1.0
        
        # Calculate R² for close prices
        prices = df['close'].values
        r_squared = IslandConsolidation(
            start_timestamp=df.index[0],
            end_timestamp=df.index[-1],
            bar_count=len(df),
            high_price=df['high'].max(),
            low_price=df['low'].min(),
            close_price=df['close'].iloc[-1],
            range_size=df['high'].max() - df['low'].min(),
            volume_sum=df['volume'].sum() if 'volume' in df else 0,
            volume_avg=df['volume'].mean() if 'volume' in df else 0,
        ).get_horizontality_r_squared(prices.tolist())
        
        # Lower R² = more horizontal (we want this)
        passes = (1.0 - r_squared) >= (1.0 - self.horizontality_threshold)
        return passes, r_squared
    
    def _check_volatility_filter(self, df: pd.DataFrame) -> bool:
        """
        Check volatility filter: Range should match expected volatility.
        """
        if not self.volatility_filter_enabled:
            return True
        
        # Calculate ATR as reference
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        
        atr = df['tr'].mean()
        island_range = df['high'].max() - df['low'].min()
        
        # Range should be reasonable relative to volatility
        return island_range <= (atr * self.volatility_multiplier * len(df))
    
    def _calculate_quality_score(
        self,
        trend_strength: float,
        r_squared: float,
        trend_pass: bool,
        volume_pass: bool,
        horizontal_pass: bool,
        volatility_pass: bool,
    ) -> float:
        """
        Calculate composite quality score (0-1).
        """
        # Base score from trend strength
        base_score = trend_strength * 0.4
        
        # Horizontality bonus (flatter = better)
        horizontal_score = (1.0 - r_squared) * 0.3 if horizontal_pass else 0
        
        # Filter bonuses
        filter_score = 0
        if trend_pass:
            filter_score += 0.1
        if volume_pass:
            filter_score += 0.1
        if volatility_pass:
            filter_score += 0.1
        
        total_score = base_score + horizontal_score + filter_score
        return min(total_score, 1.0)


def example_usage():
    """Example usage of the Island Reversal Detector."""
    import numpy as np
    
    # Generate synthetic data with trend and consolidation
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=200, freq='1h')
    
    # Create trending price
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(len(dates)) * 0.1,
        'high': prices + np.abs(np.random.randn(len(dates)) * 0.3),
        'low': prices - np.abs(np.random.randn(len(dates)) * 0.3),
        'close': prices,
        'volume': np.random.randint(1000, 5000, len(dates)),
    }, index=dates)
    
    # Create detector
    detector = IslandReversalDetector(
        min_gap_size_pct=0.5,
        trend_length=20,
        min_island_bars=2,
        max_island_bars=50,
    )
    
    print("=== GAP DETECTION ===")
    gaps = detector.detect_gaps(df)
    print(f"Gaps found: {len(gaps)}")
    for gap in gaps[:3]:
        print(f"  {gap.gap_direction.upper()}: {gap.gap_size_pct:.2f}% at {gap.gap_end_timestamp}")
    
    print("\n=== ISLAND REVERSAL DETECTION ===")
    patterns = detector.detect_island_reversals(df, gaps)
    print(f"Island reversals found: {len(patterns)}")
    
    for pattern in patterns[:3]:
        print(f"\n{pattern.direction.value.upper()} Island Reversal:")
        print(f"  Quality: {pattern.quality.value}")
        print(f"  Quality Score: {pattern.quality_score:.2f}")
        print(f"  Trend Strength: {pattern.trend_strength:.1%}")
        print(f"  Pattern Bars: {pattern.total_bars}")
        print(f"  First Gap: {pattern.first_gap.gap_size_pct:.2f}%")
        print(f"  Island Range: {pattern.island_consolidation.range_size:.4f}")
        print(f"  Second Gap: {pattern.second_gap.gap_size_pct:.2f}%")
        print(f"  Filters - Trend: {pattern.trend_filter_pass}, Volume: {pattern.volume_filter_pass}, Horizontal: {pattern.horizontality_filter_pass}, Volatility: {pattern.volatility_filter_pass}")


if __name__ == "__main__":
    example_usage()
