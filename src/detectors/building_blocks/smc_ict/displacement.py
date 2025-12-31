"""
Displacement Building Block
Category: SMC/ICT
Purpose: Detect displacement patterns - ICT strong move concept
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class Displacement:
    """
    Displacement Detector - ICT/SMC Concept
    
    Identifies when price makes a strong, impulsive move (displacement)
    indicating institutional activity. Displacement is characterized by
    large candles with minimal wicks, showing decisive directional bias.
    
    Displacement Characteristics:
    - Large candle bodies
    - Minimal wicks (< 20% of body)
    - Strong momentum
    - Indicates institutional interest
    - Often precedes continuation
    
    Types:
    - Bullish Displacement: Strong up move
    - Bearish Displacement: Strong down move
    
    Trading Application:
    - Confirms trend direction
    - Anticipate continuation after pullback
    - High momentum zones
    
    Parameters:
        min_body_pct: Minimum body % of total range (default: 70%)
        min_size_pct: Minimum size % vs average (default: 150%)
        lookback: Periods for average calculation (default: 20)
    """
    
    def __init__(self, timeframe: str = '15min',
                 min_body_pct: float = 70.0,
                 min_size_pct: float = 150.0,
                 lookback: int = 20, **kwargs):
        """Initialize Displacement detector"""
        self.timeframe = timeframe
        self.min_body_pct = min_body_pct
        self.min_size_pct = min_size_pct
        self.lookback = lookback
    
    def calculate_average_range(self, df: pd.DataFrame) -> float:
        """Calculate average candle range"""
        if len(df) < self.lookback:
            return 0.0
        recent = df.tail(self.lookback)
        ranges = recent['high'] - recent['low']
        return float(ranges.mean())
    
    def detect_displacement(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect displacement in most recent candle"""
        if len(df) < self.lookback + 1:
            return None
        
        # Get current candle
        current = df.iloc[-1]
        high = current['high']
        low = current['low']
        open_price = current['open'] if 'open' in df.columns else current['close']
        close = current['close']
        
        # Calculate candle metrics
        total_range = high - low
        if total_range == 0:
            return None
        
        body_size = abs(close - open_price)
        body_pct = (body_size / total_range) * 100
        
        # Check if body is large enough
        if body_pct < self.min_body_pct:
            return None
        
        # Calculate average range
        avg_range = self.calculate_average_range(df.iloc[:-1])
        if avg_range == 0:
            return None
        
        # Check if current candle is significantly larger
        size_vs_avg = (total_range / avg_range) * 100
        if size_vs_avg < self.min_size_pct:
            return None
        
        # Determine direction
        if close > open_price:
            displacement_type = 'BULLISH_DISPLACEMENT'
            upper_wick = high - close
            lower_wick = open_price - low
        else:
            displacement_type = 'BEARISH_DISPLACEMENT'
            upper_wick = high - open_price
            lower_wick = close - low
        
        # Calculate wick percentages
        upper_wick_pct = (upper_wick / total_range) * 100 if total_range > 0 else 0
        lower_wick_pct = (lower_wick / total_range) * 100 if total_range > 0 else 0
        
        return {
            'type': displacement_type,
            'body_pct': round(body_pct, 2),
            'size_vs_avg': round(size_vs_avg, 2),
            'upper_wick_pct': round(upper_wick_pct, 2),
            'lower_wick_pct': round(lower_wick_pct, 2),
            'total_range': float(total_range),
            'body_size': float(body_size),
            'timestamp': current['timestamp']
        }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['timestamp', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.lookback + 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.lookback + 1} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Add open column if not present
        if 'open' not in df.columns:
            df = df.copy()
            df['open'] = df['close'].shift(1).fillna(df['close'])
        
        # Detect displacement
        disp = self.detect_displacement(df)
        
        if not disp:
            return {
                'signal': 'NO_DISPLACEMENT',
                'confidence': 0,
                'metadata': {'error': 'No displacement detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['No displacement - normal price action']
            }
        
        # Determine signal
        signal = 'BULLISH' if disp['type'] == 'BULLISH_DISPLACEMENT' else 'BEARISH'
        
        # Calculate confidence based on strength
        confidence = 75  # Base confidence for displacement
        if disp['size_vs_avg'] > 200:
            confidence += 10
        if disp['body_pct'] > 85:
            confidence += 10
        confidence = min(100, confidence)
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'Displacement Type: {disp["type"]}')
        confluence_factors.append(f'Body%: {disp["body_pct"]:.1f}% (strong)')
        confluence_factors.append(f'Size vs Avg: {disp["size_vs_avg"]:.1f}%')
        confluence_factors.append('Institutional activity detected')
        confluence_factors.append('Strong momentum - expect continuation')
        
        # Metadata
        metadata = {
            'displacement_type': disp['type'],
            'body_pct': disp['body_pct'],
            'size_vs_avg': disp['size_vs_avg'],
            'upper_wick_pct': disp['upper_wick_pct'],
            'lower_wick_pct': disp['lower_wick_pct'],
            'total_range': disp['total_range'],
            'body_size': disp['body_size'],
            'displacement_timestamp': disp['timestamp']
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
