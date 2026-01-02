"""
Pennant Pattern Building Block - EXPERT MODE OPTIMIZED
Realistic detection for 15min timeframe
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd


class PennantPattern:
    """
    Pennant: Continuation pattern with strong move + triangular consolidation
    
    EXPERT MODE: Relaxed for 15min realistic detection
    - Strong directional move (1.5%+ on 15min)
    - Converging consolidation (triangular)
    - Breakout continues trend
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """EXPERT MODE: Simplified pennant detection"""
        if len(df) < 25:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check for strong move in bars 25-15 (flagpole)
        pole_section = df.iloc[-25:-10] if len(df) >= 25 else df.iloc[:-10]
        pole_start = float(pole_section['close'].iloc[0])
        pole_end = float(pole_section['close'].iloc[-1])
        pole_move_pct = (pole_end - pole_start) / pole_start
        
        # EXPERT: Only need 1% move (down from 3%)
        if abs(pole_move_pct) < 0.01:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check for consolidation in last 10 bars (pennant)
        pennant_section = df.iloc[-10:]
        
        # Check convergence: Compare first 5 vs last 5 bars
        first_5 = pennant_section.iloc[:5]
        last_5 = pennant_section.iloc[-5:]
        
        first_range = first_5['high'].max() - first_5['low'].min()
        last_range = last_5['high'].max() - last_5['low'].min()
        
        # EXPERT: Need 20% compression (down from 40%)
        is_converging = last_range < first_range * 0.8
        
        if is_converging:
            current = float(df['close'].iloc[-1])
            direction = 'BULLISH' if pole_move_pct > 0 else 'BEARISH'
            
            upper = last_5['high'].max()
            lower = last_5['low'].min()
            
            if direction == 'BULLISH':
                breakout = current > upper
                signal = 'BULLISH_BREAKOUT' if breakout else 'PATTERN_FORMING'
            else:
                breakout = current < lower
                signal = 'BEARISH_BREAKOUT' if breakout else 'PATTERN_FORMING'
            
            confidence = 70 if breakout else 55
            target = pole_end + (pole_end - pole_start)
            
            return {
                'signal': signal,
                'confidence': confidence,
                'metadata': {
                    'pattern_type': 'PENNANT',
                    'direction': direction,
                    'pole_strength_pct': round(abs(pole_move_pct) * 100, 2),
                    'breakout_confirmed': breakout,
                    'target_price': round(target, 2),
                    'expected_success_rate': 0.65
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': [
                    'Pennant detected',
                    f'{direction} flagpole: {abs(pole_move_pct)*100:.1f}%',
                    'Converging consolidation',
                    f'{'✅ Breakout!' if breakout else '⏳ Forming'}'
                ]
            }
        
        return {
            'signal': 'NO_PATTERN',
            'confidence': 0,
            'metadata': {},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': []
        }
