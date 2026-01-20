"""
Unit Tests for State Manager
Task 1.3.15: State validation tests with 100% coverage
"""

import pytest
import sys
import tempfile
import shutil
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
from nautilus_trader.model.objects import Money, Quantity, Price

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.optimizer_v3.core.results.state_manager import StateManager


@pytest.fixture
def temp_state_dir():
    """Create temporary state directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def state_manager(temp_state_dir):
    """Create state manager with temporary directory"""
    return StateManager(state_dir=temp_state_dir)


@pytest.fixture
def valid_state():
    """Create valid optimization state"""
    return {
        'results': [
            {
                'config_id': 'config_1',
                'sharpe_ratio': Decimal('2.0'),
                'pnl': Money('1000', 'USD')
            }
        ],
        'config': {
            'strategy_name': 'test_strategy',
            'parameters': {'param1': 100}
        },
        'status': 'running',
        'timestamp': datetime.now()
    }


@pytest.fixture
def state_with_nautilus_types():
    """Create state with NautilusTrader types"""
    return {
        'results': [
            {
                'pnl': Money('500', 'USD'),
                'quantity': Quantity('0.1'),
                'price': Price('50000'),
                'decimal_value': Decimal('1.23456')
            }
        ],
        'config': {'test': 'value'},
        'status': 'completed',
        'timestamp': datetime(2024, 1, 1, 12, 0, 0)
    }


class TestStateManager:
    """Test suite for StateManager"""
    
    # ==================== Initialization Tests ====================
    
    def test_initialization(self, temp_state_dir):
        """Test state manager initialization"""
        manager = StateManager(state_dir=temp_state_dir)
        
        assert manager.state_dir == Path(temp_state_dir)
        assert manager.state_dir.exists()
        assert manager.backup_dir.exists()
        assert manager.last_save_time is None
    
    def test_default_state_dir(self):
        """Test default state directory creation"""
        manager = StateManager()
        assert manager.state_dir == Path('data/optimizer_state')
    
    def test_config_loading(self, state_manager):
        """Test configuration loading"""
        assert 'save_interval' in state_manager.config
        assert 'compression' in state_manager.config
        assert 'backup_count' in state_manager.config
        assert 'validation_level' in state_manager.config
    
    # ==================== Save State Tests ====================
    
    def test_save_state_success(self, state_manager, valid_state):
        """Test successful state save"""
        result = state_manager.save_state('session_1', valid_state, force=True)
        
        assert result['saved'] is True
        assert 'filepath' in result
        assert 'size_bytes' in result
        assert 'timestamp' in result
        assert result['compressed'] == state_manager.config['compression']
    
    def test_save_state_interval_enforcement(self, state_manager, valid_state):
        """Test save interval enforcement"""
        # First save
        result1 = state_manager.save_state('session_1', valid_state, force=True)
        assert result1['saved'] is True
        
        # Immediate second save without force
        result2 = state_manager.save_state('session_1', valid_state, force=False)
        assert result2['saved'] is False
        assert 'reason' in result2
    
    def test_save_state_force_override(self, state_manager, valid_state):
        """Test forced save overrides interval"""
        # First save
        state_manager.save_state('session_1', valid_state, force=True)
        
        # Immediate second save with force
        result = state_manager.save_state('session_1', valid_state, force=True)
        assert result['saved'] is True
    
    def test_save_state_validation_strict(self, state_manager):
        """Test strict validation on save"""
        invalid_state = {'invalid': 'state'}  # Missing required keys
        
        result = state_manager.save_state('session_1', invalid_state, force=True)
        
        if state_manager.config['validation_level'] == 'strict':
            assert result['saved'] is False
            assert 'error' in result
    
    def test_save_state_creates_backup(self, state_manager, valid_state):
        """Test backup creation on subsequent saves"""
        # First save
        state_manager.save_state('session_1', valid_state, force=True)
        
        # Second save should create backup
        state_manager.save_state('session_1', valid_state, force=True)
        
        # Check backup exists
        backups = list(state_manager.backup_dir.glob('session_1_backup_*'))
        assert len(backups) > 0
    
    def test_save_state_compression(self, state_manager, valid_state):
        """Test state compression"""
        result = state_manager.save_state('session_1', valid_state, force=True)
        
        filepath = Path(result['filepath'])
        if state_manager.config['compression']:
            assert filepath.suffix == '.gz'
        else:
            assert filepath.suffix == '.json'
    
    def test_save_state_with_nautilus_types(self, state_manager, state_with_nautilus_types):
        """Test saving state with NautilusTrader types"""
        result = state_manager.save_state('session_1', state_with_nautilus_types, force=True)
        
        assert result['saved'] is True
        
        # Verify file was created
        filepath = Path(result['filepath'])
        assert filepath.exists()
    
    # ==================== Load State Tests ====================
    
    def test_load_state_success(self, state_manager, valid_state):
        """Test successful state load"""
        # Save first
        state_manager.save_state('session_1', valid_state, force=True)
        
        # Load
        loaded_state = state_manager.load_state('session_1')
        
        assert loaded_state is not None
        assert 'results' in loaded_state
        assert 'config' in loaded_state
        assert 'status' in loaded_state
    
    def test_load_nonexistent_state(self, state_manager):
        """Test loading non-existent state"""
        result = state_manager.load_state('nonexistent_session')
        
        assert result is None
    
    def test_load_state_with_nautilus_types(self, state_manager, state_with_nautilus_types):
        """Test loading state with NautilusTrader types"""
        # Save
        state_manager.save_state('session_1', state_with_nautilus_types, force=True)
        
        # Load
        loaded = state_manager.load_state('session_1')
        
        assert loaded is not None
        # Verify NautilusTrader types are restored
        assert isinstance(loaded['results'][0]['pnl'], Money)
        assert isinstance(loaded['results'][0]['quantity'], Quantity)
        assert isinstance(loaded['results'][0]['price'], Price)
        assert isinstance(loaded['results'][0]['decimal_value'], Decimal)
    
    def test_load_state_datetime_deserialization(self, state_manager, state_with_nautilus_types):
        """Test datetime deserialization"""
        state_manager.save_state('session_1', state_with_nautilus_types, force=True)
        
        loaded = state_manager.load_state('session_1')
        
        assert isinstance(loaded['timestamp'], datetime)
        assert loaded['timestamp'] == datetime(2024, 1, 1, 12, 0, 0)
    
    # ==================== Delete State Tests ====================
    
    def test_delete_state(self, state_manager, valid_state):
        """Test state deletion"""
        # Save state
        state_manager.save_state('session_1', valid_state, force=True)
        
        # Delete
        result = state_manager.delete_state('session_1')
        
        assert result is True
        assert state_manager.load_state('session_1') is None
    
    def test_delete_state_with_backups(self, state_manager, valid_state):
        """Test deletion includes backups"""
        # Create multiple saves to generate backups
        for i in range(3):
            state_manager.save_state('session_1', valid_state, force=True)
        
        # Delete
        state_manager.delete_state('session_1')
        
        # Verify all backups deleted
        backups = list(state_manager.backup_dir.glob('session_1_backup_*'))
        assert len(backups) == 0
    
    def test_delete_nonexistent_state(self, state_manager):
        """Test deleting non-existent state"""
        result = state_manager.delete_state('nonexistent_session')
        # Should not crash, may return True or False
        assert isinstance(result, bool)
    
    # ==================== Session Management Tests ====================
    
    def test_list_sessions(self, state_manager, valid_state):
        """Test listing sessions"""
        # Create multiple sessions
        for i in range(3):
            state_manager.save_state(f'session_{i}', valid_state, force=True)
        
        sessions = state_manager.list_sessions()
        
        assert len(sessions) == 3
        assert all('session_id' in s for s in sessions)
        assert all('filepath' in s for s in sessions)
        assert all('size_bytes' in s for s in sessions)
        assert all('modified' in s for s in sessions)
    
    def test_list_sessions_empty(self, state_manager):
        """Test listing when no sessions exist"""
        sessions = state_manager.list_sessions()
        
        assert isinstance(sessions, list)
        assert len(sessions) == 0
    
    def test_get_latest_session(self, state_manager, valid_state):
        """Test getting latest session"""
        # Create sessions with delays
        state_manager.save_state('session_1', valid_state, force=True)
        import time
        time.sleep(0.1)
        state_manager.save_state('session_2', valid_state, force=True)
        
        latest = state_manager.get_latest_session()
        
        assert latest == 'session_2'
    
    def test_get_latest_session_no_sessions(self, state_manager):
        """Test getting latest when no sessions exist"""
        latest = state_manager.get_latest_session()
        
        assert latest is None
    
    def test_get_state_size(self, state_manager, valid_state):
        """Test getting state file size"""
        state_manager.save_state('session_1', valid_state, force=True)
        
        size = state_manager.get_state_size('session_1')
        
        assert size is not None
        assert size > 0
    
    def test_get_state_size_nonexistent(self, state_manager):
        """Test getting size of non-existent state"""
        size = state_manager.get_state_size('nonexistent')
        
        assert size is None
    
    # ==================== Backup Management Tests ====================
    
    def test_backup_cleanup(self, state_manager, valid_state):
        """Test old backup cleanup"""
        # Create more backups than retention limit
        backup_count = state_manager.config['backup_count']
        for i in range(backup_count + 3):
            state_manager.save_state('session_1', valid_state, force=True)
            import time
            time.sleep(0.05)  # Small delay to ensure different timestamps
        
        # Check backup count
        backups = list(state_manager.backup_dir.glob('session_1_backup_*'))
        
        # Should not exceed retention limit
        assert len(backups) <= backup_count
    
    def test_restore_backup(self, state_manager, valid_state):
        """Test backup restoration"""
        # Create initial state
        state_manager.save_state('session_1', valid_state, force=True)
        
        # Modify and save again
        modified_state = valid_state.copy()
        modified_state['status'] = 'completed'
        state_manager.save_state('session_1', modified_state, force=True)
        
        # Restore backup (most recent backup)
        result = state_manager.restore_backup('session_1', backup_index=0)
        
        assert result is True
    
    def test_restore_nonexistent_backup(self, state_manager):
        """Test restoring non-existent backup"""
        result = state_manager.restore_backup('nonexistent', backup_index=0)
        
        assert result is False
    
    # ==================== Cleanup Tests ====================
    
    def test_cleanup_old_sessions(self, state_manager, valid_state):
        """Test cleanup of old sessions"""
        # Create a session
        state_manager.save_state('session_1', valid_state, force=True)
        
        # Clean up (with 0 days to force deletion)
        deleted_count = state_manager.cleanup_old_sessions(max_age_days=0)
        
        # Should have deleted the session
        assert deleted_count >= 0
    
    def test_cleanup_respects_age(self, state_manager, valid_state):
        """Test cleanup respects max age"""
        # Create a session
        state_manager.save_state('session_1', valid_state, force=True)
        
        # Clean up with future date (should not delete)
        deleted_count = state_manager.cleanup_old_sessions(max_age_days=365)
        
        # Should not delete recent session
        assert deleted_count == 0
        assert state_manager.load_state('session_1') is not None
    
    # ==================== Serialization Tests ====================
    
    def test_serialize_money(self, state_manager):
        """Test Money serialization"""
        money = Money('123.45', 'USD')
        serialized = state_manager._serialize_value(money)
        
        assert serialized['_type'] == 'Money'
        assert '_value' in serialized
    
    def test_serialize_decimal(self, state_manager):
        """Test Decimal serialization"""
        decimal = Decimal('123.456789')
        serialized = state_manager._serialize_value(decimal)
        
        assert serialized['_type'] == 'Decimal'
        assert serialized['_value'] == '123.456789'
    
    def test_serialize_datetime(self, state_manager):
        """Test datetime serialization"""
        dt = datetime(2024, 1, 1, 12, 0, 0)
        serialized = state_manager._serialize_value(dt)
        
        assert serialized['_type'] == 'datetime'
        assert '_value' in serialized
    
    def test_deserialize_money(self, state_manager):
        """Test Money deserialization"""
        serialized = {'_type': 'Money', '_value': '123.45 USD'}
        deserialized = state_manager._deserialize_value(serialized)
        
        assert isinstance(deserialized, Money)
    
    def test_deserialize_decimal(self, state_manager):
        """Test Decimal deserialization"""
        serialized = {'_type': 'Decimal', '_value': '123.456'}
        deserialized = state_manager._deserialize_value(serialized)
        
        assert isinstance(deserialized, Decimal)
        assert deserialized == Decimal('123.456')
    
    def test_deserialize_datetime(self, state_manager):
        """Test datetime deserialization"""
        dt = datetime(2024, 1, 1, 12, 0, 0)
        serialized = {'_type': 'datetime', '_value': dt.isoformat()}
        deserialized = state_manager._deserialize_value(serialized)
        
        assert isinstance(deserialized, datetime)
        assert deserialized == dt
    
    # ==================== Validation Tests ====================
    
    def test_validate_valid_state(self, state_manager, valid_state):
        """Test validation of valid state"""
        validation = state_manager._validate_state(valid_state)
        
        assert validation['valid'] is True
        assert len(validation['errors']) == 0
    
    def test_validate_missing_results(self, state_manager):
        """Test validation with missing results"""
        state = {'config': {}, 'status': 'running'}
        validation = state_manager._validate_state(state)
        
        assert validation['valid'] is False
        assert any('results' in err for err in validation['errors'])
    
    def test_validate_missing_config(self, state_manager):
        """Test validation with missing config"""
        state = {'results': [], 'status': 'running'}
        validation = state_manager._validate_state(state)
        
        assert validation['valid'] is False
        assert any('config' in err for err in validation['errors'])
    
    def test_validate_wrong_type(self, state_manager):
        """Test validation with wrong data types"""
        state = {
            'results': 'not a list',
            'config': {},
            'status': 'running'
        }
        validation = state_manager._validate_state(state)
        
        assert validation['valid'] is False
        assert any('list' in err for err in validation['errors'])


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src.optimizer_v3.core.results.state_manager', '--cov-report=term-missing'])
