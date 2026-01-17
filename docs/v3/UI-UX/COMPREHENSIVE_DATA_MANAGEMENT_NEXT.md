# COMPREHENSIVE DATA MANAGEMENT - NEXT SESSION PLAN

**Date**: 2026-01-17  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: CRITICAL - Building blocks and Trade Manager depend on this

---

## 🎯 OBJECTIVE

Implement comprehensive gap-free data management for ALL data types:
- ✅ Trades (DONE)
- ⚠️  Funding (TODO)
- ⚠️  Liquidations (TODO)
- ⚠️  Open Interest (TODO)
- ⚠️  Orderbook (TODO)

---

## 📊 CURRENT STATUS (End of Session)

### ✅ What's Working:
1. **Modal UI**: 1300x900, no scrolling, draggable ✓
2. **Trades data**: Reads actual timestamps (2022-03 → 2026-01-15) ✓
3. **Gap detection**: Correct logic (positive = bad, negative = good) ✓
4. **UnifiedDataManager**: Routes correctly, reads from RAW_DATA_DIR ✓

### ⚠️  What's Missing:
1. **Multi-data-type checking**: Only checks trades currently
2. **Multi-data-type downloading**: Only downloads bars/trades
3. **Status per data type**: Need to show gaps for each type
4. **Binance downloaders**: Need scripts for funding, liquidations, OI, orderbook

---

## 🏗️ DATA ARCHITECTURE (Confirmed)

```
data/raw/
├── trades/              9.7GB  (2022-03 → 2026-01-15) ✓
├── funding/            ~5GB    (needs gap checking)
├── liquidations/       ~10GB   (needs gap checking)
├── open_interest/      ~5GB    (needs gap checking)
└── orderbook/          4.4GB   (2026-01-16) ✓
```

---

## 📝 IMPLEMENTATION PLAN

### Phase 1: Enhanced Gap Detection (UnifiedDataManager)

**File**: `src/data_manager/unified_manager.py`

**Add method**: `get_all_data_types_status()`

```python
def get_all_data_types_status(self) -> Dict[str, Dict]:
    """
    Check status of ALL data types
    
    Returns:
        Dict with status for each data type:
        {
            'trades': {
                'start': datetime,
                'end': datetime,
                'gap_days': int,
                'status': 'complete' | 'gap' | 'missing'
            },
            'funding': {...},
            'liquidations': {...},
            'open_interest': {...},
            'orderbook': {...}
        }
    """
    data_types = ['trades', 'funding', 'liquidations', 'open_interest', 'orderbook']
    status = {}
    
    for data_type in data_types:
        data_dir = self.lakeapi_dir / data_type
        if not data_dir.exists():
            status[data_type] = {'status': 'missing', 'gap_days': 999}
            continue
        
        # Find last parquet file
        parquet_files = sorted(data_dir.glob(f'BTC-USDT_{data_type}_*.parquet'))
        if not parquet_files:
            status[data_type] = {'status': 'missing', 'gap_days': 999}
            continue
        
        # Read actual last timestamp (same logic as trades)
        try:
            last_file = parquet_files[-1]
            timestamp_cols = ['timestamp', 'origin_time', 'received_time']
            df = None
            
            for col in timestamp_cols:
                try:
                    df = pd.read_parquet(last_file, columns=[col])
                    if len(df) > 0:
                        end_date = pd.to_datetime(df[col].iloc[-1])
                        gap_days = (datetime.now() - end_date).days
                        status[data_type] = {
                            'start': datetime(2022, 3, 1),  # Known start
                            'end': end_date,
                            'gap_days': gap_days,
                            'status': 'complete' if gap_days <= 0 else 'gap'
                        }
                        break
                except:
                    continue
        except:
            status[data_type] = {'status': 'error', 'gap_days': 999}
    
    return status
```

---

### Phase 2: Enhanced Modal Display

**File**: `src/strategy_builder/ui/data_update_modal.py`

**Update**: `_check_data_gap()` method

```python
def _check_data_gap(self):
    """Check for gaps across ALL data types"""
    try:
        # Get status for ALL data types
        all_status = self.manager.get_all_data_types_status()
        
        # Build comprehensive report
        any_gaps = False
        max_gap = 0
        report_lines = []
        
        report_lines.append("📊 DATA TYPE STATUS:\n")
        
        for data_type, info in all_status.items():
            if info['status'] == 'complete':
                report_lines.append(f"  ✅ {data_type.upper()}: Complete")
                report_lines.append(f"     Through: {info['end'].strftime('%Y-%m-%d')}")
            elif info['status'] == 'gap':
                any_gaps = True
                max_gap = max(max_gap, info['gap_days'])
                report_lines.append(f"  ❌ {data_type.upper()}: GAP DETECTED")
                report_lines.append(f"     Through: {info['end'].strftime('%Y-%m-%d')}")
                report_lines.append(f"     Missing: {info['gap_days']} days")
            elif info['status'] == 'missing':
                any_gaps = True
                max_gap = 999
                report_lines.append(f"  ❌ {data_type.upper()}: MISSING")
        
        report_lines.append(f"\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        if any_gaps:
            self.status_label.setText(
                f"⚠️ DATA GAPS DETECTED: {max_gap} days MISSING"
            )
            self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
            
            report_lines.append("\n❌ CRITICAL: Building blocks need ALL data types!")
            report_lines.append("   - Trade management needs funding rates")
            report_lines.append("   - Building blocks need liquidations")
            report_lines.append("   - Advanced blocks need orderbook")
            report_lines.append("\nClick 'Update Data' to fill ALL gaps.")
            
            self.details_text.setText("\n".join(report_lines))
            self.update_button.setEnabled(True)
        else:
            self.status_label.setText("✅ ALL DATA COMPLETE - 100% ACCURATE")
            self.status_label.setStyleSheet("color: #4ADE80; font-weight: bold;")
            
            report_lines.append("\n✅ PERFECT: All data types complete!")
            report_lines.append("   Building blocks have full data access")
            report_lines.append("   Trade Manager ready for deployment")
            
            self.details_text.setText("\n".join(report_lines))
            self.skip_button.setText("Continue")
    
    except Exception as e:
        self.status_label.setText("❌ Error checking data")
        self.details_text.setText(f"Error: {str(e)}")
```

---

### Phase 3: Comprehensive Download Thread

**File**: `src/strategy_builder/ui/data_update_modal.py`

**Update**: `DataUpdateThread.run()` method

```python
def run(self):
    """Download ALL missing data types from Binance"""
    try:
        self.progress.emit(0, 100, "Checking data types...")
        
        # Get status
        all_status = self.manager.get_all_data_types_status()
        
        # Calculate total work
        data_types_with_gaps = [
            dt for dt, info in all_status.items() 
            if info['status'] in ['gap', 'missing']
        ]
        
        if not data_types_with_gaps:
            self.finished.emit(True, "✅ All data already complete!")
            return
        
        progress_per_type = 100 / len(data_types_with_gaps)
        current_progress = 0
        
        results = []
        
        # Download each type
        for i, data_type in enumerate(data_types_with_gaps):
            self.progress.emit(
                int(current_progress), 
                100, 
                f"Downloading {data_type}..."
            )
            
            # Call appropriate downloader
            if data_type == 'trades':
                # Use existing bar downloader
                pass
            elif data_type == 'funding':
                # Call funding downloader
                self._download_funding()
            elif data_type == 'liquidations':
                # Call liquidations downloader
                self._download_liquidations()
            elif data_type == 'open_interest':
                # Call OI downloader
                self._download_open_interest()
            elif data_type == 'orderbook':
                # Call orderbook downloader
                self._download_orderbook()
            
            current_progress += progress_per_type
            results.append(f"✅ {data_type}: Downloaded")
        
        self.progress.emit(100, 100, "Complete!")
        self.finished.emit(
            True,
            f"✅ Successfully updated ALL data types!\n\n" + 
            "\n".join(results) +
            "\n\nAll building blocks now have complete data!"
        )
        
    except Exception as e:
        self.finished.emit(False, f"❌ Download failed: {str(e)}")
```

---

### Phase 4: Binance Downloaders

**Create new scripts** (based on `scripts/binance/daily_sync.py` pattern):

1. **`scripts/binance/download_funding.py`**
   - Downloads funding rates from Binance Futures
   - 8-hour intervals
   - Saves to `data/binance/funding/`

2. **`scripts/binance/download_liquidations.py`**
   - Downloads liquidation events
   - Saves to `data/binance/liquidations/`

3. **`scripts/binance/download_open_interest.py`**
   - Downloads open interest data
   - Saves to `data/binance/open_interest/`

4. **`scripts/binance/download_orderbook.py`**
   - Downloads orderbook snapshots
   - 1-minute intervals
   - Saves to `data/binance/orderbook/`

**Template** (all follow same pattern):
```python
from src.data_manager.binance.rest_client import BinanceRestClient

client = BinanceRestClient()

# Download data type
data = client.get_{data_type}(
    symbol='BTCUSDT',
    start_date=gap_start,
    end_date=datetime.now()
)

# Save to parquet
output_dir = PROJECT_ROOT / "data" / "binance" / "{data_type}"
output_dir.mkdir(parents=True, exist_ok=True)
data.to_parquet(output_dir / f"BTCUSDT_{data_type}_{date}.parquet")
```

---

## 📊 WHY THIS MATTERS

### Building Blocks Need:
- **OHLCV** (Trades): 85% of blocks ✓
- **Volume + Funding**: Premium/Discount detection
- **Liquidations**: Liquidity sweep detection, stop hunts
- **Open Interest**: Market depth analysis
- **Orderbook**: Advanced market depth blocks

### Trade Manager Needs:
- **Funding rates**: Dynamic TP adjustment based on funding
- **Liquidations**: Avoid clustered liquidation zones
- **Open Interest**: Position sizing based on OI
- **Orderbook**: Optimal entry/exit prices

---

## ✅ SUCCESS CRITERIA

1. **Modal shows status** of ALL 5 data types ✓
2. **Detects gaps** in any data type ✓
3. **Downloads ALL** missing data types ✓
4. **Building blocks** have complete access ✓
5. **Trade Manager** ready for deployment ✓

---

## 🚀 IMPLEMENTATION ORDER

**Session 1** (Next):
1. Implement `get_all_data_types_status()` in UnifiedDataManager
2. Update modal to show all data types
3. Test detection of gaps across all types

**Session 2**:
1. Create Binance downloaders for each type
2. Integrate downloaders into DataUpdateThread
3. Test complete download process

**Session 3**:
1. Verify building blocks can access all data
2. Test Trade Manager integration
3. Setup cron jobs for all data types

---

## 📝 COMMITS SO FAR THIS SESSION

- Commit 29-35: Initial data integration
- Commit 36: Modal 1300x900 FINAL SIZE ✓

**Next Session**: Commits 37-45 (comprehensive data management)

---

**READY FOR IMPLEMENTATION** ✓
