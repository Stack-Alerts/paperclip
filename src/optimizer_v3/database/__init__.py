"""
Database Infrastructure for Optimizer V3
Tasks 0.2-0.4: Database Configuration, Connection Pooling, Models & Validation
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

from .models import (
    Base,
    OptimizationRun,
    StrategyVariation,
    SignalEvent,
    SignalMetrics,
    TrainingSession,
    SessionState,
    BacktestResult,
)

from .init_db import (
    initialize_database,
    verify_schema,
    get_schema_info,
)

from .nautilus_types import (
    NautilusTypeConverter,
    to_quantity,
    from_quantity,
    to_price,
    from_price,
    to_money,
    from_money,
    to_instrument_id,
    from_instrument_id,
)

from .validators import (
    NautilusDataValidator,
    ValidationError,
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
    # Models
    "Base",
    "OptimizationRun",
    "StrategyVariation",
    "SignalEvent",
    "SignalMetrics",
    "TrainingSession",
    "SessionState",
    "BacktestResult",
    # Database Initialization
    "initialize_database",
    "verify_schema",
    "get_schema_info",
    # Type Converters
    "NautilusTypeConverter",
    "to_quantity",
    "from_quantity",
    "to_price",
    "from_price",
    "to_money",
    "from_money",
    "to_instrument_id",
    "from_instrument_id",
    # Validators
    "NautilusDataValidator",
    "ValidationError",
]
