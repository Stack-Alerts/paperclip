"""
IHOD (Intraday High of Day) Building Block
Category: Price Levels
Purpose: TODAY's highest price for intraday support/resistance

This block tracks the highest price reached SO FAR during the current trading day.
Differs from HOD which tracks YESTERDAY's high.
"""

from typing import Dict, Any
from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np

import logging
logger = logging.getLogger(__name__)

@register_block(
    name='ihod',
    category='PRICE_LEVELS',
    class_name='IHOD',
    default_weight=20,
    valid_signals=[
        # Granular event signals
        'BULLISH_BREAK',      # Broke above previous IHOD
        'BEARISH_REJECTION',  # Rejected at IHOD
        'AT_IHOD',           # Price at IHOD
        'BELOW_IHOD',        # Price below IHOD
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR'
    ],
    signal_tiers={
        'BULLISH_BREAK': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bullish IHOD break - Price broke above previous intraday high. New IHOD made. Bullish momentum signal. Enter longs on breakout. Stop below previous IHOD. Target next resistance.'
        },
        'BEARISH_REJECTION': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish IHOD rejection - Price rejected at intraday high. Failed breakout. Reversal signal. Enter shorts on rejection. Stop above IHOD. Target support levels.'
        },
        'AT_IHOD': {
            'max_points': 15,
            'formula': 'scaled',
            'description': 'At IHOD - Price testing intraday high. Consolidation at resistance. Watch for breakout or rejection. Wait for confirmation before entry. Key decision point.'
        },
        'BELOW_IHOD': {
            'max_points': 10,
            'formula': 'scaled',
            'description': 'Below IHOD - Price below intraday high. Normal state. IHOD acting as resistance. Watch for move back toward IHOD or continuation lower.'
        },
        'NEUTRAL': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Neutral IHOD - No clear signal from intraday high. Price not near IHOD. Wait for price to approach resistance or establish new range.'
        },
        'ERROR': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Analysis error - Cannot calculate IHOD signals. Check data quality, timestamp availability, and sufficient bar history.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish IHOD - Intraday high breakout confirmed. Strong bullish signal. Long positions favored. Momentum building. High probability continuation.'
        },
        'BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish IHOD - Rejection at intraday high confirmed. Bearish reversal signal. Short positions favored. Resistance holding. High probability decline.'
        }
    }
)
class IHOD:
    """
    IHOD - Intraday High of Day
    
    Tracks TODAY's highest price reached so far.
    
    Key Differences from HOD:
    - HOD = Yesterday's high (static reference)
    - IHOD = Today's high (dynamic, updates intraday)
    
    Use Cases:
    - Intraday breakout trading
    - Day trading resistance levels
    - Scalping range boundaries
    - Real-time resistance tracking
    
    Signals:
    - BULLISH_BREAK: New IHOD made (breakout)
    - BEARISH_REJECTION: Rejected at IHOD (reversal)
    - AT_IHOD: Price testing IHOD
    - BELOW_IHOD: Price below today's high
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
        self.prev_ihod = None
        self.proximity_threshold = 0.15  # 0.15% = ~$67 on $45k BTC
    
    def _determine_dual_signals(self, distance_pct: float, is_new_ihod: bool, prev_high: float, current_high: float, current_close: float, current_low: float, ihod: float) -> tuple:
        """
        DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)
        
        FIXED: Simplified rejection detection:
        - AT_IHOD: Price testing IHOD (close near high)
        - BEARISH_REJECTION: High touched IHOD but closed in lower half of bar
        """
        
        if is_new_ihod:
            # Breaking to new IHOD
            granular = 'BULLISH_BREAK'
            simple = 'BULLISH'
        elif abs(distance_pct) < self.proximity_threshold:
            # NEAR IHOD: Price close to intraday high
            
            # Simple rejection check: high touched IHOD, close in lower 60% of bar
            touched_ihod = current_high >= ihod * 0.998  # Within 0.2% of IHOD
            bar_range = current_high - current_low
            
            if bar_range > 0:
                # Calculate where close is in the bar (0 = low, 1 = high)
                close_position = (current_close - current_low) / bar_range
                closed_weak = close_position < 0.6  # Closed in lower 60% of bar
            else:
                closed_weak = False
            
            # Rejection = touched IHOD but closed weak
            has_rejection = touched_ihod and closed_weak
            
            if has_rejection:
                # Rejected at IHOD
                granular = 'BEARISH_REJECTION'
                simple = 'BEARISH'
            else:
                # Testing IHOD
                granular = 'AT_IHOD'
                simple = 'NEUTRAL'
        elif distance_pct < -0.5:
            # Below IHOD (normal state)
            granular = 'BELOW_IHOD'
            simple = 'NEUTRAL'
        else:
            # Fallback
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        
        return granular, simple
        
    def calculate_ihod(self, df: pd.DataFrame) -> float:
        """Calculate INTRADAY High of Day (today's high so far)"""
        if 'timestamp' not in df.columns or 'high' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Filter for today's data only
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None
        
        # Return highest high SO FAR today (dynamic, updates as day progresses)
        return float(today_data['high'].max())
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Analyze IHOD level and price relationship"""
        
        # Validation
        if not all(col in df.columns for col in ['timestamp', 'high', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe
            }
        
        if len(df) < 5:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Insufficient data'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        # Calculate IHOD from bars BEFORE current bar to detect breaks
        ihod_prev = self.calculate_ihod(df.iloc[:-1])
        
        # Calculate IHOD including current bar
        ihod_current = self.calculate_ihod(df)
        
        # Use previous IHOD for comparison, current for tracking
        ihod = ihod_prev if ihod_prev is not None else ihod_current
        
        if ihod is None:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate IHOD'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        current_price = float(df['close'].iloc[-1])
        current_high = float(df['high'].iloc[-1])
        current_low = float(df['low'].iloc[-1])
        prev_high = float(df['high'].iloc[-2]) if len(df) >= 2 else current_high
        distance_pct = ((current_price - ihod) / ihod) * 100
        
        # Detect events: new IHOD if current bar's high breaks previous IHOD
        is_new_ihod = current_high > ihod
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(
            distance_pct, is_new_ihod, prev_high, current_high, current_price, current_low, ihod
        )
        signal = granular_signal
        
        # Determine confidence
        if signal == 'BULLISH_BREAK':
            confidence = 85
        elif signal == 'BEARISH_REJECTION':
            confidence = 80
        elif signal == 'AT_IHOD':
            confidence = 70
        elif signal == 'BELOW_IHOD':
            confidence = 60
        else:
            confidence = 50
        
        # Update tracking
        self.prev_ihod = ihod
        
        return {
            'signal': signal,  # Granular signal (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
            'confidence': confidence,
            'metadata': {
                'ihod': round(ihod, 2),
                'current_price': round(current_price, 2),
                'distance_pct': round(distance_pct, 2),
                'is_new_ihod': is_new_ihod,
                'description': f"Today's high: ${ihod:.2f}, Price: ${current_price:.2f} ({distance_pct:+.2f}%)",
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe
        }


if __name__ == "__main__":
    # Test
    logger.info("="*80)
    logger.info("IHOD (INTRADAY HIGH OF DAY) TEST")
    logger.info("="*80)
    
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    
    # Simulate intraday price action
    highs = 45000 + np.cumsum(np.random.uniform(-50, 100, 50))
    closes = highs - np.random.uniform(0, 50, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'close': closes,
        'open': closes - 20,
        'low': closes - 50,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    ihod = IHOD()
    result = ihod.analyze(data)
    
    logger.info(f"Signal: {result['signal']}")
    logger.info(f"Confidence: {result['confidence']}%")
    logger.info(f"Description: {result['metadata']['description']}")
    logger.info(f"Is New IHOD: {result['metadata']['is_new_ihod']}")
    logger.info("="*80)
