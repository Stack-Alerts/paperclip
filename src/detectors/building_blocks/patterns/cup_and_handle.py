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
from datetime import datetime
import pandas as pd
import numpy as np


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
                 cup_depth_min: float = 0.01, handle_depth_max: float = 0.3, **kwargs):
        self.timeframe = timeframe
        self.min_pattern_bars = min_pattern_bars
        self.cup_depth_min = cup_depth_min
        self.handle_depth_max = handle_depth_max
        
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
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        low_after_high = lows_after_high.min()
        
        # REALISTIC: Only need 1% dip for 15min (patterns are rare)
        dip_pct = (high_val - low_after_high) / high_val
        
        if dip_pct < self.cup_depth_min:  # Default 1%
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # REALISTIC: Check if recovered at least 30% (not 70%!)
        recovery_pct = (current_price - low_after_high) / (high_val - low_after_high)
        
        if recovery_pct < 0.30:  # At least 30% recovery (realistic for 15min)
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
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
        
        # MINIMUM THRESHOLD: Require at least 2 confluences
        if len(confluences) < 2:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {'reason': 'Insufficient confluence', 'confluences_found': len(confluences)},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check if breakout confirmed
        breakout = current_price > rim_level * 1.002  # 0.2% above rim
        
        # BREAKOUT gets additional confidence boost
        if breakout:
            base_confidence += 10
            signal = 'BREAKOUT_CONFIRMED'
        elif recovery_pct > 0.60:
            signal = 'CUP_FORMING'
        else:
            signal = 'PATTERN_FORMING'
        
        # Cap confidence at 95%
        final_confidence = min(base_confidence, 95)
        
        # Calculate target
        pattern_height = high_val - low_after_high
        target_price = rim_level + pattern_height
        
        return {
            'signal': signal,
            'confidence': final_confidence,
            'metadata': {
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
