"""
Mitigation Block Building Block
Category: SMC/ICT
Purpose: Detect mitigation blocks - ICT institutional position mitigation
"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class MitigationBlock:
    """
    Mitigation Block Detector - ICT/SMC Concept
    
    Identifies zones where institutions need to mitigate (close/reduce)
    their positions. These are unfilled orders or imbalances that price
    must return to before continuing in the intended direction.
    
    Mitigation Characteristics:
    - Unfilled institutional orders
    - Price gaps/imbalances
    - Must be filled before continuation
    - High probability retracement zone
    
    Types:
    - Bullish Mitigation: Unfilled buy orders below (support)
    - Bearish Mitigation: Unfilled sell orders above (resistance)
    
    Trading Application:
    - Entry on return to mitigation zone
    - Expect bounce/rejection
    - Continuation after mitigation
    
    Parameters:
        lookback: Periods for gap detection (default: 20)
        gap_threshold: Minimum gap % to identify (default: 0.2%)
    """
    
    def __init__(self, timeframe: str = '15min',
                 lookback: int = 20,
                 gap_threshold: float = 0.2, **kwargs):
        """Initialize Mitigation Block detector"""
        self.timeframe = timeframe
        self.lookback = lookback
        self.gap_threshold = gap_threshold
    
    def detect_bullish_mitigation(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bullish mitigation zone (unfilled buy orders below)
        
        CRITICAL FIX for Bitcoin: Traditional gaps rare in 24/7 crypto markets.
        Instead, detect:
        1. Strong bullish impulse candles (institutional buying)
        2. Areas not yet retested (mitigation pending)
        3. Imbalances in price action
        """
        if len(df) < self.lookback:
            return None
        
        recent = df.tail(self.lookback)
        current_price = float(df['close'].iloc[-1])
        
        # Look for strong bullish candles that created mitigation zones
        for i in range(len(recent) - 3):  # Need 3 bars after to check retest
            bar = recent.iloc[i]
            
            # Strong bullish candle criteria
            body = bar['close'] - bar['open']
            full_range = bar['high'] - bar['low']
            
            if full_range == 0:
                continue
                
            body_pct = (body / full_range) * 100
            move_pct = (body / bar['open']) * 100
            
            # Strong bullish move: body >50% of range, move >0.2% (more lenient for Bitcoin)
            if body > 0 and body_pct > 50 and move_pct > 0.2:
                mitigation_low = float(bar['low'])
                mitigation_high = float(bar['close'])  # Use close for bullish
                
                # Check if price is APPROACHING this zone (within 3%)
                distance_pct = ((current_price - mitigation_high) / current_price) * 100
                
                # Signal when price is above zone AND approaching (within 10%)
                if current_price > mitigation_high and distance_pct < 10.0:
                    return {
                        'type': 'BULLISH_MITIGATION',
                        'mitigation_high': mitigation_high,
                        'mitigation_low': mitigation_low,
                        'gap_size': mitigation_high - mitigation_low,
                        'gap_pct': round(move_pct, 3),
                        'current_price': current_price,
                        'distance_pct': round(((current_price - mitigation_high) / current_price) * 100, 2),
                        'timestamp': df['timestamp'].iloc[-1],
                        'bars_ago': len(recent) - i - 1
                    }
        
        return None
    
    def detect_bearish_mitigation(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bearish mitigation zone (unfilled sell orders above)
        
        CRITICAL FIX for Bitcoin: Traditional gaps rare in 24/7 crypto markets.
        Instead, detect:
        1. Strong bearish impulse candles (institutional selling)
        2. Areas not yet retested (mitigation pending)
        3. Imbalances in price action
        """
        if len(df) < self.lookback:
            return None
        
        recent = df.tail(self.lookback)
        current_price = float(df['close'].iloc[-1])
        
        # Look for strong bearish candles that created mitigation zones
        for i in range(len(recent) - 3):  # Need 3 bars after to check retest
            bar = recent.iloc[i]
            
            # Strong bearish candle criteria
            body = bar['open'] - bar['close']  # Bearish body
            full_range = bar['high'] - bar['low']
            
            if full_range == 0:
                continue
                
            body_pct = (body / full_range) * 100
            move_pct = (body / bar['open']) * 100
            
            # Strong bearish move: body >50% of range, move >0.2% (more lenient for Bitcoin)
            if body > 0 and body_pct > 50 and move_pct > 0.2:
                mitigation_high = float(bar['high'])
                mitigation_low = float(bar['close'])  # Use close for bearish
                
                # Check if price is APPROACHING this zone (within 3%)
                distance_pct = ((mitigation_low - current_price) / current_price) * 100
                
                # Signal when price is below zone AND approaching (within 10%)
                if current_price < mitigation_low and distance_pct < 10.0:
                    return {
                        'type': 'BEARISH_MITIGATION',
                        'mitigation_high': mitigation_high,
                        'mitigation_low': mitigation_low,
                        'gap_size': mitigation_high - mitigation_low,
                        'gap_pct': round(move_pct, 3),
                        'current_price': current_price,
                        'distance_pct': round(((mitigation_low - current_price) / current_price) * 100, 2),
                        'timestamp': df['timestamp'].iloc[-1],
                        'bars_ago': len(recent) - i - 1
                    }
        
        return None
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method - tracks both CONTINUOUS approach state and NEW zone entries"""
        if not all(col in df.columns for col in ['timestamp', 'open', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns (need open, high, low, close, timestamp)', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.lookback + 5:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.lookback + 5} bars', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect mitigation zones
        bullish_mit = self.detect_bullish_mitigation(df)
        bearish_mit = self.detect_bearish_mitigation(df)
        
        # Choose active mitigation (prefer closest)
        active_mit = None
        signal = 'NEUTRAL'  # confidence = 60 for valid signal
        
        if bullish_mit and bearish_mit:
            # Choose closest one
            if bullish_mit['distance_pct'] < bearish_mit['distance_pct']:
                active_mit = bullish_mit
                signal = 'BULLISH'  # confidence = 60 for valid signal
            else:
                active_mit = bearish_mit
                signal = 'BEARISH'  # confidence = 60 for valid signal
        elif bullish_mit:
            active_mit = bullish_mit
            signal = 'BULLISH'  # confidence = 60 for valid signal
        elif bearish_mit:
            active_mit = bearish_mit
            signal = 'BEARISH'  # confidence = 60 for valid signal
        
        if not active_mit:
            return {
                'signal': 'NEUTRAL',
                'confidence': 0,
                'metadata': {'message': 'No mitigation zones detected', 'is_new_event': False},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['No unfilled gaps - clean price action']
            }
        
        # **NEW:** Event tracking - detect when price ENTERS approach zone
        is_new_event = False
        bars_in_approach = 0
        
        # Check if we just started approaching (wasn't approaching last bar, is now)
        if len(df) > self.lookback + 6:
            # Check previous bar's state
            prev_bullish = self.detect_bullish_mitigation(df.iloc[:-1])
            prev_bearish = self.detect_bearish_mitigation(df.iloc[:-1])
            
            # Determine if previous bar had ANY mitigation signal
            had_prev_signal = (prev_bullish is not None or prev_bearish is not None)
            
            # New event if we NOW have signal but DIDN'T before
            is_new_event = not had_prev_signal
            
            # If continuing, approximate bars in approach
            if not is_new_event:
                bars_in_approach = 1  # At least 1 bar approaching
        
        # Calculate confidence based on gap size and distance
        confidence = 70  # Base confidence for mitigation
        if active_mit['gap_pct'] > 0.5:
            confidence += 10
        if active_mit['distance_pct'] < 2.0:
            confidence += 15  # Very close
        elif active_mit['distance_pct'] < 5.0:
            confidence += 10  # Close
        
        # Fresh approach boost
        if is_new_event:
            confidence += 5
        confidence = min(100, confidence)
        
        # Build confluence factors
        confluence_factors = []
        
        # Event-specific confluence
        if is_new_event:
            if signal == 'BULLISH':
                confluence_factors.append('⭐ NEW BULLISH MITIGATION APPROACH (fresh retracement opportunity!)')
            else:
                confluence_factors.append('⭐ NEW BEARISH MITIGATION APPROACH (fresh retracement opportunity!)')
        elif bars_in_approach > 0:
            confluence_factors.append(f'Continuing approach to mitigation ({bars_in_approach} bars)')
        
        confluence_factors.append(f'Mitigation Type: {active_mit["type"]}')
        confluence_factors.append(f'Zone: ${active_mit["mitigation_low"]:.2f} - ${active_mit["mitigation_high"]:.2f}')
        confluence_factors.append(f'Gap Size: {active_mit["gap_pct"]:.3f}%')
        confluence_factors.append(f'Distance: {active_mit["distance_pct"]:.2f}%')
        confluence_factors.append('Unfilled institutional orders - expect retracement')
        confluence_factors.append('High probability entry on mitigation')
        
        # Metadata
        metadata = {
            'mitigation_type': active_mit['type'],
            'mitigation_high': active_mit['mitigation_high'],
            'mitigation_low': active_mit['mitigation_low'],
            'gap_size': active_mit['gap_size'],
            'gap_pct': active_mit['gap_pct'],
            'current_price': active_mit['current_price'],
            'distance_pct': active_mit['distance_pct'],
            'mitigation_timestamp': active_mit['timestamp'],
            'is_new_event': is_new_event,  # NEW: Event tracking
            'bars_in_approach': bars_in_approach  # NEW: Age tracking
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
