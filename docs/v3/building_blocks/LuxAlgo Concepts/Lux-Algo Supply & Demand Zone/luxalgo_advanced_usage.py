"""
LuxAlgo Supply & Demand - Advanced Usage Examples
Advanced analysis, signal generation, and multi-timeframe features.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
from luxalgo_supply_demand import (
    LuxAlgoSupplyDemand,
    PolarityMethod,
    SupplyDemandZone,
    PremiumDiscountZone,
)


class ZoneAnalyzer:
    """Advanced analyzer for supply and demand zones."""
    
    def __init__(self, detector: LuxAlgoSupplyDemand):
        self.detector = detector
    
    def find_active_zones(
        self,
        df: pd.DataFrame,
        supply_zones: List[SupplyDemandZone],
        demand_zones: List[SupplyDemandZone],
    ) -> Tuple[List[SupplyDemandZone], List[SupplyDemandZone]]:
        """Filter zones to only those that haven't been mitigated."""
        current_price = df['close'].iloc[-1]
        
        # Supply zone is mitigated when price closes above it
        active_supply = [
            zone for zone in supply_zones
            if current_price < zone.high
        ]
        
        # Demand zone is mitigated when price closes below it
        active_demand = [
            zone for zone in demand_zones
            if current_price > zone.low
        ]
        
        return active_supply, active_demand
    
    def calculate_zone_proximity(
        self,
        df: pd.DataFrame,
        supply_zones: List[SupplyDemandZone],
        demand_zones: List[SupplyDemandZone],
        proximity_threshold: float = 0.02,
    ) -> Dict[str, List[Tuple[SupplyDemandZone, float]]]:
        """Calculate proximity of current price to zones."""
        current_price = df['close'].iloc[-1]
        result = {'supply': [], 'demand': []}
        
        for zone in supply_zones:
            distance_pct = (zone.low - current_price) / current_price
            if 0 < distance_pct <= proximity_threshold:
                result['supply'].append((zone, distance_pct))
        
        for zone in demand_zones:
            distance_pct = (current_price - zone.high) / current_price
            if 0 < distance_pct <= proximity_threshold:
                result['demand'].append((zone, distance_pct))
        
        result['supply'].sort(key=lambda x: x[1])
        result['demand'].sort(key=lambda x: x[1])
        
        return result
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        supply_zones: List[SupplyDemandZone],
        demand_zones: List[SupplyDemandZone],
        volume_threshold: float = 1.5,
    ) -> Dict[str, List[Dict]]:
        """Generate trading signals based on zone interactions."""
        signals = {
            'long_entries': [],
            'short_entries': [],
            'long_breakouts': [],
            'short_breakouts': [],
        }
        
        current_bar = df.iloc[-1]
        avg_volume = df['volume'].tail(20).mean()
        
        for zone in supply_zones:
            if current_bar['high'] >= zone.low and current_bar['close'] >= zone.low:
                signals['short_entries'].append({
                    'type': 'supply_touch',
                    'zone': zone,
                    'price': current_bar['close'],
                    'confidence': 'medium',
                })
            
            if current_bar['close'] > zone.high:
                vol_confirmed = current_bar['volume'] > avg_volume * volume_threshold
                signals['long_breakouts'].append({
                    'type': 'supply_breakout',
                    'zone': zone,
                    'price': current_bar['close'],
                    'volume_confirmed': vol_confirmed,
                    'confidence': 'high' if vol_confirmed else 'medium',
                })
        
        for zone in demand_zones:
            if current_bar['low'] <= zone.high and current_bar['close'] <= zone.high:
                signals['long_entries'].append({
                    'type': 'demand_touch',
                    'zone': zone,
                    'price': current_bar['close'],
                    'confidence': 'medium',
                })
            
            if current_bar['close'] < zone.low:
                vol_confirmed = current_bar['volume'] > avg_volume * volume_threshold
                signals['short_breakouts'].append({
                    'type': 'demand_breakout',
                    'zone': zone,
                    'price': current_bar['close'],
                    'volume_confirmed': vol_confirmed,
                    'confidence': 'high' if vol_confirmed else 'medium',
                })
        
        return signals
    
    def calculate_zone_statistics(
        self,
        supply_zones: List[SupplyDemandZone],
        demand_zones: List[SupplyDemandZone],
    ) -> Dict[str, float]:
        """Calculate aggregate statistics across all zones."""
        all_zones = supply_zones + demand_zones
        
        if not all_zones:
            return {}
        
        widths = [z.get_zone_width() for z in all_zones]
        ratios = [z.get_ratio() for z in all_zones]
        volumes = [z.total_volume for z in all_zones]
        
        return {
            'avg_zone_width': np.mean(widths),
            'median_zone_width': np.median(widths),
            'max_zone_width': np.max(widths),
            'min_zone_width': np.min(widths),
            'avg_buy_sell_ratio': np.mean(ratios),
            'avg_zone_volume': np.mean(volumes),
            'total_zones': len(all_zones),
            'supply_zones_count': len(supply_zones),
            'demand_zones_count': len(demand_zones),
        }


class MultiTimeframeAnalyzer:
    """Analyze zones across multiple timeframes."""
    
    def __init__(self):
        self.timeframes = {}
    
    def add_timeframe(
        self,
        name: str,
        df: pd.DataFrame,
        detector: LuxAlgoSupplyDemand,
    ) -> None:
        """Add a timeframe analysis."""
        supply_zones, demand_zones = detector.calculate_zones(df)
        self.timeframes[name] = {
            'detector': detector,
            'df': df,
            'supply_zones': supply_zones,
            'demand_zones': demand_zones,
        }
    
    def find_confluences(
        self,
        tolerance_pct: float = 0.01,
    ) -> Dict[str, List[Dict]]:
        """Find price levels where zones from multiple timeframes overlap."""
        confluences = {
            'support_confluences': [],
            'resistance_confluences': [],
        }
        
        all_demand_zones = []
        all_supply_zones = []
        
        for tf_name, tf_data in self.timeframes.items():
            for zone in tf_data['demand_zones']:
                all_demand_zones.append(zone)
            for zone in tf_data['supply_zones']:
                all_supply_zones.append(zone)
        
        demand_centers = self._find_zone_clusters(all_demand_zones, tolerance_pct)
        for center_price, zones in demand_centers.items():
            if len(zones) > 1:
                confluences['support_confluences'].append({
                    'price': center_price,
                    'strength': len(zones),
                    'zones': zones,
                })
        
        supply_centers = self._find_zone_clusters(all_supply_zones, tolerance_pct)
        for center_price, zones in supply_centers.items():
            if len(zones) > 1:
                confluences['resistance_confluences'].append({
                    'price': center_price,
                    'strength': len(zones),
                    'zones': zones,
                })
        
        return confluences
    
    @staticmethod
    def _find_zone_clusters(
        zones: List[SupplyDemandZone],
        tolerance_pct: float,
    ) -> Dict[float, List[SupplyDemandZone]]:
        """Group zones into clusters."""
        if not zones:
            return {}
        
        clusters = {}
        used = set()
        
        for i, zone_a in enumerate(zones):
            if i in used:
                continue
            
            cluster = [zone_a]
            used.add(i)
            
            for j, zone_b in enumerate(zones[i + 1 :], start=i + 1):
                if j in used:
                    continue
                
                if MultiTimeframeAnalyzer._zones_overlap(zone_a, zone_b, tolerance_pct):
                    cluster.append(zone_b)
                    used.add(j)
            
            center = np.mean([z.equilibrium for z in cluster])
            clusters[center] = cluster
        
        return clusters
    
    @staticmethod
    def _zones_overlap(
        zone_a: SupplyDemandZone,
        zone_b: SupplyDemandZone,
        tolerance_pct: float,
    ) -> bool:
        """Check if two zones overlap within tolerance."""
        price_a = zone_a.equilibrium
        price_b = zone_b.equilibrium
        
        distance = abs(price_a - price_b) / price_a
        return distance <= tolerance_pct


# Example usage
if __name__ == "__main__":
    print("Advanced LuxAlgo Supply & Demand Examples")
    print("=" * 60)
    
    # Generate sample data
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
    
    # Create detector and analyze
    detector = LuxAlgoSupplyDemand(
        resolution=50,
        threshold_percent=30,
        polarity_method=PolarityMethod.BAR_PRESSURE,
    )
    
    supply_zones, demand_zones = detector.calculate_zones(df)
    
    # Use analyzer
    analyzer = ZoneAnalyzer(detector)
    
    # Active zones
    active_supply, active_demand = analyzer.find_active_zones(df, supply_zones, demand_zones)
    print(f"\nActive Zones: {len(active_supply)} supply, {len(active_demand)} demand")
    
    # Proximity
    proximity = analyzer.calculate_zone_proximity(df, supply_zones, demand_zones)
    print(f"Nearby Zones: {len(proximity['supply'])} supply, {len(proximity['demand'])} demand")
    
    # Signals
    signals = analyzer.generate_signals(df, supply_zones, demand_zones)
    print(f"\nSignals Generated:")
    print(f"  Long entries: {len(signals['long_entries'])}")
    print(f"  Short entries: {len(signals['short_entries'])}")
    print(f"  Long breakouts: {len(signals['long_breakouts'])}")
    print(f"  Short breakouts: {len(signals['short_breakouts'])}")
    
    # Statistics
    stats = analyzer.calculate_zone_statistics(supply_zones, demand_zones)
    print(f"\nZone Statistics:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
