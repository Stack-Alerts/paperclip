"""
Descending Triangle Pattern Building Block
Category: Pattern-Based Building Blocks
Purpose: Identifies bearish continuation with falling highs and flat support
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
    name='descending_triangle',
    category='PATTERNS',
    class_name='DescendingTrianglePattern',
    default_weight=30,
    valid_signals=[
        # Granular pattern signals (Descending Triangle is bearish-only)
        'BEARISH_BREAKDOWN', 'PATTERN_FORMING', 'NO_PATTERN',
        # Simple directional - SIMPLE (required for dual signal architecture)
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    tags=['bearish_only_pattern'],  # BULLISH signal will never fire - bearish continuation pattern
    signal_tiers={
        # Pattern signals
        'BEARISH_BREAKDOWN': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Descending triangle breakdown - Support broken with volume. Enter shorts aggressively. Target = pattern height. Stop above resistance line. 68% success rate.'
        },
        'PATTERN_FORMING': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Descending triangle forming - Falling highs + flat support. Bearish continuation pattern. Wait for breakdown below support. Prepare short entry.'
        },
        'NO_PATTERN': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No descending triangle - Pattern conditions not met. No falling highs or flat support detected. Wait for pattern formation.'
        },
        
        # Simple directional - SIMPLE (required for dual signal architecture)
        'BULLISH': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No bullish signal - Descending Triangle is a bearish-only pattern. This signal never fires.'
        },
        'BEARISH': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bearish triangle pattern - Descending triangle detected or broken down. Short positions favorable. Use support breakdown for entry.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No triangle pattern - Market structure unclear. No descending triangle setup. Wait for pattern formation before trading.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot detect pattern. Check data quality and minimum bars requirement.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need at least 50 candles for descending triangle detection. Wait for more price history.'
        }
}
)
class DescendingTrianglePattern:
    """
    Descending Triangle Pattern Detector
    
    Bearish continuation: Falling resistance + horizontal support
    - Lower highs (descending trendline)
    - Flat support level
    - Converging price action
    - Breakout typically bearish
    
    Success Rate: 68% bearish (research validated)
    
    Parameters:
        min_pattern_bars: Minimum bars (default: 20)
        support_tolerance: Tolerance for flat support (default: 0.01)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 support_tolerance: float = 0.01, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.support_tolerance = support_tolerance
        
        # Pattern lifecycle tracking (PHASE 1 improvements)
        self.active_pattern = None
        self.pattern_start_idx = None
        self.breakout_start_idx = None
        
        # Pattern duration requirements for 15min timeframe
        self.MIN_TRIANGLE_BARS = 15    # 3.75 hours minimum
        self.MAX_TRIANGLE_DURATION = 80  # 20 hours maximum
        self.BREAKOUT_MAX_DURATION = 20  # Breakout confirmed for 20 bars
        
        # Validation requirements (STRICTER for better selectivity)
        self.MIN_CONFLUENCES = 3  # Keep at 3
        self.SUPPORT_TOLERANCE = 0.020  # 2.0% tolerance (final adjustment)
        self.MIN_SLOPE = -0.0012  # Final slope adjustment
        
        # Breakout requirements
        self.BREAK_MARGIN = 0.005  # Must break 0.5% below support
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if granular in ['BEARISH_BREAKDOWN', 'PATTERN_FORMING']:
            simple = 'BEARISH'  # Descending triangle is bearish
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
    
    def is_descending_resistance(self, highs: List) -> bool:
        """Check if highs are falling"""
        if len(highs) < 2:
            return False
        
        for i in range(len(highs) - 1):
            if highs[i+1]['price'] >= highs[i]['price']:
                return False
        return True
    
    def is_flat_support(self, lows: List) -> bool:
        """Check if lows form flat support"""
        if len(lows) < 2:
            return False
        
        prices = [l['price'] for l in lows]
        avg_price = np.mean(prices)
        
        for price in prices:
            if abs(price - avg_price) / avg_price > self.SUPPORT_TOLERANCE:
                return False
        return True
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI for bearish alignment"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP for trend confirmation"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return float(vwap.iloc[-1])
    
    def detect_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect Descending Triangle"""
        if len(df) < self.min_pattern_bars:
            return None
        
        highs, lows = self.find_swing_points(df)
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        recent_highs = highs[-min(4, len(highs)):]
        recent_lows = lows[-min(4, len(lows)):]
        
        if not self.is_flat_support(recent_lows):
            return None
        
        if not self.is_descending_resistance(recent_highs):
            return None
        
        support_level = np.mean([l['price'] for l in recent_lows])
        resistance_slope = (recent_highs[-1]['price'] - recent_highs[0]['price']) / len(recent_highs)
        
        return {
            'support_level': support_level,
            'resistance_start': recent_highs[0]['price'],
            'resistance_end': recent_highs[-1]['price'],
            'resistance_slope': resistance_slope,
            'completion': 100.0
        }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """INSTITUTIONAL GRADE: Descending Triangle with multi-block validation"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 50:
            granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'error': 'Need at least 50 bars'
                },
                'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
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
        
        # Validate slope is descending enough
        if pattern['resistance_slope'] > self.MIN_SLOPE:
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
        
        # Calculate validation indicators
        rsi = self.calculate_rsi(df)
        vwap = self.calculate_vwap(df)
        current_price = float(df['close'].iloc[-1])
        current_volume = df['volume'].iloc[-10:].mean()
        earlier_volume = df['volume'].iloc[-30:-10].mean()
        
        # INSTITUTIONAL VALIDATION: Build confidence score
        base_confidence = 60  # Start at 60%
        confluences = []
        
        current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
        
        # CONFLUENCE 1: RSI Bearish Alignment (+10 points)
        if current_rsi < 50:
            base_confidence += 10
            confluences.append(f"RSI bearish ({current_rsi:.1f})")
        elif current_rsi < 60:
            base_confidence += 5
            confluences.append(f"RSI near-bearish ({current_rsi:.1f})")
        
        # CONFLUENCE 2: VWAP Trend Confirmation (+10 points)
        if current_price < vwap:
            base_confidence += 10
            vwap_diff = ((current_price / vwap) - 1) * 100
            confluences.append(f"Below VWAP ({vwap_diff:.1f}%)")
        
        # CONFLUENCE 3: Volume Pattern (+5 points)
        vol_declining = current_volume < earlier_volume * 0.9
        if vol_declining:
            base_confidence += 5
            confluences.append("Volume declining")
        
        # CONFLUENCE 4: Pattern Quality (+10 points)
        slope_pct = abs(pattern['resistance_slope'] / pattern['resistance_start']) * 100
        if slope_pct > 0.5:  # Good descending slope
            base_confidence += 5
            confluences.append(f"Strong descent ({slope_pct:.1f}%)")
        
        support_quality = abs((max([l['price'] for l in self.find_swing_points(df)[1][-4:]]) - 
                               min([l['price'] for l in self.find_swing_points(df)[1][-4:]])) / 
                              pattern['support_level'])
        if support_quality < 0.01:  # Tight support
            base_confidence += 5
            confluences.append("Tight support level")
        
        # MINIMUM THRESHOLD: Require at least 3 confluences
        if len(confluences) < self.MIN_CONFLUENCES:
            granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'reason': 'Insufficient validation',
                    'confluences_found': len(confluences),
                    'confluences_required': self.MIN_CONFLUENCES
                
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check for breakdown
        support_broken = current_price < pattern['support_level'] * (1 - self.BREAK_MARGIN)
        signal = 'BEARISH_BREAKDOWN' if support_broken else 'PATTERN_FORMING'
        
        # BREAKDOWN gets additional confidence boost
        if support_broken:
            recent_volume = df['volume'].iloc[-3:].mean()
            if recent_volume > current_volume * 1.2:
                base_confidence += 15
                confluences.append("Breakdown with volume surge!")
            else:
                base_confidence += 10
        
        # Cap confidence at 95%
        final_confidence = min(base_confidence, 95)
        
        pattern_height = pattern['resistance_start'] - pattern['support_level']
        target_price = pattern['support_level'] - pattern_height
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': final_confidence,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'pattern_type': 'DESCENDING_TRIANGLE_INSTITUTIONAL',
                'direction': 'BEARISH',
                'support_level': round(pattern['support_level'], 2),
                'resistance_start': round(pattern['resistance_start'], 2),
                'resistance_end': round(pattern['resistance_end'], 2),
                'resistance_slope': round(pattern['resistance_slope'], 4),
                'current_rsi': round(current_rsi, 1),
                'vwap': round(vwap, 2),
                'volume_declining': vol_declining,
                'breakdown_confirmed': support_broken,
                'target_price': round(target_price, 2),
                'pattern_height': round(pattern_height, 2),
                'confluences_count': len(confluences),
                'quality_factors': confluences
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Descending Triangle: {len(confluences)} confluences',
                f'Confidence: {final_confidence}%',
                *confluences[:4],
                f'{'✅ BEARISH breakdown!' if support_broken else '⏳ Pattern forming'}'
            ]
        }
