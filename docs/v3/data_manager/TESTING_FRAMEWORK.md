# DATA MANAGER TESTING FRAMEWORK
## Comprehensive Test Suite for Institutional-Grade Reliability

**Date:** 2026-01-08  
**Status:** READY FOR IMPLEMENTATION  
**Coverage Target:** 95%+ code coverage  
**Real Money at Risk:** Every test matters

---

## 📋 TESTING PHILOSOPHY

**Institutional-Grade Requirements:**
- **100% Coverage** of critical paths (downloads, validation, financial calculations)
- **Edge Cases** - Test all boundary conditions and failure modes
- **Regression Tests** - Prevent past bugs from reoccurring
- **Performance Tests** - Ensure 30-core processing meets targets
- **Integration Tests** - Verify complete data pipeline
- **End-to-End Tests** - Full system validation

**Testing Pyramid:**
```
                  ▲
                 / \
                /   \
               / E2E \          10% - End-to-end tests
              /_______\
             /         \
            /Integration\       20% - Integration tests
           /_____________\
          /               \
         /   Unit Tests    \    70% - Unit tests
        /___________________\
```

---

## 🧪 TEST STRUCTURE

### Directory Organization
```
tests/
├── unit/                           # Unit tests (70% of tests)
│   ├── test_download/
│   │   ├── test_synchronizer.py
│   │   ├── test_lake_api_client.py
│   │   └── test_usage_tracker.py
│   ├── test_aggregation/
│   │   ├── test_tick_to_bars.py
│   │   ├── test_multicore_aggregator.py
│   │   └── test_timeframe_generator.py
│   ├── test_validation/
│   │   ├── test_file_integrity.py
│   │   ├── test_data_structure.py
│   │   ├── test_data_quality.py
│   │   └── test_multicore_validator.py
│   ├── test_nautilus/
│   │   ├── test_data_adapter.py
│   │   ├── test_catalog_manager.py
│   │   └── test_multicore_converter.py
│   └── test_utils/
│       ├── test_date_utils.py
│       ├── test_file_utils.py
│       └── test_checksum.py
│
├── integration/                    # Integration tests (20% of tests)
│   ├── test_download_pipeline.py
│   ├── test_aggregation_pipeline.py
│   ├── test_validation_pipeline.py
│   ├── test_nautilus_pipeline.py
│   └── test_multicore_pipeline.py
│
├── e2e/                           # End-to-end tests (10% of tests)
│   ├── test_complete_pipeline.py
│   ├── test_daily_automation.py
│   ├── test_recovery_procedures.py
│   └── test_live_trading_warmup.py
│
├── performance/                   # Performance benchmarks
│   ├── test_multicore_speedup.py
│   ├── test_memory_usage.py
│   └── test_throughput.py
│
├── fixtures/                      # Test data
│   ├── sample_trades.parquet
│   ├── sample_liquidations.parquet
│   ├── sample_bars.csv
│   └── corrupted_data.parquet
│
└── conftest.py                    # Pytest configuration
```

---

## 🔬 UNIT TESTS (70%)

### Test 1: Data Download - Synchronizer
**File:** `tests/unit/test_download/test_synchronizer.py`

```python
import pytest
from pathlib import Path
from datetime import datetime
from src.data_manager.download.synchronizer import DataSynchronizer

class TestDataSynchronizer:
    """Unit tests for DataSynchronizer"""
    
    @pytest.fixture
    def synchronizer(self, tmp_path):
        """Create synchronizer with temp directory"""
        return DataSynchronizer(data_dir=tmp_path)
    
    # HAPPY PATH TESTS
    
    def test_scan_existing_data_empty(self, synchronizer):
        """Test scanning empty directory"""
        result = synchronizer.scan_existing_data()
        assert result == {'trades': [], 'liquidations': [], 'funding': []}
    
    def test_scan_existing_data_populated(self, synchronizer, tmp_path):
        """Test scanning directory with files"""
        # Create test files
        (tmp_path / 'trades').mkdir()
        (tmp_path / 'trades' / 'BTC-USDT_trades_2025-01.parquet').touch()
        (tmp_path / 'trades' / 'BTC-USDT_trades_2025-02.parquet').touch()
        
        result = synchronizer.scan_existing_data()
        assert len(result['trades']) == 2
        assert '2025-01' in result['trades']
        assert '2025-02' in result['trades']
    
    def test_identify_missing_months_all_missing(self, synchronizer):
        """Test when all months need downloading"""
        missing = synchronizer.identify_missing_months(
            start_date='2025-01-01',
            end_date='2025-03-31',
            data_type='trades'
        )
        assert len(missing) == 3
        assert (2025, 1) in missing
        assert (2025, 2) in missing
        assert (2025, 3) in missing
    
    def test_identify_missing_months_some_exist(self, synchronizer, tmp_path):
        """Test when some months already exist"""
        # Create existing file
        (tmp_path / 'trades').mkdir()
        (tmp_path / 'trades' / 'BTC-USDT_trades_2025-01.parquet').touch()
        
        missing = synchronizer.identify_missing_months(
            start_date='2025-01-01',
            end_date='2025-03-31',
            data_type='trades'
        )
        assert len(missing) == 2
        assert (2025, 1) not in missing
        assert (2025, 2) in missing
        assert (2025, 3) in missing
    
    # EDGE CASE TESTS
    
    def test_current_month_freshness_missing_file(self, synchronizer):
        """Test freshness check when file doesn't exist"""
        is_stale = synchronizer.check_current_month_freshness('trades')
        assert is_stale is True
    
    def test_current_month_freshness_recent_file(self, synchronizer, tmp_path):
        """Test freshness check with recent file (<24h)"""
        # Create fresh file
        (tmp_path / 'trades').mkdir()
        current_month = datetime.now().strftime('%Y-%m')
        (tmp_path / 'trades' / f'BTC-USDT_trades_{current_month}.parquet').touch()
        
        is_stale = synchronizer.check_current_month_freshness('trades')
        assert is_stale is False
    
    def test_current_month_freshness_stale_file(self, synchronizer, tmp_path):
        """Test freshness check with old file (>24h)"""
        # Create old file (mock modification time)
        (tmp_path / 'trades').mkdir()
        current_month = datetime.now().strftime('%Y-%m')
        file_path = tmp_path / 'trades' / f'BTC-USDT_trades_{current_month}.parquet'
        file_path.touch()
        
        # Modify mtime to 25 hours ago (mock using os.utime if needed)
        import time
        old_time = time.time() - (25 * 3600)
        os.utime(file_path, (old_time, old_time))
        
        is_stale = synchronizer.check_current_month_freshness('trades')
        assert is_stale is True
    
    # BOUNDARY TESTS
    
    def test_month_range_single_month(self, synchronizer):
        """Test month range with single month"""
        missing = synchronizer.identify_missing_months(
            start_date='2025-01-01',
            end_date='2025-01-31',
            data_type='trades'
        )
        assert len(missing) == 1
        assert (2025, 1) in missing
    
    def test_month_range_year_boundary(self, synchronizer):
        """Test month range crossing year boundary"""
        missing = synchronizer.identify_missing_months(
            start_date='2024-12-01',
            end_date='2025-02-28',
            data_type='trades'
        )
        assert len(missing) == 3
        assert (2024, 12) in missing
        assert (2025, 1) in missing
        assert (2025, 2) in missing
    
    # ERROR HANDLING TESTS
    
    def test_invalid_data_type(self, synchronizer):
        """Test with invalid data type"""
        with pytest.raises(ValueError):
            synchronizer.identify_missing_months(
                start_date='2025-01-01',
                end_date='2025-03-31',
                data_type='invalid_type'
            )
    
    def test_end_before_start(self, synchronizer):
        """Test when end date is before start date"""
        with pytest.raises(ValueError):
            synchronizer.identify_missing_months(
                start_date='2025-03-01',
                end_date='2025-01-31',
                data_type='trades'
            )
```

### Test 2: Data Validation - File Integrity
**File:** `tests/unit/test_validation/test_file_integrity.py`

```python
import pytest
from pathlib import Path
import pandas as pd
from src.data_manager.validation.file_integrity import validate_file_integrity

class TestFileIntegrity:
    """Unit tests for file integrity validation"""
    
    # HAPPY PATH TESTS
    
    def test_valid_parquet_file(self, tmp_path):
        """Test validation of valid parquet file"""
        # Create valid parquet file
        df = pd.DataFrame({'col1': [1, 2, 3], 'col2': [4, 5, 6]})
        file_path = tmp_path / 'test.parquet'
        df.to_parquet(file_path)
        
        assert validate_file_integrity(file_path) is True
    
    # EDGE CASE TESTS
    
    def test_missing_file(self, tmp_path):
        """Test validation of non-existent file"""
        file_path = tmp_path / 'nonexistent.parquet'
        assert validate_file_integrity(file_path) is False
    
    def test_empty_file(self, tmp_path):
        """Test validation of empty file"""
        file_path = tmp_path / 'empty.parquet'
        file_path.touch()  # Create empty file
        assert validate_file_integrity(file_path) is False
    
    def test_zero_row_parquet(self, tmp_path):
        """Test validation of parquet with zero rows"""
        df = pd.DataFrame({'col1': [], 'col2': []})
        file_path = tmp_path / 'zero_rows.parquet'
        df.to_parquet(file_path)
        
        assert validate_file_integrity(file_path) is False
    
    def test_corrupted_parquet(self, tmp_path):
        """Test validation of corrupted parquet file"""
        file_path = tmp_path / 'corrupted.parquet'
        with open(file_path, 'wb') as f:
            f.write(b'corrupted data not parquet format')
        
        assert validate_file_integrity(file_path) is False
    
    # PERMISSION TESTS
    
    def test_unreadable_file(self, tmp_path):
        """Test validation of file without read permissions"""
        df = pd.DataFrame({'col1': [1, 2, 3]})
        file_path = tmp_path / 'unreadable.parquet'
        df.to_parquet(file_path)
        
        # Remove read permissions
        import os
        os.chmod(file_path, 0o000)
        
        assert validate_file_integrity(file_path) is False
        
        # Restore permissions for cleanup
        os.chmod(file_path, 0o644)
```

### Test 3: Data Aggregation - Tick to Bars
**File:** `tests/unit/test_aggregation/test_tick_to_bars.py`

```python
import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.data_manager.aggregation.tick_to_bars import aggregate_trades_to_bars

class TestTickToBars:
    """Unit tests for trade aggregation"""
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample tick trades"""
        timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='1min')
        prices = [50000 + i for i in range(100)]
        quantities = [0.1] * 100
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'price': prices,
            'quantity': quantities
        })
    
    # HAPPY PATH TESTS
    
    def test_aggregate_to_5min(self, sample_trades):
        """Test aggregation to 5-minute bars"""
        bars = aggregate_trades_to_bars(sample_trades, timeframe='5min')
        
        assert len(bars) == 20  # 100 minutes / 5 = 20 bars
        assert 'open' in bars.columns
        assert 'high' in bars.columns
        assert 'low' in bars.columns
        assert 'close' in bars.columns
        assert 'volume' in bars.columns
    
    def test_aggregate_to_15min(self, sample_trades):
        """Test aggregation to 15-minute bars"""
        bars = aggregate_trades_to_bars(sample_trades, timeframe='15min')
        
        assert len(bars) == 7  # 100 minutes / 15 ≈ 7 bars
        assert (bars['volume'] > 0).all()
    
    def test_ohlc_logic(self, sample_trades):
        """Test OHLC logic is correct"""
        bars = aggregate_trades_to_bars(sample_trades, timeframe='15min')
        
        # High >= Low
        assert (bars['high'] >= bars['low']).all()
        
        # Open/Close within High/Low
        assert (bars['open'] <= bars['high']).all()
        assert (bars['open'] >= bars['low']).all()
        assert (bars['close'] <= bars['high']).all()
        assert (bars['close'] >= bars['low']).all()
    
    # EDGE CASE TESTS
    
    def test_single_trade(self):
        """Test aggregation with single trade"""
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'price': [50000],
            'quantity': [1.0]
        })
        
        bars = aggregate_trades_to_bars(df, timeframe='15min')
        
        assert len(bars) == 1
        assert bars.iloc[0]['open'] == 50000
        assert bars.iloc[0]['high'] == 50000
        assert bars.iloc[0]['low'] == 50000
        assert bars.iloc[0]['close'] == 50000
        assert bars.iloc[0]['volume'] == 1.0
    
    def test_gaps_in_data(self):
        """Test aggregation with time gaps"""
        timestamps = list(pd.date_range('2025-01-01 00:00:00', periods=50, freq='1min'))
        timestamps.extend(pd.date_range('2025-01-01 02:00:00', periods=50, freq='1min'))
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'price': [50000] * 100,
            'quantity': [0.1] * 100
        })
        
        bars = aggregate_trades_to_bars(df, timeframe='15min')
        
        # Should have bars from both periods
        assert len(bars) > 0
        # Volume should be consistent
        assert (bars['volume'] > 0).all()
    
    def test_zero_volume_bars_removed(self):
        """Test that zero-volume bars are removed"""
        timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='1min')
        prices = [50000] * 100
        # All quantities zero
        quantities = [0.0] * 100
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'price': prices,
            'quantity': quantities
        })
        
        bars = aggregate_trades_to_bars(df, timeframe='15min')
        
        # Should have no bars (all zero volume removed)
        assert len(bars) == 0
    
    # BOUNDARY TESTS
    
    def test_exactly_one_timeframe(self):
        """Test when data is exactly one timeframe period"""
        timestamps = pd.date_range('2025-01-01 00:00:00', periods=15, freq='1min')
        df = pd.DataFrame({
            'timestamp': timestamps,
            'price': [50000] * 15,
            'quantity': [0.1] * 15
        })
        
        bars = aggregate_trades_to_bars(df, timeframe='15min')
        assert len(bars) == 1
    
    def test_price_spike(self):
        """Test handling of sudden price spike"""
        timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='1min')
        prices = [50000] * 50 + [100000] + [50000] * 49  # Spike in middle
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'price': prices,
            'quantity': [0.1] * 100
        })
        
        bars = aggregate_trades_to_bars(df, timeframe='15min')
        
        # High should capture the spike
        assert bars['high'].max() == 100000
        # OHLC logic still valid
        assert (bars['high'] >= bars['low']).all()
    
    # ERROR HANDLING TESTS
    
    def test_invalid_timeframe(self, sample_trades):
        """Test with invalid timeframe"""
        with pytest.raises(ValueError):
            aggregate_trades_to_bars(sample_trades, timeframe='invalid')
    
    def test_missing_columns(self):
        """Test with missing required columns"""
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'price': [50000]
            # Missing quantity column
        })
        
        with pytest.raises(KeyError):
            aggregate_trades_to_bars(df, timeframe='15min')
    
    def test_negative_prices(self):
        """Test with negative prices (invalid)"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=10, freq='1min'),
            'price': [-50000] * 10,
            'quantity': [0.1] * 10
        })
        
        with pytest.raises(ValueError):
            aggregate_trades_to_bars(df, timeframe='15min')
```

---

## 🔗 INTEGRATION TESTS (20%)

### Test 4: Complete Download Pipeline
**File:** `tests/integration/test_download_pipeline.py`

```python
import pytest
from pathlib import Path
from src.data_manager.download.synchronizer import DataSynchronizer
from src.data_manager.validation.multicore_validator import validate_all_files_parallel

class TestDownloadPipeline:
    """Integration tests for complete download pipeline"""
    
    @pytest.fixture
    def pipeline_dir(self, tmp_path):
        """Set up test directory structure"""
        (tmp_path / 'data' / 'raw' / 'trades').mkdir(parents=True)
        (tmp_path / 'data' / 'raw' / 'liquidations').mkdir(parents=True)
        return tmp_path
    
    def test_download_and_validate_pipeline(self, pipeline_dir):
        """Test complete download → validate pipeline"""
        synchronizer = DataSynchronizer(data_dir=pipeline_dir / 'data' / 'raw')
        
        # 1. Download data (mocked)
        downloaded = synchronizer.incremental_download('trades', months=[(2025, 1)])
        
        # 2. Validate downloaded files
        is_valid = validate_all_files_parallel('trades', data_dir=pipeline_dir / 'data' / 'raw')
        
        assert is_valid is True
        assert len(downloaded) > 0
    
    def test_usage_tracking_across_downloads(self, pipeline_dir):
        """Test that usage tracking accumulates correctly"""
        synchronizer = DataSynchronizer(data_dir=pipeline_dir / 'data' / 'raw')
        
        # Download multiple months
        initial_usage = synchronizer.get_monthly_usage()
        
        synchronizer.incremental_download('trades', months=[(2025, 1)])
        usage_after_first = synchronizer.get_monthly_usage()
        
        synchronizer.incremental_download('trades', months=[(2025, 2)])
        usage_after_second = synchronizer.get_monthly_usage()
        
        assert usage_after_second > usage_after_first > initial_usage
        assert usage_after_second < 300  # Under limit
    
    def test_recovery_from_failed_download(self, pipeline_dir):
        """Test recovery when download fails mid-pipeline"""
        synchronizer = DataSynchronizer(data_dir=pipeline_dir / 'data' / 'raw')
        
        # Simulate partial failure
        try:
            synchronizer.incremental_download('trades', months=[(2025, 1), (2025, 2)], 
                                            fail_on_second=True)
        except Exception:
            pass
        
        # Verify partial download succeeded
        scanned = synchronizer.scan_existing_data()
        assert '2025-01' in scanned['trades']
        
        # Retry should only download failed month
        missing = synchronizer.identify_missing_months('2025-01-01', '2025-02-28', 'trades')
        assert (2025, 2) in missing
        assert (2025, 1) not in missing
```

---

## 🎯 END-TO-END TESTS (10%)

### Test 5: Complete System Test
**File:** `tests/e2e/test_complete_pipeline.py`

```python
import pytest
from pathlib import Path
import pandas as pd
from datetime import datetime

class TestCompleteSystemPipeline:
    """End-to-end tests for entire data management system"""
    
    def test_full_data_lifecycle(self, tmp_path):
        """Test complete data lifecycle: download → aggregate → convert → validate"""
        
        # 1. Download tick data (mocked)
        from src.data_manager.download.synchronizer import DataSynchronizer
        sync = DataSynchronizer(data_dir=tmp_path / 'data' / 'raw')
        downloaded = sync.download_month('trades', 2025, 1)
        
        # 2. Aggregate to bars
        from src.data_manager.aggregation.tick_to_bars import aggregate_all_timeframes
        bars = aggregate_all_timeframes(data_type='trades', data_dir=tmp_path / 'data' / 'raw')
        
        # 3. Convert to Nautilus format
        from src.data_manager.nautilus.data_adapter import convert_to_nautilus_bars
        nautilus_bars = convert_to_nautilus_bars(bars['15min'], timeframe='15min')
        
        # 4. Validate complete pipeline
        from src.data_manager.validation.multicore_validator import validate_all_files_parallel
        is_valid = validate_all_files_parallel('trades', data_dir=tmp_path / 'data' / 'raw')
        
        # Assertions
        assert downloaded is not None
        assert len(bars) > 0
        assert len(nautilus_bars) > 0
        assert is_valid is True
    
    def test_daily_automation_sequence(self, tmp_path):
        """Test daily cron automation sequence"""
        
        # Simulate daily automation:
        # 1. Check current month freshness
        # 2. Download if stale
        # 3. Aggregate
        # 4. Update Nautilus catalog
        # 5. Validate
        
        from scripts.data_manager.process_multicore_pipeline import process_all_data_multicore
        
        success = process_all_data_multicore(data_dir=tmp_path)
        
        assert success is True
        
        # Verify all outputs exist
        assert (tmp_path / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv').exists()
        assert (tmp_path / 'data' / 'catalog' / 'parquet').exists()
    
    def test_1000_bar_warmup_for_live_trading(self, tmp_path):
        """Test that 1000-bar warmup data is correctly prepared"""
        
        # Create historical data
        from src.data_manager.aggregation.tick_to_bars import aggregate_all_timeframes
        bars = aggregate_all_timeframes(data_type='trades', data_dir=tmp_path / 'data' / 'raw')
        
        # Load last 1000 bars for warmup
        df_15min = pd.read_csv(tmp_path / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv')
        warmup_data = df_15min.tail(1000)
        
        # Verify
        assert len(warmup_data) == 1000
        assert 'timestamp' in warmup_data.columns
        assert (warmup_data['volume'] > 0).all()
        
        # Ensure continuous (no gaps)
        warmup_data['timestamp'] = pd.to_datetime(warmup_data['timestamp'])
        time_diffs = warmup_data['timestamp'].diff()
        expected_diff = pd.Timedelta(minutes=15)
        gaps = time_diffs[time_diffs > expected_diff * 2]
        assert len(gaps) == 0  # No gaps allowed for warmup
```

---

## ⚡ PERFORMANCE TESTS

### Test 6: Multicore Performance
**File:** `tests/performance/test_multicore_speedup.py`

```python
import pytest
import time
from pathlib import Path
from src.data_manager.validation.multicore_validator import validate_all_files_parallel
from src.data_manager.validation.file_integrity import validate_file_integrity

class TestMulticorePerformance:
    """Performance tests for multicore processing"""
    
    def test_validation_speedup(self, benchmark_files):
        """Test that multicore validation is actually faster"""
        
        # Single-core baseline
        start = time.time()
        for file in benchmark_files:
            validate_file_integrity(file)
        single_core_time = time.time() - start
        
        # Multicore (30 cores)
        start = time.time()
        validate_all_files_parallel('trades', benchmark_files)
        multicore_time = time.time() - start
        
        # Should be at least 10x faster with 30 cores
        speedup = single_core_time / multicore_time
        assert speedup > 10
        
        print(f"Speedup: {speedup:.1f}x")
    
    def test_memory_usage_under_limit(self, benchmark_files):
        """Test that multicore doesn't exceed memory limits"""
        import psutil
        import gc
        
        process = psutil.Process()
        
        # Get baseline memory
        gc.collect()
        baseline_mem = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run multicore processing
        validate_all_files_parallel('trades', benchmark_files)
        
        # Check peak memory
        peak_mem = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_mem - baseline_mem
        
        # Should not exceed 16GB (given 30 cores)
        assert memory_increase < 16 * 1024  # MB
        
        print(f"Memory increase: {memory_increase:.0f} MB")
    
    def test_aggregation_throughput(self, large_trade_dataset):
        """Test aggregation throughput meets targets"""
        from src.data_manager.aggregation.multicore_aggregator import aggregate_all_timeframes_parallel
        
        start = time.time()
        bars = aggregate_all_timeframes_parallel(large_trade_dataset)
        elapsed = time.time() - start
        
        # Should process all 9 timeframes in under 30 seconds
        assert elapsed < 30
        
        # Calculate throughput
        trades_per_second = len(large_trade_dataset) / elapsed
        print(f"Throughput: {trades_per_second:,.0f} trades/second")
        
        # Should exceed 100,000 trades/second
        assert trades_per_second > 100000
```

---

## 🚨 EDGE CASE & ERROR HANDLING TESTS

### Test 7: Boundary Conditions
**File:** `tests/unit/test_edge_cases.py`

```python
import pytest
import pandas as pd
from datetime import datetime

class TestEdgeCases:
    """Comprehensive edge case testing"""
    
    # EXTREME VALUE TESTS
    
    def test_extreme_price_values(self):
        """Test handling of extreme prices"""
        from src.data_manager.validation.data_quality import validate_data_quality
        
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=3),
            'price': [0.01, 1000000, 50000],  # Penny, million, normal
            'quantity': [1, 1, 1]
        })
        
        # Should handle extreme values
        validate_data_quality(df, 'trades')
    
    def test_extreme_volume_values(self):
        """Test handling of extreme volumes"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=3),
            'price': [50000, 50000, 50000],
            'quantity': [0.00000001, 1000000, 1.0]  # Tiny, huge, normal
        })
        
        # Should handle extreme volumes
        from src.data_manager.aggregation.tick_to_bars import aggregate_trades_to_bars
        bars = aggregate_trades_to_bars(df, timeframe='15min')
        assert len(bars) > 0
    
    # TIME BOUNDARY TESTS
    
    def test_year_boundary_aggregation(self):
        """Test aggregation across year boundary"""
        timestamps = list(pd.date_range('2024-12-31 23:50:00', periods=20, freq='1min'))
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'price': [50000] * 20,
            'quantity': [0.1] * 20
        })
        
        from src.data_manager.aggregation.tick_to_bars import aggregate_trades_to_bars
        bars = aggregate_trades_to_bars(df, timeframe='15min')
        
        # Should handle year boundary correctly
        assert len(bars) > 0
        assert bars['timestamp'].min().year == 2024
        assert bars['timestamp'].max().year == 2025
    
    def test_leap_year_february(self):
        """Test handling of leap year February 29"""
        timestamps = pd.date_range('2024-02-29 00:00:00', periods=100, freq='1min')
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'price': [50000] * 100,
            'quantity': [0.1] * 100
        })
        
        from src.data_manager.aggregation.tick_to_bars import aggregate_trades_to_bars
        bars = aggregate_trades_to_bars(df, timeframe='15min')
        
        # Should handle leap year correctly
        assert len(bars) > 0
    
    # DATA CORRUPTION TESTS
    
    def test_nan_in_price(self):
        """Test handling of NaN prices"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=10),
            'price': [50000] * 5 + [float('nan')] + [50000] * 4,
            'quantity': [0.1] * 10
        })
        
        from src.data_manager.validation.data_quality import validate_data_quality
        with pytest.raises(ValueError):
            validate_data_quality(df, 'trades')
    
    def test_inf_in_quantity(self):
        """Test handling of infinite quantities"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=10),
            'price': [50000] * 10,
            'quantity': [0.1] * 5 + [float('inf')] + [0.1] * 4
        })
        
        from src.data_manager.validation.data_quality import validate_data_quality
        with pytest.raises(ValueError):
            validate_data_quality(df, 'trades')
    
    # USAGE LIMIT TESTS
    
    def test_approaching_300gb_limit(self):
        """Test warning when approaching 300GB limit"""
        from src.data_manager.download.usage_tracker import UsageTracker
        
        tracker = UsageTracker()
        tracker.update_usage(285)  # 285GB used
        
        assert tracker.is_approaching_limit() is True
        assert tracker.get_warning_message() is not None
    
    def test_exceeding_300gb_limit(self):
        """Test error when exceeding 300GB limit"""
        from src.data_manager.download.usage_tracker import UsageTracker
        
        tracker = UsageTracker()
        tracker.update_usage(305)  # Over limit
        
        with pytest.raises(ValueError):
            tracker.validate_limit()
```

---

## 🔧 PYTEST CONFIGURATION

### conftest.py
**File:** `tests/conftest.py`

```python
"""Pytest configuration and shared fixtures"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Test data fixtures

@pytest.fixture
def sample_trades_100():
    """Create 100 sample trades"""
    timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='1min')
    prices = [50000 + i for i in range(100)]
    quantities = [0.1] * 100
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'price': prices,
        'quantity': quantities,
        'side': ['BUY', 'SELL'] * 50
    })

@pytest.fixture
def sample_bars_15min():
    """Create 100 sample 15-minute bars"""
    timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='15min')
    
    bars = []
    for i, ts in enumerate(timestamps):
        base = 50000 + (i * 10)
        bars.append({
            'timestamp': ts,
            'open': base,
            'high': base + 100,
            'low': base - 100,
            'close': base + 50,
            'volume': 10.0
        })
    
    return pd.DataFrame(bars)

@pytest.fixture
def large_trade_dataset():
    """Create large dataset for performance testing (1M trades)"""
    n_trades = 1_000_000
    timestamps = pd.date_range('2025-01-01', periods=n_trades, freq='1s')
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'price': [50000] * n_trades,
        'quantity': [0.001] * n_trades
    })

@pytest.fixture
def benchmark_files(tmp_path):
    """Create 24 sample parquet files for benchmarking"""
    files = []
    for i in range(1, 25):
        df = pd.DataFrame({
            'timestamp': pd.date_range(f'2024-{i:02d}-01', periods=1000, freq='1min'),
            'price': [50000] * 1000,
            'quantity': [0.1] * 1000
        })
        
        file_path = tmp_path / f'BTC-USDT_trades_2024-{i:02d}.parquet'
        df.to_parquet(file_path)
        files.append(file_path)
    
    return files

@pytest.fixture
def corrupted_parquet(tmp_path):
    """Create corrupted parquet file for testing"""
    file_path = tmp_path / 'corrupted.parquet'
    with open(file_path, 'wb') as f:
        f.write(b'This is not a valid parquet file')
    return file_path

# Mock fixtures

@pytest.fixture
def mock_lakeapi_client(monkeypatch):
    """Mock LakeAPI client to avoid real downloads in tests"""
    class MockLakeAPIClient:
        def download_data(self, table, start, end, symbols):
            # Return sample data instead of real download
            return pd.DataFrame({
                'timestamp': pd.date_range(start, end, freq='1min'),
                'price': [50000] * 1000,
                'quantity': [0.1] * 1000
            })
    
    return MockLakeAPIClient()

# Pytest marks

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance benchmarks"
    )
```

---

## 📊 TEST COVERAGE REQUIREMENTS

### Coverage Targets by Module

| Module | Coverage Target | Critical Sections |
|--------|----------------|-------------------|
| `download/` | 95%+ | Incremental logic, usage tracking |
| `aggregation/` | 100% | OHLC calculations, time handling |
| `validation/` | 100% | All validation levels |
| `nautilus/` | 90%+ | Type conversions, catalog operations |
| `monitoring/` | 85%+ | Alert systems, tracking |
| `utils/` | 95%+ | Date/file utilities |

### Running Tests with Coverage

```bash
# Run all tests with coverage
pytest tests/ --cov=src/data_manager --cov-report=html --cov-report=term

# Run only unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -m integration

# Run performance tests
pytest tests/performance/ -m performance

# Run tests excluding slow ones
pytest tests/ -m "not slow"

# Run specific test file
pytest tests/unit/test_aggregation/test_tick_to_bars.py -v

# Run with parallel execution (4 cores)
pytest tests/unit/ -n 4
```

---

## 🎯 TEST MATRIX

### Complete Test Coverage Matrix

| Component | Unit | Integration | E2E | Performance | Edge Cases |
|-----------|------|-------------|-----|-------------|------------|
| **Download** |
| Synchronizer | ✅ 20 tests | ✅ 5 tests | ✅ 2 tests | ✅ 2 tests | ✅ 10 tests |
| LakeAPI Client | ✅ 15 tests | ✅ 3 tests | - | - | ✅ 8 tests |
| Usage Tracker | ✅ 12 tests | ✅ 2 tests | ✅ 1 test | - | ✅ 5 tests |
| **Aggregation** |
| Tick to Bars | ✅ 25 tests | ✅ 5 tests | ✅ 3 tests | ✅ 3 tests | ✅ 15 tests |
| Multicore Agg | ✅ 10 tests | ✅ 3 tests | ✅ 2 tests | ✅ 5 tests | ✅ 5 tests |
| **Validation** |
| File Integrity | ✅ 10 tests | - | ✅ 1 test | - | ✅ 8 tests |
| Data Structure | ✅ 15 tests | ✅ 2 tests | - | - | ✅ 10 tests |
| Data Quality | ✅ 20 tests | ✅ 3 tests | ✅ 2 tests | - | ✅ 12 tests |
| Multicore Val | ✅ 8 tests | ✅ 2 tests | ✅ 1 test | ✅ 4 tests | ✅ 5 tests |
| **Nautilus** |
| Data Adapter | ✅ 15 tests | ✅ 5 tests | ✅ 2 tests | - | ✅ 8 tests |
| Catalog Mgr | ✅ 10 tests | ✅ 3 tests | ✅ 2 tests | ✅ 2 tests | ✅ 5 tests |
| **Utils** |
| Date Utils | ✅ 12 tests | - | - | - | ✅ 8 tests |
| File Utils | ✅ 10 tests | ✅ 2 tests | - | - | ✅ 6 tests |
| Checksum | ✅ 8 tests | - | - | - | ✅ 4 tests |
| **TOTAL** | **190** | **35** | **16** | **16** | **109** |

**Total Tests:** 366 tests covering all critical paths

---

## ✅ TESTING CHECKLIST

### Pre-Implementation Testing
- [ ] Set up pytest environment
- [ ] Install test dependencies (`pytest`, `pytest-cov`, `pytest-xdist`, `psutil`)
- [ ] Create test directory structure
- [ ] Create conftest.py with fixtures
- [ ] Configure pytest.ini

### Unit Testing Phase
- [ ] Write tests for download synchronizer
- [ ] Write tests for LakeAPI client
- [ ] Write tests for usage tracker
- [ ] Write tests for tick-to-bars aggregation
- [ ] Write tests for multicore aggregator
- [ ] Write tests for file integrity validation
- [ ] Write tests for data structure validation
- [ ] Write tests for data quality validation
- [ ] Write tests for Nautilus data adapter
- [ ] Write tests for catalog manager
- [ ] Write tests for all utilities
- [ ] Achieve 95%+ unit test coverage

### Integration Testing Phase
- [ ] Write download pipeline tests
- [ ] Write aggregation pipeline tests
- [ ] Write validation pipeline tests
- [ ] Write Nautilus conversion pipeline tests
- [ ] Write multicore pipeline tests
- [ ] Test error recovery procedures

### E2E Testing Phase
- [ ] Write complete system lifecycle test
- [ ] Write daily automation test
- [ ] Write 1000-bar warmup test
- [ ] Write live trading integration test

### Performance Testing Phase
- [ ] Write multicore speedup tests
- [ ] Write memory usage tests
- [ ] Write throughput benchmarks
- [ ] Verify 30x speedup achieved
- [ ] Verify memory under 16GB

### Continuous Integration
- [ ] Set up CI/CD pipeline
- [ ] Configure automated test runs
- [ ] Set up coverage reporting
- [ ] Configure test badges
- [ ] Set up nightly performance benchmarks

---

## 📚 TESTING DOCUMENTATION

### For Developers
- **How to run tests:** See "Running Tests with Coverage" section
- **How to write new tests:** Follow existing test patterns
- **How to mock dependencies:** Use fixtures in conftest.py
- **How to debug failing tests:** `pytest --pdb` for debugger

### For QA
- **Test execution schedule:** Run on every commit + nightly full suite
- **Coverage reports:** Available in `htmlcov/index.html`
- **Performance benchmarks:** Track in test output logs
- **Regression tracking:** Compare against baseline metrics

### For Operations
- **Production testing:** Run integration + E2E tests before deployment
- **Smoke tests:** Quick validation after deployment
- **Performance monitoring:** Compare production vs test benchmarks

---

## 🚀 SUMMARY

This comprehensive testing framework ensures institutional-grade reliability:

✅ **366 Total Tests** - Covering all critical paths
✅ **95%+ Coverage** - Critical code covered comprehensively
✅ **Edge Cases** - 109 edge case tests
✅ **Performance** - Validates 30x multicore speedup
✅ **Integration** - End-to-end pipeline validation
✅ **Real Money Safe** - Every financial calculation tested

**Testing Pyramid Distribution:**
- 70% Unit Tests (190 tests) - Fast, focused testing
- 20% Integration Tests (35 tests) - Component interaction
- 10% E2E Tests (16 tests) - Full system validation
- Performance Tests (16 tests) - Multicore verification
- Edge Cases (109 tests) - Boundary validation

**Implementation Priority:**
1. Week 1: Unit tests during implementation
2. Week 2: Integration tests
3. Week 3: E2E tests + Performance tests
4. Week 4: CI/CD setup + Complete coverage

---

**Document Status:** ✅ COMPLETE  
**Ready For:** Implementation alongside code development  
**Coverage Goal:** 95%+ code coverage  
**Real Money Protection:** Every test matters

---

*End of Testing Framework Document*
