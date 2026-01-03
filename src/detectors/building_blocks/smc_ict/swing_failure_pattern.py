"""
Swing Failure Pattern (SFP) Building Block
Category: SMC/ICT
Purpose: Detect swing failure patterns - ICT failed swing concept
"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class SwingFailurePattern:
    """
    Swing Failure Pattern (SFP) Detector - ICT/SMC Concept
    
    Identifies when price attempts to make new swing high/low but fails,
    indicating a reversal. SFP is a stop hunt that fails to continue,
    trapping breakout traders.
    
    SFP Characteristics:
    - Attempts to break swing high/low
    - Fails to close beyond it (or closes back inside)
    - Quick reversal in opposite direction
    - Traps breakout traders
    
    Types:
    - Bullish SFP: Failed swing low → reversal up
    - Bearish SFP: Failed swing high → reversal down
    
    Trading Application:
    - Counter-trend entry signal  
    - Stop hunt reversal
    - High probability setups
    
    Parameters:
        swing_lookback: Periods for swing detection (default: 10)
        failure_threshold: % penetration to confirm (default: 0.1%)
        reversal_window: Bars to check for reversal (default: 3)
    """
    
    def __init__(self, timeframe: str = '15min',
                 lookback: int = 10,
                 failure_threshold_pct: float = 0.1,
                 reversal_window: int = 3,
                 **kwargs):
        """
        Initialize SFP detector with FIXED parameters
        
        FIXES APPLIED (2026-01-02):
        - Changed NO_SFP to NEUTRAL (proper signal naming)
        - Expanded reversal detection window (2 → 3 bars)
        - Allow reversal across multiple candles (not just same candle)
        - Lowered threshold for more sensitivity (0.3 → 0.1)
        - Improved SFP detection logic
        """
        self.timeframe = timeframe
        self.swing_lookback = lookback
        self.failure_threshold = failure_threshold_pct
        self.reversal_window = reversal_window
    
    def find_swing_high(self, df: pd.DataFrame) -> Optional[float]:
        """Find recent swing high"""
        if len(df) < self.swing_lookback:
            return None
        recent = df.tail(self.swing_lookback)
        return float(recent['high'].max())
    
    def find_swing_low(self, df: pd.DataFrame) -> Optional[float]:
        """Find recent swing low"""
        if len(df) < self.swing_lookback:
            return None
        recent = df.tail(self.swing_lookback)
        return float(recent['low'].min())
    
    def detect_bullish_sfp(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bullish SFP (failed swing low)
        
        IMPROVED LOGIC:
        - Check last N candles for break attempt
        - Allow reversal across multiple candles
        - More flexible detection
        """
        if len(df) < self.swing_lookback + self.reversal_window:
            return None
        
        # Find swing low from earlier data (exclude recent reversal window)
        swing_low = self.find_swing_low(df.iloc[:-self.reversal_window])
        if swing_low is None:
            return None
        
        # Check recent candles for break attempt and reversal
        recent = df.tail(self.reversal_window)
        
        # Look for candle that broke below swing low
        break_candle_idx = None
        failure_low = None
        penetration_pct = 0
        
        for idx in range(len(recent)):
            if recent.iloc[idx]['low'] < swing_low:
                pct = ((swing_low - recent.iloc[idx]['low']) / swing_low) * 100
                if pct >= self.failure_threshold:
                    break_candle_idx = idx
                    failure_low = float(recent.iloc[idx]['low'])
                    penetration_pct = pct
                    break
        
        # If no break, no SFP
        if break_candle_idx is None:
            return None
        
        # Check for reversal: either same candle closes back above, 
        # or subsequent candle(s) push back above swing low
        reversal_found = False
        recovery_close = None
        
        # Check if break candle itself closed back above (classic SFP)
        if recent.iloc[break_candle_idx]['close'] > swing_low:
            reversal_found = True
            recovery_close = float(recent.iloc[break_candle_idx]['close'])
        else:
            # Check subsequent candles for reversal back above
            for idx in range(break_candle_idx + 1, len(recent)):
                if recent.iloc[idx]['close'] > swing_low:
                    reversal_found = True
                    recovery_close = float(recent.iloc[idx]['close'])
                    break
        
        if not reversal_found:
            return None
        
        return {
            'type': 'BULLISH_SFP',
            'swing_low': swing_low,
            'failure_low': failure_low,
            'recovery_close': recovery_close,
            'penetration_pct': round(penetration_pct, 3),
            'timestamp': recent.iloc[-1]['timestamp']
        }
    
    def detect_bearish_sfp(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bearish SFP (failed swing high)
        
        IMPROVED LOGIC:
        - Check last N candles for break attempt
        - Allow reversal across multiple candles
        - More flexible detection
        """
        if len(df) < self.swing_lookback + self.reversal_window:
            return None
        
        # Find swing high from earlier data (exclude recent reversal window)
        swing_high = self.find_swing_high(df.iloc[:-self.reversal_window])
        if swing_high is None:
            return None
        
        # Check recent candles for break attempt and reversal
        recent = df.tail(self.reversal_window)
        
        # Look for candle that broke above swing high
        break_candle_idx = None
        failure_high = None
        penetration_pct = 0
        
        for idx in range(len(recent)):
            if recent.iloc[idx]['high'] > swing_high:
                pct = ((recent.iloc[idx]['high'] - swing_high) / swing_high) * 100
                if pct >= self.failure_threshold:
                    break_candle_idx = idx
                    failure_high = float(recent.iloc[idx]['high'])
                    penetration_pct = pct
                    break
        
        # If no break, no SFP
        if break_candle_idx is None:
            return None
        
        # Check for reversal: either same candle closes back below,
        # or subsequent candle(s) push back below swing high
        reversal_found = False
        recovery_close = None
        
        # Check if break candle itself closed back below (classic SFP)
        if recent.iloc[break_candle_idx]['close'] < swing_high:
            reversal_found = True
            recovery_close = float(recent.iloc[break_candle_idx]['close'])
        else:
            # Check subsequent candles for reversal back below
            for idx in range(break_candle_idx + 1, len(recent)):
                if recent.iloc[idx]['close'] < swing_high:
                    reversal_found = True
                    recovery_close = float(recent.iloc[idx]['close'])
                    break
        
        if not reversal_found:
            return None
        
        return {
            'type': 'BEARISH_SFP',
            'swing_high': swing_high,
            'failure_high': failure_high,
            'recovery_close': recovery_close,
            'penetration_pct': round(penetration_pct, 3),
            'timestamp': recent.iloc[-1]['timestamp']
        }
    
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
        
        if len(df) < self.swing_lookback + self.reversal_window + 2:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.swing_lookback + self.reversal_window + 2} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect both types
        bullish_sfp = self.detect_bullish_sfp(df)
        bearish_sfp = self.detect_bearish_sfp(df)
        
        # Choose active SFP
        active_sfp = None
        signal = 'NEUTRAL'
        
        if bullish_sfp:
            active_sfp = bullish_sfp
            signal = 'BULLISH'
        elif bearish_sfp:
            active_sfp = bearish_sfp
            signal = 'BEARISH'
        
        # FIXED: Return NEUTRAL instead of NO_SFP to avoid validation confusion
        if not active_sfp:
            return {
                'signal': 'NEUTRAL',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate confidence based on penetration depth
        # Deeper penetration = stronger SFP = higher confidence
        base_confidence = 75  # Base for any SFP
        
        # Add confidence based on penetration
        pen = active_sfp['penetration_pct']
        if pen > 0.5:
            base_confidence += 15  # Deep penetration
        elif pen > 0.3:
            base_confidence += 10  # Good penetration
        elif pen > 0.1:
            base_confidence += 5   # Minimal penetration
        
        confidence = min(95, base_confidence)
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'SFP Type: {active_sfp["type"]}')
        confluence_factors.append(f'Penetration: {active_sfp["penetration_pct"]:.3f}%')
        confluence_factors.append('Failed swing - stop hunt reversal')
        confluence_factors.append('Breakout traders trapped')
        confluence_factors.append('High probability counter-trend entry')
        
        # Metadata
        if active_sfp['type'] == 'BULLISH_SFP':
            metadata = {
                'sfp_type': active_sfp['type'],
                'swing_low': active_sfp['swing_low'],
                'failure_low': active_sfp['failure_low'],
                'recovery_close': active_sfp['recovery_close'],
                'penetration_pct': active_sfp['penetration_pct'],
                'sfp_timestamp': active_sfp['timestamp']
            }
        else:
            metadata = {
                'sfp_type': active_sfp['type'],
                'swing_high': active_sfp['swing_high'],
                'failure_high': active_sfp['failure_high'],
                'recovery_close': active_sfp['recovery_close'],
                'penetration_pct': active_sfp['penetration_pct'],
                'sfp_timestamp': active_sfp['timestamp']
            }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
