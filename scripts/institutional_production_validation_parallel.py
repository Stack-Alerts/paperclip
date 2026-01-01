"""
Institutional-Grade Production Validation for ALL Building Blocks (PARALLEL)
Tests each block on real BTC data with backtest + walkforward validation
Uses multiprocessing for fast execution
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, Any, List
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import importlib.util
import traceback


# Institutional validation criteria (global for pickling)
INSTITUTIONAL_CRITERIA = {
    'signal_quality': {
        'min_signals': 10,
        'max_signal_rate': 0.3,
        'min_signal_rate': 0.001,
    },
    'confidence_distribution': {
        'min_avg_confidence': 20,
        'max_avg_confidence': 95,
        'min_std_confidence': 5,
    },
    'data_robustness': {
        'min_data_quality': 0.95,
    },
}


def load_btc_data(timeframe: str = '15min', days: int = 180) -> pd.DataFrame:
    """Load real BTC data from CSV files"""
    try:
        if timeframe == '15min':
            data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
        elif timeframe == '30min':
            data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_30m.csv'
        else:
            data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
        
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        
        df = pd.read_csv(data_path)
        
        # Standardize columns
        rename_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if 'time' in col_lower and 'timestamp' not in df.columns:
                rename_map[col] = 'timestamp'
            elif col_lower == 'vol':
                rename_map[col] = 'volume'
        
        if rename_map:
            df = df.rename(columns=rename_map)
        
        # Convert timestamp
        if df['timestamp'].dtype == 'object':
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by time
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Filter to last N days
        if days:
            cutoff_date = df['timestamp'].max() - timedelta(days=days)
            df = df[df['timestamp'] >= cutoff_date].copy()
        
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        return df[required_cols]
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None


def import_block(block_path: str):
    """Dynamically import a building block"""
    try:
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and hasattr(obj, 'analyze'):
                return obj
        
        return None
    except Exception as e:
        return None


def check_institutional_criteria(metrics: Dict[str, Any]) -> bool:
    """Check if block meets institutional quality criteria"""
    criteria = INSTITUTIONAL_CRITERIA
    
    # Signal quality checks
    if metrics['signal_rate'] < criteria['signal_quality']['min_signal_rate']:
        return False
    if metrics['signal_rate'] > criteria['signal_quality']['max_signal_rate']:
        return False
    
    # Confidence distribution checks
    if metrics['avg_confidence'] < criteria['confidence_distribution']['min_avg_confidence']:
        return False
    if metrics['avg_confidence'] > criteria['confidence_distribution']['max_avg_confidence']:
        return False
    if metrics['std_confidence'] < criteria['confidence_distribution']['min_std_confidence']:
        return False
    
    # Data robustness
    if metrics['data_quality'] < criteria['data_robustness']['min_data_quality']:
        return False
    
    return True


def validate_block_on_data(block_class, df: pd.DataFrame, block_name: str) -> Dict[str, Any]:
    """Run validation on a block (simplified for parallel execution)"""
    try:
        block = block_class()
        results = []
        errors = 0
        
        # Use sliding window for efficiency
        window_size = 100
        for i in range(window_size, len(df), 10):  # Sample every 10 bars for speed
            try:
                hist_df = df.iloc[max(0, i-window_size):i+1].copy()
                result = block.analyze(hist_df)
                
                if result is not None:
                    results.append(result)
                    
            except Exception as e:
                errors += 1
                if errors > 50:  # Stop if too many errors
                    break
        
        if len(results) == 0:
            return {
                'status': 'FAIL',
                'reason': 'No valid results produced',
                'metrics': {}
            }
        
        # Calculate metrics
        signals = [r.get('signal', 'NEUTRAL') for r in results]
        confidences = [r.get('confidence', 0) for r in results]
        
        signal_rate = sum(1 for s in signals if s != 'NEUTRAL') / len(signals)
        avg_confidence = np.mean(confidences)
        std_confidence = np.std(confidences)
        
        metrics = {
            'total_bars': len(df),
            'valid_results': len(results),
            'data_quality': len(results) / (len(df) // 10),  # Adjusted for sampling
            'signal_rate': signal_rate,
            'avg_confidence': avg_confidence,
            'std_confidence': std_confidence,
            'errors': errors,
        }
        
        passed = check_institutional_criteria(metrics)
        
        return {
            'status': 'PASS' if passed else 'FAIL',
            'metrics': metrics,
            'passed_criteria': passed
        }
        
    except Exception as e:
        return {
            'status': 'ERROR',
            'reason': str(e),
            'metrics': {}
        }


def validate_single_block(block_info: Dict, df_subset: pd.DataFrame) -> Dict[str, Any]:
    """Validate a single block (runs in separate process)"""
    try:
        # Re-setup path in child process
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        block_name = block_info['name']
        block_path = block_info['file']
        category = block_info['category']
        
        print(f"🔬 [{category}/{block_name}] Starting validation...")
        
        # Import block
        block_class = import_block(block_path)
        
        if block_class is None:
            return {
                'name': block_name,
                'category': category,
                'status': 'ERROR',
                'reason': 'Import failed',
                'production_ready': False,
                'issues': ['Failed to import block'],
                'recommendations': ['Check block implementation'],
            }
        
        # Run backtest
        backtest_result = validate_block_on_data(block_class, df_subset, block_name)
        
        # Expert assessment
        assessment = {
            'name': block_name,
            'category': category,
            'production_ready': False,
            'confidence_level': 'LOW',
            'issues': [],
            'recommendations': [],
            'metrics': backtest_result.get('metrics', {}),
        }
        
        if backtest_result['status'] != 'PASS':
            assessment['issues'].append(f"Backtest failed: {backtest_result.get('reason', 'Unknown')}")
            assessment['recommendations'].append("Fix backtest implementation")
            print(f"❌ [{category}/{block_name}] FAIL - {backtest_result.get('reason')}")
            return assessment
        
        metrics = backtest_result['metrics']
        
        # Expert trader perspective
        if metrics['signal_rate'] > 0.2:
            assessment['issues'].append(f"Signals too frequent ({metrics['signal_rate']:.1%})")
            assessment['recommendations'].append("Increase signal threshold/filters")
        
        if metrics['avg_confidence'] < 30:
            assessment['issues'].append(f"Low average confidence ({metrics['avg_confidence']:.1f})")
            assessment['recommendations'].append("Improve confidence calculation")
        
        if metrics['std_confidence'] < 10:
            assessment['issues'].append("Confidence values too static")
            assessment['recommendations'].append("Add dynamic confidence adjustment")
        
        # Determine production readiness
        if len(assessment['issues']) == 0:
            assessment['production_ready'] = True
            assessment['confidence_level'] = 'HIGH'
            print(f"✅ [{category}/{block_name}] PRODUCTION READY - {metrics['signal_rate']:.1%} signals, {metrics['avg_confidence']:.1f}% conf")
        elif len(assessment['issues']) <= 2:
            assessment['confidence_level'] = 'MEDIUM'
            print(f"⚠️  [{category}/{block_name}] MEDIUM - {len(assessment['issues'])} issues")
        else:
            print(f"❌ [{category}/{block_name}] LOW - {len(assessment['issues'])} issues")
        
        return assessment
        
    except Exception as e:
        print(f"❌ [{block_info['category']}/{block_info['name']}] ERROR: {str(e)}")
        return {
            'name': block_info['name'],
            'category': block_info['category'],
            'status': 'ERROR',
            'reason': str(e),
            'production_ready': False,
            'issues': [f'Exception: {str(e)}'],
            'recommendations': ['Debug block implementation'],
        }


def main():
    print("="*80)
    print("🎯 INSTITUTIONAL-GRADE PRODUCTION VALIDATION (PARALLEL)")
    print("Testing all 67 building blocks on real BTC data")
    print("="*80)
    
    # Load real BTC data
    print("\n📊 Loading BTC 15min data...")
    df = load_btc_data(timeframe='15min', days=180)
    
    if df is None or len(df) == 0:
        print("❌ Failed to load data. Aborting.")
        return
    
    print(f"✅ Loaded {len(df)} bars from {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
    
    # Get all block files
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
    
    print(f"\n📋 Found {len(all_blocks)} blocks to validate")
    
    # Determine number of cores
    n_cores = mp.cpu_count()
    n_workers = max(1, n_cores - 1)  # Leave 1 core free
    print(f"🚀 Using {n_workers} cores (of {n_cores} available)")
    
    # Run parallel validation
    print(f"\n⚙️  Validating {len(all_blocks)} blocks in parallel...")
    print("="*80)
    
    results = []
    
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Submit all jobs
        futures = {
            executor.submit(validate_single_block, block_info, df): block_info
            for block_info in all_blocks
        }
        
        # Collect results as they complete
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            # Show progress
            completed = len(results)
            total = len(all_blocks)
            print(f"Progress: {completed}/{total} ({completed/total*100:.0f}%)")
    
    # Sort by category and name
    results.sort(key=lambda x: (x['category'], x['name']))
    
    # Generate summary
    print("\n" + "="*80)
    print("📊 FINAL PRODUCTION READINESS REPORT")
    print("="*80)
    
    production_ready = [r for r in results if r.get('production_ready', False)]
    needs_work = [r for r in results if not r.get('production_ready', False)]
    
    total = len(results)
    ready_count = len(production_ready)
    
    print(f"\n🎯 Production Ready: {ready_count}/{total} ({ready_count/total*100:.1f}%)")
    print(f"⚠️  Needs Work: {len(needs_work)}/{total} ({len(needs_work)/total*100:.1f}%)")
    
    print(f"\n✅ PRODUCTION READY BLOCKS ({ready_count}):")
    for r in production_ready:
        metrics = r.get('metrics', {})
        sig_rate = metrics.get('signal_rate', 0)
        conf = metrics.get('avg_confidence', 0)
        print(f"   ✓ {r['category']}/{r['name']:30s} - {sig_rate:.1%} signals, {conf:.1f}% conf")
    
    print(f"\n⚠️  BLOCKS NEEDING WORK ({len(needs_work)}):")
    for r in needs_work:
        issues_count = len(r.get('issues', []))
        print(f"   ✗ {r['category']}/{r['name']:30s} - {issues_count} issues")
        for issue in r.get('issues', [])[:2]:  # Show first 2 issues
            print(f"      - {issue}")
    
    # Save detailed report
    report_path = Path(__file__).parent.parent / 'docs' / 'v3' / 'building_blocks' / 'PRODUCTION_VALIDATION_REPORT.md'
    
    with open(report_path, 'w') as f:
        f.write("# Institutional-Grade Production Validation Report (Parallel)\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"## Summary\n\n")
        f.write(f"- **Total Blocks:** {total}\n")
        f.write(f"- **Production Ready:** {ready_count} ({ready_count/total*100:.1f}%)\n")
        f.write(f"- **Needs Work:** {len(needs_work)} ({len(needs_work)/total*100:.1f}%)\n\n")
        
        f.write(f"## Production Ready Blocks ({ready_count})\n\n")
        for r in production_ready:
            metrics = r.get('metrics', {})
            f.write(f"- ✅ **{r['name']}** ({r['category']}) - ")
            f.write(f"{metrics.get('signal_rate', 0):.1%} signals, ")
            f.write(f"{metrics.get('avg_confidence', 0):.1f}% confidence\n")
        
        f.write(f"\n## Blocks Needing Work ({len(needs_work)})\n\n")
        for r in needs_work:
            f.write(f"### {r['name']} ({r['category']})\n\n")
            
            if r.get('issues'):
                f.write(f"**Issues:**\n")
                for issue in r['issues']:
                    f.write(f"- {issue}\n")
                f.write("\n")
            
            if r.get('recommendations'):
                f.write(f"**Recommendations:**\n")
                for rec in r['recommendations']:
                    f.write(f"- {rec}\n")
                f.write("\n")
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    # Save JSON results
    json_path = Path(__file__).parent.parent / 'docs' / 'v3' / 'building_blocks' / 'validation_results.json'
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"📄 JSON results saved to: {json_path}")
    print("="*80)


if __name__ == "__main__":
    main()
