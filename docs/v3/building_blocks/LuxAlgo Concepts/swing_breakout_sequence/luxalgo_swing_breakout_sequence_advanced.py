"""
LuxAlgo Swing Breakout Sequence - Advanced Analysis
=================================================

Advanced utilities for swing breakout sequence analysis including
trade performance tracking, pattern analysis, and optimization.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from luxalgo_swing_breakout_sequence import (
    SwingBreakoutSequence, BreakoutDirection, SequenceStatus
)


@dataclass
class SequenceTrade:
    """Track swing breakout sequence trade performance."""
    sequence: SwingBreakoutSequence
    entry_time: pd.Timestamp
    entry_price: float
    entry_reason: str  # 'point_5', 'point_3_retest', etc.
    
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    
    target_reached: bool = False
    stop_hit: bool = False
    bars_held: int = 0
    
    # Pattern characteristics
    has_point_5: bool = False
    liquidity_trapped: bool = False


class SequenceTradeAnalyzer:
    """Analyze sequence trading performance."""
    
    @staticmethod
    def generate_trades(sequences: List[SwingBreakoutSequence],
                       df: pd.DataFrame,
                       lookforward_bars: int = 50,
                       entry_on_point_5: bool = True,
                       entry_on_point_3_retest: bool = False) -> List[SequenceTrade]:
        """
        Generate trades from detected sequences.
        
        Args:
            sequences: List of sequences
            df: OHLCV DataFrame
            lookforward_bars: Bars to look forward for target/stop
            entry_on_point_5: Enter on point 5 reversal
            entry_on_point_3_retest: Enter on point 3 breakout
        
        Returns:
            List of SequenceTrade objects
        """
        trades = []
        
        for sequence in sequences:
            if sequence.status == SequenceStatus.FAILED:
                continue
            
            # Determine entry point
            entry_bar_idx = None
            entry_reason = None
            
            if entry_on_point_5 and sequence.point_5:
                entry_bar_idx = sequence.point_5.bar_index
                entry_reason = 'point_5_reversal'
            elif entry_on_point_3_retest and sequence.point_3:
                entry_bar_idx = sequence.point_3.bar_index
                entry_reason = 'point_3_breakout'
            else:
                continue
            
            if entry_bar_idx >= len(df):
                continue
            
            entry_time = df.index[entry_bar_idx]
            entry_price = df.iloc[entry_bar_idx]['close']
            
            # Determine target and stop
            if sequence.sequence_direction == BreakoutDirection.BULLISH:
                target_price = sequence.expected_breakout_price
                stop_price = sequence.stop_loss_price
            else:
                target_price = sequence.expected_breakout_price
                stop_price = sequence.stop_loss_price
            
            trade = SequenceTrade(
                sequence=sequence,
                entry_time=entry_time,
                entry_price=entry_price,
                entry_reason=entry_reason,
                has_point_5=(sequence.point_5 is not None),
            )
            
            # Look forward for target/stop hits
            end_idx = min(entry_bar_idx + lookforward_bars, len(df))
            
            for j in range(entry_bar_idx, end_idx):
                bar = df.iloc[j]
                
                if sequence.sequence_direction == BreakoutDirection.BULLISH:
                    # Target = breakout high
                    if bar['high'] >= target_price:
                        trade.exit_price = target_price
                        trade.exit_time = df.index[j]
                        trade.target_reached = True
                        trade.bars_held = j - entry_bar_idx
                        break
                    
                    # Stop = below stop
                    if bar['low'] < stop_price:
                        trade.exit_price = stop_price
                        trade.exit_time = df.index[j]
                        trade.stop_hit = True
                        trade.bars_held = j - entry_bar_idx
                        break
                
                else:  # BEARISH
                    # Target = breakout low
                    if bar['low'] <= target_price:
                        trade.exit_price = target_price
                        trade.exit_time = df.index[j]
                        trade.target_reached = True
                        trade.bars_held = j - entry_bar_idx
                        break
                    
                    # Stop = above stop
                    if bar['high'] > stop_price:
                        trade.exit_price = stop_price
                        trade.exit_time = df.index[j]
                        trade.stop_hit = True
                        trade.bars_held = j - entry_bar_idx
                        break
            
            # Calculate P&L
            if trade.exit_price:
                trade.pnl = trade.exit_price - trade.entry_price
                trade.pnl_pct = (trade.pnl / trade.entry_price) * 100
            
            trades.append(trade)
        
        return trades
    
    @staticmethod
    def calculate_statistics(trades: List[SequenceTrade]) -> Dict:
        """
        Calculate trade statistics.
        
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
        
        trades_with_p5 = [t for t in trades if t.has_point_5]
        trades_without_p5 = [t for t in trades if not t.has_point_5]
        
        bullish_trades = [t for t in trades 
                         if t.sequence.sequence_direction == BreakoutDirection.BULLISH]
        bearish_trades = [t for t in trades 
                         if t.sequence.sequence_direction == BreakoutDirection.BEARISH]
        
        return {
            'total_trades': len(trades),
            'completed': len(completed_trades),
            'pending': len(trades) - len(completed_trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': (len(winners) / len(completed_trades) * 100) if completed_trades else 0,
            'with_point_5': len(trades_with_p5),
            'without_point_5': len(trades_without_p5),
            'with_point_5_win_rate': (sum(1 for t in trades_with_p5 if t.target_reached) / len(trades_with_p5) * 100) if trades_with_p5 else 0,
            'without_point_5_win_rate': (sum(1 for t in trades_without_p5 if t.target_reached) / len(trades_without_p5) * 100) if trades_without_p5 else 0,
            'bullish_count': len(bullish_trades),
            'bearish_count': len(bearish_trades),
            'bullish_win_rate': (sum(1 for t in bullish_trades if t.target_reached) / len(bullish_trades) * 100) if bullish_trades else 0,
            'bearish_win_rate': (sum(1 for t in bearish_trades if t.target_reached) / len(bearish_trades) * 100) if bearish_trades else 0,
            'avg_bars_to_target': np.mean([t.bars_held for t in winners if t.bars_held]) if winners else 0,
            'avg_bars_to_stop': np.mean([t.bars_held for t in losers if t.bars_held]) if losers else 0,
            'avg_win': np.mean([t.pnl_pct for t in winners if t.pnl_pct]) if winners else 0,
            'avg_loss': np.mean([t.pnl_pct for t in losers if t.pnl_pct]) if losers else 0,
        }


class LiquidityTrapAnalyzer:
    """Analyze liquidity traps and failed breakouts."""
    
    @staticmethod
    def identify_liquidity_traps(sequences: List[SwingBreakoutSequence]) -> List[Dict]:
        """
        Identify liquidity trap patterns.
        
        Liquidity trap = Point 4 exceeds Point 2 (deeper into zone)
        
        Args:
            sequences: List of sequences
        
        Returns:
            List of liquidity trap data
        """
        traps = []
        
        for seq in sequences:
            if not seq.point_4 or not seq.point_2:
                continue
            
            # Check if Point 4 exceeds Point 2
            if seq.sequence_direction == BreakoutDirection.BULLISH:
                # For bullish, Point 4 low should be below Point 2 low
                if seq.point_4.price < seq.point_2.price:
                    traps.append({
                        'sequence': seq,
                        'trap_type': 'deeper_pullback',
                        'point_2_price': seq.point_2.price,
                        'point_4_price': seq.point_4.price,
                        'depth_pct': ((seq.point_2.price - seq.point_4.price) / seq.point_2.price) * 100,
                    })
            else:
                # For bearish, Point 4 high should be above Point 2 high
                if seq.point_4.price > seq.point_2.price:
                    traps.append({
                        'sequence': seq,
                        'trap_type': 'deeper_pullback',
                        'point_2_price': seq.point_2.price,
                        'point_4_price': seq.point_4.price,
                        'depth_pct': ((seq.point_4.price - seq.point_2.price) / seq.point_2.price) * 100,
                    })
        
        return traps


class SequenceStrengthAnalyzer:
    """Analyze sequence strength and component impact."""
    
    @staticmethod
    def analyze_by_strength(sequences: List[SwingBreakoutSequence],
                           strength_buckets: int = 3) -> List[Dict]:
        """
        Group sequences by strength and analyze.
        
        Args:
            sequences: List of sequences
            strength_buckets: Number of strength groups
        
        Returns:
            List of strength analysis
        """
        if not sequences:
            return []
        
        strengths = [s.sequence_strength for s in sequences]
        min_strength = min(strengths)
        max_strength = max(strengths)
        bucket_size = (max_strength - min_strength) / strength_buckets
        
        groups = []
        
        for i in range(strength_buckets):
            lower = min_strength + (i * bucket_size)
            upper = min_strength + ((i + 1) * bucket_size)
            
            group_seqs = [s for s in sequences 
                         if lower <= s.sequence_strength <= upper]
            
            if not group_seqs:
                continue
            
            groups.append({
                'strength_range': f'{lower:.0f}-{upper:.0f}%',
                'count': len(group_seqs),
                'with_p5': len([s for s in group_seqs if s.point_5]),
                'complete': len([s for s in group_seqs if s.status == SequenceStatus.COMPLETE]),
            })
        
        return groups


class SequenceReporter:
    """Generate sequence analysis reports."""
    
    @staticmethod
    def generate_trade_report(trades: List[SequenceTrade]) -> str:
        """Generate trade performance report."""
        
        stats = SequenceTradeAnalyzer.calculate_statistics(trades)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║    SWING BREAKOUT SEQUENCE - TRADE REPORT                      ║
╚════════════════════════════════════════════════════════════════╝

📊 Trade Statistics:
   Total Trades: {stats.get('total_trades', 0)}
   Completed: {stats.get('completed', 0)}
   Winners: {stats.get('winners', 0)}
   Losers: {stats.get('losers', 0)}
   Pending: {stats.get('pending', 0)}

✓ Win Rate: {stats.get('win_rate', 0):.1f}%

📊 Point 5 Analysis:
   With Point 5: {stats.get('with_point_5', 0)} ({stats.get('with_point_5_win_rate', 0):.1f}% win rate)
   Without Point 5: {stats.get('without_point_5', 0)} ({stats.get('without_point_5_win_rate', 0):.1f}% win rate)

📈 By Direction:
   Bullish: {stats.get('bullish_count', 0)} ({stats.get('bullish_win_rate', 0):.1f}% win rate)
   Bearish: {stats.get('bearish_count', 0)} ({stats.get('bearish_win_rate', 0):.1f}% win rate)

💰 P&L:
   Avg Winner: {stats.get('avg_win', 0):+.2f}%
   Avg Loser: {stats.get('avg_loss', 0):+.2f}%

⏱️ Timing:
   Avg Bars to Target: {stats.get('avg_bars_to_target', 0):.0f}
   Avg Bars to Stop: {stats.get('avg_bars_to_stop', 0):.0f}

"""
        return report
    
    @staticmethod
    def generate_sequence_summary(sequences: List[SwingBreakoutSequence]) -> str:
        """Generate sequence summary."""
        
        complete_seqs = [s for s in sequences if s.status == SequenceStatus.COMPLETE]
        incomplete_seqs = [s for s in sequences if s.status == SequenceStatus.INCOMPLETE]
        
        bullish = [s for s in sequences if s.sequence_direction == BreakoutDirection.BULLISH]
        bearish = [s for s in sequences if s.sequence_direction == BreakoutDirection.BEARISH]
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║    SWING BREAKOUT SEQUENCE - SUMMARY                           ║
╚════════════════════════════════════════════════════════════════╝

📌 Sequence Count:
   Total: {len(sequences)}
   Complete (with Point 5): {len(complete_seqs)}
   Incomplete: {len(incomplete_seqs)}

📊 Direction:
   Bullish: {len(bullish)}
   Bearish: {len(bearish)}

💪 Strength:
   Avg Strength: {np.mean([s.sequence_strength for s in sequences]):.0f}%
   Strongest: {max([s.sequence_strength for s in sequences]):.0f}%
   Weakest: {min([s.sequence_strength for s in sequences]):.0f}%

"""
        return report


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=200, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(200) * 0.2)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(200) * 0.1,
        'high': prices + np.abs(np.random.randn(200) * 0.3),
        'low': prices - np.abs(np.random.randn(200) * 0.3),
        'close': prices,
    }, index=dates)
    
    from luxalgo_swing_breakout_sequence import SwingBreakoutSequenceDetector
    
    detector = SwingBreakoutSequenceDetector()
    df_result, results = detector.analyze(df)
    
    trades = SequenceTradeAnalyzer.generate_trades(results['sequences'], df)
    
    reporter = SequenceReporter()
    print(reporter.generate_trade_report(trades))
    print(reporter.generate_sequence_summary(results['sequences']))
