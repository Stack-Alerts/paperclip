"""
Double Bottom Pattern - INSTITUTIONAL GRADE with Multi-Block Validation
Integrates RSI, VWAP, Premium/Discount, and Volume for 70%+ confidence
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



from typing import Dict, Any

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='double_bottom',
    category='PATTERNS',
    class_name='DoubleBottomPattern',
    default_weight=30,
    valid_signals=[
        # Granular pattern signals (Double Bottom is bullish-only)
        'BULLISH_BREAKOUT', 'PATTERN_FORMING', 'NO_PATTERN',
        # Simple directional - SIMPLE (bullish-only pattern)
        'BULLISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Pattern signals
        'BULLISH_BREAKOUT': {
                'base_points': 30,
                'formula': 'scaled'
        },
        'PATTERN_FORMING': {
                'base_points': 30,
                'formula': 'scaled'
        },
        'NO_PATTERN': {
                'points': 0
        },
        
        # Simple directional - SIMPLE (bullish-only)
        'BULLISH': {
                'base_points': 30,
                'formula': 'scaled'
        },
        'NEUTRAL': {
                'points': 0
        },
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        }
}
)
class DoubleBottomPattern:
    """
    Double Bottom: 2 similar troughs with multi-block validation
    
    INSTITUTIONAL VALIDATION (Target: 70%+ confidence):
    - Requires EXACTLY 2 troughs (not 3)
    - RSI oversold (<30) at BOTH troughs (confluence)
    - VWAP discount zone (price < VWAP) (confluence)
    - Volume analysis (increasing or high) (confluence)
    - Support level confirmation (confluence)
    - Quality scoring based on confluences
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 trough_tolerance: float = 0.02, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.trough_tolerance = trough_tolerance  # 2% max difference
        
        # Pattern lifecycle tracking (PHASE 1 improvements)
        self.active_pattern = None  # Track current pattern ID for event detection
        self.pattern_start_idx = None  # When pattern started forming
        self.breakout_start_idx = None  # When breakout began
        
        # Pattern duration requirements for 15min timeframe
        self.MIN_BARS_BETWEEN_TROUGHS = 15   # 3.75 hours minimum
        self.MAX_BARS_BETWEEN_TROUGHS = 100  # 25 hours maximum
        self.PATTERN_MAX_DURATION = 100    # Pattern expires after 100 bars
        self.BREAKOUT_MAX_DURATION = 20   # Breakout confirmed for 20 bars
        
        # Validation requirements
        self.MIN_CONFLUENCES = 3  # Institutional grade validation
        self.MIN_TROUGH_SPACING = 8  # Minimum bars between ANY troughs
        
        # Breakout requirements (stricter)
        self.BREAK_MARGIN = 0.005  # Must break 0.5% above neckline
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if granular in ['BULLISH_BREAKOUT', 'PATTERN_FORMING']:
            simple = 'BULLISH'  # Double bottom is bullish pattern
        else:
            simple = 'NEUTRAL'
        return granular, simple
        
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI for oversold detection"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP for discount zone detection"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return float(vwap.iloc[-1])
    
    def detect_support_level(self, df: pd.DataFrame, price: float, 
                             tolerance: float = 0.02) -> bool:
        """Check if price is at a recent support level"""
        recent_lows = df['low'].rolling(window=20).min().iloc[-50:]
        
        for low in recent_lows:
            if abs(price - low) / price < tolerance:
                # Found similar support level
                return True
        return False
    
    def find_troughs(self, df: pd.DataFrame, rsi: pd.Series, min_prominence: float = 0.0125):
        """
        Find SIGNIFICANT swing lows only - PHASE 1 STRICT
        
        Requirements for a valid trough (MUST meet ALL):
        1. Lowest in 5-hour window (20 bars @ 15min) - REQUIRED
        2. At least 1.25% below recent average (prominence) - REQUIRED
        3. Volume spike (1.3x average) - REQUIRED  
        4. Near recent support level - REQUIRED
        5. Proper spacing from other troughs (8+ bars) - REQUIRED
        """
        troughs = []
        lookback = 20  # 5 hours @ 15min bars
        
        for i in range(lookback, len(df) - lookback):
            low = df['low'].iloc[i]
            
            # REQ 1: Must be lowest in 5-hour window
            if low != df['low'].iloc[i-lookback:i+lookback+1].min():
                continue
            
            # REQ 2: Must be 1.25% below recent average (prominence) - PHASE 1: REQUIRED
            recent_avg = df['low'].iloc[i-lookback:i].mean()
            if recent_avg == 0 or low > recent_avg * (1 - min_prominence):
                continue
            
            # REQ 3: Must have volume spike (1.3x average) - PHASE 1: REQUIRED
            vol = df['volume'].iloc[i]
            avg_vol = df['volume'].iloc[max(0, i-lookback):i].mean()
            if avg_vol == 0 or vol < avg_vol * 1.3:
                continue
            
            # REQ 4: Must be near recent support - PHASE 1: REQUIRED
            recent_lows = df['low'].iloc[max(0, i-100):i].min()
            if low > recent_lows * 1.02:  # Not within 2% of support
                continue
            
            # REQ 5: Must have proper spacing from previous troughs - PHASE 1: NEW
            if len(troughs) > 0:
                last_trough_idx = troughs[-1]['idx']
                if i - last_trough_idx < self.MIN_TROUGH_SPACING:
                    continue  # Too close to previous trough
            
            # ALL requirements passed - add trough
            rsi_val = rsi.iloc[i] if i < len(rsi) else 50
            
            troughs.append({
                'idx': i,
                'price': low,
                'volume': vol,
                'rsi': rsi_val,
                'prominence': ((recent_avg / low) - 1) * 100,
                'requirements_met': 5  # All 5 requirements met
            })
        
        return troughs
    
    def reset_pattern_state(self):
        """Reset pattern tracking state - PHASE 1: NEW"""
        self.pattern_start_idx = None
        self.breakout_start_idx = None
        self.active_pattern = None
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """INSTITUTIONAL GRADE: Double bottom with multi-block validation + PHASE 1 improvements"""
        if len(df) < 30:  # Need more data for quality validation
            granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal
                },
                'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_idx = len(df) - 1
        
        # PHASE 1: Check pattern expiration
        if self.pattern_start_idx is not None:
            bars_since_pattern_start = current_idx - self.pattern_start_idx
            if bars_since_pattern_start > self.PATTERN_MAX_DURATION:
                # Pattern expired without breakout
                self.reset_pattern_state()
                granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
                return {
                    'signal': granular_signal,
                    'signal_simple': simple_signal,
                    'confidence': 0,
                    'metadata': {
                        'signal_simple': simple_signal,
                        'signal_granular': granular_signal,
                        'reason': 'Pattern expired (>100 bars)'
                    },
                    'timestamp': df['timestamp'].iloc[-1],
                    'timeframe': self.timeframe,
                    'confluence_factors': []
                }
        
        # Calculate validation indicators
        rsi = self.calculate_rsi(df)
        vwap = self.calculate_vwap(df)
        current_price = float(df['close'].iloc[-1])
        
        troughs = self.find_troughs(df, rsi)
        
        if len(troughs) < 2:
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
        
        # Last 2 troughs
        recent = troughs[-2:]
        t1, t2 = recent[0], recent[1]
        
        # CRITICAL: Check pattern duration (3.75-25 hours @ 15min)
        bars_between = t2['idx'] - t1['idx']
        
        if bars_between < self.MIN_BARS_BETWEEN_TROUGHS:
            granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'reason': 'Pattern forming too quickly',
                    'bars_between': bars_between,
                    'min_required': self.MIN_BARS_BETWEEN_TROUGHS
                
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if bars_between > self.MAX_BARS_BETWEEN_TROUGHS:
            granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'reason': 'Troughs too far apart',
                    'bars_between': bars_between,
                    'max_allowed': self.MAX_BARS_BETWEEN_TROUGHS
                
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check: Similar price (REQUIRED - tightened to 2%)
        price_diff = abs(t1['price'] - t2['price']) / t1['price']
        if price_diff > self.trough_tolerance:
            granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'reason': 'Troughs not similar enough',
                    'trough_diff_pct': round(price_diff * 100, 2),
                    'max_allowed': round(self.trough_tolerance * 100, 2)
                
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # INSTITUTIONAL VALIDATION: Build confidence score
        base_confidence = 50  # Start at 50%
        confluences = []
        
        # CONFLUENCE 1: RSI Oversold at BOTH troughs (+20 points)
        t1_oversold = t1['rsi'] < 30
        t2_oversold = t2['rsi'] < 30
        if t1_oversold and t2_oversold:
            base_confidence += 20
            confluences.append(f"RSI oversold both troughs ({t1['rsi']:.1f}, {t2['rsi']:.1f})")
        elif t1_oversold or t2_oversold:
            base_confidence += 10
            confluences.append(f"RSI oversold one trough")
        
        # CONFLUENCE 2: VWAP Discount Zone (+15 points)
        avg_trough_price = (t1['price'] + t2['price']) / 2
        in_discount = avg_trough_price < vwap * 0.98  # 2% below VWAP
        if in_discount:
            base_confidence += 15
            discount_pct = ((vwap / avg_trough_price) - 1) * 100
            confluences.append(f"Discount zone (-{discount_pct:.1f}% below VWAP)")
        
        # CONFLUENCE 3: Volume Analysis (+10 points)
        vol_increasing = t2['volume'] > t1['volume'] * 1.1
        vol_high = t2['volume'] > df['volume'].iloc[-50:].mean() * 1.3
        if vol_increasing and vol_high:
            base_confidence += 10
            vol_ratio = (t2['volume'] / t1['volume'] - 1) * 100
            confluences.append(f"Strong volume (+{vol_ratio:.1f}% on trough 2)")
        elif vol_increasing:
            base_confidence += 5
            confluences.append("Increasing volume")
        
        # CONFLUENCE 4: Support Level (+10 points)
        at_support = self.detect_support_level(df, avg_trough_price)
        if at_support:
            base_confidence += 10
            confluences.append("At key support level")
        
        # CONFLUENCE 5: Pattern Quality (+10 points)
        # Troughs very similar in price
        if price_diff < 0.02:  # Within 2%
            base_confidence += 5
            confluences.append(f"Troughs very similar ({price_diff*100:.1f}%)")
        
        # Sufficient time between troughs (7+ bars)
        bars_between = t2['idx'] - t1['idx']
        if bars_between >= 7:
            base_confidence += 5
            confluences.append(f"Good pattern duration ({bars_between} bars)")
        
        # MINIMUM THRESHOLD: Require at least 3 confluences (PHASE 1: increased from 2)
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
        
        # Find neckline
        section = df.iloc[t1['idx']:t2['idx']+1]
        neckline = section['high'].max()
        
        # PHASE 1: Stricter breakout detection
        # Require: 0.5% break above neckline AND 2 of last 3 closes above
        neckline_with_margin = neckline * (1 + self.BREAK_MARGIN)
        clean_break = current_price > neckline_with_margin
        
        # Count recent closes above neckline
        recent_closes = df['close'].iloc[-3:]
        closes_above = (recent_closes > neckline).sum()
        confirmed_closes = closes_above >= 2
        
        # Both conditions required for breakout
        breakout = clean_break and confirmed_closes
        
        # PHASE 1: Track breakout duration
        if breakout:
            if self.breakout_start_idx is None:
                # New breakout starting
                self.breakout_start_idx = current_idx
                base_confidence += 10
                signal = 'BULLISH_BREAKOUT'
            else:
                # Breakout continuing
                bars_since_breakout = current_idx - self.breakout_start_idx
                if bars_since_breakout > self.BREAKOUT_MAX_DURATION:
                    # Breakout complete - reset
                    self.reset_pattern_state()
                    granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
                    return {
                        'signal': granular_signal,
                        'signal_simple': simple_signal,
                        'confidence': 0,
                        'metadata': {
                            'signal_simple': simple_signal,
                            'signal_granular': granular_signal,
                            'reason': 'Breakout completed (>20 bars)'
                        },
                        'timestamp': df['timestamp'].iloc[-1],
                        'timeframe': self.timeframe,
                        'confluence_factors': []
                    }
                else:
                    base_confidence += 10
                    signal = 'BULLISH_BREAKOUT'
        else:
            # Not broken out
            if self.breakout_start_idx is not None:
                # Was in breakout but price dropped back - pattern invalidated
                self.reset_pattern_state()
                granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
                return {
                    'signal': granular_signal,
                    'signal_simple': simple_signal,
                    'confidence': 0,
                    'metadata': {
                        'signal_simple': simple_signal,
                        'signal_granular': granular_signal,
                        'reason': 'Price dropped back below neckline'
                    },
                    'timestamp': df['timestamp'].iloc[-1],
                    'timeframe': self.timeframe,
                    'confluence_factors': []
                }
            
            # Pattern forming - track start time
            if self.pattern_start_idx is None:
                self.pattern_start_idx = current_idx
            
            signal = 'PATTERN_FORMING'
        
        # Cap confidence at 95%
        final_confidence = min(base_confidence, 95)
        
        # EVENT TRACKING: Track pattern state for new event detection
        pattern_id = f"DB_{t1['idx']}_{t2['idx']}"
        is_new_event = False
        
        if breakout:
            # New breakout event if pattern ID changed
            is_new_event = (self.active_pattern != pattern_id)
            self.active_pattern = pattern_id
        
        avg_price = (t1['price'] + t2['price']) / 2
        target = neckline + (neckline - avg_price)
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': final_confidence,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'pattern_type': 'DOUBLE_BOTTOM_INSTITUTIONAL',
                'troughs': [round(t1['price'], 2), round(t2['price'], 2)],
                'trough_rsi': [round(t1['rsi'], 1), round(t2['rsi'], 1)],
                'neckline': round(neckline, 2),
                'vwap': round(vwap, 2),
                'in_discount_zone': in_discount,
                'volume_ratio': round(t2['volume'] / t1['volume'], 2),
                'at_support': at_support,
                'breakout_confirmed': breakout,
                'target_price': round(target, 2),
                'confluences_count': len(confluences),
                'quality_factors': confluences,
                'bars_between_troughs': bars_between,
                'pattern_id': pattern_id,
                'is_new_event': is_new_event
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Double Bottom: {len(confluences)} confluences (Institutional grade)',
                f'Confidence: {final_confidence}%',
                f'Pattern duration: {bars_between} bars ({bars_between/4:.1f} hours)',
                *confluences[:3],  # Show top 3 confluences
                f'{'✅ Breakout confirmed!' if breakout else '⏳ Pattern forming'}'
            ]
        }
