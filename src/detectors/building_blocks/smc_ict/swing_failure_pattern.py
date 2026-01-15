"""
Swing Failure Pattern (SFP) Building Block
Category: SMC/ICT
Purpose: Detect swing failure patterns - ICT failed swing concept

ENHANCEMENTS (2026-01-04):
- Priority 1.1: Penetration strength classification
- Priority 1.2: Swing strength context (ATR-relative)
- Priority 1.3: Multiple failure detection (momentum tracking)
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: SFP detection, fires on failure pattern

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='swing_failure_pattern',
    category='SMC_ICT',
    class_name='SwingFailurePattern',
    default_weight=20,
    valid_signals=[
        # Granular SMC signals
        'BEARISH_SFP', 'BULLISH_SFP',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BEARISH_SFP': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish SFP - Swing failure pattern bearish. Failed breakout up then reversal. Enter shorts. Stop hunt complete. Liquidity grabbed. Reversal confirmed.'
        },
        'BULLISH_SFP': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish SFP - Swing failure pattern bullish. Failed breakdown then reversal. Enter longs. Stop hunt complete. Liquidity grabbed. Reversal confirmed.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot calculate swing failure pattern. Check data quality and required columns.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need enough bars for SFP detection. Wait for more price history and swing points.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish SFP - Bullish swing failure detected. Long positions highly favorable. Failed low, reversal up. Stop hunt complete.'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish SFP - Bearish swing failure detected. Short positions highly favorable. Failed high, reversal down. Stop hunt complete.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Neutral SFP - No swing failure patterns detected. Wait for failed breakouts or stop hunts.'
        }
}
)
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
        
        Enhancements (2026-01-04 - Expert Mode):
            Penetration strength, swing strength, multiple failure tracking
        """
        self.timeframe = timeframe
        self.swing_lookback = lookback
        self.failure_threshold = failure_threshold_pct
        self.reversal_window = reversal_window
        self.sfp_history = []  # Track recent SFPs for multiple failure detection
        self.max_history = 5   # Keep last 5 SFPs
    
    def _determine_dual_signals(self, sfp_type: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        if sfp_type == 'BULLISH_SFP':
            granular = 'BULLISH_SFP'
            simple = 'BULLISH'
        elif sfp_type == 'BEARISH_SFP':
            granular = 'BEARISH_SFP'
            simple = 'BEARISH'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        return granular, simple
    
    def classify_penetration_strength(self, penetration_pct: float) -> str:
        """
        Classify penetration strength - Priority 1.1
        
        Returns:
            'SHALLOW': 0.1-0.2% (minimal stop hunt)
            'MODERATE': 0.2-0.4% (typical stop hunt)
            'DEEP': 0.4-0.7% (strong stop hunt)
            'VERY_DEEP': >0.7% (very strong stop hunt)
        """
        if penetration_pct >= 0.7:
            return 'VERY_DEEP'
        elif penetration_pct >= 0.4:
            return 'DEEP'
        elif penetration_pct >= 0.2:
            return 'MODERATE'
        else:
            return 'SHALLOW'
    
    def calculate_swing_strength(self, df: pd.DataFrame, swing_range: float) -> str:
        """
        Measure swing strength relative to ATR - Priority 1.2
        
        Strong swings (>2x ATR) = higher probability SFP
        
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
    
    def detect_multiple_failures(self, sfp_type: str, timestamp) -> int:
        """
        Detect multiple consecutive SFPs - Priority 1.3
        
        Returns count of recent SFPs in same direction
        """
        # Clean old history (older than 20 bars)
        current_time = pd.Timestamp(timestamp)
        self.sfp_history = [
            sfp for sfp in self.sfp_history
            if (current_time - pd.Timestamp(sfp['timestamp'])).seconds < 20 * 15 * 60  # 20 bars at 15min
        ]
        
        # Count consecutive SFPs in same direction
        consecutive = 0
        for sfp in reversed(self.sfp_history):
            if sfp['type'] == sfp_type:
                consecutive += 1
            else:
                break
        
        return consecutive + 1  # +1 for current SFP
    
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
        
        # Calculate swing range for strength measurement
        swing_range = swing_low - failure_low
        
        return {
            'type': 'BULLISH_SFP',
            'swing_low': swing_low,
            'failure_low': failure_low,
            'recovery_close': recovery_close,
            'penetration_pct': round(penetration_pct, 3),
            'timestamp': recent.iloc[-1]['timestamp'],
            'swing_range': swing_range  # For strength calculation
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
        
        # Calculate swing range for strength measurement
        swing_range = failure_high - swing_high
        
        return {
            'type': 'BEARISH_SFP',
            'swing_high': swing_high,
            'failure_high': failure_high,
            'recovery_close': recovery_close,
            'penetration_pct': round(penetration_pct, 3),
            'timestamp': recent.iloc[-1]['timestamp'],
            'swing_range': swing_range  # For strength calculation
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
        
        # **ENHANCED:** Calculate quality metrics
        penetration_strength = self.classify_penetration_strength(active_sfp['penetration_pct'])
        swing_strength = self.calculate_swing_strength(df, active_sfp['swing_range'])
        consecutive_failures = self.detect_multiple_failures(active_sfp['type'], active_sfp['timestamp'])
        
        # Add to history for future multiple failure detection
        self.sfp_history.append({
            'type': active_sfp['type'],
            'timestamp': active_sfp['timestamp']
        })
        if len(self.sfp_history) > self.max_history:
            self.sfp_history.pop(0)
        
        # **ENHANCED:** Calculate confidence with quality metrics
        base_confidence = 75  # Base for any SFP
        
        # Penetration strength bonus
        pen_strength = active_sfp['penetration_pct']
        if pen_strength >= 0.7:
            base_confidence += 15  # VERY_DEEP
        elif pen_strength >= 0.4:
            base_confidence += 10  # DEEP
        elif pen_strength >= 0.2:
            base_confidence += 5   # MODERATE
        
        # Swing strength bonus
        if swing_strength == 'VERY_STRONG':
            base_confidence += 5
        elif swing_strength == 'STRONG':
            base_confidence += 3
        
        # Multiple failures bonus
        if consecutive_failures >= 3:
            base_confidence += 5
        elif consecutive_failures >= 2:
            base_confidence += 3
        
        confidence = min(100, base_confidence)
        
        # **ENHANCED:** Build confluence factors with quality metrics
        confluence_factors = []
        confluence_factors.append(f'SFP Type: {active_sfp["type"]}')
        
        # Penetration with strength
        confluence_factors.append(f'Penetration: {active_sfp["penetration_pct"]:.3f}% ({penetration_strength})')
        
        # Swing strength indicator
        if swing_strength in ['STRONG', 'VERY_STRONG']:
            confluence_factors.append(f'💪 {swing_strength} SWING: High conviction reversal!')
        
        # Multiple failures indicator
        if consecutive_failures >= 2:
            confluence_factors.append(f'🔥 {consecutive_failures}x CONSECUTIVE FAILURES: Strong reversal momentum!')
        
        confluence_factors.append('Failed swing - stop hunt reversal')
        confluence_factors.append('Breakout traders trapped')
        confluence_factors.append('High probability counter-trend entry')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(active_sfp['type'])
        
        # **ENHANCED:** Metadata with quality metrics
        if active_sfp['type'] == 'BULLISH_SFP':
            metadata = {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'sfp_type': active_sfp['type'],
                'swing_low': active_sfp['swing_low'],
                'failure_low': active_sfp['failure_low'],
                'recovery_close': active_sfp['recovery_close'],
                'penetration_pct': active_sfp['penetration_pct'],
                'sfp_timestamp': active_sfp['timestamp'],
                'penetration_strength': penetration_strength,  # NEW: Quality tier
                'swing_strength': swing_strength,  # NEW: Context
                'consecutive_failures': consecutive_failures  # NEW: Momentum
            }
        else:
            metadata = {
                'sfp_type': active_sfp['type'],
                'swing_high': active_sfp['swing_high'],
                'failure_high': active_sfp['failure_high'],
                'recovery_close': active_sfp['recovery_close'],
                'penetration_pct': active_sfp['penetration_pct'],
                'sfp_timestamp': active_sfp['timestamp'],
                'penetration_strength': penetration_strength,  # NEW: Quality tier
                'swing_strength': swing_strength,  # NEW: Context
                'consecutive_failures': consecutive_failures  # NEW: Momentum
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
