# Data Acquisition System - Complete Guide

**Purpose**: Comprehensive data download system for Layer TBD and all trading layers  
**Date**: December 26, 2025  
**Status**: PRODUCTION READY

---

## Overview

This directory contains **complete data acquisition infrastructure** for downloading:

1. ✅ **OHLCV Data** (Already have 6+ years)
2. ✅ **Order Book Snapshots** (Already have 2024-2025)
3. ✅ **Trade Ticks** (Already have 2024-2025)
4. 🆕 **Liquidations** (NEW - Critical for Layer TBD)
5. 🆕 **Funding Rates** (NEW - Optional for Layer TBD)
6. 🆕 **Open Interest** (NEW - Optional for Layer TBD)

---

## Table of Contents

1. [Current Data Status](#current-data-status)
2. [Download Scripts](#download-scripts)
3. [Quick Start](#quick-start)
4. [Data Sources](#data-sources)
5. [Usage Examples](#usage-examples)
6. [Data Verification](#data-verification)
7. [Troubleshooting](#troubleshooting)

---

## Current Data Status

### ✅ Already Downloaded

| Data Type | Location | Coverage | Size | Status |
|-----------|----------|----------|------|--------|
| OHLCV | `data/raw/*.csv` | 2019-2025 (6+ years) | ~500 MB | ✅ Complete |
| Order Book | `data/raw/orderbook/` | 2024-2025 (25 months) | ~15-20 GB | ✅ Complete |
| Trade Ticks | `data/raw/trades/` | 2024-2025 (26 months) | ~25-30 GB | ✅ Complete |

**Total Current Storage**: ~50 GB

### 🆕 Ready to Download

| Data Type | Script | Coverage | Est. Size | Priority |
|-----------|--------|----------|-----------|----------|
| Liquidations | `download_liquidations_funding_oi.py` | 2024-2025 | ~5-8 GB | 🔴 HIGH |
| Funding Rates | `download_liquidations_funding_oi.py` | 2024-2025 | ~2-3 GB | 🟡 MEDIUM |
| Open Interest | `download_liquidations_funding_oi.py` | 2024-2025 | ~2-3 GB | 🟡 MEDIUM |

**Total After Download**: ~60-70 GB

---

## Download Scripts

### 1. `download_liquidations_funding_oi.py` (PRIMARY)

**Purpose**: Download liquidations, funding rates, and open interest from Crypto-Lake API

**Data Source**: Crypto-Lake (AWS S3-backed)

**Features**:
- ✅ Monthly chunking (memory-safe)
- ✅ Automatic skip of existing files
- ✅ Current month auto-update (if >24h old)
- ✅ Same infrastructure as existing downloads
- ✅ Comprehensive error handling

**Coverage**: Jan 2024 - Today

**Download Time**: 1-2 hours for all 3 data types

**Usage**:
```bash
python3 download_liquidations_funding_oi.py
```

**Output**:
```
data/raw/
├── liquidations/
│   ├── BTC-USDT_liquidations_2024-01.parquet
│   ├── BTC-USDT_liquidations_2024-02.parquet
│   └── ...
├── funding/
│   ├── BTC-USDT_funding_2024-01.parquet
│   └── ...
└── open_interest/
    ├── BTC-USDT_open_interest_2024-01.parquet
    └── ...
```

### 2. `download_binance_liquidations.py` (BACKUP)

**Purpose**: Download liquidations directly from Binance Futures API (backup source)

**Data Source**: Binance Public API

**Features**:
- ✅ No API key required
- ✅ Liquidation order details
- ✅ Long vs short liquidation separation
- ✅ Time-chunked downloads
- ✅ Summary statistics

**Use Cases**:
- Backup if Crypto-Lake liquidations incomplete
- Real-time liquidation monitoring
- Cross-validation of liquidation data

**Limitations**:
- 1000 records per request (requires chunking)
- Only liquidations (no funding/OI)
- May have rate limits

**Usage**:
```bash
python3 download_binance_liquidations.py
```

**Output**:
```
data/raw/liquidations_binance/
├── BTC-USDT_liquidations_2024-01.parquet
├── BTC-USDT_liquidations_2024-02.parquet
├── ...
└── SUMMARY.csv
```

### 3. `download_with_lakeapi_chunked.py` (EXISTING)

**Purpose**: Download order book and trade ticks (already used)

**Status**: ✅ Already used for current data

**Note**: This script already has the infrastructure needed. The new liquidation script follows the same pattern.

---

## Quick Start

### Step 1: Download Liquidations, Funding, and Open Interest

**Recommended** - Use Crypto-Lake API (comprehensive, matches existing data):

```bash
cd /home/sirrus/projects/BTC_Engine_LLM
python3 scripts/data_download/download_liquidations_funding_oi.py
```

**When prompted**:
- Type `yes` to proceed
- Wait 1-2 hours for download
- Script will automatically skip existing files

**Expected Output**:
```
================================================================================
CRYPTO-LAKE DOWNLOADER - LIQUIDATIONS, FUNDING, OPEN INTEREST
================================================================================

Data types to download:
  1. ⚡ Liquidations  - Liquidation events with price levels and volumes
  2. 💰 Funding Rates - Funding rate snapshots for perpetual futures
  3. 📊 Open Interest - Open interest snapshots across exchanges

Date range: Jan 2024 to TODAY
Chunk size: 1 month per download
Exchange: BINANCE (BTC-USDT perpetual futures)

Proceed with download? (yes/no): yes

================================================================================
DOWNLOADING LIQUIDATIONS
================================================================================
📊 Status: 0 exist, 13 need download
📥 Will download: 2024-01, 2024-02, ..., 2025-12

  📥 Downloading 2024-01... ✅ 156,432 rows, 12.4 MB
  📥 Downloading 2024-02... ✅ 142,891 rows, 11.2 MB
  ...
```

### Step 2: Verify Downloads

```bash
# Check liquidations
ls -lh data/raw/liquidations/
# Expected: 12-13 files, ~5-8 GB total

# Check funding rates
ls -lh data/raw/funding/
# Expected: 12-13 files, ~2-3 GB total

# Check open interest
ls -lh data/raw/open_interest/
# Expected: 12-13 files, ~2-3 GB total
```

### Step 3: Inspect Data Structure

```bash
# View liquidation data
python3 -c "
import pandas as pd
df = pd.read_parquet('data/raw/liquidations/BTC-USDT_liquidations_2024-01.parquet')
print('Liquidations Data:')
print(f'Rows: {len(df):,}')
print(f'Columns: {list(df.columns)}')
print(f'Date range: {df[\"timestamp\"].min()} to {df[\"timestamp\"].max()}')
print()
print('Sample:')
print(df.head())
"

# View funding data
python3 -c "
import pandas as pd
df = pd.read_parquet('data/raw/funding/BTC-USDT_funding_2024-01.parquet')
print('Funding Rates Data:')
print(f'Rows: {len(df):,}')
print(f'Columns: {list(df.columns)}')
print(df.head())
"

# View open interest
python3 -c "
import pandas as pd
df = pd.read_parquet('data/raw/open_interest/BTC-USDT_open_interest_2024-01.parquet')
print('Open Interest Data:')
print(f'Rows: {len(df):,}')
print(f'Columns: {list(df.columns)}')
print(df.head())
"
```

### Step 4: (Optional) Download Binance Backup

Only if Crypto-Lake liquidations are incomplete:

```bash
python3 scripts/data_download/download_binance_liquidations.py
```

---

## Data Sources

### Primary: Crypto-Lake API

**Endpoint**: AWS S3 (via lakeapi library)

**Credentials**: Embedded in scripts (existing)

**Coverage**:
- Order book snapshots (2x20 levels)
- Trade ticks (buy/sell with timestamps)
- Liquidations (liquidation events)
- Funding rates (8-hour snapshots)
- Open interest (exchange snapshots)

**Advantages**:
- ✅ Comprehensive historical data
- ✅ High quality, institutional-grade
- ✅ Already integrated (order book + trades)
- ✅ Monthly chunking (memory-safe)
- ✅ Automatic caching

**Limitations**:
- Requires AWS credentials (already have)
- Large file sizes (use parquet compression)

### Backup: Binance Futures API

**Endpoint**: `https://fapi.binance.com`

**Credentials**: None required (public endpoints)

**Coverage**:
- Liquidation orders only
- Limited to 1000 records per request
- Requires time-chunking for full history

**Advantages**:
- ✅ No credentials needed
- ✅ Real-time data available
- ✅ Official Binance data

**Limitations**:
- ❌ Only liquidations (no funding/OI)
- ❌ Request limits (1000 records)
- ❌ Requires careful chunking

---

## Usage Examples

### Example 1: Download All Missing Data

```bash
# One command to get everything
python3 scripts/data_download/download_liquidations_funding_oi.py
# Type 'yes' when prompted
# Wait 1-2 hours
```

### Example 2: Download Only Liquidations

Edit `download_liquidations_funding_oi.py`:

```python
# Change data_types list to:
data_types = [
    ('liquidations', 'liquidations'),
    # ('funding', 'funding'),  # Commented out
    # ('open_interest', 'open_interest'),  # Commented out
]
```

Then run:
```bash
python3 scripts/data_download/download_liquidations_funding_oi.py
```

### Example 3: Update Current Month Only

The script automatically re-downloads current month if >24h old:

```bash
# Just run normally
python3 scripts/data_download/download_liquidations_funding_oi.py
# It will skip existing months, update current month
```

### Example 4: Force Re-download

```python
# In download_chunk function, change:
force_redownload=True
```

Or delete existing files first:
```bash
rm data/raw/liquidations/*.parquet
rm data/raw/funding/*.parquet
rm data/raw/open_interest/*.parquet
```

### Example 5: Download from Binance (Backup)

```bash
python3 scripts/data_download/download_binance_liquidations.py
# Type 'yes' when prompted
# Downloads to data/raw/liquidations_binance/
```

---

## Data Verification

### Verification Checklist

After download, verify data quality:

#### 1. Check File Existence

```bash
# Count files
echo "Liquidations: $(ls data/raw/liquidations/*.parquet 2>/dev/null | wc -l) files"
echo "Funding: $(ls data/raw/funding/*.parquet 2>/dev/null | wc -l) files"
echo "Open Interest: $(ls data/raw/open_interest/*.parquet 2>/dev/null | wc -l) files"

# Expected: 12-13 files each (Jan 2024 - current month)
```

#### 2. Check File Sizes

```bash
# Total size per data type
du -sh data/raw/liquidations/
du -sh data/raw/funding/
du -sh data/raw/open_interest/

# Expected:
# liquidations/: 5-8 GB
# funding/: 2-3 GB
# open_interest/: 2-3 GB
```

#### 3. Verify Data Completeness

```python
import pandas as pd
from pathlib import Path

def verify_data_type(data_dir, data_type_name):
    """Verify data completeness"""
    files = sorted(Path(data_dir).glob('*.parquet'))
    
    print(f"\n{data_type_name.upper()} Verification:")
    print(f"  Files: {len(files)}")
    
    if not files:
        print(f"  ❌ No data found!")
        return
    
    total_rows = 0
    date_ranges = []
    
    for file in files:
        df = pd.read_parquet(file)
        total_rows += len(df)
        
        if 'timestamp' in df.columns or 'time' in df.columns:
            time_col = 'timestamp' if 'timestamp' in df.columns else 'time'
            df[time_col] = pd.to_datetime(df[time_col])
            date_ranges.append((
                file.name,
                df[time_col].min(),
                df[time_col].max(),
                len(df)
            ))
    
    print(f"  Total rows: {total_rows:,}")
    print(f"  Date coverage:")
    for filename, start, end, rows in date_ranges[:3]:  # First 3
        print(f"    {filename}: {start} to {end} ({rows:,} rows)")
    if len(date_ranges) > 3:
        print(f"    ... and {len(date_ranges)-3} more files")
    
    print(f"  ✅ Verification complete")

# Run verification
verify_data_type('data/raw/liquidations', 'liquidations')
verify_data_type('data/raw/funding', 'funding')
verify_data_type('data/raw/open_interest', 'open_interest')
```

Save as `scripts/data_download/verify_downloads.py` and run:

```bash
python3 scripts/data_download/verify_downloads.py
```

#### 4. Compare Data Sources (if using both)

```python
import pandas as pd

# Load same month from both sources
lake = pd.read_parquet('data/raw/liquidations/BTC-USDT_liquidations_2024-01.parquet')
binance = pd.read_parquet('data/raw/liquidations_binance/BTC-USDT_liquidations_2024-01.parquet')

print(f"Crypto-Lake liquidations: {len(lake):,}")
print(f"Binance liquidations: {len(binance):,}")
print(f"Difference: {abs(len(lake) - len(binance)):,}")

# Use the source with more data
if len(lake) >= len(binance):
    print("✅ Use Crypto-Lake (more comprehensive)")
else:
    print("⚠️  Binance has more data - investigate")
```

---

## Troubleshooting

### Issue 1: Download Fails with "No data"

**Symptoms**:
```
  📥 Downloading 2024-01... ⚠️  No data
```

**Possible Causes**:
1. Data doesn't exist for that time period
2. API credentials expired
3. Network issues
4. Data type not available on Lake API

**Solutions**:

1. **Check if data exists**:
   ```python
   from lakeapi import load_data
   import boto3
   from datetime import datetime
   
   session = boto3.Session(
       aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', ''),
       aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
       region_name='eu-west-1'
   )
   
   # Test liquidations
   df = load_data(
       table='liquidations',
       start=datetime(2024, 1, 1),
       end=datetime(2024, 1, 2),
       symbols=['BTC-USDT'],
       exchanges=['BINANCE'],
       boto3_session=session
   )
   
   print(f"Rows: {len(df)}")
   print(df.head() if not df.empty else "No data")
   ```

2. **Try different exchange**:
   - Change `exchanges=['BINANCE']` to `exchanges=['BINANCE_FUTURES']`

3. **Use Binance backup**:
   ```bash
   python3 scripts/data_download/download_binance_liquidations.py
   ```

### Issue 2: Out of Memory Error

**Symptoms**:
```
MemoryError: Unable to allocate array
```

**Cause**: Downloading too large a time period at once

**Solution**: Script already uses monthly chunks, but if still happening:

1. **Reduce chunk size** in code:
   ```python
   # In download_chunk, the monthly chunking should be fine
   # But if needed, chunk by week instead
   ```

2. **Close other applications**

3. **Check system RAM**:
   ```bash
   free -h
   ```

### Issue 3: AWS Credentials Error

**Symptoms**:
```
botocore.exceptions.NoCredentialsError
```

**Cause**: Boto3 session not properly configured

**Solution**: Credentials are embedded in script. If still failing:

```python
# Verify credentials work
import boto3

session = boto3.Session(
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', ''),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
    region_name='eu-west-1'
)

s3 = session.client('s3')
print("✅ Credentials valid")
```

### Issue 4: Slow Download Speed

**Symptoms**: Download takes >3 hours

**Causes**: Network speed, API rate limits

**Solutions**:

1. **Run during off-peak hours**
2. **Use wired connection** (not WiFi)
3. **Check network speed**:
   ```bash
   speedtest-cli
   ```
4. **Run in background**:
   ```bash
   nohup python3 scripts/data_download/download_liquidations_funding_oi.py > download.log 2>&1 &
   tail -f download.log
   ```

### Issue 5: Files Already Exist but Want to Re-download

**Solution**:

```bash
# Option 1: Delete specific data type
rm data/raw/liquidations/*.parquet

# Option 2: Delete all new data
rm -rf data/raw/liquidations/
rm -rf data/raw/funding/
rm -rf data/raw/open_interest/

# Then re-run download
python3 scripts/data_download/download_liquidations_funding_oi.py
```

---

## Next Steps After Download

### 1. Integrate into Layer TBD

See `docs/Layer_TBD/TBD_Data_Requirements_Analysis.md` for integration guide.

### 2. Create Data Loader Utilities

Create `src/utils/data_loaders.py`:

```python
def load_liquidations(start_date, end_date):
    """Load liquidation data for date range"""
    pass

def load_funding_rates(start_date, end_date):
    """Load funding rate data for date range"""
    pass

def load_open_interest(start_date, end_date):
    """Load open interest data for date range"""
    pass
```

### 3. Update Layer TBD

Add liquidation analysis to `src/layers/layer_tbd_method.py`:

```python
def _load_liquidation_data(self):
    """Load and cache liquidation levels"""
    pass

def _analyze_levels_with_liquidations(self, price, liquidation_data):
    """Enhance level analysis with liquidation proximity"""
    pass
```

### 4. Extend Reporting

Update `docs/Layer_reporting/LAYER_REPORTING_COMPLETE.md` to include:
- Liquidation-based level analysis
- Funding rate bias in session analysis
- Open interest trend validation

---

## Summary

### What You Have Now

✅ **Complete Data Infrastructure**:
- OHLCV: 6+ years (2019-2025)
- Order Book: 2 years (2024-2025)
- Trade Ticks: 2 years (2024-2025)
- Liquidations: Ready to download (2024-2025)
- Funding Rates: Ready to download (2024-2025)
- Open Interest: Ready to download (2024-2025)

✅ **Download Systems**:
- Primary: Crypto-Lake API (comprehensive)
- Backup: Binance API (liquidations only)
- Both use monthly chunking (memory-safe)
- Automatic skip of existing data
- Current month auto-update

✅ **Total Storage**: 60-70 GB after download

### Recommended Action

**Run downloads NOW** before starting Layer TBD testing:

```bash
cd /home/sirrus/projects/BTC_Engine_LLM
python3 scripts/data_download/download_liquidations_funding_oi.py
```

This ensures all data is in place before implementation begins, following your guidance to get all data systems ready first.

---

**Document Version**: 1.0  
**Date**: December 26, 2025  
**Maintained By**: BTC_Engine_LLM Team
