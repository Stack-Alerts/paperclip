"""
Market Structure Shift (MSS) Building Block
Category: SMC/ICT
Purpose: Detect market structure changes - trend reversals ICT concept
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class MarketStructureShift:
    """
    Market Structure Shift (MSS) Detector - ICT/SMC Concept
    
    Identifies when market structure changes from bullish to bearish or vice versa.
    Critical for spotting trend reversals and institutional positioning changes.
    
    MSS Criteria:
    - Bullish MSS: Price breaks above previous swing high
    - Bearish MSS: Price breaks below previous swing low
    - Indicates potential trend change
    - Often precedes new directional move
    
    Parameters:
        swing_lookback: Periods for swing detection (default: 10)
        min_break_pct: Minimum break % to confirm (default: 0.1%)
    """
    
    def __init__(self, timeframe: str = '15min',
                 swing_lookback: int = 10,
                 min_break_pct: float = 0.1, **kwargs):
        """Initialize MSS detector"""
        self.timeframe = timeframe
        self.swing_lookback = swing_lookback
        self.min_break_pct = min_break_pct
    
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
    
    def detect_bullish_mss(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect bullish market structure shift"""
        if len(df) < self.swing_lookback + 5:
            return None
        
        # Look for break above previous swing high
        for i in range(len(df) - 1, self.swing_lookback, -1):
            swing_high = self.find_swing_high(df, i-1)
            if swing_high is None:
                continue
            
            current_high = df['high'].iloc[i]
            if current_high > swing_high:
                break_pct = ((current_high - swing_high) / swing_high) * 100
                if break_pct >= self.min_break_pct:
                    return {
                        'type': 'BULLISH_MSS',
                        'index': i,
                        'swing_high': float(swing_high),
                        'break_high': float(current_high),
                        'break_pct': round(break_pct, 3),
                        'timestamp': df['timestamp'].iloc[i]
                    }
        return None
    
    def detect_bearish_mss(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect bearish market structure shift"""
        if len(df) < self.swing_lookback + 5:
            return None
        
        # Look for break below previous swing low
        for i in range(len(df) - 1, self.swing_lookback, -1):
            swing_low = self.find_swing_low(df, i-1)
            if swing_low is None:
                continue
            
            current_low = df['low'].iloc[i]
            if current_low < swing_low:
                break_pct = ((swing_low - current_low) / swing_low) * 100
                if break_pct >= self.min_break_pct:
                    return {
                        'type': 'BEARISH_MSS',
                        'index': i,
                        'swing_low': float(swing_low),
                        'break_low': float(current_low),
                        'break_pct': round(break_pct, 3),
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
        
        if len(df) < self.swing_lookback + 5:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.swing_lookback + 5} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect both types
        bullish_mss = self.detect_bullish_mss(df)
        bearish_mss = self.detect_bearish_mss(df)
        
        # Choose most recent
        active_mss = None
        signal = 'NEUTRAL'
        
        if bullish_mss and (not bearish_mss or bullish_mss['index'] > bearish_mss['index']):
            active_mss = bullish_mss
            signal = 'BULLISH'
        elif bearish_mss:
            active_mss = bearish_mss
            signal = 'BEARISH'
        
        if not active_mss:
            return {
                'signal': 'NO_MSS',
                'confidence': 0,
                'metadata': {'error': 'No market structure shift detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate confidence
        confidence = 85  # High confidence for MSS
        if active_mss['break_pct'] > 0.5:
            confidence += 10
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        confluence_factors.append(f'MSS Type: {active_mss["type"]}')
        confluence_factors.append(f'Break Strength: {active_mss["break_pct"]:.3f}%')
        confluence_factors.append('Market structure changed - trend reversal signal')
        confluence_factors.append('Institutional positioning shift likely')
        
        # Metadata
        if active_mss['type'] == 'BULLISH_MSS':
            metadata = {
                'mss_type': active_mss['type'],
                'swing_high': active_mss['swing_high'],
                'break_high': active_mss['break_high'],
                'break_pct': active_mss['break_pct'],
                'mss_timestamp': active_mss['timestamp']
            }
        else:
            metadata = {
                'mss_type': active_mss['type'],
                'swing_low': active_mss['swing_low'],
                'break_low': active_mss['break_low'],
                'break_pct': active_mss['break_pct'],
                'mss_timestamp': active_mss['timestamp']
            }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
