"""
Initial Balance Breakout - Building Block
==========================================

EVENT BLOCK - Detects breakouts from the Initial Balance (IB) range.

The Initial Balance is the high/low range formed during the first trading period
(typically first hour for stocks, or first 2 hours for crypto 24/7 markets).

Signals:
- BULLISH_BREAKOUT: Price breaks above IB high
- BEARISH_BREAKOUT: Price breaks below IB low  
- IB_FORMED: New IB session detected
- INSIDE_IB: Price inside the IB range
- NO_IB: No IB detected yet

Based on LuxAlgo Initial Balance concept, adapted for BTC_Engine_v3 framework.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, time, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class InitialBalanceRange:
    """Represents an Initial Balance period."""
    session_start: datetime
    session_end: datetime
    high: float
    low: float
    range_size: float
    midpoint: float
    volume_total: float
    
    def contains_price(self, price: float) -> bool:
        """Check if price is within IB range."""
        return self.low <= price <= self.high
    
    def is_above(self, price: float) -> bool:
        """Check if price is above IB high."""
        return price > self.high
    
    def is_below(self, price: float) -> bool:
        """Check if price is below IB low."""
        return price < self.low


class InitialBalanceBreakout:
    """
    Initial Balance Breakout Detector
    
    Building Block Classification: EVENT BLOCK
    Mode: SELECTIVE (fires on IB formation and breakouts)
    
    For crypto (24/7 markets): Uses daily session starting at 00:00 UTC
    For stocks: Would use market hours (9:30-10:30 AM typically)
    
    Designed for 15-min bars.
    """
    
    def __init__(
        self,
        timeframe: str = '15min',
        session_start_hour: int = 0,  # UTC midnight for crypto
        session_start_min: int = 0,
        ib_duration_minutes: int = 120,  # 2 hours for crypto (8 bars @ 15min)
        volume_threshold: float = 1.3,  # Volume confirmation multiplier
        min_ib_range_atr: float = 0.3,  # Minimum IB range (% of ATR)
        **kwargs
    ):
        """
        Initialize Initial Balance Breakout detector.
        
        Args:
            timeframe: Timeframe (e.g., '15min')
            session_start_hour: Hour when session starts (0-23, UTC for crypto)
            session_start_min: Minute when session starts (0-59)
            ib_duration_minutes: Duration of IB period in minutes (default: 120 = 2 hours)
            volume_threshold: Volume multiplier for breakout confirmation
            min_ib_range_atr: Minimum IB range as % of ATR (prevent tight ranges)
        """
        self.timeframe = timeframe
        self.session_start_hour = session_start_hour
        self.session_start_min = session_start_min
        self.ib_duration_minutes = ib_duration_minutes
        self.volume_threshold = volume_threshold
        self.min_ib_range_atr = min_ib_range_atr
        
        # State tracking
        self.current_ib: Optional[InitialBalanceRange] = None
        self.last_ib_date: Optional[datetime] = None
        self.breakout_detected = False
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for Initial Balance and breakouts.
        
        Compatible with building block interface.
        """
        # Validation
        required_cols = {'open', 'high', 'low', 'close', 'volume', 'timestamp'}
        if not required_cols.issubset(df.columns):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 20:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'Need at least 20 bars'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_time = df['timestamp'].iloc[-1]
        current_price = df['close'].iloc[-1]
        current_date = current_time.date()
        
        # Calculate ATR for validation
        atr = self._calculate_atr(df.tail(14))
        
        # Check if we need to detect new IB
        if self.last_ib_date != current_date or self.current_ib is None:
            self.current_ib = self._detect_ib(df, current_time, atr)
            self.last_ib_date = current_date
            self.breakout_detected = False
            
            if self.current_ib:
                # New IB formed
                return self._generate_ib_formed_signal(current_time, self.current_ib)
        
        # No IB yet
        if not self.current_ib:
            return {
                'signal': 'NO_IB',
                'confidence': 50,
                'metadata': {
                    'reason': 'IB session hasn\'t completed yet',
                    'session_start': self._get_session_start(current_time).isoformat(),
                },
                'timestamp': current_time,
                'timeframe': self.timeframe,
                'confluence_factors': ['Waiting for IB to form']
            }
        
        # Check for breakout
        avg_volume = df['volume'].tail(20).mean()
        volume_confirmed = df['volume'].iloc[-1] > (avg_volume * self.volume_threshold)
        
        # Bullish breakout
        if self.current_ib.is_above(current_price):
            if not self.breakout_detected:  # First breakout
                self.breakout_detected = True
                return self._generate_breakout_signal(
                    current_time, current_price, 'BULLISH_BREAKOUT',
                    self.current_ib, volume_confirmed, atr, df
                )
            else:
                # Continuing breakout state
                return self._generate_continuation_signal(
                    current_time, current_price, 'ABOVE_IB',
                    self.current_ib, volume_confirmed
                )
        
        # Bearish breakout
        elif self.current_ib.is_below(current_price):
            if not self.breakout_detected:  # First breakout
                self.breakout_detected = True
                return self._generate_breakout_signal(
                    current_time, current_price, 'BEARISH_BREAKOUT',
                    self.current_ib, volume_confirmed, atr, df
                )
            else:
                # Continuing breakout state
                return self._generate_continuation_signal(
                    current_time, current_price, 'BELOW_IB',
                    self.current_ib, volume_confirmed
                )
        
        # Inside IB
        else:
            self.breakout_detected = False  # Reset if back inside
            return self._generate_inside_ib_signal(
                current_time, current_price, self.current_ib
            )
    
    def _detect_ib(
        self, df: pd.DataFrame, current_time: datetime, atr: float
    ) -> Optional[InitialBalanceRange]:
        """Detect the Initial Balance for current session."""
        session_start = self._get_session_start(current_time)
        session_end = session_start + timedelta(minutes=self.ib_duration_minutes)
        
        # Get bars within IB session
        ib_mask = (df['timestamp'] >= session_start) & (df['timestamp'] < session_end)
        ib_df = df[ib_mask]
        
        if len(ib_df) == 0:
            return None
        
        # Calculate IB
        ib_high = ib_df['high'].max()
        ib_low = ib_df['low'].min()
        ib_range = ib_high - ib_low
        
        # Validate minimum range
        if atr > 0 and ib_range < (atr * self.min_ib_range_atr):
            # IB range too tight, likely consolidation
            ib_range = atr * self.min_ib_range_atr  # Widen slightly
        
        return InitialBalanceRange(
            session_start=session_start,
            session_end=session_end,
            high=ib_high,
            low=ib_low,
            range_size=ib_range,
            midpoint=(ib_high + ib_low) / 2,
            volume_total=ib_df['volume'].sum(),
        )
    
    def _get_session_start(self, timestamp: datetime) -> datetime:
        """Get session start time for given timestamp."""
        session_start = timestamp.replace(
            hour=self.session_start_hour,
            minute=self.session_start_min,
            second=0,
            microsecond=0,
        )
        
        # If current time is before session start, session started yesterday
        if timestamp < session_start:
            session_start -= timedelta(days=1)
        
        return session_start
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.tail(period).mean()
        
        return atr if not np.isnan(atr) else 0
    
    def _generate_ib_formed_signal(
        self, timestamp: datetime, ib: InitialBalanceRange
    ) -> Dict[str, Any]:
        """Generate signal when new IB is formed."""
        return {
            'signal': 'IB_FORMED',
            'confidence': 60,
            'metadata': {
                'ib_high': round(ib.high, 2),
                'ib_low': round(ib.low, 2),
                'ib_midpoint': round(ib.midpoint, 2),
                'ib_range': round(ib.range_size, 2),
                'session_start': ib.session_start.isoformat(),
                'session_end': ib.session_end.isoformat(),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'IB formed: {ib.low:.2f} - {ib.high:.2f}',
                f'Range: {ib.range_size:.2f}',
                f'Midpoint: {ib.midpoint:.2f}',
            ]
        }
    
    def _generate_breakout_signal(
        self,
        timestamp: datetime,
        price: float,
        signal_type: str,
        ib: InitialBalanceRange,
        volume_confirmed: bool,
        atr: float,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Generate breakout signal."""
        # Calculate distance from IB extreme
        if signal_type == 'BULLISH_BREAKOUT':
            distance = price - ib.high
            extreme = ib.high
        else:
            distance = ib.low - price
            extreme = ib.low
        
        # Strength based on distance
        distance_pct = (distance / ib.range_size) if ib.range_size > 0 else 0
        
        if distance_pct >= 0.5:
            strength = 'STRONG'
            confidence = 75
        elif distance_pct >= 0.25:
            strength = 'MEDIUM'
            confidence = 65
        else:
            strength = 'WEAK'
            confidence = 55
        
        # Boost confidence if volume confirmed
        if volume_confirmed:
            confidence += 10
        
        # Calculate bars since IB formation
        try:
            ib_end_idx = df[df['timestamp'] >= ib.session_end].index[0] if len(df[df['timestamp'] >= ib.session_end]) > 0 else 0
            bars_since_ib = len(df) - ib_end_idx - 1
            hours_since_ib = bars_since_ib * 0.25  # 15min bars
        except:
            bars_since_ib = 0
            hours_since_ib = 0.0
        
        # Calculate strength score (fine-grained)
        strength_score = round(distance_pct * 100, 1)  # 0-100 scale
        
        return {
            'signal': signal_type,
            'confidence': min(85, confidence),
            'metadata': {
                'ib_high': round(ib.high, 2),
                'ib_low': round(ib.low, 2),
                'ib_midpoint': round(ib.midpoint, 2),
                'ib_range': round(ib.range_size, 2),
                'breakout_price': round(price, 2),
                'distance_from_ib': round(distance, 2),
                'distance_pct': round(distance_pct * 100, 1),
                'strength': strength,
                'strength_score': strength_score,  # Fine-grained 0-100
                'volume_confirmed': volume_confirmed,
                'is_new_event': True,
                'bars_since_ib': bars_since_ib,
                'hours_since_ib': round(hours_since_ib, 2),
                # Targets (IB extensions)
                'target_25': round(extreme + (ib.range_size * 0.25 * (1 if signal_type == 'BULLISH_BREAKOUT' else -1)), 2),
                'target_50': round(extreme + (ib.range_size * 0.50 * (1 if signal_type == 'BULLISH_BREAKOUT' else -1)), 2),
                'target_100': round(extreme + (ib.range_size * 1.00 * (1 if signal_type == 'BULLISH_BREAKOUT' else -1)), 2),
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'{signal_type.replace("_", " ")} at {price:.2f}',
                f'IB: {ib.low:.2f} - {ib.high:.2f}',
                f'Strength: {strength}',
                f'Volume: {"CONFIRMED" if volume_confirmed else "weak"}',
                f'Distance: {distance:.2f} ({distance_pct*100:.1f}% of IB)',
            ]
        }
    
    def _generate_continuation_signal(
        self,
        timestamp: datetime,
        price: float,
        signal_type: str,
        ib: InitialBalanceRange,
        volume_confirmed: bool,
    ) -> Dict[str, Any]:
        """Generate continuation signal (already in breakout state)."""
        return {
            'signal': signal_type,
            'confidence': 60,
            'metadata': {
                'ib_high': round(ib.high, 2),
                'ib_low': round(ib.low, 2),
                'breakout_continuing': True,
                'volume_confirmed': volume_confirmed,
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Price {signal_type.lower().replace("_", " ")}: {price:.2f}',
                'Breakout continuing',
            ]
        }
    
    def _generate_inside_ib_signal(
        self, timestamp: datetime, price: float, ib: InitialBalanceRange
    ) -> Dict[str, Any]:
        """Generate signal when price is inside IB."""
        # Calculate position within IB
        if ib.range_size > 0:
            position_pct = ((price - ib.low) / ib.range_size) * 100
        else:
            position_pct = 50
        
        # Determine zone
        if position_pct > 70:
            zone = 'UPPER_IB'
            confidence = 55
        elif position_pct < 30:
            zone = 'LOWER_IB'
            confidence = 55
        else:
            zone = 'MID_IB'
            confidence = 50
        
        return {
            'signal': 'INSIDE_IB',
            'confidence': confidence,
            'metadata': {
                'ib_high': round(ib.high, 2),
                'ib_low': round(ib.low, 2),
                'ib_midpoint': round(ib.midpoint, 2),
                'position_pct': round(position_pct, 1),
                'zone': zone,
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': self.timeframe,
            'confluence_factors': [
                f'Price inside IB: {price:.2f}',
                f'IB: {ib.low:.2f} - {ib.high:.2f}',
                f'Position: {position_pct:.0f}% of range',
            ]
        }


if __name__ == "__main__":
    print("Initial Balance Breakout - Building Block")
    print("EVENT BLOCK - Detects IB formation and breakouts")
    print("Based on LuxAlgo methodology")
