"""
LuxAlgo Candle 2 Closure - Core Implementation
==============================================

Candle 2 Closure price action reversal indicator based on TTrades framework.
Detects four-candle failed breakout patterns with equilibrium zones.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class PatternType(Enum):
    """Pattern classification."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NONE = 'none'


@dataclass
class Candle:
    """Single OHLC candle with index."""
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    index: int
    
    @property
    def range(self) -> float:
        """Candle range (high - low)."""
        return self.high - self.low
    
    @property
    def body(self) -> float:
        """Candle body size."""
        return abs(self.close - self.open)
    
    @property
    def wick_up(self) -> float:
        """Upper wick size."""
        return self.high - max(self.open, self.close)
    
    @property
    def wick_down(self) -> float:
        """Lower wick size."""
        return min(self.open, self.close) - self.low


@dataclass
class EquilibriumZone:
    """Equilibrium zone between two candles."""
    high: float
    low: float
    source: str  # 'full_range' or 'wick'
    
    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2


@dataclass
class Candle2ClosurePattern:
    """Complete Candle 2 Closure pattern."""
    candle_1: Candle  # Context candle
    candle_2: Candle  # Reversal (closes inside C1)
    candle_3: Candle  # Expansion (closes outside C2)
    candle_4: Optional[Candle]  # Continuation
    
    pattern_type: PatternType
    
    candle_2_zone: EquilibriumZone
    candle_3_zone: EquilibriumZone
    
    candle_2_confirmed: bool
    candle_3_confirmed: bool
    
    strength: float  # 0-100 confidence score


class Candle2ClosureDetector:
    """Detect Candle 2 Closure patterns."""
    
    def __init__(self, wick_threshold_pct: float = 75.0):
        """
        Initialize detector.
        
        Args:
            wick_threshold_pct: Wick must be this % of range to use wick for zone
        """
        self.wick_threshold_pct = wick_threshold_pct
    
    def detect_candle_2_bearish(self, c1: Candle, c2: Candle) -> Optional[Dict]:
        """
        Detect bearish Candle 2 condition.
        
        Conditions:
        - C1: Up candle (close > open)
        - C2: Trades above C1 high but closes below C1 close
        
        Args:
            c1: First candle (context)
            c2: Second candle (reversal)
        
        Returns:
            Dict with reversal data if detected
        """
        # C1 must be up
        if c1.close <= c1.open:
            return None
        
        # C2 must trade above C1 but close inside C1
        if c2.high <= c1.high:
            return None
        
        if c2.close >= c1.close:  # Didn't close inside C1
            return None
        
        # Determine equilibrium zone
        zone = self._calculate_equilibrium_zone(c1, c2, 'bearish')
        
        return {
            'candle_1': c1,
            'candle_2': c2,
            'pattern_type': PatternType.BEARISH,
            'zone': zone,
            'strength': self._calculate_strength(c1, c2, 'bearish'),
        }
    
    def detect_candle_2_bullish(self, c1: Candle, c2: Candle) -> Optional[Dict]:
        """
        Detect bullish Candle 2 condition.
        
        Conditions:
        - C1: Down candle (close < open)
        - C2: Trades below C1 low but closes above C1 close
        
        Args:
            c1: First candle (context)
            c2: Second candle (reversal)
        
        Returns:
            Dict with reversal data if detected
        """
        # C1 must be down
        if c1.close >= c1.open:
            return None
        
        # C2 must trade below C1 but close inside C1
        if c2.low >= c1.low:
            return None
        
        if c2.close <= c1.close:  # Didn't close inside C1
            return None
        
        # Determine equilibrium zone
        zone = self._calculate_equilibrium_zone(c1, c2, 'bullish')
        
        return {
            'candle_1': c1,
            'candle_2': c2,
            'pattern_type': PatternType.BULLISH,
            'zone': zone,
            'strength': self._calculate_strength(c1, c2, 'bullish'),
        }
    
    def detect_candle_3_bullish(self, c2: Candle, c3: Candle) -> bool:
        """
        Detect bullish Candle 3 expansion.
        
        Condition: Close outside C2 range to upside
        
        Args:
            c2: Second candle
            c3: Third candle
        
        Returns:
            True if C3 closes above C2 high
        """
        return c3.close > c2.high
    
    def detect_candle_3_bearish(self, c2: Candle, c3: Candle) -> bool:
        """
        Detect bearish Candle 3 expansion.
        
        Condition: Close outside C2 range to downside
        
        Args:
            c2: Second candle
            c3: Third candle
        
        Returns:
            True if C3 closes below C2 low
        """
        return c3.close < c2.low
    
    def _calculate_equilibrium_zone(self, c1: Candle, c2: Candle,
                                   pattern_type: str) -> EquilibriumZone:
        """
        Calculate equilibrium zone between C2 and C1.
        
        Uses wick if wick > threshold % of range.
        """
        if pattern_type == 'bearish':
            # Zone is between C2 close and C1 high
            wick_pct = (c2.wick_down / c2.range * 100) if c2.range > 0 else 0
            
            if wick_pct >= self.wick_threshold_pct:
                # Use wick
                high = c1.high
                low = c2.low
                source = 'wick'
            else:
                # Use close
                high = c1.high
                low = c2.close
                source = 'full_range'
        
        else:  # bullish
            # Zone is between C2 close and C1 low
            wick_pct = (c2.wick_up / c2.range * 100) if c2.range > 0 else 0
            
            if wick_pct >= self.wick_threshold_pct:
                # Use wick
                high = c2.high
                low = c1.low
                source = 'wick'
            else:
                # Use close
                high = c2.close
                low = c1.low
                source = 'full_range'
        
        return EquilibriumZone(high=max(high, low), low=min(high, low), 
                              source=source)
    
    def _calculate_strength(self, c1: Candle, c2: Candle, 
                          pattern_type: str) -> float:
        """
        Calculate pattern strength 0-100.
        
        Factors:
        - How far C2 penetrated C1 range
        - C2 body vs range
        - Wick quality
        """
        if pattern_type == 'bearish':
            # How much did C2 penetrate above C1?
            penetration = max(0, c2.high - c1.high)
            max_penetration = c1.range
            
            if max_penetration > 0:
                pct_penetration = (penetration / max_penetration) * 100
            else:
                pct_penetration = 50
            
            # Close position (how much inside C1)
            close_pos = (c1.close - c2.close) / c1.range * 100
            
            strength = min(100, (pct_penetration + close_pos) / 2)
        
        else:  # bullish
            penetration = max(0, c1.low - c2.low)
            max_penetration = c1.range
            
            if max_penetration > 0:
                pct_penetration = (penetration / max_penetration) * 100
            else:
                pct_penetration = 50
            
            close_pos = (c2.close - c1.close) / c1.range * 100
            strength = min(100, (pct_penetration + close_pos) / 2)
        
        return strength


class ReversalFilter:
    """Filter reversals by structural importance."""
    
    @staticmethod
    def filter_by_extremes(patterns: List[Candle2ClosurePattern],
                          df: pd.DataFrame,
                          lookback_bars: int = 20) -> List[Candle2ClosurePattern]:
        """
        Keep only reversals at highest/lowest over lookback period.
        
        Args:
            patterns: List of detected patterns
            df: OHLCV DataFrame
            lookback_bars: Lookback period
        
        Returns:
            Filtered list of high-quality patterns
        """
        filtered = []
        
        for pattern in patterns:
            c2_idx = pattern.candle_2.index
            
            # Look back from C2
            start_idx = max(0, c2_idx - lookback_bars)
            lookback_range = df.iloc[start_idx:c2_idx + 1]
            
            if pattern.pattern_type == PatternType.BEARISH:
                # C2 must have highest high in lookback
                max_high = lookback_range['high'].max()
                if pattern.candle_2.high >= max_high * 0.99:  # 99% of max
                    filtered.append(pattern)
            
            else:  # BULLISH
                # C2 must have lowest low in lookback
                min_low = lookback_range['low'].min()
                if pattern.candle_2.low <= min_low * 1.01:  # 101% of min
                    filtered.append(pattern)
        
        return filtered


class Candle2Closure:
    """Complete Candle 2 Closure pattern detection system."""
    
    def __init__(self, wick_threshold_pct: float = 75.0,
                 detect_candle_2: bool = True,
                 detect_candle_3: bool = True,
                 reversal_filter: bool = False,
                 reversal_lookback: int = 20):
        """
        Initialize Candle 2 Closure indicator.
        
        Args:
            wick_threshold_pct: Wick threshold for zones
            detect_candle_2: Enable C2 detection
            detect_candle_3: Enable C3 detection
            reversal_filter: Filter by extremes
            reversal_lookback: Lookback for filter
        """
        self.detector = Candle2ClosureDetector(wick_threshold_pct)
        self.detect_candle_2 = detect_candle_2
        self.detect_candle_3 = detect_candle_3
        self.reversal_filter = reversal_filter
        self.reversal_lookback = reversal_lookback
    
    def analyze(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Detect all Candle 2 Closure patterns in DataFrame.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            Tuple of (DataFrame with analysis, results dict)
        """
        patterns = []
        
        # Scan through bars looking for 4-candle patterns
        for i in range(3, len(df)):
            c1 = self._bar_to_candle(df, i - 3, i - 3)
            c2 = self._bar_to_candle(df, i - 2, i - 2)
            c3 = self._bar_to_candle(df, i - 1, i - 1)
            c4 = self._bar_to_candle(df, i, i)
            
            # Try bearish
            c2_bear = self.detector.detect_candle_2_bearish(c1, c2)
            if c2_bear and self.detect_candle_2:
                c3_confirm = False
                if self.detect_candle_3:
                    c3_confirm = self.detector.detect_candle_3_bearish(c2, c3)
                
                pattern = Candle2ClosurePattern(
                    candle_1=c1,
                    candle_2=c2,
                    candle_3=c3,
                    candle_4=c4,
                    pattern_type=PatternType.BEARISH,
                    candle_2_zone=c2_bear['zone'],
                    candle_3_zone=self.detector._calculate_equilibrium_zone(c2, c3, 'bearish'),
                    candle_2_confirmed=True,
                    candle_3_confirmed=c3_confirm,
                    strength=c2_bear['strength'],
                )
                patterns.append(pattern)
            
            # Try bullish
            c2_bull = self.detector.detect_candle_2_bullish(c1, c2)
            if c2_bull and self.detect_candle_2:
                c3_confirm = False
                if self.detect_candle_3:
                    c3_confirm = self.detector.detect_candle_3_bullish(c2, c3)
                
                pattern = Candle2ClosurePattern(
                    candle_1=c1,
                    candle_2=c2,
                    candle_3=c3,
                    candle_4=c4,
                    pattern_type=PatternType.BULLISH,
                    candle_2_zone=c2_bull['zone'],
                    candle_3_zone=self.detector._calculate_equilibrium_zone(c2, c3, 'bullish'),
                    candle_2_confirmed=True,
                    candle_3_confirmed=c3_confirm,
                    strength=c2_bull['strength'],
                )
                patterns.append(pattern)
        
        # Apply reversal filter if enabled
        if self.reversal_filter:
            patterns = ReversalFilter.filter_by_extremes(
                patterns, df, self.reversal_lookback
            )
        
        # Create output DataFrame
        df_result = df.copy()
        df_result['pattern_type'] = ''
        df_result['pattern_strength'] = 0.0
        df_result['zone_high'] = np.nan
        df_result['zone_low'] = np.nan
        
        for pattern in patterns:
            idx = pattern.candle_2.index
            if idx < len(df_result):
                df_result.loc[df_result.index[idx], 'pattern_type'] = pattern.pattern_type.value
                df_result.loc[df_result.index[idx], 'pattern_strength'] = pattern.strength
                df_result.loc[df_result.index[idx], 'zone_high'] = pattern.candle_2_zone.high
                df_result.loc[df_result.index[idx], 'zone_low'] = pattern.candle_2_zone.low
        
        return df_result, {
            'patterns': patterns,
            'bullish_patterns': [p for p in patterns if p.pattern_type == PatternType.BULLISH],
            'bearish_patterns': [p for p in patterns if p.pattern_type == PatternType.BEARISH],
            'total_patterns': len(patterns),
        }
    
    def _bar_to_candle(self, df: pd.DataFrame, index: int,
                       timestamp_idx: int) -> Candle:
        """Convert DataFrame row to Candle object."""
        row = df.iloc[index]
        return Candle(
            timestamp=df.index[timestamp_idx],
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            index=index,
        )


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=100, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(100) * 0.2,
        'high': prices + np.abs(np.random.randn(100) * 0.5),
        'low': prices - np.abs(np.random.randn(100) * 0.5),
        'close': prices,
    }, index=dates)
    
    c2c = Candle2Closure(reversal_filter=True)
    df_result, results = c2c.analyze(df)
    
    print("=" * 70)
    print("CANDLE 2 CLOSURE - ANALYSIS")
    print("=" * 70)
    
    print(f"\n✓ Total Patterns: {results['total_patterns']}")
    print(f"  Bullish: {len(results['bullish_patterns'])}")
    print(f"  Bearish: {len(results['bearish_patterns'])}")
    
    for pattern in results['patterns'][-3:]:
        print(f"\n✓ {pattern.candle_2.timestamp.date()}: {pattern.pattern_type.value.upper()}")
        print(f"  Strength: {pattern.strength:.0f}%")
        print(f"  C2 Zone: {pattern.candle_2_zone.low:.2f} - {pattern.candle_2_zone.high:.2f}")
        print(f"  C3 Confirmed: {pattern.candle_3_confirmed}")
