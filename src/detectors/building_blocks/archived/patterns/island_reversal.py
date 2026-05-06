"""
Island Reversal - Building Block
=================================

EVENT BLOCK - Detects island reversal patterns (powerful trend reversals).

An island reversal is a strong technical pattern indicating trend exhaustion:
1. Strong preceding trend
2. First gap (trend continuation)
3. Consolidation phase (the "island")
4. Second gap (opposite direction - reversal)

Signals:
- BULLISH_REVERSAL: Island reversal from downtrend (bounce expected)
- BEARISH_REVERSAL: Island reversal from uptrend (fall expected)
- NO_PATTERN: No island reversal detected

Based on LuxAlgo Island Reversal concept, adapted for BTC_Engine_v3 framework.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import pandas as pd
import numpy as np

import logging
logger = logging.getLogger(__name__)

@dataclass
class Gap:
    """Represents a price gap."""
    direction: str  # 'up' or 'down'
    size_pct: float
    timestamp: datetime
    price: float


class IslandReversal:
    """
    Island Reversal Detector
    
    Building Block Classification: EVENT BLOCK
    Mode: SELECTIVE (only fires on pattern detection)
    
    Detects island reversal patterns - powerful signals of trend exhaustion
    and reversal. Consists of two gaps in opposite directions with
    consolidation between them.
    
    Designed for 15-min bars.
    """
    
    def __init__(
        self,
        timeframe: str = '15min',
        min_gap_size_pct: float = 0.5,  # Minimum gap size (%)
        trend_length: int = 20,  # Bars for trend strength
        min_island_bars: int = 2,  # Min consolidation bars
        max_island_bars: int = 50,  # Max consolidation bars
        min_trend_strength: float = 0.4,  # Min trend power (0-1)
        **kwargs
    ):
        """
        Initialize Island Reversal detector.
        
        Args:
            timeframe: Timeframe (e.g., '15min')
            min_gap_size_pct: Minimum gap size as % of price
            trend_length: Lookback for trend calculation
            min_island_bars: Minimum bars in consolidation
            max_island_bars: Maximum bars in consolidation
            min_trend_strength: Minimum trend strength required
        """
        self.timeframe = timeframe
        self.min_gap_size_pct = min_gap_size_pct
        self.trend_length = trend_length
        self. min_island_bars = min_island_bars
        self.max_island_bars = max_island_bars
        self.min_trend_strength = min_trend_strength
        
        # State tracking
        self.last_pattern_time: Optional[datetime] = None
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for island reversal patterns.
        
        Compatible with building block interface.
        """
        # Validation
        required_cols = {'open', 'high', 'low', 'close', 'volume', 'timestamp'}
        if not required_cols.issubset(df.columns):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.trend_length + self.max_island_bars + 10:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.trend_length + self.max_island_bars + 10} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_time = df['timestamp'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Detect gaps
        gaps = self._detect_gaps(df.tail(self.max_island_bars + 20))
        
        if len(gaps) < 2:
            return self._generate_no_pattern_signal(current_time, current_price)
        
        # Check for island reversal pattern
        pattern = self._detect_island_pattern(df, gaps)
        
        if pattern:
            return self._generate_reversal_signal(current_time, current_price, pattern, df)
        
        return self._generate_no_pattern_signal(current_time, current_price)
    
    def _detect_gaps(self, df: pd.DataFrame) -> List[Gap]:
        """Detect price gaps (gap up or gap down)."""
        gaps = []
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i - 1]
            
            # Gap up
            if current['open'] > previous['high']:
                gap_size = current['open'] - previous['high']
                gap_pct = (gap_size / previous['high']) * 100
                
                if gap_pct >= self.min_gap_size_pct:
                    gaps.append(Gap(
                        direction='up',
                        size_pct=gap_pct,
                        timestamp=current['timestamp'],
                        price=current['open']
                    ))
            
            # Gap down
            elif current['open'] < previous['low']:
                gap_size = previous['low'] - current['open']
                gap_pct = (gap_size / previous['low']) * 100
                
                if gap_pct >= self.min_gap_size_pct:
                    gaps.append(Gap(
                        direction='down',
                        size_pct=gap_pct,
                        timestamp=current['timestamp'],
                        price=current['open']
                    ))
        
        return gaps
    
    def _detect_island_pattern(
        self, df: pd.DataFrame, gaps: List[Gap]
    ) -> Optional[Dict[str, Any]]:
        """Detect island reversal pattern from gaps."""
        # Look for pairs of opposite-direction gaps
        for i in range(len(gaps) - 1):
            first_gap = gaps[i]
            
            for j in range(i + 1, len(gaps)):
                second_gap = gaps[j]
                
                # Must be opposite directions
                if first_gap.direction == second_gap.direction:
                    continue
                
                # Get consolidation between gaps
                first_idx = df[df['timestamp'] == first_gap.timestamp].index[0]
                second_idx = df[df['timestamp'] == second_gap.timestamp].index[0]
                
                consolidation_bars = second_idx - first_idx - 1
                
                # Check bar count
                if not (self.min_island_bars <= consolidation_bars <= self.max_island_bars):
                    continue
                
                # Get consolidation data
                island_df = df.iloc[first_idx + 1:second_idx]
                
                if len(island_df) == 0:
                    continue
                
                island_high = island_df['high'].max()
                island_low = island_df['low'].min()
                island_range = island_high - island_low
                
                # Determine direction
                if first_gap.direction == 'down':
                    direction = 'BULLISH_REVERSAL'
                else:
                    direction = 'BEARISH_REVERSAL'
                
                # Calculate trend strength before first gap
                trend_start = max(0, first_idx - self.trend_length)
                trend_df = df.iloc[trend_start:first_idx]
                
                if len(trend_df) < 5:
                    continue
                
                trend_strength = self._calculate_trend_strength(trend_df, direction)
                
                if trend_strength < self.min_trend_strength:
                    continue
                
                # Calculate quality score
                quality_score = self._calculate_quality(
                    first_gap, second_gap, island_range, trend_strength, island_df
                )
                
                if quality_score < 0.5:
                    continue
                
                # Pattern found!
                return {
                    'direction': direction,
                    'first_gap': first_gap,
                    'second_gap': second_gap,
                    'island_high': island_high,
                    'island_low': island_low,
                    'island_range': island_range,
                    'island_bars': consolidation_bars,
                    'trend_strength': trend_strength,
                    'quality_score': quality_score,
                    'pattern_start': first_gap.timestamp,
                    'pattern_end': second_gap.timestamp,
                }
        
        return None
    
    def _calculate_trend_strength(self, df: pd.DataFrame, reversal_direction: str) -> float:
        """Calculate strength of preceding trend."""
        if len(df) < 2:
            return 0.0
        
        high = df['high'].max()
        low = df['low'].min()
        trend_range = high - low
        
        if trend_range == 0:
            return 0.0
        
        # For bullish reversal, need strong downtrend before
        # For bearish reversal, need strong uptrend before
        close_change = df['close'].iloc[-1] - df['close'].iloc[0]
        
        if reversal_direction == 'BULLISH_REVERSAL':
            # Want negative trend (downtrend)
            strength = abs(min(close_change, 0)) / trend_range
        else:
            # Want positive trend (uptrend)
            strength = abs(max(close_change, 0)) / trend_range
        
        return min(strength * 2, 1.0)  # Normalize
    
    def _calculate_quality(
        self,
        first_gap: Gap,
        second_gap: Gap,
        island_range: float,
        trend_strength: float,
        island_df: pd.DataFrame
    ) -> float:
        """Calculate pattern quality score (0-1)."""
        # Base score from trend strength
        score = trend_strength * 0.4
        
        # Gap size score (larger gaps = better)
        avg_gap = (first_gap.size_pct + second_gap.size_pct) / 2
        gap_score = min(avg_gap / 2.0, 1.0) * 0.3
        score += gap_score
        
        # Consolidation score (tighter range = better)
        if len(island_df) > 0:
            avg_price = island_df['close'].mean()
            range_pct = (island_range / avg_price) * 100
            consolidation_score = max(0, 1.0 - (range_pct / 5.0)) * 0.3
            score += consolidation_score
        
        return min(score, 1.0)
    
    def _generate_reversal_signal(
        self,
        timestamp: datetime,
        price: float,
        pattern: Dict[str, Any],
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate island reversal signal."""
        direction = pattern['direction']
        quality_score = pattern['quality_score']
        
        # Confidence based on quality
        if quality_score >= 0.7:
            confidence = 80
            quality = 'EXCELLENT'
        elif quality_score >= 0.6:
            confidence = 70
            quality = 'GOOD'
        else:
            confidence = 60
            quality = 'FAIR'
        
        # Calculate targets using island as reference
        if direction == 'BULLISH_REVERSAL':
            target_1 = pattern['island_high'] + (pattern['island_range'] * 1.0)
            target_2 = pattern['island_high'] + (pattern['island_range'] * 2.0)
            stop_level = pattern['island_low']
        else:
            target_1 = pattern['island_low'] - (pattern['island_range'] * 1.0)
            target_2 = pattern['island_low'] - (pattern['island_range'] * 2.0)
            stop_level = pattern['island_high']
        
        return {
            'signal': direction,
            'confidence': confidence,
            'metadata': {
                'quality': quality,
                'quality_score': round(quality_score * 100, 1),
                'trend_strength': round(pattern['trend_strength'] * 100, 1),
                'first_gap_size': round(pattern['first_gap'].size_pct, 2),
                'second_gap_size': round(pattern['second_gap'].size_pct, 2),
                'island_bars': pattern['island_bars'],
                'island_high': round(pattern['island_high'], 2),
                'island_low': round(pattern['island_low'], 2),
                'island_range': round(pattern['island_range'], 2),
                'target_1': round(target_1, 2),
                'target_2': round(target_2, 2),
                'stop_level': round(stop_level, 2),
                'pattern_start': pattern['pattern_start'].isoformat(),
                'pattern_end': pattern['pattern_end'].isoformat(),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'{direction.replace("_", " ")} detected',
                f'Quality: {quality}',
                f'Trend strength: {pattern["trend_strength"]*100:.0f}%',
                f'Island: {pattern["island_bars"]} bars',
                f'Gaps: {pattern["first_gap"].size_pct:.1f}% + {pattern["second_gap"].size_pct:.1f}%',
            ]
        }
    
    def _generate_no_pattern_signal(
        self, timestamp: datetime, price: float
    ) -> Dict[str, Any]:
        """Generate no pattern signal."""
        return {
            'signal': 'NO_PATTERN',
            'confidence': 0,
            'metadata': {
                'reason': 'No island reversal pattern detected',
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': []
        }


if __name__ == "__main__":
    logger.info("Island Reversal - Building Block")
    logger.info("EVENT BLOCK - Detects island reversal patterns")
    logger.info("Based on LuxAlgo methodology")
