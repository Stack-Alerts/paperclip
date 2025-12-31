"""
Optimal Trade Entry (OTE) Building Block
Category: SMC/ICT
Purpose: Detect optimal trade entry zones - ICT Fibonacci concept
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class OptimalTradeEntry:
    """
    Optimal Trade Entry (OTE) Detector - ICT/SMC Concept
    
    Identifies the optimal entry zone for trades based on Fibonacci
    retracement levels. ICT's OTE zone is between 61.8% and 78.6%
    retracement of the prior move.
    
    OTE Characteristics:
    - 61.8% - 78.6% Fibonacci retracement
    - Optimal risk/reward entry
    - Institutional accumulation/distribution zone
    - Continuation pattern after retracement
    
    Types:
    - Bullish OTE: Retracement in uptrend (buy zone)
    - Bearish OTE: Retracement in downtrend (sell zone)
    
    Trading Application:
    - Enter on pullback to OTE zone
    - Combine with other ICT concepts
    - High probability continuation
    
    Parameters:
        lookback: Periods for move detection (default: 20)
        ote_min: Minimum OTE level (default: 0.618)
        ote_max: Maximum OTE level (default: 0.786)
    """
    
    def __init__(self, timeframe: str = '15min',
                 lookback: int = 20,
                 ote_min: float = 0.618,
                 ote_max: float = 0.786, **kwargs):
        """Initialize OTE detector"""
        self.timeframe = timeframe
        self.lookback = lookback
        self.ote_min = ote_min
        self.ote_max = ote_max
    
    def detect_trend(self, df: pd.DataFrame) -> str:
        """Detect trend direction"""
        if len(df) < 15:
            return 'NEUTRAL'
        
        recent = df.tail(15)
        highs_increasing = recent['high'].iloc[-1] > recent['high'].iloc[0]
        lows_increasing = recent['low'].iloc[-1] > recent['low'].iloc[0]
        
        if highs_increasing and lows_increasing:
            return 'UPTREND'
        elif not highs_increasing and not lows_increasing:
            return 'DOWNTREND'
        else:
            return 'NEUTRAL'
    
    def calculate_ote_zone(self, swing_high: float, swing_low: float) -> Dict[str, float]:
        """Calculate OTE zone levels"""
        move_range = swing_high - swing_low
        
        # Calculate Fibonacci levels
        ote_high = swing_high - (move_range * self.ote_min)  # 61.8% level
        ote_low = swing_high - (move_range * self.ote_max)   # 78.6% level
        
        return {
            'ote_high': float(ote_high),
            'ote_low': float(ote_low),
            'swing_high': float(swing_high),
            'swing_low': float(swing_low),
            'move_range': float(move_range)
        }
    
    def detect_bullish_ote(self, df: pd.DataFrame, trend: str) -> Dict[str, Any]:
        """Detect bullish OTE (in uptrend, pullback to OTE)"""
        if trend != 'UPTREND':
            return None
        
        if len(df) < self.lookback:
            return None
        
        # Find recent swing high and swing low
        recent = df.tail(self.lookback)
        swing_high = float(recent['high'].max())
        swing_low = float(recent['low'].min())
        
        # Calculate OTE zone
        ote_zone = self.calculate_ote_zone(swing_high, swing_low)
        
        # Check if current price is in OTE zone
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_close = df['close'].iloc[-1]
        
        # Price touched or is in OTE zone
        in_ote = (current_low <= ote_zone['ote_high'] and 
                  current_high >= ote_zone['ote_low'])
        
        if in_ote:
            # Calculate retracement percentage
            retracement = (swing_high - current_close) / ote_zone['move_range']
            
            return {
                'type': 'BULLISH_OTE',
                'ote_high': ote_zone['ote_high'],
                'ote_low': ote_zone['ote_low'],
                'swing_high': ote_zone['swing_high'],
                'swing_low': ote_zone['swing_low'],
                'current_price': float(current_close),
                'retracement_pct': round(retracement * 100, 2),
                'timestamp': df['timestamp'].iloc[-1]
            }
        
        return None
    
    def detect_bearish_ote(self, df: pd.DataFrame, trend: str) -> Dict[str, Any]:
        """Detect bearish OTE (in downtrend, retracement to OTE)"""
        if trend != 'DOWNTREND':
            return None
        
        if len(df) < self.lookback:
            return None
        
        # Find recent swing high and swing low
        recent = df.tail(self.lookback)
        swing_high = float(recent['high'].max())
        swing_low = float(recent['low'].min())
        
        # Calculate OTE zone (inverted for downtrend)
        move_range = swing_high - swing_low
        ote_high = swing_low + (move_range * self.ote_max)  # 78.6% from low
        ote_low = swing_low + (move_range * self.ote_min)   # 61.8% from low
        
        # Check if current price is in OTE zone
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_close = df['close'].iloc[-1]
        
        # Price touched or is in OTE zone
        in_ote = (current_high >= ote_low and 
                  current_low <= ote_high)
        
        if in_ote:
            # Calculate retracement percentage
            retracement = (current_close - swing_low) / move_range
            
            return {
                'type': 'BEARISH_OTE',
                'ote_high': float(ote_high),
                'ote_low': float(ote_low),
                'swing_high': float(swing_high),
                'swing_low': float(swing_low),
                'current_price': float(current_close),
                'retracement_pct': round(retracement * 100, 2),
                'timestamp': df['timestamp'].iloc[-1]
            }
        
        return None
    
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
        
        if len(df) < self.lookback + 5:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.lookback + 5} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect trend
        trend = self.detect_trend(df)
        
        if trend == 'NEUTRAL':
            return {
                'signal': 'NEUTRAL',
                'confidence': 0,
                'metadata': {'trend': 'NEUTRAL', 'error': 'No clear trend'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['No clear trend for OTE']
            }
        
        # Detect OTE
        bullish_ote = self.detect_bullish_ote(df, trend) if trend == 'UPTREND' else None
        bearish_ote = self.detect_bearish_ote(df, trend) if trend == 'DOWNTREND' else None
        
        # Choose active OTE
        active_ote = None
        signal = 'NEUTRAL'
        
        if bullish_ote:
            active_ote = bullish_ote
            signal = 'BULLISH'
        elif bearish_ote:
            active_ote = bearish_ote
            signal = 'BEARISH'
        
        if not active_ote:
            return {
                'signal': 'NO_OTE',
                'confidence': 0,
                'metadata': {'trend': trend, 'error': 'Not in OTE zone'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': [f'Trend: {trend}', 'Waiting for OTE zone entry']
            }
        
        # Calculate confidence
        confidence = 75  # Base confidence for OTE
        # Higher confidence if closer to sweet spot (70%)
        if 68 <= active_ote['retracement_pct'] <= 72:
            confidence += 15
        elif 65 <= active_ote['retracement_pct'] <= 75:
            confidence += 10
        confidence = min(100, confidence)
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'OTE Type: {active_ote["type"]}')
        confluence_factors.append(f'Retracement: {active_ote["retracement_pct"]:.1f}%')
        confluence_factors.append(f'OTE Zone: ${active_ote["ote_low"]:.2f} - ${active_ote["ote_high"]:.2f}')
        confluence_factors.append('Optimal entry zone - institutional interest')
        confluence_factors.append('High probability continuation setup')
        
        # Metadata
        metadata = {
            'ote_type': active_ote['type'],
            'ote_high': active_ote['ote_high'],
            'ote_low': active_ote['ote_low'],
            'swing_high': active_ote['swing_high'],
            'swing_low': active_ote['swing_low'],
            'current_price': active_ote['current_price'],
            'retracement_pct': active_ote['retracement_pct'],
            'ote_timestamp': active_ote['timestamp']
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
