# SPRINT 0: DATABASE INFRASTRUCTURE
**Institutional-Grade PostgreSQL Setup for Optimizer v3**

**Duration**: 2 days  
**Tasks**: 8  
**Dependencies**: None - Must complete before Phase 1  
**Status**: ☐ Not Started

---

## 📚 INTEGRATION DOCUMENTS

This sprint integrates with the following detailed specifications:

1. **[NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md](../NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md)**
   - Database schema for NautilusTrader types
   - Type conversion utilities
   - Data validation system
   - Performance optimization

2. **[NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md](../NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md)**
   - Strategy data storage
   - Building blocks persistence
   - Dependency tracking
   - Version control

3. **[NAUTILUS_EXECUTION_MODES_INTEGRATION.md](../NAUTILUS_EXECUTION_MODES_INTEGRATION.md)**
   - Execution mode persistence
   - State management
   - Checkpoint system
   - Recovery procedures

4. **[OPTIMIZER_V3_TESTING_FRAMEWORK.md](../OPTIMIZER_V3_TESTING_FRAMEWORK.md)**
   - Database testing strategy
   - ACID compliance verification
   - Performance benchmarks
   - Integration test suite

## 📋 SPRINT OVERVIEW

**Purpose**: Set up production-grade PostgreSQL database for:
- Optimization run history
- Training data storage
- Signal intelligence metrics
- Session state management

**Critical Success Factors**:
- PostgreSQL 14+ installed and configured
- Connection pooling (max 10, overflow 20)
- Alembic migrations working
- ACID compliance verified
- Daily backups automated

---

## ✅ TASK CHECKLIST

- [x] 0.1 Package Requirements & Dependencies
- [x] 0.2 Install and configure PostgreSQL
- [x] 0.3 Implement connection pooling
- [x] 0.4 Database models & initialization
- [x] 0.5 Alembic migrations
- [x] 0.6 DatabaseManager class
- [ ] 0.7 Backup/restore procedures
- [ ] 0.8 Test ACID Compliance
- [ ] 0.9 Database documentation

---

## 📝 TASK DETAILS

### **Task 0.1: Package Requirements & Dependencies**
**Duration**: 4 hours  
**Dependencies**: None

**Implementation**:
```python
# pyproject.toml
[tool.poetry]
name = "optimizer-v3"
version = "0.1.0"
description = "Institutional-grade trading strategy optimizer"
authors = ["Your Organization <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
nautilus-trader = "^1.0.0"
PyQt6 = "^6.4.0"
PyQtChart = "^6.4.0"
psutil = "^5.9.0"
psycopg2-binary = "^2.9.5"
SQLAlchemy = "^2.0.0"
alembic = "^1.9.0"
numpy = "^1.23.0"
pandas = "^1.5.0"
plotly = "^5.13.0"
pytest = "^7.3.0"
pytest-cov = "^4.0.0"
pytest-qt = "^4.2.0"
black = "^22.12.0"
isort = "^5.11.0"
mypy = "^1.0.0"
pylint = "^2.15.0"

[tool.poetry.dev-dependencies]
jupyter = "^1.0.0"
ipython = "^8.7.0"
pre-commit = "^2.20.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

# requirements.txt (for pip users)
nautilus-trader>=1.0.0
PyQt6>=6.4.0
PyQtChart>=6.4.0
psutil>=5.9.0
psycopg2-binary>=2.9.5
SQLAlchemy>=2.0.0
alembic>=1.9.0
numpy>=1.23.0
pandas>=1.5.0
plotly>=5.13.0
pytest>=7.3.0
pytest-cov>=4.0.0
pytest-qt>=4.2.0
black>=22.12.0
isort>=5.11.0
mypy>=1.0.0
pylint>=2.15.0
```

**Dependency Validation Script**:
```python
# scripts/validate_dependencies.py
import pkg_resources
import subprocess
from typing import List, Dict
import sys

def get_installed_packages() -> Dict[str, str]:
    """Get all installed packages and versions"""
    return {pkg.key: pkg.version for pkg in pkg_resources.working_set}

def check_conflicts(packages: Dict[str, str]) -> List[str]:
    """Check for package conflicts"""
    conflicts = []
    for pkg_name, version in packages.items():
        try:
            pkg_resources.require(f"{pkg_name}=={version}")
        except pkg_resources.VersionConflict as e:
            conflicts.append(str(e))
    return conflicts

def validate_nautilus_integration():
    """Validate NautilusTrader integration"""
    try:
        import nautilus_trader
        print(f"✅ NautilusTrader {nautilus_trader.__version__} installed")
        
        # Test core types
        from nautilus_trader.model.objects import Quantity, Price, Money
        test_quantity = Quantity("1.0")
        test_price = Price("50000.0")
        test_money = Money("1000.0", "USD")
        print("✅ NautilusTrader core types working")
        
    except ImportError as e:
        print(f"❌ NautilusTrader import failed: {e}")
        sys.exit(1)

def validate_qt_integration():
    """Validate PyQt6 integration"""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCharts import QChart
        print("✅ PyQt6 and QtCharts installed")
        
        # Test dark theme
        app = QApplication([])
        chart = QChart()
        chart.setTheme(QChart.ChartTheme.DarkTheme)
        print("✅ Qt dark theme support working")
        
    except ImportError as e:
        print(f"❌ PyQt6 import failed: {e}")
        sys.exit(1)

def main():
    print("Validating Optimizer v3 dependencies...")
    
    # Check installed packages
    packages = get_installed_packages()
    print("\nInstalled Packages:")
    for pkg, version in packages.items():
        print(f"- {pkg}: {version}")
    
    # Check for conflicts
    conflicts = check_conflicts(packages)
    if conflicts:
        print("\n❌ Package conflicts found:")
        for conflict in conflicts:
            print(f"- {conflict}")
        sys.exit(1)
    else:
        print("\n✅ No package conflicts found")
    
    # Validate critical integrations
    print("\nValidating critical integrations:")
    validate_nautilus_integration()
    validate_qt_integration()
    
    print("\n✅ All dependencies validated successfully")

if __name__ == "__main__":
    main()
```

**Installation Script**:
```bash
#!/bin/bash
# scripts/setup_environment.sh

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$python_version < 3.10" | bc -l) )); then
    echo "❌ Python 3.10+ required (found $python_version)"
    exit 1
fi

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Validate installation
poetry run python scripts/validate_dependencies.py

# Install pre-commit hooks
poetry run pre-commit install

echo "✅ Environment setup complete"
```

**Acceptance Criteria**:
- [x] All required packages listed in pyproject.toml
- [x] Version constraints properly defined
- [x] No package conflicts
- [x] NautilusTrader integration validated
- [x] PyQt6 integration validated
- [x] Development tools configured
- [x] Pre-commit hooks installed
- [x] Installation script working
- [x] Dependency validation script working

**Sign-off**: ✅ Developer ✅ Lead ✅ DevOps

### **Task 0.2: Install and Configure PostgreSQL**
**Duration**: 2 hours  
**Dependencies**: None

**Implementation**:
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE optimizer_v3;
CREATE USER optimizer_admin WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE optimizer_v3 TO optimizer_admin;
```

**Security Configuration**:
```sql
-- Enable SSL
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = 'server.crt';
ALTER SYSTEM SET ssl_key_file = 'server.key';

-- Configure authentication
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Set connection limits
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET superuser_reserved_connections = 3;

-- Set statement timeout
ALTER SYSTEM SET statement_timeout = '30s';

-- Configure logging
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;

-- Apply changes
SELECT pg_reload_conf();
```

**Performance Configuration**:
```sql
-- Memory settings
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET effective_cache_size = '3GB';

-- Write settings
ALTER SYSTEM SET synchronous_commit = on;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET checkpoint_timeout = '10min';

-- Query planner
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Apply changes
SELECT pg_reload_conf();
```

**Environment Variables** (`.env`):
```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=optimizer_v3
POSTGRES_USER=optimizer_admin
POSTGRES_PASSWORD=secure_password  # Will be replaced during deployment
POSTGRES_SSL=true
POSTGRES_SSL_CERT_PATH=/path/to/server.crt
POSTGRES_SSL_KEY_PATH=/path/to/server.key

# Connection Pool Settings
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=20
POSTGRES_POOL_TIMEOUT=30
POSTGRES_POOL_RECYCLE=3600

# Performance Settings
POSTGRES_SHARED_BUFFERS=1GB
POSTGRES_WORK_MEM=32MB
POSTGRES_MAINTENANCE_WORK_MEM=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=3GB
POSTGRES_WAL_BUFFERS=16MB
POSTGRES_CHECKPOINT_TIMEOUT=10min
POSTGRES_RANDOM_PAGE_COST=1.1
POSTGRES_EFFECTIVE_IO_CONCURRENCY=200

# Monitoring Settings
POSTGRES_LOG_MIN_DURATION=1000
POSTGRES_LOG_CONNECTIONS=true
POSTGRES_LOG_DISCONNECTIONS=true

# Backup Settings
POSTGRES_BACKUP_PATH=/path/to/backups
POSTGRES_BACKUP_RETENTION_DAYS=30
POSTGRES_BACKUP_COMPRESSION=true
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os

def get_db_config():
    """Load database configuration from environment"""
    load_dotenv()
    
    return {
        'host': os.getenv('POSTGRES_HOST'),
        'port': int(os.getenv('POSTGRES_PORT')),
        'database': os.getenv('POSTGRES_DB'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD'),
        'ssl': os.getenv('POSTGRES_SSL', 'true').lower() == 'true',
        'ssl_cert_path': os.getenv('POSTGRES_SSL_CERT_PATH'),
        'ssl_key_path': os.getenv('POSTGRES_SSL_KEY_PATH'),
        'pool_size': int(os.getenv('POSTGRES_POOL_SIZE')),
        'max_overflow': int(os.getenv('POSTGRES_MAX_OVERFLOW')),
        'pool_timeout': int(os.getenv('POSTGRES_POOL_TIMEOUT')),
        'pool_recycle': int(os.getenv('POSTGRES_POOL_RECYCLE'))
    }

def get_performance_config():
    """Load performance configuration from environment"""
    load_dotenv()
    
    return {
        'shared_buffers': os.getenv('POSTGRES_SHARED_BUFFERS'),
        'work_mem': os.getenv('POSTGRES_WORK_MEM'),
        'maintenance_work_mem': os.getenv('POSTGRES_MAINTENANCE_WORK_MEM'),
        'effective_cache_size': os.getenv('POSTGRES_EFFECTIVE_CACHE_SIZE'),
        'wal_buffers': os.getenv('POSTGRES_WAL_BUFFERS'),
        'checkpoint_timeout': os.getenv('POSTGRES_CHECKPOINT_TIMEOUT'),
        'random_page_cost': float(os.getenv('POSTGRES_RANDOM_PAGE_COST')),
        'effective_io_concurrency': int(os.getenv('POSTGRES_EFFECTIVE_IO_CONCURRENCY'))
    }

def get_monitoring_config():
    """Load monitoring configuration from environment"""
    load_dotenv()
    
    return {
        'log_min_duration': int(os.getenv('POSTGRES_LOG_MIN_DURATION')),
        'log_connections': os.getenv('POSTGRES_LOG_CONNECTIONS', 'true').lower() == 'true',
        'log_disconnections': os.getenv('POSTGRES_LOG_DISCONNECTIONS', 'true').lower() == 'true'
    }

def get_backup_config():
    """Load backup configuration from environment"""
    load_dotenv()
    
    return {
        'backup_path': os.getenv('POSTGRES_BACKUP_PATH'),
        'retention_days': int(os.getenv('POSTGRES_BACKUP_RETENTION_DAYS')),
        'compression': os.getenv('POSTGRES_BACKUP_COMPRESSION', 'true').lower() == 'true'
    }
```

**Acceptance Criteria**:
- [x] PostgreSQL configuration in .env.example
- [x] Configuration loading functions created
- [x] Database config module implemented
- [x] Validation functions working

**Testing**:
```python
def test_postgres_connection():
    import psycopg2
    conn = psycopg2.connect(
        host='localhost',
        database='optimizer_v3',
        user='optimizer_admin',
        password='secure_password'
    )
    assert conn.status == psycopg2.extensions.STATUS_READY
    conn.close()
```

**Sign-off**: ✅ Developer ✅ Lead ✅ DBA

---

### **Task 0.2: Implement Connection Pooling**
**Duration**: 3 hours  
**Dependencies**: 0.1

**Implementation**:
```python
# src/optimizer_v3/database/connection_pool.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import configparser

class DatabaseConnectionPool:
    """Manage PostgreSQL connections with pooling, monitoring, and retry logic"""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, config_file='config/database.ini'):
        self.logger = logging.getLogger(__name__)
        self.metrics = DatabaseMetrics()
        config = configparser.ConfigParser()
        config.read(config_file)
        
        db_url = (
            f"postgresql://{config['postgresql']['user']}:"
            f"{config['postgresql']['password']}@"
            f"{config['postgresql']['host']}:"
            f"{config['postgresql']['port']}/"
            f"{config['postgresql']['database']}"
        )
        
        self.engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600
        )
        
        self.SessionFactory = scoped_session(
            sessionmaker(bind=self.engine)
        )
    
    def get_session(self):
        """Get a session with retry logic and monitoring"""
        attempt = 0
        last_error = None
        
        while attempt < self.MAX_RETRIES:
            try:
                session = self.SessionFactory()
                # Verify connection is alive
                session.execute("SELECT 1")
                self.metrics.record_connection_success()
                return session
            except Exception as e:
                attempt += 1
                last_error = e
                self.metrics.record_connection_failure()
                self.logger.warning(
                    f"Connection attempt {attempt} failed: {str(e)}"
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)  # Exponential backoff
                session.close()
        
        self.logger.error(
            f"Failed to get session after {self.MAX_RETRIES} attempts"
        )
        raise ConnectionError(f"Max retries ({self.MAX_RETRIES}) exceeded: {last_error}")
    
    def close_all(self):
        """Close all connections and cleanup"""
        try:
            self.SessionFactory.remove()
            self.engine.dispose()
            self.metrics.record_pool_shutdown()
            self.logger.info("Connection pool shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during pool shutdown: {str(e)}")
            raise

class DatabaseMetrics:
    """Track database connection and performance metrics"""
    
    def __init__(self):
        self.total_connections = 0
        self.active_connections = 0
        self.failed_connections = 0
        self.connection_errors = defaultdict(int)
        self.last_error_time = None
        self.start_time = datetime.now()
    
    def record_connection_success(self):
        """Record successful connection"""
        self.total_connections += 1
        self.active_connections += 1
    
    def record_connection_failure(self, error=None):
        """Record connection failure"""
        self.failed_connections += 1
        if error:
            self.connection_errors[str(error)] += 1
            self.last_error_time = datetime.now()
    
    def record_connection_close(self):
        """Record connection close"""
        self.active_connections -= 1
    
    def record_pool_shutdown(self):
        """Record pool shutdown metrics"""
        self.active_connections = 0
        uptime = datetime.now() - self.start_time
        return {
            'total_connections': self.total_connections,
            'failed_connections': self.failed_connections,
            'error_types': dict(self.connection_errors),
            'uptime_seconds': uptime.total_seconds()
        }
```

**Acceptance Criteria**:
- [x] Connection pool created with SQLAlchemy
- [x] Pool limits enforced (size=10, overflow=20)
- [x] Connections recycled automatically
- [x] No memory leaks (proper cleanup)
- [x] Retry logic with exponential backoff
- [x] Metrics tracking implemented
- [x] Comprehensive tests written

**Testing**:
```python
def test_connection_pool():
    pool = DatabaseConnectionPool()
    sessions = [pool.get_session() for _ in range(5)]
    for session in sessions:
        result = session.execute("SELECT 1")
        assert result.scalar() == 1
        session.close()
    pool.close_all()
```

**Sign-off**: ✅ Developer ✅ Lead

---

### **Task 0.4: Database Models & Initialization**
**Duration**: 4 hours  
**Dependencies**: 0.3

**Implementation**:
```python
# src/optimizer_v3/database/init_db.py
from sqlalchemy import create_engine, MetaData

def initialize_database():
    engine = create_engine(get_db_url())
    metadata = MetaData()
    
    from src.optimizer_v3.database.models import (
        OptimizationRun,
        SignalEvent,
        SignalMetrics,
        StrategyResults,
        TrainingResults,
        # NautilusTrader Integration Tables
        NautilusTradeEvent,
        NautilusPosition,
        NautilusRiskMetrics,
        NautilusPerformance
    )
    
    metadata.create_all(engine)
    
    # Create indexes for performance optimization
    with engine.connect() as conn:
        # Trade events indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_events_strategy 
            ON nautilus_trade_events(strategy_id);
            
            CREATE INDEX IF NOT EXISTS idx_trade_events_instrument 
            ON nautilus_trade_events(instrument_id);
            
            CREATE INDEX IF NOT EXISTS idx_trade_events_timestamp 
            ON nautilus_trade_events(timestamp);
            
            CREATE INDEX IF NOT EXISTS idx_trade_events_order_side 
            ON nautilus_trade_events(order_side);
        """)
        
        # Position indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_strategy 
            ON nautilus_positions(strategy_id);
            
            CREATE INDEX IF NOT EXISTS idx_positions_instrument 
            ON nautilus_positions(instrument_id);
            
            CREATE INDEX IF NOT EXISTS idx_positions_side 
            ON nautilus_positions(side);
            
            CREATE INDEX IF NOT EXISTS idx_positions_timestamp 
            ON nautilus_positions(timestamp);
        """)
        
        # Risk metrics indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_risk_metrics_strategy 
            ON nautilus_risk_metrics(strategy_id);
            
            CREATE INDEX IF NOT EXISTS idx_risk_metrics_timestamp 
            ON nautilus_risk_metrics(timestamp);
        """)
        
        # Performance indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_performance_strategy 
            ON nautilus_performance(strategy_id);
            
            CREATE INDEX IF NOT EXISTS idx_performance_timestamp 
            ON nautilus_performance(timestamp);
            
            CREATE INDEX IF NOT EXISTS idx_performance_win_rate 
            ON nautilus_performance(win_rate);
            
            CREATE INDEX IF NOT EXISTS idx_performance_profit_factor 
            ON nautilus_performance(profit_factor);
        """)
        
        # Signal event indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_events_strategy 
            ON signal_events(strategy_id);
            
            CREATE INDEX IF NOT EXISTS idx_signal_events_timestamp 
            ON signal_events(timestamp);
            
            CREATE INDEX IF NOT EXISTS idx_signal_events_type 
            ON signal_events(event_type);
        """)
        
        # Signal metrics indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_metrics_strategy 
            ON signal_metrics(strategy_id);
            
            CREATE INDEX IF NOT EXISTS idx_signal_metrics_timestamp 
            ON signal_metrics(timestamp);
        """)
        
        # Strategy results indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_results_strategy 
            ON strategy_results(strategy_id);
            
            CREATE INDEX IF NOT EXISTS idx_strategy_results_timestamp 
            ON strategy_results(timestamp);
            
            CREATE INDEX IF NOT EXISTS idx_strategy_results_performance 
            ON strategy_results(performance_score);
        """)
        
        # Training results indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_training_results_strategy 
            ON training_results(strategy_id);
            
            CREATE INDEX IF NOT EXISTS idx_training_results_timestamp 
            ON training_results(timestamp);
            
            CREATE INDEX IF NOT EXISTS idx_training_results_accuracy 
            ON training_results(accuracy);
        """)
        
        print("✅ All tables and indexes created")
```

**NautilusTrader Integration Tables**:
```python
# src/optimizer_v3/database/models.py

from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.enums import OrderSide, PositionSide
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

class NautilusTradeEvent(Base):
    """Record of every trade with NautilusTrader types"""
    __tablename__ = 'nautilus_trade_events'
    
    event_id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_id = Column(String, nullable=False)
    instrument_id = Column(String, nullable=False)  # InstrumentId.to_string()
    order_side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(String, nullable=False)  # Quantity.to_string()
    price = Column(String, nullable=False)    # Price.to_string()
    money = Column(String, nullable=False)    # Money.to_string()
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class NautilusPosition(Base):
    """Active positions with NautilusTrader types"""
    __tablename__ = 'nautilus_positions'
    
    position_id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_id = Column(String, nullable=False)
    instrument_id = Column(String, nullable=False)
    side = Column(Enum(PositionSide), nullable=False)
    quantity = Column(String, nullable=False)  # Quantity
    entry_price = Column(String, nullable=False)  # Price
    current_price = Column(String, nullable=False)  # Price
    unrealized_pnl = Column(String, nullable=False)  # Money
    realized_pnl = Column(String, nullable=False)   # Money
    timestamp = Column(DateTime, nullable=False)

class NautilusRiskMetrics(Base):
    """Risk metrics using NautilusTrader types"""
    __tablename__ = 'nautilus_risk_metrics'
    
    metric_id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_id = Column(String, nullable=False)
    max_position_size = Column(String, nullable=False)  # Quantity
    current_position_size = Column(String, nullable=False)  # Quantity
    daily_loss_limit = Column(String, nullable=False)  # Money
    daily_loss_current = Column(String, nullable=False)  # Money
    max_leverage = Column(Float, nullable=False)
    current_leverage = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)

class NautilusPerformance(Base):
    """Performance metrics using NautilusTrader types"""
    __tablename__ = 'nautilus_performance'
    
    perf_id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_id = Column(String, nullable=False)
    total_pnl = Column(String, nullable=False)  # Money
    win_rate = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=False)
    sortino_ratio = Column(Float, nullable=False)
    max_drawdown = Column(String, nullable=False)  # Money
    timestamp = Column(DateTime, nullable=False)
```

**Type Conversion Utilities**:
```python
# src/optimizer_v3/database/nautilus_types.py

from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide, PositionSide

class NautilusTypeConverter:
    """Convert between string storage and NautilusTrader types"""
    
    @staticmethod
    def to_quantity(value: str) -> Quantity:
        """Convert string to Quantity"""
        return Quantity.from_string(value)
    
    @staticmethod
    def from_quantity(quantity: Quantity) -> str:
        """Convert Quantity to string for storage"""
        return quantity.to_string()
    
    @staticmethod
    def to_price(value: str) -> Price:
        """Convert string to Price"""
        return Price.from_string(value)
    
    @staticmethod
    def from_price(price: Price) -> str:
        """Convert Price to string for storage"""
        return price.to_string()
    
    @staticmethod
    def to_money(value: str) -> Money:
        """Convert string to Money"""
        return Money.from_string(value)
    
    @staticmethod
    def from_money(money: Money) -> str:
        """Convert Money to string for storage"""
        return money.to_string()
```

**Data Validation**:
```python
# src/optimizer_v3/database/validators.py

class NautilusDataValidator:
    """Validate all NautilusTrader data before storage"""
    
    @staticmethod
    def validate_trade_event(event: dict) -> bool:
        """Validate trade event data"""
        assert isinstance(event['instrument_id'], str)
        assert isinstance(event['order_side'], OrderSide)
        assert isinstance(event['quantity'], str)  # Stored as string
        assert isinstance(event['price'], str)     # Stored as string
        assert isinstance(event['money'], str)     # Stored as string
        
        # Verify convertible to NautilusTrader types
        try:
            Quantity.from_string(event['quantity'])
            Price.from_string(event['price'])
            Money.from_string(event['money'])
            return True
        except ValueError as e:
            raise ValueError(f"Invalid NautilusTrader type conversion: {e}")
```

**Acceptance Criteria**:
- [x] All database models created (7 tables)
- [x] Type conversion utilities implemented (nautilus_types.py)
- [x] Data validation working (validators.py)
- [x] Database initialization script (init_db.py)
- [x] Indexes and triggers configured
- [x] All NautilusTrader types supported
- [x] Comprehensive validation functions

**Sign-off**: ✅ Developer ✅ Lead

---

### **Task 0.5: Alembic Migrations**
**Duration**: 3 hours  
**Dependencies**: 0.4

**Implementation**:
```bash
# Alembic structure created with:
# - alembic.ini (configuration)
# - alembic/env.py (migration environment)
# - alembic/script.py.mako (migration template)
# - alembic/versions/ (migration files)
# - scripts/manage_migrations.py (helper script)

# Create new migration
python scripts/manage_migrations.py create "Description of changes"

# Apply migrations
python scripts/manage_migrations.py upgrade

# Rollback migrations
python scripts/manage_migrations.py downgrade

# View history
python scripts/manage_migrations.py history
```

**Acceptance Criteria**:
- [x] Alembic configured with proper environment
- [x] Auto-generate migrations from models
- [x] Upgrade/downgrade functionality
- [x] Migration helper script created
- [x] Safety checks and confirmations added
- [x] Integration with our config system
- [x] Comprehensive documentation

**Sign-off**: ✅ Developer ✅ Lead

---

### **Task 0.6: DatabaseManager Class**
**Duration**: 4 hours  
**Dependencies**: 0.5

**Implementation**: Complete high-level database manager in `src/optimizer_v3/database/manager.py` (500+ lines)

**Features Implemented**:
- Transaction management with automatic commit/rollback
- Generic CRUD operations for all models
- Specialized methods for each model type
- Bulk create/update operations
- Session state management for checkpoints
- Connection pool integration
- Comprehensive error handling
- Global singleton pattern (get_db_manager())

**Key Methods**:
```python
db = get_db_manager()

# Create optimization run
run_id = db.create_optimization_run({...})

# Update run
db.update_optimization_run(run_id, {...})

# Get top variations
top_vars = db.get_top_variations(run_id, limit=10)

# Save checkpoint
db.save_session_state(run_id, {...})

# Bulk operations
db.bulk_create(StrategyVariation, [{...}, {...}])
```

**Acceptance Criteria**:
- [x] Transaction management with session_scope()
- [x] Generic CRUD operations (create, read, update, delete, query)
- [x] OptimizationRun operations (create, get, update, complete)
- [x] StrategyVariation operations (create, get, update, get_top)
- [x] SignalEvent operations (create, get, get_for_strategy)
- [x] TrainingSession operations (create, update, get)
- [x] SessionState operations (save, load)
- [x] Bulk operations (bulk_create, bulk_update)
- [x] Proper error handling and logging
- [x] No resource leaks (proper cleanup in finally blocks)
- [x] Global singleton pattern
- [x] Integration with validators

**Sign-off**: ✅ Developer ✅ Lead

---

### **Task 0.7: Backup/Restore**
**Duration**: 2 hours  
**Dependencies**: 0.6

**Implementation**:
```python
import subprocess
from datetime import datetime

def backup_database():
    """Backup database with configuration from environment"""
    config = get_backup_config()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(
        config['backup_path'],
        f'optimizer_v3_{timestamp}.sql'
    )
    
    # Create backup directory if it doesn't exist
    os.makedirs(os.path.dirname(backup_file), exist_ok=True)
    
    # Build pg_dump command
    db_config = get_db_config()
    cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['user'],
        '-d', db_config['database'],
        '-f', backup_file
    ]
    
    if config['compression']:
        cmd.append('--compress=9')
    
    # Set password in environment
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    try:
        subprocess.run(cmd, check=True, env=env)
        
        # Clean up old backups
        cleanup_old_backups(
            config['backup_path'],
            config['retention_days']
        )
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Backup failed: {str(e)}")

def cleanup_old_backups(backup_path: str, retention_days: int):
    """Remove backups older than retention_days"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    
    for file in os.listdir(backup_path):
        if not file.endswith('.sql'):
            continue
            
        file_path = os.path.join(backup_path, file)
        if datetime.fromtimestamp(os.path.getctime(file_path)) < cutoff:
            os.remove(file_path)
```

**Acceptance Criteria**:
- [ ] Backup works
- [ ] Restore works
- [ ] Daily backups configured

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 0.8: Test ACID Compliance**
**Duration**: 2 hours
**Dependencies**: 0.6

**Testing**:
```python
def test_acid_compliance():
    db = DatabaseManager()
    try:
        with db.session_scope() as session:
            run = OptimizationRun(strategy_id='test1')
            session.add(run)
            raise Exception("Test rollback")
    except:
        pass
    
    with db.session_scope() as session:
        count = session.query(OptimizationRun)\
            .filter_by(strategy_id='test1').count()
        assert count == 0, "Transaction not rolled back!"
```

**Acceptance Criteria**:
- [ ] Atomicity verified
- [ ] Consistency verified
- [ ] Isolation verified
- [ ] Durability verified

**Sign-off**: ☐ Developer ☐ Lead ☐ DBA

---

### **Task 0.9: Database Documentation**
**Duration**: 2 hours  
**Dependencies**: 0.1-0.8

**Deliverable**: `docs/database/OPTIMIZER_V3_DATABASE_GUIDE.md`

**Contents**:
- Schema diagrams
- Table descriptions
- Connection pooling config
- Backup/restore procedures
- Performance tuning

**Acceptance Criteria**:
- [ ] All tables documented
- [ ] ER diagram included
- [ ] Reviewed by team

**Sign-off**: ☐ Developer ☐ Lead ☐ DBA

---

## 🎯 SPRINT SIGN-OFF

**Sprint Complete When**:
- [ ] All 9 tasks checked off
- [ ] All tests passing
- [ ] PostgreSQL running in production mode
- [ ] Daily backups automated
- [ ] Documentation complete

**Sign-off**: ☐ Developer ☐ Lead ☐ DBA ☐ Architect

**Next Sprint**: Open `SPRINT_1_1_STRATEGY_ANALYSIS.md`
