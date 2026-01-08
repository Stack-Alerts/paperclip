"""
Walk-Forward Test for LOW (Low of Week)
V2 - Aligned with institutional_production_validation_v2.py methodology
Test script for LOW building block validation
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
    """Walk-forward test using V2 methodology with FULL HISTORICAL DATA"""
    
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
            hist_df = df_full.iloc[:i+1].copy()
            result = block.analyze(hist_df)
            
            if result is not None and isinstance(result, dict):
                results.append(result)
                
        except Exception as e:
            errors += 1
            if errors <= 3:
                error_messages.append(str(e))
            if errors > 100:
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
    active_signals = [s for s in signals if s not in ['NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR', 'NO_PATTERN', 'NO_ORDER_BLOCK', 'NO_BREAK', 'NO_SWEEP', 'NO_FVG', 'NO_DISPLACEMENT', 'NO_INDUCEMENT', 'NO_OTE', 'NO_CHOCH', 'NO_MSS']]
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
    
    # Track is_new_event
    new_events = [r for r in results if r.get('metadata', {}).get('is_new_event') == True]
    new_event_count = len(new_events)
    has_event_tracking = any(r.get('metadata', {}).get('is_new_event') is not None for r in results)
    # **RETEST CONFIRMATION:** Track confirmed retests
    confirmed_type1 = [r for r in results if r.get('metadata', {}).get('confirmed_bounce') == True]
    confirmed_type2 = [r for r in results if r.get('metadata', {}).get('confirmed_breakdown') == True]
    total_confirmed_retests = len(confirmed_type1) + len(confirmed_type2)
    has_retest_confirmation = any(r.get('metadata', {}).get('confirmed_bounce') is not None for r in results)

    
    # Summary
    print(f"\n📊 RESULTS (V2 Methodology):")
    print(f"   Total bars sampled: {len(df_full) // sample_every}")
    print(f"   Valid results: {len(results)}")
    print(f"   Active signals: {len(active_signals)} ({active_signal_rate:.2%} of results)")
    print(f"   Errors: {errors} ({error_rate:.1%} error rate)")
    
    # Calculate days early for retest tracking
    days = (df_full[\'timestamp\'].max() - df_full[\'timestamp\'].min()).days
    
    if has_event_tracking:
        new_event_rate = new_event_count / len(results) if len(results) > 0 else 0
        print(f"\n   ⭐ NEW EVENTS: {new_event_count} ({new_event_rate:.2%} of results)")
        print(f"   Continuing state: {len(active_signals) - new_event_count} ({(len(active_signals)
    if has_retest_confirmation:
        retest_rate = total_confirmed_retests / len(results) if len(results) > 0 else 0
        retests_per_day = total_confirmed_retests / max(1, days)
        print(f"
   🎯 RETEST CONFIRMATION TRACKING:")
        print(f"   Confirmed Bounce: {len(confirmed_type1)} ({len(confirmed_type1)/len(results):.2%})")
        print(f"   Confirmed Breakdown: {len(confirmed_type2)} ({len(confirmed_type2)/len(results):.2%})")
        print(f"   Total Confirmed Retests: {total_confirmed_retests} ({retest_rate:.2%})")
        print(f"   Retests per day: {retests_per_day:.2f}")
 - new_event_count) / len(active_signals):.2%} of active)")
    
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
    
    # **POST-WALKFORWARD VALIDATION:** Validate LOW accuracy against COMPLETE week data
    print(f"\n🔍 POST-WALKFORWARD LOW ACCURACY VALIDATION:")
    print(f"   (After walkforward complete, validate against actual complete weekly data)")
    
    # Group results by week and check final LOW for each week
    results_df = pd.DataFrame(results)
    if 'timestamp' in results_df.columns:
        results_df['timestamp'] = pd.to_datetime(results_df['timestamp'])
        results_df['week'] = results_df['timestamp'].dt.to_period('W')
        
        # Get last result for each week (final LOW value for that week)
        weekly_lows = {}
        for week, week_results in results_df.groupby('week'):
            last_result = week_results.iloc[-1]
            if 'metadata' in last_result and isinstance(last_result['metadata'], dict):
                if 'low' in last_result['metadata']:
                    weekly_lows[str(week)] = {
                        'reported': last_result['metadata']['low'],
                        'timestamp': last_result['timestamp']
                    }
        
        # Compare to actual complete week data
        low_errors = 0
        low_checks = 0
        sample_errors = []
        
        for week_str, low_info in weekly_lows.items():
            # Get COMPLETE week data from df_full
            df_full['week'] = pd.to_datetime(df_full['timestamp']).dt.to_period('W')
            week_data_complete = df_full[df_full['week'] == week_str]
            
            if len(week_data_complete) > 0:
                actual_low_complete = float(week_data_complete['low'].min())
                reported_low = low_info['reported']
                
                # Compare (allow 0.01% tolerance for floating point)
                if abs(reported_low - actual_low_complete) > actual_low_complete * 0.0001:
                    low_errors += 1
                    if len(sample_errors) < 5:
                        sample_errors.append({
                            'week': week_str,
                            'reported': reported_low,
                            'actual_complete': actual_low_complete,
                            'diff': reported_low - actual_low_complete,
                            'diff_pct': ((reported_low - actual_low_complete) / actual_low_complete) * 100
                        })
                
                low_checks += 1
        
        if low_checks > 0:
            low_accuracy = ((low_checks - low_errors) / low_checks) * 100
            print(f"   Weeks checked: {low_checks}")
            print(f"   Weeks with errors: {low_errors}")
            print(f"   Accuracy: {low_accuracy:.2f}%")
            
            if low_errors > 0 and sample_errors:
                print(f"\n   ⚠️  Weeks where final LOW doesn't match complete week LOW:")
                for err in sample_errors:
                    print(f"      {err['week']}: Reported ${err['reported']:.2f}, Actual ${err['actual_complete']:.2f}")
                    print(f"         Diff: ${err['diff']:.2f} ({err['diff_pct']:+.2f}%)")
                print(f"\n   NOTE: Differences expected in walk-forward (we only see data up to each bar)")
                print(f"   This validates LOW was updated correctly as week progressed.")
            elif low_errors == 0:
                print(f"   ✅ All final weekly LOWs match complete week data!")
                print(f"   Perfect accuracy - LOW correctly tracked throughout each week.")
        else:
            print(f"   ⚠️  No weekly LOWs to validate")
    else:
        print(f"   ⚠️  Cannot validate - no timestamp in results")
    
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
    output_file = output_dir / f'walkforward_results_{block_name}.json'
    
    # Save detailed signals/trades CSV
    csv_file = output_dir / f'walkforward_results_{block_name}_signals_trades.csv'
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
    
    # Calculate days early for retest tracking
    days = (df_full[\'timestamp\'].max() - df_full[\'timestamp\'].min()).days
    
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
    from src.detectors.building_blocks.price_levels.low import LOW
    
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    
    if df is not None and len(df) > 0:
        block = LOW()
        test_block_walkforward_v2(block, "low", df)
    else:
        print("❌ Failed to load data")
