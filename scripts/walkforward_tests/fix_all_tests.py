"""Fix all test scripts by removing the corrupted retest tracking sections"""
import re

# List of files to fix (all except 46 which is working)
files_to_fix = [
    ('47_test_how.py', 'HOW', 'how'),
    ('48_test_lod.py', 'LOD', 'lod'),
    ('49_test_low.py', 'LOW', 'low'),
    ('66_test_us_settlement.py', 'USSettlement', 'us_settlement')
]

# Read the working HOD test as template
with open('46_test_hod.py', 'r') as f:
    hod_content = f.read()

for filename, class_name, block_name in files_to_fix:
    print(f"Fixing {filename}...")
    
    # Replace HOD-specific parts with appropriate names
    fixed_content = hod_content.replace('from src.detectors.building_blocks.price_levels.hod import HOD', 
                                       f'from src.detectors.building_blocks.price_levels.{block_name} import {class_name}')
    fixed_content = fixed_content.replace('block = HOD()', f'block = {class_name}()')
    fixed_content = fixed_content.replace('test_block_walkforward_v2(block, "hod", df)', 
                                         f'test_block_walkforward_v2(block, "{block_name}", df)')
    fixed_content = fixed_content.replace('Walk-Forward Test for Hod', f'Walk-Forward Test for {class_name}')
    
    # Write fixed file
    with open(filename, 'w') as f:
        f.write(fixed_content)
    
    print(f"  ✓ Fixed {filename}")

print("\n✅ All test scripts fixed!")
