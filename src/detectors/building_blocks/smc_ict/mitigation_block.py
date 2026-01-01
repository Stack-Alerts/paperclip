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
        """Detect bullish mitigation zone (unfilled orders below)"""
        if len(df) < self.lookback:
            return None
        
        recent = df.tail(self.lookback)
        current_price = float(df['close'].iloc[-1])
        
        # Look for gaps below current price
        for i in range(len(recent) - 1):
            current_bar = recent.iloc[i]
            next_bar = recent.iloc[i+1]
            
            # Check for gap  up (mitigation zone left below)
            if next_bar['low'] > current_bar['high']:
                gap_size = next_bar['low'] - current_bar['high']
                gap_pct = (gap_size / current_bar['high']) * 100
                
                if gap_pct >= self.gap_threshold:
                    mitigation_high = float(current_bar['high'])
                    mitigation_low = float(current_bar['low'])
                    
                    # Check if price is above this zone (not yet mitigated)
                    if current_price > mitigation_high:
                        return {
                            'type': 'BULLISH_MITIGATION',
                            'mitigation_high': mitigation_high,
                            'mitigation_low': mitigation_low,
                            'gap_size': float(gap_size),
                            'gap_pct': round(gap_pct, 3),
                            'current_price': current_price,
                            'distance_pct': round(((current_price - mitigation_high) / current_price) * 100, 2),
                            'timestamp': df['timestamp'].iloc[-1]
                        }
        
        return None
    
    def detect_bearish_mitigation(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect bearish mitigation zone (unfilled orders above)"""
        if len(df) < self.lookback:
            return None
        
        recent = df.tail(self.lookback)
        current_price = float(df['close'].iloc[-1])
        
        # Look for gaps above current price
        for i in range(len(recent) - 1):
            current_bar = recent.iloc[i]
            next_bar = recent.iloc[i+1]
            
            # Check for gap down (mitigation zone left above)
            if next_bar['high'] < current_bar['low']:
                gap_size = current_bar['low'] - next_bar['high']
                gap_pct = (gap_size / current_bar['low']) * 100
                
                if gap_pct >= self.gap_threshold:
                    mitigation_high = float(current_bar['high'])
                    mitigation_low = float(current_bar['low'])
                    
                    # Check if price is below this zone (not yet mitigated)
                    if current_price < mitigation_low:
                        return {
                            'type': 'BEARISH_MITIGATION',
                            'mitigation_high': mitigation_high,
                            'mitigation_low': mitigation_low,
                            'gap_size': float(gap_size),
                            'gap_pct': round(gap_pct, 3),
                            'current_price': current_price,
                            'distance_pct': round(((mitigation_low - current_price) / current_price) * 100, 2),
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
                'metadata': {'message': 'No mitigation zones detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['No unfilled gaps - clean price action']
            }
        
        # Calculate confidence based on gap size and distance
        confidence = 70  # Base confidence for mitigation
        if active_mit['gap_pct'] > 0.5:
            confidence += 10
        if active_mit['distance_pct'] < 2.0:
            confidence += 15  # Very close
        elif active_mit['distance_pct'] < 5.0:
            confidence += 10  # Close
        confidence = min(100, confidence)
        
        # Build confluence factors
        confluence_factors = []
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
            'mitigation_timestamp': active_mit['timestamp']
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
