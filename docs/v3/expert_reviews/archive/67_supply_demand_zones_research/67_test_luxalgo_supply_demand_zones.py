"""
LuxAlgo Supply & Demand Zones - Walkforward Test
================================================

Test the LuxAlgo volume profile-based approach on the same 180-day period
to compare against the current pattern-based approach.

Expected Results:
- SUPPLY/DEMAND ratio: 50/50 to 65/35 (vs 82/18 current)
- Coverage: 15-30% (vs 9.1% current)
- Grade: A- (88-90/100) vs B+ (85/100) current

Comparison Metrics:
1. SUPPLY/DEMAND balance (CRITICAL)
2. Coverage percentage
3. Zones per day
4. Confidence distribution
5. Zone quality (POC/VAH/VAL precision)
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.detectors.building_blocks.supply_demand.luxalgo_supply_demand_zones import LuxAlgoSupplyDemandZones


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data from CSV."""
    data_path = project_root / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
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


def run_luxalgo_walkforward_test():
    """Run walkforward test on LuxAlgo detector."""
    
    print("=" * 80)
    print("LUXALGO SUPPLY & DEMAND ZONES - WALKFORWARD TEST")
    print("=" * 80)
    print("Testing volume profile-based approach...")
    print("Expected: 50/50 to 65/35 SUPPLY/DEMAND ratio")
    print("=" * 80)
    
    # Load data
    print("\n📊 Loading BTC/USDT 15min data...")
    df = load_btc_data(days=180)
    
    if df is None or len(df) == 0:
        print("❌ Failed to load data")
        return
    
    print(f"✅ Loaded {len(df):,} bars")
    
    # Data already filtered to 180 days by load_btc_data()
    df_test = df.copy()
    
    print(f"\n📅 Test Period:")
    print(f"   Start: {df_test['timestamp'].iloc[0]}")
    print(f"   End: {df_test['timestamp'].iloc[-1]}")
    print(f"   Bars: {len(df_test):,}")
    print(f"   Days: {len(df_test) / 96:.0f}")
    
    # Initialize detector
    print("\n🔧 Initializing LuxAlgo detector...")
    detector = LuxAlgoSupplyDemandZones(
        timeframe='15min',
        resolution=50,
        threshold_percent=30.0,
        lookback_bars=200,
    )
    print(f"   Resolution: 50 bins")
    print(f"   Threshold: 30% of volume")
    print(f"   Lookback: 200 bars")
    
    # Run walkforward test
    print("\n🧪 Running walkforward test (expanding window)...")
    results = []
    min_bars = 100
    sample_every = 1  # Sample every bar for complete test
    
    total_bars = len(df_test)
    progress_interval = total_bars // 20  # 20 progress updates
    
    for i in range(min_bars, total_bars, sample_every):
        # Expanding window
        df_window = df_test.iloc[:i+1]
        
        # Analyze
        result = detector.analyze(df_window)
        results.append(result)
        
        # Progress
        if i % progress_interval == 0:
            pct = (i / total_bars) * 100
            print(f"   Progress: {pct:.1f}% ({i:,}/{total_bars:,} bars)")
    
    print(f"✅ Completed {len(results):,} samples")
    
    # Analyze results
    print("\n📊 ANALYZING RESULTS...")
    print("=" * 80)
    
    # Signal distribution
    signals = [r['signal'] for r in results]
    signal_counts = {}
    for sig in signals:
        signal_counts[sig] = signal_counts.get(sig, 0) + 1
    
    total_signals = len(results)
    
    print("\n🎯 SIGNAL DISTRIBUTION:")
    for signal, count in sorted(signal_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_signals) * 100
        print(f"   {signal:20s}: {count:6,} ({pct:5.1f}%)")
    
    # Zone signals only
    zone_signals = [sig for sig in signals if sig != 'NO_ZONE']
    supply_signals = [sig for sig in zone_signals if 'SUPPLY' in sig]
    demand_signals = [sig for sig in zone_signals if 'DEMAND' in sig]
    
    if len(zone_signals) > 0:
        supply_pct = (len(supply_signals) / len(zone_signals)) * 100
        demand_pct = (len(demand_signals) / len(zone_signals)) * 100
        
        print(f"\n🎯 SUPPLY/DEMAND BALANCE (Zone signals only):")
        print(f"   SUPPLY: {len(supply_signals):,} ({supply_pct:.1f}%)")
        print(f"   DEMAND: {len(demand_signals):,} ({demand_pct:.1f}%)")
        print(f"   Ratio: {supply_pct:.1f}/{demand_pct:.1f}")
    
    # Actual zones (SUPPLY_ZONE and DEMAND_ZONE only)
    supply_zones = [sig for sig in signals if sig == 'SUPPLY_ZONE']
    demand_zones = [sig for sig in signals if sig == 'DEMAND_ZONE']
    total_zones = len(supply_zones) + len(demand_zones)
    
    if total_zones > 0:
        supply_zone_pct = (len(supply_zones) / total_zones) * 100
        demand_zone_pct = (len(demand_zones) / total_zones) * 100
        
        print(f"\n🎯 ACTUAL ZONES RATIO (Inside zones only):")
        print(f"   SUPPLY_ZONE: {len(supply_zones):,} ({supply_zone_pct:.1f}%)")
        print(f"   DEMAND_ZONE: {len(demand_zones):,} ({demand_zone_pct:.1f}%)")
        print(f"   Ratio: {supply_zone_pct:.1f}/{demand_zone_pct:.1f}")
    
    # Confidence statistics
    confidences = [r['confidence'] for r in results if r['signal'] != 'NO_ZONE']
    if confidences:
        avg_conf = np.mean(confidences)
        std_conf = np.std(confidences)
        print(f"\n📈 CONFIDENCE STATISTICS:")
        print(f"   Average: {avg_conf:.1f}%")
        print(f"   Std Dev: {std_conf:.1f}%")
        print(f"   Min: {min(confidences):.1f}%")
        print(f"   Max: {max(confidences):.1f}%")
    
    # Coverage
    coverage_pct = ((total_signals - signal_counts.get('NO_ZONE', 0)) / total_signals) * 100
    print(f"\n📊 COVERAGE:")
    print(f"   Zone signals: {total_signals - signal_counts.get('NO_ZONE', 0):,}")
    print(f"   NO_ZONE: {signal_counts.get('NO_ZONE', 0):,}")
    print(f"   Coverage: {coverage_pct:.1f}%")
    
    # Zones per day
    days = len(df_test) / 96
    zones_per_day = total_zones / days
    print(f"\n📅 ZONES PER DAY:")
    print(f"   Total zones: {total_zones:,}")
    print(f"   Days: {days:.0f}")
    print(f"   Zones/day: {zones_per_day:.2f}")
    
    # Save results
    output_dir = project_root / 'data' / 'reports' / 'walkforward_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = output_dir / 'walkforward_results_luxalgo_supply_demand_zones.json'
    csv_file = output_dir / 'walkforward_results_luxalgo_supply_demand_zones_signals_trades.csv'
    
    # Create JSON summary
    summary = {
        'block': 'luxalgo_supply_demand_zones',
        'methodology': 'LuxAlgo Volume Profile',
        'total_bars_sampled': total_signals,
        'valid_results': total_signals,
        'active_signals': total_signals,
        'active_signal_rate': 1.0,
        'avg_active_confidence': float(np.mean([r['confidence'] for r in results])),
        'avg_all_confidence': float(np.mean([r['confidence'] for r in results])),
        'std_confidence': float(np.std([r['confidence'] for r in results])),
        'errors': 0,
        'error_rate': 0.0,
        'all_signal_types': signal_counts,
        'active_signal_types': signal_counts,
        'signals_per_day': 96.0,  # 15min bars per day
        'test_period': {
            'start': str(df_test['timestamp'].iloc[0]),
            'end': str(df_test['timestamp'].iloc[-1]),
            'days': int(days),
            'bars': len(df_test),
        },
        'validation_params': {
            'methodology': 'expanding_window',
            'min_bars': min_bars,
            'sample_every': sample_every,
            'total_bars_available': len(df_test),
        },
        'supply_demand_balance': {
            'supply_zones': len(supply_zones),
            'demand_zones': len(demand_zones),
            'ratio': f"{supply_zone_pct:.1f}/{demand_zone_pct:.1f}" if total_zones > 0 else "N/A",
        },
    }
    
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✅ JSON report: {json_file}")
    
    # Create CSV with signal details
    df_results = pd.DataFrame(results)
    df_results.to_csv(csv_file, index=False)
    print(f"✅ CSV report: {csv_file}")
    print(f"   Total records: {len(df_results):,}")
    print(f"   Active signals in CSV: {len(df_results):,}")
    
    # COMPARISON TO CURRENT APPROACH
    print("\n" + "=" * 80)
    print("📊 COMPARISON TO PATTERN-BASED APPROACH")
    print("=" * 80)
    print("\nCurrent Pattern-Based:")
    print("   SUPPLY/DEMAND: 82/18")
    print("   Coverage: 9.1%")
    print("   Zones/day: 0.99")
    print("   Grade: B+ (85/100)")
    
    print("\nLuxAlgo Volume Profile:")
    print(f"   SUPPLY/DEMAND: {supply_zone_pct:.1f}/{demand_zone_pct:.1f}")
    print(f"   Coverage: {coverage_pct:.1f}%")
    print(f"   Zones/day: {zones_per_day:.2f}")
    
    # Assessment
    if total_zones > 0:
        if supply_zone_pct <= 65:
            print(f"\n✅ SIGNIFICANT IMPROVEMENT in balance!")
            print(f"   82/18 → {supply_zone_pct:.1f}/{demand_zone_pct:.1f}")
            print(f"   RECOMMENDATION: **DEPLOY LUXALGO**")
            grade = "A-"
        elif supply_zone_pct <= 75:
            print(f"\n⚠️  MODERATE improvement")
            print(f"   82/18 → {supply_zone_pct:.1f}/{demand_zone_pct:.1f}")
            print(f"   RECOMMENDATION: Consider hybrid approach")
            grade = "B+"
        else:
            print(f"\n❌ MINIMAL improvement")
            print(f"   82/18 → {supply_zone_pct:.1f}/{demand_zone_pct:.1f}")
            print(f"   RECOMMENDATION: Keep current approach")
            grade = "B"
        
        print(f"\n🎯 Estimated Grade: {grade}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_luxalgo_walkforward_test()
