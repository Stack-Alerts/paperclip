"""
Supply & Demand Zones Building Block - ENHANCED
Category: Supply/Demand & Fibonacci
Purpose: Identifies institutional accumulation/distribution zones

ENHANCED VERSION (2026-01-03):
- Real zone detection (base + explosion pattern)
- Quality block integration (ATR + Volume + Swing Points)
- Event tracking (zone formation, tests, breaks)
- Smart confidence (strength-based)
- Zone management (track multiple zones)

INSTITUTIONAL DEFINITION:
- DEMAND Zone: Consolidation base → Explosive UP move (left buy imbalance)
- SUPPLY Zone: Consolidation base → Explosive DOWN move (left sell imbalance)
- Zone = The BASE area (not current price proximity!)
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: Zone detection, fires when zones form

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from src.utils.advanced_data_loader import advanced_data


class SupplyDemandZones:
    """
    Enhanced Supply & Demand Zone Detector
    
    Real institutional zones require:
    1. Base (consolidation): 3+ bars, tight range
    2. Explosion: Strong directional move FROM base
    3. Zone tracking: Fresh zones, tests, breaks
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
        self.zones = []  # Active zones
        self.max_zones = 5  # Track 5 most recent zones (increased for better coverage)
        self.zone_lookback = 50  # Bars to look for zones
        self.last_swing_high = None
        self.last_swing_low = None
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR for volatility awareness (quality block integration)"""
        if len(df) < period + 1:
            return 0.0
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1])
            )
        )
        
        atr = np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)
        return float(atr)
    
    def analyze_volume_activity(self, df: pd.DataFrame, window: int = 20) -> tuple:
        """
        Analyze volume for institutional activity detection
        Returns: (volume_ratio, is_spike, volume_score)
        """
        if len(df) < window or 'volume' not in df.columns:
            return 1.0, False, 50
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-window:].mean()
        
        if avg_volume == 0:
            return 1.0, False, 50
        
        volume_ratio = current_volume / avg_volume
        
        # Volume spike = institutional activity
        is_spike = volume_ratio > 1.5
        
        # Volume score (0-100)
        volume_score = min(100, int(volume_ratio * 50))
        
        return volume_ratio, is_spike, volume_score
    
    def find_consolidation_bases(self, df: pd.DataFrame, atr: float, lookback: int = 50) -> List[Dict]:
        """
        Find consolidation bases (potential zones)
        
        Criteria:
        - 3+ consecutive bars
        - Range < 0.5 * ATR (tight consolidation)
        - Relatively flat (low volatility)
        """
        if len(df) < lookback or atr == 0:
            return []
        
        bases = []
        recent_df = df.iloc[-lookback:]
        
        i = 0
        while i < len(recent_df) - 3:
            # Check 3-bar window
            window = recent_df.iloc[i:i+3]
            high = window['high'].max()
            low = window['low'].min()
            range_size = high - low
            
            # Consolidation = range < 0.5 * ATR
            if range_size < 0.5 * atr:
                # Found potential base
                bases.append({
                    'start_idx': i,
                    'end_idx': i + 2,
                    'high': high,
                    'low': low,
                    'range': range_size,
                    'bars': 3
                })
                i += 3  # Skip past this base
            else:
                i += 1
        
        return bases
    
    def detect_explosive_moves(self, df: pd.DataFrame, bases: List[Dict], atr: float) -> List[Dict]:
        """
        Detect explosive moves FROM consolidation bases
        
        Criteria:
        - Strong directional move (> 2.0 * ATR)
        - Volume spike (> 1.5x average)
        - Happens immediately after base
        """
        zones = []
        
        for base in bases:
            base_end = base['end_idx']
            
            # Check next 5 bars for explosion
            if base_end + 5 >= len(df):
                continue
            
            explosion_window = df.iloc[base_end+1:base_end+6]
            
            # Calculate move from base
            base_price = (base['high'] + base['low']) / 2
            
            for idx, bar in explosion_window.iterrows():
                move_up = bar['high'] - base_price
                move_down = base_price - bar['low']
                
                # Check for explosive upward move (DEMAND zone)
                if move_up > 2.0 * atr:
                    # Check volume at explosion
                    explosion_idx = df.index.get_loc(idx)
                    volume_ratio, is_spike, volume_score = self.analyze_volume_activity(
                        df.iloc[:explosion_idx+1], window=20
                    )
                    
                    if is_spike or volume_ratio > 1.3:
                        zones.append({
                            'type': 'DEMAND',
                            'high': base['high'],
                            'low': base['low'],
                            'mid': base_price,
                            'strength': min(100, int(move_up / atr * 30)),
                            'volume_score': volume_score,
                            'formation_bar': explosion_idx,
                            'tests': 0,
                            'broken': False,
                            'age': 0
                        })
                        break
                
                # Check for explosive downward move (SUPPLY zone)
                elif move_down > 2.0 * atr:
                    explosion_idx = df.index.get_loc(idx)
                    volume_ratio, is_spike, volume_score = self.analyze_volume_activity(
                        df.iloc[:explosion_idx+1], window=20
                    )
                    
                    if is_spike or volume_ratio > 1.3:
                        zones.append({
                            'type': 'SUPPLY',
                            'high': base['high'],
                            'low': base['low'],
                            'mid': base_price,
                            'strength': min(100, int(move_down / atr * 30)),
                            'volume_score': volume_score,
                            'formation_bar': explosion_idx,
                            'tests': 0,
                            'broken': False,
                            'age': 0
                        })
                        break
        
        return zones
    
    def update_zone_status(self, zones: List[Dict], current_price: float, current_idx: int) -> None:
        """Update zone status (tests, breaks, age)"""
        for zone in zones:
            # Update age
            zone['age'] = current_idx - zone['formation_bar']
            
            # Check if price tested zone
            in_zone = zone['low'] <= current_price <= zone['high']
            
            if in_zone:
                zone['tests'] += 1
            
            # Check if zone broken
            if zone['type'] == 'DEMAND' and current_price < zone['low']:
                zone['broken'] = True
            elif zone['type'] == 'SUPPLY' and current_price > zone['high']:
                zone['broken'] = True
    
    def calculate_zone_confidence(self, zone: Dict, distance: float, atr: float, in_zone: bool = False) -> int:
        """
        Enhanced smart confidence calculation for better variation
        
        Factors:
        1. Zone strength (volume at formation) - wider range
        2. Zone age (fresh better) - more nuanced
        3. Zone tests (untested stronger) - graduated
        4. Distance (closer higher) - continuous
        5. In zone boost
        6. Zone type bias correction
        """
        confidence = 45  # Lower base for more range
        
        # Strength factor (+0-25) - ENHANCED for more variation
        if zone['strength'] >= 80:
            strength_bonus = 25
        elif zone['strength'] >= 60:
            strength_bonus = 20
        elif zone['strength'] >= 40:
            strength_bonus = 15
        elif zone['strength'] >= 20:
            strength_bonus = 10
        else:
            strength_bonus = 5
        confidence += strength_bonus
        
        # Volume factor (+0-18) - ENHANCED scaling
        if zone['volume_score'] >= 90:
            volume_bonus = 18
        elif zone['volume_score'] >= 75:
            volume_bonus = 15
        elif zone['volume_score'] >= 60:
            volume_bonus = 12
        elif zone['volume_score'] >= 45:
            volume_bonus = 8
        else:
            volume_bonus = 4
        confidence += volume_bonus
        
        # Age factor (+0-12) - MORE NUANCED
        if zone['age'] < 10:
            age_bonus = 12  # Very fresh
        elif zone['age'] < 20:
            age_bonus = 9  # Fresh
        elif zone['age'] < 40:
            age_bonus = 6  # Relatively fresh
        elif zone['age'] < 60:
            age_bonus = 3  # Getting old
        else:
            age_bonus = 0  # Old zone
        confidence += age_bonus
        
        # Test factor (+0-12) - GRADUATED
        if zone['tests'] == 0:
            test_bonus = 12  # Untested = strongest
        elif zone['tests'] == 1:
            test_bonus = 8  # One test = still very good
        elif zone['tests'] == 2:
            test_bonus = 4  # Two tests = okay
        else:
            test_bonus = 0  # Multiple tests = weaker
        confidence += test_bonus
        
        # Distance factor (+0-12) - CONTINUOUS
        if atr > 0 and distance < atr * 2:
            distance_ratio = distance / atr
            if distance_ratio < 0.3:
                distance_bonus = 12  # Very close
            elif distance_ratio < 0.6:
                distance_bonus = 10  # Close
            elif distance_ratio < 1.0:
                distance_bonus = 7  # Near
            elif distance_ratio < 1.5:
                distance_bonus = 4  # Approaching
            else:
                distance_bonus = 2  # Within range
            confidence += distance_bonus
        
        # In zone boost (+8)
        if in_zone and distance == 0:
            confidence += 8  # Inside zone = boost
        
        # Zone type balance correction
        # DEMAND zones slightly boosted to improve balance
        if zone['type'] == 'DEMAND':
            confidence += 3  # Small boost for demand
        
        # Broken penalty
        if zone['broken']:
            confidence -= 25
        
        return max(40, min(95, confidence))
    

    def check_zone_liquidation_strength(self, zone_price: float, df: pd.DataFrame) -> Dict:
        """Check if liquidation clusters strengthen this zone"""
        try:
            levels = advanced_data.get_liquidation_levels(df, lookback_bars=200)
            
            # Check for liquidation clusters near zone
            cluster_strength = 0
            for cluster in levels['above'] + levels['below']:
                distance = abs(cluster['price'] - zone_price) / zone_price
                if distance < 0.02:  # Within 2%
                    cluster_strength += cluster['volume']
            
            if cluster_strength > 0:
                return {
                    'has_clusters': True,
                    'cluster_strength': cluster_strength,
                    'confidence_boost': min(20, int(cluster_strength / 100)),
                    'zone_type': 'INSTITUTIONAL'
                }
            return {'has_clusters': False, 'confidence_boost': 0}
        except:
            return {'has_clusters': False, 'confidence_boost': 0}

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Enhanced analysis with quality block integration"""
        # Validation
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 50:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 50 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_time = df['timestamp'].iloc[-1]
        current_price = df['close'].iloc[-1]
        current_idx = len(df) - 1
        
        # Quality block integration
        atr = self.calculate_atr(df, period=14)
        
        # Find zones periodically (every 10 bars to avoid heavy computation)
        if current_idx % 10 == 0 or len(self.zones) == 0:
            # Find consolidation bases
            bases = self.find_consolidation_bases(df, atr, lookback=self.zone_lookback)
            
            # Detect explosive moves from bases
            new_zones = self.detect_explosive_moves(df, bases, atr)
            
            # Add new zones (keep only recent ones)
            self.zones.extend(new_zones)
            
            # Sort by formation time (most recent first)
            self.zones.sort(key=lambda x: x['formation_bar'], reverse=True)
            
            # Keep only max_zones
            self.zones = self.zones[:self.max_zones]
        
        # Update zone status
        self.update_zone_status(self.zones, current_price, current_idx)
        
        # Remove broken zones
        self.zones = [z for z in self.zones if not z['broken']]
        
        # Find closest active zone
        closest_zone = None
        min_distance = float('inf')
        
        for zone in self.zones:
            # Distance to zone
            if current_price > zone['high']:
                distance = current_price - zone['high']
            elif current_price < zone['low']:
                distance = zone['low'] - current_price
            else:
                distance = 0  # Inside zone
            
            if distance < min_distance:
                min_distance = distance
                closest_zone = zone
        
        # Generate signal
        if closest_zone is None:
            signal = 'NO_ZONE'
            confidence = 50
            confluence_factors = ['No active zones detected']
            zone_type = 'NONE'
            is_new_event = False
        else:
            zone_type = closest_zone['type']
            
            # Check if touching zone
            in_zone = closest_zone['low'] <= current_price <= closest_zone['high']
            
            if in_zone:
                # Inside zone
                if zone_type == 'DEMAND':
                    signal = 'DEMAND_ZONE'
                    confluence_factors = [
                        f'Inside DEMAND zone (${closest_zone["low"]:.2f}-${closest_zone["high"]:.2f})',
                        f'Zone strength: {closest_zone["strength"]}/100',
                        f'Zone age: {closest_zone["age"]} bars',
                        f'Tests: {closest_zone["tests"]}'
                    ]
                else:
                    signal = 'SUPPLY_ZONE'
                    confluence_factors = [
                        f'Inside SUPPLY zone (${closest_zone["low"]:.2f}-${closest_zone["high"]:.2f})',
                        f'Zone strength: {closest_zone["strength"]}/100',
                        f'Zone age: {closest_zone["age"]} bars',
                        f'Tests: {closest_zone["tests"]}'
                    ]
                
                # Calculate confidence
                confidence = self.calculate_zone_confidence(closest_zone, 0, atr, in_zone=True)
                is_new_event = closest_zone['tests'] == 1  # First test
                
            else:
                # Near zone
                if min_distance < atr:
                    if zone_type == 'DEMAND':
                        signal = 'NEAR_DEMAND'
                    else:
                        signal = 'NEAR_SUPPLY'
                    
                    confidence = self.calculate_zone_confidence(closest_zone, min_distance, atr)
                    confluence_factors = [
                        f'Approaching {zone_type} zone',
                        f'Distance: {min_distance:.2f} (within ATR)',
                        f'Zone strength: {closest_zone["strength"]}/100'
                    ]
                    is_new_event = False
                else:
                    signal = 'NO_ZONE'
                    confidence = 55
                    confluence_factors = ['Far from zones']
                    is_new_event = False
        
        # Metadata
        metadata = {
            'zone_type': zone_type,
            'active_zones': len(self.zones),
            'atr_value': round(atr, 2),
            'is_new_event': is_new_event
        }
        
        if closest_zone:
            metadata.update({
                'zone_high': round(closest_zone['high'], 2),
                'zone_low': round(closest_zone['low'], 2),
                'zone_strength': closest_zone['strength'],
                'zone_tests': closest_zone['tests'],
                'zone_age': closest_zone['age'],
                'distance_to_zone': round(min_distance, 2)
            })
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': current_time,
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    print("=" * 80)
    print("ENHANCED SUPPLY/DEMAND ZONES - TEST")
    print("=" * 80)
    print("Looking for: Consolidation → Explosion pattern")
    print("DEMAND: Tight range → Explosive UP move")
    print("SUPPLY: Tight range → Explosive DOWN move")
    print("=" * 80)
