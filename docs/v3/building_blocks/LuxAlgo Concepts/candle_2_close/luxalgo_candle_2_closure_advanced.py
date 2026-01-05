"""
LuxAlgo Candle 2 Closure - Advanced Analysis
============================================

Advanced utilities for Candle 2 Closure including pattern performance tracking,
multi-timeframe analysis, and professional reporting.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from luxalgo_candle_2_closure import (
    Candle2ClosurePattern, PatternType, Candle2Closure
)


@dataclass
class PatternTrade:
    """Track pattern trade from signal to exit."""
    pattern: Candle2ClosurePattern
    entry_time: pd.Timestamp
    entry_price: float
    
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    
    bars_to_target: Optional[int] = None
    bars_to_stop: Optional[int] = None
    
    zone_tested: bool = False
    zone_bounce: bool = False
    hit_target: bool = False
    hit_stop: bool = False


class PatternPerformanceAnalyzer:
    """Analyze Candle 2 Closure pattern performance."""
    
    @staticmethod
    def analyze_trades(patterns: List[Candle2ClosurePattern],
                      df: pd.DataFrame,
                      entry_offset_bars: int = 1,
                      lookforward_bars: int = 50,
                      stop_atr_mult: float = 2.0) -> List[PatternTrade]:
        """
        Analyze pattern trades from entry to exit.
        
        Args:
            patterns: List of detected patterns
            df: OHLCV DataFrame with ATR
            entry_offset_bars: Bars to wait for entry
            lookforward_bars: Bars to look forward
            stop_atr_mult: ATR multiplier for stop
        
        Returns:
            List of PatternTrade objects
        """
        trades = []
        
        for pattern in patterns:
            c2_idx = pattern.candle_2.index
            entry_idx = min(c2_idx + entry_offset_bars, len(df) - 1)
            
            if entry_idx >= len(df):
                continue
            
            entry_time = df.index[entry_idx]
            entry_price = df.iloc[entry_idx]['close']
            
            # Determine target and stop
            if pattern.pattern_type == PatternType.BULLISH:
                target_price = pattern.candle_3_zone.high
                stop_price = pattern.candle_2_zone.low
            else:
                target_price = pattern.candle_3_zone.low
                stop_price = pattern.candle_2_zone.high
            
            # Look forward
            lookforward_end = min(entry_idx + lookforward_bars, len(df))
            future_bars = df.iloc[entry_idx:lookforward_end]
            
            trade = PatternTrade(
                pattern=pattern,
                entry_time=entry_time,
                entry_price=entry_price,
            )
            
            # Scan for target/stop hit
            for j, (idx, bar) in enumerate(future_bars.iterrows()):
                zone_tested = False
                
                if pattern.pattern_type == PatternType.BULLISH:
                    # Check if price touched zone
                    if bar['low'] <= pattern.candle_2_zone.low:
                        zone_tested = True
                        trade.zone_tested = True
                    
                    # Check for target
                    if bar['high'] >= target_price:
                        trade.exit_price = target_price
                        trade.exit_time = idx
                        trade.hit_target = True
                        trade.bars_to_target = j
                        break
                    
                    # Check for stop
                    if bar['low'] < stop_price:
                        trade.exit_price = stop_price
                        trade.exit_time = idx
                        trade.hit_stop = True
                        trade.bars_to_stop = j
                        break
                
                else:  # BEARISH
                    # Check if price touched zone
                    if bar['high'] >= pattern.candle_2_zone.high:
                        zone_tested = True
                        trade.zone_tested = True
                    
                    # Check for target
                    if bar['low'] <= target_price:
                        trade.exit_price = target_price
                        trade.exit_time = idx
                        trade.hit_target = True
                        trade.bars_to_target = j
                        break
                    
                    # Check for stop
                    if bar['high'] > stop_price:
                        trade.exit_price = stop_price
                        trade.exit_time = idx
                        trade.hit_stop = True
                        trade.bars_to_stop = j
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
        
        zone_tested = [t for t in completed_trades if t.zone_tested]
        
        return {
            'total_patterns': len(trades),
            'completed_trades': len(completed_trades),
            'winners': len(winners),
            'losers': len(losers),
            'pending': len(trades) - len(completed_trades),
            'win_rate': (len(winners) / len(completed_trades) * 100) if completed_trades else 0,
            'bullish_count': len(bullish_trades),
            'bearish_count': len(bearish_trades),
            'bullish_win_rate': (sum(1 for t in bullish_trades if t.hit_target) / len(bullish_trades) * 100) if bullish_trades else 0,
            'bearish_win_rate': (sum(1 for t in bearish_trades if t.hit_target) / len(bearish_trades) * 100) if bearish_trades else 0,
            'zone_tested_pct': (len(zone_tested) / len(completed_trades) * 100) if completed_trades else 0,
            'avg_bars_to_target': np.mean([t.bars_to_target for t in winners if t.bars_to_target]) if winners else 0,
            'avg_bars_to_stop': np.mean([t.bars_to_stop for t in losers if t.bars_to_stop]) if losers else 0,
            'avg_win': np.mean([t.pnl_pct for t in winners if t.pnl_pct]) if winners else 0,
            'avg_loss': np.mean([t.pnl_pct for t in losers if t.pnl_pct]) if losers else 0,
        }


class EquilibriumZoneAnalyzer:
    """Analyze behavior at equilibrium zones."""
    
    @staticmethod
    def analyze_zone_interactions(trades: List[PatternTrade],
                                 df: pd.DataFrame) -> List[Dict]:
        """
        Analyze how price behaves at equilibrium zones.
        
        Args:
            trades: List of trades
            df: OHLCV DataFrame
        
        Returns:
            List of zone interaction analysis
        """
        interactions = []
        
        for trade in trades:
            if trade.pattern.pattern_type == PatternType.BULLISH:
                zone = trade.pattern.candle_2_zone
                zone_low = zone.low
                zone_high = zone.high
                
                # Get bars from entry forward
                entry_idx = df.index.get_loc(trade.entry_time)
                for j in range(entry_idx, min(entry_idx + 20, len(df))):
                    bar = df.iloc[j]
                    
                    # Did price touch zone?
                    if bar['low'] <= zone_low < bar['high']:
                        interactions.append({
                            'trade': trade,
                            'type': 'zone_touch',
                            'level': zone_low,
                            'bar_index': j,
                            'bounce': bar['close'] > zone_high if j > entry_idx else None,
                        })
            
            else:  # BEARISH
                zone = trade.pattern.candle_2_zone
                zone_low = zone.low
                zone_high = zone.high
                
                entry_idx = df.index.get_loc(trade.entry_time)
                for j in range(entry_idx, min(entry_idx + 20, len(df))):
                    bar = df.iloc[j]
                    
                    if bar['low'] < zone_high <= bar['high']:
                        interactions.append({
                            'trade': trade,
                            'type': 'zone_touch',
                            'level': zone_high,
                            'bar_index': j,
                            'bounce': bar['close'] < zone_low if j > entry_idx else None,
                        })
        
        return interactions


class MultiTimeframeAnalyzer:
    """Analyze patterns across timeframes."""
    
    @staticmethod
    def find_aligned_patterns(patterns_higher_tf: List[Candle2ClosurePattern],
                             patterns_lower_tf: List[Candle2ClosurePattern],
                             alignment_window_bars: int = 5) -> List[Dict]:
        """
        Find patterns that align across timeframes.
        
        Args:
            patterns_higher_tf: Patterns on higher timeframe
            patterns_lower_tf: Patterns on lower timeframe
            alignment_window_bars: Time window for alignment
        
        Returns:
            List of aligned pattern pairs
        """
        aligned = []
        
        for h_pattern in patterns_higher_tf:
            # Find lower TF patterns within window
            matching_lower = [p for p in patterns_lower_tf 
                            if abs((p.candle_2.timestamp - h_pattern.candle_2.timestamp).total_seconds()) 
                               < (86400 * alignment_window_bars)]
            
            if matching_lower:
                # Check direction alignment
                same_dir = [p for p in matching_lower 
                           if p.pattern_type == h_pattern.pattern_type]
                
                if same_dir:
                    aligned.append({
                        'higher_tf_pattern': h_pattern,
                        'lower_tf_patterns': same_dir,
                        'alignment_strength': len(same_dir),
                        'confidence': 'high' if len(same_dir) > 1 else 'medium',
                    })
        
        return aligned


class Candle2ClosureReporter:
    """Generate Candle 2 Closure reports."""
    
    @staticmethod
    def generate_performance_report(trades: List[PatternTrade]) -> str:
        """Generate performance analysis report."""
        
        stats = PatternPerformanceAnalyzer.calculate_statistics(trades)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║        CANDLE 2 CLOSURE - PERFORMANCE ANALYSIS REPORT          ║
╚════════════════════════════════════════════════════════════════╝

📊 Overall Statistics:
   Total Patterns: {stats.get('total_patterns', 0)}
   Completed Trades: {stats.get('completed_trades', 0)}
   Pending: {stats.get('pending', 0)}

✓ Win Rate: {stats.get('win_rate', 0):.1f}%
   Winners: {stats.get('winners', 0)}
   Losers: {stats.get('losers', 0)}

📈 Bullish Patterns:
   Count: {stats.get('bullish_count', 0)}
   Win Rate: {stats.get('bullish_win_rate', 0):.1f}%

📉 Bearish Patterns:
   Count: {stats.get('bearish_count', 0)}
   Win Rate: {stats.get('bearish_win_rate', 0):.1f}%

💰 P&L Statistics:
   Avg Winner: {stats.get('avg_win', 0):+.2f}%
   Avg Loser: {stats.get('avg_loss', 0):+.2f}%

⏱️ Timing:
   Avg Bars to Target: {stats.get('avg_bars_to_target', 0):.0f}
   Avg Bars to Stop: {stats.get('avg_bars_to_stop', 0):.0f}

🎯 Zone Statistics:
   Zone Tested: {stats.get('zone_tested_pct', 0):.1f}%

"""
        return report
    
    @staticmethod
    def generate_pattern_summary(patterns: List[Candle2ClosurePattern]) -> str:
        """Generate pattern summary."""
        
        bullish = [p for p in patterns if p.pattern_type == PatternType.BULLISH]
        bearish = [p for p in patterns if p.pattern_type == PatternType.BEARISH]
        c3_confirmed = [p for p in patterns if p.candle_3_confirmed]
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║         CANDLE 2 CLOSURE - PATTERN SUMMARY                     ║
╚════════════════════════════════════════════════════════════════╝

📌 Pattern Count:
   Total: {len(patterns)}
   Bullish: {len(bullish)}
   Bearish: {len(bearish)}

✓ Confirmation Status:
   C3 Confirmed: {len(c3_confirmed)} ({len(c3_confirmed)/len(patterns)*100:.1f}%)

💪 Strength Analysis:
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
    
    c2c = Candle2Closure(reversal_filter=True)
    df_result, results = c2c.analyze(df)
    
    print("=" * 70)
    print("CANDLE 2 CLOSURE - ADVANCED ANALYSIS")
    print("=" * 70)
    
    trades = PatternPerformanceAnalyzer.analyze_trades(
        results['patterns'], df_result
    )
    
    reporter = Candle2ClosureReporter()
    print(reporter.generate_performance_report(trades))
    print(reporter.generate_pattern_summary(results['patterns']))
