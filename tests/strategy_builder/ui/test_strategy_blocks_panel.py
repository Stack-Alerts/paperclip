"""
Unit tests for Strategy Blocks Panel UI Component

Tests all functionality of the StrategyBlocksPanel widget including:
- Block display
- Reordering (up/down)
- Removal
- Signal emission
- Integration with orchestrator

Author: Strategy Builder Team  
Date: 2026-01-16
"""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt5.QtTest import QSignalSpy

from src.strategy_builder.ui.strategy_blocks_panel import StrategyBlocksPanel, BlockConfigItem
from src.strategy_builder.integration.strategy_builder_orchestrator import StrategyBuilderOrchestrator
from src.strategy_builder.core.strategy_config_engine import StrategyConfig, BlockConfig, SignalConfig


@pytest.fixture
def mock_block_info():
    """Create mock block info dictionary."""
    return {
        'name': 'TestBlock',
        'logic': 'AND',
        'signals': [
            {'name': 'SIGNAL_1', 'logic': 'AND'},
            {'name': 'SIGNAL_2', 'logic': 'OR'}
        ]
    }


@pytest.fixture
def orchestrator():
    """Create a mock orchestrator."""
    mock_orch = Mock(spec=StrategyBuilderOrchestrator)
    mock_orch.get_current_config = Mock(return_value=None)
    return mock_orch


@pytest.fixture
def panel(qapp, orchestrator):
    """Create a StrategyBlocksPanel instance for testing."""
    return StrategyBlocksPanel(orchestrator)


class TestBlockConfigItem:
    """Test suite for BlockConfigItem widget."""
    
    def test_item_creation(self, qapp, mock_block_info):
        """Test that block config item is created successfully."""
        item = BlockConfigItem("TestBlock", mock_block_info, 1, 2)
        assert item is not None
        assert item.block_name == "TestBlock"
        assert item.position == 1
        assert item.total == 2
    
    def test_up_button_disabled_for_first(self, qapp, mock_block_info):
        """Test that up button is disabled for first block."""
        item = BlockConfigItem("TestBlock", mock_block_info, 1, 2)
        assert not item.up_button.isEnabled()
    
    def test_down_button_disabled_for_last(self, qapp, mock_block_info):
        """Test that down button is disabled for last block."""
        item = BlockConfigItem("TestBlock", mock_block_info, 2, 2)
        assert not item.down_button.isEnabled()
    
    def test_buttons_enabled_for_middle(self, qapp, mock_block_info):
        """Test that both buttons are enabled for middle block."""
        item = BlockConfigItem("TestBlock", mock_block_info, 2, 3)
        assert item.up_button.isEnabled()
        assert item.down_button.isEnabled()
    
    def test_update_position(self, qapp, mock_block_info):
        """Test updating position and button states."""
        item = BlockConfigItem("TestBlock", mock_block_info, 2, 3)
        
        # Update to first position
        item.update_position(1, 3)
        assert item.position == 1
        assert not item.up_button.isEnabled()
        assert item.down_button.isEnabled()
    
    def test_signals_emitted(self, qapp, mock_block_info):
        """Test that signals are emitted on button clicks."""
        item = BlockConfigItem("TestBlock", mock_block_info, 2, 3)
        
        # Test move up signal
        up_spy = QSignalSpy(item.move_up_clicked)
        item.up_button.click()
        assert len(up_spy) == 1
        assert up_spy[0][0] == "TestBlock"
        
        # Test move down signal
        down_spy = QSignalSpy(item.move_down_clicked)
        item.down_button.click()
        assert len(down_spy) == 1
        assert down_spy[0][0] == "TestBlock"
        
        # Test remove signal
        remove_spy = QSignalSpy(item.remove_clicked)
        item.remove_button.click()
        assert len(remove_spy) == 1
        assert remove_spy[0][0] == "TestBlock"


class TestStrategyBlocksPanelInitialization:
    """Test suite for panel initialization."""
    
    def test_panel_creation(self, panel):
        """Test that panel is created successfully."""
        assert panel is not None
        assert isinstance(panel, StrategyBlocksPanel)
    
    def test_orchestrator_is_set(self, panel, orchestrator):
        """Test that orchestrator is properly assigned."""
        assert panel.orchestrator is orchestrator
    
    def test_ui_components_initialized(self, panel):
        """Test that all UI components are initialized."""
        assert panel.blocks_scroll_area is not None
        assert panel.blocks_container is not None
        assert panel.blocks_layout is not None
        assert panel.empty_label is not None
    
    def test_block_items_list_initialized(self, panel):
        """Test that block_items list is initialized."""
        assert panel.block_items is not None
        assert isinstance(panel.block_items, list)
        assert len(panel.block_items) == 0
    
    def test_empty_state_shown(self, panel):
        """Test that empty state is shown when no blocks."""
        panel.show()  # Show panel for visibility checks
        assert panel.empty_label.isVisible()


class TestStrategyBlocksPanelBlockDisplay:
    """Test suite for block display functionality."""
    
    def test_displays_blocks_from_config(self, qapp, orchestrator):
        """Test that blocks are displayed from configuration."""
        # Create mock config with blocks
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        signal2 = SignalConfig(name="SIGNAL_2", logic="OR")
        
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        block2 = BlockConfig(name="Block2", logic="AND", signals=[signal2])
        
        config = StrategyConfig(name="TestStrategy", blocks=[block1, block2])
        orchestrator.get_current_config = Mock(return_value=config)
        
        # Create panel
        panel = StrategyBlocksPanel(orchestrator)
        
        # Should have 2 block items
        assert len(panel.block_items) == 2
        assert panel.block_items[0].block_name == "Block1"
        assert panel.block_items[1].block_name == "Block2"
        
        # Empty label should be hidden
        assert not panel.empty_label.isVisible()
    
    def test_get_block_count(self, qapp, orchestrator):
        """Test getting block count."""
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        config = StrategyConfig(name="TestStrategy", blocks=[block1])
        orchestrator.get_current_config = Mock(return_value=config)
        
        panel = StrategyBlocksPanel(orchestrator)
        assert panel.get_block_count() == 1
    
    def test_get_block_names(self, qapp, orchestrator):
        """Test getting block names in order."""
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        block2 = BlockConfig(name="Block2", logic="AND", signals=[signal1])
        
        config = StrategyConfig(name="TestStrategy", blocks=[block1, block2])
        orchestrator.get_current_config = Mock(return_value=config)
        
        panel = StrategyBlocksPanel(orchestrator)
        names = panel.get_block_names()
        assert names == ["Block1", "Block2"]


class TestStrategyBlocksPanelReordering:
    """Test suite for block reordering."""
    
    def test_move_up_success(self, qapp, orchestrator):
        """Test successful move up operation."""
        # Setup
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        block2 = BlockConfig(name="Block2", logic="AND", signals=[signal1])
        config = StrategyConfig(name="TestStrategy", blocks=[block1, block2])
        
        orchestrator.get_current_config = Mock(return_value=config)
        
        mock_result = Mock()
        mock_result.success = True
        orchestrator.reorder_block = Mock(return_value=mock_result)
        
        panel = StrategyBlocksPanel(orchestrator)
        
        # Move block2 up
        panel.block_items[1].up_button.click()
        
        # Verify orchestrator was called
        orchestrator.reorder_block.assert_called_with("Block2", "up")
    
    def test_move_down_success(self, qapp, orchestrator):
        """Test successful move down operation."""
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        block2 = BlockConfig(name="Block2", logic="AND", signals=[signal1])
        config = StrategyConfig(name="TestStrategy", blocks=[block1, block2])
        
        orchestrator.get_current_config = Mock(return_value=config)
        
        mock_result = Mock()
        mock_result.success = True
        orchestrator.reorder_block = Mock(return_value=mock_result)
        
        panel = StrategyBlocksPanel(orchestrator)
        
        # Move block1 down
        panel.block_items[0].down_button.click()
        
        # Verify orchestrator was called
        orchestrator.reorder_block.assert_called_with("Block1", "down")


class TestStrategyBlocksPanelRemoval:
    """Test suite for block removal."""
    
    def test_remove_block_success(self, qapp, orchestrator):
        """Test successful block removal."""
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        config = StrategyConfig(name="TestStrategy", blocks=[block1])
        
        orchestrator.get_current_config = Mock(return_value=config)
        
        mock_result = Mock()
        mock_result.success = True
        orchestrator.remove_block = Mock(return_value=mock_result)
        
        panel = StrategyBlocksPanel(orchestrator)
        
        # Remove block
        panel.block_items[0].remove_button.click()
        
        # Verify orchestrator was called
        orchestrator.remove_block.assert_called_with("Block1")


class TestStrategyBlocksPanelSignals:
    """Test suite for Qt signals."""
    
    def test_blocks_changed_signal_on_reorder(self, qapp, orchestrator):
        """Test that blocks_changed signal is emitted on reorder."""
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        block2 = BlockConfig(name="Block2", logic="AND", signals=[signal1])
        config = StrategyConfig(name="TestStrategy", blocks=[block1, block2])
        
        orchestrator.get_current_config = Mock(return_value=config)
        
        mock_result = Mock()
        mock_result.success = True
        orchestrator.reorder_block = Mock(return_value=mock_result)
        
        panel = StrategyBlocksPanel(orchestrator)
        spy = QSignalSpy(panel.blocks_changed)
        
        # Move block
        panel.block_items[0].down_button.click()
        
        # Signal should be emitted
        assert len(spy) == 1
    
    def test_blocks_changed_signal_on_remove(self, qapp, orchestrator):
        """Test that blocks_changed signal is emitted on remove."""
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        config = StrategyConfig(name="TestStrategy", blocks=[block1])
        
        orchestrator.get_current_config = Mock(return_value=config)
        
        mock_result = Mock()
        mock_result.success = True
        orchestrator.remove_block = Mock(return_value=mock_result)
        
        panel = StrategyBlocksPanel(orchestrator)
        spy = QSignalSpy(panel.blocks_changed)
        
        # Remove block
        panel.block_items[0].remove_button.click()
        
        # Signal should be emitted
        assert len(spy) == 1


class TestStrategyBlocksPanelRefresh:
    """Test suite for refresh functionality."""
    
    def test_refresh_from_orchestrator(self, qapp, orchestrator):
        """Test refreshing display from orchestrator."""
        # Start with no blocks
        orchestrator.get_current_config = Mock(return_value=None)
        panel = StrategyBlocksPanel(orchestrator)
        assert len(panel.block_items) == 0
        
        # Update config to have blocks
        signal1 = SignalConfig(name="SIGNAL_1", logic="AND")
        block1 = BlockConfig(name="Block1", logic="AND", signals=[signal1])
        config = StrategyConfig(name="TestStrategy", blocks=[block1])
        orchestrator.get_current_config = Mock(return_value=config)
        
        # Refresh
        panel.refresh_from_orchestrator()
        
        # Should now have 1 block
        assert len(panel.block_items) == 1


class TestStrategyBlocksPanelAddBlock:
    """Test suite for adding blocks."""
    
    def test_add_block_success(self, qapp, orchestrator):
        """Test successfully adding a block."""
        orchestrator.get_current_config = Mock(return_value=None)
        
        mock_result = Mock()
        mock_result.success = True
        orchestrator.add_block = Mock(return_value=mock_result)
        
        panel = StrategyBlocksPanel(orchestrator)
        
        result = panel.add_block("NewBlock")
        
        assert result is True
        orchestrator.add_block.assert_called_with("NewBlock")
    
    def test_add_block_failure(self, qapp, orchestrator):
        """Test handling add block failure."""
        orchestrator.get_current_config = Mock(return_value=None)
        
        mock_result = Mock()
        mock_result.success = False
        mock_result.message = "Block already exists"
        orchestrator.add_block = Mock(return_value=mock_result)
        
        panel = StrategyBlocksPanel(orchestrator)
        
        result = panel.add_block("NewBlock")
        
        assert result is False


class TestStrategyBlocksPanelIntegration:
    """Integration tests with real orchestrator."""
    
    def test_with_real_orchestrator(self, qapp):
        """Test panel works with real orchestrator."""
        real_orchestrator = StrategyBuilderOrchestrator()
        
        # Create strategy
        real_orchestrator.create_strategy("TestStrategy", "Test description")
        
        # Create panel
        panel = StrategyBlocksPanel(real_orchestrator)
        panel.show()  # Show panel for visibility checks
        
        # Should show empty state
        assert panel.get_block_count() == 0
        assert panel.empty_label.isVisible()


# Run tests with: python -m pytest tests/strategy_builder/ui/test_strategy_blocks_panel.py -v
