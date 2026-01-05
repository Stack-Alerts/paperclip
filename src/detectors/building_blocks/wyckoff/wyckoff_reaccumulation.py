"""
Wyckoff Re-accumulation Phase Detector
Category: Wyckoff Method
Purpose: Identifies continuation consolidation within uptrends (smart money adding positions)

╔════════════════════════════════════════════════════════════════════════════╗
║ ⚠️ CRITICAL: MULTI-TIMEFRAME TESTING REQUIRED                             ║
╚════════════════════════════════════════════════════════════════════════════╝

🚨 BLOCK NOT YET VALIDATED ON CORRECT TIMEFRAMES

15MIN RESULTS (Current testing):
   ❌ 49.8% REACCUMULATION vs 50.2% NO_REACCUMULATION (50/50 split - BROKEN)
   ❌ 95.45 signals/day (too noisy - micro-consolidations)
   ❌ DO NOT USE - Detecting micro-ranges, not true reaccumulation

HYPOTHESIS (Based on Accumulation/Distribution siblings):
⭐ PRIMARY TIMEFRAME: 2HR (needs testing)
   - Expected: 25-35% REACCUMULATION_DETECTED
   - Expected: 65-75% NO_REACCUMULATION
   - Expected: 3-6 signals/day

⭐ CONFIRMATION TIMEFRAME: 4HR (needs testing)
   - Expected: 10-20% REACCUMULATION_DETECTED
   - Expected: 80-90% NO_REACCUMULATION
   - Expected: 1-3 signals/day

╔════════════════════════════════════════════════════════════════════════════╗
║ HYBRID BLOCK - CONTINUOUS STATE + SELECTIVE EVENTS                        ║
╚════════════════════════════════════════════════════════════════════════════╝

PROVIDES TWO VALUE TYPES (after proper testing):
  1. Continuous Context: NO_REACCUMULATION state
     → Know if in uptrend consolidation
     → Adjust position sizing
     → +20 confluence points for trending
  
  2. Selective Events:
     → REACCUMULATION_DETECTED: Consolidation in uptrend
     → SPRING: False breakdown (major signal)
     → BREAKOUT: Continuation confirmed

CURRENT STATUS: ⚠️ BLOCKED - Test 2HR/4HR before deployment
Grade: C+ (75/100) - Incomplete testing

PREDICTED Grade (after MTF testing): A- (88-92/100)
Predicted Value: $45K-$75K (if matches siblings on correct timeframes)
"""
"""
Building Block Classification: HYBRID BLOCK
Mode: CONTINUOUS + EVENT
Purpose: Continuous reaccumulation state (NO_REACCUMULATION) + selective events (REACCUMULATION/SPRING/BREAKOUT)

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events

HYBRID DESIGN:
- Continuous: Always provides NO_REACCUMULATION or REACCUMULATION state
- Events: Fires on SPRING and BREAKOUT (rare continuation signals)

⚠️ WARNING: Only tested on 15MIN (50/50 split - broken)
🚨 REQUIRED: Test on 2HR/4HR before production deployment
"""



from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class WyckoffReaccumulation:
    """
    Detects Wyckoff re-accumulation phases using proper methodology
    Adapted from Accumulation but for mid-trend continuation
    
    Characteristics:
    - Occurs within established uptrend
    - Consolidation range forms at elevated prices
    - Spring (optional): False breakdown before continuation
    - Breakout: Continuation above range on strong volume
    - Shorter duration than base accumulation
    """
    
    def __init__(self, timeframe: str = '15min',
                 range_lookback: int = 50,           # Lookback for range detection
                 volume_lookback: int = 50,
                 range_threshold_pct: float = 5.0,   # Tight range for consolidation
                 spring_breakdown_pct: float = 2.0,  # False breakdown threshold
                 spring_volume_ratio: float = 0.85,  # Lower volume on spring (weak)
                 breakout_volume_ratio: float = 1.15, # Higher volume on breakout
                 uptrend_lookback: int = 30,         # Bars to confirm uptrend
                 **kwargs):
        self.timeframe = timeframe
        self.range_lookback = range_lookback
        self.volume_lookback = volume_lookback
        self.range_threshold_pct = range_threshold_pct
        self.spring_breakdown_pct = spring_breakdown_pct
        self.spring_volume_ratio = spring_volume_ratio
        self.breakout_volume_ratio = breakout_volume_ratio
        self.uptrend_lookback = uptrend_lookback
    
    def detect_uptrend(self, df: pd.DataFrame) -> tuple:
        """
        Detect if price is in established uptrend
        Required context for re-accumulation
        """
        if len(df) < self.uptrend_lookback:
            return False, 0
        
        # Check price above longer-term moving average
        ma_uptrend = df['close'].iloc[-1] > df['close'].iloc[-self.uptrend_lookback:].mean()
        
        # Check recent higher lows (uptrend structure)
        recent_lows = df['low'].iloc[-self.uptrend_lookback:]
        earlier_low = recent_lows.iloc[:len(recent_lows)//2].min()
        later_low = recent_lows.iloc[len(recent_lows)//2:].min()
        higher_lows = later_low > earlier_low * 0.98  # Allow small variation
        
        # Check positive momentum
        price_change = (df['close'].iloc[-1] / df['close'].iloc[-self.uptrend_lookback] - 1) * 100
        positive_momentum = price_change > 0
        
        if ma_uptrend and (higher_lows or positive_momentum):
            confidence = 70 if (higher_lows and positive_momentum) else 60
            return True, confidence
        
        return False, 0
    
    def detect_range(self, df: pd.DataFrame) -> tuple:
        """
        Detect consolidation range within uptrend
        Similar to Accumulation but at elevated prices
        """
        if len(df) < self.range_lookback:
            return False, 0, 0, 0
        
        # Calculate range
        range_high = df['high'].iloc[-self.range_lookback:].max()
        range_low = df['low'].iloc[-self.range_lookback:].min()
        range_size = range_high - range_low
        current_price = df['close'].iloc[-1]
        
        # Range as percentage of price
        range_pct = (range_size / current_price) * 100
        
        # In consolidation if range < threshold
        in_range = range_pct < self.range_threshold_pct
        
        # Check volume declining (quiet consolidation)
        if len(df) >= self.range_lookback + 20:
            volume_recent = df['volume'].iloc[-20:].mean()
            volume_earlier = df['volume'].iloc[-self.range_lookback:-20].mean()
            volume_declining = volume_recent < volume_earlier * 0.9
        else:
            volume_declining = False
        
        if in_range:
            # Higher confidence if volume declining
            confidence = 65 if volume_declining else 55
            return True, confidence, range_high, range_low
        
        return False, 0, 0, 0
    
    def detect_spring(self, df: pd.DataFrame, support_level: float) -> tuple:
        """
        Detect spring pattern (false breakdown below support)
        Critical signal for re-accumulation continuation
        
        Spring characteristics:
        - Brief move below support
        - Lower volume (weak move - trap)
        - Quick reversal back into range
        """
        if len(df) < 10 or support_level == 0:
            return False, 0
        
        # Check for breakdown below support in last 10 bars
        recent_lows = df['low'].iloc[-10:]
        breakdown_threshold = 1.0 - (self.spring_breakdown_pct / 100.0)
        broke_support = recent_lows.min() < support_level * breakdown_threshold
        
        if not broke_support:
            return False, 0
        
        # Volume should be LOWER on breakdown (weak move - trap!)
        if len(df) >= 60:
            volume_avg = df['volume'].iloc[-60:-10].mean()
            breakdown_volume = df['volume'].iloc[-10:].mean()
            low_volume_breakdown = breakdown_volume < volume_avg * self.spring_volume_ratio
        else:
            low_volume_breakdown = False
        
        # Quick reversal back above support
        current_price = df['close'].iloc[-1]
        reversed = current_price > support_level * 1.002  # Back above support
        
        if broke_support and low_volume_breakdown and reversed:
            # SPRING DETECTED - Major continuation signal!
            return True, 85
        elif broke_support and reversed:
            # Reversed but volume not ideal
            return True, 70
        
        return False, 0
    
    def detect_breakout(self, df: pd.DataFrame, resistance_level: float) -> tuple:
        """
        Detect breakout above range (continuation confirmed)
        
        Breakout characteristics:
        - Break above resistance
        - Strong volume (institutional buying)
        - Sustained move
        """
        if len(df) < 10 or resistance_level == 0:
            return False, 0
        
        # Check for breakout above resistance
        recent_highs = df['high'].iloc[-10:]
        broke_resistance = recent_highs.max() > resistance_level * 1.01
        
        if not broke_resistance:
            return False, 0
        
        # Volume should be HIGHER on breakout (strong move)
        if len(df) >= 60:
            volume_avg = df['volume'].iloc[-60:-10].mean()
            breakout_volume = df['volume'].iloc[-10:].mean()
            high_volume_breakout = breakout_volume > volume_avg * self.breakout_volume_ratio
        else:
            high_volume_breakout = False
        
        # Sustained move (close above resistance)
        current_price = df['close'].iloc[-1]
        sustained = current_price > resistance_level * 1.005
        
        if broke_resistance and high_volume_breakout and sustained:
            # BREAKOUT CONFIRMED - Strong continuation!
            return True, 80
        elif broke_resistance and sustained:
            # Breakout but volume not ideal
            return True, 65
        
        return False, 0
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method - Comprehensive Wyckoff re-accumulation detection
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
        
        if len(df) < self.range_lookback:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect uptrend context (required!)
        in_uptrend, uptrend_conf = self.detect_uptrend(df)
        
        if not in_uptrend:
            # Not in uptrend - no re-accumulation possible
            return {
                'signal': 'NO_REACCUMULATION',
                'confidence': 45,
                'metadata': {
                    'phase': 'NONE',
                    'reason': 'Not in uptrend'
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['❌ No uptrend detected', 'Re-accumulation requires uptrend context']
            }
        
        # Detect consolidation range
        in_range, range_conf, resistance, support = self.detect_range(df)
        
        if not in_range:
            # Trending, not consolidating - not re-accumulation
            return {
                'signal': 'NO_REACCUMULATION',
                'confidence': 50,
                'metadata': {
                    'phase': 'TRENDING',
                    'reason': 'Uptrend but not consolidating'
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['✅ Uptrend confirmed', '📈 Trending - not in range']
            }
        
        # Detect spring and breakout
        spring, spring_conf = self.detect_spring(df, support)
        breakout, breakout_conf = self.detect_breakout(df, resistance)
        
        # Determine signal and phase
        confluence_factors = []
        
        if breakout:
            # BREAKOUT DETECTED - Continuation confirmed!
            signal = 'BREAKOUT_CONTINUATION'
            confidence = breakout_conf
            phase = 'BREAKOUT'
            confluence_factors.append('⭐ Breakout: Continuation above range confirmed')
            confluence_factors.append('✅ Strong volume - institutional buying')
            
        elif spring:
            # SPRING DETECTED - Major signal for continuation!
            signal = 'SPRING_DETECTED'
            confidence = spring_conf
            phase = 'SPRING'
            confluence_factors.append('⭐ Spring: False breakdown - trap set!')
            confluence_factors.append('✅ Quick reversal - continuation likely')
            
        elif in_range:
            # RANGE CONSOLIDATION - Re-accumulation in progress
            signal = 'REACCUMULATION_DETECTED'
            confidence = min(uptrend_conf, range_conf) + 10  # Bonus for both conditions
            phase = 'RANGE'
            range_pct = ((resistance - support) / df['close'].iloc[-1]) * 100
            confluence_factors.append(f'📦 Consolidation range: {range_pct:.1f}% of price')
            confluence_factors.append('✅ Uptrend pause - potential re-accumulation')
            confluence_factors.append('🔇 Volume declining - quiet accumulation')
        
        else:
            # Should not reach here, but safety net
            signal = 'NO_REACCUMULATION'
            confidence = 45
            phase = 'NONE'
            confluence_factors.append('❌ Conditions not met')
        
        # Build metadata
        metadata = {
            'phase': phase,
            'spring_detected': spring,
            'breakout_detected': breakout,
            'in_uptrend': in_uptrend,
            'in_range': in_range,
            'resistance_level': float(resistance) if resistance > 0 else 0,
            'support_level': float(support) if support > 0 else 0
        }
        
        return {
            'signal': signal,
            'confidence': int(confidence),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


def analyze_multi_timeframe(df_1hr: pd.DataFrame, df_2hr: pd.DataFrame) -> Dict[str, Any]:
    """
    Production helper for multi-timeframe Wyckoff re-accumulation analysis
    
    This is the RECOMMENDED way to use Wyckoff Reaccumulation in production.
    Note: Testing needed to determine optimal timeframes (may differ from Accumulation!)
    
    Args:
        df_1hr: 1-hour OHLCV dataframe (PRIMARY timeframe - hypothesis)
        df_2hr: 2-hour OHLCV dataframe (CONFIRMATION timeframe - hypothesis)
    
    Returns:
        dict with:
            - confluence: Total confluence points (15-120)
            - notes: List of analysis notes
            - 1hr_result: Full 1HR analysis result
            - 2hr_result: Full 2HR analysis result
            - mtf_aligned: Boolean if both timeframes agree
    
    Usage Example:
        result = analyze_multi_timeframe(df_1hr, df_2hr)
        total_confluence += result['confluence']
        notes.extend(result['notes'])
        
        if result['mtf_aligned']:
            print("🎯 Multi-timeframe re-accumulation alignment detected!")
    
    Note: Timeframes are hypothetical - test 30min, 1HR, 2HR to discover optimal!
    """
    confluence = 0
    notes = []
    
    # === ANALYZE 1HR (PRIMARY - hypothesis) ===
    wyckoff_1hr = WyckoffReaccumulation(timeframe='1hr')
    result_1hr = wyckoff_1hr.analyze(df_1hr)
    
    # Add 1HR confluence
    if result_1hr['metadata']['phase'] == 'SPRING':
        # Spring detected (major signal!)
        confluence += 60
        notes.append('⭐ Wyckoff 1HR: SPRING - Major Continuation Signal!')
        
    elif result_1hr['metadata']['phase'] == 'BREAKOUT':
        # Breakout continuation
        confluence += 55
        notes.append('⭐ Wyckoff 1HR: BREAKOUT - Continuation Confirmed!')
        
    elif result_1hr['metadata']['phase'] == 'RANGE':
        # Range consolidation
        confluence += 45
        notes.append('⭐ Wyckoff 1HR: Range - Re-accumulation in Progress')
        
    elif result_1hr['metadata']['phase'] == 'TRENDING':
        # Trending (no consolidation)
        confluence += 20
        notes.append('📈 Wyckoff 1HR: Trending - No Consolidation')
        
    elif result_1hr['signal'] == 'NO_REACCUMULATION':
        # Not in uptrend or not consolidating
        confluence += 15
        notes.append('❌ Wyckoff 1HR: No Re-accumulation')
    
    # === ANALYZE 2HR (CONFIRMATION - hypothesis) ===
    wyckoff_2hr = WyckoffReaccumulation(timeframe='2hr')
    result_2hr = wyckoff_2hr.analyze(df_2hr)
    
    # Add 2HR confirmation bonus
    if result_2hr['metadata']['phase'] == 'SPRING':
        # Spring on 2HR (very strong!)
        confluence += 35
        notes.append('✅ Wyckoff 2HR CONFIRMS: SPRING - Very Strong!')
        
    elif result_2hr['metadata']['phase'] == 'BREAKOUT':
        # Breakout on 2HR
        confluence += 30
        notes.append('✅ Wyckoff 2HR CONFIRMS: BREAKOUT!')
        
    elif result_2hr['metadata']['phase'] == 'RANGE':
        # Range on 2HR
        confluence += 25
        notes.append('✅ Wyckoff 2HR CONFIRMS: Re-accumulation Range')
        
    elif result_2hr['metadata']['phase'] == 'TRENDING':
        # Trending on 2HR
        confluence += 15
        notes.append('✅ Wyckoff 2HR: Trending')
    
    # === MULTI-TIMEFRAME ALIGNMENT BONUS ===
    mtf_aligned = False
    if (result_1hr['metadata']['phase'] in ['SPRING', 'BREAKOUT', 'RANGE'] and 
        result_2hr['metadata']['phase'] == result_1hr['metadata']['phase']):
        # Both timeframes in same phase!
        confluence += 40
        notes.append(f"🎯 MTF ALIGNMENT: Both 1HR & 2HR in {result_1hr['metadata']['phase']} phase!")
        mtf_aligned = True
    
    return {
        'confluence': confluence,
        'notes': notes,
        '1hr_result': result_1hr,
        '2hr_result': result_2hr,
        'mtf_aligned': mtf_aligned,
        '1hr_phase': result_1hr['metadata']['phase'],
        '2hr_phase': result_2hr['metadata']['phase']
    }
