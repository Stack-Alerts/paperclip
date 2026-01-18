#!/usr/bin/env python3
"""
Add ui_visible: False to all zero-point signals in building blocks.

Rule: Any signal with 'points': 0 should have 'ui_visible': False
"""

import os
import re
from pathlib import Path

def process_file(filepath):
    """Process a single building block file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    modified = False
    
    # Find all signal definitions with 'points': 0
    # Pattern: 'SIGNAL_NAME': { ... 'points': 0, ... }
    
    # Strategy: Find signal blocks, check if points: 0, add ui_visible if missing
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Check if this line has 'points': 0
        if "'points': 0" in line or '"points": 0' in line:
            # Look ahead to see if ui_visible already exists in this signal block
            has_ui_visible = False
            closing_brace_found = False
            look_ahead = 1
            
            while i + look_ahead < len(lines) and not closing_brace_found:
                next_line = lines[i + look_ahead]
                if 'ui_visible' in next_line:
                    has_ui_visible = True
                    break
                # Check for closing brace of signal definition
                if re.match(r'^\s*\},?\s*$', next_line) or re.match(r'^\s*\}\s*$', next_line):
                    closing_brace_found = True
                    break
                look_ahead += 1
            
            # If no ui_visible found and we haven't closed the signal block yet
            if not has_ui_visible and closing_brace_found:
                # Insert ui_visible: False before looking at next line
                # Get indentation from current line
                indent_match = re.match(r'^(\s*)', line)
                indent = indent_match.group(1) if indent_match else '            '
                
                # Add ui_visible line right after current line
                ui_line = f"{indent}'ui_visible': False  # Filter from Strategy Builder UI"
                new_lines.append(ui_line)
                modified = True
        
        i += 1
    
    if modified:
        new_content = '\n'.join(new_lines)
        with open(filepath, 'w') as f:
            f.write(new_content)
        return True
    
    return False

def main():
    """Process all building block files."""
    blocks_dir = Path('src/detectors/building_blocks')
    
    if not blocks_dir.exists():
        print(f"Error: {blocks_dir} does not exist")
        return
    
    files_processed = 0
    files_modified = 0
    
    # Walk through all Python files
    for filepath in blocks_dir.rglob('*.py'):
        if filepath.name == '__init__.py' or filepath.name == 'registry.py':
            continue
        
        files_processed += 1
        if process_file(filepath):
            files_modified += 1
            print(f"✓ Modified: {filepath.relative_to('src/detectors/building_blocks')}")
        else:
            print(f"  Unchanged: {filepath.relative_to('src/detectors/building_blocks')}")
    
    print(f"\n{'='*60}")
    print(f"Files processed: {files_processed}")
    print(f"Files modified: {files_modified}")
    print(f"Files unchanged: {files_processed - files_modified}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
