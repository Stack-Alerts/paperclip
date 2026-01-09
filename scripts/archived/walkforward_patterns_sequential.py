"""
Sequential Detailed Walkforward Testing for Pattern Blocks
Institutional-grade validation with comprehensive metrics
SEQUENTIAL execution for reliable output
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import importlib.util
from typing import Dict, Any, List
import json


def test_pattern_walkforward(pattern_info: Dict) -> Dict:
    """Test single pattern with detailed walkforward"""
    
    name = pattern_info['name']
    
    print(f"\n{'='*80}")
    print(f"🔬 TESTING: {name}")
    print(f"{'='*80}")
    
    try:
        # Load data
        data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
        df = pd.read_csv(data_path)
        
        if 'Timestamp' in df.columns:
            df = df.rename(columns={'Timestamp': 'timestamp'})
        if 'Vol' in df.columns:
            df = df.rename(columns={'Vol': 'volume'})
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Last 180 days
        cutoff_date = df['timestamp'].max() - timedelta(days=180)
        df = df[df['timestamp'] >= cutoff_date].copy()
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
        
        print(f"Data: {len(df)} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")
        
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
            return {'name': name, 'error': f'Class {pattern_info["class"]} not found'}
        
        # Initialize block
        block = BlockClass(timeframe='15min')
        
        # Generate signals with walkforward
        signals = []
        window_size = 800
        
        print(f"Generating signals...")
        for i in range(window_size, len(df) - 25, 10):
            try:
                hist_df = df.iloc[:i+1].copy()
                result = block.analyze(hist_df)
                
                if result and isinstance(result, dict):
                    signal_type = result.get('signal', '')
                    if signal_type not in ['ERROR', 'INSUFFICIENT_DATA', 'NEUTRAL', 'NO_PATTERN', '']:
                        result['index'] = i
                        signals.append(result)
            except:
                pass
        
        print(f"Generated {len(signals)} signals")
        
        if len(signals) == 0:
            return {'name': name, 'error': 'No signals generated'}
        
        # Validate each signal
        lookforward_bars = 20
        trades = []
        
        print(f"Validating signals...")
        for signal in signals:
            signal_idx = signal.get('index', 0)
            if signal_idx <= 0:
                continue
                
            signal_type = signal.get('signal', '').upper()
            entry_price = df.iloc[signal_idx]['close']
            entry_time = df.iloc[signal_idx]['timestamp']
            
            # Look forward
            end_idx = min(signal_idx + lookforward_bars, len(df) - 1)
            future_df = df.iloc[signal_idx+1:end_idx+1]
            
            if len(future_df) == 0:
                continue
            
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
                continue
            
            holding_bars = len(future_df)
            holding_hours = holding_bars * 0.25
            
            trades.append({
                'pattern': name,
                'entry_time': str(entry_time),
                'exit_time': str(exit_time),
                'signal_type': signal_type,
                'entry_price': float(entry_price),
                'exit_price': float(exit_price),
                'max_profit_pct': float(max_profit),
                'max_loss_pct': float(max_loss),
                'final_pnl_pct': float(final_pnl),
                'win': bool(win),
                'holding_bars': int(holding_bars),
                'holding_hours': float(holding_hours),
                'confidence': float(signal.get('confidence', 50))
            })
        
        print(f"Validated {len(trades)} trades")
        
        if len(trades) == 0:
            return {'name': name, 'error': 'No valid trades'}
        
        # Analyze trades
        trades_df = pd.DataFrame(trades)
        
        total_trades = len(trades_df)
        wins = trades_df[trades_df['win'] == True]
        losses = trades_df[trades_df['win'] == False]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = float(wins['final_pnl_pct'].mean()) if len(wins) > 0 else 0.0
        avg_loss = float(losses['final_pnl_pct'].mean()) if len(losses) > 0 else 0.0
        avg_pnl = float(trades_df['final_pnl_pct'].mean())
        total_pnl = float(trades_df['final_pnl_pct'].sum())
        
        gross_profit = float(wins['final_pnl_pct'].sum()) if len(wins) > 0 else 0.0
        gross_loss = abs(float(losses['final_pnl_pct'].sum())) if len(losses) > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
        
        best_trade_idx = trades_df['final_pnl_pct'].idxmax()
        worst_trade_idx = trades_df['final_pnl_pct'].idxmin()
        best_trade = trades_df.loc[best_trade_idx].to_dict()
        worst_trade = trades_df.loc[worst_trade_idx].to_dict()
        
        avg_holding_hours = float(trades_df['holding_hours'].mean())
        
        bullish_trades = trades_df[trades_df['signal_type'].str.contains('BULLISH|BUY', na=False)]
        bearish_trades = trades_df[trades_df['signal_type'].str.contains('BEARISH|SELL', na=False)]
        
        bullish_win_rate = float((len(bullish_trades[bullish_trades['win'] == True]) / len(bullish_trades) * 100)) if len(bullish_trades) > 0 else 0.0
        bearish_win_rate = float((len(bearish_trades[bearish_trades['win'] == True]) / len(bearish_trades) * 100)) if len(bearish_trades) > 0 else 0.0
        
        # Monthly breakdown
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
        monthly_stats = []
        for month, group in trades_df.groupby('month'):
            monthly_stats.append({
                'month': str(month),
                'trades': int(len(group)),
                'wins': int(len(group[group['win'] == True])),
                'win_rate': float(len(group[group['win'] == True]) / len(group) * 100),
                'avg_pnl': float(group['final_pnl_pct'].mean()),
                'total_pnl': float(group['final_pnl_pct'].sum())
            })
        
        # Consecutive wins/losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        consecutive_wins = 0
        consecutive_losses = 0
        
        for win in trades_df['win']:
            if win:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        # Drawdown
        cumulative_pnl = trades_df['final_pnl_pct'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - running_max
        max_drawdown = float(drawdown.min())
        
        result = {
            'pattern_name': name,
            'total_trades': int(total_trades),
            'wins': int(win_count),
            'losses': int(loss_count),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'avg_pnl': float(avg_pnl),
            'total_pnl': float(total_pnl),
            'profit_factor': float(profit_factor),
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_holding_hours': float(avg_holding_hours),
            'bullish_trades': int(len(bullish_trades)),
            'bearish_trades': int(len(bearish_trades)),
            'bullish_win_rate': float(bullish_win_rate),
            'bearish_win_rate': float(bearish_win_rate),
            'max_consecutive_wins': int(max_consecutive_wins),
            'max_consecutive_losses': int(max_consecutive_losses),
            'max_drawdown_pct': float(max_drawdown),
            'monthly_performance': monthly_stats,
            'production_ready': win_rate >= 50 and avg_pnl > 0 and profit_factor > 1.0,
            'all_trades': trades
        }
        
        print(f"✅ {name}: {total_trades} trades, {win_rate:.1f}% win rate\n")
        
        return result
        
    except Exception as e:
        print(f"❌ {name}: Error - {str(e)}\n")
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🚀 DETAILED WALKFORWARD - ALL 15 PATTERN BLOCKS")
    print(f"{'='*80}\n")
    print(f"Testing Period: Last 180 days")
    print(f"Lookforward: 20 bars (5 hours)")
    print(f"Institutional-grade detailed metrics\n")
    
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
    
    results = {}
    production_ready = 0
    
    for pattern_info in patterns:
        result = test_pattern_walkforward(pattern_info)
        results[pattern_info['name']] = result
        if result.get('production_ready'):
            production_ready += 1
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 DETAILED SUMMARY - ALL 15 PATTERN BLOCKS")
    print(f"{'='*80}\n")
    
    for name in sorted(results.keys()):
        data = results[name]
        if 'error' in data:
            print(f"❌ {name}: {data['error']}")
        else:
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
    print("✅ Detailed results saved\n")
    
    return results


if __name__ == "__main__":
    results = main()
