"""
Registry Test: ict_silver_bullet
================================
Test ID: 40/83
Category: SIGNALS
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from registry_test_library import test_building_block_registry
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test ict_silver_bullet via Registry')
    parser.add_argument('--days', type=int, default=180, help='Test period in days')
    parser.add_argument('--no-multicore', action='store_true', help='Disable multicore')
    args = parser.parse_args()
    
    result = test_building_block_registry(
        block_name='ict_silver_bullet',
        days=args.days,
        use_multicore=not args.no_multicore
    )
    
    sys.exit(0 if result else 1)
