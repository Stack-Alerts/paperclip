# OPTIMIZER V3 DATABASE GUIDE
**Institutional-Grade PostgreSQL Database Infrastructure**

**Version**: 1.1.0  
**Date**: 2026-01-20  
**Status**: ✅ Production Ready

---

## 📋 TABLE OF CONTENTS

1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [Tables Documentation](#tables-documentation)
4. [Connection Management](#connection-management)
5. [Transaction Management](#transaction-management)
6. [NautilusTrader Integration](#nautilustrader-integration)
7. [Backup & Restore](#backup--restore)
8. [Performance Tuning](#performance-tuning)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## OVERVIEW

The Optimizer V3 database provides institutional-grade data persistence for:
- Optimization run history and state management
- Strategy variation tracking and ranking
- Signal intelligence event recording
- Training session management
- Backtest results storage

### Key Features
- **ACID Compliance**: Verified with 15 comprehensive tests
- **Connection Pooling**: 10 base connections, 20 overflow, automatic retry
- **Type Safety**: Full NautilusTrader type integration (Price, Quantity, Money)
- **Migration System**: Alembic-based schema versioning
- **Backup System**: Automated pg_dump with retention policies
- **High Performance**: 20+ indexes, optimized queries, connection recycling

---

## DATABASE SCHEMA

### Entity Relationship Diagram

```
┌─────────────────────────────┐
│    OptimizationRun         │
│  (Primary: run_id UUID)    │
├─────────────────────────────┤
│ strategy_id                 │
│ strategy_name               │
│ status                      │
│ start_time                  │
│ end_time                    │
│ total_variations            │
│ completed_variations        │
│ strategy_config (JSONB)     │
│ backtest_config (JSONB)     │
│ optimization_params (JSONB) │
│ created_at                  │
│ updated_at                  │
└───────────┬─────────────────┘
            │
            │ 1:N
            ▼
┌─────────────────────────────┐
│   StrategyVariation        │
│  (Primary: variation_id)   │
├─────────────────────────────┤
│ run_id (FK)                 │◄────────┐
│ variation_id                │         │
│ parameters (JSONB)          │         │
│ status                      │         │
│ ranking_score               │         │
│ performance_metrics (JSONB) │         │
│ created_at                  │         │
│ updated_at                  │         │
└─────────────────────────────┘         │
                                        │
┌─────────────────────────────┐         │
│      SignalEvent           │         │
│   (Primary: event_id)      │         │
├─────────────────────────────┤         │
│ run_id (FK)                 │─────────┤
│ variation_id (FK)           │─────────┘
│ event_type                  │
│ signal_name                 │
│ timestamp                   │
│ metadata (JSONB)            │
│ created_at                  │
└─────────────────────────────┘

┌─────────────────────────────┐
│     SignalMetrics          │
│   (Primary: metric_id)     │
├─────────────────────────────┤
│ run_id (FK)                 │◄────────┐
│ signal_name                 │         │
│ total_occurrences           │         │
│ win_rate                    │         │
│ avg_profit                  │         │
│ aggregated_data (JSONB)     │         │
│ timestamp                   │         │
│ created_at                  │         │
└─────────────────────────────┘         │
                                        │
┌─────────────────────────────┐         │
│    TrainingSession         │         │
│   (Primary: session_id)    │         │
├─────────────────────────────┤         │
│ run_id (FK)                 │─────────┤
│ variation_id (FK)           │─────────┘
│ model_type                  │
│ training_params (JSONB)     │
│ features_used (JSONB)       │
│ performance_metrics (JSONB) │
│ model_artifacts_path        │
│ status                      │
│ created_at                  │
│ updated_at                  │
└─────────────────────────────┘

┌─────────────────────────────┐
│      SessionState          │
│   (Primary: state_id)      │
├─────────────────────────────┤
│ run_id (FK, UNIQUE)         │
│ current_variation_index     │
│ checkpoint_data (JSONB)     │
│ last_checkpoint_at          │
│ created_at                  │
│ updated_at                  │
└─────────────────────────────┘

┌─────────────────────────────┐
│     BacktestResult         │
│   (Primary: result_id)     │
├─────────────────────────────┤
│ run_id (FK)                 │
│ variation_id (FK)           │
│ metrics (JSONB)             │
│ trades (JSONB)              │
│ equity_curve (JSONB)        │
│ created_at                  │
└─────────────────────────────┘
```

---

## TABLES DOCUMENTATION

### 1. OptimizationRun

**Purpose**: Track complete optimization runs with all configuration and metrics

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| run_id | UUID | NO | Primary key, auto-generated |
| strategy_id | VARCHAR | NO | Unique strategy identifier |
| strategy_name | VARCHAR | NO | Human-readable strategy name |
| status | VARCHAR | NO | 'pending', 'running', 'completed', 'failed' |
| start_time | TIMESTAMP | NO | When optimization started |
| end_time | TIMESTAMP | YES | When optimization completed/failed |
| total_variations | INTEGER | YES | Total parameter combinations to test |
| completed_variations | INTEGER | YES | Number of variations completed |
| strategy_config | JSONB | YES | Strategy configuration parameters |
| backtest_config | JSONB | YES | Backtest configuration |
| optimization_params | JSONB | YES | Parameter ranges for optimization |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | NO | Last update timestamp (auto-updated) |

**Indexes**:
- PRIMARY KEY on run_id
- INDEX on strategy_id
- INDEX on status
- INDEX on created_at

**Triggers**:
- Auto-update `updated_at` on row modification

**Usage Example**:
```python
from src.optimizer_v3.database import get_db_manager

db = get_db_manager()

# Create new run
run_id = db.create_optimization_run({
    'strategy_id': 'hod_rejection_v1',
    'strategy_name': 'HOD Rejection Strategy',
    'status': 'pending',
    'strategy_config': {...},
    'backtest_config': {...},
    'optimization_params': {...}
})

# Update run status
db.update_optimization_run(run_id, {
    'status': 'completed',
    'total_variations': 1000,
    'completed_variations': 1000
})

# Query runs
runs = db.get_optimization_runs(status='completed')
```

---

### 2. StrategyVariation

**Purpose**: Store individual parameter combinations and their performance

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| variation_id | UUID | NO | Primary key, auto-generated |
| run_id | UUID | NO | Foreign key to OptimizationRun |
| parameters | JSONB | NO | Parameter values for this variation |
| status | VARCHAR | NO | 'pending', 'running', 'completed', 'failed' |
| ranking_score | FLOAT | YES | Calculated ranking score (auto-updated) |
| performance_metrics | JSONB | YES | All backtest metrics |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | NO | Last update timestamp |

**Indexes**:
- PRIMARY KEY on variation_id
- INDEX on run_id
- INDEX on status
- INDEX on ranking_score (DESC) for top-N queries

**Foreign Keys**:
- run_id REFERENCES OptimizationRun(run_id) ON DELETE CASCADE

**Triggers**:
- Auto-calculate `ranking_score` from performance_metrics
- Auto-update `updated_at` on row modification

**Usage Example**:
```python
# Create variation
var_id = db.create_strategy_variation({
    'run_id': run_id,
    'parameters': {'sma_period': 20, 'rsi_threshold': 70},
    'status': 'pending'
})

# Update with results
db.update_strategy_variation(var_id, {
    'status': 'completed',
    'performance_metrics': {
        'total_pnl': 5000.0,
        'sharpe_ratio': 1.8,
        'max_drawdown': -500.0,
        'win_rate': 0.65
    }
})

# Get top 10 variations
top_vars = db.get_top_variations(run_id, limit=10)
```

---

### 3. SignalEvent

**Purpose**: Record every signal event for intelligence gathering

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| event_id | UUID | NO | Primary key, auto-generated |
| run_id | UUID | NO | Foreign key to OptimizationRun |
| variation_id | UUID | YES | Foreign key to StrategyVariation |
| event_type | VARCHAR | NO | 'signal_generated', 'signal_traded', etc. |
| signal_name | VARCHAR | NO | Name of the signal block |
| timestamp | TIMESTAMP | NO | When event occurred |
| metadata | JSONB | YES | Additional event data |
| created_at | TIMESTAMP | NO | Record creation timestamp |

**Indexes**:
- PRIMARY KEY on event_id
- INDEX on run_id, variation_id
- INDEX on signal_name
- INDEX on timestamp
- INDEX on event_type

**Foreign Keys**:
- run_id REFERENCES OptimizationRun(run_id) ON DELETE CASCADE
- variation_id REFERENCES StrategyVariation(variation_id) ON DELETE CASCADE

**Usage Example**:
```python
# Record signal event
event_id = db.create_signal_event({
    'run_id': run_id,
    'variation_id': var_id,
    'event_type': 'signal_generated',
    'signal_name': 'HOD_Rejection',
    'timestamp': datetime.utcnow(),
    'metadata': {
        'price': 45000.0,
        'volume': 1000,
        'confidence': 0.85
    }
})

# Query events for strategy
events = db.get_signal_events_for_strategy(run_id)
```

---

### 4. SignalMetrics

**Purpose**: Aggregated performance metrics per signal type

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| metric_id | UUID | NO | Primary key, auto-generated |
| run_id | UUID | NO | Foreign key to OptimizationRun |
| signal_name | VARCHAR | NO | Signal block name |
| total_occurrences | INTEGER | NO | Total times signal occurred |
| win_rate | FLOAT | YES | Win rate for this signal |
| avg_profit | FLOAT | YES | Average profit per occurrence |
| aggregated_data | JSONB | YES | Additional aggregated metrics |
| timestamp | TIMESTAMP | NO | When metrics were calculated |
| created_at | TIMESTAMP | NO | Record creation timestamp |

**Indexes**:
- PRIMARY KEY on metric_id
- INDEX on run_id
- INDEX on signal_name
- INDEX on win_rate (DESC)

**Usage Example**:
```python
# Create signal metrics
metrics = {
    'run_id': run_id,
    'signal_name': 'HOD_Rejection',
    'total_occurrences': 50,
    'win_rate': 0.68,
    'avg_profit': 120.50,
    'aggregated_data': {...}
}
```

---

### 5. TrainingSession

**Purpose**: Track ML training sessions and model artifacts

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| session_id | UUID | NO | Primary key, auto-generated |
| run_id | UUID | NO | Foreign key to OptimizationRun |
| variation_id | UUID | YES | Foreign key to StrategyVariation |
| model_type | VARCHAR | NO | 'XGBoost', 'RandomForest', etc. |
| training_params | JSONB | NO | Model hyperparameters |
| features_used | JSONB | NO | Feature list used for training |
| performance_metrics | JSONB | YES | Training/validation metrics |
| model_artifacts_path | VARCHAR | YES | Path to saved model files |
| status | VARCHAR | NO | 'training', 'completed', 'failed' |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | NO | Last update timestamp |

**Indexes**:
- PRIMARY KEY on session_id
- INDEX on run_id
- INDEX on model_type
- INDEX on status

**Usage Example**:
```python
# Create training session
session_id = db.create_training_session({
    'run_id': run_id,
    'model_type': 'XGBoost',
    'training_params': {...},
    'features_used': [...],
    'status': 'training'
})

# Update with results
db.update_training_session(session_id, {
    'status': 'completed',
    'performance_metrics': {...},
    'model_artifacts_path': '/models/xgb_v1.pkl'
})
```

---

### 6. SessionState

**Purpose**: Enable checkpoint/resume functionality for long-running optimizations

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| state_id | UUID | NO | Primary key, auto-generated |
| run_id | UUID | NO | Foreign key to OptimizationRun (UNIQUE) |
| current_variation_index | INTEGER | NO | Last completed variation index |
| checkpoint_data | JSONB | YES | Additional state data |
| last_checkpoint_at | TIMESTAMP | NO | When checkpoint was saved |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | NO | Last update timestamp |

**Constraints**:
- UNIQUE constraint on run_id (one state per run)

**Usage Example**:
```python
# Save checkpoint
db.save_session_state(run_id, {
    'current_variation_index': 500,
    'checkpoint_data': {
        'progress': 0.5,
        'elapsed_time': 3600
    }
})

# Load checkpoint (for resume)
state = db.load_session_state(run_id)
if state:
    resume_from = state.current_variation_index
```

---

### 7. BacktestResult

**Purpose**: Store complete backtest results for archival and analysis

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| result_id | UUID | NO | Primary key, auto-generated |
| run_id | UUID | NO | Foreign key to OptimizationRun |
| variation_id | UUID | NO | Foreign key to StrategyVariation |
| metrics | JSONB | NO | All backtest metrics |
| trades | JSONB | YES | List of all trades |
| equity_curve | JSONB | YES | Equity curve data points |
| created_at | TIMESTAMP | NO | Record creation timestamp |

**Indexes**:
- PRIMARY KEY on result_id
- INDEX on run_id, variation_id

**Usage Example**:
```python
# Store backtest result
result = {
    'run_id': run_id,
    'variation_id': var_id,
    'metrics': {...},
    'trades': [...],
    'equity_curve': [...]
}
```

---

---

### 8. touch_index_fr_files

**Purpose**: Track which source files were touched (created/modified) by each Feature Design Requirement (FDR/FR) issue. Auto-populated by the Touch Index FR ingestion worker which polls Paperclip for FDR-labelled issues, extracts file paths from done-comments, git commit messages, or issue descriptions, and upserts them here.

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key, auto-generated via `gen_random_uuid()` |
| file_path | TEXT | NO | Repo-relative path to the affected source file |
| fr_issue_id | UUID | NO | Paperclip issue UUID for the FR |
| fr_identifier | TEXT | NO | Human-readable issue identifier (e.g. 'BTCAAAAA-1085') |
| fr_owner_agent_id | UUID | NO | Agent UUID of the FR owner/assignee |
| updated_at | TIMESTAMPTZ | NO | Last upsert timestamp (server default `now()`) |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `(file_path, fr_issue_id)` — prevents duplicate file-per-FR rows
- INDEX on `file_path` — fast file-to-FR lookups (blast radius queries)

**Ingestion Worker**: `scripts/run_touch_index_fr_worker.py` — runs every 15 minutes via GitHub Actions cron (`touch-index-fr-worker.yml`), also accepts webhook triggers via `--issue-id`. Validate with `scripts/validate_touch_index_fr.py`.

**Usage Example**:
```python
from sqlalchemy import text
from touch_index.db import get_engine

engine = get_engine()
with engine.connect() as conn:
    rows = conn.execute(
        text("SELECT fr_identifier FROM touch_index_fr_files WHERE file_path = :path"),
        {"path": "src/optimizer_v3/core.py"},
    ).fetchall()
    print([r[0] for r in rows])
```

---

### 9. touch_index_bug_files

**Purpose**: Track which source files were touched by each closed bug fix. Auto-populated by the Touch Index bug-close ingestion worker which scans git commits referencing closed non-FDR issues, extracts touched files, and upserts them here.

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key, auto-generated via `gen_random_uuid()` |
| file_path | TEXT | NO | Repo-relative path to the affected source file |
| bug_issue_id | UUID | NO | Paperclip issue UUID for the bug |
| bug_identifier | TEXT | NO | Human-readable issue identifier (e.g. 'BTCAAAAA-1202') |
| closed_at | TIMESTAMPTZ | YES | When the bug was closed (nullable — some issues lack `completedAt`) |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `(file_path, bug_issue_id)` — prevents duplicate file-per-bug rows
- INDEX on `file_path` — fast file-to-bug lookups

**Ingestion Worker**: `scripts/run_touch_index_bug_worker.py` — runs every 15 minutes via GitHub Actions cron (`touch-index-bug-worker.yml`). Validate with `scripts/validate_touch_index_bug.py`.

**Usage Example**:
```python
from sqlalchemy import text
from touch_index.db import get_engine

engine = get_engine()
with engine.connect() as conn:
    rows = conn.execute(
        text("SELECT bug_identifier FROM touch_index_bug_files WHERE file_path = :path"),
        {"path": "src/touch_index/db.py"},
    ).fetchall()
    print([r[0] for r in rows])
```

---

### 10. touch_index_file_deps

**Purpose**: Directed dependency edges between source files, derived from static import analysis. Phase 2 addition; the table is created in the Phase 1 migration as a placeholder so ingestion services have a stable join target. The `is_internal` flag distinguishes intra-repo edges from external references.

**Columns**:
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key, auto-generated via `gen_random_uuid()` |
| source_file | TEXT | NO | The file that contains the import statement |
| dep_file | TEXT | NO | The file being imported (dependency target) |
| is_internal | BOOLEAN | NO | `TRUE` if both files are within the repo (default `FALSE`) |
| updated_at | TIMESTAMPTZ | NO | Last refresh timestamp (server default `now()`) |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `(source_file, dep_file)` — prevents duplicate edges
- INDEX on `source_file` — forward dependency traversal
- INDEX on `dep_file` — reverse dependency (blast radius) traversal
- PARTIAL INDEX on `dep_file WHERE is_internal = TRUE` — internal-only blast radius queries

**Transitive Closure**: `touch_index_file_deps_transitive` — materialised transitive closure table truncated+reinserted on each refresh. Composite PK on `(source_file, dep_file)` with `min_depth` for shortest-path queries.

---

## CONNECTION MANAGEMENT

### Connection Pool Configuration

The connection pool is managed by `DatabaseConnectionPool` with the following settings:

```python
# From src/optimizer_v3/database/connection_pool.py
pool_size = 10          # Base connections
max_overflow = 20       # Additional connections under load
pool_timeout = 30       # Seconds to wait for connection
pool_recycle = 3600     # Recycle connections after 1 hour
```

### Retry Logic

All database connections include exponential backoff retry:
- Max retries: 3
- Initial delay: 1 second
- Exponential backoff: delay * attempt_number

### Usage

```python
from src.optimizer_v3.database import get_connection_pool

# Get global connection pool (singleton)
pool = get_connection_pool()

# Get a session
session = pool.get_session()
try:
    # Use session
    result = session.execute("SELECT 1")
finally:
    session.close()

# Check pool status
status = pool.get_pool_status()
print(f"Active: {status['active_connections']}")
print(f"Total: {status['total_connections']}")
```

---

## TRANSACTION MANAGEMENT

All database operations use the `session_scope()` context manager for automatic transaction management:

```python
from src.optimizer_v3.database import get_db_manager

db = get_db_manager()

# Automatic commit on success
with db.session_scope() as session:
    run = OptimizationRun(...)
    session.add(run)
    # Commits automatically here

# Automatic rollback on error
try:
    with db.session_scope() as session:
        run = OptimizationRun(...)
        session.add(run)
        raise Exception("Error!")  # Transaction rolls back
except Exception:
    pass  # No data persisted
```

### ACID Compliance

Verified with 15 comprehensive tests covering:
- **Atomicity**: All-or-nothing transactions
- **Consistency**: Constraint enforcement (foreign keys, NOT NULL, unique)
- **Isolation**: Concurrent transaction safety
- **Durability**: Data persists across restarts

---

## NAUTILUSTRADER INTEGRATION

### Type Storage

NautilusTrader types are stored as strings for precision:

```python
from nautilus_trader.model.objects import Quantity, Price, Money
from src.optimizer_v3.database.nautilus_types import NautilusTypeConverter

converter = NautilusTypeConverter()

# Store
quantity = Quantity("1.5")
stored = converter.from_quantity(quantity)  # "1.5" (string)

# Retrieve
quantity = converter.to_quantity(stored)     # Quantity("1.5")
```

### Supported Types

| NautilusTrader Type | Storage Format | Example |
|---------------------|----------------|----------|
| Quantity | String | "1.5" |
| Price | String | "45000.50" |
| Money | String | "1000.75 USD" |
| InstrumentId | String | "BTC/USDT.BINANCE" |
| OrderSide | Enum | OrderSide.BUY |
| PositionSide | Enum | PositionSide.LONG |

### Data Validation

All NautilusTrader data is validated before storage:

```python
from src.optimizer_v3.database import NautilusDataValidator

validator = NautilusDataValidator()

# Validate trade event
event = {
    'instrument_id': 'BTC/USDT.BINANCE',
    'order_side': OrderSide.BUY,
    'quantity': '1.5',
    'price': '45000.00',
    'money': '67500.00 USD'
}

try:
    validator.validate_trade_event(event)
    # Validation passed, safe to store
except ValidationError as e:
    # Handle validation error
    print(f"Invalid data: {e}")
```

---

## BACKUP & RESTORE

### Automated Backups

```bash
# Create backup
python scripts/manage_backups.py create

# Create compressed backup
python scripts/manage_backups.py create --compress

# List backups
python scripts/manage_backups.py list

# Show statistics
python scripts/manage_backups.py stats
```

### Programmatic Backup

```python
from src.optimizer_v3.database import get_backup_manager

backup_mgr = get_backup_manager()

# Create backup
backup_file = backup_mgr.create_backup(compress=True)

# List all backups
backups = backup_mgr.list_backups()

# Cleanup old backups (30 days retention)
deleted = backup_mgr.cleanup_old_backups(retention_days=30)

# Verify backup
is_valid = backup_mgr.verify_backup(backup_file)
```

### Restore

```bash
# Restore from backup
python scripts/manage_backups.py restore backup_file.sql.gz

# Restore with drop-create (DESTRUCTIVE)
python scripts/manage_backups.py restore backup_file.sql.gz --drop --yes
```

### Retention Policy

- Default retention: 30 days
- Configurable via `POSTGRES_BACKUP_RETENTION_DAYS` environment variable
- Automatic cleanup on each backup creation

---

## PERFORMANCE TUNING

### Database Configuration

Optimize PostgreSQL settings in `postgresql.conf`:

```ini
# Memory
shared_buffers = 1GB
work_mem = 32MB
maintenance_work_mem = 256MB
effective_cache_size = 3GB

# Write Performance
synchronous_commit = on
wal_buffers = 16MB
checkpoint_timeout = 10min

# Query Planner
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Indexes

All critical columns are indexed:
- Primary keys (UUID)
- Foreign keys
- Commonly filtered columns (status, timestamp, signal_name)
- Sorting columns (ranking_score DESC, win_rate DESC)

### Query Optimization

```python
# Use indexed queries
# GOOD: Uses index on status
runs = db.get_optimization_runs(status='completed')

# GOOD: Uses index on ranking_score
top_vars = db.get_top_variations(run_id, limit=10)

# GOOD: Uses indexes on timestamp range
events = session.query(SignalEvent)\
    .filter(SignalEvent.timestamp >= start_date)\
    .filter(SignalEvent.timestamp <= end_date)\
    .all()
```

---

## BEST PRACTICES

### 1. Always Use Context Managers

```python
# ✅ GOOD: Automatic cleanup
with db.session_scope() as session:
    # Do work
    pass

# ❌ BAD: Manual management
session = pool.get_session()
# Do work
session.close()  # Easy to forget!
```

### 2. Use Type-Safe NautilusTrader Types

```python
# ✅ GOOD: Type-safe
from nautilus_trader.model.objects import Money
money = Money("1000.00", "USD")
stored = converter.from_money(money)

# ❌ BAD: Float precision loss
money_float = 1000.00  # Don't use floats for money!
```

### 3. Validate Before Storing

```python
# ✅ GOOD: Validate first
validator.validate_optimization_run(run_data)
db.create_optimization_run(run_data)

# ❌ BAD: Skip validation
db.create_optimization_run(run_data)  # Might fail at DB level
```

### 4. Use Bulk Operations

```python
# ✅ GOOD: Single transaction
variations = [{'param1': i} for i in range(1000)]
db.bulk_create(StrategyVariation, variations)

# ❌ BAD: 1000 transactions
for var_data in variations:
    db.create(StrategyVariation, var_data)
```

### 5. Proper Error Handling

```python
# ✅ GOOD: Handle errors
try:
    with db.session_scope() as session:
        # Do work
        pass
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
    # Handle error appropriately

# ❌ BAD: Ignore errors
with db.session_scope() as session:
    # Do work
    pass  # Exceptions propagate unhandled
```

---

## TROUBLESHOOTING

### Connection Issues

**Problem**: `ConnectionError: Max retries exceeded`

**Solution**:
1. Check PostgreSQL is running: `systemctl status postgresql`
2. Verify connection settings in `.env`
3. Test connection: `psql -h localhost -U optimizer_admin -d optimizer_v3`
4. Check pool status: `pool.get_pool_status()`

### Performance Issues

**Problem**: Slow queries

**Solution**:
1. Check query execution plan: `EXPLAIN ANALYZE SELECT ...`
2. Verify indexes exist: `\d+ table_name`
3. Update statistics: `ANALYZE table_name;`
4. Check connection pool: Increase `pool_size` if needed

### Migration Issues

**Problem**: `alembic upgrade head` fails

**Solution**:
1. Check current version: `alembic current`
2. View migration history: `alembic history`
3. Manually apply SQL if needed
4. Downgrade and retry: `alembic downgrade -1 && alembic upgrade head`

### Backup Issues

**Problem**: Backup fails with permission error

**Solution**:
1. Check backup directory permissions
2. Verify POSTGRES_BACKUP_PATH in `.env`
3. Create directory: `mkdir -p /path/to/backups`
4. Set permissions: `chmod 755 /path/to/backups`

---

## QUICK REFERENCE

### Common Operations

```python
from src.optimizer_v3.database import get_db_manager, get_backup_manager

db = get_db_manager()

# Create run
run_id = db.create_optimization_run({...})

# Update run
db.update_optimization_run(run_id, {'status': 'completed'})

# Get runs
runs = db.get_optimization_runs(status='completed')

# Create variation
var_id = db.create_strategy_variation({...})

# Get top variations
top = db.get_top_variations(run_id, limit=10)

# Save checkpoint
db.save_session_state(run_id, {...})

# Load checkpoint
state = db.load_session_state(run_id)

# Backup
backup_mgr = get_backup_manager()
backup_file = backup_mgr.create_backup(compress=True)

# Restore
backup_mgr.restore_backup(backup_file)
```

### CLI Commands

```bash
# Migrations
python scripts/manage_migrations.py create "Add column"
python scripts/manage_migrations.py upgrade
python scripts/manage_migrations.py downgrade
python scripts/manage_migrations.py history

# Backups
python scripts/manage_backups.py create --compress
python scripts/manage_backups.py list
python scripts/manage_backups.py stats
python scripts/manage_backups.py restore file.sql.gz
python scripts/manage_backups.py cleanup --retention 30 --yes
python scripts/manage_backups.py verify file.sql.gz
```

---

## CONTACT & SUPPORT

For issues or questions:
1. Check this guide first
2. Review test files in `tests/database/`
3. Consult NautilusTrader docs: https://nautilustrader.io/docs/latest/
4. Review source code in `src/optimizer_v3/database/`

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-05-12  
**Maintained By**: Data Engineering Team  
**Status**: ✅ Production Ready
