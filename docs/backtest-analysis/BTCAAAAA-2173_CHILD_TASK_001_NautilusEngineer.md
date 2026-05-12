# Child Task for NautilusEngineer

**Parent**: BTCAAAAA-2173
**Priority**: Critical
**Assigned to**: NautilusEngineer (a472d315-3e2e-4c3b-a1ba-a931295628cc)

## Objective

Fix critical blocking issues identified in EXPERT_MODE 5-report for both strategies under review.

## Deliverables

### 1. Fix MAX_LEVERAGE from 10x to 1.0
- **Location**: Backtest configuration (likely `multicore_config` or optimizer config)
- **Current**: `Max Leverage: 10x` in evidence_capture_20260512.txt lines 11, 29600+, 34301
- **Target**: `MAX_LEVERAGE=1.0` per hard policy
- **Effort**: 30min
- **Impact**: Enables compliant backtesting; without this, all results are invalid

### 2. Add DAILY_LOSS_LIMIT=$500
- **Location**: Risk configuration in the backtest engine or strategy executor
- **Current**: Not configured — no DAILY_LOSS_LIMIT found in any log or config
- **Target**: `DAILY_LOSS_LIMIT=$500`
- **Effort**: 30min
- **Impact**: Risk compliance — current state has no daily loss limit

### 3. Investigate Mode 1 vs Mode 2 trade count discrepancy
- **Evidence**: `tests/ui_qt/evidence_capture_20260512.txt` lines 33547-33548
  - Mode 1 (Historical multicore): 286 trades
  - Mode 2 (Live replay sequential): 31 trades
  - Ratio: 9.2x on identical data (9,606 bars, same period)
- **Hypotheses**: 
  - Multicore engine generates phantom trades via parallel execution race conditions
  - Sequential mode misses valid entries due to bar-by-bar processing issue
  - Trade deduplication (107 duplicates rejected in Mode 1) suggests over-generation
- **Required**: Root cause analysis + fix for whichever mode is buggy
- **Effort**: 1-2 days
- **Impact**: All backtest results are untrustworthy until this is resolved

### 4. Reduce risk per trade from 10% to 1-2%
- **Current**: `Risk per Trade: 10% of capital`
- **Target**: Institutional standard 1-2%
- **Effort**: 15min

### 5. Add 2% fixed stop loss parameter
- **Current**: Uses adaptive Fibonacci SL with dynamic range (1.2%-2.5%), not a fixed 2%
- **Target**: Fixed 2% stop loss per policy
- **Effort**: 30min

## Verification

After fixes, re-run both Mode 1 and Mode 2 backtests on 50% Asia Rejection Simple (v27) and verify:
- [ ] Mode 1 and Mode 2 trade counts converge within 2x
- [ ] MAX_LEVERAGE=1.0 confirmed in config output
- [ ] DAILY_LOSS_LIMIT=$500 confirmed in config output
- [ ] Risk per trade ≤ 2%
- [ ] Fixed 2% SL confirmed

## Next Owner

After fixes, route back to BacktestAnalyst (79beb038) for EXPERT_MODE re-assessment.
