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
        self.reversal_candles = 5  # Monitor 5 candles after test for reversal pattern (more realistic)
        self.bounce_test_bars = []  # Track bars testing support (below settlement)
        self.last_settlement_test_bar = None  # Bar that tested settlement (above settlement)
        
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
        
        # REVERSAL CONFIRMATION: Detect reversal patterns after testing settlement
        reversal_bounce = False  # Bullish reversal after testing from below
        reversal_rejection = False  # Bearish reversal after testing from above
        
        current_bar = {
            'close': current_price,
            'low': float(df['low'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'distance': distance_pct,
            'tested_settlement': distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']
        }
        
        # Check if testing settlement
        if current_bar['tested_settlement']:
            self.last_settlement_test_bar = current_bar
            self.bars_since_test = []
        
        # Monitor bars after test
        if self.last_settlement_test_bar is not None:
            self.bars_since_test.append(current_bar)
            
            if len(self.bars_since_test) > self.reversal_candles:
                self.bars_since_test.pop(0)
            
            # Check for reversals (5 bars of consistent trend)
            if len(self.bars_since_test) >= self.reversal_candles:
                recent = self.bars_since_test[-self.reversal_candles:]
                
                higher_highs = all(recent[i]['high'] > recent[i-1]['high'] for i in range(1, len(recent)))
                higher_lows = all(recent[i]['low'] > recent[i-1]['low'] for i in range(1, len(recent)))
                lower_highs = all(recent[i]['high'] < recent[i-1]['high'] for i in range(1, len(recent)))
                lower_lows = all(recent[i]['low'] < recent[i-1]['low'] for i in range(1, len(recent)))
                
                if higher_highs and higher_lows:
                    reversal_bounce = True
                    self.last_settlement_test_bar = None
                    self.bars_since_test = []
                elif lower_highs and lower_lows:
                    reversal_rejection = True
                    self.last_settlement_test_bar = None
                    self.bars_since_test = []
            
            # Reset if moves far away
            if distance_class == 'FAR':
                self.last_settlement_test_bar = None
                self.bars_since_test = []
        
        # Determine signal (ENHANCED with reversal confirmation)
        if reversal_bounce:
            signal = 'BULLISH'  # Support holding at settlement
        elif reversal_rejection:
            signal = 'BEARISH'  # Resistance holding at settlement
        elif distance_pct > 0 and distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            signal = 'BULLISH'  # Above settlement (support)
        elif distance_pct < 0 and distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            signal = 'BEARISH'  # Below settlement (resistance)
        else:
            signal = 'NEUTRAL'
        
        # Confidence calculation (BOOSTED for reversal confirmation)
        confidence = 70
        if distance_class in ['AT_SETTLEMENT', 'VERY_CLOSE']:
            confidence += 15
        if reversal_bounce or reversal_rejection:
            confidence += 25  # Strong boost for reversal pattern
        confidence = min(95, confidence)
        
        # Build confluence
        confluence_factors = []
        
        # Reversal confirmation confluence (HIGHEST PRIORITY)
        if reversal_bounce:
            confluence_factors.append('⭐⭐⭐ BULLISH REVERSAL CONFIRMED AT SETTLEMENT!')
            confluence_factors.append(f'✓ Tested settlement then {self.reversal_candles} bars of higher highs + higher lows')
            confluence_factors.append('✓ Strong institutional support - uptrend forming')
        elif reversal_rejection:
            confluence_factors.append('⭐⭐⭐ BEARISH REVERSAL CONFIRMED AT SETTLEMENT!')
            confluence_factors.append(f'✓ Tested settlement then {self.reversal_candles} bars of lower highs + lower lows')
            confluence_factors.append('✓ Strong institutional resistance - downtrend forming')
        
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
            'reversal_bounce': reversal_bounce,
            'reversal_rejection': reversal_rejection,
            'reversal_candles': self.reversal_candles,
            'bars_monitored': len(self.bars_since_test)
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
