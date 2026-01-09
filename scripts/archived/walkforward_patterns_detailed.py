"""
Detailed Walkforward Testing for All Pattern Blocks
Institutional-grade validation with comprehensive metrics

For each pattern:
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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import importlib.util
from typing import Dict, Any, List
import json


class DetailedWalkforwardValidator:
    """Comprehensive walkforward validator with institutional metrics"""
    
    def __init__(self, pattern_name: str, lookforward_bars: int = 20):
        self.pattern_name = pattern_name
        self.lookforward_bars = lookforward_bars
        
    def validate_signal(self, df: pd.DataFrame, signal_idx: int, signal: Dict) -> Dict:
        """Validate single signal with detailed metrics"""
        
        signal_type = signal.get('signal', '').upper()
        entry_price = df.iloc[signal_idx]['close']
        entry_time = df.iloc[signal_idx]['timestamp']
        
        # Look forward to determine outcome
        end_idx = min(signal_idx + self.lookforward_bars, len(df) - 1)
        future_df = df.iloc[signal_idx+1:end_idx+1]
        
        if len(future_df) == 0:
            return None
        
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
            
            # Win if made profit
            win = final_pnl > 0
            
        elif 'BEARISH' in signal_type or 'SELL' in signal_type:
            max_profit = (entry_price - future_low) / entry_price * 100
            max_loss = (entry_price - future_high) / entry_price * 100
            final_pnl = (entry_price - exit_price) / entry_price * 100
            
            # Win if made profit
            win = final_pnl > 0
        else:
            # Neutral or unknown
            return None
        
        # Holding period
        holding_bars = len(future_df)
        holding_hours = holding_bars * 0.25  # 15min bars
        
        return {
            'pattern': self.pattern_name,
            'entry_time': entry_time,
            'exit_time': exit_time,
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
        }
    
    def analyze_trades(self, trades: List[Dict]) -> Dict:
        """Comprehensive trade analysis"""
        
        if not trades:
            return {'error': 'No trades to analyze'}
        
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
        best_trade = trades_df.loc[trades_df['final_pnl_pct'].idxmax()].to_dict()
        worst_trade = trades_df.loc[trades_df['final_pnl_pct'].idxmin()].to_dict()
        
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
        
        return {
            'pattern_name': self.pattern_name,
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
            'production_ready': win_rate >= 50 and avg_pnl > 0 and profit_factor > 1.0
        }


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
        
        if df['timestamp'].dtype == 'object':
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
        
        print(f"Generating signals...")
        for i in range(window_size, len(df) - 25, 10):  # Leave room for lookforward
            try:
                hist_df = df.iloc[:i+1].copy()
                result = block.analyze(hist_df)
                
                if result and isinstance(result, dict):
                    signal_type = result.get('signal', '')
                    if signal_type not in ['ERROR', 'INSUFFICIENT_DATA', 'NEUTRAL', '']:
                        result['index'] = i
                        signals.append(result)
            except Exception as e:
                pass
        
        print(f"Generated {len(signals)} signals")
        
        if len(signals) == 0:
            return {'name': name, 'error': 'No signals generated'}
        
        # Validate each signal
        validator = DetailedWalkforwardValidator(name, lookforward_bars=20)
        
        trades = []
        print(f"Validating signals...")
        for signal in signals:
            signal_idx = signal.get('index', 0)
            if signal_idx > 0:
                trade = validator.validate_signal(df, signal_idx, signal)
                if trade:
                    trades.append(trade)
        
        print(f"Validated {len(trades)} trades")
        
        if len(trades) == 0:
            return {'name': name, 'error': 'No valid trades'}
        
        # Analyze trades
        analysis = validator.analyze_trades(trades)
        
        # Print report
        print(f"\n📊 RESULTS for {name}:")
        print(f"   Total Trades: {analysis['total_trades']}")
        print(f"   Win Rate: {analysis['win_rate']:.1f}%")
        print(f"   Avg PnL: {analysis['avg_pnl']:.2f}%")
        print(f"   Profit Factor: {analysis['profit_factor']:.2f}")
        print(f"   Production Ready: {'✅ YES' if analysis['production_ready'] else '❌ NO'}")
        
        return analysis
        
    except Exception as e:
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🚀 DETAILED WALKFORWARD TESTING - ALL 15 PATTERN BLOCKS")
    print(f"{'='*80}\n")
    print(f"Testing Period: Last 180 days")
    print(f"Lookforward: 20 bars (5 hours)")
    print(f"Institutional-grade detailed metrics\n")
    
    patterns = [
        {'name': 'CupAndHandle', 'path': 'patterns/cup_and_handle.py', 'class': 'CupAndHandle'},
        {'name': 'InverseHeadAndShoulders', 'path': 'patterns/inverse_head_and_shoulders.py', 'class': 'InverseHeadAndShoulders'},
        {'name': 'FallingWedge', 'path': 'patterns/falling_wedge.py', 'class': 'FallingWedge'},
        {'name': 'DescendingTriangle', 'path': 'patterns/descending_triangle.py', 'class': 'DescendingTriangle'},
        {'name': 'RisingWedge', 'path': 'patterns/rising_wedge.py', 'class': 'RisingWedge'},
        {'name': 'TripleTop', 'path': 'patterns/triple_top.py', 'class': 'TripleTop'},
        {'name': 'DoubleBottom', 'path': 'patterns/double_bottom.py', 'class': 'DoubleBottom'},
        {'name': 'FlagPattern', 'path': 'patterns/flag_pattern.py', 'class': 'FlagPattern'},
        {'name': 'TripleBottom', 'path': 'patterns/triple_bottom.py', 'class': 'TripleBottom'},
        {'name': 'AscendingTriangle', 'path': 'patterns/ascending_triangle.py', 'class': 'AscendingTriangle'},
        {'name': 'HeadAndShoulders', 'path': 'patterns/head_and_shoulders.py', 'class': 'HeadAndShoulders'},
        {'name': 'RoundingBottom', 'path': 'patterns/rounding_bottom.py', 'class': 'RoundingBottom'},
        {'name': 'PennantPattern', 'path': 'patterns/pennant_pattern.py', 'class': 'PennantPattern'},
        {'name': 'SymmetricalTriangle', 'path': 'patterns/symmetrical_triangle.py', 'class': 'SymmetricalTriangle'},
        {'name': 'DoubleTop', 'path': 'patterns/double_top.py', 'class': 'DoubleTop'},
    ]
    
    results = {}
    production_ready = 0
    
    for pattern_info in patterns:
        result = test_pattern_walkforward(pattern_info)
        results[pattern_info['name']] = result
        if result.get('production_ready'):
            production_ready += 1
    
    # Overall summary
    print(f"\n{'='*80}")
    print(f"📊 OVERALL SUMMARY - ALL 15 PATTERN BLOCKS")
    print(f"{'='*80}\n")
    
    for name in sorted(results.keys()):
        data = results[name]
        if 'error' in data:
            print(f"❌ {name}: {data['error']}")
        else:
            status = '✅' if data.get('production_ready') else '⚠️'
            print(f"{status} {name}:")
            print(f"     Trades: {data['total_trades']}, Win Rate: {data['win_rate']:.1f}%, "
                  f"Avg PnL: {data['avg_pnl']:.2f}%, PF: {data['profit_factor']:.2f}")
    
    print(f"\n{'='*80}")
    print(f"Production Ready: {production_ready}/15")
    print(f"{'='*80}\n")
    
    # Save results
    with open('pattern_walkforward_detailed_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("✅ Detailed results saved to pattern_walkforward_detailed_results.json\n")
    
    return results


if __name__ == "__main__":
    results = main()
