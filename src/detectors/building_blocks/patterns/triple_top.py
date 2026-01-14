"""
Triple Top Pattern - INSTITUTIONAL GRADE with Multi-Block Validation
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
    name='triple_top',
    category='PATTERNS',
    class_name='TripleTopPattern',
    default_weight=30,
    valid_signals=[
        # Granular pattern signals
        'BEARISH_BREAKDOWN', 'PATTERN_FORMING', 'NO_PATTERN',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Pattern signals
        'BEARISH_BREAKDOWN': {
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
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 30,
                'formula': 'scaled'
        },
        'BEARISH': {
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
class TripleTopPattern:
    """
    Triple Top: 3 similar peaks with multi-block validation
    
    INSTITUTIONAL VALIDATION (Target: 70%+ confidence):
    - Requires EXACTLY 3 peaks (not 2)
    - RSI overbought (>70) at ALL 3 peaks (confluence)
    - VWAP premium zone (price > VWAP) (confluence)
    - Volume analysis (decreasing or distribution) (confluence)
    - Resistance level confirmation (confluence)
    - Quality scoring based on confluences
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 peak_tolerance: float = 0.025, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.peak_tolerance = peak_tolerance  # 2.5% max difference (middle ground for triple)
        
        # Pattern lifecycle tracking (PHASE 1 improvements)
        self.active_pattern = None  # Track current pattern ID for event detection
        self.pattern_start_idx = None  # When pattern started forming
        self.breakdown_start_idx = None  # When breakdown began
        
        # Pattern duration requirements for 15min timeframe
        self.MIN_BARS_BETWEEN_PEAKS = 12   # 3 hours minimum (middle ground)
        self.MAX_BARS_BETWEEN_PEAKS = 100  # 25 hours maximum
        self.PATTERN_MAX_DURATION = 150    # Pattern expires after 150 bars (longer for 3 peaks)
        self.BREAKDOWN_MAX_DURATION = 20   # Breakdown confirmed for 20 bars
        
        # Validation requirements (STRICTER for better selectivity)
        self.MIN_CONFLUENCES = 4  # Increased from 3 for institutional grade
        self.MIN_PEAK_SPACING = 7  # 7 bars minimum between peaks
        
        # Breakdown requirements (stricter)
        self.BREAK_MARGIN = 0.005  # Must break 0.5% below neckline
        
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI for overbought detection"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP for premium zone detection"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return float(vwap.iloc[-1])
    
    def detect_resistance_level(self, df: pd.DataFrame, price: float, 
                                tolerance: float = 0.02) -> bool:
        """Check if price is at a recent resistance level"""
        recent_highs = df['high'].rolling(window=20).max().iloc[-50:]
        
        for high in recent_highs:
            if abs(price - high) / price < tolerance:
                # Found similar resistance level
                return True
        return False
    
    def find_peaks(self, df: pd.DataFrame, rsi: pd.Series, min_prominence: float = 0.008):
        """
        Find swing highs for triple pattern - 3 of 4 requirements (resistance OPTIONAL for triple)
        
        Requirements for a valid peak:
        1. Highest in 5-hour window (20 bars @ 15min) - ALWAYS REQUIRED
        2. At least 0.8% above recent average (prominence)
        3. Volume spike (1.15x average - very relaxed for triple)
        4. Proper spacing from other peaks (6+ bars)
        
        Need 3 of 4 (REQ 1 always required, plus 2 of the other 3)
        """
        peaks = []
        lookback = 20  # 5 hours @ 15min bars
        MIN_PEAK_SPACING = 6  # Minimum spacing
        
        for i in range(lookback, len(df) - lookback):
            high = df['high'].iloc[i]
            
            # REQ 1: Must be highest in 5-hour window (ALWAYS REQUIRED)
            if high != df['high'].iloc[i-lookback:i+lookback+1].max():
                continue
            
            requirements_met = 1  # Already met REQ 1
            
            # REQ 2: 0.8% above recent average (prominence)
            recent_avg = df['high'].iloc[i-lookback:i].mean()
            has_prominence = False
            if recent_avg > 0 and high >= recent_avg * (1 + min_prominence):
                requirements_met += 1
                has_prominence = True
            
            # REQ 3: Volume spike (1.15x average - very relaxed)
            vol = df['volume'].iloc[i]
            avg_vol = df['volume'].iloc[max(0, i-lookback):i].mean()
            if avg_vol > 0 and vol >= avg_vol * 1.15:
                requirements_met += 1
            
            # REQ 4: Proper spacing from previous peaks
            spacing_ok = True
            if len(peaks) > 0:
                last_peak_idx = peaks[-1]['idx']
                if i - last_peak_idx >= MIN_PEAK_SPACING:
                    requirements_met += 1
                else:
                    spacing_ok = False
            else:
                requirements_met += 1  # First peak, spacing N/A
            
            # Need at least 3 of 4 requirements AND proper spacing
            if requirements_met < 3 or not spacing_ok:
                continue
            
            # Requirements passed - add peak
            rsi_val = rsi.iloc[i] if i < len(rsi) else 50
            
            peaks.append({
                'idx': i,
                'price': high,
                'volume': vol,
                'rsi': rsi_val,
                'prominence': ((high / recent_avg) - 1) * 100 if has_prominence else 0,
                'requirements_met': requirements_met
            })
        
        return peaks
    
    def reset_pattern_state(self):
        """Reset pattern tracking state - PHASE 1: NEW"""
        self.pattern_start_idx = None
        self.breakdown_start_idx = None
        self.active_pattern = None
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """INSTITUTIONAL GRADE: Triple top with multi-block validation + PHASE 1 improvements"""
        if len(df) < 40:  # Need more data for quality validation
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_idx = len(df) - 1
        
        # PHASE 1: Check pattern expiration
        if self.pattern_start_idx is not None:
            bars_since_pattern_start = current_idx - self.pattern_start_idx
            if bars_since_pattern_start > self.PATTERN_MAX_DURATION:
                # Pattern expired without breakdown
                self.reset_pattern_state()
                return {
                    'signal': 'NO_PATTERN',
                    'confidence': 0,
                    'metadata': {'reason': 'Pattern expired (>150 bars)'},
                    'timestamp': df['timestamp'].iloc[-1],
                    'timeframe': self.timeframe,
                    'confluence_factors': []
                }
        
        # Calculate validation indicators
        rsi = self.calculate_rsi(df)
        vwap = self.calculate_vwap(df)
        current_price = float(df['close'].iloc[-1])
        
        peaks = self.find_peaks(df, rsi)
        
        if len(peaks) < 3:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Last 3 peaks
        recent = peaks[-3:]
        p1, p2, p3 = recent[0], recent[1], recent[2]
        
        # CRITICAL: Check pattern duration between peaks
        bars_1_2 = p2['idx'] - p1['idx']
        bars_2_3 = p3['idx'] - p2['idx']
        
        if bars_1_2 < self.MIN_BARS_BETWEEN_PEAKS or bars_2_3 < self.MIN_BARS_BETWEEN_PEAKS:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {
                    'reason': 'Pattern forming too quickly',
                    'bars_1_2': bars_1_2,
                    'bars_2_3': bars_2_3,
                    'min_required': self.MIN_BARS_BETWEEN_PEAKS
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if bars_1_2 > self.MAX_BARS_BETWEEN_PEAKS or bars_2_3 > self.MAX_BARS_BETWEEN_PEAKS:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {
                    'reason': 'Peaks too far apart',
                    'bars_1_2': bars_1_2,
                    'bars_2_3': bars_2_3,
                    'max_allowed': self.MAX_BARS_BETWEEN_PEAKS
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check: Similar price (REQUIRED - tightened to 2%)
        avg_price = (p1['price'] + p2['price'] + p3['price']) / 3
        price_diffs = [
            abs(p1['price'] - avg_price) / avg_price,
            abs(p2['price'] - avg_price) / avg_price,
            abs(p3['price'] - avg_price) / avg_price
        ]
        
        if any(diff > self.peak_tolerance for diff in price_diffs):
            max_diff = max(price_diffs)
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {
                    'reason': 'Peaks not similar enough',
                    'max_peak_diff_pct': round(max_diff * 100, 2),
                    'max_allowed': round(self.peak_tolerance * 100, 2)
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # INSTITUTIONAL VALIDATION: Build confidence score
        base_confidence = 50  # Start at 50%
        confluences = []
        
        # CONFLUENCE 1: RSI Overbought at ALL 3 peaks (+20 points)
        p1_overbought = p1['rsi'] > 70
        p2_overbought = p2['rsi'] > 70
        p3_overbought = p3['rsi'] > 70
        
        if p1_overbought and p2_overbought and p3_overbought:
            base_confidence += 20
            confluences.append(f"RSI overbought all 3 peaks ({p1['rsi']:.1f}, {p2['rsi']:.1f}, {p3['rsi']:.1f})")
        elif (p1_overbought and p2_overbought) or (p2_overbought and p3_overbought):
            base_confidence += 12
            confluences.append(f"RSI overbought 2 peaks")
        elif p1_overbought or p2_overbought or p3_overbought:
            base_confidence += 6
            confluences.append(f"RSI overbought 1 peak")
        
        # CONFLUENCE 2: VWAP Premium Zone (+15 points)
        in_premium = avg_price > vwap * 1.02  # 2% above VWAP
        if in_premium:
            base_confidence += 15
            premium_pct = ((avg_price / vwap) - 1) * 100
            confluences.append(f"Premium zone (+{premium_pct:.1f}% above VWAP)")
        
        # CONFLUENCE 3: Volume Analysis (+10 points)
        vol_decreasing = p3['volume'] < p2['volume'] * 0.9
        vol_low = p3['volume'] < df['volume'].iloc[-50:].mean() * 0.7
        
        if vol_decreasing and vol_low:
            base_confidence += 10
            vol_ratio = ((p2['volume'] / p3['volume']) - 1) * 100
            confluences.append(f"Weak volume (-{vol_ratio:.1f}% on peak 3)")
        elif vol_decreasing:
            base_confidence += 5
            confluences.append("Decreasing volume")
        
        # CONFLUENCE 4: Resistance Level (+10 points)
        at_resistance = self.detect_resistance_level(df, avg_price)
        if at_resistance:
            base_confidence += 10
            confluences.append("At key resistance level")
        
        # CONFLUENCE 5: Pattern Quality (+10 points)
        # Peaks very similar in price
        max_diff = max(price_diffs)
        if max_diff < 0.02:  # Within 2%
            base_confidence += 5
            confluences.append(f"Peaks very similar ({max_diff*100:.1f}%)")
        
        # Sufficient time between peaks (7+ bars each)
        bars_1_2 = p2['idx'] - p1['idx']
        bars_2_3 = p3['idx'] - p2['idx']
        if bars_1_2 >= 7 and bars_2_3 >= 7:
            base_confidence += 5
            confluences.append(f"Good pattern duration ({bars_1_2}+{bars_2_3} bars)")
        
        # MINIMUM THRESHOLD: Require at least 3 confluences (PHASE 1: increased from 2)
        if len(confluences) < self.MIN_CONFLUENCES:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {
                    'reason': 'Insufficient validation',
                    'confluences_found': len(confluences),
                    'confluences_required': self.MIN_CONFLUENCES
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Find neckline
        section = df.iloc[p1['idx']:p3['idx']+1]
        neckline = section['low'].min()
        
        # PHASE 1: Stricter breakdown detection
        # Require: 0.5% break below neckline AND 2 of last 3 closes below
        neckline_with_margin = neckline * (1 - self.BREAK_MARGIN)
        clean_break = current_price < neckline_with_margin
        
        # Count recent closes below neckline
        recent_closes = df['close'].iloc[-3:]
        closes_below = (recent_closes < neckline).sum()
        confirmed_closes = closes_below >= 2
        
        # Both conditions required for breakdown
        breakdown = clean_break and confirmed_closes
        
        # PHASE 1: Track breakdown duration
        if breakdown:
            if self.breakdown_start_idx is None:
                # New breakdown starting
                self.breakdown_start_idx = current_idx
                base_confidence += 10
                signal = 'BEARISH_BREAKDOWN'
            else:
                # Breakdown continuing
                bars_since_breakdown = current_idx - self.breakdown_start_idx
                if bars_since_breakdown > self.BREAKDOWN_MAX_DURATION:
                    # Breakdown complete - reset
                    self.reset_pattern_state()
                    return {
                        'signal': 'NO_PATTERN',
                        'confidence': 0,
                        'metadata': {'reason': 'Breakdown completed (>20 bars)'},
                        'timestamp': df['timestamp'].iloc[-1],
                        'timeframe': self.timeframe,
                        'confluence_factors': []
                    }
                else:
                    base_confidence += 10
                    signal = 'BEARISH_BREAKDOWN'
        else:
            # Not broken down
            if self.breakdown_start_idx is not None:
                # Was in breakdown but price recovered - pattern invalidated
                self.reset_pattern_state()
                return {
                    'signal': 'NO_PATTERN',
                    'confidence': 0,
                    'metadata': {'reason': 'Price recovered above neckline'},
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
        pattern_id = f"TT_{p1['idx']}_{p2['idx']}_{p3['idx']}"
        is_new_event = False
        
        if breakdown:
            # New breakdown event if pattern ID changed
            is_new_event = (self.active_pattern != pattern_id)
            self.active_pattern = pattern_id
        
        target = neckline - (avg_price - neckline)
        
        return {
            'signal': signal,
            'confidence': final_confidence,
            'metadata': {
                'pattern_type': 'TRIPLE_TOP_INSTITUTIONAL',
                'peaks': [round(p1['price'], 2), round(p2['price'], 2), round(p3['price'], 2)],
                'peak_rsi': [round(p1['rsi'], 1), round(p2['rsi'], 1), round(p3['rsi'], 1)],
                'neckline': round(neckline, 2),
                'vwap': round(vwap, 2),
                'in_premium_zone': in_premium,
                'volume_ratio': round(p2['volume'] / p3['volume'], 2),
                'at_resistance': at_resistance,
                'breakdown_confirmed': breakdown,
                'target_price': round(target, 2),
                'confluences_count': len(confluences),
                'quality_factors': confluences,
                'bars_between_peaks': f"{bars_1_2}+{bars_2_3}",
                'pattern_id': pattern_id,
                'is_new_event': is_new_event
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Triple Top: {len(confluences)} confluences (Institutional grade)',
                f'Confidence: {final_confidence}%',
                f'Pattern duration: {bars_1_2}+{bars_2_3} bars',
                *confluences[:3],  # Show top 3 confluences
                f'{'✅ Breakdown confirmed!' if breakdown else '⏳ Pattern forming'}'
            ]
        }
