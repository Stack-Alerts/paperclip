"""
Database Configuration Management
Task 0.2: PostgreSQL Configuration Loading

Loads database configuration from environment variables (.env file) via the
pydantic-settings `DatabaseSettings` class (BTCAAAAA-30576). `.env` is the
single source of truth; pydantic loads it directly, so adding a new POSTGRES_*
to `.env` does NOT require a `start.sh` allowlist amendment.
"""

from typing import Dict, Any

from .settings import get_database_settings


def get_db_config() -> Dict[str, Any]:
    """
    Load database configuration from environment

    Returns:
        Dictionary containing database connection parameters:
        - host: PostgreSQL host address
        - port: PostgreSQL port number
        - database: Database name
        - user: Database user
        - password: Database password
        - ssl: SSL enabled flag
        - ssl_cert_path: Path to SSL certificate
        - ssl_key_path: Path to SSL key
        - pool_size: Connection pool size
        - max_overflow: Maximum overflow connections
        - pool_timeout: Connection timeout in seconds
        - pool_recycle: Connection recycle time in seconds
    """
    s = get_database_settings()
    return {
        'host': s.POSTGRES_HOST,
        'port': s.POSTGRES_PORT,
        'database': s.POSTGRES_DB,
        'user': s.POSTGRES_USER,
        'password': s.POSTGRES_PASSWORD,
        'ssl': s.POSTGRES_SSL,
        'ssl_cert_path': s.POSTGRES_SSL_CERT_PATH,
        'ssl_key_path': s.POSTGRES_SSL_KEY_PATH,
        'pool_size': s.POSTGRES_POOL_SIZE,
        'max_overflow': s.POSTGRES_MAX_OVERFLOW,
        'pool_timeout': s.POSTGRES_POOL_TIMEOUT,
        'pool_recycle': s.POSTGRES_POOL_RECYCLE,
    }


def get_performance_config() -> Dict[str, Any]:
    """
    Load performance configuration from environment

    Returns:
        Dictionary containing PostgreSQL performance settings:
        - shared_buffers: Shared memory buffer size
        - work_mem: Memory for sort operations
        - maintenance_work_mem: Memory for maintenance operations
        - effective_cache_size: Expected OS cache size
        - wal_buffers: Write-ahead log buffers
        - checkpoint_timeout: Checkpoint interval
        - random_page_cost: Random page access cost
        - effective_io_concurrency: Expected concurrent I/O operations
    """
    s = get_database_settings()
    return {
        'shared_buffers': s.POSTGRES_SHARED_BUFFERS,
        'work_mem': s.POSTGRES_WORK_MEM,
        'maintenance_work_mem': s.POSTGRES_MAINTENANCE_WORK_MEM,
        'effective_cache_size': s.POSTGRES_EFFECTIVE_CACHE_SIZE,
        'wal_buffers': s.POSTGRES_WAL_BUFFERS,
        'checkpoint_timeout': s.POSTGRES_CHECKPOINT_TIMEOUT,
        'random_page_cost': s.POSTGRES_RANDOM_PAGE_COST,
        'effective_io_concurrency': s.POSTGRES_EFFECTIVE_IO_CONCURRENCY,
    }


def get_monitoring_config() -> Dict[str, Any]:
    """
    Load monitoring configuration from environment

    Returns:
        Dictionary containing monitoring settings:
        - log_min_duration: Minimum query duration to log (ms)
        - log_connections: Log new connections
        - log_disconnections: Log disconnections
    """
    s = get_database_settings()
    return {
        'log_min_duration': s.POSTGRES_LOG_MIN_DURATION,
        'log_connections': s.POSTGRES_LOG_CONNECTIONS,
        'log_disconnections': s.POSTGRES_LOG_DISCONNECTIONS,
    }


def get_backup_config() -> Dict[str, Any]:
    """
    Load backup configuration from environment

    Returns:
        Dictionary containing backup settings:
        - backup_path: Path to store backups
        - retention_days: Number of days to keep backups
        - compression: Enable backup compression
    """
    s = get_database_settings()
    return {
        'backup_path': s.POSTGRES_BACKUP_PATH,
        'retention_days': s.POSTGRES_BACKUP_RETENTION_DAYS,
        'compression': s.POSTGRES_BACKUP_COMPRESSION,
    }


def get_db_url() -> str:
    """
    Generate PostgreSQL database URL from configuration

    Returns:
        PostgreSQL connection URL string
        Format: postgresql://user:password@host:port/database
    """
    return get_database_settings().database_url()


def validate_config() -> bool:
    """
    Validate that all required configuration is present

    Returns:
        True if configuration is valid, raises ValueError otherwise

    Raises:
        ValueError: If required configuration is missing
    """
    config = get_db_config()

    required_fields = ['host', 'port', 'database', 'user', 'password']
    missing_fields = [field for field in required_fields if not config.get(field)]

    if missing_fields:
        raise ValueError(
            f"Missing required database configuration: {', '.join(missing_fields)}\n"
            f"Please check your .env file and ensure all POSTGRES_* variables are set."
        )

    return True
