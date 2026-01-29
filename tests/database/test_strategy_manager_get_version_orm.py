"""
Unit tests for get_strategy_version() ORM refactoring
Sprint 1.6.1 - Task 1.3

Tests verify get_strategy_version() works correctly with ORM StrategyVersion model.
Institutional-grade testing for read operations with JSONB fields.
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
from src.optimizer_v3.database.models import Strategy, StrategyVersion


class TestGetStrategyVersionORM:
    """Test get_strategy_version() ORM refactoring - Task 1.3"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create strategy database manager"""
        return StrategyDatabaseManager(db_session)
    
    @pytest.fixture
    def test_strategy(self, manager):
        """Create a test strategy"""
        return manager.create_strategy("Test Strategy for Get Tests")
    
    @pytest.fixture
    def test_version_data(self, test_strategy):
        """Create test version data"""
        return {
            'strategy_id': test_strategy,
            'name': 'Test Version for Get',
            'description': 'Test description',
            'blocks': [{'name': 'test_block', 'signals': [], 'parameters': {'value': 10}}],
            'signals': {'test_signal': {'enabled': True, 'threshold': 0.5}},
            'parameters': {'test_param': 10, 'nested': {'deep': 'value'}},
            'entry_conditions': {'logic': 'AND', 'rules': []},
            'exit_conditions': [{'type': 'stop_loss', 'value': 0.02}],
            'risk_management': {'max_position': 1.0, 'stop_loss': 0.02},
            'backtest_config': {'start_date': '2023-01-01', 'end_date': '2023-12-31'}
        }
    
    @pytest.fixture
    def created_version_id(self, manager, test_version_data):
        """Create a version and return its ID"""
        return manager.create_strategy_version(test_version_data)
    
    def test_get_version_basic(self, manager, created_version_id, test_version_data):
        """Test 1: Basic version retrieval with ORM"""
        # Get the version
        version = manager.get_strategy_version(created_version_id)
        
        # Verify it was retrieved
        assert version is not None
        assert isinstance(version, dict)
        assert version['version_id'] == created_version_id
        assert version['name'] == test_version_data['name']
        assert version['strategy_id'] == test_version_data['strategy_id']
    
    def test_get_version_jsonb_fields_as_python_objects(self, manager, created_version_id):
        """Test 2: JSONB fields are returned as Python objects (not strings)"""
        version = manager.get_strategy_version(created_version_id)
        
        # Verify JSONB fields are Python objects
        assert isinstance(version['blocks'], list)
        assert isinstance(version['signals'], dict)
        assert isinstance(version['parameters'], dict)
        assert isinstance(version['entry_conditions'], dict)
        assert isinstance(version['exit_conditions'], list)
        assert isinstance(version['risk_management'], dict)
        assert isinstance(version['backtest_config'], dict)
        
        # Verify nested structures are preserved
        assert version['parameters']['nested']['deep'] == 'value'
        assert version['blocks'][0]['parameters']['value'] == 10
    
    def test_get_version_all_required_fields(self, manager, created_version_id):
        """Test 3: All expected fields are present in returned dict"""
        version = manager.get_strategy_version(created_version_id)
        
        # Required fields
        assert 'version_id' in version
        assert 'strategy_id' in version
        assert 'version_number' in version
        assert 'name' in version
        assert 'description' in version
        
        # JSONB fields
        assert 'blocks' in version
        assert 'signals' in version
        assert 'parameters' in version
        assert 'entry_conditions' in version
        assert 'exit_conditions' in version
        assert 'risk_management' in version
        assert 'backtest_config' in version
        assert 'backtest_results' in version
        assert 'metrics' in version
        assert 'trades' in version
        assert 'equity_curve' in version
        
        # Metadata fields
        assert 'timestamp' in version
        assert 'git_commit_hash' in version
        assert 'created_at' in version
        assert 'created_by' in version
        assert 'notes' in version
        assert 'tags' in version
        assert 'config_hash' in version
    
    def test_get_version_not_found_returns_none(self, manager):
        """Test 4: Non-existent version returns None"""
        # Generate random UUID that doesn't exist
        fake_uuid = str(uuid4())
        
        version = manager.get_strategy_version(fake_uuid)
        
        assert version is None
    
    def test_get_version_uuid_string_format(self, manager, created_version_id):
        """Test 5: version_id is returned as string UUID"""
        version = manager.get_strategy_version(created_version_id)
        
        # version_id should be string
        assert isinstance(version['version_id'], str)
        
        # Should be valid UUID format
        try:
            UUID(version['version_id'])
            valid_uuid = True
        except ValueError:
            valid_uuid = False
        
        assert valid_uuid
        assert version['version_id'] == created_version_id
    
    def test_get_version_timestamps_are_datetime(self, manager, created_version_id):
        """Test 6: Timestamp fields are datetime objects"""
        version = manager.get_strategy_version(created_version_id)
        
        assert isinstance(version['timestamp'], datetime)
        assert isinstance(version['created_at'], datetime)
    
    def test_get_version_with_optional_fields(self, manager, test_strategy):
        """Test 7: Optional fields (backtest_results, metrics, etc.) are retrievable"""
        # Create version with optional fields
        full_data = {
            'strategy_id': test_strategy,
            'name': 'Full Version',
            'blocks': [{'name': 'b1'}],
            'signals': {},
            'parameters': {},
            'entry_conditions': {},
            'exit_conditions': [],
            'risk_management': {},
            'backtest_config': {},
            'backtest_results': {'pnl': 1000, 'trades': 50},
            'metrics': {'sharpe': 1.5, 'drawdown': -0.10},
            'trades': [{'id': 1, 'profit': 100}],
            'equity_curve': [{'date': '2023-01-01', 'value': 10000}],
            'tags': ['test', 'full'],
            'notes': 'Test notes',
            'created_by': 'test_user',
            'git_commit_hash': 'abc123'
        }
        
        version_id = manager.create_strategy_version(full_data)
        version = manager.get_strategy_version(version_id)
        
        # Verify optional JSONB fields
        assert version['backtest_results'] == {'pnl': 1000, 'trades': 50}
        assert version['metrics'] == {'sharpe': 1.5, 'drawdown': -0.10}
        assert version['trades'] == [{'id': 1, 'profit': 100}]
        assert version['equity_curve'] == [{'date': '2023-01-01', 'value': 10000}]
        assert version['tags'] == ['test', 'full']
        assert version['notes'] == 'Test notes'
        assert version['created_by'] == 'test_user'
        assert version['git_commit_hash'] == 'abc123'
    
    def test_get_version_empty_optional_fields(self, manager, test_strategy):
        """Test 8: Empty optional JSONB fields are None"""
        # Create version without optional fields
        minimal_data = {
            'strategy_id': test_strategy,
            'name': 'Minimal Version',
            'blocks': [],
            'signals': {},
            'parameters': {},
            'entry_conditions': {},
            'exit_conditions': [],
            'risk_management': {},
            'backtest_config': {}
        }
        
        version_id = manager.create_strategy_version(minimal_data)
        version = manager.get_strategy_version(version_id)
        
        # Optional JSONB fields should be None
        assert version['backtest_results'] is None
        assert version['metrics'] is None
        assert version['trades'] is None
        assert version['equity_curve'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
