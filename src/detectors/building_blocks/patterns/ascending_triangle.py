"""
Ascending Triangle Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Identifies bullish continuation with rising lows and flat resistance
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: Pattern formation detection, fires when complete

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='ascending_triangle',
    category='PATTERNS',
    class_name='AscendingTrianglePattern',
    default_weight=30,
    valid_signals=[
        # Granular pattern signals
        'BULLISH_BREAKOUT', 'PATTERN_FORMING', 'NO_PATTERN',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Pattern signals
        'BULLISH_BREAKOUT': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Ascending triangle breakout - Resistance broken with volume. Enter longs aggressively. Target = pattern height. Stop below support line. 72% success rate.'
        },
        'PATTERN_FORMING': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Ascending triangle forming - Rising lows + flat resistance. Bullish continuation pattern. Wait for breakout above resistance. Prepare long entry.'
        },
        'NO_PATTERN': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No ascending triangle - Pattern conditions not met. No rising lows or flat resistance detected. Wait for pattern formation.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bullish triangle pattern - Ascending triangle detected or broken out. Long positions favorable. Use resistance breakout for entry.'
        },
        'BEARISH': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bearish triangle (rare) - Unexpected breakdown from ascending triangle. Exit longs immediately. Consider short with tight stop.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No triangle pattern - Market structure unclear. No ascending triangle setup. Wait for pattern formation before trading.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot detect pattern. Check data quality and minimum bars requirement.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need at least 15 candles for ascending triangle detection. Wait for more price history.'
        }
}
)
class AscendingTrianglePattern:
    """
    Ascending Triangle Pattern Detector
    
    Bullish continuation: Rising support + horizontal resistance
    - Higher lows (ascending trendline)
    - Flat resistance level
    - Converging price action
    - Breakout typically bullish
    
    Success Rate: 72% bullish (research validated)
    
    Parameters:
        min_pattern_bars: Minimum bars (default: 20)
        resistance_tolerance: Tolerance for flat resistance (default: 0.01)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 resistance_tolerance: float = 0.01, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.resistance_tolerance = resistance_tolerance
        
        # Event tracking
        self.prev_signal = 'NO_PATTERN'
        self.prev_pattern_id = None
        self.bars_in_state = 0
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if granular in ['BULLISH_BREAKOUT', 'PATTERN_FORMING']:
            simple = 'BULLISH'  # Ascending triangle is bullish
        else:
            simple = 'NEUTRAL'
        return granular, simple
    
    def find_swing_points(self, df: pd.DataFrame, lookback: int = 5):
        """Find swing highs and lows"""
        highs = []
        lows = []
        
        for i in range(lookback, len(df) - lookback):
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                highs.append({'idx': i, 'price': df['high'].iloc[i]})
            
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                lows.append({'idx': i, 'price': df['low'].iloc[i]})
        
        return highs, lows
    
    def is_ascending_support(self, lows: List) -> bool:
        """Check if lows are rising"""
        if len(lows) < 2:
            return False
        
        for i in range(len(lows) - 1):
            if lows[i+1]['price'] <= lows[i]['price']:
                return False
        return True
    
    def is_flat_resistance(self, highs: List) -> bool:
        """Check if highs form flat resistance"""
        if len(highs) < 2:
            return False
        
        prices = [h['price'] for h in highs]
        avg_price = np.mean(prices)
        
        for price in prices:
            if abs(price - avg_price) / avg_price > self.resistance_tolerance:
                return False
        return True
    
    def detect_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect Ascending Triangle"""
        if len(df) < self.min_pattern_bars:
            return None
        
        highs, lows = self.find_swing_points(df)
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        # Take recent points
        recent_highs = highs[-min(4, len(highs)):]
        recent_lows = lows[-min(4, len(lows)):]
        
        # Check pattern conditions
        if not self.is_flat_resistance(recent_highs):
            return None
        
        if not self.is_ascending_support(recent_lows):
            return None
        
        resistance_level = np.mean([h['price'] for h in recent_highs])
        support_slope = (recent_lows[-1]['price'] - recent_lows[0]['price']) / len(recent_lows)
        
        return {
            'resistance_level': resistance_level,
            'support_start': recent_lows[0]['price'],
            'support_end': recent_lows[-1]['price'],
            'support_slope': support_slope,
            'highs_count': len(recent_highs),
            'lows_count': len(recent_lows),
            'completion': 100.0
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
        
        if len(df) < self.min_pattern_bars:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.min_pattern_bars} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        pattern = self.detect_pattern(df)
        
        if pattern is None:
            granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        current_volume = float(df['volume'].iloc[-1])
        resistance_broken = current_price > pattern['resistance_level']
        
        # Volume analysis for breakout confirmation
        avg_volume = df['volume'].iloc[-20:].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # Volume declining into pattern (coiling energy)
        first_half_vol = df['volume'].iloc[-40:-20].mean() if len(df) >= 40 else avg_volume
        second_half_vol = df['volume'].iloc[-20:].mean()
        volume_declining = second_half_vol < first_half_vol * 0.85
        
        # Require volume confirmation for breakout
        volume_confirmed = volume_ratio >= 1.3  # 30% above average
        high_volume_breakout = volume_ratio >= 1.6  # 60% above average
        
        # Only signal BULLISH_BREAKOUT if volume confirms
        if resistance_broken and volume_confirmed:
            signal = 'BULLISH_BREAKOUT'
        elif resistance_broken and not volume_confirmed:
            # Weak breakout - stay in PATTERN_FORMING
            signal = 'PATTERN_FORMING'
            resistance_broken = False  # Treat as not broken yet
        else:
            signal = 'PATTERN_FORMING'
        
        # Calculate pattern quality score for confidence
        quality_score = 50  # Base
        
        # Resistance touches quality
        if pattern['highs_count'] >= 4:
            quality_score += 15
        elif pattern['highs_count'] == 3:
            quality_score += 10
        else:
            quality_score += 5
        
        # Support lows quality  
        if pattern['lows_count'] >= 3:
            quality_score += 15
        elif pattern['lows_count'] == 2:
            quality_score += 10
        
        # Volume pattern bonus
        if volume_declining:
            quality_score += 10  # Good coiling
        
        # Breakout quality bonuses
        if resistance_broken and volume_confirmed:
            if high_volume_breakout:
                quality_score += 25  # Exceptional volume
            else:
                quality_score += 20  # Good volume
        
        # Assign confidence based on quality (70-85 range)
        if quality_score >= 85:
            confidence = 85  # A grade
        elif quality_score >= 70:
            confidence = 78  # B grade
        else:
            confidence = 70  # C grade
        
        # Target = pattern height projected upward
        pattern_height = pattern['resistance_level'] - pattern['support_start']
        target_price = pattern['resistance_level'] + pattern_height
        
        # Create unique pattern ID for event tracking
        pattern_id = f"{int(pattern['resistance_level'])}_{int(pattern['support_start'])}"
        
        # Detect new event
        is_new_event = (
            signal != self.prev_signal or
            pattern_id != self.prev_pattern_id
        ) and signal != 'NO_PATTERN'
        
        # Update state tracking
        if signal == self.prev_signal and pattern_id == self.prev_pattern_id:
            self.bars_in_state += 1
        else:
            self.bars_in_state = 1
        
        self.prev_signal = signal
        self.prev_pattern_id = pattern_id
        
        confluence_factors = []
        confluence_factors.append("Ascending Triangle detected")
        confluence_factors.append(f"Resistance: ${pattern['resistance_level']:.2f}")
        confluence_factors.append(f"Rising support: ${pattern['support_start']:.2f} → ${pattern['support_end']:.2f}")
        confluence_factors.append(f"Bullish continuation pattern")
        
        if resistance_broken:
            confluence_factors.append("✅ BREAKOUT confirmed - Bullish!")
        else:
            confluence_factors.append("⏳ Awaiting breakout")
        
        confluence_factors.append(f"Target: ${target_price:.2f}")
        confluence_factors.append("Success rate: 72% bullish")
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'pattern_type': 'ASCENDING_TRIANGLE',
            'resistance_level': round(pattern['resistance_level'], 2),
            'support_start': round(pattern['support_start'], 2),
            'support_end': round(pattern['support_end'], 2),
            'breakout_confirmed': resistance_broken,
            'volume_confirmed': volume_confirmed if resistance_broken else False,
            'volume_ratio': round(volume_ratio, 2),
            'volume_declining': volume_declining,
            'target_price': round(target_price, 2),
            'pattern_height': round(pattern_height, 2),
            'expected_success_rate': 0.72,
            'quality_score': quality_score,
            'pattern_grade': 'A' if quality_score >= 85 else ('B' if quality_score >= 70 else 'C'),
            'is_new_event': is_new_event,
            'bars_in_state': self.bars_in_state,
            'pattern_id': pattern_id,
            'highs_count': pattern['highs_count'],
            'lows_count': pattern['lows_count']
        }
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
