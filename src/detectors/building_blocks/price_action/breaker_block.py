"""
Breaker Block Building Block
Category: Advanced Price Action
Purpose: Identify breaker blocks - failed order blocks that reverse - ICT concept
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class BreakerBlock:
    """
    Breaker Block Detector - ICT/SMC Concept
    
    A Breaker Block is a failed Order Block that has been broken through,
    which now acts as the OPPOSITE type:
    - Bullish OB broken down → becomes Bearish Breaker
    - Bearish OB broken up → becomes Bullish Breaker
    
    Significance:
    - Shows change in market structure
    - Indicates institutional positioning change
    - High probability reversal zones
    - Strong support/resistance after break
    
    Parameters:
        min_break_pct: Minimum % break through OB (default: 0.3%)
        lookback: Periods to look back (default: 50)
    """
    
    def __init__(self, timeframe: str = '15min',
                 min_break_pct: float = 0.3,
                 lookback: int = 50, **kwargs):
        """Initialize Breaker Block detector"""
        self.timeframe = timeframe
        self.min_break_pct = min_break_pct
        self.lookback = lookback
    
    def detect_bullish_breaker(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect bullish breaker (bearish OB broken up)"""
        if len(df) < 5:
            return None
        
        for i in range(len(df) - 5, max(len(df) - self.lookback, 0), -1):
            # Look for up candle (potential bearish OB)
            if df['close'].iloc[i] <= df['open'].iloc[i]:
                continue
            
            ob_high = df['high'].iloc[i]
            ob_low = df['low'].iloc[i]
            
            # Check if broken upward (price closes above OB high)
            for j in range(i+1, min(i+10, len(df))):
                if df['close'].iloc[j] > ob_high:
                    break_pct = ((df['close'].iloc[j] - ob_high) / ob_high) * 100
                    
                    if break_pct >= self.min_break_pct:
                        return {
                            'type': 'BULLISH_BREAKER',
                            'index': i,
                            'high': float(ob_high),
                            'low': float(ob_low),
                            'mid': float((ob_high + ob_low) / 2),
                            'break_pct': round(break_pct, 2),
                            'timestamp': df['timestamp'].iloc[i]
                        }
        
        return None
    
    def detect_bearish_breaker(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect bearish breaker (bullish OB broken down)"""
        if len(df) < 5:
            return None
        
        for i in range(len(df) - 5, max(len(df) - self.lookback, 0), -1):
            # Look for down candle (potential bullish OB)
            if df['close'].iloc[i] >= df['open'].iloc[i]:
                continue
            
            ob_high = df['high'].iloc[i]
            ob_low = df['low'].iloc[i]
            
            # Check if broken downward (price closes below OB low)
            for j in range(i+1, min(i+10, len(df))):
                if df['close'].iloc[j] < ob_low:
                    break_pct = ((ob_low - df['close'].iloc[j]) / ob_low) * 100
                    
                    if break_pct >= self.min_break_pct:
                        return {
                            'type': 'BEARISH_BREAKER',
                            'index': i,
                            'high': float(ob_high),
                            'low': float(ob_low),
                            'mid': float((ob_high + ob_low) / 2),
                            'break_pct': round(break_pct, 2),
                            'timestamp': df['timestamp'].iloc[i]
                        }
        
        return None
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['timestamp', 'open', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 10:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 10 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect both types
        bullish_breaker = self.detect_bullish_breaker(df)
        bearish_breaker = self.detect_bearish_breaker(df)
        
        current_price = float(df['close'].iloc[-1])
        
        # Determine active breaker
        active_breaker = None
        signal = 'NEUTRAL'
        
        if bullish_breaker and (not bearish_breaker or bullish_breaker['index'] > bearish_breaker['index']):
            active_breaker = bullish_breaker
            # Check if price near breaker zone
            if bullish_breaker['low'] <= current_price <= bullish_breaker['high'] * 1.01:
                signal = 'BULLISH'
        elif bearish_breaker:
            active_breaker = bearish_breaker
            # Check if price near breaker zone
            if bearish_breaker['low'] * 0.99 <= current_price <= bearish_breaker['high']:
                signal = 'BEARISH'
        
        if not active_breaker:
            return {
                'signal': 'NO_BREAKER',
                'confidence': 0,
                'metadata': {'error': 'No breaker block detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate confidence
        confidence = 75
        if active_breaker['break_pct'] > 0.5:
            confidence += 10
        if active_breaker['break_pct'] > 1.0:
            confidence += 10
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        confluence_factors.append(f'Breaker Type: {active_breaker["type"]}')
        confluence_factors.append(f'Zone: ${active_breaker["low"]:.2f} - ${active_breaker["high"]:.2f}')
        confluence_factors.append(f'Break Strength: {active_breaker["break_pct"]}%')
        confluence_factors.append('Failed OB now acting as opposite - structure change')
        
        if signal != 'NEUTRAL':
            confluence_factors.append('Price at breaker zone - high probability setup')
        
        # Metadata
        metadata = {
            'breaker_type': active_breaker['type'],
            'breaker_high': active_breaker['high'],
            'breaker_low': active_breaker['low'],
            'breaker_mid': active_breaker['mid'],
            'break_pct': active_breaker['break_pct'],
            'current_price': round(current_price, 2),
            'in_zone': signal != 'NEUTRAL',
            'breaker_timestamp': active_breaker['timestamp']
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
