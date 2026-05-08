"""
ICT Silver Bullet - Building Block
===================================

SIGNAL BLOCK - Detects Fair Value Gap setups in Silver Bullet sessions.

Identifies three institutional trading windows and Fair Value Gaps (FVGs):
- London Open (3-4 AM NY time) 
- AM Session (10-11 AM NY time)
- PM Session (2-3 PM NY time)

Detects bullish/bearish FVGs and generates signals when price retests them.

Based on Inner Circle Trader (ICT) Silver Bullet methodology.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime, time
from enum import Enum
import pandas as pd
import numpy as np

import logging
logger = logging.getLogger(__name__)

class SessionType(Enum):
    """Silver Bullet session types."""
    LONDON_OPEN = "london_open"
    AM_SESSION = "am_session"
    PM_SESSION = "pm_session"
    OTHER = "other"


@register_block(
    name='ict_silver_bullet',
    category='SIGNALS',
    class_name='ICTSilverBullet',
    default_weight=20,
    description='ICT Silver Bullet - ICT-based precision entry during specific kill zone windows (10:00-11:00 NY). Identifies fair value gaps and liquidity sweeps to enter with smart money. Bearish or bullish depending on session context.',
    direction='NEUTRAL',
    valid_signals=[
        # Granular ICT signals
        'BEARISH_FVG_IN_ZONE', 'BEARISH_FVG_RETEST', 'BULLISH_FVG_IN_ZONE', 'BULLISH_FVG_RETEST',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BEARISH_FVG_IN_ZONE': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish FVG in zone - Price in bearish Fair Value Gap. Institutional selling imbalance. Enter shorts. Silver Bullet setup. Stop above gap. Target gap fill.'
        },
        'BEARISH_FVG_RETEST': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish FVG retest - Price retesting bearish Fair Value Gap. High-probability short entry. Institutional distribution zone. Premium signal. Tight stop above gap.'
        },
        'BULLISH_FVG_IN_ZONE': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish FVG in zone - Price in bullish Fair Value Gap. Institutional buying imbalance. Enter longs. Silver Bullet setup. Stop below gap. Target gap fill.'
        },
        'BULLISH_FVG_RETEST': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish FVG retest - Price retesting bullish Fair Value Gap. High-probability long entry. Institutional accumulation zone. Premium signal. Tight stop below gap.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot calculate ICT Silver Bullet signals. Check data quality and timestamp availability.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need at least 50 bars for FVG detection. Wait for more price history.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish Silver Bullet - Bullish FVG detected or retested. Long positions highly favorable. ICT institutional buy zone. High probability setup.'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish Silver Bullet - Bearish FVG detected or retested. Short positions highly favorable. ICT institutional sell zone. High probability setup.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Neutral Silver Bullet - No Fair Value Gaps detected. No institutional imbalances. Wait for Silver Bullet sessions and FVG formation.'
        }
}
)
class ICTSilverBullet:
    """
    ICT Silver Bullet Detector
    
    Building Block Classification: SIGNAL BLOCK
    Mode: SELECTIVE (only on FVG retest setups)
    
    Detects Fair Value Gaps in three institutional trading windows
    and generates signals when price retests these gaps.
    
    Designed for 3-15 min intraday bars.
    """
    
    # Session times (NY timezone)
    LONDON_OPEN_START = time(3, 0)
    LONDON_OPEN_END = time(4, 0)
    AM_SESSION_START = time(10, 0)
    AM_SESSION_END = time(11, 0)
    PM_SESSION_START = time(14, 0)
    PM_SESSION_END = time(15, 0)
    
    def __init__(
        self,
        timeframe: str = '15min',
        min_gap_pct: float = 0.02,
        trend_aligned_only: bool = False,
        **kwargs
    ):
        """
        Initialize ICT Silver Bullet detector.
        
        Args:
            timeframe: Timeframe (e.g., '3min', '5min', '15min')
            min_gap_pct: Minimum gap size as % of price (0.02 = 0.02%)
            trend_aligned_only: Only show trend-aligned FVGs
        """
        self.timeframe = timeframe
        self.min_gap_pct = min_gap_pct
        self.trend_aligned_only = trend_aligned_only
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for Silver Bullet FVG signals.
        
        Compatible with building block interface.
        """
        try:
            # Validation
            required_cols = {'open', 'high', 'low', 'close', 'timestamp'}
            if not required_cols.issubset(df.columns):
                return {
                    'signal': 'ERROR',
                    'confidence': 0,
                    'metadata': {'error': 'Missing required columns'},
                    'timestamp': datetime.now(),
                    'timeframe': self.timeframe,
                    'confluence_factors': []
                }
            
            min_bars = 50
            if len(df) < min_bars:
                return {
                    'signal': 'INSUFFICIENT_DATA',
                    'confidence': 0,
                    'metadata': {'error': f'Need at least {min_bars} bars'},
                    'timestamp': datetime.now(),
                    'timeframe': self.timeframe,
                    'confluence_factors': []
                }
            
            # Detect trend
            trend = self._detect_trend(df['close'].tail(20))
            
            # Detect current session
            current_timestamp = df['timestamp'].iloc[-1]
            current_session = self._get_session_type(current_timestamp)
            
            # Find FVGs in recent bars
            fvgs = self._detect_fvgs(df.tail(50), trend)
            
            if not fvgs:
                return self._generate_neutral_signal(
                    current_timestamp,
                    df['close'].iloc[-1],
                    current_session,
                    trend
                )
            
            # Check for retest setup
            current_price = df['close'].iloc[-1]
            retest_setup = self._check_fvg_retest(fvgs, current_price, df.tail(10))
            
            if retest_setup:
                return self._generate_signal(
                    retest_setup,
                    current_timestamp,
                    current_price,
                    current_session,
                    trend
                )
            
            # No retest - just report FVG presence
            return self._generate_fvg_present_signal(
                fvgs,
                current_timestamp,
                current_price,
                current_session,
                trend
            )
            
        except Exception as e:
            # Graceful error handling - return neutral signal
            try:
                timestamp = df['timestamp'].iloc[-1] if len(df) > 0 else datetime.now()
                price = df['close'].iloc[-1] if len(df) > 0 else 0
            except:
                timestamp = datetime.now()
                price = 0
            
            return {
                'signal': 'NEUTRAL',
                'confidence': 50,
                'metadata': {
                    'current_price': round(price, 2) if price > 0 else 0,
                    'session': 'other',
                    'trend': 'ranging',
                    'fvg_count': 0,
                    'is_new_event': False,
                    'error_caught': str(e)[:100],
                },
                'timestamp': timestamp,
                'timeframe': self.timeframe,
                'confluence_factors': ['Error handled gracefully']
            }
    
    def _get_session_type(self, timestamp: datetime) -> SessionType:
        """Determine Silver Bullet session from timestamp."""
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        
        bar_time = timestamp.time()
        
        if self.LONDON_OPEN_START <= bar_time < self.LONDON_OPEN_END:
            return SessionType.LONDON_OPEN
        elif self.AM_SESSION_START <= bar_time < self.AM_SESSION_END:
            return SessionType.AM_SESSION
        elif self.PM_SESSION_START <= bar_time < self.PM_SESSION_END:
            return SessionType.PM_SESSION
        else:
            return SessionType.OTHER
    
    def _detect_trend(self, prices: pd.Series) -> str:
        """Detect trend using simple comparison."""
        if len(prices) < 10:
            return 'ranging'
        
        recent = prices.tail(10).mean()
        prev = prices.head(10).mean()
        
        if recent > prev * 1.005:
            return 'bullish'
        elif recent < prev * 0.995:
            return 'bearish'
        else:
            return 'ranging'
    
    def _detect_fvgs(self, df: pd.DataFrame, trend: str) -> List[Dict]:
        """
        Detect Fair Value Gaps in recent bars.
        
        NOTE: On 15min+ timeframes, true gaps are rare (24/7 markets).
        Using 3-bar imbalance method as alternative.
        """
        fvgs = []
        
        for i in range(len(df) - 2):
            bar1 = df.iloc[i]
            bar2 = df.iloc[i + 1]
            bar3 = df.iloc[i + 2]
            
            # Method 1: Classic gap (rare on 15min)
            # Bullish FVG: gap up (bar2 low > bar1 high)
            if bar2['low'] > bar1['high']:
                gap_size = bar2['low'] - bar1['high']
                gap_pct = (gap_size / bar1['close']) * 100
                
                if gap_pct >= self.min_gap_pct:
                    is_trend_aligned = (trend == 'bullish')
                    
                    if not self.trend_aligned_only or is_trend_aligned:
                        fvg = {
                            'type': 'bullish',
                            'timestamp': bar2['timestamp'],
                            'high': bar2['low'],
                            'low': bar1['high'],
                            'size': gap_size,
                            'size_pct': gap_pct,
                            'support_level': bar1['high'],
                            'trend_aligned': is_trend_aligned,
                            'session': self._get_session_type(bar2['timestamp']),
                        }
                        fvgs.append(fvg)
            
            # Bearish FVG: gap down (bar2 high < bar1 low)
            elif bar2['high'] < bar1['low']:
                gap_size = bar1['low'] - bar2['high']
                gap_pct = (gap_size / bar1['close']) * 100
                
                if gap_pct >= self.min_gap_pct:
                    is_trend_aligned = (trend == 'bearish')
                    
                    if not self.trend_aligned_only or is_trend_aligned:
                        fvg = {
                            'type': 'bearish',
                            'timestamp': bar2['timestamp'],
                            'high': bar1['low'],
                            'low': bar2['high'],
                            'size': gap_size,
                            'size_pct': gap_pct,
                            'resistance_level': bar1['low'],
                            'trend_aligned': is_trend_aligned,
                            'session': self._get_session_type(bar2['timestamp']),
                        }
                        fvgs.append(fvg)
            
            # Method 2: 3-bar imbalance (works on 15min)
            # Bullish imbalance: bar3 low > bar1 high (bar2 is the imbalance)
            elif bar3['low'] > bar1['high']:
                gap_size = bar3['low'] - bar1['high']
                gap_pct = (gap_size / bar2['close']) * 100
                
                if gap_pct >= self.min_gap_pct:
                    is_trend_aligned = (trend == 'bullish')
                    
                    if not self.trend_aligned_only or is_trend_aligned:
                        fvg = {
                            'type': 'bullish',
                            'timestamp': bar2['timestamp'],
                            'high': bar3['low'],
                            'low': bar1['high'],
                            'size': gap_size,
                            'size_pct': gap_pct,
                            'support_level': bar1['high'],
                            'trend_aligned': is_trend_aligned,
                            'session': self._get_session_type(bar2['timestamp']),
                        }
                        fvgs.append(fvg)
            
            # Bearish imbalance: bar3 high < bar1 low
            elif bar3['high'] < bar1['low']:
                gap_size = bar1['low'] - bar3['high']
                gap_pct = (gap_size / bar2['close']) * 100
                
                if gap_pct >= self.min_gap_pct:
                    is_trend_aligned = (trend == 'bearish')
                    
                    if not self.trend_aligned_only or is_trend_aligned:
                        fvg = {
                            'type': 'bearish',
                            'timestamp': bar2['timestamp'],
                            'high': bar1['low'],
                            'low': bar3['high'],
                            'size': gap_size,
                            'size_pct': gap_pct,
                            'resistance_level': bar1['low'],
                            'trend_aligned': is_trend_aligned,
                            'session': self._get_session_type(bar2['timestamp']),
                        }
                        fvgs.append(fvg)
        
        return fvgs
    
    def _check_fvg_retest(self, fvgs: List[Dict], current_price: float,
                         recent_bars: pd.DataFrame) -> Optional[Dict]:
        """Check if price is retesting an FVG."""
        if len(recent_bars) < 2:
            return None
        
        try:
            for fvg in reversed(fvgs):  # Check most recent first
                # Check if price is in FVG zone
                in_zone = fvg['low'] <= current_price <= fvg['high']
                
                if in_zone:
                    # Check if this is a retest (price was outside before)
                    prev_prices = recent_bars['close'].iloc[:-1]
                    
                    # Need at least 1 previous price
                    if len(prev_prices) == 0:
                        return {
                            'fvg': fvg,
                            'retest_price': current_price,
                            'is_retest': False,
                        }
                    
                    # Check last 3 bars (or fewer if not available)
                    check_count = min(3, len(prev_prices))
                    prev_to_check = prev_prices.tail(check_count)
                    
                    was_outside = all(
                        (p < fvg['low']) or (p > fvg['high'])
                        for p in prev_to_check
                    )
                    
                    if was_outside:
                        # Valid retest setup
                        return {
                            'fvg': fvg,
                            'retest_price': current_price,
                            'is_retest': True,
                        }
                    else:
                        # In zone but not a retest
                        return {
                            'fvg': fvg,
                            'retest_price': current_price,
                            'is_retest': False,
                        }
            
            return None
            
        except Exception:
            # Graceful fallback - treat as no retest
            return None
    
    def _generate_signal(
        self,
        retest_setup: Dict,
        timestamp: datetime,
        current_price: float,
        session: SessionType,
        trend: str
    ) -> Dict[str, Any]:
        """Generate signal for FVG retest."""
        fvg = retest_setup['fvg']
        is_retest = retest_setup['is_retest']
        
        # Determine signal type (granular)
        if fvg['type'] == 'bullish':
            granular_signal = 'BULLISH_FVG_RETEST' if is_retest else 'BULLISH_FVG_IN_ZONE'
            simple_signal = 'BULLISH'
        else:
            granular_signal = 'BEARISH_FVG_RETEST' if is_retest else 'BEARISH_FVG_IN_ZONE'
            simple_signal = 'BEARISH'
        
        # Calculate confidence
        base_confidence = 65
        
        if is_retest:
            base_confidence += 15  # Retest is higher quality
        
        if fvg['trend_aligned']:
            base_confidence += 10  # Trend alignment
        
        if session in [SessionType.AM_SESSION, SessionType.PM_SESSION]:
            base_confidence += 5  # Premium sessions
        
        if fvg['size_pct'] > 0.3:
            base_confidence += 5  # Larger gap = institutional
        
        confidence = max(50, min(90, base_confidence))
        
        # Calculate targets
        if fvg['type'] == 'bullish':
            stop_loss = fvg['low'] * 0.998
            target = fvg['high'] * 1.015
        else:
            stop_loss = fvg['high'] * 1.002
            target = fvg['low'] * 0.985
        
        risk = abs(current_price - stop_loss)
        reward = abs(target - current_price)
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': confidence,
            'metadata': {
                'signal_simple': simple_signal,
               'signal_granular': granular_signal,
                'fvg_type': fvg['type'],
                'fvg_size': round(fvg['size'], 2),
                'fvg_size_pct': round(fvg['size_pct'], 3),
                'fvg_high': round(fvg['high'], 2),
                'fvg_low': round(fvg['low'], 2),
                'current_price': round(current_price, 2),
                'session': session.value,
                'trend': trend,
                'trend_aligned': fvg['trend_aligned'],
                'is_retest': is_retest,
                'support_resistance': round(fvg.get('support_level', fvg.get('resistance_level', 0)), 2),
                'stop_loss': round(stop_loss, 2),
                'target': round(target, 2),
                'risk_reward_ratio': round(risk_reward, 2),
                'is_new_event': is_retest,  # Only retests are new events
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': self._get_confluence_factors(
                fvg, is_retest, session, trend
            )
        }
    
    def _generate_fvg_present_signal(
        self,
        fvgs: List[Dict],
        timestamp: datetime,
        current_price: float,
        session: SessionType,
        trend: str
    ) -> Dict[str, Any]:
        """Generate signal when FVG present but no retest yet."""
        latest_fvg = fvgs[-1]
        
        return {
            'signal': 'FVG_PRESENT',
            'confidence': 50,
            'metadata': {
                'fvg_type': latest_fvg['type'],
                'fvg_count': len(fvgs),
                'current_price': round(current_price, 2),
                'session': session.value,
                'trend': trend,
                'nearest_fvg_distance': round(
                    min(
                        abs(current_price - fvg['high']),
                        abs(current_price - fvg['low'])
                    )
                    for fvg in fvgs
                ),
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'{len(fvgs)} FVGs detected',
                f'Session: {session.value}',
                f'Trend: {trend}'
            ]
        }
    
    def _generate_neutral_signal(
        self,
        timestamp: datetime,
        current_price: float,
        session: SessionType,
        trend: str
    ) -> Dict[str, Any]:
        """Generate neutral signal when no FVGs detected."""
        return {
            'signal': 'NEUTRAL',
            'confidence': 50,
            'metadata': {
                'current_price': round(current_price, 2),
                'session': session.value,
                'trend': trend,
                'fvg_count': 0,
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': ['No FVGs detected']
        }
    
    def _get_confluence_factors(
        self,
        fvg: Dict,
        is_retest: bool,
        session: SessionType,
        trend: str
    ) -> List[str]:
        """Get confluence factors for signal."""
        factors = []
        
        factors.append(f'FVG {fvg["type"]} ({fvg["size_pct"]:.2f}%)')
        
        if is_retest:
            factors.append('Price retesting FVG')
        else:
            factors.append('Price in FVG zone')
        
        if fvg['trend_aligned']:
            factors.append(f'Trend-aligned ({trend})')
        
        factors.append(f'Session: {session.value}')
        
        if fvg['size_pct'] > 0.3:
            factors.append('Large gap (institutional)')
        
        return factors


if __name__ == "__main__":
    logger.info("ICT Silver Bullet - Building Block")
    logger.info("SIGNAL BLOCK - Fair Value Gap retest setups")
    logger.info("Based on Inner Circle Trader methodology")
