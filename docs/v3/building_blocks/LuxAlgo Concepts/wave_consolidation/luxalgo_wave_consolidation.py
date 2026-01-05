"""
LuxAlgo Wave Consolidation - Core Implementation
===============================================

Wave consolidation zone detection using volume profiles and market structure
to identify support/resistance zones from directional moves.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class ZoneBias(Enum):
    """Zone bias (support/resistance)."""
    BULLISH = 'bullish'  # Support zone
    BEARISH = 'bearish'  # Resistance zone
    NEUTRAL = 'neutral'


class ZoneStatus(Enum):
    """Zone interaction status."""
    ACTIVE = 'active'
    MITIGATED = 'mitigated'
    DELETED = 'deleted'
    BROKEN = 'broken'


@dataclass
class VolumeProfile:
    """Volume profile for a price range."""
    start_bar: int
    end_bar: int
    price_levels: List[float]
    volume_at_level: List[float]
    poc: float  # Point of Control
    average_volume: float


@dataclass
class ConsolidationZone:
    """Identified consolidation zone."""
    zone_id: int
    start_bar: int
    end_bar: int
    timestamp_start: pd.Timestamp
    timestamp_end: pd.Timestamp
    
    zone_bias: ZoneBias
    status: ZoneStatus
    
    # Zone boundaries
    zone_high: float
    zone_low: float
    zone_midpoint: float
    
    # Volume profile
    poc: float  # Point of Control
    volume_profile: Optional[VolumeProfile] = None
    
    # Zone characteristics
    zone_width_pct: float = 0.0
    touches: int = 0
    breaks: int = 0
    rejections: int = 0
    
    # Management
    is_merged: bool = False
    merged_with: Optional[int] = None


class StructureDetector:
    """Detect market structure (swings, higher highs, lower lows)."""
    
    def __init__(self, structure_length: int = 5):
        """
        Initialize structure detector.
        
        Args:
            structure_length: Bars to identify structure
        """
        self.structure_length = structure_length
    
    def detect_swings(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect swing highs and lows (market structure).
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            List of swing points
        """
        swings = []
        half_len = self.structure_length // 2
        
        for i in range(half_len, len(df) - half_len):
            # Check swing high
            center_high = df.iloc[i]['high']
            left_high = df.iloc[max(0, i - half_len):i]['high'].max()
            right_high = df.iloc[i + 1:min(len(df), i + half_len + 1)]['high'].max()
            
            if center_high >= left_high and center_high >= right_high:
                swings.append({
                    'type': 'high',
                    'price': center_high,
                    'bar_index': i,
                    'timestamp': df.index[i],
                })
            
            # Check swing low
            center_low = df.iloc[i]['low']
            left_low = df.iloc[max(0, i - half_len):i]['low'].min()
            right_low = df.iloc[i + 1:min(len(df), i + half_len + 1)]['low'].min()
            
            if center_low <= left_low and center_low <= right_low:
                swings.append({
                    'type': 'low',
                    'price': center_low,
                    'bar_index': i,
                    'timestamp': df.index[i],
                })
        
        return swings
    
    def identify_directional_moves(self, swings: List[Dict]) -> List[Dict]:
        """
        Identify directional moves (higher highs, lower lows).
        
        Args:
            swings: List of swing points
        
        Returns:
            List of directional moves
        """
        moves = []
        
        if len(swings) < 2:
            return moves
        
        for i in range(1, len(swings)):
            curr = swings[i]
            prev = swings[i - 1]
            
            if curr['type'] == prev['type']:
                continue
            
            # Higher high = bullish move
            if curr['type'] == 'high' and curr['price'] > prev['price']:
                moves.append({
                    'type': 'bullish',
                    'start_bar': prev['bar_index'],
                    'end_bar': curr['bar_index'],
                    'from_price': prev['price'],
                    'to_price': curr['price'],
                    'start_time': prev['timestamp'],
                    'end_time': curr['timestamp'],
                })
            
            # Lower low = bearish move
            elif curr['type'] == 'low' and curr['price'] < prev['price']:
                moves.append({
                    'type': 'bearish',
                    'start_bar': prev['bar_index'],
                    'end_bar': curr['bar_index'],
                    'from_price': prev['price'],
                    'to_price': curr['price'],
                    'start_time': prev['timestamp'],
                    'end_time': curr['timestamp'],
                })
        
        return moves


class VolumeProfileCalculator:
    """Calculate volume profiles for price ranges."""
    
    @staticmethod
    def calculate_profile(df: pd.DataFrame,
                         start_bar: int,
                         end_bar: int,
                         price_bins: int = 50) -> VolumeProfile:
        """
        Calculate volume profile for bar range.
        
        Args:
            df: OHLCV DataFrame
            start_bar: Start bar index
            end_bar: End bar index
            price_bins: Number of price bins
        
        Returns:
            VolumeProfile object
        """
        data_slice = df.iloc[start_bar:end_bar + 1]
        
        # Get price range
        high = data_slice['high'].max()
        low = data_slice['low'].min()
        
        # Create bins
        bins = np.linspace(low, high, price_bins)
        volume_at_level = np.zeros(price_bins - 1)
        
        # Distribute volume to bins
        for idx, row in data_slice.iterrows():
            bar_high = row['high']
            bar_low = row['low']
            bar_volume = row.get('volume', 1.0)
            
            # Find bins this bar touches
            touching_bins = np.where((bins >= bar_low) & (bins <= bar_high))[0]
            if len(touching_bins) > 0:
                # Distribute volume equally
                volume_per_bin = bar_volume / len(touching_bins)
                volume_at_level[touching_bins] += volume_per_bin
        
        # Find POC (Point of Control)
        poc_idx = np.argmax(volume_at_level)
        poc = (bins[poc_idx] + bins[poc_idx + 1]) / 2
        
        avg_volume = np.mean(volume_at_level)
        
        price_levels = list(bins[:-1])
        
        return VolumeProfile(
            start_bar=start_bar,
            end_bar=end_bar,
            price_levels=price_levels,
            volume_at_level=list(volume_at_level),
            poc=poc,
            average_volume=avg_volume,
        )


class ConsolidationZoneBuilder:
    """Build consolidation zones from directional moves."""
    
    @staticmethod
    def build_zone(df: pd.DataFrame,
                  directional_move: Dict,
                  multiplier: float = 1.0) -> ConsolidationZone:
        """
        Build consolidation zone from directional move.
        
        Args:
            df: OHLCV DataFrame
            directional_move: Directional move data
            multiplier: Volume threshold multiplier
        
        Returns:
            ConsolidationZone object
        """
        # Calculate volume profile
        profile = VolumeProfileCalculator.calculate_profile(
            df, directional_move['start_bar'], directional_move['end_bar']
        )
        
        # Determine zone boundaries based on volume profile
        poc = profile.poc
        avg_vol = profile.average_volume
        threshold = avg_vol * multiplier
        
        # Find zone high (expand up from POC)
        zone_high = poc
        for price, vol in zip(profile.price_levels, profile.volume_at_level):
            if price >= poc and vol >= threshold:
                zone_high = max(zone_high, price)
        
        # Find zone low (expand down from POC)
        zone_low = poc
        for price, vol in zip(profile.price_levels, profile.volume_at_level):
            if price <= poc and vol >= threshold:
                zone_low = min(zone_low, price)
        
        # Ensure zones have minimum width
        if zone_high == zone_low:
            min_width = np.abs(zone_high) * 0.001
            zone_high += min_width
            zone_low -= min_width
        
        zone_midpoint = (zone_high + zone_low) / 2
        zone_width_pct = ((zone_high - zone_low) / zone_low) * 100
        
        # Determine bias
        if directional_move['type'] == 'bullish':
            bias = ZoneBias.BULLISH
        else:
            bias = ZoneBias.BEARISH
        
        return ConsolidationZone(
            zone_id=int(directional_move['start_bar']),
            start_bar=directional_move['start_bar'],
            end_bar=directional_move['end_bar'],
            timestamp_start=directional_move['start_time'],
            timestamp_end=directional_move['end_time'],
            zone_bias=bias,
            status=ZoneStatus.ACTIVE,
            zone_high=zone_high,
            zone_low=zone_low,
            zone_midpoint=zone_midpoint,
            poc=poc,
            volume_profile=profile,
            zone_width_pct=zone_width_pct,
        )


class ZoneManager:
    """Manage zone lifecycle (merge, delete, update status)."""
    
    @staticmethod
    def merge_overlapping_zones(zones: List[ConsolidationZone]) -> List[ConsolidationZone]:
        """
        Merge overlapping zones into one.
        
        Args:
            zones: List of zones
        
        Returns:
            Merged zones
        """
        if not zones:
            return zones
        
        merged = []
        used_ids = set()
        
        for i, zone1 in enumerate(zones):
            if zone1.zone_id in used_ids:
                continue
            
            merged_zone = zone1
            used_ids.add(zone1.zone_id)
            
            # Check for overlaps with other zones
            for j, zone2 in enumerate(zones[i + 1:], i + 1):
                if zone2.zone_id in used_ids:
                    continue
                
                # Check if zones overlap
                if not (zone1.zone_high < zone2.zone_low or zone1.zone_low > zone2.zone_high):
                    # Merge zones
                    merged_zone = ConsolidationZone(
                        zone_id=min(zone1.zone_id, zone2.zone_id),
                        start_bar=min(zone1.start_bar, zone2.start_bar),
                        end_bar=max(zone1.end_bar, zone2.end_bar),
                        timestamp_start=min(zone1.timestamp_start, zone2.timestamp_start),
                        timestamp_end=max(zone1.timestamp_end, zone2.timestamp_end),
                        zone_bias=zone1.zone_bias if zone1.start_bar < zone2.start_bar else zone2.zone_bias,
                        status=ZoneStatus.ACTIVE,
                        zone_high=max(zone1.zone_high, zone2.zone_high),
                        zone_low=min(zone1.zone_low, zone2.zone_low),
                        zone_midpoint=(max(zone1.zone_high, zone2.zone_high) + min(zone1.zone_low, zone2.zone_low)) / 2,
                        poc=(zone1.poc + zone2.poc) / 2,
                        is_merged=True,
                        merged_with=zone2.zone_id,
                    )
                    used_ids.add(zone2.zone_id)
            
            merged.append(merged_zone)
        
        return merged
    
    @staticmethod
    def update_zone_status(zones: List[ConsolidationZone],
                          df: pd.DataFrame,
                          current_bar: int) -> List[ConsolidationZone]:
        """
        Update zone status based on price interaction.
        
        Args:
            zones: List of zones
            df: OHLCV DataFrame
            current_bar: Current bar index
        
        Returns:
            Updated zones
        """
        if current_bar >= len(df):
            return zones
        
        current_price = df.iloc[current_bar]['close']
        current_high = df.iloc[current_bar]['high']
        current_low = df.iloc[current_bar]['low']
        
        for zone in zones:
            if zone.status == ZoneStatus.DELETED:
                continue
            
            # Check if price is within zone
            if zone.zone_low <= current_price <= zone.zone_high:
                zone.touches += 1
            
            # Check for break (opposite direction of bias)
            if zone.zone_bias == ZoneBias.BULLISH:
                # Bullish zone broken if price closes below it
                if current_price < zone.zone_low:
                    zone.status = ZoneStatus.MITIGATED
                    zone.breaks += 1
            else:
                # Bearish zone broken if price closes above it
                if current_price > zone.zone_high:
                    zone.status = ZoneStatus.MITIGATED
                    zone.breaks += 1
            
            # Check for rejection
            if (zone.zone_bias == ZoneBias.BULLISH and current_low < zone.zone_low and current_price > zone.zone_low):
                zone.rejections += 1
            elif (zone.zone_bias == ZoneBias.BEARISH and current_high > zone.zone_high and current_price < zone.zone_high):
                zone.rejections += 1
        
        return zones


class WaveConsolidationDetector:
    """Main wave consolidation detection engine."""
    
    def __init__(self, structure_length: int = 5,
                 multiplier: float = 1.0,
                 display_count: int = 10):
        """
        Initialize wave consolidation detector.
        
        Args:
            structure_length: Bars for structure detection
            multiplier: Volume threshold multiplier
            display_count: Number of zones to display
        """
        self.structure_detector = StructureDetector(structure_length)
        self.multiplier = multiplier
        self.display_count = display_count
        self.zone_counter = 0
    
    def analyze(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Detect wave consolidation zones.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            Tuple of (DataFrame with analysis, results dict)
        """
        # Detect structure
        swings = self.structure_detector.detect_swings(df)
        moves = self.structure_detector.identify_directional_moves(swings)
        
        # Build zones
        zones = []
        for move in moves:
            zone = ConsolidationZoneBuilder.build_zone(df, move, self.multiplier)
            zones.append(zone)
        
        # Merge overlapping zones
        zones = ZoneManager.merge_overlapping_zones(zones)
        
        # Update zones for all bars
        for bar_idx in range(len(df)):
            zones = ZoneManager.update_zone_status(zones, df, bar_idx)
        
        # Keep only recent zones
        zones = sorted(zones, key=lambda z: z.end_bar, reverse=True)[:self.display_count]
        
        # Create result DataFrame
        df_result = df.copy()
        df_result['zone_high'] = np.nan
        df_result['zone_low'] = np.nan
        df_result['zone_bias'] = ''
        df_result['in_zone'] = False
        
        for zone in zones:
            for bar_idx in range(zone.start_bar, min(zone.end_bar + 1, len(df_result))):
                df_result.iloc[bar_idx, df_result.columns.get_loc('zone_high')] = zone.zone_high
                df_result.iloc[bar_idx, df_result.columns.get_loc('zone_low')] = zone.zone_low
                df_result.iloc[bar_idx, df_result.columns.get_loc('zone_bias')] = zone.zone_bias.value
                
                if zone.zone_low <= df.iloc[bar_idx]['close'] <= zone.zone_high:
                    df_result.iloc[bar_idx, df_result.columns.get_loc('in_zone')] = True
        
        bullish_zones = [z for z in zones if z.zone_bias == ZoneBias.BULLISH]
        bearish_zones = [z for z in zones if z.zone_bias == ZoneBias.BEARISH]
        
        return df_result, {
            'zones': zones,
            'total_zones': len(zones),
            'bullish_zones': len(bullish_zones),
            'bearish_zones': len(bearish_zones),
            'active_zones': len([z for z in zones if z.status == ZoneStatus.ACTIVE]),
            'mitigated_zones': len([z for z in zones if z.status == ZoneStatus.MITIGATED]),
            'swings': swings,
            'moves': moves,
        }


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=200, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(200) * 0.2)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(200) * 0.1,
        'high': prices + np.abs(np.random.randn(200) * 0.3),
        'low': prices - np.abs(np.random.randn(200) * 0.3),
        'close': prices,
        'volume': np.random.uniform(1000, 5000, 200),
    }, index=dates)
    
    detector = WaveConsolidationDetector(structure_length=5, multiplier=1.0, display_count=10)
    df_result, results = detector.analyze(df)
    
    print("=" * 70)
    print("WAVE CONSOLIDATION - ANALYSIS")
    print("=" * 70)
    
    print(f"\n✓ Total Zones: {results['total_zones']}")
    print(f"  Bullish: {results['bullish_zones']}")
    print(f"  Bearish: {results['bearish_zones']}")
    print(f"  Active: {results['active_zones']}")
    print(f"  Mitigated: {results['mitigated_zones']}")
    
    if results['zones']:
        print(f"\nRecent Zones:")
        for zone in results['zones'][:5]:
            print(f"  {zone.timestamp_end.date()}: {zone.zone_bias.value.upper()} ${zone.zone_low:.2f}-${zone.zone_high:.2f} (Touches: {zone.touches})")
