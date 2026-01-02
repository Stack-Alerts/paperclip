"""
Comprehensive Walkforward Test - All 67 Building Blocks
Runs appropriate test for each category systematically
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime

def run_phase(phase_num, phase_name, command, output_file):
    """Run a single test phase"""
    print("="*80)
    print(f"PHASE {phase_num}: {phase_name}")
    print("="*80)
    print(f"Command: {command}")
    print(f"Output: {output_file}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout per phase
        )
        
        print(f"✅ Phase {phase_num} complete")
        return {
            'phase': phase_num,
            'name': phase_name,
            'status': 'COMPLETE',
            'output_file': output_file,
            'stdout_lines': len(result.stdout.split('\n')),
            'stderr_lines': len(result.stderr.split('\n'))
        }
    except Exception as e:
        print(f"❌ Phase {phase_num} error: {e}")
        return {
            'phase': phase_num,
            'name': phase_name,
            'status': 'ERROR',
            'error': str(e)
        }

def main():
    """Run all 9 phases of testing"""
    
    print("="*80)
    print("🏗️ COMPREHENSIVE WALKFORWARD TEST - ALL 67 BLOCKS")
    print("="*80)
    print(f"Start Time: {datetime.now()}")
    print()
    
    phases = [
        (1, "Pattern Blocks (15)", 
         "python scripts/walkforward_patterns_detailed_parallel.py",
         "pattern_walkforward_detailed_results.json"),
        
        (2, "Moving Average Signals (6)",
         "python scripts/batch_test_nonpattern_signals.py",
         "moving_average_results.json"),
        
        (3, "ICT/SMC Advanced Signals (10)",
         "python scripts/batch_test_advanced_signals_parallel.py",
         "advanced_signal_results.json"),
        
        (4, "Metadata Blocks (16)",
         "python scripts/validate_metadata_blocks.py",
         "metadata_validation_results.json"),
        
        (5, "Custom/Remaining Blocks",
         "python scripts/batch_test_custom_metadata_parallel.py",
         "custom_metadata_results.json"),
        
        (6, "All Remaining Non-Pattern Signals",
         "python scripts/batch_test_remaining_nonpatterns.py",
         "remaining_nonpattern_results.json"),
    ]
    
    results = []
    
    for phase in phases:
        result = run_phase(*phase)
        results.append(result)
        print()
    
    # Save summary
    summary = {
        'test_run': datetime.now().isoformat(),
        'total_phases': len(phases),
        'results': results
    }
    
    with open('all_blocks_walkforward_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("="*80)
    print("🎯 ALL TESTS COMPLETE")
    print("="*80)
    print(f"End Time: {datetime.now()}")
    print(f"Summary saved: all_blocks_walkforward_summary.json")
    
    # Print completion status
    completed = sum(1 for r in results if r['status'] == 'COMPLETE')
    print(f"\nPhases Completed: {completed}/{len(phases)}")
    
    for r in results:
        status_icon = "✅" if r['status'] == 'COMPLETE' else "❌"
        print(f"{status_icon} Phase {r['phase']}: {r['name']}")

if __name__ == "__main__":
    main()
