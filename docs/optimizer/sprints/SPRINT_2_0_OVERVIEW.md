# SPRINT 2.0: REAL DATA INTEGRATION - MASTER OVERVIEW
**Replace Demo Data with Real Historical & Live Data - Institutional Grade**

**Status**: ☐ Not Started  
**Priority**: 🔴🔴🔴 CRITICAL - System functional but uses hardcoded demo data  
**Total Duration**: 10-12 days (updated 2026-02-06 - institutional complexity validated)  
**Sub-Sprints**: 4  
**Architecture**: Validated from HOD Rejection v9 (Production Strategy)

---

## 🎯 EXECUTIVE SUMMARY

### Current State
The BTC Engine v3 system is **FULLY FUNCTIONAL** with demo data:
- ✅ Complete execution engine (BacktestWorker.run())
- ✅ Trade lifecycle management (OPEN → CLOSED)
- ✅ All 7 tabs integrated (Trades, Metrics, AI, etc.)
- ✅ Progress tracking and UI updates
- ❌ **Uses hardcoded demo data** (5 hardcoded sources)

### Gap Analysis Results
**Total Gaps**: 12 (down from initial estimate of 67!)
- Category 1: Data Loading (2 gaps)
- Category 2: Signal Evaluation (3 gaps)
- Category 3: Real Pricing (2 gaps)
- Category 4: TP/SL Management (3 gaps)
- Category 5: Exit Management (2 gaps)

### Components to Build
Only **3 new components** required:
1. **SignalEvaluator** - Evaluate building block signals on each candle
2. **TPSLCalculator** - Calculate TP/SL levels (Fibonacci/Hybrid/Fixed)
3. **AdaptiveSLManager** - Update SL each candle based on Adaptive v2.0

### Sprint Breakdown

| Sub-Sprint | Focus | Duration | Tasks | Status |
|------------|-------|----------|-------|--------|
| 2.0.1 | Data Loading & Integration | 2 days | 5 | ☐ Not Started |
| 2.0.2 | **Institutional Signal Evaluation** | **5 days** | **9** | ☐ Not Started |
| 2.0.3 | TP/SL Management | 3 days | 6 | ☐ Not Started |
| 2.0.4 | Exit Management & Testing | 2 days | 7 | ☐ Not Started |

**Total**: 27 tasks across 4 sub-sprints (updated 2026-02-06)

**Key Update**: Sprint 2.0.2 expanded from 3 days/6 tasks → 5 days/9 tasks due to institutional complexity validated from HOD Rejection v9 production strategy.

---

## 📊 DETAILED SUB-SPRINT STRUCTURE

### **Sprint 2.0.1: Data Loading & Integration** (2 days)
**File**: `SPRINT_2_0_1_DATA_LOADING.md`

**Objective**: Connect DataManager to BacktestWorker, load real bars

**Tasks**:
- 2.0.1.1: Add date range selection to UI (start_date, end_date spinboxes)
- 2.0.1.2: Create BacktestDataProvider class
- 2.0.1.3: Integrate DataManager.load_bars() in BacktestWorker
- 2.0.1.4: Replace hardcoded `total_candles = 14040`
- 2.0.1.5: Test real bar loading end-to-end

**Deliverables**:
- Date range UI controls
- BacktestDataProvider implementation
- Real bars loaded from DataManager

**Acceptance Criteria**:
- [ ] Date range selection working
- [ ] Real bars load successfully
- [ ] Progress tracking accurate (real candle count)
- [ ] No hardcoded candle counts remain

---

### **Sprint 2.0.2: Institutional Signal Evaluation System** (5 days)
**File**: `SPRINT_2_0_2_SIGNAL_EVALUATION.md`  
**Architecture**: `SPRINT_2_0_2_SIGNAL_EVALUATION_ARCHITECTURE.md` (1,448 lines)  
**Validated From**: HOD Rejection v9 (Production Strategy)

**Objective**: Build institutional-grade signal evaluation with RECHECK validation, TIMING constraints, and 3-tier EXIT hierarchy

**Tasks** (9 total - expanded from 6):
- 2.0.2.1: Design Institutional SignalEvaluator Architecture (8 hours)
- 2.0.2.2: Implement InstitutionalSignalEvaluator Core (~1,000 lines, 12 hours)
- 2.0.2.3: Implement RecheckValidator (~300 lines, 6 hours)
- 2.0.2.4: Implement TimingChainManager (~200 lines, 4 hours)
- 2.0.2.5: Implement ExitHierarchyEvaluator (~250 lines, 6 hours)
- 2.0.2.6: Implement ConfluenceCalculator with scaling (4 hours)
- 2.0.2.7: Connect to strategy config from orchestrator (3 hours)
- 2.0.2.8: Replace hardcoded trade_schedule (2 hours)
- 2.0.2.9: Comprehensive testing (8 hours)

**Key Institutional Features**:
- **Multi-level RECHECK validation** (up to 3 deep)
  - reference_type: PARENT vs SIGNAL (fixes nested recheck bug)
  - timing_mode: AT vs WITHIN (institutional flexibility)
  - signal_fire_bar preservation through chains
- **Sequential TIMING constraints** (signal chains with windows)
- **3-tier EXIT hierarchy** (STRATEGY → BLOCK → SIGNAL)
- **TP-aware exit calculations** (dynamic percentage on remaining position)
- **Single trade management** (institutional risk control)

**Deliverables** (~1,750 lines total):
- InstitutionalSignalEvaluator class (~1,000 lines)
- RecheckValidator class (~300 lines - ENHANCED)
- TimingChainManager class (~200 lines)
- ExitHierarchyEvaluator class (~250 lines)
- ConfluenceCalculator class (~100 lines RECHECK bonuses)
- Complete architecture documentation (1,448 lines)

**Acceptance Criteria**:
- [ ] All 9 tasks complete
- [ ] ~1,750 lines implementation
- [ ] RECHECK validation working (AT/WITHIN modes)
- [ ] TIMING constraints validated
- [ ] 3-tier EXIT hierarchy functional
- [ ] TP-aware exit calculations accurate
- [ ] Signals evaluate correctly on real bars
- [ ] Confluence threshold with scaling working
- [ ] Entries triggered by real signals (not schedule)
- [ ] All building blocks supported
- [ ] HOD Rejection v9 validation passing
- [ ] 100% test coverage

**Critical Bug Fixed**: Nested RECHECK "of signal" reference calculation (production bug affecting all strategies with complex RECHECK chains)

---

### **Sprint 2.0.3: TP/SL Management** (3 days)
**File**: `SPRINT_2_0_3_TPSL_MANAGEMENT.md`

**Objective**: Implement TP/SL calculation and Adaptive SL v2.0

**Tasks**:
- 2.0.3.1: Implement TPSLCalculator (Fibonacci/Hybrid/Fixed)
- 2.0.3.2: Implement Adaptive SL v2.0 logic
- 2.0.3.3: Connect to user config parameters
- 2.0.3.4: Implement emergency SL during delay period
- 2.0.3.5: Implement SL updates each candle
- 2.0.3.6: Test TP/SL management end-to-end

**Deliverables**:
- TPSLCalculator class
- AdaptiveSLManager class
- Real TP/SL levels (not hardcoded)

**Acceptance Criteria**:
- [ ] TP/SL calculated from real bars
- [ ] Adaptive SL updates working
- [ ] All 3 modes working (Fib/Hybrid/Fixed)
- [ ] User config parameters applied

---

### **Sprint 2.0.4: Exit Management & Testing** (2 days)
**File**: `SPRINT_2_0_4_EXIT_TESTING.md`

**Objective**: Implement real exit detection, complete integration, test

**Tasks**:
- 2.0.4.1: Implement TP/SL hit detection
- 2.0.4.2: Implement exit condition evaluation
- 2.0.4.3: Use real prices (replace fake `50000 + offset`)
- 2.0.4.4: Use real timestamps (replace fake datetime)
- 2.0.4.5: Calculate real PnL (not predetermined win/loss)
- 2.0.4.6: Complete integration testing
- 2.0.4.7: Functional & data accuracy validation

**Deliverables**:
- Real exit management
- Real pricing and timestamps
- Complete integration

**Acceptance Criteria**:
- [ ] Exits triggered by real TP/SL hits
- [ ] Real prices used throughout
- [ ] Real PnL calculated from actual trades
- [ ] All accuracy tests passing
- [ ] System produces realistic backtest results

---

## 🔗 DEPENDENCIES

### External Dependencies
- ✅ DataManager (`src/data_manager/`) - READY
- ✅ NautilusDataLoader - READY
- ✅ Building Block Registry - READY
- ✅ Strategy Orchestrator - READY

### Internal Dependencies
```
Sprint 2.0.1 → Sprint 2.0.2 → Sprint 2.0.3 → Sprint 2.0.4
(Data Loading) (Signal Eval) (TP/SL Mgmt) (Exit & Test)
```

Each sub-sprint depends on previous completion.

---

## ✅ SPRINT COMPLETION CRITERIA

**Sprint 2.0 Complete When**:
- [ ] All 4 sub-sprints complete
- [ ] All 24 tasks complete
- [ ] All 5 hardcoded data sources replaced
- [ ] All 3 new components implemented and tested
- [ ] System runs backtest with 100% real data
- [ ] All tabs display real results
- [ ] Functional tests passing
- [ ] Data accuracy tests passing
- [ ] Performance acceptable (< 2min for 180-day backtest)

**Sign-off Required**:
- [ ] Developer
- [ ] Lead
- [ ] NautilusTrader Expert
- [ ] QA (Functional & Data Accuracy)

---

## 📁 REFERENCE DOCUMENTS

**Gap Analysis**:
- `SPRINT_2_0_GAP_ANALYSIS_FINAL.md` - Correct gap analysis (12 gaps)

**Sub-Sprint Files**:
- `SPRINT_2_0_1_DATA_LOADING.md`
- `SPRINT_2_0_2_SIGNAL_EVALUATION.md`
- `SPRINT_2_0_3_TPSL_MANAGEMENT.md`
- `SPRINT_2_0_4_EXIT_TESTING.md`

**Code References**:
- `src/strategy_builder/ui/backtest_config_panel.py` - BacktestWorker (lines 86-265)
- `src/data_manager/unified_manager.py` - DataManager
- `src/data_manager/nautilus_loader.py` - Nautilus integration

---

## 🚀 IMPLEMENTATION SEQUENCE

**Week 1** (Days 1-5):
- Day 1-2: Sprint 2.0.1 (Data Loading)
- Day 3-7: Sprint 2.0.2 (Institutional Signal Evaluation)

**Week 2** (Days 8-12):
- Day 8-10: Sprint 2.0.3 (TP/SL Management)
- Day 11-12: Sprint 2.0.4 (Exit & Testing)

**Total**: 10-12 days (updated 2026-02-06 based on institutional complexity validation)

---

## 📊 PROGRESS TRACKING

### Overall Sprint Progress
- Sub-Sprints Complete: 0 / 4 (0%)
- Tasks Complete: 0 / 27 (0%)
- Components Built: 0 / 8 (0%)

**Components** (8 total - updated from 3):
1. BacktestDataProvider
2. InstitutionalSignalEvaluator
3. RecheckValidator (with AT/WITHIN modes)
4. TimingChainManager
5. ExitHierarchyEvaluator
6. ConfluenceCalculator
7. TPSLCalculator
8. AdaptiveSLManager

### Sub-Sprint Status
- [ ] Sprint 2.0.1: Data Loading
- [ ] Sprint 2.0.2: Signal Evaluation
- [ ] Sprint 2.0.3: TP/SL Management
- [ ] Sprint 2.0.4: Exit Management & Testing

---

## 🎯 SUCCESS METRICS

**Functional Metrics**:
- [ ] Backtest executes with real bars
- [ ] Trades generated from real signals
- [ ] TP/SL levels calculated from real data
- [ ] Exits triggered by real price hits
- [ ] PnL calculated from actual entry/exit prices

**Data Accuracy Metrics**:
- [ ] All prices from real bars (no fake `50000 + offset`)
- [ ] All timestamps from real bars (no fake datetime)
- [ ] Trade count varies based on real signals (not fixed 24)
- [ ] Win/loss determined by real outcomes (not predetermined)
- [ ] Metrics calculated from real trade results

**Performance Metrics**:
- [ ] 180-day backtest: < 2 minutes
- [ ] 1000 bars: < 10 seconds
- [ ] Memory usage: < 500MB
- [ ] No memory leaks
- [ ] Thread-safe operations verified

---

**Next**: Begin Sprint 2.0.1 - Data Loading & Integration
