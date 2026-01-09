"""
Apply Block Type Classifications
Adds standardized headers to all building blocks
"""

import os
import sys
from pathlib import Path

# Import classifications from classify_and_label_blocks
sys.path.insert(0, str(Path(__file__).parent))
from classify_and_label_blocks import BLOCK_CLASSIFICATIONS


def create_classification_header(block_type, mode, description):
    """Create standardized classification header"""
    return f'''"""
Building Block Classification: {block_type}
Mode: {mode}
Purpose: {description}

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""

'''


def apply_classification(file_path: Path, block_type: str, mode: str, description: str):
    """Add classification header to a file"""
    
    # Read existing content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already has classification
    if 'Building Block Classification:' in content:
        print(f"   ⏭️  SKIP: Already classified")
        return False
    
    # Create new header
    new_header = create_classification_header(block_type, mode, description)
    
    # Find where to insert (after any existing docstring or at top)
    lines = content.split('\n')
    insert_pos = 0
    
    # Skip shebang if present
    if lines[0].startswith('#!'):
        insert_pos = 1
    
    # Skip existing module docstring if present
    in_docstring = False
    docstring_start = None
    for i, line in enumerate(lines[insert_pos:], start=insert_pos):
        if line.strip().startswith('"""') or line.strip().startswith("'''"):
            if not in_docstring:
                in_docstring = True
                docstring_start = i
            else:
                # End of docstring - insert after it
                insert_pos = i + 1
                break
        elif not line.strip() and not in_docstring:
            # Empty line before any content
            continue
        elif not in_docstring:
            # Hit actual code, insert here
            insert_pos = i
            break
    
    # Insert new header
    new_lines = lines[:insert_pos] + [new_header] + lines[insert_pos:]
    new_content = '\n'.join(new_lines)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    return True


def main():
    blocks_dir = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks'
    
    print("=" * 80)
    print("APPLYING BLOCK CLASSIFICATIONS")
    print("=" * 80)
    print(f"\nProcessing {len(BLOCK_CLASSIFICATIONS)} blocks...")
    print()
    
    updated = 0
    skipped = 0
    errors = 0
    
    for block_path, info in sorted(BLOCK_CLASSIFICATIONS.items()):
        full_path = blocks_dir / block_path
        
        if not full_path.exists():
            print(f"❌ {block_path}")
            print(f"   ERROR: File not found")
            errors += 1
            continue
        
        print(f"📝 {block_path}")
        print(f"   {info['type']} | {info['mode']}")
        
        try:
            if apply_classification(full_path, info['type'], info['mode'], info['description']):
                updated += 1
                print(f"   ✅ Updated")
            else:
                skipped += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            errors += 1
        
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped} (already classified)")
    print(f"Errors: {errors}")
    print("=" * 80)
    
    if errors > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
