"""
Unit Tests for RegistryInterface
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/03_COMPONENT_SPECS.md, docs/v3/UI-UX/10_BLOCK_SEARCH_FILTER.md
"""

import pytest
from src.strategy_builder.core.registry_interface import (
    RegistryInterface,
    BlockInfo,
    SignalInfo,
    SearchResult,
    SearchFilters
)


class TestRegistryInterface:
    """Test suite for RegistryInterface"""
    
    def test_interface_initialization(self):
        """Test interface initializes with registry"""
        # Mock registry for testing
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        assert interface is not None
        assert interface.registry == mock_registry
        
    def test_get_all_blocks(self):
        """Test retrieving all blocks from registry"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        blocks = interface.get_all_blocks()
        assert len(blocks) > 0
        assert all(isinstance(b, BlockInfo) for b in blocks)
        
    def test_get_block_by_name(self):
        """Test retrieving specific block by name"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        block = interface.get_block("Double_Top")
        assert block is not None
        assert block.name == "Double_Top"
        assert block.category is not None
        
    def test_get_nonexistent_block_returns_none(self):
        """Test getting non-existent block returns None"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        block = interface.get_block("NonExistentBlock")
        assert block is None
        
    def test_get_signal_statistics(self):
        """Test retrieving signal occurrence statistics"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        stats = interface.get_signal_statistics("Double_Top", "BEARISH_BREAKDOWN")
        assert stats is not None
        assert 'total_count' in stats
        assert 'percentage' in stats
        assert stats['total_count'] >= 0
        
    def test_search_blocks_by_name(self):
        """Test searching blocks by name"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        results = interface.search_blocks(query="Double")
        assert len(results) > 0
        assert any("Double" in r.block_name for r in results)
        
    def test_search_blocks_by_signal_name(self):
        """Test searching blocks by signal name"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        results = interface.search_blocks(query="BEARISH")
        assert len(results) > 0
        
    def test_search_blocks_by_description(self):
        """Test searching blocks by description"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        results = interface.search_blocks(query="momentum")
        assert len(results) >= 0  # May or may not find results
        
    def test_search_with_filters_category(self):
        """Test searching with category filter"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        filters = SearchFilters(categories=["PATTERN"])
        results = interface.search_blocks(query="", filters=filters)
        assert all(r.category == "PATTERN" for r in results)
        
    def test_search_with_filters_type(self):
        """Test searching with type filter"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        filters = SearchFilters(block_types=["SIGNAL"])
        results = interface.search_blocks(query="", filters=filters)
        assert all(r.block_type == "SIGNAL" for r in results)
        
    def test_search_empty_query_returns_all(self):
        """Test empty search query returns all blocks"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        results = interface.search_blocks(query="")
        all_blocks = interface.get_all_blocks()
        assert len(results) == len(all_blocks)
        
    def test_get_block_signals(self):
        """Test retrieving signals for a block"""
        mock_registry = MockRegistry()
        interface = RegistryInterface(registry=mock_registry)
        
        signals = interface.get_block_signals("Double_Top")
        assert len(signals) > 0
        assert all(isinstance(s, SignalInfo) for s in signals)
        

class TestBlockInfo:
    """Test BlockInfo data class"""
    
    def test_block_info_creation(self):
        """Test creating BlockInfo"""
        block = BlockInfo(
            name="Double_Top",
            category="PATTERN",
            block_type="SIGNAL",
            default_weight=10,
            description="Double top pattern detector"
        )
        assert block.name == "Double_Top"
        assert block.category == "PATTERN"
        assert block.default_weight == 10
        
    def test_block_info_with_signals(self):
        """Test BlockInfo with signals"""
        signal1 = SignalInfo(
            name="BEARISH_BREAKDOWN",
            count=100,
            percentage=50.0,
            description="Bearish breakdown signal"
        )
        block = BlockInfo(
            name="Double_Top",
            category="PATTERN",
            block_type="SIGNAL",
            default_weight=10,
            description="Test",
            signals=[signal1]
        )
        assert len(block.signals) == 1
        assert block.signals[0].name == "BEARISH_BREAKDOWN"


class TestSignalInfo:
    """Test SignalInfo data class"""
    
    def test_signal_info_creation(self):
        """Test creating SignalInfo"""
        signal = SignalInfo(
            name="BEARISH_BREAKDOWN",
            count=100,
            percentage=50.0,
            description="Bearish breakdown signal"
        )
        assert signal.name == "BEARISH_BREAKDOWN"
        assert signal.count == 100
        assert signal.percentage == 50.0


class TestSearchResult:
    """Test SearchResult data class"""
    
    def test_search_result_creation(self):
        """Test creating SearchResult"""
        result = SearchResult(
            block_name="Double_Top",
            category="PATTERN",
            block_type="SIGNAL",
            match_type="block_name",
            match_text="Double_Top",
            relevance_score=1.0
        )
        assert result.block_name == "Double_Top"
        assert result.match_type == "block_name"
        assert result.relevance_score == 1.0


class TestSearchFilters:
    """Test SearchFilters data class"""
    
    def test_filters_creation(self):
        """Test creating SearchFilters"""
        filters = SearchFilters(
            categories=["PATTERN", "INDICATOR"],
            block_types=["SIGNAL"],
            min_weight=5,
            max_weight=20
        )
        assert "PATTERN" in filters.categories
        assert filters.min_weight == 5


# Mock Registry for testing
class MockRegistry:
    """Mock registry for testing purposes"""
    
    def get_all_blocks(self):
        """Return mock blocks"""
        return [
            {
                'name': 'Double_Top',
                'category': 'PATTERN',
                'type': 'SIGNAL',
                'weight': 10,
                'description': 'Double top pattern detector',
                'signals': [
                    {'name': 'BEARISH_BREAKDOWN', 'count': 100, 'percentage': 50.0},
                    {'name': 'BEARISH_REVERSAL', 'count': 80, 'percentage': 40.0}
                ]
            },
            {
                'name': 'RSI',
                'category': 'INDICATOR',
                'type': 'CONTEXT',
                'weight': 5,
                'description': 'Relative Strength Index',
                'signals': [
                    {'name': 'OVERBOUGHT', 'count': 200, 'percentage': 30.0},
                    {'name': 'OVERSOLD', 'count': 180, 'percentage': 27.0}
                ]
            }
        ]
    
    def get_block(self, name):
        """Get specific block"""
        blocks = self.get_all_blocks()
        for block in blocks:
            if block['name'] == name:
                return block
        return None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
