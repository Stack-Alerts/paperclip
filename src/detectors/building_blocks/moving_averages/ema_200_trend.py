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
from datetime import datetime
import pandas as pd
import numpy as np


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
        """Classify price position relative to 200 EMA"""
        if price > ema:
            return 'ABOVE_200EMA'
        elif price < ema:
            return 'BELOW_200EMA'
        else:
            return 'AT_200EMA'
    
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
                'confidence': 0,
                'metadata': {'error': 'Invalid data format'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check minimum data
        min_required = self.period + 20
        if len(df) < min_required:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need {min_required} periods, got {len(df)}'},
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
        
        # Detect EMA cross events
        crossed_above = (prev_position == 'BELOW_200EMA' and current_position == 'ABOVE_200EMA')
        crossed_below = (prev_position == 'ABOVE_200EMA' and current_position == 'BELOW_200EMA')
        
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
            'bars_monitored': bars_monitored
        }
        
        return {
            'signal': signal,
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
    
    print("=" * 80)
    print("200 EMA TREND FILTER - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\n200 EMA Analysis:")
    print(f"  200 EMA: ${result['metadata']['ema_200']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Position: {result['metadata']['position']}")
    print(f"  Slope: {result['metadata']['slope']}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"  Trend Filter: {result['metadata']['trend_filter']}")
    print(f"  Overextended: {result['metadata']['is_overextended']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
