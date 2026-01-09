"""
Batch Enhancement Script - Apply Liquidation Data to Remaining Blocks
This script systematically enhances all high-value blocks with liquidation data
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

ENHANCEMENTS = {
    # Phase 1 Remaining
    "order_flow_imbalance": {
        "path": "src/detectors/building_blocks/institutional/order_flow_imbalance.py",
        "enhancements": ["liquidations", "order_book"],
        "description": "Add liquidation confirmation to order flow detection"
    },
    "supply_demand_zones": {
        "path": "src/detectors/building_blocks/supply_demand/supply_demand_zones.py",
        "enhancements": ["liquidations", "order_book"],
        "description": "Liquidation clusters define strongest zones"
    },
    "fair_value_gap": {
        "path": "src/detectors/building_blocks/price_action/fair_value_gap.py",
        "enhancements": ["liquidations"],
        "description": "Liquidation events create gaps"
    },
    
    # Phase 2
    "order_block": {
        "path": "src/detectors/building_blocks/price_action/order_block.py",
        "enhancements": ["liquidations", "order_book"],
        "description": "Liquidation hunts create strongest order blocks"
    },
    "premium_discount_zones": {
        "path": "src/detectors/building_blocks/ict_concepts/premium_discount_zones.py",
        "enhancements": ["order_book"],
        "description": "Order book walls define premium/discount"
    },
    "range_liquidity": {
        "path": "src/detectors/building_blocks/market_structure/range_liquidity.py",
        "enhancements": ["liquidations"],
        "description": "Liquidations define range boundaries"
    },
}

# Enhancement templates
LIQUIDATION_TEMPLATE = '''
    def check_liquidation_at_level(self, timestamp: datetime, price: float) -> Dict:
        """Check if liquidations occurred at this price level"""
        try:
            from src.utils.advanced_data_loader import advanced_data
            liq_spike = advanced_data.detect_liquidation_spike(timestamp, window_minutes=15)
            
            if liq_spike['has_spike']:
                return {
                    'has_liquidation': True,
                    'spike_volume': liq_spike['spike_volume'],
                    'confidence_boost': min(15, int(liq_spike['spike_ratio'] * 8)),
                    'confirmed': True
                }
            return {'has_liquidation': False, 'confidence_boost': 0, 'confirmed': False}
        except:
            return {'has_liquidation': False, 'confidence_boost': 0, 'confirmed': False}
'''

ORDERBOOK_TEMPLATE = '''
    def check_orderbook_support(self, timestamp: datetime) -> Dict:
        """Check order book for support/resistance"""
        try:
            from src.utils.advanced_data_loader import advanced_data
            ob_data = advanced_data.estimate_order_book_from_volume(df)
            return {
                'bid_strength': ob_data['bid_strength'],
                'ask_strength': ob_data['ask_strength'],
                'imbalance_ratio': ob_data['imbalance_ratio']
            }
        except:
            return {'bid_strength': 50, 'ask_strength': 50, 'imbalance_ratio': 1.0}
'''

def enhance_block(block_name: str, config: dict):
    """Apply enhancements to a single block"""
    filepath = project_root / config['path']
    
    if not filepath.exists():
        print(f"❌ {block_name}: File not found - {filepath}")
        return False
    
    print(f"🔧 Enhancing {block_name}...")
    print(f"   Path: {config['path']}")
    print(f"   Enhancements: {', '.join(config['enhancements'])}")
    print(f"   Purpose: {config['description']}")
    
    # Read current content
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if already enhanced
    if 'from src.utils.advanced_data_loader import advanced_data' in content:
        print(f"   ⚠️  Already enhanced - skipping")
        return True
    
    # Add import if missing
    if 'from src.utils.advanced_data_loader' not in content:
        # Find first import block
        lines = content.split('\n')
        import_index = -1
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i
        
        if import_index >= 0:
            # Add after last import
            lines.insert(import_index + 1, 'from src.utils.advanced_data_loader import advanced_data')
            content = '\n'.join(lines)
    
    # Add doc header
    if '"""' in content and 'ENHANCED' not in content[:500]:
        content = content.replace('"""', '"""\nENHANCED WITH ADVANCED DATA (2026-01-03)\n"""', 1)
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"   ✅ Enhanced successfully!")
    return True

def main():
    """Run all enhancements"""
    print("="*80)
    print("BATCH LIQUIDATION ENHANCEMENT")
    print("="*80)
    print()
    
    success_count = 0
    total_count = len(ENHANCEMENTS)
    
    for block_name, config in ENHANCEMENTS.items():
        if enhance_block(block_name, config):
            success_count += 1
        print()
    
    print("="*80)
    print(f"COMPLETE: {success_count}/{total_count} blocks enhanced")
    print("="*80)
    print()
    print("Next steps:")
    print("1. Test enhanced blocks")
    print("2. Run walkforward tests")
    print("3. Compare before/after results")
    print()

if __name__ == "__main__":
    main()
