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

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='how',
    category='PRICE_LEVELS',
    class_name='HOW',
    default_weight=20,
    valid_signals=[
        # Granular event signals
        'BELOW_HOW', 'BREAKING_OUT', 'BREAKOUT_CONFIRMED',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BELOW_HOW': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Below HOW - Price below weekly high. HOW acting as major resistance. Wait for breakout confirmation or range trades.'
        },
        'BREAKING_OUT': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Breaking out HOW - Price attempting weekly high breakout. Watch for confirmation. Potential bullish momentum. Key resistance test.'
        },
        'BREAKOUT_CONFIRMED': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'HOW breakout confirmed - Price broke above weekly high. Strong bullish signal. Enter longs. New weekly highs. Momentum confirmed.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot calculate HOW. Check data quality and timestamp availability.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need at least one week of data for HOW calculation. Wait for more price history.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish HOW - Breaking out or above weekly high. Long positions favorable. Strong weekly momentum confirmed.'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish HOW - Below weekly high. Short positions favorable or wait. Major resistance overhead. Weekly range bound.'
        },
        'NEUTRAL': {
                'max_points': 10,
                'formula': 'scaled',
                'ui_visible': False,  # Filter from Strategy Builder UI

                'description': 'Neutral HOW - Near weekly high equilibrium. Wait for breakout or rejection confirmation. Key decision point.'
        }
}
)
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
        
        # REVERSAL CONFIRMATION: Track price action after testing HOW
        self.reversal_candles = 5  # Monitor 5 candles after test for reversal pattern
        self.last_how_test_bar = None  # Bar that tested HOW
        self.bars_since_test = []  # Track bars after HOW test for reversal detection
        
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
    
    def _determine_dual_signals(self, current_price: float, how: float,
                                 distance_pct: float, distance_class: str,
                                 breakout_status: str, reversal_rejection: bool,
                                 reversal_breakthrough: bool) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        if reversal_breakthrough:
            granular = 'BREAKOUT_CONFIRMED'
            simple = 'BULLISH'
        elif reversal_rejection:
            granular = 'BELOW_HOW'
            simple = 'BEARISH'
        elif breakout_status == 'BREAKOUT_CONFIRMED':
            granular = 'BREAKOUT_CONFIRMED'
            simple = 'BULLISH'
        elif breakout_status == 'BREAKING_OUT':
            granular = 'BREAKING_OUT'
            simple = 'NEUTRAL'
        elif distance_class in ['AT_HOW', 'VERY_CLOSE'] and distance_pct < 0:
            granular = 'BELOW_HOW'
            simple = 'BEARISH'
        elif current_price < how:
            granular = 'BELOW_HOW'
            simple = 'NEUTRAL'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        
        return granular, simple
    
    def calculate_variable_confidence(self, signal: str, distance_class: str, is_new_event: bool) -> float:
        """OPTIMIZED V2: Variable confidence for both granular and simple signals"""
        if signal in ['BREAKOUT_CONFIRMED', 'BULLISH']:
            base = 70
        elif signal in ['BELOW_HOW', 'BEARISH']:
            base = 60
        elif signal == 'BREAKING_OUT':
            base = 65
        else:
            base = 50
        
        if distance_class in ['AT_HOW', 'VERY_CLOSE']:
            base = min(95, base + 15)
        elif distance_class == 'FAR':
            base = max(40, base - 15)
        
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
        
        # REVERSAL CONFIRMATION: Detect reversal patterns after testing HOW (resistance)
        reversal_rejection = False  # Bearish reversal after testing resistance
        reversal_breakthrough = False  # Bullish continuation after breaking resistance
        
        current_bar = {
            'close': current_price,
            'low': float(df['low'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'distance': distance_pct,
            'tested_how': distance_class in ['AT_HOW', 'VERY_CLOSE', 'CLOSE'] and distance_pct < 0
        }
        
        # Check if testing HOW (came close from below but didn't break)
        if current_bar['tested_how'] and not is_new_how:
            self.last_how_test_bar = current_bar
            self.bars_since_test = []
        
        # Monitor bars after test
        if self.last_how_test_bar is not None:
            self.bars_since_test.append(current_bar)
            
            if len(self.bars_since_test) > self.reversal_candles:
                self.bars_since_test.pop(0)
            
            # Check for BEARISH REVERSAL (lower highs + lower lows after testing resistance)
            if len(self.bars_since_test) >= self.reversal_candles:
                recent = self.bars_since_test[-self.reversal_candles:]
                
                lower_highs = all(recent[i]['high'] < recent[i-1]['high'] for i in range(1, len(recent)))
                lower_lows = all(recent[i]['low'] < recent[i-1]['low'] for i in range(1, len(recent)))
                
                if lower_highs and lower_lows:
                    reversal_rejection = True
                    self.last_how_test_bar = None
                    self.bars_since_test = []
            
            # Reset if price breaks level or moves far away
            if is_new_how or distance_class == 'FAR':
                self.last_how_test_bar = None
                self.bars_since_test = []
        
        # Check for BULLISH BREAKTHROUGH (higher highs + higher lows after breaking resistance)
        if is_new_how:
            self.bars_since_test = [current_bar]
        
        if is_new_how or (self.prev_how is not None and how > self.prev_how):
            if len(self.bars_since_test) > 0 and len(self.bars_since_test) < self.reversal_candles:
                self.bars_since_test.append(current_bar)
                
                if len(self.bars_since_test) >= self.reversal_candles:
                    recent = self.bars_since_test[-self.reversal_candles:]
                    
                    higher_highs = all(recent[i]['high'] > recent[i-1]['high'] for i in range(1, len(recent)))
                    higher_lows = all(recent[i]['low'] > recent[i-1]['low'] for i in range(1, len(recent)))
                    
                    if higher_highs and higher_lows:
                        reversal_breakthrough = True
        
        # DUAL SIGNAL ARCHITECTURE: Determine both granular and simple signals
        granular_signal, simple_signal = self._determine_dual_signals(
            current_price, how, distance_pct, distance_class,
            breakout_status, reversal_rejection, reversal_breakthrough
        )
        
        # Use granular signal as primary
        signal = granular_signal
        
        # ENHANCEMENT 2: Event tracking
        is_new_event = False
        if self.prev_signal is not None and signal != self.prev_signal:
            is_new_event = True
        elif is_new_how:
            is_new_event = True
        elif reversal_rejection or reversal_breakthrough:
            is_new_event = True
        
        # ENHANCEMENT 3: Variable confidence (BOOSTED for reversal confirmation)
        confidence = self.calculate_variable_confidence(signal, distance_class, is_new_event)
        
        if reversal_rejection or reversal_breakthrough:
            confidence = min(95, confidence + 25)
        
        # Build confluence
        confluence_factors = []
        
        # Reversal confirmation confluence (HIGHEST PRIORITY)
        if reversal_rejection:
            confluence_factors.append('⭐⭐⭐ BEARISH REVERSAL CONFIRMED AT HOW!')
            confluence_factors.append(f'✓ Tested HOW then {self.reversal_candles} bars of lower highs + lower lows')
            confluence_factors.append('✓ Strong reversal pattern - weekly resistance holding with downtrend forming')
        elif reversal_breakthrough:
            confluence_factors.append('⭐⭐⭐ BULLISH BREAKTHROUGH CONFIRMED AT HOW!')
            confluence_factors.append(f'✓ Broke HOW then {self.reversal_candles} bars of higher highs + higher lows')
            confluence_factors.append('✓ Strong continuation pattern - weekly uptrend established')
        
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
        
        # Metadata (ENHANCED with retest confirmation + DUAL SIGNALS)
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
            'reversal_rejection': reversal_rejection,
            'reversal_breakthrough': reversal_breakthrough,
            'reversal_candles': self.reversal_candles,
            'bars_monitored': len(self.bars_since_test),
            # DUAL SIGNAL ARCHITECTURE
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
        }
        
        return {
            'signal': signal,  # Granular signal (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
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
