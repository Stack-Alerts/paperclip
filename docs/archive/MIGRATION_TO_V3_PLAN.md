# BTC_Engine_v3 Migration Plan
## Professional Framework Migration: PFund + VectorBT

**Date:** December 30, 2025  
**Status:** Planning Phase  
**Objective:** Migrate from custom backtest engine to institutional-grade frameworks

---

## Executive Summary

### Critical Issue Identified
Current custom backtest engine has P&L calculation inconsistencies (38.1% error rate in validation), making it unsuitable for real money trading despite correct code logic. Root cause unclear after extensive debugging.

### Solution
Migrate to proven, battle-tested frameworks:
- **PFund**: Production-grade trading framework (live + paper + backtest)
- **VectorBT**: High-performance vectorized backtesting & optimization

### Migration Goals
1. ✅ 100% accurate P&L calculations (verified by established frameworks)
2. ✅ Preserve 6 years of BTC historical data
3. ✅ Retain sophisticated M/W pattern detectors
4. ✅ Faster backtesting (vectorized operations)
5. ✅ Cleaner, maintainable codebase
6. ✅ Path to production trading

---

## Phase 1: Discovery & Analysis (Days 1-2)

### 1.1 Framework Research & Comparison

**Task List:**
- [ ] Clone PFund repository locally
- [ ] Clone VectorBT repository locally
- [ ] Review PFund architecture documentation
- [ ] Review VectorBT API documentation
- [ ] Create feature comparison matrix (our engine vs new frameworks)
- [ ] Identify gaps and required custom components
- [ ] Document integration points between PFund and VectorBT

**Deliverable:** `docs/v3/FRAMEWORK_COMPARISON.md`

### 1.2 Current System Audit

**What We Keep (HIGH VALUE):**

```
/data/                          # 6 years BTC data - CRITICAL ASSET
├── raw/                        # OHLCV, orderbook, funding, liquidations
├── processed/                  # Feature matrices
├── models/                     # Pattern statistics, ML models
└── reports/                    # Existing backtest results

/src/layers/tbd_v2/             # Pattern detectors - CORE IP
├── sophisticated_m_pattern_layer.py    # ✅ KEEP
├── sophisticated_w_pattern_layer.py    # ✅ KEEP
├── detectors/
│   ├── zigzag_detector.py              # ✅ KEEP
│   ├── divergence_detector.py          # ✅ KEEP
│   ├── oscillators.py                  # ✅ KEEP
│   └── pattern_statistics.py           # ✅ KEEP

/scripts/data_download/         # Data acquisition - ESSENTIAL
├── download_binance_spot.py
├── download_funding_rates.py
├── download_liquidations.py
└── download_orderbook.py

/docs/Layer_TBD/               # Pattern documentation
├── SOPHISTICATED_M_PATTERN_DETECTOR_SPEC.md
├── SOPHISTICATED_M_PATTERN_IMPLEMENTATION.md
├── SOPHISTICATED_M_PATTERN_USER_GUIDE.md
└── (W-pattern equivalents)

/TradingView_Scripts/          # Pine scripts for pattern validation
```

**What We Archive (LOW VALUE / BROKEN):**

```
/src/backtesting/              # ❌ ARCHIVE - replaced by VectorBT
├── backtest_engine.py
├── backtest_engine_tbd.py     # Bug-prone
├── enhanced_backtest.py
├── performance_metrics.py
└── walk_forward.py

/src/optimization/             # ❌ ARCHIVE - replaced by VectorBT
├── optimizer.py
├── search_space.py
└── evaluator.py

/src/layers/                   # ❌ ARCHIVE - only keep tbd_v2/
├── layer0_*.py                # Old layer system
├── layer1_*.py
├── layer2_*.py
├── layer3_*.py
├── layer4_*.py
├── layer5_*.py
└── layer6_*.py

/config/strategies/            # ❌ ARCHIVE most (rewrite for PFund)
├── scalp_*.py                 # All old strategies
└── (only keep sophisticated_m/w_pattern as reference)
```

**Task List:**
- [ ] Create `/archive_v2/` directory
- [ ] Document what goes to archive with reasons
- [ ] Create inventory of all scripts and their purposes
- [ ] Identify reusable utility functions
- [ ] Map data dependencies

**Deliverable:** `docs/v3/ASSET_INVENTORY.md`

---

## Phase 2: Environment Setup (Day 3)

### 2.1 New Project Structure

```
BTC_Engine_v3/
├── .env                        # API keys, secrets
├── .gitignore                  # Updated for new frameworks
├── requirements_v3.txt         # New dependencies
├── README.md                   # Updated docs
│
├── pfund_config/              # PFund configuration
│   ├── account_config.yaml
│   ├── strategy_config.yaml
│   └── exchange_config.yaml
│
├── strategies/                # PFund strategies
│   ├── m_pattern_strategy.py
│   ├── w_pattern_strategy.py
│   └── base_pattern_strategy.py
│
├── indicators/                # Custom indicators
│   ├── zigzag.py
│   ├── pattern_detector.py
│   └── divergence.py
│
├── backtests/                 # VectorBT backtests
│   ├── m_pattern_backtest.py
│   ├── w_pattern_backtest.py
│   └── optimization/
│
├── data/                      # MIGRATED FROM V2 (symlink or copy)
│   ├── raw/
│   ├── processed/
│   └── models/
│
├── scripts/                   # Utility scripts
│   ├── data_download/        # MIGRATED FROM V2
│   ├── data_processing/
│   └── analysis/
│
├── notebooks/                 # Jupyter analysis
│   ├── pattern_analysis.ipynb
│   └── backtest_results.ipynb
│
├── docs/                      # Documentation
│   ├── v3/                   # V3-specific docs
│   ├── patterns/             # MIGRATED FROM V2
│   └── archive_v2/           # Old docs reference
│
├── tests/                     # pytest tests
│   ├── test_patterns.py
│   ├── test_indicators.py
│   └── test_strategies.py
│
└── archive_v2/                # Old codebase (read-only reference)
    └── (everything deprecated)
```

### 2.2 Dependency Installation

**Task List:**
- [ ] Create `requirements_v3.txt`
- [ ] Install PFund: `pip install pfund`
- [ ] Install VectorBT: `pip install vectorbt`
- [ ] Install dependencies: pandas, numpy, ta-lib, etc.
- [ ] Verify installations with test imports
- [ ] Document version pins for reproducibility

**Dependencies:**
```txt
# Core Frameworks
pfund>=0.1.0
vectorbt>=0.26.0

# Data & Analysis
pandas>=2.0.0
numpy>=1.24.0
ta-lib>=0.4.28

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0
loguru>=0.7.0
```

**Deliverable:** `requirements_v3.txt` + installation verification

---

## Phase 3: Pattern Detector Migration (Days 4-6)

### 3.1 Extract Core Pattern Logic

**Goal:** Isolate pure pattern detection from framework dependencies

**Task List:**
- [ ] Create `indicators/pattern_detector.py` (framework-agnostic)
- [ ] Migrate zigzag logic to standalone function
- [ ] Migrate M-pattern detection to pure function
- [ ] Migrate W-pattern detection to pure function
- [ ] Migrate divergence detection to pure function
- [ ] Remove all backtest_engine dependencies
- [ ] Create unit tests for each detector
- [ ] Validate against known patterns in historical data

**Code Structure:**
```python
# indicators/pattern_detector.py

class PatternDetector:
    """
    Framework-agnostic pattern detection.
    Input: OHLCV DataFrame
    Output: Pattern signals with metadata
    """
    
    def __init__(self, config: dict):
        self.zigzag = ZigzagDetector(config['pivot_length'], config['threshold'])
        self.divergence = DivergenceDetector(config['oscillator'])
        self.stats = PatternStatistics(config['stats_file'])
    
    def detect_m_pattern(self, df: pd.DataFrame) -> pd.Series:
        """Returns boolean series where M-pattern detected"""
        pass
    
    def detect_w_pattern(self, df: pd.DataFrame) -> pd.Series:
        """Returns boolean series where W-pattern detected"""
        pass
    
    def get_signal_metadata(self, df: pd.DataFrame, index: int) -> dict:
        """Returns entry/exit/stop/targets for given pattern"""
        pass
```

**Deliverable:** `indicators/pattern_detector.py` + tests

### 3.2 VectorBT Integration

**Task List:**
- [ ] Create VectorBT custom indicator wrapper
- [ ] Implement M-pattern as VectorBT indicator
- [ ] Implement W-pattern as VectorBT indicator
- [ ] Create entry/exit signal generators
- [ ] Implement stop-loss logic
- [ ] Implement take-profit levels (TP1/TP2/TP3)
- [ ] Test on sample data (100 candles)
- [ ] Validate P&L calculations match expected

**Code Structure:**
```python
# backtests/indicators_vbt.py

import vectorbt as vbt

class MPatternIndicator(vbt.IndicatorFactory):
    """VectorBT wrapper for M-pattern detection"""
    
    @classmethod
    def create_indicator(cls, df, config):
        detector = PatternDetector(config)
        signals = detector.detect_m_pattern(df)
        metadata = detector.get_signal_metadata(df, signals)
        return signals, metadata
```

**Deliverable:** VectorBT-compatible indicators

---

## Phase 4: Backtesting Framework (Days 7-10)

### 4.1 VectorBT Backtest Implementation

**Task List:**
- [ ] Create baseline M-pattern backtest script
- [ ] Implement entry logic (pattern detection)
- [ ] Implement exit logic (TP1/TP2/TP3 scaling)
- [ ] Implement stop-loss (price-based)
- [ ] Implement time-based exit
- [ ] Add commission/slippage modeling
- [ ] Create metrics calculation
- [ ] Generate equity curve
- [ ] Export trade log to CSV
- [ ] **CRITICAL:** Validate P&L against manual calculations
- [ ] Compare results with old engine (on same data)

**Code Structure:**
```python
# backtests/m_pattern_backtest.py

import vectorbt as vbt
import pandas as pd
from indicators.pattern_detector import PatternDetector

def run_m_pattern_backtest(
    data: pd.DataFrame,
    config: dict,
    initial_capital: float = 10000
):
    """
    Run vectorized backtest for M-pattern strategy.
    
    Returns:
        vbt.Portfolio object with full metrics
    """
    # 1. Generate signals
    detector = PatternDetector(config)
    entries = detector.detect_m_pattern(data)
    
    # 2. Generate exit signals (TP/SL)
    exits = generate_exits(data, entries, config)
    
    # 3. Run backtest
    portfolio = vbt.Portfolio.from_signals(
        data['close'],
        entries=entries,
        exits=exits,
        init_cash=initial_capital,
        fees=0.001,  # 0.1% commission
        slippage=0.0002,  # 2 bps
        direction='short'  # M-pattern = SHORT
    )
    
    return portfolio

if __name__ == '__main__':
    # Load data
    data = pd.read_parquet('data/raw/btc_usdt_15m.parquet')
    
    # Run backtest
    pf = run_m_pattern_backtest(data, config)
    
    # Print metrics
    print(pf.stats())
    
    # Export trades
    pf.trades.records_readable.to_csv('m_pattern_trades.csv')
```

**Deliverable:** Working VectorBT backtest with verified P&L

### 4.2 Walk-Forward Validation

**Task List:**
- [ ] Implement walk-forward analysis with VectorBT
- [ ] Create rolling window backtest
- [ ] Calculate period-by-period metrics
- [ ] Detect overfitting (train vs test performance)
- [ ] Generate walk-forward report
- [ ] Compare with old walk-forward results

**Deliverable:** `backtests/walk_forward.py`

### 4.3 Optimization Framework

**Task List:**
- [ ] Define parameter search space
- [ ] Implement VectorBT parameter optimization
- [ ] Add custom objective function (Sharpe, Calmar, etc.)
- [ ] Implement parallel optimization
- [ ] Generate optimization report
- [ ] Visualize parameter sensitivity
- [ ] Compare with old optimizer results

**Deliverable:** `backtests/optimization/optimize_m_pattern.py`

---

## Phase 5: PFund Integration (Days 11-14)

### 5.1 PFund Strategy Implementation

**Task List:**
- [ ] Study PFund strategy API
- [ ] Create base pattern strategy class
- [ ] Implement M-pattern PFund strategy
- [ ] Implement W-pattern PFund strategy
- [ ] Add position sizing logic
- [ ] Add risk management
- [ ] Configure exchange connection (Binance)
- [ ] Test in paper trading mode
- [ ] Create strategy monitoring dashboard

**Code Structure:**
```python
# strategies/m_pattern_strategy.py

from pfund import Strategy
from indicators.pattern_detector import PatternDetector

class MPatternStrategy(Strategy):
    """
    PFund strategy for M-pattern trading.
    Supports: backtest, paper, live
    """
    
    def __init__(self, config):
        super().__init__()
        self.detector = PatternDetector(config)
        self.position_size = config['position_size']
        self.risk_per_trade = config['risk_per_trade']
    
    def on_data(self, data):
        """Called on each new candle"""
        # Detect pattern
        if self.detector.has_m_pattern(data):
            metadata = self.detector.get_signal_metadata(data)
            
            # Enter SHORT
            self.enter_short(
                size=self.calculate_position_size(metadata['stop_loss']),
                stop_loss=metadata['stop_loss'],
                take_profit=[
                    metadata['tp1'],
                    metadata['tp2'],
                    metadata['tp3']
                ]
            )
    
    def calculate_position_size(self, stop_loss):
        """Risk-based position sizing"""
        risk_amount = self.capital * self.risk_per_trade
        stop_distance = abs(self.current_price - stop_loss)
        return risk_amount / stop_distance
```

**Deliverable:** Production-ready PFund strategies

### 5.2 Live Trading Preparation

**Task List:**
- [ ] Configure PFund for Binance API
- [ ] Set up paper trading environment
- [ ] Implement order execution logic
- [ ] Add position tracking
- [ ] Add real-time logging
- [ ] Create performance monitoring
- [ ] Set up alerts (Telegram/Discord)
- [ ] Create kill switch / emergency stop
- [ ] Document deployment procedure

**Deliverable:** `docs/v3/DEPLOYMENT_GUIDE.md`

---

## Phase 6: Data Migration & Testing (Days 15-17)

### 6.1 Data Directory Migration

**Task List:**
- [ ] Verify data integrity (checksums)
- [ ] Create `data/` symlink or copy to v3
- [ ] Test data loading in VectorBT
- [ ] Verify all timeframes accessible
- [ ] Test orderbook data access
- [ ] Test open interest data access
- [ ] Document data schema
- [ ] Create data access utilities

**Deliverable:** Working data pipeline in v3

### 6.2 Comprehensive Testing

**Test Suite Checklist:**
- [ ] Unit tests for pattern detectors (100% coverage)
- [ ] Unit tests for indicators
- [ ] Integration tests for VectorBT backtests
- [ ] Integration tests for PFund strategies
- [ ] End-to-end test: data → backtest → results
- [ ] P&L accuracy validation (compare manual calculations)
- [ ] Performance tests (backtest speed)
- [ ] Memory leak tests (large datasets)

**Critical P&L Validation Tests:**
```python
def test_pnl_accuracy():
    """
    CRITICAL: Verify P&L calculations are 100% accurate
    """
    # Known trade
    entry = 115621.571
    exit = 115726.6
    qty = 0.017297810275922747
    
    # Expected P&L for SHORT
    expected_pnl = (entry - exit) * qty - (entry * qty * 0.001) - (exit * qty * 0.001)
    # = -1.8168 - 2.000 - 2.0018 = -5.8186
    
    # Run backtest
    pf = run_single_trade_backtest(entry, exit, qty, 'short')
    actual_pnl = pf.trades.pnl.sum()
    
    # MUST MATCH EXACTLY
    assert abs(actual_pnl - expected_pnl) < 0.01, f"P&L mismatch! Expected {expected_pnl}, got {actual_pnl}"
```

**Deliverable:** `tests/` directory with >90% coverage

---

## Phase 7: Documentation & Knowledge Transfer (Days 18-20)

### 7.1 Documentation

**Task List:**
- [ ] Update main README.md
- [ ] Create V3 architecture diagram
- [ ] Document pattern detector API
- [ ] Document backtest workflow
- [ ] Document optimization workflow
- [ ] Document paper trading setup
- [ ] Create troubleshooting guide
- [ ] Create performance optimization guide
- [ ] Archive V2 documentation

**Deliverables:**
- `README.md` (updated)
- `docs/v3/ARCHITECTURE.md`
- `docs/v3/API_REFERENCE.md`
- `docs/v3/USER_GUIDE.md`
- `docs/v3/TROUBLESHOOTING.md`

### 7.2 Migration Report

**Task List:**
- [ ] Document migration decisions
- [ ] Compare V2 vs V3 performance
- [ ] Document lessons learned
- [ ] Create rollback plan (if needed)
- [ ] Final sign-off checklist

**Deliverable:** `docs/v3/MIGRATION_REPORT.md`

---

## Phase 8: Cleanup & Finalization (Day 21)

### 8.1 Archive V2 Codebase

**Task List:**
- [ ] Create `archive_v2/` directory
- [ ] Move deprecated code to archive
- [ ] Keep minimal reference docs
- [ ] Update .gitignore
- [ ] Clean up root directory
- [ ] Remove unused dependencies
- [ ] Update CI/CD if applicable

### 8.2 GitHub Cleanup

**Task List:**
- [ ] Create new branch: `v3_migration`
- [ ] Commit v3 codebase
- [ ] Tag v2 as `v2.0-final`
- [ ] Update GitHub README
- [ ] Update repository description
- [ ] Archive old issues related to V2 bugs
- [ ] Create new project board for V3
- [ ] Update GitHub Actions (if any)

---

## Framework Feature Comparison

### Backtest Features

| Feature | V2 (Custom) | VectorBT | Status |
|---------|-------------|----------|--------|
| **Basic Backtesting** | ✅ | ✅ | Covered |
| Entry/Exit Signals | ✅ | ✅ | Covered |
| Stop Loss | ✅ | ✅ | Covered |
| Take Profit Levels | ✅ (3 levels) | ✅ | Covered |
| Partial Exits | ✅ | ✅ | Covered |
| Commission Modeling | ✅ | ✅ | Covered |
| Slippage Modeling | ✅ | ✅ | Covered |
| **Performance Metrics** | | | |
| Win Rate | ✅ | ✅ | Covered |
| Profit Factor | ✅ | ✅ | Covered |
| Sharpe Ratio | ✅ | ✅ | Covered |
| Max Drawdown | ✅ | ✅ | Covered |
| Calmar Ratio | ❌ | ✅ | **Improvement** |
| Sortino Ratio | ❌ | ✅ | **Improvement** |
| **Optimization** | | | |
| Parameter Search | ✅ (custom) | ✅ (built-in) | Covered |
| Parallel Processing | ✅ | ✅ | Covered |
| Custom Objectives | ✅ | ✅ | Covered |
| Grid Search | ✅ | ✅ | Covered |
| Random Search | ❌ | ✅ | **Improvement** |
| Bayesian Optimization | ❌ | ⚠️ (via Optuna) | **Enhancement** |
| **Walk-Forward** | | | |
| Rolling Window | ✅ | ✅ | Covered |
| Anchored Window | ❌ | ✅ | **Improvement** |
| Out-of-Sample Testing | ✅ | ✅ | Covered |
| **Visualization** | | | |
| Equity Curve | ✅ | ✅ | Covered |
| Drawdown Chart | ✅ | ✅ | Covered |
| Trade Distribution | ⚠️ (basic) | ✅ | **Improvement** |
| 3D Parameter Surface | ❌ | ✅ | **Improvement** |
| **Core Advantage** | | | |
| **P&L Accuracy** | ❌ (38% errors) | ✅ (proven) | **CRITICAL FIX** |
| **Performance** | ~1000 bars/sec | ~100K bars/sec | **100x faster** |
| **Memory Efficiency** | ⚠️ (loops) | ✅ (vectorized) | **Improvement** |

### Live Trading Features

| Feature | V2 (Custom) | PFund | Status |
|---------|-------------|-------|--------|
| **Trading Modes** | | | |
| Backtesting | ✅ (buggy) | ✅ | Covered |
| Paper Trading | ✅ | ✅ | Covered |
| Live Trading | ✅ | ✅ | Covered |
| **Exchange Support** | | | |
| Binance Spot | ✅ | ✅ | Covered |
| Binance Futures | ⚠️ (partial) | ✅ | **Improvement** |
| Multiple Exchanges | ❌ | ✅ | **Improvement** |
| **Order Management** | | | |
| Market Orders | ✅ | ✅ | Covered |
| Limit Orders | ✅ | ✅ | Covered |
| Stop Orders | ✅ | ✅ | Covered |
| OCO Orders | ❌ | ✅ | **Improvement** |
| **Risk Management** | | | |
| Position Sizing | ✅ (custom) | ✅ (built-in) | Covered |
| Max Position Size | ✅ | ✅ | Covered |
| Daily Loss Limit | ❌ | ✅ | **Improvement** |
| Exposure Limits | ❌ | ✅ | **Improvement** |
| **Monitoring** | | | |
| Real-time Logging | ✅ | ✅ | Covered |
| Performance Dashboard | ❌ | ✅ | **Improvement** |
| Alerts | ⚠️ (basic) | ✅ | **Improvement** |
| **Data Handling** | | | |
| Live Data Streaming | ✅ | ✅ | Covered |
| Historical Data | ✅ | ✅ | Covered |
| Multi-Timeframe | ✅ | ✅ | Covered |
| Orderbook Data | ✅ (custom) | ⚠️ (extension) | **Custom Work** |
| **Core Advantage** | | | |
| **Production Ready** | ❌ | ✅ | **CRITICAL** |
| **Error Handling** | ⚠️ (basic) | ✅ (robust) | **Improvement** |
| **Testing Framework** | ⚠️ (manual) | ✅ (built-in) | **Improvement** |

---

## Critical Success Factors

### Must-Have Requirements
1. **P&L Accuracy: 100%** (non-negotiable)
2. **Pattern Detector Preservation** (our core IP)
3. **Data Integrity** (6 years historical data)
4. **Backtest Speed** (>10x current)
5. **Production Readiness** (paper → live path)

### Risk Mitigation
1. **Parallel Development**: Build V3 alongside V2 (no deletion until proven)
2. **Validation**: Cross-verify results (V2 vs V3 on same data)
3. **Rollback Plan**: Keep V2 functional until V3 production-tested
4. **Documentation**: Comprehensive migration notes
5. **Testing**: >90% code coverage before deployment

---

## Timeline Summary

| Phase | Duration | Critical Path |
|-------|----------|---------------|
| 1. Discovery & Analysis | 2 days | Framework research |
| 2. Environment Setup | 1 day | Dependencies |
| 3. Pattern Migration | 3 days | Core IP preservation |
| 4. Backtesting | 4 days | VectorBT integration |
| 5. PFund Integration | 4 days | Live trading prep |
| 6. Data & Testing | 3 days | P&L validation |
| 7. Documentation | 3 days | Knowledge transfer |
| 8. Cleanup | 1 day | Finalization |
| **Total** | **21 days** | **~3 weeks** |

---

## Next Steps

1. **Approve This Plan** → Proceed to Phase 1
2. **Start Framework Research** → Clone repos, review docs
3. **Begin Asset Inventory** → Document what to keep/archive
4. **Set Up V3 Branch** → `git checkout -b v3_migration`

---

## Sign-Off Checklist

Before declaring V3 production-ready:

- [ ] All pattern detectors migrated and tested
- [ ] Backtest P&L verified 100% accurate (manual validation)
- [ ] Walk-forward validation matches or exceeds V2 accuracy
- [ ] Optimization runs successfully
- [ ] Paper trading tested for 1 week minimum
- [ ] All critical data migrated and accessible
- [ ] Documentation complete
- [ ] Code coverage >90%
- [ ] Performance benchmarks met
- [ ] Emergency stop/rollback tested

**Final Approval Required Before Live Trading**

---

**Document Owner:** BTC_Engine Development Team  
**Last Updated:** December 30, 2025  
**Status:** Ready for Execution
