"""
Integration Tests - Strategy Builder

Tests complete workflows across all components.

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import pytest
import tempfile
from pathlib import Path

from src.utils.Strategy_Builder import (
    StrategyConfiguration,
    BlockSelection,
    SignalConfiguration,
    StrategyCategory,
    SignalRole,
    BlockType,
    RegistryBridge,
    StrategyValidator,
    StrategyRegistry
)
from src.detectors.building_blocks.registry import auto_discover_blocks

# Auto-discover blocks for testing
auto_discover_blocks()


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def components(temp_storage):
    """Create all components for integration testing"""
    return {
        'bridge': RegistryBridge(),
        'validator': StrategyValidator(),
        'registry': StrategyRegistry(storage_dir=temp_storage)
    }


class TestCompleteWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_create_validate_save_load_workflow(self, components):
        """Test complete workflow: Create → Validate → Save → Load"""
        bridge = components['bridge']
        validator = components['validator']
        registry = components['registry']
        
        # Step 1: Get available blocks from bridge
        blocks = bridge.get_blocks_by_category()
        assert len(blocks) > 0, "No blocks available"
        
        # Step 2: Create strategy using bridge data
        first_category = list(blocks.keys())[0]
        first_block = blocks[first_category][0]
        
        if not first_block.signals:
            pytest.skip("Block has no signals")
        
        strategy_num = registry.get_next_strategy_number()
        
        config = StrategyConfiguration(
            strategy_name=f"integration_test",
            strategy_number=strategy_num,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block=first_block.name,
            blocks=[
                BlockSelection(
                    block_name=first_block.name,
                    block_display_name=first_block.display_name,
                    block_category=first_block.category,
                    block_type=first_block.block_type,
                    weight=first_block.default_weight,
                    weight_range=first_block.weight_range,
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name=first_block.signals[0],
                            signal_display_name=first_block.signals[0].replace('_', ' ').title(),
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        # Step 3: Validate
        validation = validator.validate(config)
        assert validation.is_valid, f"Validation failed: {validation.errors}"
        
        # Step 4: Save
        filepath = registry.save_strategy(config, validate=False)
        assert filepath.exists()
        
        # Step 5: Load
        loaded = registry.load_strategy(strategy_num)
        assert loaded is not None
        assert loaded.strategy_number == strategy_num
        assert loaded.strategy_name == config.strategy_name
    
    def test_modify_and_resave_workflow(self, components):
        """Test workflow: Create → Save → Load → Modify → Save"""
        registry = components['registry']
        validator = components['validator']
        
        # Create and save initial strategy
        strategy_num = registry.get_next_strategy_number()
        
        config = StrategyConfiguration(
            strategy_name="modifiable_strategy",
            strategy_number=strategy_num,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="test_block",
            blocks=[
                BlockSelection(
                    block_name="test_block",
                    block_display_name="Test Block",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=25,
                    weight_range=(20, 30),
                    is_main_signal=True
                )
            ]
        )
        
        registry.save_strategy(config, validate=False)
        
        # Load and modify
        loaded = registry.load_strategy(strategy_num)
        assert loaded is not None
        
        # Modify description
        loaded.description = "Modified description"
        
        # Save again with overwrite
        registry.save_strategy(loaded, validate=False, overwrite=True)
        
        # Load again and verify
        reloaded = registry.load_strategy(strategy_num)
        assert reloaded.description == "Modified description"


class TestCrossComponentValidation:
    """Test validation across components"""
    
    def test_bridge_provides_valid_block_info(self, components):
        """Test that bridge provides info that passes validator"""
        bridge = components['bridge']
        validator = components['validator']
        
        # Get all blocks from all categories
        blocks_by_category = bridge.get_blocks_by_category()
        if not blocks_by_category:
            pytest.skip("No blocks in registry")
        
        # Flatten to list
        all_blocks = []
        for category_blocks in blocks_by_category.values():
            all_blocks.extend(category_blocks)
        
        if not all_blocks:
            pytest.skip("No blocks in registry")
        
        # Find a block with signals
        valid_block = None
        for block in all_blocks:
            if block.signals:
                valid_block = block
                break
        
        if not valid_block:
            pytest.skip("No blocks with signals")
        
        # Create strategy using this block
        config = StrategyConfiguration(
            strategy_name="bridge_validated",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block=valid_block.name,
            blocks=[
                BlockSelection(
                    block_name=valid_block.name,
                    block_display_name=valid_block.display_name,
                    block_category=valid_block.category,
                    block_type=valid_block.block_type,
                    weight=valid_block.default_weight,
                    weight_range=valid_block.weight_range,
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name=valid_block.signals[0],
                            signal_display_name=valid_block.signals[0].replace('_', ' ').title(),
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        # Should validate successfully
        result = validator.validate(config)
        assert result.is_valid
    
    def test_registry_validates_before_save(self, components):
        """Test that registry validates before saving"""
        registry = components['registry']
        
        # Create invalid strategy (non-existent block)
        config = StrategyConfiguration(
            strategy_name="invalid_strategy",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="nonexistent_block_xyz",
            blocks=[
                BlockSelection(
                    block_name="nonexistent_block_xyz",
                    block_display_name="Nonexistent",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=20,
                    weight_range=(10, 30)
                )
            ]
        )
        
        # Should raise validation error
        with pytest.raises(ValueError, match="validation failed"):
            registry.save_strategy(config, validate=True)


class TestErrorHandling:
    """Test error handling across components"""
    
    def test_load_nonexistent_strategy(self, components):
        """Test loading non-existent strategy"""
        registry = components['registry']
        
        result = registry.load_strategy(999)
        assert result is None
    
    def test_delete_nonexistent_strategy(self, components):
        """Test deleting non-existent strategy"""
        registry = components['registry']
        
        success = registry.delete_strategy(999)
        assert not success
    
    def test_validation_fails_gracefully(self, components):
        """Test validator fails gracefully on bad data"""
        validator = components['validator']
        
        # Pydantic will catch main_signal not in blocks during model creation
        # So we test with a different validation issue that validator catches
        # Create strategy with non-existent block (validator-level error)
        config = StrategyConfiguration(
            strategy_name="bad_strategy",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="nonexistent_block",
            blocks=[
                BlockSelection(
                    block_name="nonexistent_block",
                    block_display_name="Nonexistent",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=20,
                    weight_range=(10, 30)
                )
            ]
        )
        
        # Validator should catch that block is not in registry
        result = validator.validate(config)
        assert not result.is_valid
        assert len(result.errors) > 0


class TestMultiStrategyOperations:
    """Test operations with multiple strategies"""
    
    def test_create_multiple_strategies(self, components):
        """Test creating and managing multiple strategies"""
        registry = components['registry']
        
        # Create 5 strategies
        for i in range(1, 6):
            config = StrategyConfiguration(
                strategy_name=f"multi_test_{i}",
                strategy_number=i,
                strategy_category=StrategyCategory.REVERSAL if i % 2 == 0 else StrategyCategory.CONTINUATION,
                main_signal_block="test_block",
                blocks=[
                    BlockSelection(
                        block_name="test_block",
                        block_display_name="Test",
                        block_category="TEST",
                        block_type=BlockType.EVENT,
                        weight=20,
                        weight_range=(10, 30),
                        is_main_signal=True
                    )
                ]
            )
            registry.save_strategy(config, validate=False)
        
        # Verify count
        assert registry.get_strategy_count() == 5
        
        # Verify list
        strategies = registry.list_strategies()
        assert len(strategies) == 5
        
        # Verify category counts
        counts = registry.get_category_counts()
        assert counts[StrategyCategory.REVERSAL] == 2
        assert counts[StrategyCategory.CONTINUATION] == 3
    
    def test_search_across_strategies(self, components):
        """Test searching across multiple strategies"""
        registry = components['registry']
        
        # Create strategies with different names
        names = ['reversal_m', 'reversal_w', 'continuation_ema', 'breakout_pattern']
        for i, name in enumerate(names, 1):
            config = StrategyConfiguration(
                strategy_name=name,
                strategy_number=i,
                strategy_category=StrategyCategory.REVERSAL,
                main_signal_block="test",
                blocks=[
                    BlockSelection(
                        block_name="test",
                        block_display_name="Test",
                        block_category="TEST",
                        block_type=BlockType.EVENT,
                        weight=20,
                        weight_range=(10, 30),
                        is_main_signal=True
                    )
                ]
            )
            registry.save_strategy(config, validate=False)
        
        # Search for 'reversal'
        results = registry.search_strategies('reversal')
        assert len(results) == 2
        
        # Search for 'pattern'
        results = registry.search_strategies('pattern')
        assert len(results) == 1


class TestPerformance:
    """Basic performance tests"""
    
    def test_validate_performance(self, components):
        """Test validation performance"""
        import time
        
        validator = components['validator']
        
        # Create a complex strategy
        config = StrategyConfiguration(
            strategy_name="performance_test",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="test",
            blocks=[
                BlockSelection(
                    block_name=f"test",
                    block_display_name="Test",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=20,
                    weight_range=(10, 30),
                    is_main_signal=True
                )
            ]
        )
        
        # Time validation
        start = time.time()
        for _ in range(100):
            validator.validate(config)
        elapsed = time.time() - start
        
        # Should be fast (< 1 second for 100 validations)
        assert elapsed < 1.0, f"Validation too slow: {elapsed:.3f}s for 100 runs"
    
    def test_save_load_performance(self, components):
        """Test save/load performance"""
        import time
        
        registry = components['registry']
        
        # Create strategy
        config = StrategyConfiguration(
            strategy_name="performance_save",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="test",
            blocks=[
                BlockSelection(
                    block_name="test",
                    block_display_name="Test",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=20,
                    weight_range=(10, 30),
                    is_main_signal=True
                )
            ]
        )
        
        # Time save
        start = time.time()
        registry.save_strategy(config, validate=False)
        save_time = time.time() - start
        
        # Time load
        start = time.time()
        registry.load_strategy(1)
        load_time = time.time() - start
        
        # Should be fast
        assert save_time < 0.1, f"Save too slow: {save_time:.3f}s"
        assert load_time < 0.1, f"Load too slow: {load_time:.3f}s"


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_strategy_development_cycle(self, components):
        """Test typical strategy development cycle"""
        bridge = components['bridge']
        validator = components['validator']
        registry = components['registry']
        
        # 1. Developer explores available blocks
        blocks = bridge.get_blocks_by_category()
        assert len(blocks) > 0
        
        # 2. Developer selects blocks for strategy
        # (Using first available block for test)
        first_category = list(blocks.keys())[0]
        selected_block = blocks[first_category][0]
        
        if not selected_block.signals:
            pytest.skip("Block has no signals")
        
        # 3. Developer creates strategy configuration
        strategy_num = registry.get_next_strategy_number()
        config = StrategyConfiguration(
            strategy_name="development_test",
            strategy_number=strategy_num,
            strategy_category=StrategyCategory.REVERSAL,
            description="Test strategy for development cycle",
            main_signal_block=selected_block.name,
            blocks=[
                BlockSelection(
                    block_name=selected_block.name,
                    block_display_name=selected_block.display_name,
                    block_category=selected_block.category,
                    block_type=selected_block.block_type,
                    weight=selected_block.default_weight,
                    weight_range=selected_block.weight_range,
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name=selected_block.signals[0],
                            signal_display_name=selected_block.signals[0].replace('_', ' ').title(),
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        # 4. Developer validates strategy
        validation = validator.validate(config)
        assert validation.is_valid
        
        # 5. Developer saves strategy
        filepath = registry.save_strategy(config, validate=False)
        assert filepath.exists()
        
        # 6. Developer lists all strategies
        all_strategies = registry.list_strategies()
        assert len(all_strategies) >= 1
        
        # 7. Developer can reload for modification
        reloaded = registry.load_strategy(strategy_num)
        assert reloaded is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])