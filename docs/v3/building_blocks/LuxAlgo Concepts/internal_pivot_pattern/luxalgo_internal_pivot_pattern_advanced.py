"""
LuxAlgo Internal Pivot Pattern - Advanced Analysis
=================================================

Advanced utilities for internal pivot pattern analysis including
trade tracking, timeframe optimization, and pivot performance metrics.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from luxalgo_internal_pivot_pattern import (
    InternalPivot, PivotType, TrendDirection, AccuracyDashboard
)


@dataclass
class PivotTrade:
    """Track internal pivot pattern trade performance."""
    entry_pivot: InternalPivot
    entry_time: pd.Timestamp
    entry_price: float
    
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    
    target_reached: bool = False
    stop_hit: bool = False
    bars_held: int = 0
    
    zigzag_confirmed: bool = False


class PivotTradeAnalyzer:
    """Analyze internal pivot trading performance."""
    
    @staticmethod
    def generate_trades(pivots: List[InternalPivot],
                       df: pd.DataFrame,
                       lookforward_bars: int = 20) -> List[PivotTrade]:
        """
        Generate potential trades from detected pivots.
        
        Entry on pivot close, target = next pivot level, stop = pivot extreme
        
        Args:
            pivots: List of detected pivots
            df: OHLCV DataFrame
            lookforward_bars: Bars to look forward for target/stop
        
        Returns:
            List of PivotTrade objects
        """
        trades = []
        
        for i, pivot in enumerate(pivots):
            if pivot.bar_index >= len(df):
                continue
            
            entry_time = df.index[pivot.bar_index]
            entry_price = df.iloc[pivot.bar_index]['close']
            
            # Determine target (next pivot)
            target_price = None
            if i + 1 < len(pivots):
                target_price = pivots[i + 1].pivot_price
            
            # Determine stop (same pivot type low)
            stop_price = None
            if pivot.pivot_type == PivotType.LOW:
                stop_price = pivot.pivot_price * 0.99  # 1% below
            else:
                stop_price = pivot.pivot_price * 1.01  # 1% above
            
            trade = PivotTrade(
                entry_pivot=pivot,
                entry_time=entry_time,
                entry_price=entry_price,
            )
            
            # Look forward for target/stop hits
            end_idx = min(pivot.bar_index + lookforward_bars, len(df))
            
            for j in range(pivot.bar_index, end_idx):
                bar = df.iloc[j]
                
                if pivot.pivot_type == PivotType.LOW:
                    # Bullish trade
                    # Target = next pivot high
                    if target_price and bar['high'] >= target_price:
                        trade.exit_price = target_price
                        trade.exit_time = df.index[j]
                        trade.target_reached = True
                        trade.bars_held = j - pivot.bar_index
                        break
                    
                    # Stop = below pivot
                    if bar['low'] < stop_price:
                        trade.exit_price = stop_price
                        trade.exit_time = df.index[j]
                        trade.stop_hit = True
                        trade.bars_held = j - pivot.bar_index
                        break
                
                else:  # PIVOT_HIGH
                    # Bearish trade
                    # Target = next pivot low
                    if target_price and bar['low'] <= target_price:
                        trade.exit_price = target_price
                        trade.exit_time = df.index[j]
                        trade.target_reached = True
                        trade.bars_held = j - pivot.bar_index
                        break
                    
                    # Stop = above pivot
                    if bar['high'] > stop_price:
                        trade.exit_price = stop_price
                        trade.exit_time = df.index[j]
                        trade.stop_hit = True
                        trade.bars_held = j - pivot.bar_index
                        break
            
            # Calculate P&L
            if trade.exit_price:
                trade.pnl = trade.exit_price - trade.entry_price
                trade.pnl_pct = (trade.pnl / trade.entry_price) * 100
            
            trades.append(trade)
        
        return trades
    
    @staticmethod
    def calculate_statistics(trades: List[PivotTrade]) -> Dict:
        """
        Calculate pivot trade statistics.
        
        Args:
            trades: List of trades
        
        Returns:
            Statistics dictionary
        """
        if not trades:
            return {}
        
        completed_trades = [t for t in trades if t.exit_price is not None]
        winners = [t for t in completed_trades if t.target_reached]
        losers = [t for t in completed_trades if t.stop_hit]
        
        bullish_trades = [t for t in trades if t.entry_pivot.pivot_type == PivotType.LOW]
        bearish_trades = [t for t in trades if t.entry_pivot.pivot_type == PivotType.HIGH]
        
        return {
            'total_trades': len(trades),
            'completed': len(completed_trades),
            'pending': len(trades) - len(completed_trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': (len(winners) / len(completed_trades) * 100) if completed_trades else 0,
            'bullish_trades': len(bullish_trades),
            'bearish_trades': len(bearish_trades),
            'bullish_win_rate': (sum(1 for t in bullish_trades if t.target_reached) / len(bullish_trades) * 100) if bullish_trades else 0,
            'bearish_win_rate': (sum(1 for t in bearish_trades if t.target_reached) / len(bearish_trades) * 100) if bearish_trades else 0,
            'avg_bars_to_target': np.mean([t.bars_held for t in winners if t.bars_held]) if winners else 0,
            'avg_bars_to_stop': np.mean([t.bars_held for t in losers if t.bars_held]) if losers else 0,
            'avg_win': np.mean([t.pnl_pct for t in winners if t.pnl_pct]) if winners else 0,
            'avg_loss': np.mean([t.pnl_pct for t in losers if t.pnl_pct]) if losers else 0,
        }


class TimeframeOptimizer:
    """Optimize timeframe ratio for better pivot detection."""
    
    @staticmethod
    def test_timeframe_ratios(df: pd.DataFrame,
                             ratio_range: Tuple[int, int] = (2, 10),
                             target_metric: str = 'accuracy') -> Dict:
        """
        Test different timeframe ratios to find optimal.
        
        Args:
            df: OHLCV DataFrame
            ratio_range: (min_ratio, max_ratio) to test
            target_metric: 'accuracy', 'signal_count', 'win_rate'
        
        Returns:
            Optimization results
        """
        from luxalgo_internal_pivot_pattern import InternalPivotPattern
        
        results = {}
        
        for ratio in range(ratio_range[0], ratio_range[1] + 1):
            ipp = InternalPivotPattern(timeframe_ratio=ratio)
            df_result, analysis = ipp.analyze(df)
            
            if target_metric == 'accuracy':
                metric_value = analysis['accuracy_percentage']
            elif target_metric == 'signal_count':
                metric_value = analysis['total_pivots']
            else:  # win_rate
                trades = PivotTradeAnalyzer.generate_trades(analysis['pivots'], df)
                stats = PivotTradeAnalyzer.calculate_statistics(trades)
                metric_value = stats.get('win_rate', 0)
            
            results[ratio] = {
                'ratio': ratio,
                'metric_value': metric_value,
                'total_pivots': analysis['total_pivots'],
                'accuracy': analysis['accuracy_percentage'],
            }
        
        return results
    
    @staticmethod
    def recommend_timeframe(results: Dict,
                           target_metric: str = 'accuracy') -> int:
        """
        Recommend optimal timeframe ratio.
        
        Args:
            results: Results from test_timeframe_ratios
            target_metric: Metric to optimize
        
        Returns:
            Recommended ratio
        """
        best_ratio = min(results.keys())
        best_value = results[best_ratio]['metric_value']
        
        for ratio, data in results.items():
            if data['metric_value'] > best_value:
                best_ratio = ratio
                best_value = data['metric_value']
        
        return best_ratio


class PivotStructureAnalyzer:
    """Analyze market structure from pivots."""
    
    @staticmethod
    def identify_swing_patterns(pivots: List[InternalPivot]) -> List[Dict]:
        """
        Identify swing patterns from pivot sequence.
        
        Patterns: Higher High, Lower Low, Double Top/Bottom, etc.
        
        Args:
            pivots: List of pivots
        
        Returns:
            List of identified patterns
        """
        patterns = []
        
        if len(pivots) < 2:
            return patterns
        
        for i in range(1, len(pivots)):
            curr = pivots[i]
            prev = pivots[i - 1]
            
            if curr.pivot_type == prev.pivot_type:
                continue  # Different types only
            
            pattern_type = None
            
            # Check for Higher High / Higher Low (uptrend)
            if curr.pivot_type == PivotType.HIGH and prev.pivot_type == PivotType.LOW:
                if curr.pivot_price > (pivots[i-2].pivot_price if i >= 2 else 0):
                    pattern_type = 'higher_high'
            
            # Check for Lower Low / Lower High (downtrend)
            elif curr.pivot_type == PivotType.LOW and prev.pivot_type == PivotType.HIGH:
                if curr.pivot_price < (pivots[i-2].pivot_price if i >= 2 else float('inf')):
                    pattern_type = 'lower_low'
            
            if pattern_type:
                patterns.append({
                    'pattern': pattern_type,
                    'pivot_index': i,
                    'pivot': curr,
                    'previous': prev,
                })
        
        return patterns
    
    @staticmethod
    def detect_consolidation(pivots: List[InternalPivot],
                            price_range_pct: float = 2.0) -> List[Dict]:
        """
        Detect consolidation zones (tight pivot ranges).
        
        Args:
            pivots: List of pivots
            price_range_pct: Percentage range to consider consolidation
        
        Returns:
            List of consolidation zones
        """
        consolidations = []
        
        if len(pivots) < 3:
            return consolidations
        
        for i in range(len(pivots) - 2):
            high = max(pivots[i].pivot_price, pivots[i+1].pivot_price, pivots[i+2].pivot_price)
            low = min(pivots[i].pivot_price, pivots[i+1].pivot_price, pivots[i+2].pivot_price)
            
            range_pct = ((high - low) / low) * 100
            
            if range_pct <= price_range_pct:
                consolidations.append({
                    'start_idx': i,
                    'end_idx': i + 2,
                    'high': high,
                    'low': low,
                    'range_pct': range_pct,
                })
        
        return consolidations


class InternalPivotReporter:
    """Generate internal pivot pattern reports."""
    
    @staticmethod
    def generate_analysis_report(analysis: Dict) -> str:
        """Generate overall analysis report."""
        
        trades = PivotTradeAnalyzer.generate_trades(
            analysis['pivots'], pd.DataFrame()
        )
        stats = PivotTradeAnalyzer.calculate_statistics(trades)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║    INTERNAL PIVOT PATTERN - ANALYSIS REPORT                    ║
╚════════════════════════════════════════════════════════════════╝

📊 Pivot Detection:
   Total Pivots: {analysis['total_pivots']}
   Pivot Lows: {len(analysis['pivot_lows'])}
   Pivot Highs: {len(analysis['pivot_highs'])}

✓ Accuracy: {analysis['accuracy_percentage']:.1f}%
   Correct Predictions: {len([a for a in analysis['accuracies'] if a.is_accurate])}

📈 Trend Status: {analysis['current_trend'].value.upper()}

📊 Trade Performance:
   Total Trades: {stats.get('total_trades', 0)}
   Completed: {stats.get('completed', 0)}
   Winners: {stats.get('winners', 0)}
   Losers: {stats.get('losers', 0)}
   Win Rate: {stats.get('win_rate', 0):.1f}%

💡 By Pivot Type:
   Bullish (Pivot Low): {stats.get('bullish_win_rate', 0):.1f}%
   Bearish (Pivot High): {stats.get('bearish_win_rate', 0):.1f}%

💰 P&L:
   Avg Winner: {stats.get('avg_win', 0):+.2f}%
   Avg Loser: {stats.get('avg_loss', 0):+.2f}%

⏱️ Timing:
   Avg Bars to Target: {stats.get('avg_bars_to_target', 0):.0f}
   Avg Bars to Stop: {stats.get('avg_bars_to_stop', 0):.0f}

"""
        return report
    
    @staticmethod
    def generate_pivot_summary(pivots: List[InternalPivot]) -> str:
        """Generate pivot summary."""
        
        lows = [p for p in pivots if p.pivot_type == PivotType.LOW]
        highs = [p for p in pivots if p.pivot_type == PivotType.HIGH]
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║       INTERNAL PIVOT PATTERN - PIVOT SUMMARY                   ║
╚════════════════════════════════════════════════════════════════╝

📌 Pivot Count:
   Total: {len(pivots)}
   Lows: {len(lows)}
   Highs: {len(highs)}

💪 Pivot Strength:
   Avg Depth: {np.mean([p.pivot_depth for p in pivots]):.1f}%
   Strongest: {max([p.pivot_depth for p in pivots]):.1f}%
   Weakest: {min([p.pivot_depth for p in pivots]):.1f}%

💰 Price Levels:
   Highest Pivot: ${max([p.pivot_price for p in pivots]):.2f}
   Lowest Pivot: ${min([p.pivot_price for p in pivots]):.2f}

"""
        return report


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=100, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(100) * 0.2,
        'high': prices + np.abs(np.random.randn(100) * 0.5),
        'low': prices - np.abs(np.random.randn(100) * 0.5),
        'close': prices,
    }, index=dates)
    
    from luxalgo_internal_pivot_pattern import InternalPivotPattern
    
    ipp = InternalPivotPattern(pivot_lookback=21)
    df_result, analysis = ipp.analyze(df)
    
    trades = PivotTradeAnalyzer.generate_trades(analysis['pivots'], df)
    
    reporter = InternalPivotReporter()
    print(reporter.generate_analysis_report(analysis))
    print(reporter.generate_pivot_summary(analysis['pivots']))
