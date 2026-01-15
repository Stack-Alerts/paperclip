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
    
    md.append("## Failed Blocks")
    md.append("")
    
    failed = [name for name, result in results.items() if result is None]
    if failed:
        md.append("| Block | Status |")
        md.append("|-------|--------|")
        for name in failed:
            md.append(f"| {name} | ❌ Test Failed |")
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
        
        try:
            result = test_building_block_registry(
                block_name=block_name,
                days=args.days,
                use_multicore=True
            )
            results[block_name] = result
            
            if result:
                coverage = result['coverage']['coverage_pct']
                signals = result['results']['total_results']
                print(f"\n✅ {block_name}: {coverage:.1f}% coverage, {signals:,} signals")
            else:
                print(f"\n❌ {block_name}: Test failed")
                
        except Exception as e:
            print(f"\n❌ {block_name}: Exception: {e}")
            results[block_name] = None
        
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
