"""
LuxAlgo ICT Silver Bullet - Core Implementation
===============================================

ICT (Inner Circle Trader) Silver Bullet indicator for identifying Fair Value
Gap (FVG) patterns during critical trading sessions and drawing support/
resistance lines based on market structure analysis.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import time, datetime, timedelta


class SessionType(Enum):
    """Silver Bullet session types."""
    LONDON_OPEN = 'london_open'      # 3 AM - 4 AM NY time
    AM_SESSION = 'am_session'         # 10 AM - 11 AM NY time
    PM_SESSION = 'pm_session'         # 2 PM - 3 PM NY time
    OTHER = 'other'


class TrendDirection(Enum):
    """Market trend direction."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    RANGING = 'ranging'


class FVGMode(Enum):
    """FVG display modes."""
    ALL = 'all'
    TREND_ALIGNED = 'trend_aligned'
    STRICT = 'strict'
    SUPER_STRICT = 'super_strict'


@dataclass
class FairValueGap:
    """Fair Value Gap detection result."""
    timestamp: pd.Timestamp
    session_type: SessionType
    gap_type: str  # 'bullish' or 'bearish'
    gap_high: float
    gap_low: float
    gap_size: float
    gap_pct: float
    is_retested: bool = False
    retest_bar: Optional[pd.Timestamp] = None
    trend_aligned: bool = False
    is_valid: bool = True  # Based on FVG mode
    
    def contains_price(self, price: float) -> bool:
        """Check if price is within FVG range."""
        return self.gap_low <= price <= self.gap_high


@dataclass
class SupportResistanceLine:
    """Support or resistance line from FVG."""
    timestamp: pd.Timestamp
    session_type: SessionType
    line_type: str  # 'support' or 'resistance'
    level: float
    source_fvg: FairValueGap
    is_touched: bool = False
    touch_timestamp: Optional[pd.Timestamp] = None
    min_framework: float = 0.0  # Expected move target


class SilverBulletSession:
    """Represents a single Silver Bullet session."""
    
    LONDON_OPEN_START = time(3, 0)
    LONDON_OPEN_END = time(4, 0)
    AM_SESSION_START = time(10, 0)
    AM_SESSION_END = time(11, 0)
    PM_SESSION_START = time(14, 0)
    PM_SESSION_END = time(15, 0)
    
    @staticmethod
    def get_session_type(timestamp: pd.Timestamp) -> SessionType:
        """Determine session type from timestamp (NY time)."""
        bar_time = timestamp.time()
        
        if SilverBulletSession.LONDON_OPEN_START <= bar_time < SilverBulletSession.LONDON_OPEN_END:
            return SessionType.LONDON_OPEN
        elif SilverBulletSession.AM_SESSION_START <= bar_time < SilverBulletSession.AM_SESSION_END:
            return SessionType.AM_SESSION
        elif SilverBulletSession.PM_SESSION_START <= bar_time < SilverBulletSession.PM_SESSION_END:
            return SessionType.PM_SESSION
        else:
            return SessionType.OTHER
    
    @staticmethod
    def get_session_name(session_type: SessionType) -> str:
        """Get readable session name."""
        names = {
            SessionType.LONDON_OPEN: 'London Open (3-4 AM)',
            SessionType.AM_SESSION: 'AM Session (10-11 AM)',
            SessionType.PM_SESSION: 'PM Session (2-3 PM)',
            SessionType.OTHER: 'Other',
        }
        return names.get(session_type, 'Unknown')


class FairValueGapDetector:
    """Detect Fair Value Gaps in price data."""
    
    @staticmethod
    def detect_bullish_fvg(bar1: pd.Series, bar2: pd.Series, bar3: pd.Series) -> Optional[FairValueGap]:
        """
        Detect bullish FVG (gap up).
        Pattern: Bar1 up, Bar2 up, Gap between Bar1 high and Bar2 low
        
        Args:
            bar1, bar2, bar3: Consecutive OHLC bars
        
        Returns:
            FairValueGap if detected
        """
        # Bullish FVG: low of bar2 > high of bar1 (gap up)
        if bar2['low'] > bar1['high']:
            gap_high = bar2['low']
            gap_low = bar1['high']
            
            return {
                'type': 'bullish',
                'high': gap_high,
                'low': gap_low,
                'size': gap_high - gap_low,
            }
        return None
    
    @staticmethod
    def detect_bearish_fvg(bar1: pd.Series, bar2: pd.Series, bar3: pd.Series) -> Optional[FairValueGap]:
        """
        Detect bearish FVG (gap down).
        Pattern: Bar1 down, Bar2 down, Gap between Bar1 low and Bar2 high
        
        Args:
            bar1, bar2, bar3: Consecutive OHLC bars
        
        Returns:
            FairValueGap if detected
        """
        # Bearish FVG: high of bar2 < low of bar1 (gap down)
        if bar2['high'] < bar1['low']:
            gap_low = bar2['high']
            gap_high = bar1['low']
            
            return {
                'type': 'bearish',
                'high': gap_high,
                'low': gap_low,
                'size': gap_high - gap_low,
            }
        return None
    
    @staticmethod
    def detect_fvg_in_session(session_bars: List[pd.Series]) -> List[Dict]:
        """Detect all FVGs within a session."""
        fvgs = []
        
        for i in range(len(session_bars) - 2):
            bar1 = session_bars[i]
            bar2 = session_bars[i + 1]
            bar3 = session_bars[i + 2]
            
            # Try bullish FVG
            bullish = FairValueGapDetector.detect_bullish_fvg(bar1, bar2, bar3)
            if bullish:
                fvgs.append(bullish)
            
            # Try bearish FVG
            bearish = FairValueGapDetector.detect_bearish_fvg(bar1, bar2, bar3)
            if bearish:
                fvgs.append(bearish)
        
        return fvgs


class TrendAnalyzer:
    """Analyze market trend using zigzag pattern."""
    
    @staticmethod
    def detect_trend(prices: List[float], length: int = 5) -> TrendDirection:
        """
        Detect trend using simple comparison.
        
        Args:
            prices: List of prices
            length: Lookback length
        
        Returns:
            TrendDirection enum
        """
        if len(prices) < length:
            return TrendDirection.RANGING
        
        recent = prices[-length:]
        avg_recent = np.mean(recent)
        prev_avg = np.mean(prices[-(length*2):-length])
        
        if avg_recent > prev_avg * 1.01:
            return TrendDirection.BULLISH
        elif avg_recent < prev_avg * 0.99:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.RANGING
    
    @staticmethod
    def calculate_swing_highs_lows(df: pd.DataFrame, length: int = 5) -> Tuple[List[float], List[float]]:
        """
        Calculate swing highs and lows using zigzag pattern.
        
        Args:
            df: OHLCV DataFrame
            length: Zigzag sensitivity
        
        Returns:
            Tuple of (swing_highs, swing_lows)
        """
        swing_highs = []
        swing_lows = []
        
        for i in range(length, len(df) - length):
            window = df.iloc[i-length:i+length+1]
            
            if window['high'].iloc[length] == window['high'].max():
                swing_highs.append(window['high'].iloc[length])
            
            if window['low'].iloc[length] == window['low'].min():
                swing_lows.append(window['low'].iloc[length])
        
        return swing_highs, swing_lows


class SupportResistanceBuilder:
    """Build support and resistance lines from FVGs."""
    
    @staticmethod
    def calculate_sr_from_fvg(fvg: Dict, fvg_type: str,
                            trend: TrendDirection) -> Dict:
        """
        Create S/R lines from FVG.
        
        Args:
            fvg: FVG data
            fvg_type: 'bullish' or 'bearish'
            trend: Market trend direction
        
        Returns:
            S/R line configuration
        """
        if fvg_type == 'bullish' and trend == TrendDirection.BULLISH:
            # Support level at FVG low
            return {
                'type': 'support',
                'level': fvg['low'],
                'trend_aligned': True,
            }
        elif fvg_type == 'bearish' and trend == TrendDirection.BEARISH:
            # Resistance level at FVG high
            return {
                'type': 'resistance',
                'level': fvg['high'],
                'trend_aligned': True,
            }
        else:
            # Counter-trend
            if fvg_type == 'bullish':
                return {
                    'type': 'resistance',
                    'level': fvg['high'],
                    'trend_aligned': False,
                }
            else:
                return {
                    'type': 'support',
                    'level': fvg['low'],
                    'trend_aligned': False,
                }
    
    @staticmethod
    def calculate_min_trade_framework(level: float, line_type: str,
                                     market_type: str = 'equities') -> float:
        """
        Calculate minimum trade framework (mTFW) - expected move target.
        
        Args:
            level: S/R line level
            line_type: 'support' or 'resistance'
            market_type: 'equities', 'futures', or 'forex'
        
        Returns:
            Target price level
        """
        if market_type == 'futures' or market_type == 'indices':
            framework = 40  # ticks
            pct_move = (framework / level) * 100 / 100  # Convert to pct
        elif market_type == 'forex':
            framework = 15  # pips
            pct_move = (framework / 10000)  # Forex pips to pct
        else:
            pct_move = 0.02  # 2% default
        
        if line_type == 'support':
            return level - (level * pct_move)
        else:
            return level + (level * pct_move)


class SilverBulletIndicator:
    """Complete ICT Silver Bullet analysis system."""
    
    def __init__(self, fvg_mode: FVGMode = FVGMode.TREND_ALIGNED,
                 swing_length: int = 5,
                 market_type: str = 'equities'):
        """
        Initialize Silver Bullet indicator.
        
        Args:
            fvg_mode: FVG display mode
            swing_length: Zigzag/swing sensitivity
            market_type: 'equities', 'futures', or 'forex'
        """
        self.fvg_mode = fvg_mode
        self.swing_length = swing_length
        self.market_type = market_type
        self.fvg_detector = FairValueGapDetector()
        self.trend_analyzer = TrendAnalyzer()
        self.sr_builder = SupportResistanceBuilder()
    
    def analyze(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Complete Silver Bullet analysis.
        
        Args:
            df: OHLCV DataFrame (intraday, NY timezone)
        
        Returns:
            Tuple of (DataFrame with analysis, dict with results)
        """
        # Detect trend
        trend = self.trend_analyzer.detect_trend(df['close'].tolist(), self.swing_length)
        
        # Group by session
        sessions = self._group_by_session(df)
        
        # Analyze each session
        all_fvgs = []
        all_sr_lines = []
        session_data = {}
        
        for session_type, session_df in sessions.items():
            if len(session_df) < 3:
                continue
            
            # Detect FVGs in session
            fvgs = self._detect_fvgs_in_session(session_df, session_type, trend)
            all_fvgs.extend(fvgs)
            
            # Build S/R lines
            sr_lines = self._build_sr_lines(fvgs, session_type, trend)
            all_sr_lines.extend(sr_lines)
            
            session_data[session_type] = {
                'fvgs': fvgs,
                'sr_lines': sr_lines,
                'bars': len(session_df),
            }
        
        # Retest FVGs
        self._check_fvg_retests(all_fvgs, df)
        
        # Check S/R touches
        self._check_sr_touches(all_sr_lines, df)
        
        # Add to DataFrame
        df_result = df.copy()
        df_result['sb_session'] = df.index.map(lambda x: SilverBulletSession.get_session_type(x).value)
        df_result['sb_fvg_count'] = 0
        
        return df_result, {
            'trend': trend.value,
            'fvgs': all_fvgs,
            'sr_lines': all_sr_lines,
            'sessions': session_data,
        }
    
    def _group_by_session(self, df: pd.DataFrame) -> Dict[SessionType, pd.DataFrame]:
        """Group bars by Silver Bullet session."""
        sessions = {}
        
        for session_type in [SessionType.LONDON_OPEN, SessionType.AM_SESSION, SessionType.PM_SESSION]:
            session_bars = []
            for idx, row in df.iterrows():
                if SilverBulletSession.get_session_type(idx) == session_type:
                    session_bars.append(row)
            
            if session_bars:
                sessions[session_type] = pd.DataFrame(session_bars)
        
        return sessions
    
    def _detect_fvgs_in_session(self, session_df: pd.DataFrame,
                               session_type: SessionType,
                               trend: TrendDirection) -> List[Dict]:
        """Detect FVGs within a specific session."""
        fvgs = []
        
        for i in range(len(session_df) - 2):
            bar1 = session_df.iloc[i]
            bar2 = session_df.iloc[i + 1]
            bar3 = session_df.iloc[i + 2]
            
            # Bullish FVG
            if bar2['low'] > bar1['high']:
                fvg = {
                    'timestamp': bar2.name,
                    'session': session_type,
                    'type': 'bullish',
                    'high': bar2['low'],
                    'low': bar1['high'],
                    'size': bar2['low'] - bar1['high'],
                    'trend_aligned': trend == TrendDirection.BULLISH,
                }
                
                # Check FVG mode
                if self._should_display_fvg(fvg, trend):
                    fvgs.append(fvg)
            
            # Bearish FVG
            if bar2['high'] < bar1['low']:
                fvg = {
                    'timestamp': bar2.name,
                    'session': session_type,
                    'type': 'bearish',
                    'high': bar1['low'],
                    'low': bar2['high'],
                    'size': bar1['low'] - bar2['high'],
                    'trend_aligned': trend == TrendDirection.BEARISH,
                }
                
                # Check FVG mode
                if self._should_display_fvg(fvg, trend):
                    fvgs.append(fvg)
        
        return fvgs
    
    def _should_display_fvg(self, fvg: Dict, trend: TrendDirection) -> bool:
        """Determine if FVG should be displayed based on mode."""
        if self.fvg_mode == FVGMode.ALL:
            return True
        elif self.fvg_mode == FVGMode.TREND_ALIGNED:
            return fvg['trend_aligned']
        elif self.fvg_mode == FVGMode.STRICT:
            # Strict: trend-aligned only
            return fvg['trend_aligned']
        elif self.fvg_mode == FVGMode.SUPER_STRICT:
            # Super-strict: trend-aligned with no break in opposite direction
            return fvg['trend_aligned']
        return False
    
    def _build_sr_lines(self, fvgs: List[Dict], session_type: SessionType,
                       trend: TrendDirection) -> List[Dict]:
        """Build support and resistance lines from FVGs."""
        sr_lines = []
        
        for fvg in fvgs:
            line = self.sr_builder.calculate_sr_from_fvg(
                fvg, fvg['type'], trend
            )
            
            # Calculate minimum trade framework
            line['min_framework'] = self.sr_builder.calculate_min_trade_framework(
                line['level'], line['type'], self.market_type
            )
            
            sr_lines.append(line)
        
        return sr_lines
    
    def _check_fvg_retests(self, fvgs: List[Dict], df: pd.DataFrame):
        """Check if FVGs are retested."""
        for fvg in fvgs:
            fvg_time = fvg['timestamp']
            fvg_idx = df.index.get_loc(fvg_time) if fvg_time in df.index else None
            
            if fvg_idx is None:
                continue
            
            # Check bars after FVG
            for i in range(fvg_idx + 1, len(df)):
                bar = df.iloc[i]
                
                # Check if price touched FVG
                if fvg['low'] <= bar['low'] <= fvg['high']:
                    fvg['retested'] = True
                    fvg['retest_bar'] = df.index[i]
                    break
    
    def _check_sr_touches(self, sr_lines: List[Dict], df: pd.DataFrame):
        """Check if S/R lines are touched."""
        for line in sr_lines:
            for idx, row in df.iterrows():
                # Check if price touched level
                if abs(row['close'] - line['level']) < (line['level'] * 0.001):
                    line['touched'] = True
                    line['touch_time'] = idx
                    break


if __name__ == "__main__":
    import numpy as np
    
    dates = pd.date_range('2024-01-01', periods=500, freq='3min')
    prices = 100 + np.cumsum(np.random.randn(500) * 0.1)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(500) * 0.05,
        'high': prices + np.abs(np.random.randn(500) * 0.1),
        'low': prices - np.abs(np.random.randn(500) * 0.1),
        'close': prices,
        'volume': np.random.randint(1000, 100000, 500),
    }, index=dates)
    
    sb = SilverBulletIndicator(fvg_mode=FVGMode.TREND_ALIGNED, swing_length=5)
    df_result, results = sb.analyze(df)
    
    print("=" * 70)
    print("ICT SILVER BULLET - ANALYSIS")
    print("=" * 70)
    
    print(f"\n✓ Trend: {results['trend'].upper()}")
    print(f"✓ FVGs detected: {len(results['fvgs'])}")
    print(f"✓ S/R lines: {len(results['sr_lines'])}")
    
    for session_type, data in results['sessions'].items():
        print(f"\n{SilverBulletSession.get_session_name(session_type)}")
        print(f"  FVGs: {len(data['fvgs'])}")
        print(f"  S/R Lines: {len(data['sr_lines'])}")
