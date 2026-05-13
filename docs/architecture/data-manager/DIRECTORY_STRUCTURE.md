# DATA MANAGER DIRECTORY STRUCTURE
## Organized Layout for Production Implementation

**Date:** 2026-01-08  
**Status:** FINALIZED - READY FOR IMPLEMENTATION

---

## 📁 DIRECTORY ORGANIZATION

### 1. SOURCE FILES: `src/data_manager/`
**Purpose:** Core data management library code (importable modules)

```
src/data_manager/
├── __init__.py                      # Package initialization
├── download/
│   ├── __init__.py
│   ├── synchronizer.py              # Incremental download logic
│   ├── lake_api_client.py           # LakeAPI wrapper
│   └── usage_tracker.py             # 300GB limit tracking
├── aggregation/
│   ├── __init__.py
│   ├── tick_to_bars.py              # Trade aggregation engine
│   ├── multicore_aggregator.py      # 30-core parallel aggregation
│   └── timeframe_generator.py       # All timeframe generation
├── validation/
│   ├── __init__.py
│   ├── file_integrity.py            # Level 1: File checks
│   ├── data_structure.py            # Level 2: Schema validation
│   ├── data_quality.py              # Level 3: Quality checks
│   └── multicore_validator.py       # 30-core parallel validation
├── nautilus/
│   ├── __init__.py
│   ├── data_adapter.py              # DataFrame → Nautilus conversion
│   ├── catalog_manager.py           # ParquetDataCatalog operations
│   └── multicore_converter.py       # 30-core parallel conversion
├── monitoring/
│   ├── __init__.py
│   ├── freshness_checker.py         # Data freshness monitoring
│   ├── usage_monitor.py             # LakeAPI usage alerts
│   └── validation_tracker.py        # Validation error logging
└── utils/
    ├── __init__.py
    ├── date_utils.py                # Month range generation
    ├── file_utils.py                # File operations helpers
    └── checksum.py                  # SHA256 checksums
```

### 2. SCRIPT FILES: `scripts/data_manager/`
**Purpose:** Executable scripts for automation (cron jobs, manual runs)

```
scripts/data_manager/
├── download_synchronize_data.py     # Main download orchestrator
├── aggregate_all_timeframes.py      # Aggregation runner
├── update_nautilus_catalog.py       # Nautilus catalog updater
├── validate_all_data.py             # Validation runner
├── process_multicore_pipeline.py    # Master 30-core pipeline
├── update_paper_trading_data.py     # Hourly paper trading updates
├── backup_critical_data.py          # Backup automation
├── recover_corrupted_file.py        # Recovery procedures
├── check_data_freshness.py          # Freshness monitoring
└── daily_maintenance.py             # Daily automated maintenance
```

### 3. DOCUMENTATION: `docs/v3/data_manager/`
**Purpose:** Planning, architecture, and operational documentation

```
docs/v3/data_manager/
├── INSTITUTIONAL_DATA_MANAGEMENT_PLAN.md  # Master plan (current)
├── DIRECTORY_STRUCTURE.md                 # This file
├── IMPLEMENTATION_GUIDE.md                # Step-by-step implementation
├── OPERATIONS_MANUAL.md                   # Day-to-day operations
├── TROUBLESHOOTING_GUIDE.md               # Common issues & solutions
└── API_REFERENCE.md                       # Code API documentation
```

---

## 🔄 DATA FLOW (With New Structure)

### Download Flow
```
LakeAPI S3
    ↓
scripts/data_manager/download_synchronize_data.py
    ↓ (uses)
src/data_manager/download/synchronizer.py
src/data_manager/download/lake_api_client.py
src/data_manager/download/usage_tracker.py
    ↓ (validates with)
src/data_manager/validation/*.py
    ↓ (saves to)
data/raw/{trades,liquidations,funding,etc.}/
```

### Aggregation Flow
```
data/raw/trades/*.parquet
    ↓
scripts/data_manager/aggregate_all_timeframes.py
    ↓ (uses)
src/data_manager/aggregation/multicore_aggregator.py
src/data_manager/aggregation/tick_to_bars.py
    ↓ (validates with)
src/data_manager/validation/data_quality.py
    ↓ (saves to)
data/raw/BTC_USDT_PERP_{5m,15m,30m,1h,4h}.csv
```

### Nautilus Conversion Flow
```
data/raw/BTC_USDT_PERP_*.csv
    ↓
scripts/data_manager/update_nautilus_catalog.py
    ↓ (uses)
src/data_manager/nautilus/multicore_converter.py
src/data_manager/nautilus/data_adapter.py
src/data_manager/nautilus/catalog_manager.py
    ↓ (saves to)
data/catalog/parquet/bar_data/
```

### Multicore Pipeline Flow
```
scripts/data_manager/process_multicore_pipeline.py
    ↓ (orchestrates)
1. src/data_manager/validation/multicore_validator.py     (30 cores)
2. src/data_manager/aggregation/multicore_aggregator.py   (30 cores)
3. src/data_manager/nautilus/multicore_converter.py       (30 cores)
4. src/data_manager/validation/multicore_validator.py     (30 cores)
```

---

## 🎯 IMPORT PATTERNS

### From Scripts (Executable)
```python
#!/usr/bin/env python3
"""Script: scripts/data_manager/download_synchronize_data.py"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import from src/data_manager
from src.data_manager.download.synchronizer import DataSynchronizer
from src.data_manager.download.usage_tracker import UsageTracker
from src.data_manager.validation.multicore_validator import validate_all_files_parallel

if __name__ == "__main__":
    # Script logic here
    synchronizer = DataSynchronizer()
    synchronizer.sync_all_data()
```

### From Source (Library)
```python
"""Library: src/data_manager/download/synchronizer.py"""

from pathlib import Path
from datetime import datetime

# Import from other data_manager modules
from src.data_manager.download.lake_api_client import LakeAPIClient
from src.data_manager.download.usage_tracker import UsageTracker
from src.data_manager.validation.file_integrity import validate_file_integrity

class DataSynchronizer:
    """Incremental data download and synchronization"""
    
    def __init__(self):
        self.client = LakeAPIClient()
        self.tracker = UsageTracker()
    
    def sync_all_data(self):
        """Download missing data only"""
        # Implementation here
```

### From Other Projects (External)
```python
"""External script using data_manager as library"""

import sys
from pathlib import Path

# Add BTC-Trade-Engine-PaperClip to path
sys.path.insert(0, '/home/sirrus/projects/BTC-Trade-Engine-PaperClip')

# Import data_manager modules
from src.data_manager.aggregation.tick_to_bars import aggregate_trades_to_bars
from src.data_manager.nautilus.data_adapter import convert_to_nautilus_bars

# Use in your code
df_bars = aggregate_trades_to_bars(df_trades, timeframe='15min')
nautilus_bars = convert_to_nautilus_bars(df_bars, timeframe='15min')
```

---

## 📋 IMPLEMENTATION PRIORITY

### Phase 1: Core Library (Week 1)
**Directory:** `src/data_manager/`

1. ✅ Create package structure
2. ✅ Implement download modules
3. ✅ Implement validation modules
4. ✅ Implement aggregation modules
5. ✅ Implement utils

### Phase 2: Scripts (Week 1-2)
**Directory:** `scripts/data_manager/`

1. ✅ Create download script
2. ✅ Create aggregation script
3. ✅ Create validation script
4. ✅ Create multicore pipeline script

### Phase 3: Nautilus Integration (Week 2)
**Directory:** `src/data_manager/nautilus/`

1. ✅ Implement data adapter
2. ✅ Implement catalog manager
3. ✅ Implement multicore converter
4. ✅ Create update script

### Phase 4: Automation (Week 3)
**Directory:** `scripts/data_manager/`

1. ✅ Set up cron jobs
2. ✅ Implement monitoring scripts
3. ✅ Implement backup scripts
4. ✅ Create maintenance script

---

## 🔧 CONFIGURATION

### Environment Variables (.env file)

**⚠️ SECURITY: Never commit .env to git! Add to .gitignore**

Create `.env` file in project root:
```bash
# .env (NEVER COMMIT THIS FILE!)

# LakeAPI Credentials (SENSITIVE - DO NOT SHARE)
LAKEAPI_KEY=your_access_key_here
LAKEAPI_SECRET=your_secret_key_here

# Project paths
BTC_ENGINE_ROOT=/home/sirrus/projects/BTC-Trade-Engine-PaperClip

# Configuration
LAKEAPI_LIMIT_GB=300
MULTICORE_WORKERS=30
```

**Setup .gitignore:**
```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore
```

### Configuration File (Loads from .env)
```python
# src/data_manager/config.py

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_ROOT / "raw"
CATALOG_DIR = DATA_ROOT / "catalog"

# LakeAPI Configuration (loaded from .env - NEVER hardcode!)
LAKEAPI_KEY = os.getenv('LAKEAPI_KEY')
LAKEAPI_SECRET = os.getenv('LAKEAPI_SECRET')
LAKEAPI_LIMIT_GB = int(os.getenv('LAKEAPI_LIMIT_GB', 300))
LAKEAPI_WARNING_GB = int(LAKEAPI_LIMIT_GB * 0.93)  # 93% of limit

# Validate credentials loaded
if not LAKEAPI_KEY or not LAKEAPI_SECRET:
    raise ValueError(
        "LakeAPI credentials not found in .env file! "
        "Please create .env with LAKEAPI_KEY and LAKEAPI_SECRET"
    )

# Multicore
NUM_CORES = int(os.getenv('MULTICORE_WORKERS', 30))  # Leave 2 for system

# Timeframes
TIMEFRAMES = ['5min', '15min', '30min', '1h', '2h', '4h', '6h', '12h', '1d']

# Data Types
DATA_TYPES = ['trades', 'liquidations', 'funding', 'open_interest', 'orderbook']
```

### Usage in Code
```python
# src/data_manager/download/lake_api_client.py

import boto3
from src.data_manager.config import LAKEAPI_KEY, LAKEAPI_SECRET

class LakeAPIClient:
    """LakeAPI client with secure credential handling"""
    
    def __init__(self):
        # Credentials loaded from .env via config.py
        self.session = boto3.Session(
            aws_access_key_id=LAKEAPI_KEY,
            aws_secret_access_key=LAKEAPI_SECRET,
            region_name='eu-west-1'
        )
    
    def download_data(self, table, start, end, symbols):
        """Download data using secure credentials"""
        # Implementation here
```

### Installing python-dotenv
```bash
# Add to requirements.txt
python-dotenv>=1.0.0

# Install
pip install python-dotenv
```

---

## 📝 CRON SCHEDULE (Updated Paths)

```bash
# /etc/cron.d/btc_engine_data_manager

# Monthly: Historical data download (1st of month, 2 AM)
0 2 1 * * /home/sirrus/projects/BTC-Trade-Engine-PaperClip/scripts/data_manager/download_synchronize_data.py --mode=historical

# Daily: Current month download (3 AM)
0 3 * * * /home/sirrus/projects/BTC-Trade-Engine-PaperClip/scripts/data_manager/download_synchronize_data.py --mode=current

# Daily: Multicore processing pipeline (4 AM)
0 4 * * * /home/sirrus/projects/BTC-Trade-Engine-PaperClip/scripts/data_manager/process_multicore_pipeline.py

# Hourly: Paper trading data update
0 * * * * /home/sirrus/projects/BTC-Trade-Engine-PaperClip/scripts/data_manager/update_paper_trading_data.py

# Daily: Data freshness check (5 AM)
0 5 * * * /home/sirrus/projects/BTC-Trade-Engine-PaperClip/scripts/data_manager/check_data_freshness.py

# Weekly: Backup critical data (Sunday, 1 AM)
0 1 * * 0 /home/sirrus/projects/BTC-Trade-Engine-PaperClip/scripts/data_manager/backup_critical_data.py
```

---

## 🎓 BENEFITS OF THIS STRUCTURE

### 1. **Separation of Concerns**
- Library code (src/) separate from executables (scripts/)
- Clear distinction between importable modules and runnable scripts

### 2. **Reusability**
- Other projects can import from src/data_manager/
- Scripts can be called from other scripts
- Building blocks can use data_manager as library

### 3. **Testability**
- Easy to write unit tests for src/data_manager/ modules
- Integration tests for scripts/data_manager/ scripts
- Mock dependencies cleanly

### 4. **Maintainability**
- Logical grouping of related functionality
- Easy to find and modify specific components
- Clear dependency graph

### 5. **Scalability**
- Add new data types by extending modules
- Add new scripts without touching library code
- Easy to parallelize or distribute

---

## 📚 NEXT STEPS

1. **Toggle to ACT MODE** to begin implementation
2. **Week 1:** Create directory structure and core library
3. **Week 2:** Implement scripts and Nautilus integration
4. **Week 3:** Set up automation and monitoring
5. **Week 4:** Test and deploy to production

---

**Status:** ✅ DIRECTORY STRUCTURE FINALIZED  
**Approved By:** User + Expert Mode  
**Ready For:** Implementation Phase

---

*End of Directory Structure Document*