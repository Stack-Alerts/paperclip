"""
Stochastic RSI Cross Building Block
Category: Oscillator Indicators
Purpose: Momentum oscillator combining RSI with Stochastic for precise entry/exit timing
"""

from typing import Dict, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


class StochasticRSI:
    """
    Stochastic RSI - Advanced Momentum Oscillator
    
    Applies Stochastic calculation to RSI values for enhanced sensitivity.
    More reactive than standard RSI, better for timing entries/exits.
    
    Components:
    - %K Line: Stochastic of RSI
    - %D Line: SMA of %K (signal line)
    - Overbought: > 80
    - Oversold: < 20
    - Crossovers: %K crosses %D
    
    Parameters:
        rsi_period: RSI calculation period (default: 14)
        stoch_period: Stochastic period (default: 14)
        k_smooth: %K smoothing (default: 3)
        d_smooth: %D smoothing (default: 3)
        timeframe: Data timeframe
    """
    
    def __init__(self, rsi_period: int = 14, stoch_period: int = 14,
                 k_smooth: int = 3, d_smooth: int = 3, timeframe: str = '15min', **kwargs):
        """Initialize Stochastic RSI block"""
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.k_smooth = k_smooth
        self.d_smooth = d_smooth
        self.timeframe = timeframe
        
        # Bitcoin-specific thresholds
        self.btc_levels = {
            'extreme_oversold': 10,
            'oversold': 20,
            'neutral_low': 40,
            'neutral_high': 60,
            'overbought': 80,
            'extreme_overbought': 90
        }
    
    def calculate_rsi(self, close: pd.Series) -> pd.Series:
        """Calculate RSI"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_stochastic_rsi(self, rsi: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic RSI %K and %D"""
        # Calculate Stochastic of RSI
        rsi_min = rsi.rolling(window=self.stoch_period).min()
        rsi_max = rsi.rolling(window=self.stoch_period).max()
        
        stoch = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
        
        # %K: Smooth stochastic
        k_line = stoch.rolling(window=self.k_smooth).mean()
        
        # %D: Signal line (SMA of %K)
        d_line = k_line.rolling(window=self.d_smooth).mean()
        
        return k_line, d_line
    
    def detect_crossover(self, k: pd.Series, d: pd.Series) -> str:
        """Detect %K/%D crossovers"""
        if len(k) < 2 or len(d) < 2:
            return 'INSUFFICIENT_DATA'
        
        current_k, current_d = k.iloc[-1], d.iloc[-1]
        previous_k, previous_d = k.iloc[-2], d.iloc[-2]
        
        # Bullish: %K crosses above %D
        if previous_k <= previous_d and current_k > current_d:
            return 'BULLISH_CROSS'
        # Bearish: %K crosses below %D
        elif previous_k >= previous_d and current_k < current_d:
            return 'BEARISH_CROSS'
        
        return 'NO_CROSS'
    
    def classify_level(self, k_value: float) -> str:
        """Classify Stochastic RSI level"""
        if k_value >= self.btc_levels['extreme_overbought']:
            return 'EXTREME_OVERBOUGHT'
        elif k_value >= self.btc_levels['overbought']:
            return 'OVERBOUGHT'
        elif k_value >= self.btc_levels['neutral_high']:
            return 'NEUTRAL_HIGH'
        elif k_value >= self.btc_levels['neutral_low']:
            return 'NEUTRAL'
        elif k_value >= self.btc_levels['oversold']:
            return 'NEUTRAL_LOW'
        elif k_value >= self.btc_levels['extreme_oversold']:
            return 'OVERSOLD'
        else:
            return 'EXTREME_OVERSOLD'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
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
        min_required = self.rsi_period + self.stoch_period + max(self.k_smooth, self.d_smooth)
        if len(df) < min_required:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need {min_required} periods, got {len(df)}'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate
        rsi = self.calculate_rsi(df['close'])
        k_line, d_line = self.calculate_stochastic_rsi(rsi)
        
        current_k = float(k_line.iloc[-1])
        current_d = float(d_line.iloc[-1])
        current_price = float(df['close'].iloc[-1])
        
        # Detect crossover
        crossover = self.detect_crossover(k_line, d_line)
        
        # Classify level
        level = self.classify_level(current_k)
        
        # Calculate confidence
        data_quality = min(100, (len(df) / min_required) * 100)
        confidence = data_quality * 0.7
        
        if crossover in ['BULLISH_CROSS', 'BEARISH_CROSS']:
            confidence += 20
        if level in ['EXTREME_OVERBOUGHT', 'EXTREME_OVERSOLD']:
            confidence += 15
        elif level in ['OVERBOUGHT', 'OVERSOLD']:
            confidence += 10
        
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        
        if crossover == 'BULLISH_CROSS':
            if level in ['OVERSOLD', 'EXTREME_OVERSOLD']:
                confluence_factors.append(f'Bullish cross in {level} zone - strong buy signal')
            else:
                confluence_factors.append('Bullish cross detected')
        elif crossover == 'BEARISH_CROSS':
            if level in ['OVERBOUGHT', 'EXTREME_OVERBOUGHT']:
                confluence_factors.append(f'Bearish cross in {level} zone - strong sell signal')
            else:
                confluence_factors.append('Bearish cross detected')
        
        confluence_factors.append(f'StochRSI level: {level} (%K: {current_k:.1f})')
        
        # Determine signal
        if crossover == 'BULLISH_CROSS' or (level in ['EXTREME_OVERSOLD', 'OVERSOLD'] and current_k > current_d):
            signal = 'BULLISH'
        elif crossover == 'BEARISH_CROSS' or (level in ['EXTREME_OVERBOUGHT', 'OVERBOUGHT'] and current_k < current_d):
            signal = 'BEARISH'
        else:
            signal = 'NEUTRAL'
        
        # Metadata
        metadata = {
            'k_value': round(current_k, 2),
            'd_value': round(current_d, 2),
            'current_price': round(current_price, 2),
            'level': level,
            'crossover': crossover,
            'rsi_period': self.rsi_period,
            'stoch_period': self.stoch_period,
            'recent_k': k_line.tail(10).tolist(),
            'recent_d': d_line.tail(10).tolist()
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
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base = 45000
    data = pd.DataFrame({
        'timestamp': dates,
        'close': base + np.random.randn(100).cumsum() * 100,
        'open': base + np.random.randn(100).cumsum() * 100,
        'high': base + np.random.randn(100).cumsum() * 100 + 100,
        'low': base + np.random.randn(100).cumsum() * 100 - 100,
        'volume': np.random.uniform(100, 1000, 100)
    })
    
    stoch_rsi = StochasticRSI()
    result = stoch_rsi.analyze(data)
    
    print("=" * 80)
    print("STOCHASTIC RSI BUILDING BLOCK - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nStochastic RSI:")
    print(f"  %K: {result['metadata']['k_value']:.2f}")
    print(f"  %D: {result['metadata']['d_value']:.2f}")
    print(f"  Level: {result['metadata']['level']}")
    print(f"  Crossover: {result['metadata']['crossover']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
