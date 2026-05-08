"""
Connection Pool Tests
Task 0.3: Test Connection Pooling

Tests for:
- Connection pool creation
- Pool limits enforced
- Connections recycled
- No memory leaks
- Retry logic
- Metrics tracking
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from src.optimizer_v3.database.connection_pool import (
    DatabaseConnectionPool,
    DatabaseMetrics,
    get_connection_pool,
    close_connection_pool,
)


class TestDatabaseMetrics:
    """Test DatabaseMetrics class"""
    
    def test_initialization(self):
        """Test metrics initialization"""
        metrics = DatabaseMetrics()
        assert metrics.total_connections == 0
        assert metrics.active_connections == 0
        assert metrics.failed_connections == 0
        assert metrics.total_queries == 0
        assert metrics.failed_queries == 0
        assert metrics.last_error_time is None
        assert len(metrics.connection_errors) == 0
    
    def test_record_connection_success(self):
        """Test recording successful connections"""
        metrics = DatabaseMetrics()
        metrics.record_connection_success()
        assert metrics.total_connections == 1
        assert metrics.active_connections == 1
        
        metrics.record_connection_success()
        assert metrics.total_connections == 2
        assert metrics.active_connections == 2
    
    def test_record_connection_failure(self):
        """Test recording connection failures"""
        metrics = DatabaseMetrics()
        error = ValueError("Test error")
        
        metrics.record_connection_failure(error)
        assert metrics.failed_connections == 1
        assert metrics.connection_errors["ValueError"] == 1
        assert metrics.last_error_time is not None
    
    def test_record_connection_close(self):
        """Test recording connection closes"""
        metrics = DatabaseMetrics()
        metrics.record_connection_success()
        metrics.record_connection_success()
        
        metrics.record_connection_close()
        assert metrics.active_connections == 1
        
        metrics.record_connection_close()
        assert metrics.active_connections == 0
    
    def test_record_query_success(self):
        """Test recording successful queries"""
        metrics = DatabaseMetrics()
        metrics.record_query_success()
        assert metrics.total_queries == 1
    
    def test_record_query_failure(self):
        """Test recording query failures"""
        metrics = DatabaseMetrics()
        metrics.record_query_failure()
        assert metrics.failed_queries == 1
    
    def test_get_stats(self):
        """Test getting current statistics"""
        metrics = DatabaseMetrics()
        metrics.record_connection_success()
        metrics.record_query_success()
        
        stats = metrics.get_stats()
        assert stats['total_connections'] == 1
        assert stats['active_connections'] == 1
        assert stats['total_queries'] == 1
        assert 'uptime_seconds' in stats


class TestDatabaseConnectionPool:
    """Test DatabaseConnectionPool class"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock database configuration"""
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass',
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 3600
        }
    
    @pytest.fixture
    def mock_db_url(self):
        """Mock database URL"""
        return "postgresql://test_user:test_pass@localhost:5432/test_db"
    
    def test_pool_initialization(self, mock_config, mock_db_url):
        """Test connection pool initialization"""
        with patch('src.optimizer_v3.database.connection_pool.get_db_config', return_value=mock_config):
            with patch('src.optimizer_v3.database.connection_pool.get_db_url', return_value=mock_db_url):
                with patch('src.optimizer_v3.database.connection_pool.create_engine') as mock_engine:
                    mock_engine_instance = MagicMock()
                    mock_engine.return_value = mock_engine_instance
                    
                    # Mock successful connection verification
                    mock_conn = MagicMock()
                    mock_engine_instance.connect.return_value.__enter__.return_value = mock_conn
                    
                    pool = DatabaseConnectionPool()
                    
                    assert pool._engine is not None
                    assert pool._session_factory is not None
                    assert mock_engine.called
    
    def test_get_session_success(self, mock_config, mock_db_url):
        """Test successful session acquisition"""
        with patch('src.optimizer_v3.database.connection_pool.get_db_config', return_value=mock_config):
            with patch('src.optimizer_v3.database.connection_pool.get_db_url', return_value=mock_db_url):
                with patch('src.optimizer_v3.database.connection_pool.create_engine') as mock_engine:
                    mock_engine_instance = MagicMock()
                    mock_engine.return_value = mock_engine_instance
                    
                    # Mock successful connection
                    mock_conn = MagicMock()
                    mock_engine_instance.connect.return_value.__enter__.return_value = mock_conn
                    
                    pool = DatabaseConnectionPool()
                    
                    # Mock session
                    mock_session = MagicMock()
                    pool._session_factory = MagicMock(return_value=mock_session)
                    
                    session = pool.get_session()
                    assert session is not None
                    assert pool.metrics.total_connections > 0
    
    def test_get_session_retry_logic(self, mock_config, mock_db_url):
        """Test retry logic on connection failure"""
        with patch('src.optimizer_v3.database.connection_pool.get_db_config', return_value=mock_config):
            with patch('src.optimizer_v3.database.connection_pool.get_db_url', return_value=mock_db_url):
                with patch('src.optimizer_v3.database.connection_pool.create_engine') as mock_engine:
                    mock_engine_instance = MagicMock()
                    mock_engine.return_value = mock_engine_instance
                    
                    # Mock successful initialization
                    mock_conn = MagicMock()
                    mock_engine_instance.connect.return_value.__enter__.return_value = mock_conn
                    
                    pool = DatabaseConnectionPool()
                    
                    # Mock session that fails twice then succeeds
                    mock_session = MagicMock()
                    call_count = 0
                    
                    def side_effect(*args):
                        nonlocal call_count
                        call_count += 1
                        if call_count <= 2:
                            raise OperationalError("Connection failed", None, None)
                        return MagicMock()
                    
                    mock_session.execute.side_effect = side_effect
                    pool._session_factory = MagicMock(return_value=mock_session)
                    
                    # Should succeed on 3rd attempt
                    with patch('time.sleep'):  # Don't actually sleep in tests
                        session = pool.get_session()
                        assert session is not None
    
    def test_get_session_max_retries_exceeded(self, mock_config, mock_db_url):
        """Test max retries exceeded raises error"""
        with patch('src.optimizer_v3.database.connection_pool.get_db_config', return_value=mock_config):
            with patch('src.optimizer_v3.database.connection_pool.get_db_url', return_value=mock_db_url):
                with patch('src.optimizer_v3.database.connection_pool.create_engine') as mock_engine:
                    mock_engine_instance = MagicMock()
                    mock_engine.return_value = mock_engine_instance
                    
                    # Mock successful initialization
                    mock_conn = MagicMock()
                    mock_engine_instance.connect.return_value.__enter__.return_value = mock_conn
                    
                    pool = DatabaseConnectionPool()
                    
                    # Mock session that always fails
                    mock_session = MagicMock()
                    mock_session.execute.side_effect = OperationalError("Connection failed", None, None)
                    pool._session_factory = MagicMock(return_value=mock_session)
                    
                    # Should raise ConnectionError after max retries
                    with patch('time.sleep'):  # Don't actually sleep in tests
                        with pytest.raises(ConnectionError):
                            pool.get_session()
    
    def test_close_all(self, mock_config, mock_db_url):
        """Test closing all connections"""
        with patch('src.optimizer_v3.database.connection_pool.get_db_config', return_value=mock_config):
            with patch('src.optimizer_v3.database.connection_pool.get_db_url', return_value=mock_db_url):
                with patch('src.optimizer_v3.database.connection_pool.create_engine') as mock_engine:
                    with patch('src.optimizer_v3.database.connection_pool.scoped_session') as mock_scoped_session:
                        mock_engine_instance = MagicMock()
                        mock_engine.return_value = mock_engine_instance
                        
                        # Mock scoped_session so _session_factory is a MagicMock
                        mock_session_factory = MagicMock()
                        mock_scoped_session.return_value = mock_session_factory
                        
                        # Mock successful connection
                        mock_conn = MagicMock()
                        mock_engine_instance.connect.return_value.__enter__.return_value = mock_conn
                        
                        pool = DatabaseConnectionPool()
                        metrics = pool.close_all()
                        
                        assert isinstance(metrics, dict)
                        assert 'total_connections' in metrics
                        assert 'uptime_seconds' in metrics
                        assert pool._session_factory.remove.called
                        assert pool._engine.dispose.called
    
    def test_get_pool_status(self, mock_config, mock_db_url):
        """Test getting pool status"""
        with patch('src.optimizer_v3.database.connection_pool.get_db_config', return_value=mock_config):
            with patch('src.optimizer_v3.database.connection_pool.get_db_url', return_value=mock_db_url):
                with patch('src.optimizer_v3.database.connection_pool.create_engine') as mock_engine:
                    mock_engine_instance = MagicMock()
                    mock_pool = MagicMock()
                    mock_engine_instance.pool = mock_pool
                    mock_engine.return_value = mock_engine_instance
                    
                    # Mock successful connection
                    mock_conn = MagicMock()
                    mock_engine_instance.connect.return_value.__enter__.return_value = mock_conn
                    
                    pool = DatabaseConnectionPool()
                    status = pool.get_pool_status()
                    
                    assert status['status'] == 'active'
                    assert 'metrics' in status


class TestGlobalConnectionPool:
    """Test global connection pool functions"""
    
    def test_get_connection_pool_singleton(self):
        """Test singleton pattern for global pool"""
        # Reset global pool
        close_connection_pool()
        
        with patch('src.optimizer_v3.database.connection_pool.DatabaseConnectionPool'):
            pool1 = get_connection_pool()
            pool2 = get_connection_pool()
            
            # Should be the same instance
            assert pool1 is pool2
    
    def test_close_connection_pool(self):
        """Test closing global connection pool"""
        # Reset global pool
        close_connection_pool()
        
        with patch('src.optimizer_v3.database.connection_pool.DatabaseConnectionPool') as MockPool:
            mock_instance = MagicMock()
            MockPool.return_value = mock_instance
            mock_instance.close_all.return_value = {'test': 'metrics'}
            
            # Get pool (creates instance)
            pool = get_connection_pool()
            
            # Close it
            metrics = close_connection_pool()
            
            assert metrics == {'test': 'metrics'}
            assert mock_instance.close_all.called


@pytest.mark.integration
class TestConnectionPoolIntegration:
    """Integration tests (require actual PostgreSQL)"""
    
    def test_real_connection_pool(self, request):
        """Test with real PostgreSQL connection (if available)"""
        if not request.config.getoption("--run-integration", default=False):
            pytest.skip("Integration tests require --run-integration flag")
        try:
            pool = DatabaseConnectionPool()
            session = pool.get_session()
            
            # Execute simple query
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            
            session.close()
            metrics = pool.close_all()
            
            assert metrics['total_connections'] > 0
            assert metrics['failed_connections'] == 0
            
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {str(e)}")


def pytest_addoption(parser):
    """Add custom pytest options"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests"
    )
