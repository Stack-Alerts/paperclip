"""
EXPERT MODE: Multicore Block Parameter Tuner
Discovers optimal block parameters through exhaustive grid search with walk-forward validation

Features:
- Multicore parallel processing for speed
- Tests thousands of parameter combinations
- Walk-forward validation on real data
- Expert Mode price action validation
- Tracks tested combinations (no duplicates)
- Returns top 10 configurations

Author: Cline (Expert Mode)
Date: 2026-01-01
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
import hashlib
from typing import Dict, Any, List, Tuple
from multiprocessing import Pool, cpu_count
from itertools import product
import pickle

from validate_walkforward_signals import SignalValidator


class BlockParameterTuner:
    """
    Expert-level hyperparameter tuner for building blocks
    
    Uses grid search with multicore processing to find optimal parameters
    """
    
    def __init__(self, 
                 block_path: str,
                 block_name: str,
                 data: pd.DataFrame,
                 cache_file: str = 'tuning_cache.pkl'):
        """
        Initialize tuner
        
        Args:
            block_path: Path to block Python file
            block_name: Name of block for identification
            data: Full dataset for testing
            cache_file: File to cache tested combinations
        """
        self.block_path = block_path
        self.block_name = block_name
        self.data = data
        self.cache_file = Path(__file__).parent.parent / cache_file
        
        # Load cache if exists
        self.tested_combinations = self.load_cache()
        
        print(f"{'='*80}")
        print(f"🔬 EXPERT MODE: MULTICORE PARAMETER TUNER")
        print(f"{'='*80}")
        print(f"Block: {block_name}")
        print(f"Data: {len(data)} bars from {data['timestamp'].min()} to {data['timestamp'].max()}")
        print(f"Cached combinations: {len(self.tested_combinations)}")
        print(f"CPU cores available: {cpu_count()}")
        print(f"{'='*80}\n")
    
    def load_cache(self) -> Dict[str, Dict]:
        """Load cache of tested combinations"""
        if self.cache_file.exists():
            with open(self.cache_file, 'rb') as f:
                return pickle.load(f)
        return {}
    
    def save_cache(self):
        """Save cache of tested combinations"""
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.tested_combinations, f)
    
    def get_combination_hash(self, params: Dict) -> str:
        """Generate unique hash for parameter combination"""
        # Sort keys for consistent hashing
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()
    
    def test_single_combination(self, params: Dict) -> Dict[str, Any]:
        """
        Test a single parameter combination
        
        Args:
            params: Dictionary of parameters to test
            
        Returns:
            Results dictionary with metrics
        """
        # Check cache first
        param_hash = self.get_combination_hash(params)
        if param_hash in self.tested_combinations:
            return self.tested_combinations[param_hash]
        
        try:
            # Import block with parameters
            spec = importlib.util.spec_from_file_location("block", self.block_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            block_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and hasattr(obj, 'analyze'):
                    block_class = obj
                    break
            
            if not block_class:
                return {'error': 'Could not load block class'}
            
            # Initialize block with parameters
            block = block_class(**params)
            
            # Run walk-forward test on 180-day period - TEST EVERY BAR FOR ACCURACY
            signals = []
            errors = 0
            window_size = 800
            
            # CRITICAL: Test EVERY bar for accurate parameter discovery
            for i in range(window_size, len(self.data), 1):  # Changed from 20 to 1
                try:
                    hist_df = self.data.iloc[:i+1].copy()
                    result = block.analyze(hist_df)
                    
                    if result and isinstance(result, dict):
                        signal = result.get('signal', 'UNKNOWN')
                        confidence = result.get('confidence', 0)
                        
                        if signal not in ['NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR', 'NO_BREAK']:
                            signals.append({
                                'timestamp': hist_df['timestamp'].iloc[-1],
                                'signal': signal,
                                'confidence': confidence,
                                'price': hist_df['close'].iloc[-1],
                                'bar_index': i
                            })
                except:
                    errors += 1
            
            # If no signals, return poor result
            if len(signals) == 0:
                result = {
                    'params': params,
                    'param_hash': param_hash,
                    'total_signals': 0,
                    'accuracy': 0.0,
                    'quality_score': 0,
                    'reward_risk': 0.0,
                    'follow_through': 0.0,
                    'errors': errors,
                    'status': 'NO_SIGNALS'
                }
                self.tested_combinations[param_hash] = result
                return result
            
            # Run Expert Mode validation
            validator = SignalValidator(lookback_bars=20, lookforward_bars=50)
            validation_report = validator.validate_all_signals(self.data, signals)
            
            if 'error' in validation_report:
                result = {
                    'params': params,
                    'param_hash': param_hash,
                    'total_signals': len(signals),
                    'accuracy': 0.0,
                    'quality_score': 0,
                    'reward_risk': 0.0,
                    'follow_through': 0.0,
                    'errors': errors,
                    'status': 'VALIDATION_ERROR'
                }
                self.tested_combinations[param_hash] = result
                return result
            
            # Extract metrics
            result = {
                'params': params,
                'param_hash': param_hash,
                'total_signals': validation_report['total_signals'],
                'correct_signals': validation_report['correct_signals'],
                'accuracy': validation_report['accuracy'],
                'quality_score': validation_report['quality_score'],
                'reward_risk': validation_report['overall_metrics']['avg_reward_risk_ratio'],
                'follow_through': validation_report['overall_metrics']['avg_consecutive_favorable_bars'],
                'bullish_accuracy': validation_report['bullish_signals']['accuracy'],
                'bearish_accuracy': validation_report['bearish_signals']['accuracy'],
                'errors': errors,
                'status': 'SUCCESS',
                'validation_report': validation_report
            }
            
            # Cache result
            self.tested_combinations[param_hash] = result
            
            return result
            
        except Exception as e:
            result = {
                'params': params,
                'param_hash': param_hash,
                'total_signals': 0,
                'accuracy': 0.0,
                'quality_score': 0,
                'reward_risk': 0.0,
                'follow_through': 0.0,
                'errors': 1,
                'status': f'ERROR: {str(e)}'
            }
            self.tested_combinations[param_hash] = result
            return result
    
    def run_grid_search(self, 
                       param_grid: Dict[str, List],
                       max_combinations: int = None,
                       n_cores: int = None) -> List[Dict]:
        """
        Run grid search over parameter space
        
        Args:
            param_grid: Dictionary of parameter names to lists of values
            max_combinations: Maximum combinations to test (None = all)
            n_cores: Number of CPU cores to use (None = all available)
            
        Returns:
            List of results sorted by quality score
        """
        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combinations = list(product(*param_values))
        
        # Convert to list of dicts
        param_dicts = [
            dict(zip(param_names, combo))
            for combo in all_combinations
        ]
        
        # Limit if requested
        if max_combinations and len(param_dicts) > max_combinations:
            print(f"⚠️  Limiting to {max_combinations} of {len(param_dicts)} combinations")
            # Random sample for diversity
            import random
            random.shuffle(param_dicts)
            param_dicts = param_dicts[:max_combinations]
        
        print(f"\n🔍 Testing {len(param_dicts)} parameter combinations...")
        print(f"{'='*80}\n")
        
        # Determine cores to use
        if n_cores is None:
            n_cores = max(1, cpu_count() - 1)  # Leave one core free
        
        print(f"Using {n_cores} CPU cores for parallel processing\n")
        
        # Run parallel grid search
        if n_cores > 1:
            with Pool(n_cores) as pool:
                results = pool.map(self.test_single_combination, param_dicts)
        else:
            results = [self.test_single_combination(p) for p in param_dicts]
        
        # Save cache after each batch
        self.save_cache()
        
        # Filter successful results and sort by quality score
        successful_results = [r for r in results if r['status'] == 'SUCCESS']
        successful_results.sort(key=lambda x: x['quality_score'], reverse=True)
        
        print(f"\n{'='*80}")
        print(f"✅ GRID SEARCH COMPLETE")
        print(f"{'='*80}")
        print(f"Total combinations tested: {len(results)}")
        print(f"Successful: {len(successful_results)}")
        print(f"Failed: {len(results) - len(successful_results)}")
        print(f"{'='*80}\n")
        
        return successful_results
    
    def print_top_results(self, results: List[Dict], top_n: int = 10):
        """Pretty print top N results"""
        print(f"{'='*80}")
        print(f"🏆 TOP {min(top_n, len(results))} PARAMETER COMBINATIONS")
        print(f"{'='*80}\n")
        
        for i, result in enumerate(results[:top_n], 1):
            print(f"#{i} - Quality Score: {result['quality_score']}/100")
            print(f"   Parameters: {result['params']}")
            print(f"   Accuracy: {result['accuracy']:.1f}%")
            print(f"   Total Signals: {result['total_signals']}")
            print(f"   Reward/Risk: {result['reward_risk']:.2f}")
            print(f"   Follow-Through: {result['follow_through']:.1f} bars")
            print(f"   Bullish Accuracy: {result['bullish_accuracy']:.1f}%")
            print(f"   Bearish Accuracy: {result['bearish_accuracy']:.1f}%")
            print()
    
    def save_top_results(self, results: List[Dict], filename: str, top_n: int = 10):
        """Save top results to JSON file"""
        output_path = Path(__file__).parent.parent / filename
        
        # Prepare data for JSON (remove non-serializable fields)
        top_results = []
        for result in results[:top_n]:
            clean_result = result.copy()
            if 'validation_report' in clean_result:
                del clean_result['validation_report']  # Too verbose
            top_results.append(clean_result)
        
        with open(output_path, 'w') as f:
            json.dump(top_results, f, indent=2)
        
        print(f"✅ Top {len(top_results)} results saved to: {output_path}\n")


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
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)


if __name__ == "__main__":
    print(f"\n{'='*80}")
    print(f"🎯 EXPERT MODE: FAIR VALUE GAP PARAMETER TUNING")
    print(f"{'='*80}\n")
    
    # Load data
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Initialize tuner
    block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / 'price_action' / 'fair_value_gap.py'
    tuner = BlockParameterTuner(
        block_path=str(block_path),
        block_name='fair_value_gap',
        data=df,
        cache_file='fair_value_gap_tuning_cache.pkl'
    )
    
    # Define parameter grid - FAIR VALUE GAP
    param_grid = {
        'lookback': [3, 5, 7],  # Gap detection lookback
        'timeframe': ['15min'],
    }
    
    print("📝 Parameter Ranges (INSTITUTIONAL GRADE - FAIR VALUE GAP):") 
    print("   lookback: 3-7 (3 values around classic 5)")
    print("   Total combinations: 3 (quick test)")
    print("   NOTE: FVG = Critical ICT price action concept")
    print("   ⚠️  Testing EVERY bar (17K+) for maximum accuracy")
    print(f"\n{'='*80}\n")
    
    print("Parameter grid:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")
    
    total_combinations = np.prod([len(v) for v in param_grid.values()])
    print(f"\nTotal combinations: {total_combinations}")
    print(f"{'='*80}\n")
    
    # Run grid search
    results = tuner.run_grid_search(
        param_grid=param_grid,
        max_combinations=None,  # Test all combinations
        n_cores=None  # Use all available cores minus 1
    )
    
    # Print top results
    tuner.print_top_results(results, top_n=10)
    
    # Save top results
    tuner.save_top_results(results, f'top_params_{tuner.block_name}.json', top_n=10)
    
    print(f"{'='*80}")
    print(f"✅ TUNING COMPLETE")
    print(f"{'='*80}\n")
    
    if len(results) > 0:
        best = results[0]
        print(f"🏆 BEST CONFIGURATION:")
        print(f"   Parameters: {best['params']}")
        print(f"   Quality Score: {best['quality_score']}/100")
        print(f"   Accuracy: {best['accuracy']:.1f}%")
        print(f"   Signals: {best['total_signals']}")
        print(f"\n   → Use these parameters for production deployment")
    else:
        print("❌ No successful configurations found")
        print("   → Block may need fundamental redesign")
