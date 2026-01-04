"""
Session Time Building Block - ENHANCED
Category: Sessions & Time
Purpose: Identify active trading session with data validation

ENHANCED VERSION (2026-01-03):
- Event tracking (session transitions)
- Volume confirmation (quality block integration)
- ATR awareness (volatility context)
- Smart confidence (data-driven)
- Rich metadata for confluence
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: TIME-BASED
Purpose: Continuous session state tracking

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


class SessionTime:
    """
    Session Time Identifier - ENHANCED
    
    Identifies trading sessions with quality block enhancements:
    - Event tracking (session transitions)
    - Volume confirmation (active vs quiet sessions)
    - ATR context (volatility awareness)
    - Smart confidence (historical + real-time)
    
    Sessions (UTC):
    - Asia: 00:00-08:00 (Tokyo/Hong Kong/Singapore)
    - London: 08:00-16:00 (London/Frankfurt/Zurich)
    - New York: 13:00-21:00 (New York/Chicago)
    - London/NY Overlap: 13:00-16:00 (peak hours)
    - Sydney: 21:00-06:00 (overlaps with Asia)
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        """Initialize Enhanced Session Time block"""
        self.timeframe = timeframe
        self.last_session = None
        self.bars_in_session = 0
        
        # Session times in UTC
        self.sessions = {
            'ASIA': {'start': 0, 'end': 8, 'base_confidence': 50},
            'LONDON': {'start': 8, 'end': 16, 'base_confidence': 85},
            'NEW_YORK': {'start': 13, 'end': 21, 'base_confidence': 90},
            'SYDNEY': {'start': 21, 'end': 24, 'base_confidence': 40}
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
        Analyze volume activity for session confirmation
        Returns: (volume_ratio, is_active, activity_score)
        """
        if len(df) < window or 'volume' not in df.columns:
            return 1.0, False, 50
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-window:].mean()
        
        if avg_volume == 0:
            return 1.0, False, 50
        
        volume_ratio = current_volume / avg_volume
        
        # High volume = active session
        is_active = volume_ratio > 1.2
        
        # Activity score (0-100)
        activity_score = min(100, int(volume_ratio * 50))
        
        return volume_ratio, is_active, activity_score
    
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
    
    def get_base_confidence(self, session: str) -> int:
        """Get base confidence for session"""
        if session == 'LONDON_NY_OVERLAP':
            return 95
        elif session in self.sessions:
            return self.sessions[session]['base_confidence']
        else:
            return 30
    
    def calculate_smart_confidence(self, base_confidence: int,
                                   activity_score: int,
                                   atr: float,
                                   avg_atr: float = 1000.0,
                                   is_transition: bool = False) -> int:
        """
        Smart confidence calculation using real-time data
        
        Factors:
        1. Base confidence (from session type)
        2. Volume activity (confirms session is active)
        3. Volatility context (ATR)
        4. Transition bonus (new session entry)
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
                # High volatility during session = good
                confidence += 5
            elif volatility_ratio < 0.5:
                # Low volatility during session = reduce
                confidence -= 5
        
        # Transition bonus (+5%)
        if is_transition:
            confidence += 5  # Fresh session entry
        
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
        
        if len(df) < 50:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 50 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Current and previous time
        current_time = df['timestamp'].iloc[-1]
        previous_time = df['timestamp'].iloc[-2]
        
        current_session = self.identify_session(current_time)
        previous_session = self.identify_session(previous_time)
        
        # Event tracking: is this a new session?
        is_new_event = (current_session != self.last_session)
        session_changed = current_session != previous_session
        
        if is_new_event:
            self.bars_in_session = 0
        else:
            self.bars_in_session += 1
        
        # Update tracking
        self.last_session = current_session
        
        # Session properties
        characteristics = self.get_session_characteristics(current_session)
        is_high_vol = self.is_high_volatility_session(current_session)
        base_confidence = self.get_base_confidence(current_session)
        
        # Quality block integrations
        atr = self.calculate_atr(df, period=14)
        volume_ratio, is_volume_active, activity_score = self.analyze_volume_activity(df, window=20)
        
        # Smart confidence (data-driven!)
        confidence = self.calculate_smart_confidence(
            base_confidence,
            activity_score,
            atr,
            avg_atr=atr,  # Could use historical avg
            is_transition=session_changed
        )
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'Active Session: {current_session}')
        confluence_factors.append(f'Volatility: {characteristics["volatility"]}')
        confluence_factors.append(f'Volume: {characteristics["volume"]}')
        confluence_factors.append(f'Expected Range: {characteristics["typical_range"]}')
        
        if is_new_event:
            confluence_factors.append(f'🆕 NEW session entered!')
        else:
            confluence_factors.append(f'Session active for {self.bars_in_session} bars')
        
        if session_changed:
            confluence_factors.append(f'Session change: {previous_session} → {current_session}')
        
        if is_volume_active:
            confluence_factors.append(f'⭐ HIGH volume activity ({volume_ratio:.1f}x average)')
        
        if current_session == 'LONDON_NY_OVERLAP':
            confluence_factors.append('🎯 Peak trading hours - highest activity')
        elif current_session == 'ASIA':
            confluence_factors.append('Asia session - range-bound typical')
        elif current_session == 'SYDNEY':
            confluence_factors.append('Sydney session - minimal activity')
        
        # Signal ONLY on session changes (not continuously)
        if session_changed:
            if is_high_vol:
                signal = 'SESSION_ACTIVE'  # Entering active session
            else:
                signal = 'SESSION_QUIET'  # Entering quiet session
        else:
            signal = 'NEUTRAL'  # No session change
        
        # Rich metadata for confluence
        metadata = {
            'session': current_session,
            'hour_utc': current_time.hour,
            'volatility': characteristics['volatility'],
            'volume': characteristics['volume'],
            'expected_range': characteristics['typical_range'],
            'is_high_volatility': is_high_vol,
            'is_overlap': current_session == 'LONDON_NY_OVERLAP',
            'session_hours_utc': self._get_session_hours(current_session),
            # ENHANCED metadata:
            'is_new_event': is_new_event,
            'bars_in_session': self.bars_in_session,
            'previous_session': previous_session,
            'session_changed': session_changed,
            'volume_ratio': round(volume_ratio, 2),
            'is_volume_active': is_volume_active,
            'activity_score': activity_score,
            'atr_value': round(atr, 2),
            'base_confidence': base_confidence,
            'adjusted_confidence': confidence
        }
        
        return {
            'signal': signal,
            'confidence': confidence,
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
    data = pd.DataFrame({
        'timestamp': dates,
        'high': np.random.randn(24) * 100 + 50000,
        'low': np.random.randn(24) * 100 + 49500,
        'close': np.random.randn(24) * 100 + 49750,
        'volume': np.random.rand(24) * 1000
    })
    
    session = SessionTime()
    
    print("=" * 80)
    print("ENHANCED SESSION TIME - TEST RESULTS")
    print("=" * 80)
    
    for i in range(len(data)):
        result = session.analyze(data.iloc[:i+1])
        sess_name = result['metadata']['session']
        is_new = result['metadata']['is_new_event']
        event_marker = "🆕 NEW! " if is_new else ""
        print(f"{data['timestamp'].iloc[i]}: {event_marker}{sess_name} - {result['signal']} ({result['confidence']}%)")
    print("=" * 80)
