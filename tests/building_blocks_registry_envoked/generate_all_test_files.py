"""
Generate All 83 Registry Test Files
====================================

This script generates individual test files for all 83 building blocks.
Each test file can be run independently to test its specific building block.

This is NOT a batch test runner - it just creates the individual test files.
Each file must still be run separately to actually test the building block.

Usage:
    python generate_all_test_files.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.detectors.building_blocks.registry import BlockRegistry


def generate_test_file(block_name: str, test_number: int, category: str, output_dir: Path):
    """Generate a single test file for a building block"""
    
    content = f'''"""
Registry Test: {block_name}
{'=' * (15 + len(block_name))}
Test ID: {test_number:02d}/83
Category: {category}
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from registry_test_library import test_building_block_registry
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test {block_name} via Registry')
    parser.add_argument('--days', type=int, default=180, help='Test period in days')
    parser.add_argument('--no-multicore', action='store_true', help='Disable multicore')
    args = parser.parse_args()
    
    result = test_building_block_registry(
        block_name='{block_name}',
        days=args.days,
        use_multicore=not args.no_multicore
    )
    
    sys.exit(0 if result else 1)
'''
    
    filename =output_dir / f'test_{test_number:02d}_{block_name}.py'
    with open(filename, 'w') as f:
        f.write(content)
    
    return filename


def main():
    """Generate all 83 test files"""
    
    print("="*80)
    print("GENERATING 83 REGISTRY TEST FILES")
    print("="*80)
    
    # Get all blocks from registry
    all_blocks = BlockRegistry.get_all_blocks()
    sorted_blocks = sorted(all_blocks.items())
    
    print(f"\nTotal blocks in registry: {len(sorted_blocks)}")
    
    # Output directory
    output_dir = Path(__file__).parent
    
    print(f"Output directory: {output_dir}\n")
    
    # Generate files
    generated = []
    failed = []
    
    for idx, (block_name, metadata) in enumerate(sorted_blocks, 1):
        try:
            filename = generate_test_file(
                block_name=block_name,
                test_number=idx,
                category=metadata.category,
                output_dir=output_dir
            )
            generated.append(filename)
            print(f"✅ [{idx:02d}/83] {block_name:40s} -> {filename.name}")
        except Exception as e:
            failed.append((block_name, str(e)))
            print(f"❌ [{idx:02d}/83] {block_name:40s} FAILED: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("GENERATION COMPLETE")
    print("="*80)
    print(f"Generated: {len(generated)} test files")
    print(f"Failed: {len(failed)} files")
    
    if failed:
        print("\n⚠️  Failed files:")
        for block_name, error in failed:
            print(f"   - {block_name}: {error}")
    
    print(f"\n✅ All test files created in: {output_dir}")
    print(f"\nTo run a test:")
    print(f"   python {output_dir}/test_01_adaptive_momentum_oscillator.py")
    print(f"   python {output_dir}/test_01_adaptive_momentum_oscillator.py --days 30 --no-multicore")
    print("="*80)
    
    return len(failed) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
