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
from datetime import datetime
import pandas as pd
import numpy as np


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
        self.confirmation_candles = 3  # Require 3 consecutive bars
        self.bounce_test_bars = []  # Track bars testing support
        self.breakdown_bars = []  # Track bars breaking below
        
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
    
    def calculate_variable_confidence(self, signal: str, distance_class: str, is_new_event: bool) -> float:
        """
        OPTIMIZED V2: Further reduced to hit 85-88% average for weekly
        """
        # Base confidence by signal (FURTHER OPTIMIZED)
        if signal == 'BEARISH':
            base = 60  # Breakdown (reduced from 65)
        elif signal == 'BULLISH':
            base = 65  # Bounce from LOW (reduced from 70)
        else:  # NEUTRAL
            base = 50  # Neutral (reduced from 55)
        
        # Adjust by distance (±15% for variation)
        if distance_class in ['AT_LOW', 'VERY_CLOSE']:
            base = min(95, base + 15)  # Near LOW
        elif distance_class == 'FAR':
            base = max(40, base - 15)  # Far from LOW
        
        # Fresh event boost (+15% for new events)
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
        
        # RETEST CONFIRMATION: Track LOW retests
        confirmed_bounce = False
        confirmed_breakdown = False
        
        current_bar = {
            'close': current_price,
            'low': float(df['low'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'distance': distance_pct,
            'breached_below': float(df['low'].iloc[-1]) < low,
            'breached_above': float(df['high'].iloc[-1]) > low,
            'closed_above': current_price > low,
            'closed_below': current_price < low
        }
        
        # BOUNCE TEST: Price wicks BELOW LOW but closes ABOVE (support holding)
        if current_bar['breached_below'] and current_bar['closed_above']:
            self.bounce_test_bars.append(current_bar)
            if len(self.bounce_test_bars) > self.confirmation_candles + 2:
                self.bounce_test_bars.pop(0)
            
            if len(self.bounce_test_bars) >= self.confirmation_candles:
                recent_bars = self.bounce_test_bars[-self.confirmation_candles:]
                all_tested_and_held = all(
                    bar['breached_below'] and bar['closed_above']
                    for bar in recent_bars
                )
                
                if all_tested_and_held:
                    confirmed_bounce = True
                    self.bounce_test_bars = []
        elif distance_class not in ['AT_LOW', 'VERY_CLOSE']:
            if len(self.bounce_test_bars) > 0:
                self.bounce_test_bars = []
        
        # BREAKDOWN TEST: Price closes BELOW LOW (support broken)
        if current_bar['closed_below']:
            self.breakdown_bars.append(current_bar)
            if len(self.breakdown_bars) > self.confirmation_candles + 2:
                self.breakdown_bars.pop(0)
            
            if len(self.breakdown_bars) >= self.confirmation_candles:
                recent_bars = self.breakdown_bars[-self.confirmation_candles:]
                all_closed_below = all(
                    bar['closed_below']
                    for bar in recent_bars
                )
                
                if all_closed_below:
                    confirmed_breakdown = True
                    self.breakdown_bars = []
        elif current_bar['closed_above']:
            if len(self.breakdown_bars) > 0:
                self.breakdown_bars = []
        
        # Determine signal (ENHANCED with retest confirmation)
        if confirmed_bounce:
            signal = 'BULLISH'
        elif confirmed_breakdown:
            signal = 'BEARISH'
        elif breakdown_status == 'BREAKDOWN_CONFIRMED' or is_new_low:
            signal = 'BEARISH'
        elif breakdown_status == 'BREAKING_DOWN':
            signal = 'NEUTRAL'
        elif distance_class == 'AT_LOW' and distance_pct > 0:
            signal = 'BULLISH'
        else:
            signal = 'NEUTRAL'
        
        # ENHANCEMENT 2: Event tracking
        is_new_event = False
        if self.prev_signal is not None and signal != self.prev_signal:
            is_new_event = True
        elif is_new_low:
            is_new_event = True
        elif confirmed_bounce or confirmed_breakdown:
            is_new_event = True
        
        # ENHANCEMENT 3: Variable confidence (BOOSTED for retest confirmation)
        confidence = self.calculate_variable_confidence(signal, distance_class, is_new_event)
        
        if confirmed_bounce or confirmed_breakdown:
            confidence = min(95, confidence + 20)
        
        # Build confluence
        confluence_factors = []
        
        # Retest confirmation confluence (HIGHEST PRIORITY)
        if confirmed_bounce:
            confluence_factors.append('⭐⭐ CONFIRMED BOUNCE FROM LOW - Strong weekly bullish setup!')
            confluence_factors.append(f'✓ {self.confirmation_candles} retests: wicked below, closed above (weekly support holding!)')
        elif confirmed_breakdown:
            confluence_factors.append('⭐⭐ CONFIRMED BREAKDOWN BELOW LOW - Strong weekly bearish setup!')
            confluence_factors.append(f'✓ {self.confirmation_candles} bars: closed below LOW (weekly support broken!)')
        
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
            'confirmed_bounce': confirmed_bounce,
            'confirmed_breakdown': confirmed_breakdown,
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
