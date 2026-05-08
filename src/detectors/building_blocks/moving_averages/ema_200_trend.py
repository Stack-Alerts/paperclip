"""
200 EMA Trend Filter Building Block
Category: Moving Averages
Purpose: Long-term trend identification and filter using 200-period EMA
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous HTF trend state above/below 200 EMA

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

import logging
logger = logging.getLogger(__name__)

@register_block(
    name='ema_200_trend',
    category='MOVING_AVERAGES',
    class_name='EMA200Trend',
    default_weight=12,
    description='EMA 200 Trend - Tracks price position relative to the 200 EMA (major long-term trend filter). Bullish when price is above, bearish when below. Primary macro trend direction indicator for strategy alignment.',
    direction='NEUTRAL',
    valid_signals=[
        # Granular signals
        'BULLISH_CROSS', 'BEARISH_CROSS', 'ABOVE_200EMA', 'BELOW_200EMA', 'AT_200EMA',
        # Simple signals
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'INSUFFICIENT_DATA', 'ERROR'
    ],
    signal_tiers={
        # Granular cross events
        'BULLISH_CROSS': {
                'base_points': 15,
                'formula': 'scaled',
                'description': 'Bullish cross above 200 EMA - Major trend reversal. Long-term uptrend starting. Enter longs. Stop below 200 EMA.'
        },
        'BEARISH_CROSS': {
                'base_points': 15,
                'formula': 'scaled',
                'description': 'Bearish cross below 200 EMA - Major trend reversal. Long-term downtrend starting. Enter shorts. Stop above 200 EMA.'
        },
        # Granular position
        'ABOVE_200EMA': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Price above 200 EMA - Long-term bullish trend. Favor longs only. 200 EMA acts as support. Avoid shorts.'
        },
        'BELOW_200EMA': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Price below 200 EMA - Long-term bearish trend. Favor shorts only. 200 EMA acts as resistance. Avoid longs.'
        },
        'AT_200EMA': {
                'base_points': 12,
                'formula': 'scaled',
                'description': 'Price at 200 EMA - Major support/resistance test. Wait for breakout or rejection. Set stops beyond 200 EMA.'
        },
        # Simple signals
        'BULLISH': {
                'base_points': 12,
                'formula': 'scaled',
                'description': 'Bullish 200 EMA trend - Above 200 EMA or bullish cross. Long positions favorable. Use 200 EMA as trailing stop.'
        },
        'BEARISH': {
                'base_points': 12,
                'formula': 'scaled',
                'description': 'Bearish 200 EMA trend - Below 200 EMA or bearish cross. Short positions favorable. Use 200 EMA as trailing stop.'
        },
        'NEUTRAL': {
                'max_points': 6,
                'formula': 'scaled',
                'ui_visible': False,  # Filter from Strategy Builder UI

                'description': 'Neutral 200 EMA - No clear long-term trend. Market ranging. Wait for decisive break above or below 200 EMA.'
        },
        # Status
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot calculate 200 EMA. Check data quality and minimum period requirements.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need at least 220 candles for 200 EMA calculation. Wait for more price history.'
        }
}
)
class EMA200Trend:
    """
    200 EMA Trend Filter - Long-Term Trend Indicator
    
    The 200 EMA is the gold standard for identifying long-term market trends.
    Acts as major support/resistance and trend filter for all strategies.
    
    Signals:
    - Above 200 EMA: Bullish long-term trend (only take longs)
    - Below 200 EMA: Bearish long-term trend (only take shorts)
    - Price distance from 200 EMA: Overextension detection
    - 200 EMA slope: Trend strength
    
    Parameters:
        period: EMA period (default: 200)
        timeframe: Data timeframe
    """
    
    def __init__(self, period: int = 220, timeframe: str = '15min', **kwargs):  # OPTIMIZED: 220 outperforms 200
        """Initialize 200 EMA Trend Filter block"""
        self.period = period
        self.timeframe = timeframe
        
        # Bitcoin-specific distance thresholds (% from 200 EMA)
        self.btc_distance_thresholds = {
            'touching': 0.5,       # < 0.5% - at EMA
            'near': 2.0,           # 0.5-2% - near EMA
            'moderate': 5.0,       # 2-5% - moderate distance
            'extended':  10.0,     # 5-10% - extended
            'overextended': 10.0   # > 10% - very overextended
        }
        
        # Reversal pattern tracking (5-bar confirmation)
        self.reversal_candles = 5  # Bars needed to confirm reversal
        self.tracking_bullish_reversal = False
        self.tracking_bearish_reversal = False
        self.reversal_bars_monitored = 0
        self.reversal_start_bar = None
    
    def _determine_dual_signals(self, crossed_above: bool, crossed_below: bool, 
                                 current_position: str, simple_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        # Handle status signals first (ERROR, INSUFFICIENT_DATA)
        if simple_signal in ['ERROR', 'INSUFFICIENT_DATA']:
            return simple_signal, 'NEUTRAL'
        
        # Granular: specific event or position
        if crossed_above:
            granular = 'BULLISH_CROSS'
        elif crossed_below:
            granular = 'BEARISH_CROSS'
        else:
            # Use position when no cross
            granular = current_position  # ABOVE_200EMA, BELOW_200EMA, or AT_200EMA
        
        # Simple: keep existing logic (BULLISH, BEARISH, NEUTRAL)
        simple = simple_signal
        
        return granular, simple
    
    def calculate_ema(self, close: pd.Series) -> pd.Series:
        """Calculate 200 EMA"""
        return close.ewm(span=self.period, adjust=False).mean()
    
    def calculate_slope(self, ema: pd.Series, lookback: int = 20) -> str:
        """
        Calculate 200 EMA slope for trend strength
        
        Args:
            ema: EMA series
            lookback: Periods for slope calculation
        """
        if len(ema) < lookback:
            return 'INSUFFICIENT_DATA'
        
        recent = ema.iloc[-lookback:]
        x = np.arange(len(recent))
        y = recent.values
        
        slope = np.polyfit(x, y, 1)[0]
        avg_price = y.mean()
        slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0
        
        if slope_pct > 0.02:
            return 'STRONG_UPTREND'
        elif slope_pct > 0.005:
            return 'UPTREND'
        elif slope_pct < -0.02:
            return 'STRONG_DOWNTREND'
        elif slope_pct < -0.005:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'
    
    def classify_position(self, price: float, ema: float) -> str:
        """Classify price position relative to 200 EMA (with threshold for AT_200EMA)"""
        # Use 0.5% threshold for "AT" (touching) detection
        distance_pct = abs((price - ema) / ema * 100)
        
        if distance_pct < self.btc_distance_thresholds['touching']:  # < 0.5%
            return 'AT_200EMA'
        elif price > ema:
            return 'ABOVE_200EMA'
        else:  # price < ema
            return 'BELOW_200EMA'
    
    def calculate_distance(self, price: float, ema: float) -> float:
        """Calculate percentage distance from 200 EMA"""
        return ((price - ema) / ema) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from 200 EMA"""
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['touching']:
            return 'TOUCHING'
        elif abs_dist < self.btc_distance_thresholds['near']:
            return 'NEAR'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        elif abs_dist < self.btc_distance_thresholds['extended']:
            return 'EXTENDED'
        else:
            return 'OVEREXTENDED'
    
    def determine_trend_filter(self, position: str, slope: str) -> str:
        """
        Determine trading bias based on 200 EMA
        
        Returns trade direction filter
        """
        if position == 'ABOVE_200EMA' and slope in ['UPTREND', 'STRONG_UPTREND']:
            return 'LONGS_ONLY'
        elif position == 'ABOVE_200EMA':
            return 'LONGS_PREFERRED'
        elif position == 'BELOW_200EMA' and slope in ['DOWNTREND', 'STRONG_DOWNTREND']:
            return 'SHORTS_ONLY'
        elif position == 'BELOW_200EMA':
            return 'SHORTS_PREFERRED'
        else:
            return 'NEUTRAL'
    
    def check_bullish_reversal_pattern(self, df: pd.DataFrame) -> bool:
        """
        Check for bullish reversal pattern (5 bars of higher highs + higher lows)
        after price crossed above 200 EMA
        
        Returns True if pattern confirmed
        """
        if len(df) < self.reversal_candles:
            return False
        
        recent_bars = df.iloc[-self.reversal_candles:]
        highs = recent_bars['high'].values
        lows = recent_bars['low'].values
        
        # Check for consistent higher highs and higher lows
        for i in range(1, len(highs)):
            if highs[i] <= highs[i-1] or lows[i] <= lows[i-1]:
                return False
        
        return True
    
    def check_bearish_reversal_pattern(self, df: pd.DataFrame) -> bool:
        """
        Check for bearish reversal pattern (5 bars of lower highs + lower lows)
        after price crossed below 200 EMA
        
        Returns True if pattern confirmed
        """
        if len(df) < self.reversal_candles:
            return False
        
        recent_bars = df.iloc[-self.reversal_candles:]
        highs = recent_bars['high'].values
        lows = recent_bars['low'].values
        
        # Check for consistent lower highs and lower lows
        for i in range(1, len(highs)):
            if highs[i] >= highs[i-1] or lows[i] >= lows[i-1]:
                return False
        
        return True
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method - IMPROVED FOR INSTITUTIONAL ACCURACY"""
        # Validate
        if 'close' not in df.columns:
            return {
                'signal': 'ERROR',
                'signal_simple': 'NEUTRAL',
                'confidence': 0,
                'metadata': {
                    'signal_simple': 'NEUTRAL',
                    'signal_granular': 'ERROR',
                    'error': 'Invalid data format'
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check minimum data
        min_required = self.period + 20
        if len(df) < min_required:
            granular_signal, simple_signal = self._determine_dual_signals('INSUFFICIENT_DATA')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'error': f'Need {min_required} periods, got {len(df)}'
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate 200 EMA
        ema = self.calculate_ema(df['close'])
        
        current_price = float(df['close'].iloc[-1])
        prev_price = float(df['close'].iloc[-2])
        current_ema = float(ema.iloc[-1])
        prev_ema = float(ema.iloc[-2])
        
        # Calculate slope
        slope = self.calculate_slope(ema, lookback=20)
        
        # Classify current and previous position for cross detection
        current_position = self.classify_position(current_price, current_ema)
        prev_position = self.classify_position(prev_price, prev_ema)
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, current_ema)
        distance_class = self.classify_distance(distance_pct)
        
        # Determine trend filter
        trend_filter = self.determine_trend_filter(current_position, slope)
        
        # INSTITUTIONAL IMPROVEMENT: Only signal on crossovers with strong confirmation
        signal = 'NEUTRAL'
        confidence = 70  # Base institutional confidence
        
        # Detect EMA cross events (AT_200EMA should not break cross detection)
        # Treat AT_200EMA as neutral - check if we crossed from below to above or vice versa
        crossed_above = (
            (prev_position == 'BELOW_200EMA' and current_position in ['ABOVE_200EMA', 'AT_200EMA']) or
            (prev_position == 'AT_200EMA' and current_position == 'ABOVE_200EMA' and prev_price < prev_ema)
        )
        crossed_below = (
            (prev_position == 'ABOVE_200EMA' and current_position in ['BELOW_200EMA', 'AT_200EMA']) or
            (prev_position == 'AT_200EMA' and current_position == 'BELOW_200EMA' and prev_price > prev_ema)
        )
        
        # Initialize reversal tracking variables
        reversal_confirmed = False
        reversal_type = None
        bars_monitored = 0
        
        # Check if we should start tracking a new reversal
        if crossed_above:
            self.tracking_bullish_reversal = True
            self.tracking_bearish_reversal = False
            self.reversal_bars_monitored = 0
            self.reversal_start_bar = len(df) - 1
        elif crossed_below:
            self.tracking_bearish_reversal = True
            self.tracking_bullish_reversal = False
            self.reversal_bars_monitored = 0
            self.reversal_start_bar = len(df) - 1
        
        # Check reversal pattern if we're tracking one
        if self.tracking_bullish_reversal and self.reversal_start_bar is not None:
            bars_since_cross = len(df) - self.reversal_start_bar
            bars_monitored = bars_since_cross
            
            if bars_since_cross >= self.reversal_candles:
                # Check if we have the reversal pattern
                reversal_confirmed = self.check_bullish_reversal_pattern(df)
                if reversal_confirmed:
                    reversal_type = 'bullish_continuation'
                    self.tracking_bullish_reversal = False  # Stop tracking
                elif bars_since_cross > self.reversal_candles + 5:
                    # Pattern failed, stop tracking
                    self.tracking_bullish_reversal = False
        
        elif self.tracking_bearish_reversal and self.reversal_start_bar is not None:
            bars_since_cross = len(df) - self.reversal_start_bar
            bars_monitored = bars_since_cross
            
            if bars_since_cross >= self.reversal_candles:
                # Check if we have the reversal pattern
                reversal_confirmed = self.check_bearish_reversal_pattern(df)
                if reversal_confirmed:
                    reversal_type = 'bearish_continuation'
                    self.tracking_bearish_reversal = False  # Stop tracking
                elif bars_since_cross > self.reversal_candles + 5:
                    # Pattern failed, stop tracking
                    self.tracking_bearish_reversal = False
        
        # Build confluence
        confluence_factors = []
        
        # Only signal on MAJOR events with strong confirmation
        if crossed_above and slope in ['UPTREND', 'STRONG_UPTREND']:
            # Bullish cross with uptrending 200 EMA
            signal = 'BULLISH'
            confidence = 85
            confluence_factors.append('📈 BULLISH CROSS: Price crossed above 200 EMA')
            confluence_factors.append('✅ 200 EMA slope confirms uptrend')
            
            if slope == 'STRONG_UPTREND':
                confidence = 95
                confluence_factors.append('⚡ STRONG uptrend - high conviction')
            
        elif crossed_below and slope in ['DOWNTREND', 'STRONG_DOWNTREND']:
            # Bearish cross with downtrending 200 EMA
            signal = 'BEARISH'
            confidence = 85
            confluence_factors.append('📉 BEARISH CROSS: Price crossed below 200 EMA')
            confluence_factors.append('✅ 200 EMA slope confirms downtrend')
            
            if slope == 'STRONG_DOWNTREND':
                confidence = 95
                confluence_factors.append('⚡ STRONG downtrend - high conviction')
                
        elif crossed_above:
            # Bullish cross but EMA not strongly trending
            signal = 'BULLISH'
            confidence = 70
            confluence_factors.append('📈 Price crossed above 200 EMA')
            confluence_factors.append('⚠️  200 EMA slope weak - lower conviction')
            
        elif crossed_below:
            # Bearish cross but EMA not strongly trending
            signal = 'BEARISH'
            confidence = 70
            confluence_factors.append('📉 Price crossed below 200 EMA')
            confluence_factors.append('⚠️  200 EMA slope weak - lower conviction')
        
        # Status information (only if no cross)
        if signal == 'NEUTRAL':
            if current_position == 'ABOVE_200EMA':
                confluence_factors.append('Price above 200 EMA - long-term bullish bias')
            elif current_position == 'BELOW_200EMA':
                confluence_factors.append('Price below 200 EMA - long-term bearish bias')
            
            confluence_factors.append(f'Distance from 200 EMA: {distance_pct:+.2f}% ({distance_class})')
            confluence_factors.append('No cross event - holding position')
        
        # Add reversal pattern confirmation
        if reversal_confirmed and reversal_type == 'bullish_continuation':
            # Boost confidence for confirmed bullish reversal
            if signal == 'BULLISH' or current_position == 'ABOVE_200EMA':
                confidence = min(95, confidence + 10)
                confluence_factors.append('⭐ 5-bar bullish continuation confirmed!')
                
        elif reversal_confirmed and reversal_type == 'bearish_continuation':
            # Boost confidence for confirmed bearish reversal
            if signal == 'BEARISH' or current_position == 'BELOW_200EMA':
                confidence = min(95, confidence + 10)
                confluence_factors.append('⭐ 5-bar bearish continuation confirmed!')
        
        # Add slope context
        if slope == 'STRONG_UPTREND':
            confluence_factors.append('200 EMA strongly rising')
        elif slope == 'UPTREND':
            confluence_factors.append('200 EMA rising')
        elif slope == 'STRONG_DOWNTREND':
            confluence_factors.append('200 EMA strongly falling')
        elif slope == 'DOWNTREND':
            confluence_factors.append('200 EMA falling')
        elif slope == 'SIDEWAYS':
            confluence_factors.append('200 EMA flat - ranging market')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(
            crossed_above, crossed_below, current_position, signal
        )
        
        # Metadata
        metadata = {
            'ema_200': round(current_ema, 2),
            'current_price': round(current_price, 2),
            'current_position': current_position,
            'prev_position': prev_position,
            'crossed_above': crossed_above,
            'crossed_below': crossed_below,
            'slope': slope,
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'trend_filter': trend_filter,
            'period': self.period,
            'is_overextended': distance_class == 'OVEREXTENDED',
            # Reversal pattern tracking
            'reversal_continuation': reversal_confirmed,
            'reversal_type': reversal_type if reversal_confirmed else None,
            'reversal_candles': self.reversal_candles,
            'bars_monitored': bars_monitored,
            # DUAL SIGNAL ARCHITECTURE
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
        }
        
        return {
            'signal': granular_signal,  # Granular signal (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=250, freq='15min')
    np.random.seed(42)
    base = 45000
    trend = np.linspace(0, 5000, 250)
    data = pd.DataFrame({
        'timestamp': dates,
        'close': base + trend + np.random.randn(250).cumsum() * 100,
        'open': base + trend,
        'high': base + trend + 200,
        'low': base + trend - 200,
        'volume': np.random.uniform(100, 1000, 250)
    })
    
    ema200 = EMA200Trend()
    result = ema200.analyze(data)
    
    logger.info("=" * 80)
    logger.info("200 EMA TREND FILTER - TEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Signal: {result['signal']}")
    logger.info(f"Confidence: {result['confidence']}%")
    logger.info(f"\n200 EMA Analysis:")
    logger.info(f"  200 EMA: ${result['metadata']['ema_200']:.2f}")
    logger.info(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    logger.info(f"  Position: {result['metadata']['position']}")
    logger.info(f"  Slope: {result['metadata']['slope']}")
    logger.info(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    logger.info(f"  Trend Filter: {result['metadata']['trend_filter']}")
    logger.info(f"  Overextended: {result['metadata']['is_overextended']}")
    logger.info(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        logger.info(f"  - {factor}")
    logger.info("=" * 80)
