# CHILD TASK 001 — Fix NautilusTrader API Drift in Optimizer Modules

**Parent**: BTCAAAAA-20265
**Priority**: Critical (blocks backtest execution)
**Assigned to**: NautilusEngineer (a472d315-3e2e-4c3b-a1ba-a931295628cc)
**Status**: todo

## Objective

Update all optimizer_v3 modules to NautilusTrader v1.226.0 constructor APIs.

## Files to Fix

- src/optimizer_v3/core/results/statistical_comparison.py
- src/optimizer_v3/core/results/state_manager.py
- src/optimizer_v3/core/results/trade_analyzer.py
- src/optimizer_v3/core/results/session_history.py
- src/optimizer_v3/core/results/risk_metrics.py
- src/optimizer_v3/core/results/recheck_metrics.py
- src/optimizer_v3/core/results/institutional_metrics.py
- src/optimizer_v3/core/results/config_diff.py
- src/optimizer_v3/core/results/results_ranker.py
- src/optimizer_v3/core/results/csv_exporter.py
- src/optimizer_v3/database/nautilus_types.py
- src/optimizer_v3/core/validator.py
- tests/strategies/walkforward_test.py

## Migration Patterns

- Money(1.5) -> Money.from_str("1.5")
- Price(50000.50) -> Price.from_str("50000.50")
- Quantity(1.5) -> Quantity.from_str("1.5")
- Quantity(1) -> Quantity.from_int(1)

## Acceptance Criteria

- [ ] All optimizer_v3 modules import and instantiate without API errors
- [ ] Walkforward test passes
- [ ] No remaining deprecated single-arg constructors
