"""
Integration Tests for RECHECK System

Full system validation covering:
- UI interaction
- Backend processing
- Data persistence
- Metrics calculation
- Debug logging
- Live output

Author: BTC_Engine_v3
Date: 2026-01-22
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import json
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

from src.strategy_builder.ui.strategy_blocks_panel import BlockConfigItem
from src.strategy_builder.core.strategy_config_engine import RecheckConfig, SignalConfig
from src.debugger_logger.recheck_debugger import RecheckDebugger, RecheckValidationState
from src.optimizer_v3.core.results.recheck_metrics import RecheckMetricsCalculator
from src.optimizer_v3.ui.live_output_panel import LiveOutputPanel


class TestRecheckSystemIntegration(unittest.TestCase):
    """Integration tests for complete RECHECK system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Create QApplication instance for UI tests
        cls.app = QApplication([])
        
        # Create temp directory for test files
        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_path = Path(cls.temp_dir)
    
    def setUp(self):
        """Set up test cases"""
        # Mock orchestrator
        self.mock_orchestrator = Mock()
        self.mock_orchestrator.get_current_config.return_value = None
        
        # Create UI components
        self.block_item = BlockConfigItem(
            block_name="test_block",
            block_info={
                'name': 'test_block',
                'logic': 'AND',
                'signals': [
                    {
                        'name': 'test_signal',
                        'logic': 'AND'
                    }
                ]
            },
            position=1,
            total=1
        )
        
        # Create debugger with temp log file
        self.debugger = RecheckDebugger(
            log_file=self.temp_path / "recheck_debug.log",
            console_output=False
        )
        
        # Create metrics calculator
        self.metrics = RecheckMetricsCalculator()
        
        # Create live output panel
        self.live_output = LiveOutputPanel()
    
    def test_complete_recheck_workflow(self):
        """Test complete RECHECK workflow from UI to metrics"""
        # 1. Configure base RECHECK through UI
        with patch('PyQt5.QtWidgets.QInputDialog.getInt') as mock_dialog:
            mock_dialog.return_value = (25, True)  # bar_delay = 25, OK clicked
            
            # Click RECHECK button
            recheck_btn = self.block_item.findChild(
                QPushButton,
                "recheck_btn_test_signal"
            )
            QTest.mouseClick(recheck_btn, Qt.LeftButton)
        
        # Verify base RECHECK configuration
        config = self.mock_orchestrator.get_current_config()
        self.assertIsNotNone(config)
        signal = config.blocks[0].signals[0]
        self.assertTrue(signal.recheck_config.enabled)
        self.assertEqual(signal.recheck_config.bar_delay, 25)
        
        # 2. Add nested RECHECK through UI
        with patch('PyQt5.QtWidgets.QDialog.exec_') as mock_dialog:
            mock_dialog.return_value = QDialog.Accepted
            
            # Configure dialog result
            dialog = mock_dialog.return_value
            dialog.findChild(QCheckBox, "recheck_radio").setChecked(True)
            dialog.findChild(QSpinBox, "delay_input").setValue(10)
            
            # Click duplicate button
            duplicate_btn = self.block_item.findChild(
                QPushButton,
                "duplicate_btn_test_signal"
            )
            QTest.mouseClick(duplicate_btn, Qt.LeftButton)
        
        # Verify nested RECHECK configuration
        config = self.mock_orchestrator.get_current_config()
        signal = config.blocks[0].signals[0]
        self.assertEqual(len(signal.recheck_chain), 1)
        self.assertEqual(signal.recheck_chain[0].bar_delay, 10)
        self.assertEqual(signal.recheck_chain[0].validation_mode, "RECHECK")
        
        # 3. Process validation through debug logger
        chain_id = "test_block::test_signal"
        
        # Register chain
        self.debugger.log_recheck_chain(
            "test_block",
            "test_signal",
            [
                {'enabled': True, 'bar_delay': 25},
                {'enabled': True, 'bar_delay': 10, 'validation_mode': 'RECHECK'}
            ]
        )
        
        # Simulate validation flow
        self.debugger.log_validation_start(chain_id, 0, 100)
        self.debugger.log_validation_result(
            chain_id, 0, True, 110,
            {'found_at': 108}
        )
        
        self.debugger.log_validation_start(chain_id, 1, 110)
        self.debugger.log_validation_result(
            chain_id, 1, True, 115,
            {'found_at': 113}
        )
        
        # 4. Calculate metrics
        self.metrics.add_chain_result(
            chain_id,
            self.debugger.validation_states[chain_id]['validation_history'],
            RecheckValidationState.VALIDATED,
            15.0
        )
        
        # Add trade result
        self.metrics.add_trade_result("trade1", True, True)
        
        # Calculate final metrics
        results = self.metrics.calculate_metrics()
        
        # Verify metrics
        self.assertEqual(results['chain_metrics']['successful_chains'], 1)
        self.assertEqual(results['chain_metrics']['success_rate'], 1.0)
        self.assertEqual(results['level_metrics'][0]['success_rate'], 1.0)
        self.assertEqual(results['level_metrics'][1]['success_rate'], 1.0)
        self.assertEqual(results['trade_impact']['with_recheck']['wins'], 1)
        
        # 5. Verify live output
        self.live_output.add_message(
            "RECHECK validation complete",
            level="INFO",
            category="RECHECK"
        )
        
        messages = self.live_output.get_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['category'].value, "RECHECK")
    
    def test_error_handling(self):
        """Test error handling across system components"""
        chain_id = "test_block::test_signal"
        
        # 1. Register invalid chain
        with self.assertRaises(ValueError):
            self.debugger.log_recheck_chain(
                "test_block",
                "test_signal",
                []  # Empty chain
            )
        
        # 2. Try to validate non-existent chain
        self.debugger.log_validation_start("invalid_chain", 0, 100)
        self.assertNotIn("invalid_chain", self.debugger.validation_states)
        
        # 3. Calculate metrics with no data
        results = self.metrics.calculate_metrics()
        self.assertIn('error', results)
        
        # 4. Test UI error handling
        with patch('PyQt5.QtWidgets.QInputDialog.getInt') as mock_dialog:
            mock_dialog.return_value = (-1, True)  # Invalid bar_delay
            
            # Click RECHECK button
            recheck_btn = self.block_item.findChild(
                QPushButton,
                "recheck_btn_test_signal"
            )
            QTest.mouseClick(recheck_btn, Qt.LeftButton)
        
        # Verify no configuration was added
        config = self.mock_orchestrator.get_current_config()
        signal = config.blocks[0].signals[0]
        self.assertIsNone(signal.recheck_config)
    
    def test_persistence(self):
        """Test data persistence across components"""
        chain_id = "test_block::test_signal"
        
        # 1. Create test data
        self.debugger.log_recheck_chain(
            "test_block",
            "test_signal",
            [{'enabled': True, 'bar_delay': 25}]
        )
        
        self.debugger.log_validation_result(
            chain_id, 0, True, 110,
            {'found_at': 108}
        )
        
        self.metrics.add_chain_result(
            chain_id,
            self.debugger.validation_states[chain_id]['validation_history'],
            RecheckValidationState.VALIDATED,
            15.0
        )
        
        # 2. Export debug logs
        debug_file = self.temp_path / "debug_export.json"
        self.debugger.export_validation_data(debug_file)
        
        # 3. Export metrics
        metrics_file = self.temp_path / "metrics_export.json"
        self.metrics.export_metrics(metrics_file)
        
        # 4. Verify exported data
        with open(debug_file) as f:
            debug_data = json.load(f)
            self.assertIn(chain_id, debug_data['validation_states'])
        
        with open(metrics_file) as f:
            metrics_data = json.load(f)
            self.assertEqual(metrics_data['chain_metrics']['total_chains'], 1)
    
    def tearDown(self):
        """Clean up test cases"""
        # Clean up temp files
        for file in self.temp_path.glob("*"):
            file.unlink()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Remove temp directory
        cls.temp_path.rmdir()
        
        # Clean up QApplication
        cls.app.quit()


if __name__ == '__main__':
    unittest.main()
