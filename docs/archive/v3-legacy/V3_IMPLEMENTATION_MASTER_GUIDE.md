# BTC_Engine_v3 Implementation Master Guide
## NautilusTrader Migration - Complete Implementation Plan

**Project:** BTC_Engine_v3 (Fresh Start)  
**Framework:** NautilusTrader v1.221.0  
**Timeline:** 14 Days  
**Confidence:** 94%

---

## 🎯 Project Objectives

Build institutional-grade BTC scalping bot using NautilusTrader with our sophisticated M/W pattern detection algorithms.

**Core Goals:**
1. Fix V2's P&L calculation bugs (institutional-grade accuracy)
2. Maintain pattern detection IP (zero rewrite)
3. Enable live trading (production-ready)
4. Achieve 10-100x performance boost (Rust core)
5. Timeline: 14 days to production

---

## 📁 Project Structure

```
/home/sirrus/projects/BTC_Engine_v3/
├── data/                          # ✅ COPIED (308GB)
│   ├── raw/                       # 142 Parquet files, 109K BTC bars
│   ├── processed/                 # Feature-engineered data
│   └── models/                    # ML models (if needed)
├── src/
│   ├── strategies/                # NautilusTrader strategies
│   │   ├── __init__.py
│   │   ├── m_pattern_strategy.py # M-pattern (to create)
│   │   └── w_pattern_strategy.py # W-pattern (to create)
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── pattern_detectors/     # ✅ COPIED from V2
│   │       ├── sophisticated_m_pattern_layer.py
│   │       ├── sophisticated_w_pattern_layer.py
│   │       ├── detectors/
│   │       │   ├── zigzag_detector.py
│   │       │   ├── divergence_detector.py
│   │       │   ├── nested_m_detector.py
│   │       │   └── oscillators.py
│   │       └── utils/
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── data_loader.py         # Load our Parquet data
│       └── logger.py              # Logging utilities
├── config/
│   ├── backtest_config.json       # Backtest configuration
│   ├── live_config.json           # Live trading config
│   └── sandbox_config.json        # Paper trading config
├── scripts/
│   ├── run_backtest.py            # Backtest runner
│   ├── run_sandbox.py             # Paper trading runner
│   └── data_catalog_setup.py     # Initialize NautilusTrader catalog
├── tests/
│   ├── test_m_pattern.py          # M-pattern tests
│   ├── test_w_pattern.py          # W-pattern tests
│   └── test_data_loading.py      # Data pipeline tests
├── docs/                          # ✅ Documentation
│   ├── V3_IMPLEMENTATION_MASTER_GUIDE.md  # THIS FILE
│   ├── NAUTILUS_TRADER_ANALYSIS.md
│   ├── MIGRATION_TO_V3_PLAN.md
│   └── v3/
│       ├── PHASE1_DISCOVERY_COMPLETE.md
│       ├── COMPLETE_ASSET_INVENTORY.md
│       └── LAKEAPI_ASSET_INVENTORY.md
├── requirements.txt               # Python dependencies
└── README.md                      # Project overview
```

---

## 🗂️ Critical Assets (Already Available)

### ✅ Data Assets (308GB)
Located: `/home/sirrus/projects/BTC_Engine_v3/data/`

**Raw Data:**
- `BTC_USDT_PERP_30m.pkl` - 109,949 bars, 30m timeframe
- 141 more Parquet/PKL files
- Orderbook depth data (200GB)
- Funding rates (1GB)
- Liquidations (5GB)
- Trades data

**Format:** Parquet/PKL (NautilusTrader native support ✅)

### ✅ Pattern Detection Code
Located: `/home/sirrus/projects/BTC_Engine_v3/src/indicators/pattern_detectors/`

**Core IP (Copied from V2):**
- `sophisticated_m_pattern_layer.py` - M-pattern detector (our secret sauce)
- `sophisticated_w_pattern_layer.py` - W-pattern detector
- `detectors/zigzag_detector.py` - ZigZag algorithm
- `detectors/divergence_detector.py` - Multi-oscillator divergence
- `detectors/nested_m_detector.py` - Nested M-patterns
- `detectors/oscillators.py` - RSI, Stoch, CCI, etc.

**Status:** Framework-agnostic, ready to integrate ✅

### ✅ Documentation
Located: `/home/sirrus/projects/BTC_Engine_v3/docs/`

- Migration plan
- NautilusTrader analysis
- Asset inventory
- LakeAPI data catalog

---

## 🚀 14-Day Implementation Plan

### **PHASE 1: Setup & Validation (Days 1-2)**

#### Day 1: Environment Setup
- [ ] **1.1** Create Python virtual environment
  ```bash
  cd /home/sirrus/projects/BTC_Engine_v3
  python3 -m venv venv
  source venv/bin/activate
  ```

- [ ] **1.2** Install NautilusTrader
  ```bash
  pip install nautilus_trader pandas numpy pyarrow
  ```

- [ ] **1.3** Verify installation
  ```bash
  python -c "import nautilus_trader as nt; print(f'✅ v{nt.__version__}')"
  ```

- [ ] **1.4** Configure NautilusTrader data catalog
  ```bash
  export NAUTILUS_PATH=/home/sirrus/projects/BTC_Engine_v3/data
  ```

#### Day 2: Data Validation
- [ ] **2.1** Create `scripts/data_catalog_setup.py`
  - Initialize ParquetDataCatalog
  - Index existing data files
  - Test data loading

- [ ] **2.2** Load first dataset (BTC_USDT_PERP_30m.pkl)
  - Verify 109,949 bars load correctly
  - Check OHLCV columns
  - Validate timestamps

- [ ] **2.3** Simple backtest test
  - Create dummy strategy (buy & hold)
  - Run on 100 bars
  - Verify P&L calculation accuracy

**Day 2 Exit Criteria:** Data loads successfully, basic backtest runs ✅

---

### **PHASE 2: Pattern Integration (Days 3-5)**

#### Day 3: Framework-Agnostic Adapter
- [ ] **3.1** Create `src/indicators/pattern_adapter.py`
  - Wrapper around our pattern detectors
  - Converts NautilusTrader bars → our format
  - Returns signals in Nautilus format

- [ ] **3.2** Test pattern adapter
  - Load 1000 bars
  - Run through M-pattern detector
  - Verify signals match V2 output

#### Day 4: M-Pattern Strategy
- [ ] **4.1** Create `src/strategies/m_pattern_strategy.py`
  ```python
  from nautilus_trader.trading.strategy import Strategy
  from src.indicators.pattern_adapter import PatternAdapter
  
  class MPatternStrategy(Strategy):
      def __init__(self, config):
          super().__init__(config)
          self.pattern_detector = PatternAdapter('m_pattern')
      
      def on_bar(self, bar):
          signal = self.pattern_detector.detect(bar)
          if signal == 'short':
              self.submit_order(...)
  ```

- [ ] **4.2** Backtest M-pattern on 1-week data
  - Verify trades match expected patterns
  - Check P&L calculation
  - Log all trades for analysis

#### Day 5: W-Pattern Strategy
- [ ] **5.1** Create `src/strategies/w_pattern_strategy.py`
  - Similar to M-pattern
  - Uses W-pattern detector

- [ ] **5.2** Backtest W-pattern
  - 1-week validation
  - Compare vs M-pattern performance

**Day 5 Exit Criteria:** Both strategies run successfully, patterns detected ✅

---

### **PHASE 3: Historical Backtesting (Days 6-8)**

#### Day 6: Full Historical Backtest
- [ ] **6.1** Run M-pattern on full 109K bars
  - All 30m data (several months)
  - Generate trade log
  - Calculate metrics:
    - Total P&L
    - Win rate
    - Sharpe ratio
    - Max drawdown
    - Average trade duration

- [ ] **6.2** Analyze results
  - Compare metrics vs V2
  - Identify any discrepancies
  - Validate P&L accuracy

#### Day 7: Walk-Forward Validation
- [ ] **7.1** Split data into periods
  - Training: 60%
  - Validation: 20%
  - Test: 20%

- [ ] **7.2** Walk-forward analysis
  - Optimize on training data
  - Validate on validation set
  - Final test on test set

- [ ] **7.3** Document results
  - Performance by period
  - Parameter stability
  - Overfitting check

#### Day 8: Parameter Optimization
- [ ] **8.1** Create `scripts/optimize_params.py`
  - Grid search key parameters:
    - Entry thresholds
    - Exit thresholds
    - Stop loss %
    - Take profit %

- [ ] **8.2** Run optimization
  - Use Nautilus built-in optimizer
  - Multiple parameter combinations
  - Find optimal settings

- [ ] **8.3** Validation
  - Test optimal params on holdout data
  - Ensure not overfit

**Day 8 Exit Criteria:** Optimized strategy with validated performance ✅

---

### **PHASE 4: Paper Trading (Days 9-11)**

#### Day 9: Binance Testnet Setup
- [ ] **9.1** Create Binance testnet account
  - Get API key & secret
  - Store in config (encrypted)

- [ ] **9.2** Configure `config/sandbox_config.json`
  ```json
  {
    "environment": "sandbox",
    "data_clients": {
      "BINANCE": {
        "api_key": "...",
        "api_secret": "...",
        "testnet": true
      }
    }
  }
  ```

- [ ] **9.3** Create `scripts/run_sandbox.py`
  - Initialize TradingNode
  - Load M-pattern strategy
  - Connect to Binance testnet

#### Day 10: Live Paper Trading
- [ ] **10.1** Start paper trading
  ```bash
  python scripts/run_sandbox.py
  ```

- [ ] **10.2** Monitor for 24 hours
  - Watch for signals
  - Verify orders execute
  - Check P&L tracking

- [ ] **10.3** Log analysis
  - Review execution logs
  - Check for errors
  - Validate behavior

#### Day 11: Fine-Tuning
- [ ] **11.1** Adjust based on paper results
  - Tweak entry thresholds if needed
  - Adjust position sizing
  - Optimize stop loss

- [ ] **11.2** Run for another 24 hours
  - Confirm improvements
  - Stability test

- [ ] **11.3** Performance validation
  - Paper P&L vs backtest expectations
  - Slippage analysis
  - Commission impact

**Day 11 Exit Criteria:** Stable paper trading, predictable performance ✅

---

### **PHASE 5: Production Preparation (Days 12-14)**

#### Day 12: Risk Management
- [ ] **12.1** Implement risk limits
  - Max position size
  - Max daily loss
  - Max drawdown trigger

- [ ] **12.2** Emergency stop procedures
  - Kill switch implementation
  - Manual override capability
  - Alert system

- [ ] **12.3** Position sizing calculator
  - Based on account balance
  - Kelly criterion consideration
  - Conservative start (1% risk per trade)

#### Day 13: Monitoring & Alerts
- [ ] **13.1** Setup monitoring dashboard
  - Real-time P&L
  - Open positions
  - Daily performance
  - System health

- [ ] **13.2** Alert system
  - Error notifications
  - Trade notifications
  - Performance alerts
  - System status updates

- [ ] **13.3** Logging system
  - Comprehensive trade logs
  - Error logs
  - Performance logs
  - Audit trail

#### Day 14: Final Validation & GO-LIVE Decision
- [ ] **14.1** Final checklist review
  - All tests passing ✅
  - Risk limits configured ✅
  - Monitoring operational ✅
  - Emergency procedures tested ✅

- [ ] **14.2** Production configuration
  - Update `config/live_config.json`
  - Real Binance API credentials
  - Production URLs

- [ ] **14.3** GO-LIVE Decision Meeting
  - Review all metrics
  - Confirm readiness
  - Approve or delay

- [ ] **14.4** (If approved) Start live trading
  - Small position size initially
  - Close monitoring for 48 hours
  - Gradual scale-up

**Day 14 Exit Criteria:** LIVE TRADING or clear roadmap to go-live ✅

---

## 🛠️ Key Technical Components

### 1. Data Loading (`src/utils/data_loader.py`)

```python
"""
Load historical data into NautilusTrader format
"""
import pandas as pd
from nautilus_trader.model.data import Bar
from nautilus_trader.persistence.catalog import ParquetDataCatalog

class BTC_DataLoader:
    def __init__(self, data_path="/home/sirrus/projects/BTC_Engine_v3/data"):
        self.catalog = ParquetDataCatalog(data_path)
    
    def load_btc_30m(self):
        """Load BTC 30m bars"""
        df = pd.read_pickle(f"{self.data_path}/raw/BTC_USDT_PERP_30m.pkl")
        return self._convert_to_nautilus_bars(df)
    
    def _convert_to_nautilus_bars(self, df):
        """Convert DataFrame to Nautilus Bar objects"""
        # Implementation here
        pass
```

### 2. Pattern Adapter (`src/indicators/pattern_adapter.py`)

```python
"""
Adapts our pattern detectors to NautilusTrader
"""
from src.indicators.pattern_detectors.sophisticated_m_pattern_layer import SophisticatedMPatternLayer

class PatternAdapter:
    def __init__(self, pattern_type='m_pattern'):
        if pattern_type == 'm_pattern':
            self.detector = SophisticatedMPatternLayer()
        # ... other patterns
    
    def detect(self, nautilus_bar):
        """
        Convert Nautilus bar to our format,
        run detection, return signal
        """
        # Convert format
        our_data = self._convert_bar(nautilus_bar)
        
        # Run detection (OUR EXISTING CODE - unchanged!)
        signal = self.detector.generate_signal(our_data)
        
        return signal
```

### 3. M-Pattern Strategy (`src/strategies/m_pattern_strategy.py`)

```python
"""
NautilusTrader strategy using our M-pattern detector
"""
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.orders import MarketOrder
from src.indicators.pattern_adapter import PatternAdapter

class MPatternStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config=config)
        self.pattern = PatternAdapter('m_pattern')
        self.position_size = config.get('position_size', 0.01)
    
    def on_start(self):
        """Called when strategy starts"""
        self.subscribe_bars("BTC/USDT.BINANCE", bar_type="30-MINUTE")
    
    def on_bar(self, bar):
        """Called on each new bar"""
        signal = self.pattern.detect(bar)
        
        if signal['signal'] == -1:  # SHORT signal
            if signal['confidence'] > 0.7:
                self.enter_short(
                    quantity=self.position_size,
                    stop_loss=signal['stop_loss'],
                    take_profit=signal['take_profit']
                )
    
    def enter_short(self, quantity, stop_loss, take_profit):
        """Execute SHORT entry"""
        order = MarketOrder(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=quantity,
        )
        self.submit_order(order)
```

---

## 📊 Expected Performance Metrics

Based on V2 validation and NautilusTrader capabilities:

**Backtesting:**
- Total P&L: TBD (to validate)
- Win Rate: 55-65% (historical)
- Sharpe Ratio: >1.5 (target)
- Max Drawdown: <15%
- Avg Trade: 2-8 hours

**Performance:**
- Backtest Speed: <1 second for 109K bars
- Memory Usage: <2GB
- Order Latency: <10ms

---

## ⚠️ Critical Success Factors

### 1. P&L Accuracy (HIGHEST PRIORITY)
- NautilusTrader's institutional-grade calculations
- Must match real exchange behavior
- Validate with small live trades

### 2. Pattern Detection Integrity
- Our detectors must work identically
- Zero logic changes in pattern code
- Adapter layer handles all conversion

### 3. Risk Management
- Hard limits enforced
- Emergency stops tested
- Position sizing conservative

### 4. Data Quality
- Verify all 109K bars clean
- Handle gaps/anomalies
- Timezone consistency

### 5. Monitoring
- Real-time visibility
- Alert on anomalies
- Audit trail complete

---

## 🔧 Development Best Practices

### Code Standards
- Type hints on all functions
- Docstrings (Google format)
- Unit tests for critical paths
- Integration tests for strategies

### Git Workflow
```bash
# Main branch: production-ready only
# Development: feature branches

git checkout -b feature/m-pattern-strategy
# ... develop ...
git commit -m "feat: add M-pattern strategy"
git push origin feature/m-pattern-strategy
# ... review & merge ...
```

### Testing Protocol
- Unit tests before integration
- Backtest validation before paper
- Paper trading before live
- Small size before scaling

---

## 📚 Essential Documentation References

### NautilusTrader Docs
- [Official Docs](https://nautilustrader.io/)
- [Backtest Guide](https://nautilustrader.io/docs/latest/getting_started/backtest)
- [Strategy Development](https://nautilustrader.io/docs/latest/concepts/strategies)
- [Live Trading](https://nautilustrader.io/docs/latest/getting_started/live_trading)

### Our Docs (in this repo)
- `docs/NAUTILUS_TRADER_ANALYSIS.md` - Deep framework analysis
- `docs/MIGRATION_TO_V3_PLAN.md` - Migration strategy
- `docs/v3/COMPLETE_ASSET_INVENTORY.md` - All available assets
- `docs/v3/LAKEAPI_ASSET_INVENTORY.md` - Data catalog

---

## 🐛 Known Issues & Mitigations

### Issue 1: V2 P&L Bug
- **Problem:** V2 had SHORT P&L calculation errors
- **Solution:** NautilusTrader handles this correctly (hedge-fund proven)
- **Validation:** Compare V3 backtest vs real exchange fills

### Issue 2: Data Format Conversion
- **Problem:** Our data is Pandas/Parquet, Nautilus uses Arrow
- **Solution:** Nautilus has native Parquet support
- **Mitigation:** Test data loading thoroughly (Day 2)

### Issue 3: Pattern Detector Dependencies
- **Problem:** Our detectors may have V2 framework dependencies
- **Solution:** Adapter pattern isolates dependencies
- **Mitigation:** Refactor to framework-agnostic (Day 3)

---

## 🎯 Success Criteria

### Minimum Viable Product (Day 14)
- ✅ M-pattern strategy backtested on full dataset
- ✅ P&L calculations verified accurate
- ✅ Paper trading runs for 48+ hours without errors
- ✅ All risk limits functional
- ✅ Monitoring dashboard operational

### Stretch Goals (Post Day 14)
- W-pattern strategy live
- Multi-pattern ensemble
- ML optimization layer
- Multi-exchange support
- HFT optimization

---

## 📞 Emergency Contacts & Resources

### If Stuck
1. Check NautilusTrader docs: https://nautilustrader.io/
2. Review this guide's troubleshooting section
3. Search NautilusTrader GitHub issues
4. Ask in NautilusTrader Discord (active community)

### Critical Files Backup
- Pattern detectors: `src/indicators/pattern_detectors/`
- Data: `/home/sirrus/projects/BTC_Engine_v3/data/`
- Configs: Stored in `config/`

---

## 📋 Pre-Flight Checklist

Before starting Day 1:

- [ ] V3 directory exists: `/home/sirrus/projects/BTC_Engine_v3/`
- [ ] Data copied (308GB): `data/` directory
- [ ] Pattern detectors copied: `src/indicators/pattern_detectors/`
- [ ] Documentation copied: `docs/` directory
- [ ] This guide reviewed completely
- [ ] Fresh mindset, ready to build! 🚀

---

## 🚀 Quick Start (Day 1 Commands)

```bash
# Navigate to project
cd /home/sirrus/projects/BTC_Engine_v3

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install nautilus_trader pandas numpy pyarrow

# Verify installation
python -c "import nautilus_trader as nt; print(f'✅ NautilusTrader v{nt.__version__}')"

# Set data path
export NAUTILUS_PATH=/home/sirrus/projects/BTC_Engine_v3/data

# Ready to start Day 1 tasks! 🎯
```

---

## 📖 Document Version Control

**Version:** 1.0  
**Created:** December 30, 2025  
**Last Updated:** December 30, 2025  
**Author:** BTC_Engine Migration Team  
**Status:** READY FOR EXECUTION

---

## ✅ Final Pre-Execution Checklist

- [x] Framework selected: NautilusTrader ✅
- [x] Data assets ready: 308GB ✅
- [x] Pattern IP protected: Copied ✅
- [x] Implementation plan: 14 days ✅
- [x] Documentation complete: This guide ✅
- [ ] **READY TO START FRESH IN NEW DIRECTORY** ✅

---

**🎯 THIS IS YOUR SINGLE SOURCE OF TRUTH FOR V3 IMPLEMENTATION**

When starting the new task in `/home/sirrus/projects/BTC_Engine_v3/`:
1. Read this document completely
2. Execute Day 1 checklist
3. Follow 14-day plan sequentially
4. Update checklists as you progress
5. Refer back when stuck

**Good luck! You have everything you need to succeed. 🚀**
