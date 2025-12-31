"""
Break of Structure (BOS) Building Block
Category: SMC/ICT
Purpose: Detect trend continuation - Break of Structure ICT concept
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class BreakOfStructure:
    """
    Break of Structure (BOS) Detector - ICT/SMC Concept
    
    Identifies when price breaks structure in the direction of the existing trend,
    indicating trend continuation rather than reversal.
    
    BOS vs MSS:
    - BOS: Break in trend direction = continuation
    - MSS: Break against trend = reversal
    
    BOS Criteria:
    - Bullish BOS: In uptrend, break above previous swing high
    - Bearish BOS: In downtrend, break below previous swing low
    - Indicates trend continuation
    - Entry opportunity in trend direction
    
    Parameters:
        swing_lookback: Periods for swing detection (default: 10)
        min_break_pct: Minimum break % to confirm (default: 0.1%)
    """
    
    def __init__(self, timeframe: str = '15min',
                 swing_lookback: int = 10,
                 min_break_pct: float = 0.1, **kwargs):
        """Initialize BOS detector"""
        self.timeframe = timeframe
        self.swing_lookback = swing_lookback
        self.min_break_pct = min_break_pct
    
    def determine_trend(self, df: pd.DataFrame) -> str:
        """Determine current trend from recent price action"""
        if len(df) < 20:
            return 'NEUTRAL'
        
        recent = df.tail(20)
        highs_increasing = recent['high'].iloc[-1] > recent['high'].iloc[0]
        lows_increasing = recent['low'].iloc[-1] > recent['low'].iloc[0]
        
        if highs_increasing and lows_increasing:
            return 'UPTREND'
        elif not highs_increasing and not lows_increasing:
            return 'DOWNTREND'
        else:
            return 'NEUTRAL'
    
    def find_swing_high(self, df: pd.DataFrame, idx: int) -> float:
        """Find swing high at index"""
        lookback_start = max(0, idx - self.swing_lookback)
        lookback_data = df.iloc[lookback_start:idx+1]
        return lookback_data['high'].max() if len(lookback_data) > 0 else None
    
    def find_swing_low(self, df: pd.DataFrame, idx: int) -> float:
        """Find swing low at index"""
        lookback_start = max(0, idx - self.swing_lookback)
        lookback_data = df.iloc[lookback_start:idx+1]
        return lookback_data['low'].min() if len(lookback_data) > 0 else None
    
    def detect_bullish_bos(self, df: pd.DataFrame, trend: str) -> Dict[str, Any]:
        """Detect bullish BOS (in uptrend, break above swing high)"""
        if trend != 'UPTREND':
            return None
        
        if len(df) < self.swing_lookback + 5:
            return None
        
        # Look for break above previous swing high in uptrend
        for i in range(len(df) - 1, self.swing_lookback, -1):
            swing_high = self.find_swing_high(df, i-1)
            if swing_high is None:
                continue
            
            current_high = df['high'].iloc[i]
            if current_high > swing_high:
                break_pct = ((current_high - swing_high) / swing_high) * 100
                if break_pct >= self.min_break_pct:
                    return {
                        'type': 'BULLISH_BOS',
                        'index': i,
                        'swing_high': float(swing_high),
                        'break_high': float(current_high),
                        'break_pct': round(break_pct, 3),
                        'trend': trend,
                        'timestamp': df['timestamp'].iloc[i]
                    }
        return None
    
    def detect_bearish_bos(self, df: pd.DataFrame, trend: str) -> Dict[str, Any]:
        """Detect bearish BOS (in downtrend, break below swing low)"""
        if trend != 'DOWNTREND':
            return None
        
        if len(df) < self.swing_lookback + 5:
            return None
        
        # Look for break below previous swing low in downtrend
        for i in range(len(df) - 1, self.swing_lookback, -1):
            swing_low = self.find_swing_low(df, i-1)
            if swing_low is None:
                continue
            
            current_low = df['low'].iloc[i]
            if current_low < swing_low:
                break_pct = ((swing_low - current_low) / swing_low) * 100
                if break_pct >= self.min_break_pct:
                    return {
                        'type': 'BEARISH_BOS',
                        'index': i,
                        'swing_low': float(swing_low),
                        'break_low': float(current_low),
                        'break_pct': round(break_pct, 3),
                        'trend': trend,
                        'timestamp': df['timestamp'].iloc[i]
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
        
        if len(df) < self.swing_lookback + 20:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.swing_lookback + 20} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Determine current trend
        trend = self.determine_trend(df)
        
        if trend == 'NEUTRAL':
            return {
                'signal': 'NEUTRAL',
                'confidence': 0,
                'metadata': {'trend': 'NEUTRAL', 'error': 'No clear trend for BOS detection'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['No clear trend - BOS requires established trend']
            }
        
        # Detect BOS based on trend
        bullish_bos = self.detect_bullish_bos(df, trend) if trend == 'UPTREND' else None
        bearish_bos = self.detect_bearish_bos(df, trend) if trend == 'DOWNTREND' else None
        
        # Choose most recent
        active_bos = None
        signal = 'NEUTRAL'
        
        if bullish_bos:
            active_bos = bullish_bos
            signal = 'BULLISH'
        elif bearish_bos:
            active_bos = bearish_bos
            signal = 'BEARISH'
        
        if not active_bos:
            return {
                'signal': 'NO_BOS',
                'confidence': 0,
                'metadata': {'trend': trend, 'error': 'No break of structure detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': [f'Trend: {trend}', 'No BOS yet - waiting for structure break']
            }
        
        # Calculate confidence
        confidence = 80  # High confidence for BOS in trend
        if active_bos['break_pct'] > 0.5:
            confidence += 10
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        confluence_factors.append(f'BOS Type: {active_bos["type"]}')
        confluence_factors.append(f'Trend: {active_bos["trend"]} (confirmed)')
        confluence_factors.append(f'Break Strength: {active_bos["break_pct"]:.3f}%')
        confluence_factors.append('Structure broken in trend direction')
        confluence_factors.append('Trend continuation signal - high probability')
        
        # Metadata
        if active_bos['type'] == 'BULLISH_BOS':
            metadata = {
                'bos_type': active_bos['type'],
                'trend': active_bos['trend'],
                'swing_high': active_bos['swing_high'],
                'break_high': active_bos['break_high'],
                'break_pct': active_bos['break_pct'],
                'bos_timestamp': active_bos['timestamp']
            }
        else:
            metadata = {
                'bos_type': active_bos['type'],
                'trend': active_bos['trend'],
                'swing_low': active_bos['swing_low'],
                'break_low': active_bos['break_low'],
                'break_pct': active_bos['break_pct'],
                'bos_timestamp': active_bos['timestamp']
            }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
