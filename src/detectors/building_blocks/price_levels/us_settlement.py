"""
US Settlement Price Building Block
Category: Price Levels
Purpose: CME Bitcoin futures settlement price (4 PM ET / 9 PM UTC)
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous US settlement price reference

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


class USSettlement:
    """
    US Settlement Price - CME Bitcoin Futures Settlement
    
    Tracks the CME settlement price (4 PM ET / 9 PM UTC).
    Critical for:
    - Futures expiry levels
    - Institutional activity
    - End-of-day positioning
    - Gap trading
    """
    
    def __init__(self, timeframe: str = '15min', settlement_hour_utc: int = 21, **kwargs):
        """Initialize US Settlement block"""
        self.timeframe = timeframe
        self.settlement_hour_utc = settlement_hour_utc
        
        # RETEST CONFIRMATION: Track retests of settlement level
        self.confirmation_candles = 2  # Require 2 consecutive bars (more realistic)
        self.bounce_test_bars = []  # Track bars testing support (below settlement)
        self.rejection_test_bars = []  # Track bars testing resistance (above settlement)
        
        self.btc_distance_thresholds = {
            'at_settlement': 0.15,
            'very_close': 0.75,
            'close': 1.5,
            'moderate': 3.0,
            'far': 3.0
        }
    
    def find_settlement_price(self, df: pd.DataFrame) -> float:
        """Find most recent settlement price (21:00 UTC / 4 PM ET)"""
        if 'timestamp' not in df.columns or 'close' not in df.columns:
            return None
        
        settlement_data = df[df['timestamp'].dt.hour == self.settlement_hour_utc]
        if len(settlement_data) == 0:
            return None
        
        return float(settlement_data['close'].iloc[-1])
    
    def calculate_distance(self, price: float, settlement: float) -> float:
        """Calculate percentage distance from settlement"""
        if settlement is None:
            return None
        return ((price - settlement) / settlement) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from settlement"""
        if distance_pct is None:
            return 'NO_SETTLEMENT'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_settlement']:
            return 'AT_SETTLEMENT'
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
        if not all(col in df.columns for col in ['timestamp', 'close']):
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
        
        settlement = self.find_settlement_price(df)
        
        if settlement is None:
            return {
                'signal': 'NO_SETTLEMENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No settlement price found'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = self.calculate_distance(current_price, settlement)
        distance_class = self.classify_distance(distance_pct)
        
        # RETEST CONFIRMATION: Track settlement retests
        confirmed_bounce = False
        confirmed_rejection = False
        
        current_bar = {
            'close': current_price,
            'low': float(df['low'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'distance': distance_pct,
            'breached_below': float(df['low'].iloc[-1]) < settlement,
            'breached_above': float(df['high'].iloc[-1]) > settlement,
            'closed_above': current_price > settlement,
            'closed_below': current_price < settlement
        }
        
        # BOUNCE TEST: Price wicks BELOW settlement but closes ABOVE (support holding)
        if current_bar['breached_below'] and current_bar['closed_above']:
            self.bounce_test_bars.append(current_bar)
            if len(self.bounce_test_bars) > self.confirmation_candles + 2:
                self.bounce_test_bars.pop(0)
            
            if len(self.bounce_test_bars) >= self.confirmation_candles:
                recent_bars = self.bounce_test_bars[-self.confirmation_candles:]
                all_tested_and_held = all(
                    bar['breached_below'] and bar['closed_above']
                    for bar in recent_bars
                )
                
                if all_tested_and_held:
                    confirmed_bounce = True
                    self.bounce_test_bars = []
        elif distance_class not in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            if len(self.bounce_test_bars) > 0:
                self.bounce_test_bars = []
        
        # REJECTION TEST: Price wicks ABOVE settlement but closes BELOW (resistance holding)
        if current_bar['breached_above'] and current_bar['closed_below']:
            self.rejection_test_bars.append(current_bar)
            if len(self.rejection_test_bars) > self.confirmation_candles + 2:
                self.rejection_test_bars.pop(0)
            
            if len(self.rejection_test_bars) >= self.confirmation_candles:
                recent_bars = self.rejection_test_bars[-self.confirmation_candles:]
                all_tested_and_rejected = all(
                    bar['breached_above'] and bar['closed_below']
                    for bar in recent_bars
                )
                
                if all_tested_and_rejected:
                    confirmed_rejection = True
                    self.rejection_test_bars = []
        elif distance_class not in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            if len(self.rejection_test_bars) > 0:
                self.rejection_test_bars = []
        
        # Determine signal (ENHANCED with retest confirmation)
        if confirmed_bounce:
            signal = 'BULLISH'  # Support holding at settlement
        elif confirmed_rejection:
            signal = 'BEARISH'  # Resistance holding at settlement
        elif distance_pct > 0 and distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            signal = 'BULLISH'  # Above settlement (support)
        elif distance_pct < 0 and distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            signal = 'BEARISH'  # Below settlement (resistance)
        else:
            signal = 'NEUTRAL'
        
        # Confidence calculation (BOOSTED for retest confirmation)
        confidence = 70
        if distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            confidence += 15
        if confirmed_bounce or confirmed_rejection:
            confidence += 20  # Strong boost for 3-bar confirmation
        confidence = min(95, confidence)
        
        # Build confluence
        confluence_factors = []
        
        # Retest confirmation confluence (HIGHEST PRIORITY)
        if confirmed_bounce:
            confluence_factors.append('⭐⭐ CONFIRMED BOUNCE FROM SETTLEMENT - Strong institutional support!')
            confluence_factors.append(f'✓ {self.confirmation_candles} retests: wicked below, closed above (settlement support holding!)')
        elif confirmed_rejection:
            confluence_factors.append('⭐⭐ CONFIRMED REJECTION FROM SETTLEMENT - Strong institutional resistance!')
            confluence_factors.append(f'✓ {self.confirmation_candles} retests: wicked above, closed below (settlement resistance holding!)')
        
        # Standard confluence
        elif distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            confluence_factors.append('Price at/near US settlement - institutional level')
        
        confluence_factors.append(f'US Settlement: ${settlement:.2f}')
        confluence_factors.append(f'Distance: {distance_pct:+.2f}% ({distance_class})')
        
        metadata = {
            'settlement_price': round(settlement, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'is_institutional_level': distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE'],
            'settlement_hour_utc': self.settlement_hour_utc,
            'confirmed_bounce': confirmed_bounce,
            'confirmed_rejection': confirmed_rejection,
            'confirmation_candles': self.confirmation_candles
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
