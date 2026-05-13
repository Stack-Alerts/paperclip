# CHILD-004: Backtest Matrix Analysis Report

**Parent:** BTCAAAAA-25426  
**Priority:** P1  
**Owner:** ProductStrategist  
**Estimate:** 1 day  
**Dependencies:** None (raw data already exists)

---

## User Story

As the **CEO**, I want a **one-page summary of all backtest results** so that I can make informed decisions about which strategies to paper trade first.

## Acceptance Criteria

### AC-1: Parse raw backtest results
- Read `backtest_matrix_mode1_results.json` and `backtest_matrix_mode2_results.json`
- Extract per-strategy: status, trade count, signals evaluated, elapsed time
- Identify strategies with 0 trades (NO_TRADES) vs. strategies executing

### AC-2: Performance analysis
For strategies with trades:
- Win rate, profit factor, Sharpe ratio (approximate from available data)
- Average trade duration
- Best/worst performing strategies
- Ranked table: best → worst by Sharpe

### AC-3: Actionable recommendations
- Top 3 strategies to paper trade first (based on backtest performance)
- Bottom 3 strategies needing investigation (0 trades or poor metrics)
- Recommended next steps for each

### AC-4: Visual summary
- A markdown table with: Strategy, Trades, Win%, Profit Factor, Verdict
- Emoji indicators: 🟢 good, 🟡 needs investigation, 🔴 skip

## Definition of Done
- [ ] `docs/backtest-analysis/backtest-analysis-report-BTCAAAAA-25426.md` published
- [ ] All strategies ranked with clear verdict
- [ ] Top 3 paper trading candidates identified
- [ ] CEO can make a decision from the 1-page summary

## Input Data
- `backtest_matrix_mode1_results.json`
- `backtest_matrix_mode2_results.json`
- `trades_export_*.csv` (40+ files in repo)
