# Complete Asset Inventory - V3 Migration
## Comprehensive Codebase Audit Results

**Date:** December 30, 2025  
**Audit Date:** December 30, 2025 09:13 AM  
**Status:** Final Preservation Plan  
**Priority:** MAXIMUM - Zero Asset Loss Policy

---

## Executive Summary

**Total Assets Identified:**
- CRITICAL: 32 files + 308GB data
- HIGH VALUE: 115 files
- REFERENCE: 57+ documentation files
- **Grand Total: ~200+ files + data to preserve**

---

## CRITICAL ASSETS (✅ MUST MIGRATE - Zero Tolerance for Loss)

### 1. Historical Data (308GB - $100K+ Value)

**Location:** `data/raw/` (20 files detected)

```
data/raw/
├── BTC_USDT_PERP_*.pkl          # Multi-timeframe futures data
├── BTC_USDT_PERP_*.csv          # CSV exports
├── download_summary.txt         # Data acquisition logs
├── btc_usdt_*m.parquet          # OHLCV all timeframes (100GB)
├── orderbook_*.parquet          # Orderbook snapshots (200GB) - RARE DATA
├── funding_*.parquet            # Funding rates (1GB)
├── liquidations_*.parquet       # Liquidation events (5GB)
└── open_interest_*.parquet      # OI data (2GB)
```

**V3 Action:** 
- [ ] Create data integrity checksums BEFORE migration
- [ ] Symlink or rsync to V3 (DO NOT MOVE - keep V2 backup)
- [ ] Verify all 20 files accessible in V3
- [ ] Test VectorBT data loading

---

### 2. Trained ML Models & Statistics

**Location:** `data/models/` (2+ directories)

```
data/models/
├── pattern_statistics/
│   ├── m_pattern_stats_v2.pkl        # ✅ CRITICAL - M-pattern statistics
│   └── w_pattern_stats_v2.pkl        # ✅ CRITICAL - W-pattern statistics
├── cnn_lstm/                          # Deep learning models
├── xgboost/                           # XGBoost models
├── layer05_ml*/                       # Layer 0.5 models
├── model_metrics.json                 # Model performance tracking
└── .gitkeep
```

**V3 Action:**
- [ ] Migrate all pattern statistics (required by detectors)
- [ ] Archive ML models (may retrain in V3)
- [ ] Preserve model_metrics.json for comparison

---

### 3. Sophisticated Pattern Detectors (Core IP)

**Location:** `src/layers/tbd_v2/` (10 files)

```
src/layers/tbd_v2/
├── __init__.py
├── base_tbd_pattern.py              # ✅ Base class
├── m_pattern_layer.py               # ✅ Legacy M-pattern
├── w_pattern_layer.py               # ✅ Legacy W-pattern
├── sophisticated_m_pattern_layer.py # ✅ CRITICAL - Production M-pattern
├── sophisticated_w_pattern_layer.py # ✅ CRITICAL - Production W-pattern
└── detectors/
    ├── __init__.py
    ├── zigzag_detector.py           # ✅ Pivot detection logic
    ├── oscillators.py               # ✅ RSI, Stochastic
    ├── divergence_detector.py       # ✅ Divergence analysis
    └── pattern_statistics.py        # ✅ Statistical validation
```

**V3 Action:**
- [ ] Extract to framework-agnostic `indicators/pattern_detector.py`
- [ ] Preserve ALL detector logic
- [ ] Remove backtest_engine dependencies
- [ ] Create comprehensive unit tests

---

## HIGH VALUE ASSETS (⭐ STRONGLY RECOMMENDED TO KEEP)

### 4. Core Utilities (src/utils - 8 files)

```
src/utils/
├── logger.py                    # ⭐ Logging system
├── constants.py                 # ⭐ Global constants
├── error_handler.py             # ⭐ Error management
├── fibonacci_calculator.py      # ⭐ Fib calculations (used in patterns)
├── multiprocessing_utils.py     # ⭐ Parallel processing
├── crypto-lake-test.py          # Testing utilities
├── download_all_binance_futures.py
└── __init__.py
```

**V3 Action:**
- [x] ✅ fibonacci_calculator.py → Migrate (used by patterns)
- [x] ✅ logger.py → Evaluate (may use loguru instead)
- [x] ✅ constants.py → Merge into V3 config
- [x] ✅ error_handler.py → Migrate
- [x] ✅ multiprocessing_utils.py → Evaluate (VectorBT has parallel)

---

### 5. Trading Infrastructure (src/trading - 5 files)

```
src/trading/
├── risk_manager.py              # ⭐ Position sizing, risk limits
├── order_manager.py             # ⭐ Order execution logic
├── fee_calculator.py            # ⭐ Commission calculations
├── signal_generator.py          # ⭐ Signal conversion
└── __init__.py
```

**V3 Action:**
- [x] ⚠️ risk_manager.py → REFERENCE (PFund has built-in risk)
- [x] ⚠️ order_manager.py → REFERENCE (PFund handles orders)
- [x] ✅ fee_calculator.py → Migrate (accurate fee modeling critical)
- [x] ⚠️ signal_generator.py → REFERENCE (rewrite for PFund)

**Critical Functions to Extract:**
- Position sizing formulas
- Fee calculation logic (Binance maker/taker)
- Risk constraint algorithms

---

### 6. Core Framework (src/core - 12 files)

```
src/core/
├── indicator_engine.py          # ⭐ Technical indicator calculations
├── data_pipeline.py             # ⭐ Data loading & preprocessing
├── signal_generator.py          # Signal generation
├── synchronization.py           # Time sync utilities
├── multi_timeframe_sync.py      # ⭐ MTF alignment (critical for patterns)
├── framework/
│   ├── base_layer.py            # Base layer interface
│   ├── base_strategy.py         # Base strategy interface
│   ├── layer_factory.py         # Layer instantiation
│   ├── strategy_factory.py      # Strategy instantiation
│   └── plugin_manager.py        # Plugin system
└── __init__.py
```

**V3 Action:**
- [x] ✅ indicator_engine.py → Evaluate (may use TA-Lib + pandas-ta)
- [x] ✅ data_pipeline.py → **MIGRATE** (proven data loading logic)
- [x] ✅ multi_timeframe_sync.py → **MIGRATE** (critical for patterns)
- [x] ⚠️ framework/* → REFERENCE (replaced by PFund/VectorBT)

**Critical to Preserve:**
- MTF synchronization algorithms
- Data preprocessing pipelines
- Indicator calculation optimizations

---

### 7. Data Download Scripts (scripts/data_download - 5 files)

```
scripts/data_download/
├── download_liquidations_funding_oi.py  # ⭐ Binance data downloader
├── download_cryptolake_orderbook.py     # ⭐ LakeAPI orderbook
├── download_with_lakeapi_chunked.py     # ⭐ LakeAPI OHLCV (chunked)
├── restore_2022_data.py                 # Data restoration utility
└── (+ LakeAPI scanner.py)               # See LAKEAPI_ASSET_INVENTORY.md
```

**V3 Action:**
- [x] ✅ ALL files → **MIGRATE** to `scripts/data_download/`
- [x] ✅ Preserve Binance API integrations
- [x] ✅ LakeAPI scripts → See separate inventory document

---

### 8. Feature Extraction Pipelines (scripts/feature_extraction - 4 files)

```
scripts/feature_extraction/
├── extract_institutional_orderbook_features_chunked.py  # ⭐ Orderbook features
├── extract_institutional_orderbook_features.py          # Original version
├── extract_features_5cores.py                           # ⭐ Parallel extraction
└── (others)
```

**V3 Action:**
- [x] ⚠️ **EVALUATE** - May not need in V3 (VectorBT = raw OHLCV)
- [x] ✅ **PRESERVE** orderbook feature extraction (rare data)
- [x] ⚠️ Archive heavy ML feature pipelines (may not use ML in V3)

**Decision Criteria:**
- If patterns need orderbook features → Migrate
- If only OHLCV + pattern detection → Archive

---

### 9. ML Training Scripts (scripts/ml_training - 21 files)

```
scripts/ml_training/
├── train_pattern_statistics.py              # ⭐ CRITICAL - Pattern stats
├── generate_30min_trend_labels.py           # Labeling
├── train_layer05_regime_specialists.py      # Regime detection
├── generate_triple_barrier_ground_truth.py  # Triple barrier labels
└── (17 others)
```

**V3 Action:**
- [x] ✅ train_pattern_statistics.py → **MIGRATE** (updates pattern stats)
- [x] ⚠️ Other ML scripts → **ARCHIVE** (may not use ML in V3)

**Keep for Reference:**
- Labeling methodologies
- Ground truth generation logic
- Feature engineering approaches

---

### 10. Pattern Documentation (docs/Layer_TBD - 57 files)

```
docs/Layer_TBD/
├── SOPHISTICATED_M_PATTERN_DETECTOR_SPEC.md         # ⭐ CRITICAL
├── SOPHISTICATED_M_PATTERN_IMPLEMENTATION.md        # ⭐ CRITICAL
├── SOPHISTICATED_M_PATTERN_USER_GUIDE.md            # ⭐ CRITICAL
├── SOPHISTICATED_W_PATTERN_*.md                     # ⭐ CRITICAL
├── PHASE3_TUNING_ROUND1.md                          # Optimization history
├── TBD_Implementation_Complete.md                   # Implementation notes
└── (51+ other analysis & tuning docs)
```

**V3 Action:**
- [x] ✅ Sophisticated M/W pattern docs → **MIGRATE** to `docs/v3/patterns/`
- [x] ✅ Tuning/optimization docs → **ARCHIVE** (reference)
- [x] ✅ Implementation notes → **ARCHIVE** (historical)

---

## REFERENCE ONLY (📚 Archive for Historical Context)

### 11. Deprecated Layers (src/layers - Excluding tbd_v2)

```
src/layers/
├── layer0_multi_tf_trend.py          # Multi-TF trend detection
├── layer05_micro_trend.py            # Micro-trend
├── layer1_traditional.py             # Classic TA
├── layer2_volume_delta.py            # Volume analysis
├── layer3_weis_wave.py               # Weis Wave
├── layer4_xgboost.py                 # XGBoost ML
├── layer5_cnn_lstm.py                # Deep learning
├── layer6_tv_alerts.py               # TradingView alerts
├── layer_compositor.py               # Multi-layer fusion
└── layer_tbd_method.py               # Original TBD layer
```

**V3 Action:**
- [x] 📚 **ARCHIVE** all (replaced by pattern-only strategy)
- [x] ⚠️ **EXCEPTION**: Extract any reusable indicator functions

**Potential Salvage:**
- ADX calculations from Layer 0
- Volume profile logic from Layer 2
- Weis Wave algorithms from Layer 3

---

### 12. Custom Backtest/Optimization (✗ DO NOT MIGRATE - Buggy)

```
src/backtesting/
├── backtest_engine.py               # ❌ ARCHIVE - Replaced by VectorBT
├── backtest_engine_tbd.py           # ❌ ARCHIVE - Bug-prone P&L
├── enhanced_backtest.py             # ❌ ARCHIVE
├── performance_metrics.py           # ⚠️ REFERENCE (metrics formulas)
├── walk_forward.py                  # ❌ ARCHIVE
└── layer_report_formatter.py        # ❌ ARCHIVE

src/optimization/
├── optimizer.py                     # ❌ ARCHIVE - Replaced by VectorBT
├── search_space.py                  # ⚠️ REFERENCE (param ranges)
├── evaluator.py                     # ❌ ARCHIVE
└── tbd_optimizer.py                 # ❌ ARCHIVE
```

**V3 Action:**
- [x] ❌ Move ALL to `archive_v2/`
- [x] ⚠️ Extract useful metric formulas before archiving

---

### 13. CLI Tools (src/cli - 11 files)

```
src/cli/
├── commands.py                      # CLI command definitions
├── backtest_runner.py               # Backtest CLI
├── live_runner.py                   # Live trading CLI
├── paper_runner.py                  # Paper trading CLI
├── train_runner.py                  # ML training CLI
├── optimize_runner.py               # Optimization CLI
├── validator.py                     # Validation tools
├── test_runner.py                   # Test runner
├── profiler.py                      # Performance profiler
└── status_checker.py                # Status monitoring
```

**V3 Action:**
- [x] ⚠️ **ARCHIVE** (rewrite CLIs for V3)
- [x] ⚠️ **REFERENCE** for CLI design patterns
- [x] ✅ Preserve profiler logic (performance tracking)

---

## MIGRATION PRIORITY MATRIX

### Tier 1: CRITICAL - Migrate First (Days 1-7)

| Asset | Files | Size | Priority | V3 Location |
|-------|-------|------|----------|-------------|
| Historical Data | 20 | 308GB | P0 | `data/raw/` (symlink) |
| Pattern Detectors | 10 | <1MB | P0 | `indicators/` |
| Pattern Statistics | 2 | <10MB | P0 | `data/models/pattern_statistics/` |
| Pattern Docs | 6 | <5MB | P0 | `docs/v3/patterns/` |
| LakeAPI Scripts | 5 | <1MB | P0 | `scripts/lakeapi/` |

### Tier 2: HIGH VALUE - Migrate Second (Days 8-14)

| Asset | Files | Size | Priority | V3 Location |
|-------|-------|------|----------|-------------|
| Data Download Scripts | 5 | <1MB | P1 | `scripts/data_download/` |
| Core Data Pipeline | 2 | <500KB | P1 | `scripts/data_processing/` |
| MTF Sync | 1 | <100KB | P1 | `indicators/utils/` |
| Fee Calculator | 1 | <50KB | P1 | `strategies/utils/` |
| Pattern Training | 1 | <200KB | P1 | `scripts/ml_training/` |
| Fibonacci Utils | 1 | <50KB | P1 | `indicators/utils/` |

### Tier 3: REFERENCE - Archive (Days 19-20)

| Asset | Files | Size | Priority | V3 Location |
|-------|-------|------|----------|-------------|
| Old Layers | 15+ | <5MB | P2 | `archive_v2/src/layers/` |
| Backtest Engine | 7 | <1MB | P2 | `archive_v2/src/backtesting/` |
| Optimizer | 4 | <500KB | P2 | `archive_v2/src/optimization/` |
| CLI Tools | 11 | <1MB | P2 | `archive_v2/src/cli/` |
| ML Training | 20 | <2MB | P2 | `archive_v2/scripts/ml_training/` |
| Tuning Docs | 50+ | <10MB | P2 | `archive_v2/docs/Layer_TBD/` |

---

## V3 PROJECT STRUCTURE (Final)

```
BTC_Engine_v3/
├── .env                           # Secrets, API keys
├── .gitignore
├── requirements_v3.txt
├── README.md
│
├── data/                          # SYMLINK from V2 (DO NOT COPY)
│   ├── raw/                       # 308GB historical data
│   ├── processed/
│   └── models/
│       └── pattern_statistics/    # M & W pattern stats
│
├── indicators/                    # MIGRATED pattern detectors
│   ├── pattern_detector.py       # Base detector (framework-agnostic)
│   ├── m_pattern.py               # M-pattern logic
│   ├── w_pattern.py               # W-pattern logic
│   └── utils/
│       ├── zigzag.py              # Zigzag detector
│       ├── divergence.py          # Divergence detector
│       ├── oscillators.py         # RSI, Stochastic
│       ├── fibonacci.py           # Fib calculations
│       └── mtf_sync.py            # Multi-timeframe sync
│
├── strategies/                    # PFund strategies
│   ├── m_pattern_strategy.py
│   ├── w_pattern_strategy.py
│   └── utils/
│       └── fees.py                # Fee calculator
│
├── backtests/                     # VectorBT backtests
│   ├── m_pattern_backtest.py
│   ├── w_pattern_backtest.py
│   └── optimization/
│
├── scripts/
│   ├── lakeapi/                   # LakeAPI infrastructure
│   │   ├── scanner.py
│   │   ├── downloader.py
│   │   └── orderbook_downloader.py
│   ├── data_download/             # Other downloaders
│   │   ├── download_binance_*.py
│   │   └── download_liquidations_funding_oi.py
│   ├── data_processing/           # Data pipeline
│   │   └── data_loader.py
│   └── ml_training/               # Pattern statistics training
│       └── train_pattern_stats.py
│
├── docs/
│   ├── v3/
│   │   ├── patterns/              # Pattern documentation
│   │   │   ├── M_PATTERN_SPEC.md
│   │   │   └── W_PATTERN_SPEC.md
│   │   ├── ARCHITECTURE.md
│   │   ├── USER_GUIDE.md
│   │   └── LAKEAPI_GUIDE.md
│   └── archive_v2/                # V2 documentation reference
│
├── tests/
│   ├── test_patterns.py
│   ├── test_indicators.py
│   └── test_strategies.py
│
└── archive_v2/                    # COMPLETE V2 codebase (read-only)
    ├── src/
    ├── scripts/
    ├── docs/
    └── README_V2.md               # "Why we migrated" explanation
```

---

## CRITICAL MIGRATION CHECKLISTS

### Pre-Migration Safety Checks

- [ ] Create FULL backup of `/home/sirrus/projects/BTC_Engine_LLM`
- [ ] Verify Git commit: `7e229ec1acf76a891fab8018a74fbaf0573637f3`
- [ ] Tag V2: `git tag -a v2.0-final -m "Final V2 before migration"`
- [ ] Push tag: `git push origin v2.0-final`
- [ ] Calculate checksums: `find data/raw -type f -exec md5sum {} \; > data_checksums.txt`
- [ ] Verify AWS credentials valid
- [ ] Test LakeAPI connectivity
- [ ] Document any uncommitted changes

### Data Migration Validation

- [ ] Symlink created: `ln -s /path/to/V2/data /path/to/V3/data`
- [ ] All 20 raw data files accessible
- [ ] Pattern statistics files present (m_pattern_stats_v2.pkl, w_pattern_stats_v2.pkl)
- [ ] Test data loading in Python
- [ ] Verify no corruption: `md5sum -c data_checksums.txt`

### Code Migration Validation

- [ ] Pattern detectors extracted to indicators/
- [ ] All tests passing
- [ ] No backtest_engine imports remaining
- [ ] VectorBT integration working
- [ ] PFund strategies implemented
- [ ] Paper trading tested

### Documentation Migration

- [ ] M-pattern spec migrated
- [ ] W-pattern spec migrated
- [ ] LakeAPI guide updated
- [ ] V3 architecture documented
- [ ] Migration report complete

---

## FILE COUNTS SUMMARY

| Category | Files | Action |
|----------|-------|--------|
| **Critical Assets** | 32 | ✅ MIGRATE |
| **High Value** | 115 | ⭐ MIGRATE/REFERENCE |
| **Historical Data** | 20 files (308GB) | ✅ SYMLINK |
| **Documentation** | 57+ | ✅ SELECTIVE MIGRATE |
| **Archive** | 100+ | 📚 ARCHIVE |
| **TOTAL** | ~324 files | - |

---

## ESTIMATED MIGRATION EFFORT

| Phase | Assets | Time | Risk |
|-------|--------|------|------|
| Data Validation | 20 files, 308GB | 4 hours | LOW (read-only) |
| Pattern Migration | 10 files | 2 days | MEDIUM (refactor) |
| Utilities Migration | 15 files | 1 day | LOW (copy/adapt) |
| Documentation | 6 files | 1 day | LOW (copy) |
| Testing | All | 3 days | MEDIUM (new framework) |
| **TOTAL** | **All Assets** | **~7 days** | **MEDIUM** |

---

## SIGN-OFF CRITERIA

**Migration is COMPLETE when:**

✅ All Tier 1 assets migrated and tested  
✅ All Tier 2 assets evaluated and migrated/archived  
✅ Data integrity verified (checksums match)  
✅ Pattern detectors work in V3  
✅ Backtest P&L 100% accurate  
✅ LakeAPI functional  
✅ V2 codebase archived (not deleted)  
✅ Documentation complete  
✅ Rollback plan tested  

**Final Approval:** Project Lead + Technical Review

---

**Document Owner:** BTC_Engine Development Team  
**Last Audit:** December 30, 2025 09:13 AM  
**Status:** READY FOR MIGRATION  
**Assets at Risk:** ZERO (all identified and planned)
