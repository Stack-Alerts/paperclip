"""
Tests for Sprint 2.0.1 Task 2.0.1.1 - Date Range UI Verification

Validates that existing lookback/training/testing spinboxes work correctly
with updated get_config() method that calculates dates.

NAUTILUS EXPERT: Ensures institutional-grade date handling

Author: BTC_Engine_v3 Test Suite
Date: 2026-02-06
"""

import pytest
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QApplication
from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def panel(qapp):
    """Create BacktestConfigPanel instance for testing"""
    # Mock orchestrator with minimal required methods
    class MockOrchestrator:
        def validate_strategy(self):
            class ValidationResult:
                success = True
                message = ""
            return ValidationResult()
        
        def get_current_config(self):
            return None
    
    orchestrator = MockOrchestrator()
    panel = BacktestConfigPanel(orchestrator=orchestrator)
    yield panel
    panel.close()


def test_date_range_widgets_exist(panel):
    """Test that date range spinboxes exist"""
    assert hasattr(panel, 'lookback_spin')
    assert hasattr(panel, 'training_spin')
    assert hasattr(panel, 'testing_spin')
    assert panel.lookback_spin is not None
    assert panel.training_spin is not None
    assert panel.testing_spin is not None


def test_default_values(panel):
    """Test default spinbox values"""
    assert panel.lookback_spin.value() == 180
    assert panel.training_spin.value() == 90
    assert panel.testing_spin.value() == 30


def test_config_includes_dates(panel):
    """Test get_config() includes calculated dates"""
    config = panel.get_config()
    
    assert 'start_date' in config
    assert 'end_date' in config
    assert 'timeframe' in config
    assert isinstance(config['start_date'], datetime)
    assert isinstance(config['end_date'], datetime)
    assert config['timeframe'] == '15m'


def test_date_calculation_mode1(panel):
    """Test date calculation for Mode 1"""
    # Set Mode 1
    panel.mode1_radio.setChecked(True)
    
    # Set lookback to 30 days
    panel.lookback_spin.setValue(30)
    panel.training_spin.setValue(20)
    panel.testing_spin.setValue(10)
    
    config = panel.get_config()
    
    # Verify dates calculated correctly (within 1 second tolerance)
    expected_start = datetime.now() - timedelta(days=30)
    expected_end = datetime.now()
    
    # Check start_date (within 2 seconds tolerance)
    assert abs((config['start_date'] - expected_start).total_seconds()) < 2
    
    # Check end_date (within 2 seconds tolerance)
    assert abs((config['end_date'] - expected_end).total_seconds()) < 2
    
    # Mode 1 should include training/testing windows
    assert 'training_window' in config
    assert 'testing_window' in config
    assert config['training_window'] == 20
    assert config['testing_window'] == 10
    
    # Mode 1 should include split dates
    assert 'training_end' in config
    assert 'testing_start' in config
    
    expected_training_end = config['start_date'] + timedelta(days=20)
    assert abs((config['training_end'] - expected_training_end).total_seconds()) < 2


def test_date_calculation_mode2(panel):
    """Test date calculation for Mode 2"""
    # Set Mode 2
    panel.mode2_radio.setChecked(True)
    
    # Set lookback to 90 days
    panel.lookback_spin.setValue(90)
    
    config = panel.get_config()
    
    # Verify dates calculated correctly
    expected_start = datetime.now() - timedelta(days=90)
    expected_end = datetime.now()
    
    # Check dates (within 2 seconds tolerance)
    assert abs((config['start_date'] - expected_start).total_seconds()) < 2
    assert abs((config['end_date'] - expected_end).total_seconds()) < 2
    
    # Mode 2 should NOT include training/testing windows
    assert 'training_window' not in config
    assert 'testing_window' not in config
    assert 'training_end' not in config
    assert 'testing_start' not in config


def test_lookback_range_variations(panel):
    """Test different lookback day values"""
    test_cases = [
        (7, "7 days"),
        (31, "31 days"),
        (90, "90 days"),
        (180, "180 days"),
        (365, "365 days")
    ]
    
    for days, description in test_cases:
        panel.lookback_spin.setValue(days)
        config = panel.get_config()
        
        expected_start = datetime.now() - timedelta(days=days)
        actual_diff = (config['end_date'] - config['start_date']).days
        
        # Verify lookback period (within 1 day tolerance for rounding)
        assert abs(actual_diff - days) <= 1, f"Failed for {description}"


def test_mode_switching(panel):
    """Test switching between Mode 1 and Mode 2"""
    # Start with Mode 1
    panel.mode1_radio.setChecked(True)
    panel.lookback_spin.setValue(60)
    
    config1 = panel.get_config()
    assert 'training_window' in config1
    assert config1['mode'] == 1
    
    # Switch to Mode 2
    panel.mode2_radio.setChecked(True)
    
    config2 = panel.get_config()
    assert 'training_window' not in config2
    assert config2['mode'] == 2
    
    # Dates should be the same (based on lookback)
    assert abs((config1['start_date'] - config2['start_date']).total_seconds()) < 1
    assert abs((config1['end_date'] - config2['end_date']).total_seconds()) < 1


def test_config_consistency(panel):
    """Test that multiple get_config() calls return consistent dates"""
    panel.lookback_spin.setValue(45)
    
    config1 = panel.get_config()
    config2 = panel.get_config()
    
    # Should be within 1 second of each other
    assert abs((config1['start_date'] - config2['start_date']).total_seconds()) < 1
    assert abs((config1['end_date'] - config2['end_date']).total_seconds()) < 1


def test_timeframe_always_15m(panel):
    """Test that timeframe is always 15m (system designed for 15m only)"""
    # Try different configurations
    configs = []
    
    for mode in [1, 2]:
        for lookback in [30, 90, 180]:
            if mode == 1:
                panel.mode1_radio.setChecked(True)
            else:
                panel.mode2_radio.setChecked(True)
            
            panel.lookback_spin.setValue(lookback)
            config = panel.get_config()
            configs.append(config)
    
    # All configs should have timeframe = '15m'
    for config in configs:
        assert config['timeframe'] == '15m'


def test_mode1_training_end_calculation(panel):
    """Test Mode 1 training_end calculation"""
    panel.mode1_radio.setChecked(True)
    panel.lookback_spin.setValue(100)
    panel.training_spin.setValue(60)
    panel.testing_spin.setValue(40)
    
    config = panel.get_config()
    
    # training_end should be start_date + training_window
    expected_training_end = config['start_date'] + timedelta(days=60)
    assert abs((config['training_end'] - expected_training_end).total_seconds()) < 2
    
    # testing_start should equal training_end
    assert abs((config['testing_start'] - config['training_end']).total_seconds()) < 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
