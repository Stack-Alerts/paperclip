"""
LuxAlgo Buyside & Sellside Liquidity Implementation
====================================================

A robust, production-ready implementation of LuxAlgo's Buyside & Sellside
Liquidity indicator based on ICT (Inner Circle Trader) concepts. Identifies
institutional liquidity levels where smart money accumulates stop-loss orders.

Features:
    - Buyside liquidity detection (short stop-losses)
    - Sellside liquidity detection (long stop-losses)
    - Liquidity zone identification
    - Liquidity void detection (gap patterns)
    - Historical and recent mode analysis
    - Liquidity breach notifications
    - Smart money order flow analysis

Author: Advanced Trading Systems
Date: 2026
Python: 3.8+

Dependencies:
    - pandas>=1.3.0
    - numpy>=1.21.0

ICT Concepts:
    Based on Michael J. Huddleston's Inner Circle Trader methodology.
    Focuses on institutional order flow and liquidity accumulation.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime, timedelta
import warnings


class LiquidityType(Enum):
    """Types of liquidity levels."""
    BUYSIDE = "buyside"  # Short stop-losses (buy pressure)
    SELLSIDE = "sellside"  # Long stop-losses (sell pressure)
    VOID = "void"  # Liquidity void (gap)


class LiquidityMode(Enum):
    """Display modes for liquidity analysis."""
    PRESENT = "present"  # Last N bars only
    HISTORICAL = "historical"  # All available data


class VoidType(Enum):
    """Types of liquidity voids."""
    BULLISH = "bullish"  # Upward void
    BEARISH = "bearish"  # Downward void


@dataclass
class LiquidityLevel:
    """Data structure for a liquidity level/zone."""
    price: float
    liquidity_type: LiquidityType
    strength: float  # 0.0 to 1.0 (how strong/significant)
    first_touch: datetime
    last_touch: datetime
    touch_count: int
    zone_high: float  # Top of liquidity zone
    zone_low: float  # Bottom of liquidity zone
    breached: bool
    breach_timestamp: Optional[datetime] = None
    
    def get_zone_width(self) -> float:
        """Get the width of the liquidity zone."""
        return self.zone_high - self.zone_low
    
    def is_level_touched(self, price: float, margin: float = 0.001) -> bool:
        """Check if price touches this liquidity level."""
        return abs(price - self.price) <= margin
    
    def is_zone_breached(self, price: float) -> bool:
        """Check if price breaks through the zone."""
        return price < self.zone_low or price > self.zone_high


@dataclass
class LiquidityVoid:
    """Data structure for a liquidity void (gap)."""
    void_type: VoidType
    top_price: float
    bottom_price: float
    void_size: float
    candle_count: int  # Consecutive large candles forming void
    start_timestamp: datetime
    end_timestamp: datetime
    avg_body_size: float
    avg_wick_ratio: float  # Wick size / Body size (lower = more aggressive)
    
    def get_void_size_pct(self, reference_price: float) -> float:
        """Get void size as percentage of reference price."""
        return (self.void_size / reference_price) * 100


@dataclass
class BuysideLiquidityZone:
    """Buyside liquidity zone (short stop-loss accumulation)."""
    zone_high: float
    zone_low: float
    liquidity_levels: List[LiquidityLevel]
    total_strength: float
    formation_timestamp: datetime
    last_update: datetime
    
    def get_zone_center(self) -> float:
        """Get center of zone."""
        return (self.zone_high + self.zone_low) / 2
    
    def get_zone_width(self) -> float:
        """Get width of zone."""
        return self.zone_high - self.zone_low


@dataclass
class SellsideLiquidityZone:
    """Sellside liquidity zone (long stop-loss accumulation)."""
    zone_high: float
    zone_low: float
    liquidity_levels: List[LiquidityLevel]
    total_strength: float
    formation_timestamp: datetime
    last_update: datetime
    
    def get_zone_center(self) -> float:
        """Get center of zone."""
        return (self.zone_high + self.zone_low) / 2
    
    def get_zone_width(self) -> float:
        """Get width of zone."""
        return self.zone_high - self.zone_low


class LiquidityDetector:
    """
    Main class for detecting institutional liquidity levels.
    
    Based on ICT (Inner Circle Trader) concepts:
    - Buyside: Where short sellers have stop-losses (buy pressure)
    - Sellside: Where long traders have stop-losses (sell pressure)
    - Voids: Rapid price movements with no support
    """
    
    def __init__(
        self,
        detection_length: int = 20,
        margin: float = 0.002,  # 0.2% default
        mode: LiquidityMode = LiquidityMode.PRESENT,
        present_bars: int = 500,
        void_sensitivity: float = 2.0,
        min_touch_count: int = 2,
        zone_merge_tolerance: float = 0.005,  # 0.5%
    ):
        """
        Initialize the Liquidity Detector.
        
        Args:
            detection_length: Lookback period for liquidity detection
            margin: Price margin for zone detection (as % of price)
            mode: PRESENT (last N bars) or HISTORICAL (all data)
            present_bars: Number of recent bars to analyze in PRESENT mode
            void_sensitivity: Sensitivity for void detection (2.0 = normal)
            min_touch_count: Minimum touches to confirm liquidity level
            zone_merge_tolerance: Tolerance for merging nearby levels into zones
        """
        self.detection_length = detection_length
        self.margin = margin
        self.mode = mode
        self.present_bars = present_bars
        self.void_sensitivity = void_sensitivity
        self.min_touch_count = min_touch_count
        self.zone_merge_tolerance = zone_merge_tolerance
        
        self._validate_parameters()
    
    def _validate_parameters(self) -> None:
        """Validate initialization parameters."""
        if self.detection_length < 5:
            raise ValueError(f"detection_length must be >= 5, got {self.detection_length}")
        if not 0 < self.margin < 0.1:
            raise ValueError(f"margin must be between 0 and 0.1, got {self.margin}")
        if self.present_bars < 50:
            raise ValueError(f"present_bars must be >= 50, got {self.present_bars}")
        if self.void_sensitivity <= 0:
            raise ValueError(f"void_sensitivity must be > 0, got {self.void_sensitivity}")
    
    def detect_liquidity_levels(
        self, df: pd.DataFrame
    ) -> Tuple[List[LiquidityLevel], List[LiquidityLevel]]:
        """
        Detect buyside and sellside liquidity levels.
        
        Args:
            df: OHLCV DataFrame with DatetimeIndex
        
        Returns:
            Tuple of (buyside_levels, sellside_levels)
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain {required_cols}")
        
        # Get analysis range
        if self.mode == LiquidityMode.PRESENT:
            analysis_df = df.tail(self.present_bars).copy()
        else:
            analysis_df = df.copy()
        
        buyside_levels = []
        sellside_levels = []
        
        # Find local extremes (swing highs and lows)
        for i in range(self.detection_length, len(analysis_df) - self.detection_length):
            window = analysis_df.iloc[i - self.detection_length:i + self.detection_length + 1]
            current_bar = analysis_df.iloc[i]
            
            # Detect swing highs (potential sellside liquidity)
            if current_bar['high'] == window['high'].max():
                strength = self._calculate_level_strength(
                    analysis_df, i, current_bar['high'], is_high=True
                )
                
                if strength > 0.3:  # Minimum strength threshold
                    level = self._create_liquidity_level(
                        analysis_df, i, current_bar['high'],
                        LiquidityType.SELLSIDE, strength
                    )
                    if level:
                        sellside_levels.append(level)
            
            # Detect swing lows (potential buyside liquidity)
            if current_bar['low'] == window['low'].min():
                strength = self._calculate_level_strength(
                    analysis_df, i, current_bar['low'], is_high=False
                )
                
                if strength > 0.3:
                    level = self._create_liquidity_level(
                        analysis_df, i, current_bar['low'],
                        LiquidityType.BUYSIDE, strength
                    )
                    if level:
                        buyside_levels.append(level)
        
        return buyside_levels, sellside_levels
    
    def _calculate_level_strength(
        self,
        df: pd.DataFrame,
        index: int,
        level_price: float,
        is_high: bool,
    ) -> float:
        """
        Calculate the strength of a liquidity level.
        
        Strength based on:
        - How many times price tests the level
        - Volume at the level
        - How long the level has held
        """
        # Count touches around this level
        touch_tolerance = level_price * self.margin
        touches = df[
            (df['high'] >= level_price - touch_tolerance) &
            (df['low'] <= level_price + touch_tolerance)
        ]
        
        touch_count = len(touches)
        touch_strength = min(touch_count / 10, 1.0)  # Normalize to 0-1
        
        # Volume strength
        volume_at_level = touches['volume'].sum()
        avg_volume = df['volume'].mean()
        volume_strength = min(volume_at_level / (avg_volume * 5), 1.0)
        
        # Time strength (older levels that still hold are stronger)
        bars_since_level = len(df) - index
        time_strength = min(bars_since_level / len(df), 1.0)
        
        # Combined strength (weighted average)
        strength = (touch_strength * 0.5) + (volume_strength * 0.3) + (time_strength * 0.2)
        
        return strength
    
    def _create_liquidity_level(
        self,
        df: pd.DataFrame,
        index: int,
        level_price: float,
        liquidity_type: LiquidityType,
        strength: float,
    ) -> Optional[LiquidityLevel]:
        """Create a LiquidityLevel object with zone information."""
        touch_tolerance = level_price * self.margin
        
        # Find all touches
        touches = df[
            (df['high'] >= level_price - touch_tolerance) &
            (df['low'] <= level_price + touch_tolerance)
        ]
        
        if len(touches) < self.min_touch_count:
            return None
        
        zone_high = touches['high'].max()
        zone_low = touches['low'].min()
        
        # Check if level has been breached
        recent_df = df.iloc[index:]
        breached = False
        breach_ts = None
        
        if liquidity_type == LiquidityType.BUYSIDE:
            breached_mask = recent_df['low'] < zone_low
        else:  # SELLSIDE
            breached_mask = recent_df['high'] > zone_high
        
        if breached_mask.any():
            breached = True
            breach_ts = recent_df[breached_mask].index[0]
        
        return LiquidityLevel(
            price=level_price,
            liquidity_type=liquidity_type,
            strength=strength,
            first_touch=touches.index[0],
            last_touch=touches.index[-1],
            touch_count=len(touches),
            zone_high=zone_high,
            zone_low=zone_low,
            breached=breached,
            breach_timestamp=breach_ts,
        )
    
    def detect_buyside_zones(
        self, df: pd.DataFrame, buyside_levels: List[LiquidityLevel]
    ) -> List[BuysideLiquidityZone]:
        """
        Cluster buyside liquidity levels into zones.
        
        Buyside zones = where short sellers accumulated stop-losses
        """
        if not buyside_levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(buyside_levels, key=lambda x: x.price)
        
        zones = []
        current_zone_levels = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if level should be merged into current zone
            zone_center = np.mean([l.price for l in current_zone_levels])
            distance_pct = abs(level.price - zone_center) / zone_center
            
            if distance_pct <= self.zone_merge_tolerance:
                current_zone_levels.append(level)
            else:
                # Finalize current zone and start new one
                if len(current_zone_levels) >= 1:
                    zone = self._create_buyside_zone(current_zone_levels, df)
                    zones.append(zone)
                current_zone_levels = [level]
        
        # Finalize last zone
        if current_zone_levels:
            zone = self._create_buyside_zone(current_zone_levels, df)
            zones.append(zone)
        
        return zones
    
    def detect_sellside_zones(
        self, df: pd.DataFrame, sellside_levels: List[LiquidityLevel]
    ) -> List[SellsideLiquidityZone]:
        """
        Cluster sellside liquidity levels into zones.
        
        Sellside zones = where long traders accumulated stop-losses
        """
        if not sellside_levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(sellside_levels, key=lambda x: x.price)
        
        zones = []
        current_zone_levels = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if level should be merged into current zone
            zone_center = np.mean([l.price for l in current_zone_levels])
            distance_pct = abs(level.price - zone_center) / zone_center
            
            if distance_pct <= self.zone_merge_tolerance:
                current_zone_levels.append(level)
            else:
                # Finalize current zone and start new one
                if len(current_zone_levels) >= 1:
                    zone = self._create_sellside_zone(current_zone_levels, df)
                    zones.append(zone)
                current_zone_levels = [level]
        
        # Finalize last zone
        if current_zone_levels:
            zone = self._create_sellside_zone(current_zone_levels, df)
            zones.append(zone)
        
        return zones
    
    def _create_buyside_zone(
        self, levels: List[LiquidityLevel], df: pd.DataFrame
    ) -> BuysideLiquidityZone:
        """Create a buyside zone from clustered levels."""
        prices = [l.price for l in levels]
        zone_low = min(prices) - (min(prices) * self.margin)
        zone_high = max(prices) + (max(prices) * self.margin)
        
        total_strength = sum(l.strength for l in levels) / len(levels)
        
        return BuysideLiquidityZone(
            zone_high=zone_high,
            zone_low=zone_low,
            liquidity_levels=levels,
            total_strength=total_strength,
            formation_timestamp=min(l.first_touch for l in levels),
            last_update=max(l.last_touch for l in levels),
        )
    
    def _create_sellside_zone(
        self, levels: List[LiquidityLevel], df: pd.DataFrame
    ) -> SellsideLiquidityZone:
        """Create a sellside zone from clustered levels."""
        prices = [l.price for l in levels]
        zone_low = min(prices) - (min(prices) * self.margin)
        zone_high = max(prices) + (max(prices) * self.margin)
        
        total_strength = sum(l.strength for l in levels) / len(levels)
        
        return SellsideLiquidityZone(
            zone_high=zone_high,
            zone_low=zone_low,
            liquidity_levels=levels,
            total_strength=total_strength,
            formation_timestamp=min(l.first_touch for l in levels),
            last_update=max(l.last_touch for l in levels),
        )
    
    def detect_liquidity_voids(
        self, df: pd.DataFrame
    ) -> List[LiquidityVoid]:
        """
        Detect liquidity voids - rapid price movements with minimal support.
        
        Characteristics:
        - Large-bodied candles
        - Minimal wicks
        - Strong directional bias
        - Often get "filled" later
        """
        if self.mode == LiquidityMode.PRESENT:
            analysis_df = df.tail(self.present_bars).copy()
        else:
            analysis_df = df.copy()
        
        voids = []
        
        # Calculate candle metrics
        analysis_df['body_size'] = abs(analysis_df['close'] - analysis_df['open'])
        analysis_df['total_range'] = analysis_df['high'] - analysis_df['low']
        analysis_df['upper_wick'] = analysis_df['high'] - analysis_df[['open', 'close']].max(axis=1)
        analysis_df['lower_wick'] = analysis_df[['open', 'close']].min(axis=1) - analysis_df['low']
        analysis_df['wick_ratio'] = (analysis_df['upper_wick'] + analysis_df['lower_wick']) / (
            analysis_df['body_size'] + 0.0001
        )
        
        # Find consecutive large-bodied candles with small wicks
        in_void = False
        void_start_idx = 0
        void_candles = []
        
        for i in range(len(analysis_df)):
            row = analysis_df.iloc[i]
            
            # Check void conditions
            body_pct = row['body_size'] / row['total_range'] if row['total_range'] > 0 else 0
            is_large_candle = body_pct > (0.7 * self.void_sensitivity)
            is_low_wick = row['wick_ratio'] < 0.3
            
            if is_large_candle and is_low_wick:
                if not in_void:
                    in_void = True
                    void_start_idx = i
                    void_candles = [i]
                else:
                    void_candles.append(i)
            else:
                # Void ended
                if in_void and len(void_candles) >= 2:
                    void = self._create_liquidity_void(analysis_df, void_candles)
                    if void:
                        voids.append(void)
                
                in_void = False
                void_candles = []
        
        # Handle final void
        if in_void and len(void_candles) >= 2:
            void = self._create_liquidity_void(analysis_df, void_candles)
            if void:
                voids.append(void)
        
        return voids
    
    def _create_liquidity_void(
        self, df: pd.DataFrame, candle_indices: List[int]
    ) -> Optional[LiquidityVoid]:
        """Create a LiquidityVoid object."""
        if not candle_indices:
            return None
        
        void_df = df.iloc[candle_indices]
        
        # Determine void direction
        start_price = df.iloc[candle_indices[0]]['close']
        end_price = df.iloc[candle_indices[-1]]['close']
        
        if end_price > start_price:
            void_type = VoidType.BULLISH
            top_price = void_df['high'].max()
            bottom_price = void_df['low'].min()
        else:
            void_type = VoidType.BEARISH
            top_price = void_df['high'].max()
            bottom_price = void_df['low'].min()
        
        void_size = abs(top_price - bottom_price)
        avg_body = void_df['body_size'].mean()
        avg_wick_ratio = void_df['wick_ratio'].mean()
        
        return LiquidityVoid(
            void_type=void_type,
            top_price=top_price,
            bottom_price=bottom_price,
            void_size=void_size,
            candle_count=len(candle_indices),
            start_timestamp=df.iloc[candle_indices[0]].name,
            end_timestamp=df.iloc[candle_indices[-1]].name,
            avg_body_size=avg_body,
            avg_wick_ratio=avg_wick_ratio,
        )
    
    def detect_zone_breaches(
        self,
        df: pd.DataFrame,
        buyside_zones: List[BuysideLiquidityZone],
        sellside_zones: List[SellsideLiquidityZone],
    ) -> Dict[str, List[Dict]]:
        """
        Detect when price breaks through liquidity zones.
        
        Returns:
            Dictionary with bullish_breaches and bearish_breaches
        """
        breaches = {
            'bullish_breaches': [],  # Breaking above sellside
            'bearish_breaches': [],  # Breaking below buyside
        }
        
        current_price = df['close'].iloc[-1]
        
        # Check sellside zone breaches (bullish)
        for zone in sellside_zones:
            if current_price > zone.zone_high and not zone.liquidity_levels[0].breached:
                breaches['bullish_breaches'].append({
                    'zone': zone,
                    'price': current_price,
                    'zone_center': zone.get_zone_center(),
                    'excess': current_price - zone.zone_high,
                    'timestamp': df.index[-1],
                    'strength': zone.total_strength,
                })
        
        # Check buyside zone breaches (bearish)
        for zone in buyside_zones:
            if current_price < zone.zone_low and not zone.liquidity_levels[0].breached:
                breaches['bearish_breaches'].append({
                    'zone': zone,
                    'price': current_price,
                    'zone_center': zone.get_zone_center(),
                    'excess': zone.zone_low - current_price,
                    'timestamp': df.index[-1],
                    'strength': zone.total_strength,
                })
        
        return breaches


def example_usage():
    """Example usage of the Liquidity Detector."""
    import numpy as np
    
    # Generate synthetic price data with some structure
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='1h')
    
    # Create trending price with noise
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(len(dates)) * 0.1,
        'high': prices + np.abs(np.random.randn(len(dates)) * 0.3),
        'low': prices - np.abs(np.random.randn(len(dates)) * 0.3),
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates)),
    }, index=dates)
    
    # Create detector
    detector = LiquidityDetector(
        detection_length=20,
        margin=0.002,
        mode=LiquidityMode.PRESENT,
        present_bars=200,
    )
    
    print("=== LIQUIDITY LEVEL DETECTION ===")
    buyside, sellside = detector.detect_liquidity_levels(df)
    
    print(f"\nBuyside Liquidity Levels: {len(buyside)}")
    for i, level in enumerate(buyside[:3], 1):
        print(f"  Level {i}: ${level.price:.2f}")
        print(f"    Strength: {level.strength:.1%}")
        print(f"    Touches: {level.touch_count}")
        print(f"    Breached: {level.breached}")
    
    print(f"\nSellside Liquidity Levels: {len(sellside)}")
    for i, level in enumerate(sellside[:3], 1):
        print(f"  Level {i}: ${level.price:.2f}")
        print(f"    Strength: {level.strength:.1%}")
        print(f"    Touches: {level.touch_count}")
        print(f"    Breached: {level.breached}")
    
    # Detect zones
    print("\n=== LIQUIDITY ZONES ===")
    buyside_zones = detector.detect_buyside_zones(df, buyside)
    sellside_zones = detector.detect_sellside_zones(df, sellside)
    
    print(f"Buyside Zones: {len(buyside_zones)}")
    for zone in buyside_zones[:2]:
        print(f"  ${zone.zone_low:.2f} - ${zone.zone_high:.2f}")
        print(f"    Center: ${zone.get_zone_center():.2f}, Width: ${zone.get_zone_width():.2f}")
    
    print(f"\nSellside Zones: {len(sellside_zones)}")
    for zone in sellside_zones[:2]:
        print(f"  ${zone.zone_low:.2f} - ${zone.zone_high:.2f}")
        print(f"    Center: ${zone.get_zone_center():.2f}, Width: ${zone.get_zone_width():.2f}")
    
    # Detect voids
    print("\n=== LIQUIDITY VOIDS ===")
    voids = detector.detect_liquidity_voids(df)
    print(f"Total Voids: {len(voids)}")
    for i, void in enumerate(voids[:3], 1):
        print(f"  Void {i}: {void.void_type.value.upper()}")
        print(f"    Size: ${void.void_size:.4f}")
        print(f"    Candles: {void.candle_count}")
        print(f"    Wick Ratio: {void.avg_wick_ratio:.2f}")
    
    # Detect breaches
    print("\n=== ZONE BREACHES ===")
    breaches = detector.detect_zone_breaches(df, buyside_zones, sellside_zones)
    print(f"Bullish Breaches: {len(breaches['bullish_breaches'])}")
    print(f"Bearish Breaches: {len(breaches['bearish_breaches'])}")


if __name__ == "__main__":
    example_usage()
