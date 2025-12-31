"""
Fibonacci Retracements Building Block
Category: Supply/Demand & Fibonacci
Purpose: Identifies reversal levels using Fibonacci ratios (23.6%, 38.2%, 50%, 61.8%, 78.6%)
"""

from typing import Dict, Any, List
from datetime import datetime
import pandas as pd


class FibonacciRetracements:
    """Calculates Fibonacci retracement levels"""
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < 20:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        # Find swing high and low
        swing_high = df['high'].max()
        swing_low = df['low'].min()
        current_price = df['close'].iloc[-1]
        
        # Calculate Fibonacci levels
        price_range = swing_high - swing_low
        fib_prices = {}
        
        for level in self.fib_levels:
            fib_price = swing_high - (price_range * level)
            fib_prices[f'fib_{int(level*100)}'] = round(fib_price, 2)
        
        # Determine closest level
        closest_level = None
        min_distance = float('inf')
        
        for level_name, level_price in fib_prices.items():
            distance = abs(current_price - level_price)
            if distance < min_distance:
                min_distance = distance
                closest_level = level_name
        
        # Check if at key level (within 1%)
        at_level = min_distance / current_price < 0.01
        
        if at_level:
            signal = f'AT_{closest_level.upper()}'
            confidence = 70
            confluence_factors = [f'Price at {closest_level} level (${fib_prices[closest_level]:.2f})']
        else:
            signal = 'BETWEEN_LEVELS'
            confidence = 50
            confluence_factors = [f'Nearest: {closest_level} (${fib_prices[closest_level]:.2f})']
        
        # Add Golden Ratio note
        if closest_level == 'fib_61':
            confluence_factors.append('⭐ Golden Ratio level - most significant')
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'swing_high': round(swing_high, 2),
                'swing_low': round(swing_low, 2),
                'fib_levels': fib_prices,
                'closest_level': closest_level,
                'at_level': at_level
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
