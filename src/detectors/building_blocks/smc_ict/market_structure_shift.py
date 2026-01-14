"""
Market Structure Shift (MSS) Building Block
Category: SMC/ICT
Purpose: Detect market structure changes - trend reversals ICT concept

ENHANCEMENTS (2026-01-04):
- Priority 1.1: Multiple MSS detection (reversal confirmation tracking)
- Priority 1.2: Break strength tiers (quality classification)
- Priority 1.3: Retest detection (safer entry opportunities)
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: MSS detection, fires on trend reversal

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
    name='market_structure_shift',
    category='SMC_ICT',
    class_name='MarketStructureShift',
    default_weight=20,
    valid_signals=[
        # Granular SMC signals
        'BEARISH_MSS', 'BEARISH_RETEST', 'BULLISH_MSS', 'BULLISH_RETEST',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BEARISH_MSS': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'BEARISH_RETEST': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'BULLISH_MSS': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'BULLISH_RETEST': {
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
        swing_lookback: Periods for swing detection (default: 8)
        min_break_pct: Minimum break % to confirm (default: 0.05%)
        track_confirmation: Track consecutive MSS for confirmation (default: True)
        detect_retest: Detect pullbacks to MSS level (default: True)
    """
    
    def __init__(self, timeframe: str = '15min',
                 swing_lookback: int = 8,
                 min_break_pct: float = 0.05,
                 track_confirmation: bool = True,
                 detect_retest: bool = True, **kwargs):
        """
        Initialize MSS detector with OPTIMIZED parameters (batch tuning 2026-01-01)
        
        Batch Optimization Results:
            Quality: 80/100
            Accuracy: 55.7%
            Signals: 16,431 in 180 days (91.3/day - very high frequency)
            R/R: 7.93 (excellent)
            Discovery: swing=8 (vs 10), thresh=0.05 (vs 0.1) - faster + looser
        
        Enhancements (2026-01-04 - Expert Mode Priority 1 & 2):
            track_confirmation: Track consecutive MSS for reversal confirmation
            detect_retest: Detect pullbacks to MSS level for safer entries
        """
        self.timeframe = timeframe
        self.swing_lookback = swing_lookback
        self.min_break_pct = min_break_pct
        self.track_confirmation = track_confirmation
        self.detect_retest = detect_retest
        self.mss_history = []  # Track MSS events for confirmation
    
    def _determine_dual_signals(self, mss_type: str, has_retest: bool = False, retest_type: str = None) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        if has_retest and retest_type:
            # Retest signals are more specific
            granular = retest_type  # BULLISH_RETEST or BEARISH_RETEST
            simple = 'BULLISH' if 'BULLISH' in retest_type else 'BEARISH'
        elif mss_type == 'BULLISH_MSS':
            granular = 'BULLISH_MSS'
            simple = 'BULLISH'
        elif mss_type == 'BEARISH_MSS':
            granular = 'BEARISH_MSS'
            simple = 'BEARISH'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        return granular, simple
    
    def classify_break_strength(self, break_pct: float) -> str:
        """
        Classify break strength into tiers (Priority 1.2 Enhancement)
        
        Returns:
            'WEAK': 0.05-0.15% break
            'MODERATE': 0.15-0.3% break
            'STRONG': 0.3-0.6% break
            'VERY_STRONG': >0.6% break
        """
        if break_pct >= 0.6:
            return 'VERY_STRONG'
        elif break_pct >= 0.3:
            return 'STRONG'
        elif break_pct >= 0.15:
            return 'MODERATE'
        else:
            return 'WEAK'
    
    def count_consecutive_mss(self, current_signal: str) -> int:
        """
        Count consecutive MSS in same direction (Priority 1.1 Enhancement)
        
        Returns:
            Number of consecutive MSS events in current direction
            (2+ indicates strong reversal confirmation)
        """
        if not self.track_confirmation or len(self.mss_history) == 0:
            return 1
        
        consecutive = 1
        for mss_event in reversed(self.mss_history[-3:]):  # Check last 3
            if mss_event == current_signal:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def update_mss_history(self, signal: str, is_new_event: bool):
        """Update MSS history for confirmation tracking"""
        if self.track_confirmation and is_new_event and signal in ['BULLISH', 'BEARISH']:
            self.mss_history.append(signal)
            # Keep only last 5 events
            if len(self.mss_history) > 5:
                self.mss_history.pop(0)
    
    def detect_mss_retest(self, df: pd.DataFrame, mss_data: Dict[str, Any], current_index: int) -> Dict[str, Any]:
        """
        Detect pullback to MSS level (Priority 1.3 Enhancement)
        
        Returns dict with retest info or None if no retest detected
        """
        if not self.detect_retest:  # This is the parameter, not the method
            return None
        
        mss_index = mss_data['index']
        bars_since_mss = current_index - mss_index
        
        # Only check for retest within 10 bars of MSS
        if bars_since_mss < 2 or bars_since_mss > 10:
            return None
        
        if mss_data['type'] == 'BULLISH_MSS':
            # Check if price pulled back to MSS level and rejected
            mss_level = mss_data['swing_high']
            recent_bars = df.iloc[mss_index+1:current_index+1]
            
            # Look for pullback to within 0.5% of MSS level
            for i, row in recent_bars.iterrows():
                distance_pct = abs((row['low'] - mss_level) / mss_level) * 100
                if distance_pct <= 0.5:
                    # Check if price rejected (closed above)
                    if row['close'] > mss_level:
                        return {
                            'has_retest': True,
                            'retest_bar': row['timestamp'],
                            'retest_distance': round(distance_pct, 3),
                            'retest_type': 'BULLISH_RETEST'
                        }
        
        else:  # BEARISH_MSS
            # Check if price pulled back to MSS level and rejected
            mss_level = mss_data['swing_low']
            recent_bars = df.iloc[mss_index+1:current_index+1]
            
            # Look for pullback to within 0.5% of MSS level
            for i, row in recent_bars.iterrows():
                distance_pct = abs((row['high'] - mss_level) / mss_level) * 100
                if distance_pct <= 0.5:
                    # Check if price rejected (closed below)
                    if row['close'] < mss_level:
                        return {
                            'has_retest': True,
                            'retest_bar': row['timestamp'],
                            'retest_distance': round(distance_pct, 3),
                            'retest_type': 'BEARISH_RETEST'
                        }
        
        return None
    
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
                        'timestamp': df['timestamp'].iloc[i],
                        'break_strength': self.classify_break_strength(break_pct)
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
                        'timestamp': df['timestamp'].iloc[i],
                        'break_strength': self.classify_break_strength(break_pct)
                    }
        return None
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method - tracks both CONTINUOUS state and NEW events"""
        if not all(col in df.columns for col in ['timestamp', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.swing_lookback + 5:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.swing_lookback + 5} bars', 'is_new_event': False},
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
                'metadata': {'error': 'No market structure shift detected', 'is_new_event': False},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # **NEW:** Determine if this is a NEW event (occurred on current bar) vs continuing state
        current_bar_index = len(df) - 1
        is_new_event = (active_mss['index'] == current_bar_index)
        
        # **ENHANCED:** Count consecutive MSS (confirmation tracking)
        consecutive_mss = self.count_consecutive_mss(signal)
        
        # Update MSS history
        self.update_mss_history(signal, is_new_event)
        
        # **ENHANCED:** Detect retest
        retest_info = self.detect_mss_retest(df, active_mss, current_bar_index)
        
        # **ENHANCED:** Calculate confidence with new factors
        confidence = 85  # High confidence for MSS
        
        # Break strength bonus
        break_strength = active_mss.get('break_strength', 'MODERATE')
        if break_strength == 'VERY_STRONG':
            confidence += 15
        elif break_strength == 'STRONG':
            confidence += 10
        elif break_strength == 'MODERATE':
            confidence += 5
        
        # NEW event bonus
        if is_new_event:
            confidence += 5  # Fresh reversal timing critical!
        
        # Confirmation bonus (consecutive MSS)
        if consecutive_mss >= 2:
            confidence += 5  # Strong reversal confirmation
        
        # Retest bonus
        if retest_info and retest_info['has_retest']:
            confidence += 10  # Retest = safer entry
        
        confidence = min(100, confidence)
        
        # **ENHANCED:** Build confluence with new factors
        confluence_factors = []
        confluence_factors.append(f'MSS Type: {active_mss["type"]}')
        confluence_factors.append(f'Break Strength: {active_mss["break_pct"]:.3f}% ({break_strength})')
        confluence_factors.append('Market structure changed - trend reversal signal')
        
        # Confirmation indicator
        if consecutive_mss >= 2:
            confluence_factors.append(f'✅ CONFIRMED: {consecutive_mss} consecutive MSS (strong reversal)')
        
        # Retest indicator
        if retest_info and retest_info['has_retest']:
            confluence_factors.append(f'🎯 RETEST DETECTED: Pullback to MSS level (safer entry!)')
        
        if is_new_event:
            confluence_factors.append('⭐ NEW MSS EVENT (just occurred - fresh reversal signal!)')
        else:
            confluence_factors.append('Continuing MSS state (structure already shifted)')
        confluence_factors.append('Institutional positioning shift likely')
        
        # DUAL SIGNAL ARCHITECTURE
        has_retest = retest_info.get('has_retest', False) if retest_info else False
        retest_type = retest_info.get('retest_type') if retest_info else None
        granular_signal, simple_signal = self._determine_dual_signals(active_mss['type'], has_retest, retest_type)
        
        # **ENHANCED:** Metadata with new tracking
        if active_mss['type'] == 'BULLISH_MSS':
            metadata = {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'mss_type': active_mss['type'],
                'swing_high': active_mss['swing_high'],
                'break_high': active_mss['break_high'],
                'break_pct': active_mss['break_pct'],
                'break_strength': break_strength,  # NEW: Strength tier
                'consecutive_mss': consecutive_mss,  # NEW: Confirmation tracking
                'mss_timestamp': active_mss['timestamp'],
                'is_new_event': is_new_event,
                'bars_since_mss': current_bar_index - active_mss['index']
            }
            # Add retest info if detected
            if retest_info:
                metadata.update(retest_info)
        else:
            metadata = {
                'mss_type': active_mss['type'],
                'swing_low': active_mss['swing_low'],
                'break_low': active_mss['break_low'],
                'break_pct': active_mss['break_pct'],
                'break_strength': break_strength,  # NEW: Strength tier
                'consecutive_mss': consecutive_mss,  # NEW: Confirmation tracking
                'mss_timestamp': active_mss['timestamp'],
                'is_new_event': is_new_event,
                'bars_since_mss': current_bar_index - active_mss['index']
            }
            # Add retest info if detected
            if retest_info:
                metadata.update(retest_info)
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
