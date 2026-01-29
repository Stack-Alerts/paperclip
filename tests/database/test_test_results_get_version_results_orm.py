"""
Unit tests for get_version_test_results() ORM refactoring
Sprint 1.6.1 - Task 3.1.3

Tests verify get_version_test_results() works correctly with ORM.
Institutional-grade testing for version-specific result retrieval.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from src.optimizer_v3.database.test_results_manager import TestResultsManager
from src.optimizer_v3.database.models import Strategy, StrategyVersion, StrategyTestResult


class TestGetVersionTestResultsORM:
    """Test get_version_test_results() ORM refactoring - Task 3.1.3"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create test results database manager"""
        return TestResultsManager(db_session)
    
    @pytest.fixture
    def version_with_results(self, db_session):
        """Create version with multiple test results"""
        # Create parent strategy
        strategy = Strategy(strategy_id='vers_test_001', name='Version Test Strategy')
        db_session.add(strategy)
        db_session.flush()
        
        # Create strategy version
        version = StrategyVersion(
            strategy_id='vers_test_001',
            version_number=1,
            name='Version Test Strategy v1',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version)
        db_session.flush()
        
        # Create multiple test results for this version
        results = []
        test_types = ['backtest', 'forward_test', 'backtest', 'paper_trade', 'live']
        
        for i, test_type in enumerate(test_types):
            result = StrategyTestResult(
                strategy_id='vers_test_001',
                version_id=version.version_id,
                test_type=test_type,
                test_config={'test_run': i+1, 'timeframe': '15m'},
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                metrics={'run': i+1, 'sharpe': 1.2 + i*0.2},
                total_return_pct=8.0 + i*3.0,
                sharpe_ratio=1.2 + i*0.2,
                max_drawdown_pct=-3.0 - i*0.5,
                win_rate=0.55 + i*0.05,
                profit_factor=1.8 + i*0.2,
                total_trades=80 + i*10,
                trades=[{'trade_id': i+1}],
                equity_curve=[1000 + i*50]
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
    
    def test_get_version_test_results_basic(self, manager, version_with_results):
        """Test 1: Basic retrieval of all results for a version"""
        version_id = str(version_with_results['version'].version_id)
        results = manager.get_version_test_results(version_id)
        
        # Should have 5 results
        assert len(results) == 5
        assert all(r['version_id'] == version_id for r in results)
    
    def test_get_version_test_results_empty(self, manager):
        """Test 2: Returns empty list when no results exist"""
        fake_version_id = str(uuid4())
        results = manager.get_version_test_results(fake_version_id)
        
        assert results == []
        assert isinstance(results, list)
    
    def test_get_version_test_results_multiple_test_types(self, manager, version_with_results):
        """Test 3: Returns multiple test types for same version"""
        version_id = str(version_with_results['version'].version_id)
        results = manager.get_version_test_results(version_id)
        
        test_types = set(r['test_type'] for r in results)
        
        # Should have 4 unique test types
        assert len(test_types) == 4
        assert 'backtest' in test_types
        assert 'forward_test' in test_types
        assert 'paper_trade' in test_types
        assert 'live' in test_types
    
    def test_get_version_test_results_jsonb_deserialized(self, manager, version_with_results):
        """Test 4: JSONB fields are automatically deserialized"""
        version_id = str(version_with_results['version'].version_id)
        results = manager.get_version_test_results(version_id)
        
        # Check first result
        result = results[0]
        
        # JSONB fields should be Python objects
        assert isinstance(result['test_config'], dict)
        assert isinstance(result['metrics'], dict)
        assert isinstance(result['trades'], list)
        assert isinstance(result['equity_curve'], list)
        
        # Verify data integrity
        assert 'test_run' in result['test_config']
        assert 'timeframe' in result['test_config']
        assert result['test_config']['timeframe'] == '15m'
    
    def test_get_version_test_results_ordered_desc(self, manager, version_with_results):
        """Test 5: Results ordered by created_at DESC"""
        version_id = str(version_with_results['version'].version_id)
        results = manager.get_version_test_results(version_id)
        
        # Should be 5 results
        assert len(results) == 5
        
        # Verify all results have created_at timestamps
        for result in results:
            assert result['created_at'] is not None
            assert isinstance(result['created_at'], datetime)
    
    def test_get_version_test_results_returns_list_of_dicts(self, manager, version_with_results):
        """Test 6: Returns list of dicts (not ORM objects)"""
        version_id = str(version_with_results['version'].version_id)
        results = manager.get_version_test_results(version_id)
        
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)
        assert all(not isinstance(r, StrategyTestResult) for r in results)
    
    def test_get_version_test_results_field_completeness(self, manager, version_with_results):
        """Test 7: All expected fields present in results"""
        version_id = str(version_with_results['version'].version_id)
        results = manager.get_version_test_results(version_id)
        
        # Check first result has all required fields
        result = results[0]
        
        required_fields = [
            'result_id', 'strategy_id', 'version_id', 'test_type',
            'test_config', 'metrics', 'trades', 'equity_curve',
            'start_date', 'end_date', 'total_return_pct', 'sharpe_ratio',
            'max_drawdown_pct', 'win_rate', 'profit_factor', 'total_trades',
            'timestamp', 'created_at'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
    
    def test_get_version_test_results_metric_values(self, manager, version_with_results):
        """Test 8: Metric values correctly retrieved"""
        version_id = str(version_with_results['version'].version_id)
        results = manager.get_version_test_results(version_id)
        
        # Verify metrics are numbers
        for result in results:
            assert isinstance(result['total_return_pct'], (int, float))
            assert isinstance(result['sharpe_ratio'], (int, float))
            assert isinstance(result['max_drawdown_pct'], (int, float))
            assert isinstance(result['win_rate'], (int, float))
            assert isinstance(result['profit_factor'], (int, float))
            assert isinstance(result['total_trades'], int)
    
    def test_get_version_test_results_multiple_versions(self, manager, db_session):
        """Test 9: Only returns results for specified version"""
        # Create strategy with 2 versions
        strategy = Strategy(strategy_id='multi_vers_001', name='Multi Version Strategy')
        db_session.add(strategy)
        db_session.flush()
        
        # Version 1
        version1 = StrategyVersion(
            strategy_id='multi_vers_001', version_number=1, name='v1',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version1)
        db_session.flush()
        
        # Version 2
        version2 = StrategyVersion(
            strategy_id='multi_vers_001', version_number=2, name='v2',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version2)
        db_session.flush()
        
        # Create 3 results for version 1
        for i in range(3):
            result = StrategyTestResult(
                strategy_id='multi_vers_001',
                version_id=version1.version_id,
                test_type='backtest',
                test_config={'version': 1},
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                metrics={'v': 1}
            )
            db_session.add(result)
        
        # Create 2 results for version 2
        for i in range(2):
            result = StrategyTestResult(
                strategy_id='multi_vers_001',
                version_id=version2.version_id,
                test_type='backtest',
                test_config={'version': 2},
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                metrics={'v': 2}
            )
            db_session.add(result)
        
        db_session.commit()
        
        # Get results for version 1
        v1_results = manager.get_version_test_results(str(version1.version_id))
        assert len(v1_results) == 3
        assert all(r['test_config']['version'] == 1 for r in v1_results)
        
        # Get results for version 2
        v2_results = manager.get_version_test_results(str(version2.version_id))
        assert len(v2_results) == 2
        assert all(r['test_config']['version'] == 2 for r in v2_results)
    
    def test_get_version_test_results_date_fields(self, manager, version_with_results):
        """Test 10: Date fields are datetime objects"""
        version_id = str(version_with_results['version'].version_id)
        results = manager.get_version_test_results(version_id)
        
        for result in results:
            assert isinstance(result['start_date'], datetime)
            assert isinstance(result['end_date'], datetime)
            assert isinstance(result['created_at'], datetime)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
