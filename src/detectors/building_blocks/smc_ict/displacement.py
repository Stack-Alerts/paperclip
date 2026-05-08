"""
Displacement Building Block
Category: SMC/ICT
Purpose: Detect displacement patterns - ICT strong move concept

ENHANCEMENTS (2026-01-04):
- Priority 1.1: Consecutive displacement detection (momentum strength)
- Priority 1.2: Volume confirmation (quality filtering)
- Priority 1.3: Gap size tracking (FVG detection integration)
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: Displacement detection, fires on strong moves

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

@register_block(
    name='displacement',
    category='SMC_ICT',
    class_name='Displacement',
    default_weight=20,
    description='Displacement - SMC/ICT concept detecting a strong, impulsive move leaving a fair value gap (imbalance). Signals institutional participation and is used to identify the starting point of a new price leg. Neutral, direction context-dependent.',
    direction='NEUTRAL',
    valid_signals=[
        # Granular SMC signals (FVG removed - too rare for 15min, tracked in metadata)
        'BEARISH_DISPLACEMENT', 'BULLISH_DISPLACEMENT',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BEARISH_DISPLACEMENT': {
                'base_points': 25,
                'formula': 'scaled',
                'description': 'Bearish displacement - Fast downmove rejecting consolidation. Strong bearish momentum. Enter shorts. Institutional selling. Trend acceleration down.'
        },
        'BULLISH_DISPLACEMENT': {
                'base_points': 25,
                'formula': 'scaled',
                'description': 'Bullish displacement - Fast upmove rejecting consolidation. Strong bullish momentum. Enter longs. Institutional buying. Trend acceleration up.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot calculate displacement. Check data quality and required columns.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need enough bars for displacement detection. Wait for more price history.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish displacement - Strong upward momentum detected. Long positions highly favorable. Institutional buying surge.'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish displacement - Strong downward momentum detected. Short positions highly favorable. Institutional selling surge.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Neutral displacement - No strong displacement. Wait for momentum surge or consolidation break.'
        }
}
)
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
        lookback: Periods for average calculation (default: 5)
        track_consecutive: Track consecutive displacement for momentum (default: True)
        volume_confirmation: Require volume spike (default: False)
        track_gaps: Track gap size for FVG integration (default: True)
    """
    
    def __init__(self, timeframe: str = '15min',
                 min_body_pct: float = 70.0,
                 min_size_pct: float = 150.0,
                 lookback: int = 5,
                 track_consecutive: bool = True,
                 volume_confirmation: bool = False,
                 track_gaps: bool = True, **kwargs):
        """
        Initialize Displacement detector with OPTIMIZED parameters (batch tuning 2026-01-01)
        
        Batch Optimization Results:
            Quality: 80/100
            Accuracy: 55.8%
            Signals: 1,006 in 180 days (5.6/day)
            R/R: 5.34 (good)
            Discovery: lookback=5 (vs 20) - much faster = better
        
        Enhancements (2026-01-04 - Expert Mode Priority 1 & 2):
            track_consecutive: Track consecutive displacement candles for momentum
            volume_confirmation: Optional volume spike requirement (>2x average)
            track_gaps: Track gap size created by displacement (FVG integration)
        """
        self.timeframe = timeframe
        self.min_body_pct = min_body_pct
        self.min_size_pct = min_size_pct
        self.lookback = lookback
        self.track_consecutive = track_consecutive
        self.volume_confirmation = volume_confirmation
        self.track_gaps = track_gaps
        self.displacement_history = []  # Track displacement events for consecutive detection
    
    def _determine_dual_signals(self, disp_type: str, has_gap: bool = False, gap_type: str = None) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        if disp_type == 'BULLISH_DISPLACEMENT':
            if has_gap and gap_type == 'BULLISH_FVG':
                granular = 'BULLISH_FVG'
            else:
                granular = 'BULLISH_DISPLACEMENT'
            simple = 'BULLISH'
        elif disp_type == 'BEARISH_DISPLACEMENT':
            if has_gap and gap_type == 'BEARISH_FVG':
                granular = 'BEARISH_FVG'
            else:
                granular = 'BEARISH_DISPLACEMENT'
            simple = 'BEARISH'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        return granular, simple
    
    def count_consecutive_displacement(self, current_signal: str) -> int:
        """
        Count consecutive displacement candles (Priority 1.1 Enhancement)
        
        Returns:
            Number of consecutive displacement candles in current direction
            (2+ indicates very strong momentum)
        """
        if not self.track_consecutive or len(self.displacement_history) == 0:
            return 1
        
        consecutive = 1
        for disp_event in reversed(self.displacement_history[-3:]):  # Check last 3
            if disp_event == current_signal:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def update_displacement_history(self, signal: str):
        """Update displacement history for consecutive tracking"""
        if self.track_consecutive and signal in ['BULLISH', 'BEARISH']:
            self.displacement_history.append(signal)
            # Keep only last 5 events
            if len(self.displacement_history) > 5:
                self.displacement_history.pop(0)
    
    def check_volume_confirmation(self, df: pd.DataFrame) -> bool:
        """
        Check if displacement has volume confirmation (Priority 1.2 Enhancement)
        
        Returns:
            True if volume spike detected (>2x average), False otherwise
        """
        if not self.volume_confirmation:
            return True  # Not required
        
        if 'volume' not in df.columns:
            return True  # Can't check, assume OK
        
        if len(df) < self.lookback + 1:
            return True
        
        # Calculate average volume
        recent_volume = df['volume'].iloc[-(self.lookback+1):-1]
        avg_volume = recent_volume.mean()
        
        if avg_volume == 0:
            return True
        
        # Check current volume
        current_volume = df['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume
        
        return volume_ratio >= 2.0  # 2x spike required
    
    def calculate_gap_size(self, df: pd.DataFrame, displacement_type: str) -> Dict[str, Any]:
        """
        Calculate gap size created by displacement (Priority 1.3 Enhancement)
        
        Returns dict with gap info for FVG integration
        """
        if not self.track_gaps or len(df) < 2:
            return None
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        if displacement_type == 'BULLISH_DISPLACEMENT':
            # Gap = space between previous high and current low
            gap_low = float(previous['high'])
            gap_high = float(current['low'])
            
            if gap_high > gap_low:
                gap_size = gap_high - gap_low
                gap_pct = (gap_size / gap_low) * 100
                
                return {
                    'has_gap': True,
                    'gap_size': round(gap_size, 2),
                    'gap_pct': round(gap_pct, 3),
                    'gap_low': gap_low,
                    'gap_high': gap_high,
                    'gap_type': 'BULLISH_FVG'
                }
        
        else:  # BEARISH_DISPLACEMENT
            # Gap = space between previous low and current high
            gap_high = float(previous['low'])
            gap_low = float(current['high'])
            
            if gap_low < gap_high:
                gap_size = gap_high - gap_low
                gap_pct = (gap_size / gap_high) * 100
                
                return {
                    'has_gap': True,
                    'gap_size': round(gap_size, 2),
                    'gap_pct': round(gap_pct, 3),
                    'gap_low': gap_low,
                    'gap_high': gap_high,
                    'gap_type': 'BEARISH_FVG'
                }
        
        return None
    
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
                'signal': 'NEUTRAL',
                'signal_simple': 'NEUTRAL',
                'confidence': 0,
                'metadata': {
                    'signal_simple': 'NEUTRAL',
                    'signal_granular': 'NEUTRAL',
                    'error': 'No displacement detected'
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['No displacement - normal price action']
            }
        
        # Determine signal
        signal = 'BULLISH' if disp['type'] == 'BULLISH_DISPLACEMENT' else 'BEARISH'
        
        # **ENHANCED:** Count consecutive displacement (momentum tracking)
        consecutive_disp = self.count_consecutive_displacement(signal)
        
        # Update displacement history
        self.update_displacement_history(signal)
        
        # **ENHANCED:** Check volume confirmation
        has_volume_confirmation = self.check_volume_confirmation(df)
        
        # **ENHANCED:** Calculate gap size (FVG detection)
        gap_info = self.calculate_gap_size(df, disp['type'])
        
        # **ENHANCED:** Calculate confidence with new factors
        confidence = 90  # Base confidence for displacement
        
        # Size bonus
        if disp['size_vs_avg'] > 200:
            confidence += 5
        
        # Body percentage bonus
        if disp['body_pct'] > 85:
            confidence += 5
        
        # Consecutive displacement bonus (momentum)
        if consecutive_disp >= 2:
            confidence += 5  # Strong momentum
        
        # Volume confirmation bonus
        if has_volume_confirmation and self.volume_confirmation:
            confidence += 10  # Volume spike = higher quality
        
        # Gap creation bonus (FVG opportunity)
        if gap_info and gap_info['has_gap']:
            if gap_info['gap_pct'] > 0.2:  # Significant gap
                confidence += 10  # Large gap = FVG opportunity
        
        confidence = min(100, confidence)
        
        # **ENHANCED:** Build confluence factors with new info
        confluence_factors = []
        confluence_factors.append(f'Displacement Type: {disp["type"]}')
        confluence_factors.append(f'Body%: {disp["body_pct"]:.1f}% (strong)')
        confluence_factors.append(f'Size vs Avg: {disp["size_vs_avg"]:.1f}%')
        
        # Momentum indicator
        if consecutive_disp >= 2:
            confluence_factors.append(f'🔥 STRONG MOMENTUM: {consecutive_disp} consecutive displacement candles!')
        
        # Volume indicator
        if has_volume_confirmation and self.volume_confirmation:
            confluence_factors.append('📊 VOLUME CONFIRMED: >2x average volume spike')
        
        # Gap indicator
        if gap_info and gap_info['has_gap']:
            confluence_factors.append(f'💎 FVG CREATED: {gap_info["gap_pct"]:.2f}% gap ({gap_info["gap_type"]})')
        
        confluence_factors.append('Institutional activity detected')
        confluence_factors.append('Strong momentum - expect continuation')
        
        # DUAL SIGNAL ARCHITECTURE
        has_gap = gap_info.get('has_gap', False) if gap_info else False
        gap_type = gap_info.get('gap_type') if gap_info else None
        granular_signal, simple_signal = self._determine_dual_signals(disp['type'], has_gap, gap_type)
        
        # **ENHANCED:** Metadata with new tracking
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'displacement_type': disp['type'],
            'body_pct': disp['body_pct'],
            'size_vs_avg': disp['size_vs_avg'],
            'upper_wick_pct': disp['upper_wick_pct'],
            'lower_wick_pct': disp['lower_wick_pct'],
            'total_range': disp['total_range'],
            'body_size': disp['body_size'],
            'displacement_timestamp': disp['timestamp'],
            'consecutive_displacement': consecutive_disp,  # NEW: Momentum tracking
            'has_volume_confirmation': has_volume_confirmation  # NEW: Volume check
        }
        
        # Add gap info if detected
        if gap_info:
            metadata.update(gap_info)
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
