"""
MULTICORE Detailed Walkforward Testing for All Pattern Blocks
Institutional-grade validation with comprehensive metrics - PARALLEL EXECUTION

For each pattern (tested in parallel):
- 180 days walkforward test
- Detailed signal analysis
- Win/loss breakdown
- Holding period analysis
- Monthly performance
- Drawdown analysis
- Best/worst trades
"""

import sys
import os
from multiprocessing import Pool, cpu_count
import json


def test_pattern_walkforward_worker(args):
    """Test single pattern with detailed walkforward (worker for multiprocessing)"""
    
    # Import inside worker for multiprocessing
    import pandas as pd
    import numpy as np
    from pathlib import Path
    from datetime import datetime, timedelta
    import importlib.util
    from typing import Dict, Any, List
    
    pattern_info, = args
    name = pattern_info['name']
    
    print(f"\n[{name}] Starting detailed walkforward test...")
    
    try:
        # Load data
        data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
        df = pd.read_csv(data_path)
        
        if 'Timestamp' in df.columns:
            df = df.rename(columns={'Timestamp': 'timestamp'})
        if 'Vol' in df.columns:
            df = df.rename(columns={'Vol': 'volume'})
        
        if df['timestamp'].dtype == 'object':
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Last 180 days
        cutoff_date = df['timestamp'].max() - timedelta(days=180)
        df = df[df['timestamp'] >= cutoff_date].copy()
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
        
        print(f"[{name}] Data: {len(df)} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Load block
        block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / pattern_info['path']
        
        if not block_path.exists():
            return {'name': name, 'error': 'File not found'}
        
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get block class
        if hasattr(module, pattern_info['class']):
            BlockClass = getattr(module, pattern_info['class'])
        else:
            for cls_name in dir(module):
                obj = getattr(module, cls_name)
                if isinstance(obj, type) and hasattr(obj, 'analyze'):
                    BlockClass = obj
                    break
            else:
                return {'name': name, 'error': 'Could not find block class'}
        
        # Initialize block
        block = BlockClass(timeframe='15min')
        
        # Generate signals with walkforward
        signals = []
        window_size = 800
        
        print(f"[{name}] Generating signals...")
        for i in range(window_size, len(df) - 25, 10):  # Leave room for lookforward
            try:
                hist_df = df.iloc[:i+1].copy()
                result = block.analyze(hist_df)
                
                if result and isinstance(result, dict):
                    signal_type = result.get('signal', '')
                    if signal_type not in ['ERROR', 'INSUFFICIENT_DATA', 'NEUTRAL', 'NO_PATTERN', '']:
                        result['index'] = i
                        signals.append(result)
            except Exception as e:
                pass
        
        print(f"[{name}] Generated {len(signals)} signals")
        
        if len(signals) == 0:
            return {'name': name, 'error': 'No signals generated'}
        
        # Validate each signal
        lookforward_bars = 20
        trades = []
        
        print(f"[{name}] Validating signals...")
        for signal in signals:
            signal_idx = signal.get('index', 0)
            if signal_idx <= 0:
                continue
                
            signal_type = signal.get('signal', '').upper()
            entry_price = df.iloc[signal_idx]['close']
            entry_time = df.iloc[signal_idx]['timestamp']
            
            # Look forward to determine outcome
            end_idx = min(signal_idx + lookforward_bars, len(df) - 1)
            future_df = df.iloc[signal_idx+1:end_idx+1]
            
            if len(future_df) == 0:
                continue
            
            # Calculate metrics
            future_high = future_df['high'].max()
            future_low = future_df['low'].min()
            exit_price = future_df.iloc[-1]['close']
            exit_time = future_df.iloc[-1]['timestamp']
            
            # Determine win/loss
            if 'BULLISH' in signal_type or 'BUY' in signal_type:
                max_profit = (future_high - entry_price) / entry_price * 100
                max_loss = (future_low - entry_price) / entry_price * 100
                final_pnl = (exit_price - entry_price) / entry_price * 100
                win = final_pnl > 0
                
            elif 'BEARISH' in signal_type or 'SELL' in signal_type:
                max_profit = (entry_price - future_low) / entry_price * 100
                max_loss = (entry_price - future_high) / entry_price * 100
                final_pnl = (entry_price - exit_price) / entry_price * 100
                win = final_pnl > 0
            else:
                # Neutral or unknown
                continue
            
            # Holding period
            holding_bars = len(future_df)
            holding_hours = holding_bars * 0.25  # 15min bars
            
            trades.append({
                'pattern': name,
                'entry_time': str(entry_time),
                'exit_time': str(exit_time),
                'signal_type': signal_type,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'max_profit_pct': max_profit,
                'max_loss_pct': max_loss,
                'final_pnl_pct': final_pnl,
                'win': win,
                'holding_bars': holding_bars,
                'holding_hours': holding_hours,
                'confidence': signal.get('confidence', 50)
            })
        
        print(f"[{name}] Validated {len(trades)} trades")
        
        if len(trades) == 0:
            return {'name': name, 'error': 'No valid trades'}
        
        # Analyze trades
        trades_df = pd.DataFrame(trades)
        
        # Basic stats
        total_trades = len(trades_df)
        wins = trades_df[trades_df['win'] == True]
        losses = trades_df[trades_df['win'] == False]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        # PnL stats
        avg_win = wins['final_pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['final_pnl_pct'].mean() if len(losses) > 0 else 0
        avg_pnl = trades_df['final_pnl_pct'].mean()
        total_pnl = trades_df['final_pnl_pct'].sum()
        
        # Profit factor
        gross_profit = wins['final_pnl_pct'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['final_pnl_pct'].sum()) if len(losses) > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Best/worst trades
        best_trade_idx = trades_df['final_pnl_pct'].idxmax()
        worst_trade_idx = trades_df['final_pnl_pct'].idxmin()
        best_trade = trades_df.loc[best_trade_idx].to_dict()
        worst_trade = trades_df.loc[worst_trade_idx].to_dict()
        
        # Holding period
        avg_holding_hours = trades_df['holding_hours'].mean()
        
        # Signal type breakdown
        bullish_trades = trades_df[trades_df['signal_type'].str.contains('BULLISH|BUY', na=False)]
        bearish_trades = trades_df[trades_df['signal_type'].str.contains('BEARISH|SELL', na=False)]
        
        bullish_win_rate = (len(bullish_trades[bullish_trades['win'] == True]) / len(bullish_trades) * 100) if len(bullish_trades) > 0 else 0
        bearish_win_rate = (len(bearish_trades[bearish_trades['win'] == True]) / len(bearish_trades) * 100) if len(bearish_trades) > 0 else 0
        
        # Monthly breakdown
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
        monthly_stats = []
        for month, group in trades_df.groupby('month'):
            monthly_stats.append({
                'month': str(month),
                'trades': len(group),
                'wins': len(group[group['win'] == True]),
                'win_rate': len(group[group['win'] == True]) / len(group) * 100,
                'avg_pnl': group['final_pnl_pct'].mean(),
                'total_pnl': group['final_pnl_pct'].sum()
            })
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for win in trades_df['win']:
            if win:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        # Drawdown analysis
        cumulative_pnl = trades_df['final_pnl_pct'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - running_max
        max_drawdown = drawdown.min()
        
        result = {
            'pattern_name': name,
            'total_trades': total_trades,
            'wins': win_count,
            'losses': loss_count,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_pnl': avg_pnl,
            'total_pnl': total_pnl,
            'profit_factor': profit_factor,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_holding_hours': avg_holding_hours,
            'bullish_trades': len(bullish_trades),
            'bearish_trades': len(bearish_trades),
            'bullish_win_rate': bullish_win_rate,
            'bearish_win_rate': bearish_win_rate,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'max_drawdown_pct': max_drawdown,
            'monthly_performance': monthly_stats,
            'production_ready': win_rate >= 50 and avg_pnl > 0 and profit_factor > 1.0,
            'all_trades': trades  # Include all trade data
        }
        
        print(f"[{name}] ✅ COMPLETE - {total_trades} trades, {win_rate:.1f}% win rate, {avg_pnl:.2f}% avg PnL")
        
        return result
        
    except Exception as e:
        print(f"[{name}] ❌ ERROR: {str(e)}")
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🚀 MULTICORE DETAILED WALKFORWARD - ALL 15 PATTERN BLOCKS")
    print(f"{'='*80}\n")
    print(f"Testing Period: Last 180 days")
    print(f"Lookforward: 20 bars (5 hours)")
    print(f"Institutional-grade detailed metrics")
    print(f"Using ALL CPU cores for parallel execution\n")
    
    patterns = [
        {'name': 'CupAndHandle', 'path': 'patterns/cup_and_handle.py', 'class': 'CupAndHandlePattern'},
        {'name': 'InverseHeadAndShoulders', 'path': 'patterns/inverse_head_and_shoulders.py', 'class': 'InverseHeadAndShouldersPattern'},
        {'name': 'FallingWedge', 'path': 'patterns/falling_wedge.py', 'class': 'FallingWedgePattern'},
        {'name': 'DescendingTriangle', 'path': 'patterns/descending_triangle.py', 'class': 'DescendingTrianglePattern'},
        {'name': 'RisingWedge', 'path': 'patterns/rising_wedge.py', 'class': 'RisingWedgePattern'},
        {'name': 'TripleTop', 'path': 'patterns/triple_top.py', 'class': 'TripleTopPattern'},
        {'name': 'DoubleBottom', 'path': 'patterns/double_bottom.py', 'class': 'DoubleBottomPattern'},
        {'name': 'FlagPattern', 'path': 'patterns/flag_pattern.py', 'class': 'FlagPattern'},
        {'name': 'TripleBottom', 'path': 'patterns/triple_bottom.py', 'class': 'TripleBottomPattern'},
        {'name': 'AscendingTriangle', 'path': 'patterns/ascending_triangle.py', 'class': 'AscendingTrianglePattern'},
        {'name': 'HeadAndShoulders', 'path': 'patterns/head_and_shoulders.py', 'class': 'HeadAndShouldersPattern'},
        {'name': 'RoundingBottom', 'path': 'patterns/rounding_bottom.py', 'class': 'RoundingBottomPattern'},
        {'name': 'PennantPattern', 'path': 'patterns/pennant_pattern.py', 'class': 'PennantPattern'},
        {'name': 'SymmetricalTriangle', 'path': 'patterns/symmetrical_triangle.py', 'class': 'SymmetricalTrianglePattern'},
        {'name': 'DoubleTop', 'path': 'patterns/double_top.py', 'class': 'DoubleTopPattern'},
    ]
    
    # Prepare args for multiprocessing
    args_list = [(pattern_info,) for pattern_info in patterns]
    
    # Multicore execution
    cores = cpu_count()
    print(f"Using {cores} CPU cores for parallel testing")
    print(f"Testing {len(patterns)} patterns in parallel...\n")
    print(f"{'='*80}\n")
    
    with Pool(processes=cores) as pool:
        results_list = pool.map(test_pattern_walkforward_worker, args_list)
    
    # Convert to dict
    results = {r['name'] if 'name' in r else r.get('pattern_name', 'Unknown'): r for r in results_list}
    
    # Overall summary
    print(f"\n{'='*80}")
    print(f"📊 DETAILED WALKFORWARD SUMMARY - ALL 15 PATTERN BLOCKS")
    print(f"{'='*80}\n")
    
    production_ready = 0
    for name in sorted(results.keys()):
        data = results[name]
        if 'error' in data:
            print(f"❌ {name}: {data['error']}")
        else:
            if data.get('production_ready'):
                production_ready += 1
            status = '✅' if data.get('production_ready') else '⚠️'
            print(f"{status} {name}:")
            print(f"     Trades: {data['total_trades']}, Wins: {data['wins']}, Losses: {data['losses']}")
            print(f"     Win Rate: {data['win_rate']:.1f}%, Avg Win: {data['avg_win']:.2f}%, Avg Loss: {data['avg_loss']:.2f}%")
            print(f"     Avg PnL: {data['avg_pnl']:.2f}%, Total PnL: {data['total_pnl']:.2f}%")
            print(f"     Profit Factor: {data['profit_factor']:.2f}, Max DD: {data['max_drawdown_pct']:.2f}%")
            print(f"     Avg Hold: {data['avg_holding_hours']:.1f}h")
            print(f"     Best: +{data['best_trade']['final_pnl_pct']:.2f}%, Worst: {data['worst_trade']['final_pnl_pct']:.2f}%")
            print(f"     Max Consecutive Wins: {data['max_consecutive_wins']}, Losses: {data['max_consecutive_losses']}")
            print()
    
    print(f"{'='*80}")
    print(f"Production Ready (50%+ win rate, positive avg PnL, PF>1.0): {production_ready}/15")
    print(f"{'='*80}\n")
    
    # Save results
    with open('pattern_walkforward_detailed_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("✅ Detailed results saved to pattern_walkforward_detailed_results.json\n")
    
    return results


if __name__ == "__main__":
    results = main()
