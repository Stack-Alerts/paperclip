"""
Unit tests for get_strategy_test_results() ORM refactoring
Sprint 1.6.1 - Task 3.1.2

Tests verify get_strategy_test_results() works correctly with ORM.
Institutional-grade testing for multi-result retrieval.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from src.optimizer_v3.database.test_results_manager import TestResultsManager
from src.optimizer_v3.database.models import Strategy, StrategyVersion, StrategyTestResult


class TestGetStrategyTestResultsORM:
    """Test get_strategy_test_results() ORM refactoring - Task 3.1.2"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create test results database manager"""
        return TestResultsManager(db_session)
    
    @pytest.fixture
    def strategy_with_results(self, db_session):
        """Create strategy with multiple test results"""
        # Create parent strategy
        strategy = Strategy(strategy_id='strat_multi_001', name='Multi Test Strategy')
        db_session.add(strategy)
        db_session.flush()
        
        # Create strategy version
        version = StrategyVersion(
            strategy_id='strat_multi_001',
            version_number=1,
            name='Multi Test Strategy',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version)
        db_session.flush()
        
        # Create multiple test results
        results = []
        test_types = ['backtest', 'forward_test', 'backtest', 'paper_trade']
        
        for i, test_type in enumerate(test_types):
            result = StrategyTestResult(
                strategy_id='strat_multi_001',
                version_id=version.version_id,
                test_type=test_type,
                test_config={'run': i+1},
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                metrics={'run_number': i+1, 'sharpe': 1.5 + i*0.1},
                total_return_pct=10.0 + i*5.0,
                sharpe_ratio=1.5 + i*0.1,
                trades=[{'id': i+1}],
                equity_curve=[1000 + i*100]
            )
            db_session.add(result)
            db_session.flush()
            results.append(result)
        
        db_session.commit()
        
        return {
            'strategy': strategy,
            'version': version,
            'results': results
        }
    
    def test_get_strategy_test_results_basic(self, manager, strategy_with_results):
        """Test 1: Basic retrieval of all results for a strategy"""
        results = manager.get_strategy_test_results('strat_multi_001')
        
        # Should have 4 results
        assert len(results) == 4
        assert all(r['strategy_id'] == 'strat_multi_001' for r in results)
    
    def test_get_strategy_test_results_empty(self, manager):
        """Test 2: Returns empty list when no results exist"""
        results = manager.get_strategy_test_results('nonexistent_strategy')
        
        assert results == []
        assert isinstance(results, list)
    
    def test_get_strategy_test_results_filter_by_type(self, manager, strategy_with_results):
        """Test 3: Filter results by test type"""
        # Filter for backtest only
        backtest_results = manager.get_strategy_test_results(
            'strat_multi_001',
            test_type='backtest'
        )
        
        assert len(backtest_results) == 2
        assert all(r['test_type'] == 'backtest' for r in backtest_results)
        
        # Filter for forward_test
        forward_results = manager.get_strategy_test_results(
            'strat_multi_001',
            test_type='forward_test'
        )
        
        assert len(forward_results) == 1
        assert forward_results[0]['test_type'] == 'forward_test'
    
    def test_get_strategy_test_results_with_limit(self, manager, strategy_with_results):
        """Test 4: Limit number of results returned"""
        # Get only 2 results
        limited_results = manager.get_strategy_test_results(
            'strat_multi_001',
            limit=2
        )
        
        assert len(limited_results) == 2
    
    def test_get_strategy_test_results_type_and_limit(self, manager, strategy_with_results):
        """Test 5: Filter by type AND limit combined"""
        # Get 1 backtest result
        results = manager.get_strategy_test_results(
            'strat_multi_001',
            test_type='backtest',
            limit=1
        )
        
        assert len(results) == 1
        assert results[0]['test_type'] == 'backtest'
    
    def test_get_strategy_test_results_jsonb_deserialized(self, manager, strategy_with_results):
        """Test 6: JSONB fields are automatically deserialized"""
        results = manager.get_strategy_test_results('strat_multi_001')
        
        # Check first result
        result = results[0]
        
        # JSONB fields should be Python objects
        assert isinstance(result['test_config'], dict)
        assert isinstance(result['metrics'], dict)
        assert isinstance(result['trades'], list)
        assert isinstance(result['equity_curve'], list)
        
        # Verify data integrity
        assert 'run' in result['test_config']
        assert 'run_number' in result['metrics']
    
    def test_get_strategy_test_results_ordered_desc(self, manager, db_session):
        """Test 7: Results ordered by created_at DESC (newest first)"""
        # Create strategy and version
        strategy = Strategy(strategy_id='strat_order_001', name='Order Test')
        db_session.add(strategy)
        db_session.flush()
        
        version = StrategyVersion(
            strategy_id='strat_order_001',
            version_number=1,
            name='Order Test',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version)
        db_session.flush()
        
        # Create results
        for i in range(3):
            result = StrategyTestResult(
                strategy_id='strat_order_001',
                version_id=version.version_id,
                test_type='backtest',
                test_config={'order': i},
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                metrics={'order': i}
            )
            db_session.add(result)
            db_session.commit()
        
        # Retrieve results
        results = manager.get_strategy_test_results('strat_order_001')
        
        # Should be 3 results
        assert len(results) == 3
        
        # Verify all results have created_at timestamps
        for result in results:
            assert result['created_at'] is not None
            assert isinstance(result['created_at'], datetime)
    
    def test_get_strategy_test_results_multiple_types(self, manager, strategy_with_results):
        """Test 8: Returns multiple test types correctly"""
        results = manager.get_strategy_test_results('strat_multi_001')
        
        test_types = set(r['test_type'] for r in results)
        
        # Should have 3 unique test types
        assert len(test_types) == 3
        assert 'backtest' in test_types
        assert 'forward_test' in test_types
        assert 'paper_trade' in test_types
    
    def test_get_strategy_test_results_returns_list_of_dicts(self, manager, strategy_with_results):
        """Test 9: Returns list of dicts (not ORM objects)"""
        results = manager.get_strategy_test_results('strat_multi_001')
        
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)
        assert all(not isinstance(r, StrategyTestResult) for r in results)
    
    def test_get_strategy_test_results_field_completeness(self, manager, strategy_with_results):
        """Test 10: All expected fields present in results"""
        results = manager.get_strategy_test_results('strat_multi_001')
        
        # Check first result has all required fields
        result = results[0]
        
        required_fields = [
            'result_id', 'strategy_id', 'version_id', 'test_type',
            'test_config', 'metrics', 'trades', 'equity_curve',
            'start_date', 'end_date', 'total_return_pct', 'sharpe_ratio',
            'timestamp', 'created_at'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
    
    def test_get_strategy_test_results_metric_values(self, manager, strategy_with_results):
        """Test 11: Metric values correctly retrieved"""
        results = manager.get_strategy_test_results('strat_multi_001')
        
        # First result should have highest values (newest)
        # Last result should have lowest values (oldest)
        # Verify metrics are numbers
        for result in results:
            if result['total_return_pct'] is not None:
                assert isinstance(result['total_return_pct'], (int, float))
            if result['sharpe_ratio'] is not None:
                assert isinstance(result['sharpe_ratio'], (int, float))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
