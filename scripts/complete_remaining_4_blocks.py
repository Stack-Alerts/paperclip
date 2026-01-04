"""
Complete remaining 4 blocks with liquidation integration
Efficient batch completion
"""

import re
from pathlib import Path

blocks_to_complete = {
    "supply_demand_zones": {
        "file": "src/detectors/building_blocks/supply_demand/supply_demand_zones.py",
        "method": '''
    def check_zone_liquidation_strength(self, zone_price: float, df: pd.DataFrame) -> Dict:
        """Check if liquidation clusters strengthen this zone"""
        try:
            levels = advanced_data.get_liquidation_levels(df, lookback_bars=200)
            
            # Check for liquidation clusters near zone
            cluster_strength = 0
            for cluster in levels['above'] + levels['below']:
                distance = abs(cluster['price'] - zone_price) / zone_price
                if distance < 0.02:  # Within 2%
                    cluster_strength += cluster['volume']
            
            if cluster_strength > 0:
                return {
                    'has_clusters': True,
                    'cluster_strength': cluster_strength,
                    'confidence_boost': min(20, int(cluster_strength / 100)),
                    'zone_type': 'INSTITUTIONAL'
                }
            return {'has_clusters': False, 'confidence_boost': 0}
        except:
            return {'has_clusters': False, 'confidence_boost': 0}
''',
        "integration_find": "confidence = min(",
        "integration_add": '''
        # Check liquidation clusters at zone
        liq_boost = self.check_zone_liquidation_strength(
            zone.get('zone_mid', current_price), df
        )
        confidence += liq_boost['confidence_boost']
        
        if liq_boost['has_clusters']:
            confluence_factors.append(f'⭐ LIQUIDATION CLUSTERS at zone! Institutional strength!')
        
        '''
    },
    
    "fair_value_gap": {
        "file": "src/detectors/building_blocks/price_action/fair_value_gap.py",
        "method": '''
    def check_gap_liquidation_event(self, gap_timestamp: datetime) -> Dict:
        """Check if gap formed during liquidation event"""
        try:
            liq_spike = advanced_data.detect_liquidation_spike(gap_timestamp, window_minutes=15)
            
            if liq_spike['has_spike']:
                return {
                    'has_liquidation': True,
                    'gap_quality': 'INSTITUTIONAL',
                    'confidence_boost': min(15, int(liq_spike['spike_ratio'] * 10)),
                    'spike_volume': liq_spike['spike_volume']
                }
            return {'has_liquidation': False, 'confidence_boost': 0, 'gap_quality': 'STANDARD'}
        except:
            return {'has_liquidation': False, 'confidence_boost': 0, 'gap_quality': 'STANDARD'}
''',
        "integration_find": "if is_new_event:",
        "integration_add": '''
        # Check if gap formed during liquidation
        liq_event = self.check_gap_liquidation_event(active_fvg['timestamp'])
        if liq_event['has_liquidation']:
            confidence += liq_event['confidence_boost']
            confluence_factors.insert(0, f'⭐ {liq_event["gap_quality"]} GAP - Liquidation event!')
        
        '''
    },
    
    "order_block": {
        "file": "src/detectors/building_blocks/price_action/order_block.py",
        "method": '''
    def check_block_liquidation_confirmation(self, block_timestamp: datetime) -> Dict:
        """Check if order block formed during liquidation hunt"""
        try:
            liq_spike = advanced_data.detect_liquidation_spike(block_timestamp, window_minutes=15)
            
            if liq_spike['has_spike']:
                return {
                    'has_liquidation': True,
                    'block_type': 'INSTITUTIONAL',
                    'confidence_boost': min(15, int(liq_spike['spike_ratio'] * 10)),
                    'spike_side': liq_spike['spike_side']
                }
            return {'has_liquidation': False, 'confidence_boost': 0}
        except:
            return {'has_liquidation': False, 'confidence_boost': 0}
''',
        "integration_find": "confidence = ",
        "integration_add": '''
        # Check liquidation confirmation
        liq_confirm = self.check_block_liquidation_confirmation(block_timestamp)
        confidence += liq_confirm['confidence_boost']
        
        if liq_confirm['has_liquidation']:
            confluence_factors.append(f'⭐ LIQUIDATION HUNT! {liq_confirm["block_type"]} block!')
        
        '''
    },
    
    "range_liquidity": {
        "file": "src/detectors/building_blocks/market_structure/range_liquidity.py",
        "method": '''
    def check_liquidation_magnets(self, range_high: float, range_low: float, df: pd.DataFrame) -> Dict:
        """Check for liquidation clusters acting as magnets"""
        try:
            levels = advanced_data.get_liquidation_levels(df, lookback_bars=100)
            
            magnets_above = []
            magnets_below = []
            
            for cluster in levels['above']:
                if cluster['price'] > range_high:
                    magnets_above.append(cluster)
            
            for cluster in levels['below']:
                if cluster['price'] < range_low:
                    magnets_below.append(cluster)
            
            has_magnets = len(magnets_above) > 0 or len(magnets_below) > 0
            
            if has_magnets:
                return {
                    'has_magnets': True,
                    'magnets_above': len(magnets_above),
                    'magnets_below': len(magnets_below),
                    'confidence_boost': 10 if has_magnets else 0
                }
            return {'has_magnets': False, 'confidence_boost': 0}
        except:
            return {'has_magnets': False, 'confidence_boost': 0}
''',
        "integration_find": "# Build confluence",
        "integration_add": '''
        # Check liquidation magnets
        liq_magnets = self.check_liquidation_magnets(range_high, range_low, df)
        confidence += liq_magnets['confidence_boost']
        
        if liq_magnets['has_magnets']:
            confluence_factors.append(f'⭐ LIQUIDATION MAGNETS detected!')
        
        '''
    }
}

def complete_block(block_name, config):
    """Add liquidation methods to a block"""
    filepath = Path(config['file'])
    
    if not filepath.exists():
        print(f"❌ {block_name}: File not found")
        return False
    
    print(f"✅ Completing {block_name}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Add method before analyze()
    if 'def analyze(self' in content and config['method'] not in content:
        content = content.replace(
            '    def analyze(self',
            config['method'] + '\n    def analyze(self'
        )
    
    # Note: Integration would need manual placement for accuracy
    # This script documents the pattern
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"   Method added to {block_name}")
    return True

if __name__ == "__main__":
    print("="*80)
    print("COMPLETING REMAINING 4 BLOCKS")
    print("="*80)
    
    for block_name, config in blocks_to_complete.items():
        complete_block(block_name, config)
    
    print("\n" + "="*80)
    print("NOTE: Methods added. Integration points documented in config.")
    print("Manual integration recommended for production quality.")
    print("="*80)
