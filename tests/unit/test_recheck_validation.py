"""
Unit Tests for RECHECK Validation System

Comprehensive test suite covering:
- Data structures
- UI components
- Backend processing
- Metrics calculation
- Debug logging

Author: BTC_Engine_v3
Date: 2026-01-22
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.strategy_builder.core.strategy_config_engine import RecheckConfig, SignalConfig
from src.debugger_logger.recheck_debugger import RecheckDebugger, RecheckValidationState
from src.optimizer_v3.core.results.recheck_metrics import RecheckMetricsCalculator


class TestRecheckDataStructures(unittest.TestCase):
    """Test RECHECK data structure implementations"""
    
    def setUp(self):
        """Set up test cases"""
        self.base_recheck = RecheckConfig(
            enabled=True,
            bar_delay=25
        )
        
        self.nested_recheck = RecheckConfig(
            enabled=True,
            bar_delay=10,
            validation_mode="RECHECK",
            parent_signal="base_recheck"
        )
    
    def test_recheck_config_creation(self):
        """Test RecheckConfig creation and defaults"""
        config = RecheckConfig()
        self.assertFalse(config.enabled)
        self.assertEqual(config.bar_delay, 0)
        self.assertIsNone(config.parent_signal)
        self.assertEqual(config.validation_mode, "SIGNAL")
        self.assertEqual(len(config.nested_rechecks), 0)
    
    def test_nested_recheck_chain(self):
        """Test nested RECHECK chain construction"""
        self.base_recheck.nested_rechecks.append(self.nested_recheck)
        
        self.assertEqual(len(self.base_recheck.nested_rechecks), 1)
        self.assertEqual(self.base_recheck.nested_rechecks[0].bar_delay, 10)
        self.assertEqual(self.base_recheck.nested_rechecks[0].validation_mode, "RECHECK")
    
    def test_signal_config_with_recheck(self):
        """Test SignalConfig with RECHECK configuration"""
        signal = SignalConfig(
            name="test_signal",
            logic="AND",
            recheck_config=self.base_recheck
        )
        
        self.assertTrue(signal.recheck_config.enabled)
        self.assertEqual(signal.recheck_config.bar_delay, 25)
        self.assertEqual(len(signal.recheck_chain), 0)


class TestRecheckDebugger(unittest.TestCase):
    """Test RECHECK debug logging functionality"""
    
    def setUp(self):
        """Set up test cases"""
        self.debugger = RecheckDebugger(console_output=False)
        self.chain_id = "test_block::test_signal"
    
    def test_chain_registration(self):
        """Test RECHECK chain registration"""
        recheck_chain = [
            {'enabled': True, 'bar_delay': 25},
            {'enabled': True, 'bar_delay': 10, 'validation_mode': 'RECHECK'}
        ]
        
        self.debugger.log_recheck_chain(
            block_name="test_block",
            signal_name="test_signal",
            recheck_chain=recheck_chain
        )
        
        self.assertIn(self.chain_id, self.debugger.validation_states)
        state = self.debugger.validation_states[self.chain_id]
        self.assertEqual(state['current_level'], 0)
        self.assertEqual(state['state'], RecheckValidationState.PENDING)
    
    def test_validation_tracking(self):
        """Test validation state tracking"""
        # Register chain
        self.debugger.log_recheck_chain(
            "test_block", "test_signal",
            [{'enabled': True, 'bar_delay': 25}]
        )
        
        # Start validation
        self.debugger.log_validation_start(self.chain_id, 0, 100)
        state = self.debugger.validation_states[self.chain_id]
        self.assertEqual(state['state'], RecheckValidationState.VALIDATING)
        
        # Log success
        self.debugger.log_validation_result(
            self.chain_id, 0, True, 105,
            {'found_at': 103}
        )
        state = self.debugger.validation_states[self.chain_id]
        self.assertEqual(state['state'], RecheckValidationState.VALIDATED)
    
    def test_chain_expiration(self):
        """Test chain expiration handling"""
        # Register chain
        self.debugger.log_recheck_chain(
            "test_block", "test_signal",
            [{'enabled': True, 'bar_delay': 25}]
        )
        
        # Expire chain
        self.debugger.log_chain_expired(
            self.chain_id, 125,
            "Validation window exceeded"
        )
        
        state = self.debugger.validation_states[self.chain_id]
        self.assertEqual(state['state'], RecheckValidationState.EXPIRED)


class TestRecheckMetrics(unittest.TestCase):
    """Test RECHECK metrics calculation"""
    
    def setUp(self):
        """Set up test cases"""
        self.metrics = RecheckMetricsCalculator()
        self.chain_id = "test_block::test_signal"
    
    def test_chain_metrics(self):
        """Test chain-level metrics calculation"""
        # Add successful chain
        self.metrics.add_chain_result(
            self.chain_id,
            [{'level': 0, 'success': True}, {'level': 1, 'success': True}],
            RecheckValidationState.VALIDATED,
            15.5
        )
        
        # Calculate metrics
        results = self.metrics.calculate_metrics()
        
        self.assertEqual(results['chain_metrics']['total_chains'], 1)
        self.assertEqual(results['chain_metrics']['successful_chains'], 1)
        self.assertEqual(results['chain_metrics']['success_rate'], 1.0)
    
    def test_level_metrics(self):
        """Test level-specific metrics calculation"""
        # Add chain with mixed results
        self.metrics.add_chain_result(
            self.chain_id,
            [
                {'level': 0, 'success': True},
                {'level': 1, 'success': False}
            ],
            RecheckValidationState.FAILED,
            12.3
        )
        
        # Calculate metrics
        results = self.metrics.calculate_metrics()
        
        self.assertEqual(results['level_metrics'][0]['attempts'], 1)
        self.assertEqual(results['level_metrics'][0]['success_rate'], 1.0)
        self.assertEqual(results['level_metrics'][1]['failures'], 1)
    
    def test_trade_impact(self):
        """Test trade impact analysis"""
        # Add trades with and without RECHECK
        self.metrics.add_trade_result("trade1", True, True)   # Win with RECHECK
        self.metrics.add_trade_result("trade2", False, True)  # Loss with RECHECK
        self.metrics.add_trade_result("trade3", True, False)  # Win without RECHECK
        
        # Calculate metrics
        results = self.metrics.calculate_metrics()
        impact = results['trade_impact']
        
        self.assertEqual(impact['with_recheck']['total'], 2)
        self.assertEqual(impact['with_recheck']['wins'], 1)
        self.assertEqual(impact['without_recheck']['total'], 1)
        self.assertEqual(impact['without_recheck']['wins'], 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for RECHECK system"""
    
    def setUp(self):
        """Set up test environment"""
        self.debugger = RecheckDebugger(console_output=False)
        self.metrics = RecheckMetricsCalculator()
    
    def test_complete_validation_flow(self):
        """Test complete validation flow with metrics"""
        chain_id = "test_block::test_signal"
        
        # 1. Register chain
        self.debugger.log_recheck_chain(
            "test_block",
            "test_signal",
            [
                {'enabled': True, 'bar_delay': 25},
                {'enabled': True, 'bar_delay': 10, 'validation_mode': 'RECHECK'}
            ]
        )
        
        # 2. Start validation
        self.debugger.log_validation_start(chain_id, 0, 100)
        
        # 3. Log first level success
        self.debugger.log_validation_result(
            chain_id, 0, True, 110,
            {'found_at': 108}
        )
        
        # 4. Start second level
        self.debugger.log_validation_start(chain_id, 1, 110)
        
        # 5. Log second level success
        self.debugger.log_validation_result(
            chain_id, 1, True, 115,
            {'found_at': 113}
        )
        
        # 6. Add to metrics
        self.metrics.add_chain_result(
            chain_id,
            self.debugger.validation_states[chain_id]['validation_history'],
            RecheckValidationState.VALIDATED,
            15.0
        )
        
        # 7. Verify metrics
        results = self.metrics.calculate_metrics()
        
        self.assertEqual(results['chain_metrics']['successful_chains'], 1)
        self.assertEqual(len(results['level_metrics']), 2)
        self.assertEqual(results['level_metrics'][0]['success_rate'], 1.0)
        self.assertEqual(results['level_metrics'][1]['success_rate'], 1.0)


if __name__ == '__main__':
    unittest.main()
