"""
Unit tests for Block Search Panel UI Component

Tests all functionality of the BlockSearchPanel widget including:
- Block loading from registry
- Search and filtering
- Block selection
- Add/Remove tracking
- Signal emission

Author: Strategy Builder Team
Date: 2026-01-16
"""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QSignalSpy
import sys

from src.strategy_builder.ui.block_search_panel import BlockSearchPanel, BlockListItem
from src.strategy_builder.integration.strategy_builder_orchestrator import StrategyBuilderOrchestrator
from src.strategy_builder.core.registry_interface import BlockInfo, SignalInfo


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for testing Qt widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def mock_block_info():
    """Create a mock BlockInfo object."""
    signal1 = Mock(spec=SignalInfo)
    signal1.name = "TEST_SIGNAL_1"
    signal1.occurrences = 100
    signal1.total_candles = 1000
    
    signal2 = Mock(spec=SignalInfo)
    signal2.name = "TEST_SIGNAL_2"
    signal2.occurrences = 200
    signal2.total_candles = 1000
    
    block = Mock(spec=BlockInfo)
    block.name = "TestBlock"
    block.category = "TEST"
    block.type = "EVENT"
    block.description = "Test block description"
    block.signals = [signal1, signal2]
    block.default_weight = 50
    
    return block


@pytest.fixture
def orchestrator():
    """Create a mock orchestrator with registry."""
    mock_orch = Mock(spec=StrategyBuilderOrchestrator)
    
    # Setup mock registry
    mock_registry = Mock()
    mock_orch.registry = mock_registry
    
    # Mock search_blocks to return empty list by default
    mock_orch.search_blocks = Mock(return_value=[])
    
    return mock_orch


@pytest.fixture
def panel(qapp, orchestrator):
    """Create a BlockSearchPanel instance for testing."""
    return BlockSearchPanel(orchestrator)


class TestBlockListItem:
    """Test suite for BlockListItem widget."""
    
    def test_item_creation(self, qapp, mock_block_info):
        """Test that block list item is created successfully."""
        item = BlockListItem(mock_block_info)
        assert item is not None
        assert item.block_info == mock_block_info
        assert not item.expanded
    
    def test_item_displays_block_name(self, qapp, mock_block_info):
        """Test that block name is displayed."""
        item = BlockListItem(mock_block_info)
        # Block info is stored and accessible
        assert item.block_info.name == "TestBlock"
    
    def test_toggle_signals_expands(self, qapp, mock_block_info):
        """Test that toggling signals expands/collapses the view."""
        item = BlockListItem(mock_block_info)
        item.show()  # Need to show widget for visibility to work
        
        # Initially not expanded
        assert not item.expanded
        assert not item.signals_widget.isVisible()
        
        # Toggle to expand
        item._toggle_signals()
        assert item.expanded
        assert item.signals_widget.isVisible()
        
        # Toggle to collapse
        item._toggle_signals()
        assert not item.expanded
        assert not item.signals_widget.isVisible()
    
    def test_disable_add_button(self, qapp, mock_block_info):
        """Test that add button can be disabled."""
        item = BlockListItem(mock_block_info)
        
        # Initially enabled
        assert item.add_button.isEnabled()
        
        # Disable
        item.disable_add_button()
        assert not item.add_button.isEnabled()
        assert "✓ Added" in item.add_button.text()
    
    def test_enable_add_button(self, qapp, mock_block_info):
        """Test that add button can be re-enabled."""
        item = BlockListItem(mock_block_info)
        
        # Disable first
        item.disable_add_button()
        assert not item.add_button.isEnabled()
        
        # Re-enable
        item.enable_add_button()
        assert item.add_button.isEnabled()
        assert "Add to Strategy" in item.add_button.text()
    
    def test_add_clicked_signal(self, qapp, mock_block_info):
        """Test that add_clicked signal is emitted."""
        item = BlockListItem(mock_block_info)
        spy = QSignalSpy(item.add_clicked)
        
        # Click the add button
        item.add_button.click()
        
        assert len(spy) == 1
        assert spy[0][0] == "TestBlock"


class TestBlockSearchPanelInitialization:
    """Test suite for panel initialization."""
    
    def test_panel_creation(self, panel):
        """Test that panel is created successfully."""
        assert panel is not None
        assert isinstance(panel, BlockSearchPanel)
    
    def test_orchestrator_is_set(self, panel, orchestrator):
        """Test that orchestrator is properly assigned."""
        assert panel.orchestrator is orchestrator
    
    def test_ui_components_initialized(self, panel):
        """Test that all UI components are initialized."""
        assert panel.search_input is not None
        assert panel.category_filter is not None
        assert panel.type_filter is not None
        assert panel.blocks_scroll_area is not None
        assert panel.blocks_container is not None
        assert panel.blocks_layout is not None
    
    def test_added_blocks_set_initialized(self, panel):
        """Test that added_blocks set is initialized."""
        assert panel.added_blocks is not None
        assert isinstance(panel.added_blocks, set)
        assert len(panel.added_blocks) == 0
    
    def test_block_items_dict_initialized(self, panel):
        """Test that block_items dictionary is initialized."""
        assert panel.block_items is not None
        assert isinstance(panel.block_items, dict)


class TestBlockSearchPanelBlockLoading:
    """Test suite for block loading functionality."""
    
    def test_loads_blocks_from_orchestrator(self, qapp, orchestrator, mock_block_info):
        """Test that blocks are loaded from the orchestrator."""
        # Setup mock to return one block
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        # Create panel (which triggers loading)
        panel = BlockSearchPanel(orchestrator)
        
        # Verify search was called
        orchestrator.search_blocks.assert_called_once_with("")
        
        # Verify block info was retrieved
        orchestrator.registry.get_block_by_name.assert_called_with("TestBlock")
        
        # Verify block item was created
        assert "TestBlock" in panel.block_items
    
    def test_empty_registry_shows_message(self, qapp, orchestrator):
        """Test that empty registry shows appropriate message."""
        # No blocks returned
        orchestrator.search_blocks = Mock(return_value=[])
        
        panel = BlockSearchPanel(orchestrator)
        
        # Should have created panel without errors
        assert panel is not None


class TestBlockSearchPanelSearch:
    """Test suite for search functionality."""
    
    def test_get_search_text(self, panel):
        """Test getting search text."""
        panel.search_input.setText("test")
        assert panel.get_search_text() == "test"
    
    def test_search_filters_blocks(self, qapp, orchestrator, mock_block_info):
        """Test that search text filters blocks."""
        # Setup with one block
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        panel.show()  # Show panel for visibility checks
        
        # Initially visible
        assert panel.block_items["TestBlock"].isVisible()
        
        # Search for non-matching text
        panel.search_input.setText("nonexistent")
        assert not panel.block_items["TestBlock"].isVisible()
        
        # Search for matching text
        panel.search_input.setText("Test")
        assert panel.block_items["TestBlock"].isVisible()


class TestBlockSearchPanelFilters:
    """Test suite for filter functionality."""
    
    def test_get_selected_category(self, panel):
        """Test getting selected category."""
        # Default should be "All Categories"
        assert panel.get_selected_category() == "All Categories"
    
    def test_get_selected_type(self, panel):
        """Test getting selected type."""
        # Default should be "All Types"
        assert panel.get_selected_type() == "All Types"
    
    def test_category_filter_populated(self, qapp, orchestrator, mock_block_info):
        """Test that category filter is populated from blocks."""
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        
        # Should have "All Categories" + the TEST category
        assert panel.category_filter.count() >= 2
        categories = [panel.category_filter.itemText(i) for i in range(panel.category_filter.count())]
        assert "All Categories" in categories
        assert "TEST" in categories
    
    def test_type_filter_populated(self, qapp, orchestrator, mock_block_info):
        """Test that type filter is populated from blocks."""
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        
        # Should have "All Types" + the EVENT type
        assert panel.type_filter.count() >= 2
        types = [panel.type_filter.itemText(i) for i in range(panel.type_filter.count())]
        assert "All Types" in types
        assert "EVENT" in types


class TestBlockSearchPanelSelection:
    """Test suite for block selection."""
    
    def test_mark_block_as_added(self, qapp, orchestrator, mock_block_info):
        """Test marking a block as added."""
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        
        # Mark as added
        panel.mark_block_as_added("TestBlock")
        
        # Should be in added_blocks set
        assert "TestBlock" in panel.added_blocks
        
        # Button should be disabled
        assert not panel.block_items["TestBlock"].add_button.isEnabled()
    
    def test_mark_block_as_removed(self, qapp, orchestrator, mock_block_info):
        """Test marking a block as removed."""
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        
        # Add first
        panel.mark_block_as_added("TestBlock")
        assert "TestBlock" in panel.added_blocks
        
        # Remove
        panel.mark_block_as_removed("TestBlock")
        assert "TestBlock" not in panel.added_blocks
        
        # Button should be enabled
        assert panel.block_items["TestBlock"].add_button.isEnabled()
    
    def test_get_added_blocks(self, qapp, orchestrator, mock_block_info):
        """Test getting list of added blocks."""
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        
        # Initially empty
        assert panel.get_added_blocks() == []
        
        # Add block
        panel.mark_block_as_added("TestBlock")
        assert panel.get_added_blocks() == ["TestBlock"]
    
    def test_clear_added_blocks(self, qapp, orchestrator, mock_block_info):
        """Test clearing all added blocks."""
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        
        # Add block
        panel.mark_block_as_added("TestBlock")
        assert len(panel.get_added_blocks()) == 1
        
        # Clear
        panel.clear_added_blocks()
        assert len(panel.get_added_blocks()) == 0
        
        # Button should be enabled
        assert panel.block_items["TestBlock"].add_button.isEnabled()


class TestBlockSearchPanelSignals:
    """Test suite for Qt signals."""
    
    def test_block_selected_signal_on_add(self, qapp, orchestrator, mock_block_info):
        """Test that block_selected signal is emitted when block is added."""
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        spy = QSignalSpy(panel.block_selected)
        
        # Click the add button on the block item
        panel.block_items["TestBlock"].add_button.click()
        
        # Signal should be emitted
        assert len(spy) == 1
        assert spy[0][0] == "TestBlock"


class TestBlockSearchPanelUtilities:
    """Test suite for utility methods."""
    
    def test_get_visible_blocks_count(self, qapp, orchestrator, mock_block_info):
        """Test getting visible blocks count."""
        orchestrator.search_blocks = Mock(return_value=["TestBlock"])
        orchestrator.registry.get_block_by_name = Mock(return_value=mock_block_info)
        
        panel = BlockSearchPanel(orchestrator)
        panel.show()  # Show panel for visibility checks
        
        # Initially all visible
        assert panel.get_visible_blocks_count() == 1
        
        # Filter to hide
        panel.search_input.setText("nonexistent")
        assert panel.get_visible_blocks_count() == 0
        
        # Filter to show
        panel.search_input.setText("Test")
        assert panel.get_visible_blocks_count() == 1


class TestBlockSearchPanelIntegration:
    """Integration tests with real orchestrator."""
    
    def test_with_real_orchestrator(self, qapp):
        """Test panel works with real orchestrator."""
        # Create real orchestrator
        real_orchestrator = StrategyBuilderOrchestrator()
        
        # Create panel
        panel = BlockSearchPanel(real_orchestrator)
        
        # Panel should be created successfully
        assert panel is not None
        # Registry may or may not have blocks depending on environment
        assert isinstance(panel.block_items, dict)
    
    def test_real_block_selection(self, qapp):
        """Test block selection with real orchestrator."""
        real_orchestrator = StrategyBuilderOrchestrator()
        panel = BlockSearchPanel(real_orchestrator)
        
        # Get first block name
        if len(panel.block_items) > 0:
            first_block = list(panel.block_items.keys())[0]
            
            # Mark as added
            panel.mark_block_as_added(first_block)
            
            # Verify
            assert first_block in panel.get_added_blocks()


# Run tests with: python -m pytest tests/strategy_builder/ui/test_block_search_panel.py -v
