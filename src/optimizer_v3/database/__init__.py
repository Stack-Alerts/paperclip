"""
Database Infrastructure for Optimizer V3
Tasks 0.2-0.3: Database Configuration and Connection Pooling
"""

from .config import (
    get_db_config,
    get_performance_config,
    get_monitoring_config,
    get_backup_config,
    get_db_url,
    validate_config,
)

from .connection_pool import (
    DatabaseConnectionPool,
    DatabaseMetrics,
    get_connection_pool,
    close_connection_pool,
)

__all__ = [
    # Configuration
    "get_db_config",
    "get_performance_config",
    "get_monitoring_config",
    "get_backup_config",
    "get_db_url",
    "validate_config",
    # Connection Pool
    "DatabaseConnectionPool",
    "DatabaseMetrics",
    "get_connection_pool",
    "close_connection_pool",
]
