"""
Triple Bottom Pattern - INSTITUTIONAL GRADE with Multi-Block Validation
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



from typing import Dict, Any, List

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='triple_bottom',
    category='PATTERNS',
    class_name='TripleBottomPattern',
    default_weight=30,
    valid_signals=['BULLISH_BREAKOUT', 'NO_PATTERN', 'PATTERN_FORMING', 'ERROR', 'INSUFFICIENT_DATA'],
    signal_tiers={
        'BULLISH_BREAKOUT': {
                'base_points': 30,
                'formula': 'scaled'
        },
        'NO_PATTERN': {
                'points': 0
        },
        'PATTERN_FORMING': {
                'base_points': 30,
                'formula': 'scaled'
        },
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        }
}
)
class TripleBottomPattern:
    """
    Triple Bottom: 3 similar troughs with multi-block validation
    
    INSTITUTIONAL VALIDATION (Target: 70%+ confidence):
    - Requires EXACTLY 3 troughs (not 2)
    - RSI oversold (<30) at ALL 3 troughs (confluence)
    - VWAP discount zone (price < VWAP) (confluence)
    - Volume analysis (decreasing or accumulation) (confluence)
    - Support level confirmation (confluence)
    - Quality scoring based on confluences
    """
    
    def __init__(self, timeframe: str = '15min', min_pattern_bars: int = 15,
                 trough_tolerance: float = 0.025, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.trough_tolerance = trough_tolerance  # 2.5% max difference (same as triple_top)
        
        # Pattern lifecycle tracking (PHASE 1 improvements)
        self.active_pattern = None  # Track current pattern ID for event detection
        self.pattern_start_idx = None  # When pattern started forming
        self.breakout_start_idx = None  # When breakout began
        
        # Pattern duration requirements for 15min timeframe
        self.MIN_BARS_BETWEEN_TROUGHS = 12   # 3 hours minimum (same as triple_top)
        self.MAX_BARS_BETWEEN_TROUGHS = 100  # 25 hours maximum
        self.PATTERN_MAX_DURATION = 150      # Pattern expires after 150 bars
        self.BREAKOUT_MAX_DURATION = 20      # Breakout confirmed for 20 bars
        
        # Validation requirements (STRICTER for better selectivity)
        self.MIN_CONFLUENCES = 4  # Increased from 2 for institutional grade
        self.MIN_TROUGH_SPACING = 7  # 7 bars minimum between troughs
        
        # Breakout requirements (stricter)
        self.BREAK_MARGIN = 0.005  # Must break 0.5% above neckline
        
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
    
    def find_troughs(self, df: pd.DataFrame, rsi: pd.Series, min_prominence: float = 0.008):
        """
        Find swing lows for triple pattern - 3 of 4 requirements
        
        Requirements for a valid trough:
        1. Lowest in 5-hour window (20 bars @ 15min) - ALWAYS REQUIRED
        2. At least 0.8% below recent average (prominence)
        3. Volume spike (1.15x average - relaxed for triple)
        4. Proper spacing from other troughs (6+ bars)
        
        Need 3 of 4 (REQ 1 always required, plus 2 of the other 3)
        """
        troughs = []
        lookback = 20  # 5 hours @ 15min bars
        MIN_TROUGH_SPACING = 6  # Minimum spacing
        
        for i in range(lookback, len(df) - lookback):
            low = df['low'].iloc[i]
            
            # REQ 1: Must be lowest in 5-hour window (ALWAYS REQUIRED)
            if low != df['low'].iloc[i-lookback:i+lookback+1].min():
                continue
            
            requirements_met = 1  # Already met REQ 1
            
            # REQ 2: 0.8% below recent average (prominence)
            recent_avg = df['low'].iloc[i-lookback:i].mean()
            has_prominence = False
            if recent_avg > 0 and low <= recent_avg * (1 - min_prominence):
                requirements_met += 1
                has_prominence = True
            
            # REQ 3: Volume spike (1.15x average - relaxed)
            vol = df['volume'].iloc[i]
            avg_vol = df['volume'].iloc[max(0, i-lookback):i].mean()
            if avg_vol > 0 and vol >= avg_vol * 1.15:
                requirements_met += 1
            
            # REQ 4: Proper spacing from previous troughs
            spacing_ok = True
            if len(troughs) > 0:
                last_trough_idx = troughs[-1]['idx']
                if i - last_trough_idx >= MIN_TROUGH_SPACING:
                    requirements_met += 1
                else:
                    spacing_ok = False
            else:
                requirements_met += 1  # First trough, spacing N/A
            
            # Need at least 3 of 4 requirements AND proper spacing
            if requirements_met < 3 or not spacing_ok:
                continue
            
            # Requirements passed - add trough
            rsi_val = rsi.iloc[i] if i < len(rsi) else 50
            
            troughs.append({
                'idx': i,
                'price': low,
                'volume': vol,
                'rsi': rsi_val,
                'prominence': ((recent_avg / low) - 1) * 100 if has_prominence else 0,
                'requirements_met': requirements_met
            })
        
        return troughs
    
    def reset_pattern_state(self):
        """Reset pattern tracking state - PHASE 1: NEW"""
        self.pattern_start_idx = None
        self.breakout_start_idx = None
        self.active_pattern = None
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """INSTITUTIONAL GRADE: Triple bottom with multi-block validation + PHASE 1 improvements"""
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
                # Pattern expired without breakout
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
        
        troughs = self.find_troughs(df, rsi)
        
        if len(troughs) < 3:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Last 3 troughs
        recent = troughs[-3:]
        t1, t2, t3 = recent[0], recent[1], recent[2]
        
        # CRITICAL: Check pattern duration between troughs
        bars_1_2 = t2['idx'] - t1['idx']
        bars_2_3 = t3['idx'] - t2['idx']
        
        if bars_1_2 < self.MIN_BARS_BETWEEN_TROUGHS or bars_2_3 < self.MIN_BARS_BETWEEN_TROUGHS:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {
                    'reason': 'Pattern forming too quickly',
                    'bars_1_2': bars_1_2,
                    'bars_2_3': bars_2_3,
                    'min_required': self.MIN_BARS_BETWEEN_TROUGHS
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if bars_1_2 > self.MAX_BARS_BETWEEN_TROUGHS or bars_2_3 > self.MAX_BARS_BETWEEN_TROUGHS:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {
                    'reason': 'Troughs too far apart',
                    'bars_1_2': bars_1_2,
                    'bars_2_3': bars_2_3,
                    'max_allowed': self.MAX_BARS_BETWEEN_TROUGHS
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check: Similar price (REQUIRED)
        avg_price = (t1['price'] + t2['price'] + t3['price']) / 3
        price_diffs = [
            abs(t1['price'] - avg_price) / avg_price,
            abs(t2['price'] - avg_price) / avg_price,
            abs(t3['price'] - avg_price) / avg_price
        ]
        
        if any(diff > self.trough_tolerance for diff in price_diffs):
            max_diff = max(price_diffs)
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {
                    'reason': 'Troughs not similar enough',
                    'max_trough_diff_pct': round(max_diff * 100, 2),
                    'max_allowed': round(self.trough_tolerance * 100, 2)
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # INSTITUTIONAL VALIDATION: Build confidence score
        base_confidence = 50  # Start at 50%
        confluences = []
        
        # CONFLUENCE 1: RSI Oversold at ALL 3 troughs (+20 points)
        t1_oversold = t1['rsi'] < 30
        t2_oversold = t2['rsi'] < 30
        t3_oversold = t3['rsi'] < 30
        
        if t1_oversold and t2_oversold and t3_oversold:
            base_confidence += 20
            confluences.append(f"RSI oversold all 3 troughs ({t1['rsi']:.1f}, {t2['rsi']:.1f}, {t3['rsi']:.1f})")
        elif (t1_oversold and t2_oversold) or (t2_oversold and t3_oversold):
            base_confidence += 12
            confluences.append(f"RSI oversold 2 troughs")
        elif t1_oversold or t2_oversold or t3_oversold:
            base_confidence += 6
            confluences.append(f"RSI oversold 1 trough")
        
        # CONFLUENCE 2: VWAP Discount Zone (+15 points)
        in_discount = avg_price < vwap * 0.98  # 2% below  VWAP
        if in_discount:
            base_confidence += 15
            discount_pct = ((vwap / avg_price) - 1) * 100
            confluences.append(f"Discount zone (-{discount_pct:.1f}% below VWAP)")
        
        # CONFLUENCE 3: Volume Analysis (+10 points)
        vol_decreasing = t3['volume'] < t2['volume'] * 0.9
        vol_low = t3['volume'] < df['volume'].iloc[-50:].mean() * 0.7
        
        if vol_decreasing and vol_low:
            base_confidence += 10
            vol_ratio = ((t2['volume'] / t3['volume']) - 1) * 100
            confluences.append(f"Weak volume (-{vol_ratio:.1f}% on trough 3)")
        elif vol_decreasing:
            base_confidence += 5
            confluences.append("Decreasing volume")
        
        # CONFLUENCE 4: Support Level (+10 points)
        at_support = self.detect_support_level(df, avg_price)
        if at_support:
            base_confidence += 10
            confluences.append("At key support level")
        
        # CONFLUENCE 5: Pattern Quality (+10 points)
        # Troughs very similar in price
        max_diff = max(price_diffs)
        if max_diff < 0.02:  # Within 2%
            base_confidence += 5
            confluences.append(f"Troughs very similar ({max_diff*100:.1f}%)")
        
        # Sufficient time between troughs (7+ bars each)
        bars_1_2 = t2['idx'] - t1['idx']
        bars_2_3 = t3['idx'] - t2['idx']
        if bars_1_2 >= 7 and bars_2_3 >= 7:
            base_confidence += 5
            confluences.append(f"Good pattern duration ({bars_1_2}+{bars_2_3} bars)")
        
        # MINIMUM THRESHOLD: Require at least 4 confluences (PHASE 1: increased from 2)
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
        section = df.iloc[t1['idx']:t3['idx']+1]
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
                    return {
                        'signal': 'NO_PATTERN',
                        'confidence': 0,
                        'metadata': {'reason': 'Breakout completed (>20 bars)'},
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
                # Was in breakout but price fell back - pattern invalidated
                self.reset_pattern_state()
                return {
                    'signal': 'NO_PATTERN',
                    'confidence': 0,
                    'metadata': {'reason': 'Price fell back below neckline'},
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
        pattern_id = f"TB_{t1['idx']}_{t2['idx']}_{t3['idx']}"
        is_new_event = False
        
        if breakout:
            # New breakout event if pattern ID changed
            is_new_event = (self.active_pattern != pattern_id)
            self.active_pattern = pattern_id
        
        target = neckline + (neckline - avg_price)
        
        return {
            'signal': signal,
            'confidence': final_confidence,
            'metadata': {
                'pattern_type': 'TRIPLE_BOTTOM_INSTITUTIONAL',
                'troughs': [round(t1['price'], 2), round(t2['price'], 2), round(t3['price'], 2)],
                'trough_rsi': [round(t1['rsi'], 1), round(t2['rsi'], 1), round(t3['rsi'], 1)],
                'neckline': round(neckline, 2),
                'vwap': round(vwap, 2),
                'in_discount_zone': in_discount,
                'volume_ratio': round(t2['volume'] / t3['volume'], 2),
                'at_support': at_support,
                'breakout_confirmed': breakout,
                'target_price': round(target, 2),
                'confluences_count': len(confluences),
                'quality_factors': confluences,
                'bars_between_troughs': f"{bars_1_2}+{bars_2_3}",
                'pattern_id': pattern_id,
                'is_new_event': is_new_event
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Triple Bottom: {len(confluences)} confluences (Institutional grade)',
                f'Confidence: {final_confidence}%',
                f'Pattern duration: {bars_1_2}+{bars_2_3} bars',
                *confluences[:3],  # Show top 3 confluences
                f'{'✅ Breakout confirmed!' if breakout else '⏳ Pattern forming'}'
            ]
        }
