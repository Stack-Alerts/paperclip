"""
Fair Value Gap (FVG) Building Block
Category: Advanced Price Action
Purpose: Identify fair value gaps (price inefficiencies) - ICT/SMC concept
"""

from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
import numpy as np


class FairValueGap:
    """
    Fair Value Gap (FVG) Detector - ICT/SMC Concept
    
    Identifies price inefficiencies where price moved too quickly,
    leaving unfilled areas (gaps). These gaps often get filled later.
    
    FVG Formation:
    - 3-candle pattern
    - Middle candle creates gap
    - Gap = no overlap between candle 1 high and candle 3 low (bullish)
    - Gap = no overlap between candle 1 low and candle 3 high (bearish)
    
    Trading Significance:
    - Price tends to return to fill gaps
    - High probability reversal zones
    - Entry opportunities on gap fill
    
    Parameters:
        min_gap_pct: Minimum gap size % to qualify (default: 0.2%)
        lookback: Periods to look back (default: 50)
    """
    
    def __init__(self, timeframe: str = '15min',
                 min_gap_pct: float = 0.2,
                 lookback: int = 50, **kwargs):
        """Initialize FVG detector"""
        self.timeframe = timeframe
        self.min_gap_pct = min_gap_pct
        self.lookback = lookback
    
    def detect_bullish_fvg(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect bullish FVG (gap up)"""
        if len(df) < 3:
            return None
        
        for i in range(len(df) - 3, max(len(df) - self.lookback, 0), -1):
            # Check for bullish FVG: low of candle 3 > high of candle 1
            candle1_high = df['high'].iloc[i]
            candle3_low = df['low'].iloc[i+2]
            
            if candle3_low > candle1_high:
                gap_size = candle3_low - candle1_high
                gap_pct = (gap_size / candle1_high) * 100
                
                if gap_pct >= self.min_gap_pct:
                    return {
                        'type': 'BULLISH_FVG',
                        'index': i,
                        'gap_high': float(candle3_low),
                        'gap_low': float(candle1_high),
                        'gap_mid': float((candle3_low + candle1_high) / 2),
                        'gap_size': round(gap_size, 2),
                        'gap_pct': round(gap_pct, 3),
                        'timestamp': df['timestamp'].iloc[i+1]
                    }
        
        return None
    
    def detect_bearish_fvg(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect bearish FVG (gap down)"""
        if len(df) < 3:
            return None
        
        for i in range(len(df) - 3, max(len(df) - self.lookback, 0), -1):
            # Check for bearish FVG: high of candle 3 < low of candle 1
            candle1_low = df['low'].iloc[i]
            candle3_high = df['high'].iloc[i+2]
            
            if candle3_high < candle1_low:
                gap_size = candle1_low - candle3_high
                gap_pct = (gap_size / candle1_low) * 100
                
                if gap_pct >= self.min_gap_pct:
                    return {
                        'type': 'BEARISH_FVG',
                        'index': i,
                        'gap_high': float(candle1_low),
                        'gap_low': float(candle3_high),
                        'gap_mid': float((candle1_low + candle3_high) / 2),
                        'gap_size': round(gap_size, 2),
                        'gap_pct': round(gap_pct, 3),
                        'timestamp': df['timestamp'].iloc[i+1]
                    }
        
        return None
    
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
        
        if len(df) < 10:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 10 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect both types
        bullish_fvg = self.detect_bullish_fvg(df)
        bearish_fvg = self.detect_bearish_fvg(df)
        
        current_price = float(df['close'].iloc[-1])
        
        # Determine active FVG
        active_fvg = None
        signal = 'NEUTRAL'
        
        if bullish_fvg and (not bearish_fvg or bullish_fvg['index'] > bearish_fvg['index']):
            active_fvg = bullish_fvg
            # Check if price is in or near gap
            if bullish_fvg['gap_low'] <= current_price <= bullish_fvg['gap_high']:
                signal = 'BULLISH'  # In gap, expect continuation up
        elif bearish_fvg:
            active_fvg = bearish_fvg
            # Check if price is in or near gap
            if bearish_fvg['gap_low'] <= current_price <= bearish_fvg['gap_high']:
                signal = 'BEARISH'  # In gap, expect continuation down
        
        if not active_fvg:
            return {
                'signal': 'NO_FVG',
                'confidence': 0,
                'metadata': {'error': 'No fair value gap detected'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate confidence
        confidence = 75
        if active_fvg['gap_pct'] > 0.5:
            confidence += 10
        if active_fvg['gap_pct'] > 1.0:
            confidence += 10
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        confluence_factors.append(f'FVG Type: {active_fvg["type"]}')
        confluence_factors.append(f'Gap Zone: ${active_fvg["gap_low"]:.2f} - ${active_fvg["gap_high"]:.2f}')
        confluence_factors.append(f'Gap Size: ${active_fvg["gap_size"]:.2f} ({active_fvg["gap_pct"]:.3f}%)')
        
        if signal != 'NEUTRAL':
            confluence_factors.append('Price in FVG zone - gap fill in progress')
        else:
            confluence_factors.append('FVG present - watch for price return to gap')
        
        # Metadata
        metadata = {
            'fvg_type': active_fvg['type'],
            'gap_high': active_fvg['gap_high'],
            'gap_low': active_fvg['gap_low'],
            'gap_mid': active_fvg['gap_mid'],
            'gap_size': active_fvg['gap_size'],
            'gap_pct': active_fvg['gap_pct'],
            'current_price': round(current_price, 2),
            'in_gap': signal != 'NEUTRAL',
            'fvg_timestamp': active_fvg['timestamp']
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    
    # Create data with FVG
    highs = [45000]
    lows = [44900]
    for i in range(99):
        if i == 50:  # Create bullish FVG
            highs.append(45100)
            lows.append(45000)
        elif i == 51:  # Gap candle
            highs.append(45300)
            lows.append(45200)
        elif i == 52:  # After gap
            highs.append(45400)
            lows.append(45250)
        else:
            highs.append(highs[-1] + np.random.uniform(-20, 20))
            lows.append(highs[-1] - 100)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': [(h + l) / 2 for h, l in zip(highs, lows)]
    })
    
    fvg = FairValueGap()
    result = fvg.analyze(data)
    
    print("=" * 80)
    print("FAIR VALUE GAP DETECTOR - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    if 'fvg_type' in result['metadata']:
        print(f"\nFVG Analysis:")
        print(f"  Type: {result['metadata']['fvg_type']}")
        print(f"  Gap: ${result['metadata']['gap_low']:.2f} - ${result['metadata']['gap_high']:.2f}")
        print(f"  Size: ${result['metadata']['gap_size']:.2f} ({result['metadata']['gap_pct']:.3f}%)")
        print(f"\nConfluence:")
        for factor in result['confluence_factors']:
            print(f"  - {factor}")
    print("=" * 80)
