"""
Liquidity Sweep Building Block
Category: Advanced Price Action
Purpose: Detect liquidity sweeps - price hunting stops before reversing - ICT concept
"""

from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
import numpy as np


class LiquiditySweep:
    """
    Liquidity Sweep Detector - ICT/SMC Concept
    
    Identifies when price sweeps above/below a key level to trigger stop losses
    (take liquidity) before reversing. Classic institutional manipulation pattern.
    
    Characteristics:
    - Price spikes above resistance or below support
    - Quick reversal (wick)
    - Often happens at session highs/lows
    - Indicates institutional stop hunting
    
    Types:
    - Bullish Sweep: Sweeps below support, then reverses up
    - Bearish Sweep: Sweeps above resistance, then reverses down
    
    Parameters:
        min_sweep_pct: Minimum sweep distance % (default: 0.15%)
        max_wick_pct: Maximum wick size vs body (default: 70%)
        lookback: Periods to look back (default: 20)
    """
    
    def __init__(self, timeframe: str = '15min',
                 min_sweep_pct: float = 0.15,
                 max_wick_pct: float = 70.0,
                 lookback: int = 20, **kwargs):
        """Initialize Liquidity Sweep detector"""
        self.timeframe = timeframe
        self.min_sweep_pct = min_sweep_pct
        self.max_wick_pct = max_wick_pct
        self.lookback = lookback
    
    def detect_bullish_sweep(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect bullish liquidity sweep (sweep low, reverse up)"""
        if len(df) < 3:
            return None
        
        for i in range(len(df) - 1, max(len(df) - self.lookback, 1), -1):
            candle = df.iloc[i]
            
            # Find recent support (lowest low in lookback)
            lookback_data = df.iloc[max(0, i-self.lookback):i]
            if len(lookback_data) == 0:
                continue
            
            support = lookback_data['low'].min()
            
            # Check if current candle swept below support
            sweep_distance = support - candle['low']
            if sweep_distance <= 0:
                continue
            
            sweep_pct = (sweep_distance / support) * 100
            
            # Check if it's a wick (close above the sweep)
            if candle['close'] < candle['low']:
                continue
            
            # Calculate wick vs body
            body_size = abs(candle['close'] - candle['open'])
            lower_wick = min(candle['close'], candle['open']) - candle['low']
            
            if body_size == 0:
                wick_ratio = 100
            else:
                wick_ratio = (lower_wick / body_size)  * 100
            
            if sweep_pct >= self.min_sweep_pct and wick_ratio <= self.max_wick_pct:
                return {
                    'type': 'BULLISH_SWEEP',
                    'index': i,
                    'support_level': float(support),
                    'sweep_low': float(candle['low']),
                    'close': float(candle['close']),
                    'sweep_pct': round(sweep_pct, 3),
                    'wick_ratio': round(wick_ratio, 1),
                    'timestamp': candle['timestamp']
                }
        
        return None
    
    def detect_bearish_sweep(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect bearish liquidity sweep (sweep high, reverse down)"""
        if len(df) < 3:
            return None
        
        for i in range(len(df) - 1, max(len(df) - self.lookback, 1), -1):
            candle = df.iloc[i]
            
            # Find recent resistance (highest high in lookback)
            lookback_data = df.iloc[max(0, i-self.lookback):i]
            if len(lookback_data) == 0:
                continue
            
            resistance = lookback_data['high'].max()
            
            # Check if current candle swept above resistance
            sweep_distance = candle['high'] - resistance
            if sweep_distance <= 0:
                continue
            
            sweep_pct = (sweep_distance / resistance) * 100
            
            # Check if it's a wick (close below the sweep)
            if candle['close'] > candle['high']:
                continue
            
            # Calculate wick vs body
            body_size = abs(candle['close'] - candle['open'])
            upper_wick = candle['high'] - max(candle['close'], candle['open'])
            
            if body_size == 0:
                wick_ratio = 100
            else:
                wick_ratio = (upper_wick / body_size) * 100
            
            if sweep_pct >= self.min_sweep_pct and wick_ratio <= self.max_wick_pct:
                return {
                    'type': 'BEARISH_SWEEP',
                    'index': i,
                    'resistance_level': float(resistance),
                    'sweep_high': float(candle['high']),
                    'close': float(candle['close']),
                    'sweep_pct': round(sweep_pct, 3),
                    'wick_ratio': round(wick_ratio, 1),
                    'timestamp': candle['timestamp']
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
        
        if len(df) < 5:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 5 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect both types
        bullish_sweep = self.detect_bullish_sweep(df)
        bearish_sweep = self.detect_bearish_sweep(df)
        
        # Choose most recent
        active_sweep = None
        signal = 'NEUTRAL'
        
        if bullish_sweep and (not bearish_sweep or bullish_sweep['index'] > bearish_sweep['index']):
            active_sweep = bullish_sweep
            signal = 'BULLISH'
        elif bearish_sweep:
            active_sweep = bearish_sweep
            signal = 'BEARISH'
        
        if not active_sweep:
            return {
                'signal': 'NO_SWEEP',
                'confidence': 0,
                'metadata': {'error': 'No liquidity sweep detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate confidence
        confidence = 80  # High confidence for sweeps
        if active_sweep['sweep_pct'] > 0.3:
            confidence += 10
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        confluence_factors.append(f'Sweep Type: {active_sweep["type"]}')
        confluence_factors.append(f'Sweep Distance: {active_sweep["sweep_pct"]:.3f}%')
        confluence_factors.append(f'Wick Ratio: {active_sweep["wick_ratio"]:.1f}%')
        confluence_factors.append('Liquidity hunted - institutional manipulation')
        confluence_factors.append('High probability reversal setup')
        
        # Metadata
        if active_sweep['type'] == 'BULLISH_SWEEP':
            metadata = {
                'sweep_type': active_sweep['type'],
                'support_level': active_sweep['support_level'],
                'sweep_low': active_sweep['sweep_low'],
                'close': active_sweep['close'],
                'sweep_pct': active_sweep['sweep_pct'],
                'wick_ratio': active_sweep['wick_ratio'],
                'sweep_timestamp': active_sweep['timestamp']
            }
        else:
            metadata = {
                'sweep_type': active_sweep['type'],
                'resistance_level': active_sweep['resistance_level'],
                'sweep_high': active_sweep['sweep_high'],
                'close': active_sweep['close'],
                'sweep_pct': active_sweep['sweep_pct'],
                'wick_ratio': active_sweep['wick_ratio'],
                'sweep_timestamp': active_sweep['timestamp']
            }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
