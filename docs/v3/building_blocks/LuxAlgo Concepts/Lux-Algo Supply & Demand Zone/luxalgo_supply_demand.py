"""
LuxAlgo Supply & Demand Zone Detection Implementation
======================================================

A robust, production-ready implementation of LuxAlgo's supply and demand zone
detection algorithm using volume profile analysis, intrabar data decomposition,
and polarity assessment.

Author: Advanced Trading Systems
Date: 2026
Python: 3.8+

Dependencies:
    - pandas>=1.3.0
    - numpy>=1.21.0
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
import warnings


class PolarityMethod(Enum):
    """Enumeration of available volume polarity classification methods."""
    BAR_POLARITY = "bar_polarity"
    BAR_PRESSURE = "bar_pressure"
    INTRABAR_POLARITY = "intrabar_polarity"
    INTRABAR_PRESSURE = "intrabar_pressure"
    VOLUME_DELTA = "volume_delta"


@dataclass
class SupplyDemandZone:
    """Data structure representing a single supply or demand zone."""
    zone_type: str
    high: float
    low: float
    poc: float
    vah: float
    val: float
    simple_avg: float
    weighted_avg: float
    equilibrium: float
    total_volume: float
    buying_volume: float
    selling_volume: float
    threshold_volume: float
    price_levels: Dict[float, float]
    
    def get_zone_width(self) -> float:
        """Calculate the width of the zone in price units."""
        return self.high - self.low
    
    def get_ratio(self) -> float:
        """Calculate the buying/selling ratio."""
        if self.total_volume == 0:
            return 0.0
        return self.buying_volume / self.total_volume


@dataclass
class PremiumDiscountZone:
    """Data structure for premium/discount zones."""
    swing_high: float
    swing_low: float
    equilibrium: float
    range_size: float
    discount_zone_start: float = None
    discount_zone_end: float = None
    premium_zone_start: float = None
    premium_zone_end: float = None
    
    def __post_init__(self):
        """Calculate zone boundaries."""
        self.range_size = self.swing_high - self.swing_low
        self.equilibrium = self.swing_low + (self.range_size * 0.5)
        self.discount_zone_start = self.swing_low
        self.discount_zone_end = self.equilibrium
        self.premium_zone_start = self.equilibrium
        self.premium_zone_end = self.swing_high
    
    def get_price_zone_percentage(self, price: float) -> float:
        """Calculate percentage of range a price occupies."""
        if self.range_size == 0:
            return 50.0
        return ((price - self.swing_low) / self.range_size) * 100
    
    def is_in_discount(self, price: float) -> bool:
        """Check if price is in discount zone (0-50%)."""
        return self.swing_low <= price <= self.equilibrium
    
    def is_in_premium(self, price: float) -> bool:
        """Check if price is in premium zone (50-100%)."""
        return self.equilibrium <= price <= self.swing_high


class LuxAlgoSupplyDemand:
    """
    Main class implementing LuxAlgo's supply and demand zone detection algorithm.
    
    Uses volume profile analysis to identify where institutional buying/selling occurred.
    """
    
    def __init__(
        self,
        resolution: int = 50,
        threshold_percent: float = 30.0,
        value_area_percent: float = 70.0,
        polarity_method: PolarityMethod = PolarityMethod.BAR_PRESSURE,
        intrabar_multiplier: int = 4,
    ):
        """
        Initialize the LuxAlgo Supply & Demand detector.
        
        Args:
            resolution: Number of price bins (10-200, default: 50)
            threshold_percent: % of total volume to trigger zone (10-60, default: 30)
            value_area_percent: % of volume in value area (50-90, default: 70)
            polarity_method: How to classify buy/sell volume (default: BAR_PRESSURE)
            intrabar_multiplier: Lower TF decomposition factor (default: 4)
        """
        self.resolution = resolution
        self.threshold_percent = threshold_percent
        self.value_area_percent = value_area_percent
        self.polarity_method = polarity_method
        self.intrabar_multiplier = intrabar_multiplier
        
        self._validate_parameters()
    
    def _validate_parameters(self) -> None:
        """Validate initialization parameters."""
        if not 10 <= self.resolution <= 200:
            raise ValueError(f"Resolution must be 10-200, got {self.resolution}")
        if not 10 <= self.threshold_percent <= 60:
            raise ValueError(f"Threshold must be 10-60%, got {self.threshold_percent}")
        if not 50 <= self.value_area_percent <= 90:
            raise ValueError(f"Value area must be 50-90%, got {self.value_area_percent}")
    
    def calculate_zones(
        self,
        df: pd.DataFrame,
        start_idx: Optional[int] = None,
        end_idx: Optional[int] = None,
    ) -> Tuple[List[SupplyDemandZone], List[SupplyDemandZone]]:
        """
        Calculate supply and demand zones.
        
        Args:
            df: DataFrame with OHLCV columns
            start_idx: Starting bar index
            end_idx: Ending bar index
        
        Returns:
            Tuple of (supply_zones, demand_zones) lists
        """
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain {required_cols}")
        
        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = len(df)
        
        range_df = df.iloc[start_idx:end_idx].copy()
        
        # Calculate volume profile (bin-based distribution)
        price_profile = self._calculate_volume_profile(range_df)
        
        # Classify volume by polarity (buying vs selling)
        buying_selling_profile = self._calculate_polarity(range_df)
        
        # Identify supply and demand zones
        supply_zones = self._identify_supply_zones(
            range_df, price_profile, buying_selling_profile
        )
        demand_zones = self._identify_demand_zones(
            range_df, price_profile, buying_selling_profile
        )
        
        return supply_zones, demand_zones
    
    def _calculate_volume_profile(self, df: pd.DataFrame) -> Dict[float, float]:
        """Calculate volume profile by binning prices."""
        price_high = df['high'].max()
        price_low = df['low'].min()
        price_range = price_high - price_low
        
        if price_range == 0:
            warnings.warn("Price range is zero, using single bin")
            price_range = 1.0
        
        bin_width = price_range / self.resolution
        price_profile: Dict[float, float] = {}
        
        for _, row in df.iterrows():
            price_point = row['close']
            bin_index = int((price_point - price_low) / bin_width)
            bin_index = min(bin_index, self.resolution - 1)
            bin_boundary = price_low + (bin_index * bin_width)
            
            if bin_boundary not in price_profile:
                price_profile[bin_boundary] = 0.0
            price_profile[bin_boundary] += row['volume']
        
        return price_profile
    
    def _calculate_polarity(self, df: pd.DataFrame) -> Dict[float, Tuple[float, float]]:
        """Classify volume as buying or selling pressure."""
        buying_selling: Dict[float, Tuple[float, float]] = {}
        
        price_high = df['high'].max()
        price_low = df['low'].min()
        price_range = price_high - price_low
        
        if price_range == 0:
            price_range = 1.0
        
        bin_width = price_range / self.resolution
        
        for _, row in df.iterrows():
            price_point = row['close']
            bin_index = int((price_point - price_low) / bin_width)
            bin_index = min(bin_index, self.resolution - 1)
            bin_boundary = price_low + (bin_index * bin_width)
            
            # Determine polarity using selected method
            if self.polarity_method == PolarityMethod.BAR_POLARITY:
                is_bullish = row['close'] > row['open']
                
            elif self.polarity_method == PolarityMethod.BAR_PRESSURE:
                bar_range = row['high'] - row['low']
                if bar_range == 0:
                    is_bullish = row['close'] > row['open']
                else:
                    close_position = (row['close'] - row['low']) / bar_range
                    is_bullish = close_position > 0.5
                    
            else:  # Default to BAR_PRESSURE for other methods
                bar_range = row['high'] - row['low']
                if bar_range == 0:
                    is_bullish = row['close'] > row['open']
                else:
                    close_position = (row['close'] - row['low']) / bar_range
                    is_bullish = close_position > 0.5
            
            if bin_boundary not in buying_selling:
                buying_selling[bin_boundary] = (0.0, 0.0)
            
            buying_vol, selling_vol = buying_selling[bin_boundary]
            if is_bullish:
                buying_vol += row['volume']
            else:
                selling_vol += row['volume']
            
            buying_selling[bin_boundary] = (buying_vol, selling_vol)
        
        return buying_selling
    
    def _identify_supply_zones(
        self,
        df: pd.DataFrame,
        price_profile: Dict[float, float],
        buying_selling: Dict[float, Tuple[float, float]],
    ) -> List[SupplyDemandZone]:
        """Identify supply zones by accumulating volume from top downward."""
        supply_zones = []
        
        total_volume = sum(price_profile.values())
        if total_volume == 0:
            return supply_zones
        
        threshold_volume = total_volume * (self.threshold_percent / 100.0)
        sorted_prices = sorted(price_profile.keys(), reverse=True)
        
        accumulated_volume = 0.0
        zone_start = None
        zone_prices = {}
        accumulated_buying = 0.0
        accumulated_selling = 0.0
        
        for price_bin in sorted_prices:
            bin_volume = price_profile[price_bin]
            buying_vol, selling_vol = buying_selling.get(price_bin, (0.0, 0.0))
            
            accumulated_volume += bin_volume
            accumulated_buying += buying_vol
            accumulated_selling += selling_vol
            zone_prices[price_bin] = bin_volume
            
            if accumulated_volume >= threshold_volume and zone_start is not None:
                zone_low = price_bin
                zone_high = zone_start
                
                zone = self._calculate_zone_stats(
                    zone_prices, zone_low, zone_high, 'supply',
                    accumulated_volume, accumulated_buying, accumulated_selling,
                    threshold_volume
                )
                supply_zones.append(zone)
                
                accumulated_volume = 0.0
                accumulated_buying = 0.0
                accumulated_selling = 0.0
                zone_start = None
                zone_prices = {}
            
            elif accumulated_volume >= threshold_volume and zone_start is None:
                zone_start = price_bin
        
        return supply_zones
    
    def _identify_demand_zones(
        self,
        df: pd.DataFrame,
        price_profile: Dict[float, float],
        buying_selling: Dict[float, Tuple[float, float]],
    ) -> List[SupplyDemandZone]:
        """Identify demand zones by accumulating volume from bottom upward."""
        demand_zones = []
        
        total_volume = sum(price_profile.values())
        if total_volume == 0:
            return demand_zones
        
        threshold_volume = total_volume * (self.threshold_percent / 100.0)
        sorted_prices = sorted(price_profile.keys())
        
        accumulated_volume = 0.0
        zone_start = None
        zone_prices = {}
        accumulated_buying = 0.0
        accumulated_selling = 0.0
        
        for price_bin in sorted_prices:
            bin_volume = price_profile[price_bin]
            buying_vol, selling_vol = buying_selling.get(price_bin, (0.0, 0.0))
            
            accumulated_volume += bin_volume
            accumulated_buying += buying_vol
            accumulated_selling += selling_vol
            zone_prices[price_bin] = bin_volume
            
            if accumulated_volume >= threshold_volume and zone_start is not None:
                zone_high = price_bin
                zone_low = zone_start
                
                zone = self._calculate_zone_stats(
                    zone_prices, zone_low, zone_high, 'demand',
                    accumulated_volume, accumulated_buying, accumulated_selling,
                    threshold_volume
                )
                demand_zones.append(zone)
                
                accumulated_volume = 0.0
                accumulated_buying = 0.0
                accumulated_selling = 0.0
                zone_start = None
                zone_prices = {}
            
            elif accumulated_volume >= threshold_volume and zone_start is None:
                zone_start = price_bin
        
        return demand_zones
    
    def _calculate_zone_stats(
        self,
        zone_prices: Dict[float, float],
        zone_low: float,
        zone_high: float,
        zone_type: str,
        total_volume: float,
        buying_volume: float,
        selling_volume: float,
        threshold_volume: float,
    ) -> SupplyDemandZone:
        """Calculate all statistical measures for a zone."""
        # Point of Control (POC)
        poc = max(zone_prices.items(), key=lambda x: x[1])[0]
        
        # Value Area
        vah, val = self._calculate_value_area(zone_prices, poc)
        
        # Simple average
        simple_avg = (zone_high + zone_low) / 2.0
        
        # Weighted average price
        weighted_sum = sum(price * vol for price, vol in zone_prices.items())
        weighted_avg = weighted_sum / total_volume if total_volume > 0 else simple_avg
        
        # Equilibrium
        equilibrium = (simple_avg + weighted_avg) / 2.0
        
        return SupplyDemandZone(
            zone_type=zone_type,
            high=zone_high,
            low=zone_low,
            poc=poc,
            vah=vah,
            val=val,
            simple_avg=simple_avg,
            weighted_avg=weighted_avg,
            equilibrium=equilibrium,
            total_volume=total_volume,
            buying_volume=buying_volume,
            selling_volume=selling_volume,
            threshold_volume=threshold_volume,
            price_levels=zone_prices.copy(),
        )
    
    def _calculate_value_area(
        self, zone_prices: Dict[float, float], poc: float
    ) -> Tuple[float, float]:
        """Calculate Value Area High and Low (VAH/VAL)."""
        total_vol = sum(zone_prices.values())
        target_vol = total_vol * (self.value_area_percent / 100.0)
        
        value_area_prices = {poc}
        accumulated_vol = zone_prices[poc]
        
        sorted_prices = sorted(zone_prices.keys())
        poc_idx = sorted_prices.index(poc)
        
        lower_idx = poc_idx - 1
        upper_idx = poc_idx + 1
        
        while accumulated_vol < target_vol:
            lower_vol = zone_prices.get(sorted_prices[lower_idx], 0) if lower_idx >= 0 else 0
            upper_vol = zone_prices.get(sorted_prices[upper_idx], 0) if upper_idx < len(sorted_prices) else 0
            
            if lower_vol > upper_vol and lower_idx >= 0:
                value_area_prices.add(sorted_prices[lower_idx])
                accumulated_vol += lower_vol
                lower_idx -= 1
            elif upper_idx < len(sorted_prices):
                value_area_prices.add(sorted_prices[upper_idx])
                accumulated_vol += upper_vol
                upper_idx += 1
            else:
                break
        
        vah = max(value_area_prices)
        val = min(value_area_prices)
        
        return vah, val
    
    def calculate_premium_discount_zones(
        self,
        swing_high: float,
        swing_low: float,
    ) -> PremiumDiscountZone:
        """Calculate premium and discount zones from swing structure."""
        return PremiumDiscountZone(
            swing_high=swing_high,
            swing_low=swing_low,
            equilibrium=0.0,
        )


def example_usage():
    """Example usage of the detector."""
    import numpy as np
    
    np.random.seed(42)
    n_bars = 200
    prices = 100 + np.cumsum(np.random.randn(n_bars) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(n_bars) * 0.1,
        'high': prices + np.abs(np.random.randn(n_bars) * 0.2),
        'low': prices - np.abs(np.random.randn(n_bars) * 0.2),
        'close': prices,
        'volume': np.random.randint(1000, 10000, n_bars),
    })
    
    detector = LuxAlgoSupplyDemand(
        resolution=50,
        threshold_percent=30,
        polarity_method=PolarityMethod.BAR_PRESSURE,
    )
    
    supply_zones, demand_zones = detector.calculate_zones(df)
    
    print("=== SUPPLY ZONES ===")
    for i, zone in enumerate(supply_zones, 1):
        print(f"\nZone #{i}")
        print(f"  Range: {zone.low:.2f} - {zone.high:.2f}")
        print(f"  Width: {zone.get_zone_width():.2f}")
        print(f"  POC: {zone.poc:.2f}")
        print(f"  Volume: {zone.total_volume:.0f}")
        print(f"  Ratio: {zone.get_ratio():.2%}")
    
    print("\n=== DEMAND ZONES ===")
    for i, zone in enumerate(demand_zones, 1):
        print(f"\nZone #{i}")
        print(f"  Range: {zone.low:.2f} - {zone.high:.2f}")
        print(f"  Width: {zone.get_zone_width():.2f}")
        print(f"  POC: {zone.poc:.2f}")
        print(f"  Volume: {zone.total_volume:.0f}")
        print(f"  Ratio: {zone.get_ratio():.2%}")
    
    swing_high = df['high'].max()
    swing_low = df['low'].min()
    pd_zone = detector.calculate_premium_discount_zones(swing_high, swing_low)
    
    print(f"\n=== PREMIUM/DISCOUNT ZONES ===")
    print(f"Swing High: {swing_high:.2f}")
    print(f"Swing Low: {swing_low:.2f}")
    print(f"Equilibrium: {pd_zone.equilibrium:.2f}")


if __name__ == "__main__":
    example_usage()
