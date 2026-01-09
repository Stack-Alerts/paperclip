"""
Fix Import Statements in Migrated Building Blocks
==================================================

The migration script accidentally broke import statements by inserting
the registry import in the middle of a 'from typing' import.

This script fixes all affected files.

Usage:
    python scripts/fix_migrated_imports.py

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re


# Files that were migrated
MIGRATED_FILES = [
    'src/detectors/building_blocks/market_structure/premium_discount_zones.py',
    'src/detectors/building_blocks/moving_averages/ema_200_trend.py',
    'src/detectors/building_blocks/moving_averages/ema_20_50_trend.py',
    'src/detectors/building_blocks/institutional/vwap.py',
    'src/detectors/building_blocks/sessions/session_time.py',
    'src/detectors/building_blocks/sessions/kill_zones.py',
    'src/detectors/building_blocks/price_levels/hod.py',
    'src/detectors/building_blocks/price_levels/lod.py',
    'src/detectors/building_blocks/volatility/adr.py',
    'src/detectors/building_blocks/oscillators/rsi_divergence.py',
    'src/detectors/building_blocks/patterns/double_top.py',
]


def fix_import_statement(file_path: Path) -> bool:
    """
    Fix broken import statement in a file
    
    Pattern we're fixing:
    from typing 
    from src.detectors.building_blocks.registry import register_block
    import Dict, Any, List
    
    Should be:
    from typing import Dict, Any, List
    
    from src.detectors.building_blocks.registry import register_block
    
    Returns:
        True if file was fixed, False if no changes needed
    """
    if not file_path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already fixed
    if 'from typing import' in content and 'from typing \n' not in content:
        print(f"  ✅ Already fixed: {file_path.name}")
        return False
    
    # Pattern: from typing \nfrom registry...\nimport X, Y, Z
    pattern = r'from typing\s*\nfrom src\.detectors\.building_blocks\.registry import register_block\s*\nimport ([^\n]+)'
    
    def replace_imports(match):
        imports_list = match.group(1).strip()
        return f'from typing import {imports_list}\n\nfrom src.detectors.building_blocks.registry import register_block'
    
    new_content = re.sub(pattern, replace_imports, content)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"  ✅ Fixed: {file_path.name}")
        return True
    else:
        print(f"  ℹ️  No changes: {file_path.name}")
        return False


def main():
    print("="*80)
    print("FIXING MIGRATED BLOCK IMPORTS")
    print("="*80)
    print()
    
    fixed_count = 0
    skipped_count = 0
    
    for file_str in MIGRATED_FILES:
        file_path = Path(file_str)
        if fix_import_statement(file_path):
            fixed_count += 1
        else:
            skipped_count += 1
    
    print()
    print("="*80)
    print("IMPORT FIX COMPLETE")
    print("="*80)
    print(f"\n✅ Fixed: {fixed_count}")
    print(f"ℹ️  Skipped: {skipped_count}")
    print()
    
    return 0 if fixed_count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())