"""
HOW (High of Week) Building Block
Category: Price Levels
Purpose: Weekly high price level for major resistance and breakout detection
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous high of week level

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class HOW:
    """
    HOW - High of Week Price Level (ENHANCED 2026-01-04)
    
    Tracks the highest price reached during the current trading week.
    Critical level for:
    - Major resistance identification
    - Weekly breakout detection
    - Swing trading setups
    - Higher timeframe analysis
    
    ENHANCEMENTS (2026-01-04):
    - Added BULLISH signal generation for HOW breakouts
    - Added event tracking for HOW breaks and tests
    - Improved confidence variation (70-100% range)
    - Fixed breakout detection to track previous HOW
    
    Parameters:
        timeframe: Data timeframe
        week_start: Day week starts (0=Monday, default: 0)
    """
    
    def __init__(self, timeframe: str = '15min', week_start: int = 0, **kwargs):
        """Initialize HOW block"""
        self.timeframe = timeframe
        self.week_start = week_start
        
        # ENHANCEMENT: Track previous state for event detection
        self.prev_how = None
        self.prev_signal = None
        
        # RETEST CONFIRMATION: Track retests of HOW level
        self.confirmation_candles = 2  # Require 2 consecutive bars (more realistic)
        self.rejection_test_bars = []  # Track bars testing resistance
        self.breakthrough_bars = []  # Track bars breaking above
        
        # Bitcoin-specific distance thresholds (% from HOW)
        self.btc_distance_thresholds = {
            'at_how': 0.2,          # < 0.2% - at HOW
            'very_close': 1.0,      # 0.2-1% - very close
            'close': 2.5,           # 1-2.5% - close
            'moderate': 5.0,        # 2.5-5% - moderate
            'far': 5.0              # > 5% - far from HOW
        }
    
    def calculate_how(self, df: pd.DataFrame) -> float:
        """Calculate High of Week from intraday data"""
        if 'timestamp' not in df.columns or 'high' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_week = current_time.isocalendar()[1]
        current_year = current_time.isocalendar()[0]
        
        week_data = df[
            (df['timestamp'].dt.isocalendar().week == current_week) &
            (df['timestamp'].dt.isocalendar().year == current_year)
        ]
        
        if len(week_data) == 0:
            return None
        
        return float(week_data['high'].max())
    
    def detect_breakout(self, current_price: float, how: float, prev_how: float = None, threshold_pct: float = 0.1) -> Dict[str, Any]:
        """
        ENHANCED: Detect HOW breakout by comparing to PREVIOUS HOW
        
        Args:
            current_price: Current price
            how: Current High of Week
            prev_how: Previous HOW (to detect fresh breaks)
            threshold_pct: Threshold for breakout confirmation (default: 0.1%)
            
        Returns:
            Dict with breakout status and event info
        """
        if how is None:
            return {
                'status': 'NO_HOW',
                'is_new_how': False,
                'is_breakout': False
            }
        
        # Check if HOW was updated (new weekly high made)
        is_new_how = False
        if prev_how is not None and how > prev_how:
            is_new_how = True
        
        # Calculate distance from PREVIOUS HOW (not current, which updates)
        ref_how = prev_how if prev_how is not None else how
        distance_pct = ((current_price - ref_how) / ref_how) * 100
        
        # Determine breakout status
        if is_new_how and distance_pct > threshold_pct:
            return {
                'status': 'BREAKOUT_CONFIRMED',
                'is_new_how': True,
                'is_breakout': True
            }
        elif distance_pct > 0 and distance_pct <= threshold_pct:
            return {
                'status': 'BREAKING_OUT',
                'is_new_how': is_new_how,
                'is_breakout': False
            }
        else:
            return {
                'status': 'BELOW_HOW',
                'is_new_how': False,
                'is_breakout': False
            }
    
    def calculate_distance(self, price: float, how: float) -> float:
        """Calculate percentage distance from HOW"""
        if how is None:
            return None
        return ((price - how) / how) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from HOW"""
        if distance_pct is None:
            return 'NO_HOW'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_how']:
            return 'AT_HOW'
        elif abs_dist < self.btc_distance_thresholds['very_close']:
            return 'VERY_CLOSE'
        elif abs_dist < self.btc_distance_thresholds['close']:
            return 'CLOSE'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        else:
            return 'FAR'
    
    def calculate_variable_confidence(self, signal: str, distance_class: str, is_new_event: bool) -> float:
        """
        OPTIMIZED V2: Further reduced bases to hit 80-85% average
        """
        # Base confidence by signal (FURTHER OPTIMIZED)
        if signal == 'BULLISH':
            base = 70  # Weekly breakout (reduced from 75)
        elif signal == 'BEARISH':
            base = 60  # Rejection at HOW (reduced from 65)
        else:  # NEUTRAL
            base = 50  # Neutral (reduced from 55)
        
        # Adjust by distance (±15% for variation)
        if distance_class in ['AT_HOW', 'VERY_CLOSE']:
            base = min(95, base + 15)  # Near HOW
        elif distance_class == 'FAR':
            base = max(40, base - 15)  # Far from HOW
        
        # Fresh event boost (+15% for new events)
        if is_new_event:
            base = min(95, base + 15)
        
        return base
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method (ENHANCED)"""
        # Validate
        if not all(col in df.columns for col in ['timestamp', 'high', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No data provided', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate HOW
        how = self.calculate_how(df)
        
        if how is None:
            return {
                'signal': 'NO_HOW_DATA',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate HOW', 'is_new_event': False},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        
        # ENHANCEMENT 1: Detect breakout with prev_how tracking
        breakout_info = self.detect_breakout(current_price, how, self.prev_how)
        breakout_status = breakout_info['status']
        is_new_how = breakout_info['is_new_how']
        is_breakout = breakout_info['is_breakout']
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, how)
        distance_class = self.classify_distance(distance_pct)
        
        # RETEST CONFIRMATION: Track HOW retests
        confirmed_rejection = False
        confirmed_breakthrough = False
        
        current_bar = {
            'close': current_price,
            'low': float(df['low'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'distance': distance_pct,
            'breached_above': float(df['high'].iloc[-1]) > how,
            'breached_below': float(df['low'].iloc[-1]) < how,
            'closed_above': current_price > how,
            'closed_below': current_price < how
        }
        
        # REJECTION TEST: Price wicks ABOVE HOW but closes BELOW (resistance holding)
        if current_bar['breached_above'] and current_bar['closed_below']:
            self.rejection_test_bars.append(current_bar)
            if len(self.rejection_test_bars) > self.confirmation_candles + 2:
                self.rejection_test_bars.pop(0)
            
            if len(self.rejection_test_bars) >= self.confirmation_candles:
                recent_bars = self.rejection_test_bars[-self.confirmation_candles:]
                all_tested_and_rejected = all(
                    bar['breached_above'] and bar['closed_below']
                    for bar in recent_bars
                )
                
                if all_tested_and_rejected:
                    confirmed_rejection = True
                    self.rejection_test_bars = []
        elif distance_class not in ['AT_HOW', 'VERY_CLOSE']:
            if len(self.rejection_test_bars) > 0:
                self.rejection_test_bars = []
        
        # BREAKTHROUGH TEST: Price closes ABOVE HOW (resistance broken)
        if current_bar['closed_above']:
            self.breakthrough_bars.append(current_bar)
            if len(self.breakthrough_bars) > self.confirmation_candles + 2:
                self.breakthrough_bars.pop(0)
            
            if len(self.breakthrough_bars) >= self.confirmation_candles:
                recent_bars = self.breakthrough_bars[-self.confirmation_candles:]
                all_closed_above = all(
                    bar['closed_above']
                    for bar in recent_bars
                )
                
                if all_closed_above:
                    confirmed_breakthrough = True
                    self.breakthrough_bars = []
        elif current_bar['closed_below']:
            if len(self.breakthrough_bars) > 0:
                self.breakthrough_bars = []
        
        # Determine signal (ENHANCED with retest confirmation)
        if confirmed_breakthrough:
            signal = 'BULLISH'
        elif confirmed_rejection:
            signal = 'BEARISH'
        elif breakout_status == 'BREAKOUT_CONFIRMED' or is_new_how:
            signal = 'BULLISH'
        elif breakout_status == 'BREAKING_OUT':
            signal = 'NEUTRAL'
        elif distance_class == 'AT_HOW' and distance_pct < 0:
            signal = 'BEARISH'
        else:
            signal = 'NEUTRAL'
        
        # ENHANCEMENT 2: Event tracking
        is_new_event = False
        if self.prev_signal is not None and signal != self.prev_signal:
            is_new_event = True
        elif is_new_how:
            is_new_event = True
        elif confirmed_rejection or confirmed_breakthrough:
            is_new_event = True
        
        # ENHANCEMENT 3: Variable confidence (BOOSTED for retest confirmation)
        confidence = self.calculate_variable_confidence(signal, distance_class, is_new_event)
        
        if confirmed_rejection or confirmed_breakthrough:
            confidence = min(95, confidence + 20)
        
        # Build confluence
        confluence_factors = []
        
        # Retest confirmation confluence (HIGHEST PRIORITY)
        if confirmed_rejection:
            confluence_factors.append('⭐⭐ CONFIRMED REJECTION FROM HOW - Strong weekly bearish setup!')
            confluence_factors.append(f'✓ {self.confirmation_candles} retests: wicked above, closed below (weekly resistance holding!)')
        elif confirmed_breakthrough:
            confluence_factors.append('⭐⭐ CONFIRMED BREAKTHROUGH ABOVE HOW - Strong weekly bullish setup!')
            confluence_factors.append(f'✓ {self.confirmation_candles} bars: closed above HOW (weekly resistance broken!)')
        
        # Event-specific confluence
        elif is_new_event:
            if is_new_how:
                confluence_factors.append('⭐ NEW HOW: Fresh weekly high - bullish breakout!')
            elif signal == 'BULLISH' and self.prev_signal != 'BULLISH':
                confluence_factors.append('⭐ NEW STATE: HOW breakout initiated')
            elif signal == 'BEARISH' and self.prev_signal != 'BEARISH':
                confluence_factors.append('⭐ NEW STATE: HOW rejection detected')
        
        if breakout_status == 'BREAKOUT_CONFIRMED':
            confluence_factors.append('HOW breakout confirmed - strong weekly bullish signal')
        elif breakout_status == 'BREAKING_OUT':
            confluence_factors.append('Price breaking above HOW - major resistance test')
        elif distance_class in ['AT_HOW', 'VERY_CLOSE']:
            if distance_pct < 0:
                confluence_factors.append('Price testing HOW resistance - potential weekly rejection')
            else:
                confluence_factors.append('Price at HOW - critical weekly level')
        
        confluence_factors.append(f'HOW: ${how:.2f}')
        confluence_factors.append(f'Distance from HOW: {distance_pct:+.2f}% ({distance_class})')
        
        # Update tracking
        self.prev_how = how
        self.prev_signal = signal
        
        # Metadata (ENHANCED with retest confirmation)
        metadata = {
            'how': round(how, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'breakout_status': breakout_status,
            'is_new_how': is_new_how,
            'is_breakout': is_breakout,
            'is_major_resistance': distance_class in ['AT_HOW', 'VERY_CLOSE'] and distance_pct < 0,
            'is_breaking_out': breakout_status in ['BREAKING_OUT', 'BREAKOUT_CONFIRMED'],
            'is_new_event': is_new_event,
            'confirmed_rejection': confirmed_rejection,
            'confirmed_breakthrough': confirmed_breakthrough,
            'confirmation_candles': self.confirmation_candles
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
    np.random.seed(42)
    base = 45000
    highs = base + np.random.uniform(-500, 1000, 200)
    closes = highs - np.random.uniform(0, 200, 200)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'close': closes,
        'open': closes - 50,
        'low': closes - 100,
        'volume': np.random.uniform(100, 1000, 200)
    })
    
    how_block = HOW()
    result = how_block.analyze(data)
    
    print("=" * 80)
    print("HOW (HIGH OF WEEK) - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nHOW Analysis:")
    print(f"  HOW: ${result['metadata']['how']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"  Breakout Status: {result['metadata']['breakout_status']}")
    print(f"  Major Resistance: {result['metadata']['is_major_resistance']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
