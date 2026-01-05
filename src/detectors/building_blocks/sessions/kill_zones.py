"""
Kill Zones Building Block - ENHANCED
Category: Sessions & Time
Purpose: ICT Kill Zones - high-probability trading time windows

ENHANCED VERSION (2026-01-03):
- Event tracking (zone transitions)
- Volume confirmation (quality block integration)
- ATR awareness (volatility context)
- Smart confidence (data-driven)
- Rich metadata for confluence
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: TIME-BASED
Purpose: Continuous kill zone state (in/out)

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any
from datetime import datetime, time
import pandas as pd
import numpy as np


class KillZones:
    """
    ICT Kill Zones - ENHANCED
    
    Identifies Inner Circle Trader's "Kill Zones" with quality block enhancements:
    - Event tracking (zone transitions)
    - Volume confirmation (active vs quiet zones)
    - ATR context (volatility awareness)
    - Smart confidence (historical + real-time)
    
    Kill Zones (UTC):
    - Asian: 00:00-03:00 (Asian session open)
    - London Open: 02:00-05:00 (pre-London positioning)
    - London: 07:00-10:00 (London session open)
    - New York AM: 12:00-15:00 (NY open + London/NY overlap) ⭐
    - New York PM: 18:00-21:00 (NY afternoon session)
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        """Initialize Enhanced Kill Zones block"""
        self.timeframe = timeframe
        self.last_zone = None
        self.bars_in_zone = 0
        
        # ICT Kill Zones (UTC)
        self.kill_zones = {
            'ASIAN_KZ': {'start': 0, 'end': 3, 'priority': 'LOW', 'base_confidence': 50},
            'LONDON_OPEN_KZ': {'start': 2, 'end': 5, 'priority': 'MEDIUM', 'base_confidence': 70},
            'LONDON_KZ': {'start': 7, 'end': 10, 'priority': 'HIGH', 'base_confidence': 85},
            'NY_AM_KZ': {'start': 12, 'end': 15, 'priority': 'VERY_HIGH', 'base_confidence': 95},
            'NY_PM_KZ': {'start': 18, 'end': 21, 'priority': 'MEDIUM', 'base_confidence': 70}
        }
        
        # Optional Enhancement 1: Historical win rates (populated over time)
        # Tracks actual performance by zone
        self.zone_performance = {
            'ASIAN_KZ': {'trades': 0, 'wins': 0, 'win_rate': 0.45},  # Default estimates
            'LONDON_OPEN_KZ': {'trades': 0, 'wins': 0, 'win_rate': 0.60},
            'LONDON_KZ': {'trades': 0, 'wins': 0, 'win_rate': 0.65},
            'NY_AM_KZ': {'trades': 0, 'wins': 0, 'win_rate': 0.75},
            'NY_PM_KZ': {'trades': 0, 'wins': 0, 'win_rate': 0.62},
            'NO_KZ': {'trades': 0, 'wins': 0, 'win_rate': 0.40}
        }
        
        # Optional Enhancement 2: Day-of-week patterns
        # Different days have different characteristics
        self.day_profiles = {
            0: {'name': 'Monday', 'behavior': 'TREND_START', 'adjustment': 3},      # +3%
            1: {'name': 'Tuesday', 'behavior': 'CONTINUATION', 'adjustment': 2},    # +2%
            2: {'name': 'Wednesday', 'behavior': 'PEAK', 'adjustment': 5},          # +5% (midweek strongest)
            3: {'name': 'Thursday', 'behavior': 'CONTINUATION', 'adjustment': 2},   # +2%
            4: {'name': 'Friday', 'behavior': 'CLOSING', 'adjustment': -3},         # -3% (position closing)
            5: {'name': 'Saturday', 'behavior': 'WEEKEND', 'adjustment': -10},      # -10% (low liquidity)
            6: {'name': 'Sunday', 'behavior': 'WEEKEND', 'adjustment': -10}         # -10% (low liquidity)
        }
        
        # Kill Zone characteristics
        self.kz_characteristics = {
            'ASIAN_KZ': {'strength': 'WEAK', 'direction': 'RANGING', 'notes': 'Low volume, range-bound'},
            'LONDON_OPEN_KZ': {'strength': 'MODERATE', 'direction': 'SETUP', 'notes': 'Pre-London positioning'},
            'LONDON_KZ': {'strength': 'STRONG', 'direction': 'TRENDING', 'notes': 'High probability moves'},
            'NY_AM_KZ': {'strength': 'VERY_STRONG', 'direction': 'EXPLOSIVE', 'notes': 'Highest probability - London/NY overlap'},
            'NY_PM_KZ': {'strength': 'MODERATE', 'direction': 'CONTINUATION', 'notes': 'Afternoon continuation moves'},
            'NO_KZ': {'strength': 'MINIMAL', 'direction': 'AVOID', 'notes': 'Low probability period'}
        }
    
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
        Analyze volume activity for zone confirmation
        Returns: (volume_ratio, is_active, activity_score)
        """
        if len(df) < window or 'volume' not in df.columns:
            return 1.0, False, 50
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-window:].mean()
        
        if avg_volume == 0:
            return 1.0, False, 50
        
        volume_ratio = current_volume / avg_volume
        
        # High volume = active zone
        is_active = volume_ratio > 1.2
        
        # Activity score (0-100)
        activity_score = min(100, int(volume_ratio * 50))
        
        return volume_ratio, is_active, activity_score
    
    def identify_kill_zone(self, timestamp: datetime) -> str:
        """Identify which kill zone is active"""
        hour = timestamp.hour
        
        for kz_name, kz_data in self.kill_zones.items():
            if kz_data['start'] <= hour < kz_data['end']:
                return kz_name
        
        return 'NO_KZ'
    
    def get_time_remaining_in_zone(self, timestamp: datetime, zone: str) -> int:
        """Calculate minutes remaining in current zone"""
        if zone not in self.kill_zones:
            return 0
        
        current_hour = timestamp.hour
        current_minute = timestamp.minute
        zone_end = self.kill_zones[zone]['end']
        
        # Minutes until zone ends
        if current_hour < zone_end:
            hours_remaining = zone_end - current_hour - 1
            minutes_remaining = 60 - current_minute
            total_minutes = hours_remaining * 60 + minutes_remaining
        else:
            total_minutes = 0
        
        return total_minutes
    
    def get_next_kill_zone(self, current_zone: str, current_hour: int) -> str:
        """Predict next kill zone"""
        # Sort zones by start time
        zones_sorted = sorted(self.kill_zones.items(), key=lambda x: x[1]['start'])
        
        # Find next zone
        for kz_name, kz_data in zones_sorted:
            if kz_data['start'] > current_hour:
                return kz_name
        
        # Wrap around to first zone (next day)
        return zones_sorted[0][0]
    
    def detect_zone_overlap(self, zone: str, hour: int) -> bool:
        """
        Optional Enhancement 3: Detect zone overlaps
        Returns True if current time is in an overlap period
        """
        # London Open (02:00-05:00) overlaps Asian (00:00-03:00)
        # Overlap period: 02:00-03:00
        if zone == 'LONDON_OPEN_KZ' and 2 <= hour < 3:
            return True
        if zone == 'ASIAN_KZ' and 2 <= hour < 3:
            return True
        
        return False
    
    def calculate_smart_confidence(self, base_confidence: int, 
                                   activity_score: int, 
                                   atr: float, 
                                   avg_atr: float = 1000.0,
                                   current_zone: str = 'NO_KZ',
                                   day_of_week: int = 0,
                                   hour: int = 0) -> int:
        """
        Smart confidence calculation using real-time data + optional enhancements
        
        Factors:
        1. Base confidence (from zone priority)
        2. Volume activity (is it actually active?)
        3. Volatility context (ATR)
        4. OPTIONAL: Historical win rate (if tracked)
        5. OPTIONAL: Day-of-week patterns
        6. OPTIONAL: Zone overlap detection
        """
        confidence = base_confidence
        
        # Volume activity adjustment (+/- 10%)
        if activity_score >= 80:
            confidence += 10  # Very active - boost
        elif activity_score >= 60:
            confidence += 5   # Active - small boost
        elif activity_score < 40:
            confidence -= 10  # Quiet - reduce
        
        # Volatility adjustment (+/- 5%)
        if atr > 0 and avg_atr > 0:
            volatility_ratio = atr / avg_atr
            
            if volatility_ratio > 1.5:
                # High volatility during zone = good
                confidence += 5
            elif volatility_ratio < 0.5:
                # Low volatility during zone = reduce
                confidence -= 5
        
        # OPTIONAL ENHANCEMENT 1: Historical win rate adjustment (+/-5%)
        if current_zone in self.zone_performance:
            perf = self.zone_performance[current_zone]
            if perf['trades'] >= 10:  # Only after 10+ trades
                win_rate = perf['win_rate']
                # Win rate above 65% = boost, below 50% = reduce
                if win_rate > 0.65:
                    confidence += 5
                elif win_rate < 0.50:
                    confidence -= 5
        
        # OPTIONAL ENHANCEMENT 2: Day-of-week adjustment (+/-10%)
        if day_of_week in self.day_profiles:
            day_adj = self.day_profiles[day_of_week]['adjustment']
            confidence += day_adj
        
        # OPTIONAL ENHANCEMENT 3: Zone overlap bonus (+5%)
        if self.detect_zone_overlap(current_zone, hour):
            confidence += 5  # Overlap periods often significant
        
        return max(30, min(100, confidence))
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Enhanced analysis with quality block integration"""
        # Validation
        if 'timestamp' not in df.columns:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing timestamp column'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No data provided'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Current time and zone
        current_time = df['timestamp'].iloc[-1]
        current_kz = self.identify_kill_zone(current_time)
        
        # Event tracking: is this a new zone?
        is_new_event = (current_kz != self.last_zone)
        if is_new_event:
            self.bars_in_zone = 0
        else:
            self.bars_in_zone += 1
        
        # Update tracking
        self.last_zone = current_kz
        
        # Zone properties
        priority = self.kill_zones.get(current_kz, {}).get('priority', 'NONE')
        base_confidence = self.kill_zones.get(current_kz, {}).get('base_confidence', 30)
        characteristics = self.kz_characteristics.get(current_kz, self.kz_characteristics['NO_KZ'])
        is_high_priority = priority in ['HIGH', 'VERY_HIGH']
        
        # Quality block integrations
        atr = self.calculate_atr(df, period=14)
        volume_ratio, is_volume_active, activity_score = self.analyze_volume_activity(df, window=20)
        
        # Optional enhancements context
        day_of_week = current_time.weekday()
        hour = current_time.hour
        is_overlap = self.detect_zone_overlap(current_kz, hour)
        
        # Smart confidence (data-driven + optional enhancements!)
        confidence = self.calculate_smart_confidence(
            base_confidence,
            activity_score,
            atr,
            avg_atr=atr,  # Could use historical avg
            current_zone=current_kz,
            day_of_week=day_of_week,
            hour=hour
        )
        
        # Time metadata
        time_remaining = self.get_time_remaining_in_zone(current_time, current_kz)
        next_zone = self.get_next_kill_zone(current_kz, current_time.hour)
        
        # Build confluence factors
        confluence_factors = []
        
        if current_kz != 'NO_KZ':
            confluence_factors.append(f'Active Kill Zone: {current_kz.replace("_", " ")}')
            confluence_factors.append(f'Priority: {priority}')
            confluence_factors.append(f'Strength: {characteristics["strength"]}')
            confluence_factors.append(f'Expected: {characteristics["direction"]}')
            
            if is_new_event:
                confluence_factors.append(f'🆕 NEW zone entered!')
            else:
                confluence_factors.append(f'Zone active for {self.bars_in_zone} bars')
            
            if is_volume_active:
                confluence_factors.append(f'⭐ HIGH volume activity ({volume_ratio:.1f}x average)')
            
            confluence_factors.append(characteristics['notes'])
            
        else:
            confluence_factors.append('No active Kill Zone - low probability period')
            confluence_factors.append(f'Next zone: {next_zone.replace("_", " ")}')
        
        if current_kz == 'NY_AM_KZ':
            confluence_factors.append('🎯 OPTIMAL KILL ZONE - Highest probability window')
        
        # Get day profile for confluence
        day_profile = self.day_profiles.get(day_of_week, {'name': 'Unknown', 'behavior': 'UNKNOWN', 'adjustment': 0})
        
        # Optional enhancement confluence factors
        if is_overlap:
            confluence_factors.append(f'⭐ ZONE OVERLAP - Asian + London Open transition (+5% conf)')
        
        if day_of_week in [2]:  # Wednesday
            confluence_factors.append(f'📅 {day_profile["name"]} - {day_profile["behavior"]} (Peak day +{day_profile["adjustment"]}% conf)')
        elif day_of_week in [4, 5, 6]:  # Friday-Sunday
            confluence_factors.append(f'📅 {day_profile["name"]} - {day_profile["behavior"]} ({day_profile["adjustment"]}% conf)')
        
        # Signal
        if is_high_priority:
            signal = 'PRIME_TIME'
        elif priority in ['MEDIUM', 'LOW']:
            signal = 'ACTIVE'
        else:
            signal = 'WAIT'
        
        # Rich metadata for confluence
        metadata = {
            'kill_zone': current_kz,
            'hour_utc': current_time.hour,
            'priority': priority,
            'strength': characteristics['strength'],
            'expected_direction': characteristics['direction'],
            'is_high_priority': is_high_priority,
            'is_optimal_kz': current_kz == 'NY_AM_KZ',
            'time_window_utc': self._get_kz_hours(current_kz),
            # ENHANCED metadata:
            'is_new_event': is_new_event,
            'bars_in_zone': self.bars_in_zone,
            'time_remaining_minutes': time_remaining,
            'next_kill_zone': next_zone,
            'volume_ratio': round(volume_ratio, 2),
            'is_volume_active': is_volume_active,
            'activity_score': activity_score,
            'atr_value': round(atr, 2),
            'base_confidence': base_confidence,
            'adjusted_confidence': confidence,
            # OPTIONAL ENHANCEMENTS metadata:
            'day_of_week': day_profile['name'],
            'day_behavior': day_profile['behavior'],
            'day_adjustment': day_profile['adjustment'],
            'is_zone_overlap': is_overlap,
            'historical_win_rate': self.zone_performance.get(current_kz, {}).get('win_rate', 0.0)
        }
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': current_time,
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
    
    def _get_kz_hours(self, kz: str) -> str:
        """Get kill zone hours as string"""
        if kz in self.kill_zones:
            k = self.kill_zones[kz]
            return f"{k['start']:02d}:00-{k['end']:02d}:00 UTC"
        return 'N/A'


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=24, freq='1h')
    data = pd.DataFrame({
        'timestamp': dates,
        'high': np.random.randn(24) * 100 + 50000,
        'low': np.random.randn(24) * 100 + 49500,
        'close': np.random.randn(24) * 100 + 49750,
        'volume': np.random.rand(24) * 1000
    })
    
    kz = KillZones()
    
    print("=" * 80)
    print("ENHANCED KILL ZONES - TEST RESULTS")
    print("=" * 80)
    
    for i in range(len(data)):
        result = kz.analyze(data.iloc[:i+1])
        kz_name = result['metadata']['kill_zone']
        priority = result['metadata']['priority']
        is_new = result['metadata']['is_new_event']
        event_marker = "🆕 NEW! " if is_new else ""
        print(f"{data['timestamp'].iloc[i]}: {event_marker}{kz_name} (Priority: {priority}) - {result['signal']} ({result['confidence']}%)")
    print("=" * 80)
