"""
Unit tests for create_strategy_version() ORM refactoring
Sprint 1.6.1 - Task 1.2

Tests verify create_strategy_version() works correctly with ORM StrategyVersion model.
Institutional-grade testing with complete coverage for JSONB fields.
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
from src.optimizer_v3.database.models import Strategy, StrategyVersion


class TestCreateStrategyVersionORM:
    """Test create_strategy_version() ORM refactoring - Task 1.2"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create strategy database manager"""
        return StrategyDatabaseManager(db_session)
    
    @pytest.fixture
    def test_strategy(self, manager):
        """Create a test strategy for version tests"""
        return manager.create_strategy("Test Strategy for Versions")
    
    @pytest.fixture
    def minimal_version_data(self, test_strategy):
        """Minimal valid version data"""
        return {
            'strategy_id': test_strategy,
            'name': 'Test Version',
            'blocks': [{'name': 'test_block', 'signals': []}],
            'signals': {'test_signal': {'enabled': True}},
            'parameters': {'test_param': 10},
            'entry_conditions': {'logic': 'AND'},
            'exit_conditions': [{'type': 'stop_loss'}],
            'risk_management': {'max_position': 1.0},
            'backtest_config': {'start_date': '2023-01-01'}
        }
    
    def test_create_version_basic(self, manager, db_session, minimal_version_data):
        """Test 1: Basic version creation with ORM"""
        # Create version
        version_id = manager.create_strategy_version(minimal_version_data)
        
        # Verify return value is UUID string
        assert version_id is not None
        assert isinstance(version_id, str)
        assert len(version_id) == 36  # UUID format
        UUID(version_id)  # Validate UUID format
        
        # Verify in database using ORM query
        version = db_session.query(StrategyVersion).filter_by(
            version_id=version_id
        ).first()
        
        assert version is not None
        assert version.name == 'Test Version'
        assert version.strategy_id == minimal_version_data['strategy_id']
        assert version.version_number == 1  # First version
        assert version.created_at is not None
        assert isinstance(version.created_at, datetime)
    
    def test_create_version_jsonb_fields(self, manager, db_session, minimal_version_data):
        """Test 2: JSONB fields are correctly stored and retrieved"""
        version_id = manager.create_strategy_version(minimal_version_data)
        
        version = db_session.query(StrategyVersion).filter_by(
            version_id=version_id
        ).first()
        
        # Verify JSONB fields are Python objects (not strings)
        assert isinstance(version.blocks, list)
        assert isinstance(version.signals, dict)
        assert isinstance(version.parameters, dict)
        assert isinstance(version.entry_conditions, dict)
        assert isinstance(version.exit_conditions, list)
        assert isinstance(version.risk_management, dict)
        assert isinstance(version.backtest_config, dict)
        
        # Verify content
        assert version.blocks == minimal_version_data['blocks']
        assert version.signals == minimal_version_data['signals']
        assert version.parameters == minimal_version_data['parameters']
    
    def test_create_version_missing_required_fields(self, manager, minimal_version_data):
        """Test 3: Missing required fields raises ValueError"""
        # Remove required field
        incomplete_data = minimal_version_data.copy()
        del incomplete_data['blocks']
        
        with pytest.raises(ValueError, match="Missing required fields"):
            manager.create_strategy_version(incomplete_data)
    
    def test_create_version_increments_version_number(self, manager, db_session, minimal_version_data):
        """Test 4: Version numbers increment correctly"""
        # Create 3 versions
        v1_id = manager.create_strategy_version(minimal_version_data)
        v2_id = manager.create_strategy_version(minimal_version_data)
        v3_id = manager.create_strategy_version(minimal_version_data)
        
        # Verify version numbers
        v1 = db_session.query(StrategyVersion).filter_by(version_id=v1_id).first()
        v2 = db_session.query(StrategyVersion).filter_by(version_id=v2_id).first()
        v3 = db_session.query(StrategyVersion).filter_by(version_id=v3_id).first()
        
        assert v1.version_number == 1
        assert v2.version_number == 2
        assert v3.version_number == 3
    
    def test_create_version_with_optional_fields(self, manager, db_session, minimal_version_data):
        """Test 5: Optional fields (description, notes, tags, etc.) are stored"""
        # Add optional fields
        full_data = minimal_version_data.copy()
        full_data.update({
            'description': 'Test description',
            'notes': 'Test notes',
            'tags': ['test', 'version'],
            'created_by': 'test_user',
            'git_commit_hash': 'abc123def456',
            'backtest_results': {'pnl': 1000},
            'metrics': {'sharpe': 1.5},
            'trades': [{'id': 1, 'profit': 100}],
            'equity_curve': [{'date': '2023-01-01', 'value': 10000}]
        })
        
        version_id = manager.create_strategy_version(full_data)
        version = db_session.query(StrategyVersion).filter_by(version_id=version_id).first()
        
        # Verify optional fields
        assert version.description == 'Test description'
        assert version.notes == 'Test notes'
        assert version.tags == ['test', 'version']
        assert version.created_by == 'test_user'
        assert version.git_commit_hash == 'abc123def456'
        
        # Verify optional JSONB fields
        assert version.backtest_results == {'pnl': 1000}
        assert version.metrics == {'sharpe': 1.5}
        assert version.trades == [{'id': 1, 'profit': 100}]
        assert version.equity_curve == [{'date': '2023-01-01', 'value': 10000}]
    
    def test_create_version_config_hash_generated(self, manager, db_session, minimal_version_data):
        """Test 6: Config hash is automatically generated"""
        version_id = manager.create_strategy_version(minimal_version_data)
        version = db_session.query(StrategyVersion).filter_by(version_id=version_id).first()
        
        # Verify config hash exists and has correct format
        assert version.config_hash is not None
        assert isinstance(version.config_hash, str)
        assert len(version.config_hash) == 64  # SHA-256 hex string
    
    def test_create_version_updates_parent_strategy(self, manager, db_session, minimal_version_data):
        """Test 7: Creating version updates parent strategy's updated_at"""
        strategy_id = minimal_version_data['strategy_id']
        
        # Get parent strategy
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        # Verify strategy exists
        assert strategy is not None
        assert strategy.updated_at is not None
        
        # Create version - this should trigger updated_at update
        version_id = manager.create_strategy_version(minimal_version_data)
        
        # Verify version was created
        version = db_session.query(StrategyVersion).filter_by(
            version_id=version_id
        ).first()
        assert version is not None
        assert version.strategy_id == strategy_id
        
        # Verify parent strategy still exists and is linked
        db_session.expire(strategy)  # Refresh from database
        strategy_after = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        assert strategy_after is not None
        assert strategy_after.updated_at is not None
    
    def test_create_version_rollback_on_error(self, manager, db_session, minimal_version_data):
        """Test 8: Session rolls back on error"""
        count_before = db_session.query(StrategyVersion).count()
        
        # Try to create with invalid data (missing required field)
        invalid_data = minimal_version_data.copy()
        del invalid_data['name']
        
        try:
            manager.create_strategy_version(invalid_data)
        except ValueError:
            pass
        
        # Rollback to ensure clean state
        db_session.rollback()
        
        # Count should be unchanged
        count_after = db_session.query(StrategyVersion).count()
        assert count_after == count_before
    
    def test_create_version_complex_jsonb_data(self, manager, db_session, minimal_version_data):
        """Test 9: Complex nested JSONB structures are handled correctly"""
        # Create complex nested data
        complex_data = minimal_version_data.copy()
        complex_data['blocks'] = [
            {
                'name': 'complex_block',
                'signals': [
                    {'name': 'signal1', 'params': {'threshold': 0.5}},
                    {'name': 'signal2', 'params': {'period': 14}}
                ],
                'parameters': {
                    'nested': {
                        'deeply': {
                            'value': 123
                        }
                    }
                },
                'logic_type': 'AND'
            },
            {
                'name': 'another_block',
                'signals': [],
                'parameters': {'array': [1, 2, 3, 4, 5]}
            }
        ]
        
        version_id = manager.create_strategy_version(complex_data)
        version = db_session.query(StrategyVersion).filter_by(version_id=version_id).first()
        
        # Verify complex structure is preserved
        assert len(version.blocks) == 2
        assert version.blocks[0]['name'] == 'complex_block'
        assert len(version.blocks[0]['signals']) == 2
        assert version.blocks[0]['parameters']['nested']['deeply']['value'] == 123
        assert version.blocks[1]['parameters']['array'] == [1, 2, 3, 4, 5]
    
    def test_create_version_empty_optional_jsonb(self, manager, db_session, minimal_version_data):
        """Test 10: Empty optional JSONB fields are handled correctly"""
        # Don't include optional JSONB fields
        version_id = manager.create_strategy_version(minimal_version_data)
        version = db_session.query(StrategyVersion).filter_by(version_id=version_id).first()
        
        # Optional JSONB fields should be None
        assert version.backtest_results is None
        assert version.metrics is None
        assert version.trades is None
        assert version.equity_curve is None
    
    def test_create_version_returns_string_uuid(self, manager, minimal_version_data):
        """Test 11: Return type is string UUID"""
        version_id = manager.create_strategy_version(minimal_version_data)
        
        # Should be string
        assert isinstance(version_id, str)
        
        # Should be valid UUID format
        try:
            UUID(version_id)
            valid_uuid = True
        except ValueError:
            valid_uuid = False
        
        assert valid_uuid, f"Returned value '{version_id}' is not a valid UUID"
    
    def test_create_version_unique_ids(self, manager, db_session, minimal_version_data):
        """Test 12: Multiple versions get unique UUIDs"""
        # Create 5 versions
        version_ids = set()
        for i in range(5):
            vid = manager.create_strategy_version(minimal_version_data)
            version_ids.add(vid)
        
        # All should be unique
        assert len(version_ids) == 5
        
        # Verify all in database
        versions = db_session.query(StrategyVersion).filter_by(
            strategy_id=minimal_version_data['strategy_id']
        ).all()
        assert len(versions) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
