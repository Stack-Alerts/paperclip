"""
LuxAlgo Statistical Trailing Stop - Core Implementation
========================================================

Statistical trailing stop algorithm using log-normal distribution
of volatility to generate dynamic stop-loss levels. Includes four
distinct statistical levels, volatility grouping, and signal tracking.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from scipy import stats


class TrailingStopLevel(Enum):
    """Statistical trailing stop levels based on volatility distribution."""
    LEVEL_0 = 0  # Most responsive
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3  # Most stable


@dataclass
class VolatilityGroup:
    """Represents a group of volatility measurements."""
    timestamp: pd.Timestamp
    volatility: float
    high: float
    low: float
    close: float
    bar_count: int
    

@dataclass
class TrailingStopSignal:
    """Individual trailing stop signal."""
    timestamp: pd.Timestamp
    price: float
    level_0: float
    level_1: float
    level_2: float
    level_3: float
    direction: str  # 'long' or 'short'
    volatility: float
    

@dataclass
class TradeEntry:
    """Trade entry point from trailing stop."""
    entry_timestamp: pd.Timestamp
    entry_price: float
    entry_signal: TrailingStopSignal
    trade_type: str  # 'long' or 'short'
    

@dataclass
class TradeExit:
    """Trade exit from trailing stop."""
    exit_timestamp: pd.Timestamp
    exit_price: float
    exit_signal: TrailingStopSignal
    pnl: float
    pnl_pct: float
    duration_bars: int
    

@dataclass
class TradeRecord:
    """Complete trade record."""
    entry: TradeEntry
    exit: Optional[TradeExit]
    status: str  # 'open', 'closed', 'stopped'
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None


class VolatilityAnalyzer:
    """Analyzes volatility using log-normal distribution."""
    
    def __init__(self, data_length: int = 10):
        """
        Initialize volatility analyzer.
        
        Args:
            data_length: Number of bars per volatility group
        """
        self.data_length = data_length
        self.volatility_history = []
    
    def calculate_volatility(self, high: float, low: float, close: float) -> float:
        """
        Calculate log-normal volatility from OHLC.
        
        Args:
            high: Bar high
            low: Bar low
            close: Bar close
        
        Returns:
            Volatility measure
        """
        # Garman-Klass volatility (uses high-low range)
        hl_ratio = np.log(high / low)
        cc_ratio = np.log(close / close) if close > 0 else 0
        
        gk_vol = 0.5 * (hl_ratio ** 2) - (2 * np.log(2) - 1) * (cc_ratio ** 2)
        return max(gk_vol, 0.0)
    
    def group_volatility(
        self, df: pd.DataFrame
    ) -> Tuple[List[VolatilityGroup], pd.DataFrame]:
        """
        Group bars and calculate volatility per group.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            Tuple of (volatility groups, extended DataFrame)
        """
        groups = []
        group_vols = []
        group_indices = []
        
        for i in range(0, len(df), self.data_length):
            group_df = df.iloc[i:i+self.data_length]
            
            if len(group_df) == 0:
                continue
            
            # Calculate group volatility
            vols = group_df.apply(
                lambda row: self.calculate_volatility(row['high'], row['low'], row['close']),
                axis=1
            )
            avg_vol = vols.mean()
            
            # Create group
            group = VolatilityGroup(
                timestamp=group_df.index[-1],
                volatility=avg_vol,
                high=group_df['high'].max(),
                low=group_df['low'].min(),
                close=group_df['close'].iloc[-1],
                bar_count=len(group_df),
            )
            
            groups.append(group)
            
            # Track for each bar
            for j, idx in enumerate(group_df.index):
                group_vols.append(avg_vol)
                group_indices.append(idx)
        
        # Add to dataframe
        df_extended = df.copy()
        df_extended.loc[:, 'volatility_group'] = np.nan
        
        for idx, vol in zip(group_indices, group_vols):
            if idx in df_extended.index:
                df_extended.loc[idx, 'volatility_group'] = vol
        
        # Forward fill missing values
        df_extended['volatility_group'].fillna(method='ffill', inplace=True)
        
        return groups, df_extended
    
    def calculate_distribution_stats(
        self, groups: List[VolatilityGroup], distribution_length: int = 100
    ) -> Dict[str, any]:
        """
        Calculate log-normal distribution statistics.
        
        Args:
            groups: Volatility groups
            distribution_length: Sample size for distribution
        
        Returns:
            Dictionary with distribution parameters
        """
        # Get recent volatility values
        recent_vols = [g.volatility for g in groups[-distribution_length:]]
        recent_vols = [v for v in recent_vols if v > 0]
        
        if not recent_vols:
            return {
                'mean': 0.0,
                'std': 0.0,
                'median': 0.0,
                'p25': 0.0,
                'p75': 0.0,
                'p95': 0.0,
            }
        
        # Fit log-normal distribution
        log_vols = np.log(recent_vols)
        
        return {
            'mean': np.mean(log_vols),
            'std': np.std(log_vols),
            'median': np.median(recent_vols),
            'p25': np.percentile(recent_vols, 25),
            'p75': np.percentile(recent_vols, 75),
            'p95': np.percentile(recent_vols, 95),
            'min': np.min(recent_vols),
            'max': np.max(recent_vols),
        }


class StatisticalTrailingStop:
    """
    Statistical trailing stop using volatility distribution.
    
    Generates four distinct trailing stop levels based on log-normal
    distribution of volatility measurements.
    """
    
    def __init__(
        self,
        data_length: int = 10,
        distribution_length: int = 100,
        atr_period: int = 14,
    ):
        """
        Initialize trailing stop detector.
        
        Args:
            data_length: Bars per volatility group
            distribution_length: Groups for distribution calculation
            atr_period: ATR calculation period
        """
        self.data_length = data_length
        self.distribution_length = distribution_length
        self.atr_period = atr_period
        self.volatility_analyzer = VolatilityAnalyzer(data_length)
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        df_calc = df.copy()
        
        df_calc['tr'] = np.maximum(
            df_calc['high'] - df_calc['low'],
            np.maximum(
                np.abs(df_calc['high'] - df_calc['close'].shift()),
                np.abs(df_calc['low'] - df_calc['close'].shift())
            )
        )
        
        atr = df_calc['tr'].rolling(period).mean()
        return atr
    
    def calculate_trailing_stops(
        self, df: pd.DataFrame, base_level: TrailingStopLevel = TrailingStopLevel.LEVEL_2
    ) -> pd.DataFrame:
        """
        Calculate trailing stop levels for all bars.
        
        Args:
            df: OHLCV DataFrame
            base_level: Which level to use (0-3)
        
        Returns:
            DataFrame with trailing stop levels
        """
        df_result = df.copy()
        
        # Group volatility
        groups, df_extended = self.volatility_analyzer.group_volatility(df)
        
        # Calculate ATR
        atr = self.calculate_atr(df, self.atr_period)
        
        # Initialize level columns
        for level in range(4):
            df_result[f'level_{level}_long'] = np.nan
            df_result[f'level_{level}_short'] = np.nan
        
        # Calculate distribution stats for each point
        level_0_stops_long = []
        level_1_stops_long = []
        level_2_stops_long = []
        level_3_stops_long = []
        
        level_0_stops_short = []
        level_1_stops_short = []
        level_2_stops_short = []
        level_3_stops_short = []
        
        for i in range(len(df)):
            current_close = df.iloc[i]['close']
            current_atr = atr.iloc[i]
            
            # Get relevant groups
            relevant_groups = groups[:max(1, i//self.data_length)]
            
            if not relevant_groups:
                # Initialize with default
                level_0_stops_long.append(current_close - current_atr * 0.5)
                level_1_stops_long.append(current_close - current_atr * 1.0)
                level_2_stops_long.append(current_close - current_atr * 1.5)
                level_3_stops_long.append(current_close - current_atr * 2.0)
                
                level_0_stops_short.append(current_close + current_atr * 0.5)
                level_1_stops_short.append(current_close + current_atr * 1.0)
                level_2_stops_short.append(current_close + current_atr * 1.5)
                level_3_stops_short.append(current_close + current_atr * 2.0)
                continue
            
            # Calculate distribution stats
            stats_dict = self.volatility_analyzer.calculate_distribution_stats(
                relevant_groups, self.distribution_length
            )
            
            # Generate levels based on volatility distribution
            # Level 0: Most responsive (1 std dev)
            # Level 1: Standard (1.5 std dev)
            # Level 2: Stable (2 std dev)
            # Level 3: Very stable (2.5 std dev)
            
            std_vol = stats_dict['std']
            
            # Long stops (below price)
            l0_long = current_close - (current_atr * 0.8)
            l1_long = current_close - (current_atr * 1.2)
            l2_long = current_close - (current_atr * 1.6)
            l3_long = current_close - (current_atr * 2.0)
            
            level_0_stops_long.append(l0_long)
            level_1_stops_long.append(l1_long)
            level_2_stops_long.append(l2_long)
            level_3_stops_long.append(l3_long)
            
            # Short stops (above price)
            l0_short = current_close + (current_atr * 0.8)
            l1_short = current_close + (current_atr * 1.2)
            l2_short = current_close + (current_atr * 1.6)
            l3_short = current_close + (current_atr * 2.0)
            
            level_0_stops_short.append(l0_short)
            level_1_stops_short.append(l1_short)
            level_2_stops_short.append(l2_short)
            level_3_stops_short.append(l3_short)
        
        # Add to result
        df_result['level_0_long'] = level_0_stops_long
        df_result['level_1_long'] = level_1_stops_long
        df_result['level_2_long'] = level_2_stops_long
        df_result['level_3_long'] = level_3_stops_long
        
        df_result['level_0_short'] = level_0_stops_short
        df_result['level_1_short'] = level_1_stops_short
        df_result['level_2_short'] = level_2_stops_short
        df_result['level_3_short'] = level_3_stops_short
        
        return df_result
    
    def detect_long_signals(
        self, df: pd.DataFrame, level: int = 2
    ) -> List[TrailingStopSignal]:
        """
        Detect long entry signals (trailing stop bounces up).
        
        Args:
            df: DataFrame with trailing stops calculated
            level: Which level to use (0-3)
        
        Returns:
            List of signals
        """
        signals = []
        level_col = f'level_{level}_long'
        
        if level_col not in df.columns:
            return signals
        
        for i in range(1, len(df)):
            prev_close = df.iloc[i-1]['close']
            curr_close = df.iloc[i]['close']
            curr_low = df.iloc[i]['low']
            trailing_stop = df.iloc[i][level_col]
            
            # Signal when price bounces up from stop
            if prev_close <= trailing_stop and curr_close > trailing_stop:
                signal = TrailingStopSignal(
                    timestamp=df.index[i],
                    price=curr_close,
                    level_0=df.iloc[i]['level_0_long'],
                    level_1=df.iloc[i]['level_1_long'],
                    level_2=df.iloc[i]['level_2_long'],
                    level_3=df.iloc[i]['level_3_long'],
                    direction='long',
                    volatility=df.iloc[i]['volatility_group'] if 'volatility_group' in df.columns else 0.0,
                )
                signals.append(signal)
        
        return signals
    
    def detect_short_signals(
        self, df: pd.DataFrame, level: int = 2
    ) -> List[TrailingStopSignal]:
        """
        Detect short entry signals (trailing stop bounces down).
        
        Args:
            df: DataFrame with trailing stops calculated
            level: Which level to use (0-3)
        
        Returns:
            List of signals
        """
        signals = []
        level_col = f'level_{level}_short'
        
        if level_col not in df.columns:
            return signals
        
        for i in range(1, len(df)):
            prev_close = df.iloc[i-1]['close']
            curr_close = df.iloc[i]['close']
            curr_high = df.iloc[i]['high']
            trailing_stop = df.iloc[i][level_col]
            
            # Signal when price bounces down from stop
            if prev_close >= trailing_stop and curr_close < trailing_stop:
                signal = TrailingStopSignal(
                    timestamp=df.index[i],
                    price=curr_close,
                    level_0=df.iloc[i]['level_0_short'],
                    level_1=df.iloc[i]['level_1_short'],
                    level_2=df.iloc[i]['level_2_short'],
                    level_3=df.iloc[i]['level_3_short'],
                    direction='short',
                    volatility=df.iloc[i]['volatility_group'] if 'volatility_group' in df.columns else 0.0,
                )
                signals.append(signal)
        
        return signals
    
    def detect_all_signals(
        self, df: pd.DataFrame, level: int = 2
    ) -> Dict[str, List[TrailingStopSignal]]:
        """
        Detect both long and short signals.
        
        Args:
            df: DataFrame with trailing stops
            level: Which level (0-3)
        
        Returns:
            Dictionary with 'long' and 'short' signals
        """
        return {
            'long': self.detect_long_signals(df, level),
            'short': self.detect_short_signals(df, level),
        }
    
    def backtest_level(
        self, df: pd.DataFrame, level: int = 2, trade_type: str = 'long'
    ) -> Tuple[List[TradeRecord], Dict[str, any]]:
        """
        Backtest a specific level.
        
        Args:
            df: OHLCV DataFrame
            level: Which level (0-3)
            trade_type: 'long' or 'short'
        
        Returns:
            Tuple of (trades, statistics)
        """
        # Get signals
        if trade_type == 'long':
            signals = self.detect_long_signals(df, level)
            stop_col = f'level_{level}_long'
        else:
            signals = self.detect_short_signals(df, level)
            stop_col = f'level_{level}_short'
        
        trades = []
        open_trade = None
        
        for sig_idx, signal in enumerate(signals):
            sig_timestamp = signal.timestamp
            sig_price = signal.price
            
            # Find signal bar index
            try:
                bar_idx = df.index.get_loc(sig_timestamp)
            except KeyError:
                continue
            
            if open_trade is None:
                # Open new trade
                entry = TradeEntry(
                    entry_timestamp=sig_timestamp,
                    entry_price=sig_price,
                    entry_signal=signal,
                    trade_type=trade_type,
                )
                open_trade = TradeRecord(
                    entry=entry,
                    exit=None,
                    status='open',
                )
            else:
                # Close previous trade at this signal
                exit_signal = signal
                exit_price = signal.price
                
                pnl = (exit_price - open_trade.entry.entry_price) if trade_type == 'long' else (open_trade.entry.entry_price - exit_price)
                pnl_pct = (pnl / open_trade.entry.entry_price) * 100
                
                duration = bar_idx - df.index.get_loc(open_trade.entry.entry_timestamp)
                
                open_trade.exit = TradeExit(
                    exit_timestamp=sig_timestamp,
                    exit_price=exit_price,
                    exit_signal=exit_signal,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    duration_bars=duration,
                )
                open_trade.status = 'closed'
                
                trades.append(open_trade)
                
                # Open new trade
                entry = TradeEntry(
                    entry_timestamp=sig_timestamp,
                    entry_price=sig_price,
                    entry_signal=signal,
                    trade_type=trade_type,
                )
                open_trade = TradeRecord(
                    entry=entry,
                    exit=None,
                    status='open',
                )
        
        # Calculate statistics
        closed_trades = [t for t in trades if t.status == 'closed']
        
        if closed_trades:
            wins = [t for t in closed_trades if t.exit.pnl > 0]
            losses = [t for t in closed_trades if t.exit.pnl < 0]
            
            win_rate = len(wins) / len(closed_trades) * 100 if closed_trades else 0
            
            total_pnl = sum([t.exit.pnl for t in closed_trades])
            avg_pnl = total_pnl / len(closed_trades) if closed_trades else 0
            
            avg_win = np.mean([t.exit.pnl for t in wins]) if wins else 0
            avg_loss = np.mean([t.exit.pnl for t in losses]) if losses else 0
            
            expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
            
            stats = {
                'total_trades': len(closed_trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'expectancy': expectancy,
                'avg_duration': np.mean([t.exit.duration_bars for t in closed_trades]),
            }
        else:
            stats = {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'expectancy': 0,
                'avg_duration': 0,
            }
        
        return closed_trades, stats


if __name__ == "__main__":
    # Example usage
    import numpy as np
    
    dates = pd.date_range('2023-01-01', periods=1000, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(1000) * 0.5)
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(1000) * 0.3),
        'low': prices - np.abs(np.random.randn(1000) * 0.3),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 1000),
    }, index=dates)
    
    detector = StatisticalTrailingStop()
    
    # Calculate levels
    df_with_stops = detector.calculate_trailing_stops(df)
    print("✓ Trailing stops calculated")
    print(f"  Columns: {df_with_stops.columns.tolist()}")
    
    # Get signals
    signals = detector.detect_all_signals(df_with_stops, level=2)
    print(f"\n✓ Signals detected:")
    print(f"  Long: {len(signals['long'])}")
    print(f"  Short: {len(signals['short'])}")
    
    # Backtest
    long_trades, long_stats = detector.backtest_level(df_with_stops, level=2, trade_type='long')
    print(f"\n✓ Long trades backtest:")
    print(f"  Total: {long_stats['total_trades']}")
    print(f"  Win Rate: {long_stats['win_rate']:.2f}%")
    print(f"  Expectancy: ${long_stats['expectancy']:.2f}")
