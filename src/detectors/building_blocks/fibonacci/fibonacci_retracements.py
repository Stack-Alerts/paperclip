"""
Fibonacci Retracements Building Block
Category: Supply/Demand & Fibonacci
Purpose: Identifies reversal levels using Fibonacci ratios (23.6%, 38.2%, 50%, 61.8%, 78.6%)
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous Fibonacci levels, always provides retracement zones

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List
from datetime import datetime
import pandas as pd


class FibonacciRetracements:
    """
    Calculates Fibonacci retracement levels (IMPROVED v2)
    
    Improvements:
    - Adaptive swing points (recent swings, not all-time)
    - Trend-aware direction
    - ATR-based level detection
    """
    
    def __init__(self, timeframe: str = '15min', 
                 swing_lookback: int = 100,
                 **kwargs):
        self.timeframe = timeframe
        self.swing_lookback = swing_lookback
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
    
    def find_swing_points(self, df: pd.DataFrame) -> tuple:
        """
        Find recent swing high and low (IMPROVED - ADAPTIVE)
        
        Returns:
            (swing_high, swing_low, swing_high_idx, swing_low_idx)
        """
        lookback = min(self.swing_lookback, len(df))
        
        # Use recent data only (ADAPTIVE)
        recent_df = df.iloc[-lookback:]
        
        # Find swing high and low with their indices
        swing_high_idx = recent_df['high'].idxmax()
        swing_high = recent_df.loc[swing_high_idx, 'high']
        
        swing_low_idx = recent_df['low'].idxmin()
        swing_low = recent_df.loc[swing_low_idx, 'low']
        
        return swing_high, swing_low, swing_high_idx, swing_low_idx
    
    def determine_trend_direction(self, swing_high_idx, swing_low_idx) -> str:
        """
        Determine if uptrend or downtrend retracement (NEW)
        
        Returns:
            'UPTREND' or 'DOWNTREND'
        """
        # If swing low came before swing high = uptrend retracement
        if swing_low_idx < swing_high_idx:
            return 'UPTREND'  # Price made low, then high (uptrend)
        else:
            return 'DOWNTREND'  # Price made high, then low (downtrend)
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range (NEW)"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        import pandas as pd
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.iloc[-period:].mean()
        
        return atr
    
    def is_at_fib_level(self, current_price: float, fib_price: float, atr: float) -> bool:
        """
        Check if price is "at" Fibonacci level using ATR (IMPROVED)
        
        More sophisticated than fixed 1% threshold
        """
        # Use 0.5 * ATR as proximity threshold
        threshold = atr * 0.5
        distance = abs(current_price - fib_price)
        
        return distance <= threshold
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method (IMPROVED v2)"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < max(20, self.swing_lookback):
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        # Find RECENT swing high and low (IMPROVED - ADAPTIVE)
        swing_high, swing_low, high_idx, low_idx = self.find_swing_points(df)
        current_price = df['close'].iloc[-1]
        
        # Determine trend direction (NEW)
        trend = self.determine_trend_direction(high_idx, low_idx)
        
        # Calculate Fibonacci levels based on trend direction
        price_range = swing_high - swing_low
        fib_prices = {}
        
        if trend == 'UPTREND':
            # Uptrend retracement: Fib levels from high down
            for level in self.fib_levels:
                fib_price = swing_high - (price_range * level)
                fib_prices[f'fib_{int(level*100)}'] = round(fib_price, 2)
        else:
            # Downtrend retracement: Fib levels from low up
            for level in self.fib_levels:
                fib_price = swing_low + (price_range * level)
                fib_prices[f'fib_{int(level*100)}'] = round(fib_price, 2)
        
        # Calculate ATR (NEW)
        atr = self.calculate_atr(df)
        
        # Determine closest level
        closest_level = None
        min_distance = float('inf')
        
        for level_name, level_price in fib_prices.items():
            distance = abs(current_price - level_price)
            if distance < min_distance:
                min_distance = distance
                closest_level = level_name
        
        # Check if at key level using ATR (IMPROVED)
        at_level = self.is_at_fib_level(current_price, fib_prices[closest_level], atr)
        
        # Build signal and confluence
        if at_level:
            signal = f'AT_{closest_level.upper()}'
            # Higher confidence for Golden Ratio
            confidence = 90 if closest_level == 'fib_61' else 85
            confluence_factors = [
                f'Price at {closest_level} level (${fib_prices[closest_level]:.2f})',
                f'{trend} retracement'
            ]
        else:
            signal = 'BETWEEN_LEVELS'
            confidence = 65
            confluence_factors = [
                f'Nearest: {closest_level} (${fib_prices[closest_level]:.2f})',
                f'{trend} context'
            ]
        
        # Add Golden Ratio note (most significant)
        if closest_level == 'fib_61':
            confluence_factors.append('⭐ Golden Ratio (61.8%) - strongest level')
        
        # Add trend-specific notes
        if trend == 'UPTREND' and at_level:
            confluence_factors.append('Support zone in uptrend')
        elif trend == 'DOWNTREND' and at_level:
            confluence_factors.append('Resistance zone in downtrend')
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'swing_high': round(swing_high, 2),
                'swing_low': round(swing_low, 2),
                'fib_levels': fib_prices,
                'closest_level': closest_level,
                'at_level': at_level,
                'trend': trend,
                'atr': round(atr, 2),
                'lookback_bars': self.swing_lookback
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
