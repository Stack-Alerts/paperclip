"""
Session Time Building Block
Category: Sessions & Time
Purpose: Identify active trading session (Asia, London, New York)
"""

from typing import Dict, Any
from datetime import datetime, time
import pandas as pd


class SessionTime:
    """
    Session Time Identifier
    
    Identifies which major trading session is currently active.
    Critical for:
    - Session-based strategies
    - Volume pattern recognition
    - Institutional activity timing
    - Volatility expectations
    
    Sessions (UTC):
    - Asia: 00:00-08:00 (Tokyo/Hong Kong/Singapore)
    - London: 08:00-16:00 (London/Frankfurt/Zurich)
    - New York: 13:00-21:00 (New York/Chicago)
    - Sydney: 21:00-06:00 (overlaps with Asia)
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        """Initialize Session Time block"""
        self.timeframe = timeframe
        
        # Session times in UTC
        self.sessions = {
            'ASIA': {'start': 0, 'end': 8},
            'LONDON': {'start': 8, 'end': 16},
            'NEW_YORK': {'start': 13, 'end': 21},
            'SYDNEY': {'start': 21, 'end': 24}  # 21:00-00:00
        }
        
        # Session characteristics
        self.session_characteristics = {
            'ASIA': {'volatility': 'LOW', 'volume': 'MODERATE', 'typical_range': 'TIGHT'},
            'LONDON': {'volatility': 'HIGH', 'volume': 'HIGH', 'typical_range': 'WIDE'},
            'NEW_YORK': {'volatility': 'HIGHEST', 'volume': 'HIGHEST', 'typical_range': 'WIDEST'},
            'LONDON_NY_OVERLAP': {'volatility': 'EXTREME', 'volume': 'EXTREME', 'typical_range': 'VERY_WIDE'},
            'SYDNEY': {'volatility': 'VERY_LOW', 'volume': 'LOW', 'typical_range': 'VERY_TIGHT'},
            'OFF_SESSION': {'volatility': 'MINIMAL', 'volume': 'VERY_LOW', 'typical_range': 'MINIMAL'}
        }
    
    def identify_session(self, timestamp: datetime) -> str:
        """Identify which session is active at given timestamp"""
        hour = timestamp.hour
        
        # Check for London/NY overlap (13:00-16:00 UTC)
        if 13 <= hour < 16:
            return 'LONDON_NY_OVERLAP'
        
        # Check individual sessions
        if self.sessions['ASIA']['start'] <= hour < self.sessions['ASIA']['end']:
            return 'ASIA'
        elif self.sessions['LONDON']['start'] <= hour < self.sessions['LONDON']['end']:
            return 'LONDON'
        elif self.sessions['NEW_YORK']['start'] <= hour < self.sessions['NEW_YORK']['end']:
            return 'NEW_YORK'
        elif hour >= self.sessions['SYDNEY']['start'] or hour < self.sessions['ASIA']['start']:
            return 'SYDNEY'
        else:
            return 'OFF_SESSION'
    
    def get_session_characteristics(self, session: str) -> Dict[str, str]:
        """Get volatility and volume characteristics for session"""
        return self.session_characteristics.get(session, self.session_characteristics['OFF_SESSION'])
    
    def is_high_volatility_session(self, session: str) -> bool:
        """Check if session is high volatility"""
        char = self.get_session_characteristics(session)
        return char['volatility'] in ['HIGH', 'HIGHEST', 'EXTREME']
    
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
        
        if len(df) < 50:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 2 periods for session change detection'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_time = df['timestamp'].iloc[-1]
        previous_time = df['timestamp'].iloc[-2]
        
        current_session = self.identify_session(current_time)
        previous_session = self.identify_session(previous_time)
        
        characteristics = self.get_session_characteristics(current_session)
        is_high_vol = self.is_high_volatility_session(current_session)
        
        # Detect session change
        session_changed = current_session != previous_session
        
        # Calculate confidence based on session
        confidence = 90 if session_changed else 70
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'Active Session: {current_session}')
        confluence_factors.append(f'Volatility: {characteristics["volatility"]}')
        confluence_factors.append(f'Volume: {characteristics["volume"]}')
        confluence_factors.append(f'Expected Range: {characteristics["typical_range"]}')
        
        if session_changed:
            confluence_factors.append(f'Session change: {previous_session} → {current_session}')
        
        if current_session == 'LONDON_NY_OVERLAP':
            confluence_factors.append('Peak trading hours - highest activity')
        elif current_session == 'ASIA':
            confluence_factors.append('Asia session - range-bound typical')
        elif current_session == 'SYDNEY':
            confluence_factors.append('Sydney session - minimal activity')
        
        # Signal ONLY on session changes, not continuously
        # This prevents signaling on every bar (reduces noise)
        if session_changed:
            if is_high_vol:
                signal = 'SESSION_ACTIVE'  # Entering active session
            else:
                signal = 'SESSION_QUIET'  # Entering quiet session
        else:
            signal = 'NEUTRAL'  # No session change
        
        # Metadata
        metadata = {
            'session': current_session,
            'hour_utc': current_time.hour,
            'volatility': characteristics['volatility'],
            'volume': characteristics['volume'],
            'expected_range': characteristics['typical_range'],
            'is_high_volatility': is_high_vol,
            'is_overlap': current_session == 'LONDON_NY_OVERLAP',
            'session_hours_utc': self._get_session_hours(current_session)
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': current_time,
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
    
    def _get_session_hours(self, session: str) -> str:
        """Get session hours as string"""
        if session == 'LONDON_NY_OVERLAP':
            return '13:00-16:00 UTC'
        elif session in self.sessions:
            s = self.sessions[session]
            return f"{s['start']:02d}:00-{s['end']:02d}:00 UTC"
        else:
            return 'N/A'


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=24, freq='1h')
    data = pd.DataFrame({'timestamp': dates})
    
    session = SessionTime()
    
    print("=" * 80)
    print("SESSION TIME IDENTIFIER - TEST RESULTS")
    print("=" * 80)
    
    for _, row in data.iterrows():
        result = session.analyze(pd.DataFrame([row]))
        print(f"{row['timestamp']}: {result['metadata']['session']} - {result['signal']}")
    print("=" * 80)
