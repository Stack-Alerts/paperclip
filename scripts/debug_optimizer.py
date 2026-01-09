#!/usr/bin/env python3
"""
Debug script to identify where optimizer hangs
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("="*80)
print("UNIVERSAL OPTIMIZER DEBUG")
print("="*80)

# Test 1: Import modules
print("\n1. Testing module imports...")
try:
    from src.strategies.universal_optimizer.modules.data_loader import load_btc_data, get_strategy_class
    from src.strategies.universal_optimizer.modules.file_operations import extract_blocks_from_strategy
    from src.strategies.universal_optimizer.modules.catalog import get_weight_presets_for_blocks
    from src.strategies.universal_optimizer.modules.data_classes import OptimizationConfig
    print("   ✅ All modules imported successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Extract blocks
print("\n2. Testing block extraction...")
try:
    blocks = extract_blocks_from_strategy('strategy_01_reversal_m_pattern')
    if blocks:
        print(f"   ✅ Extracted {len(blocks)} blocks:")
        for name in blocks.keys():
            print(f"      - {name}")
    else:
        print("   ❌ No blocks found")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Extraction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Load data
print("\n3. Testing data loading...")
try:
    warmup_df, test_df = load_btc_data(test_days=30, warmup_bars=1000)
    if warmup_df is not None:
        print(f"   ✅ Data loaded:")
        print(f"      Warmup: {len(warmup_df)} bars")
        print(f"      Test: {len(test_df)} bars")
    else:
        print("   ❌ Data loading failed")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Data load failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Build single config
print("\n4. Testing config creation...")
try:
    weight_presets = get_weight_presets_for_blocks(list(blocks.keys()))
    print(f"   ✅ Created {len(weight_presets)} weight presets")
    
    # Build one config
    config = OptimizationConfig(
        config_id=0,
        min_confluence=50,
        min_risk_reward=2.0,
        blocks=blocks,
        strategy_id='strategy_01_reversal_m_pattern',
        strategy_name='Test Strategy',
        side='SHORT'
    )
    print(f"   ✅ Config created: confluence={config.min_confluence}, rr={config.min_risk_reward}")
except Exception as e:
    print(f"   ❌ Config creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Load strategy class
print("\n5. Testing strategy class loading...")
try:
    strategy_class = get_strategy_class('strategy_01_reversal_m_pattern')
    print(f"   ✅ Strategy class loaded: {strategy_class.__name__}")
    
    # Check for required methods
    required_methods = ['_analyze_blocks', '_calculate_confluence']
    for method in required_methods:
        if hasattr(strategy_class, method):
            print(f"      ✓ Has method: {method}")
        else:
            print(f"      ✗ Missing method: {method}")
except Exception as e:
    print(f"   ❌ Strategy load failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Test MultiConfigSimulator creation
print("\n6. Testing MultiConfigSimulator creation...")
try:
    from src.strategies.universal_optimizer.modules.multi_config_simulator import MultiConfigSimulator
    
    configs = [config]  # Just one config for testing
    simulator = MultiConfigSimulator(configs)
    print(f"   ✅ Simulator created with {len(simulator.simulators)} simulator(s)")
except Exception as e:
    print(f"   ❌ Simulator creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Process one bar
print("\n7. Testing single bar processing...")
try:
    # Create a mock strategy instance
    class MockStrategy:
        def __init__(self):
            self.blocks = blocks
            self.detectors = {}
            
        def _analyze_blocks(self, df):
            # Return mock results
            return {
                'double_top': {'signal': 'BEARISH_BREAKDOWN', 'confidence': 80},
                'rsi_divergence': {'signal': 'BEARISH_DIVERGENCE', 'confidence': 75},
                'hod': {'signal': 'BELOW_HOD', 'confidence': 90},
                'asia_50': {'signal': 'BELOW_EQUILIBRIUM', 'confidence': 70},
                'session_time': {'signal': 'LONDON_OPEN', 'confidence': 100},
                'vwap': {'signal': 'BELOW_VWAP', 'confidence': 85}
            }
    
    mock_strategy = MockStrategy()
    
    # Get one bar from test data
    test_bar = test_df.iloc[100]
    history = test_df.iloc[:101]
    
    print(f"   Processing bar at index 100...")
    print(f"   Bar timestamp: {test_bar['timestamp']}")
    print(f"   Bar close: ${test_bar['close']:.2f}")
    
    simulator.process_bar(test_bar, mock_strategy, history)
    print(f"   ✅ Bar processed successfully")
    
    # Check if any trades were recorded
    results = simulator.get_all_results()
    if results:
        print(f"   Config 0: {results[0].total_trades} trades")
    
except Exception as e:
    print(f"   ❌ Bar processing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("✅ ALL TESTS PASSED!")
print("="*80)
print("\nOptimizer architecture is functional.")
print("Issue likely in:")
print("  - Strategy method binding in optimizer_core.py")
print("  - Building block initialization")
print("  - Analysis loop logic")