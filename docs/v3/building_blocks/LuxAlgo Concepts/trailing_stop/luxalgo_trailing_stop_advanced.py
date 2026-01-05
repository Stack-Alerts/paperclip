"""
LuxAlgo Statistical Trailing Stop - Advanced Analysis & Dashboard
==================================================================

Advanced utilities for statistical trailing stop analysis including
dashboard statistics, multi-level backtesting, signal analysis,
and optimization tools.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from luxalgo_trailing_stop import (
    StatisticalTrailingStop,
    TrailingStopSignal,
    TradeRecord,
    TradeEntry,
    TradeExit,
)


@dataclass
class DashboardMetrics:
    """Dashboard statistics for trailing stop performance."""
    level: int
    trade_type: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    sharpe_ratio: float
    max_drawdown: float
    win_avg_duration: float
    loss_avg_duration: float
    risk_reward_ratio: float


class DashboardAnalyzer:
    """Generates comprehensive dashboard statistics."""
    
    def __init__(self, detector: StatisticalTrailingStop):
        self.detector = detector
    
    def calculate_metrics(
        self, df: pd.DataFrame, level: int = 2, trade_type: str = 'long'
    ) -> DashboardMetrics:
        """
        Calculate all dashboard metrics.
        
        Args:
            df: DataFrame with trailing stops
            level: Trailing stop level (0-3)
            trade_type: 'long' or 'short'
        
        Returns:
            DashboardMetrics object
        """
        trades, stats = self.detector.backtest_level(df, level, trade_type)
        
        closed_trades = [t for t in trades if t.status == 'closed']
        
        if not closed_trades:
            return DashboardMetrics(
                level=level,
                trade_type=trade_type,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                avg_pnl=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                expectancy=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_avg_duration=0.0,
                loss_avg_duration=0.0,
                risk_reward_ratio=0.0,
            )
        
        # Calculate profit factor
        wins = [t for t in closed_trades if t.exit.pnl > 0]
        losses = [t for t in closed_trades if t.exit.pnl < 0]
        
        total_wins = sum([t.exit.pnl for t in wins]) if wins else 0
        total_losses = abs(sum([t.exit.pnl for t in losses])) if losses else 0
        
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Calculate Sharpe ratio
        pnl_series = pd.Series([t.exit.pnl for t in closed_trades])
        sharpe = (pnl_series.mean() / pnl_series.std()) * np.sqrt(252) if pnl_series.std() > 0 else 0
        
        # Calculate max drawdown
        cumulative_pnl = np.cumsum([t.exit.pnl for t in closed_trades])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Duration analysis
        win_durations = [t.exit.duration_bars for t in wins] if wins else [0]
        loss_durations = [t.exit.duration_bars for t in losses] if losses else [0]
        
        win_avg_duration = np.mean(win_durations) if win_durations else 0
        loss_avg_duration = np.mean(loss_durations) if loss_durations else 0
        
        # Risk/Reward
        avg_win = stats['avg_win']
        avg_loss = abs(stats['avg_loss'])
        risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
        
        return DashboardMetrics(
            level=level,
            trade_type=trade_type,
            total_trades=stats['total_trades'],
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=stats['win_rate'],
            total_pnl=stats['total_pnl'],
            avg_pnl=stats['avg_pnl'],
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=stats['expectancy'],
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            win_avg_duration=win_avg_duration,
            loss_avg_duration=loss_avg_duration,
            risk_reward_ratio=risk_reward,
        )
    
    def generate_report(
        self, df: pd.DataFrame, level: int = 2, trade_type: str = 'long'
    ) -> str:
        """Generate formatted dashboard report."""
        metrics = self.calculate_metrics(df, level, trade_type)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║           STATISTICAL TRAILING STOP DASHBOARD                 ║
╚════════════════════════════════════════════════════════════════╝

📊 Configuration
   Level: {metrics.level}
   Trade Type: {metrics.trade_type.upper()}

📈 Trade Statistics
   Total Trades: {metrics.total_trades}
   Winning Trades: {metrics.winning_trades}
   Losing Trades: {metrics.losing_trades}
   Win Rate: {metrics.win_rate:.2f}%

💰 Profitability
   Total P&L: ${metrics.total_pnl:,.2f}
   Average P&L: ${metrics.avg_pnl:,.2f}
   Average Win: ${metrics.avg_win:,.2f}
   Average Loss: ${metrics.avg_loss:,.2f}
   Profit Factor: {metrics.profit_factor:.2f}
   Expectancy: ${metrics.expectancy:,.2f}

📊 Risk Metrics
   Risk/Reward Ratio: 1:{metrics.risk_reward_ratio:.2f}
   Sharpe Ratio: {metrics.sharpe_ratio:.2f}
   Max Drawdown: ${metrics.max_drawdown:,.2f}

⏱️  Duration Analysis
   Avg Win Duration: {metrics.win_avg_duration:.0f} bars
   Avg Loss Duration: {metrics.loss_avg_duration:.0f} bars
"""
        return report


class MultiLevelBacktest:
    """Compare performance across all levels."""
    
    def __init__(self, detector: StatisticalTrailingStop):
        self.detector = detector
        self.analyzer = DashboardAnalyzer(detector)
    
    def backtest_all_levels(
        self, df: pd.DataFrame, trade_type: str = 'long'
    ) -> Dict[int, DashboardMetrics]:
        """
        Backtest all 4 levels.
        
        Args:
            df: DataFrame with trailing stops
            trade_type: 'long' or 'short'
        
        Returns:
            Dictionary mapping level -> metrics
        """
        results = {}
        
        for level in range(4):
            metrics = self.analyzer.calculate_metrics(df, level, trade_type)
            results[level] = metrics
        
        return results
    
    def compare_levels(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compare all levels for long and short.
        
        Args:
            df: DataFrame with trailing stops
        
        Returns:
            Comparison DataFrame
        """
        comparison_data = []
        
        for trade_type in ['long', 'short']:
            results = self.backtest_all_levels(df, trade_type)
            
            for level, metrics in results.items():
                comparison_data.append({
                    'Level': level,
                    'Type': trade_type.upper(),
                    'Trades': metrics.total_trades,
                    'Win %': metrics.win_rate,
                    'P&L': metrics.total_pnl,
                    'Expectancy': metrics.expectancy,
                    'R/R': metrics.risk_reward_ratio,
                    'Sharpe': metrics.sharpe_ratio,
                })
        
        return pd.DataFrame(comparison_data)
    
    def find_best_level(
        self, df: pd.DataFrame, trade_type: str = 'long', metric: str = 'expectancy'
    ) -> Tuple[int, DashboardMetrics]:
        """
        Find best performing level.
        
        Args:
            df: DataFrame with trailing stops
            trade_type: 'long' or 'short'
            metric: Metric to optimize ('expectancy', 'win_rate', 'sharpe_ratio')
        
        Returns:
            Tuple of (best_level, metrics)
        """
        results = self.backtest_all_levels(df, trade_type)
        
        best_level = 0
        best_value = float('-inf')
        
        for level, metrics in results.items():
            value = getattr(metrics, metric)
            if value > best_value:
                best_value = value
                best_level = level
        
        return best_level, results[best_level]


class SignalAnalyzer:
    """Analyze signal characteristics and patterns."""
    
    def __init__(self, detector: StatisticalTrailingStop):
        self.detector = detector
    
    def analyze_signal_spacing(
        self, signals: List[TrailingStopSignal]
    ) -> Dict[str, any]:
        """
        Analyze spacing between signals.
        
        Args:
            signals: List of signals
        
        Returns:
            Spacing statistics
        """
        if len(signals) < 2:
            return {
                'avg_spacing': 0,
                'min_spacing': 0,
                'max_spacing': 0,
                'spacing_std': 0,
            }
        
        timestamps = [s.timestamp for s in signals]
        spacings = [(timestamps[i] - timestamps[i-1]).days for i in range(1, len(timestamps))]
        
        return {
            'avg_spacing': np.mean(spacings),
            'min_spacing': np.min(spacings),
            'max_spacing': np.max(spacings),
            'spacing_std': np.std(spacings),
        }
    
    def analyze_volatility_at_signals(
        self, signals: List[TrailingStopSignal]
    ) -> Dict[str, any]:
        """
        Analyze volatility characteristics at signal points.
        
        Args:
            signals: List of signals
        
        Returns:
            Volatility statistics
        """
        if not signals:
            return {
                'avg_volatility': 0,
                'min_volatility': 0,
                'max_volatility': 0,
                'volatility_std': 0,
            }
        
        vols = [s.volatility for s in signals if s.volatility > 0]
        
        return {
            'avg_volatility': np.mean(vols) if vols else 0,
            'min_volatility': np.min(vols) if vols else 0,
            'max_volatility': np.max(vols) if vols else 0,
            'volatility_std': np.std(vols) if vols else 0,
        }
    
    def analyze_price_at_signals(
        self, signals: List[TrailingStopSignal]
    ) -> Dict[str, any]:
        """
        Analyze price characteristics at signals.
        
        Args:
            signals: List of signals
        
        Returns:
            Price statistics
        """
        if not signals:
            return {
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'price_range': 0,
            }
        
        prices = [s.price for s in signals]
        
        return {
            'avg_price': np.mean(prices),
            'min_price': np.min(prices),
            'max_price': np.max(prices),
            'price_range': np.max(prices) - np.min(prices),
        }


class ParameterOptimizer:
    """Find optimal parameters."""
    
    def __init__(self, detector: StatisticalTrailingStop):
        self.detector = detector
        self.multi_test = MultiLevelBacktest(detector)
    
    def optimize_for_metric(
        self,
        df: pd.DataFrame,
        trade_type: str = 'long',
        metric: str = 'expectancy',
    ) -> Dict[str, any]:
        """
        Find best level for given metric.
        
        Args:
            df: DataFrame
            trade_type: 'long' or 'short'
            metric: Optimization target
        
        Returns:
            Optimization results
        """
        best_level, best_metrics = self.multi_test.find_best_level(
            df, trade_type, metric
        )
        
        return {
            'best_level': best_level,
            'metric_value': getattr(best_metrics, metric),
            'metrics': best_metrics,
        }
    
    def compare_configurations(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compare all level configurations.
        
        Args:
            df: DataFrame
        
        Returns:
            Comparison table
        """
        return self.multi_test.compare_levels(df)


def example_dashboard_analysis():
    """Example: Generate dashboard statistics."""
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=500, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 1.0)
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(len(dates)) * 0.5),
        'low': prices - np.abs(np.random.randn(len(dates)) * 0.5),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, len(dates)),
    }, index=dates)
    
    # Setup
    detector = StatisticalTrailingStop()
    df_with_stops = detector.calculate_trailing_stops(df)
    
    print("=" * 65)
    print("STATISTICAL TRAILING STOP - DASHBOARD ANALYSIS")
    print("=" * 65)
    
    # Generate dashboard
    dashboard = DashboardAnalyzer(detector)
    
    for level in range(4):
        print(f"\n{'─' * 65}")
        print(f"LEVEL {level} ANALYSIS")
        print(f"{'─' * 65}")
        
        for trade_type in ['long', 'short']:
            report = dashboard.generate_report(df_with_stops, level, trade_type)
            print(report)
    
    # Compare levels
    print(f"\n{'=' * 65}")
    print("LEVEL COMPARISON")
    print(f"{'=' * 65}\n")
    
    multi = MultiLevelBacktest(detector)
    comparison = multi.compare_levels(df_with_stops)
    print(comparison.to_string(index=False))
    
    # Find best
    print(f"\n{'=' * 65}")
    print("OPTIMAL CONFIGURATIONS")
    print(f"{'=' * 65}\n")
    
    for trade_type in ['long', 'short']:
        best_level, metrics = multi.find_best_level(
            df_with_stops, trade_type, 'expectancy'
        )
        print(f"Best {trade_type.upper()}: Level {best_level} (Expectancy: ${metrics.expectancy:,.2f})")


if __name__ == "__main__":
    example_dashboard_analysis()
