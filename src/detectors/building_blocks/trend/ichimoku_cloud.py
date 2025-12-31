"""
Ichimoku Cloud Building Block
Category: Trend Strength & Momentum
Purpose: Comprehensive trend indicator with support/resistance cloud
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class IchimokuCloud:
    """
    Ichimoku Cloud - Comprehensive Trend System
    
    5 components showing trend, momentum, support/resistance:
    
    1. Tenkan-sen (Conversion Line): (9-high + 9-low) / 2 - Short-term momentum
    2. Kijun-sen (Base Line): (26-high + 26-low) / 2 - Medium-term trend
    3. Senkou Span A: (Tenkan + Kijun) / 2, plotted 26 ahead - Cloud edge
    4. Senkou Span B: (52-high + 52-low) / 2, plotted 26 ahead - Cloud edge
    5. Chikou Span: Close plotted 26 behind - Momentum confirmation
    
    Cloud (Kumo):
    - Green: Span A > Span B (bullish)
    - Red: Span B > Span A (bearish)
    - Thick cloud: Strong support/resistance
    
    Signals:
    - Price above cloud: Bullish
    - Price below cloud: Bearish
    - Cloud twist: Potential reversal
    
    Parameters:
        tenkan_period: Conversion line period (default: 9)
        kijun_period: Base line period (default: 26)
        senkou_period: Leading span B period (default: 52)
    """
    
    def __init__(self, timeframe: str = '15min',
                 tenkan_period: int = 9,
                 kijun_period: int = 26,
                 senkou_period: int = 52, **kwargs):
        """Initialize Ichimoku Cloud indicator"""
        self.timeframe = timeframe
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_period = senkou_period
    
    def calculate_ichimoku(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all Ichimoku components"""
        if len(df) < self.senkou_period:
            return None
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Tenkan-sen (Conversion Line)
        tenkan_high = pd.Series(high).rolling(self.tenkan_period).max()
        tenkan_low = pd.Series(high).rolling(self.tenkan_period).min()
        tenkan = (tenkan_high + tenkan_low) / 2
        
        # Kijun-sen (Base Line)
        kijun_high = pd.Series(high).rolling(self.kijun_period).max()
        kijun_low = pd.Series(low).rolling(self.kijun_period).min()
        kijun = (kijun_high + kijun_low) / 2
        
        # Senkou Span A (Leading Span A)
        senkou_a = (tenkan + kijun) / 2
        
        # Senkou Span B (Leading Span B)
        senkou_high = pd.Series(high).rolling(self.senkou_period).max()
        senkou_low = pd.Series(low).rolling(self.senkou_period).min()
        senkou_b = (senkou_high + senkou_low) / 2
        
        # Get current values
        current_price = float(close[-1])
        current_tenkan = float(tenkan.iloc[-1]) if not pd.isna(tenkan.iloc[-1]) else current_price
        current_kijun = float(kijun.iloc[-1]) if not pd.isna(kijun.iloc[-1]) else current_price
        current_senkou_a = float(senkou_a.iloc[-1]) if not pd.isna(senkou_a.iloc[-1]) else current_price
        current_senkou_b = float(senkou_b.iloc[-1]) if not pd.isna(senkou_b.iloc[-1]) else current_price
        
        return {
            'tenkan': current_tenkan,
            'kijun': current_kijun,
            'senkou_a': current_senkou_a,
            'senkou_b': current_senkou_b,
            'current_price': current_price
        }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.senkou_period + 10:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.senkou_period + 10} bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate Ichimoku components
        result = self.calculate_ichimoku(df)
        if not result:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Ichimoku calculation failed'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        tenkan = result['tenkan']
        kijun = result['kijun']
        senkou_a = result['senkou_a']
        senkou_b = result['senkou_b']
        price = result['current_price']
        
        # Cloud characteristics
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        cloud_thickness = abs(senkou_a - senkou_b)
        cloud_color = 'GREEN' if senkou_a > senkou_b else 'RED'
        
        # Price position relative to cloud
        if price > cloud_top:
            position = 'ABOVE_CLOUD'
            signal = 'BULLISH'
        elif price < cloud_bottom:
            position = 'BELOW_CLOUD'
            signal = 'BEARISH'
        else:
            position = 'IN_CLOUD'
            signal = 'NEUTRAL'
        
        # Confidence based on multiple factors
        confidence = 50  # Base
        
        # Cloud color alignment
        if signal == 'BULLISH' and cloud_color == 'GREEN':
            confidence += 20
        elif signal == 'BEARISH' and cloud_color == 'RED':
            confidence += 20
        
        # Tenkan/Kijun alignment
        if signal == 'BULLISH' and tenkan > kijun:
            confidence += 15
        elif signal == 'BEARISH' and tenkan < kijun:
            confidence += 15
        
        # Cloud thickness (strength)
        if cloud_thickness > price * 0.02:  # >2% thick
            confidence += 10
        
        confidence = min(100, confidence)
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f'Position: {position}')
        confluence_factors.append(f'Cloud: {cloud_color}')
        confluence_factors.append(f'Tenkan: ${tenkan:.2f}, Kijun: ${kijun:.2f}')
        confluence_factors.append(f'Cloud Range: ${cloud_bottom:.2f} - ${cloud_top:.2f}')
        
        if position == 'ABOVE_CLOUD':
            confluence_factors.append('Strong bullish - price above cloud')
        elif position == 'BELOW_CLOUD':
            confluence_factors.append('Strong bearish - price below cloud')
        else:
            confluence_factors.append('Neutral - price in cloud (consolidation)')
        
        if cloud_thickness > price * 0.02:
            confluence_factors.append('Thick cloud - strong support/resistance')
        
        # Metadata
        metadata = {
            'tenkan': round(tenkan, 2),
            'kijun': round(kijun, 2),
            'senkou_a': round(senkou_a, 2),
            'senkou_b': round(senkou_b, 2),
            'cloud_top': round(cloud_top, 2),
            'cloud_bottom': round(cloud_bottom, 2),
            'cloud_color': cloud_color,
            'position': position,
            'cloud_thickness_pct': round((cloud_thickness / price) * 100, 2)
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
