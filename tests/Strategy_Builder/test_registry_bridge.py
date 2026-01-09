"""
Test Registry Bridge

Tests the clean interface to BlockRegistry.

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import pytest

from src.utils.Strategy_Builder.registry_bridge import RegistryBridge
from src.utils.Strategy_Builder.models import BlockInfo, SignalInfo, BlockType
from src.detectors.building_blocks.registry import auto_discover_blocks

# Auto-discover blocks once before running tests
auto_discover_blocks()


class TestRegistryBridge:
    """Test RegistryBridge functionality"""
    
    def test_initialization(self):
        """Test bridge can be initialized"""
        bridge = RegistryBridge()
        assert bridge is not None
        assert bridge.registry is not None
    
    def test_get_blocks_by_category(self):
        """Test fetching blocks organized by category"""
        blocks = RegistryBridge.get_blocks_by_category()
        
        # Should return a dict
        assert isinstance(blocks, dict)
        
        # Should have categories
        assert len(blocks) > 0, "Should have at least one category"
        
        # Each category should have blocks
        for category, block_list in blocks.items():
            assert isinstance(category, str)
            assert isinstance(block_list, list)
            assert len(block_list) > 0, f"Category {category} should have blocks"
            
            # Each block should be BlockInfo
            for block in block_list:
                assert isinstance(block, BlockInfo)
                assert block.name
                assert block.display_name
                assert block.category == category
    
    def test_blocks_are_sorted(self):
        """Test blocks are sorted within categories"""
        blocks = RegistryBridge.get_blocks_by_category()
        
        for category, block_list in blocks.items():
            display_names = [b.display_name for b in block_list]
            sorted_names = sorted(display_names)
            assert display_names == sorted_names, f"Blocks in {category} should be sorted"
    
    def test_get_signal_options(self):
        """Test getting signal options for a block"""
        # First get a valid block
        blocks = RegistryBridge.get_blocks_by_category()
        
        # Find a block with signals
        test_block = None
        for category, block_list in blocks.items():
            for block in block_list:
                if block.signals:
                    test_block = block
                    break
            if test_block:
                break
        
        if not test_block:
            pytest.skip("No blocks with signals found")
        
        # Get signals for this block
        signals = RegistryBridge.get_signal_options(test_block.name)
        
        assert isinstance(signals, list)
        assert len(signals) > 0, f"Block {test_block.name} should have signals"
        
        # Each signal should be SignalInfo
        for signal in signals:
            assert isinstance(signal, SignalInfo)
            assert signal.name
            assert signal.display_name
    
    def test_get_signal_options_invalid_block(self):
        """Test getting signals for non-existent block"""
        signals = RegistryBridge.get_signal_options('nonexistent_block')
        
        # Should return empty list (not error)
        assert isinstance(signals, list)
        assert len(signals) == 0
    
    def test_validate_block_signal_valid(self):
        """Test validating a valid block+signal combination"""
        # Get a block with signals
        blocks = RegistryBridge.get_blocks_by_category()
        
        test_block = None
        for category, block_list in blocks.items():
            for block in block_list:
                if block.signals:
                    test_block = block
                    break
            if test_block:
                break
        
        if not test_block:
            pytest.skip("No blocks with signals found")
        
        # Validate with first signal
        signal = test_block.signals[0]
        result = RegistryBridge.validate_block_signal(test_block.name, signal)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_block_signal_invalid_block(self):
        """Test validating with non-existent block"""
        result = RegistryBridge.validate_block_signal('nonexistent_block', 'ANY_SIGNAL')
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert 'not found' in result.errors[0].lower()
    
    def test_validate_block_signal_invalid_signal(self):
        """Test validating with invalid signal for valid block"""
        # Get any block
        blocks = RegistryBridge.get_blocks_by_category()
        if not blocks:
            pytest.skip("No blocks found")
        
        # Get first block from first category
        first_category = list(blocks.keys())[0]
        test_block = blocks[first_category][0]
        
        # Use invalid signal
        result = RegistryBridge.validate_block_signal(test_block.name, 'INVALID_SIGNAL_XYZ')
        
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_get_block_metadata(self):
        """Test getting metadata for a specific block"""
        # Get a block
        blocks = RegistryBridge.get_blocks_by_category()
        if not blocks:
            pytest.skip("No blocks found")
        
        first_category = list(blocks.keys())[0]
        test_block = blocks[first_category][0]
        
        # Get metadata
        metadata = RegistryBridge.get_block_metadata(test_block.name)
        
        assert metadata is not None
        assert isinstance(metadata, dict)
        assert 'category' in metadata
    
    def test_get_block_metadata_invalid(self):
        """Test getting metadata for non-existent block"""
        metadata = RegistryBridge.get_block_metadata('nonexistent_block')
        
        assert metadata is None
    
    def test_get_block_count(self):
        """Test getting total block count"""
        count = RegistryBridge.get_block_count()
        
        assert isinstance(count, int)
        assert count > 0, "Should have at least one block"
    
    def test_get_category_count(self):
        """Test getting category count"""
        count = RegistryBridge.get_category_count()
        
        assert isinstance(count, int)
        assert count > 0, "Should have at least one category"
    
    def test_search_blocks(self):
        """Test searching for blocks"""
        # Get all blocks first
        all_blocks = RegistryBridge.get_blocks_by_category()
        if not all_blocks:
            pytest.skip("No blocks found")
        
        # Get a block to search for
        first_category = list(all_blocks.keys())[0]
        test_block = all_blocks[first_category][0]
        
        # Search by partial name
        search_term = test_block.name[:5]  # First 5 chars
        results = RegistryBridge.search_blocks(search_term)
        
        assert isinstance(results, list)
        # Should find at least the test block
        found = any(b.name == test_block.name for b in results)
        assert found, f"Should find block with search term '{search_term}'"
    
    def test_search_blocks_case_insensitive(self):
        """Test search is case-insensitive"""
        all_blocks = RegistryBridge.get_blocks_by_category()
        if not all_blocks:
            pytest.skip("No blocks found")
        
        first_category = list(all_blocks.keys())[0]
        test_block = all_blocks[first_category][0]
        
        # Search with uppercase
        results_upper = RegistryBridge.search_blocks(test_block.name.upper())
        
        # Search with lowercase
        results_lower = RegistryBridge.search_blocks(test_block.name.lower())
        
        # Should return same results
        assert len(results_upper) == len(results_lower)
    
    def test_search_blocks_no_results(self):
        """Test search with no matches"""
        results = RegistryBridge.search_blocks('xyznonexistentblock123')
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_clear_cache(self):
        """Test cache clearing"""
        # Fetch blocks to populate cache
        blocks1 = RegistryBridge.get_blocks_by_category()
        
        # Clear cache
        RegistryBridge.clear_cache()
        
        # Fetch again (should re-query)
        blocks2 = RegistryBridge.get_blocks_by_category()
        
        # Should have same data
        assert len(blocks1) == len(blocks2)
    
    def test_block_info_has_required_fields(self):
        """Test all BlockInfo objects have required fields"""
        blocks = RegistryBridge.get_blocks_by_category()
        
        for category, block_list in blocks.items():
            for block in block_list:
                # Required fields
                assert block.name, "Block must have name"
                assert block.display_name, "Block must have display_name"
                assert block.category, "Block must have category"
                # block_type will be string due to use_enum_values=True
                assert block.block_type in ['EVENT', 'SIGNAL', 'CONTEXT', 'HYBRID'], "Block must have valid type"
                assert isinstance(block.weight_range, tuple), "Block must have weight_range"
                assert len(block.weight_range) == 2, "Weight range must be tuple of 2"
                assert isinstance(block.default_weight, int), "Default weight must be int"
                assert isinstance(block.signals, list), "Signals must be list"


class TestRegistryBridgeCaching:
    """Test caching behavior"""
    
    def test_cache_returns_same_object(self):
        """Test cache returns same object reference"""
        blocks1 = RegistryBridge.get_blocks_by_category()
        blocks2 = RegistryBridge.get_blocks_by_category()
        
        # Should be same object due to caching
        assert blocks1 is blocks2
    
    def test_cache_clear_forces_refresh(self):
        """Test clearing cache forces new query"""
        blocks1 = RegistryBridge.get_blocks_by_category()
        RegistryBridge.clear_cache()
        blocks2 = RegistryBridge.get_blocks_by_category()
        
        # Should be different objects
        assert blocks1 is not blocks2
        
        # But should have same data
        assert len(blocks1) == len(blocks2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])