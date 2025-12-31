"""
Inducement Building Block
Category: SMC/ICT
Purpose: Detect inducement patterns - ICT liquidity trap concept
"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class Inducement:
    """
    Inducement Detector - ICT/SMC Concept
    
    Identifies when price creates false moves (inducement) to trap traders
    before reversing. Smart money uses inducement to grab liquidity before
    the real move.
    
    Inducement Characteristics:
    - False break of key level
    - Quick reversal after break
    - Traps breakout traders
    - Precedes strong move in opposite direction
    
    Types:
    - Bullish Inducement: False breakdown → reversal up
    - Bearish Inducement: False breakout → reversal down
    
    Trading Application:
    - Wait for inducement to complete
    - Enter on reversal after trap
    - High probability setups
    
    Parameters:
        lookback: Periods for level detection (default: 10)
        reversal_threshold: % reversal to confirm trap (default: 0.3%)
    """
    
    def __init__(self, timeframe: str = '15min',
                 lookback: int = 10,
                 reversal_threshold: float = 0.3, **kwargs):
        """Initialize Inducement detector"""
        self.timeframe = timeframe
        self.lookback = lookback
        self.reversal_threshold = reversal_threshold
    
    def find_recent_high(self, df: pd.DataFrame) -> Optional[float]:
        """Find recent swing high"""
        if len(df) < self.lookback:
            return None
        recent = df.tail(self.lookback)
        return float(recent['high'].max())
    
    def find_recent_low(self, df: pd.DataFrame) -> Optional[float]:
        """Find recent swing low"""
        if len(df) < self.lookback:
            return None
        recent = df.tail(self.lookback)
        return float(recent['low'].min())
    
    def detect_bullish_inducement(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bullish inducement (false breakdown followed by reversal up)
        """
        if len(df) < self.lookback + 3:
            return None
        
        # Find recent swing low
        swing_low = self.find_recent_low(df.iloc[:-3])
        if swing_low is None:
            return None
        
        # Check for false break below swing low
        recent_bars = df.tail(3)
        broke_below = False
        break_low = None
        
        for idx in range(len(recent_bars) - 1):
            if recent_bars.iloc[idx]['low'] < swing_low:
                broke_below = True
                break_low = float(recent_bars.iloc[idx]['low'])
                break
        
        if not broke_below:
            return None
        
        # Check for reversal back above
        current_close = df['close'].iloc[-1]
        if current_close > swing_low:
            reversal_pct = ((current_close - break_low) / break_low) * 100
            if reversal_pct >= self.reversal_threshold:
                return {
                    'type': 'BULLISH_INDUCEMENT',
                    'swing_low': swing_low,
                    'break_low': break_low,
                    'reversal_close': float(current_close),
                    'reversal_pct': round(reversal_pct, 3),
                    'timestamp': df['timestamp'].iloc[-1]
                }
        
        return None
    
    def detect_bearish_inducement(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bearish inducement (false breakout followed by reversal down)
        """
        if len(df) < self.lookback + 3:
            return None
        
        # Find recent swing high
        swing_high = self.find_recent_high(df.iloc[:-3])
        if swing_high is None:
            return None
        
        # Check for false break above swing high
        recent_bars = df.tail(3)
        broke_above = False
        break_high = None
        
        for idx in range(len(recent_bars) - 1):
            if recent_bars.iloc[idx]['high'] > swing_high:
                broke_above = True
                break_high = float(recent_bars.iloc[idx]['high'])
                break
        
        if not broke_above:
            return None
        
        # Check for reversal back below
        current_close = df['close'].iloc[-1]
        if current_close < swing_high:
            reversal_pct = ((break_high - current_close) / break_high) * 100
            if reversal_pct >= self.reversal_threshold:
                return {
                    'type': 'BEARISH_INDUCEMENT',
                    'swing_high': swing_high,
                    'break_high': break_high,
                    'reversal_close': float(current_close),
                    'reversal_pct': round(reversal_pct, 3),
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
        
        # Detect both types of inducement
        bullish_ind = self.detect_bullish_inducement(df)
        bearish_ind = self.detect_bearish_inducement(df)
        
        # Choose active inducement
        active_ind = None
        signal = 'NEUTRAL'
        
        if bullish_ind:
            active_ind = bullish_ind
            signal = 'BULLISH'
        elif bearish_ind:
            active_ind = bearish_ind
            signal = 'BEARISH'
        
        if not active_ind:
            return {
                'signal': 'NO_INDUCEMENT',
                'confidence': 0,
                'metadata': {'error': 'No inducement pattern detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['No inducement - clean price action']
            }
        
        # Calculate confidence based on reversal strength
        confidence = 75  # Base confidence for inducement
        if active_ind['reversal_pct'] > 0.5:
            confidence += 10
        if active_ind['reversal_pct'] > 1.0:
            confidence += 10
        confidence = min(100, confidence)
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'Inducement Type: {active_ind["type"]}')
        confluence_factors.append(f'Reversal Strength: {active_ind["reversal_pct"]:.3f}%')
        confluence_factors.append('Liquidity trap detected - Smart money move')
        confluence_factors.append('Breakout traders trapped')
        confluence_factors.append('High probability reversal setup')
        
        # Metadata
        if active_ind['type'] == 'BULLISH_INDUCEMENT':
            metadata = {
                'inducement_type': active_ind['type'],
                'swing_low': active_ind['swing_low'],
                'break_low': active_ind['break_low'],
                'reversal_close': active_ind['reversal_close'],
                'reversal_pct': active_ind['reversal_pct'],
                'inducement_timestamp': active_ind['timestamp']
            }
        else:
            metadata = {
                'inducement_type': active_ind['type'],
                'swing_high': active_ind['swing_high'],
                'break_high': active_ind['break_high'],
                'reversal_close': active_ind['reversal_close'],
                'reversal_pct': active_ind['reversal_pct'],
                'inducement_timestamp': active_ind['timestamp']
            }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
