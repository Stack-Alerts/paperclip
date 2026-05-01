# Data Manager Complete Architecture Guide

**Author:** BTC_Engine_v3  
**Date:** February 6, 2026  
**Purpose:** Institutional-grade reference for data_manager system

---

## Executive Summary

The data_manager system provides **unified access to market data** through:
1. **Historical Data:** LakeAPI trades aggregated to bars  
2. **Recent Data:** Binance parquet files (maintained locally)  
3. **Live Updates:** Binance REST API for real-time sync  
4. **Seamless Integration:** Automatic routing and gap-filling

**Critical Understanding:**
- Data is **pre-downloaded** and stored in parquet files
- **Update Manager** keeps files current via Binance API  
- **Backtests** read from local files (NO API calls)
- **Live trading** uses real-time API

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER APPLICATION                         │
│          (Backtesting, Live Trading, Research)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  NAUTILUS LOADER                             │
│         (Converts DataFrame → NautilusTrader Bars)          │
│   File: src/data_manager/nautilus_loader.py                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 UNIFIED MANAGER                              │
│          (Smart routing & source selection)                  │
│   File: src/data_manager/unified_manager.py                 │
│                                                              │
│   Decision Tree:                                             │
│   - Historical (>30 days ago) → LakeAPI                     │
│   - Recent (<30 days) → Binance Files                       │
│   - Hybrid → Combines both seamlessly                       │
└──────────┬────────────────────────────┬────────────────────┘
           │                            │
           ▼                            ▼
┌────────────────────┐      ┌──────────────────────────┐
│  BAR AGGREGATOR    │      │   BINANCE REST CLIENT    │
│  (LakeAPI Layer)   │      │   (API & File Layer)     │
│                    │      │                          │
│  Reads:            │      │  TWO MODES:              │
│  data/raw/trades/  │      │  1. Read Local Files     │
│  BTC-USDT_trades_  │      │     data/binance/        │
│  YYYY-MM.parquet   │      │     BTCUSDT_PERP_15m_    │
│                    │      │     YYYY-MM.parquet      │
│  Aggregates:       │      │                          │
│  Trades → OHLCV    │      │  2. Update Files         │
│  (15min, 1h, etc)  │      │     Via REST API         │
└────────────────────┘      │     (Data Manager only)  │
                            └──────────────────────────┘
```

---

## Component Details

### 1. Unified Manager (`unified_manager.py`)

**Purpose:** Central routing for all data requests

**Key Methods:**

```python
get_bars(timeframe, count=None, start_date=None, end_date=None, source=AUTO)
```
- **Usage:** Primary interface for getting bars
- **Returns:** pandas DataFrame with OHLCV data
- **Routing:** Auto-selects LakeAPI, Binance, or Hybrid

**Internal Methods:**

```python
_get_bars_lakeapi(timeframe, start_date, end_date)
```
- Reads LakeAPI trades from `data/raw/trades/`
- Uses BarAggregator to create OHLCV bars
- Historical data only (>30 days old)

```python
_get_bars_binance(timeframe, start_date, end_date)
```
- **CRITICAL:** Has TWO modes:
  - **Backtest Mode:** Read local parquet files
  - **Update Mode:** Call Binance REST API
- Current implementation calls API (WRONG for backtests!)

```python
_get_bars_hybrid(timeframe, start_date, end_date)
```
- Combines LakeAPI (historical) + Binance (recent)
- Seamless merging across 30-day threshold

---

### 2. Bar Aggregator (`processing/bar_aggregator.py`)

**Purpose:** Convert LakeAPI trades to OHLCV bars

**Key Methods:**

```python
aggregate_from_file(file_path, timeframe='15min', start_date, end_date)
```
- Reads parquet file: `data/raw/trades/BTC-USDT_trades_YYYY-MM.parquet`
- Aggregates trades to OHLCV using pandas resample
- Returns DataFrame with OHLCV bars

```python
aggregate_date_range(data_type, start_date, end_date, timeframe)
```
- Spans multiple months automatically
- Calls `aggregate_from_file()` for each month
- Concatenates and filters to exact range

**Supported Timeframes:**
- Defined in `config.py`: `['5min', '15min', '30min', '1h', '2h', '4h', '6h', '12h', '1d']`
- **NOTE:** Uses 'min' suffix (not 'm')!

---

### 3. Nautilus Loader (`nautilus_loader.py`)

**Purpose:** Convert pandas DataFrame to NautilusTrader Bar objects

**Key Methods:**

```python
load_bars(start, end, timeframe)
```
- Calls UnifiedManager.get_bars()
- Converts DataFrame → List[Bar] (NautilusTrader format)
- Handles timestamp conversion (ns precision)
- Sets instrument ID (BTC-USDT-PERP.BINANCE)

```python
load_warmup_bars(count, timeframe, end_date)
```
- Gets last N bars for strategy initialization
- Typical usage: `load_warmup_bars(count=5000, timeframe='15m')`

---

### 4. Binance REST Client (`binance/rest_client.py`)

**Purpose:** Interface to Binance Futures API

**Key Methods:**

```python
get_klines(interval, symbol, limit, futures=True)
```
- **Current Usage:** Updates local parquet files
- **Problem:** Also called during backtests (WRONG!)
- Gets OHLCV candles from Binance Futures API
- Limit: 1500 candles max per request

**Where It Should Be Used:**
- Data Update Manager (sync process)
- Live trading data feed
- **NOT in backtests!**

---

### 5. Config (`config.py`)

**Critical Definitions:**

```python
TIMEFRAMES = ['5min', '15min', '30min', '1h', '2h', '4h', '6h', '12h', '1d']
PRIMARY_TIMEFRAME = '15min'

TIMEFRAME_MAPPING = {
    '5min': '5T',   # pandas resample format
    '15min': '15T',
    '1h': '1H',
    # ...
}
```

**Data Paths:**
```python
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
# LakeAPI trades: data/raw/trades/BTC-USDT_trades_YYYY-MM.parquet

BINANCE_DIR = PROJECT_ROOT / "data" / "binance"  
# Binance bars: data/binance/YYYY-MM/BTCUSDT_PERP_15m_YYYY-MM.parquet
```

---

## Data Flow Examples

### Example 1: Backtest (30 days)

```python
# User code
from src.optimizer_v3.core.backtest_data_provider import BacktestDataProvider

provider = BacktestDataProvider()
bars = provider.load_bars_for_backtest(
    timeframe='15m',
    start_date=datetime(2026, 1, 7),
    end_date=datetime(2026, 2, 6)
)
```

**What SHOULD happen:**
1. BacktestDataProvider → NautilusDataLoader
2. NautilusDataLoader → UnifiedManager.get_bars()
3. UnifiedManager routes to `_get_bars_binance()` (recent data)
4. `_get_bars_binance()` **reads local parquet files**:
   - `data/binance/2026-01/BTCUSDT_PERP_15m_2026-01.parquet`
   - `data/binance/2026-02/BTCUSDT_PERP_15m_2026-02.parquet`
5. Returns ~2,880 bars (30 days * 96 bars/day)
6. **NO API calls!**

**What's CURRENTLY happening:**
1-3. Same
4. `_get_bars_binance()` **calls Binance REST API**
5. Gets only 1,500 bars (API limit)
6. Network latency + unnecessary API usage

---

### Example 2: Data Update (every 15 min)

```python
# Data Manager sync process
from src.data_manager.binance.rest_client import BinanceRestClient

client = BinanceRestClient()
new_bars = client.get_klines(
    interval='15m',
    limit=10,  # Just get latest bars
    futures=True
)

# Append to existing parquet file
# data/binance/2026-02/BTCUSDT_PERP_15m_2026-02.parquet
```

**This is CORRECT usage of API:**
- Updates local files
- Keeps data <15 minutes stale
- Runs continuously in background

---

### Example 3: Historical Backtest (1 year)

```python
bars = provider.load_bars_for_backtest(
    timeframe='15m',
    start_date=datetime(2025, 2, 1),
    end_date=datetime(2026, 2, 1)
)
```

**Expected flow:**
1. UnifiedManager detects hybrid range
2. Historical part (2025-02 to 2025-12):
   - Routes to `_get_bars_lakeapi()`
   - BarAggregator reads `data/raw/trades/BTC-USDT_trades_2025-*.parquet`
   - Aggregates to 15min bars
3. Recent part (2026-01 to 2026-02):
   - Routes to `_get_bars_binance()` 
   - **Should read** `data/binance/2026-*/BTCUSDT_PERP_15m*.parquet`
4. Combines both seamlessly
5. Returns ~35,040 bars (365 days * 96 bars/day)

---

## Critical Issues Identified

### Issue #1: Timeframe Format Mismatch

**Problem:**
- NautilusLoader passes `'15m'`
- BarAggregator expects `'15min'` (from TIMEFRAMES list)
- Causes LakeAPI to fail → Falls back to Binance API

**Fix Needed:**
Convert format in UnifiedManager before routing:
```python
def _normalize_timeframe(self, tf: str) -> str:
    """Convert 15m → 15min for BarAggregator"""
    mapping = {'1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min'}
    return mapping.get(tf, tf)
```

---

### Issue #2: Building Blocks Expect DataFrame

**Problem:**
- InstitutionalSignalEvaluator passes `List[Bar]` 
- Building blocks expect `pd.DataFrame` with OHLCV columns
- Causes: `'list' object has no attribute 'columns'`

**Fix Applied:** ✅ (Commit 0465a5f)
- Added `_bars_to_dataframe()` helper
- Converts List[Bar] → DataFrame before calling analyze()

---

### Issue #3: Backtests Call Binance API

**Problem:**
- `_get_bars_binance()` calls REST API
- Should read local parquet files instead
- Causes slow execution + only 1,500 bars

**Fix Needed:**
Modify `_get_bars_binance()` to:
1. Check if local files exist
2. Read from `data/binance/YYYY-MM/BTCUSDT_PERP_{timeframe}_YYYY-MM.parquet`
3. Only call API if files missing (fallback)

**BUT:** This broke Data Update Manager!
- Update Manager **needs** API access
- Need separate code paths for backtest vs update

---

## Proper Solution

### Option A: Mode Parameter

Add mode to UnifiedManager:
```python
class UnifiedDataManager:
    def __init__(self, mode='backtest'):  # or 'live'
        self.mode = mode
        
    def _get_bars_binance(self, timeframe, start, end):
        if self.mode == 'backtest':
            return self._read_local_files(...)
        else:  # 'live' or 'update'
            return self._call_binance_api(...)
```

### Option B: Separate Managers

```python
class BacktestDataManager(UnifiedDataManager):
    def _get_bars_binance(self, ...):
        # Always read local files
        
class LiveDataManager(UnifiedDataManager):
    def _get_bars_binance(self, ...):
        # Call API for real-time data
```

### Option C: Check Context

```python
def _get_bars_binance(self, ...):
    # Check if called from backtest or live
    import inspect
    caller = inspect.stack()[2].function
    
    if 'backtest' in caller.lower():
        return self._read_local_files(...)
    else:
        return self._call_binance_api(...)
```

---

## Recommendations

1. **Implement Option A** (mode parameter)
   - Clean separation of concerns
   - Explicit behavior
   - Easy to test

2. **Fix timeframe conversion**
   - Add normalization in UnifiedManager
   - Support both '15m' and '15min'

3. **Document update process**
   - How Data Manager syncs
   - When API is appropriate
   - When to read files

4. **Add validation**
   - Check file freshness
   - Warn if data stale
   - Auto-update if needed

---

## File Locations

```
data/
├── raw/                           # LakeAPI historical
│   └── trades/
│       ├── BTC-USDT_trades_2024-01.parquet
│       ├── BTC-USDT_trades_2024-02.parquet
│       └── ...
│
└── binance/                       # Recent data (maintained)
    ├── 2026-01/
    │   ├── BTCUSDT_PERP_15m_2026-01.parquet
    │   └── BTCUSDT_PERP_1h_2026-01.parquet
    └── 2026-02/
        ├── BTCUSDT_PERP_15m_2026-02.parquet  
        └── BTCUSDT_PERP_1h_2026-02.parquet
```

**Update Frequency:**
- Binance files: Every 15 minutes (via Data Manager)
- LakeAPI files: Static (historical archive)

---

## API Reference

### UnifiedDataManager

```python
manager = UnifiedDataManager()

# Get bars
bars = manager.get_bars(
    timeframe='15m',      # or '15min'
    count=1000,           # last N bars
    start_date=None,      # or datetime
    end_date=None,        # or datetime  
    source=DataSource.AUTO  # AUTO, LAKEAPI, or BINANCE
)

# Check available range
range_info = manager.get_available_date_range('15m')
# Returns: {'earliest': datetime, 'latest': datetime}
```

### NautilusDataLoader

```python
loader = NautilusDataLoader()

# Load for backtest
bars = loader.load_bars(
    start=datetime(2026, 1, 1),
    end=datetime(2026, 2, 1),
    timeframe='15m'
)
# Returns: List[Bar] (NautilusTrader format)

# Load for warmup
bars = loader.load_warmup_bars(
    count=5000,
    timeframe='15m'
)
```

### BarAggregator  

```python
aggregator = BarAggregator()

# Aggregate single month
bars = aggregator.aggregate_month(
    data_type='trades',
    year=2025,
    month=12,
    timeframe='15min'  # NOTE: '15min' not '15m'!
)

# Aggregate date range
bars = aggregator.aggregate_date_range(
    data_type='trades',
    start_date=datetime(2025, 12, 1),
    end_date=datetime(2025, 12, 31),
    timeframe='15min'
)
```

---

## Summary

**Key Principles:**
1. Data is **pre-downloaded and local**
2. Backtests **read files, never call APIs**
3. Data Manager **updates files via API**
4. UnifiedManager **routes intelligently**
5. BarAggregator **uses '15min' format**
6. Building blocks **need DataFrames**

**Current Status:**
- ✅ DataFrame conversion fixed
- ❌ Timeframe format needs conversion
- ❌ Backtest API calls need fixing
- ❌ Need mode separation

This document provides complete understanding for proper fixes.

---

**END OF DOCUMENT**
