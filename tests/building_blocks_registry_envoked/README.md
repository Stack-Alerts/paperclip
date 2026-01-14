# Building Block Registry Test Suite
**83 Individual Test Scripts for All Building Blocks**

## Overview

This directory contains **83 individual test scripts**, one for each building block registered in the BlockRegistry. Each test script validates that its building block:

- ✅ Can be instantiated via the BlockRegistry
- ✅ Tests all valid_signals defined in the registry
- ✅ Runs 180-day walkforward testing (candle-by-candle, NO sampling)
- ✅ Uses multicore processing for efficiency
- ✅ Reports detailed signal statistics with start/end times
- ✅ Generates both JSON reports and CSV files with all signals

## Architecture

### Core Components

1. **`registry_test_library.py`** - Reusable test framework
   - Provides `test_building_block_registry()` function
   - Handles all test logic, data loading, multicore processing
   - Generates reports and validates signals

2. **`test_01_*.py` through `test_83_*.py`** - Individual test files
   - Each file tests one specific building block
   - Simple wrapper calling the library function
   - Can be run independently

3. **`generate_all_test_files.py`** - Generator script
   - Creates all 83 test files from the registry
   - Only needs to be run once (already executed)

## Test Files

All 83 building blocks have test files:

```
test_01_adaptive_momentum_oscillator.py
test_02_adr.py
test_03_adx.py
test_04_anchored_vwap.py
test_05_ascending_triangle.py
test_06_asfx_a2_vwap.py
test_07_asia_session_50_percent.py
test_08_atr.py
test_09_balanced_price_range.py
test_10_bollinger_bands.py
... (73 more) ...
test_81_wyckoff_accumulation.py
test_82_wyckoff_distribution.py
test_83_wyckoff_reaccumulation.py
```

## Usage

### Run a Single Test

Test with default settings (180 days, multicore enabled):
```bash
python test_37_hod.py
```

Test with custom settings:
```bash
python test_37_hod.py --days 30 --no-multicore
```

### Run Multiple Tests

Test several building blocks sequentially:
```bash
for test in test_37_hod.py test_50_lod.py test_79_vwap.py; do
    python $test --days 30
done
```

### Run All Tests

Test all 83 building blocks (will take time):
```bash
for test in test_*.py; do
    echo "Running $test..."
    python $test || echo "FAILED: $test"
done
```

## Test Parameters

Each test script accepts:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--days` | 180 | Test period in days |
| `--no-multicore` | False | Disable multicore processing |

## Test Output

### Console Output

```
================================================================================
REGISTRY-BASED BUILDING BLOCK TEST
================================================================================
Block: hod
Start Time: 2026-01-14 09:31:19
================================================================================

📋 Block Metadata:
   Category: PRICE_LEVELS
   Class: HOD
   Valid Signals: ['BEARISH', 'BULLISH', 'NEUTRAL', ...]

📊 Loading 30 days of BTC 15min data...
   Loaded 2881 candles

🔬 Test Configuration:
   Test candles: 2781
   Method: EXPANDING window (candle-by-candle)
   Multicore: ENABLED

⚡ Multicore Processing:
   Workers: 31
   Batch size: ~89 candles/worker

================================================================================
TEST RESULTS
================================================================================
Duration: 1.02 seconds
Processing Speed: 2740 candles/second

📊 Signal Statistics:
   Total results: 2781
   Unique signals found: 3
   
🎯 Valid Signals Coverage:
   Expected: 8 signals
   Found: 3 signals
   Coverage: 37.5%

📈 Signal Distribution:
   [✓] NEUTRAL: 2736 (98.4%)
   [✓] BEARISH: 39 (1.4%)
   [✓] BULLISH: 6 (0.2%)

✅ Report saved: data/reports/registry_tests/test_hod.json
✅ Signals CSV saved: data/reports/registry_tests/test_hod_signals.csv
```

### Generated Files

For each test, two files are generated in `data/reports/registry_tests/`:

1. **JSON Report** (`test_{block_name}.json`)
   - Complete test metadata
   - Block metadata from registry
   - Signal counts and coverage
   - Test duration and performance metrics

2. **Signals CSV** (`test_{block_name}_signals.csv`)
   - Every signal generated during the test
   - Includes timestamps, confidence, metadata
   - Can be analyzed for patterns

## Report Structure

### JSON Report

```json
{
  "block_name": "hod",
  "test_info": {
    "start_time": "2026-01-14T09:31:19",
    "end_time": "2026-01-14T09:31:20",
    "duration_seconds": 1.02,
    "multicore": false
  },
  "data_info": {
    "test_days": 30,
    "total_candles": 2881,
    "test_candles": 2781
  },
  "block_metadata": {
    "category": "PRICE_LEVELS",
    "class_name": "HOD",
    "valid_signals": ["BEARISH", "BULLISH", "NEUTRAL", ...]
  },
  "results": {
    "total_results": 2781,
    "signal_counts": {
      "NEUTRAL": 2736,
      "BEARISH": 39,
      "BULLISH": 6
    },
    "signals_per_day": 92.70
  },
  "coverage": {
    "expected_signals": ["BEARISH", "BULLISH", ...],
    "found_signals": ["NEUTRAL", "BEARISH", "BULLISH"],
    "missing_signals": ["ABOVE_HOD", "AT_HOD", ...],
    "coverage_pct": 37.5
  }
}
```

### Signals CSV

| Column | Description |
|--------|-------------|
| signal | Signal name (e.g., BULLISH, BEARISH) |
| confidence | Confidence score (0-100) |
| timestamp | When signal occurred |
| bar_index | Candle index in test |
| timeframe | Timeframe (15min) |
| ...metadata... | Additional metadata fields |

## Key Features

### ✅ Registry-Based

- Uses `BlockRegistry.instantiate()` to create blocks
- Validates against `valid_signals` from registry
- Reports coverage of expected vs found signals

### ✅ Candle-by-Candle Testing

- NO sampling - tests EVERY candle
- Uses EXPANDING window (full history)
- Realistic walkforward simulation

### ✅ Multicore Processing

- Automatically uses all CPU cores
- Processes batches in parallel
- Fallback to single-core if needed
- ~30x faster for 180-day tests

### ✅ Comprehensive Reports

- Start time / end time tracked
- Signal distribution with percentages
- Coverage analysis (which signals found/missing)
- Performance metrics (candles/second)
- Both JSON and CSV outputs

### ✅ Error Handling

- Gracefully handles blocks without `timeframe` parameter
- Reports instantiation failures
- Tracks errors per candle
- Provides sample error messages

## Performance

Typical performance (30-day test, multicore):
- **Simple blocks** (HOD, LOD): 1-2 seconds
- **Medium blocks** (EMA, RSI): 5-15 seconds  
- **Complex blocks** (Patterns): 30-60 seconds

180-day test scales approximately 6x longer.

## Validation Checklist

For each building block, the test verifies:

- [x] Block can be instantiated from registry
- [x] Block returns valid dict results
- [x] All returned signals are in `valid_signals`
- [x] Signal coverage is tracked
- [x] Confidence scores are present
- [x] Timestamps are included
- [x] Metadata is populated
- [x] No critical errors during processing

## Troubleshooting

### Block instantiation fails

Some blocks may have incorrect registry metadata (wrong `class_name`). The test library handles this gracefully and reports the error.

### Missing signals

If a test shows missing signals, it means those signals didn't occur in the test period. This is normal - not all signals occur every day (e.g., rare patterns).

### Slow performance

For 180-day tests on complex blocks:
- Use multicore (default)
- Reduce to 30-90 days for faster testing
- Check CPU usage during test

## Regenerating Test Files

If you add new building blocks to the registry:

```bash
python generate_all_test_files.py
```

This will regenerate all 83 test files based on current registry.

## Integration with CI/CD

These tests can be integrated into automated testing:

```bash
# Test all blocks
python -m pytest test_*.py -v

# Test specific category
python -m pytest test_37_hod.py test_50_lod.py -v
```

## Summary

- **83 building blocks** = **83 test files**
- **Each test** runs independently
- **Reports** verify signal coverage
- **Multicore** for fast execution
- **Registry-driven** for accuracy

All building blocks are now testable individually to ensure they work correctly and emit all expected signals.

---

**Created:** 2026-01-14  
**Author:** BTC_Engine_v3 - Registry Test Suite  
**Version:** 1.0
