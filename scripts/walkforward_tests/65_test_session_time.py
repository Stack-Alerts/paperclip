"""
Walk-Forward Test for Session Time
V2 - Aligned with institutional_production_validation_v2.py methodology
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


def test_block_walkforward_v2(block, block_name: str, df_full: pd.DataFrame):
    """
    Walk-forward test using V2 methodology with FULL HISTORICAL DATA
    
    Key changes:
    - Uses EXPANDING window (all data from start to current bar)
    - Tests EVERY bar (sample_every=1)
    - Accepts ALL valid results (including NEUTRAL, INSUFFICIENT_DATA)
    - Separately tracks "active signals" vs all results
    - Compatible with long-period indicators (EMA 200, 255, 800)
    """
    
    print("="*80)
    print(f"🔬 WALK-FORWARD TEST V2: {block_name}")
    print("="*80)
    print(f"Full Dataset: {len(df_full)} bars from {df_full['timestamp'].min()} to {df_full['timestamp'].max()}")
    
    # V2 Parameters - EXPANDING WINDOW (full historical data)
    min_bars = 100  # Minimum bars before starting tests
    sample_every = 1  # Test EVERY bar for complete accuracy
    
    results = []
    errors = 0
    error_messages = []
    
    print(f"\nTesting with EXPANDING window (full history, sample_every={sample_every})...")
    print(f"Starting from bar {min_bars}, using all previous bars for context...")
    
    # EXPANDING window - use ALL data from start to current bar
    for i in range(min_bars, len(df_full), sample_every):
        try:
            # EXPANDING window: use ALL data from beginning up to current bar
            hist_df = df_full.iloc[:i+1].copy()
            
            result = block.analyze(hist_df)
            
            # V2: Accept ANY valid result (including NEUTRAL, INSUFFICIENT_DATA, etc.)
            if result is not None and isinstance(result, dict):
                results.append(result)
                
        except Exception as e:
            errors += 1
            if errors <= 3:  # Store first 3 error messages
                error_messages.append(str(e))
            if errors > 100:  # Stop if too many errors
                print(f"  ⚠️  Too many errors ({errors}), stopping early")
                break
    
    # Calculate V2 metrics
    if len(results) == 0:
        print(f"\n❌ NO RESULTS PRODUCED")
        print(f"   Errors: {errors}")
        if error_messages:
            print(f"   Sample errors: {error_messages[:2]}")
        return
    
    # Extract signals and confidences
    signals = [r.get('signal', 'UNKNOWN') for r in results]
    confidences = [r.get('confidence', 0) for r in results]
    
    # V2: Separate "active signals" from all results
    # Active signals = signals that are NOT neutral/error states
    active_signals = [s for s in signals if s not in ['NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR', 'NO_PATTERN', 'NO_ORDER_BLOCK', 'NO_BREAK', 'NO_SWEEP', 'NO_FVG', 'NO_DISPLACEMENT', 'NO_INDUCEMENT', 'NO_OTE', 'NO_CHOCH', 'NO_MSS']]
    active_signal_rate = len(active_signals) / len(signals) if len(signals) > 0 else 0
    
    # Confidence stats (only when actively signaling)
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
    
    # Active signal distribution (for detailed breakdown)
    active_signal_types = {}
    for s in active_signals:
        active_signal_types[s] = active_signal_types.get(s, 0) + 1
    
    # **NEW:** Track is_new_event for blocks that support it (BOS, MSS, etc.)
    new_events = [r for r in results if r.get('metadata', {}).get('is_new_event') == True]
    new_event_count = len(new_events)
    has_event_tracking = any(r.get('metadata', {}).get('is_new_event') is not None for r in results)
    
    # Summary
    print(f"\n📊 RESULTS (V2 Methodology):")
    print(f"   Total bars sampled: {len(df_full) // sample_every}")
    print(f"   Valid results: {len(results)}")
    print(f"   Active signals: {len(active_signals)} ({active_signal_rate:.2%} of results)")
    print(f"   Errors: {errors} ({error_rate:.1%} error rate)")
    
    if has_event_tracking:
        new_event_rate = new_event_count / len(results) if len(results) > 0 else 0
        print(f"\n   ⭐ NEW EVENTS: {new_event_count} ({new_event_rate:.2%} of results)")
        print(f"   Continuing state: {len(active_signals) - new_event_count} ({(len(active_signals) - new_event_count) / len(active_signals):.2%} of active)")
    
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
    
    # Calculate signals per day (using active signals)
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
    
    # Save results to proper directory structure
    output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'walkforward_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'walkforward_results_{block_name}.json'
    
    # Save detailed signals/trades CSV
    csv_file = output_dir / f'walkforward_results_{block_name}_signals_trades.csv'
    signals_df = pd.DataFrame(results)
    if len(signals_df) > 0:
        # Flatten metadata if it exists
        if 'metadata' in signals_df.columns:
            # Extract common metadata fields
            metadata_fields = []
            for idx, row in signals_df.iterrows():
                meta = row.get('metadata', {})
                if isinstance(meta, dict):
                    metadata_fields.append(meta)
                else:
                    metadata_fields.append({})
            
            # Add metadata columns
            meta_df = pd.DataFrame(metadata_fields)
            signals_df = pd.concat([signals_df.drop('metadata', axis=1), meta_df], axis=1)
        
        # Flatten confluence_factors if it exists (join list into string)
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
    
    # Add event tracking metrics if supported
    if has_event_tracking:
        new_event_rate = new_event_count / len(results) if len(results) > 0 else 0
        continuing_rate = (len(active_signals) - new_event_count) / len(active_signals) if len(active_signals) > 0 else 0
        new_events_per_day = new_event_count / max(1, days)
        
        report['event_tracking'] = {
            'has_event_tracking': True,
            'new_events': new_event_count,
            'new_event_rate': float(new_event_rate),
            'continuing_state': len(active_signals) - new_event_count,
            'continuing_state_rate': float(continuing_rate),
            'new_events_per_day': float(new_events_per_day)
        }
    else:
        report['event_tracking'] = {
            'has_event_tracking': False
        }
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ JSON results saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    from src.detectors.building_blocks.sessions.session_time import SessionTime
    
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    
    if df is not None and len(df) > 0:
        block = SessionTime()
        test_block_walkforward_v2(block, "session_time", df)
    else:
        print("❌ Failed to load data")
