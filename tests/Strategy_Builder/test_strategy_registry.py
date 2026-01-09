"""
Test Strategy Registry

Tests strategy storage, loading, and management.

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import pytest
import tempfile
import json
from pathlib import Path

from src.utils.Strategy_Builder.strategy_registry import StrategyRegistry
from src.utils.Strategy_Builder.models import (
    StrategyConfiguration,
    BlockSelection,
    SignalConfiguration,
    StrategyCategory,
    SignalRole,
    BlockType
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_storage):
    """Create registry instance with temp storage"""
    return StrategyRegistry(storage_dir=temp_storage)


@pytest.fixture
def sample_strategy():
    """Create sample valid strategy"""
    return StrategyConfiguration(
        strategy_name="test_strategy",
        strategy_number=1,
        strategy_category=StrategyCategory.REVERSAL,
        main_signal_block="double_top",
        blocks=[
            BlockSelection(
                block_name="double_top",
                block_display_name="Double Top",
                block_category="PATTERNS",
                block_type=BlockType.EVENT,
                weight=30,
                weight_range=(20, 40),
                is_main_signal=True,
                signals=[
                    SignalConfiguration(
                        signal_name="BEARISH_BREAKDOWN",
                        signal_display_name="Bearish Breakdown",
                        role=SignalRole.SIGNAL
                    )
                ]
            )
        ]
    )


class TestStrategyRegistryInit:
    """Test registry initialization"""
    
    def test_init_with_custom_dir(self, temp_storage):
        """Test initialization with custom directory"""
        registry = StrategyRegistry(storage_dir=temp_storage)
        assert registry.storage_dir == temp_storage
        assert registry.storage_dir.exists()
    
    def test_init_creates_directory(self, temp_storage):
        """Test that init creates storage directory if missing"""
        subdir = temp_storage / "strategies"
        assert not subdir.exists()
        
        registry = StrategyRegistry(storage_dir=subdir)
        assert subdir.exists()


class TestAutoIncrement:
    """Test auto-increment strategy numbers"""
    
    def test_first_number_is_one(self, registry):
        """Test first strategy gets number 1"""
        next_num = registry.get_next_strategy_number()
        assert next_num == 1
    
    def test_increments_after_save(self, registry, sample_strategy):
        """Test number increments after saving"""
        # Save strategy 1
        registry.save_strategy(sample_strategy, validate=False)
        
        # Next should be 2
        next_num = registry.get_next_strategy_number()
        assert next_num == 2
    
    def test_finds_gaps(self, registry, sample_strategy):
        """Test finds gaps in numbering"""
        # Save strategies 1, 2, 4 (skip 3)
        for num in [1, 2, 4]:
            config = sample_strategy.model_copy()
            config.strategy_number = num
            config.strategy_name = f"strategy_{num:02d}_test"
            registry.save_strategy(config, validate=False)
        
        # Next should be 3 (the gap)
        next_num = registry.get_next_strategy_number()
        assert next_num == 3


class TestSaveStrategy:
    """Test saving strategies"""
    
    def test_save_creates_file(self, registry, sample_strategy):
        """Test save creates JSON file"""
        filepath = registry.save_strategy(sample_strategy, validate=False)
        
        assert filepath.exists()
        assert filepath.suffix == '.json'
    
    def test_save_validates_by_default(self, registry):
        """Test save validates strategy by default"""
        # Create invalid strategy (non-existent block)
        invalid_strategy = StrategyConfiguration(
            strategy_name="invalid",
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
        
        # Should raise error due to validation
        with pytest.raises(ValueError, match="validation failed"):
            registry.save_strategy(invalid_strategy, validate=True)
    
    def test_save_without_validation(self, registry):
        """Test can skip validation"""
        invalid_strategy = StrategyConfiguration(
            strategy_name="invalid",
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
        
        # Should succeed without validation
        filepath = registry.save_strategy(invalid_strategy, validate=False)
        assert filepath.exists()
    
    def test_save_prevents_overwrite(self, registry, sample_strategy):
        """Test prevents overwriting without explicit flag"""
        # Save once
        registry.save_strategy(sample_strategy, validate=False)
        
        # Try to save again
        with pytest.raises(ValueError, match="already exists"):
            registry.save_strategy(sample_strategy, validate=False, overwrite=False)
    
    def test_save_allows_overwrite(self, registry, sample_strategy):
        """Test can overwrite with flag"""
        # Save once
        filepath1 = registry.save_strategy(sample_strategy, validate=False)
        
        # Save again with overwrite
        filepath2 = registry.save_strategy(sample_strategy, validate=False, overwrite=True)
        
        assert filepath1 == filepath2
        assert filepath2.exists()


class TestLoadStrategy:
    """Test loading strategies"""
    
    def test_load_returns_config(self, registry, sample_strategy):
        """Test load returns StrategyConfiguration"""
        # Save strategy
        registry.save_strategy(sample_strategy, validate=False)
        
        # Load it back
        loaded = registry.load_strategy(1)
        
        assert loaded is not None
        assert isinstance(loaded, StrategyConfiguration)
        assert loaded.strategy_number == 1
    
    def test_load_nonexistent_returns_none(self, registry):
        """Test loading non-existent strategy returns None"""
        loaded = registry.load_strategy(999)
        assert loaded is None
    
    def test_loaded_equals_saved(self, registry, sample_strategy):
        """Test loaded strategy equals saved"""
        # Save
        registry.save_strategy(sample_strategy, validate=False)
        
        # Load
        loaded = registry.load_strategy(1)
        
        # Compare
        assert loaded.strategy_name == sample_strategy.strategy_name
        assert loaded.strategy_category == sample_strategy.strategy_category
        assert len(loaded.blocks) == len(sample_strategy.blocks)


class TestListStrategies:
    """Test listing strategies"""
    
    def test_list_empty_returns_empty(self, registry):
        """Test list returns empty when no strategies"""
        strategies = registry.list_strategies()
        assert len(strategies) == 0
    
    def test_list_returns_metadata(self, registry, sample_strategy):
        """Test list returns StrategyMetadata objects"""
        # Save some strategies
        for i in range(1, 4):
            config = sample_strategy.model_copy()
            config.strategy_number = i
            config.strategy_name = f"strategy_{i:02d}_test"
            registry.save_strategy(config, validate=False)
        
        # List them
        strategies = registry.list_strategies()
        
        assert len(strategies) == 3
        assert all(hasattr(s, 'number') for s in strategies)
        assert all(hasattr(s, 'name') for s in strategies)
    
    def test_list_filter_by_category(self, registry, sample_strategy):
        """Test filtering by category"""
        # Save reversal strategy
        registry.save_strategy(sample_strategy, validate=False)
        
        # Save continuation strategy
        config2 = sample_strategy.model_copy()
        config2.strategy_number = 2
        config2.strategy_name = "strategy_02_continuation"
        config2.strategy_category = StrategyCategory.CONTINUATION
        registry.save_strategy(config2, validate=False)
        
        # Filter by REVERSAL
        reversal = registry.list_strategies(category=StrategyCategory.REVERSAL)
        assert len(reversal) == 1
        assert reversal[0].category == StrategyCategory.REVERSAL


class TestSearchStrategies:
    """Test searching strategies"""
    
    def test_search_finds_match(self, registry, sample_strategy):
        """Test search finds matching strategies"""
        # Save strategies
        for i, name in enumerate(['reversal_m', 'reversal_w', 'continuation_trend'], 1):
            config = sample_strategy.model_copy()
            config.strategy_number = i
            config.strategy_name = f"strategy_{i:02d}_{name}"
            registry.save_strategy(config, validate=False)
        
        # Search for 'reversal'
        results = registry.search_strategies('reversal')
        assert len(results) == 2
    
    def test_search_case_insensitive(self, registry, sample_strategy):
        """Test search is case-insensitive"""
        registry.save_strategy(sample_strategy, validate=False)
        
        results_lower = registry.search_strategies('test')
        results_upper = registry.search_strategies('TEST')
        
        assert len(results_lower) == len(results_upper)


class TestDeleteStrategy:
    """Test deleting strategies"""
    
    def test_delete_removes_file(self, registry, sample_strategy):
        """Test delete removes file"""
        # Save
        filepath = registry.save_strategy(sample_strategy, validate=False)
        assert filepath.exists()
        
        # Delete
        success = registry.delete_strategy(1)
        assert success
        assert not filepath.exists()
    
    def test_delete_nonexistent_returns_false(self, registry):
        """Test deleting non-existent returns false"""
        success = registry.delete_strategy(999)
        assert not success


class TestStrategyCount:
    """Test counting strategies"""
    
    def test_count_empty(self, registry):
        """Test count is 0 when empty"""
        count = registry.get_strategy_count()
        assert count == 0
    
    def test_count_after_saves(self, registry, sample_strategy):
        """Test count increases after saves"""
        # Save 3 strategies
        for i in range(1, 4):
            config = sample_strategy.model_copy()
            config.strategy_number = i
            config.strategy_name = f"strategy_{i:02d}_test"
            registry.save_strategy(config, validate=False)
        
        count = registry.get_strategy_count()
        assert count == 3


class TestCategoryCounts:
    """Test category counting"""
    
    def test_category_counts(self, registry, sample_strategy):
        """Test get_category_counts returns correct counts"""
        # Save 2 reversal, 1 continuation
        for i in range(1, 3):
            config = sample_strategy.model_copy()
            config.strategy_number = i
            config.strategy_category = StrategyCategory.REVERSAL
            registry.save_strategy(config, validate=False)
        
        config3 = sample_strategy.model_copy()
        config3.strategy_number = 3
        config3.strategy_category = StrategyCategory.CONTINUATION
        registry.save_strategy(config3, validate=False)
        
        counts = registry.get_category_counts()
        assert counts[StrategyCategory.REVERSAL] == 2
        assert counts[StrategyCategory.CONTINUATION] == 1


class TestExportImport:
    """Test export and import"""
    
    def test_export_creates_file(self, registry, sample_strategy, temp_storage):
        """Test export creates file at specified location"""
        # Save strategy
        registry.save_strategy(sample_strategy, validate=False)
        
        # Export
        export_path = temp_storage / "exported.json"
        success = registry.export_strategy(1, export_path)
        
        assert success
        assert export_path.exists()
    
    def test_import_loads_strategy(self, registry, sample_strategy, temp_storage):
        """Test import loads and saves strategy"""
        # Create export file
        export_path = temp_storage / "import_test.json"
        strategy_dict = sample_strategy.model_dump()
        with open(export_path, 'w') as f:
            json.dump(strategy_dict, f)
        
        # Import
        imported = registry.import_strategy(export_path, validate=False)
        
        assert imported is not None
        assert imported.strategy_number == 1  # Auto-assigned


class TestFilenameGeneration:
    """Test filename generation"""
    
    def test_filename_format(self, registry, sample_strategy):
        """Test filename uses correct format"""
        filepath = registry.save_strategy(sample_strategy, validate=False)
        
        # Should be: strategy_001_test_strategy.json
        assert filepath.name.startswith('strategy_001_')
        assert filepath.suffix == '.json'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])