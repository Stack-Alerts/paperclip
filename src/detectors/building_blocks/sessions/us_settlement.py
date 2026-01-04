"""
US Settlement Building Block - ENHANCED
Category: Sessions & Time
Purpose: Detect US market settlement window (price magnet effect)

RESEARCH:
- 4:00 PM EST (20:00 UTC) = US equity market close & settlement
- Acts as "price magnet" - institutional flows settle positions
- Portfolio rebalancing, end-of-day positioning
- Options/futures settlement prices
- Crypto correlation with equity market settlement

ENHANCED VERSION (2026-01-03):
- Event tracking (settlement window entry)
- Volume confirmation (quality block integration)
- ATR awareness (volatility context)
- Magnet effect detection (drift toward settlement)
- Smart confidence (data-driven)
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: TIME-BASED
Purpose: US settlement time state

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


class USSettlement:
    """
    US Settlement Window Detector - ENHANCED
    
    Detects the US equity market settlement window with enhancements:
    - Event tracking (entry into settlement window)
    - Volume confirmation (settlement flow detection)
    - ATR context (volatility awareness)
    - Magnet effect (price drift detection)
    - Smart confidence (activity-based)
    
    Settlement Window:
    - US Market Close: 16:00 EST (21:00 UTC)
    - Settlement Period: 15:00-16:00 EST (20:00-21:00 UTC)
    - Acts as "price magnet" for institutional flows
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        """Initialize Enhanced US Settlement detector"""
        self.timeframe = timeframe
        self.last_in_settlement = False
        self.bars_in_settlement = 0
        
        # Settlement window (UTC) - 15:00-16:00 EST = 20:00-21:00 UTC
        self.settlement_start = 20
        self.settlement_end = 21
        
        # Pre-settlement window for magnet detection
        self.pre_settlement_start = 19  # 1 hour before settlement
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR for volatility awareness (quality block integration)"""
        if len(df) < period + 1:
            return 0.0
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1])
            )
        )
        
        atr = np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)
        return float(atr)
    
    def analyze_volume_activity(self, df: pd.DataFrame, window: int = 20) -> tuple:
        """
        Analyze volume activity for settlement flow detection
        Returns: (volume_ratio, is_active, activity_score)
        """
        if len(df) < window or 'volume' not in df.columns:
            return 1.0, False, 50
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-window:].mean()
        
        if avg_volume == 0:
            return 1.0, False, 50
        
        volume_ratio = current_volume / avg_volume
        
        # High volume = settlement flows active
        is_active = volume_ratio > 1.2
        
        # Activity score (0-100)
        activity_score = min(100, int(volume_ratio * 50))
        
        return volume_ratio, is_active, activity_score
    
    def detect_magnet_effect(self, df: pd.DataFrame, window: int = 8) -> tuple:
        """
        Detect "magnet effect" - price drift toward settlement
        
        During pre-settlement hour, price tends to drift toward
        settlement levels. This creates directional bias.
        
        Returns: (has_magnet, direction, strength)
        """
        if len(df) < window:
            return False, 'NEUTRAL', 0
        
        # Get recent price action
        recent_closes = df['close'].iloc[-window:].values
        
        # Calculate trend (simple linear regression)
        x = np.arange(len(recent_closes))
        slope = np.polyfit(x, recent_closes, 1)[0]
        
        # Normalize by ATR
        atr = self.calculate_atr(df)
        if atr > 0:
            normalized_slope = slope / atr
        else:
            normalized_slope = 0
        
        # Detect magnet effect
        threshold = 0.1  # 10% of ATR per bar
        
        if abs(normalized_slope) > threshold:
            has_magnet = True
            direction = 'BULLISH' if slope > 0 else 'BEARISH'
            strength = min(100, int(abs(normalized_slope) * 100))
        else:
            has_magnet = False
            direction = 'NEUTRAL'
            strength = 0
        
        return has_magnet, direction, strength
    
    def calculate_smart_confidence(self, base_confidence: int,
                                   activity_score: int,
                                   atr: float,
                                   avg_atr: float = 1000.0,
                                   is_transition: bool = False,
                                   magnet_strength: int = 0) -> int:
        """
        Smart confidence calculation using real-time data
        
        Factors:
        1. Base confidence (settlement window)
        2. Volume activity (settlement flows)
        3. Volatility context (ATR)
        4. Transition bonus (window entry)
        5. Magnet effect (price drift)
        """
        confidence = base_confidence
        
        # Volume activity adjustment (+/- 10%)
        if activity_score >= 80:
            confidence += 10  # Very active - boost
        elif activity_score >= 60:
            confidence += 5   # Active - small boost
        elif activity_score < 40:
            confidence -= 10  # Quiet - reduce
        
        # Volatility adjustment (+/- 5%)
        if atr > 0 and avg_atr > 0:
            volatility_ratio = atr / avg_atr
            
            if volatility_ratio > 1.5:
                # High volatility during settlement = good
                confidence += 5
            elif volatility_ratio < 0.5:
                # Low volatility = reduce
                confidence -= 5
        
        # Transition bonus (+5%)
        if is_transition:
            confidence += 5  # Fresh window entry
        
        # Magnet effect bonus (+0-10%)
        if magnet_strength > 0:
            magnet_bonus = min(10, magnet_strength // 10)
            confidence += magnet_bonus
        
        return max(30, min(100, confidence))
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Enhanced analysis with quality block integration"""
        # Validation
        if 'timestamp' not in df.columns:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing timestamp column'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 50:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 50 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Current time
        current_time = df['timestamp'].iloc[-1]
        current_hour = current_time.hour
        
        # Check settlement windows
        in_settlement = (current_hour >= self.settlement_start and 
                        current_hour < self.settlement_end)
        in_pre_settlement = (current_hour >= self.pre_settlement_start and
                            current_hour < self.settlement_start)
        
        # Event tracking
        is_new_event = in_settlement and not self.last_in_settlement
        
        if is_new_event:
            self.bars_in_settlement = 0
        elif in_settlement:
            self.bars_in_settlement += 1
        
        # Update tracking
        self.last_in_settlement = in_settlement
        
        # Quality block integrations
        atr = self.calculate_atr(df, period=14)
        volume_ratio, is_volume_active, activity_score = self.analyze_volume_activity(df, window=20)
        
        # Magnet effect detection
        has_magnet, magnet_direction, magnet_strength = self.detect_magnet_effect(df, window=8)
        
        # Base confidence
        if in_settlement:
            base_confidence = 90  # In settlement window
        elif in_pre_settlement:
            base_confidence = 70  # Pre-settlement (magnet building)
        else:
            base_confidence = 50  # Off-hours
        
        # Smart confidence (data-driven!)
        confidence = self.calculate_smart_confidence(
            base_confidence,
            activity_score,
            atr,
            avg_atr=atr,
            is_transition=is_new_event,
            magnet_strength=magnet_strength
        )
        
        # Build confluence factors
        confluence_factors = []
        
        if in_settlement:
            confluence_factors.append('🎯 US Settlement Window (20:00-21:00 UTC)')
            confluence_factors.append('Institutional settlement flows')
            confluence_factors.append('Portfolio rebalancing period')
            
            if is_new_event:
                confluence_factors.append('🆕 Just entered settlement window!')
            else:
                confluence_factors.append(f'In settlement for {self.bars_in_settlement} bars')
            
            if is_volume_active:
                confluence_factors.append(f'⭐ HIGH settlement volume ({volume_ratio:.1f}x average)')
            
        elif in_pre_settlement:
            confluence_factors.append('Pre-settlement period (19:00-20:00 UTC)')
            
            if has_magnet:
                confluence_factors.append(f'🧲 MAGNET EFFECT detected ({magnet_direction})')
                confluence_factors.append(f'Price drift strength: {magnet_strength}/100')
                confluence_factors.append('Positioning for settlement')
            
        else:
            confluence_factors.append('Outside settlement window')
        
        if in_settlement or in_pre_settlement:
            confluence_factors.append('Price magnet effect period')
        
        # Signal generation
        if in_settlement:
            signal = 'SETTLEMENT_ACTIVE'
        elif in_pre_settlement and has_magnet:
            # Pre-settlement with magnet effect
            signal = f'PRE_SETTLEMENT_{magnet_direction}'
        else:
            signal = 'NEUTRAL'
        
        # Rich metadata
        metadata = {
            'in_settlement': in_settlement,
            'in_pre_settlement': in_pre_settlement,
            'settlement_window_utc': '20:00-21:00',
            'is_new_event': is_new_event,
            'bars_in_settlement': self.bars_in_settlement,
            'hour_utc': current_hour,
            'volume_ratio': round(volume_ratio, 2),
            'is_volume_active': is_volume_active,
            'activity_score': activity_score,
            'atr_value': round(atr, 2),
            'has_magnet_effect': has_magnet,
            'magnet_direction': magnet_direction,
            'magnet_strength': magnet_strength,
            'base_confidence': base_confidence,
            'adjusted_confidence': confidence
        }
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': current_time,
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=24, freq='1h')
    data = pd.DataFrame({
        'timestamp': dates,
        'high': np.random.randn(24) * 100 + 50000,
        'low': np.random.randn(24) * 100 + 49500,
        'close': np.random.randn(24) * 100 + 49750,
        'volume': np.random.rand(24) * 1000
    })
    
    settlement = USSettlement()
    
    print("=" * 80)
    print("US SETTLEMENT DETECTOR - TEST RESULTS")
    print("=" * 80)
    
    for i in range(len(data)):
        result = settlement.analyze(data.iloc[:i+1])
        is_new = result['metadata']['is_new_event']
        magnet = result['metadata']['has_magnet_effect']
        event_marker = "🆕 " if is_new else ""
        magnet_marker = "🧲 " if magnet else ""
        print(f"{data['timestamp'].iloc[i]}: {event_marker}{magnet_marker}{result['signal']} ({result['confidence']}%)")
    print("=" * 80)
