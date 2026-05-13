# CHILD-002: CI Walkforward Validation Pipeline

**Parent:** BTCAAAAA-25426  
**Priority:** P0  
**Owner:** DevOps  
**Estimate:** 2 days  
**Dependencies:** CHILD-001 (strategy factory) — needs strategies to validate

---

## User Story

As a **strategy developer**, I want every new strategy to **automatically run walkforward validation in CI** so that I know immediately if a strategy meets the 65%+ win rate bar before it reaches paper trading.

## Acceptance Criteria

### AC-1: Walkforward runner script
- A script `scripts/run_walkforward_ci.py` that:
  - Accepts a strategy file path and config
  - Runs walkforward validation using the existing walkforward infrastructure
  - Uses 30min data (existing: `data/raw/BTC_USDT_PERP_30m.pkl`)
  - Outputs: win rate, profit factor, Sharpe ratio, max drawdown, total trades
  - Exits 0 if metrics pass thresholds, exits 1 if they fail
  - Timeout-safe (max 10 min per strategy)

### AC-2: CI workflow
- A new GitHub Actions workflow (`.github/workflows/strategy-walkforward.yml`):
  - Triggers: on push to `src/strategies/` matching `strategy_*.py`
  - Jobs: detect changed strategies, run walkforward on each
  - Posts results as a PR/commit check with pass/fail
  - Caches data files to avoid 47GB re-download each run

### AC-3: Threshold gates
Strategies must meet minimums to pass CI:
- Win rate: >= 60% (warning at 55-60%)
- Profit factor: >= 1.5
- Max drawdown: <= 20%
- Minimum trades: >= 20 (statistical significance)

### AC-4: Results artifact
- Walkforward results are uploaded as a CI artifact (JSON)
- Results also append to a running `walkforward_results_registry.json` at repo root
- This enables the ProductStrategist to track progress across all strategies

## Definition of Done
- [ ] `scripts/run_walkforward_ci.py` runs on any strategy and returns pass/fail
- [ ] CI workflow triggers on strategy file changes
- [ ] Walkforward results artifact uploaded
- [ ] Registry file updated with each run
- [ ] At least 2 existing strategies tested through the pipeline
- [ ] Documentation: `docs/runbook-walkforward-ci.md`

## References
- Existing walkforward: `scripts/archived/walkforward_validation.py`, `scripts/archived/walkforward_15min.py`
- Existing summary: `all_blocks_walkforward_summary.json` (84/84 blocks passed)
- Data file: `data/raw/BTC_USDT_PERP_30m.pkl` (109,949 bars)
- CI workflows: `.github/workflows/test.yml`, `.github/workflows/lint.yml`
- Backtest framework: `scripts/run_backtest.py`
