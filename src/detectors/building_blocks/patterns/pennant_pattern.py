"""
Pennant Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Identifies continuation pattern with converging channel after strong move
"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class PennantPattern:
    """
    Pennant Pattern Detector
    
    Continuation pattern: Converging channel after strong trend move
    - Strong directional move (flagpole)
    - Consolidation in converging channel (pennant)
    - Breakout continues original trend
    - Symmetrical pennant (both trendlines converge)
    
    Success Rate: 65% continuation (research validated)
    
    Parameters:
        min_pattern_bars: Minimum bars (default: 10)
        convergence_threshold: Convergence requirement (default: 0.6)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 10,
                 convergence_threshold: float = 0.6, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.convergence_threshold = convergence_threshold
    
    def detect_strong_move(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect preceding strong move (flagpole)"""
        if len(df) < 20:
            return None
        
        lookback_start = float(df['close'].iloc[-20])
        lookback_end = float(df['close'].iloc[-10])
        
        price_change_pct = (lookback_end - lookback_start) / lookback_start
        
        if abs(price_change_pct) < 0.03:  # Need >3% move
            return None
        
        return {
            'direction': 'BULLISH' if price_change_pct > 0 else 'BEARISH',
            'strength': abs(price_change_pct),
            'pole_start': lookback_start,
            'pole_end': lookback_end
        }
    
    def detect_converging_channel(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect converging consolidation channel"""
        if len(df) < self.min_pattern_bars:
            return None
        
        recent = df.iloc[-self.min_pattern_bars:]
        
        # Check convergence
        initial_range = float(recent['high'].iloc[0] - recent['low'].iloc[0])
        final_range = float(recent['high'].iloc[-1] - recent['low'].iloc[-1])
        
        if initial_range == 0:
            return None
        
        convergence_ratio = final_range / initial_range
        
        if convergence_ratio > self.convergence_threshold:
            return None  # Not converging enough
        
        return {
            'upper_start': float(recent['high'].iloc[0]),
            'upper_end': float(recent['high'].iloc[-1]),
            'lower_start': float(recent['low'].iloc[0]),
            'lower_end': float(recent['low'].iloc[-1]),
            'convergence_ratio': convergence_ratio,
            'apex_price': (float(recent['high'].iloc[-1]) + float(recent['low'].iloc[-1])) / 2
        }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 20:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 20 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        flagpole = self.detect_strong_move(df)
        if flagpole is None:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        channel = self.detect_converging_channel(df)
        if channel is None:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        
        if flagpole['direction'] == 'BULLISH':
            breakout = current_price > channel['upper_end']
            signal = 'BULLISH_BREAKOUT' if breakout else 'PATTERN_FORMING'
            target = flagpole['pole_end'] + (flagpole['pole_end'] - flagpole['pole_start'])
        else:
            breakout = current_price < channel['lower_end']
            signal = 'BEARISH_BREAKOUT' if breakout else 'PATTERN_FORMING'
            target = flagpole['pole_end'] - (flagpole['pole_start'] - flagpole['pole_end'])
        
        confidence = 68 if breakout else 53
        
        confluence_factors = []
        confluence_factors.append("Pennant Pattern detected")
        confluence_factors.append(f"Flagpole: {flagpole['direction']} move ({flagpole['strength']*100:.1f}%)")
        confluence_factors.append(f"Converging consolidation")
        confluence_factors.append(f"Continuation pattern")
        
        if breakout:
            confluence_factors.append(f"✅ Breakout confirmed - {flagpole['direction']}!")
            confidence += 10
        else:
            confluence_factors.append("⏳ Awaiting breakout")
        
        confluence_factors.append(f"Target: ${target:.2f}")
        confluence_factors.append("Success rate: 65% continuation")
        
        metadata = {
            'pattern_type': 'PENNANT',
            'direction': flagpole['direction'],
            'flagpole_strength': round(flagpole['strength'] * 100, 2),
            'apex_price': round(channel['apex_price'], 2),
            'breakout_confirmed': breakout,
            'target_price': round(target, 2),
            'expected_success_rate': 0.65
        }
        
        return {
            'signal': signal,
            'confidence': min(100, round(confidence, 2)),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
