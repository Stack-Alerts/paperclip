"""
Test All Building Blocks - Comprehensive Registry Test Suite
=============================================================

Tests all building blocks one by one using the registry_test_library
and generates a comprehensive markdown report.

Usage:
    python scripts/test_all_building_blocks.py --days 180

This will test ALL building blocks and generate:
- data/reports/ALL_BUILDING_BLOCKS_TEST_REPORT.md

Author: BTC_Engine_v3
Date: 2026-01-15
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.building_blocks_registry_envoked.registry_test_library import test_building_block_registry
from src.detectors.building_blocks.registry import BlockRegistry
from datetime import datetime
import argparse
import time
import traceback


def generate_markdown_report(results, output_file, test_days, start_time, end_time):
    """Generate comprehensive markdown report."""
    duration = (end_time - start_time).total_seconds()
    
    # Calculate summary statistics
    total_blocks = len(results)
    successful_blocks = len([r for r in results.values() if r is not None])
    failed_blocks = total_blocks - successful_blocks
    
    total_signals = sum(r['results']['total_results'] for r in results.values() if r)
    total_errors = sum(r['results']['total_errors'] for r in results.values() if r)
    
    # Coverage statistics
    coverage_stats = []
    for block_name, result in results.items():
        if result:
            coverage_stats.append({
                'name': block_name,
                'coverage': result['coverage']['coverage_pct'],
                'signals': result['results']['total_results'],
                'category': result['block_metadata']['category']
            })
    
    coverage_stats.sort(key=lambda x: x['coverage'], reverse=True)
    
    # Generate markdown
    md = []
    md.append("# Building Blocks Comprehensive Test Report")
    md.append(f"\n**Generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Test Period:** {test_days} days")
    md.append(f"**Duration:** {duration/60:.1f} minutes ({duration/3600:.2f} hours)")
    md.append("")
    
    md.append("## Executive Summary")
    md.append("")
    md.append(f"- **Total Blocks Tested:** {total_blocks}")
    md.append(f"- **Successful:** {successful_blocks} ({successful_blocks/total_blocks*100:.1f}%)")
    md.append(f"- **Failed:** {failed_blocks} ({failed_blocks/total_blocks*100:.1f}%)")
    md.append(f"- **Total Signals Generated:** {total_signals:,}")
    md.append(f"- **Total Errors:** {total_errors:,}")
    md.append(f"- **Average Coverage:** {sum(s['coverage'] for s in coverage_stats)/len(coverage_stats):.1f}%")
    md.append("")
    
    md.append("## Coverage Leaderboard")
    md.append("")
    md.append("| Rank | Block | Category | Coverage | Signals | Status |")
    md.append("|------|-------|----------|----------|---------|--------|")
    
    for idx, stat in enumerate(coverage_stats, 1):
        status = "✅" if stat['coverage'] == 100.0 else "⚠️" if stat['coverage'] >= 50.0 else "❌"
        md.append(f"| {idx} | {stat['name']} | {stat['category']} | {stat['coverage']:.1f}% | {stat['signals']:,} | {status} |")
    
    md.append("")
    
    md.append("## Test Performance")
    md.append("")
    
    # Calculate timing statistics
    all_durations = [r['test_duration_seconds'] for r in results.values() if r and 'test_duration_seconds' in r]
    if all_durations:
        total_test_time = sum(all_durations)
        avg_time = total_test_time / len(all_durations)
        md.append(f"- **Total Test Time:** {total_test_time/60:.1f} min ({total_test_time/3600:.2f} hours)")
        md.append(f"- **Average per Block:** {avg_time:.1f}s ({avg_time/60:.2f} min)")
        md.append(f"- **Fastest Test:** {min(all_durations):.1f}s")
        md.append(f"- **Slowest Test:** {max(all_durations):.1f}s")
        md.append("")
    
    md.append("## Failed/Crashed Blocks")
    md.append("")
    
    failed_blocks = [(name, result) for name, result in results.items() 
                     if result and result.get('test_status') in ['FAILED', 'CRASHED']]
    
    if failed_blocks:
        md.append("| Block | Status | Duration | Error |")
        md.append("|-------|--------|----------|-------|")
        for name, result in failed_blocks:
            status = result.get('test_status', 'UNKNOWN')
            duration = result.get('test_duration_seconds', 0)
            error = result.get('error_details', 'No details')[:100]  # Truncate long errors
            md.append(f"| {name} | ❌ {status} | {duration:.1f}s | {error} |")
        
        md.append("")
        md.append("### Crash Details")
        md.append("")
        
        for name, result in failed_blocks:
            if result.get('test_status') == 'CRASHED':
                md.append(f"#### {name}")
                md.append("")
                md.append(f"**Error:** {result.get('error_details', 'Unknown')}")
                md.append("")
                if 'error_traceback' in result:
                    md.append("**Traceback:**")
                    md.append("```python")
                    md.append(result['error_traceback'])
                    md.append("```")
                md.append("")
    else:
        md.append("✅ **All blocks passed!**")
    
    md.append("")
    
    md.append("## Detailed Results by Category")
    md.append("")
    
    # Group by category
    by_category = {}
    for stat in coverage_stats:
        cat = stat['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(stat)
    
    for category in sorted(by_category.keys()):
        blocks = by_category[category]
        md.append(f"### {category} ({len(blocks)} blocks)")
        md.append("")
        md.append("| Block | Coverage | Signals | Missing Signals |")
        md.append("|-------|----------|---------|-----------------|")
        
        for stat in blocks:
            result = results[stat['name']]
            missing = len(result['coverage']['missing_signals'])
            md.append(f"| {stat['name']} | {stat['coverage']:.1f}% | {stat['signals']:,} | {missing} |")
        
        md.append("")
    
    md.append("## Individual Block Details")
    md.append("")
    
    for block_name in sorted(results.keys()):
        result = results[block_name]
        if not result:
            continue
        
        md.append(f"### {block_name}")
        md.append("")
        md.append(f"**Category:** {result['block_metadata']['category']}")
        md.append(f"**Class:** {result['block_metadata']['class_name']}")
        md.append(f"**Weight:** {result['block_metadata']['default_weight']}")
        md.append("")
        
        # Signal Statistics
        md.append("#### 📊 Signal Statistics")
        md.append("")
        total_tests = result['results']['total_results'] + result['results']['total_errors']
        error_pct = result['results']['total_errors'] / total_tests * 100 if total_tests > 0 else 0
        md.append(f"- **Total results:** {result['results']['total_results']:,}")
        md.append(f"- **Errors:** {result['results']['total_errors']} ({error_pct:.1f}%)")
        md.append(f"- **Unique signals found:** {result['results']['unique_signals_found']}")
        md.append("")
        
        # Valid Signals Coverage
        md.append("#### 🎯 Valid Signals Coverage")
        md.append("")
        expected_count = len(result['coverage']['expected_signals'])
        found_count = len(result['coverage']['found_signals'])
        md.append(f"- **Expected (from registry):** {expected_count} signals")
        md.append(f"- **Found in test:** {found_count} signals")
        md.append(f"- **Coverage:** {result['coverage']['coverage_pct']:.1f}%")
        md.append("")
        
        # Missing Signals (with hidden status)
        missing = result['coverage']['missing_signals']
        if missing:
            md.append("#### ⚠️ Missing Signals (not found in test)")
            md.append("")
            
            # Get metadata to check ui_visible status
            metadata = BlockRegistry.get_block(block_name)
            for sig in sorted(missing):
                signal_config = metadata.signal_tiers.get(sig, {})
                is_hidden = signal_config.get('ui_visible', True) == False or signal_config.get('points', 1) == 0
                
                if is_hidden:
                    md.append(f"- **{sig}** - Hidden from UI (points: 0)")
                else:
                    md.append(f"- **{sig}** - ❌ ERROR MISSING")
            
            md.append("")
        
        # Signal Distribution
        md.append("#### 📈 Signal Distribution")
        md.append("")
        signal_counts = result['results']['signal_counts']
        expected_signals = set(result['coverage']['expected_signals'])
        
        for sig, count in sorted(signal_counts.items(), key=lambda x: -x[1]):
            pct = count / result['results']['total_results'] * 100
            in_registry = "✓" if sig in expected_signals else "✗"
            md.append(f"- **[{in_registry}] {sig}:** {count:,} ({pct:.1f}%)")
        
        md.append("")
        
        # Density Metrics
        md.append("#### 📉 Density Metrics")
        md.append("")
        test_days = result['data_info']['test_days']
        md.append(f"- **Test period:** {test_days} days")
        md.append(f"- **Signals per day:** {result['results']['signals_per_day']:.2f}")
        candles_per_signal = result['data_info']['test_candles'] / result['results']['total_results'] if result['results']['total_results'] > 0 else 0
        md.append(f"- **Candles per signal:** {candles_per_signal:.1f}")
        md.append("")
    
    md.append("## Test Configuration")
    md.append("")
    md.append(f"- Test Period: {test_days} days")
    md.append(f"- Timeframe: 15 minutes")
    md.append(f"- Method: Expanding window (candle-by-candle)")
    md.append(f"- Multicore: Enabled")
    md.append("")
    
    md.append("---")
    md.append(f"*Report generated by BTC_Engine_v3 Building Block Test Suite*")
    md.append(f"*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(md))
    
    print(f"\n✅ Markdown report saved: {output_file}")


def generate_signal_occurrence_json(results, test_days):
    """
    Generate signal occurrence statistics JSON for Strategy Builder UI.
    
    Args:
        results: Test results dictionary
        test_days: Number of days tested
    """
    import json
    
    # Build statistics for each block
    blocks_stats = {}
    
    for block_name, result in results.items():
        if not result or result.get('test_status') != 'SUCCESS':
            # Skip failed blocks
            continue
        
        # Extract signal counts
        signal_counts = result['results']['signal_counts']
        total_results = result['results']['total_results']
        
        # Calculate percentages and format
        signal_stats = {}
        for signal, count in signal_counts.items():
            percentage = (count / total_results * 100) if total_results > 0 else 0
            signal_stats[signal] = {
                'count': count,
                'percentage': round(percentage, 2),
                'total_candles': total_results
            }
        
        blocks_stats[block_name] = {
            'block_name': block_name,
            'total_candles': total_results,
            'errors': result['results']['total_errors'],
            'signals': signal_stats
        }
    
    # Create output
    output_data = {
        'analysis_date': datetime.now().isoformat(),
        'data_timeframe': '15min',
        'data_days': test_days,
        'total_blocks': len(blocks_stats),
        'blocks': blocks_stats
    }
    
    # Save to catalog directory (used by Strategy Builder)
    output_path = Path('data/catalog/signal_occurrence_statistics.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Signal occurrence statistics saved: {output_path}")
    print(f"   Blocks with data: {len(blocks_stats)}")
    print(f"   Total signals tracked: {sum(len(b['signals']) for b in blocks_stats.values())}")


def main():
    """Test all building blocks and generate report."""
    parser = argparse.ArgumentParser(description='Test All Building Blocks')
    parser.add_argument('--days', type=int, default=180, help='Test period in days (default: 180)')
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("COMPREHENSIVE BUILDING BLOCK TEST SUITE")
    print("="*80)
    print(f"Test Period: {args.days} days")
    print(f"Timeframe: 15 minutes")
    print("="*80)
    
    start_time = datetime.now()
    
    # Get all blocks from registry
    all_blocks = BlockRegistry.list_blocks()
    total_blocks = len(all_blocks)
    
    print(f"\n📋 Found {total_blocks} building blocks in registry")
    print("\n🔬 Starting comprehensive test...\n")
    
    results = {}
    
    for idx, block_name in enumerate(sorted(all_blocks), 1):
        print(f"\n{'='*80}")
        print(f"[{idx}/{total_blocks}] Testing: {block_name}")
        print(f"{'='*80}")
        
        block_start = time.time()
        
        try:
            result = test_building_block_registry(
                block_name=block_name,
                days=args.days,
                use_multicore=True
            )
            
            block_duration = time.time() - block_start
            
            if result:
                # Add timing to result
                result['test_duration_seconds'] = block_duration
                result['test_status'] = 'SUCCESS'
                result['error_details'] = None
                
                coverage = result['coverage']['coverage_pct']
                signals = result['results']['total_results']
                print(f"\n✅ {block_name}: {coverage:.1f}% coverage, {signals:,} signals")
                print(f"⏱️  Duration: {block_duration:.1f}s ({block_duration/60:.2f} min)")
            else:
                # Test returned None (failed)
                result = {
                    'test_duration_seconds': block_duration,
                    'test_status': 'FAILED',
                    'error_details': 'Test returned None - check building block implementation',
                    'block_metadata': BlockRegistry.get_block(block_name).__dict__ if BlockRegistry.get_block(block_name) else {}
                }
                print(f"\n❌ {block_name}: Test failed")
                print(f"⏱️  Duration: {block_duration:.1f}s ({block_duration/60:.2f} min)")
            
            results[block_name] = result
                
        except Exception as e:
            block_duration = time.time() - block_start
            error_trace = traceback.format_exc()
            
            print(f"\n❌ {block_name}: Exception: {str(e)}")
            print(f"⏱️  Duration: {block_duration:.1f}s ({block_duration/60:.2f} min)")
            print(f"\n📋 Traceback:")
            print(error_trace)
            
            # Store crash details
            results[block_name] = {
                'test_duration_seconds': block_duration,
                'test_status': 'CRASHED',
                'error_details': str(e),
                'error_traceback': error_trace,
                'block_metadata': BlockRegistry.get_block(block_name).__dict__ if BlockRegistry.get_block(block_name) else {}
            }
        
        print(f"\nProgress: {idx}/{total_blocks} ({idx/total_blocks*100:.1f}%)")
    
    end_time = datetime.now()
    
    # Generate report
    print("\n" + "="*80)
    print("GENERATING COMPREHENSIVE REPORT")
    print("="*80)
    
    output_dir = Path('data/reports')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'ALL_BUILDING_BLOCKS_TEST_REPORT.md'
    
    generate_markdown_report(results, output_file, args.days, start_time, end_time)
    
    # Also generate signal occurrence statistics JSON for Strategy Builder UI
    print("\n" + "="*80)
    print("GENERATING SIGNAL OCCURRENCE STATISTICS")
    print("="*80)
    
    generate_signal_occurrence_json(results, args.days)
    
    # Summary
    successful = len([r for r in results.values() if r is not None])
    failed = total_blocks - successful
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)
    print(f"Total Blocks: {total_blocks}")
    print(f"Successful: {successful} ({successful/total_blocks*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total_blocks*100:.1f}%)")
    print(f"Duration: {(end_time-start_time).total_seconds()/60:.1f} minutes")
    print(f"\n📊 Full report: {output_file}")
    print("="*80)


if __name__ == "__main__":
    main()
