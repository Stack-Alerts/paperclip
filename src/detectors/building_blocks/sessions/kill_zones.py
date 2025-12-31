"""
Kill Zones Building Block
Category: Sessions & Time
Purpose: ICT Kill Zones - high-probability trading time windows
"""

from typing import Dict, Any
from datetime import datetime, time
import pandas as pd


class KillZones:
    """
    ICT Kill Zones
    
    Identifies Inner Circle Trader's "Kill Zones" - specific time windows
    with highest institutional activity and price movement probability.
    
    Kill Zones (UTC):
    - Asian: 00:00-03:00 (Asian session open)
    - London Open: 02:00-05:00 (pre-London positioning)
    - London: 07:00-10:00 (London session open)
    - New York AM: 12:00-15:00 (NY open + London/NY overlap)
    - New York PM: 18:00-21:00 (NY afternoon session)
    
    These are optimal times for trade entries with highest probability.
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        """Initialize Kill Zones block"""
        self.timeframe = timeframe
        
        # ICT Kill Zones (UTC)
        self.kill_zones = {
            'ASIAN_KZ': {'start': 0, 'end': 3, 'priority': 'LOW'},
            'LONDON_OPEN_KZ': {'start': 2, 'end': 5, 'priority': 'MEDIUM'},
            'LONDON_KZ': {'start': 7, 'end': 10, 'priority': 'HIGH'},
            'NY_AM_KZ': {'start': 12, 'end': 15, 'priority': 'VERY_HIGH'},
            'NY_PM_KZ': {'start': 18, 'end': 21, 'priority': 'MEDIUM'}
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
    
    def identify_kill_zone(self, timestamp: datetime) -> str:
        """Identify which kill zone is active"""
        hour = timestamp.hour
        
        for kz_name, kz_data in self.kill_zones.items():
            if kz_data['start'] <= hour < kz_data['end']:
                return kz_name
        
        return 'NO_KZ'
    
    def get_kill_zone_priority(self, kz: str) -> str:
        """Get priority level of kill zone"""
        if kz in self.kill_zones:
            return self.kill_zones[kz]['priority']
        return 'NONE'
    
    def is_high_priority_kz(self, kz: str) -> bool:
        """Check if this is a high-priority kill zone"""
        priority = self.get_kill_zone_priority(kz)
        return priority in ['HIGH', 'VERY_HIGH']
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
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
        
        current_time = df['timestamp'].iloc[-1]
        current_kz = self.identify_kill_zone(current_time)
        priority = self.get_kill_zone_priority(current_kz)
        characteristics = self.kz_characteristics.get(current_kz, self.kz_characteristics['NO_KZ'])
        is_high_priority = self.is_high_priority_kz(current_kz)
        
        # Calculate confidence
        confidence_map = {
            'VERY_HIGH': 95,
            'HIGH': 85,
            'MEDIUM': 70,
            'LOW': 50,
            'NONE': 30
        }
        confidence = confidence_map.get(priority, 30)
        
        # Build confluence factors
        confluence_factors = []
        
        if current_kz != 'NO_KZ':
            confluence_factors.append(f'Active Kill Zone: {current_kz.replace("_", " ")}')
            confluence_factors.append(f'Priority: {priority}')
            confluence_factors.append(f'Strength: {characteristics["strength"]}')
            confluence_factors.append(f'Expected: {characteristics["direction"]}')
            confluence_factors.append(characteristics['notes'])
        else:
            confluence_factors.append('No active Kill Zone - low probability period')
            confluence_factors.append('Consider waiting for next Kill Zone')
        
        if current_kz == 'NY_AM_KZ':
            confluence_factors.append('OPTIMAL KILL ZONE - Highest probability window')
        
        # Signal
        if is_high_priority:
            signal = 'PRIME_TIME'
        elif priority in ['MEDIUM', 'LOW']:
            signal = 'ACTIVE'
        else:
            signal = 'WAIT'
        
        # Metadata
        metadata = {
            'kill_zone': current_kz,
            'hour_utc': current_time.hour,
            'priority': priority,
            'strength': characteristics['strength'],
            'expected_direction': characteristics['direction'],
            'is_high_priority': is_high_priority,
            'is_optimal_kz': current_kz == 'NY_AM_KZ',
            'time_window_utc': self._get_kz_hours(current_kz)
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
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
    data = pd.DataFrame({'timestamp': dates})
    
    kz = KillZones()
    
    print("=" * 80)
    print("KILL ZONES IDENTIFIER - TEST RESULTS")
    print("=" * 80)
    
    for _, row in data.iterrows():
        result = kz.analyze(pd.DataFrame([row]))
        kz_name = result['metadata']['kill_zone']
        priority = result['metadata']['priority']
        print(f"{row['timestamp']}: {kz_name} (Priority: {priority}) - {result['signal']}")
    print("=" * 80)
