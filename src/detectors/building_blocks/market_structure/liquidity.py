"""
Liquidity - Building Block
===========================

CONTEXT BLOCK - Detects institutional liquidity zones and events.

Based on LuxAlgo Liquidity and ICT (Inner Circle Trader) concepts:
- Buyside Liquidity: Where short sellers accumulate stops (potential bounce zones)
- Sellside Liquidity: Where long traders accumulate stops (potential reversal zones)
- Liquidity Voids: Rapid price movements indicating aggressive institutional action
- Zone Breaches: When price breaks through liquidity zones (momentum signals)

Signals:
- BUYSIDE_ZONE_TOUCH: Price testing buyside liquidity (potential long)
- SELLSIDE_ZONE_TOUCH: Price testing sellside liquidity (potential short)
- VOID_DETECTED: New liquidity void identified
- BUYSIDE_BREACH: Bearish break below buyside
- SELLSIDE_BREACH: Bullish break above sellside
- NEAR_BUYSIDE: Approaching buyside zone
- NEAR_SELLSIDE: Approaching sellside zone
- NEUTRAL: No significant liquidity event

Based on LuxAlgo Liquidity concept, adapted for BTC_Engine_v3 framework.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional, Tuple

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class LiquidityZone:
    """Represents a liquidity zone."""
    zone_type: str  # 'buyside' or 'sellside'
    high: float
    low: float
    center: float
    strength: float
    first_seen: datetime
    touch_count: int
    breached: bool
    
    def contains_price(self, price: float) -> bool:
        """Check if price is within zone."""
        return self.low <= price <= self.high
    
    def get_width(self) -> float:
        """Get zone width."""
        return self.high - self.low


@register_block(
    name='liquidity',
    category='MARKET_STRUCTURE',
    class_name='Liquidity',
    default_weight=15,
    valid_signals=[
        # Zone Touch Events (highest value) - GRANULAR
        'BUYSIDE_ZONE_TOUCH', 'SELLSIDE_ZONE_TOUCH',
        # Breach Events (momentum) - GRANULAR
        'BUYSIDE_BREACH', 'SELLSIDE_BREACH',
        # Void Detection - GRANULAR
        'VOID_DETECTED',
        # Proximity Signals - GRANULAR
        'NEAR_BUYSIDE', 'NEAR_SELLSIDE',
        # Simple directional signals - SIMPLE for basic users
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Zone touches - Institutional reversal zones (highest value)
        'BUYSIDE_ZONE_TOUCH': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Price touching buyside liquidity - potential bounce/reversal up'
        },
        'SELLSIDE_ZONE_TOUCH': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Price touching sellside liquidity - potential reversal down'
        },
        
        # Breaches - Momentum continuation
        'BUYSIDE_BREACH': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bearish breach below buyside - stop hunt complete'
        },
        'SELLSIDE_BREACH': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bullish breach above sellside - stop hunt complete'
        },
        
        # Void - Aggressive institutional move
        'VOID_DETECTED': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Liquidity void detected - rapid price movement'
        },
        
        # Proximity - Approaching zones
        'NEAR_BUYSIDE': {
            'base_points': 12,
            'formula': 'scaled',
            'description': 'Approaching buyside liquidity zone'
        },
        'NEAR_SELLSIDE': {
            'base_points': 12,
            'formula': 'scaled',
            'description': 'Approaching sellside liquidity zone'
        },
        
        # Neutral - Between zones
        'NEUTRAL': {
            'base_points': 5,
            'formula': 'scaled',
            'description': 'Between liquidity zones - no clear setup'
        },
        
        # Simple directional signals - SIMPLE for basic users
        'BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish liquidity setup - any event (simple)'
        },
        'BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish liquidity setup - any event (simple)'
        },
        
        # Status
        'ERROR': {
            'points': 0,
            'description': 'Analysis error occurred'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'description': 'Not enough data for analysis'
        }
    },
    description='Liquidity - ICT/LuxAlgo institutional liquidity zones (buyside/sellside stops, voids, breaches)',
    tags=['market_structure', 'liquidity', 'ict', 'luxalgo', 'institutional', 'stop_hunt', 'context_block']
)
class Liquidity:
    """
    Liquidity Detector
    
    Building Block Classification: CONTEXT BLOCK
    Mode: ALWAYS ACTIVE (provides market structure continuously)
    
    Detects institutional liquidity accumulation zones where smart money
    hunts stop-losses before major moves.
    
    Designed for 15-min bars.
    """
    
    def __init__(
        self,
        timeframe: str = '15min',
        detection_length: int = 20,  # Lookback for swing detection
        zone_margin: float = 0.003,  # 0.3% zone width
        min_touches: int = 2,  # Minimum touches to confirm zone
        proximity_pct: float = 0.01,  # 1% to be "near" a zone
        void_threshold: float = 0.005,  # 0.5% minimum void size
        **kwargs
    ):
        """
        Initialize Liquidity detector.
        
        Args:
            timeframe: Timeframe (e.g., '15min')
            detection_length: Lookback period for swing detection
            zone_margin: Zone width as % of price
            min_touches: Minimum touches to confirm liquidity level
            proximity_pct: Distance threshold for "near" signals
            void_threshold: Minimum void size as % of price
        """
        self.timeframe = timeframe
        self.detection_length = detection_length
        self.zone_margin = zone_margin
        self.min_touches = min_touches
        self.proximity_pct = proximity_pct
        self.void_threshold = void_threshold
        
        # State tracking
        self.buyside_zones: List[LiquidityZone] = []
        self.sellside_zones: List[LiquidityZone] = []
        self.last_void_check: Optional[datetime] = None
    
    def _determine_dual_signals(self, granular_signal: str, direction: str = None) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if granular in ['BUYSIDE_ZONE_TOUCH', 'SELLSIDE_BREACH']:
            simple = 'BULLISH'
        elif granular in ['SELLSIDE_ZONE_TOUCH', 'BUYSIDE_BREACH']:
            simple = 'BEARISH'
        elif granular == 'VOID_DETECTED' and direction:
            simple = 'BULLISH' if direction == 'BULLISH' else 'BEARISH'
        else:
            simple = 'NEUTRAL'
        return granular, simple
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for liquidity zones and events.
        
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
        
        if len(df) < self.detection_length * 2:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.detection_length * 2} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_time = df['timestamp'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Detect liquidity zones
        self._detect_zones(df)
        
        # Check for void
        void_info = self._check_for_void(df)
        
        # Determine current state relative to zones
        return self._generate_signal(df, current_time, current_price, void_info)
    
    def _detect_zones(self, df: pd.DataFrame) -> None:
        """Detect buyside and sellside liquidity zones."""
        # Use recent data for zone detection
        recent_df = df.tail(min(200, len(df)))
        
        buyside_levels = []
        sellside_levels = []
        
        # Find swing highs and lows
        for i in range(self.detection_length, len(recent_df) - self.detection_length):
            window_start = i - self.detection_length
            window_end = i + self.detection_length + 1
            window = recent_df.iloc[window_start:window_end]
            current = recent_df.iloc[i]
            
            # Swing high (sellside liquidity)
            if current['high'] == window['high'].max():
                level_price = current['high']
                touches = self._count_touches(recent_df, level_price, is_high=True)
                
                if touches >= self.min_touches:
                    strength = min(touches / 5.0, 1.0)  # Normalize
                    sellside_levels.append({
                        'price': level_price,
                        'strength': strength,
                        'touches': touches,
                        'timestamp': current['timestamp']
                    })
            
            # Swing low (buyside liquidity)
            if current['low'] == window['low'].min():
                level_price = current['low']
                touches = self._count_touches(recent_df, level_price, is_high=False)
                
                if touches >= self.min_touches:
                    strength = min(touches / 5.0, 1.0)
                    buyside_levels.append({
                        'price': level_price,
                        'strength': strength,
                        'touches': touches,
                        'timestamp': current['timestamp']
                    })
        
        # Create zones from levels
        self.buyside_zones = self._cluster_into_zones(buyside_levels, 'buyside')
        self.sellside_zones = self._cluster_into_zones(sellside_levels, 'sellside')
    
    def _count_touches(self, df: pd.DataFrame, level_price: float, is_high: bool) -> int:
        """Count how many times price touched a level."""
        tolerance = level_price * self.zone_margin
        
        if is_high:
            touches = df[(df['high'] >= level_price - tolerance) & 
                        (df['high'] <= level_price + tolerance)]
        else:
            touches = df[(df['low'] >= level_price - tolerance) & 
                        (df['low'] <= level_price + tolerance)]
        
        return len(touches)
    
    def _cluster_into_zones(self, levels: List[Dict], zone_type: str) -> List[LiquidityZone]:
        """Cluster nearby levels into zones."""
        if not levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x['price'])
        
        zones = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if level is close to current cluster
            cluster_center = np.mean([l['price'] for l in current_cluster])
            distance_pct = abs(level['price'] - cluster_center) / cluster_center
            
            if distance_pct <= self.zone_margin * 3:  # Clustering tolerance
                current_cluster.append(level)
            else:
                # Create zone from current cluster
                if current_cluster:
                    zone = self._create_zone(current_cluster, zone_type)
                    zones.append(zone)
                current_cluster = [level]
        
        # Create final zone
        if current_cluster:
            zone = self._create_zone(current_cluster, zone_type)
            zones.append(zone)
        
        return zones
    
    def _create_zone(self, levels: List[Dict], zone_type: str) -> LiquidityZone:
        """Create a LiquidityZone from clustered levels."""
        prices = [l['price'] for l in levels]
        center = np.mean(prices)
        
        # Zone bounds
        zone_width = center * self.zone_margin
        low = center - zone_width
        high = center + zone_width
        
        # Aggregate strength
        total_strength = sum(l['strength'] for l in levels) / len(levels)
        total_touches = sum(l['touches'] for l in levels)
        
        return LiquidityZone(
            zone_type=zone_type,
            high=high,
            low=low,
            center=center,
            strength=total_strength,
            first_seen=min(l['timestamp'] for l in levels),
            touch_count=total_touches,
            breached=False
        )
    
    def _check_for_void(self, df: pd.DataFrame) -> Optional[Dict]:
        """Check for liquidity voids (large candles with small wicks)."""
        recent = df.tail(10)
        
        for i in range(len(recent)):
            row = recent.iloc[i]
            
            body = abs(row['close'] - row['open'])
            total_range = row['high'] - row['low']
            
            if total_range == 0:
                continue
            
            body_pct = body / total_range
            void_size = total_range
            void_size_pct = void_size / row['close']
            
            # Large body, small wicks = aggressive move = void
            if body_pct > 0.75 and void_size_pct > self.void_threshold:
                return {
                    'detected': True,
                    'size': void_size,
                    'size_pct': void_size_pct * 100,
                    'direction': 'BULLISH' if row['close'] > row['open'] else 'BEARISH',
                    'timestamp': row['timestamp'],
                    'price_range': (row['low'], row['high'])
                }
        
        return None
    
    def _generate_signal(
        self, df: pd.DataFrame, timestamp: datetime, price: float, void_info: Optional[Dict]
    ) -> Dict[str, Any]:
        """Generate signal based on current price relative to zones."""
        # Check for void first (priority signal)
        if void_info and void_info.get('detected'):
            return self._generate_void_signal(timestamp, price, void_info)
        
        # Find nearest buyside and sellside zones
        nearest_buyside = self._find_nearest_zone(price, self.buyside_zones)
        nearest_sellside = self._find_nearest_zone(price, self.sellside_zones)
        
        # Check buyside interactions
        if nearest_buyside:
            if nearest_buyside.contains_price(price):
                return self._generate_buyside_touch_signal(timestamp, price, nearest_buyside)
            elif price < nearest_buyside.low:
                return self._generate_buyside_breach_signal(timestamp, price, nearest_buyside)
            elif self._is_near_zone(price, nearest_buyside):
                return self._generate_near_buyside_signal(timestamp, price, nearest_buyside)
        
        # Check sellside interactions
        if nearest_sellside:
            if nearest_sellside.contains_price(price):
                return self._generate_sellside_touch_signal(timestamp, price, nearest_sellside)
            elif price > nearest_sellside.high:
                return self._generate_sellside_breach_signal(timestamp, price, nearest_sellside)
            elif self._is_near_zone(price, nearest_sellside):
                return self._generate_near_sellside_signal(timestamp, price, nearest_sellside)
        
        # Neutral - between zones
        return self._generate_neutral_signal(timestamp, price, nearest_buyside, nearest_sellside)
    
    def _find_nearest_zone(self, price: float, zones: List[LiquidityZone]) -> Optional[LiquidityZone]:
        """Find nearest zone to current price."""
        if not zones:
            return None
        
        nearest = min(zones, key=lambda z: abs(z.center - price))
        return nearest
    
    def _is_near_zone(self, price: float, zone: LiquidityZone) -> bool:
        """Check if price is near a zone."""
        distance = abs(price - zone.center)
        threshold = zone.center * self.proximity_pct
        return distance <= threshold and not zone.contains_price(price)
    
    def _generate_void_signal(self, timestamp: datetime, price: float, void_info: Dict) -> Dict[str, Any]:
        """Generate void detection signal."""
        # Determine void fill potential based on size
        void_size_pct = void_info['size_pct']
        if void_size_pct < 0.5:
            void_fill_potential = 'HIGH'
        elif void_size_pct < 1.0:
            void_fill_potential = 'MEDIUM'
        else:
            void_fill_potential = 'LOW'
        
        granular_signal, simple_signal = self._determine_dual_signals('VOID_DETECTED', void_info['direction'])
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 70,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'void_direction': void_info['direction'],
                'void_size': round(void_info['size'], 2),
                'void_size_pct': round(void_info['size_pct'], 2),
                'void_range_low': round(void_info['price_range'][0], 2),
                'void_range_high': round(void_info['price_range'][1], 2),
                'void_fill_potential': void_fill_potential,
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'{void_info["direction"]} void detected',
                f'Size: {void_info["size_pct"]:.1f}% of price',
                'Aggressive institutional move',
            ]
        }
    
    def _generate_buyside_touch_signal(
        self, timestamp: datetime, price: float, zone: LiquidityZone
    ) -> Dict[str, Any]:
        """Generate signal when price touches buyside zone."""
        granular_signal, simple_signal = self._determine_dual_signals('BUYSIDE_ZONE_TOUCH')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 60 + int(zone.strength * 15),
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'zone_center': round(zone.center, 2),
                'zone_high': round(zone.high, 2),
                'zone_low': round(zone.low, 2),
                'zone_strength': round(zone.strength * 100, 1),
                'zone_strength_pct': round(zone.strength * 100, 1),  # Fine-grained filtering
                'touch_count': zone.touch_count,
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Price in buyside zone: {zone.center:.2f}',
                f'Zone strength: {zone.strength*100:.0f}%',
                f'Previous touches: {zone.touch_count}',
                'Potential bounce/reversal up',
            ]
        }
    
    def _generate_sellside_touch_signal(
        self, timestamp: datetime, price: float, zone: LiquidityZone
    ) -> Dict[str, Any]:
        """Generate signal when price touches sellside zone."""
        granular_signal, simple_signal = self._determine_dual_signals('SELLSIDE_ZONE_TOUCH')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 60 + int(zone.strength * 15),
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'zone_center': round(zone.center, 2),
                'zone_high': round(zone.high, 2),
                'zone_low': round(zone.low, 2),
                'zone_strength': round(zone.strength * 100, 1),
                'zone_strength_pct': round(zone.strength * 100, 1),  # Fine-grained filtering
                'touch_count': zone.touch_count,
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Price in sellside zone: {zone.center:.2f}',
                f'Zone strength: {zone.strength*100:.0f}%',
                f'Previous touches: {zone.touch_count}',
                'Potential reversal down',
            ]
        }
    
    def _generate_buyside_breach_signal(
        self, timestamp: datetime, price: float, zone: LiquidityZone
    ) -> Dict[str, Any]:
        """Generate signal when price breaks below buyside."""
        distance = zone.low - price
        granular_signal, simple_signal = self._determine_dual_signals('BUYSIDE_BREACH')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 70,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'zone_center': round(zone.center, 2),
                'breach_distance': round(distance, 2),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Bearish breach below {zone.center:.2f}',
                f'Excess: {distance:.2f}',
                'Stop hunt complete',
            ]
        }
    
    def _generate_sellside_breach_signal(
        self, timestamp: datetime, price: float, zone: LiquidityZone
    ) -> Dict[str, Any]:
        """Generate signal when price breaks above sellside."""
        distance = price - zone.high
        granular_signal, simple_signal = self._determine_dual_signals('SELLSIDE_BREACH')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 70,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'zone_center': round(zone.center, 2),
                'breach_distance': round(distance, 2),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Bullish breach above {zone.center:.2f}',
                f'Excess: {distance:.2f}',
                'Stop hunt complete',
            ]
        }
    
    def _generate_near_buyside_signal(
        self, timestamp: datetime, price: float, zone: LiquidityZone
    ) -> Dict[str, Any]:
        """Generate signal when approaching buyside zone."""
        distance = abs(price - zone.center)
        granular_signal, simple_signal = self._determine_dual_signals('NEAR_BUYSIDE')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 55,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'zone_center': round(zone.center, 2),
                'distance': round(distance, 2),
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Approaching buyside at {zone.center:.2f}',
                f'Distance: {distance:.2f}',
            ]
        }
    
    def _generate_near_sellside_signal(
        self, timestamp: datetime, price: float, zone: LiquidityZone
    ) -> Dict[str, Any]:
        """Generate signal when approaching sellside zone."""
        distance = abs(price - zone.center)
        granular_signal, simple_signal = self._determine_dual_signals('NEAR_SELLSIDE')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 55,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'zone_center': round(zone.center, 2),
                'distance': round(distance, 2),
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Approaching sellside at {zone.center:.2f}',
                f'Distance: {distance:.2f}',
            ]
        }
    
    def _generate_neutral_signal(
        self,
        timestamp: datetime,
        price: float,
        nearest_buyside: Optional[LiquidityZone],
        nearest_sellside: Optional[LiquidityZone]
    ) -> Dict[str, Any]:
        """Generate neutral signal when between zones."""
        granular_signal, simple_signal = self._determine_dual_signals('NEUTRAL')
        
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'buyside_zones': len(self.buyside_zones),
            'sellside_zones': len(self.sellside_zones),
            'is_new_event': False,
        }
        
        if nearest_buyside:
            metadata['nearest_buyside'] = round(nearest_buyside.center, 2)
        if nearest_sellside:
            metadata['nearest_sellside'] = round(nearest_sellside.center, 2)
        
        factors = [
            f'Between liquidity zones',
            f'Buyside zones: {len(self.buyside_zones)}',
            f'Sellside zones: {len(self.sellside_zones)}',
        ]
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 50,
            'metadata': metadata,
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': factors
        }


if __name__ == "__main__":
    print("Liquidity - Building Block")
    print("CONTEXT BLOCK - Detects institutional liquidity zones")
    print("Based on LuxAlgo/ICT methodology")
