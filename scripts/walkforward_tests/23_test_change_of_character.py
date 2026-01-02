"""
Walk-Forward Test for Change Of Character
Auto-generated test script for individual block validation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data"""
    data_path = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    df = pd.read_csv(data_path)
    
    # Standardize column names
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
    
    # Filter to last N days
    cutoff_date = df['timestamp'].max() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date].copy()
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def test_block_walkforward(block, block_name: str, df_full: pd.DataFrame):
    """Walk-forward test the block"""
    
    print("="*80)
    print(f"🔬 WALK-FORWARD TEST: {block_name}")
    print("="*80)
    print(f"Full Dataset: {len(df_full)} bars from {df_full['timestamp'].min()} to {df_full['timestamp'].max()}")
    
    # Test on full period
    all_signals = []
    window_size = 100
    
    print(f"\nTesting with expanding window (min {window_size} bars)...")
    
    for i in range(window_size, len(df_full), 20):  # Test every 20th bar
        hist_df = df_full.iloc[:i+1].copy()
        
        try:
            result = block.analyze(hist_df)
            
            if result and isinstance(result, dict):
                signal = result.get('signal', 'UNKNOWN')
                confidence = result.get('confidence', 0)
                
                # Skip non-actionable signals
                if signal not in ['NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR', 'NO_BREAK']:
                    all_signals.append({
                        'timestamp': hist_df['timestamp'].iloc[-1],
                        'signal': signal,
                        'confidence': confidence,
                        'price': hist_df['close'].iloc[-1],
                        'bar_index': i
                    })
                    
                    if len(all_signals) <= 10:  # Show first 10 signals
                        print(f"  🎯 Signal {len(all_signals)}: {signal} @ {hist_df['timestamp'].iloc[-1]} | "
                              f"Price: ${hist_df['close'].iloc[-1]:.2f} | Confidence: {confidence}%")
        
        except Exception as e:
            if i == window_size:  # Only print first error
                print(f"  ⚠️  Error at bar {i}: {e}")
    
    # Summary
    print(f"\n📊 RESULTS:")
    print(f"   Total signals: {len(all_signals)}")
    
    if all_signals:
        confidences = [s['confidence'] for s in all_signals]
        print(f"   Avg confidence: {np.mean(confidences):.1f}%")
        
        # Signal types
        signal_types = {}
        for s in all_signals:
            signal_types[s['signal']] = signal_types.get(s['signal'], 0) + 1
        
        print(f"   Signal distribution:")
        for sig_type, count in sorted(signal_types.items(), key=lambda x: -x[1]):
            print(f"      {sig_type}: {count}")
        
        # Calculate signals per day
        days = (df_full['timestamp'].max() - df_full['timestamp'].min()).days
        density = len(all_signals) / max(1, days)
        print(f"\n   Signal density: {density:.2f} signals/day")
        
        # Save results to proper directory structure
        output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'walkforward_tests'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f'walkforward_results_{block_name}.json'
        results = {
            'block': block_name,
            'total_signals': len(all_signals),
            'avg_confidence': float(np.mean(confidences)),
            'signal_types': signal_types,
            'signals_per_day': float(density),
            'test_period': {
                'start': str(df_full['timestamp'].min()),
                'end': str(df_full['timestamp'].max()),
                'days': days,
                'bars': len(df_full)
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Results saved to: {output_file}")
    else:
        print("   ❌ NO SIGNALS GENERATED")
    
    print("="*80)


if __name__ == "__main__":
    from src.detectors.building_blocks.smc_ict.change_of_character import ChangeOfCharacter
    
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    
    if df is not None and len(df) > 0:
        block = ChangeOfCharacter()
        test_block_walkforward(block, "change_of_character", df)
    else:
        print("❌ Failed to load data")
