"""
Comprehensive Building Block Migration to Registry
===================================================

Automatically discovers ALL building blocks, extracts their metadata,
and migrates them to the registry pattern.

This is the complete 80-block migration solution.

Usage:
    python scripts/migrate_all_blocks_to_registry.py [--dry-run]

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
import argparse
import importlib
import inspect
from typing import Dict, List, Any
import json


def discover_all_blocks() -> Dict[str, Dict[str, Any]]:
    """
    Auto-discover all building blocks from file system
    
    Returns:
        Dictionary mapping block_name -> metadata
    """
    blocks = {}
    base_path = Path('src/detectors/building_blocks')
    
    # Category mappings
    categories = {
        'patterns': 'PATTERNS',
        'oscillators': 'OSCILLATORS',
        'price_levels': 'PRICE_LEVELS',
        'sessions': 'SESSIONS',
        'moving_averages': 'MOVING_AVERAGES',
        'market_structure': 'MARKET_STRUCTURE',
        'volatility': 'VOLATILITY',
        'institutional': 'INSTITUTIONAL',
        'smc_ict': 'SMC_ICT',
        'price_action': 'PRICE_ACTION',
        'fibonacci': 'FIBONACCI',
        'elliott_wave': 'ELLIOTT_WAVE',
        'wyckoff': 'WYCKOFF',
        'supply_demand': 'SUPPLY_DEMAND',
        'trend': 'TREND',
        'signals': 'SIGNALS',
        'risk_management': 'RISK_MANAGEMENT',
    }
    
    # Default weights by category
    default_weights = {
        'PATTERNS': 30,
        'OSCILLATORS': 25,
        'PRICE_LEVELS': 20,
        'SESSIONS': 15,
        'MOVING_AVERAGES': 12,
        'MARKET_STRUCTURE': 15,
        'VOLATILITY': 10,
        'INSTITUTIONAL': 15,
        'SMC_ICT': 20,
        'PRICE_ACTION': 25,
        'FIBONACCI': 18,
        'ELLIOTT_WAVE': 22,
        'WYCKOFF': 28,
        'SUPPLY_DEMAND': 24,
        'TREND': 16,
        'SIGNALS': 20,
        'RISK_MANAGEMENT': 8,
    }
    
    for category_dir, category_name in categories.items():
        category_path = base_path / category_dir
        if not category_path.exists():
            continue
        
        for py_file in category_path.glob('*.py'):
            if py_file.name.startswith('_') or py_file.name == 'registry.py':
                continue
            
            block_name = py_file.stem
            
            # Try to import and extract class name
            module_path = f'src.detectors.building_blocks.{category_dir}.{block_name}'
            class_name = None
            valid_signals = ['BULLISH', 'BEARISH', 'NEUTRAL', 'ERROR', 'INSUFFICIENT_DATA']
            
            try:
                # Read file to extract class name
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Find class definition
                class_match = re.search(r'class\s+(\w+)[\(:]', content)
                if class_match:
                    class_name = class_match.group(1)
                
                # Try to extract signals from docstring or code
                # Look for common signal patterns
                signal_patterns = [
                    r"'([A-Z_]+)'",  # Single quotes
                    r'"([A-Z_]+)"',  # Double quotes
                ]
                
                found_signals = set()
                for pattern in signal_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Filter for likely signal names
                        if len(match) > 3 and match.isupper() and '_' in match:
                            if any(word in match for word in ['BULLISH', 'BEARISH', 'NEUTRAL', 'DETECTED', 'SIGNAL', 'PATTERN', 'CROSS', 'BREAK', 'ABOVE', 'BELOW', 'HIGH', 'LOW', 'ACTIVE', 'INACTIVE']):
                                found_signals.add(match)
                
                if found_signals:
                    valid_signals = sorted(list(found_signals))
                    # Ensure ERROR and INSUFFICIENT_DATA are included
                    if 'ERROR' not in valid_signals:
                        valid_signals.append('ERROR')
                    if 'INSUFFICIENT_DATA' not in valid_signals:
                        valid_signals.append('INSUFFICIENT_DATA')
                
            except Exception as e:
                print(f"  ⚠️  Could not analyze {block_name}: {e}")
                continue
            
            if not class_name:
                print(f"  ⚠️  Could not find class in {block_name}")
                continue
            
            # Store metadata
            blocks[block_name] = {
                'category': category_name,
                'class_name': class_name,
                'weight': default_weights.get(category_name, 20),
                'signals': valid_signals,
                'file_path': str(py_file),
                'module_path': module_path
            }
    
    return blocks


def generate_signal_tiers(signals: List[str], weight: int) -> Dict[str, Any]:
    """Generate signal tier configuration"""
    tiers = {}
    
    # Zero-point signals
    zero_signals = ['ERROR', 'INSUFFICIENT_DATA', 'NO_SIGNAL', 'NO_PATTERN', 
                   'NO_SWINGS', 'NO_ZONE', 'INACTIVE', 'NO_DATA', 'NEUTRAL']
    
    for signal in signals:
        if signal in zero_signals or 'NO_' in signal:
            tiers[signal] = {'points': 0}
        elif 'NEUTRAL' in signal or 'CALM' in signal or 'MODERATE' in signal or 'STABLE' in signal:
            tiers[signal] = {'max_points': weight // 2, 'formula': 'scaled'}
        else:
            tiers[signal] = {'base_points': weight, 'formula': 'scaled'}
    
    return tiers


def generate_decorator(block_name: str, metadata: Dict[str, Any]) -> str:
    """Generate @register_block decorator"""
    signal_tiers = generate_signal_tiers(metadata['signals'], metadata['weight'])
    
    # Format for readability
    tiers_json = json.dumps(signal_tiers, indent=8).replace('"', "'")
    
    decorator = f"""@register_block(
    name='{block_name}',
    category='{metadata['category']}',
    class_name='{metadata['class_name']}',
    default_weight={metadata['weight']},
    valid_signals={metadata['signals']},
    signal_tiers={tiers_json}
)"""
    
    return decorator


def migrate_block(block_name: str, metadata: Dict[str, Any], dry_run: bool = False) -> bool:
    """Migrate a single block to registry pattern"""
    file_path = Path(metadata['file_path'])
    
    if not file_path.exists():
        print(f"  ❌ File not found: {file_path}")
        return False
    
    # Read file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already migrated
    if '@register_block' in content:
        print(f"  ℹ️  Already migrated: {block_name}")
        return True
    
    # Generate decorator
    decorator = generate_decorator(block_name, metadata)
    
    # Find class definition
    class_pattern = rf'class {metadata["class_name"]}[:\(]'
    match = re.search(class_pattern, content)
    
    if not match:
        print(f"  ❌ Could not find class {metadata['class_name']} in {block_name}")
        return False
    
    # Add registry import if not present
    if 'from src.detectors.building_blocks.registry import register_block' not in content:
        # Find best place to insert import
        import_pos = content.find('from typing')
        if import_pos == -1:
            import_pos = content.find('import ')
        
        if import_pos != -1:
            # Find end of that line
            line_end = content.find('\n', import_pos)
            import_line = '\n\nfrom src.detectors.building_blocks.registry import register_block'
            content = content[:line_end] + import_line + content[line_end:]
        else:
            # Add at top after docstring
            doc_end = content.find('"""', 3)
            if doc_end != -1:
                import_line = '\n\nfrom src.detectors.building_blocks.registry import register_block\n'
                content = content[:doc_end+3] + import_line + content[doc_end+3:]
    
    # Add decorator before class
    class_start = content.find(match.group())
    line_start = content.rfind('\n', 0, class_start) + 1
    
    new_content = (
        content[:line_start] +
        decorator + '\n' +
        content[line_start:]
    )
    
    if dry_run:
        print(f"  🔍 Would migrate: {block_name}")
        return True
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"  ✅ Migrated: {block_name}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Migrate ALL building blocks to registry')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--category', help='Migrate specific category only')
    
    args = parser.parse_args()
    
    print("="*80)
    print("COMPREHENSIVE BUILDING BLOCK MIGRATION")
    print("="*80)
    print()
    
    print("📋 Discovering all building blocks...")
    blocks = discover_all_blocks()
    
    print(f"\n✅ Found {len(blocks)} blocks to migrate")
    
    if args.category:
        blocks = {k: v for k, v in blocks.items() if v['category'] == args.category.upper()}
        print(f"   Filtered to category {args.category}: {len(blocks)} blocks")
    
    if args.dry_run:
        print("   (DRY RUN MODE - no files will be modified)\n")
    
    # Group by category
    by_category = {}
    for name, meta in blocks.items():
        cat = meta['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(name)
    
    # Migrate by category
    total_success = 0
    total_fail = 0
    
    for category in sorted(by_category.keys()):
        block_names = by_category[category]
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category} ({len(block_names)} blocks)")
        print(f"{'='*80}\n")
        
        for block_name in sorted(block_names):
            metadata = blocks[block_name]
            if migrate_block(block_name, metadata, dry_run=args.dry_run):
                total_success += 1
            else:
                total_fail += 1
    
    print(f"\n{'='*80}")
    print("MIGRATION COMPLETE")
    print(f"{'='*80}\n")
    print(f"✅ Successful: {total_success}")
    print(f"❌ Failed: {total_fail}")
    print(f"\n📊 Total: {total_success + total_fail} blocks processed")
    
    if not args.dry_run and total_success > 0:
        print(f"\n📝 Next steps:")
        print(f"   1. Fix any import syntax errors: python scripts/fix_migrated_imports.py")
        print(f"   2. Test registry: python scripts/test_registry.py")
        print(f"   3. Commit changes")
    
    return 0 if total_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())