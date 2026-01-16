"""
Unit tests for Strategy Information Panel UI Component

Tests all functionality of the StrategyInfoPanel widget including:
- UI initialization
- Signal emission
- Getter/setter methods
- Integration with orchestrator
- Auto-update functionality

Author: Strategy Builder Team
Date: 2026-01-16
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QSignalSpy
import sys

from src.strategy_builder.ui.strategy_info_panel import StrategyInfoPanel
from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)
from src.strategy_builder.core.strategy_config_engine import StrategyConfig, BlockConfig, SignalConfig


# Fixture for QApplication (required for Qt widgets)
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for testing Qt widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def orchestrator():
    """Create a mock orchestrator for testing."""
    mock_orch = Mock(spec=StrategyBuilderOrchestrator)
    mock_orch.get_current_config = Mock(return_value=None)
    return mock_orch


@pytest.fixture
def panel(qapp, orchestrator):
    """Create a StrategyInfoPanel instance for testing."""
    return StrategyInfoPanel(orchestrator)


class TestStrategyInfoPanelInitialization:
    """Test suite for panel initialization."""
    
    def test_panel_creation(self, panel):
        """Test that panel is created successfully."""
        assert panel is not None
        assert isinstance(panel, StrategyInfoPanel)
    
    def test_orchestrator_is_set(self, panel, orchestrator):
        """Test that orchestrator is properly assigned."""
        assert panel.orchestrator is orchestrator
    
    def test_ui_components_initialized(self, panel):
        """Test that all UI components are initialized."""
        assert panel.name_input is not None
        assert panel.description_text is not None
        assert panel.bullish_radio is not None
        assert panel.bearish_radio is not None
        assert panel.type_button_group is not None
        assert panel.required_signals_label is not None
    
    def test_default_values(self, panel):
        """Test default values are set correctly."""
        assert panel.get_strategy_name() == ""
        assert panel.get_strategy_type() == "Bullish"
        assert panel.get_required_signals() == 0
    
    def test_bullish_radio_checked_by_default(self, panel):
        """Test that Bullish radio is checked by default."""
        assert panel.bullish_radio.isChecked()
        assert not panel.bearish_radio.isChecked()


class TestStrategyInfoPanelGettersSetters:
    """Test suite for getter and setter methods."""
    
    def test_get_set_strategy_name(self, panel):
        """Test getting and setting strategy name."""
        panel.set_strategy_name("Test_Strategy")
        assert panel.get_strategy_name() == "Test_Strategy"
    
    def test_get_set_strategy_name_with_whitespace(self, panel):
        """Test that get_strategy_name strips whitespace."""
        panel.set_strategy_name("  Test_Strategy  ")
        assert panel.get_strategy_name() == "Test_Strategy"
    
    def test_get_set_strategy_type_bullish(self, panel):
        """Test setting strategy type to Bullish."""
        panel.set_strategy_type("Bullish")
        assert panel.get_strategy_type() == "Bullish"
        assert panel.bullish_radio.isChecked()
        assert not panel.bearish_radio.isChecked()
    
    def test_get_set_strategy_type_bearish(self, panel):
        """Test setting strategy type to Bearish."""
        panel.set_strategy_type("Bearish")
        assert panel.get_strategy_type() == "Bearish"
        assert panel.bearish_radio.isChecked()
        assert not panel.bullish_radio.isChecked()
    
    def test_set_strategy_type_case_insensitive(self, panel):
        """Test that set_strategy_type is case-insensitive."""
        panel.set_strategy_type("BULLISH")
        assert panel.get_strategy_type() == "Bullish"
        
        panel.set_strategy_type("bearish")
        assert panel.get_strategy_type() == "Bearish"
    
    def test_get_set_description(self, panel):
        """Test getting and setting description."""
        desc = "This is a test strategy description"
        panel.set_description(desc)
        assert panel.get_description() == desc
    
    def test_get_set_required_signals(self, panel):
        """Test getting and setting required signals count."""
        panel.set_required_signals(5)
        assert panel.get_required_signals() == 5
        assert panel.required_signals_label.text() == "5"
    
    def test_required_signals_color_coding_zero(self, panel):
        """Test color coding for 0 required signals (gray)."""
        panel.set_required_signals(0)
        assert "#888888" in panel.required_signals_label.styleSheet()
    
    def test_required_signals_color_coding_low(self, panel):
        """Test color coding for 1-5 required signals (green)."""
        panel.set_required_signals(3)
        assert "#00aa00" in panel.required_signals_label.styleSheet()
    
    def test_required_signals_color_coding_medium(self, panel):
        """Test color coding for 6-10 required signals (blue)."""
        panel.set_required_signals(8)
        assert "#0066cc" in panel.required_signals_label.styleSheet()
    
    def test_required_signals_color_coding_high(self, panel):
        """Test color coding for >10 required signals (orange)."""
        panel.set_required_signals(15)
        assert "#ff6600" in panel.required_signals_label.styleSheet()


class TestStrategyInfoPanelSignals:
    """Test suite for Qt signal emissions."""
    
    def test_strategy_name_changed_signal(self, panel):
        """Test that strategy_name_changed signal is emitted."""
        spy = QSignalSpy(panel.strategy_name_changed)
        
        panel.name_input.setText("New_Strategy")
        
        assert len(spy) > 0
        # Last emitted value should be the full text
        assert spy[-1][0] == "New_Strategy"
    
    def test_strategy_type_changed_signal_to_bearish(self, panel):
        """Test that strategy_type_changed signal is emitted when changing to Bearish."""
        spy = QSignalSpy(panel.strategy_type_changed)
        
        panel.bearish_radio.setChecked(True)
        
        assert len(spy) > 0
        assert spy[-1][0] == "Bearish"
    
    def test_strategy_type_changed_signal_to_bullish(self, panel):
        """Test that strategy_type_changed signal is emitted when changing to Bullish."""
        # First set to Bearish
        panel.bearish_radio.setChecked(True)
        
        spy = QSignalSpy(panel.strategy_type_changed)
        
        panel.bullish_radio.setChecked(True)
        
        assert len(spy) > 0
        assert spy[-1][0] == "Bullish"


class TestStrategyInfoPanelOrchestrator:
    """Test suite for orchestrator integration."""
    
    def test_create_strategy_in_orchestrator_success(self, panel, orchestrator):
        """Test successful strategy creation in orchestrator."""
        # Setup
        panel.set_strategy_name("Test_Strategy")
        panel.set_description("Test description")
        
        mock_result = Mock()
        mock_result.success = True
        orchestrator.create_strategy = Mock(return_value=mock_result)
        
        # Execute
        result = panel.create_strategy_in_orchestrator()
        
        # Verify
        assert result is True
        orchestrator.create_strategy.assert_called_once_with("Test_Strategy", "Test description")
        assert "created" in panel.status_label.text().lower()
    
    def test_create_strategy_in_orchestrator_no_name(self, panel, orchestrator):
        """Test that creation fails without a strategy name."""
        # Setup - no name set
        panel.set_strategy_name("")
        
        # Execute
        result = panel.create_strategy_in_orchestrator()
        
        # Verify
        assert result is False
        orchestrator.create_strategy.assert_not_called()
        assert "required" in panel.status_label.text().lower()
    
    def test_create_strategy_in_orchestrator_failure(self, panel, orchestrator):
        """Test handling of orchestrator failure."""
        # Setup
        panel.set_strategy_name("Test_Strategy")
        
        mock_result = Mock()
        mock_result.success = False
        mock_result.message = "Test error"
        orchestrator.create_strategy = Mock(return_value=mock_result)
        
        # Execute
        result = panel.create_strategy_in_orchestrator()
        
        # Verify
        assert result is False
        assert "error" in panel.status_label.text().lower()
    
    def test_create_strategy_in_orchestrator_exception(self, panel, orchestrator):
        """Test handling of exceptions during creation."""
        # Setup
        panel.set_strategy_name("Test_Strategy")
        orchestrator.create_strategy = Mock(side_effect=Exception("Test exception"))
        
        # Execute
        result = panel.create_strategy_in_orchestrator()
        
        # Verify
        assert result is False
        assert "exception" in panel.status_label.text().lower()


class TestStrategyInfoPanelAutoUpdate:
    """Test suite for auto-update functionality from config."""
    
    def test_update_description_from_config_with_description(self, panel, orchestrator):
        """Test updating description when config has a description."""
        # Setup
        mock_config = Mock(spec=StrategyConfig)
        mock_config.description = "Test strategy description"
        mock_config.blocks = []
        orchestrator.get_current_config = Mock(return_value=mock_config)
        
        # Execute
        panel.update_description_from_config()
        
        # Verify
        assert panel.get_description() == "Test strategy description"
    
    def test_update_description_from_config_with_blocks(self, panel, orchestrator):
        """Test generating description from blocks when no description exists."""
        # Setup
        mock_signal1 = Mock()
        mock_signal1.name = "SIGNAL_1"
        mock_signal2 = Mock()
        mock_signal2.name = "SIGNAL_2"
        
        mock_block1 = Mock()
        mock_block1.name = "Block_1"
        mock_block1.signals = [mock_signal1, mock_signal2]
        
        mock_config = Mock()
        mock_config.description = None
        mock_config.blocks = [mock_block1]
        orchestrator.get_current_config = Mock(return_value=mock_config)
        
        # Execute
        panel.update_description_from_config()
        
        # Verify
        desc = panel.get_description()
        assert "Block_1" in desc
        assert "SIGNAL_1" in desc
    
    def test_update_description_from_config_no_blocks(self, panel, orchestrator):
        """Test description when no blocks are present."""
        # Setup
        mock_config = Mock()
        mock_config.description = None
        mock_config.blocks = []
        orchestrator.get_current_config = Mock(return_value=mock_config)
        
        # Execute
        panel.update_description_from_config()
        
        # Verify
        assert "No blocks" in panel.get_description()
    
    def test_update_description_from_config_none_config(self, panel, orchestrator):
        """Test description update when config is None."""
        # Setup
        orchestrator.get_current_config = Mock(return_value=None)
        
        # Execute
        panel.update_description_from_config()
        
        # Verify
        assert "No blocks" in panel.get_description()
    
    def test_update_required_signals_from_config_with_value(self, panel, orchestrator):
        """Test updating required signals when config has the value."""
        # Setup
        mock_config = Mock()
        mock_config.required_signals = 7
        orchestrator.get_current_config = Mock(return_value=mock_config)
        
        # Execute
        panel.update_required_signals_from_config()
        
        # Verify
        assert panel.get_required_signals() == 7
    
    def test_update_required_signals_calculates_from_blocks(self, panel, orchestrator):
        """Test calculating required signals from blocks."""
        # Setup - 2 AND signals in AND block, 1 OR block
        mock_signal1 = Mock()
        mock_signal1.logic = "AND"
        mock_signal2 = Mock()
        mock_signal2.logic = "AND"
        mock_signal3 = Mock()
        mock_signal3.logic = "OR"
        
        mock_block1 = Mock()
        mock_block1.logic = "AND"
        mock_block1.signals = [mock_signal1, mock_signal2]
        
        mock_block2 = Mock()
        mock_block2.logic = "OR"
        mock_block2.signals = [mock_signal3]
        
        mock_config = Mock()
        mock_config.blocks = [mock_block1, mock_block2]
        orchestrator.get_current_config = Mock(return_value=mock_config)
        
        # Remove required_signals attribute to trigger calculation
        del mock_config.required_signals
        
        # Execute
        panel.update_required_signals_from_config()
        
        # Verify - 2 AND signals + 1 from OR block = 3
        assert panel.get_required_signals() == 3
    
    def test_update_required_signals_handles_none_config(self, panel, orchestrator):
        """Test handling of None config when updating required signals."""
        # Setup
        orchestrator.get_current_config = Mock(return_value=None)
        
        # Execute
        panel.update_required_signals_from_config()
        
        # Verify - should default to 0
        assert panel.get_required_signals() == 0
    
    def test_refresh_from_orchestrator(self, panel, orchestrator):
        """Test complete refresh from orchestrator."""
        # Setup
        mock_config = Mock()
        mock_config.description = "Refreshed description"
        mock_config.required_signals = 5
        mock_config.blocks = []
        orchestrator.get_current_config = Mock(return_value=mock_config)
        
        panel.set_strategy_name("Test")  # Set name to verify status update
        
        # Execute
        panel.refresh_from_orchestrator()
        
        # Verify all updates happened
        assert panel.get_description() == "Refreshed description"
        assert panel.get_required_signals() == 5
        # Status should be updated since name is set
        assert "ready" in panel.status_label.text().lower()


class TestStrategyInfoPanelStatusUpdates:
    """Test suite for status indicator updates."""
    
    def test_status_update_no_name(self, panel):
        """Test status when no name is entered."""
        panel.set_strategy_name("")
        panel._update_status()
        
        assert "enter" in panel.status_label.text().lower()
        assert "#ff6600" in panel.status_label.styleSheet()  # Orange
    
    def test_status_update_with_name(self, panel):
        """Test status when name is entered."""
        panel.set_strategy_name("Test_Strategy")
        panel._update_status()
        
        assert "ready" in panel.status_label.text().lower()
        assert "#00aa00" in panel.status_label.styleSheet()  # Green
    
    def test_status_updates_on_name_change(self, panel):
        """Test that status updates automatically when name changes."""
        # Add name first - setText triggers textChanged signal which updates status
        panel.name_input.setText("New_Strategy")
        assert "ready" in panel.status_label.text().lower()
        
        # Clear name - should update to show "enter"
        panel.name_input.setText("")
        assert "enter" in panel.status_label.text().lower()


class TestStrategyInfoPanelIntegration:
    """Integration tests with real StrategyBuilderOrchestrator."""
    
    def test_with_real_orchestrator(self, qapp):
        """Test panel works with real orchestrator instance."""
        # Create real orchestrator
        real_orchestrator = StrategyBuilderOrchestrator()
        
        # Create panel
        panel = StrategyInfoPanel(real_orchestrator)
        
        # Set values
        panel.set_strategy_name("Integration_Test_Strategy")
        panel.set_strategy_type("Bullish")
        
        # Create strategy
        result = panel.create_strategy_in_orchestrator()
        
        # Verify
        assert result is True
        
        # Verify we can get the config back
        config = real_orchestrator.get_current_config()
        assert config is not None
        assert config.name == "Integration_Test_Strategy"
    
    def test_refresh_with_real_data(self, qapp):
        """Test refresh functionality with real orchestrator data."""
        # Create real orchestrator
        real_orchestrator = StrategyBuilderOrchestrator()
        
        # Create strategy directly in orchestrator
        real_orchestrator.create_strategy("Test_Strategy", "Test description")
        
        # Create panel
        panel = StrategyInfoPanel(real_orchestrator)
        
        # Refresh from orchestrator
        panel.refresh_from_orchestrator()
        
        # Verify description was loaded
        desc = panel.get_description()
        assert desc is not None
        assert len(desc) > 0


# Run tests with: python -m pytest tests/strategy_builder/ui/test_strategy_info_panel.py -v
