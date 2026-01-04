"""
Comprehensive Walkforward Test - All 67 Building Blocks
Runs individual test for each block and organizes reports properly
EXPERT MODE: Institutional-grade testing with proper report organization
"""
import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime


def ensure_directories():
    """Ensure all required directories exist"""
    output_dir = Path('data/reports/walkforward_tests/building_blocks')
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def run_individual_test(test_num, test_file, block_name, output_dir):
    """
    Run a single individual test script and move outputs to proper location
    
    Args:
        test_num: Test number (01, 02, etc.)
        test_file: Path to test script
        block_name: Block identifier (e.g., ema_20_50_cross)
        output_dir: Building blocks output directory
    """
    print("="*80)
    print(f"TEST {test_num}: {block_name}")
    print("="*80)
    print(f"Script: {test_file}")
    
    try:
        # Run the test (using venv)
        result = subprocess.run(
            f"source venv/bin/activate && python {test_file}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout per test
            executable='/bin/bash'
        )
        
        # Check for generated files in default location
        temp_json = Path(f'data/reports/walkforward_tests/walkforward_results_{block_name}.json')
        temp_csv = Path(f'data/reports/walkforward_tests/walkforward_results_{block_name}_signals_trades.csv')
        
        # Define target locations with proper naming
        target_json = output_dir / f'{test_num}_walkforward_results_{block_name}.json'
        target_csv = output_dir / f'{test_num}_walkforward_results_{block_name}_trades.csv'
        
        # Move files to proper location
        files_moved = []
        if temp_json.exists():
            shutil.move(str(temp_json), str(target_json))
            files_moved.append(str(target_json))
            print(f"✅ JSON report: {target_json.name}")
        else:
            print(f"⚠️  JSON report not found: {temp_json}")
        
        if temp_csv.exists():
            shutil.move(str(temp_csv), str(target_csv))
            files_moved.append(str(target_csv))
            print(f"✅ CSV report: {target_csv.name}")
        else:
            print(f"⚠️  CSV report not found: {temp_csv}")
        
        if len(files_moved) == 2:
            print(f"✅ Test {test_num} COMPLETE - Both reports generated")
            status = 'COMPLETE'
        elif len(files_moved) == 1:
            print(f"⚠️  Test {test_num} PARTIAL - Only 1 report generated")
            status = 'PARTIAL'
        else:
            print(f"❌ Test {test_num} FAILED - No reports generated")
            status = 'FAILED'
        
        return {
            'test_num': test_num,
            'block_name': block_name,
            'status': status,
            'files_generated': files_moved,
            'stdout_lines': len(result.stdout.split('\n')),
            'stderr_lines': len(result.stderr.split('\n'))
        }
        
    except subprocess.TimeoutExpired:
        print(f"❌ Test {test_num} TIMEOUT")
        return {
            'test_num': test_num,
            'block_name': block_name,
            'status': 'TIMEOUT',
            'error': 'Test exceeded 10 minute timeout'
        }
    except Exception as e:
        print(f"❌ Test {test_num} ERROR: {e}")
        return {
            'test_num': test_num,
            'block_name': block_name,
            'status': 'ERROR',
            'error': str(e)
        }


def move_aggregate_reports(output_dir):
    """Move aggregate reports to building_blocks directory"""
    print("\n" + "="*80)
    print("MOVING AGGREGATE REPORTS")
    print("="*80)
    
    aggregate_files = [
        'custom_metadata_results.json',
        'nonpattern_signal_results.json',
        'pattern_walkforward_detailed_results.json',
        'remaining_nonpattern_results.json'
    ]
    
    moved = []
    for filename in aggregate_files:
        source = Path('data/reports/walkforward_tests') / filename
        target = output_dir.parent / filename
        
        if source.exists():
            shutil.copy(str(source), str(target))
            moved.append(filename)
            print(f"✅ Moved: {filename}")
        else:
            print(f"⚠️  Not found: {filename}")
    
    return moved


def main():
    """Run all 67 individual building block tests"""
    
    print("="*80)
    print("🏗️  COMPREHENSIVE WALKFORWARD TEST - ALL 67 BUILDING BLOCKS")
    print("="*80)
    print(f"Start Time: {datetime.now()}")
    print()
    
    # Ensure output directory exists
    output_dir = ensure_directories()
    print(f"Output Directory: {output_dir}")
    print()
    
    # Define all 67 tests (in order)
    tests = [
        # EMA Tests (1-7)
        ('01', 'scripts/walkforward_tests/01_test_ema_20_50_cross.py', 'ema_20_50_cross'),
        ('02', 'scripts/walkforward_tests/02_test_ema_20_50_trend.py', 'ema_20_50_trend'),
        ('03', 'scripts/walkforward_tests/03_test_ema_50_vector.py', 'ema_50_vector'),
        ('04', 'scripts/walkforward_tests/04_test_ema_55_vector.py', 'ema_55_vector'),
        ('05', 'scripts/walkforward_tests/05_test_ema_200_trend.py', 'ema_200_trend'),
        ('06', 'scripts/walkforward_tests/06_test_ema_255_vector.py', 'ema_255_vector'),
        ('07', 'scripts/walkforward_tests/07_test_ema_800_vector.py', 'ema_800_vector'),
        
        # Technical Indicators (8-10)
        ('08', 'scripts/walkforward_tests/08_test_macd_signal.py', 'macd_signal'),
        ('09', 'scripts/walkforward_tests/09_test_rsi_divergence.py', 'rsi_divergence'),
        ('10', 'scripts/walkforward_tests/10_test_stochastic_rsi.py', 'stochastic_rsi'),
        
        # ICT/SMC Concepts (11-26)
        ('11', 'scripts/walkforward_tests/11_test_order_block.py', 'order_block'),
        ('12', 'scripts/walkforward_tests/12_test_fair_value_gap.py', 'fair_value_gap'),
        ('13', 'scripts/walkforward_tests/13_test_liquidity_sweep.py', 'liquidity_sweep'),
        ('14', 'scripts/walkforward_tests/14_test_breaker_block.py', 'breaker_block'),
        ('15', 'scripts/walkforward_tests/15_test_ichimoku_cloud.py', 'ichimoku_cloud'),
        ('16', 'scripts/walkforward_tests/16_test_adx.py', 'adx'),
        ('17', 'scripts/walkforward_tests/17_test_break_of_structure.py', 'break_of_structure'),
        ('18', 'scripts/walkforward_tests/18_test_market_structure_shift.py', 'market_structure_shift'),
        ('19', 'scripts/walkforward_tests/19_test_displacement.py', 'displacement'),
        ('20', 'scripts/walkforward_tests/20_test_inducement.py', 'inducement'),
        ('21', 'scripts/walkforward_tests/21_test_optimal_trade_entry.py', 'optimal_trade_entry'),
        ('22', 'scripts/walkforward_tests/22_test_swing_failure_pattern.py', 'swing_failure_pattern'),
        ('23', 'scripts/walkforward_tests/23_test_premium_discount.py', 'premium_discount'),
        ('24', 'scripts/walkforward_tests/24_test_change_of_character.py', 'change_of_character'),
        ('25', 'scripts/walkforward_tests/25_test_mitigation_block.py', 'mitigation_block'),
        ('26', 'scripts/walkforward_tests/26_test_balanced_price_range.py', 'balanced_price_range'),
        
        # Volume/Volatility (27-30)
        ('27', 'scripts/walkforward_tests/27_test_vwap.py', 'vwap'),
        ('28', 'scripts/walkforward_tests/28_test_atr.py', 'atr'),
        ('29', 'scripts/walkforward_tests/29_test_adr.py', 'adr'),
        ('30', 'scripts/walkforward_tests/30_test_bollinger_bands.py', 'bollinger_bands'),
        
        # Chart Patterns (31-45)
        ('31', 'scripts/walkforward_tests/31_test_double_top.py', 'double_top'),
        ('32', 'scripts/walkforward_tests/32_test_double_bottom.py', 'double_bottom'),
        ('33', 'scripts/walkforward_tests/33_test_triple_top.py', 'triple_top'),
        ('34', 'scripts/walkforward_tests/34_test_triple_bottom.py', 'triple_bottom'),
        ('35', 'scripts/walkforward_tests/35_test_head_and_shoulders.py', 'head_and_shoulders'),
        ('36', 'scripts/walkforward_tests/36_test_inverse_head_and_shoulders.py', 'inverse_head_and_shoulders'),
        ('37', 'scripts/walkforward_tests/37_test_cup_and_handle.py', 'cup_and_handle'),
        ('38', 'scripts/walkforward_tests/38_test_rounding_bottom.py', 'rounding_bottom'),
        ('39', 'scripts/walkforward_tests/39_test_flag_pattern.py', 'flag_pattern'),
        ('40', 'scripts/walkforward_tests/40_test_pennant_pattern.py', 'pennant_pattern'),
        ('41', 'scripts/walkforward_tests/41_test_symmetrical_triangle.py', 'symmetrical_triangle'),
        ('42', 'scripts/walkforward_tests/42_test_ascending_triangle.py', 'ascending_triangle'),
        ('43', 'scripts/walkforward_tests/43_test_descending_triangle.py', 'descending_triangle'),
        ('44', 'scripts/walkforward_tests/44_test_falling_wedge.py', 'falling_wedge'),
        ('45', 'scripts/walkforward_tests/45_test_rising_wedge.py', 'rising_wedge'),
        
        # Session/Time Patterns (46-50)
        ('46', 'scripts/walkforward_tests/46_test_hod.py', 'hod'),
        ('47', 'scripts/walkforward_tests/47_test_how.py', 'how'),
        ('48', 'scripts/walkforward_tests/48_test_lod.py', 'lod'),
        ('49', 'scripts/walkforward_tests/49_test_low.py', 'low'),
        ('50', 'scripts/walkforward_tests/50_test_asia_session_50_percent.py', 'asia_session_50_percent'),
        
        # Elliott Wave (51-52)
        ('51', 'scripts/walkforward_tests/51_test_elliott_wave_count.py', 'elliott_wave_count'),
        ('52', 'scripts/walkforward_tests/52_test_elliott_wave_oscillator.py', 'elliott_wave_oscillator'),
        
        # Wyckoff (53-55) - Note: 53 and 54 have multiple timeframes
        ('53', 'scripts/walkforward_tests/53_test_wyckoff_accumulation.py', 'wyckoff_accumulation'),
        ('53', 'scripts/walkforward_tests/53_test_wyckoff_accumulation_2hr.py', 'wyckoff_accumulation_2hr'),
        ('53', 'scripts/walkforward_tests/53_test_wyckoff_accumulation_4hr.py', 'wyckoff_accumulation_4hr'),
        ('54', 'scripts/walkforward_tests/54_test_wyckoff_distribution.py', 'wyckoff_distribution'),
        ('54', 'scripts/walkforward_tests/54_test_wyckoff_distribution_2hr.py', 'wyckoff_distribution_2hr'),
        ('54', 'scripts/walkforward_tests/54_test_wyckoff_distribution_4hr.py', 'wyckoff_distribution_4hr'),
        ('55', 'scripts/walkforward_tests/55_test_wyckoff_reaccumulation.py', 'wyckoff_reaccumulation'),
        
        # Advanced Concepts (56-67)
        ('56', 'scripts/walkforward_tests/56_test_fibonacci_retracements.py', 'fibonacci_retracements'),
        ('57', 'scripts/walkforward_tests/57_test_anchored_vwap.py', 'anchored_vwap'),
        ('58', 'scripts/walkforward_tests/58_test_ema_crossover.py', 'ema_crossover'),
        ('59', 'scripts/walkforward_tests/59_test_market_depth.py', 'market_depth'),
        ('60', 'scripts/walkforward_tests/60_test_order_flow_imbalance.py', 'order_flow_imbalance'),
        ('61', 'scripts/walkforward_tests/61_test_premium_discount_zones.py', 'premium_discount_zones'),
        ('62', 'scripts/walkforward_tests/62_test_range_liquidity.py', 'range_liquidity'),
        ('63', 'scripts/walkforward_tests/63_test_swing_points.py', 'swing_points'),
        ('64', 'scripts/walkforward_tests/64_test_kill_zones.py', 'kill_zones'),
        ('65', 'scripts/walkforward_tests/65_test_session_time.py', 'session_time'),
        ('66', 'scripts/walkforward_tests/66_test_us_settlement.py', 'us_settlement'),
        ('67', 'scripts/walkforward_tests/67_test_supply_demand_zones.py', 'supply_demand_zones'),
    ]
    
    print(f"Total Tests to Run: {len(tests)}")
    print()
    
    # Run all tests
    results = []
    for test_num, test_file, block_name in tests:
        result = run_individual_test(test_num, test_file, block_name, output_dir)
        results.append(result)
        print()
    
    # Move aggregate reports
    aggregate_moved = move_aggregate_reports(output_dir)
    
    # Generate summary
    print("\n" + "="*80)
    print("🎯 ALL TESTS COMPLETE")
    print("="*80)
    print(f"End Time: {datetime.now()}")
    
    # Count results
    complete = sum(1 for r in results if r['status'] == 'COMPLETE')
    partial = sum(1 for r in results if r['status'] == 'PARTIAL')
    failed = sum(1 for r in results if r['status'] in ['FAILED', 'ERROR', 'TIMEOUT'])
    
    print(f"\nTest Results:")
    print(f"  ✅ Complete (2 reports): {complete}/{len(tests)}")
    print(f"  ⚠️  Partial (1 report): {partial}/{len(tests)}")
    print(f"  ❌ Failed (0 reports): {failed}/{len(tests)}")
    print(f"\nAggregate Reports Moved: {len(aggregate_moved)}/4")
    
    # Save detailed summary
    summary = {
        'test_run': datetime.now().isoformat(),
        'total_tests': len(tests),
        'complete': complete,
        'partial': partial,
        'failed': failed,
        'aggregate_reports_moved': len(aggregate_moved),
        'output_directory': str(output_dir),
        'detailed_results': results
    }
    
    summary_file = 'all_blocks_walkforward_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✅ Summary saved: {summary_file}")
    
    # List any failures
    failures = [r for r in results if r['status'] in ['FAILED', 'ERROR', 'TIMEOUT']]
    if failures:
        print(f"\n⚠️  Failed Tests ({len(failures)}):")
        for f in failures:
            print(f"   - Test {f['test_num']}: {f['block_name']} ({f['status']})")
            if 'error' in f:
                print(f"     Error: {f['error']}")
    
    print("\n" + "="*80)
    print("Report files generated in:")
    print(f"  {output_dir}")
    print("="*80)


if __name__ == "__main__":
    main()
