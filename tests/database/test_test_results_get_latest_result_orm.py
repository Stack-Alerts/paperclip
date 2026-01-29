"""
Unit tests for get_latest_test_result() ORM refactoring
Sprint 1.6.1 - Task 3.1.4

Tests verify get_latest_test_result() works correctly with ORM.
Institutional-grade testing for latest result retrieval.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from src.optimizer_v3.database.test_results_manager import TestResultsManager
from src.optimizer_v3.database.models import Strategy, StrategyVersion, StrategyTestResult


class TestGetLatestTestResultORM:
    """Test get_latest_test_result() ORM refactoring - Task 3.1.4"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create test results database manager"""
        return TestResultsManager(db_session)
    
    @pytest.fixture
    def strategy_version_with_results(self, db_session):
        """Create strategy/version with multiple test results"""
        # Create parent strategy
        strategy = Strategy(strategy_id='latest_test_001', name='Latest Test Strategy')
        db_session.add(strategy)
        db_session.flush()
        
        # Create strategy version
        version = StrategyVersion(
            strategy_id='latest_test_001',
            version_number=1,
            name='Latest Test Strategy v1',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(version)
        db_session.flush()
        
        # Create 3 backtest results at different times
        results = []
        for i in range(3):
            result = StrategyTestResult(
                strategy_id='latest_test_001',
                version_id=version.version_id,
                test_type='backtest',
                test_config={'run': i+1, 'timeframe': '15m'},
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                metrics={'run': i+1, 'sharpe': 1.5 + i*0.1},
                total_return_pct=10.0 + i*2.0,
                sharpe_ratio=1.5 + i*0.1
            )
            db_session.add(result)
            db_session.commit()  # Commit each to get different created_at
            db_session.refresh(result)
            results.append(result)
        
        # Create 1 forward_test result
        forward_result = StrategyTestResult(
            strategy_id='latest_test_001',
            version_id=version.version_id,
            test_type='forward_test',
            test_config={'type': 'forward'},
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            metrics={'type': 'forward'}
        )
        db_session.add(forward_result)
        db_session.commit()
        
        return {
            'strategy': strategy,
            'version': version,
            'backtest_results': results,
            'forward_result': forward_result
        }
    
    def test_get_latest_test_result_basic(self, manager, strategy_version_with_results):
        """Test 1: Get latest result for strategy/version/type"""
        strategy_id = 'latest_test_001'
        version_id = str(strategy_version_with_results['version'].version_id)
        
        latest = manager.get_latest_test_result(strategy_id, version_id, 'backtest')
        
        # Should get a result (latest of 3)
        assert latest is not None
        assert latest['test_type'] == 'backtest'
        assert 'run' in latest['test_config']
        assert latest['test_config']['run'] in [1, 2, 3]
    
    def test_get_latest_test_result_not_found(self, manager):
        """Test 2: Returns None when no results exist"""
        result = manager.get_latest_test_result(
            'nonexistent',
            str(uuid4()),
            'backtest'
        )
        
        assert result is None
    
    def test_get_latest_test_result_filters_by_test_type(self, manager, strategy_version_with_results):
        """Test 3: Correctly filters by test_type"""
        strategy_id = 'latest_test_001'
        version_id = str(strategy_version_with_results['version'].version_id)
        
        # Get backtest result
        backtest = manager.get_latest_test_result(strategy_id, version_id, 'backtest')
        assert backtest['test_type'] == 'backtest'
        assert 'run' in backtest['test_config']
        
        # Get forward_test result
        forward = manager.get_latest_test_result(strategy_id, version_id, 'forward_test')
        assert forward['test_type'] == 'forward_test'
        assert forward['test_config']['type'] == 'forward'
    
    def test_get_latest_test_result_multiple_versions(self, manager, db_session):
        """Test 4: Correctly filters by version_id"""
        # Create strategy with 2 versions
        strategy = Strategy(strategy_id='multi_v_002', name='Multi Version')
        db_session.add(strategy)
        db_session.flush()
        
        # Version 1
        v1 = StrategyVersion(
            strategy_id='multi_v_002', version_number=1, name='v1',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(v1)
        db_session.flush()
        
        # Version 2
        v2 = StrategyVersion(
            strategy_id='multi_v_002', version_number=2, name='v2',
            blocks=[], signals={}, parameters={}, entry_conditions={},
            exit_conditions=[], risk_management={}, backtest_config={}
        )
        db_session.add(v2)
        db_session.flush()
        
        # Add result for v1
        r1 = StrategyTestResult(
            strategy_id='multi_v_002',
            version_id=v1.version_id,
            test_type='backtest',
            test_config={'version': 1},
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            metrics={'v': 1}
        )
        db_session.add(r1)
        
        # Add result for v2
        r2 = StrategyTestResult(
            strategy_id='multi_v_002',
            version_id=v2.version_id,
            test_type='backtest',
            test_config={'version': 2},
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            metrics={'v': 2}
        )
        db_session.add(r2)
        db_session.commit()
        
        # Get for v1
        v1_result = manager.get_latest_test_result('multi_v_002', str(v1.version_id), 'backtest')
        assert v1_result['test_config']['version'] == 1
        
        # Get for v2
        v2_result = manager.get_latest_test_result('multi_v_002', str(v2.version_id), 'backtest')
        assert v2_result['test_config']['version'] == 2
    
    def test_get_latest_test_result_jsonb_deserialized(self, manager, strategy_version_with_results):
        """Test 5: JSONB fields automatically deserialized"""
        strategy_id = 'latest_test_001'
        version_id = str(strategy_version_with_results['version'].version_id)
        
        latest = manager.get_latest_test_result(strategy_id, version_id, 'backtest')
        
        # JSONB fields should be Python objects
        assert isinstance(latest['test_config'], dict)
        assert isinstance(latest['metrics'], dict)
        assert 'run' in latest['test_config']
        assert 'run' in latest['metrics']
    
    def test_get_latest_test_result_returns_dict(self, manager, strategy_version_with_results):
        """Test 6: Returns dict (not ORM object)"""
        strategy_id = 'latest_test_001'
        version_id = str(strategy_version_with_results['version'].version_id)
        
        latest = manager.get_latest_test_result(strategy_id, version_id, 'backtest')
        
        assert isinstance(latest, dict)
        assert not isinstance(latest, StrategyTestResult)
    
    def test_get_latest_test_result_field_completeness(self, manager, strategy_version_with_results):
        """Test 7: All expected fields present"""
        strategy_id = 'latest_test_001'
        version_id = str(strategy_version_with_results['version'].version_id)
        
        latest = manager.get_latest_test_result(strategy_id, version_id, 'backtest')
        
        required_fields = [
            'result_id', 'strategy_id', 'version_id', 'test_type',
            'test_config', 'metrics', 'start_date', 'end_date',
            'total_return_pct', 'sharpe_ratio', 'created_at'
        ]
        
        for field in required_fields:
            assert field in latest, f"Missing field: {field}"
    
    def test_get_latest_test_result_correct_ids(self, manager, strategy_version_with_results):
        """Test 8: Returns correct strategy and version IDs"""
        strategy_id = 'latest_test_001'
        version_id = str(strategy_version_with_results['version'].version_id)
        
        latest = manager.get_latest_test_result(strategy_id, version_id, 'backtest')
        
        assert latest['strategy_id'] == strategy_id
        assert latest['version_id'] == version_id
        assert latest['test_type'] == 'backtest'
    
    def test_get_latest_test_result_date_fields(self, manager, strategy_version_with_results):
        """Test 9: Date fields are datetime objects"""
        strategy_id = 'latest_test_001'
        version_id = str(strategy_version_with_results['version'].version_id)
        
        latest = manager.get_latest_test_result(strategy_id, version_id, 'backtest')
        
        assert isinstance(latest['start_date'], datetime)
        assert isinstance(latest['end_date'], datetime)
        assert isinstance(latest['created_at'], datetime)
    
    def test_get_latest_test_result_metric_values(self, manager, strategy_version_with_results):
        """Test 10: Metric values correctly retrieved"""
        strategy_id = 'latest_test_001'
        version_id = str(strategy_version_with_results['version'].version_id)
        
        latest = manager.get_latest_test_result(strategy_id, version_id, 'backtest')
        
        # Should have metric values (one of the 3 results)
        assert latest['total_return_pct'] in [10.0, 12.0, 14.0]
        assert latest['sharpe_ratio'] in [1.5, 1.6, 1.7]
        assert isinstance(latest['total_return_pct'], (int, float))
        assert isinstance(latest['sharpe_ratio'], (int, float))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
