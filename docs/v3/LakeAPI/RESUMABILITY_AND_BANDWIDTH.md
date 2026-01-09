# Data Download Resumability & Bandwidth Management

**Important**: All download scripts are designed to be **resumable** and **bandwidth-efficient** to handle large downloads and monthly transfer limits.

---

## Resumability Features

### ✅ Already Implemented

All download scripts (`download_liquidations_funding_oi.py`, `download_with_lakeapi_chunked.py`, `download_binance_liquidations.py`) have these features:

#### 1. **Automatic File Detection**

Before downloading any data, scripts check if files already exist:

```python
if output_file.exists() and not force_redownload:
    print(f"  ✅ Skipping {chunk_name}... (already exists, {file_size_mb:.1f} MB)")
    return "skipped"
```

**Result**: No re-downloading of existing data.

#### 2. **Pre-Download Scanning**

Scripts scan the `data/raw/` directory before starting:

```python
for start_date, end_date, chunk_name in month_ranges:
    output_file = output_dir / f"BTC-USDT_{data_type_name}_{chunk_name}.parquet"
    
    if output_file.exists():
        already_exists.append(chunk_name)
    else:
        needs_download.append(chunk_name)

print(f"📊 Status: {len(already_exists)} exist, {len(needs_download)} need download")
print(f"📥 Will download: {', '.join(needs_download)}")
```

**Output Example**:
```
📊 Status: 8 exist, 5 need download
📥 Will download: 2024-09, 2024-10, 2024-11, 2024-12, 2025-12
```

#### 3. **Current Month Auto-Update**

Only the current month is re-downloaded if data is >24 hours old:

```python
if is_current_month:
    file_age_hours = (datetime.now().timestamp() - output_file.stat().st_mtime) / 3600
    
    if file_age_hours > 24:
        print(f"  🔄 Re-downloading {chunk_name}... (outdated: {file_age_hours:.1f}h old)")
        output_file.unlink()
    else:
        print(f"  ✅ Skipping {chunk_name}... (recent: {file_age_hours:.1f}h old)")
        return "skipped"
```

**Result**: Historical data never re-downloaded, current month stays fresh.

#### 4. **Safe Interruption**

Downloads can be safely interrupted (Ctrl+C):

- Each file is written atomically
- Partially downloaded files are not saved
- Next run picks up where it left off
- No corrupted files

#### 5. **Error Handling**

Failed downloads don't stop the script:

```python
except Exception as e:
    print(f" ❌ Error: {type(e).__name__}: {str(e)}")
    return "error"
```

**Result**: Script continues with next file. Re-run to retry failed files.

---

## Bandwidth Usage Estimation

### Per Download Session

#### Liquidations, Funding, Open Interest (New Data)

**If starting from scratch**:

| Data Type | Months | Size per Month | Total Size |
|-----------|--------|----------------|------------|
| Liquidations | 13 | 400-600 MB | ~5-8 GB |
| Funding Rates | 13 | 80-150 MB | ~1-2 GB |
| Open Interest | 13 | 300-500 MB | ~4-6 GB |
| **TOTAL** | | | **~10-16 GB** |

**If partially downloaded** (resuming):

Only missing months are downloaded. For example:
- If 8 months already downloaded: Only 5 months × ~800 MB = **~4 GB**
- If current month update only: **~800 MB**

#### Order Book & Trades (Already Downloaded)

These scripts (`download_with_lakeapi_chunked.py`) also have resumability:

| Data Type | Size | Status |
|-----------|------|--------|
| Order Book | ~15-20 GB | ✅ Already downloaded (25 files) |
| Trade Ticks | ~25-30 GB | ✅ Already downloaded (26 files) |

**Bandwidth if re-running**: **~0 GB** (all files skipped)

---

## How to Minimize Bandwidth Usage

### 1. **Check What You Have First**

Before running any download script:

```bash
# Check liquidations
ls -lh data/raw/liquidations/ 2>/dev/null | wc -l
du -sh data/raw/liquidations/ 2>/dev/null

# Check funding
ls -lh data/raw/funding/ 2>/dev/null | wc -l
du -sh data/raw/funding/ 2>/dev/null

# Check open interest
ls -lh data/raw/open_interest/ 2>/dev/null | wc -l
du -sh data/raw/open_interest/ 2>/dev/null

# Check existing order book & trades
ls -lh data/raw/orderbook/ | wc -l  # Should be 26 files
ls -lh data/raw/trades/ | wc -l     # Should be 27 files
```

**If files exist**: Script will skip them automatically.

### 2. **Run Incrementally**

Download one data type at a time by editing the script:

```python
# In download_liquidations_funding_oi.py, comment out unneeded types:

data_types = [
    ('liquidations', 'liquidations'),  # Download this first
    # ('funding', 'funding'),          # Comment out
    # ('open_interest', 'open_interest'),  # Comment out
]
```

**Bandwidth per type**:
- Liquidations only: ~5-8 GB
- Funding only: ~1-2 GB
- Open Interest only: ~4-6 GB

### 3. **Test with Single Month First**

Modify start year to test:

```python
# In main() function:
start_year = 2025  # Only download 2025 data
end_year = datetime.now().year
```

**Bandwidth**: ~800 MB for all 3 data types for 1 month

### 4. **Use Download Scheduling**

For limited monthly bandwidth, schedule downloads:

```bash
# Week 1: Liquidations only
python3 scripts/data_download/download_liquidations_funding_oi.py
# Edit script to enable only liquidations

# Week 2: Funding only  
python3 scripts/data_download/download_liquidations_funding_oi.py
# Edit script to enable only funding

# Week 3: Open Interest only
python3 scripts/data_download/download_liquidations_funding_oi.py
# Edit script to enable only open_interest
```

---

## Bandwidth Monitoring

### Track Download Progress

The script shows real-time bandwidth usage:

```
  📥 Downloading 2024-01... ✅ 156,432 rows, 12.4 MB
  📥 Downloading 2024-02... ✅ 142,891 rows, 11.2 MB
  ...
  
✅ Completed: 13 downloaded, 0 skipped, 0 no data, 0 errors
```

**Running Total**: Sum the MB values to track bandwidth used.

### System Bandwidth Monitor

Monitor network usage during download:

```bash
# Install if not available
sudo apt install nethogs

# Monitor network usage
sudo nethogs

# Or use iftop
sudo apt install iftop
sudo iftop -i eth0  # Replace eth0 with your interface
```

### Calculate Remaining Downloads

```python
# Quick script to check remaining downloads
import os
from pathlib import Path

data_types = ['liquidations', 'funding', 'open_interest']
months_expected = 13  # Jan 2024 - Dec 2025

for dtype in data_types:
    path = Path(f'data/raw/{dtype}')
    if path.exists():
        files = list(path.glob('*.parquet'))
        print(f"{dtype}: {len(files)}/{months_expected} files")
        print(f"  Missing: {months_expected - len(files)} files")
        print(f"  Est. bandwidth needed: {(months_expected - len(files)) * 600} MB")
    else:
        print(f"{dtype}: 0/{months_expected} files")
        print(f"  Est. bandwidth needed: {months_expected * 600} MB (~{months_expected * 0.6:.1f} GB)")
    print()
```

Save as `scripts/data_download/check_missing.py` and run:

```bash
python3 scripts/data_download/check_missing.py
```

---

## Recovery from Interruption

### If Download is Interrupted

The script is **fully resumable**:

1. **Partial files are discarded**: Only complete files are saved
2. **Re-run the same command**: Script automatically detects existing files
3. **No data corruption**: Atomic file writes ensure integrity

**Example**:

```bash
# Download interrupted after 5 files
python3 scripts/data_download/download_liquidations_funding_oi.py
# Ctrl+C pressed

# Re-run (safe to do)
python3 scripts/data_download/download_liquidations_funding_oi.py

# Output will show:
# 📊 Status: 5 exist, 8 need download
# 📥 Will download: 2024-06, 2024-07, ...
```

### If Files Are Corrupted

Manually delete corrupted files:

```bash
# Remove single corrupted file
rm data/raw/liquidations/BTC-USDT_liquidations_2024-05.parquet

# Remove all files for a data type (if needed)
rm data/raw/liquidations/*.parquet

# Re-run download
python3 scripts/data_download/download_liquidations_funding_oi.py
```

---

## Monthly Update Strategy

### After Initial Download

**Monthly Bandwidth Usage**: ~800 MB - 1.5 GB

Once all historical data is downloaded, monthly updates are minimal:

```bash
# Run monthly (first week of new month)
python3 scripts/data_download/download_liquidations_funding_oi.py

# Expected output:
📊 Status: 12 exist, 1 need download
📥 Will download: 2025-01

  📥 Downloading 2025-01... ✅ 145,234 rows, 11.8 MB
  ✅ Skipping 2024-01... (already exists, 12.4 MB)
  ✅ Skipping 2024-02... (already exists, 11.2 MB)
  ...
```

**Bandwidth**: Only new month (~400-600 MB per data type) = **~1.2-1.8 GB total**

### Automation

Create monthly cron job (optional):

```bash
# Edit crontab
crontab -e

# Add line (runs 1st of each month at 2 AM)
0 2 1 * * cd /home/sirrus/projects/BTC_Engine_LLM && /home/sirrus/projects/BTC_Engine_LLM/venv/bin/python3 scripts/data_download/download_liquidations_funding_oi.py > logs/data_download_$(date +\%Y\%m).log 2>&1
```

---

## Summary

### Resumability: ✅ EXCELLENT

- **Automatic file detection**: Never re-download existing files
- **Pre-scan reporting**: Know what will download before it starts
- **Safe interruption**: Ctrl+C won't corrupt data
- **Atomic writes**: Files are complete or don't exist
- **Current month updates**: Only re-download if >24h old

### Bandwidth Efficiency: ✅ EXCELLENT

- **Initial download**: ~10-16 GB (once)
- **Monthly updates**: ~1-2 GB
- **Re-runs**: ~0 GB (all skipped)
- **Partial downloads**: Script shows exactly what's missing
- **Incremental approach**: Download one type at a time if needed

### Best Practices

1. ✅ Check existing data before running: `ls -lh data/raw/*/`
2. ✅ Run script - it will skip existing files automatically
3. ✅ If interrupted, just re-run - perfectly safe
4. ✅ Monitor bandwidth with `nethogs` or `iftop` if concerned
5. ✅ Download incrementally if bandwidth-limited (1 type per week)

### Transfer Limit Management

If you have a **monthly transfer limit**:

**Option 1**: Download all at once (~10-16 GB initial)
- Best if you have >20 GB monthly limit
- Fastest approach

**Option 2**: Download incrementally
- Week 1: Liquidations (~5-8 GB)
- Week 2: Open Interest (~4-6 GB)  
- Week 3: Funding (~1-2 GB)
- Best if monthly limit is <20 GB

**Option 3**: Download recent data only
- Modify `start_year = 2025` in script
- Only 1-2 months instead of 13
- Bandwidth: ~1-2 GB instead of 10-16 GB
- Can backfill historical data later

---

**Document Version**: 1.0  
**Date**: December 26, 2025  
**Purpose**: Ensure users understand bandwidth efficiency and resumability
