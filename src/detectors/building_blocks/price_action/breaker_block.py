"""
Breaker Block Building Block
Category: Advanced Price Action
Purpose: Identify breaker blocks - failed order blocks that reverse - ICT concept
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: Breaker block detection, fires when structure breaks

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
    name='breaker_block',
    category='PRICE_ACTION',
    class_name='BreakerBlock',
    default_weight=25,
    valid_signals=[
        # Granular signals
        'BEARISH_BREAKER', 'BULLISH_BREAKER', 'NO_BREAKER',
        # Simple directional - SIMPLE (what code actually emits!)
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BEARISH_BREAKER': {
                'base_points': 25,
                'formula': 'scaled'
        },
        'BULLISH_BREAKER': {
                'base_points': 25,
                'formula': 'scaled'
        },
        'NO_BREAKER': {
                'points': 0
        },
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 25,
                'formula': 'scaled'
        },
        'BEARISH': {
                'base_points': 25,
                'formula': 'scaled'
        },
        'NEUTRAL': {
                'points': 0
        }
}
)
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
                 lookback: int = 15, **kwargs):
        """
        Initialize Breaker Block detector with OPTIMIZED parameters (batch tuning 2026-01-01)
        
        Batch Optimization Results:
            Quality: 80/100 (good)
            Accuracy: 58.2%
            Signals: 11,024 in 180 days (61/day)
            R/R: 8.47 (excellent)
            Bullish: 56.4%, Bearish: 60.0%
            Discovery: lookback=15 (vs 50) - 70% faster = better performance
        """
        self.timeframe = timeframe
        self.min_break_pct = min_break_pct
        self.lookback = lookback
    
    def _determine_dual_signals(self, signal: str, active_breaker: Dict = None) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Map current state to granular + simple"""
        # Current logic returns BULLISH/BEARISH/NEUTRAL for price in zone
        # We need to map to granular breaker type + simple directional
        if signal == 'BULLISH' and active_breaker:
            granular = 'BULLISH_BREAKER'
            simple = 'BULLISH'
        elif signal == 'BEARISH' and active_breaker:
            granular = 'BEARISH_BREAKER'
            simple = 'BEARISH'
        elif signal == 'NO_BREAKER':
            granular = 'NO_BREAKER'
            simple = 'NEUTRAL'
        else:  # NEUTRAL (breaker exists but price not in zone)
            granular = 'NO_BREAKER'
            simple = 'NEUTRAL'
        return granular, simple
    
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
        """Main analysis method - tracks both CONTINUOUS breaker state and NEW breaker formations"""
        if not all(col in df.columns for col in ['timestamp', 'open', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 10:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 10 bars', 'is_new_event': False},
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
            granular_signal, simple_signal = self._determine_dual_signals('NO_BREAKER', None)
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'error': 'No breaker block detected',
                    'is_new_event': False
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # **NEW:** Event tracking - detect when price ENTERS breaker zone (new event)
        current_bar_index = len(df) - 1
        bars_since_breaker = current_bar_index - active_breaker['index']
        
        # Check if price just entered the zone (wasn't in zone last bar, is in zone now)
        is_new_event = False
        if signal != 'NEUTRAL' and len(df) > 1:  # Price IS in zone now
            prev_price = float(df['close'].iloc[-2])
            # Check if previous price was NOT in zone
            if active_breaker['type'] == 'BULLISH_BREAKER':
                was_in_zone = (active_breaker['low'] <= prev_price <= active_breaker['high'] * 1.01)
            else:  # BEARISH_BREAKER
                was_in_zone = (active_breaker['low'] * 0.99 <= prev_price <= active_breaker['high'])
            is_new_event = not was_in_zone  # Just entered if wasn't in before
        
        # Calculate confidence
        confidence = 75
        if active_breaker['break_pct'] > 0.5:
            confidence += 10
        if active_breaker['break_pct'] > 1.0:
            confidence += 10
        if is_new_event:
            confidence += 5  # Boost for fresh breaker (immediate entry opportunity)
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        
        # Event-specific confluence
        if is_new_event:
            confluence_factors.append('⭐ NEW BREAKER FORMED (just occurred - fresh failed OB!)')
        elif bars_since_breaker > 0:
            confluence_factors.append(f'Active breaker zone (formed {bars_since_breaker} bars ago)')
        
        confluence_factors.append(f'Breaker Type: {active_breaker["type"]}')
        confluence_factors.append(f'Zone: ${active_breaker["low"]:.2f} - ${active_breaker["high"]:.2f}')
        confluence_factors.append(f'Break Strength: {active_breaker["break_pct"]}%')
        confluence_factors.append('Failed OB now acting as opposite - structure change')
        
        if signal != 'NEUTRAL':
            confluence_factors.append('Price at breaker zone - high probability setup')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal, active_breaker)
        
        # Metadata
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'breaker_type': active_breaker['type'],
            'breaker_high': active_breaker['high'],
            'breaker_low': active_breaker['low'],
            'breaker_mid': active_breaker['mid'],
            'break_pct': active_breaker['break_pct'],
            'current_price': round(current_price, 2),
            'in_zone': signal != 'NEUTRAL',
            'breaker_timestamp': active_breaker['timestamp'],
            'is_new_event': is_new_event,  # NEW: Event tracking
            'bars_since_breaker': bars_since_breaker  # NEW: Age tracking
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
