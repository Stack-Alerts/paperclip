"""
LuxAlgo Three Bar Reversal Pattern - Core Implementation
======================================================

Three-bar reversal pattern detector with trend filtering using
Moving Average Cloud, Supertrend, and Donchian Channels.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class PatternType(Enum):
    """Three-bar reversal pattern type."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NONE = 'none'


class PatternMode(Enum):
    """Pattern detection mode."""
    NORMAL = 'normal'
    ENHANCED = 'enhanced'
    ALL = 'all'


class TrendDirection(Enum):
    """Market trend direction."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NEUTRAL = 'neutral'


class TrendFilter(Enum):
    """Trend filter type."""
    ALIGNED = 'aligned'
    OPPOSITE = 'opposite'
    NONE = 'none'


class TrendIndicator(Enum):
    """Trend indicator type."""
    MA_CLOUD = 'ma_cloud'
    SUPERTREND = 'supertrend'
    DONCHIAN = 'donchian'
    NONE = 'none'


@dataclass
class ThreeBar:
    """Three-bar reversal structure."""
    bar_1_idx: int
    bar_2_idx: int
    bar_3_idx: int
    
    bar_1_open: float
    bar_1_high: float
    bar_1_low: float
    bar_1_close: float
    
    bar_2_open: float
    bar_2_high: float
    bar_2_low: float
    bar_2_close: float
    
    bar_3_open: float
    bar_3_high: float
    bar_3_low: float
    bar_3_close: float
    
    pattern_type: PatternType
    is_enhanced: bool
    support_level: float
    resistance_level: float
    strength: float  # 0-100


class MovingAverageCloud:
    """Calculate MA cloud for trend filtering."""
    
    @staticmethod
    def calculate(prices: List[float], fast_period: int = 9,
                 slow_period: int = 21, ma_type: str = 'EMA') -> Tuple[List[float], List[float]]:
        """
        Calculate moving average cloud.
        
        Args:
            prices: List of prices
            fast_period: Fast MA period
            slow_period: Slow MA period
            ma_type: 'SMA', 'EMA', or 'HMA'
        
        Returns:
            Tuple of (fast_ma, slow_ma)
        """
        if ma_type == 'SMA':
            fast_ma = pd.Series(prices).rolling(fast_period).mean().tolist()
            slow_ma = pd.Series(prices).rolling(slow_period).mean().tolist()
        elif ma_type == 'EMA':
            fast_ma = pd.Series(prices).ewm(span=fast_period).mean().tolist()
            slow_ma = pd.Series(prices).ewm(span=slow_period).mean().tolist()
        else:  # HMA (Hull Moving Average)
            fast_ma = MovingAverageCloud._hma(prices, fast_period)
            slow_ma = MovingAverageCloud._hma(prices, slow_period)
        
        return fast_ma, slow_ma
    
    @staticmethod
    def _hma(prices: List[float], period: int) -> List[float]:
        """Calculate Hull Moving Average."""
        prices_series = pd.Series(prices)
        wma1 = prices_series.rolling(period // 2).mean()
        wma2 = prices_series.rolling(period).mean()
        hma_raw = 2 * wma1 - wma2
        hma = hma_raw.rolling(int(np.sqrt(period))).mean()
        return hma.tolist()
    
    @staticmethod
    def get_trend(price: float, fast_ma: float, slow_ma: float) -> TrendDirection:
        """Determine trend from cloud."""
        if fast_ma > slow_ma and price > fast_ma:
            return TrendDirection.BULLISH
        elif fast_ma < slow_ma and price < fast_ma:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL


class SupertrendIndicator:
    """Calculate Supertrend for trend filtering."""
    
    @staticmethod
    def calculate(df: pd.DataFrame, atr_length: int = 10,
                 multiplier: float = 3.0) -> Tuple[List[float], List[TrendDirection]]:
        """
        Calculate Supertrend.
        
        Args:
            df: OHLCV DataFrame
            atr_length: ATR length
            multiplier: ATR multiplier
        
        Returns:
            Tuple of (supertrend_values, trend_direction)
        """
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(atr_length).mean()
        
        # Calculate basic bands
        hl_avg = (df['high'] + df['low']) / 2
        matr = multiplier * atr
        
        upperband = hl_avg + matr
        lowerband = hl_avg - matr
        
        # Calculate final bands
        final_upperband = upperband.copy()
        final_lowerband = lowerband.copy()
        
        for i in range(1, len(df)):
            if upperband.iloc[i] < final_upperband.iloc[i-1] or df['close'].iloc[i-1] > final_upperband.iloc[i-1]:
                final_upperband.iloc[i] = upperband.iloc[i]
            else:
                final_upperband.iloc[i] = final_upperband.iloc[i-1]
            
            if lowerband.iloc[i] > final_lowerband.iloc[i-1] or df['close'].iloc[i-1] < final_lowerband.iloc[i-1]:
                final_lowerband.iloc[i] = lowerband.iloc[i]
            else:
                final_lowerband.iloc[i] = final_lowerband.iloc[i-1]
        
        # Determine trend
        trends = []
        supertrend = []
        
        for i in range(len(df)):
            if pd.isna(final_lowerband.iloc[i]) or pd.isna(final_upperband.iloc[i]):
                trends.append(TrendDirection.NEUTRAL)
                supertrend.append(df['close'].iloc[i])
            elif df['close'].iloc[i] <= final_upperband.iloc[i]:
                trends.append(TrendDirection.BEARISH)
                supertrend.append(final_upperband.iloc[i])
            else:
                trends.append(TrendDirection.BULLISH)
                supertrend.append(final_lowerband.iloc[i])
        
        return supertrend, trends


class DonchianChannels:
    """Calculate Donchian Channels for trend filtering."""
    
    @staticmethod
    def calculate(df: pd.DataFrame, length: int = 20) -> Tuple[List[float], List[float], List[TrendDirection]]:
        """
        Calculate Donchian Channels.
        
        Args:
            df: OHLCV DataFrame
            length: Channel length
        
        Returns:
            Tuple of (upper, lower, trend)
        """
        upper = df['high'].rolling(length).max().tolist()
        lower = df['low'].rolling(length).min().tolist()
        
        trends = []
        for i in range(len(df)):
            if pd.isna(upper[i]) or pd.isna(lower[i]):
                trends.append(TrendDirection.NEUTRAL)
            elif df['close'].iloc[i] > upper[i]:
                trends.append(TrendDirection.BULLISH)
            elif df['close'].iloc[i] < lower[i]:
                trends.append(TrendDirection.BEARISH)
            else:
                trends.append(TrendDirection.NEUTRAL)
        
        return upper, lower, trends


class ThreeBarReversalDetector:
    """Detect three-bar reversal patterns."""
    
    @staticmethod
    def detect_bullish(bar_1: Dict, bar_2: Dict, bar_3: Dict,
                      mode: PatternMode = PatternMode.ENHANCED) -> Optional[ThreeBar]:
        """
        Detect bullish reversal (uptrend).
        
        Bullish Pattern:
        - Bar 1 & 2: Downtrend (lower lows)
        - Bar 3: Makes new low THEN closes above Bar 2 close
        - Enhanced: Bar 3 low < Bar 1 low
        
        Args:
            bar_1: First bar data
            bar_2: Second bar data
            bar_3: Third bar data
            mode: Pattern detection mode
        
        Returns:
            ThreeBar pattern if detected
        """
        # Check downtrend (Bar 1 and 2)
        if bar_2['close'] >= bar_1['close']:
            return None
        
        # Bar 3 must close above Bar 2 close
        if bar_3['close'] <= bar_2['close']:
            return None
        
        # Check if Bar 3 makes new low
        if bar_3['low'] >= bar_2['low']:
            return None
        
        is_enhanced = bar_3['low'] < bar_1['low']
        
        if mode == PatternMode.NORMAL:
            is_valid = True
        elif mode == PatternMode.ENHANCED:
            is_valid = is_enhanced
        else:  # ALL
            is_valid = True
        
        if not is_valid:
            return None
        
        # Support at Bar 3 low, Resistance at Bar 1 high
        support = bar_3['low']
        resistance = bar_1['high']
        
        # Calculate strength (0-100)
        strength = ThreeBarReversalDetector._calculate_strength(
            bar_1, bar_2, bar_3, PatternType.BULLISH, is_enhanced
        )
        
        return ThreeBar(
            bar_1_idx=bar_1['index'],
            bar_2_idx=bar_2['index'],
            bar_3_idx=bar_3['index'],
            bar_1_open=bar_1['open'],
            bar_1_high=bar_1['high'],
            bar_1_low=bar_1['low'],
            bar_1_close=bar_1['close'],
            bar_2_open=bar_2['open'],
            bar_2_high=bar_2['high'],
            bar_2_low=bar_2['low'],
            bar_2_close=bar_2['close'],
            bar_3_open=bar_3['open'],
            bar_3_high=bar_3['high'],
            bar_3_low=bar_3['low'],
            bar_3_close=bar_3['close'],
            pattern_type=PatternType.BULLISH,
            is_enhanced=is_enhanced,
            support_level=support,
            resistance_level=resistance,
            strength=strength,
        )
    
    @staticmethod
    def detect_bearish(bar_1: Dict, bar_2: Dict, bar_3: Dict,
                      mode: PatternMode = PatternMode.ENHANCED) -> Optional[ThreeBar]:
        """
        Detect bearish reversal (downtrend).
        
        Bearish Pattern:
        - Bar 1 & 2: Uptrend (higher highs)
        - Bar 3: Makes new high THEN closes below Bar 2 close
        - Enhanced: Bar 3 high > Bar 1 high
        
        Args:
            bar_1: First bar data
            bar_2: Second bar data
            bar_3: Third bar data
            mode: Pattern detection mode
        
        Returns:
            ThreeBar pattern if detected
        """
        # Check uptrend (Bar 1 and 2)
        if bar_2['close'] <= bar_1['close']:
            return None
        
        # Bar 3 must close below Bar 2 close
        if bar_3['close'] >= bar_2['close']:
            return None
        
        # Check if Bar 3 makes new high
        if bar_3['high'] <= bar_2['high']:
            return None
        
        is_enhanced = bar_3['high'] > bar_1['high']
        
        if mode == PatternMode.NORMAL:
            is_valid = True
        elif mode == PatternMode.ENHANCED:
            is_valid = is_enhanced
        else:  # ALL
            is_valid = True
        
        if not is_valid:
            return None
        
        # Resistance at Bar 3 high, Support at Bar 1 low
        resistance = bar_3['high']
        support = bar_1['low']
        
        # Calculate strength
        strength = ThreeBarReversalDetector._calculate_strength(
            bar_1, bar_2, bar_3, PatternType.BEARISH, is_enhanced
        )
        
        return ThreeBar(
            bar_1_idx=bar_1['index'],
            bar_2_idx=bar_2['index'],
            bar_3_idx=bar_3['index'],
            bar_1_open=bar_1['open'],
            bar_1_high=bar_1['high'],
            bar_1_low=bar_1['low'],
            bar_1_close=bar_1['close'],
            bar_2_open=bar_2['open'],
            bar_2_high=bar_2['high'],
            bar_2_low=bar_2['low'],
            bar_2_close=bar_2['close'],
            bar_3_open=bar_3['open'],
            bar_3_high=bar_3['high'],
            bar_3_low=bar_3['low'],
            bar_3_close=bar_3['close'],
            pattern_type=PatternType.BEARISH,
            is_enhanced=is_enhanced,
            support_level=support,
            resistance_level=resistance,
            strength=strength,
        )
    
    @staticmethod
    def _calculate_strength(bar_1: Dict, bar_2: Dict, bar_3: Dict,
                           pattern_type: PatternType, is_enhanced: bool) -> float:
        """Calculate pattern strength 0-100."""
        base_strength = 50.0
        
        if pattern_type == PatternType.BULLISH:
            # How far below Bar 2 low did Bar 3 go?
            penetration = (bar_2['low'] - bar_3['low']) / (bar_1['low'] or 1)
            penetration_score = min(50, penetration * 100)
            
            # How much did Bar 3 recover?
            recovery = (bar_3['close'] - bar_3['low']) / bar_3['low']
            recovery_score = min(50, recovery * 100)
        
        else:  # BEARISH
            penetration = (bar_3['high'] - bar_2['high']) / (bar_1['high'] or 1)
            penetration_score = min(50, penetration * 100)
            
            recovery = (bar_3['high'] - bar_3['close']) / bar_3['high']
            recovery_score = min(50, recovery * 100)
        
        strength = (penetration_score + recovery_score) / 2
        
        if is_enhanced:
            strength = min(100, strength * 1.2)  # Boost enhanced patterns
        
        return strength


class ThreeBarReversal:
    """Complete three-bar reversal pattern detection system."""
    
    def __init__(self, pattern_mode: PatternMode = PatternMode.ENHANCED,
                 trend_indicator: TrendIndicator = TrendIndicator.MA_CLOUD,
                 trend_filter: TrendFilter = TrendFilter.ALIGNED,
                 show_levels: bool = True,
                 ma_type: str = 'EMA',
                 ma_fast: int = 9,
                 ma_slow: int = 21,
                 atr_length: int = 10,
                 atr_mult: float = 3.0,
                 donchian_length: int = 20):
        """
        Initialize three-bar reversal detector.
        
        Args:
            pattern_mode: Normal, Enhanced, or All
            trend_indicator: MA Cloud, Supertrend, Donchian, or None
            trend_filter: Aligned, Opposite, or None
            show_levels: Show support/resistance levels
            ma_type: SMA, EMA, or HMA
            ma_fast: Fast MA period
            ma_slow: Slow MA period
            atr_length: ATR length for Supertrend
            atr_mult: ATR multiplier for Supertrend
            donchian_length: Donchian channel length
        """
        self.pattern_mode = pattern_mode
        self.trend_indicator = trend_indicator
        self.trend_filter = trend_filter
        self.show_levels = show_levels
        self.ma_type = ma_type
        self.ma_fast = ma_fast
        self.ma_slow = ma_slow
        self.atr_length = atr_length
        self.atr_mult = atr_mult
        self.donchian_length = donchian_length
        self.detector = ThreeBarReversalDetector()
    
    def analyze(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Detect three-bar reversal patterns in DataFrame.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            Tuple of (DataFrame with analysis, results dict)
        """
        patterns = []
        
        # Calculate trend indicators if needed
        trends = self._calculate_trends(df)
        
        # Scan for 3-bar patterns
        for i in range(2, len(df)):
            bar_1 = self._row_to_dict(df, i - 2, i - 2)
            bar_2 = self._row_to_dict(df, i - 1, i - 1)
            bar_3 = self._row_to_dict(df, i, i)
            
            # Detect bullish
            bullish_pattern = self.detector.detect_bullish(bar_1, bar_2, bar_3, self.pattern_mode)
            if bullish_pattern:
                if self._passes_trend_filter(bullish_pattern.pattern_type, trends[i]):
                    patterns.append(bullish_pattern)
            
            # Detect bearish
            bearish_pattern = self.detector.detect_bearish(bar_1, bar_2, bar_3, self.pattern_mode)
            if bearish_pattern:
                if self._passes_trend_filter(bearish_pattern.pattern_type, trends[i]):
                    patterns.append(bearish_pattern)
        
        # Create result DataFrame
        df_result = df.copy()
        df_result['pattern_type'] = ''
        df_result['pattern_strength'] = 0.0
        df_result['support_level'] = np.nan
        df_result['resistance_level'] = np.nan
        
        for pattern in patterns:
            idx = pattern.bar_3_idx
            if idx < len(df_result):
                df_result.iloc[idx, df_result.columns.get_loc('pattern_type')] = pattern.pattern_type.value
                df_result.iloc[idx, df_result.columns.get_loc('pattern_strength')] = pattern.strength
                if self.show_levels:
                    df_result.iloc[idx, df_result.columns.get_loc('support_level')] = pattern.support_level
                    df_result.iloc[idx, df_result.columns.get_loc('resistance_level')] = pattern.resistance_level
        
        return df_result, {
            'patterns': patterns,
            'bullish_patterns': [p for p in patterns if p.pattern_type == PatternType.BULLISH],
            'bearish_patterns': [p for p in patterns if p.pattern_type == PatternType.BEARISH],
            'total_patterns': len(patterns),
            'trends': trends,
        }
    
    def _calculate_trends(self, df: pd.DataFrame) -> List[TrendDirection]:
        """Calculate trend using selected indicator."""
        if self.trend_indicator == TrendIndicator.NONE:
            return [TrendDirection.NEUTRAL] * len(df)
        
        elif self.trend_indicator == TrendIndicator.MA_CLOUD:
            fast_ma, slow_ma = MovingAverageCloud.calculate(
                df['close'].tolist(), self.ma_fast, self.ma_slow, self.ma_type
            )
            trends = []
            for i in range(len(df)):
                if pd.isna(fast_ma[i]) or pd.isna(slow_ma[i]):
                    trends.append(TrendDirection.NEUTRAL)
                else:
                    trends.append(MovingAverageCloud.get_trend(
                        df['close'].iloc[i], fast_ma[i], slow_ma[i]
                    ))
            return trends
        
        elif self.trend_indicator == TrendIndicator.SUPERTREND:
            _, trends = SupertrendIndicator.calculate(df, self.atr_length, self.atr_mult)
            return trends
        
        else:  # DONCHIAN
            _, _, trends = DonchianChannels.calculate(df, self.donchian_length)
            return trends
    
    def _passes_trend_filter(self, pattern_type: PatternType, trend: TrendDirection) -> bool:
        """Check if pattern passes trend filter."""
        if self.trend_filter == TrendFilter.NONE:
            return True
        
        elif self.trend_filter == TrendFilter.ALIGNED:
            if pattern_type == PatternType.BULLISH:
                return trend == TrendDirection.BULLISH
            else:
                return trend == TrendDirection.BEARISH
        
        else:  # OPPOSITE
            if pattern_type == PatternType.BULLISH:
                return trend == TrendDirection.BEARISH
            else:
                return trend == TrendDirection.BULLISH
    
    def _row_to_dict(self, df: pd.DataFrame, index: int, timestamp_idx: int) -> Dict:
        """Convert DataFrame row to dictionary."""
        row = df.iloc[index]
        return {
            'index': index,
            'timestamp': df.index[timestamp_idx],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
        }


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=100, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(100) * 0.2,
        'high': prices + np.abs(np.random.randn(100) * 0.5),
        'low': prices - np.abs(np.random.randn(100) * 0.5),
        'close': prices,
    }, index=dates)
    
    tbr = ThreeBarReversal(
        pattern_mode=PatternMode.ENHANCED,
        trend_indicator=TrendIndicator.MA_CLOUD,
        trend_filter=TrendFilter.ALIGNED
    )
    df_result, results = tbr.analyze(df)
    
    print("=" * 70)
    print("THREE BAR REVERSAL - ANALYSIS")
    print("=" * 70)
    
    print(f"\n✓ Total Patterns: {results['total_patterns']}")
    print(f"  Bullish: {len(results['bullish_patterns'])}")
    print(f"  Bearish: {len(results['bearish_patterns'])}")
    
    for pattern in results['patterns'][-3:]:
        print(f"\n✓ Bar 3: {df.index[pattern.bar_3_idx].date()}")
        print(f"  Type: {pattern.pattern_type.value.upper()}")
        print(f"  Enhanced: {pattern.is_enhanced}")
        print(f"  Strength: {pattern.strength:.0f}%")
        print(f"  Support: {pattern.support_level:.2f}")
        print(f"  Resistance: {pattern.resistance_level:.2f}")
