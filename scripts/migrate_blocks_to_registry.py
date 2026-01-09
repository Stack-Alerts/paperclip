"""
Migrate Building Blocks to Registry Pattern
============================================

This script automatically adds @register_block decorators to existing
building blocks based on the comprehensive signal audit results.

Usage:
    python scripts/migrate_blocks_to_registry.py [--block BLOCK_NAME] [--dry-run]
    
Examples:
    # Migrate all blocks
    python scripts/migrate_blocks_to_registry.py
    
    # Migrate specific block
    python scripts/migrate_blocks_to_registry.py --block swing_points
    
    # Dry run (preview changes)
    python scripts/migrate_blocks_to_registry.py --dry-run

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
import argparse
from typing import Dict, List, Any
import json


# Signal catalog from audit - maps block name to actual signals found
BLOCK_SIGNALS = {
    # Based on comprehensive_signal_audit.py results
    'swing_points': {
        'signals': ['SWING_HIGH_DETECTED', 'SWING_LOW_DETECTED', 'MINOR_SWING_HIGH_DETECTED', 
                   'MINOR_SWING_LOW_DETECTED', 'MAJOR_SWING_HIGH_DETECTED', 'MAJOR_SWING_LOW_DETECTED',
                   'NO_SWINGS', 'INSUFFICIENT_DATA', 'ERROR'],
        'category': 'MARKET_STRUCTURE',
        'class_name': 'SwingPoints',
        'weight': 15
    },
    'premium_discount_zones': {
        'signals': ['PRICE_IN_PREMIUM', 'PRICE_IN_DISCOUNT', 'AT_EQUILIBRIUM', 
                   'NO_ZONE', 'INSUFFICIENT_DATA', 'ERROR'],
        'category': 'MARKET_STRUCTURE',
        'class_name': 'PremiumDiscountZones',
        'weight': 14
    },
    'ema_200_trend': {
        'signals': ['BULLISH', 'BEARISH', 'NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR'],
        'category': 'MOVING_AVERAGES',
        'class_name': 'EMA200Trend',
        'weight': 12
    },
    'ema_20_50_trend': {
        'signals': ['BULLISH', 'BEARISH', 'NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR'],
        'category': 'MOVING_AVERAGES',
        'class_name': 'EMA2050Trend',
        'weight': 12
    },
    'vwap': {
        'signals': ['BULLISH', 'BEARISH', 'NEUTRAL', 'ERROR'],
        'category': 'INSTITUTIONAL',
        'class_name': 'VWAP',
        'weight': 15
    },
    'session_time': {
        'signals': ['MODERATE_SESSION', 'HIGH_VOLUME_SESSION', 'LOW_VOLUME_SESSION', 
                   'SESSION_OPEN', 'SESSION_CLOSE', 'NO_SIGNAL', 'ERROR'],
        'category': 'SESSIONS',
        'class_name': 'SessionTime',
        'weight': 15
    },
    'kill_zones': {
        'signals': ['ACTIVE', 'LONDON_KZ', 'NY_AM_KZ', 'NY_PM_KZ', 'ASIAN_KZ', 
                   'INACTIVE', 'NO_SIGNAL', 'ERROR'],
        'category': 'SESSIONS',
        'class_name': 'KillZones',
        'weight': 16
    },
    'hod': {
        'signals': ['BEARISH', 'BULLISH', 'NEUTRAL', 'HOD_REJECTION', 'AT_HOD', 
                   'BELOW_HOD', 'ABOVE_HOD', 'ERROR'],
        'category': 'PRICE_LEVELS',
        'class_name': 'HOD',
        'weight': 20
    },
    'lod': {
        'signals': ['BULLISH', 'BEARISH', 'NEUTRAL', 'LOD_BOUNCE', 'AT_LOD',
                   'ABOVE_LOD', 'BELOW_LOD', 'ERROR'],
        'category': 'PRICE_LEVELS',
        'class_name': 'LOD',
        'weight': 20
    },
    'adr': {
        'signals': ['CALM', 'VOLATILE', 'NEAR_ADR', 'ABOVE_ADR', 'BELOW_ADR', 
                   'WITHIN_ADR', 'ERROR'],
        'category': 'VOLATILITY',
        'class_name': 'ADR',
        'weight': 8
    },
    'rsi_divergence': {
        'signals': ['BEARISH_DIVERGENCE', 'BULLISH_DIVERGENCE', 'OVERBOUGHT', 
                   'OVERSOLD', 'NEUTRAL', 'ERROR'],
        'category': 'OSCILLATORS',
        'class_name': 'RSIDivergence',
        'weight': 25
    },
    'double_top': {
        'signals': ['BEARISH_BREAKDOWN', 'PATTERN_FORMING', 'NO_PATTERN', 
                   'INSUFFICIENT_DATA', 'ERROR'],
        'category': 'PATTERNS',
        'class_name': 'DoubleTopPattern',
        'weight': 30
    },
}


def generate_signal_tiers(signals: List[str], weight: int) -> Dict[str, Any]:
    """
    Generate signal tier configuration based on signals
    
    Args:
        signals: List of valid signals
        weight: Default weight for block
        
    Returns:
        Signal tiers dictionary
    """
    tiers = {}
    
    # Standard signals get 0 points
    for signal in ['ERROR', 'INSUFFICIENT_DATA', 'NO_SIGNAL', 'NO_PATTERN', 'NO_SWINGS', 'NO_ZONE']:
        if signal in signals:
            tiers[signal] = {'points': 0}
    
    # Active signals get scaled points
    active_signals = [s for s in signals if s not in tiers]
    
    for signal in active_signals:
        # Determine if this is a weak signal (NEUTRAL, etc.)
        if 'NEUTRAL' in signal or 'CALM' in signal or 'MODERATE' in signal:
            tiers[signal] = {'max_points': weight // 2, 'formula': 'scaled'}
        else:
            tiers[signal] = {'base_points': weight, 'formula': 'scaled'}
    
    return tiers


def generate_decorator(block_name: str, metadata: Dict[str, Any]) -> str:
    """Generate @register_block decorator code"""
    
    signal_tiers = generate_signal_tiers(metadata['signals'], metadata['weight'])
    
    decorator = f"""@register_block(
    name='{block_name}',
    category='{metadata['category']}',
    class_name='{metadata['class_name']}',
    default_weight={metadata['weight']},
    valid_signals={metadata['signals']},
    signal_tiers={json.dumps(signal_tiers, indent=8).replace('"', "'")}
)"""
    
    return decorator


def migrate_block_file(block_name: str, dry_run: bool = False) -> bool:
    """
    Add @register_block decorator to a building block file
    
    Args:
        block_name: Name of block to migrate
        dry_run: If True, only print changes without writing
        
    Returns:
        True if successful, False if failed
    """
    if block_name not in BLOCK_SIGNALS:
        print(f"❌ No metadata for block '{block_name}'")
        return False
    
    metadata = BLOCK_SIGNALS[block_name]
    
    # Find file
    category = metadata['category'].lower().replace('_', '')
    category_map = {
        'marketstructure': 'market_structure',
        'movinvaverages': 'moving_averages',
        'pricelevels': 'price_levels',
        'smcict': 'smc_ict',
    }
    category_dir = category_map.get(category, category if category != 'marketstructure' else 'market_structure')
    
    # Try multiple possible locations
    possible_paths = [
        Path(f'src/detectors/building_blocks/{category_dir}/{block_name}.py'),
        Path(f'src/detectors/building_blocks/{metadata["category"].lower()}/{block_name}.py'),
    ]
    
    file_path = None
    for path in possible_paths:
        if path.exists():
            file_path = path
            break
    
    if not file_path:
        print(f"❌ File not found for '{block_name}' (tried {[str(p) for p in possible_paths]})")
        return False
    
    print(f"\n📦 Migrating: {block_name}")
    print(f"   File: {file_path}")
    
    # Read file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already migrated
    if '@register_block' in content:
        print(f"   ℹ️  Already migrated (has @register_block)")
        return True
    
    # Generate decorator
    decorator = generate_decorator(block_name, metadata)
    
    # Find class definition
    class_pattern = rf'class {metadata["class_name"]}[:\(]'
    match = re.search(class_pattern, content)
    
    if not match:
        print(f"   ❌ Could not find class '{metadata['class_name']}'")
        return False
    
    # Add import at top if not present
    if 'from src.detectors.building_blocks.registry import register_block' not in content:
        # Find first import or module docstring
        import_pos = content.find('import ')
        if import_pos == -1:
            import_pos = content.find('"""')
            if import_pos != -1:
                # After docstring
                end_doc = content.find('"""', import_pos + 3)
                import_pos = end_doc + 3
        
        import_line = '\nfrom src.detectors.building_blocks.registry import register_block\n'
        content = content[:import_pos] + import_line + content[import_pos:]
    
    # Add decorator before class
    class_start = content.find(match.group())
    
    # Find start of line for proper indentation
    line_start = content.rfind('\n', 0, class_start) + 1
    
    # Insert decorator
    new_content = (
        content[:line_start] +
        decorator + '\n' +
        content[line_start:]
    )
    
    if dry_run:
        print(f"   🔍 DRY RUN - Would add:")
        print(f"   {decorator}")
        return True
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"   ✅ Migrated successfully")
    return True


def main():
    parser = argparse.ArgumentParser(description='Migrate building blocks to registry pattern')
    parser.add_argument('--block', help='Migrate specific block only')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    
    args = parser.parse_args()
    
    print("="*80)
    print("BUILDING BLOCK REGISTRY MIGRATION")
    print("="*80)
    
    if args.block:
        # Migrate single block
        blocks_to_migrate = [args.block]
    else:
        # Migrate all blocks
        blocks_to_migrate = list(BLOCK_SIGNALS.keys())
    
    print(f"\nMigrating {len(blocks_to_migrate)} blocks...")
    if args.dry_run:
        print("(DRY RUN MODE - no files will be modified)\n")
    
    successes = 0
    failures = 0
    
    for block_name in blocks_to_migrate:
        if migrate_block_file(block_name, dry_run=args.dry_run):
            successes += 1
        else:
            failures += 1
    
    print("\n" + "="*80)
    print("MIGRATION COMPLETE")
    print("="*80)
    print(f"\n✅ Successful: {successes}")
    print(f"❌ Failed: {failures}")
    
    if not args.dry_run and successes > 0:
        print(f"\n📝 Next steps:")
        print(f"   1. Test: python -c \"from src.detectors.building_blocks.registry import BlockRegistry; BlockRegistry.print_summary()\"")
        print(f"   2. Validate: python scripts/validate_registry.py")
        print(f"   3. Commit changes")
    
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())