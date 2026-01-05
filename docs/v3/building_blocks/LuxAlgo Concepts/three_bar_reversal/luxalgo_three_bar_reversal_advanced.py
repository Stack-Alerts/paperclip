"""
LuxAlgo Three Bar Reversal Pattern - Advanced Analysis
====================================================

Advanced utilities for three-bar reversal pattern analysis including
performance tracking, support/resistance testing, and multi-indicator
alignment.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from luxalgo_three_bar_reversal import ThreeBar, PatternType


@dataclass
class PatternTrade:
    """Track three-bar pattern trade performance."""
    pattern: ThreeBar
    entry_time: pd.Timestamp
    entry_price: float
    
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    
    bars_to_target: Optional[int] = None
    bars_to_stop: Optional[int] = None
    
    support_tested: bool = False
    resistance_tested: bool = False
    hit_target: bool = False
    hit_stop: bool = False


class PatternPerformanceAnalyzer:
    """Analyze three-bar pattern trading performance."""
    
    @staticmethod
    def analyze_trades(patterns: List[ThreeBar], df: pd.DataFrame,
                      entry_offset_bars: int = 1,
                      lookforward_bars: int = 20) -> List[PatternTrade]:
        """
        Analyze pattern trades from entry to exit.
        
        Args:
            patterns: List of detected patterns
            df: OHLCV DataFrame
            entry_offset_bars: Bars after pattern to enter
            lookforward_bars: Bars to look forward for target/stop
        
        Returns:
            List of PatternTrade objects
        """
        trades = []
        
        for pattern in patterns:
            bar_3_idx = pattern.bar_3_idx
            entry_idx = min(bar_3_idx + entry_offset_bars, len(df) - 1)
            
            if entry_idx >= len(df):
                continue
            
            entry_time = df.index[entry_idx]
            entry_price = df.iloc[entry_idx]['close']
            
            # Determine target and stop
            if pattern.pattern_type == PatternType.BULLISH:
                target_price = pattern.resistance_level
                stop_price = pattern.support_level
            else:
                target_price = pattern.support_level
                stop_price = pattern.resistance_level
            
            trade = PatternTrade(
                pattern=pattern,
                entry_time=entry_time,
                entry_price=entry_price,
            )
            
            # Look forward
            lookforward_end = min(entry_idx + lookforward_bars, len(df))
            
            for j in range(entry_idx, lookforward_end):
                bar = df.iloc[j]
                
                if pattern.pattern_type == PatternType.BULLISH:
                    # Check support test
                    if bar['low'] <= pattern.support_level:
                        trade.support_tested = True
                    
                    # Check for target
                    if bar['high'] >= target_price:
                        trade.exit_price = target_price
                        trade.exit_time = df.index[j]
                        trade.hit_target = True
                        trade.bars_to_target = j - entry_idx
                        break
                    
                    # Check for stop
                    if bar['low'] < stop_price:
                        trade.exit_price = stop_price
                        trade.exit_time = df.index[j]
                        trade.hit_stop = True
                        trade.bars_to_stop = j - entry_idx
                        break
                
                else:  # BEARISH
                    # Check resistance test
                    if bar['high'] >= pattern.resistance_level:
                        trade.resistance_tested = True
                    
                    # Check for target
                    if bar['low'] <= target_price:
                        trade.exit_price = target_price
                        trade.exit_time = df.index[j]
                        trade.hit_target = True
                        trade.bars_to_target = j - entry_idx
                        break
                    
                    # Check for stop
                    if bar['high'] > stop_price:
                        trade.exit_price = stop_price
                        trade.exit_time = df.index[j]
                        trade.hit_stop = True
                        trade.bars_to_stop = j - entry_idx
                        break
            
            # Calculate P&L
            if trade.exit_price:
                trade.pnl = trade.exit_price - trade.entry_price
                trade.pnl_pct = (trade.pnl / trade.entry_price) * 100
            
            trades.append(trade)
        
        return trades
    
    @staticmethod
    def calculate_statistics(trades: List[PatternTrade]) -> Dict:
        """
        Calculate performance statistics.
        
        Args:
            trades: List of trades
        
        Returns:
            Statistics dictionary
        """
        if not trades:
            return {}
        
        completed_trades = [t for t in trades if t.exit_price is not None]
        winners = [t for t in completed_trades if t.hit_target]
        losers = [t for t in completed_trades if t.hit_stop]
        
        bullish_trades = [t for t in trades if t.pattern.pattern_type == PatternType.BULLISH]
        bearish_trades = [t for t in trades if t.pattern.pattern_type == PatternType.BEARISH]
        
        enhanced = [t for t in trades if t.pattern.is_enhanced]
        normal = [t for t in trades if not t.pattern.is_enhanced]
        
        return {
            'total_patterns': len(trades),
            'completed_trades': len(completed_trades),
            'winners': len(winners),
            'losers': len(losers),
            'pending': len(trades) - len(completed_trades),
            'win_rate': (len(winners) / len(completed_trades) * 100) if completed_trades else 0,
            'bullish_count': len(bullish_trades),
            'bearish_count': len(bearish_trades),
            'enhanced_count': len(enhanced),
            'normal_count': len(normal),
            'bullish_win_rate': (sum(1 for t in bullish_trades if t.hit_target) / len(bullish_trades) * 100) if bullish_trades else 0,
            'bearish_win_rate': (sum(1 for t in bearish_trades if t.hit_target) / len(bearish_trades) * 100) if bearish_trades else 0,
            'enhanced_win_rate': (sum(1 for t in enhanced if t.hit_target) / len(enhanced) * 100) if enhanced else 0,
            'normal_win_rate': (sum(1 for t in normal if t.hit_target) / len(normal) * 100) if normal else 0,
            'avg_bars_to_target': np.mean([t.bars_to_target for t in winners if t.bars_to_target]) if winners else 0,
            'avg_bars_to_stop': np.mean([t.bars_to_stop for t in losers if t.bars_to_stop]) if losers else 0,
            'avg_win': np.mean([t.pnl_pct for t in winners if t.pnl_pct]) if winners else 0,
            'avg_loss': np.mean([t.pnl_pct for t in losers if t.pnl_pct]) if losers else 0,
        }


class LevelTestingAnalyzer:
    """Analyze how price tests support and resistance levels."""
    
    @staticmethod
    def analyze_level_interactions(trades: List[PatternTrade],
                                  df: pd.DataFrame) -> List[Dict]:
        """
        Analyze level testing and bounces.
        
        Args:
            trades: List of trades
            df: OHLCV DataFrame
        
        Returns:
            List of level interaction data
        """
        interactions = []
        
        for trade in trades:
            entry_idx = df.index.get_loc(trade.entry_time)
            
            for j in range(entry_idx, min(entry_idx + 20, len(df))):
                bar = df.iloc[j]
                
                if trade.pattern.pattern_type == PatternType.BULLISH:
                    # Support test
                    if trade.support_tested and bar['close'] > trade.pattern.support_level:
                        interactions.append({
                            'trade': trade,
                            'level_type': 'support',
                            'level_price': trade.pattern.support_level,
                            'bar_index': j,
                            'bounced': bar['close'] > bar['open'],
                        })
                
                else:  # BEARISH
                    # Resistance test
                    if trade.resistance_tested and bar['close'] < trade.pattern.resistance_level:
                        interactions.append({
                            'trade': trade,
                            'level_type': 'resistance',
                            'level_price': trade.pattern.resistance_level,
                            'bar_index': j,
                            'bounced': bar['close'] < bar['open'],
                        })
        
        return interactions


class PatternStrengthAnalyzer:
    """Analyze pattern strength vs win rate correlation."""
    
    @staticmethod
    def analyze_by_strength(trades: List[PatternTrade],
                           strength_buckets: int = 5) -> List[Dict]:
        """
        Group trades by pattern strength and calculate win rate.
        
        Args:
            trades: List of trades
            strength_buckets: Number of strength groups
        
        Returns:
            List of strength group statistics
        """
        if not trades:
            return []
        
        # Group by strength
        min_strength = min(t.pattern.strength for t in trades)
        max_strength = max(t.pattern.strength for t in trades)
        bucket_size = (max_strength - min_strength) / strength_buckets
        
        groups = []
        
        for i in range(strength_buckets):
            lower = min_strength + (i * bucket_size)
            upper = min_strength + ((i + 1) * bucket_size)
            
            group_trades = [t for t in trades 
                          if lower <= t.pattern.strength <= upper]
            
            if not group_trades:
                continue
            
            completed = [t for t in group_trades if t.exit_price is not None]
            winners = [t for t in completed if t.hit_target]
            
            groups.append({
                'strength_range': f'{lower:.0f}-{upper:.0f}%',
                'count': len(group_trades),
                'completed': len(completed),
                'winners': len(winners),
                'win_rate': (len(winners) / len(completed) * 100) if completed else 0,
                'avg_bars_to_target': np.mean([t.bars_to_target for t in winners if t.bars_to_target]) if winners else 0,
            })
        
        return groups


class ThreeBarReversalReporter:
    """Generate three-bar reversal pattern reports."""
    
    @staticmethod
    def generate_performance_report(trades: List[PatternTrade]) -> str:
        """Generate overall performance report."""
        
        stats = PatternPerformanceAnalyzer.calculate_statistics(trades)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║     THREE BAR REVERSAL - PERFORMANCE ANALYSIS REPORT           ║
╚════════════════════════════════════════════════════════════════╝

📊 Pattern Statistics:
   Total Patterns: {stats.get('total_patterns', 0)}
   Completed Trades: {stats.get('completed_trades', 0)}
   Pending: {stats.get('pending', 0)}

✓ Overall Win Rate: {stats.get('win_rate', 0):.1f}%
   Winners: {stats.get('winners', 0)}
   Losers: {stats.get('losers', 0)}

📈 Bullish Patterns:
   Count: {stats.get('bullish_count', 0)}
   Win Rate: {stats.get('bullish_win_rate', 0):.1f}%

📉 Bearish Patterns:
   Count: {stats.get('bearish_count', 0)}
   Win Rate: {stats.get('bearish_win_rate', 0):.1f}%

🔥 Enhanced vs Normal:
   Enhanced: {stats.get('enhanced_count', 0)} ({stats.get('enhanced_win_rate', 0):.1f}% win rate)
   Normal: {stats.get('normal_count', 0)} ({stats.get('normal_win_rate', 0):.1f}% win rate)

💰 P&L Statistics:
   Avg Winner: {stats.get('avg_win', 0):+.2f}%
   Avg Loser: {stats.get('avg_loss', 0):+.2f}%

⏱️ Timing:
   Avg Bars to Target: {stats.get('avg_bars_to_target', 0):.0f}
   Avg Bars to Stop: {stats.get('avg_bars_to_stop', 0):.0f}

"""
        return report
    
    @staticmethod
    def generate_pattern_summary(patterns: List[ThreeBar]) -> str:
        """Generate pattern summary."""
        
        bullish = [p for p in patterns if p.pattern_type == PatternType.BULLISH]
        bearish = [p for p in patterns if p.pattern_type == PatternType.BEARISH]
        enhanced = [p for p in patterns if p.is_enhanced]
        normal = [p for p in patterns if not p.is_enhanced]
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║         THREE BAR REVERSAL - PATTERN SUMMARY                   ║
╚════════════════════════════════════════════════════════════════╝

📌 Pattern Count:
   Total: {len(patterns)}
   Bullish: {len(bullish)}
   Bearish: {len(bearish)}

💪 Pattern Type:
   Enhanced: {len(enhanced)}
   Normal: {len(normal)}

📊 Strength Analysis:
   Avg Strength: {np.mean([p.strength for p in patterns]):.0f}%
   Strongest: {max([p.strength for p in patterns]):.0f}%
   Weakest: {min([p.strength for p in patterns]):.0f}%

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
    
    from luxalgo_three_bar_reversal import ThreeBarReversal, PatternMode, TrendIndicator, TrendFilter
    
    tbr = ThreeBarReversal(
        pattern_mode=PatternMode.ENHANCED,
        trend_indicator=TrendIndicator.MA_CLOUD,
        trend_filter=TrendFilter.ALIGNED
    )
    df_result, results = tbr.analyze(df)
    
    print("=" * 70)
    print("THREE BAR REVERSAL - ADVANCED ANALYSIS")
    print("=" * 70)
    
    trades = PatternPerformanceAnalyzer.analyze_trades(
        results['patterns'], df_result
    )
    
    reporter = ThreeBarReversalReporter()
    print(reporter.generate_performance_report(trades))
    print(reporter.generate_pattern_summary(results['patterns']))
    
    strength_analysis = PatternStrengthAnalyzer.analyze_by_strength(trades)
    print("\n💪 Win Rate by Pattern Strength:\n")
    for group in strength_analysis:
        print(f"  {group['strength_range']}: {group['win_rate']:.1f}% ({group['count']} patterns)")
