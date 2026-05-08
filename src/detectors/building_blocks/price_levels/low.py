"""
LOW (Low of Week) Building Block
Category: Price Levels
Purpose: Weekly low price level for major support and breakdown detection
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous low of week level

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
    name='low',
    category='PRICE_LEVELS',
    class_name='LOW',
    default_weight=20,
    description='Low - Detects significant recent swing lows and structural price lows. Used as dynamic support reference and stop placement guide. Neutral indicator identifying where buyers have previously defended price.',
    direction='NEUTRAL',
    valid_signals=[
        # Granular event signals
        'ABOVE_LOW', 'AT_LOW', 'BREAKDOWN_CONFIRMED', 'BREAKING_DOWN',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'NO_LOW', 'NO_LOW_DATA', 'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'ABOVE_LOW': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Above LOW - Price above weekly low. LOW acting as major support. Bullish bias. Support holding. Range trades or continuation.'
        },
        'AT_LOW': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'At LOW - Price testing weekly low. Key decision level. Watch for bounce or breakdown. High probability setup. Major support test.'
        },
        'BREAKDOWN_CONFIRMED': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'LOW breakdown confirmed - Price broke below weekly low. Strong bearish signal. Enter shorts. New weekly lows. Breakdown confirmed.'
        },
        'BREAKING_DOWN': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Breaking down LOW - Price attempting weekly low breakdown. Watch for confirmation. Potential bearish momentum. Key support test.'
        },
        'NO_LOW': {
                'points': 0,
                'description': 'No LOW - No weekly low detected. Wait for more price data or check calculation.',
                'ui_visible': False  # Filter from Strategy Builder UI
        },
        'NO_LOW_DATA': {
                'points': 0,
                'description': 'No LOW data - Cannot calculate weekly low. Check data quality and availability.',
                'ui_visible': False  # Filter from Strategy Builder UI
        },
        'ERROR': {
                'points': 0,
                'description': 'Analysis error - Cannot calculate LOW. Check data quality and timestamp availability.',
                'ui_visible': False  # Filter from Strategy Builder UI
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'description': 'Insufficient data - Need at least one week of data for LOW calculation. Wait for more price history.',
                'ui_visible': False  # Filter from Strategy Builder UI
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish LOW - Above weekly low or bouncing. Long positions favorable. Weekly support confirmed. Strong weekly bias up.'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish LOW - Breaking down or below weekly low. Short positions favorable. Major support broken. Strong weekly momentum down.'
        },
        'NEUTRAL': {
                'max_points': 10,
                'formula': 'scaled',
                'ui_visible': False,  # Filter from Strategy Builder UI

                'description': 'Neutral LOW - Near weekly low equilibrium. Wait for bounce or breakdown confirmation. Key weekly decision point.'
        }
}
)
class LOW:
    """
    LOW - Low of Week Price Level (ENHANCED 2026-01-04)
    
    Tracks the lowest price reached during the current trading week.
    Critical level for:
    - Major support identification
    - Weekly breakdown detection
    - Swing trading setups
    - Higher timeframe analysis
    
    ENHANCEMENTS (2026-01-04):
    - Added BEARISH signal generation for LOW breakdowns
    - Added event tracking for LOW breaks and tests
    - Improved confidence variation (70-100% range)
    - Fixed breakdown detection to track previous LOW
    """
    
    def __init__(self, timeframe: str = '15min', week_start: int = 0, **kwargs):
        """Initialize LOW block"""
        self.timeframe = timeframe
        self.week_start = week_start
        
        # ENHANCEMENT: Track previous state for event detection
        self.prev_low = None
        self.prev_signal = None
        
        # RETEST CONFIRMATION: Track retests of LOW level
        self.reversal_candles = 5  # Monitor 5 candles after test for reversal pattern
        self.last_low_test_bar = None  # Bar that tested LOW
        self.bars_since_test = []  # Track bars after LOW test for reversal detection
        
        # Bitcoin-specific distance thresholds (% from LOW)
        self.btc_distance_thresholds = {
            'at_low': 0.2,
            'very_close': 1.0,
            'close': 2.5,
            'moderate': 5.0,
            'far': 5.0
        }
    
    def calculate_low(self, df: pd.DataFrame) -> float:
        """Calculate Low of Week from intraday data"""
        if 'timestamp' not in df.columns or 'low' not in df.columns:
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
        
        return float(week_data['low'].min())
    
    def detect_breakdown(self, current_price: float, low: float, prev_low: float = None, threshold_pct: float = 0.1) -> Dict[str, Any]:
        """
        ENHANCED: Detect LOW breakdown by comparing to PREVIOUS LOW
        
        Args:
            current_price: Current price
            low: Current Low of Week
            prev_low: Previous LOW (to detect fresh breaks)
            threshold_pct: Threshold for breakdown confirmation (default: 0.1%)
            
        Returns:
            Dict with breakdown status and event info
        """
        if low is None:
            return {
                'status': 'NO_LOW',
                'is_new_low': False,
                'is_breakdown': False
            }
        
        # Check if LOW was updated (new weekly low made)
        is_new_low = False
        if prev_low is not None and low < prev_low:
            is_new_low = True
        
        # Calculate distance from PREVIOUS LOW (not current, which updates)
        ref_low = prev_low if prev_low is not None else low
        distance_pct = ((current_price - ref_low) / ref_low) * 100
        
        # Determine breakdown status
        if is_new_low and distance_pct < -threshold_pct:
            return {
                'status': 'BREAKDOWN_CONFIRMED',
                'is_new_low': True,
                'is_breakdown': True
            }
        elif distance_pct < 0 and distance_pct >= -threshold_pct:
            return {
                'status': 'BREAKING_DOWN',
                'is_new_low': is_new_low,
                'is_breakdown': False
            }
        else:
            return {
                'status': 'ABOVE_LOW',
                'is_new_low': False,
                'is_breakdown': False
            }
    
    def calculate_distance(self, price: float, low: float) -> float:
        """Calculate percentage distance from LOW"""
        if low is None:
            return None
        return ((price - low) / low) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from LOW"""
        if distance_pct is None:
            return 'NO_LOW'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_low']:
            return 'AT_LOW'
        elif abs_dist < self.btc_distance_thresholds['very_close']:
            return 'VERY_CLOSE'
        elif abs_dist < self.btc_distance_thresholds['close']:
            return 'CLOSE'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        else:
            return 'FAR'
    
    def _determine_dual_signals(self, current_price: float, low: float,
                                 distance_pct: float, distance_class: str,
                                 breakdown_status: str, reversal_bounce: bool,
                                 reversal_breakdown: bool) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        if reversal_bounce:
            granular = 'AT_LOW'
            simple = 'BULLISH'
        elif reversal_breakdown:
            granular = 'BREAKDOWN_CONFIRMED'
            simple = 'BEARISH'
        elif breakdown_status == 'BREAKDOWN_CONFIRMED':
            granular = 'BREAKDOWN_CONFIRMED'
            simple = 'BEARISH'
        elif breakdown_status == 'BREAKING_DOWN':
            granular = 'BREAKING_DOWN'
            simple = 'NEUTRAL'
        elif distance_class in ['AT_LOW', 'VERY_CLOSE'] and distance_pct > 0:
            granular = 'AT_LOW'
            simple = 'BULLISH'
        elif current_price > low:
            granular = 'ABOVE_LOW'
            simple = 'NEUTRAL'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        
        return granular, simple
    
    def calculate_variable_confidence(self, signal: str, distance_class: str, is_new_event: bool) -> float:
        """OPTIMIZED V2: Variable confidence for both granular and simple signals"""
        if signal in ['BREAKDOWN_CONFIRMED', 'BEARISH']:
            base = 60
        elif signal in ['AT_LOW', 'ABOVE_LOW', 'BULLISH']:
            base = 65
        elif signal == 'BREAKING_DOWN':
            base = 55
        else:
            base = 50
        
        if distance_class in ['AT_LOW', 'VERY_CLOSE']:
            base = min(95, base + 15)
        elif distance_class == 'FAR':
            base = max(40, base - 15)
        
        if is_new_event:
            base = min(95, base + 15)
        
        return base
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method (ENHANCED)"""
        if not all(col in df.columns for col in ['timestamp', 'low', 'close']):
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
        
        low = self.calculate_low(df)
        
        if low is None:
            return {
                'signal': 'NO_LOW_DATA',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate LOW', 'is_new_event': False},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        
        # ENHANCEMENT 1: Detect breakdown with prev_low tracking
        breakdown_info = self.detect_breakdown(current_price, low, self.prev_low)
        breakdown_status = breakdown_info['status']
        is_new_low = breakdown_info['is_new_low']
        is_breakdown = breakdown_info['is_breakdown']
        
        distance_pct = self.calculate_distance(current_price, low)
        distance_class = self.classify_distance(distance_pct)
        
        # REVERSAL CONFIRMATION: Detect reversal patterns after testing LOW (support)
        reversal_bounce = False  # Bullish reversal after testing support
        reversal_breakdown = False  # Bearish continuation after breaking support
        
        current_bar = {
            'close': current_price,
            'low': float(df['low'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'distance': distance_pct,
            'tested_low': distance_class in ['AT_LOW', 'VERY_CLOSE', 'CLOSE'] and distance_pct > 0
        }
        
        # Check if testing LOW (came close from above but didn't break)
        if current_bar['tested_low'] and not is_new_low:
            self.last_low_test_bar = current_bar
            self.bars_since_test = []
        
        # Monitor bars after test
        if self.last_low_test_bar is not None:
            self.bars_since_test.append(current_bar)
            
            if len(self.bars_since_test) > self.reversal_candles:
                self.bars_since_test.pop(0)
            
            # Check for BULLISH REVERSAL (higher highs + higher lows after testing support)
            if len(self.bars_since_test) >= self.reversal_candles:
                recent = self.bars_since_test[-self.reversal_candles:]
                
                higher_highs = all(recent[i]['high'] > recent[i-1]['high'] for i in range(1, len(recent)))
                higher_lows = all(recent[i]['low'] > recent[i-1]['low'] for i in range(1, len(recent)))
                
                if higher_highs and higher_lows:
                    reversal_bounce = True
                    self.last_low_test_bar = None
                    self.bars_since_test = []
            
            # Reset if price breaks level or moves far away
            if is_new_low or distance_class == 'FAR':
                self.last_low_test_bar = None
                self.bars_since_test = []
        
        # Check for BEARISH BREAKDOWN (lower highs + lower lows after breaking support)
        if is_new_low:
            self.bars_since_test = [current_bar]
        
        if is_new_low or (self.prev_low is not None and low < self.prev_low):
            if len(self.bars_since_test) > 0 and len(self.bars_since_test) < self.reversal_candles:
                self.bars_since_test.append(current_bar)
                
                if len(self.bars_since_test) >= self.reversal_candles:
                    recent = self.bars_since_test[-self.reversal_candles:]
                    
                    lower_highs = all(recent[i]['high'] < recent[i-1]['high'] for i in range(1, len(recent)))
                    lower_lows = all(recent[i]['low'] < recent[i-1]['low'] for i in range(1, len(recent)))
                    
                    if lower_highs and lower_lows:
                        reversal_breakdown = True
        
        # DUAL SIGNAL ARCHITECTURE: Determine both granular and simple signals
        granular_signal, simple_signal = self._determine_dual_signals(
            current_price, low, distance_pct, distance_class,
            breakdown_status, reversal_bounce, reversal_breakdown
        )
        
        # Use granular signal as primary
        signal = granular_signal
        
        # ENHANCEMENT 2: Event tracking
        is_new_event = False
        if self.prev_signal is not None and signal != self.prev_signal:
            is_new_event = True
        elif is_new_low:
            is_new_event = True
        elif reversal_bounce or reversal_breakdown:
            is_new_event = True
        
        # ENHANCEMENT 3: Variable confidence (BOOSTED for reversal confirmation)
        confidence = self.calculate_variable_confidence(signal, distance_class, is_new_event)
        
        if reversal_bounce or reversal_breakdown:
            confidence = min(95, confidence + 25)
        
        # Build confluence
        confluence_factors = []
        
        # Reversal confirmation confluence (HIGHEST PRIORITY)
        if reversal_bounce:
            confluence_factors.append('⭐⭐⭐ BULLISH REVERSAL CONFIRMED AT LOW!')
            confluence_factors.append(f'✓ Tested LOW then {self.reversal_candles} bars of higher highs + higher lows')
            confluence_factors.append('✓ Strong reversal pattern - weekly support holding with uptrend forming')
        elif reversal_breakdown:
            confluence_factors.append('⭐⭐⭐ BEARISH BREAKDOWN CONFIRMED AT LOW!')
            confluence_factors.append(f'✓ Broke LOW then {self.reversal_candles} bars of lower highs + lower lows')
            confluence_factors.append('✓ Strong continuation pattern - weekly downtrend established')
        
        # Event-specific confluence
        elif is_new_event:
            if is_new_low:
                confluence_factors.append('⭐ NEW LOW: Fresh weekly low - bearish breakdown!')
            elif signal == 'BEARISH' and self.prev_signal != 'BEARISH':
                confluence_factors.append('⭐ NEW STATE: LOW breakdown initiated')
            elif signal == 'BULLISH' and self.prev_signal != 'BULLISH':
                confluence_factors.append('⭐ NEW STATE: LOW bounce detected')
        
        if breakdown_status == 'BREAKDOWN_CONFIRMED':
            confluence_factors.append('LOW breakdown confirmed - strong weekly bearish signal')
        elif breakdown_status == 'BREAKING_DOWN':
            confluence_factors.append('Price breaking below LOW - major support test')
        elif distance_class in ['AT_LOW', 'VERY_CLOSE']:
            if distance_pct > 0:
                confluence_factors.append('Price testing LOW support - potential weekly bounce')
            else:
                confluence_factors.append('Price at LOW - critical weekly level')
        
        confluence_factors.append(f'LOW: ${low:.2f}')
        confluence_factors.append(f'Distance from LOW: {distance_pct:+.2f}% ({distance_class})')
        
        # Update tracking
        self.prev_low = low
        self.prev_signal = signal
        
        metadata = {
            'low': round(low, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'breakdown_status': breakdown_status,
            'is_new_low': is_new_low,
            'is_breakdown': is_breakdown,
            'is_major_support': distance_class in ['AT_LOW', 'VERY_CLOSE'] and distance_pct > 0,
            'is_breaking_down': breakdown_status in ['BREAKING_DOWN', 'BREAKDOWN_CONFIRMED'],
            'is_new_event': is_new_event,
            'reversal_bounce': reversal_bounce,
            'reversal_breakdown': reversal_breakdown,
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
