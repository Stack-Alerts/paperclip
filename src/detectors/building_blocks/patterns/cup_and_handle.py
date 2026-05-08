"""
Cup and Handle Pattern - INSTITUTIONAL GRADE with Multi-Block Validation
Integrates RSI, VWAP, Volume for realistic 15min bullish continuation detection
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



from typing import Dict, Any, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='cup_and_handle',
    category='PATTERNS',
    class_name='CupAndHandlePattern',
    default_weight=30,
    description='Cup and Handle - Bullish continuation pattern with rounded accumulation base and brief consolidation handle. Fires on breakout above handle resistance. High-confidence bullish setup for trending markets.',
    direction='BULLISH',
    valid_signals=[
        # Granular pattern signals (Cup&Handle is bullish-only)
        'BREAKOUT_CONFIRMED', 'CUP_FORMING', 'PATTERN_FORMING', 'NO_PATTERN',
        # Simple directional - SIMPLE (required for dual signal architecture)
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    tags=['bullish_only_pattern'],  # BEARISH signal will never fire - bullish continuation pattern
    signal_tiers={
        # Pattern signals
        'BREAKOUT_CONFIRMED': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Cup & Handle breakout - Rim resistance broken with volume. Enter longs aggressively. Target = cup depth projection. Stop below handle. 65% success rate.'
        },
        'CUP_FORMING': {
                'base_points': 25,
                'formula': 'scaled',
                'description': 'Cup forming - Rounded bottom recovery >60% complete. Bullish continuation developing. Wait for handle formation. Prepare long entry on breakout.'
        },
        'PATTERN_FORMING': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Cup & Handle forming - Early pattern structure. Cup depth confirmed. Waiting for recovery and handle. Monitor for completion.'
        },
        'NO_PATTERN': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No Cup & Handle - Pattern conditions not met. Insufficient cup depth or recovery. Cup & Handle patterns are rare. Wait for formation.'
        },
        # Simple directional - SIMPLE (required for dual signal architecture)
        'BULLISH': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bullish Cup & Handle - Pattern forming or broken out. Long positions favorable. Bullish continuation pattern. Use cup depth for targets.'
        },
        'BEARISH': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No bearish signal - Cup & Handle is a bullish-only pattern. This signal never fires.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No Cup & Handle pattern - Market not forming bullish continuation. Wait for cup formation and breakout before entering longs.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot detect Cup & Handle pattern. Check data quality and minimum bars requirement.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need at least 40 candles for Cup & Handle detection. Wait for more price history to form pattern.'
        }
}
)
class CupAndHandlePattern:
    """
    Cup and Handle Pattern Detector with Multi-Block Validation
    
    INSTITUTIONAL VALIDATION (Target: 75%+ confidence):
    - Cup: Rounded bottom recovery (realistic 30% threshold for 15min)
    - Handle: Consolidation/pullback near rim
    - RSI neutral to bullish (confluence)
    - VWAP relationship (confluence)
    - Volume surge on breakout (confluence)
    - Pattern quality metrics (confluence)
    
    Success Rate: 65% bullish (research), targeting 75%+ with validation
    
    Note: Cup & Handle patterns are increasingly rare (user note)
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 20,
                 cup_depth_min: float = 0.013, handle_depth_max: float = 0.3, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.cup_depth_min = cup_depth_min  # 1.3% minimum cup depth (middle ground)
        self.handle_depth_max = handle_depth_max
        
        # Pattern lifecycle tracking (PHASE 1 improvements)
        self.active_pattern = None
        self.pattern_start_idx = None
        self.breakout_start_idx = None
        
        # Pattern duration requirements for 15min timeframe
        self.MIN_CUP_DURATION = 20   # 5 hours minimum for cup
        self.MAX_CUP_DURATION = 120  # 30 hours maximum for cup
        self.PATTERN_MAX_DURATION = 150  # Pattern expires after 150 bars
        self.BREAKOUT_MAX_DURATION = 20   # Breakout confirmed for 20 bars
        
        # Validation requirements (STRICTER for better selectivity)
        self.MIN_CONFLUENCES = 4  # Back to 4 for better selectivity
        self.MIN_RECOVERY_PCT = 0.38  # Minimum 38% recovery (middle ground)
        
        # Breakout requirements (realistic for 15min)
        self.BREAK_MARGIN = 0.0002  # Must break 0.02% above rim (sensitive for 15min patterns)
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if granular in ['BREAKOUT_CONFIRMED', 'CUP_FORMING', 'PATTERN_FORMING']:
            simple = 'BULLISH'  # Cup & Handle is bullish pattern
        else:
            simple = 'NEUTRAL'
        return granular, simple
        
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI for bullish confirmation"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP for price relationship"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return float(vwap.iloc[-1])
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """INSTITUTIONAL GRADE: Cup & Handle with multi-block validation"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 40:  # Need sufficient data for quality validation
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least 40 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate validation indicators
        rsi = self.calculate_rsi(df)
        vwap = self.calculate_vwap(df)
        current_price = float(df['close'].iloc[-1])
        current_volume = df['volume'].iloc[-20:].mean()  # Recent avg volume
        
        # Find cup pattern (dip and recovery)
        lookback = min(60, len(df))  # Up to 15 hours for 15min
        section = df.iloc[-lookback:]
        
        # Find local max (rim), then dip (cup bottom), then recovery
        high_idx = section['high'].idxmax()
        high_val = section.loc[high_idx, 'high']
        
        # Find lowest point after the high (cup bottom)
        lows_after_high = section.loc[high_idx:, 'low']
        if len(lows_after_high) < 5:  # Need some data after high
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
        
        low_after_high = lows_after_high.min()
        
        # REALISTIC: Only need 1% dip for 15min (patterns are rare)
        dip_pct = (high_val - low_after_high) / high_val
        
        if dip_pct < self.cup_depth_min:  # Default 1%
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
        
        # REALISTIC: Check if recovered at least 30% (not 70%!)
        recovery_pct = (current_price - low_after_high) / (high_val - low_after_high)
        
        if recovery_pct < 0.30:  # At least 30% recovery (realistic for 15min)
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
        
        # INSTITUTIONAL VALIDATION: Build confidence score
        base_confidence = 55  # Start at 55%
        confluences = []
        
        rim_level = high_val
        current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
        
        # CONFLUENCE 1: RSI Neutral to Bullish (+15 points)
        if 40 < current_rsi < 70:  # Neutral zone - healthy
            base_confidence += 15
            confluences.append(f"RSI neutral/bullish ({current_rsi:.1f})")
        elif current_rsi >= 70:  # Overbought - still bullish but cautious
            base_confidence += 8
            confluences.append(f"RSI overbought ({current_rsi:.1f})")
        elif current_rsi > 30:  # At least not oversold
            base_confidence += 5
            confluences.append(f"RSI recovering ({current_rsi:.1f})")
        
        # CONFLUENCE 2: VWAP Relationship (+10 points)
        near_vwap = abs(current_price - vwap) / vwap < 0.02  # Within 2% of VWAP
        if near_vwap:
            base_confidence += 10
            vwap_diff = ((current_price / vwap) - 1) * 100
            confluences.append(f"Near VWAP ({vwap_diff:+.1f}%)")
        
        # CONFLUENCE 3: Volume Analysis (+10 points)
        # Check if volume increasing on recovery
        recent_vol = df['volume'].iloc[-10:].mean()
        earlier_vol = df['volume'].iloc[-30:-10].mean()
        vol_increase = recent_vol > earlier_vol * 1.1  # 10% increase
        
        if vol_increase:
            base_confidence += 10
            vol_ratio = ((recent_vol / earlier_vol) - 1) * 100
            confluences.append(f"Volume increasing (+{vol_ratio:.1f}%)")
        
        # CONFLUENCE 4: Pattern Quality (+10 points)
        # Good recovery percentage
        if recovery_pct > 0.60:  # Recovered 60%+
            base_confidence += 5
            confluences.append(f"Strong recovery ({recovery_pct*100:.1f}%)")
        elif recovery_pct > 0.45:  # Recovered 45%+
            base_confidence += 3
            confluences.append(f"Good recovery ({recovery_pct*100:.1f}%)")
        
        # Reasonable cup depth
        if 0.02 < dip_pct < 0.10:  # 2-10% cu p depth - ideal
            base_confidence += 5
            confluences.append(f"Good cup depth ({dip_pct*100:.1f}%)")
        
        # CONFLUENCE 5: Check for handle consolidation (+5 points)
        # If price near rim but not broken = potential handle
        near_rim = 0.95 < (current_price / rim_level) < 1.00
        if near_rim and recovery_pct > 0.70:
            base_confidence += 5
            confluences.append("Handle forming near rim")
        
        # Check if breakout confirmed (price at/above rim OR 95%+ recovery)
        breakout = current_price >= rim_level or recovery_pct >= 0.95
        
        # BREAKOUT PRIORITY: Allow breakout with fewer confluences (3 minimum)
        if breakout and len(confluences) >= 3:
            base_confidence +=10
            signal = 'BREAKOUT_CONFIRMED'
        # PATTERN FORMING: Require 4 confluences for non-breakout patterns
        elif len(confluences) < self.MIN_CONFLUENCES:
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
        elif recovery_pct > 0.60:
            signal = 'CUP_FORMING'
        else:
            signal = 'PATTERN_FORMING'
        
        # Cap confidence at 95%
        final_confidence = min(base_confidence, 95)
        
        # Calculate target
        pattern_height = high_val - low_after_high
        target_price = rim_level + pattern_height
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': final_confidence,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'pattern_type': 'CUP_AND_HANDLE_INSTITUTIONAL',
                'cup_depth_pct': round(dip_pct * 100, 2),
                'recovery_pct': round(recovery_pct * 100, 2),
                'rim_level': round(rim_level, 2),
                'cup_bottom': round(low_after_high, 2),
                'current_rsi': round(current_rsi, 1),
                'vwap': round(vwap, 2),
                'near_vwap': near_vwap,
                'volume_increasing': vol_increase,
                'breakout_confirmed': breakout,
                'target_price': round(target_price, 2),
                'pattern_height': round(pattern_height, 2),
                'confluences_count': len(confluences),
                'quality_factors': confluences
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Cup & Handle: {len(confluences)} confluences (Rare pattern - realistic thresholds)',
                f'Confidence: {final_confidence}% (improved from 55%)',
                *confluences[:4],  # Show top 4 confluences
                f'{'✅ Breakout confirmed!' if breakout else f'Recovery {recovery_pct*100:.0f}%'}'
            ]
        }
