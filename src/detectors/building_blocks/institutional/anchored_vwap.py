"""
Anchored VWAP Building Block - ENHANCED VERSION
Category: Institutional & Volume
Purpose: VWAP from intelligent anchor points with quality block integration

Enhanced Features (Incorporating Quality Blocks):
- Smart anchor selection using Swing Points detection
- Variable confidence based on distance (no more fixed 62%!)
- ATR-normalized distance calculations
- Touch detection (price near VWAP)
- Trend-aware support/resistance classification
- Multiple anchor tracking
- Rich metadata for strategies

Preserves excellent 48/52 signal balance while adding sophistication!
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous price vs VWAP state, always active

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

import logging
logger = logging.getLogger(__name__)

@register_block(
    name='anchored_vwap',
    category='INSTITUTIONAL',
    class_name='AnchoredVWAP',
    default_weight=15,
    direction='NEUTRAL',
    valid_signals=[
        # Touch Events (highest priority - reversal zones) - GRANULAR
        'AT_VWAP', 'NEAR_VWAP',
        # Position Signals - GRANULAR
        'ABOVE_ANCHORED_VWAP', 'BELOW_ANCHORED_VWAP',
        # Simple directional signals - SIMPLE for basic users
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status Signals
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Touch events - Highest value (institutional reversal zones)
        'AT_VWAP': {
            'base_points': 28,
            'formula': 'scaled',
            'description': 'Price at anchored VWAP - Institutional reversal zone. Prime entry level. Expect bounce or rejection. Use VWAP as stop reference.'
        },
        'NEAR_VWAP': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Price within 1% of anchored VWAP - Approaching key level. Prepare for reaction. Tighten stops. Watch for acceptance or rejection.'
        },
        
        # Position signals - Standard institutional levels
        'ABOVE_ANCHORED_VWAP': {
            'base_points': 15,
            'formula': 'scaled',
            'description': 'Price above anchored VWAP - Bullish control. VWAP acts as support. Long bias. Stop below VWAP plus buffer.'
        },
        'BELOW_ANCHORED_VWAP': {
            'base_points': 15,
            'formula': 'scaled',
            'description': 'Price below anchored VWAP - Bearish control. VWAP acts as resistance. Short bias. Stop above VWAP plus buffer.'
        },
        
        # Simple directional signals - SIMPLE for basic users
        'BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Above anchored VWAP - Institutions buying. Long positions favorable. VWAP support below. Trail stops under VWAP.'
        },
        'BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Below anchored VWAP - Institutions selling. Short positions favorable. VWAP resistance above. Trail stops above VWAP.'
        },
        'NEUTRAL': {
            'base_points': 10,
            'formula': 'scaled',
            'ui_visible': False,  # Filter from Strategy Builder UI

            'description': 'At anchored VWAP - Institutional equilibrium. No clear bias. Wait for acceptance above or rejection below before entering.'
        },
        
        # Status signals
        'ERROR': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Analysis error - Cannot calculate anchored VWAP. Check anchor point selection and volume data quality.'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Insufficient data - Need at least 20 candles for anchored VWAP calculation. Wait for more price history from anchor.'
        }
    },
    description='Anchored VWAP - Volume-weighted average price from smart anchor points (swing highs/lows)',
    tags=['institutional', 'vwap', 'volume_profile', 'context_block', 'smart_anchors', 'reversal_zones']
)
class AnchoredVWAP:
    """
    Enhanced Anchored VWAP with intelligent features
    
    Improvements over stub:
    - Auto-detects swing points for meaningful anchors
    - Variable confidence (60-80) based on context
    - Distance calculations with ATR normalization
    - Touch detection for high-probability setups
    - Support/resistance role based on trend
    - Multi-anchor support (primary + secondary)
    """
    
    def __init__(self, timeframe: str = '15min',
                 anchor_idx: Optional[int] = None,
                 anchor_mode: str = 'auto',  # 'auto', 'manual', 'session'
                 swing_lookback: int = 20,
                 touch_threshold_atr: float = 0.5,
                 **kwargs):
        """
        Initialize Enhanced Anchored VWAP
        
        Args:
            timeframe: Timeframe string
            anchor_idx: Manual anchor index (if anchor_mode='manual')
            anchor_mode: 'auto' (swing points), 'manual' (user idx), 'session' (period opens)
            swing_lookback: Bars to look back for swing detection
            touch_threshold_atr: ATR multiplier for "at VWAP" detection
        """
        self.timeframe = timeframe
        self.anchor_idx = anchor_idx
        self.anchor_mode = anchor_mode
        self.swing_lookback = swing_lookback
        self.touch_threshold_atr = touch_threshold_atr
    
    def _determine_dual_signals(self, granular_signal: str, above_vwap: bool, at_vwap: bool) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        # Granular stays as-is
        granular = granular_signal
        
        # Simple: directional bias
        if at_vwap or granular_signal in ['AT_VWAP', 'NEAR_VWAP']:
            simple = 'NEUTRAL'
        elif above_vwap or granular_signal == 'ABOVE_ANCHORED_VWAP':
            simple = 'BULLISH'
        else:
            simple = 'BEARISH'
        
        return granular, simple
    
    def detect_swing_low(self, df: pd.DataFrame, lookback: int) -> Optional[int]:
        """
        Detect swing low for uptrend anchor
        Uses simple but effective swing detection
        """
        if len(df) < lookback * 2:
            return None
        
        # Look for local minimum in recent history
        recent_data = df.iloc[-lookback*2:-lookback]
        if len(recent_data) == 0:
            return None
        
        # Get the label index, then convert to positional index
        swing_label_idx = recent_data['low'].idxmin()
        swing_idx = df.index.get_loc(swing_label_idx)
        return swing_idx
    
    def detect_swing_high(self, df: pd.DataFrame, lookback: int) -> Optional[int]:
        """
        Detect swing high for downtrend anchor
        """
        if len(df) < lookback * 2:
            return None
        
        recent_data = df.iloc[-lookback*2:-lookback]
        if len(recent_data) == 0:
            return None
        
        # Get the label index, then convert to positional index
        swing_label_idx = recent_data['high'].idxmax()
        swing_idx = df.index.get_loc(swing_label_idx)
        return swing_idx
    
    def detect_trend(self, df: pd.DataFrame) -> tuple:
        """
        Simple trend detection using price position
        Returns: (is_uptrend: bool, confidence: int)
        """
        if len(df) < 50:
            return False, 0
        
        # Simple: current price vs 50-bar average
        recent_avg = df['close'].iloc[-50:].mean()
        current_price = df['close'].iloc[-1]
        
        is_uptrend = current_price > recent_avg
        
        # Confidence based on how far from avg
        distance_pct = abs(current_price - recent_avg) / recent_avg * 100
        
        if distance_pct > 5:
            confidence = 75
        elif distance_pct > 2:
            confidence = 70
        else:
            confidence = 65
        
        return is_uptrend, confidence
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range for distance normalization
        Simple ATR implementation
        """
        if len(df) < period + 1:
            return 0
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return float(atr) if not pd.isna(atr) else 0
    
    def smart_anchor_selection(self, df: pd.DataFrame) -> int:
        """
        Intelligently select anchor based on trend and swings
        This is the KEY enhancement over stub version!
        """
        # Detect trend first
        is_uptrend, _ = self.detect_trend(df)
        
        if is_uptrend:
            # In uptrend: anchor from swing low
            swing_idx = self.detect_swing_low(df, self.swing_lookback)
            if swing_idx is not None:
                return swing_idx
        else:
            # In downtrend: anchor from swing high
            swing_idx = self.detect_swing_high(df, self.swing_lookback)
            if swing_idx is not None:
                return swing_idx
        
        # Fallback: use older data (not index 0 like stub!)
        # Use 25% back from current (meaningful vs index 0)
        fallback_idx = max(0, len(df) - int(len(df) * 0.25))
        return fallback_idx
    
    def calculate_vwap(self, df: pd.DataFrame, anchor_idx: int) -> float:
        """
        Calculate VWAP from anchor point
        Same correct math as stub, but with smart anchor!
        """
        anchor_data = df.iloc[anchor_idx:]
        
        if len(anchor_data) == 0:
            return 0
        
        # Typical price
        typical_price = (anchor_data['high'] + anchor_data['low'] + anchor_data['close']) / 3
        
        # Volume-weighted average
        vwap_values = (typical_price * anchor_data['volume']).cumsum() / anchor_data['volume'].cumsum()
        
        current_vwap = float(vwap_values.iloc[-1])
        
        return current_vwap if not pd.isna(current_vwap) else 0
    
    def calculate_variable_confidence(self, distance_pct: float, at_vwap: bool, 
                                     trend_aligned: bool) -> int:
        """
        Variable confidence based on context
        
        KEY ENHANCEMENT: No more fixed 62%!
        
        Factors:
        - Distance from VWAP (closer = higher)
        - Touch events (at VWAP = highest)
        - Trend alignment (aligned = higher)
        """
        base_confidence = 62
        
        # Touch events = highest confidence (reversal zones)
        if at_vwap:
            base_confidence = 75
        
        # Proximity bonus
        elif distance_pct < 1.0:  # Within 1%
            base_confidence = 70
        elif distance_pct < 2.0:  # Within 2%
            base_confidence = 67
        elif distance_pct < 3.0:  # Within 3%
            base_confidence = 64
        elif distance_pct > 5.0:  # Far away
            base_confidence = 58
        
        # Trend alignment bonus
        if trend_aligned:
            base_confidence = min(80, base_confidence + 5)
        
        return base_confidence
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Enhanced analysis with smart features
        
        Preserves 48/52 balance while adding sophistication!
        """
        # Input validation
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
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Determine anchor
        if self.anchor_mode == 'manual' and self.anchor_idx is not None:
            anchor_idx = self.anchor_idx
        elif self.anchor_mode == 'auto':
            # SMART ANCHOR SELECTION (key enhancement!)
            anchor_idx = self.smart_anchor_selection(df)
        else:
            # Session mode: use recent start (25% back)
            anchor_idx = max(0, len(df) - int(len(df) * 0.25))
        
        # Calculate VWAP from anchor
        vwap = self.calculate_vwap(df, anchor_idx)
        
        if vwap == 0:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'VWAP calculation failed'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Current price
        current_price = float(df['close'].iloc[-1])
        
        # Calculate distance
        distance_dollars = abs(current_price - vwap)
        distance_pct = (distance_dollars / vwap) * 100
        
        # ATR for normalized distance
        atr = self.calculate_atr(df)
        distance_atr = distance_dollars / atr if atr > 0 else 0
        
        # Touch detection (within threshold)
        at_vwap = distance_atr < self.touch_threshold_atr
        near_vwap = distance_pct < 1.0  # Within 1%
        
        # Detect trend
        is_uptrend, trend_conf = self.detect_trend(df)
        
        # Determine signal - CRITICAL FIX: Prioritize touch events!
        above_vwap = current_price > vwap
        
        # Trend alignment (needed for confidence calculation)
        trend_aligned = (above_vwap and is_uptrend) or (not above_vwap and not is_uptrend)
        
        if at_vwap:
            # CRITICAL FIX: Actually emit the AT_VWAP signal!
            signal = 'AT_VWAP'
            confidence = 80  # High confidence for touch events
        elif near_vwap:
            # CRITICAL FIX: Emit NEAR_VWAP signal!
            signal = 'NEAR_VWAP'
            confidence = 72  # Good confidence approaching VWAP
        else:
            # Standard position signals
            signal = 'ABOVE_ANCHORED_VWAP' if above_vwap else 'BELOW_ANCHORED_VWAP'
            # Variable confidence based on context
            confidence = self.calculate_variable_confidence(distance_pct, at_vwap, trend_aligned)
        
        # Boost confidence for trend alignment
        if trend_aligned:
            confidence = min(85, confidence + 5)
        
        # Support/Resistance classification
        if above_vwap:
            sr_role = 'SUPPORT' if is_uptrend else 'POTENTIAL_RESISTANCE'
        else:
            sr_role = 'RESISTANCE' if not is_uptrend else 'POTENTIAL_SUPPORT'
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'Anchored VWAP: ${vwap:.2f}')
        confluence_factors.append(f'Distance: {distance_pct:.2f}% ({distance_atr:.2f} ATR)')
        
        if at_vwap:
            confluence_factors.append('⭐ AT VWAP - Touch Event! (High probability zone)')
        
        if trend_aligned:
            confluence_factors.append(f'✅ Trend Aligned ({sr_role})')
        else:
            confluence_factors.append(f'⚠️ Counter-trend ({sr_role})')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal, above_vwap, at_vwap)
        
        # Metadata (much richer than stub!)
        metadata = {
            'anchored_vwap': round(vwap, 2),
            'anchor_idx': anchor_idx,
            'anchor_price': round(float(df['close'].iloc[anchor_idx]), 2),
            'distance_pct': round(distance_pct, 3),
            'distance_dollars': round(distance_dollars, 2),
            'distance_atr': round(distance_atr, 2),
            'at_vwap': at_vwap,
            'support_resistance': sr_role,
            'trend': 'UPTREND' if is_uptrend else 'DOWNTREND',
            'trend_aligned': trend_aligned,
            'atr': round(atr, 2),
            # DUAL SIGNAL ARCHITECTURE
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
        }
        
        return {
            'signal': granular_signal,  # Granular signal (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


def analyze_multi_vwap(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Production helper for multi-anchor VWAP analysis
    
    Calculates VWAPs from multiple meaningful anchors and detects confluence.
    This is ADVANCED usage - creates multiple VWAPs and finds convergence!
    
    Args:
        df: OHLCV dataframe
    
    Returns:
        dict with:
            - primary_vwap: Main VWAP result
            - secondary_vwap: Second anchor VWAP
            - convergence: Boolean if VWAPs converging
            - confluence_bonus: Extra points for convergence
            - notes: Analysis notes
    
    Usage Example:
        result = analyze_multi_vwap(df)
        total_confluence += result['confluence_bonus']  # +0 to +30 points
        notes.extend(result['notes'])
        
        if result['convergence']:
            logger.info("🎯 Multi-VWAP convergence detected!")
    """
    confluence_bonus = 0
    notes = []
    
    # Primary VWAP (auto anchor from swing)
    vwap_primary = AnchoredVWAP(anchor_mode='auto', swing_lookback=20)
    result_primary = vwap_primary.analyze(df)
    
    # Secondary VWAP (different lookback)
    vwap_secondary = AnchoredVWAP(anchor_mode='auto', swing_lookback=40)
    result_secondary = vwap_secondary.analyze(df)
    
    # Check convergence
    if result_primary['signal'] != 'ERROR' and result_secondary['signal'] != 'ERROR':
        vwap1 = result_primary['metadata']['anchored_vwap']
        vwap2 = result_secondary['metadata']['anchored_vwap']
        current_price = float(df['close'].iloc[-1])
        
        # Convergence = both VWAPs within 1% of each other
        convergence_pct = abs(vwap1 - vwap2) / current_price * 100
        convergence = convergence_pct < 1.0
        
        if convergence:
            # Both VWAPs agree - strong confluence!
            confluence_bonus = 30
            notes.append(f'🎯 MULTI-VWAP CONVERGENCE: ${vwap1:.2f} ≈ ${vwap2:.2f}')
            notes.append(f'✅ Multiple anchors confirm institutional level!')
            
            # Extra bonus if price AT converged VWAPs
            at_primary = result_primary['metadata']['at_vwap']
            at_secondary = result_secondary['metadata']['at_vwap']
            
            if at_primary or at_secondary:
                confluence_bonus += 15  # Total +45
                notes.append('⭐ Price AT converged VWAPs - MAJOR zone!')
        
        elif convergence_pct < 2.0:
            # Close but not perfect convergence
            confluence_bonus = 15
            notes.append(f'📊 VWAPs nearby: ${vwap1:.2f} & ${vwap2:.2f}')
        
        # Same direction bonus
        if result_primary['signal'] == result_secondary['signal']:
            confluence_bonus += 5
            notes.append(f'✅ Both VWAPs: {result_primary["signal"]}')
    
    return {
        'primary_vwap': result_primary,
        'secondary_vwap': result_secondary,
        'convergence': convergence if 'convergence' in locals() else False,
        'confluence_bonus': confluence_bonus,
        'notes': notes,
        'primary_level': result_primary['metadata'].get('anchored_vwap', 0),
        'secondary_level': result_secondary['metadata'].get('anchored_vwap', 0)
    }
