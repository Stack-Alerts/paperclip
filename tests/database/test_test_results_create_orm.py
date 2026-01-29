"""
Unit tests for create_test_result() ORM refactoring
Sprint 1.6.1 - Task 3.1.5

Tests verify create_test_result() works correctly with ORM.
Institutional-grade testing for database WRITE operations.
"""

import pytest
from datetime import datetime
from uuid import UUID
from src.optimizer_v3.database.test_results_manager import TestResultsManager
from src.optimizer_v3.database.models import Strategy, StrategyVersion, StrategyTestResult


class TestCreateTestResultORM:
    """Test create_test_result() ORM refactoring - Task 3.1.5"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create test results database manager"""
        return TestResultsManager(db_session)
    
    @pytest.fixture
    def strategy_and_version(self, db_session):
        """Create strategy and version for testing"""
        strategy = Strategy(strategy_id='create_test_001', name='Create Test Strategy')
        db_session.add(strategy)
        db_session.flush()
        
        version = StrategyVersion(
            strategy_id='create_test_001',
            version_number=1,
            name='v1',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version)
        db_session.commit()
        
        return {'strategy': strategy, 'version': version}
    
    def test_create_test_result_basic(self, manager, strategy_and_version, db_session):
        """Test 1: Basic test result creation"""
        test_data = {
            'strategy_id': 'create_test_001',
            'strategy_version_id': str(strategy_and_version['version'].version_id),
            'test_type': 'backtest',
            'test_config': {'timeframe': '15m', 'symbols': ['BTC/USDT']},
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31),
            'metrics': {
                'total_return_pct': 15.5,
                'sharpe_ratio': 1.8,
                'max_drawdown_pct': -5.2,
                'win_rate': 0.65,
                'profit_factor': 2.1,
                'total_trades': 100
            }
        }
        
        result_id = manager.create_test_result(test_data)
        
        # Verify returned UUID
        assert result_id is not None
        assert isinstance(result_id, str)
        UUID(result_id)  # Should parse as valid UUID
        
        # Verify record created in database
        created = db_session.query(StrategyTestResult).filter_by(result_id=result_id).first()
        assert created is not None
        assert created.test_type == 'backtest'
    
    def test_create_test_result_missing_required_field(self, manager, strategy_and_version):
        """Test 2: Raises ValueError when required field missing"""
        test_data = {
            'strategy_id': 'create_test_001',
            # Missing strategy_version_id
            'test_type': 'backtest',
            'test_config': {},
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31),
            'metrics': {}
        }
        
        with pytest.raises(ValueError, match="Missing required fields"):
            manager.create_test_result(test_data)
    
    def test_create_test_result_invalid_test_type(self, manager, strategy_and_version):
        """Test 3: Raises ValueError for invalid test_type"""
        test_data = {
            'strategy_id': 'create_test_001',
            'strategy_version_id': str(strategy_and_version['version'].version_id),
            'test_type': 'invalid_type',  # Invalid
            'test_config': {},
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31),
            'metrics': {}
        }
        
        with pytest.raises(ValueError, match="Invalid test_type"):
            manager.create_test_result(test_data)
    
    def test_create_test_result_with_optional_fields(self, manager, strategy_and_version, db_session):
        """Test 4: Creates with all optional fields"""
        test_data = {
            'strategy_id': 'create_test_001',
            'strategy_version_id': str(strategy_and_version['version'].version_id),
            'test_type': 'forward_test',
            'test_config': {'config': 'value'},
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31),
            'metrics': {'sharpe': 1.5},
            'trades': [{'id': 1}, {'id': 2}],
            'equity_curve': [1000, 1050, 1100],
            'risk_metrics': {'var': 0.05},
            'exit_condition_results': {'total': 10},
            'errors': ['error1'],
            'warnings': ['warn1'],
            'notes': 'Test notes'
        }
        
        result_id = manager.create_test_result(test_data)
        
        created = db_session.query(StrategyTestResult).filter_by(result_id=result_id).first()
        assert created.trades == [{'id': 1}, {'id': 2}]
        assert created.equity_curve == [1000, 1050, 1100]
        assert created.notes == 'Test notes'
    
    def test_create_test_result_metrics_extracted(self, manager, strategy_and_version, db_session):
        """Test 5: Key metrics extracted from metrics dict"""
        test_data = {
            'strategy_id': 'create_test_001',
            'strategy_version_id': str(strategy_and_version['version'].version_id),
            'test_type': 'backtest',
            'test_config': {},
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31),
            'metrics': {
                'total_return_pct': 20.0,
                'sharpe_ratio': 2.5,
                'max_drawdown_pct': -8.0,
                'win_rate': 0.70,
                'profit_factor': 3.0,
                'total_trades': 150
            }
        }
        
        result_id = manager.create_test_result(test_data)
        
        created = db_session.query(StrategyTestResult).filter_by(result_id=result_id).first()
        assert created.total_return_pct == 20.0
        assert created.sharpe_ratio == 2.5
        assert created.max_drawdown_pct == -8.0
        assert created.win_rate == 0.70
        assert created.profit_factor == 3.0
        assert created.total_trades == 150
    
    def test_create_test_result_jsonb_stored_correctly(self, manager, strategy_and_version, db_session):
        """Test 6: JSONB fields stored as Python objects (no manual serialization)"""
        test_data = {
            'strategy_id': 'create_test_001',
            'strategy_version_id': str(strategy_and_version['version'].version_id),
            'test_type': 'paper_trade',
            'test_config': {'nested': {'data': 'value'}},
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31),
            'metrics': {'complex': {'metric': 123}}
        }
        
        result_id = manager.create_test_result(test_data)
        
        created = db_session.query(StrategyTestResult).filter_by(result_id=result_id).first()
        # JSONB should be Python dicts, not strings
        assert isinstance(created.test_config, dict)
        assert created.test_config == {'nested': {'data': 'value'}}
        assert isinstance(created.metrics, dict)
        assert created.metrics == {'complex': {'metric': 123}}
    
    def test_create_test_result_timestamps_auto_generated(self, manager, strategy_and_version, db_session):
        """Test 7: Timestamps automatically generated"""
        test_data = {
            'strategy_id': 'create_test_001',
            'strategy_version_id': str(strategy_and_version['version'].version_id),
            'test_type': 'live',
            'test_config': {},
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31),
            'metrics': {}
        }
        
        result_id = manager.create_test_result(test_data)
        
        created = db_session.query(StrategyTestResult).filter_by(result_id=result_id).first()
        assert created.timestamp is not None
        assert created.created_at is not None
        assert isinstance(created.timestamp, datetime)
        assert isinstance(created.created_at, datetime)
    
    def test_create_test_result_multiple_test_types(self, manager, strategy_and_version):
        """Test 8: All valid test types work"""
        valid_types = ['backtest', 'forward_test', 'paper_trade', 'live', 'walk_forward']
        
        for test_type in valid_types:
            test_data = {
                'strategy_id': 'create_test_001',
                'strategy_version_id': str(strategy_and_version['version'].version_id),
                'test_type': test_type,
                'test_config': {'type': test_type},
                'start_date': datetime(2024, 1, 1),
                'end_date': datetime(2024, 12, 31),
                'metrics': {}
            }
            
            result_id = manager.create_test_result(test_data)
            assert result_id is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
