"""
Optimal Trade Entry (OTE) Building Block
Category: SMC/ICT
Purpose: Detect optimal trade entry zones - ICT Fibonacci concept

ENHANCEMENTS (2026-01-04):
- Priority 1.1: Precise OTE detection (70.5% equilibrium)
- Priority 1.2: Retracement strength classification
- Priority 1.3: Swing strength measurement (ATR-relative)
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: OTE zone detection, fires in Fibonacci zone

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='optimal_trade_entry',
    category='SMC_ICT',
    class_name='OptimalTradeEntry',
    default_weight=20,
    valid_signals=[
        # Granular SMC signals
        'BEARISH_OTE', 'BULLISH_OTE',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BEARISH_OTE': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'BULLISH_OTE': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'NEUTRAL': {
                'points': 0
        }
}
)
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
                 lookback: int = 15,
                 ote_min: float = 0.618,
                 ote_max: float = 0.786, **kwargs):
        """
        Initialize OTE detector with OPTIMIZED parameters (batch tuning 2026-01-01)
        
        Batch Optimization Results:
            Quality: 70/100
            Accuracy: 55.4%
            Signals: 2,460 in 180 days (13.7/day)
            R/R: 5.34 (good)
            Discovery: lookback=15 (vs 20) - faster = better (consistent pattern)
        
        Enhancements (2026-01-04 - Expert Mode):
            Precise OTE detection, retracement strength, swing strength
        """
        self.timeframe = timeframe
        self.lookback = lookback
        self.ote_min = ote_min
        self.ote_max = ote_max
        self.precise_ote = 0.705  # 70.5% equilibrium (ICT)
    
    def _determine_dual_signals(self, ote_type: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        if ote_type == 'BULLISH_OTE':
            granular = 'BULLISH_OTE'
            simple = 'BULLISH'
        elif ote_type == 'BEARISH_OTE':
            granular = 'BEARISH_OTE'
            simple = 'BEARISH'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        return granular, simple
    
    def is_precise_ote(self, retracement_pct: float) -> bool:
        """
        Check if at precise OTE (70.5% ± 2%) - Priority 1.1
        
        ICT's precise OTE is 70.5% (equilibrium between 61.8% and 78.6%)
        """
        return 68.5 <= retracement_pct <= 72.5
    
    def classify_retracement_strength(self, retracement_pct: float) -> str:
        """
        Classify retracement strength - Priority 1.2
        
        Returns:
            'SHALLOW': 61.8-67% (weak retracement)
            'MODERATE': 67-74% (typical retracement)
            'DEEP': 74-78.6% (deep retracement)
        """
        if retracement_pct < 67:
            return 'SHALLOW'
        elif retracement_pct <= 74:
            return 'MODERATE'
        else:
            return 'DEEP'
    
    def calculate_swing_strength(self, df: pd.DataFrame, swing_range: float) -> str:
        """
        Measure swing strength relative to ATR - Priority 1.3
        
        Strong swings (>2x ATR) = higher probability OTE
        
        Returns:
            'WEAK': <1x ATR
            'MODERATE': 1-2x ATR
            'STRONG': 2-3x ATR
            'VERY_STRONG': >3x ATR
        """
        if len(df) < 14:
            return 'MODERATE'  # Default if insufficient data
        
        # Calculate ATR(14)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.tail(14).mean()
        
        if atr == 0:
            return 'MODERATE'
        
        # Swing strength as multiple of ATR
        swing_strength_ratio = swing_range / atr
        
        if swing_strength_ratio >= 3.0:
            return 'VERY_STRONG'
        elif swing_strength_ratio >= 2.0:
            return 'STRONG'
        elif swing_strength_ratio >= 1.0:
            return 'MODERATE'
        else:
            return 'WEAK'
    
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
            retracement_pct = round(retracement * 100, 2)
            
            # **ENHANCED:** Calculate quality metrics
            at_precise_ote = self.is_precise_ote(retracement_pct)
            retracement_strength = self.classify_retracement_strength(retracement_pct)
            swing_strength = self.calculate_swing_strength(df, ote_zone['move_range'])
            
            return {
                'type': 'BULLISH_OTE',
                'ote_high': ote_zone['ote_high'],
                'ote_low': ote_zone['ote_low'],
                'swing_high': ote_zone['swing_high'],
                'swing_low': ote_zone['swing_low'],
                'current_price': float(current_close),
                'retracement_pct': retracement_pct,
                'timestamp': df['timestamp'].iloc[-1],
                'at_precise_ote': at_precise_ote,  # NEW: 70.5% flag
                'retracement_strength': retracement_strength,  # NEW: Quality tier
                'swing_strength': swing_strength  # NEW: Context
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
            retracement_pct = round(retracement * 100, 2)
            
            # **ENHANCED:** Calculate quality metrics
            at_precise_ote = self.is_precise_ote(retracement_pct)
            retracement_strength = self.classify_retracement_strength(retracement_pct)
            swing_strength = self.calculate_swing_strength(df, move_range)
            
            return {
                'type': 'BEARISH_OTE',
                'ote_high': float(ote_high),
                'ote_low': float(ote_low),
                'swing_high': float(swing_high),
                'swing_low': float(swing_low),
                'current_price': float(current_close),
                'retracement_pct': retracement_pct,
                'timestamp': df['timestamp'].iloc[-1],
                'at_precise_ote': at_precise_ote,  # NEW: 70.5% flag
                'retracement_strength': retracement_strength,  # NEW: Quality tier
                'swing_strength': swing_strength  # NEW: Context
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
        
        # **ENHANCED:** Calculate confidence with quality metrics
        confidence = 90  # Base confidence for OTE
        
        # Precise OTE bonus (70.5% ± 2%)
        if active_ote['at_precise_ote']:
            confidence += 10
        
        # Swing strength bonus
        if active_ote['swing_strength'] == 'VERY_STRONG':
            confidence += 5
        elif active_ote['swing_strength'] == 'STRONG':
            confidence += 3
        
        confidence = min(100, confidence)
        
        # **ENHANCED:** Build confluence factors with quality metrics
        confluence_factors = []
        confluence_factors.append(f'OTE Type: {active_ote["type"]}')
        
        # Retracement with strength
        retr_str = active_ote['retracement_strength']
        confluence_factors.append(f'Retracement: {active_ote["retracement_pct"]:.1f}% ({retr_str})')
        
        # Precise OTE indicator
        if active_ote['at_precise_ote']:
            confluence_factors.append('🎯 PRECISE OTE (70.5%): Highest probability entry!')
        
        # Swing strength indicator
        swing_str = active_ote['swing_strength']
        if swing_str in ['STRONG', 'VERY_STRONG']:
            confluence_factors.append(f'💪 {swing_str} SWING: High conviction setup!')
        
        confluence_factors.append(f'OTE Zone: ${active_ote["ote_low"]:.2f} - ${active_ote["ote_high"]:.2f}')
        confluence_factors.append('Optimal entry zone - institutional interest')
        confluence_factors.append('High probability continuation setup')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(active_ote['type'])
        
        # **ENHANCED:** Metadata with quality metrics
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'ote_type': active_ote['type'],
            'ote_high': active_ote['ote_high'],
            'ote_low': active_ote['ote_low'],
            'swing_high': active_ote['swing_high'],
            'swing_low': active_ote['swing_low'],
            'current_price': active_ote['current_price'],
            'retracement_pct': active_ote['retracement_pct'],
            'ote_timestamp': active_ote['timestamp'],
            'at_precise_ote': active_ote['at_precise_ote'],  # NEW: 70.5% flag
            'retracement_strength': active_ote['retracement_strength'],  # NEW: Quality
            'swing_strength': active_ote['swing_strength']  # NEW: Context
        }
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
