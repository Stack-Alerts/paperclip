"""
EXPERT MODE: Debug why Reaccumulation SPRING isn't detecting
"""
import pandas as pd
import sys
sys.path.insert(0, 'src')

from detectors.building_blocks.wyckoff.wyckoff_reaccumulation import WyckoffReaccumulation

# Load test results to find bars with uptrend + range
df_results = pd.read_csv('data/reports/registry_tests/test_wyckoff_reaccumulation_signals.csv')

# Find a sample bar with uptrend + range
sample_bars = df_results[(df_results['in_uptrend'] == True) & (df_results['in_range'] == True)]
print(f"Found {len(sample_bars)} bars with uptrend + range")

if len(sample_bars) > 0:
    # Get first occurrence
    sample_idx = sample_bars.index[500]  # Pick middle one
    print(f"\nAnalyzing bar {sample_idx}")
    print(f"Signal: {df_results.iloc[sample_idx]['signal']}")
    print(f"Support level: {df_results.iloc[sample_idx]['support_level']}")
    print(f"Resistance level: {df_results.iloc[sample_idx]['resistance_level']}")
    
    # Now manually test detect_spring on a range of data around this bar
    # Load actual price data to test
    import sys
    sys.path.insert(0, 'tests/building_blocks_registry_envoked')
    from registry_test_library import RegistryTestRunner
    
    runner = RegistryTestRunner('wyckoff_reaccumulation')
    df_price = runner.load_data(days=180)
    
    # Test on a window
    test_window = df_price.iloc[:sample_idx+1]
    
    # Create detector
    detector = WyckoffReaccumulation()
    
    # Get support from range detection
    in_range, range_conf, resistance, support = detector.detect_range(test_window)
    
    print(f"\nRange detection on this window:")
    print(f"  in_range: {in_range}")
    print(f"  support: {support}")
    print(f"  resistance: {resistance}")
    
    if support > 0:
        # Test spring detection
        spring, spring_conf = detector.detect_spring(test_window, support)
        print(f"\nSpring detection with support={support}:")
        print(f"  spring: {spring}")
        print(f"  confidence: {spring_conf}")
        
        # Manual check - look for breakdown and recovery
        scan_window = min(20, len(test_window) - 3)
        print(f"\nManual scan (last {scan_window} bars):")
        
        for i in range(len(test_window) - scan_window, len(test_window)):
            if i < 5:
                continue
            window_start = max(0, i - 5)
            window = test_window.iloc[window_start:i+1]
            
            breakdown_threshold = support * 0.99
            broke_support = window['low'].min() < breakdown_threshold
            final_close = window['close'].iloc[-1]
            recovered = final_close > support * 0.998
            
            if broke_support:
                print(f"  Bar {i}: BREAKDOWN (low={window['low'].min():.2f} < {breakdown_threshold:.2f}), recovered={recovered}")
