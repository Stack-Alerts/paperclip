#!/usr/bin/env python3
"""
180-Day Walkforward Test - 6 EMA Signal Blocks Only
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import building blocks
from src.detectors.building_blocks.moving_averages.ema_20_50_cross import EMA2050Cross
from src.detectors.building_blocks.moving_averages.ema_50_vector import EMA50Vector
from src.detectors.building_blocks.moving_averages.ema_55_vector import EMA55VectorBreak
from src.detectors.building_blocks.moving_averages.ema_200_trend import EMA200Trend
from src.detectors.building_blocks.moving_averages.ema_255_vector import EMA255VectorBreak
from src.detectors.building_blocks.moving_averages.ema_800_vector import EMA800VectorBreak

def load_btc_data():
    """Load BTC/USDT 15min data"""
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    df = pd.read_csv(data_path)
    
    # Normalize column names
    if 'Timestamp' in df.columns:
        df.rename(columns={
            'Timestamp': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }, inplace=True)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df

def calculate_lookforward_pnl(df, signal_idx, lookforward_bars=20):
    """Calculate PnL for lookforward period"""
    if signal_idx + lookforward_bars >= len(df):
        return None
    
    entry_price = df.iloc[signal_idx]['close']
    exit_price = df.iloc[signal_idx + lookforward_bars]['close']
    
    return ((exit_price - entry_price) / entry_price) * 100

def test_block_walkforward(block_class, block_name, df, lookforward=20):
    """Test a single block with walkforward validation"""
    
    print(f"\n{'='*80}")
    print(f"Testing: {block_name}")
    print(f"{'='*80}")
    
    # Initialize block
    block = block_class()
    
    # Collect all signals
    signals = []
    
    # Need minimum data for EMA calculation
    min_window = max(block.period if hasattr(block, 'period') else 50, 100)
    
    for i in range(min_window, len(df)):
        # Get window of data up to current bar
        window_df = df.iloc[:i+1].copy()
        
        # Analyze using the block's analyze method
        result = block.analyze(window_df)
        
        if result and result.get('signal') not in ['NEUTRAL', 'ERROR', 'INSUFFICIENT_DATA', None]:
            signal_type = result['signal']
            pnl = calculate_lookforward_pnl(df, i, lookforward)
            
            if pnl is not None:
                signals.append({
                    'timestamp': window_df['timestamp'].iloc[-1],
                    'index': i,
                    'signal': signal_type,
                    'entry_price': window_df['close'].iloc[-1],
                    'pnl': pnl,
                    'win': pnl > 0
                })
    
    # Calculate metrics
    if not signals:
        print(f"❌ NO SIGNALS GENERATED")
        return None
    
    total_trades = len(signals)
    wins = sum(1 for s in signals if s['win'])
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(s['pnl'] for s in signals)
    avg_win = np.mean([s['pnl'] for s in signals if s['win']]) if wins > 0 else 0
    avg_loss = np.mean([s['pnl'] for s in signals if not s['win']]) if losses > 0 else 0
    profit_factor = abs(avg_win * wins / (avg_loss * losses)) if losses > 0 and avg_loss != 0 else 0
    
    # Print results
    print(f"\n📊 RESULTS:")
    print(f"  Total Signals:    {total_trades}")
    print(f"  Wins:             {wins}")
    print(f"  Losses:           {losses}")
    print(f"  Win Rate:         {win_rate:.2f}%")
    print(f"  Total PnL:        {total_pnl:.2f}%")
    print(f"  Avg Win:          {avg_win:.2f}%")
    print(f"  Avg Loss:         {avg_loss:.2f}%")
    print(f"  Profit Factor:    {profit_factor:.2f}")
    
    # Production ready check
    production_ready = (
        total_trades >= 10 and
        win_rate >= 45 and
        profit_factor >= 1.0
    )
    
    status = "✅ PRODUCTION READY" if production_ready else "⚠️  NEEDS WORK"
    print(f"\n{status}")
    
    return {
        'block': block_name,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'production_ready': production_ready,
        'signals': signals
    }

def main():
    print("="*80)
    print("🎯 180-DAY WALKFORWARD TEST - 6 EMA SIGNAL BLOCKS")
    print("="*80)
    print(f"Start Time: {datetime.now()}")
    print(f"Lookforward: 20 bars (5 hours)")
    print()
    
    # Load data
    print("Loading BTC/USDT 15min data...")
    df = load_btc_data()
    
    # Use last 180 days
    cutoff_date = df['timestamp'].max() - timedelta(days=180)
    df = df[df['timestamp'] >= cutoff_date].reset_index(drop=True)
    
    print(f"Data loaded: {len(df)} bars")
    print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()
    
    # Test each block
    blocks_to_test = [
        (EMA2050Cross, "EMA 20/50 Cross"),
        (EMA50Vector, "EMA 50 Vector"),
        (EMA55VectorBreak, "EMA 55 Vector"),
        (EMA200Trend, "EMA 200 Trend"),
        (EMA255VectorBreak, "EMA 255 Vector"),
        (EMA800VectorBreak, "EMA 800 Vector"),
    ]
    
    results = {}
    
    for block_class, block_name in blocks_to_test:
        try:
            result = test_block_walkforward(block_class, block_name, df)
            if result:
                results[block_name] = result
        except Exception as e:
            print(f"❌ ERROR testing {block_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*80)
    print("📈 SUMMARY - 6 EMA BLOCKS")
    print("="*80)
    print(f"{'Block':<25} {'Trades':>8} {'Win%':>8} {'PnL%':>10} {'PF':>8} {'Status':>12}")
    print("-"*80)
    
    for block_name, data in results.items():
        status = "✅ PROD" if data['production_ready'] else "⚠️  DEV"
        print(f"{block_name:<25} {data['total_trades']:>8} {data['win_rate']:>7.1f}% {data['total_pnl']:>9.2f}% {data['profit_factor']:>7.2f} {status:>12}")
    
    print("-"*80)
    prod_ready = sum(1 for d in results.values() if d['production_ready'])
    print(f"Production Ready: {prod_ready}/6 ({prod_ready/6*100:.0f}%)")
    
    # Save results to proper directory structure
    output_dir = Path(__file__).parent.parent / 'data' / 'reports' / 'walkforward_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "ema_6_blocks_walkforward_results.json"
    with open(output_file, 'w') as f:
        # Remove signals list and convert all values to JSON-serializable types
        summary = {}
        for name, data in results.items():
            clean_data = {}
            for k, v in data.items():
                if k == 'signals':
                    continue
                elif isinstance(v, (np.integer, np.int64, np.int32)):
                    clean_data[k] = int(v)
                elif isinstance(v, (np.floating, np.float64, np.float32)):
                    clean_data[k] = float(v)
                elif isinstance(v, (np.bool_, bool)):
                    clean_data[k] = bool(v)
                elif isinstance(v, (int, float, str)):
                    clean_data[k] = v
                else:
                    clean_data[k] = str(v)
            summary[name] = clean_data
        json.dump(summary, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    print(f"End Time: {datetime.now()}")
    print("="*80)

if __name__ == "__main__":
    main()
