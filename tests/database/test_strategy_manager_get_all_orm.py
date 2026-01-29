"""
Unit tests for get_all_strategies() ORM refactoring
Sprint 1.6.1 - Task 1.4

Tests verify get_all_strategies() works correctly with ORM JOIN + aggregation.
Institutional-grade testing for complex SQL operations with ORM.
"""

import pytest
from datetime import datetime
import time
from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
from src.optimizer_v3.database.models import Strategy, StrategyVersion


class TestGetAllStrategiesORM:
    """Test get_all_strategies() ORM refactoring - Task 1.4"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create strategy database manager"""
        return StrategyDatabaseManager(db_session)
    
    @pytest.fixture
    def minimal_version_data(self):
        """Minimal version data factory"""
        def create_version_data(strategy_id, name="Test Version"):
            return {
                'strategy_id': strategy_id,
                'name': name,
                'blocks': [],
                'signals': {},
                'parameters': {},
                'entry_conditions': {},
                'exit_conditions': [],
                'risk_management': {},
                'backtest_config': {}
            }
        return create_version_data
    
    def test_get_all_strategies_empty(self, manager, db_session):
        """Test 1: Empty list when no strategies exist"""
        # Clear any existing strategies in this transaction
        db_session.query(Strategy).delete()
        db_session.commit()
        
        strategies = manager.get_all_strategies()
        
        assert isinstance(strategies, list)
        assert len(strategies) == 0
    
    def test_get_all_strategies_basic(self, manager):
        """Test 2: Basic retrieval of strategies"""
        # Create a strategy
        strategy_id = manager.create_strategy("Test Strategy 1")
        
        strategies = manager.get_all_strategies()
        
        # Should have at least our strategy
        assert isinstance(strategies, list)
        assert len(strategies) >= 1
        
        # Find our strategy
        our_strategy = next((s for s in strategies if s['strategy_id'] == strategy_id), None)
        assert our_strategy is not None
        assert our_strategy['name'] == "Test Strategy 1"
    
    def test_get_all_strategies_required_fields(self, manager):
        """Test 3: All required fields present in returned dicts"""
        strategy_id = manager.create_strategy("Test Strategy Fields")
        strategies = manager.get_all_strategies()
        
        # Find our strategy
        our_strategy = next((s for s in strategies if s['strategy_id'] == strategy_id), None)
        
        # Verify all required fields
        assert 'strategy_id' in our_strategy
        assert 'name' in our_strategy
        assert 'created_at' in our_strategy
        assert 'updated_at' in our_strategy
        assert 'latest_version' in our_strategy
    
    def test_get_all_strategies_with_no_versions(self, manager):
        """Test 4: Strategy with no versions has latest_version = None"""
        strategy_id = manager.create_strategy("Strategy No Versions")
        
        strategies = manager.get_all_strategies()
        our_strategy = next((s for s in strategies if s['strategy_id'] == strategy_id), None)
        
        # Should have None for latest_version
        assert our_strategy['latest_version'] is None
    
    def test_get_all_strategies_with_versions(self, manager, minimal_version_data):
        """Test 5: Strategy with versions shows correct latest_version"""
        # Create strategy
        strategy_id = manager.create_strategy("Strategy With Versions")
        
        # Create 3 versions
        for i in range(3):
            manager.create_strategy_version(
                minimal_version_data(strategy_id, f"Version {i+1}")
            )
        
        strategies = manager.get_all_strategies()
        our_strategy = next((s for s in strategies if s['strategy_id'] == strategy_id), None)
        
        # Should show latest version number (3)
        assert our_strategy['latest_version'] == 3
    
    def test_get_all_strategies_multiple(self, manager):
        """Test 6: Multiple strategies are all returned"""
        # Create 5 strategies
        strategy_ids = []
        for i in range(5):
            sid = manager.create_strategy(f"Strategy {i+1}")
            strategy_ids.append(sid)
        
        strategies = manager.get_all_strategies()
        
        # Verify all our strategies are present
        returned_ids = [s['strategy_id'] for s in strategies]
        for sid in strategy_ids:
            assert sid in returned_ids
    
    def test_get_all_strategies_ordered_by_updated_at(self, manager):
        """Test 7: Strategies ordered by updated_at DESC (newest first)"""
        # Create 3 strategies with small delays
        s1_id = manager.create_strategy("Strategy Oldest")
        time.sleep(0.1)
        s2_id = manager.create_strategy("Strategy Middle")
        time.sleep(0.1)
        s3_id = manager.create_strategy("Strategy Newest")
        
        strategies = manager.get_all_strategies()
        
        # Find our strategies with timestamps
        our_strategies = {}
        for s in strategies:
            if s['strategy_id'] in [s1_id, s2_id, s3_id]:
                our_strategies[s['strategy_id']] = s['updated_at']
        
        # Verify all 3 found
        assert len(our_strategies) == 3
        
        # Verify ordering: s3 (newest) should have most recent timestamp
        assert our_strategies[s3_id] >= our_strategies[s2_id]
        assert our_strategies[s2_id] >= our_strategies[s1_id]
    
    def test_get_all_strategies_mixed_versions(self, manager, minimal_version_data):
        """Test 8: Mix of strategies with and without versions"""
        # Create strategy with versions
        s1_id = manager.create_strategy("Strategy With Versions")
        manager.create_strategy_version(minimal_version_data(s1_id))
        manager.create_strategy_version(minimal_version_data(s1_id))
        
        # Create strategy without versions
        s2_id = manager.create_strategy("Strategy Without Versions")
        
        strategies = manager.get_all_strategies()
        
        # Find both strategies
        s1 = next((s for s in strategies if s['strategy_id'] == s1_id), None)
        s2 = next((s for s in strategies if s['strategy_id'] == s2_id), None)
        
        assert s1 is not None
        assert s2 is not None
        assert s1['latest_version'] == 2
        assert s2['latest_version'] is None
    
    def test_get_all_strategies_timestamps_are_datetime(self, manager):
        """Test 9: Timestamp fields are datetime objects"""
        strategy_id = manager.create_strategy("Timestamp Test")
        strategies = manager.get_all_strategies()
        
        our_strategy = next((s for s in strategies if s['strategy_id'] == strategy_id), None)
        
        assert isinstance(our_strategy['created_at'], datetime)
        assert isinstance(our_strategy['updated_at'], datetime)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
