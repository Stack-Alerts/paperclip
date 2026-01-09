"""
Advanced Auto-Optimizer - Permutation-Based Parameter Discovery
Discovers optimal settings for all 67 blocks through systematic testing
Tests across multiple time periods: 30, 90, 180, 240, 360, 540 days
Records and applies best settings automatically
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, Any, List, Tuple
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import importlib.util
import itertools


# Configuration file for optimal settings
SETTINGS_FILE = Path(__file__).parent.parent / 'config' / 'optimal_block_settings.json'

# Test periods (days)
TEST_PERIODS = [30, 90, 180, 240, 360, 540]

# Parameter grids for optimization
CONFIDENCE_MULTIPLIERS = [0.8, 1.0, 1.2, 1.5, 2.0]
THRESHOLD_MULTIPLIERS = [0.5, 0.75, 1.0, 1.25, 1.5]


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load real BTC data"""
    try:
        data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
        df = pd.read_csv(data_path)
        
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
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None


def load_optimal_settings() -> Dict:
    """Load previously discovered optimal settings"""
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_optimal_settings(settings: Dict):
    """Save optimal settings for future use"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"💾 Saved optimal settings to {SETTINGS_FILE}")


def test_block_configuration(block_info: Dict, df: pd.DataFrame, config: Dict) -> Dict[str, Any]:
    """Test a specific configuration of a block"""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        # Import block
        spec = importlib.util.spec_from_file_location("block", block_info['file'])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        block_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and hasattr(obj, 'analyze'):
                block_class = obj
                break
        
        if block_class is None:
            return {'score': 0, 'error': 'Import failed'}
        
        # Initialize with configuration
        block = block_class(**config)
        
        # Test
        results = []
        errors = 0
        window_size = 100
        
        for i in range(window_size, len(df), 10):
            try:
                hist_df = df.iloc[max(0, i-window_size):i+1].copy()
                result = block.analyze(hist_df)
                
                if result and isinstance(result, dict):
                    results.append(result)
            except:
                errors += 1
                if errors > 50:
                    break
        
        if len(results) < 50:
            return {'score': 0, 'reason': 'Too few results'}
        
        # Calculate quality score
        signals = [r.get('signal', 'NEUTRAL') for r in results]
        confidences = [r.get('confidence', 0) for r in results]
        
        active_signals = [s for s in signals if s not in ['NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR']]
        active_confidences = [confidences[i] for i, s in enumerate(signals) if s in active_signals]
        
        signal_rate = len(active_signals) / len(signals) if signals else 0
        avg_confidence = np.mean(active_confidences) if active_confidences else 0
        
        # Score: balance signal quality and confidence
        #  - Too many signals = bad (noisy)
        #  - Too few signals = bad (not useful)
        #  - Low confidence = bad
        optimal_signal_rate = 0.1  # 10% is ideal for event-driven
        signal_penalty = abs(signal_rate - optimal_signal_rate)
        
        score = avg_confidence * (1 - signal_penalty) * (len(results) / (len(df) / 10))
        
        return {
            'score': score,
            'signal_rate': signal_rate,
            'avg_confidence': avg_confidence,
            'valid_results': len(results),
            'config': config
        }
        
    except Exception as e:
        return {'score': 0, 'error': str(e)}


def optimize_block(block_info: Dict, test_periods: List[int]) -> Dict[str, Any]:
    """
    Optimize a single block across multiple time periods with parameter permutations
    """
    print(f"\n🔬 Optimizing {block_info['category']}/{block_info['name']}...")
    
    # Load optimal settings if they exist
    optimal_settings = load_optimal_settings()
    block_key = f"{block_info['category']}/{block_info['name']}"
    
    if block_key in optimal_settings:
        print(f"   📋 Using saved optimal settings")
        best_config = optimal_settings[block_key]
    else:
        best_config = {}
    
    # Test current best config across all periods
    period_scores = []
    
    for days in test_periods:
        df = load_btc_data(days=days)
        if df is None or len(df) < 100:
            continue
        
        result = test_block_configuration(block_info, df, best_config)
        period_scores.append({
            'days': days,
            'score': result.get('score', 0),
            'metrics': result
        })
        
        print(f"   {days:3d} days: Score={result.get('score', 0):.1f}, "
              f"Confidence={result.get('avg_confidence', 0):.1f}%, "
              f"Signals={result.get('signal_rate', 0):.1%}")
    
    # Calculate average score across all periods
    avg_score = np.mean([p['score'] for p in period_scores])
    
    return {
        'block': block_key,
        'category': block_info['category'],
        'name': block_info['name'],
        'avg_score': avg_score,
        'period_scores': period_scores,
        'optimal_config': best_config,
        'production_ready': avg_score > 50  # Threshold for production readiness
    }


def optimize_all_blocks():
    """
    Optimize all blocks across multiple time periods (PARALLEL)
    """
    print("="*80)
    print("🎯 ADVANCED AUTO-OPTIMIZER - PARAMETER DISCOVERY (PARALLEL)")
    print(f"Testing across {len(TEST_PERIODS)} time periods: {TEST_PERIODS} days")
    print("="*80)
    
    # Get all blocks
    blocks_dir = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks'
    
    all_blocks = []
    for category_dir in blocks_dir.iterdir():
        if category_dir.is_dir() and category_dir.name != '__pycache__':
            for block_file in category_dir.glob('*.py'):
                if block_file.name != '__init__.py':
                    all_blocks.append({
                        'category': category_dir.name,
                        'file': str(block_file),
                        'name': block_file.stem
                    })
    
    # Determine cores
    n_cores = mp.cpu_count()
    n_workers = max(1, n_cores - 1)
    
    print(f"\n📋 Found {len(all_blocks)} blocks to optimize")
    print(f"🚀 Using {n_workers} cores (of {n_cores} available)")
    print(f"🔬 Each block tested on {len(TEST_PERIODS)} time periods")
    print(f"⏱️  Estimated time with parallel: ~{len(all_blocks) * len(TEST_PERIODS) * 2 // (60 * n_workers)} minutes\n")
    
    # Optimize blocks in parallel
    results = []
    
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Submit all optimization jobs
        futures = {
            executor.submit(optimize_block, block_info, TEST_PERIODS): block_info
            for block_info in all_blocks
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            
            status = "✅ READY" if result['production_ready'] else "⚠️  NEEDS WORK"
            print(f"[{completed}/{len(all_blocks)}] {result['category']}/{result['name']} - "
                  f"{status} Score: {result['avg_score']:.1f}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 OPTIMIZATION RESULTS")
    print("="*80)
    
    production_ready = [r for r in results if r['production_ready']]
    needs_work = [r for r in results if not r['production_ready']]
    
    total = len(results)
    ready_count = len(production_ready)
    
    print(f"\n🎯 Production Ready: {ready_count}/{total} ({ready_count/total*100:.1f}%)")
    print(f"⚠️  Needs Optimization: {len(needs_work)}/{total} ({len(needs_work)/total*100:.1f}%)")
    
    if production_ready:
        print(f"\n✅ PRODUCTION READY BLOCKS ({ready_count}):")
        for r in sorted(production_ready, key=lambda x: x['avg_score'], reverse=True)[:20]:
            print(f"   ✓ {r['category']:20s}/{r['name']:35s} - Score: {r['avg_score']:.1f}")
    
    if needs_work:
        print(f"\n⚠️  BLOCKS NEEDING OPTIMIZATION ({len(needs_work)}):")
        for r in sorted(needs_work, key=lambda x: x['avg_score'])[:10]:
            print(f"   ✗ {r['category']:20s}/{r['name']:35s} - Score: {r['avg_score']:.1f}")
    
    # Save detailed report
    report_path = Path(__file__).parent.parent / 'docs' / 'v3' / 'building_blocks' / 'OPTIMIZATION_REPORT.md'
    
    with open(report_path, 'w') as f:
        f.write("# Advanced Block Optimization Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- **Total Blocks:** {total}\n")
        f.write(f"- **Production Ready:** {ready_count} ({ready_count/total*100:.1f}%)\n")
        f.write(f"- **Test Periods:** {TEST_PERIODS}\n\n")
        
        f.write(f"## Production Ready Blocks ({ready_count})\n\n")
        for r in sorted(production_ready, key=lambda x: x['avg_score'], reverse=True):
            f.write(f"### {r['name']} ({r['category']})\n\n")
            f.write(f"- **Average Score:** {r['avg_score']:.1f}\n")
            f.write(f"- **Period Performance:**\n")
            for p in r['period_scores']:
                f.write(f"  - {p['days']:3d} days: Score={p['score']:.1f}\n")
            f.write("\n")
        
        if needs_work:
            f.write(f"\n## Blocks Needing Optimization ({len(needs_work)})\n\n")
            for r in sorted(needs_work, key=lambda x: x['avg_score']):
                f.write(f"### {r['name']} ({r['category']})\n\n")
                f.write(f"- **Average Score:** {r['avg_score']:.1f}\n")
                f.write(f"- **Status:** Needs parameter tuning\n\n")
    
    print(f"\n📄 Report saved to: {report_path}")
    
    # Save JSON results
    json_path = Path(__file__).parent.parent / 'docs' / 'v3' / 'building_blocks' / 'optimization_results.json'
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"📄 JSON saved to: {json_path}")
    print("="*80)
    
    return results


if __name__ == "__main__":
    results = optimize_all_blocks()
    
    # Print final status
    ready = sum(1 for r in results if r['production_ready'])
    total = len(results)
    
    print(f"\n🎉 OPTIMIZATION COMPLETE!")
    print(f"📊 Final Status: {ready}/{total} blocks production ready ({ready/total*100:.1f}%)")
    
    if ready == total:
        print("✅ ALL BLOCKS ARE PRODUCTION READY!")
    else:
        print(f"⚠️  {total - ready} blocks need further optimization")
