#!/usr/bin/env python3
"""
Debug TP Mode Configuration Issue

This script demonstrates how to use the institutional-grade debugger
to diagnose why TP mode changes aren't affecting test results.

Usage:
    python scripts/debug_tp_mode.py

Output:
    - Console: Real-time debug logs
    - logs/tp_mode_debug.log: Full debug log
    - reports/tp_mode_audit.txt: Comprehensive audit report
    - reports/tp_mode_audit.json: JSON data for analysis

Author: BTC_Engine_v3
Date: 2026-01-11
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.debugger_logger import ConfigDebugger, DebugLevel
import yaml
import json


def debug_optimizer_config():
    """Debug LOD Rejection strategy configuration to find TP mode issue"""
    
    print("\n" + "="*80)
    print("DEBUGGING TP MODE CONFIGURATION")
    print("="*80 + "\n")
    
    # Initialize debugger
    debugger = ConfigDebugger(
        name="TPModeDebugger",
        level=DebugLevel.MEDIUM,  # Show config reads and decisions
        log_file=Path("logs/tp_mode_debug.log"),
        console_output=True
    )
    
    print("Step 1: Loading strategy configuration from Strategy Builder")
    print("-" * 80)
    
    # Load the strategy JSON file (from Strategy Builder)
    strategy_json = project_root / "data/strategies/unpublished/strategy_001_lod_rejection.json"
    
    if not strategy_json.exists():
        print(f"❌ Strategy file not found: {strategy_json}")
        print("\nSearching for strategy file...")
        
        # Search all strategy folders
        for folder in ["drafts", "unpublished", "published"]:
            folder_path = project_root / f"data/strategies/{folder}"
            if folder_path.exists():
                strategy_files = list(folder_path.glob("strategy_001_*.json"))
                if strategy_files:
                    strategy_json = strategy_files[0]
                    print(f"✓ Found: {strategy_json}")
                    break
    
    if not strategy_json.exists():
        print("❌ No strategy file found. Please create strategy first.")
        return
    
    # Load strategy config
    with open(strategy_json) as f:
        strategy_config = json.load(f)
    
    # Register with debugger
    debugger.register_config_source(
        config_dict=strategy_config,
        source=str(strategy_json),
        source_type="strategy_json"
    )
    
    # Check tp_mode in strategy config
    tp_mode_from_strategy = strategy_config.get('tp_mode', 'NOT_FOUND')
    print(f"\n✓ Strategy Config Loaded")
    print(f"  tp_mode in strategy.json: {tp_mode_from_strategy}")
    
    print("\nStep 2: Loading optimizer configuration (YAML)")
    print("-" * 80)
    
    # Load the optimizer YAML config
    optimizer_yaml = project_root / "config/optimizer_001_lod_rejection.yaml"
    
    if not optimizer_yaml.exists():
        print(f"❌ Optimizer config not found: {optimizer_yaml}")
        print("\nPlease generate files using Strategy Builder first.")
        return
    
    with open(optimizer_yaml) as f:
        optimizer_config = yaml.safe_load(f)
    
    # Register with debugger
    debugger.register_config_source(
        config_dict=optimizer_config.get('backtest', {}),
        source=str(optimizer_yaml),
        source_type="optimizer_yaml"
    )
    
    # Check tp_mode in optimizer config
    tp_mode_from_yaml = optimizer_config.get('backtest', {}).get('tp_mode', 'NOT_FOUND')
    print(f"\n✓ Optimizer Config Loaded")
    print(f"  tp_mode in optimizer YAML: {tp_mode_from_yaml}")
    
    print("\nStep 3: Validating Configuration Chain")
    print("-" * 80)
    
    # Validate the chain
    if tp_mode_from_strategy == tp_mode_from_yaml:
        print(f"✓ TP MODE MATCHES: {tp_mode_from_strategy}")
    else:
        print(f"❌ TP MODE MISMATCH DETECTED!")
        print(f"   Strategy JSON: {tp_mode_from_strategy}")
        print(f"   Optimizer YAML: {tp_mode_from_yaml}")
        print(f"\n⚠️  THIS IS THE ROOT CAUSE!")
        print(f"   The strategy config has tp_mode={tp_mode_from_strategy}")
        print(f"   But the optimizer YAML has tp_mode={tp_mode_from_yaml}")
        
        # Log the mismatch
        debugger.validate_config_usage(
            key='tp_mode',
            expected_value=tp_mode_from_strategy,
            actual_value=tp_mode_from_yaml,
            location="optimizer_yaml vs strategy_json"
        )
    
    print("\nStep 4: Checking Test Flags")
    print("-" * 80)
    
    # Check for test flags that might override tp_mode
    test_tp_modes = optimizer_config.get('backtest', {}).get('test_tp_modes', 'NOT_FOUND')
    quick_test = optimizer_config.get('backtest', {}).get('quick_test', 'NOT_FOUND')
    
    print(f"  test_tp_modes: {test_tp_modes}")
    print(f"  quick_test: {quick_test}")
    
    if test_tp_modes == False:
        print("\n⚠️  test_tp_modes = False")
        print("   This forces PERCENTAGE mode regardless of tp_mode setting!")
        print("   This is why FIBONACCI mode isn't working!")
    
    print("\nStep 5: Generating Audit Report")
    print("-" * 80)
    
    # Generate comprehensive report
    report = debugger.generate_report()
    
    # Save reports
    report_dir = project_root / "reports"
    report_dir.mkdir(exist_ok=True)
    
    debugger.save_report(report_dir / "tp_mode_audit.txt")
    debugger.export_json(report_dir / "tp_mode_audit.json")
    
    print(f"\n✓ Audit reports saved:")
    print(f"  - {report_dir / 'tp_mode_audit.txt'}")
    print(f"  - {report_dir / 'tp_mode_audit.json'}")
    
    print("\nStep 6: Summary")
    print("=" * 80)
    
    if debugger.mismatch_registry:
        print(f"\n❌ FOUND {len(debugger.mismatch_registry)} CONFIGURATION MISMATCH(ES)!\n")
        for mismatch in debugger.mismatch_registry:
            print(f"  Key: {mismatch['key']}")
            print(f"  Expected: {mismatch['expected']}")
            print(f"  Actual: {mismatch['actual']}")
            print(f"  Location: {mismatch['location']}\n")
        
        print("RECOMMENDATION:")
        print("1. Fix the mismatch in the configuration files")
        print("2. Regenerate optimizer YAML from Strategy Builder")
        print("3. Ensure test_tp_modes is not set to False")
        print("4. Run test again")
    else:
        print("\n✓ No configuration mismatches found")
        print("\nIf tests still show same results, the issue is likely:")
        print("1. test_tp_modes=False forcing PERCENTAGE mode")
        print("2. TP calculation not using tp_mode parameter")
        print("3. Hardcoded TP mode somewhere in the code")
        
        print("\nNEXT STEPS:")
        print("1. Check universal_optimizer_v2.py for test_tp_modes flag")
        print("2. Check dynamic_tp_calculator.py for tp_mode usage")
        print("3. Add debugger to optimizer run to track tp_mode at runtime")
    
    print("\n" + "=" * 80)
    print("DEBUG SESSION COMPLETE")
    print("=" * 80 + "\n")
    
    return debugger


if __name__ == "__main__":
    try:
        debugger = debug_optimizer_config()
        
        print("\nFor detailed analysis, see:")
        print(f"  - logs/tp_mode_debug.log")
        print(f"  - reports/tp_mode_audit.txt")
        print(f"  - reports/tp_mode_audit.json\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
