"""
LuxAlgo Buyside & Sellside Liquidity - Advanced Usage & Analysis
=================================================================

Advanced analysis utilities for ICT-based liquidity trading strategies,
including smart money order flow analysis, void fill probability,
and reversal/continuation pattern detection.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from luxalgo_liquidity import (
    LiquidityDetector,
    LiquidityLevel,
    LiquidityVoid,
    BuysideLiquidityZone,
    SellsideLiquidityZone,
    LiquidityType,
    VoidType,
    LiquidityMode,
)


class SmartMoneyAnalyzer:
    """Advanced analyzer for smart money order flow and liquidity hunting."""
    
    def __init__(self, detector: LiquidityDetector):
        self.detector = detector
    
    def analyze_zone_strength(
        self,
        buyside_zones: List[BuysideLiquidityZone],
        sellside_zones: List[SellsideLiquidityZone],
    ) -> Dict[str, List[Dict]]:
        """
        Rank liquidity zones by strength and significance.
        
        Factors:
        - Number of price tests
        - Total zone strength
        - Zone width (tighter = stronger)
        - Time in effect
        """
        buyside_analysis = []
        sellside_analysis = []
        
        # Analyze buyside zones
        for zone in buyside_zones:
            score = self._calculate_zone_score(zone)
            
            buyside_analysis.append({
                'zone': zone,
                'score': score,
                'rank': 0,  # Will be set after sorting
                'level_count': len(zone.liquidity_levels),
                'avg_level_strength': np.mean([l.strength for l in zone.liquidity_levels]),
                'zone_width_pct': (zone.get_zone_width() / zone.get_zone_center()) * 100,
                'formation_age_bars': 0,  # Set during analysis
                'interpretation': 'Short stop-loss accumulation - potential buy zone',
            })
        
        # Analyze sellside zones
        for zone in sellside_zones:
            score = self._calculate_zone_score(zone)
            
            sellside_analysis.append({
                'zone': zone,
                'score': score,
                'rank': 0,
                'level_count': len(zone.liquidity_levels),
                'avg_level_strength': np.mean([l.strength for l in zone.liquidity_levels]),
                'zone_width_pct': (zone.get_zone_width() / zone.get_zone_center()) * 100,
                'formation_age_bars': 0,
                'interpretation': 'Long stop-loss accumulation - potential sell zone',
            })
        
        # Sort by score and assign ranks
        buyside_analysis.sort(key=lambda x: x['score'], reverse=True)
        sellside_analysis.sort(key=lambda x: x['score'], reverse=True)
        
        for i, analysis in enumerate(buyside_analysis, 1):
            analysis['rank'] = i
        for i, analysis in enumerate(sellside_analysis, 1):
            analysis['rank'] = i
        
        return {
            'buyside': buyside_analysis,
            'sellside': sellside_analysis,
        }
    
    def _calculate_zone_score(
        self, zone: 'BuysideLiquidityZone | SellsideLiquidityZone'
    ) -> float:
        """Calculate composite strength score for a zone."""
        level_count_score = min(len(zone.liquidity_levels) / 5, 1.0)
        strength_score = zone.total_strength
        width_efficiency = 1.0 / (1.0 + zone.get_zone_width())  # Tighter is better
        
        composite = (level_count_score * 0.4) + (strength_score * 0.4) + (width_efficiency * 0.2)
        return composite
    
    def predict_void_fill_probability(
        self,
        df: pd.DataFrame,
        void: LiquidityVoid,
        lookback_bars: int = 100,
    ) -> Dict[str, any]:
        """
        Calculate probability that a liquidity void will be filled.
        
        Factors:
        - Void age
        - Void size
        - Market momentum
        - Support/resistance
        """
        bars_since_void = len(df) - df.index.get_loc(void.end_timestamp)
        current_price = df['close'].iloc[-1]
        
        # Void fill tendency (voids tend to be filled within time)
        age_factor = min(bars_since_void / 20, 1.0)  # Older voids more likely filled
        
        # Size factor (larger voids filled more slowly)
        size_factor = 1.0 / (1.0 + (void.void_size * 10))
        
        # Momentum factor (momentum pulls price to fill voids)
        recent_df = df.tail(lookback_bars)
        momentum = (recent_df['close'].iloc[-1] - recent_df['close'].iloc[0]) / recent_df['close'].iloc[0]
        momentum_factor = abs(momentum)
        
        # Direction alignment (if price moving toward void)
        if void.void_type == VoidType.BULLISH:
            # Void is above price, moving up fills it
            direction_aligned = current_price < void.bottom_price
        else:
            # Void is below price, moving down fills it
            direction_aligned = current_price > void.top_price
        
        direction_factor = 0.8 if direction_aligned else 0.2
        
        # Calculate probability
        fill_probability = (
            (age_factor * 0.3) +
            (size_factor * 0.2) +
            (momentum_factor * 0.3) +
            (direction_factor * 0.2)
        )
        
        return {
            'void': void,
            'fill_probability': min(fill_probability, 1.0),
            'bars_since_creation': bars_since_void,
            'size_vs_price': (void.void_size / current_price) * 100,
            'momentum': momentum,
            'direction_aligned': direction_aligned,
            'prediction': 'HIGH probability' if fill_probability > 0.7 else 'MEDIUM probability' if fill_probability > 0.4 else 'LOW probability',
        }
    
    def detect_reversal_patterns(
        self,
        df: pd.DataFrame,
        buyside_zones: List[BuysideLiquidityZone],
        sellside_zones: List[SellsideLiquidityZone],
    ) -> Dict[str, List[Dict]]:
        """
        Identify reversal patterns at liquidity zones.
        
        Patterns:
        - Price touches zone and bounces (rejection)
        - Double bottom/top at zones
        - Price sweeps and reverses
        """
        reversals = {
            'buyside_bounces': [],  # Price bounces up from buyside
            'sellside_bounces': [],  # Price bounces down from sellside
            'zone_touches': [],     # Recent touches without break
        }
        
        current_price = df['close'].iloc[-1]
        recent_df = df.tail(50)
        
        # Check buyside zones for bounces
        for zone in buyside_zones:
            # Check if price recently touched zone without breaking below
            touched = (
                recent_df['low'] <= zone.zone_high
            ) & (
                recent_df['low'] >= zone.zone_low
            )
            
            if touched.any():
                touch_idx = recent_df[touched].index[0]
                touch_price = recent_df[touched]['low'].min()
                
                # Check if bounced (price went up after touch)
                bars_after_touch = len(recent_df) - recent_df.index.get_loc(touch_idx)
                if bars_after_touch >= 3:
                    bounce_high = recent_df[recent_df.index > touch_idx]['high'].max()
                    bounce_strength = (bounce_high - touch_price) / zone.get_zone_width()
                    
                    if bounce_strength > 0.5:  # Significant bounce
                        reversals['buyside_bounces'].append({
                            'zone': zone,
                            'touch_price': touch_price,
                            'bounce_high': bounce_high,
                            'bounce_strength': bounce_strength,
                            'touch_timestamp': touch_idx,
                            'pattern': 'Bullish reversal - buy pressure confirmed',
                        })
        
        # Check sellside zones for bounces
        for zone in sellside_zones:
            touched = (
                recent_df['high'] >= zone.zone_low
            ) & (
                recent_df['high'] <= zone.zone_high
            )
            
            if touched.any():
                touch_idx = recent_df[touched].index[0]
                touch_price = recent_df[touched]['high'].max()
                
                bars_after_touch = len(recent_df) - recent_df.index.get_loc(touch_idx)
                if bars_after_touch >= 3:
                    bounce_low = recent_df[recent_df.index > touch_idx]['low'].min()
                    bounce_strength = (touch_price - bounce_low) / zone.get_zone_width()
                    
                    if bounce_strength > 0.5:
                        reversals['sellside_bounces'].append({
                            'zone': zone,
                            'touch_price': touch_price,
                            'bounce_low': bounce_low,
                            'bounce_strength': bounce_strength,
                            'touch_timestamp': touch_idx,
                            'pattern': 'Bearish reversal - sell pressure confirmed',
                        })
        
        return reversals
    
    def analyze_continuation_patterns(
        self,
        df: pd.DataFrame,
        buyside_zones: List[BuysideLiquidityZone],
        sellside_zones: List[SellsideLiquidityZone],
    ) -> Dict[str, List[Dict]]:
        """
        Identify continuation patterns when liquidity is breached.
        
        Continuation = price breaks through zone and extends further
        """
        continuations = {
            'bullish_continuations': [],  # Price breaks above sellside and continues
            'bearish_continuations': [],  # Price breaks below buyside and continues
        }
        
        current_price = df['close'].iloc[-1]
        recent_df = df.tail(50)
        
        # Check for bullish continuations
        for zone in sellside_zones:
            # Price must break above zone
            above_zone = recent_df['close'] > zone.zone_high
            
            if above_zone.any():
                break_idx = recent_df[above_zone].index[0]
                break_bar = recent_df[recent_df.index == break_idx].iloc[0]
                
                # Check continuation after break
                bars_after_break = len(recent_df) - recent_df.index.get_loc(break_idx)
                if bars_after_break >= 5:
                    extension = recent_df[recent_df.index >= break_idx]['high'].max() - zone.zone_high
                    extension_pct = (extension / zone.get_zone_width()) * 100
                    
                    if extension_pct > 50:  # Significant continuation
                        continuations['bullish_continuations'].append({
                            'zone': zone,
                            'break_price': break_bar['close'],
                            'extension': extension,
                            'extension_pct': extension_pct,
                            'break_timestamp': break_idx,
                            'pattern': 'Bullish continuation - momentum through resistance',
                        })
        
        # Check for bearish continuations
        for zone in buyside_zones:
            below_zone = recent_df['close'] < zone.zone_low
            
            if below_zone.any():
                break_idx = recent_df[below_zone].index[0]
                break_bar = recent_df[recent_df.index == break_idx].iloc[0]
                
                bars_after_break = len(recent_df) - recent_df.index.get_loc(break_idx)
                if bars_after_break >= 5:
                    extension = zone.zone_low - recent_df[recent_df.index >= break_idx]['low'].min()
                    extension_pct = (extension / zone.get_zone_width()) * 100
                    
                    if extension_pct > 50:
                        continuations['bearish_continuations'].append({
                            'zone': zone,
                            'break_price': break_bar['close'],
                            'extension': extension,
                            'extension_pct': extension_pct,
                            'break_timestamp': break_idx,
                            'pattern': 'Bearish continuation - momentum through support',
                        })
        
        return continuations


class MultiZoneAnalyzer:
    """Analyze relationships between multiple liquidity zones."""
    
    def __init__(self, detector: LiquidityDetector):
        self.detector = detector
    
    def find_zone_clusters(
        self,
        buyside_zones: List[BuysideLiquidityZone],
        sellside_zones: List[SellsideLiquidityZone],
        cluster_tolerance: float = 0.01,
    ) -> Dict[str, List]:
        """
        Identify clusters of zones in close proximity.
        
        Zones that cluster together = stronger support/resistance.
        """
        clusters = {
            'buyside_clusters': [],
            'sellside_clusters': [],
        }
        
        # Cluster buyside zones
        if buyside_zones:
            zone_prices = [z.get_zone_center() for z in buyside_zones]
            clusters_idx = self._find_clusters(zone_prices, cluster_tolerance)
            
            for cluster_indices in clusters_idx:
                cluster_zones = [buyside_zones[i] for i in cluster_indices]
                avg_price = np.mean([z.get_zone_center() for z in cluster_zones])
                
                clusters['buyside_clusters'].append({
                    'zones': cluster_zones,
                    'center_price': avg_price,
                    'cluster_strength': np.mean([z.total_strength for z in cluster_zones]),
                    'zone_count': len(cluster_zones),
                    'interpretation': 'Strong buyside accumulation',
                })
        
        # Cluster sellside zones
        if sellside_zones:
            zone_prices = [z.get_zone_center() for z in sellside_zones]
            clusters_idx = self._find_clusters(zone_prices, cluster_tolerance)
            
            for cluster_indices in clusters_idx:
                cluster_zones = [sellside_zones[i] for i in cluster_indices]
                avg_price = np.mean([z.get_zone_center() for z in cluster_zones])
                
                clusters['sellside_clusters'].append({
                    'zones': cluster_zones,
                    'center_price': avg_price,
                    'cluster_strength': np.mean([z.total_strength for z in cluster_zones]),
                    'zone_count': len(cluster_zones),
                    'interpretation': 'Strong sellside distribution',
                })
        
        return clusters
    
    def _find_clusters(self, values: List[float], tolerance: float) -> List[List[int]]:
        """Find clusters of similar values within tolerance."""
        if not values:
            return []
        
        sorted_indices = sorted(range(len(values)), key=lambda i: values[i])
        clusters = []
        current_cluster = [sorted_indices[0]]
        
        for i in range(1, len(sorted_indices)):
            idx = sorted_indices[i]
            prev_idx = sorted_indices[i - 1]
            
            distance_pct = abs(values[idx] - values[prev_idx]) / values[prev_idx]
            
            if distance_pct <= tolerance:
                current_cluster.append(idx)
            else:
                if len(current_cluster) > 0:
                    clusters.append(current_cluster)
                current_cluster = [idx]
        
        if current_cluster:
            clusters.append(current_cluster)
        
        return clusters


def example_smart_money_analysis():
    """Example: Analyze smart money order flow patterns."""
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='1h')
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(len(dates)) * 0.1,
        'high': prices + np.abs(np.random.randn(len(dates)) * 0.3),
        'low': prices - np.abs(np.random.randn(len(dates)) * 0.3),
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates)),
    }, index=dates)
    
    # Setup detector
    detector = LiquidityDetector(detection_length=20, mode=LiquidityMode.PRESENT)
    
    # Detect liquidity
    buyside, sellside = detector.detect_liquidity_levels(df)
    buyside_zones = detector.detect_buyside_zones(df, buyside)
    sellside_zones = detector.detect_sellside_zones(df, sellside)
    voids = detector.detect_liquidity_voids(df)
    
    print("=" * 60)
    print("SMART MONEY ORDER FLOW ANALYSIS")
    print("=" * 60)
    
    # Analyze zone strength
    analyzer = SmartMoneyAnalyzer(detector)
    zone_analysis = analyzer.analyze_zone_strength(buyside_zones, sellside_zones)
    
    print("\nTOP BUYSIDE ZONES (Buy Pressure):")
    for analysis in zone_analysis['buyside'][:3]:
        print(f"  Zone: ${analysis['zone'].zone_low:.2f} - ${analysis['zone'].zone_high:.2f}")
        print(f"    Score: {analysis['score']:.3f}, Levels: {analysis['level_count']}")
        print(f"    Strength: {analysis['avg_level_strength']:.1%}")
    
    print("\nTOP SELLSIDE ZONES (Sell Pressure):")
    for analysis in zone_analysis['sellside'][:3]:
        print(f"  Zone: ${analysis['zone'].zone_low:.2f} - ${analysis['zone'].zone_high:.2f}")
        print(f"    Score: {analysis['score']:.3f}, Levels: {analysis['level_count']}")
        print(f"    Strength: {analysis['avg_level_strength']:.1%}")
    
    # Analyze void fills
    print("\nLIQUIDITY VOID ANALYSIS:")
    for void in voids[:3]:
        prediction = analyzer.predict_void_fill_probability(df, void)
        print(f"  {void.void_type.value.upper()} Void: ${void.bottom_price:.2f} - ${void.top_price:.2f}")
        print(f"    Fill Probability: {prediction['fill_probability']:.1%}")
        print(f"    {prediction['prediction']}")
    
    # Detect reversals
    print("\nREVERSAL PATTERNS:")
    reversals = analyzer.detect_reversal_patterns(df, buyside_zones, sellside_zones)
    print(f"  Buyside Bounces: {len(reversals['buyside_bounces'])}")
    print(f"  Sellside Bounces: {len(reversals['sellside_bounces'])}")
    
    # Multi-zone analysis
    print("\nZONE CLUSTERING:")
    multi_analyzer = MultiZoneAnalyzer(detector)
    clusters = multi_analyzer.find_zone_clusters(buyside_zones, sellside_zones)
    print(f"  Buyside Clusters: {len(clusters['buyside_clusters'])}")
    print(f"  Sellside Clusters: {len(clusters['sellside_clusters'])}")


if __name__ == "__main__":
    example_smart_money_analysis()
