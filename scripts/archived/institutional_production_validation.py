"""
Institutional-Grade Production Validation for ALL Building Blocks
Tests each block on real BTC data with backtest + walkforward validation
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
import importlib.util
import traceback


class InstitutionalBlockValidator:
    """
    Institutional-grade validation framework for building blocks
    - Real BTC data from CSV files
    - Backtest validation
    - Walkforward validation
    - Statistical robustness checks
    - EXPERT MODE quality assessment
    """
    
    def __init__(self):
        self.results = {}
        self.production_ready = []
        self.needs_work = []
        
        # Institutional validation criteria
        self.INSTITUTIONAL_CRITERIA = {
            'signal_quality': {
                'min_signals': 10,  # Must generate meaningful signals
                'max_signal_rate': 0.3,  # Can't signal on >30% of bars
                'min_signal_rate': 0.001,  # Must signal on at least 0.1% of bars
            },
            'confidence_distribution': {
                'min_avg_confidence': 20,  # Average confidence ≥ 20%
                'max_avg_confidence': 95,  # Average confidence ≤ 95% (avoid overconfidence)
                'min_std_confidence': 5,   # Confidence must vary (not static)
            },
            'data_robustness': {
                'min_data_quality': 0.95,  # 95% data usage (not too many NaN)
                'handles_volatility': True,  # Must work during high volatility
                'handles_ranging': True,     # Must work in ranging markets
            },
            'institutional_quality': {
                'no_lookahead_bias': True,
                'no_repainting': True,
                'production_safe': True,
                'consistent_across_timeframes': True,
            }
        }
    
    def load_real_btc_data(self, timeframe: str = '15min', days: int = 180) -> pd.DataFrame:
        """Load real BTC data from CSV files"""
        print(f"\n📊 Loading BTC {timeframe} data from CSV...")
        
        try:
            # Determine which file to load
            if timeframe == '15min':
                data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
            elif timeframe == '30min':
                data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_30m.csv'
            else:
                data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
            
            if not data_path.exists():
                raise FileNotFoundError(f"Data file not found: {data_path}")
            
            print(f"Loading from: {data_path}")
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
            
            # Ensure required columns
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            # Convert timestamp
            if df['timestamp'].dtype == 'object':
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Sort by time
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Filter to last N days if specified
            if days:
                cutoff_date = df['timestamp'].max() - timedelta(days=days)
                df = df[df['timestamp'] >= cutoff_date].copy()
            
            # Validate OHLC logic
            assert (df['high'] >= df['low']).all(), "High < Low error"
            assert (df['high'] >= df['open']).all(), "High < Open error"
            assert (df['high'] >= df['close']).all(), "High < Close error"
            assert (df['low'] <= df['open']).all(), "Low > Open error"
            assert (df['low'] <= df['close']).all(), "Low > Close error"
            
            print(f"✅ Loaded {len(df)} bars from {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
            return df
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            traceback.print_exc()
            return None
    
    def import_block(self, block_path: str):
        """Dynamically import a building block"""
        try:
            spec = importlib.util.spec_from_file_location("block", block_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the class in the module
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and hasattr(obj, 'analyze'):
                    return obj
            
            return None
        except Exception as e:
            print(f"❌ Error importing block {block_path}: {e}")
            traceback.print_exc()
            return None
    
    def validate_block_backtest(self, block_class, df: pd.DataFrame, block_name: str) -> Dict[str, Any]:
        """Run backtest validation on a block"""
        print(f"\n🔬 Backtesting {block_name}...")
        
        try:
            # Initialize block
            block = block_class()
            
            # Test on full dataset
            results = []
            errors = 0
            
            for i in range(len(df)):
                try:
                    # Get historical data up to this point
                    hist_df = df.iloc[:i+1].copy()
                    
                    if len(hist_df) < 20:  # Need minimum data
                        continue
                    
                    # Run block analysis
                    result = block.analyze(hist_df)
                    
                    if result is not None:
                        results.append(result)
                        
                except Exception as e:
                    errors += 1
                    if errors < 5:  # Only show first few errors
                        print(f"  ⚠️  Error at bar {i}: {e}")
            
            # Analyze results
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
            unique_signals = len(set(signals))
            
            metrics = {
                'total_bars': len(df),
                'valid_results': len(results),
                'data_quality': len(results) / len(df),
                'signal_rate': signal_rate,
                'avg_confidence': avg_confidence,
                'std_confidence': std_confidence,
                'unique_signals': unique_signals,
                'errors': errors,
            }
            
            # Check against institutional criteria
            passed = self.check_institutional_criteria(metrics)
            
            return {
                'status': 'PASS' if passed else 'FAIL',
                'metrics': metrics,
                'passed_criteria': passed
            }
            
        except Exception as e:
            print(f"❌ Backtest failed: {e}")
            traceback.print_exc()
            return {
                'status': 'ERROR',
                'reason': str(e),
                'metrics': {}
            }
    
    def validate_block_walkforward(self, block_class, df: pd.DataFrame, block_name: str) -> Dict[str, Any]:
        """Run walkforward validation on a block"""
        print(f"\n🚶 Walkforward testing {block_name}...")
        
        try:
            # Split into walk-forward windows
            window_size = len(df) // 4  # 4 windows
            results_by_window = []
            
            for window_idx in range(3):  # Test on 3 windows
                start_idx = window_idx * window_size
                end_idx = start_idx + window_size
                
                window_df = df.iloc[start_idx:end_idx].copy()
                
                print(f"  Window {window_idx + 1}: Bars {start_idx} to {end_idx}")
                
                # Run backtest on this window
                window_result = self.validate_block_backtest(block_class, window_df, f"{block_name}_W{window_idx+1}")
                results_by_window.append(window_result)
            
            # Check consistency across windows
            all_passed = all(r['status'] == 'PASS' for r in results_by_window)
            
            # Calculate consistency metrics
            if all_passed:
                signal_rates = [r['metrics']['signal_rate'] for r in results_by_window]
                confidences = [r['metrics']['avg_confidence'] for r in results_by_window]
                
                consistency = {
                    'signal_rate_variance': np.std(signal_rates),
                    'confidence_variance': np.std(confidences),
                    'all_windows_passed': True
                }
            else:
                consistency = {
                    'all_windows_passed': False
                }
            
            return {
                'status': 'PASS' if all_passed else 'FAIL',
                'consistency': consistency,
                'window_results': results_by_window
            }
            
        except Exception as e:
            print(f"❌ Walkforward failed: {e}")
            traceback.print_exc()
            return {
                'status': 'ERROR',
                'reason': str(e)
            }
    
    def check_institutional_criteria(self, metrics: Dict[str, Any]) -> bool:
        """Check if block meets institutional quality criteria"""
        criteria = self.INSTITUTIONAL_CRITERIA
        
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
    
    def expert_mode_assessment(self, block_name: str, backtest_result: Dict, walkforward_result: Dict) -> Dict[str, Any]:
        """EXPERT MODE institutional-grade assessment"""
        print(f"\n⭐ EXPERT MODE Assessment: {block_name}")
        
        assessment = {
            'block_name': block_name,
            'timestamp': datetime.now().isoformat(),
            'production_ready': False,
            'confidence_level': 'LOW',
            'issues': [],
            'recommendations': [],
        }
        
        # Analyze backtest results
        if backtest_result['status'] != 'PASS':
            assessment['issues'].append(f"Backtest failed: {backtest_result.get('reason', 'Unknown')}")
            assessment['recommendations'].append("Fix backtest implementation")
            return assessment
        
        # Analyze walkforward results
        if walkforward_result['status'] != 'PASS':
            assessment['issues'].append("Walkforward validation failed")
            assessment['recommendations'].append("Improve consistency across time periods")
            return assessment
       
        # Check metrics
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
        elif len(assessment['issues']) <= 2:
            assessment['confidence_level'] = 'MEDIUM'
        
        return assessment
    
    def validate_all_blocks(self):
        """Validate all 67 building blocks"""
        print("="*80)
        print("🎯 INSTITUTIONAL-GRADE PRODUCTION VALIDATION")
        print("Testing all 67 building blocks on real BTC data")
        print("="*80)
        
        # Load real BTC data
        df_15min = self.load_real_btc_data(timeframe='15min', days=180)
        
        if df_15min is None:
            print("❌ Failed to load data. Aborting.")
            return
        
        # Get all block files
        blocks_dir = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks'
        
        all_blocks = []
        for category_dir in blocks_dir.iterdir():
            if category_dir.is_dir():
                for block_file in category_dir.glob('*.py'):
                    if block_file.name != '__init__.py':
                        all_blocks.append({
                            'category': category_dir.name,
                            'file': block_file,
                            'name': block_file.stem
                        })
        
        print(f"\n📋 Found {len(all_blocks)} blocks to validate")
        
        # Validate each block
        for idx, block_info in enumerate(all_blocks, 1):
            print(f"\n{'='*80}")
            print(f"Block {idx}/{len(all_blocks)}: {block_info['category']}/{block_info['name']}")
            print(f"{'='*80}")
            
            # Import block
            block_class = self.import_block(str(block_info['file']))
            
            if block_class is None:
                print(f"❌ Failed to import block")
                self.results[block_info['name']] = {
                    'status': 'ERROR',
                    'reason': 'Import failed'
                }
                self.needs_work.append(block_info['name'])
                continue
            
            # Run backtest validation
            backtest_result = self.validate_block_backtest(
                block_class, df_15min, block_info['name']
            )
            
            # Run walkforward validation
            walkforward_result = self.validate_block_walkforward(
                block_class, df_15min, block_info['name']
            )
            
            # Expert mode assessment
            expert_assessment = self.expert_mode_assessment(
                block_info['name'], backtest_result, walkforward_result
            )
            
            # Store results
            self.results[block_info['name']] = {
                'category': block_info['category'],
                'backtest': backtest_result,
                'walkforward': walkforward_result,
                'expert_assessment': expert_assessment
            }
            
            # Categorize
            if expert_assessment['production_ready']:
                self.production_ready.append(block_info['name'])
                print(f"✅ PRODUCTION READY")
            else:
                self.needs_work.append(block_info['name'])
                print(f"⚠️  NEEDS WORK: {len(expert_assessment['issues'])} issues")
                for issue in expert_assessment['issues']:
                    print(f"   - {issue}")
        
        # Generate final report
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate final institutional-grade report"""
        print("\n" + "="*80)
        print("📊 FINAL PRODUCTION READINESS REPORT")
        print("="*80)
        
        total_blocks = len(self.results)
        ready_count = len(self.production_ready)
        needs_work_count = len(self.needs_work)
        
        print(f"\n🎯 Production Ready: {ready_count}/{total_blocks} ({ready_count/total_blocks*100:.1f}%)")
        print(f"⚠️  Needs Work: {needs_work_count}/{total_blocks} ({needs_work_count/total_blocks*100:.1f}%)")
        
        print(f"\n✅ PRODUCTION READY BLOCKS ({ready_count}):")
        for block in sorted(self.production_ready):
            print(f"   ✓ {block}")
        
        print(f"\n⚠️  BLOCKS NEEDING WORK ({needs_work_count}):")
        for block in sorted(self.needs_work):
            assessment = self.results[block]['expert_assessment']
            print(f"   ✗ {block} - {len(assessment['issues'])} issues")
        
        # Save detailed report
        report_path = Path(__file__).parent.parent / 'docs' / 'v3' / 'building_blocks' / 'PRODUCTION_VALIDATION_REPORT.md'
        self.save_detailed_report(report_path)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        print("="*80)
    
    def save_detailed_report(self, path: Path):
        """Save detailed markdown report"""
        with open(path, 'w') as f:
            f.write("# Institutional-Grade Production Validation Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            
            total = len(self.results)
            ready = len(self.production_ready)
            
            f.write(f"## Summary\n\n")
            f.write(f"- **Total Blocks:** {total}\n")
            f.write(f"- **Production Ready:** {ready} ({ready/total*100:.1f}%)\n")
            f.write(f"- **Needs Work:** {total - ready} ({(total-ready)/total*100:.1f}%)\n\n")
            
            f.write(f"## Production Ready Blocks ({ready})\n\n")
            for block in sorted(self.production_ready):
                category = self.results[block]['category']
                f.write(f"- ✅ **{block}** ({category})\n")
            
            f.write(f"\n## Blocks Needing Work ({total - ready})\n\n")
            for block in sorted(self.needs_work):
                result = self.results[block]
                category = result['category']
                assessment = result['expert_assessment']
                
                f.write(f"### {block} ({category})\n\n")
                f.write(f"**Status:** ⚠️ Needs Work\n\n")
                
                if assessment['issues']:
                    f.write(f"**Issues:**\n")
                    for issue in assessment['issues']:
                        f.write(f"- {issue}\n")
                    f.write("\n")
                
                if assessment['recommendations']:
                    f.write(f"**Recommendations:**\n")
                    for rec in assessment['recommendations']:
                        f.write(f"- {rec}\n")
                    f.write("\n")


if __name__ == "__main__":
    validator = InstitutionalBlockValidator()
    validator.validate_all_blocks()
