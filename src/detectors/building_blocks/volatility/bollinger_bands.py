"""
Bollinger Bands Building Block
Category: Volatility Indicators
Purpose: Volatility indicator using standard deviations around moving average
"""
"""
Building Block Classification: HYBRID BLOCK
Mode: CONTINUOUS + EVENT
Purpose: Continuous band state + squeeze/expansion events

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List, Optional, Tuple

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np

import logging
logger = logging.getLogger(__name__)

@register_block(
    name='bollinger_bands',
    category='VOLATILITY',
    class_name='BollingerBands',
    default_weight=10,
    valid_signals=[
        # Granular BB position signals
        'ABOVE_UPPER', 'NEAR_UPPER', 'UPPER_HALF', 'LOWER_HALF', 'NEAR_LOWER', 'BELOW_LOWER',
        # Granular BB pattern signals
        'BULLISH_REVERSAL', 'BEARISH_REVERSAL', 'UPPER_BAND_WALK', 'LOWER_BAND_WALK',
        # Granular BB squeeze signals
        'SQUEEZE_BREAKOUT_BULL', 'SQUEEZE_BREAKOUT_BEAR',
        # Granular volatility regime signals
        'MEDIUM_HIGH', 'MEDIUM_LOW',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Position signals
        'ABOVE_UPPER': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Above upper band - Price extended beyond upper Bollinger Band. Overbought. Consider shorts or take profit on longs. Mean reversion likely.'
        },
        'NEAR_UPPER': {
                'base_points': 9,
                'formula': 'scaled',
                'description': 'Near upper band - Price approaching upper band. Strong uptrend. Momentum favors longs but watch for reversal. Consider partial profits.'
        },
        'UPPER_HALF': {
                'base_points': 7,
                'formula': 'scaled',
                'description': 'Upper half - Price in upper half of bands. Bullish bias. Above middle band. Trend strength moderate. Continue longs.'
        },
        'LOWER_HALF': {
                'base_points': 7,
                'formula': 'scaled',
                'description': 'Lower half - Price in lower half of bands. Bearish bias. Below middle band. Trend weakness. Consider shorts or wait.'
        },
        'NEAR_LOWER': {
                'base_points': 9,
                'formula': 'scaled',
                'description': 'Near lower band - Price approaching lower band. Strong downtrend or oversold. Watch for reversal. Potential long entries forming.'
        },
        'BELOW_LOWER': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Below lower band - Price extended beyond lower Bollinger Band. Oversold. Consider longs or take profit on shorts. Mean reversion likely.'
        },
        
        # Pattern signals
        'BULLISH_REVERSAL': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Bullish reversal - Price bounced from lower band. Reversal signal. Enter longs. Stop below recent low. Target middle or upper band.'
        },
        'BEARISH_REVERSAL': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Bearish reversal - Price rejected from upper band. Reversal signal. Enter shorts. Stop above recent high. Target middle or lower band.'
        },
        'UPPER_BAND_WALK': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Upper band walk - Price riding upper band. Strong bullish trend. Stay in longs. Trend continuation pattern. Exit on close below middle band.'
        },
        'LOWER_BAND_WALK': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Lower band walk - Price riding lower band. Strong bearish trend. Stay in shorts. Trend continuation pattern. Exit on close above middle band.'
        },
        
        # Squeeze signals
        'SQUEEZE_BREAKOUT_BULL': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Bullish squeeze breakout - Squeeze broken upward. Enter longs aggressively. Strong momentum expected. Volatility expansion bullish.'
        },
        'SQUEEZE_BREAKOUT_BEAR': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Bearish squeeze breakout - Squeeze broken downward. Enter shorts aggressively. Strong momentum expected. Volatility expansion bearish.'
        },
        
        # Volatility regime
        'MEDIUM_HIGH': {
                'base_points': 8,
                'formula': 'scaled',
                'description': 'Medium-high volatility - Bollinger bands widening. Volatility increasing. Good for trend trading. Wider stops required.'
        },
        'MEDIUM_LOW': {
                'base_points': 8,
                'formula': 'scaled',
                'description': 'Medium-low volatility - Bollinger bands narrowing. Volatility decreasing. Consolidation phase. Watch for squeeze breakout.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Bullish - Price action bullish vs Bollinger Bands. Long positions favorable. Trend or reversal favors upside.'
        },
        'BEARISH': {
                'base_points': 10,
                'formula': 'scaled',
                'description': 'Bearish - Price action bearish vs Bollinger Bands. Short positions favorable. Trend or reversal favors downside.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Neutral - Price near middle band. No clear bias. Wait for directional signal before trading.'
        }
}
)
class BollingerBands:
    """
    Bollinger Bands - Volatility Indicator
    
    Uses standard deviations around a moving average to identify overbought/oversold
    conditions, volatility expansion/contraction, and potential reversal patterns.
    
    Created by John Bollinger, Bollinger Bands consist of:
    - Middle Band: Simple Moving Average (typically 20 periods)
    - Upper Band: SMA + (Standard Deviation × Multiplier)
    - Lower Band: SMA - (Standard Deviation × Multiplier)
    
    Parameters:
        period: SMA calculation period (default: 20)
        std_dev: Standard deviation multiplier (default: 2.0)
        timeframe: Timeframe string (e.g., '15min', '1hr', '4hr', '1D')
    
    Returns:
        Standardized dict with band values, position, squeeze detection, and patterns
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0, timeframe: str = '15min', **kwargs):
        """
        Initialize Bollinger Bands block with parameters
        
        Args:
            period: SMA calculation period (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)
            timeframe: Timeframe for the data
        """
        self.period = period
        self.std_dev = std_dev
        self.timeframe = timeframe
        
        # Squeeze detection thresholds (band width as percentage of price)
        self.squeeze_thresholds = {
            '15min': {'tight': 0.5, 'normal': 1.5, 'wide': 3.0},
            '1hr': {'tight': 0.8, 'normal': 2.0, 'wide': 4.0},
            '4hr': {'tight': 1.0, 'normal': 2.5, 'wide': 5.0},
            '1D': {'tight': 1.5, 'normal': 3.5, 'wide': 7.0},
        }
    
    def _determine_dual_signals(self, signal: str, percent_b: float, 
                                squeeze_breakout: Dict, w_bottom: bool, m_top: bool) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        granular = signal
        simple = self.map_to_simple_signal(signal, percent_b, squeeze_breakout, w_bottom, m_top)
        return granular, simple
    
    def calculate_bands(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands (Upper, Middle, Lower)
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band) Series
        """
        # Middle band is Simple Moving Average
        middle_band = df['close'].rolling(window=self.period).mean()
        
        # Calculate standard deviation
        std = df['close'].rolling(window=self.period).std()
        
        # Upper and lower bands
        upper_band = middle_band + (std * self.std_dev)
        lower_band = middle_band - (std * self.std_dev)
        
        return upper_band, middle_band, lower_band
    
    def calculate_band_width(self, upper: pd.Series, lower: pd.Series, middle: pd.Series) -> pd.Series:
        """
        Calculate Bollinger Band Width
        
        Band Width = (Upper Band - Lower Band) / Middle Band
        Used to identify squeeze (low volatility) and expansion (high volatility)
        
        Args:
            upper: Upper band series
            lower: Lower band series
            middle: Middle band series
            
        Returns:
            Band width as percentage
        """
        return ((upper - lower) / middle) * 100
    
    def calculate_percent_b(self, close: pd.Series, upper: pd.Series, lower: pd.Series) -> pd.Series:
        """
        Calculate %B (Percent B)
        
        %B = (Close - Lower Band) / (Upper Band - Lower Band)
        - %B > 1.0: Price above upper band (overbought)
        - %B < 0.0: Price below lower band (oversold)
        - %B = 0.5: Price at middle band
        
        Args:
            close: Close price series
            upper: Upper band series
            lower: Lower band series
            
        Returns:
            %B values
        """
        return (close - lower) / (upper - lower)
    
    def detect_squeeze(self, band_width: float, price: float) -> str:
        """
        Detect Bollinger Squeeze (low volatility before breakout)
        
        Args:
            band_width: Current band width percentage
            price: Current price
            
        Returns:
            Squeeze classification
        """
        thresholds = self.squeeze_thresholds.get(
            self.timeframe,
            self.squeeze_thresholds['15min']
        )
        
        if band_width < thresholds['tight']:
            return 'TIGHT_SQUEEZE'
        elif band_width < thresholds['normal']:
            return 'NORMAL'
        elif band_width < thresholds['wide']:
            return 'EXPANDING'
        else:
            return 'WIDE'
    
    def detect_squeeze_breakout(self, band_width_series: pd.Series, 
                                close_series: pd.Series, 
                                upper_series: pd.Series,
                                lower_series: pd.Series,
                                lookback: int = 10) -> Dict[str, Any]:
        """
        Detect Bollinger Squeeze Breakout
        
        A squeeze breakout occurs when:
        1. Band width was in TIGHT_SQUEEZE recently
        2. Band width is now expanding
        3. Price breaks decisively through upper or lower band
        
        Args:
            band_width_series: Series of band width values
            close_series: Series of close prices
            upper_series: Series of upper band values
            lower_series: Series of lower band values
            lookback: Periods to look back for squeeze
            
        Returns:
            Dictionary with breakout status and details
        """
        if len(band_width_series) < lookback:
            return {
                'breakout_detected': False,
                'breakout_direction': None,
                'squeeze_duration': 0,
                'breakout_strength': 0.0
            }
        
        # Get thresholds
        thresholds = self.squeeze_thresholds.get(
            self.timeframe,
            self.squeeze_thresholds['15min']
        )
        
        # Check recent band widths
        recent_widths = band_width_series.iloc[-lookback:].values
        current_width = band_width_series.iloc[-1]
        
        # Was there a squeeze recently?
        squeeze_count = sum(recent_widths < thresholds['tight'])
        
        if squeeze_count < 3:  # Need at least 3 periods in squeeze
            return {
                'breakout_detected': False,
                'breakout_direction': None,
                'squeeze_duration': 0,
                'breakout_strength': 0.0
            }
        
        # Check if bands are expanding now
        width_change = current_width - recent_widths[-2]
        is_expanding = width_change > 0 and current_width > thresholds['tight']
        
        if not is_expanding:
            return {
                'breakout_detected': False,
                'breakout_direction': 'PENDING',
                'squeeze_duration': squeeze_count,
                'breakout_strength': 0.0
            }
        
        # Determine breakout direction
        current_price = close_series.iloc[-1]
        current_upper = upper_series.iloc[-1]
        current_lower = lower_series.iloc[-1]
        band_range = current_upper - current_lower
        
        # Bullish breakout: price breaks above upper band
        if current_price > current_upper:
            breakout_strength = ((current_price - current_upper) / band_range) * 100
            return {
                'breakout_detected': True,
                'breakout_direction': 'BULLISH',
                'squeeze_duration': squeeze_count,
                'breakout_strength': round(breakout_strength, 2)
            }
        
        # Bearish breakout: price breaks below lower band
        elif current_price < current_lower:
            breakout_strength = ((current_lower - current_price) / band_range) * 100
            return {
                'breakout_detected': True,
                'breakout_direction': 'BEARISH',
                'squeeze_duration': squeeze_count,
                'breakout_strength': round(breakout_strength, 2)
            }
        
        # Bands expanding but price still in range
        else:
            return {
                'breakout_detected': False,
                'breakout_direction': 'PENDING',
                'squeeze_duration': squeeze_count,
                'breakout_strength': 0.0
            }
    
    def detect_band_walk(self, percent_b: pd.Series, lookback: int = 5) -> str:
        """
        Detect 'Band Walk' - when price consistently stays near band edge in trending market
        
        Args:
            percent_b: %B values series
            lookback: Periods to check
            
        Returns:
            Band walk status
        """
        if len(percent_b) < lookback:
            return 'INSUFFICIENT_DATA'
        
        recent_b = percent_b.iloc[-lookback:].values
        
        # Upper band walk (strong uptrend)
        if np.mean(recent_b > 0.8) >= 0.6:  # 60%+ of time above 0.8
            return 'UPPER_BAND_WALK'
        
        # Lower band walk (strong downtrend)
        if np.mean(recent_b < 0.2) >= 0.6:  # 60%+ of time below 0.2
            return 'LOWER_BAND_WALK'
        
        return 'NO_WALK'
    
    def detect_w_bottom(self, df: pd.DataFrame, lower_band: pd.Series, middle_band: pd.Series, lookback: int = 20) -> bool:
        """
        Detect W-Bottom pattern (bullish reversal) - INSTITUTIONAL GRADE
        
        TRUE W-Bottom criteria (STRICT):
        - First low penetrates lower band
        - Rally toward middle
        - Second low holds ABOVE first low (bullish divergence - KEY!)
        - Price breaking UP from second low
        - Must be in downtrend/neutral context (price below middle)
        
        Args:
            df: OHLCV DataFrame
            lower_band: Lower band series
            middle_band: Middle band series
            lookback: Periods to search for pattern
            
        Returns:
            True if W-Bottom detected
        """
        if len(df) < lookback:
            return False
        
        # FIXED: Proper W-Bottom structure detection
        recent_data = df.iloc[-lookback:]
        recent_lower = lower_band.iloc[-lookback:]
        recent_middle = middle_band.iloc[-lookback:]
        
        lows = recent_data['low'].values
        closes = recent_data['close'].values
        lower_vals = recent_lower.values
        current_price = closes[-1]
        current_middle = recent_middle.values[-1]
        
        # FILTER 1: Only valid in downtrend/neutral (price below/at middle)
        if current_price > current_middle * 1.02:  # More than 2% above middle = uptrend
            return False
        
        # FILTER 2: Find touches to lower band
        touches_lower = closes < (lower_vals * 1.01)  # Within 1% of lower band
        touch_indices = np.where(touches_lower)[0]
        
        if len(touch_indices) < 2:  # Need at least 2 touches
            return False
        
        # FILTER 3: Check for W-structure (second low higher than first)
        first_touch_idx = touch_indices[0]
        last_touch_idx = touch_indices[-1]
        
        first_low = lows[first_touch_idx]
        second_low = lows[last_touch_idx]
        
        # CRITICAL: Second low must be higher (bullish divergence)
        if second_low <= first_low:
            return False  # Not a W - second low failed to hold
        
        # FILTER 4: Must have rallied between touches (to create W shape)
        between_highs = recent_data['high'].iloc[first_touch_idx:last_touch_idx+1].values
        if len(between_highs) > 2:
            rally_high = np.max(between_highs)
            # Rally must reach at least middle band
            middle_between = recent_middle.values[first_touch_idx:last_touch_idx+1].mean()
            if rally_high < middle_between * 0.98:  # Didn't rally enough
                return False
        
        # FILTER 5: Price must be breaking UP from second low (confirmation)
        if current_price < second_low * 1.005:  # Need 0.5% above second low minimum
            return False  # Not confirmed yet
        
        # All filters passed = TRUE W-Bottom!
        return True
    
    def detect_m_top(self, df: pd.DataFrame, upper_band: pd.Series, middle_band: pd.Series, lookback: int = 20) -> bool:
        """
        Detect M-Top pattern (bearish reversal) - INSTITUTIONAL GRADE
        
        TRUE M-Top criteria (STRICT):
        - First high penetrates upper band
        - Pullback toward middle
        - Second high holds BELOW first high (bearish divergence - KEY!)
        - Price breaking DOWN from second high
        - Must be in uptrend/neutral context (price above middle)
        
        Args:
            df: OHLCV DataFrame
            upper_band: Upper band series
            middle_band: Middle band series
            lookback: Periods to search for pattern
            
        Returns:
            True if M-Top detected
        """
        if len(df) < lookback:
            return False
        
        # FIXED: Proper M-Top structure detection
        recent_data = df.iloc[-lookback:]
        recent_upper = upper_band.iloc[-lookback:]
        recent_middle = middle_band.iloc[-lookback:]
        
        highs = recent_data['high'].values
        closes = recent_data['close'].values
        upper_vals = recent_upper.values
        current_price = closes[-1]
        current_middle = recent_middle.values[-1]
        
        # FILTER 1: Only valid in uptrend/neutral (price above/at middle)
        if current_price < current_middle * 0.98:  # More than 2% below middle = downtrend
            return False
        
        # FILTER 2: Find touches to upper band
        touches_upper = closes > (upper_vals * 0.99)  # Within 1% of upper band
        touch_indices = np.where(touches_upper)[0]
        
        if len(touch_indices) < 2:  # Need at least 2 touches
            return False
        
        # FILTER 3: Check for M-structure (second high lower than first)
        first_touch_idx = touch_indices[0]
        last_touch_idx = touch_indices[-1]
        
        first_high = highs[first_touch_idx]
        second_high = highs[last_touch_idx]
        
        # CRITICAL: Second high must be lower (bearish divergence)
        if second_high >= first_high:
            return False  # Not an M - second high failed to reject
        
        # FILTER 4: Must have pulled back between touches (to create M shape)
        between_lows = recent_data['low'].iloc[first_touch_idx:last_touch_idx+1].values
        if len(between_lows) > 2:
            pullback_low = np.min(between_lows)
            # Pullback must reach at least middle band
            middle_between = recent_middle.values[first_touch_idx:last_touch_idx+1].mean()
            if pullback_low > middle_between * 1.02:  # Didn't pull back enough
                return False
        
        # FILTER 5: Price must be breaking DOWN from second high (confirmation)
        if current_price > second_high * 0.995:  # Need 0.5% below second high minimum
            return False  # Not confirmed yet
        
        # All filters passed = TRUE M-Top!
        return True
    
    def classify_position(self, percent_b: float) -> str:
        """
        Classify price position relative to bands
        
        Args:
            percent_b: Current %B value
            
        Returns:
            Position classification
        """
        if percent_b > 1.0:
            return 'ABOVE_UPPER'
        elif percent_b > 0.8:
            return 'NEAR_UPPER'
        elif percent_b > 0.6:
            return 'UPPER_HALF'
        elif percent_b > 0.4:
            return 'LOWER_HALF'
        elif percent_b > 0.2:
            return 'NEAR_LOWER'
        else:
            return 'BELOW_LOWER'
    
    def calculate_variable_confidence(self, signal: str) -> float:
        """
        ENHANCEMENT (2026-01-04): Calculate variable confidence based on signal type
        
        Differentiates signal quality:
        - Squeeze breakouts = highest confidence (rare, high-value)
        - Reversals = high confidence (pattern-based signals)
        - Extremes = elevated confidence (outside bands)
        - Near extremes = moderate-high confidence (approaching bands)
        - Neutral positions = baseline confidence (inside bands)
        
        Args:
            signal: Signal classification
            
        Returns:
            Confidence score (75-100%)
        """
        if 'SQUEEZE_BREAKOUT' in signal:
            return 100  # Highest - documented +20 confluence points
        elif 'REVERSAL' in signal:
            return 90   # High - pattern-based, documented +15 confluence
        elif signal in ['ABOVE_UPPER', 'BELOW_LOWER']:
            return 85   # Extreme positions - outside bands
        elif signal in ['NEAR_UPPER', 'NEAR_LOWER']:
            return 80   # Approaching extremes
        else:  # UPPER_HALF, LOWER_HALF
            return 75   # Neutral positions - inside bands
    
    def map_to_simple_signal(self, signal: str, percent_b: float, 
                            squeeze_breakout: Dict, w_bottom: bool, m_top: bool) -> str:
        """
        EXPANSION: Map complex Bollinger signals to simple directional signals
        
        This maintains ALL original functionality while adding validator compatibility.
        Original 'signal' field is unchanged - this creates a NEW 'simple_signal' field.
        
        Args:
            signal: Original complex signal
            percent_b: Current %B value
            squeeze_breakout: Squeeze breakout detection dict
            w_bottom: W-bottom pattern detected
            m_top: M-top pattern detected
            
        Returns:
            Simple directional signal: BULLISH, BEARISH, or NEUTRAL
        """
        # Priority 1: Squeeze breakouts (strongest signals)
        if 'SQUEEZE_BREAKOUT_BULL' in signal:
            return 'BULLISH'
        if 'SQUEEZE_BREAKOUT_BEAR' in signal:
            return 'BEARISH'
        
        # Priority 2: Reversal patterns
        if 'BULLISH_REVERSAL' in signal or w_bottom:
            return 'BULLISH'
        if 'BEARISH_REVERSAL' in signal or m_top:
            return 'BEARISH'
        
        # Priority 3: Extreme positions (oversold/overbought)
        if signal in ['BELOW_LOWER']:  # Oversold = bullish opportunity
            return 'BULLISH'
        if signal in ['ABOVE_UPPER']:  # Overbought = bearish opportunity
            return 'BEARISH'
        
        # Priority 4: Near extremes
        if signal in ['NEAR_LOWER']:
            return 'BULLISH'
        if signal in ['NEAR_UPPER']:
            return 'BEARISH'
        
        # Default: Use %B to determine bias
        if percent_b > 0.5:
            return 'BULLISH'  # Above middle = bullish bias
        elif percent_b < 0.5:
            return 'BEARISH'  # Below middle = bearish bias
        else:
            return 'NEUTRAL'  # At equilibrium
    
    def classify_volatility_regime(self, band_width_series: pd.Series, lookback: int = 50) -> Dict[str, Any]:
        """
        Classify current volatility regime based on historical band width percentiles
        
        This helps traders adapt their strategy to market conditions:
        - LOW: Consolidation phase, expect breakout soon
        - MEDIUM: Normal volatility, standard strategies work
        - HIGH: Increased volatility, widen stops
        - EXTREME: Very high volatility, reduce position size or stay out
        
        Args:
            band_width_series: Historical band width values
            lookback: Periods to analyze for percentile calculation
            
        Returns:
            Dictionary with regime classification and percentile rank
        """
        if len(band_width_series) < lookback:
            return {
                'regime': 'INSUFFICIENT_DATA',
                'percentile_rank': 0.0,
                'current_bandwidth': 0.0,
                'historical_median': 0.0,
                'historical_std': 0.0
            }
        
        # Get historical bandwidth values
        historical_widths = band_width_series.iloc[-lookback:].values
        current_width = band_width_series.iloc[-1]
        
        # Calculate percentile rank (where current width ranks in history)
        percentile_rank = (np.sum(historical_widths < current_width) / len(historical_widths)) * 100
        
        # Calculate historical statistics
        historical_median = np.median(historical_widths)
        historical_std = np.std(historical_widths)
        
        # Classify regime based on percentile
        if percentile_rank < 20:
            regime = 'LOW'  # Bottom 20% - very tight range, breakout imminent
        elif percentile_rank < 50:
            regime = 'MEDIUM_LOW'  # 20-50% - below average volatility
        elif percentile_rank < 80:
            regime = 'MEDIUM_HIGH'  # 50-80% - above average volatility
        elif percentile_rank < 95:
            regime = 'HIGH'  # 80-95% - high volatility
        else:
            regime = 'EXTREME'  # Top 5% - extreme volatility
        
        return {
            'regime': regime,
            'percentile_rank': round(percentile_rank, 2),
            'current_bandwidth': round(current_width, 2),
            'historical_median': round(historical_median, 2),
            'historical_std': round(historical_std, 2),
            'z_score': round((current_width - historical_median) / historical_std, 2) if historical_std > 0 else 0.0
        }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method for Bollinger Bands - tracks CONTINUOUS multi-state and STATE CHANGES
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            **kwargs: Additional parameters:
                - lookback_walk: Periods for band walk detection (default: 5)
                - lookback_pattern: Periods for pattern detection (default: 20)
        
        Returns:
            {
                'signal': str,  # Complex multi-state signal
                'confidence': float,  # 0-100 confidence score
                'metadata': dict,  # Band values, patterns, is_new_event
                'timestamp': datetime,
                'timeframe': str,
                'confluence_factors': list
            }
        """
        # Validate input data
        if not self.validate_data(df):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Invalid data format', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Need minimum periods for calculation
        if len(df) < self.period:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {
                    'error': f'Need at least {self.period} periods, got {len(df)}',
                    'required_periods': self.period,
                    'provided_periods': len(df)
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate Bollinger Bands
        upper, middle, lower = self.calculate_bands(df)
        
        # Get current values
        current_price = float(df['close'].iloc[-1])
        current_upper = float(upper.iloc[-1])
        current_middle = float(middle.iloc[-1])
        current_lower = float(lower.iloc[-1])
        
        # Calculate band width and %B
        band_width_series = self.calculate_band_width(upper, lower, middle)
        percent_b_series = self.calculate_percent_b(df['close'], upper, lower)
        
        current_band_width = float(band_width_series.iloc[-1])
        current_percent_b = float(percent_b_series.iloc[-1])
        
        # Get parameters
        lookback_walk = kwargs.get('lookback_walk', 5)
        lookback_pattern = kwargs.get('lookback_pattern', 20)
        
        # Detect squeeze
        squeeze_status = self.detect_squeeze(current_band_width, current_price)
        
        # Detect squeeze breakout
        squeeze_breakout = self.detect_squeeze_breakout(
            band_width_series, df['close'], upper, lower, lookback=10
        )
        
        # Detect band walk
        band_walk = self.detect_band_walk(percent_b_series, lookback_walk)
        
        # Detect patterns (FIXED: Pass middle_band for trend filtering)
        w_bottom = self.detect_w_bottom(df, lower, middle, lookback_pattern)
        m_top = self.detect_m_top(df, upper, middle, lookback_pattern)
        
        # Classify volatility regime
        volatility_regime = self.classify_volatility_regime(band_width_series, lookback=50)
        
        # Classify position
        position = self.classify_position(current_percent_b)
        
        # Build confluence factors
        confluence_factors = []
        
        if position in ['ABOVE_UPPER', 'NEAR_UPPER']:
            confluence_factors.append('Price at/above upper band - overbought potential')
        elif position in ['BELOW_LOWER', 'NEAR_LOWER']:
            confluence_factors.append('Price at/below lower band - oversold potential')
        
        if squeeze_status == 'TIGHT_SQUEEZE':
            confluence_factors.append('Bollinger Squeeze detected - breakout imminent')
        elif squeeze_status == 'EXPANDING':
            confluence_factors.append('Bands expanding - volatility increasing')
        
        if band_walk == 'UPPER_BAND_WALK':
            confluence_factors.append('Upper band walk - strong uptrend')
        elif band_walk == 'LOWER_BAND_WALK':
            confluence_factors.append('Lower band walk - strong downtrend')
        
        if w_bottom:
            confluence_factors.append('W-Bottom pattern detected - bullish reversal signal')
        if m_top:
            confluence_factors.append('M-Top pattern detected - bearish reversal signal')
        
        # Add squeeze breakout confluence
        if squeeze_breakout['breakout_detected']:
            direction = squeeze_breakout['breakout_direction']
            strength = squeeze_breakout['breakout_strength']
            duration = squeeze_breakout['squeeze_duration']
            confluence_factors.append(
                f"SQUEEZE BREAKOUT: {direction} breakout detected (strength: {strength}%, squeeze duration: {duration} periods)"
            )
        elif squeeze_breakout['breakout_direction'] == 'PENDING':
            confluence_factors.append(
                f"Squeeze breakout pending - {squeeze_breakout['squeeze_duration']} periods in squeeze"
            )
        
        # Add volatility regime confluence
        if volatility_regime['regime'] != 'INSUFFICIENT_DATA':
            regime = volatility_regime['regime']
            percentile = volatility_regime['percentile_rank']
            
            if regime == 'LOW':
                confluence_factors.append(f"Volatility regime: {regime} ({percentile}th percentile) - Consolidation, breakout expected")
            elif regime == 'EXTREME':
                confluence_factors.append(f"Volatility regime: {regime} ({percentile}th percentile) - Extreme volatility, reduce position size")
            elif regime in ['HIGH', 'MEDIUM_HIGH']:
                confluence_factors.append(f"Volatility regime: {regime} ({percentile}th percentile) - Elevated volatility, widen stops")
            else:
                confluence_factors.append(f"Volatility regime: {regime} ({percentile}th percentile) - Normal conditions")
        
        # Determine signal - PRIORITY ORDER
        # Priority 1: Squeeze breakout (highest priority - rare events)
        if squeeze_breakout['breakout_detected']:
            # Squeeze breakout takes priority as it's a strong signal
            if squeeze_breakout['breakout_direction'] == 'BULLISH':
                signal = 'SQUEEZE_BREAKOUT_BULL'
            else:  # Must be BEARISH
                signal = 'SQUEEZE_BREAKOUT_BEAR'
        
        # Priority 2: Band walk (strong trending behavior)
        elif band_walk == 'UPPER_BAND_WALK':
            signal = 'UPPER_BAND_WALK'
        elif band_walk == 'LOWER_BAND_WALK':
            signal = 'LOWER_BAND_WALK'
        
        # Priority 3: Reversal patterns
        elif w_bottom:
            signal = 'BULLISH_REVERSAL'
        elif m_top:
            signal = 'BEARISH_REVERSAL'
        
        # Priority 4: Volatility regime signals (when no other patterns present)
        elif volatility_regime['regime'] == 'MEDIUM_HIGH':
            signal = 'MEDIUM_HIGH'
        elif volatility_regime['regime'] == 'MEDIUM_LOW':
            signal = 'MEDIUM_LOW'
        
        # Priority 5: Position-based signals
        elif position == 'UPPER_HALF' and current_percent_b >= 0.49 and current_percent_b <= 0.51:
            # Very close to middle band = neutral
            signal = 'NEUTRAL'
        elif position == 'LOWER_HALF' and current_percent_b >= 0.49 and current_percent_b <= 0.51:
            # Very close to middle band = neutral
            signal = 'NEUTRAL'
        else:
            # Default to position-based classification
            signal = position
        
        # ENHANCEMENT: Calculate variable confidence based on signal type
        confidence = self.calculate_variable_confidence(signal)
        
        # **NEW:** Event tracking - detect multi-state SIGNAL CHANGES
        is_new_event = False
        bars_in_state = 0
        
        # Check if signal state changed
        if len(df) > self.period + 1:
            # Calculate previous bar's signal
            prev_df = df.iloc[:-1]
            prev_upper, prev_middle, prev_lower = self.calculate_bands(prev_df)
            prev_band_width_series = self.calculate_band_width(prev_upper, prev_lower, prev_middle)
            prev_percent_b_series = self.calculate_percent_b(prev_df['close'], prev_upper, prev_lower)
            
            prev_percent_b = float(prev_percent_b_series.iloc[-1])
            prev_position = self.classify_position(prev_percent_b)
            
            prev_squeeze_breakout = self.detect_squeeze_breakout(
                prev_band_width_series, prev_df['close'], prev_upper, prev_lower, lookback=10
            )
            prev_w_bottom = self.detect_w_bottom(prev_df, prev_lower, prev_middle, lookback_pattern)
            prev_m_top = self.detect_m_top(prev_df, prev_upper, prev_middle, lookback_pattern)
            
            # Determine previous signal
            if prev_squeeze_breakout['breakout_detected']:
                if prev_squeeze_breakout['breakout_direction'] == 'BULLISH':
                    prev_signal = 'SQUEEZE_BREAKOUT_BULL'
                elif prev_squeeze_breakout['breakout_direction'] == 'BEARISH':
                    prev_signal = 'SQUEEZE_BREAKOUT_BEAR'
                else:
                    prev_signal = prev_position
            elif prev_w_bottom:
                prev_signal = 'BULLISH_REVERSAL'
            elif prev_m_top:
                prev_signal = 'BEARISH_REVERSAL'
            else:
                prev_signal = prev_position
            
            # Detect state change
            is_new_event = (signal != prev_signal)
            
            # If not changed, approximate bars in state
            if not is_new_event:
                bars_in_state = 1  # At least 1 bar in current state
        
        # Fresh state change boost
        if is_new_event:
            confidence = min(100, confidence + 5)
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal, current_percent_b, squeeze_breakout, w_bottom, m_top)
        
        # Update confluence with event info
        if is_new_event:
            confluence_factors.insert(0, f'⭐ NEW STATE: {granular_signal} (BB signal changed!)')
        elif bars_in_state > 0:
            confluence_factors.insert(0, f'Continuing {granular_signal.lower().replace("_", " ")} state ({bars_in_state} bars)')
        
        # Prepare metadata
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'upper_band': round(current_upper, 2),
            'middle_band': round(current_middle, 2),
            'lower_band': round(current_lower, 2),
            'current_price': round(current_price, 2),
            'band_width': round(current_band_width, 2),
            'percent_b': round(current_percent_b, 4),
            'position': position,
            'squeeze_status': squeeze_status,
            'squeeze_breakout': squeeze_breakout,
            'volatility_regime': volatility_regime,
            'band_walk': band_walk,
            'patterns': {
                'w_bottom': w_bottom,
                'm_top': m_top
            },
            'period': self.period,
            'std_dev_multiplier': self.std_dev,
            'distance_from_middle': round(((current_price - current_middle) / current_middle) * 100, 2),
            'recent_band_widths': band_width_series.tail(10).tolist(),
            'recent_percent_b': percent_b_series.tail(10).tolist(),
            'is_new_event': is_new_event,
            'bars_in_state': bars_in_state
        }
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate input data has required columns
        
        Args:
            df: Input DataFrame
            
        Returns:
            True if valid, False otherwise
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required_cols)


# Usage example
if __name__ == "__main__":
    # Test with sample Bitcoin data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    
    # Create sample data with realistic Bitcoin prices
    np.random.seed(42)
    base_price = 45000
    trend = np.linspace(0, 2000, 100)  # Uptrend
    noise = np.random.randn(100).cumsum() * 100
    
    data = {
        'timestamp': dates,
        'open': base_price + trend + noise,
        'high': base_price + trend + noise + np.random.uniform(50, 200, 100),
        'low': base_price + trend + noise - np.random.uniform(50, 200, 100),
        'close': base_price + trend + noise,
        'volume': np.random.uniform(100, 1000, 100)
    }
    
    df = pd.DataFrame(data)
    
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    # Test Bollinger Bands block
    bb_block = BollingerBands(period=20, std_dev=2.0, timeframe='15min')
    result = bb_block.analyze(df)
    
    logger.info("=" * 80)
    logger.info("BOLLINGER BANDS BUILDING BLOCK - TEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Signal: {result['signal']}")
    logger.info(f"Confidence: {result['confidence']}%")
    logger.info(f"\nBand Values:")
    logger.info(f"  Upper Band: ${result['metadata']['upper_band']:.2f}")
    logger.info(f"  Middle Band: ${result['metadata']['middle_band']:.2f}")
    logger.info(f"  Lower Band: ${result['metadata']['lower_band']:.2f}")
    logger.info(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    logger.info(f"\nIndicators:")
    logger.info(f"  Band Width: {result['metadata']['band_width']:.2f}%")
    logger.info(f"  %B: {result['metadata']['percent_b']:.4f}")
    logger.info(f"  Position: {result['metadata']['position']}")
    logger.info(f"  Squeeze Status: {result['metadata']['squeeze_status']}")
    logger.info(f"  Band Walk: {result['metadata']['band_walk']}")
    logger.info(f"\nPatterns:")
    logger.info(f"  W-Bottom: {result['metadata']['patterns']['w_bottom']}")
    logger.info(f"  M-Top: {result['metadata']['patterns']['m_top']}")
    logger.info(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        logger.info(f"  - {factor}")
    logger.info("=" * 80)
