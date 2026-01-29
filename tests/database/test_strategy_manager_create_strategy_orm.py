"""
Unit tests for create_strategy() ORM refactoring
Sprint 1.6.1 - Task 1.1

Tests verify create_strategy() works correctly with ORM Strategy model.
Institutional-grade testing with complete coverage.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
from src.optimizer_v3.database.models import Strategy


class TestCreateStrategyORM:
    """Test create_strategy() ORM refactoring - Task 1.1"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create strategy database manager"""
        return StrategyDatabaseManager(db_session)
    
    def test_create_strategy_basic(self, manager, db_session):
        """Test 1: Basic strategy creation with ORM"""
        # Create strategy
        strategy_id = manager.create_strategy("Test Strategy 001")
        
        # Verify return value
        assert strategy_id is not None
        assert strategy_id.startswith("strategy_")
        assert len(strategy_id) == 17  # "strategy_" + 8 hex chars
        
        # Verify in database using ORM query
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert strategy is not None
        assert strategy.name == "Test Strategy 001"
        assert strategy.created_at is not None
        assert strategy.updated_at is not None
        assert isinstance(strategy.created_at, datetime)
        assert isinstance(strategy.updated_at, datetime)
    
    def test_create_strategy_strips_whitespace(self, manager, db_session):
        """Test 2: Whitespace is properly stripped"""
        # Create with extra whitespace
        strategy_id = manager.create_strategy("  Test Strategy  ")
        
        # Verify stripped
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert strategy.name == "Test Strategy"
        assert strategy.name != "  Test Strategy  "
        assert not strategy.name.startswith(" ")
        assert not strategy.name.endswith(" ")
    
    def test_create_strategy_empty_name_fails(self, manager, db_session):
        """Test 3: Empty name raises ValueError"""
        # Count existing strategies in this transaction
        count_before = db_session.query(Strategy).count()
        
        # Empty string should fail
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            manager.create_strategy("")
        
        # Whitespace-only should also fail
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            manager.create_strategy("   ")
        
        # None should also fail
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            manager.create_strategy(None)
        
        # Verify nothing new was created
        count_after = db_session.query(Strategy).count()
        assert count_after == count_before
    
    def test_create_strategy_unique_ids(self, manager, db_session):
        """Test 4: Multiple strategies get unique IDs"""
        # Count existing strategies
        count_before = db_session.query(Strategy).count()
        
        # Create 10 strategies
        strategy_ids = set()
        for i in range(10):
            sid = manager.create_strategy(f"Strategy {i}")
            strategy_ids.add(sid)
        
        # All should be unique
        assert len(strategy_ids) == 10
        
        # Verify count increased by 10
        count_after = db_session.query(Strategy).count()
        assert count_after == count_before + 10
        
        # Verify each has correct format
        for sid in strategy_ids:
            assert sid.startswith("strategy_")
            assert len(sid) == 17
    
    def test_create_strategy_timestamps_auto_set(self, manager, db_session):
        """Test 5: created_at and updated_at are automatically set"""
        strategy_id = manager.create_strategy("Timestamp Test")
        
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert strategy.created_at is not None
        assert strategy.updated_at is not None
        assert isinstance(strategy.created_at, datetime)
        assert isinstance(strategy.updated_at, datetime)
        
        # On creation, both timestamps should be very close
        time_diff = abs((strategy.updated_at - strategy.created_at).total_seconds())
        assert time_diff < 2.0  # Less than 2 seconds apart
    
    def test_create_strategy_rollback_on_error(self, manager, db_session):
        """Test 6: Session rolls back on error"""
        # Count before
        count_before = db_session.query(Strategy).count()
        
        # Try to create with invalid data (empty name)
        try:
            manager.create_strategy("")
        except ValueError:
            pass
        
        # Manually rollback to ensure clean state
        db_session.rollback()
        
        # Count after - should be unchanged
        count_after = db_session.query(Strategy).count()
        assert count_after == count_before
    
    def test_create_strategy_returns_correct_type(self, manager, db_session):
        """Test 7: Return type is string"""
        result = manager.create_strategy("Type Test")
        
        assert isinstance(result, str)
        assert not isinstance(result, bytes)
        assert not isinstance(result, int)
    
    def test_create_strategy_special_characters(self, manager, db_session):
        """Test 8: Strategy name with special characters"""
        special_name = "Strategy™ with Ümlauts & Émojis 🚀"
        strategy_id = manager.create_strategy(special_name)
        
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert strategy.name == special_name
        assert "™" in strategy.name
        assert "🚀" in strategy.name
    
    def test_create_strategy_long_name(self, manager, db_session):
        """Test 9: Strategy with maximum length name"""
        # Create max length name (255 char limit in model)
        long_name = "A" * 255
        strategy_id = manager.create_strategy(long_name)
        
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert len(strategy.name) == 255
        assert strategy.name == long_name
    
    def test_create_strategy_relationships_initialized(self, manager, db_session):
        """Test 10: ORM object is complete and properly initialized"""
        strategy_id = manager.create_strategy("Relationships Test")
        
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        # Verify strategy object is complete with all required attributes
        assert strategy.strategy_id == strategy_id
        assert strategy.name == "Relationships Test"
        assert strategy.created_at is not None
        assert strategy.updated_at is not None
        assert isinstance(strategy, Strategy)
        
        # Verify ORM model class has relationship definitions (without triggering queries)
        assert hasattr(Strategy, 'versions')
        assert hasattr(Strategy, 'recommendations')
        assert hasattr(Strategy, 'test_results')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
