"""
Base TBD Pattern - Shared Functionality for TBD v2 Modular Patterns

Provides common helpers for all TBD pattern detection layers:
- Peak/trough finding
- ATR calculation
- Session detection
- Risk management helpers
- Pattern validation utilities

Author: BTC Scalp Bot V10 Framework
Version: 2.0.0 (Modular)
Date: December 29, 2025
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from datetime import time
from enum import Enum

from src.core.framework.base_layer import BaseLayer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Session(Enum):
    """Trading Session Types"""
    ASIAN = "asian"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP = "overlap"
    WEEKEND = "weekend"


class BaseTBDPattern(BaseLayer):
    """
    Base class for all TBD v2 modular pattern layers
    
    Provides shared functionality:
    - Peak/trough detection
    - ATR calculation
    - Session identification
    - Risk management helpers
    """
    
    def __init__(self, name: str, config: dict, weight: float = 1.0):
        """
        Initialize base TBD pattern layer
        
        Args:
            name: Layer name
            config: Layer configuration
            weight: Layer weight in compositor
        """
        super().__init__(
            name=name,
            enabled=True,
            weight=weight,
            confidence_threshold=0.5,
            config=config
        )
    
    # ==================== PEAK/TROUGH DETECTION ====================
    
    def _find_peaks(self, values: np.ndarray, order: int = 3) -> List[int]:
        """
        Find local maxima in array
        
        Args:
            values: Array of prices
            order: Number of points on each side to compare
            
        Returns:
            List of peak indices
        """
        peaks = []
        for i in range(order, len(values) - order):
            if all(values[i] >= values[i-j] for j in range(1, order+1)) and \
               all(values[i] >= values[i+j] for j in range(1, order+1)):
                peaks.append(i)
        return peaks
    
    def _find_troughs(self, values: np.ndarray, order: int = 3) -> List[int]:
        """
        Find local minima in array
        
        Args:
            values: Array of prices
            order: Number of points on each side to compare
            
        Returns:
            List of trough indices
        """
        troughs = []
        for i in range(order, len(values) - order):
            if all(values[i] <= values[i-j] for j in range(1, order+1)) and \
               all(values[i] <= values[i+j] for j in range(1, order+1)):
                troughs.append(i)
        return troughs
    
    # ==================== ATR CALCULATION ====================
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Average True Range
        
        Args:
            data: OHLCV DataFrame
            period: ATR period
            
        Returns:
            DataFrame with ATR column added
        """
        high = data['high']
        low = data['low']
        close = data['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        data['atr'] = atr
        return data
    
    def _get_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """
        Get current ATR value
        
        Args:
            data: OHLCV DataFrame
            period: ATR period
            
        Returns:
            Current ATR value
        """
        if 'atr' in data.columns:
            return data['atr'].iloc[-1]
        else:
            data = self._calculate_atr(data, period)
            return data['atr'].iloc[-1]
    
    # ==================== SESSION DETECTION ====================
    
    def _is_uk_dst(self, timestamp: pd.Timestamp) -> bool:
        """
        Check if UK is in daylight saving time (BST)
        DST: Last Sunday in March → Last Sunday in October
        """
        import calendar
        year = timestamp.year
        
        # DST starts last Sunday in March at 01:00 UTC
        march_weeks = calendar.monthcalendar(year, 3)
        march_sundays = [week[-1] for week in march_weeks if week[-1] != 0]
        dst_start = pd.Timestamp(year, 3, march_sundays[-1], 1, 0, tz='UTC')
        
        # DST ends last Sunday in October at 01:00 UTC  
        oct_weeks = calendar.monthcalendar(year, 10)
        oct_sundays = [week[-1] for week in oct_weeks if week[-1] != 0]
        dst_end = pd.Timestamp(year, 10, oct_sundays[-1], 1, 0, tz='UTC')
        
        # Make timestamp timezone-aware if needed
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize('UTC')
        
        return dst_start <= timestamp < dst_end
    
    def _is_us_dst(self, timestamp: pd.Timestamp) -> bool:
        """
        Check if US is in daylight saving time (EDT)
        DST: 2nd Sunday in March → 1st Sunday in November
        """
        import calendar
        year = timestamp.year
        
        # DST starts 2nd Sunday in March at 02:00 UTC
        march_weeks = calendar.monthcalendar(year, 3)
        march_sundays = [week[-1] for week in march_weeks if week[-1] != 0]
        if len(march_sundays) < 2:
            dst_start = pd.Timestamp(year, 3, march_sundays[0] + 7, 2, 0, tz='UTC')
        else:
            dst_start = pd.Timestamp(year, 3, march_sundays[1], 2, 0, tz='UTC')
        
        # DST ends 1st Sunday in November at 02:00 UTC
        nov_weeks = calendar.monthcalendar(year, 11)
        nov_sundays = [week[-1] for week in nov_weeks if week[-1] != 0]
        dst_end = pd.Timestamp(year, 11, nov_sundays[0], 2, 0, tz='UTC')
        
        # Make timestamp timezone-aware if needed
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize('UTC')
        
        return dst_start <= timestamp < dst_end
    
    def _get_current_session(self, timestamp: pd.Timestamp) -> Session:
        """
        Determine current trading session with DST awareness
        
        Args:
            timestamp: Current timestamp
            
        Returns:
            Current session
        """
        hour = timestamp.hour
        day = timestamp.dayofweek

        if day >= 5:  # Weekend
            return Session.WEEKEND

        # Get DST-adjusted session times
        uk_dst = self._is_uk_dst(timestamp)
        us_dst = self._is_us_dst(timestamp)
        
        # UK times (UTC)
        if uk_dst:
            london_start, london_end = 7, 16  # BST
        else:
            london_start, london_end = 8, 17  # GMT
        
        # US times (UTC)
        if us_dst:
            ny_start, ny_end = 12, 21  # EDT
        else:
            ny_start, ny_end = 13, 22  # EST
        
        # Asian session (no DST)
        asian_start, asian_end = 23, 8
        
        # Check for overlap first
        london_active = london_start <= hour < london_end
        ny_active = ny_start <= hour < ny_end
        
        if london_active and ny_active:
            return Session.OVERLAP
        
        # Individual sessions
        if ny_active:
            return Session.NEW_YORK
        elif london_active:
            return Session.LONDON
        elif hour >= asian_start or hour < asian_end:
            return Session.ASIAN
        else:
            return Session.ASIAN  # Default fallback
    
    # ==================== TIMEFRAME DETECTION ====================
    
    def _get_timeframe(self, data: pd.DataFrame) -> str:
        """
        Detect timeframe from data
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Timeframe string
        """
        if len(data) < 2:
            return "Unknown"
        
        if not isinstance(data.index, pd.DatetimeIndex):
            return "Unknown"
        
        time_diff = (data.index[-1] - data.index[-2]).total_seconds() / 60
        
        if time_diff <= 1:
            return "1m"
        elif time_diff <= 5:
            return "5m"
        elif time_diff <= 15:
            return "15m"
        elif time_diff <= 60:
            return "1H"
        elif time_diff <= 240:
            return "4H"
        elif time_diff <= 1440:
            return "1D"
        else:
            return "Unknown"
    
    # ==================== PATTERN CONFIDENCE ====================
    
    def _calculate_pattern_confidence(
        self,
        peak_symmetry: float,
        volume_confirmed: bool,
        pattern_clarity: float
    ) -> float:
        """
        Calculate pattern confidence from multiple factors
        
        Args:
            peak_symmetry: How symmetric the peaks are (0-1)
            volume_confirmed: Whether volume confirms pattern
            pattern_clarity: How clear the pattern is (0-1)
            
        Returns:
            Confidence score (0-1)
        """
        confidence = (
            peak_symmetry * 0.4 +
            (1.0 if volume_confirmed else 0.5) * 0.3 +
            pattern_clarity * 0.3
        )
        return min(confidence, 1.0)
