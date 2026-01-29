"""
Unit tests for get_test_result() ORM refactoring
Sprint 1.6.1 - Task 3.1.1

Tests verify get_test_result() works correctly with ORM.
Institutional-grade testing for test results retrieval.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from src.optimizer_v3.database.test_results_manager import TestResultsManager
from src.optimizer_v3.database.models import StrategyTestResult


class TestGetTestResultORM:
    """Test get_test_result() ORM refactoring - Task 3.1.1"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create test results database manager"""
        return TestResultsManager(db_session)
    
    @pytest.fixture
    def sample_test_result(self, db_session):
        """Create a sample test result in database with parent records"""
        from src.optimizer_v3.database.models import Strategy, StrategyVersion, StrategyTestResult
        
        # First create parent strategy
        strategy = Strategy(
            strategy_id='test_strategy_001',
            name='Test Strategy 001'
        )
        db_session.add(strategy)
        db_session.flush()
        
        # Then create strategy version
        version = StrategyVersion(
            strategy_id='test_strategy_001',
            version_number=1,
            name='Test Strategy 001',
            blocks=[],
            signals={},
            parameters={},
            entry_conditions={},
            exit_conditions=[],
            risk_management={},
            backtest_config={}
        )
        db_session.add(version)
        db_session.flush()
        
        # Finally create test result
        result = StrategyTestResult(
            strategy_id='test_strategy_001',
            version_id=version.version_id,
            test_type='backtest',
            test_config={'timeframe': '15m', 'symbols': ['BTC/USDT']},
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            total_return_pct=15.5,
            sharpe_ratio=1.8,
            max_drawdown_pct=-5.2,
            win_rate=0.65,
            profit_factor=2.1,
            total_trades=100,
            metrics={
                'total_return_pct': 15.5,
                'sharpe_ratio': 1.8,
                'avg_trade_duration': '2.5h'
            },
            trades=[{'entry': 50000, 'exit': 51000}],
            equity_curve=[1000, 1050, 1100],
            ai_recommendations={'recommendation_1': 'Add RSI'},
            exit_condition_results={'total_triggers': 50}
        )
        
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        
        return result
    
    def test_get_test_result_basic(self, manager, sample_test_result):
        """Test 1: Basic test result retrieval with ORM"""
        result_id = str(sample_test_result.result_id)
        
        # Retrieve using ORM
        test_result = manager.get_test_result(result_id)
        
        # Verify return value
        assert test_result is not None
        assert test_result['result_id'] == result_id
        assert test_result['strategy_id'] == 'test_strategy_001'
        assert test_result['test_type'] == 'backtest'
    
    def test_get_test_result_not_found(self, manager):
        """Test 2: Returns None for non-existent result"""
        fake_id = str(uuid4())
        
        result = manager.get_test_result(fake_id)
        
        assert result is None
    
    def test_get_test_result_jsonb_auto_deserialized(self, manager, sample_test_result):
        """Test 3: JSONB fields are automatically deserialized"""
        result_id = str(sample_test_result.result_id)
        
        test_result = manager.get_test_result(result_id)
        
        # Verify JSONB fields are Python objects (not strings)
        assert isinstance(test_result['test_config'], dict)
        assert isinstance(test_result['metrics'], dict)
        assert isinstance(test_result['trades'], list)
        assert isinstance(test_result['equity_curve'], list)
        assert isinstance(test_result['ai_recommendations'], dict)
        assert isinstance(test_result['exit_condition_results'], dict)
        
        # Verify content
        assert test_result['test_config']['timeframe'] == '15m'
        assert test_result['metrics']['sharpe_ratio'] == 1.8
        assert test_result['trades'][0]['entry'] == 50000
        assert test_result['equity_curve'] == [1000, 1050, 1100]
    
    def test_get_test_result_required_fields_present(self, manager, sample_test_result):
        """Test 4: All required fields are present in returned dict"""
        result_id = str(sample_test_result.result_id)
        
        test_result = manager.get_test_result(result_id)
        
        # Verify all required fields
        required_fields = [
            'result_id', 'strategy_id', 'version_id', 'test_type',
            'test_config', 'metrics', 'start_date', 'end_date',
            'total_return_pct', 'sharpe_ratio', 'max_drawdown_pct',
            'win_rate', 'profit_factor', 'total_trades', 'created_at'
        ]
        
        for field in required_fields:
            assert field in test_result, f"Missing field: {field}"
    
    def test_get_test_result_metrics_correct(self, manager, sample_test_result):
        """Test 5: Performance metrics are correctly retrieved"""
        result_id = str(sample_test_result.result_id)
        
        test_result = manager.get_test_result(result_id)
        
        # Verify metric values
        assert test_result['total_return_pct'] == 15.5
        assert test_result['sharpe_ratio'] == 1.8
        assert test_result['max_drawdown_pct'] == -5.2
        assert test_result['win_rate'] == 0.65
        assert test_result['profit_factor'] == 2.1
        assert test_result['total_trades'] == 100
    
    def test_get_test_result_optional_fields_null(self, manager, db_session):
        """Test 6: Optional fields can be NULL"""
        from src.optimizer_v3.database.models import Strategy, StrategyVersion, StrategyTestResult
        
        # Create parent strategy
        strategy = Strategy(strategy_id='test_strategy_002', name='Test Strategy 002')
        db_session.add(strategy)
        db_session.flush()
        
        # Create strategy version
        version = StrategyVersion(
            strategy_id='test_strategy_002',
            version_number=1,
            name='Test Strategy 002',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version)
        db_session.flush()
        
        # Create test result with minimal fields
        result = StrategyTestResult(
            strategy_id='test_strategy_002',
            version_id=version.version_id,
            test_type='backtest',
            test_config={'basic': 'config'},
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            metrics={'simple': 'metrics'},
            # Optional fields left as None
            trades=None,
            equity_curve=None,
            ai_recommendations=None,
            exit_condition_results=None
        )
        
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        
        # Retrieve
        result_id = str(result.result_id)
        test_result = manager.get_test_result(result_id)
        
        # Verify optional fields are None
        assert test_result['trades'] is None
        assert test_result['equity_curve'] is None
        assert test_result['ai_recommendations'] is None
        assert test_result['exit_condition_results'] is None
    
    def test_get_test_result_date_fields_are_datetime(self, manager, sample_test_result):
        """Test 7: Date fields are datetime objects"""
        result_id = str(sample_test_result.result_id)
        
        test_result = manager.get_test_result(result_id)
        
        assert isinstance(test_result['start_date'], datetime)
        assert isinstance(test_result['end_date'], datetime)
        assert isinstance(test_result['created_at'], datetime)
    
    def test_get_test_result_uuid_fields_are_strings(self, manager, sample_test_result):
        """Test 8: UUID fields are converted to strings"""
        result_id = str(sample_test_result.result_id)
        
        test_result = manager.get_test_result(result_id)
        
        # Verify UUID fields are strings (not UUID objects)
        assert isinstance(test_result['result_id'], str)
        assert isinstance(test_result['version_id'], str)
    
    def test_get_test_result_different_test_types(self, manager, db_session):
        """Test 9: Retrieves different test types correctly"""
        from src.optimizer_v3.database.models import Strategy, StrategyVersion, StrategyTestResult
        
        # Create parent strategy and version
        strategy = Strategy(strategy_id='test_strategy_003', name='Test Strategy 003')
        db_session.add(strategy)
        db_session.flush()
        
        version = StrategyVersion(
            strategy_id='test_strategy_003',
            version_number=1,
            name='Test Strategy 003',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version)
        db_session.flush()
        
        test_types = ['backtest', 'forward_test', 'paper_trade', 'live']
        result_ids = []
        
        for test_type in test_types:
            result = StrategyTestResult(
                strategy_id='test_strategy_003',
                version_id=version.version_id,
                test_type=test_type,
                test_config={'test': test_type},
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                metrics={'type': test_type}
            )
            db_session.add(result)
            db_session.commit()
            db_session.refresh(result)
            result_ids.append(str(result.result_id))
        
        # Verify each test type retrieved correctly
        for i, test_type in enumerate(test_types):
            test_result = manager.get_test_result(result_ids[i])
            assert test_result['test_type'] == test_type
    
    def test_get_test_result_returns_correct_type(self, manager, sample_test_result):
        """Test 10: Returns dict (not ORM object)"""
        result_id = str(sample_test_result.result_id)
        
        test_result = manager.get_test_result(result_id)
        
        assert isinstance(test_result, dict)
        assert not isinstance(test_result, StrategyTestResult)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
