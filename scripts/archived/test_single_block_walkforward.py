"""
Single Block Walk-Forward Test (MULTICORE VERSION)
Test one specific block across multiple time periods with verbose output
Includes Expert Mode signal validation against price action
Uses 31 CPU cores for parallel processing
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import importlib.util
import json
from multiprocessing import Pool, cpu_count
from functools import partial

# Import SignalValidator from validate_walkforward_signals
from validate_walkforward_signals import SignalValidator


def test_single_window(args):
    """
    Worker function to test a single window (for multiprocessing)
    
    Args:
        args: Tuple of (block_path, df_period, window_end_idx)
    
    Returns:
        Dict with signal info or None
    """
    block_path, df_period_dict, window_end_idx = args
    
    try:
        # Reconstruct DataFrame from dict
        df_period = pd.DataFrame(df_period_dict)
        
        # Import block
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        block_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and hasattr(obj, 'analyze'):
                block_class = obj
                break
        
        if not block_class:
            return None
        
        # Initialize block
        block = block_class()
        
        # Test window
        hist_df = df_period.iloc[:window_end_idx+1].copy()
        result = block.analyze(hist_df)
        
        if result and isinstance(result, dict):
            signal = result.get('signal', 'UNKNOWN')
            confidence = result.get('confidence', 0)
            
            # Return signal if not neutral
            if signal not in ['NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR', 'NO_BREAK']:
                return {
                    'timestamp': hist_df['timestamp'].iloc[-1],
                    'signal': signal,
                    'confidence': confidence,
                    'price': hist_df['close'].iloc[-1],
                    'bar_index': window_end_idx
                }
        
        return None
        
    except Exception as e:
        return {'error': str(e), 'bar_index': window_end_idx}


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data"""
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    df = pd.read_csv(data_path)
    
    # Standardize column names
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'time' in col_lower and 'timestamp' not in df.columns:
            rename_map[col] = 'timestamp'
        elif col_lower == 'vol':
            rename_map[col] = 'volume'
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    if df['timestamp'].dtype == 'object':
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Filter to last N days
    cutoff_date = df['timestamp'].max() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date].copy()
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def test_block_walkforward(block_path: str, block_name: str, df_full: pd.DataFrame):
    """
    Walk-forward test a single block
    Test across 3 expanding windows: 0-60, 0-120, 0-180 days ago
    """
    print("="*80)
    print(f"🔬 WALK-FORWARD TEST: {block_name}")
    print("="*80)
    print(f"\nFull Dataset: {len(df_full)} bars from {df_full['timestamp'].min()} to {df_full['timestamp'].max()}")
    
    # Import block
    spec = importlib.util.spec_from_file_location("block", block_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    block_class = None
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and hasattr(obj, 'analyze'):
            block_class = obj
            break
    
    if not block_class:
        print("❌ Could not import block class")
        return
    
    # Define walk-forward periods (expanding windows)
    periods = [
        (0, 60, "Recent 60 days (0-60 days ago)"),
        (0, 120, "Recent 120 days (0-120 days ago)"),
        (0, 180, "Full 180 days (0-180 days ago)")
    ]
    
    all_results = []
    all_signals_for_validation = []  # Collect signals from final period for validation
    
    for start_offset, end_offset, period_name in periods:
        print(f"\n{'='*80}")
        print(f"📊 Period: {period_name}")
        print(f"{'='*80}")
        
        # Get period data
        start_date = df_full['timestamp'].max() - timedelta(days=end_offset)
        end_date = df_full['timestamp'].max() - timedelta(days=start_offset)
        
        df_period = df_full[
            (df_full['timestamp'] >= start_date) & 
            (df_full['timestamp'] <= end_date)
        ].copy()
        
        print(f"Period range: {df_period['timestamp'].min()} to {df_period['timestamp'].max()}")
        print(f"Bars in period: {len(df_period)}")
        
        # Initialize block
        try:
            block = block_class()
            print(f"✅ Block initialized: {block_class.__name__}")
        except Exception as e:
            print(f"❌ Block init error: {e}")
            continue
        
        # Test block with expanding window - MULTICORE VERSION
        signals = []
        errors = 0
        window_size = 800
        
        print(f"\n🔍 Testing with expanding window (min {window_size} bars)...")
        print(f"Testing EVERY bar using 31 CPU cores (no sampling)...")
        
        # Prepare arguments for parallel processing - TEST EVERY BAR
        window_indices = list(range(window_size, len(df_period), 1))  # Changed from 20 to 1
        df_period_dict = df_period.to_dict('list')  # Convert to dict for pickling
        
        args_list = [(block_path, df_period_dict, idx) for idx in window_indices]
        
        # Run parallel processing with 31 cores
        n_cores = min(31, cpu_count() - 1)
        print(f"Using {n_cores} CPU cores for parallel processing\n")
        
        with Pool(n_cores) as pool:
            results = pool.map(test_single_window, args_list)
        
        # Process results
        for result in results:
            if result is not None:
                if 'error' in result:
                    errors += 1
                    if errors <= 3:
                        print(f"  ⚠️  Error at bar {result['bar_index']}: {result['error']}")
                else:
                    signals.append(result)
                    print(f"  🎯 Signal {len(signals)}: {result['signal']} @ {result['timestamp']} | "
                          f"Price: ${result['price']:.2f} | Confidence: {result['confidence']}%")
        
        # Period summary
        print(f"\n📈 Period Summary:")
        print(f"   Total signals: {len(signals)}")
        print(f"   Error rate: {errors}/{(len(df_period)-window_size)//20} ({errors/max(1,(len(df_period)-window_size)//20)*100:.1f}%)")
        
        if signals:
            confidences = [s['confidence'] for s in signals]
            print(f"   Avg confidence: {np.mean(confidences):.1f}%")
            print(f"   Confidence range: {min(confidences):.1f}% - {max(confidences):.1f}%")
            
            # Show signal distribution
            signal_types = {}
            for s in signals:
                signal_types[s['signal']] = signal_types.get(s['signal'], 0) + 1
            print(f"   Signal types:")
            for sig_type, count in sorted(signal_types.items()):
                print(f"      {sig_type}: {count}")
        
        all_results.append({
            'period': period_name,
            'signals': len(signals),
            'errors': errors,
            'avg_confidence': np.mean([s['confidence'] for s in signals]) if signals else 0
        })
        
        # Save signals from final period for validation
        if end_offset == 180:  # Full 180-day period
            all_signals_for_validation = signals
    
    # Final comparison
    print(f"\n{'='*80}")
    print(f"🎯 WALK-FORWARD COMPARISON")
    print(f"{'='*80}")
    print(f"\n{'Period':<30} {'Signals':<10} {'Avg Conf':<12} {'Errors'}")
    print("-"*80)
    for r in all_results:
        print(f"{r['period']:<30} {r['signals']:<10} {r['avg_confidence']:<12.1f} {r['errors']}")
    
    # Calculate variance
    signal_counts = [r['signals'] for r in all_results]
    if len(signal_counts) > 1 and sum(signal_counts) > 0:
        variance = np.std(signal_counts) / np.mean(signal_counts)
        print(f"\n📊 Signal Count Variance: {variance:.1%}")
        if variance < 0.15:
            print("   ✅ PASS - Variance <15% (Consistent)")
        else:
            print("   ❌ FAIL - Variance ≥15% (Inconsistent)")
        
        # Calculate signal density (signals per day)
        print(f"\n📈 Signal Density (signals/day):")
        period_days = [60, 120, 180]
        densities = []
        for i, r in enumerate(all_results):
            density = r['signals'] / period_days[i]
            densities.append(density)
            print(f"   {period_days[i]:>3} days: {r['signals']:>2} ÷ {period_days[i]:>3} = {density:.2f} signals/day")
        
        # Calculate density variance
        if len(densities) > 1:
            density_variance = np.std(densities) / np.mean(densities) if np.mean(densities) > 0 else 0
            print(f"\n📊 Signal Density Variance: {density_variance:.1%}")
            if density_variance < 0.15:
                print("   ✅ EXCELLENT - Density variance <15% (Highly consistent)")
            else:
                print("   ⚠️  Density variance ≥15% (Note: Raw count variance may be misleading)")
    
    print("="*80)
    
    # EXPERT MODE: Validate signals against historic price action
    if all_signals_for_validation and len(all_signals_for_validation) > 0:
        print(f"\n🎯 Running Expert Mode validation on {len(all_signals_for_validation)} signals...")
        
        # Initialize validator
        validator = SignalValidator(lookback_bars=20, lookforward_bars=50)
        
        # Run validation
        validation_report = validator.validate_all_signals(df_full, all_signals_for_validation)
        
        # Save validation report
        report_path = Path(__file__).parent.parent / f'validation_report_{block_name}.json'
        with open(report_path, 'w') as f:
            json.dump(validation_report, f, indent=2)
        print(f"\n✅ Validation report saved to: {report_path}")


if __name__ == "__main__":
    # Test ema_50_vector
    block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / 'moving_averages' / 'ema_50_vector.py'
    
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    
    if df is not None and len(df) > 0:
        test_block_walkforward(str(block_path), "ema_50_vector", df)
    else:
        print("❌ Failed to load data")
