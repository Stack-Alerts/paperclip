"""
Script to convert walkforward test scripts (51-67) to multicore processing
"""

import os
import re
from pathlib import Path

# Map of test number to (block_path, block_class, block_kwargs)
TEST_CONFIG = {
    51: ('elliott_wave.elliott_wave_count', 'ElliottWaveCount', '{}'),
    52: ('elliott_wave.elliott_wave_oscillator', 'ElliottWaveOscillator', '{}'),
    53: ('wyckoff.wyckoff_accumulation', 'WyckoffAccumulation', '{}'),
    54: ('wyckoff.wyckoff_distribution', 'WyckoffDistribution', '{}'),
    55: ('wyckoff.wyckoff_reaccumulation', 'WyckoffReaccumulation', '{}'),
    56: ('fibonacci.fibonacci_retracements', 'FibonacciRetracements', '{}'),
    57: ('vwap.anchored_vwap', 'AnchoredVWAP', '{}'),
    58: ('ema.ema_crossover', 'EMACrossover', '{}'),
    59: ('market_structure.market_depth', 'MarketDepth', '{}'),
    60: ('order_flow.order_flow_imbalance', 'OrderFlowImbalance', '{}'),
    61: ('price_action.premium_discount_zones', 'PremiumDiscountZones', '{}'),
    62: ('liquidity.range_liquidity', 'RangeLiquidity', '{}'),
    63: ('market_structure.swing_points', 'SwingPoints', '{}'),
    64: ('sessions.kill_zones', 'KillZones', '{}'),
    65: ('sessions.session_time', 'SessionTime', '{}'),
    66: ('sessions.us_settlement', 'USSettlement', '{}'),
    67: ('supply_demand.supply_demand_zones', 'SupplyDemandZones', '{}'),
}

MULTICORE_IMPORTS = """from multiprocessing import Pool, cpu_count
from functools import partial"""

PROCESS_CHUNK_FUNCTION = '''

def process_chunk(args):
    """
    Process a chunk of bars sequentially (multicore worker)
    Each worker gets a chunk to avoid massive serialization overhead
    Args: tuple of (chunk_indices, df_full_dict, block_class, block_kwargs)
    Returns: list of (result_dict, error_message or None) tuples
    """
    chunk_indices, df_full_dict, block_class, block_kwargs = args
    
    # Reconstruct full dataframe once per chunk
    df_full = pd.DataFrame(df_full_dict)
    
    # Create block instance once per chunk
    block = block_class(**block_kwargs)
    
    chunk_results = []
    
    for i in chunk_indices:
        try:
            # Create expanding window for this bar
            hist_df = df_full.iloc[:i+1]
            
            # Analyze
            result = block.analyze(hist_df)
            
            if result is not None and isinstance(result, dict):
                chunk_results.append((result, None))
            else:
                chunk_results.append((None, "Invalid result type"))
                
        except Exception as e:
            chunk_results.append((None, str(e)))
    
    return chunk_results
'''

def convert_file(test_num):
    """Convert a single test file to multicore"""
    
    if test_num not in TEST_CONFIG:
        print(f"  Warning: No config for test {test_num}")
        return False
    
    block_path, block_class, block_kwargs = TEST_CONFIG[test_num]
    
    file_path = Path(__file__).parent / 'walkforward_tests' / f'{test_num:02d}_test_{block_path.split(".")[-1]}.py'
    
    if not file_path.exists():
        print(f"  Warning: File not found: {file_path}")
        return False
    
    print(f"  Converting {file_path.name}...")
    
    # Read original file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already converted
    if 'multiprocessing' in content and 'process_chunk' in content:
        print(f"    Already multicore, skipping")
        return True
    
    # 1. Update docstring
    content = content.replace(
        'Auto-generated test script for individual block validation',
        'MULTICORE - Uses all CPU cores for parallel processing\nAuto-generated test script for individual block validation'
    )
    
    # 2. Add multicore imports after other imports
    import_section = re.search(r'(import json\n)', content)
    if import_section:
        content = content.replace(
            import_section.group(1),
            import_section.group(1) + MULTICORE_IMPORTS + '\n'
        )
    
    # 3. Add process_chunk function after load_btc_data
    load_btc_end = re.search(r'(    return df\[\[\'timestamp\', \'open\', \'high\', \'low\', \'close\', \'volume\'\]\]\n)\n', content)
    if load_btc_end:
        content = content.replace(
            load_btc_end.group(1),
            load_btc_end.group(1) + PROCESS_CHUNK_FUNCTION
        )
    
    # 4. Replace function signature
    content = content.replace(
        'def test_block_walkforward_v2(block, block_name: str, df_full: pd.DataFrame):',
        'def test_block_walkforward_v2(block_class, block_kwargs, block_name: str, df_full: pd.DataFrame):'
    )
    
    # 5. Replace function docstring note about expanding window
    content = content.replace(
        '    Key changes:\n    - Uses EXPANDING window (all data from start to current bar)\n    - Tests EVERY bar (sample_every=1)\n    - Accepts ALL valid results (including NEUTRAL, INSUFFICIENT_DATA)\n    - Separately tracks "active signals" vs all results\n    - Compatible with long-period indicators (EMA 200, 255, 800)',
        '    Key changes:\n    - Uses ALL CPU cores for parallel processing\n    - Much faster than sequential processing\n    - Expanding window (all data from start to current bar)\n    - Tests EVERY bar (sample_every=1)'
    )
    
    # 6. Update print statement
    content = content.replace(
        '    print(f"🔬 WALK-FORWARD TEST V2: {block_name}")',
        '    print(f"🔬 WALK-FORWARD TEST V2 (MULTICORE): {block_name}")'
    )
    
    # 7. Add number of cores section
    min_bars_section = re.search(r'(    # V2 Parameters.*\n    min_bars = 100.*\n    sample_every = 1.*\n)', content, re.DOTALL)
    if min_bars_section:
        new_section = '''    # V2 Parameters
    min_bars = 100
    sample_every = 1
    
    # Get number of CPU cores (leave 1 for system, max 31)
    num_cores = min(cpu_count() - 1, 31)
    print(f"🚀 Using {num_cores} CPU cores for parallel processing...")
    
    # Prepare chunks for parallel processing
    indices_to_process = list(range(min_bars, len(df_full), sample_every))
    total_bars = len(indices_to_process)
    
    # Split into chunks (one per core for optimal load balancing)
    chunk_size = max(1, total_bars // num_cores)
    chunks = []
    for i in range(0, total_bars, chunk_size):
        chunk_indices = indices_to_process[i:i+chunk_size]
        chunks.append(chunk_indices)
    
    print(f"\\n📦 Splitting {total_bars} bars into {len(chunks)} chunks (~{chunk_size} bars each)")
    print(f"🚀 Starting parallel processing with {num_cores} workers...")
    
    # Convert dataframe to dict once for all workers
    df_full_dict = df_full.to_dict('list')
    
    # Prepare work items (each worker gets a chunk)
    work_items = [(chunk, df_full_dict, block_class, block_kwargs) for chunk in chunks]
    
    # Process chunks in parallel
    with Pool(processes=num_cores) as pool:
        chunk_results = pool.map(process_chunk, work_items)
    
    # Flatten results from all chunks
'''
        content = content.replace(min_bars_section.group(1), new_section)
    
    # 8. Replace the old sequential processing loop
    old_loop = re.search(
        r'    results = \[\]\n    errors = 0\n    error_messages = \[\].*?'
        r'                break\n',
        content,
        re.DOTALL
    )
    if old_loop:
        new_processing = '''    results = []
    errors = 0
    error_messages = []
    
    for chunk_result_list in chunk_results:
        for result, error_msg in chunk_result_list:
            if result is not None:
                results.append(result)
            else:
                errors += 1
                if len(error_messages) < 3:
                    error_messages.append(error_msg)
    
    print(f"✅ Parallel processing complete!")
'''
        content = content.replace(old_loop.group(0), new_processing)
    
    # 9. Update results section print
    content = content.replace(
        '    print(f"\\n📊 RESULTS (V2 Methodology):',
        '    print(f"\\n📊 RESULTS (V2 Methodology - Multicore):'
    )
    
    # 10. Update main section - pass class and kwargs
    main_section = re.search(
        r'if __name__ == "__main__":\n'
        r'    from src\.detectors\.building_blocks\.([\w.]+) import (\w+)\n'
        r'    \n'
        r'    print\("Loading 180 days of BTC 15min data\.\.\."\)\n'
        r'    df = load_btc_data\(days=180\)\n'
        r'    \n'
        r'    if df is not None and len\(df\) > 0:\n'
        r'        block = (\w+)\(\)\n'
        r'        test_block_walkforward_v2\(block, "(\w+)", df\)',
        content
    )
    
    if main_section:
        import_path = main_section.group(1)
        class_name = main_section.group(2)
        block_name = main_section.group(4)
        
        new_main = f'''if __name__ == "__main__":
    from src.detectors.building_blocks.{import_path} import {class_name}
    
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    
    if df is not None and len(df) > 0:
        # Pass class and kwargs instead of instance (for multiprocessing)
        test_block_walkforward_v2({class_name}, {{}}, "{block_name}", df)'''
        
        content = content.replace(main_section.group(0), new_main)
    
    # Write converted file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"    ✅ Converted successfully")
    return True


if __name__ == "__main__":
    print("Converting walkforward test scripts to multicore...")
    print("="*80)
    
    success_count = 0
    for test_num in sorted(TEST_CONFIG.keys()):
        if convert_file(test_num):
            success_count += 1
    
    print("="*80)
    print(f"✅ Conversion complete: {success_count}/{len(TEST_CONFIG)} files converted")
