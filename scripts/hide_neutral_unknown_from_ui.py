"""
Hide NEUTRAL and UNKNOWN signals from Strategy Builder UI
==========================================================

These signals provide little value for end users:
- NEUTRAL: No directional bias (just noise in UI)
- UNKNOWN: Error/fallback state (shouldn't be selectable)

This script adds 'ui_visible': False to all NEUTRAL/UNKNOWN signals
that don't already have it set.

Author: BTC_Engine_v3
Date: 2026-01-15
"""

import re
from pathlib import Path


def hide_neutral_unknown_in_file(filepath):
    """Add ui_visible: False to NEUTRAL and UNKNOWN signals."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    modified = False
    
    # Pattern 1: NEUTRAL or UNKNOWN with points but NO ui_visible
    # Match: 'NEUTRAL': { ... 'points': X, ... 'description': ... }
    # Where there's NO ui_visible already
    
    for signal_name in ['NEUTRAL', 'UNKNOWN']:
        # Find all occurrences of this signal
        pattern = rf"'{signal_name}':\s*\{{([^}}]+)\}}"
        
        def replace_signal(match):
            nonlocal modified
            signal_block = match.group(1)
            
            # Check if ui_visible already exists
            if 'ui_visible' in signal_block:
                return match.group(0)  # Already has ui_visible, don't touch
            
            # Check if it has points or base_points
            if 'points' not in signal_block and 'base_points' not in signal_block:
                return match.group(0)  # No points definition, skip
            
            # Add ui_visible: False before the description
            if "'description':" in signal_block:
                new_block = re.sub(
                    r"(\s+)'description':",
                    r"\1'ui_visible': False,  # Filter from Strategy Builder UI\n\1'description':",
                    signal_block
                )
                modified = True
                return f"'{signal_name}': {{{new_block}}}"
            
            return match.group(0)
        
        content = re.sub(pattern, replace_signal, content, flags=re.DOTALL)
    
    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    
    return False


def main():
    """Process all building blocks."""
    blocks_dir = Path('src/detectors/building_blocks')
    modified_files = []
    
    for filepath in blocks_dir.rglob('*.py'):
        if filepath.name in ['__init__.py', 'registry.py']:
            continue
        if 'archived' in str(filepath):
            continue
        
        if hide_neutral_unknown_in_file(filepath):
            modified_files.append(filepath.relative_to('src/detectors/building_blocks'))
    
    print(f"Modified {len(modified_files)} files:")
    for f in modified_files:
        print(f"  - {f}")
    
    if modified_files:
        print(f"\n✅ Hidden NEUTRAL/UNKNOWN from UI in {len(modified_files)} building blocks")
    else:
        print("\n✅ All NEUTRAL/UNKNOWN signals already hidden or no changes needed")


if __name__ == "__main__":
    main()
