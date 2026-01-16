"""
Building Block Registry Test Library
=====================================

Reusable test framework for testing all 83 building blocks via BlockRegistry.

This library provides a standardized testing function that:
- Uses BlockRegistry to instantiate blocks
- Tests all valid_signals from registry
- Runs 180-day walkforward (candle-by-candle, NO sampling)
- Uses multicore processing for efficiency
- Reports detailed signal statistics
- Handles blocks that don't accept timeframe parameter

Author: BTC_Engine_v3 - Registry Test Suite
Date: 2026-01-14
Version: 1.0
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Any

# Import registry
from src.detectors.building_blocks.registry import BlockRegistry


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data for testing"""
    data_path = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
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


def process_candle_batch(args):
    """Process a batch of candles (for multicore processing)"""
    block_name, start_idx, end_idx, df_full = args
    
    # Instantiate block for this worker (try with timeframe, fallback to no params)
    try:
        block = BlockRegistry.instantiate(block_name, timeframe='15min')
    except (TypeError, AttributeError):
        # Some blocks don't accept timeframe parameter or have registry issues
        try:
            block = BlockRegistry.instantiate(block_name)
        except Exception as e:
            # If still fails, return error for all candles in batch
            errors = [{'bar_index': i, 'error': f'Instantiation failed: {str(e)}'} 
                     for i in range(start_idx, end_idx)]
            return [], errors
    
    results = []
    errors = []
    
    for i in range(start_idx, end_idx):
        try:
            # EXPANDING window: use ALL data from beginning up to current candle
            hist_df = df_full.iloc[:i+1].copy()
            
            result = block.analyze(hist_df)
            
            # Accept any valid result
            if result is not None and isinstance(result, dict):
                result['bar_index'] = i
                results.append(result)
                
        except Exception as e:
            errors.append({
                'bar_index': i,
                'error': str(e)
            })
    
    return results, errors


def test_building_block_registry(block_name: str, days: int = 180, use_multicore: bool = True):
    """
    Test a building block using BlockRegistry
    
    Args:
        block_name: Name of block in registry
        days: Test period in days
        use_multicore: Use multicore processing for speed
    
    Returns:
        dict: Test report with results, or None if test failed
    """
    
    start_time = datetime.now()
    
    print("\n" + "="*80)
    print(f"REGISTRY-BASED BUILDING BLOCK TEST")
    print("="*80)
    print(f"Block: {block_name}")
    print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Get block metadata from registry
    metadata = BlockRegistry.get_block(block_name)
    if not metadata:
        print(f"❌ ERROR: Block '{block_name}' not found in registry")
        return None
    
    print(f"\n📋 Block Metadata:")
    print(f"   Category: {metadata.category}")
    print(f"   Class: {metadata.class_name}")
    print(f"   Default Weight: {metadata.default_weight}")
    print(f"   Valid Signals: {metadata.valid_signals}")
    
    # Load data
    print(f"\n📊 Loading {days} days of BTC 15min data...")
    try:
        df_full = load_btc_data(days=days)
    except Exception as e:
        print(f"❌ ERROR loading data: {e}")
        return None
        
    print(f"   Loaded {len(df_full)} candles")
    print(f"   Period: {df_full['timestamp'].min()} to {df_full['timestamp'].max()}")
    
    # Test configuration
    min_bars = 100  # Minimum bars before starting tests
    total_candles = len(df_full)
    test_candles = total_candles - min_bars
    
    print(f"\n🔬 Test Configuration:")
    print(f"   Total candles: {total_candles}")
    print(f"   Warmup candles: {min_bars}")
    print(f"   Test candles: {test_candles}")
    print(f"   Method: EXPANDING window (candle-by-candle)")
    print(f"   Multicore: {'ENABLED' if use_multicore else 'DISABLED'}")
    
    # Run test
    all_results = []
    all_errors = []
    
    if use_multicore and test_candles > 1000:
        # Multicore processing for large datasets
        num_workers = max(1, cpu_count() - 1)
        batch_size = test_candles // num_workers
        
        print(f"\n⚡ Multicore Processing:")
        print(f"   Workers: {num_workers}")
        print(f"   Batch size: ~{batch_size} candles/worker")
        
        # Create batches
        batches = []
        for worker_idx in range(num_workers):
            start_idx = min_bars + (worker_idx * batch_size)
            end_idx = min_bars + ((worker_idx + 1) * batch_size) if worker_idx < num_workers - 1 else total_candles
            batches.append((block_name, start_idx, end_idx, df_full))
        
        # Process in parallel
        try:
            with Pool(num_workers) as pool:
                batch_results = pool.map(process_candle_batch, batches)
            
            # Combine results
            for results, errors in batch_results:
                all_results.extend(results)
                all_errors.extend(errors)
        except Exception as e:
            print(f"❌ ERROR during multicore processing: {e}")
            print(f"   Falling back to single-core processing...")
            use_multicore = False
    
    if not use_multicore or test_candles <= 1000:
        # Single-core processing
        print(f"\n🔄 Single-core Processing...")
        try:
            block = BlockRegistry.instantiate(block_name, timeframe='15min')
        except (TypeError, AttributeError):
            # Some blocks don't accept timeframe parameter or have registry issues
            try:
                block = BlockRegistry.instantiate(block_name)
            except Exception as e:
                print(f"❌ ERROR: Cannot instantiate block: {e}")
                return None
        
        for i in range(min_bars, total_candles):
            try:
                hist_df = df_full.iloc[:i+1].copy()
                result = block.analyze(hist_df)
                
                if result is not None and isinstance(result, dict):
                    result['bar_index'] = i
                    all_results.append(result)
                    
            except Exception as e:
                all_errors.append({
                    'bar_index': i,
                    'error': str(e)
                })
            
            # Progress indicator
            if i % 5000 == 0:
                print(f"   Progress: {i-min_bars}/{test_candles} candles processed...")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Analyze results
    print(f"\n" + "="*80)
    print(f"TEST RESULTS")
    print("="*80)
    print(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    if duration > 0:
        print(f"Processing Speed: {test_candles/duration:.0f} candles/second")
    
    if len(all_results) == 0:
        print(f"\n❌ NO VALID RESULTS")
        print(f"   Errors: {len(all_errors)}")
        if all_errors[:3]:
            print(f"   Sample errors:")
            for err in all_errors[:3]:
                print(f"      Bar {err['bar_index']}: {err['error']}")
        return None
    
    # Extract signal statistics from BOTH signal and signal_simple fields
    # FIXED: Don't double-count when signal == signal_simple
    signal_counts = {}
    
    for r in all_results:
        sig_granular = r.get('signal', 'UNKNOWN')
        sig_simple = r.get('signal_simple', 'UNKNOWN')
        
        # Count granular signal
        signal_counts[sig_granular] = signal_counts.get(sig_granular, 0) + 1
        
        # Count simple signal ONLY if different from granular (avoid double-counting)
        if sig_simple != sig_granular:
            signal_counts[sig_simple] = signal_counts.get(sig_simple, 0) + 1
    
    # Check which valid_signals were found
    found_signals = set(signal_counts.keys())
    expected_signals = set(metadata.valid_signals)
    missing_signals = expected_signals - found_signals
    
    print(f"\n📊 Signal Statistics:")
    print(f"   Total results: {len(all_results)}")
    print(f"   Errors: {len(all_errors)} ({len(all_errors)/(len(all_results)+len(all_errors))*100:.1f}%)")
    print(f"   Unique signals found: {len(signal_counts)}")
    
    print(f"\n🎯 Valid Signals Coverage:")
    print(f"   Expected (from registry): {len(expected_signals)} signals")
    print(f"   Found in test: {len(found_signals)} signals")
    coverage_pct = len(found_signals)/len(expected_signals)*100 if expected_signals else 0
    print(f"   Coverage: {coverage_pct:.1f}%")
    
    if missing_signals:
        print(f"\n⚠️  Missing Signals (not found in test):")
        for sig in sorted(missing_signals):
            # Check if signal is hidden from UI (points: 0 or ui_visible: False)
            signal_config = metadata.signal_tiers.get(sig, {})
            is_hidden = signal_config.get('ui_visible', True) == False or signal_config.get('points', 1) == 0
            
            if is_hidden:
                print(f"      - {sig} - Hidden from UI (points: 0)")
            else:
                print(f"      - {sig} - ❌ ERROR MISSING")
    
    print(f"\n📈 Signal Distribution:")
    for sig, count in sorted(signal_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(all_results)) * 100
        in_registry = "✓" if sig in expected_signals else "✗"
        print(f"   [{in_registry}] {sig}: {count} ({pct:.1f}%)")
    
    # Calculate additional metrics
    test_days = (df_full['timestamp'].max() - df_full['timestamp'].min()).days
    signals_per_day = len(all_results) / max(1, test_days)
    
    print(f"\n📉 Density Metrics:")
    print(f"   Test period: {test_days} days")
    print(f"   Signals per day: {signals_per_day:.2f}")
    print(f"   Candles per signal: {test_candles/len(all_results):.1f}")
    
    # Save detailed report
    output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'registry_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON report
    report = {
        'block_name': block_name,
        'test_info': {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'multicore': use_multicore
        },
        'data_info': {
            'test_days': test_days,
            'total_candles': total_candles,
            'test_candles': test_candles,
            'warmup_candles': min_bars
        },
        'block_metadata': {
            'category': metadata.category,
            'class_name': metadata.class_name,
            'default_weight': metadata.default_weight,
            'valid_signals': metadata.valid_signals
        },
        'results': {
            'total_results': len(all_results),
            'total_errors': len(all_errors),
            'error_rate': len(all_errors)/(len(all_results)+len(all_errors)) if (len(all_results)+len(all_errors)) > 0 else 0,
            'unique_signals_found': len(signal_counts),
            'signal_counts': signal_counts,
            'signals_per_day': signals_per_day
        },
        'coverage': {
            'expected_signals': list(expected_signals),
            'found_signals': list(found_signals),
            'missing_signals': list(missing_signals),
            'coverage_pct': coverage_pct
        }
    }
    
    json_file = output_dir / f'test_{block_name}.json'
    with open(json_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Report saved: {json_file}")
    
    # CSV with all results
    if all_results:
        csv_file = output_dir / f'test_{block_name}_signals.csv'
        results_df = pd.DataFrame(all_results)
        
        # Flatten metadata if present
        if 'metadata' in results_df.columns:
            metadata_rows = []
            for idx, row in results_df.iterrows():
                meta = row.get('metadata', {})
                if isinstance(meta, dict):
                    metadata_rows.append(meta)
                else:
                    metadata_rows.append({})
            
            meta_df = pd.DataFrame(metadata_rows)
            results_df = pd.concat([results_df.drop('metadata', axis=1), meta_df], axis=1)
        
        results_df.to_csv(csv_file, index=False)
        print(f"✅ Signals CSV saved: {csv_file}")
    
    print("="*80)
    
    return report
