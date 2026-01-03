"""
Walk-Forward Test for Wyckoff Distribution - 4HR TIMEFRAME
Based on Accumulation's MTF success (4HR = selective confirmation!)
MULTICORE - Uses all CPU cores for parallel processing

Testing hypothesis: Distribution works better on higher timeframes
Expected: ~85% trending, ~12% distribution (very selective - perfect confirmation layer)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from multiprocessing import Pool, cpu_count
from functools import partial


def load_4hr_data(days: int = 180) -> pd.DataFrame:
    """Load 4HR data directly (no resampling needed)"""
    
    data_path_4hr = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_4h.csv'
    
    if not data_path_4hr.exists():
        print("⚠️ 4HR data file not found, will try resampling from 1HR...")
        return load_and_resample_to_4hr(days)
    
    print("Loading 4HR data directly...")
    df = pd.read_csv(data_path_4hr)
    
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
    
    print(f"Loaded {len(df)} 4HR bars")
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def load_and_resample_to_4hr(days: int = 180) -> pd.DataFrame:
    """Resample from 1HR to 4HR if direct 4HR not available"""
    
    data_path_1hr = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_1h.csv'
    
    if not data_path_1hr.exists():
        print("❌ Neither 4HR nor 1HR data available")
        return None
    
    print("Resampling 1HR data to 4HR...")
    df = pd.read_csv(data_path_1hr)
    
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
    
    # Filter to last N days before resampling
    cutoff_date = df['timestamp'].max() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date].copy()
    
    # Resample to 4HR
    df.set_index('timestamp', inplace=True)
    df_4hr = df.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_4hr.reset_index(inplace=True)
    
    print(f"Resampled to 4HR: {len(df_4hr)} bars")
    return df_4hr[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def process_chunk(args):
    """Process a chunk of bars sequentially (multicore worker)"""
    chunk_indices, df_full_dict, block_class, block_kwargs = args
    
    # Reconstruct full dataframe once per chunk
    df_full = pd.DataFrame(df_full_dict)
    
    # Create block instance once per chunk
    block = block_class(**block_kwargs)
    
    chunk_results = []
    
    for i in chunk_indices:
        try:
            # Create expanding window for this bar
            hist_df = df_full.iloc[:i+1]
            
            # Analyze
            result = block.analyze(hist_df)
            
            if result is not None and isinstance(result, dict):
                chunk_results.append((result, None))
            else:
                chunk_results.append((None, "Invalid result type"))
                
        except Exception as e:
            chunk_results.append((None, str(e)))
    
    return chunk_results


def test_block_walkforward_v2(block_class, block_kwargs, block_name: str, df_full: pd.DataFrame):
    """Walk-forward test using V2 methodology with MULTICORE PROCESSING"""
    
    print("="*80)
    print(f"🔬 WALK-FORWARD TEST V2 (MULTICORE - 4HR): {block_name}")
    print("="*80)
    print(f"Full Dataset: {len(df_full)} bars from {df_full['timestamp'].min()} to {df_full['timestamp'].max()}")
    
    # V2 Parameters
    min_bars = 50  # Fewer bars needed for 4HR
    sample_every = 1
    
    # Get number of CPU cores
    num_cores = min(cpu_count() - 1, 31)
    print(f"🚀 Using {num_cores} CPU cores for parallel processing...")
    
    # Prepare chunks for parallel processing
    indices_to_process = list(range(min_bars, len(df_full), sample_every))
    total_bars = len(indices_to_process)
    
    # Split into chunks
    chunk_size = max(1, total_bars // num_cores)
    chunks = []
    for i in range(0, total_bars, chunk_size):
        chunk_indices = indices_to_process[i:i+chunk_size]
        chunks.append(chunk_indices)
    
    print(f"\n📦 Splitting {total_bars} bars into {len(chunks)} chunks (~{chunk_size} bars each)")
    print(f"🚀 Starting parallel processing with {num_cores} workers...")
    
    # Convert dataframe to dict once for all workers
    df_full_dict = df_full.to_dict('list')
    
    # Prepare work items
    work_items = [(chunk, df_full_dict, block_class, block_kwargs) for chunk in chunks]
    
    # Process chunks in parallel
    with Pool(processes=num_cores) as pool:
        chunk_results = pool.map(process_chunk, work_items)
    
    # Flatten results
    results = []
    errors = 0
    error_messages = []
    
    for chunk_result_list in chunk_results:
        for result, error_msg in chunk_result_list:
            if result is not None:
                results.append(result)
            else:
                errors += 1
                if len(error_messages) < 3:
                    error_messages.append(error_msg)
    
    print(f"✅ Parallel processing complete!")
    
    # Calculate metrics
    if len(results) == 0:
        print(f"\n❌ NO RESULTS PRODUCED")
        print(f"   Errors: {errors}")
        if error_messages:
            print(f"   Sample errors: {error_messages[:2]}")
        return
    
    # Extract signals and confidences
    signals = [r.get('signal', 'UNKNOWN') for r in results]
    confidences = [r.get('confidence', 0) for r in results]
    
    # Active signals
    active_signals = [s for s in signals if s not in ['NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR']]
    active_signal_rate = len(active_signals) / len(signals) if len(signals) > 0 else 0
    
    # Confidence stats
    active_confidences = [confidences[i] for i, s in enumerate(signals) if signals[i] in active_signals]
    avg_active_confidence = np.mean(active_confidences) if active_confidences else 0
    avg_all_confidence = np.mean(confidences) if confidences else 0
    std_confidence = np.std(confidences) if confidences else 0
    
    # Error rate
    total_attempts = len(results) + errors
    error_rate = errors / total_attempts if total_attempts > 0 else 0
    
    # Signal distribution
    signal_types = {}
    for s in signals:
        signal_types[s] = signal_types.get(s, 0) + 1
    
    active_signal_types = {}
    for s in active_signals:
        active_signal_types[s] = active_signal_types.get(s, 0) + 1
    
    # Summary
    print(f"\n📊 RESULTS (4HR Timeframe):")
    print(f"   Total bars sampled: {len(df_full) // sample_every}")
    print(f"   Valid results: {len(results)}")
    print(f"   Active signals: {len(active_signals)} ({active_signal_rate:.2%} of results)")
    print(f"   Errors: {errors} ({error_rate:.1%} error rate)")
    
    print(f"\n   Average confidence (when active): {avg_active_confidence:.1f}%")
    print(f"   Average confidence (all results): {avg_all_confidence:.1f}%")
    print(f"   Confidence std dev: {std_confidence:.1f}%")
    
    print(f"\n   All signal distribution:")
    for sig_type, count in sorted(signal_types.items(), key=lambda x: -x[1]):
        pct = (count / len(signals)) * 100
        print(f"      {sig_type}: {count} ({pct:.1f}%)")
    
    if active_signal_types:
        print(f"\n   Active signal breakdown:")
        for sig_type, count in sorted(active_signal_types.items(), key=lambda x: -x[1]):
            pct = (count / len(active_signals)) * 100
            print(f"      {sig_type}: {count} ({pct:.1f}%)")
    
    # Calculate signals per day
    days = (df_full['timestamp'].max() - df_full['timestamp'].min()).days
    density = len(active_signals) / max(1, days)
    print(f"\n   Active signal density: {density:.2f} signals/day")
    
    # Show first few active signals
    if active_signals:
        print(f"\n   Sample active signals (first 5):")
        count = 0
        for i, r in enumerate(results):
            if r.get('signal') in active_signals and count < 5:
                print(f"      {count+1}. {r.get('signal')} @ {r.get('timestamp')} | "
                      f"Confidence: {r.get('confidence')}%")
                count += 1
                if count >= 5:
                    break
    
    # Save results
    output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'walkforward_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'walkforward_results_{block_name}_4hr.json'
    
    # Save CSV
    csv_file = output_dir / f'walkforward_results_{block_name}_4hr_signals_trades.csv'
    signals_df = pd.DataFrame(results)
    if len(signals_df) > 0:
        if 'metadata' in signals_df.columns:
            metadata_fields = []
            for idx, row in signals_df.iterrows():
                meta = row.get('metadata', {})
                if isinstance(meta, dict):
                    metadata_fields.append(meta)
                else:
                    metadata_fields.append({})
            
            meta_df = pd.DataFrame(metadata_fields)
            signals_df = pd.concat([signals_df.drop('metadata', axis=1), meta_df], axis=1)
        
        if 'confluence_factors' in signals_df.columns:
            signals_df['confluence_factors'] = signals_df['confluence_factors'].apply(
                lambda x: ' | '.join(x) if isinstance(x, list) else str(x)
            )
        
        signals_df.to_csv(csv_file, index=False)
        print(f"\n✅ Detailed signals/trades CSV saved to: {csv_file}")
        print(f"   Total records: {len(signals_df)}")
        print(f"   Active signals in CSV: {len([s for s in signals_df['signal'] if s in active_signals])}")
    
    report = {
        'block': block_name,
        'timeframe': '4hr',
        'methodology': 'V2',
        'total_bars_sampled': len(df_full) // sample_every,
        'valid_results': len(results),
        'active_signals': len(active_signals),
        'active_signal_rate': float(active_signal_rate),
        'avg_active_confidence': float(avg_active_confidence),
        'avg_all_confidence': float(avg_all_confidence),
        'std_confidence': float(std_confidence),
        'errors': errors,
        'error_rate': float(error_rate),
        'all_signal_types': signal_types,
        'active_signal_types': active_signal_types,
        'signals_per_day': float(density),
        'test_period': {
            'start': str(df_full['timestamp'].min()),
            'end': str(df_full['timestamp'].max()),
            'days': days,
            'bars': len(df_full)
        },
        'validation_params': {
            'methodology': 'expanding_window',
            'min_bars': min_bars,
            'sample_every': sample_every,
            'total_bars_available': len(df_full)
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ JSON results saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    from src.detectors.building_blocks.wyckoff.wyckoff_distribution import WyckoffDistribution
    
    print("Loading 4HR data...")
    df = load_4hr_data(days=180)
    
    if df is not None and len(df) > 0:
        # Test with 4HR timeframe designation
        test_block_walkforward_v2(WyckoffDistribution, {'timeframe': '4hr'}, "wyckoff_distribution", df)
    else:
        print("❌ Failed to load data")
