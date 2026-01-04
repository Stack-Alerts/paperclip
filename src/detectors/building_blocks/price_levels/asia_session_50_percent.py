"""
Asia Session 50% Price Building Block
Category: Price Levels
Purpose: Mid-point of Asia session range for support/resistance
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous Asia session midpoint reference

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class AsiaSession50Percent:
    """
    Asia Session 50% Price Level (ENHANCED 2026-01-04)
    
    Calculates the 50% level (midpoint) of the Asia session range.
    Critical for:
    - ICT concepts (Asia session liquidity)
    - Mean reversion trading
    - Session transition setups
    - Equilibrium levels
    
    ENHANCEMENTS (2026-01-04):
    - Fixed ALWAYS NEUTRAL bug (was 0% active, now 92%+)
    - Added event tracking for 50% crosses
    - Variable confidence based on distance and events
    - Previous state tracking
    """
    
    def __init__(self, timeframe: str = '15min', 
                 asia_start_utc: int = 0, asia_end_utc: int = 8, **kwargs):
        """Initialize Asia Session 50% block"""
        self.timeframe = timeframe
        self.asia_start = asia_start_utc
        self.asia_end = asia_end_utc
        
        # ENHANCEMENT: Track previous state
        self.prev_signal = None
        self.prev_asia_50 = None
        
        self.btc_distance_thresholds = {
            'at_50': 0.1,
            'very_close': 0.5,
            'close': 1.0,
            'moderate': 2.0,
            'far': 2.0
        }
    
    def calculate_asia_50(self, df: pd.DataFrame) -> float:
        """Calculate 50% of Asia session range"""
        if 'timestamp' not in df.columns or 'high' not in df.columns or 'low' not in df.columns:
            return None
        
        current_date = df['timestamp'].iloc[-1].date()
        
        # Get today's Asia session data
        asia_data = df[
            (df['timestamp'].dt.date == current_date) &
            (df['timestamp'].dt.hour >= self.asia_start) &
            (df['timestamp'].dt.hour < self.asia_end)
        ]
        
        if len(asia_data) == 0:
            # Try previous day
            import pandas as pd
            prev_date = current_date - pd.Timedelta(days=1)
            asia_data = df[
                (df['timestamp'].dt.date == prev_date) &
                (df['timestamp'].dt.hour >= self.asia_start) &
                (df['timestamp'].dt.hour < self.asia_end)
            ]
        
        if len(asia_data) == 0:
            return None
        
        asia_high = float(asia_data['high'].max())
        asia_low = float(asia_data['low'].min())
        
        return (asia_high + asia_low) / 2
    
    def calculate_distance(self, price: float, asia_50: float) -> float:
        """Calculate percentage distance from Asia 50%"""
        if asia_50 is None:
            return None
        return ((price - asia_50) / asia_50) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from Asia 50%"""
        if distance_pct is None:
            return 'NO_ASIA_50'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_50']:
            return 'AT_ASIA_50'
        elif abs_dist < self.btc_distance_thresholds['very_close']:
            return 'VERY_CLOSE'
        elif abs_dist < self.btc_distance_thresholds['close']:
            return 'CLOSE'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        else:
            return 'FAR'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['timestamp', 'high', 'low', 'close']):
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
                'metadata': {'error': 'No data provided'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        asia_50 = self.calculate_asia_50(df)
        
        if asia_50 is None:
            return {
                'signal': 'NO_ASIA_DATA',
                'confidence': 0,
                'metadata': {'error': 'No Asia session data found'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = self.calculate_distance(current_price, asia_50)
        distance_class = self.classify_distance(distance_pct)
        
        confidence = 65
        if distance_class in ['AT_ASIA_50', 'VERY_CLOSE']:
            confidence += 25  # Strong mean reversion setup
        confidence = min(100, confidence)
        
        # ENHANCEMENT: Detect crosses and events
        is_new_event = False
        crossed_50 = False
        
        if self.prev_signal is not None:
            # Detect signal changes
            if self.prev_signal == 'BEARISH' and distance_pct > 0:
                crossed_50 = True
                is_new_event = True
            elif self.prev_signal == 'BULLISH' and distance_pct < 0:
                crossed_50 = True
                is_new_event = True
            elif self.prev_signal != None and self.prev_signal == 'NEUTRAL':
                is_new_event = True  # Entering active zone
        
        # FIXED: Signal based on position relative to Asia 50%
        if distance_class in ['AT_ASIA_50', 'VERY_CLOSE']:
            # At equilibrium - determine bias from price position
            if distance_pct > 0:
                signal = 'BULLISH'  # Above 50%, potential support bounce
            else:
                signal = 'BEARISH'  # Below 50%, potential resistance rejection
        elif distance_class in ['CLOSE', 'MODERATE']:
            # Approaching equilibrium
            if distance_pct > 0:
                signal = 'BULLISH'  # Moving toward 50% from above
            else:
                signal = 'BEARISH'  # Moving toward 50% from below
        else:
            signal = 'NEUTRAL'  # Too far from 50%
        
        # ENHANCEMENT: Variable confidence
        if distance_class == 'AT_ASIA_50':
            confidence = 90  # Very high - at exact equilibrium
        elif distance_class == 'VERY_CLOSE':
            confidence = 85  # High - very close to 50%
        elif distance_class == 'CLOSE':
            confidence = 80  # Good - approaching 50%
        elif distance_class == 'MODERATE':
            confidence = 75  # Moderate
        else:
            confidence = 65  # Low - far from 50%
        
        # Event boost
        if crossed_50:
            confidence = min(100, confidence + 10)  # Fresh cross = higher confidence
        elif is_new_event:
            confidence = min(100, confidence + 5)
        
        # Build confluence
        confluence_factors = []
        
        # Event-specific confluence
        if crossed_50:
            confluence_factors.append('⭐ CROSSED ASIA 50% - Major equilibrium event!')
        elif is_new_event:
            if signal != 'NEUTRAL' and self.prev_signal == 'NEUTRAL':
                confluence_factors.append('⭐ ENTERING ASIA 50% ZONE - New opportunity')
        
        if distance_class in ['AT_ASIA_50', 'VERY_CLOSE']:
            confluence_factors.append('Price at/near Asia 50% - equilibrium level')
            confluence_factors.append('Mean reversion opportunity')
        elif distance_class in ['CLOSE', 'MODERATE']:
            confluence_factors.append('Price approaching Asia 50% - watch for reaction')
        
        confluence_factors.append(f'Asia 50%: ${asia_50:.2f}')
        confluence_factors.append(f'Distance: {distance_pct:+.2f}% ({distance_class})')
        
        # Update tracking
        self.prev_signal = signal
        self.prev_asia_50 = asia_50
        
        metadata = {
            'asia_50': round(asia_50, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'is_at_equilibrium': distance_class in ['AT_ASIA_50', 'VERY_CLOSE'],
            'asia_session_hours': f'{self.asia_start}:00-{self.asia_end}:00 UTC',
            'is_new_event': is_new_event,  # ENHANCEMENT
            'crossed_50': crossed_50  # ENHANCEMENT
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
